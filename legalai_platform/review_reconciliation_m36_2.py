from __future__ import annotations

"""M36.2 — reconciliación verificable entre la Mesa M32 y el journey M24.

M36.2 no crea decisiones jurídicas ni QA. Agrega evidencia de todos los desks
M32 de un expediente y registra en M24 únicamente hitos que ya están acreditados
por decisiones humanas inmutables. Las transiciones derivadas usan el actor
``system-m36-2`` y conservan por separado los aprobadores humanos fuente.
"""

from hashlib import sha256
import json
import re
from typing import Any, Mapping
import uuid

import core_v11 as core
from legalai_platform.approval_desk_operations import ApprovalDeskOperations
from legalai_platform.approval_desk_workspace import ApprovalDeskWorkspace, PermissionDenied


SCHEMA_VERSION = "36.2.0"
SYSTEM_ACTOR_ID = "system-m36-2"
SYSTEM_ACTOR_ROLE = "system"
SYSTEM_ACTOR_NAME = "LegalAIZ.it · M36.2"
FULFILLMENT_REVIEW_STATE = "EN_REVISION_JURIDICA"
OBSERVED_DESK_STATES = frozenset({"changes_required", "rejected", "findings_pending"})
REVIEW_DESK_STATES = frozenset({
    "draft", "legal_pending", "qa_pending", "ready_to_release", "released",
    "changes_required", "rejected", "findings_pending",
})
M24_REVIEW_STATES = frozenset({
    "EN_REVISION_JURIDICA", "OBSERVADO", "CORREGIDO", "APROBADO_JURIDICAMENTE",
    "EN_QA", "APROBADO_QA", "ESCALADO",
})
RECONCILIABLE_TARGETS = frozenset({
    "OBSERVADO", "CORREGIDO", "EN_REVISION_JURIDICA", "APROBADO_JURIDICAMENTE",
    "EN_QA", "APROBADO_QA", "ESCALADO",
})


class ReviewReconciliationError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 100 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ReviewReconciliationError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _decode_list(raw: Any, field: str) -> list[str]:
    try:
        values = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ReviewReconciliationError("LEDGER_INVALID", f"{field} no puede verificarse.", 422) from exc
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ReviewReconciliationError("LEDGER_INVALID", f"{field} no puede verificarse.", 422)
    return list(dict.fromkeys(values))


