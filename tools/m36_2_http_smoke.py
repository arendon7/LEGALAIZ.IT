#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, require
from tools.m36_0_http_smoke import create_activated_case, login_admin


SPECIALIST_EMAILS = {
    "USR-LAB": "maria@demo.legalaiz.it",
    "USR-COMM": "carlos@demo.legalaiz.it",
    "USR-TRANSIT": "laura@demo.legalaiz.it",
}


def login_specialist(user_id: str) -> Client:
    email = SPECIALIST_EMAILS.get(user_id)
    require(bool(email), f"M36.2 no conoce la cuenta demo del especialista {user_id}")
    password = str(os.environ.get("LEGAL_DEMO_PASSWORD") or "")
    require(bool(password), "M36.2 exige la clave demo efímera inyectada por CI")
    client = Client()
    logged = client.post(
        "/api/auth/login",
        {"email": email, "password": password, "mfa_code": ""},
        expected=200,
    )
    client.csrf = str(logged.get("csrf_token") or logged.get("csrf") or "")
    require(bool(client.csrf), "Login especialista M36.2 no devolvió CSRF")
    require(logged.get("user", {}).get("id") == user_id, "M36.2 autenticó otro especialista")
    require(logged.get("user", {}).get("role") == "specialist", "M36.2 no autenticó rol specialist")
    require(not logged.get("mfa_enrollment_required"), "El entorno CI M36.2 no debe exigir MFA demo")
    return client


def current_revision(client: Client, desk_id: str) -> tuple[str, str]:
    detail = client.get(f"/api/m32/approval-desk/cases/{desk_id}", expected=200)
    current_id = str((detail.get("case") or {}).get("current_revision_id") or "")
    current = next(
        (item for item in detail.get("revisions") or [] if str(item.get("revision_id") or "") == current_id),
        None,
    )
    require(bool(current_id and current), f"M36.2 no encontró revisión vigente en {desk_id}")
    digest = str(current.get("sha256") or "")
    require(len(digest) == 64, f"M36.2 recibió SHA inválido en {desk_id}")
    return current_id, digest


def approve(client: Client, desk_id: str, approval_type: str) -> None:
    revision_id, digest = current_revision(client, desk_id)
    result = client.post(
        f"/api/m32/approval-desk/cases/{desk_id}/approvals",
        {
            "revision_id": revision_id,
            "approval_type": approval_type,
            "decision": "approve",
            "comment": f"Aprobación {approval_type} sintética M36.2 CI sobre hash vigente.",
            "expected_sha256": digest,
        },
        expected=201,
    )
    require(result.get("decision") == "approve", f"M36.2 no registró aprobación {approval_type} en {desk_id}")
    require(result.get("revision_id") == revision_id, f"M36.2 aprobó otra revisión en {desk_id}")
    require(result.get("sha256") == digest, f"M36.2 aprobó otro hash en {desk_id}")


def release(admin: Client, desk_id: str) -> None:
    revision_id, digest = current_revision(admin, desk_id)
    result = admin.post(
        f"/api/m32/approval-desk/cases/{desk_id}/release",
        {"revision_id": revision_id, "expected_sha256": digest},
        expected=201,
    )
    require(result.get("revision_id") == revision_id, f"M36.2 liberó otra revisión en {desk_id}")
    require(result.get("sha256") == digest, f"M36.2 liberó otro hash en {desk_id}")
    require(result.get("status") == "released_exact_hash", f"M36.2 no obtuvo liberación exacta en {desk_id}")


