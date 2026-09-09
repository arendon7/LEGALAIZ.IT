from __future__ import annotations

"""M36.1 — asignación profesional consistente a nivel de expediente.

Coordina la asignación manual ya existente en M32.6 para todos los documentos de
un intake M36.0. La coordinación es una saga recuperable porque M32.6 conserva
bitácoras append-only en archivos además de persistencia SQL. Ningún estado
M36.1 equivale a aprobación jurídica, QA, liberación o entrega.
"""

import json
import re
from typing import Any, Mapping
import uuid

import core_v11 as core
from legalai_platform.approval_desk_operations import ApprovalDeskOperations
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.approval_notification_center import ApprovalNotificationCenter
from legalai_platform.fulfillment_intake_m36_0 import FulfillmentIntakeCenter, FulfillmentIntakeError


SCHEMA_VERSION = "36.1.0"
ASSIGNMENT_STATES = frozenset({"PENDING", "PARTIAL", "ASSIGNED", "COMPLETE"})
REVIEW_ALLOWED_STATES = frozenset({
    "EN_REVISION_JURIDICA",
    "OBSERVADO",
    "CORREGIDO",
    "APROBADO_JURIDICAMENTE",
    "EN_QA",
    "APROBADO_QA",
    "ESCALADO",
})


class ProfessionalAssignmentError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 100 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ProfessionalAssignmentError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _decode_ids(raw: Any) -> list[str]:
    try:
        values = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProfessionalAssignmentError("ASSIGNMENT_LEDGER_INVALID", "La asignación registrada no puede verificarse.", 422) from exc
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ProfessionalAssignmentError("ASSIGNMENT_LEDGER_INVALID", "La asignación registrada no puede verificarse.", 422)
    return list(dict.fromkeys(values))