class ReviewLifecycleReconciler:
    """Agrega evidencia M32 y reconcilia M24 sin impersonar aprobadores."""

    def __init__(
        self,
        workspace: ApprovalDeskWorkspace,
        operations: ApprovalDeskOperations,
        journey,
        *,
        db_factory=None,
    ):
        self.workspace = workspace
        self.operations = operations
        self.journey = journey
        self.db_factory = db_factory or core.db

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m36_review_reconciliation_event(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              from_state TEXT NOT NULL,
              to_state TEXT NOT NULL,
              aggregate_state TEXT NOT NULL,
              evidence_fingerprint TEXT NOT NULL,
              evidence_json TEXT NOT NULL,
              initiated_by TEXT NOT NULL,
              legal_approver_id TEXT,
              qa_approver_id TEXT,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              UNIQUE(case_id,sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_m36_review_reconciliation_case
              ON m36_review_reconciliation_event(case_id,sequence);
            """
        )

    @staticmethod
    def _require_admin(actor: Mapping[str, Any]) -> None:
        if str(actor.get("role") or "") != "admin" or not str(actor.get("id") or "").strip():
            raise PermissionDenied("Solo administración puede reconciliar el ciclo de revisión del expediente.")

    @staticmethod
    def _fulfillment(con, case_id: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM m36_fulfillment_intake WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            raise ReviewReconciliationError("FULFILLMENT_NOT_FOUND", "El expediente no tiene intake M36.0 verificable.", 404)
        value = dict(row)
        if str(value.get("state") or "") != FULFILLMENT_REVIEW_STATE:
            raise ReviewReconciliationError(
                "FULFILLMENT_NOT_READY",
                "El intake M36.0 no acredita el ingreso canónico a revisión jurídica.",
                422,
            )
        return value

    @staticmethod
    def _assignment(con, case_id: str, fulfillment_id: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM m36_professional_assignment WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            raise ReviewReconciliationError("ASSIGNMENT_NOT_FOUND", "El expediente no tiene asignación M36.1.", 404)
        value = dict(row)
        if str(value.get("state") or "") != "COMPLETE":
            raise ReviewReconciliationError("ASSIGNMENT_NOT_COMPLETE", "La asignación M36.1 aún no está completa.", 422)
        if str(value.get("fulfillment_intake_id") or "") != fulfillment_id:
            raise ReviewReconciliationError("ASSIGNMENT_INTAKE_MISMATCH", "La asignación no corresponde al intake vigente.", 422)
        return value

    def _desk_evidence(
        self,
        actor: dict[str, Any],
        case_id: str,
        desk_id: str,
        specialist_id: str,
        qa_id: str,
    ) -> dict[str, Any]:
        detail = self.workspace.detail(actor, desk_id)
        if str(detail.get("source_case_id") or "") != case_id:
            raise ReviewReconciliationError("DESK_SOURCE_MISMATCH", "Una mesa documental apunta a otro expediente.", 422)
        approval_audit = detail.get("audit") or {}
        if not approval_audit.get("valid"):
            raise ReviewReconciliationError("APPROVAL_CHAIN_INVALID", "La cadena de aprobación M32.5 no es íntegra.", 422)
        operations_audit = self.operations.verify_chain(desk_id)
        if not operations_audit.get("valid"):
            raise ReviewReconciliationError("OPERATIONS_CHAIN_INVALID", "La cadena operativa M32.6 no es íntegra.", 422)

        operation_state = self.operations.state(actor, desk_id).get("operations") or {}
        assigned_specialist = str((operation_state.get("assigned_specialist") or {}).get("id") or "")
        assigned_qa = str((operation_state.get("assigned_qa") or {}).get("id") or "")
        if assigned_specialist != specialist_id or assigned_qa != qa_id:
            raise ReviewReconciliationError("ASSIGNMENT_DRIFT", "Los responsables M32.6 no coinciden con M36.1.", 422)

        current_id = str((detail.get("case") or {}).get("current_revision_id") or "")
        current = next(
            (item for item in detail.get("revisions") or [] if str(item.get("revision_id") or "") == current_id),
            None,
        )
        if not current:
            raise ReviewReconciliationError("CURRENT_REVISION_MISSING", "Una mesa no tiene revisión vigente verificable.", 422)
        status = str(detail.get("workflow_status") or "")
        if status not in REVIEW_DESK_STATES:
            raise ReviewReconciliationError("DESK_STATE_UNSUPPORTED", f"Estado M32 no reconciliable: {status or 'vacío'}.", 422)

        approvals = current.get("approvals") or {}
        legal = approvals.get("legal") or {}
        qa = approvals.get("qa") or {}
        legal_decision = str(legal.get("decision") or "")
        qa_decision = str(qa.get("decision") or "")
        legal_actor = str((legal.get("actor") or {}).get("id") or "")
        qa_actor = str((qa.get("actor") or {}).get("id") or "")
        revision_sha = str(current.get("sha256") or "")

        if legal_decision == "approve" and (
            legal_actor != specialist_id
            or str(legal.get("revision_id") or "") != current_id
            or str(legal.get("sha256") or "") != revision_sha
        ):
            raise ReviewReconciliationError(
                "LEGAL_APPROVAL_MISMATCH",
                "Una aprobación jurídica no corresponde al especialista o hash vigentes.",
                422,
            )
        if qa_decision == "approve":
            if (
                qa_actor != qa_id
                or str(qa.get("revision_id") or "") != current_id
                or str(qa.get("sha256") or "") != revision_sha
            ):
                raise ReviewReconciliationError(
                    "QA_APPROVAL_MISMATCH",
                    "Una aprobación QA no corresponde al responsable o hash vigentes.",
                    422,
                )
            if legal_decision != "approve" or legal_actor == qa_actor:
                raise ReviewReconciliationError(
                    "DUAL_APPROVAL_INVALID",
                    "La aprobación QA no conserva la secuencia y separación exigidas.",
                    422,
                )

        release = detail.get("release") or {}
        if release and (
            str(release.get("revision_id") or "") != current_id
            or str(release.get("sha256") or "") != revision_sha
        ):
            raise ReviewReconciliationError("RELEASE_MISMATCH", "La liberación M32 no corresponde a la revisión vigente.", 422)

        return {
            "desk_id": desk_id,
            "document_id": str((detail.get("case") or {}).get("document_id") or ""),
            "workflow_status": status,
            "revision_id": current_id,
            "revision_sha256": revision_sha,
            "revision_number": int(current.get("revision_number") or 0),
            "legal_decision": legal_decision or None,
            "legal_actor_id": legal_actor or None,
            "legal_record_hash": str(legal.get("record_hash") or "") or None,
            "qa_decision": qa_decision or None,
            "qa_actor_id": qa_actor or None,
            "qa_record_hash": str(qa.get("record_hash") or "") or None,
            "release_id": str(release.get("release_id") or "") or None,
            "release_record_hash": str(release.get("release_record_hash") or "") or None,
            "open_findings": sum(item.get("state") == "open" for item in current.get("findings") or []),
            "approval_audit_last_hash": str(approval_audit.get("last_hash") or ""),
            "operations_audit_last_hash": str(operations_audit.get("last_hash") or ""),
        }

    @staticmethod
    def _aggregate(desks: list[dict[str, Any]], specialist_id: str, qa_id: str) -> dict[str, Any]:
        statuses = [str(item["workflow_status"]) for item in desks]
        observed = [item["desk_id"] for item in desks if item["workflow_status"] in OBSERVED_DESK_STATES]
        legal_complete = all(
            item.get("legal_decision") == "approve" and item.get("legal_actor_id") == specialist_id
            for item in desks
        )
        qa_complete = legal_complete and all(
            item.get("qa_decision") == "approve" and item.get("qa_actor_id") == qa_id
            for item in desks
        )
        release_complete = qa_complete and all(bool(item.get("release_id")) for item in desks)
        if observed:
            aggregate_state = "OBSERVED"
        elif qa_complete:
            aggregate_state = "QA_APPROVED"
        elif legal_complete:
            aggregate_state = "LEGAL_APPROVED"
        else:
            aggregate_state = "LEGAL_REVIEW"
        counts: dict[str, int] = {}
        for status in statuses:
            counts[status] = counts.get(status, 0) + 1
        return {
            "aggregate_state": aggregate_state,
            "legal_approval_complete": legal_complete,
            "qa_approval_complete": qa_complete,
            "release_complete": release_complete,
            "observed_desk_ids": observed,
            "status_counts": counts,
        }

    @staticmethod
    def _last_event_to(con, case_id: str, target: str) -> dict[str, Any] | None:
        row = con.execute(
            "SELECT * FROM m36_review_reconciliation_event WHERE case_id=? AND to_state=? ORDER BY sequence DESC LIMIT 1",
            (case_id, target),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _review_material(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """Material jurídico-documental; excluye churn puramente operativo M32.6."""
        desks = []
        for item in snapshot.get("desks") or []:
            desks.append({
                "desk_id": item.get("desk_id"),
                "document_id": item.get("document_id"),
                "workflow_status": item.get("workflow_status"),
                "revision_id": item.get("revision_id"),
                "revision_sha256": item.get("revision_sha256"),
                "revision_number": item.get("revision_number"),
                "legal_decision": item.get("legal_decision"),
                "legal_actor_id": item.get("legal_actor_id"),
                "legal_record_hash": item.get("legal_record_hash"),
                "qa_decision": item.get("qa_decision"),
                "qa_actor_id": item.get("qa_actor_id"),
                "qa_record_hash": item.get("qa_record_hash"),
                "release_id": item.get("release_id"),
                "release_record_hash": item.get("release_record_hash"),
                "open_findings": item.get("open_findings"),
                "approval_audit_last_hash": item.get("approval_audit_last_hash"),
            })
        return {
            "case_id": snapshot.get("case_id"),
            "product_code": snapshot.get("product_code"),
            "fulfillment_intake_id": snapshot.get("fulfillment_intake_id"),
            "assignment_id": snapshot.get("assignment_id"),
            "specialist_id": snapshot.get("specialist_id"),
            "qa_id": snapshot.get("qa_id"),
            "desks": desks,
            "aggregate": snapshot.get("aggregate"),
        }

    @classmethod
    def _changed_since_event(cls, event: dict[str, Any] | None, current_snapshot: Mapping[str, Any]) -> bool:
        if not event:
            return False
        try:
            previous_snapshot = json.loads(event.get("evidence_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(previous_snapshot, dict):
            return False
        return _fingerprint(cls._review_material(previous_snapshot)) != _fingerprint(cls._review_material(current_snapshot))

    def _proposed_path(
        self,
        con,
        case_id: str,
        current: str,
        aggregate: str,
        evidence_snapshot: Mapping[str, Any],
    ) -> tuple[list[str], list[str]]:
        if current not in M24_REVIEW_STATES:
            return [], ["M24_STATE_OUTSIDE_REVIEW_RECONCILIATION"]

        # OBSERVADO es un estado de control: primero se compara contra la
        # fotografía que originó la observación. Churn operativo no acredita
        # corrección y una evidencia distinta que siga observada tampoco.
        if current == "OBSERVADO":
            observation = self._last_event_to(con, case_id, "OBSERVADO")
            if not observation:
                return [], ["OBSERVATION_BASELINE_MISSING"]
            if not self._changed_since_event(observation, evidence_snapshot):
                return [], ["CORRECTION_EVIDENCE_NOT_CHANGED"]
            if aggregate == "OBSERVED":
                return [], ["OBSERVATION_STILL_ACTIVE"]
            return ["CORREGIDO", "EN_REVISION_JURIDICA"], []

        if current == "CORREGIDO":
            return ["EN_REVISION_JURIDICA"], []
        if current == "ESCALADO":
            return [], ["ESCALATION_REQUIRES_EXPLICIT_RESOLUTION"]

        if aggregate == "OBSERVED":
            if current in {"EN_REVISION_JURIDICA", "EN_QA"}:
                return ["OBSERVADO"], []
            if current in {"APROBADO_JURIDICAMENTE", "APROBADO_QA"}:
                return ["ESCALADO"], ["EVIDENCE_REGRESSION_AFTER_APPROVAL"]
            return [], []

        if aggregate == "LEGAL_REVIEW":
            if current in {"APROBADO_JURIDICAMENTE", "EN_QA", "APROBADO_QA"}:
                if "ESCALADO" in self.journey.ALLOWED.get(current, set()):
                    return ["ESCALADO"], ["EVIDENCE_REGRESSION_AFTER_APPROVAL"]
            return [], []

        if aggregate == "LEGAL_APPROVED":
            if current == "EN_REVISION_JURIDICA":
                return ["APROBADO_JURIDICAMENTE", "EN_QA"], []
            if current == "APROBADO_JURIDICAMENTE":
                return ["EN_QA"], []
            if current == "APROBADO_QA" and "ESCALADO" in self.journey.ALLOWED.get(current, set()):
                return ["ESCALADO"], ["EVIDENCE_REGRESSION_AFTER_APPROVAL"]
            return [], []

        if aggregate == "QA_APPROVED":
            if current == "EN_REVISION_JURIDICA":
                return ["APROBADO_JURIDICAMENTE", "EN_QA", "APROBADO_QA"], []
            if current == "APROBADO_JURIDICAMENTE":
                return ["EN_QA", "APROBADO_QA"], []
            if current == "EN_QA":
                return ["APROBADO_QA"], []
            return [], []

        return [], []

    def _collect(self, actor: dict[str, Any], case_id: str, con) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        self.ensure_schema(con)
        fulfillment = self._fulfillment(con, case_id)
        assignment = self._assignment(con, case_id, str(fulfillment["id"]))
        desk_ids = _decode_list(fulfillment.get("desk_case_ids_json"), "desk_case_ids_json")
        completed = _decode_list(assignment.get("completed_desk_ids_json"), "completed_desk_ids_json")
        notified = _decode_list(assignment.get("notified_desk_ids_json"), "notified_desk_ids_json")
        if not desk_ids or set(completed) != set(desk_ids) or set(notified) != set(desk_ids):
            raise ReviewReconciliationError("ASSIGNMENT_COVERAGE_INVALID", "M36.1 no conserva cobertura completa del intake.", 422)

        specialist_id = _safe_id(assignment.get("specialist_id"), "specialist_id")
        qa_id = _safe_id(assignment.get("qa_id"), "qa_id")
        if specialist_id == qa_id:
            raise ReviewReconciliationError("SEPARATION_OF_DUTIES_INVALID", "M36.1 no conserva separación especialista/QA.", 422)

        desks = [self._desk_evidence(actor, case_id, desk_id, specialist_id, qa_id) for desk_id in desk_ids]
        aggregate = self._aggregate(desks, specialist_id, qa_id)
        snapshot = {
            "case_id": case_id,
            "product_code": fulfillment.get("product_code"),
            "fulfillment_intake_id": fulfillment.get("id"),
            "assignment_id": assignment.get("id"),
            "specialist_id": specialist_id,
            "qa_id": qa_id,
            "desks": desks,
            "aggregate": aggregate,
        }
        evidence_fingerprint = _fingerprint(snapshot)
        journey = self.journey.detail(con, case_id, actor)
        current = str(journey.get("current_state") or "")
        path, blockers = self._proposed_path(
            con,
            case_id,
            current,
            str(aggregate["aggregate_state"]),
            snapshot,
        )
        return {
            "case_id": case_id,
            "product_code": fulfillment.get("product_code"),
            "fulfillment_intake_id": fulfillment.get("id"),
            "assignment_id": assignment.get("id"),
            "specialist_id": specialist_id,
            "qa_id": qa_id,
            "desks": desks,
            "aggregate": aggregate,
            "evidence_snapshot": snapshot,
            "evidence_fingerprint": evidence_fingerprint,
            "m24_current_state": current,
            "proposed_path": path,
            "blockers": blockers,
            "journey": journey,
        }

    @staticmethod
    def _public_assessment(collected: Mapping[str, Any]) -> dict[str, Any]:
        aggregate = collected["aggregate"]
        desks = collected["desks"]
        return {
            "schema": "legalai_m36_2_review_assessment_v1",
            "schema_version": SCHEMA_VERSION,
            "case_id": collected["case_id"],
            "product_code": collected.get("product_code"),
            "m24_current_state": collected["m24_current_state"],
            "aggregate_review_state": aggregate["aggregate_state"],
            "desk_count": len(desks),
            "status_counts": aggregate["status_counts"],
            "legal_approval_complete": aggregate["legal_approval_complete"],
            "qa_approval_complete": aggregate["qa_approval_complete"],
            "release_complete": aggregate["release_complete"],
            "proposed_path": list(collected["proposed_path"]),
            "reconciliation_needed": bool(collected["proposed_path"]),
            "blockers": list(collected["blockers"]),
            "delivery_gate_ready": bool(
                aggregate["release_complete"] and collected["m24_current_state"] == "APROBADO_QA"
            ),
            "desks": [
                {
                    "desk_id": item["desk_id"],
                    "document_id": item["document_id"],
                    "workflow_status": item["workflow_status"],
                    "revision_id": item["revision_id"],
                    "legal_approved": item.get("legal_decision") == "approve",
                    "qa_approved": item.get("qa_decision") == "approve",
                    "released": bool(item.get("release_id")),
                    "open_findings": item["open_findings"],
                }
                for item in desks
            ],
            "governance": {
                "derived_state_is_not_new_legal_approval": True,
                "human_m32_approvals_are_source_of_truth": True,
                "system_actor_does_not_impersonate_approvers": True,
                "all_desks_required": True,
                "dual_approval_preserved": True,
                "automatic_delivery": False,
                "delivery_requires_separate_gate": True,
            },
        }

    def assess(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        con = self.db_factory()
        try:
            return self._public_assessment(self._collect(actor, case_id, con))
        finally:
            con.close()

    def _verify_event_chain(self, con, case_id: str) -> dict[str, Any]:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m36_review_reconciliation_event WHERE case_id=? ORDER BY sequence",
            (case_id,),
        ).fetchall()]
        previous = "0" * 64
        for index, row in enumerate(rows, 1):
            if int(row.get("sequence") or 0) != index or str(row.get("previous_hash") or "") != previous:
                return {"valid": False, "events": len(rows), "failed_sequence": index, "last_hash": previous}
            unsigned = dict(row)
            stored = str(unsigned.pop("event_hash", "") or "")
            calculated = _fingerprint(unsigned)
            if stored != calculated:
                return {"valid": False, "events": len(rows), "failed_sequence": index, "last_hash": previous}
            previous = stored
        return {"valid": True, "events": len(rows), "failed_sequence": None, "last_hash": previous}

    def _append_event(
        self,
        con,
        *,
        case_id: str,
        from_state: str,
        to_state: str,
        aggregate_state: str,
        evidence_fingerprint: str,
        evidence_snapshot: Mapping[str, Any],
        initiated_by: str,
        legal_approver_id: str | None,
        qa_approver_id: str | None,
    ) -> dict[str, Any]:
        chain = self._verify_event_chain(con, case_id)
        if not chain["valid"]:
            raise ReviewReconciliationError("RECONCILIATION_CHAIN_INVALID", "La cadena M36.2 está alterada.", 422)
        row = {
            "id": "RCE-" + uuid.uuid4().hex[:14].upper(),
            "case_id": case_id,
            "sequence": int(chain["events"]) + 1,
            "from_state": from_state,
            "to_state": to_state,
            "aggregate_state": aggregate_state,
            "evidence_fingerprint": evidence_fingerprint,
            "evidence_json": _canonical_json(evidence_snapshot),
            "initiated_by": initiated_by,
            "legal_approver_id": legal_approver_id,
            "qa_approver_id": qa_approver_id,
            "previous_hash": chain["last_hash"],
            "created_at": core.now(),
        }
        row["event_hash"] = _fingerprint(row)
        con.execute(
            """INSERT INTO m36_review_reconciliation_event(
                 id,case_id,sequence,from_state,to_state,aggregate_state,evidence_fingerprint,evidence_json,
                 initiated_by,legal_approver_id,qa_approver_id,previous_hash,event_hash,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(row[key] for key in (
                "id", "case_id", "sequence", "from_state", "to_state", "aggregate_state",
                "evidence_fingerprint", "evidence_json", "initiated_by", "legal_approver_id",
                "qa_approver_id", "previous_hash", "event_hash", "created_at",
            )),
        )
        return row

    def _system_transition(
        self,
        con,
        *,
        collected: Mapping[str, Any],
        target: str,
        initiated_by: Mapping[str, Any],
    ) -> dict[str, Any]:
        case_id = str(collected["case_id"])
        journey_row = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        if not journey_row:
            raise ReviewReconciliationError("M24_JOURNEY_MISSING", "El journey M24 no existe.", 422)
        current = str(journey_row["current_state"])
        if target not in self.journey.ALLOWED.get(current, set()):
            raise ReviewReconciliationError("M24_TRANSITION_INVALID", f"M24 no permite {current} → {target}.", 422)
        if target == "ENTREGADO":
            raise ReviewReconciliationError("DELIVERY_OUT_OF_SCOPE", "M36.2 no puede registrar entrega.", 422)
        if target not in RECONCILIABLE_TARGETS:
            raise ReviewReconciliationError("TARGET_OUT_OF_SCOPE", "El hito solicitado está fuera de M36.2.", 422)

        aggregate = collected["aggregate"]
        legal_approver = str(journey_row["legal_approver_id"] or "") or None
        qa_approver = str(journey_row["qa_approver_id"] or "") or None
        if target == "APROBADO_JURIDICAMENTE":
            if not aggregate["legal_approval_complete"]:
                raise ReviewReconciliationError("LEGAL_EVIDENCE_INCOMPLETE", "No existe aprobación jurídica M32 completa.", 422)
            legal_approver = str(collected["specialist_id"])
        if target == "APROBADO_QA":
            if not aggregate["qa_approval_complete"]:
                raise ReviewReconciliationError("QA_EVIDENCE_INCOMPLETE", "No existe aprobación QA M32 completa.", 422)
            legal_approver = legal_approver or str(collected["specialist_id"])
            qa_approver = str(collected["qa_id"])
            if legal_approver == qa_approver:
                raise ReviewReconciliationError("DUAL_APPROVAL_INVALID", "Los aprobadores jurídico y QA no pueden coincidir.", 422)

        now = core.now()
        con.execute(
            """UPDATE m24_case_journey
               SET current_state=?,legal_approver_id=?,qa_approver_id=?,updated_at=? WHERE case_id=?""",
            (target, legal_approver, qa_approver, now, case_id),
        )
        evidence = {
            "source": "m36_2_verified_m32_reconciliation",
            "aggregate_state": aggregate["aggregate_state"],
            "evidence_fingerprint": collected["evidence_fingerprint"],
            "desk_count": len(collected["desks"]),
            "initiated_by": {"id": initiated_by.get("id"), "role": initiated_by.get("role")},
            "human_legal_approver_id": legal_approver,
            "human_qa_approver_id": qa_approver,
            "automatic_delivery": False,
        }
        con.execute(
            """INSERT INTO m24_case_transition(
                 id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()), case_id, current, target,
                SYSTEM_ACTOR_ID, SYSTEM_ACTOR_ROLE, SYSTEM_ACTOR_NAME,
                "Reconciliación técnica de evidencia humana M32 ya registrada, sin crear una nueva decisión profesional.",
                _canonical_json(evidence), now,
            ),
        )
        event = self._append_event(
            con,
            case_id=case_id,
            from_state=current,
            to_state=target,
            aggregate_state=str(aggregate["aggregate_state"]),
            evidence_fingerprint=str(collected["evidence_fingerprint"]),
            evidence_snapshot=collected["evidence_snapshot"],
            initiated_by=str(initiated_by.get("id") or ""),
            legal_approver_id=legal_approver,
            qa_approver_id=qa_approver,
        )
        core.audit(
            con,
            str(initiated_by.get("id") or ""),
            "m36_review_reconciliation",
            event["id"],
            "m24_review_state_reconciled",
            {
                "case_id": case_id,
                "from": current,
                "to": target,
                "aggregate_state": aggregate["aggregate_state"],
                "system_actor": SYSTEM_ACTOR_ID,
                "human_legal_approver_id": legal_approver,
                "human_qa_approver_id": qa_approver,
            },
        )
        return event

    def reconcile(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            collected = self._collect(actor, case_id, con)
            path = list(collected["proposed_path"])
            if not path:
                public = self._public_assessment(collected)
                public.update({"reconciled": False, "applied_transitions": [], "idempotent": True})
                return public

            chain = self._verify_event_chain(con, case_id)
            if not chain["valid"]:
                raise ReviewReconciliationError("RECONCILIATION_CHAIN_INVALID", "La cadena M36.2 está alterada.", 422)
            applied: list[dict[str, Any]] = []
            try:
                for target in path:
                    applied.append(self._system_transition(con, collected=collected, target=target, initiated_by=actor))
                con.commit()
            except Exception:
                con.rollback()
                raise

            refreshed = self._collect(actor, case_id, con)
            public = self._public_assessment(refreshed)
            public.update({
                "reconciled": True,
                "applied_transitions": [
                    {"from": item["from_state"], "to": item["to_state"], "sequence": item["sequence"]}
                    for item in applied
                ],
                "idempotent": False,
            })
            return public
        finally:
            con.close()

    def history(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            chain = self._verify_event_chain(con, case_id)
            if not chain["valid"]:
                raise ReviewReconciliationError("RECONCILIATION_CHAIN_INVALID", "La cadena M36.2 está alterada.", 422)
            rows = [dict(row) for row in con.execute(
                """SELECT id,sequence,from_state,to_state,aggregate_state,initiated_by,
                          legal_approver_id,qa_approver_id,created_at
                   FROM m36_review_reconciliation_event WHERE case_id=? ORDER BY sequence""",
                (case_id,),
            ).fetchall()]
            return {
                "schema": "legalai_m36_2_review_history_v1",
                "schema_version": SCHEMA_VERSION,
                "case_id": case_id,
                "events": rows,
                "audit": {"valid": True, "events": chain["events"]},
                "notice": "Los eventos M36.2 reconcilian estados derivados; las decisiones humanas fuente permanecen en M32.",
            }
        finally:
            con.close()


__all__ = [
    "ReviewLifecycleReconciler",
    "ReviewReconciliationError",
    "SCHEMA_VERSION",
    "SYSTEM_ACTOR_ID",
    "FULFILLMENT_REVIEW_STATE",
]
