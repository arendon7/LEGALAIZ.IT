from __future__ import annotations

"""M37.2 — recorded dates and in-app reminder boundary.

M37.2 records event dates and personal/case follow-up reminders without
calculating or claiming statutory/legal deadlines. M24 due_at remains an
operational checkpoint. Date corrections are append-only supersessions and
reminder state changes are append-only events. Time passage may derive DUE in
the read model, but never mutates M24 tasks or case lifecycle.
"""

from datetime import date, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping
import uuid
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpCenter


SCHEMA_VERSION = "37.2.0"
DATE_EVENT_TYPES = frozenset({
    "ACTION_PERFORMED",
    "AUTHORITY_RECEIPT_REPORTED",
    "NOTICE_RECEIVED",
    "RESPONSE_RECEIVED",
    "OTHER_RELEVANT_EVENT",
})
PROVENANCE = frozenset({"USER_ASSERTED", "PROFESSIONAL_RECORDED"})
REMINDER_ACTIONS = frozenset({"ACKNOWLEDGED", "CANCELLED"})
ZERO_HASH = "0" * 64


class TimingReminderError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(dict(value)).encode("utf-8")).hexdigest()


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise TimingReminderError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


class TimingReminderCenter:
    """Append-only event-date records and in-app operational reminders."""

    def __init__(
        self,
        followup: PostDeliveryFollowUpCenter,
        evidence_center,
        *,
        db_factory=None,
        contract_path: str | Path | None = None,
        now_provider=None,
    ):
        self.followup = followup
        self.evidence = evidence_center
        self.db_factory = db_factory or core.db
        self.contract_path = Path(contract_path or (core.ROOT / "config" / "m37" / "timing_reminder_contracts.json"))
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        timezone_name = str(self.contract.get("timezone") or "America/Bogota")
        try:
            self.timezone = ZoneInfo(timezone_name)
        except Exception as exc:
            raise TimingReminderError("TIMING_TIMEZONE_INVALID", "La zona horaria M37.2 es inválida.", 500) from exc
        self.now_provider = now_provider or (lambda: datetime.now(self.timezone))
        self.validate_contract()

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m37_timing_date_record(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              follow_up_id TEXT NOT NULL,
              event_type TEXT NOT NULL CHECK(event_type IN (
                'ACTION_PERFORMED','AUTHORITY_RECEIPT_REPORTED','NOTICE_RECEIVED','RESPONSE_RECEIVED','OTHER_RELEVANT_EVENT'
              )),
              date_value TEXT NOT NULL,
              provenance TEXT NOT NULL CHECK(provenance IN ('USER_ASSERTED','PROFESSIONAL_RECORDED')),
              evidence_id TEXT,
              supersedes_id TEXT,
              recorder_id TEXT NOT NULL,
              recorder_role TEXT NOT NULL,
              record_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_timing_date_case
              ON m37_timing_date_record(case_id,follow_up_id,created_at,id);
            CREATE INDEX IF NOT EXISTS idx_m37_timing_date_supersedes
              ON m37_timing_date_record(supersedes_id);

            CREATE TABLE IF NOT EXISTS m37_timing_reminder(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              follow_up_id TEXT NOT NULL,
              scheduled_for TEXT NOT NULL,
              source_date_record_id TEXT,
              creator_id TEXT NOT NULL,
              creator_role TEXT NOT NULL,
              reminder_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_timing_reminder_case
              ON m37_timing_reminder(case_id,follow_up_id,scheduled_for);

            CREATE TABLE IF NOT EXISTS m37_timing_reminder_event(
              id TEXT PRIMARY KEY,
              reminder_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              action TEXT NOT NULL CHECK(action IN ('SCHEDULED','ACKNOWLEDGED','CANCELLED')),
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(reminder_id,sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_m37_timing_reminder_event
              ON m37_timing_reminder_event(reminder_id,sequence);
            """
        )

    def validate_contract(self) -> dict[str, Any]:
        payload = self.contract
        if payload.get("schema") != "legalai_m37_2_timing_reminder_contracts_v1":
            raise TimingReminderError("TIMING_CONTRACT_INVALID", "M37.2 usa un contrato temporal desconocido.", 500)
        if str(payload.get("timezone") or "") != "America/Bogota":
            raise TimingReminderError("TIMING_TIMEZONE_POLICY_DRIFT", "M37.2 debe usar la zona operativa America/Bogota.", 500)
        if set(payload.get("date_event_types") or []) != set(DATE_EVENT_TYPES):
            raise TimingReminderError("TIMING_EVENT_TYPES_DRIFT", "Los tipos de fecha M37.2 no coinciden con el contrato.", 500)
        if set(payload.get("provenance") or []) != set(PROVENANCE):
            raise TimingReminderError("TIMING_PROVENANCE_DRIFT", "La procedencia de fechas M37.2 no coincide con el contrato.", 500)
        if set(payload.get("reminder_actions") or []) != set(REMINDER_ACTIONS):
            raise TimingReminderError("TIMING_REMINDER_ACTIONS_DRIFT", "Las acciones de recordatorio M37.2 no coinciden con el contrato.", 500)
        if int(payload.get("max_date_records_per_task") or 0) < 1:
            raise TimingReminderError("TIMING_DATE_QUOTA_INVALID", "La cuota de fechas M37.2 es inválida.", 500)
        if int(payload.get("max_reminders_per_task") or 0) < 1:
            raise TimingReminderError("TIMING_REMINDER_QUOTA_INVALID", "La cuota de recordatorios M37.2 es inválida.", 500)
        if not 1 <= int(payload.get("max_future_reminder_days") or 0) <= 730:
            raise TimingReminderError("TIMING_REMINDER_HORIZON_INVALID", "El horizonte de recordatorios M37.2 es inválido.", 500)
        try:
            minimum = date.fromisoformat(str(payload.get("minimum_event_date") or ""))
        except ValueError as exc:
            raise TimingReminderError("TIMING_MINIMUM_DATE_INVALID", "La fecha mínima M37.2 es inválida.", 500) from exc
        if minimum.year < 1900:
            raise TimingReminderError("TIMING_MINIMUM_DATE_INVALID", "La fecha mínima M37.2 es demasiado antigua.", 500)
        governance = payload.get("governance") or {}
        true_keys = {
            "m24_due_at_is_operational_checkpoint_only",
            "date_records_append_only",
            "reminder_events_append_only",
        }
        false_keys = {
            "date_record_is_legal_deadline",
            "date_record_legal_deadline_verified",
            "evidence_reference_verifies_date",
            "professional_record_verifies_legal_deadline",
            "reminder_is_legal_deadline",
            "reminder_acknowledgement_completes_task",
            "reminder_due_completes_task",
            "automatic_external_notification",
            "automatic_task_completion",
            "automatic_close",
            "automatic_escalation",
            "business_calendar_calculation",
            "statutory_deadline_calculation",
        }
        if any(governance.get(key) is not True for key in true_keys):
            raise TimingReminderError("TIMING_GOVERNANCE_INVALID", "M37.2 perdió una garantía append-only u operativa.", 500)
        if any(governance.get(key) is not False for key in false_keys):
            raise TimingReminderError("TIMING_LEGAL_BOUNDARY_INVALID", "M37.2 no puede presentar fechas operativas como términos legales.", 500)
        return {
            "valid": True,
            "event_types": len(DATE_EVENT_TYPES),
            "provenance": len(PROVENANCE),
            "timezone": "America/Bogota",
        }

    def _now(self) -> datetime:
        current = self.now_provider()
        if not isinstance(current, datetime):
            raise TimingReminderError("TIMING_CLOCK_INVALID", "El reloj M37.2 no devolvió una fecha válida.", 500)
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        return current.astimezone(self.timezone)

    def _today(self) -> date:
        return self._now().date()

    def _created_at(self) -> str:
        return self._now().isoformat(timespec="seconds")

    def _ensure_schemas(self, con) -> None:
        self.followup.ensure_schema(con)
        self.evidence.ensure_schema(con)
        self.ensure_schema(con)

    def _context(self, con, actor: Mapping[str, Any], case_id: str, *, writable: bool) -> tuple[dict[str, Any], dict[str, Any]]:
        self._ensure_schemas(con)
        case = self.followup._require_access(con, case_id, actor)
        self.followup._delivery(con, case_id)
        enrollment = self.followup._enrollment(con, case_id)
        if not enrollment or str(enrollment.get("state") or "") != "ACTIVE":
            raise TimingReminderError("TIMING_FOLLOWUP_NOT_ACTIVE", "M37.2 requiere un seguimiento M37.0 activo.", 409)
        integrity = self.followup.verify_chain(con, case_id)
        if not integrity.get("valid"):
            raise TimingReminderError("TIMING_FOLLOWUP_AUDIT_INVALID", "La cadena M37 está alterada.", 422)
        if writable:
            journey = self.followup.journey.detail(con, case_id, dict(actor))
            if str(journey.get("current_state") or "") != "EN_SEGUIMIENTO":
                raise TimingReminderError("TIMING_FOLLOWUP_READ_ONLY", "El expediente ya no admite cambios temporales M37.2.", 409)
        return case, enrollment

    def _task(self, con, case_id: str, follow_up_id: str, enrollment: Mapping[str, Any]) -> dict[str, Any]:
        if follow_up_id not in self.followup._task_ids(enrollment):
            raise TimingReminderError("TIMING_TASK_NOT_AVAILABLE", "La actividad no pertenece al seguimiento M37.0.", 404)
        row = con.execute(
            "SELECT id,action_label,due_at,status FROM m24_case_follow_up WHERE id=? AND case_id=?",
            (follow_up_id, case_id),
        ).fetchone()
        if not row:
            raise TimingReminderError("TIMING_TASK_NOT_AVAILABLE", "La actividad no está disponible.", 404)
        task = dict(row)
        if str(task.get("action_label") or "") not in self.followup._task_contracts(str(enrollment.get("product_code") or "")):
            raise TimingReminderError("TIMING_TASK_DRIFT", "La actividad dejó de coincidir con el contrato M37.", 422)
        return task

    @staticmethod
    def _provenance(actor: Mapping[str, Any]) -> str:
        role = str(actor.get("role") or "")
        if role == "client":
            return "USER_ASSERTED"
        if role in {"specialist", "admin"}:
            return "PROFESSIONAL_RECORDED"
        raise PermissionDenied("El rol actual no puede registrar fechas M37.2.")

    def _parse_event_date(self, raw: Any) -> str:
        text = str(raw or "").strip()
        try:
            value = date.fromisoformat(text)
        except ValueError as exc:
            raise TimingReminderError("TIMING_EVENT_DATE_INVALID", "La fecha del evento debe usar formato AAAA-MM-DD.", 422) from exc
        minimum = date.fromisoformat(str(self.contract["minimum_event_date"]))
        maximum = self._today() + timedelta(days=366)
        if value < minimum or value > maximum:
            raise TimingReminderError("TIMING_EVENT_DATE_OUT_OF_RANGE", "La fecha del evento está fuera del rango admitido.", 422)
        return value.isoformat()

    def _parse_reminder_date(self, raw: Any) -> str:
        text = str(raw or "").strip()
        try:
            value = date.fromisoformat(text)
        except ValueError as exc:
            raise TimingReminderError("TIMING_REMINDER_DATE_INVALID", "El recordatorio debe usar formato AAAA-MM-DD.", 422) from exc
        today = self._today()
        maximum = today + timedelta(days=int(self.contract["max_future_reminder_days"]))
        if value < today or value > maximum:
            raise TimingReminderError("TIMING_REMINDER_DATE_OUT_OF_RANGE", "El recordatorio debe programarse entre hoy y el horizonte operativo permitido.", 422)
        return value.isoformat()

    def _verify_evidence_link(self, con, case_id: str, follow_up_id: str, evidence_id: str | None) -> str | None:
        if not evidence_id:
            return None
        evidence_id = _safe_id(evidence_id, "evidence_id")
        row = self.evidence._item(con, case_id, evidence_id)
        if str(row.get("follow_up_id") or "") != follow_up_id:
            raise TimingReminderError("TIMING_EVIDENCE_TASK_MISMATCH", "El soporte no pertenece a la actividad indicada.", 422)
        self.evidence._verify_content(con, row)
        return evidence_id

    @staticmethod
    def _date_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "follow_up_id": str(row.get("follow_up_id") or ""),
            "event_type": str(row.get("event_type") or ""),
            "date_value": str(row.get("date_value") or ""),
            "provenance": str(row.get("provenance") or ""),
            "evidence_id": str(row.get("evidence_id") or "") or None,
            "supersedes_id": str(row.get("supersedes_id") or "") or None,
            "recorder_id": str(row.get("recorder_id") or ""),
            "recorder_role": str(row.get("recorder_role") or ""),
            "created_at": str(row.get("created_at") or ""),
        }

    def _verify_date_records(self, con, case_id: str) -> list[dict[str, Any]]:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_timing_date_record WHERE case_id=? ORDER BY created_at,id",
            (case_id,),
        ).fetchall()]
        ids = {str(row.get("id") or "") for row in rows}
        superseded_by: dict[str, str] = {}
        for row in rows:
            if _hash(self._date_candidate(row)) != str(row.get("record_hash") or ""):
                raise TimingReminderError("TIMING_DATE_RECORD_TAMPERED", "Un registro de fecha M37.2 fue alterado.", 422)
            parent = str(row.get("supersedes_id") or "")
            if parent:
                if parent not in ids or parent in superseded_by:
                    raise TimingReminderError("TIMING_DATE_SUPERSESSION_INVALID", "La cadena de corrección de fechas M37.2 es inválida.", 422)
                superseded_by[parent] = str(row["id"])
        for row in rows:
            row["superseded_by_id"] = superseded_by.get(str(row["id"]))
        return rows

    def _date_row(self, con, case_id: str, date_record_id: str) -> dict[str, Any]:
        rows = self._verify_date_records(con, case_id)
        for row in rows:
            if str(row.get("id") or "") == date_record_id:
                return row
        raise TimingReminderError("TIMING_DATE_RECORD_NOT_AVAILABLE", "El registro de fecha no está disponible.", 404)

    @staticmethod
    def _reminder_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "follow_up_id": str(row.get("follow_up_id") or ""),
            "scheduled_for": str(row.get("scheduled_for") or ""),
            "source_date_record_id": str(row.get("source_date_record_id") or "") or None,
            "creator_id": str(row.get("creator_id") or ""),
            "creator_role": str(row.get("creator_role") or ""),
            "created_at": str(row.get("created_at") or ""),
        }

    def _verify_reminder(self, row: Mapping[str, Any]) -> None:
        if _hash(self._reminder_candidate(row)) != str(row.get("reminder_hash") or ""):
            raise TimingReminderError("TIMING_REMINDER_TAMPERED", "Un recordatorio M37.2 fue alterado.", 422)

    @staticmethod
    def _reminder_event_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "reminder_id": str(row.get("reminder_id") or ""),
            "case_id": str(row.get("case_id") or ""),
            "sequence": int(row.get("sequence") or 0),
            "action": str(row.get("action") or ""),
            "actor_id": str(row.get("actor_id") or ""),
            "actor_role": str(row.get("actor_role") or ""),
            "created_at": str(row.get("created_at") or ""),
            "previous_hash": str(row.get("previous_hash") or ""),
        }

    def _reminder_events(self, con, reminder_id: str) -> list[dict[str, Any]]:
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m37_timing_reminder_event WHERE reminder_id=? ORDER BY sequence,id",
            (reminder_id,),
        ).fetchall()]
        previous = ZERO_HASH
        for expected, row in enumerate(rows, 1):
            candidate = self._reminder_event_candidate(row)
            if candidate["sequence"] != expected or candidate["previous_hash"] != previous:
                raise TimingReminderError("TIMING_REMINDER_EVENT_CHAIN_INVALID", "La secuencia de eventos del recordatorio es inválida.", 422)
            calculated = _hash(candidate)
            if calculated != str(row.get("event_hash") or ""):
                raise TimingReminderError("TIMING_REMINDER_EVENT_TAMPERED", "Un evento de recordatorio M37.2 fue alterado.", 422)
            previous = calculated
        if rows and str(rows[0].get("action") or "") != "SCHEDULED":
            raise TimingReminderError("TIMING_REMINDER_EVENT_CHAIN_INVALID", "El recordatorio no conserva su evento inicial.", 422)
        return rows

    def _append_reminder_event(self, con, reminder: Mapping[str, Any], action: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        events = self._reminder_events(con, str(reminder["id"]))
        if events and str(events[-1].get("action") or "") in REMINDER_ACTIONS:
            raise TimingReminderError("TIMING_REMINDER_TERMINAL", "El recordatorio ya fue reconocido o cancelado.", 409)
        sequence = len(events) + 1
        previous = str(events[-1].get("event_hash") or ZERO_HASH) if events else ZERO_HASH
        row = {
            "id": f"RME-{uuid.uuid4().hex[:16].upper()}",
            "reminder_id": str(reminder["id"]),
            "case_id": str(reminder["case_id"]),
            "sequence": sequence,
            "action": action,
            "actor_id": str(actor.get("id") or ""),
            "actor_role": str(actor.get("role") or ""),
            "created_at": self._created_at(),
            "previous_hash": previous,
        }
        row["event_hash"] = _hash(row)
        con.execute(
            """INSERT INTO m37_timing_reminder_event
               (id,reminder_id,case_id,sequence,action,actor_id,actor_role,previous_hash,event_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                row["id"], row["reminder_id"], row["case_id"], row["sequence"], row["action"],
                row["actor_id"], row["actor_role"], row["previous_hash"], row["event_hash"], row["created_at"],
            ),
        )
        return row

    def _reminder_row(self, con, case_id: str, reminder_id: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM m37_timing_reminder WHERE id=? AND case_id=?", (reminder_id, case_id)).fetchone()
        if not row:
            raise TimingReminderError("TIMING_REMINDER_NOT_AVAILABLE", "El recordatorio no está disponible.", 404)
        reminder = dict(row)
        self._verify_reminder(reminder)
        self._reminder_events(con, reminder_id)
        return reminder

    def _public_date(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "date_record_id": str(row.get("id") or ""),
            "follow_up_id": str(row.get("follow_up_id") or ""),
            "event_type": str(row.get("event_type") or ""),
            "date": str(row.get("date_value") or ""),
            "provenance": str(row.get("provenance") or ""),
            "evidence_referenced": bool(row.get("evidence_id")),
            "recorded_by_role": str(row.get("recorder_role") or ""),
            "recorded_at": str(row.get("created_at") or ""),
            "supersedes_date_record_id": str(row.get("supersedes_id") or "") or None,
            "superseded": bool(row.get("superseded_by_id")),
            "superseded_by_date_record_id": str(row.get("superseded_by_id") or "") or None,
            "timing": {
                "kind": "RECORDED_EVENT_DATE",
                "is_legal_deadline": False,
                "legal_deadline_verified": False,
                "evidence_reference_verifies_date": False,
            },
        }

    def _public_reminder(self, con, row: Mapping[str, Any], date_rows: list[dict[str, Any]]) -> dict[str, Any]:
        self._verify_reminder(row)
        events = self._reminder_events(con, str(row["id"]))
        latest = str(events[-1].get("action") or "") if events else ""
        if latest == "ACKNOWLEDGED":
            status = "ACKNOWLEDGED"
        elif latest == "CANCELLED":
            status = "CANCELLED"
        else:
            status = "DUE" if date.fromisoformat(str(row["scheduled_for"])) <= self._today() else "SCHEDULED"
        source_id = str(row.get("source_date_record_id") or "")
        source = next((item for item in date_rows if str(item.get("id") or "") == source_id), None) if source_id else None
        return {
            "reminder_id": str(row.get("id") or ""),
            "follow_up_id": str(row.get("follow_up_id") or ""),
            "scheduled_for": str(row.get("scheduled_for") or ""),
            "timezone": "America/Bogota",
            "status": status,
            "created_by_role": str(row.get("creator_role") or ""),
            "created_at": str(row.get("created_at") or ""),
            "source_date_record_id": source_id or None,
            "source_date_superseded": bool(source and source.get("superseded_by_id")),
            "event_count": len(events),
            "timing": {
                "kind": "IN_APP_OPERATIONAL_REMINDER",
                "is_legal_deadline": False,
                "legal_deadline_verified": False,
            },
            "governance": {
                "acknowledgement_completes_task": False,
                "due_completes_task": False,
                "automatic_external_notification": False,
                "automatic_close": False,
                "automatic_escalation": False,
            },
        }

    def record_date(
        self,
        actor: dict[str, Any],
        case_id: str,
        follow_up_id: str,
        event_type: str,
        date_value: str,
        *,
        evidence_id: str | None = None,
        supersedes_date_record_id: str | None = None,
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        follow_up_id = _safe_id(follow_up_id, "follow_up_id")
        event_type = str(event_type or "").strip().upper()
        if event_type not in DATE_EVENT_TYPES:
            raise TimingReminderError("TIMING_EVENT_TYPE_INVALID", "Tipo de fecha M37.2 inválido.", 422)
        normalized_date = self._parse_event_date(date_value)
        con = self.db_factory()
        try:
            _case, enrollment = self._context(con, actor, case_id, writable=True)
            task = self._task(con, case_id, follow_up_id, enrollment)
            provenance = self._provenance(actor)
            evidence_id = self._verify_evidence_link(con, case_id, follow_up_id, evidence_id)
            supersedes_id = _safe_id(supersedes_date_record_id, "supersedes_date_record_id") if supersedes_date_record_id else None
            rows = self._verify_date_records(con, case_id)
            if sum(1 for row in rows if str(row.get("follow_up_id") or "") == follow_up_id) >= int(self.contract["max_date_records_per_task"]):
                raise TimingReminderError("TIMING_DATE_RECORD_QUOTA", "La actividad alcanzó el máximo de registros de fecha M37.2.", 409)
            parent = None
            if supersedes_id:
                parent = next((row for row in rows if str(row.get("id") or "") == supersedes_id), None)
                if not parent or str(parent.get("follow_up_id") or "") != follow_up_id:
                    raise TimingReminderError("TIMING_SUPERSEDED_DATE_NOT_AVAILABLE", "La fecha a corregir no pertenece a esta actividad.", 404)
                if parent.get("superseded_by_id"):
                    raise TimingReminderError("TIMING_DATE_ALREADY_SUPERSEDED", "La fecha indicada ya fue corregida; use el registro vigente.", 409)
            exact = next((
                row for row in reversed(rows)
                if str(row.get("follow_up_id") or "") == follow_up_id
                and str(row.get("event_type") or "") == event_type
                and str(row.get("date_value") or "") == normalized_date
                and (str(row.get("evidence_id") or "") or None) == evidence_id
                and (str(row.get("supersedes_id") or "") or None) == supersedes_id
                and str(row.get("recorder_id") or "") == str(actor.get("id") or "")
            ), None)
            if exact:
                result = self._public_date(exact)
                result["idempotent"] = True
                return result
            before_status = str(task.get("status") or "")
            now = self._created_at()
            row = {
                "id": f"DTR-{uuid.uuid4().hex[:16].upper()}",
                "case_id": case_id,
                "follow_up_id": follow_up_id,
                "event_type": event_type,
                "date_value": normalized_date,
                "provenance": provenance,
                "evidence_id": evidence_id,
                "supersedes_id": supersedes_id,
                "recorder_id": str(actor.get("id") or ""),
                "recorder_role": str(actor.get("role") or ""),
                "created_at": now,
            }
            row["record_hash"] = _hash(self._date_candidate(row))
            con.execute(
                """INSERT INTO m37_timing_date_record
                   (id,case_id,follow_up_id,event_type,date_value,provenance,evidence_id,supersedes_id,
                    recorder_id,recorder_role,record_hash,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["id"], case_id, follow_up_id, event_type, normalized_date, provenance, evidence_id,
                    supersedes_id, row["recorder_id"], row["recorder_role"], row["record_hash"], now,
                ),
            )
            self.followup._append_event(
                con,
                case_id,
                "DATE_RECORDED" if not supersedes_id else "DATE_CORRECTION_RECORDED",
                actor,
                {
                    "date_record_id": row["id"],
                    "follow_up_id": follow_up_id,
                    "event_type": event_type,
                    "provenance": provenance,
                    "evidence_referenced": bool(evidence_id),
                    "supersedes_date_record_id": supersedes_id,
                    "task_status_changed": False,
                    "is_legal_deadline": False,
                    "legal_deadline_verified": False,
                },
            )
            after = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (follow_up_id, case_id)).fetchone()
            if not after or str(after[0] or "") != before_status:
                raise TimingReminderError("TIMING_DATE_TASK_MUTATION_DETECTED", "Registrar una fecha alteró indebidamente la actividad.", 500)
            con.commit()
            result = self._public_date(self._date_row(con, case_id, row["id"]))
            result["idempotent"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()

    def schedule_reminder(
        self,
        actor: dict[str, Any],
        case_id: str,
        follow_up_id: str,
        scheduled_for: str,
        *,
        source_date_record_id: str | None = None,
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        follow_up_id = _safe_id(follow_up_id, "follow_up_id")
        normalized = self._parse_reminder_date(scheduled_for)
        con = self.db_factory()
        try:
            _case, enrollment = self._context(con, actor, case_id, writable=True)
            task = self._task(con, case_id, follow_up_id, enrollment)
            source_id = _safe_id(source_date_record_id, "source_date_record_id") if source_date_record_id else None
            date_rows = self._verify_date_records(con, case_id)
            if source_id:
                source = next((row for row in date_rows if str(row.get("id") or "") == source_id), None)
                if not source or str(source.get("follow_up_id") or "") != follow_up_id:
                    raise TimingReminderError("TIMING_SOURCE_DATE_NOT_AVAILABLE", "La fecha fuente no pertenece a esta actividad.", 404)
                if source.get("superseded_by_id"):
                    raise TimingReminderError("TIMING_SOURCE_DATE_SUPERSEDED", "No se puede programar un recordatorio desde una fecha ya corregida.", 409)
            existing_rows = [dict(row) for row in con.execute(
                "SELECT * FROM m37_timing_reminder WHERE case_id=? AND follow_up_id=? ORDER BY created_at,id",
                (case_id, follow_up_id),
            ).fetchall()]
            if len(existing_rows) >= int(self.contract["max_reminders_per_task"]):
                raise TimingReminderError("TIMING_REMINDER_QUOTA", "La actividad alcanzó el máximo de recordatorios M37.2.", 409)
            for existing in reversed(existing_rows):
                self._verify_reminder(existing)
                if (
                    str(existing.get("scheduled_for") or "") == normalized
                    and (str(existing.get("source_date_record_id") or "") or None) == source_id
                    and str(existing.get("creator_id") or "") == str(actor.get("id") or "")
                ):
                    events = self._reminder_events(con, str(existing["id"]))
                    if events and str(events[-1].get("action") or "") == "SCHEDULED":
                        result = self._public_reminder(con, existing, date_rows)
                        result["idempotent"] = True
                        return result
            before_status = str(task.get("status") or "")
            now = self._created_at()
            reminder = {
                "id": f"RMD-{uuid.uuid4().hex[:16].upper()}",
                "case_id": case_id,
                "follow_up_id": follow_up_id,
                "scheduled_for": normalized,
                "source_date_record_id": source_id,
                "creator_id": str(actor.get("id") or ""),
                "creator_role": str(actor.get("role") or ""),
                "created_at": now,
            }
            reminder["reminder_hash"] = _hash(self._reminder_candidate(reminder))
            con.execute(
                """INSERT INTO m37_timing_reminder
                   (id,case_id,follow_up_id,scheduled_for,source_date_record_id,creator_id,creator_role,reminder_hash,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    reminder["id"], case_id, follow_up_id, normalized, source_id, reminder["creator_id"],
                    reminder["creator_role"], reminder["reminder_hash"], now,
                ),
            )
            self._append_reminder_event(con, reminder, "SCHEDULED", actor)
            self.followup._append_event(
                con,
                case_id,
                "REMINDER_SCHEDULED",
                actor,
                {
                    "reminder_id": reminder["id"],
                    "follow_up_id": follow_up_id,
                    "source_date_record_id": source_id,
                    "task_status_changed": False,
                    "timing_kind": "IN_APP_OPERATIONAL_REMINDER",
                    "is_legal_deadline": False,
                    "legal_deadline_verified": False,
                    "external_notification": False,
                },
            )
            after = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (follow_up_id, case_id)).fetchone()
            if not after or str(after[0] or "") != before_status:
                raise TimingReminderError("TIMING_REMINDER_TASK_MUTATION_DETECTED", "Programar un recordatorio alteró indebidamente la actividad.", 500)
            con.commit()
            result = self._public_reminder(con, self._reminder_row(con, case_id, reminder["id"]), self._verify_date_records(con, case_id))
            result["idempotent"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()

    def record_reminder_action(self, actor: dict[str, Any], case_id: str, reminder_id: str, action: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        reminder_id = _safe_id(reminder_id, "reminder_id")
        action = str(action or "").strip().upper()
        if action not in REMINDER_ACTIONS:
            raise TimingReminderError("TIMING_REMINDER_ACTION_INVALID", "Acción de recordatorio inválida.", 422)
        con = self.db_factory()
        try:
            _case, enrollment = self._context(con, actor, case_id, writable=True)
            reminder = self._reminder_row(con, case_id, reminder_id)
            task = self._task(con, case_id, str(reminder.get("follow_up_id") or ""), enrollment)
            events = self._reminder_events(con, reminder_id)
            if events and str(events[-1].get("action") or "") == action:
                result = self._public_reminder(con, reminder, self._verify_date_records(con, case_id))
                result["idempotent"] = True
                return result
            if events and str(events[-1].get("action") or "") in REMINDER_ACTIONS:
                raise TimingReminderError("TIMING_REMINDER_TERMINAL", "El recordatorio ya tiene un estado final distinto.", 409)
            before_status = str(task.get("status") or "")
            self._append_reminder_event(con, reminder, action, actor)
            self.followup._append_event(
                con,
                case_id,
                f"REMINDER_{action}",
                actor,
                {
                    "reminder_id": reminder_id,
                    "follow_up_id": str(reminder.get("follow_up_id") or ""),
                    "task_status_changed": False,
                    "is_legal_deadline": False,
                    "legal_deadline_verified": False,
                    "external_notification": False,
                },
            )
            after = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (str(reminder["follow_up_id"]), case_id)).fetchone()
            if not after or str(after[0] or "") != before_status:
                raise TimingReminderError("TIMING_REMINDER_ACTION_TASK_MUTATION_DETECTED", "La acción del recordatorio alteró indebidamente la actividad.", 500)
            con.commit()
            result = self._public_reminder(con, self._reminder_row(con, case_id, reminder_id), self._verify_date_records(con, case_id))
            result["idempotent"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            case, _enrollment = self._context(con, actor, case_id, writable=False)
            followup = self.followup._detail_from_open_connection(con, actor, case_id)
            date_rows = self._verify_date_records(con, case_id)
            reminder_rows = [dict(row) for row in con.execute(
                "SELECT * FROM m37_timing_reminder WHERE case_id=? ORDER BY scheduled_for,created_at,id",
                (case_id,),
            ).fetchall()]
            for reminder in reminder_rows:
                self._verify_reminder(reminder)
            dates = [self._public_date(row) for row in date_rows]
            reminders = [self._public_reminder(con, row, date_rows) for row in reminder_rows]
            checkpoints = []
            for task in followup.get("tasks") or []:
                if task.get("due_at"):
                    checkpoints.append({
                        "follow_up_id": task.get("follow_up_id"),
                        "due_at": task.get("due_at"),
                        "kind": "OPERATIONAL_CHECKPOINT",
                        "is_legal_deadline": False,
                        "legal_deadline_verified": False,
                        "source": "M24_EXISTING_DUE_AT",
                    })
            return {
                "schema": "legalai_m37_2_recorded_dates_reminders_v1",
                "schema_version": SCHEMA_VERSION,
                "case_id": case_id,
                "product_code": str(case.get("product_code") or ""),
                "timezone": "America/Bogota",
                "operational_checkpoints": checkpoints,
                "date_records": dates,
                "reminders": reminders,
                "metrics": {
                    "date_records": len(dates),
                    "effective_date_records": sum(1 for item in dates if not item["superseded"]),
                    "evidence_referenced_dates": sum(1 for item in dates if item["evidence_referenced"]),
                    "reminders": len(reminders),
                    "scheduled": sum(1 for item in reminders if item["status"] == "SCHEDULED"),
                    "due": sum(1 for item in reminders if item["status"] == "DUE"),
                    "acknowledged": sum(1 for item in reminders if item["status"] == "ACKNOWLEDGED"),
                    "cancelled": sum(1 for item in reminders if item["status"] == "CANCELLED"),
                },
                "notice": str(self.contract.get("notice") or ""),
                "governance": {
                    "m24_due_at_is_operational_checkpoint_only": True,
                    "date_record_is_legal_deadline": False,
                    "date_record_legal_deadline_verified": False,
                    "evidence_reference_verifies_date": False,
                    "professional_record_verifies_legal_deadline": False,
                    "reminder_is_legal_deadline": False,
                    "reminder_acknowledgement_completes_task": False,
                    "reminder_due_completes_task": False,
                    "business_calendar_calculation": False,
                    "statutory_deadline_calculation": False,
                    "automatic_external_notification": False,
                    "automatic_task_completion": False,
                    "automatic_close": False,
                    "automatic_escalation": False,
                },
            }
        finally:
            con.close()


__all__ = [
    "TimingReminderCenter",
    "TimingReminderError",
    "DATE_EVENT_TYPES",
    "PROVENANCE",
    "REMINDER_ACTIONS",
    "SCHEMA_VERSION",
]
