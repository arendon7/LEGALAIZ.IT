from __future__ import annotations

"""M37.3 — explicit professional close/escalation gate.

M37.0 reserves CERRADO/ESCALADO for a later controlled phase. M37.3 consumes
M37.0 follow-up state, M37.1 evidence-review state and M37.2 reminders to make
that transition explicit and auditable. Closing means only that the contracted
follow-up scope was concluded; it never verifies legal success, an external
legal effect, evidence authenticity or a statutory deadline.
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
from legalai_platform.m37_3_journey_guard import controlled_m37_disposition_transition


SCHEMA_VERSION = "37.3.0"
TARGET_CLOSE = "CERRADO"
TARGET_ESCALATE = "ESCALADO"
TARGETS = frozenset({TARGET_CLOSE, TARGET_ESCALATE})
INTENT_ACTIONS = frozenset({"PREPARED", "COMPLETED"})
ZERO_HASH = "0" * 64


class ProfessionalDispositionError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ProfessionalDispositionError("DISPOSITION_IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProfessionalDispositionCenter:
    """Immutable disposition intent plus recoverable M24 lifecycle transition."""

    def __init__(
        self,
        followup,
        evidence,
        timing,
        *,
        db_factory=None,
        contract_path: str | Path | None = None,
    ):
        self.followup = followup
        self.evidence = evidence
        self.timing = timing
        self.db_factory = db_factory or core.db
        self.contract_path = Path(contract_path or (core.ROOT / "config" / "m37" / "disposition_contracts.json"))
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.validate_contract()

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m37_disposition_intent(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              target TEXT NOT NULL CHECK(target IN ('CERRADO','ESCALADO')),
              reason_code TEXT NOT NULL,
              internal_reason TEXT NOT NULL,
              client_summary TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              intent_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS m37_disposition_event(
              id TEXT PRIMARY KEY,
              intent_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              action TEXT NOT NULL CHECK(action IN ('PREPARED','COMPLETED')),
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              m24_transition_id TEXT,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(intent_id,sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_m37_disposition_event_intent
              ON m37_disposition_event(intent_id,sequence);
            """
        )

    def _ensure_schemas(self, con) -> None:
        self.followup.ensure_schema(con)
        self.evidence._ensure_schemas(con)
        self.timing.ensure_schema(con)
        self.ensure_schema(con)

    def validate_contract(self) -> dict[str, Any]:
        payload = self.contract
        if payload.get("schema") != "legalai_m37_3_professional_disposition_contracts_v1":
            raise ProfessionalDispositionError("DISPOSITION_CONTRACT_INVALID", "M37.3 usa un contrato desconocido.", 500)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ProfessionalDispositionError("DISPOSITION_VERSION_INVALID", "La versión del contrato M37.3 no coincide.", 500)
        if payload.get("close_confirmation") != "CERRAR SEGUIMIENTO" or payload.get("escalate_confirmation") != "ESCALAR SEGUIMIENTO":
            raise ProfessionalDispositionError("DISPOSITION_CONFIRMATION_POLICY_INVALID", "Las confirmaciones M37.3 no son las esperadas.", 500)
        if set(payload.get("close_roles") or []) != {"specialist"}:
            raise ProfessionalDispositionError("DISPOSITION_CLOSE_ROLE_POLICY_INVALID", "El cierre M37.3 exige especialista.", 500)
        if set(payload.get("escalate_roles") or []) != {"specialist", "admin"}:
            raise ProfessionalDispositionError("DISPOSITION_ESCALATE_ROLE_POLICY_INVALID", "Los roles de escalamiento M37.3 no son válidos.", 500)
        if set(payload.get("close_reason_codes") or []) != {"FOLLOW_UP_SCOPE_COMPLETED"}:
            raise ProfessionalDispositionError("DISPOSITION_CLOSE_REASON_POLICY_INVALID", "La causal de cierre M37.3 no es válida.", 500)
        if not set(payload.get("escalate_reason_codes") or []):
            raise ProfessionalDispositionError("DISPOSITION_ESCALATE_REASON_POLICY_INVALID", "M37.3 requiere causales cerradas de escalamiento.", 500)
        limits = payload.get("limits") or {}
        if int(limits.get("internal_reason_min") or 0) < 30 or int(limits.get("internal_reason_max") or 0) > 4000:
            raise ProfessionalDispositionError("DISPOSITION_REASON_LIMIT_INVALID", "Los límites de razón interna M37.3 son inválidos.", 500)
        if int(limits.get("client_summary_min") or 0) < 30 or int(limits.get("client_summary_max") or 0) > 2000:
            raise ProfessionalDispositionError("DISPOSITION_SUMMARY_LIMIT_INVALID", "Los límites de resumen al cliente M37.3 son inválidos.", 500)
        governance = payload.get("governance") or {}
        required_true = {
            "close_requires_assigned_specialist",
            "m24_transition_uses_client_summary_only",
            "close_requires_m37_0_close_readiness",
            "close_requires_evidence_review_resolution",
            "close_requires_no_active_reminders",
            "immutable_intent",
            "append_only_events",
        }
        required_false = {
            "admin_may_close_without_specialist",
            "client_may_dispose_case",
            "internal_reason_exposed_to_client",
            "escalation_requires_close_readiness",
            "disposition_is_legal_success",
            "disposition_verifies_external_effect",
            "disposition_verifies_evidence_authenticity",
            "disposition_verifies_legal_deadline",
            "automatic_close",
            "automatic_escalation",
            "external_notification",
        }
        if any(governance.get(key) is not True for key in required_true) or any(governance.get(key) is not False for key in required_false):
            raise ProfessionalDispositionError("DISPOSITION_GOVERNANCE_INVALID", "La gobernanza M37.3 no conserva la frontera profesional requerida.", 500)
        if governance.get("escalation_may_be_recorded_by_admin") is not True:
            raise ProfessionalDispositionError("DISPOSITION_ESCALATION_ADMIN_POLICY_INVALID", "Administración debe poder escalar contingencias M37.3.", 500)
        return {"valid": True, "targets": 2, "close_roles": 1, "escalate_roles": 2}

    @staticmethod
    def _intent_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "intent_id": str(row.get("id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "target": str(row.get("target") or ""),
            "reason_code": str(row.get("reason_code") or ""),
            "internal_reason": str(row.get("internal_reason") or ""),
            "client_summary": str(row.get("client_summary") or ""),
            "actor": {"id": str(row.get("actor_id") or ""), "role": str(row.get("actor_role") or "")},
            "created_at": str(row.get("created_at") or ""),
        }

    @staticmethod
    def _event_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(row.get("id") or ""),
            "intent_id": str(row.get("intent_id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "sequence": int(row.get("sequence") or 0),
            "action": str(row.get("action") or ""),
            "actor": {"id": str(row.get("actor_id") or ""), "role": str(row.get("actor_role") or "")},
            "m24_transition_id": str(row.get("m24_transition_id") or "") or None,
            "previous_hash": str(row.get("previous_hash") or ""),
            "created_at": str(row.get("created_at") or ""),
        }

    def _intent(self, con, case_id: str) -> dict[str, Any] | None:
        row = con.execute("SELECT * FROM m37_disposition_intent WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        value = dict(row)
        calculated = _hash(self._intent_candidate(value))
        if calculated != str(value.get("intent_hash") or ""):
            raise ProfessionalDispositionError("DISPOSITION_INTENT_TAMPERED", "La intención M37.3 no superó la verificación de integridad.", 422)
        return value

    def _events(self, con, intent_id: str) -> list[dict[str, Any]]:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_disposition_event WHERE intent_id=? ORDER BY sequence,id",
            (intent_id,),
        ).fetchall()]
        previous = ZERO_HASH
        for expected, row in enumerate(rows, 1):
            candidate = self._event_candidate(row)
            calculated = _hash(candidate)
            if candidate["sequence"] != expected or candidate["previous_hash"] != previous or calculated != str(row.get("event_hash") or ""):
                raise ProfessionalDispositionError("DISPOSITION_EVENT_CHAIN_TAMPERED", "La secuencia M37.3 no superó la verificación de integridad.", 422)
            previous = calculated
        return rows

    def _append_event(
        self,
        con,
        intent: Mapping[str, Any],
        action: str,
        actor: Mapping[str, Any],
        *,
        m24_transition_id: str | None = None,
    ) -> dict[str, Any]:
        if action not in INTENT_ACTIONS:
            raise ProfessionalDispositionError("DISPOSITION_EVENT_INVALID", "Evento M37.3 inválido.", 500)
        rows = self._events(con, str(intent["id"]))
        sequence = len(rows) + 1
        previous = str(rows[-1].get("event_hash") or "") if rows else ZERO_HASH
        row = {
            "id": f"DSP-EVT-{uuid.uuid4().hex[:16].upper()}",
            "intent_id": str(intent["id"]),
            "case_id": str(intent["case_id"]),
            "sequence": sequence,
            "action": action,
            "actor_id": str(actor.get("id") or ""),
            "actor_role": str(actor.get("role") or ""),
            "m24_transition_id": str(m24_transition_id or "") or None,
            "previous_hash": previous,
            "created_at": _now(),
        }
        row["event_hash"] = _hash(self._event_candidate(row))
        con.execute(
            """INSERT INTO m37_disposition_event
               (id,intent_id,case_id,sequence,action,actor_id,actor_role,m24_transition_id,previous_hash,event_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["id"], row["intent_id"], row["case_id"], sequence, action, row["actor_id"], row["actor_role"],
                row["m24_transition_id"], previous, row["event_hash"], row["created_at"],
            ),
        )
        return row

    def _context(self, con, actor: Mapping[str, Any], case_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        self._ensure_schemas(con)
        case = self.followup._require_access(con, case_id, actor)
        self.followup._delivery(con, case_id)
        enrollment = self.followup._enrollment(con, case_id)
        if not enrollment or str(enrollment.get("state") or "") != "ACTIVE":
            raise ProfessionalDispositionError("DISPOSITION_FOLLOWUP_NOT_ACTIVE", "M37.3 requiere un seguimiento M37.0 activo.", 409)
        integrity = self.followup.verify_chain(con, case_id)
        if not integrity.get("valid"):
            raise ProfessionalDispositionError("DISPOSITION_FOLLOWUP_AUDIT_INVALID", "La cadena M37 está alterada.", 422)
        journey = self.followup.journey.detail(con, case_id, dict(actor))
        return case, enrollment, journey

    @staticmethod
    def _assigned_specialist(case: Mapping[str, Any], actor: Mapping[str, Any]) -> bool:
        return (
            str(actor.get("role") or "") == "specialist"
            and bool(str(actor.get("id") or ""))
            and str(actor.get("id") or "") == str(case.get("specialist_id") or "")
        )

    def _require_actor(self, case: Mapping[str, Any], actor: Mapping[str, Any], target: str) -> None:
        role = str(actor.get("role") or "")
        if target == TARGET_CLOSE:
            if not self._assigned_specialist(case, actor):
                raise PermissionDenied("El cierre M37.3 requiere el especialista asignado al expediente.")
            return
        if target == TARGET_ESCALATE:
            if role == "admin" and str(actor.get("id") or ""):
                return
            if self._assigned_specialist(case, actor):
                return
            raise PermissionDenied("El escalamiento M37.3 requiere administración o el especialista asignado.")
        raise ProfessionalDispositionError("DISPOSITION_TARGET_INVALID", "Objetivo M37.3 inválido.", 422)

    def _evidence_snapshot(self, con, case_id: str) -> dict[str, int]:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_evidence_item WHERE case_id=? ORDER BY created_at,id",
            (case_id,),
        ).fetchall()]
        pending = 0
        clarification = 0
        reviewed = 0
        for row in rows:
            public = self.evidence._public_item(con, row)
            review = public.get("review") or {}
            if review.get("status") == "PENDING_REVIEW":
                pending += 1
            else:
                reviewed += 1
            if review.get("disposition") == "NEEDS_CLARIFICATION":
                clarification += 1
        return {
            "items": len(rows),
            "reviewed": reviewed,
            "pending_review": pending,
            "needs_clarification": clarification,
        }

    def _timing_snapshot(self, con, case_id: str) -> dict[str, int]:
        date_rows = self.timing._verify_date_records(con, case_id)
        reminder_rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_timing_reminder WHERE case_id=? ORDER BY scheduled_for,created_at,id",
            (case_id,),
        ).fetchall()]
        reminders = [self.timing._public_reminder(con, row, date_rows) for row in reminder_rows]
        return {
            "date_records": len(date_rows),
            "reminders": len(reminders),
            "active_reminders": sum(1 for item in reminders if item.get("status") in {"SCHEDULED", "DUE"}),
            "acknowledged": sum(1 for item in reminders if item.get("status") == "ACKNOWLEDGED"),
            "cancelled": sum(1 for item in reminders if item.get("status") == "CANCELLED"),
        }

    @staticmethod
    def _public_disposition(intent: Mapping[str, Any], events: list[Mapping[str, Any]]) -> dict[str, Any]:
        completed = next((row for row in reversed(events) if str(row.get("action") or "") == "COMPLETED"), None)
        return {
            "disposition_id": str(intent.get("id") or ""),
            "target": str(intent.get("target") or ""),
            "reason_code": str(intent.get("reason_code") or ""),
            "client_summary": str(intent.get("client_summary") or ""),
            "actor_role": str(intent.get("actor_role") or ""),
            "status": "COMPLETED" if completed else "PREPARED",
            "created_at": str(intent.get("created_at") or ""),
            "completed_at": str(completed.get("created_at") or "") if completed else None,
            "governance": {
                "legal_success_verified": False,
                "external_effect_verified": False,
                "evidence_authenticity_verified": False,
                "legal_deadline_verified": False,
            },
        }

    def _assessment_open(self, con, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case, _enrollment, journey = self._context(con, actor, case_id)
        followup = self.followup._detail_from_open_connection(con, actor, case_id)
        evidence = self._evidence_snapshot(con, case_id)
        timing = self._timing_snapshot(con, case_id)
        current = str(journey.get("current_state") or "")
        blockers: list[str] = []
        if str(followup.get("lifecycle") or "") != "ACTIVE":
            blockers.append("FOLLOW_UP_NOT_ACTIVE")
        if current != "EN_SEGUIMIENTO":
            blockers.append("M24_NOT_IN_FOLLOW_UP")
        if not bool((followup.get("close_readiness") or {}).get("ready")):
            blockers.append("REQUIRED_TASKS_NOT_COMPLETED")
        if evidence["pending_review"]:
            blockers.append("EVIDENCE_PENDING_REVIEW")
        if evidence["needs_clarification"]:
            blockers.append("EVIDENCE_NEEDS_CLARIFICATION")
        if timing["active_reminders"]:
            blockers.append("ACTIVE_REMINDER")
        configured = set(self.contract.get("close_blockers") or [])
        if any(item not in configured for item in blockers):
            raise ProfessionalDispositionError("DISPOSITION_BLOCKER_POLICY_DRIFT", "M37.3 detectó un bloqueo no previsto por contrato.", 500)

        intent = self._intent(con, case_id)
        events = self._events(con, str(intent["id"])) if intent else []
        final = self._public_disposition(intent, events) if intent else None
        has_intent = bool(intent)
        close_actor = self._assigned_specialist(case, actor)
        escalate_actor = close_actor or (str(actor.get("role") or "") == "admin" and bool(str(actor.get("id") or "")))
        return {
            "schema": "legalai_m37_3_professional_disposition_v1",
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "product_code": str(case.get("product_code") or ""),
            "m24_current_state": current,
            "close_gate": {
                "ready": not blockers and not has_intent,
                "blockers": blockers,
                "actor_can_execute": bool(close_actor and current == "EN_SEGUIMIENTO" and not has_intent),
                "requires_confirmation": str(self.contract["close_confirmation"]),
            },
            "escalation_gate": {
                "ready": bool(current == "EN_SEGUIMIENTO" and not has_intent),
                "actor_can_execute": bool(escalate_actor and current == "EN_SEGUIMIENTO" and not has_intent),
                "requires_confirmation": str(self.contract["escalate_confirmation"]),
                "requires_close_readiness": False,
            },
            "evidence_review": evidence,
            "timing": timing,
            "disposition": final,
            "notice": str(self.contract.get("notice") or ""),
            "governance": {
                "internal_reason_exposed": False,
                "close_is_legal_success": False,
                "external_effect_verified": False,
                "evidence_authenticity_verified": False,
                "legal_deadline_verified": False,
                "automatic_close": False,
                "automatic_escalation": False,
                "external_notification": False,
            },
        }

    def assessment(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            return self._assessment_open(con, actor, case_id)
        finally:
            con.close()

    def _normalize_request(
        self,
        target: str,
        reason_code: str,
        internal_reason: str,
        client_summary: str,
        confirmation: str,
    ) -> tuple[str, str, str, str]:
        target = str(target or "").strip().upper()
        reason_code = str(reason_code or "").strip().upper()
        internal_reason = _clean_text(internal_reason)
        client_summary = _clean_text(client_summary)
        if target not in TARGETS:
            raise ProfessionalDispositionError("DISPOSITION_TARGET_INVALID", "Objetivo M37.3 inválido.", 422)
        allowed_codes = set(self.contract["close_reason_codes"] if target == TARGET_CLOSE else self.contract["escalate_reason_codes"])
        if reason_code not in allowed_codes:
            raise ProfessionalDispositionError("DISPOSITION_REASON_CODE_INVALID", "Causal M37.3 inválida para esta decisión.", 422)
        expected = self.contract["close_confirmation"] if target == TARGET_CLOSE else self.contract["escalate_confirmation"]
        if str(confirmation or "").strip() != str(expected):
            raise ProfessionalDispositionError("DISPOSITION_CONFIRMATION_REQUIRED", f"Debe escribir exactamente: {expected}", 422)
        limits = self.contract["limits"]
        if not int(limits["internal_reason_min"]) <= len(internal_reason) <= int(limits["internal_reason_max"]):
            raise ProfessionalDispositionError("DISPOSITION_INTERNAL_REASON_INVALID", "La razón interna no cumple la longitud M37.3.", 422)
        if not int(limits["client_summary_min"]) <= len(client_summary) <= int(limits["client_summary_max"]):
            raise ProfessionalDispositionError("DISPOSITION_CLIENT_SUMMARY_INVALID", "El resumen visible no cumple la longitud M37.3.", 422)
        return target, reason_code, internal_reason, client_summary

    @staticmethod
    def _intent_matches(
        intent: Mapping[str, Any],
        actor: Mapping[str, Any],
        target: str,
        reason_code: str,
        internal_reason: str,
        client_summary: str,
    ) -> bool:
        return all((
            str(intent.get("target") or "") == target,
            str(intent.get("reason_code") or "") == reason_code,
            str(intent.get("internal_reason") or "") == internal_reason,
            str(intent.get("client_summary") or "") == client_summary,
            str(intent.get("actor_id") or "") == str(actor.get("id") or ""),
            str(intent.get("actor_role") or "") == str(actor.get("role") or ""),
        ))

    @staticmethod
    def _find_transition(con, intent: Mapping[str, Any]) -> dict[str, Any] | None:
        rows = [dict(row) for row in con.execute(
            """SELECT id,actor_id,actor_role,evidence_json,created_at FROM m24_case_transition
               WHERE case_id=? AND to_state=? ORDER BY created_at DESC,id DESC""",
            (str(intent["case_id"]), str(intent["target"])),
        ).fetchall()]
        for row in rows:
            try:
                evidence = json.loads(str(row.get("evidence_json") or "{}"))
            except json.JSONDecodeError:
                continue
            if (
                str(evidence.get("source") or "") == "m37_3_professional_disposition"
                and str(evidence.get("disposition_id") or "") == str(intent["id"])
                and str(row.get("actor_id") or "") == str(intent["actor_id"])
                and str(row.get("actor_role") or "") == str(intent["actor_role"])
            ):
                return row
        return None

    def _followup_has_final_event(self, con, case_id: str, disposition_id: str, event_type: str) -> bool:
        rows = con.execute(
            "SELECT event_type,payload_json FROM m37_followup_event WHERE case_id=? ORDER BY sequence DESC",
            (case_id,),
        ).fetchall()
        for row in rows:
            if str(row["event_type"] or "") != event_type:
                continue
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                continue
            if str(payload.get("disposition_id") or "") == disposition_id:
                return True
        return False

    def _finalize(self, con, actor: dict[str, Any], intent: dict[str, Any], *, idempotent: bool) -> dict[str, Any]:
        events = self._events(con, str(intent["id"]))
        completed = next((row for row in events if str(row.get("action") or "") == "COMPLETED"), None)
        journey = self.followup.journey.detail(con, str(intent["case_id"]), actor)
        if str(journey.get("current_state") or "") != str(intent["target"]):
            raise ProfessionalDispositionError("DISPOSITION_M24_STATE_DRIFT", "M24 no coincide con la disposición M37.3 preparada.", 422)
        transition = self._find_transition(con, intent)
        if not transition:
            raise ProfessionalDispositionError("DISPOSITION_M24_TRANSITION_MISSING", "No existe la transición M24 atribuible a la disposición M37.3.", 422)
        if not completed:
            self._append_event(con, intent, "COMPLETED", actor, m24_transition_id=str(transition["id"]))
        final_event = "FOLLOW_UP_CLOSED" if str(intent["target"]) == TARGET_CLOSE else "FOLLOW_UP_ESCALATED"
        if not self._followup_has_final_event(con, str(intent["case_id"]), str(intent["id"]), final_event):
            self.followup._append_event(
                con,
                str(intent["case_id"]),
                final_event,
                actor,
                {
                    "disposition_id": str(intent["id"]),
                    "target": str(intent["target"]),
                    "reason_code": str(intent["reason_code"]),
                    "m24_transition_id": str(transition["id"]),
                    "internal_reason_in_ledger": False,
                    "client_summary_in_ledger": False,
                    "legal_success_verified": False,
                    "external_effect_verified": False,
                    "evidence_authenticity_verified": False,
                    "legal_deadline_verified": False,
                    "automatic": False,
                },
            )
        con.commit()
        result = self._assessment_open(con, actor, str(intent["case_id"]))
        result["idempotent"] = bool(idempotent)
        return result

    def dispose(
        self,
        actor: dict[str, Any],
        case_id: str,
        target: str,
        reason_code: str,
        internal_reason: str,
        client_summary: str,
        confirmation: str,
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        target, reason_code, internal_reason, client_summary = self._normalize_request(
            target, reason_code, internal_reason, client_summary, confirmation
        )
        con = self.db_factory()
        try:
            case, _enrollment, journey = self._context(con, actor, case_id)
            existing = self._intent(con, case_id)
            if existing:
                if not self._intent_matches(existing, actor, target, reason_code, internal_reason, client_summary):
                    raise ProfessionalDispositionError("DISPOSITION_ALREADY_PREPARED", "El expediente ya tiene una disposición M37.3 distinta.", 409)
                self._require_actor(case, actor, target)
                events = self._events(con, str(existing["id"]))
                if any(str(row.get("action") or "") == "COMPLETED" for row in events):
                    return self._finalize(con, actor, existing, idempotent=True)
                current = str(journey.get("current_state") or "")
                if current == target:
                    return self._finalize(con, actor, existing, idempotent=True)
                if current != "EN_SEGUIMIENTO":
                    raise ProfessionalDispositionError("DISPOSITION_RECOVERY_STATE_INVALID", "La disposición preparada no puede recuperarse desde el estado M24 actual.", 422)
                intent = existing
            else:
                if str(journey.get("current_state") or "") != "EN_SEGUIMIENTO":
                    raise ProfessionalDispositionError("DISPOSITION_NOT_WRITABLE", "M37.3 sólo admite una nueva disposición desde EN_SEGUIMIENTO.", 409)
                self._require_actor(case, actor, target)
                assessment = self._assessment_open(con, actor, case_id)
                if target == TARGET_CLOSE and (assessment.get("close_gate") or {}).get("blockers"):
                    raise ProfessionalDispositionError(
                        "DISPOSITION_CLOSE_BLOCKED",
                        "El seguimiento aún tiene condiciones pendientes para cierre.",
                        409,
                    )
                if target == TARGET_ESCALATE and not (assessment.get("escalation_gate") or {}).get("ready"):
                    raise ProfessionalDispositionError("DISPOSITION_ESCALATION_BLOCKED", "El expediente no está disponible para escalamiento M37.3.", 409)
                now = _now()
                intent = {
                    "id": f"DSP-{uuid.uuid4().hex[:16].upper()}",
                    "case_id": case_id,
                    "target": target,
                    "reason_code": reason_code,
                    "internal_reason": internal_reason,
                    "client_summary": client_summary,
                    "actor_id": str(actor.get("id") or ""),
                    "actor_role": str(actor.get("role") or ""),
                    "created_at": now,
                }
                intent["intent_hash"] = _hash(self._intent_candidate(intent))
                con.execute(
                    """INSERT INTO m37_disposition_intent
                       (id,case_id,target,reason_code,internal_reason,client_summary,actor_id,actor_role,intent_hash,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        intent["id"], case_id, target, reason_code, internal_reason, client_summary,
                        intent["actor_id"], intent["actor_role"], intent["intent_hash"], now,
                    ),
                )
                self._append_event(con, intent, "PREPARED", actor)
                self.followup._append_event(
                    con,
                    case_id,
                    "DISPOSITION_PREPARED",
                    actor,
                    {
                        "disposition_id": intent["id"],
                        "target": target,
                        "reason_code": reason_code,
                        "internal_reason_in_ledger": False,
                        "client_summary_in_ledger": False,
                        "automatic": False,
                    },
                )

            controlled_m37_disposition_transition(
                self.followup.journey,
                con,
                case_id,
                target,
                client_summary,
                {
                    "source": "m37_3_professional_disposition",
                    "disposition_id": str(intent["id"]),
                    "reason_code": reason_code,
                    "internal_reason_exposed": False,
                    "legal_success_verified": False,
                    "external_effect_verified": False,
                    "evidence_authenticity_verified": False,
                    "legal_deadline_verified": False,
                },
                actor,
            )
            return self._finalize(con, actor, intent, idempotent=False)
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()


__all__ = [
    "ProfessionalDispositionCenter",
    "ProfessionalDispositionError",
    "SCHEMA_VERSION",
    "TARGET_CLOSE",
    "TARGET_ESCALATE",
]
