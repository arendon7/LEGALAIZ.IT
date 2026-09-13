#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, require
from tools.m36_0_http_smoke import create_activated_case, login_admin


def main() -> int:
    owner = Client()
    case = create_activated_case(owner)
    case_id = case["case_id"]

    admin = login_admin()
    fulfillment = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=201)
    require(fulfillment.get("journey_state") == "EN_REVISION_JURIDICA", "M36.1 necesita intake M36.0 en revisión")
    desk_ids = fulfillment.get("desk_case_ids") or []
    require(len(desk_ids) == case["document_count"] >= 1, "M36.1 necesita cobertura desk completa")

    owner_denied = owner.get("/api/m36/assignments/professionals", expected=403)
    require(owner_denied.get("code") == "PERMISSION_DENIED", "El cliente pudo consultar directorio profesional M36.1")

    directory = admin.get("/api/m36/assignments/professionals", expected=200)
    specialists = directory.get("specialists") or []
    qa_users = directory.get("qa") or []
    require(bool(specialists), "M36.1 no encontró especialistas activos")
    require(bool(qa_users), "M36.1 no encontró responsables QA activos")
    require(directory.get("policy", {}).get("automatic_matching") is False, "M36.1 habilitó matching automático")
    specialist = specialists[0]
    qa = next((item for item in qa_users if item.get("id") != specialist.get("id")), None)
    require(qa is not None, "M36.1 no encontró pareja separada especialista/QA")

    csrf = admin.csrf
    admin.csrf = ""
    csrf_denied = admin.post(
        f"/api/m36/assignments/cases/{case_id}/assign",
        {"specialist_id": specialist["id"], "qa_id": qa["id"]},
        expected=403,
    )
    require(csrf_denied.get("code") == "CSRF_FAILED", "M36.1 aceptó asignación sin CSRF")
    admin.csrf = csrf

    assigned = admin.post(
        f"/api/m36/assignments/cases/{case_id}/assign",
        {"specialist_id": specialist["id"], "qa_id": qa["id"]},
        expected=201,
    )
    require(assigned.get("schema") == "legalai_m36_1_professional_assignment_v1", "Schema M36.1 inesperado")
    require(assigned.get("case_id") == case_id, "M36.1 asignó otro expediente")
    require(assigned.get("state") == "COMPLETE", f"M36.1 no completó saga: {assigned}")
    require(assigned.get("specialist", {}).get("id") == specialist["id"], "M36.1 cambió especialista seleccionado")
    require(assigned.get("qa", {}).get("id") == qa["id"], "M36.1 cambió QA seleccionado")
    require(assigned.get("specialist", {}).get("id") != assigned.get("qa", {}).get("id"), "M36.1 rompió separación de funciones")
    require(int(assigned.get("assigned_desks") or 0) == len(desk_ids), "M36.1 no asignó todos los desks")
    require(int(assigned.get("notification_evaluations") or 0) == len(desk_ids), "M36.1 no evaluó handoff en todos los desks")
    require(assigned.get("all_desks_assigned") is True, "M36.1 presentó cobertura incompleta")
    require(assigned.get("handoff_evaluated") is True, "M36.1 no completó evaluación M32.7")
    governance = assigned.get("governance") or {}
    require(governance.get("manual_selection_required") is True, "M36.1 perdió selección manual")
    require(governance.get("automatic_matching") is False, "M36.1 ejecutó matching automático")
    require(governance.get("automatic_legal_approval") is False, "M36.1 aprobó jurídicamente")
    require(governance.get("automatic_qa_approval") is False, "M36.1 aprobó QA")
    require(governance.get("automatic_release") is False, "M36.1 liberó documento")
    require(governance.get("dual_approval_preserved") is True, "M36.1 debilitó aprobación dual")
    require(governance.get("notification_evaluation_is_not_delivery") is True, "M36.1 confundió notificación con entrega")

    repeated = admin.post(
        f"/api/m36/assignments/cases/{case_id}/assign",
        {"specialist_id": specialist["id"], "qa_id": qa["id"]},
        expected=200,
    )
    require(repeated.get("idempotent") is True, "Retry M36.1 no fue idempotente")
    require(repeated.get("assignment_id") == assigned.get("assignment_id"), "Retry M36.1 cambió assignment id")
    require(repeated.get("updated_at") == assigned.get("updated_at"), "Retry COMPLETE M36.1 mutó timestamp")

    detail = admin.get(f"/api/m36/assignments/cases/{case_id}", expected=200)
    require(detail.get("assignment_id") == assigned.get("assignment_id"), "Detalle M36.1 perdió saga")
    queue = admin.get("/api/m36/assignments", expected=200)
    item = next((row for row in queue.get("items") or [] if row.get("case_id") == case_id), None)
    require(item is not None and item.get("state") == "COMPLETE", "Cola M36.1 no contiene asignación completa")

    # M32.6 debe mostrar la misma pareja en cada documento y M32.7 debe dirigir legal_pending al especialista.
    for desk_id in desk_ids:
        operations = admin.get(f"/api/m32/approval-operations/cases/{desk_id}", expected=200)
        current = operations.get("operations") or {}
        require((current.get("assigned_specialist") or {}).get("id") == specialist["id"], f"Desk {desk_id} perdió especialista")
        require((current.get("assigned_qa") or {}).get("id") == qa["id"], f"Desk {desk_id} perdió QA")
        require(operations.get("workflow_status") == "legal_pending", "Asignación M36.1 adelantó indebidamente aprobación")
        notifications = admin.get(f"/api/m32/notification-center/cases/{desk_id}", expected=200)
        serialized_notifications = json.dumps(notifications, ensure_ascii=False)
        require(specialist["id"] in serialized_notifications, f"M32.7 no dirigió handoff al especialista en {desk_id}")

    raw = json.dumps({"assigned": assigned, "queue": queue}, ensure_ascii=False).lower()
    for forbidden in ("problem_statement", "answers", "receipt_number", "payment_intent_id", "activation_sha256", "document_snapshot_sha256"):
        require(forbidden not in raw, f"M36.1 filtró dato interno: {forbidden}")

    print(
        "M36.1 HTTP smoke PASS · "
        f"case={case_id} assignment={assigned.get('assignment_id')} desks={len(desk_ids)} "
        f"specialist={specialist['id']} qa={qa['id']} state={assigned.get('state')} "
        f"handoff=m32.7-evaluated approvals=manual dual_approval=preserved idempotent={repeated.get('idempotent')}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M36.1 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
