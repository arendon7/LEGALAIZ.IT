from __future__ import annotations

"""M37.0 — controlled post-delivery follow-up foundation.

M24 remains the canonical store for operational follow-up tasks. M37.0 adds an
explicit enrollment gate, an append-only hash-linked audit chain and public
semantics that distinguish an operational checkpoint from a verified legal
term. It does not calculate statutory deadlines, verify evidence, close a case
automatically or infer that a reported action produced a legal effect.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping
import uuid

import core_v11 as core
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.m37_0_journey_guard import controlled_follow_up_update


SCHEMA_VERSION = "37.0.0"
START_CONFIRMATION = "INICIAR SEGUIMIENTO"
STATE_PREPARED = "PREPARED"
STATE_ACTIVE = "ACTIVE"
ENROLLMENT_STATES = frozenset({STATE_PREPARED, STATE_ACTIVE})
TASK_STATUSES = frozenset({"pending", "completed", "cancelled"})
TASK_KINDS = frozenset({"PRIMARY_ACTION", "EVIDENCE_PRESERVATION", "STATUS_CHECK", "ONGOING_CONTROL"})
ZERO_HASH = "0" * 64


class PostDeliveryFollowUpError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise PostDeliveryFollowUpError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class PostDeliveryFollowUpCenter:
    """Case-level post-delivery follow-up layered on the existing M24 journey."""

    def __init__(self, journey, *, db_factory=None, contract_path: str | Path | None = None):
        self.journey = journey
        self.db_factory = db_factory or core.db
        self.contract_path = Path(contract_path or (core.ROOT / "config" / "m37" / "follow_up_contracts.json"))
        self.contracts = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.validate_contracts()

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m37_followup_enrollment(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              delivery_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state IN ('PREPARED','ACTIVE')),
              task_ids_json TEXT NOT NULL,
              prepared_by TEXT NOT NULL,
              prepared_at TEXT NOT NULL,
              started_by TEXT,
              started_at TEXT,
              m24_transition_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_followup_state
              ON m37_followup_enrollment(state,updated_at);
            CREATE TABLE IF NOT EXISTS m37_followup_event(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(case_id,sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_m37_followup_event_case
              ON m37_followup_event(case_id,sequence);
            """
        )

    def validate_contracts(self) -> dict[str, Any]:
        payload = self.contracts
        if payload.get("schema") != "legalai_m37_0_follow_up_contracts_v1":
            raise PostDeliveryFollowUpError("CONTRACT_SCHEMA_INVALID", "El registro M37.0 usa un esquema desconocido.", 500)
        timing = payload.get("timing_policy") or {}
        if timing.get("kind") != "OPERATIONAL_CHECKPOINT":
            raise PostDeliveryFollowUpError("TIMING_POLICY_INVALID", "M37.0 debe usar puntos de control operativos.", 500)
        if timing.get("is_legal_deadline") is not False or timing.get("legal_deadline_verified") is not False:
            raise PostDeliveryFollowUpError("LEGAL_DEADLINE_POLICY_INVALID", "M37.0 no puede presentar sus fechas como términos legales verificados.", 500)
        products = payload.get("products") or {}
        expected_codes = set(self.journey.plans)
        if set(products) != expected_codes or len(products) != 11:
            raise PostDeliveryFollowUpError("CONTRACT_COVERAGE_INVALID", "M37.0 debe cubrir exactamente los once planes M24 vigentes.", 500)
        total = 0
        for code in sorted(expected_codes):
            plan = self.journey.plans.get(code) or {}
            expected = []
            if plan.get("delivery_action"):
                expected.append(str(plan["delivery_action"]))
            expected.extend(str(item) for item in (plan.get("required_actions") or []))
            rows = list((products.get(code) or {}).get("tasks") or [])
            labels = [str(item.get("label_exact") or "") for item in rows]
            if labels != expected or len(labels) != len(set(labels)):
                raise PostDeliveryFollowUpError("TASK_CONTRACT_DRIFT", f"El contrato M37.0 de {code} no coincide exactamente con M24.", 500)
            for item in rows:
                if item.get("kind") not in TASK_KINDS or item.get("required_for_close") is not True:
                    raise PostDeliveryFollowUpError("TASK_CONTRACT_INVALID", f"El contrato M37.0 de {code} contiene una tarea inválida.", 500)
            total += len(rows)
        return {"valid": True, "products": len(products), "tasks": total}

    @staticmethod
    def _case(con, case_id: str) -> dict[str, Any]:
        row = con.execute(
            "SELECT id,product_code,owner_id,specialist_id,status FROM cases WHERE id=?",
            (case_id,),
        ).fetchone()
        if not row:
            raise PostDeliveryFollowUpError("FOLLOWUP_NOT_AVAILABLE", "El seguimiento no está disponible.", 404)
        return dict(row)

    def _require_access(self, con, case_id: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        case = self._case(con, case_id)
        if not self.journey.can_access(case, dict(actor)):
            raise PostDeliveryFollowUpError("FOLLOWUP_NOT_AVAILABLE", "El seguimiento no está disponible.", 404)
        role = str(actor.get("role") or "")
        if role not in {"client", "specialist", "admin"} or not str(actor.get("id") or "").strip():
            raise PermissionDenied("El rol actual no puede operar el seguimiento del expediente.")
        return case

    @staticmethod
    def _delivery(con, case_id: str) -> dict[str, Any]:
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='m36_controlled_delivery'"
        ).fetchone()
        if not table:
            raise PostDeliveryFollowUpError("FOLLOWUP_NOT_AVAILABLE", "El seguimiento no está disponible.", 404)
        row = con.execute(
            "SELECT id,case_id,owner_id,product_code,state,delivered_at FROM m36_controlled_delivery WHERE case_id=?",
            (case_id,),
        ).fetchone()
        if not row or str(row["state"] or "") != "DELIVERED_IN_APP":
            raise PostDeliveryFollowUpError("FOLLOWUP_NOT_AVAILABLE", "El seguimiento sólo se habilita después de una entrega M36.3 válida.", 404)
        return dict(row)

    @staticmethod
    def _enrollment(con, case_id: str) -> dict[str, Any] | None:
        row = con.execute("SELECT * FROM m37_followup_enrollment WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _task_ids(enrollment: Mapping[str, Any]) -> list[str]:
        try:
            values = json.loads(str(enrollment.get("task_ids_json") or "[]"))
        except json.JSONDecodeError as exc:
            raise PostDeliveryFollowUpError("FOLLOWUP_SNAPSHOT_INVALID", "El snapshot M37.0 no es legible.", 422) from exc
        if not isinstance(values, list) or not values or any(not isinstance(item, str) or not item for item in values):
            raise PostDeliveryFollowUpError("FOLLOWUP_SNAPSHOT_INVALID", "El snapshot M37.0 de actividades es inválido.", 422)
        return values

    def _task_contracts(self, product_code: str) -> dict[str, dict[str, Any]]:
        rows = ((self.contracts.get("products") or {}).get(product_code) or {}).get("tasks") or []
        return {str(item["label_exact"]): dict(item) for item in rows}

    def _validate_live_tasks(self, product_code: str, followups: list[dict[str, Any]]) -> list[str]:
        contracts = self._task_contracts(product_code)
        by_label: dict[str, dict[str, Any]] = {}
        for item in followups:
            label = str(item.get("action_label") or "")
            if not label or label in by_label:
                raise PostDeliveryFollowUpError(
                    "FOLLOWUP_TASK_DRIFT",
                    "Las actividades M24 contienen etiquetas vacías o duplicadas.",
                    422,
                )
            by_label[label] = item
        if set(by_label) != set(contracts):
            raise PostDeliveryFollowUpError("FOLLOWUP_TASK_DRIFT", "Las actividades M24 no coinciden con el contrato M37.0 vigente.", 422)
        ordered_ids = [str(by_label[label].get("id") or "") for label in contracts]
        if any(not item for item in ordered_ids) or len(ordered_ids) != len(set(ordered_ids)):
            raise PostDeliveryFollowUpError("FOLLOWUP_TASK_IDS_INVALID", "Las actividades M24 no tienen identificadores íntegros.", 422)
        return ordered_ids

    @staticmethod
    def _event_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(str(row.get("payload_json") or "{}"))
        except json.JSONDecodeError:
            payload = None
        return {
            "schema_version": SCHEMA_VERSION,
            "sequence": int(row.get("sequence") or 0),
            "event_id": str(row.get("id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "event_type": str(row.get("event_type") or ""),
            "actor": {"id": str(row.get("actor_id") or ""), "role": str(row.get("actor_role") or "")},
            "payload": payload,
            "created_at": str(row.get("created_at") or ""),
            "previous_hash": str(row.get("previous_hash") or ""),
        }

    def verify_chain(self, con, case_id: str) -> dict[str, Any]:
        self.ensure_schema(con)
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_followup_event WHERE case_id=? ORDER BY sequence,id",
            (case_id,),
        ).fetchall()]
        previous = ZERO_HASH
        for expected, row in enumerate(rows, 1):
            candidate = self._event_candidate(row)
            calculated = _sha(_canonical_json(candidate))
            if candidate["sequence"] != expected or candidate["previous_hash"] != previous or str(row.get("event_hash") or "") != calculated:
                return {"valid": False, "events": len(rows), "failed_sequence": expected, "last_hash": previous}
            previous = calculated
        return {"valid": True, "events": len(rows), "failed_sequence": None, "last_hash": previous}

    def _append_event(self, con, case_id: str, event_type: str, actor: Mapping[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        integrity = self.verify_chain(con, case_id)
        if not integrity["valid"]:
            raise PostDeliveryFollowUpError("FOLLOWUP_AUDIT_INVALID", "La cadena M37.0 está alterada; no se admiten nuevas actuaciones.", 422)
        sequence = int(integrity["events"]) + 1
        created_at = _now()
        event_id = f"FUP-EVT-{uuid.uuid4().hex[:16].upper()}"
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "sequence": sequence,
            "event_id": event_id,
            "case_id": case_id,
            "event_type": str(event_type),
            "actor": {"id": str(actor.get("id") or ""), "role": str(actor.get("role") or "")},
            "payload": payload,
            "created_at": created_at,
            "previous_hash": integrity["last_hash"],
        }
        event_hash = _sha(_canonical_json(candidate))
        con.execute(
            """INSERT INTO m37_followup_event
               (id,case_id,sequence,event_type,actor_id,actor_role,payload_json,previous_hash,event_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                case_id,
                sequence,
                str(event_type),
                str(actor.get("id") or ""),
                str(actor.get("role") or ""),
                _canonical_json(payload),
                integrity["last_hash"],
                event_hash,
                created_at,
            ),
        )
        return candidate | {"event_hash": event_hash}

    @staticmethod
    def _transition_to_followup(con, case_id: str) -> dict[str, Any] | None:
        row = con.execute(
            """SELECT id,actor_id,actor_role,created_at FROM m24_case_transition
               WHERE case_id=? AND to_state='EN_SEGUIMIENTO'
               ORDER BY created_at DESC,id DESC LIMIT 1""",
            (case_id,),
        ).fetchone()
        return dict(row) if row else None

    def _finalize_start(self, con, enrollment: dict[str, Any], actor: Mapping[str, Any]) -> None:
        transition = self._transition_to_followup(con, str(enrollment["case_id"]))
        if not transition:
            raise PostDeliveryFollowUpError("M24_FOLLOWUP_TRANSITION_MISSING", "M24 no conserva la transición que inició el seguimiento.", 422)
        started_at = str(transition.get("created_at") or "")
        started_by = str(transition.get("actor_id") or "")
        if not started_at or not started_by:
            raise PostDeliveryFollowUpError("M24_FOLLOWUP_TRANSITION_INVALID", "La transición M24 de seguimiento está incompleta.", 422)
        con.execute(
            """UPDATE m37_followup_enrollment
               SET state='ACTIVE',started_by=?,started_at=?,m24_transition_id=?,updated_at=?
               WHERE case_id=? AND state='PREPARED'""",
            (started_by, started_at, str(transition.get("id") or ""), _now(), str(enrollment["case_id"])),
        )
        self._append_event(
            con,
            str(enrollment["case_id"]),
            "FOLLOW_UP_STARTED",
            {"id": started_by, "role": str(transition.get("actor_role") or actor.get("role") or "")},
            {
                "delivery_id": str(enrollment["delivery_id"]),
                "task_count": len(self._task_ids(enrollment)),
                "source": "m24_case_follow_up",
                "timing_kind": "OPERATIONAL_CHECKPOINT",
                "is_legal_deadline": False,
                "legal_deadline_verified": False,
            },
        )

    def start(self, actor: dict[str, Any], case_id: str, confirmation: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        if str(confirmation or "").strip() != START_CONFIRMATION:
            raise PostDeliveryFollowUpError(
                "FOLLOWUP_CONFIRMATION_REQUIRED",
                f"Para iniciar el seguimiento debe escribir exactamente: {START_CONFIRMATION}",
                422,
            )
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            case = self._require_access(con, case_id, actor)
            delivery = self._delivery(con, case_id)
            if str(delivery.get("product_code") or "") != str(case.get("product_code") or ""):
                raise PostDeliveryFollowUpError("FOLLOWUP_PRODUCT_MISMATCH", "La entrega y el expediente corresponden a productos distintos.", 422)
            journey = self.journey.detail(con, case_id, actor)
            enrollment = self._enrollment(con, case_id)
            if enrollment and str(enrollment.get("state") or "") == STATE_ACTIVE:
                integrity = self.verify_chain(con, case_id)
                if not integrity["valid"]:
                    raise PostDeliveryFollowUpError("FOLLOWUP_AUDIT_INVALID", "La cadena M37.0 está alterada.", 422)
                result = self._detail_from_open_connection(con, actor, case_id)
                result["idempotent"] = True
                return result

            if not enrollment:
                if journey.get("current_state") != "ENTREGADO":
                    raise PostDeliveryFollowUpError(
                        "FOLLOWUP_STATE_NOT_ENROLLABLE",
                        "M37.0 sólo puede iniciar un seguimiento nuevo desde un expediente ENTREGADO por M36.3.",
                        409,
                    )
                followups = list(journey.get("follow_ups") or [])
                task_ids = self._validate_live_tasks(str(case["product_code"]), followups)
                now = _now()
                enrollment = {
                    "id": f"FUP-{uuid.uuid4().hex[:16].upper()}",
                    "case_id": case_id,
                    "delivery_id": str(delivery["id"]),
                    "product_code": str(case["product_code"]),
                    "state": STATE_PREPARED,
                    "task_ids_json": _canonical_json(task_ids),
                    "prepared_by": str(actor.get("id") or ""),
                    "prepared_at": now,
                }
                con.execute(
                    """INSERT INTO m37_followup_enrollment
                       (id,case_id,delivery_id,product_code,state,task_ids_json,prepared_by,prepared_at,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        enrollment["id"], case_id, enrollment["delivery_id"], enrollment["product_code"],
                        STATE_PREPARED, enrollment["task_ids_json"], enrollment["prepared_by"], now, now, now,
                    ),
                )
                con.commit()
            else:
                if str(enrollment.get("delivery_id") or "") != str(delivery.get("id") or ""):
                    raise PostDeliveryFollowUpError("FOLLOWUP_DELIVERY_DRIFT", "El seguimiento preparado apunta a otra entrega.", 422)
                task_ids = self._validate_live_tasks(str(case["product_code"]), list(journey.get("follow_ups") or []))
                if task_ids != self._task_ids(enrollment):
                    raise PostDeliveryFollowUpError("FOLLOWUP_SNAPSHOT_DRIFT", "Las actividades cambiaron después de preparar M37.0.", 422)

            current = self.journey.detail(con, case_id, actor).get("current_state")
            if current == "ENTREGADO":
                try:
                    self.journey.transition(
                        con,
                        case_id,
                        "EN_SEGUIMIENTO",
                        "Inicio explícito y trazable del seguimiento post-entrega controlado por M37.0.",
                        {"source": "m37_0_post_delivery_followup", "delivery_id": str(delivery["id"])},
                        "",
                        actor,
                    )
                except Exception:
                    refreshed = self.journey.detail(con, case_id, actor).get("current_state")
                    if refreshed == "ENTREGADO":
                        con.execute("DELETE FROM m37_followup_enrollment WHERE case_id=? AND state='PREPARED'", (case_id,))
                        con.commit()
                    raise
                current = self.journey.detail(con, case_id, actor).get("current_state")
            if current != "EN_SEGUIMIENTO":
                raise PostDeliveryFollowUpError("FOLLOWUP_STATE_DRIFT", "M24 no quedó en EN_SEGUIMIENTO; M37.0 falla cerrado.", 422)
            enrollment = self._enrollment(con, case_id)
            if not enrollment or str(enrollment.get("state") or "") != STATE_PREPARED:
                raise PostDeliveryFollowUpError("FOLLOWUP_PREPARED_MISSING", "No existe preparación M37.0 recuperable.", 422)
            self._finalize_start(con, enrollment, actor)
            con.commit()
            result = self._detail_from_open_connection(con, actor, case_id)
            result["idempotent"] = False
            return result
        finally:
            con.close()

    def _latest_task_event(self, con, case_id: str, follow_up_id: str) -> dict[str, Any] | None:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_followup_event WHERE case_id=? ORDER BY sequence DESC",
            (case_id,),
        ).fetchall()]
        for row in rows:
            try:
                payload = json.loads(str(row.get("payload_json") or "{}"))
            except json.JSONDecodeError:
                continue
            if str(payload.get("follow_up_id") or "") == follow_up_id:
                return {"event_type": str(row.get("event_type") or ""), "actor_role": str(row.get("actor_role") or ""), "payload": payload}
        return None

    @staticmethod
    def _completion_class(status: str, actor_role: str | None) -> str:
        if status != "completed":
            return "NOT_RECORDED"
        if actor_role == "client":
            return "SELF_REPORTED"
        if actor_role in {"specialist", "admin"}:
            return "PROFESSIONAL_RECORDED"
        return "LEGACY_RECORDED"

    def record_task(self, actor: dict[str, Any], case_id: str, follow_up_id: str, status: str, note: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        follow_up_id = _safe_id(follow_up_id, "follow_up_id")
        status = str(status or "").strip().lower()
        note = str(note or "").strip()
        if status not in TASK_STATUSES:
            raise PostDeliveryFollowUpError("FOLLOWUP_STATUS_INVALID", "Estado de actividad inválido.", 422)
        if len(note) < 10 or len(note) > 2000:
            raise PostDeliveryFollowUpError("FOLLOWUP_NOTE_INVALID", "La nota debe tener entre 10 y 2.000 caracteres.", 422)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            self._require_access(con, case_id, actor)
            self._delivery(con, case_id)
            enrollment = self._enrollment(con, case_id)
            if not enrollment or str(enrollment.get("state") or "") != STATE_ACTIVE:
                raise PostDeliveryFollowUpError("FOLLOWUP_NOT_STARTED", "Debe iniciar M37.0 antes de actualizar actividades.", 409)
            integrity = self.verify_chain(con, case_id)
            if not integrity["valid"]:
                raise PostDeliveryFollowUpError("FOLLOWUP_AUDIT_INVALID", "La cadena M37.0 está alterada.", 422)
            journey = self.journey.detail(con, case_id, actor)
            if journey.get("current_state") != "EN_SEGUIMIENTO":
                raise PostDeliveryFollowUpError("FOLLOWUP_READ_ONLY", "El expediente ya no admite cambios de seguimiento en M37.0.", 409)
            if follow_up_id not in self._task_ids(enrollment):
                raise PostDeliveryFollowUpError("FOLLOWUP_TASK_NOT_AVAILABLE", "La actividad no pertenece al snapshot M37.0.", 404)
            row = con.execute(
                "SELECT id,action_label,status,note FROM m24_case_follow_up WHERE id=? AND case_id=?",
                (follow_up_id, case_id),
            ).fetchone()
            if not row:
                raise PostDeliveryFollowUpError("FOLLOWUP_TASK_NOT_AVAILABLE", "La actividad no está disponible.", 404)
            row = dict(row)
            if str(row.get("action_label") or "") not in self._task_contracts(str(enrollment["product_code"])):
                raise PostDeliveryFollowUpError("FOLLOWUP_TASK_DRIFT", "La actividad dejó de coincidir con el contrato M37.0.", 422)
            old_status = str(row.get("status") or "")
            old_note = str(row.get("note") or "").strip()
            latest = self._latest_task_event(con, case_id, follow_up_id)
            if old_status == status and old_note == note and latest and str((latest.get("payload") or {}).get("new_status") or "") == status:
                result = self._detail_from_open_connection(con, actor, case_id)
                result["idempotent"] = True
                return result

            event_type = "TASK_STATUS_RECORDED"
            if old_status == status and old_note == note and not latest:
                event_type = "TASK_STATUS_RECONCILED"
            else:
                controlled_follow_up_update(self.journey, con, case_id, follow_up_id, status, note, actor)

            completion_class = self._completion_class(status, str(actor.get("role") or ""))
            self._append_event(
                con,
                case_id,
                event_type,
                actor,
                {
                    "follow_up_id": follow_up_id,
                    "old_status": old_status,
                    "new_status": status,
                    "note_present": True,
                    "completion_class": completion_class,
                    "legal_effect_verified": False,
                    "evidence_verified": False,
                },
            )
            con.commit()
            result = self._detail_from_open_connection(con, actor, case_id)
            result["idempotent"] = event_type == "TASK_STATUS_RECONCILED"
            return result
        finally:
            con.close()

    def _public_task(self, con, case_id: str, product_code: str, row: Mapping[str, Any]) -> dict[str, Any]:
        label = str(row.get("action_label") or "")
        contract = self._task_contracts(product_code).get(label)
        if not contract:
            raise PostDeliveryFollowUpError("FOLLOWUP_TASK_DRIFT", "Una actividad no tiene contrato M37.0 explícito.", 422)
        latest = self._latest_task_event(con, case_id, str(row.get("id") or ""))
        actor_role = str(latest.get("actor_role") or "") if latest else None
        status = str(row.get("status") or "")
        effective = str(row.get("effective_status") or status)
        due_at = row.get("due_at")
        return {
            "follow_up_id": str(row.get("id") or ""),
            "label": label,
            "kind": contract["kind"],
            "required_for_close": bool(contract["required_for_close"]),
            "status": status,
            "effective_status": effective,
            "due_at": due_at,
            "timing": {
                "kind": "OPERATIONAL_CHECKPOINT" if due_at else "UNSCHEDULED_OPERATIONAL_ACTION",
                "is_legal_deadline": False,
                "legal_deadline_verified": False,
            },
            "completion": {
                "class": self._completion_class(status, actor_role),
                "evidence_verified": False,
                "legal_effect_verified": False,
            },
            "note_present": bool(str(row.get("note") or "").strip()),
        }

    def _detail_from_open_connection(self, con, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self.ensure_schema(con)
        case = self._require_access(con, case_id, actor)
        delivery = self._delivery(con, case_id)
        journey = self.journey.detail(con, case_id, actor)
        product_code = str(case.get("product_code") or "")
        if product_code != str(delivery.get("product_code") or ""):
            raise PostDeliveryFollowUpError("FOLLOWUP_PRODUCT_MISMATCH", "La entrega no coincide con el producto del expediente.", 422)
        followups = list(journey.get("follow_ups") or [])
        live_ids = self._validate_live_tasks(product_code, followups)
        enrollment = self._enrollment(con, case_id)
        audit = {"valid": True, "events": 0, "failed_sequence": None}
        if enrollment:
            if live_ids != self._task_ids(enrollment):
                raise PostDeliveryFollowUpError("FOLLOWUP_SNAPSHOT_DRIFT", "El conjunto de actividades cambió después del enrolamiento M37.0.", 422)
            audit = self.verify_chain(con, case_id)
            if not audit["valid"]:
                raise PostDeliveryFollowUpError("FOLLOWUP_AUDIT_INVALID", "La cadena M37.0 está alterada.", 422)
        tasks = [self._public_task(con, case_id, product_code, row) for row in followups]
        required = [item for item in tasks if item["required_for_close"]]
        pending = sum(1 for item in tasks if item["effective_status"] in {"pending", "overdue"})
        completed = sum(1 for item in tasks if item["status"] == "completed")
        cancelled = sum(1 for item in tasks if item["status"] == "cancelled")
        overdue = sum(1 for item in tasks if item["effective_status"] == "overdue")
        current = str(journey.get("current_state") or "")
        active = bool(enrollment and str(enrollment.get("state") or "") == STATE_ACTIVE)
        ready_to_close = bool(active and current == "EN_SEGUIMIENTO" and required and all(item["status"] == "completed" for item in required))
        plan = self.journey.plans.get(product_code) or {}
        timing = self.contracts.get("timing_policy") or {}
        if not enrollment:
            lifecycle = "AVAILABLE" if current == "ENTREGADO" else "NOT_ENROLLED"
        elif current == "EN_SEGUIMIENTO":
            lifecycle = "ACTIVE"
        elif current == "ESCALADO":
            lifecycle = "ESCALATED"
        elif current == "CERRADO":
            lifecycle = "CLOSED"
        else:
            lifecycle = "READ_ONLY"
        return {
            "schema": "legalai_m37_0_post_delivery_followup_v1",
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "product_code": product_code,
            "delivery_id": str(delivery.get("id") or ""),
            "lifecycle": lifecycle,
            "m24_current_state": current,
            "started": active,
            "tasks": tasks,
            "metrics": {
                "tasks": len(tasks),
                "pending": pending,
                "completed": completed,
                "cancelled": cancelled,
                "overdue": overdue,
            },
            "close_readiness": {
                "ready": ready_to_close,
                "automatic_close": False,
                "requires_explicit_later_control": True,
            },
            "advisory": {
                "response_window_label": str(plan.get("response_window_label") or ""),
                "escalation_path": list(plan.get("escalation_path") or []),
                "plan_notice": str(self.journey.plan_notice or ""),
                "timing_notice": str(timing.get("notice") or ""),
            },
            "audit": {
                "valid": bool(audit.get("valid")),
                "events": int(audit.get("events") or 0),
            },
            "governance": {
                "source_tasks": "M24_CASE_FOLLOW_UP",
                "requires_m36_3_delivered_in_app": True,
                "operational_checkpoint_is_not_legal_deadline": True,
                "legal_deadline_calculation": False,
                "automatic_task_completion": False,
                "automatic_case_close": False,
                "automatic_escalation": False,
                "evidence_verification": False,
                "legal_effect_verification": False,
            },
        }

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            return self._detail_from_open_connection(con, actor, case_id)
        finally:
            con.close()

    def queue(self, actor: dict[str, Any]) -> dict[str, Any]:
        if str(actor.get("role") or "") != "admin" or not str(actor.get("id") or ""):
            raise PermissionDenied("Solo administración puede consultar la cola global M37.0.")
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            table = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='m36_controlled_delivery'"
            ).fetchone()
            if not table:
                rows = []
            else:
                rows = con.execute(
                    "SELECT case_id FROM m36_controlled_delivery WHERE state='DELIVERED_IN_APP' ORDER BY delivered_at DESC,case_id"
                ).fetchall()
            items = []
            for row in rows:
                try:
                    detail = self._detail_from_open_connection(con, actor, str(row["case_id"]))
                except PostDeliveryFollowUpError:
                    continue
                items.append({
                    "case_id": detail["case_id"],
                    "product_code": detail["product_code"],
                    "lifecycle": detail["lifecycle"],
                    "m24_current_state": detail["m24_current_state"],
                    "pending": detail["metrics"]["pending"],
                    "overdue": detail["metrics"]["overdue"],
                    "close_ready": detail["close_readiness"]["ready"],
                })
            return {
                "schema": "legalai_m37_0_followup_queue_v1",
                "items": items,
                "metrics": {
                    "cases": len(items),
                    "available": sum(1 for item in items if item["lifecycle"] == "AVAILABLE"),
                    "active": sum(1 for item in items if item["lifecycle"] == "ACTIVE"),
                    "overdue_tasks": sum(int(item["overdue"]) for item in items),
                    "close_ready": sum(1 for item in items if item["close_ready"]),
                },
                "governance": {
                    "operational_only": True,
                    "legal_deadlines_verified": False,
                    "automatic_close": False,
                },
            }
        finally:
            con.close()


__all__ = [
    "PostDeliveryFollowUpCenter",
    "PostDeliveryFollowUpError",
    "SCHEMA_VERSION",
    "START_CONFIRMATION",
]
