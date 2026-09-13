from __future__ import annotations

"""M37.2 idempotency hardening.

The certified runtime must resolve an exact retry before quota enforcement.
This wrapper keeps the base M37.2 semantics unchanged for new writes while
ensuring retries do not consume additional capacity or fail only because the
quota became full after the original successful operation.
"""

from typing import Any

from legalai_platform import timing_reminders_m37_2 as base


class HardenedTimingReminderCenter(base.TimingReminderCenter):
    """Runtime M37.2 center with retry-before-quota ordering."""

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
        safe_case_id = base._safe_id(case_id, "case_id")
        safe_follow_up_id = base._safe_id(follow_up_id, "follow_up_id")
        normalized_event_type = str(event_type or "").strip().upper()
        if normalized_event_type not in base.DATE_EVENT_TYPES:
            raise base.TimingReminderError("TIMING_EVENT_TYPE_INVALID", "Tipo de fecha M37.2 inválido.", 422)
        normalized_date = self._parse_event_date(date_value)

        con = self.db_factory()
        try:
            _case, enrollment = self._context(con, actor, safe_case_id, writable=True)
            self._task(con, safe_case_id, safe_follow_up_id, enrollment)
            self._provenance(actor)
            normalized_evidence_id = self._verify_evidence_link(
                con,
                safe_case_id,
                safe_follow_up_id,
                evidence_id,
            )
            supersedes_id = (
                base._safe_id(supersedes_date_record_id, "supersedes_date_record_id")
                if supersedes_date_record_id
                else None
            )
            rows = self._verify_date_records(con, safe_case_id)

            parent = None
            if supersedes_id:
                parent = next((row for row in rows if str(row.get("id") or "") == supersedes_id), None)
                if not parent or str(parent.get("follow_up_id") or "") != safe_follow_up_id:
                    raise base.TimingReminderError(
                        "TIMING_SUPERSEDED_DATE_NOT_AVAILABLE",
                        "La fecha a corregir no pertenece a esta actividad.",
                        404,
                    )

            exact = next(
                (
                    row
                    for row in reversed(rows)
                    if str(row.get("follow_up_id") or "") == safe_follow_up_id
                    and str(row.get("event_type") or "") == normalized_event_type
                    and str(row.get("date_value") or "") == normalized_date
                    and (str(row.get("evidence_id") or "") or None) == normalized_evidence_id
                    and (str(row.get("supersedes_id") or "") or None) == supersedes_id
                    and str(row.get("recorder_id") or "") == str(actor.get("id") or "")
                ),
                None,
            )
            if exact:
                if parent and str(parent.get("superseded_by_id") or "") not in {"", str(exact.get("id") or "")}:
                    raise base.TimingReminderError(
                        "TIMING_DATE_SUPERSESSION_INVALID",
                        "La corrección exacta ya no coincide con la cadena vigente.",
                        422,
                    )
                result = self._public_date(exact)
                result["idempotent"] = True
                return result

            if parent and parent.get("superseded_by_id"):
                raise base.TimingReminderError(
                    "TIMING_DATE_ALREADY_SUPERSEDED",
                    "La fecha indicada ya fue corregida; use el registro vigente.",
                    409,
                )

            task_count = sum(1 for row in rows if str(row.get("follow_up_id") or "") == safe_follow_up_id)
            if task_count >= int(self.contract["max_date_records_per_task"]):
                raise base.TimingReminderError(
                    "TIMING_DATE_RECORD_QUOTA",
                    "La actividad alcanzó el máximo de registros de fecha M37.2.",
                    409,
                )
        finally:
            con.close()

        return super().record_date(
            actor,
            safe_case_id,
            safe_follow_up_id,
            normalized_event_type,
            normalized_date,
            evidence_id=normalized_evidence_id,
            supersedes_date_record_id=supersedes_id,
        )

    def schedule_reminder(
        self,
        actor: dict[str, Any],
        case_id: str,
        follow_up_id: str,
        scheduled_for: str,
        *,
        source_date_record_id: str | None = None,
    ) -> dict[str, Any]:
        safe_case_id = base._safe_id(case_id, "case_id")
        safe_follow_up_id = base._safe_id(follow_up_id, "follow_up_id")
        normalized = self._parse_reminder_date(scheduled_for)

        con = self.db_factory()
        try:
            _case, enrollment = self._context(con, actor, safe_case_id, writable=True)
            self._task(con, safe_case_id, safe_follow_up_id, enrollment)
            source_id = (
                base._safe_id(source_date_record_id, "source_date_record_id")
                if source_date_record_id
                else None
            )
            date_rows = self._verify_date_records(con, safe_case_id)
            if source_id:
                source = next((row for row in date_rows if str(row.get("id") or "") == source_id), None)
                if not source or str(source.get("follow_up_id") or "") != safe_follow_up_id:
                    raise base.TimingReminderError(
                        "TIMING_SOURCE_DATE_NOT_AVAILABLE",
                        "La fecha fuente no pertenece a esta actividad.",
                        404,
                    )
                if source.get("superseded_by_id"):
                    raise base.TimingReminderError(
                        "TIMING_SOURCE_DATE_SUPERSEDED",
                        "No se puede programar un recordatorio desde una fecha ya corregida.",
                        409,
                    )

            existing_rows = [
                dict(row)
                for row in con.execute(
                    "SELECT * FROM m37_timing_reminder WHERE case_id=? AND follow_up_id=? ORDER BY created_at,id",
                    (safe_case_id, safe_follow_up_id),
                ).fetchall()
            ]
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

            if len(existing_rows) >= int(self.contract["max_reminders_per_task"]):
                raise base.TimingReminderError(
                    "TIMING_REMINDER_QUOTA",
                    "La actividad alcanzó el máximo de recordatorios M37.2.",
                    409,
                )
        finally:
            con.close()

        return super().schedule_reminder(
            actor,
            safe_case_id,
            safe_follow_up_id,
            normalized,
            source_date_record_id=source_id,
        )


TimingReminderError = base.TimingReminderError
DATE_EVENT_TYPES = base.DATE_EVENT_TYPES
PROVENANCE = base.PROVENANCE
REMINDER_ACTIONS = base.REMINDER_ACTIONS
SCHEMA_VERSION = base.SCHEMA_VERSION

__all__ = [
    "HardenedTimingReminderCenter",
    "TimingReminderError",
    "DATE_EVENT_TYPES",
    "PROVENANCE",
    "REMINDER_ACTIONS",
    "SCHEMA_VERSION",
]