def main() -> int:
    owner = Client()
    case = create_activated_case(owner)
    case_id = case["case_id"]

    admin = login_admin()
    fulfillment = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=201)
    desk_ids = fulfillment.get("desk_case_ids") or []
    require(fulfillment.get("journey_state") == "EN_REVISION_JURIDICA", "M36.2 necesita M36.0 en revisión jurídica")
    require(len(desk_ids) == case["document_count"] >= 1, "M36.2 necesita cobertura documental completa")

    directory = admin.get("/api/m36/assignments/professionals", expected=200)
    specialists = directory.get("specialists") or []
    qa_users = directory.get("qa") or []
    specialist = next((item for item in specialists if item.get("id") == "USR-COMM"), None)
    if specialist is None:
        specialist = next((item for item in specialists if item.get("id") in SPECIALIST_EMAILS), None)
    qa = next((item for item in qa_users if item.get("id") == "USR-ADMIN"), None)
    require(specialist is not None, "M36.2 no encontró especialista demo autenticable")
    require(qa is not None, "M36.2 necesita QA/admin demo independiente")
    require(specialist.get("id") != qa.get("id"), "M36.2 requiere separación especialista/QA")

    assignment = admin.post(
        f"/api/m36/assignments/cases/{case_id}/assign",
        {"specialist_id": specialist["id"], "qa_id": qa["id"]},
        expected=201,
    )
    require(assignment.get("state") == "COMPLETE", "M36.2 necesita asignación M36.1 completa")
    specialist_client = login_specialist(str(specialist["id"]))

    denied = owner.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=403)
    require(denied.get("code") == "PERMISSION_DENIED", "Cliente pudo leer reconciliación M36.2")

    initial = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
    require(initial.get("schema") == "legalai_m36_2_review_assessment_v1", "Schema M36.2 inesperado")
    require(initial.get("m24_current_state") == "EN_REVISION_JURIDICA", "M36.2 perdió estado M24 inicial")
    require(initial.get("aggregate_review_state") == "LEGAL_REVIEW", "M36.2 inventó aprobación inicial")
    require(initial.get("proposed_path") == [], "M36.2 quiso adelantar M24 sin aprobaciones")
    require(initial.get("legal_approval_complete") is False, "M36.2 presentó aprobación jurídica inexistente")
    require(initial.get("qa_approval_complete") is False, "M36.2 presentó aprobación QA inexistente")

    for index, desk_id in enumerate(desk_ids):
        approve(specialist_client, desk_id, "legal")
        if index == 0 and len(desk_ids) > 1:
            partial = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
            require(partial.get("legal_approval_complete") is False, "M36.2 aceptó aprobación jurídica parcial")
            require(partial.get("proposed_path") == [], "M36.2 adelantó M24 con sólo un documento aprobado")

    legal_ready = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
    require(legal_ready.get("aggregate_review_state") == "LEGAL_APPROVED", "M36.2 no agregó aprobaciones jurídicas completas")
    require(legal_ready.get("legal_approval_complete") is True, "M36.2 no acreditó legal completo")
    require(legal_ready.get("qa_approval_complete") is False, "M36.2 adelantó QA")
    require(
        legal_ready.get("proposed_path") == ["APROBADO_JURIDICAMENTE", "EN_QA"],
        f"Ruta legal M36.2 inesperada: {legal_ready.get('proposed_path')}",
    )

    csrf = admin.csrf
    admin.csrf = ""
    csrf_denied = admin.post(f"/api/m36/review-lifecycle/cases/{case_id}/reconcile", {}, expected=403)
    require(csrf_denied.get("code") == "CSRF_FAILED", "M36.2 aceptó reconciliación sin CSRF")
    admin.csrf = csrf

    legal_reconciled = admin.post(
        f"/api/m36/review-lifecycle/cases/{case_id}/reconcile",
        {},
        expected=201,
    )
    require(legal_reconciled.get("reconciled") is True, "M36.2 no reconcilió aprobación jurídica")
    require(legal_reconciled.get("m24_current_state") == "EN_QA", "M36.2 no llevó M24 a EN_QA")
    require(
        [item.get("to") for item in legal_reconciled.get("applied_transitions") or []]
        == ["APROBADO_JURIDICAMENTE", "EN_QA"],
        "M36.2 aplicó hitos jurídicos inesperados",
    )

    legal_retry = admin.post(f"/api/m36/review-lifecycle/cases/{case_id}/reconcile", {}, expected=200)
    require(legal_retry.get("idempotent") is True, "Retry legal M36.2 no fue idempotente")
    require(legal_retry.get("applied_transitions") == [], "Retry legal M36.2 duplicó transiciones")

    for index, desk_id in enumerate(desk_ids):
        approve(admin, desk_id, "qa")
        if index == 0 and len(desk_ids) > 1:
            partial_qa = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
            require(partial_qa.get("qa_approval_complete") is False, "M36.2 aceptó QA parcial")
            require(partial_qa.get("m24_current_state") == "EN_QA", "M36.2 movió M24 durante QA parcial")

    qa_ready = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
    require(qa_ready.get("aggregate_review_state") == "QA_APPROVED", "M36.2 no agregó QA completo")
    require(qa_ready.get("qa_approval_complete") is True, "M36.2 no acreditó QA completo")
    require(qa_ready.get("proposed_path") == ["APROBADO_QA"], "M36.2 propuso una ruta QA inesperada")

    qa_reconciled = admin.post(f"/api/m36/review-lifecycle/cases/{case_id}/reconcile", {}, expected=201)
    require(qa_reconciled.get("m24_current_state") == "APROBADO_QA", "M36.2 no llevó M24 a APROBADO_QA")
    require(
        [item.get("to") for item in qa_reconciled.get("applied_transitions") or []] == ["APROBADO_QA"],
        "M36.2 duplicó o inventó hitos QA",
    )

    history = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}/history", expected=200)
    require(history.get("audit", {}).get("valid") is True, "Cadena M36.2 inválida")
    require(int(history.get("audit", {}).get("events") or 0) == 3, "M36.2 debe registrar exactamente tres hitos reconciliados")
    require([item.get("sequence") for item in history.get("events") or []] == [1, 2, 3], "Secuencia M36.2 no es contigua")
    require((history.get("events") or [])[0].get("legal_approver_id") == specialist["id"], "M36.2 perdió aprobador jurídico humano")
    require((history.get("events") or [])[-1].get("qa_approver_id") == qa["id"], "M36.2 perdió aprobador QA humano")

    for desk_id in desk_ids:
        release(admin, desk_id)

    released = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
    require(released.get("release_complete") is True, "M36.2 no detectó liberación completa")
    require(released.get("delivery_gate_ready") is True, "M36.2 no abrió gate de entrega tras liberación completa")
    require(released.get("m24_current_state") == "APROBADO_QA", "M36.2 registró entrega automática")
    require(released.get("proposed_path") == [], "M36.2 intentó convertir liberación en entrega")
    governance = released.get("governance") or {}
    require(governance.get("derived_state_is_not_new_legal_approval") is True, "M36.2 confundió reconciliación con aprobación")
    require(governance.get("system_actor_does_not_impersonate_approvers") is True, "M36.2 perdió atribución de aprobadores")
    require(governance.get("dual_approval_preserved") is True, "M36.2 debilitó aprobación dual")
    require(governance.get("automatic_delivery") is False, "M36.2 entregó automáticamente")
    require(governance.get("delivery_requires_separate_gate") is True, "M36.2 eliminó gate de entrega")

    raw = json.dumps({"assessment": released, "history": history}, ensure_ascii=False).lower()
    for forbidden in (
        "revision_sha256",
        "record_hash",
        "evidence_fingerprint",
        "evidence_json",
        "problem_statement",
        "answers",
        "receipt_number",
        "payment_intent_id",
        "activation_sha256",
    ):
        require(forbidden not in raw, f"M36.2 filtró dato interno: {forbidden}")

    print(
        "M36.2 HTTP smoke PASS · "
        f"case={case_id} desks={len(desk_ids)} legal={specialist['id']} qa={qa['id']} "
        f"m24={released.get('m24_current_state')} reconciliation_events={history.get('audit', {}).get('events')} "
        "release=complete delivery_gate=ready automatic_delivery=false dual_approval=preserved"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M36.2 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
