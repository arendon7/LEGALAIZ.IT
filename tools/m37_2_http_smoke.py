#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, register_client, require
from tools.m36_0_http_smoke import login_admin
from tools.m36_2_http_smoke import login_specialist
from tools.m36_3_http_smoke import CONFIRMATION, prepare_reviewed_released_case


FOLLOWUP_CONFIRMATION = "INICIAR SEGUIMIENTO"
BOGOTA = ZoneInfo("America/Bogota")


def main() -> int:
    owner = Client()
    admin = login_admin()
    case, desk_ids, specialist_id = prepare_reviewed_released_case(owner, admin)
    case_id = case["case_id"]

    delivered = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": CONFIRMATION},
        expected=201,
    )
    require(delivered.get("state") == "DELIVERED_IN_APP", "M37.2 necesita entrega M36.3 válida")

    started = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": FOLLOWUP_CONFIRMATION},
        expected=201,
    )
    require(started.get("lifecycle") == "ACTIVE", "M37.2 necesita seguimiento M37.0 ACTIVE")
    require(started.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.2 necesita M24 EN_SEGUIMIENTO")
    tasks = started.get("tasks") or []
    require(bool(tasks), "M37.2 no encontró actividades de seguimiento")
    task = tasks[0]
    task_id = str(task.get("follow_up_id") or "")
    task_status_before = str(task.get("status") or "")

    initial = owner.get(f"/api/m37/timing/cases/{case_id}", expected=200)
    require((initial.get("metrics") or {}).get("date_records") == 0, "M37.2 inventó fechas antes de registro")
    require((initial.get("metrics") or {}).get("reminders") == 0, "M37.2 inventó recordatorios antes de registro")
    governance = initial.get("governance") or {}
    require(governance.get("m24_due_at_is_operational_checkpoint_only") is True, "M37.2 perdió frontera de checkpoint operativo")
    require(governance.get("date_record_is_legal_deadline") is False, "M37.2 convirtió fecha registrada en término legal")
    require(governance.get("statutory_deadline_calculation") is False, "M37.2 activó cálculo normativo")
    require(governance.get("business_calendar_calculation") is False, "M37.2 activó calendario jurídico")

    today = datetime.now(BOGOTA).date().isoformat()

    date_path = f"/api/m37/timing/cases/{case_id}/tasks/{task_id}/dates"
    recorded = owner.post(
        date_path,
        {"event_type": "ACTION_PERFORMED", "date": today},
        expected=201,
    )
    date_record_id = str(recorded.get("date_record_id") or "")
    require(bool(date_record_id), "M37.2 no devolvió date_record_id")
    require(recorded.get("provenance") == "USER_ASSERTED", "M37.2 perdió procedencia del cliente")
    require(recorded.get("idempotent") is False, "Primer registro de fecha se marcó idempotente")
    require((recorded.get("timing") or {}).get("is_legal_deadline") is False, "M37.2 presentó fecha como término legal")
    require((recorded.get("timing") or {}).get("legal_deadline_verified") is False, "M37.2 inventó verificación de término legal")

    retry = owner.post(
        date_path,
        {"event_type": "ACTION_PERFORMED", "date": today},
        expected=200,
    )
    require(retry.get("idempotent") is True, "Retry exacto de fecha M37.2 no fue idempotente")
    require(retry.get("date_record_id") == date_record_id, "Retry exacto de fecha creó otro registro")

    specialist = login_specialist(specialist_id)
    professional = specialist.post(
        date_path,
        {"event_type": "AUTHORITY_RECEIPT_REPORTED", "date": today},
        expected=201,
    )
    require(professional.get("provenance") == "PROFESSIONAL_RECORDED", "M37.2 perdió procedencia profesional")
    require((professional.get("timing") or {}).get("legal_deadline_verified") is False, "Fecha profesional se convirtió en término verificado")

    reminder_path = f"/api/m37/timing/cases/{case_id}/tasks/{task_id}/reminders"
    reminder = owner.post(
        reminder_path,
        {"scheduled_for": today, "source_date_record_id": date_record_id},
        expected=201,
    )
    reminder_id = str(reminder.get("reminder_id") or "")
    require(bool(reminder_id), "M37.2 no devolvió reminder_id")
    require(reminder.get("status") == "DUE", "Recordatorio para hoy no quedó DUE en Bogotá")
    require((reminder.get("timing") or {}).get("is_legal_deadline") is False, "Recordatorio se presentó como término legal")
    require((reminder.get("governance") or {}).get("due_completes_task") is False, "DUE completó tarea por semántica")
    require((reminder.get("governance") or {}).get("automatic_external_notification") is False, "M37.2 declaró comunicación externa automática")

    reminder_retry = owner.post(
        reminder_path,
        {"scheduled_for": today, "source_date_record_id": date_record_id},
        expected=200,
    )
    require(reminder_retry.get("idempotent") is True, "Retry exacto de recordatorio M37.2 no fue idempotente")
    require(reminder_retry.get("reminder_id") == reminder_id, "Retry exacto de recordatorio creó otro registro")

    acknowledged = owner.post(
        f"/api/m37/timing/cases/{case_id}/reminders/{reminder_id}/acknowledge",
        {},
        expected=201,
    )
    require(acknowledged.get("status") == "ACKNOWLEDGED", "M37.2 no registró acknowledge")
    require((acknowledged.get("governance") or {}).get("acknowledgement_completes_task") is False, "Acknowledge completó tarea")

    acknowledged_retry = owner.post(
        f"/api/m37/timing/cases/{case_id}/reminders/{reminder_id}/acknowledge",
        {},
        expected=200,
    )
    require(acknowledged_retry.get("idempotent") is True, "Retry acknowledge M37.2 duplicó evento")

    detail = owner.get(f"/api/m37/timing/cases/{case_id}", expected=200)
    metrics = detail.get("metrics") or {}
    require(metrics.get("date_records") == 2, "M37.2 perdió o duplicó registros de fecha")
    require(metrics.get("reminders") == 1, "M37.2 perdió o duplicó recordatorio")
    require(metrics.get("acknowledged") == 1, "M37.2 perdió acknowledge")
    require(metrics.get("due") == 0, "Recordatorio reconocido siguió presentado como DUE")

    other = Client()
    register_client(other, "M372Other")
    hidden = other.get(f"/api/m37/timing/cases/{case_id}", expected=404)
    require(hidden.get("code") == "FOLLOWUP_NOT_AVAILABLE", "M37.2 reveló datos temporales cross-tenant")

    final_followup = owner.get(f"/api/m37/follow-up/cases/{case_id}", expected=200)
    final_task = next(item for item in final_followup.get("tasks") or [] if item.get("follow_up_id") == task_id)
    require(final_task.get("status") == task_status_before, "M37.2 alteró estado de tarea M24")
    require(final_followup.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.2 cerró o escaló el expediente")

    raw = json.dumps({"recorded": recorded, "professional": professional, "reminder": reminder, "detail": detail}, ensure_ascii=False).lower()
    for forbidden in (
        "record_hash",
        "reminder_hash",
        "event_hash",
        "previous_hash",
        "recorder_id",
        "creator_id",
        "actor_id",
        "payment_intent_id",
        "problem_statement",
        "answers",
    ):
        require(forbidden not in raw, f"M37.2 filtró dato interno: {forbidden}")

    print(
        "M37.2 HTTP smoke PASS · "
        f"case={case_id} desks={len(desk_ids)} dates=2 reminders=1 acknowledged=1 "
        f"m24={final_followup.get('m24_current_state')} task_unchanged=true date_idempotent=true "
        "reminder_idempotent=true cross_tenant=hidden legal_deadline=false "
        "statutory_calculation=false external_notification=false auto_close=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M37.2 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
