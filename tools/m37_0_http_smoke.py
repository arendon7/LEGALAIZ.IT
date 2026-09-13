#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, register_client, require
from tools.m36_0_http_smoke import login_admin
from tools.m36_3_http_smoke import CONFIRMATION as DELIVERY_CONFIRMATION, prepare_reviewed_released_case


START_CONFIRMATION = "INICIAR SEGUIMIENTO"


def main() -> int:
    owner = Client()
    admin = login_admin()
    case, desk_ids, _ = prepare_reviewed_released_case(owner, admin)
    case_id = case["case_id"]

    delivered = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": DELIVERY_CONFIRMATION},
        expected=201,
    )
    require(delivered.get("state") == "DELIVERED_IN_APP", "M37.0 necesita una entrega M36.3 real")

    before = owner.get(f"/api/m37/follow-up/cases/{case_id}", expected=200)
    require(before.get("schema") == "legalai_m37_0_post_delivery_followup_v1", "Schema M37.0 inesperado")
    require(before.get("lifecycle") == "AVAILABLE", "M37.0 debería estar disponible antes de iniciar")
    require(before.get("started") is False, "GET M37.0 inició seguimiento automáticamente")
    require(before.get("m24_current_state") == "ENTREGADO", "Lectura M37.0 mutó M24")
    require(int((before.get("metrics") or {}).get("tasks") or 0) >= 1, "M37.0 no reutilizó tareas M24")
    require((before.get("close_readiness") or {}).get("automatic_close") is False, "M37.0 habilitó cierre automático")
    for task in before.get("tasks") or []:
        timing = task.get("timing") or {}
        require(timing.get("is_legal_deadline") is False, "M37.0 presentó checkpoint como término legal")
        require(timing.get("legal_deadline_verified") is False, "M37.0 declaró término jurídico no verificado")

    owner_queue = owner.get("/api/m37/follow-up", expected=403)
    require(owner_queue.get("code") == "PERMISSION_DENIED", "Cliente accedió a cola global M37.0")

    csrf = owner.csrf
    owner.csrf = ""
    denied_csrf = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": START_CONFIRMATION},
        expected=403,
    )
    require(denied_csrf.get("code") == "CSRF_FAILED", "M37.0 aceptó inicio sin CSRF")
    owner.csrf = csrf

    wrong = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": "INICIAR"},
        expected=422,
    )
    require(wrong.get("code") == "FOLLOWUP_CONFIRMATION_REQUIRED", "M37.0 aceptó confirmación débil")

    started = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": START_CONFIRMATION},
        expected=201,
    )
    require(started.get("lifecycle") == "ACTIVE", "M37.0 no activó seguimiento")
    require(started.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.0 no reconcilió M24")
    require(started.get("idempotent") is False, "Primer inicio M37.0 apareció idempotente")
    require((started.get("audit") or {}).get("valid") is True, "M37.0 no conserva cadena válida")
    require((started.get("audit") or {}).get("events") == 1, "M37.0 debería registrar un evento de inicio")

    repeated = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": START_CONFIRMATION},
        expected=200,
    )
    require(repeated.get("idempotent") is True, "Retry M37.0 no fue idempotente")
    require((repeated.get("audit") or {}).get("events") == 1, "Retry M37.0 duplicó evento de inicio")

    first_task = started["tasks"][0]
    bypass = owner.post(
        f"/api/m24/case-journeys/{case_id}/follow-up",
        {
            "follow_up_id": first_task["follow_up_id"],
            "status": "completed",
            "note": "Intento CI de omitir la compuerta de seguimiento controlado M37.0.",
        },
        expected=409,
    )
    require(bypass.get("code") == "M37_CONTROLLED_FOLLOWUP_REQUIRED", "M24 permitió bypass de M37.0")

    note = "El titular reporta esta actividad como realizada; la evidencia jurídica sigue pendiente de revisión."
    one_done = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/tasks/{first_task['follow_up_id']}",
        {"status": "completed", "note": note},
        expected=200,
    )
    updated_first = next(item for item in one_done.get("tasks") or [] if item.get("follow_up_id") == first_task["follow_up_id"])
    require(updated_first.get("status") == "completed", "M37.0 no registró tarea completada")
    completion = updated_first.get("completion") or {}
    require(completion.get("class") == "SELF_REPORTED", "M37.0 elevó indebidamente reporte del cliente")
    require(completion.get("evidence_verified") is False, "M37.0 inventó verificación de evidencia")
    require(completion.get("legal_effect_verified") is False, "M37.0 inventó efecto jurídico")

    retry_task = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/tasks/{first_task['follow_up_id']}",
        {"status": "completed", "note": note},
        expected=200,
    )
    require(retry_task.get("idempotent") is True, "Retry de tarea M37.0 no fue idempotente")
    require((retry_task.get("audit") or {}).get("events") == (one_done.get("audit") or {}).get("events"), "Retry duplicó evento M37.0")

    current = retry_task
    for index, task in enumerate(current.get("tasks") or [], 1):
        if task.get("status") == "completed":
            continue
        current = owner.post(
            f"/api/m37/follow-up/cases/{case_id}/tasks/{task['follow_up_id']}",
            {
                "status": "completed",
                "note": f"Actividad operacional {index} reportada como completada por el cliente para el smoke M37.0.",
            },
            expected=200,
        )

    require((current.get("close_readiness") or {}).get("ready") is True, "M37.0 no detectó readiness al completar tareas")
    require((current.get("close_readiness") or {}).get("automatic_close") is False, "M37.0 cerró automáticamente")
    require(current.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.0 convirtió readiness en CERRADO")
    require((current.get("governance") or {}).get("automatic_escalation") is False, "M37.0 escaló automáticamente")
    require((current.get("governance") or {}).get("legal_deadline_calculation") is False, "M37.0 calculó término legal")

    other = Client()
    register_client(other, "M370Other")
    hidden = other.get(f"/api/m37/follow-up/cases/{case_id}", expected=404)
    require(hidden.get("code") == "FOLLOWUP_NOT_AVAILABLE", "M37.0 reveló seguimiento a otro cliente")

    queue = admin.get("/api/m37/follow-up", expected=200)
    item = next((row for row in queue.get("items") or [] if row.get("case_id") == case_id), None)
    require(item is not None, "Cola M37.0 perdió el expediente")
    require(item.get("lifecycle") == "ACTIVE", "Cola M37.0 muestra lifecycle incorrecto")
    require(item.get("close_ready") is True, "Cola M37.0 perdió close readiness")

    raw = json.dumps({"started": started, "current": current, "queue_item": item}, ensure_ascii=False).lower()
    for forbidden in (
        "task_ids_json",
        "prepared_by",
        "started_by",
        "m24_transition_id",
        "previous_hash",
        "event_hash",
        "owner_id",
        "specialist_id",
        "payment_intent_id",
        "package_path",
        "release_record_hash",
        note.lower(),
    ):
        require(forbidden not in raw, f"M37.0 filtró dato interno/sensible: {forbidden[:40]}")

    print(
        "M37.0 HTTP smoke PASS · "
        f"case={case_id} desks={len(desk_ids)} tasks={(current.get('metrics') or {}).get('tasks')} "
        f"completed={(current.get('metrics') or {}).get('completed')} lifecycle={current.get('lifecycle')} "
        f"m24={current.get('m24_current_state')} close_ready=true auto_close=false "
        "legal_deadline=false evidence_verified=false cross_tenant=hidden idempotent=true"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M37.0 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
