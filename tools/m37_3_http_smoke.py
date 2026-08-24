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
from tools.m36_3_http_smoke import CONFIRMATION as DELIVERY_CONFIRMATION, prepare_reviewed_released_case
from tools.m37_1_http_smoke import multipart_post


START_CONFIRMATION = "INICIAR SEGUIMIENTO"
BOGOTA = ZoneInfo("America/Bogota")
CLOSE_INTERNAL = "El especialista revisó el seguimiento integral y no identificó actuaciones pendientes dentro del alcance contratado."
CLOSE_PUBLIC = "El seguimiento contratado fue completado y el expediente se cierra administrativamente sin afirmar un resultado jurídico externo."
ESC_INTERNAL = "Se identificó una contingencia que requiere nueva revisión profesional antes de continuar con el seguimiento actual."
ESC_PUBLIC = "El expediente requiere una nueva revisión profesional antes de continuar con el seguimiento actual."


def prepare_followup(owner: Client, admin: Client) -> tuple[dict, list[str], str, dict]:
    case, desk_ids, specialist_id = prepare_reviewed_released_case(owner, admin)
    case_id = case["case_id"]
    delivered = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": DELIVERY_CONFIRMATION},
        expected=201,
    )
    require(delivered.get("state") == "DELIVERED_IN_APP", "M37.3 necesita entrega M36.3 válida")
    started = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": START_CONFIRMATION},
        expected=201,
    )
    require(started.get("lifecycle") == "ACTIVE", "M37.3 necesita seguimiento M37.0 ACTIVE")
    require(started.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.3 necesita M24 EN_SEGUIMIENTO")
    return case, desk_ids, specialist_id, started


def main() -> int:
    owner = Client()
    admin = login_admin()
    case, desk_ids, specialist_id, started = prepare_followup(owner, admin)
    case_id = case["case_id"]
    specialist = login_specialist(specialist_id)
    tasks = started.get("tasks") or []
    require(bool(tasks), "M37.3 no encontró tareas M37.0")
    first_task_id = str(tasks[0].get("follow_up_id") or "")

    initial_owner = owner.get(f"/api/m37/disposition/cases/{case_id}", expected=200)
    require("REQUIRED_TASKS_NOT_COMPLETED" in (initial_owner.get("close_gate") or {}).get("blockers", []), "M37.3 no bloqueó cierre con tareas pendientes")
    require((initial_owner.get("close_gate") or {}).get("actor_can_execute") is False, "Cliente apareció habilitado para cerrar")
    require((initial_owner.get("escalation_gate") or {}).get("actor_can_execute") is False, "Cliente apareció habilitado para escalar")

    close_payload = {
        "reason_code": "FOLLOW_UP_SCOPE_COMPLETED",
        "internal_reason": CLOSE_INTERNAL,
        "client_summary": CLOSE_PUBLIC,
        "confirmation": "CERRAR SEGUIMIENTO",
    }
    client_denied = owner.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=403)
    require(client_denied.get("code") == "PERMISSION_DENIED", "Cliente pudo cerrar M37.3")
    admin_denied = admin.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=403)
    require(admin_denied.get("code") == "PERMISSION_DENIED", "Admin cerró M37.3 sin especialista asignado")

    support_body = b"%PDF-1.4\nsoporte M37.3 pendiente de revision\n%%EOF\n"
    uploaded = multipart_post(
        owner,
        f"/api/m37/evidence/cases/{case_id}/tasks/{first_task_id}/upload",
        "seguimiento_m373.pdf",
        support_body,
        expected=201,
    )
    evidence_id = str(uploaded.get("evidence_id") or "")
    require(bool(evidence_id), "M37.3 no recibió evidence_id M37.1")

    current = started
    for index, task in enumerate(tasks, 1):
        current = specialist.post(
            f"/api/m37/follow-up/cases/{case_id}/tasks/{task['follow_up_id']}",
            {
                "status": "completed",
                "note": f"Actividad {index} revisada y registrada profesionalmente para la compuerta M37.3.",
            },
            expected=200,
        )
    require((current.get("close_readiness") or {}).get("ready") is True, "M37.0 no quedó close_ready tras completar tareas")

    blocked_evidence = specialist.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=409)
    require(blocked_evidence.get("code") == "DISPOSITION_CLOSE_BLOCKED", "M37.3 cerró con soporte pendiente")
    assessment_pending = specialist.get(f"/api/m37/disposition/cases/{case_id}", expected=200)
    require("EVIDENCE_PENDING_REVIEW" in (assessment_pending.get("close_gate") or {}).get("blockers", []), "M37.3 perdió bloqueo de evidencia pendiente")

    reviewed = specialist.post(
        f"/api/m37/evidence/cases/{case_id}/items/{evidence_id}/review",
        {"disposition": "ACKNOWLEDGED_FOR_FOLLOWUP", "message_to_client": ""},
        expected=201,
    )
    require((reviewed.get("review") or {}).get("status") == "REVIEWED_FOR_INTAKE", "M37.3 no consumió revisión M37.1")

    today = datetime.now(BOGOTA).date().isoformat()
    reminder = owner.post(
        f"/api/m37/timing/cases/{case_id}/tasks/{first_task_id}/reminders",
        {"scheduled_for": today},
        expected=201,
    )
    reminder_id = str(reminder.get("reminder_id") or "")
    require(reminder.get("status") == "DUE", "M37.3 smoke esperaba recordatorio DUE operativo")

    blocked_reminder = specialist.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=409)
    require(blocked_reminder.get("code") == "DISPOSITION_CLOSE_BLOCKED", "M37.3 cerró con recordatorio activo")
    assessment_reminder = specialist.get(f"/api/m37/disposition/cases/{case_id}", expected=200)
    require("ACTIVE_REMINDER" in (assessment_reminder.get("close_gate") or {}).get("blockers", []), "M37.3 perdió bloqueo de recordatorio activo")

    acknowledged = owner.post(
        f"/api/m37/timing/cases/{case_id}/reminders/{reminder_id}/acknowledge",
        {},
        expected=201,
    )
    require(acknowledged.get("status") == "ACKNOWLEDGED", "M37.3 no consumió acknowledge M37.2")

    ready = specialist.get(f"/api/m37/disposition/cases/{case_id}", expected=200)
    require((ready.get("close_gate") or {}).get("ready") is True, "M37.3 no abrió cierre tras resolver bloqueos")
    require((ready.get("close_gate") or {}).get("actor_can_execute") is True, "Especialista asignado no quedó habilitado")
    require((ready.get("close_gate") or {}).get("blockers") == [], "M37.3 conservó bloqueos resueltos")

    closed = specialist.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=201)
    disposition = closed.get("disposition") or {}
    require(closed.get("idempotent") is False, "Primer cierre M37.3 apareció idempotente")
    require(closed.get("m24_current_state") == "CERRADO", "M37.3 no llevó M24 a CERRADO")
    require(disposition.get("target") == "CERRADO" and disposition.get("status") == "COMPLETED", "M37.3 no completó disposición de cierre")
    require(disposition.get("client_summary") == CLOSE_PUBLIC, "M37.3 perdió resumen visible")
    require((disposition.get("governance") or {}).get("legal_success_verified") is False, "M37.3 convirtió cierre en éxito jurídico")
    require((closed.get("governance") or {}).get("automatic_close") is False, "M37.3 presentó cierre como automático")

    retry = specialist.post(f"/api/m37/disposition/cases/{case_id}/close", close_payload, expected=200)
    require(retry.get("idempotent") is True, "Retry exacto de cierre M37.3 no fue idempotente")
    require((retry.get("disposition") or {}).get("disposition_id") == disposition.get("disposition_id"), "Retry M37.3 cambió disposition_id")

    owner_closed = owner.get(f"/api/m37/disposition/cases/{case_id}", expected=200)
    raw_close = json.dumps(owner_closed, ensure_ascii=False)
    require(CLOSE_INTERNAL not in raw_close, "M37.3 expuso razón interna al cliente")
    require((owner_closed.get("disposition") or {}).get("client_summary") == CLOSE_PUBLIC, "Cliente no recibió resumen de disposición")
    final_followup = owner.get(f"/api/m37/follow-up/cases/{case_id}", expected=200)
    require(final_followup.get("lifecycle") == "CLOSED", "M37.0 no reflejó cierre M37.3")
    require(final_followup.get("m24_current_state") == "CERRADO", "M37.0/M24 divergieron tras cierre M37.3")

    other = Client()
    register_client(other, "M373Other")
    hidden = other.get(f"/api/m37/disposition/cases/{case_id}", expected=404)
    require(hidden.get("code") == "FOLLOWUP_NOT_AVAILABLE", "M37.3 reveló disposición cross-tenant")

    # Segunda rama: una contingencia puede escalar aun con tareas pendientes.
    owner2 = Client()
    case2, _desk_ids2, _specialist2, started2 = prepare_followup(owner2, admin)
    case2_id = case2["case_id"]
    require((started2.get("close_readiness") or {}).get("ready") is False, "Caso de escalamiento no debería estar listo para cierre")
    escalate_payload = {
        "reason_code": "LEGAL_REVIEW_REQUIRED",
        "internal_reason": ESC_INTERNAL,
        "client_summary": ESC_PUBLIC,
        "confirmation": "ESCALAR SEGUIMIENTO",
    }
    escalated = admin.post(f"/api/m37/disposition/cases/{case2_id}/escalate", escalate_payload, expected=201)
    require(escalated.get("m24_current_state") == "ESCALADO", "Admin no pudo escalar contingencia M37.3")
    require((escalated.get("disposition") or {}).get("target") == "ESCALADO", "M37.3 perdió target de escalamiento")
    require((escalated.get("escalation_gate") or {}).get("requires_close_readiness") is False, "M37.3 hizo depender escalamiento del cierre")
    require((escalated.get("governance") or {}).get("automatic_escalation") is False, "M37.3 presentó escalamiento como automático")

    raw = json.dumps({"closed": closed, "retry": retry, "escalated": escalated}, ensure_ascii=False).lower()
    for forbidden in (
        "internal_reason",
        CLOSE_INTERNAL.lower(),
        ESC_INTERNAL.lower(),
        "intent_hash",
        "event_hash",
        "previous_hash",
        "actor_id",
        "payment_intent_id",
        "problem_statement",
        "answers",
    ):
        require(forbidden not in raw, f"M37.3 filtró dato interno: {forbidden[:40]}")

    print(
        "M37.3 HTTP smoke PASS · "
        f"close_case={case_id} desks={len(desk_ids)} evidence_reviewed=true reminder_resolved=true "
        "close=CERRADO close_idempotent=true client_summary_only=true legal_success=false cross_tenant=hidden "
        f"escalate_case={case2_id} escalate=ESCALADO close_readiness_required=false auto_close=false auto_escalation=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M37.3 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