class ProfessionalAssignmentCenter:
    """Case-level saga over the existing M32.6 assignment operation."""

    def __init__(
        self,
        fulfillment: FulfillmentIntakeCenter,
        operations: ApprovalDeskOperations,
        notifications: ApprovalNotificationCenter,
        *,
        db_factory=None,
    ):
        self.fulfillment = fulfillment
        self.operations = operations
        self.notifications = notifications
        self.db_factory = db_factory or core.db

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m36_professional_assignment(
              id TEXT PRIMARY KEY,
              fulfillment_intake_id TEXT NOT NULL UNIQUE,
              case_id TEXT NOT NULL UNIQUE,
              specialist_id TEXT NOT NULL,
              qa_id TEXT NOT NULL,
              state TEXT NOT NULL,
              completed_desk_ids_json TEXT NOT NULL DEFAULT '[]',
              notified_desk_ids_json TEXT NOT NULL DEFAULT '[]',
              initiated_by TEXT NOT NULL,
              last_error_code TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m36_assignment_state
              ON m36_professional_assignment(state,updated_at);
            """
        )

    @staticmethod
    def _require_admin(actor: Mapping[str, Any]) -> None:
        if str(actor.get("role") or "") != "admin" or not str(actor.get("id") or "").strip():
            raise PermissionDenied("Solo administración puede asignar responsables del expediente.")

    def _professional_directory(self, actor: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        directory = self.operations.professionals(actor)
        specialists = {str(item.get("id")): dict(item) for item in directory.get("specialists", []) if item.get("id")}
        qa = {str(item.get("id")): dict(item) for item in directory.get("qa", []) if item.get("id")}
        return specialists, qa

    def professionals(self, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        specialists, qa = self._professional_directory(actor)
        return {
            "schema": "legalai_m36_1_professional_directory_v1",
            "schema_version": SCHEMA_VERSION,
            "specialists": [
                {"id": item["id"], "name": item.get("name"), "specialty": item.get("specialty")}
                for item in specialists.values()
            ],
            "qa": [
                {"id": item["id"], "name": item.get("name"), "role": item.get("role")}
                for item in qa.values()
            ],
            "policy": {
                "manual_selection_required": True,
                "automatic_matching": False,
                "distinct_specialist_and_qa": True,
                "specialty_is_advisory": True,
            },
        }

    def _preflight(
        self,
        actor: dict[str, Any],
        case_id: str,
        specialist_id: str,
        qa_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        specialist_id = _safe_id(specialist_id, "specialist_id")
        qa_id = _safe_id(qa_id, "qa_id")
        if specialist_id == qa_id:
            raise ProfessionalAssignmentError(
                "SEPARATION_OF_DUTIES_REQUIRED",
                "El especialista jurídico y QA deben ser personas distintas.",
                422,
            )
        specialists, qa_users = self._professional_directory(actor)
        specialist = specialists.get(specialist_id)
        qa = qa_users.get(qa_id)
        if not specialist:
            raise ProfessionalAssignmentError("SPECIALIST_NOT_AVAILABLE", "El especialista seleccionado no está activo o no tiene el rol requerido.", 422)
        if not qa:
            raise ProfessionalAssignmentError("QA_NOT_AVAILABLE", "El responsable QA seleccionado no está activo o no tiene el rol requerido.", 422)
        try:
            intake = self.fulfillment.detail(actor, case_id)
        except FulfillmentIntakeError as exc:
            raise ProfessionalAssignmentError("FULFILLMENT_NOT_READY", "El expediente no tiene un intake M36.0 íntegro para asignación.", exc.status) from exc
        journey_state = str(intake.get("journey_state") or "")
        if journey_state not in REVIEW_ALLOWED_STATES:
            raise ProfessionalAssignmentError(
                "JOURNEY_NOT_ASSIGNABLE",
                f"El expediente está en {journey_state or 'estado desconocido'} y no admite asignación profesional M36.1.",
            )
        desk_ids = [str(item) for item in intake.get("desk_case_ids") or []]
        if not desk_ids or len(set(desk_ids)) != len(desk_ids) or len(desk_ids) != int(intake.get("document_count") or 0):
            raise ProfessionalAssignmentError("DESK_COVERAGE_INVALID", "El intake M36.0 no conserva una mesa única por documento.", 422)
        for desk_id in desk_ids:
            detail = self.operations.workspace.detail(actor, desk_id)
            if str(detail.get("source_case_id") or "") != case_id:
                raise ProfessionalAssignmentError("DESK_SOURCE_MISMATCH", "Una mesa del intake apunta a otro expediente.", 422)
            if not bool((detail.get("audit") or {}).get("valid")):
                raise ProfessionalAssignmentError("APPROVAL_CHAIN_INVALID", "Una cadena de aprobación M32.5 no es íntegra.", 422)
            audit = self.operations.verify_chain(desk_id)
            if not audit.get("valid"):
                raise ProfessionalAssignmentError("OPERATIONS_CHAIN_INVALID", "Una cadena operativa M32.6 no es íntegra.", 422)
            current = self.operations.state(actor, desk_id).get("operations") or {}
            current_specialist = (current.get("assigned_specialist") or {}).get("id")
            current_qa = (current.get("assigned_qa") or {}).get("id")
            if (current_specialist or current_qa) and (str(current_specialist or "") != specialist_id or str(current_qa or "") != qa_id):
                raise ProfessionalAssignmentError(
                    "EXISTING_ASSIGNMENT_CONFLICT",
                    "Una mesa ya tiene responsables distintos. M36.1 no realiza reasignaciones silenciosas.",
                )
        return intake, specialist, qa, desk_ids

    @staticmethod
    def _row(con, case_id: str):
        row = con.execute("SELECT * FROM m36_professional_assignment WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None

    def _checkpoint(
        self,
        con,
        assignment_id: str,
        *,
        state: str,
        completed: list[str],
        notified: list[str],
        error_code: str | None,
    ) -> None:
        if state not in ASSIGNMENT_STATES:
            raise ProfessionalAssignmentError("ASSIGNMENT_STATE_INVALID", "Estado interno de asignación inválido.", 500)
        con.execute(
            """UPDATE m36_professional_assignment
               SET state=?,completed_desk_ids_json=?,notified_desk_ids_json=?,last_error_code=?,updated_at=?
               WHERE id=?""",
            (
                state,
                json.dumps(completed, ensure_ascii=False, separators=(",", ":")),
                json.dumps(notified, ensure_ascii=False, separators=(",", ":")),
                error_code,
                core.now(),
                assignment_id,
            ),
        )
        con.commit()

    def assign(
        self,
        actor: dict[str, Any],
        case_id: str,
        specialist_id: str,
        qa_id: str,
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        specialist_id = _safe_id(specialist_id, "specialist_id")
        qa_id = _safe_id(qa_id, "qa_id")
        intake, specialist, qa, desk_ids = self._preflight(actor, case_id, specialist_id, qa_id)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            existing = self._row(con, case_id)
            if existing:
                if existing["specialist_id"] != specialist_id or existing["qa_id"] != qa_id:
                    raise ProfessionalAssignmentError(
                        "ASSIGNMENT_REQUEST_CONFLICT",
                        "El expediente ya tiene una asignación M36.1 con otra pareja profesional.",
                    )
                assignment = existing
                completed = _decode_ids(existing.get("completed_desk_ids_json"))
                notified = _decode_ids(existing.get("notified_desk_ids_json"))
                if set(completed) - set(desk_ids) or set(notified) - set(desk_ids):
                    raise ProfessionalAssignmentError("ASSIGNMENT_LEDGER_INVALID", "El ledger contiene mesas ajenas al intake actual.", 422)
                if existing.get("state") == "COMPLETE":
                    if set(completed) != set(desk_ids) or set(notified) != set(desk_ids):
                        raise ProfessionalAssignmentError(
                            "ASSIGNMENT_LEDGER_INVALID",
                            "Una asignación marcada COMPLETE no conserva cobertura total.",
                            422,
                        )
                    return self._public(existing, intake, specialist, qa, desk_ids, completed, notified, idempotent=True)
            else:
                assignment_id = "ASN-" + uuid.uuid4().hex[:14].upper()
                now = core.now()
                con.execute(
                    """INSERT INTO m36_professional_assignment(
                         id,fulfillment_intake_id,case_id,specialist_id,qa_id,state,
                         completed_desk_ids_json,notified_desk_ids_json,initiated_by,last_error_code,created_at,updated_at
                       ) VALUES(?,?,?,?,?,'PENDING','[]','[]',?,NULL,?,?)""",
                    (
                        assignment_id,
                        intake["fulfillment_intake_id"],
                        case_id,
                        specialist_id,
                        qa_id,
                        actor["id"],
                        now,
                        now,
                    ),
                )
                con.commit()
                assignment = self._row(con, case_id)
                completed = []
                notified = []

            assignment_id = str(assignment["id"])
            try:
                for desk_id in desk_ids:
                    state = self.operations.state(actor, desk_id)
                    operations = state.get("operations") or {}
                    current_specialist = (operations.get("assigned_specialist") or {}).get("id")
                    current_qa = (operations.get("assigned_qa") or {}).get("id")
                    if str(current_specialist or "") == specialist_id and str(current_qa or "") == qa_id:
                        if desk_id not in completed:
                            completed.append(desk_id)
                            self._checkpoint(con, assignment_id, state="PARTIAL", completed=completed, notified=notified, error_code=None)
                        continue
                    if current_specialist or current_qa:
                        raise ProfessionalAssignmentError("EXISTING_ASSIGNMENT_CONFLICT", "Una mesa cambió de responsables durante la saga.")
                    self.operations.update_assignment(actor, desk_id, specialist_id, qa_id)
                    completed.append(desk_id)
                    self._checkpoint(con, assignment_id, state="PARTIAL", completed=completed, notified=notified, error_code=None)
                self._checkpoint(con, assignment_id, state="ASSIGNED", completed=completed, notified=notified, error_code=None)

                for desk_id in desk_ids:
                    if desk_id in notified:
                        continue
                    self.notifications.evaluate(actor, desk_id)
                    notified.append(desk_id)
                    self._checkpoint(con, assignment_id, state="ASSIGNED", completed=completed, notified=notified, error_code=None)

                self._checkpoint(con, assignment_id, state="COMPLETE", completed=completed, notified=notified, error_code=None)
            except Exception as exc:
                code = exc.code if isinstance(exc, ProfessionalAssignmentError) else exc.__class__.__name__.upper()[:80]
                current_state = "ASSIGNED" if len(completed) == len(desk_ids) else "PARTIAL"
                self._checkpoint(con, assignment_id, state=current_state, completed=completed, notified=notified, error_code=code)
                raise

            row = self._row(con, case_id)
            core.audit(
                con,
                actor["id"],
                "m36_professional_assignment",
                assignment_id,
                "assignment_completed",
                {
                    "case_id": case_id,
                    "fulfillment_intake_id": intake["fulfillment_intake_id"],
                    "specialist_id": specialist_id,
                    "qa_id": qa_id,
                    "desk_count": len(desk_ids),
                    "notification_evaluations": len(notified),
                    "automatic_selection": False,
                },
            )
            con.commit()
            return self._public(row, intake, specialist, qa, desk_ids, completed, notified, idempotent=False)
        finally:
            con.close()

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            row = self._row(con, case_id)
            if not row:
                raise ProfessionalAssignmentError("ASSIGNMENT_NOT_FOUND", "El expediente aún no tiene asignación M36.1.", 404)
            intake = self.fulfillment.detail(actor, case_id)
            specialists, qa_users = self._professional_directory(actor)
            specialist = specialists.get(str(row["specialist_id"])) or {"id": row["specialist_id"], "name": "Responsable registrado", "specialty": None}
            qa = qa_users.get(str(row["qa_id"])) or {"id": row["qa_id"], "name": "Responsable QA registrado", "role": "unknown"}
            desk_ids = [str(item) for item in intake.get("desk_case_ids") or []]
            completed = _decode_ids(row.get("completed_desk_ids_json"))
            notified = _decode_ids(row.get("notified_desk_ids_json"))
            return self._public(row, intake, specialist, qa, desk_ids, completed, notified, idempotent=True)
        finally:
            con.close()

    def queue(self, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            rows = [dict(row) for row in con.execute(
                "SELECT * FROM m36_professional_assignment ORDER BY created_at DESC,id DESC"
            ).fetchall()]
            items = []
            for row in rows:
                completed = _decode_ids(row.get("completed_desk_ids_json"))
                notified = _decode_ids(row.get("notified_desk_ids_json"))
                items.append({
                    "assignment_id": row["id"],
                    "case_id": row["case_id"],
                    "state": row["state"],
                    "specialist_id": row["specialist_id"],
                    "qa_id": row["qa_id"],
                    "assigned_desks": len(completed),
                    "notified_desks": len(notified),
                    "last_error_code": row.get("last_error_code"),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return {
                "schema": "legalai_m36_1_assignment_queue_v1",
                "schema_version": SCHEMA_VERSION,
                "items": items,
                "metrics": {
                    "cases": len(items),
                    "complete": sum(item["state"] == "COMPLETE" for item in items),
                    "partial": sum(item["state"] in {"PENDING", "PARTIAL", "ASSIGNED"} for item in items),
                },
                "notice": "La asignación organiza responsables operativos. No constituye revisión, aprobación jurídica, QA, liberación ni entrega.",
            }
        finally:
            con.close()

    @staticmethod
    def _public(
        row: Mapping[str, Any],
        intake: Mapping[str, Any],
        specialist: Mapping[str, Any],
        qa: Mapping[str, Any],
        desk_ids: list[str],
        completed: list[str],
        notified: list[str],
        *,
        idempotent: bool,
    ) -> dict[str, Any]:
        return {
            "schema": "legalai_m36_1_professional_assignment_v1",
            "schema_version": SCHEMA_VERSION,
            "assignment_id": row["id"],
            "fulfillment_intake_id": row["fulfillment_intake_id"],
            "case_id": row["case_id"],
            "product_code": intake.get("product_code"),
            "state": row["state"],
            "specialist": {
                "id": specialist.get("id"),
                "name": specialist.get("name"),
                "specialty": specialist.get("specialty"),
            },
            "qa": {"id": qa.get("id"), "name": qa.get("name"), "role": qa.get("role")},
            "desk_count": len(desk_ids),
            "assigned_desks": len(completed),
            "notification_evaluations": len(notified),
            "all_desks_assigned": len(completed) == len(desk_ids),
            "handoff_evaluated": len(notified) == len(desk_ids),
            "last_error_code": row.get("last_error_code"),
            "idempotent": bool(idempotent),
            "governance": {
                "manual_selection_required": True,
                "automatic_matching": False,
                "specialty_is_advisory": True,
                "automatic_legal_approval": False,
                "automatic_qa_approval": False,
                "automatic_release": False,
                "dual_approval_preserved": True,
                "assignment_completion_is_not_review_completion": True,
                "notification_evaluation_is_not_delivery": True,
            },
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


__all__ = [
    "ProfessionalAssignmentCenter",
    "ProfessionalAssignmentError",
    "SCHEMA_VERSION",
    "ASSIGNMENT_STATES",
]
