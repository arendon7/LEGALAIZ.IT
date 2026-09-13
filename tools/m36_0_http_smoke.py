#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, recommended_consumer_intake, register_client, require
from tools.m35_2_http_smoke import demo_answers


PRODUCT = "CO-CD-003"


def create_activated_case(client: Client) -> dict:
    anonymous = Client()
    recovery_code, decision_id = recommended_consumer_intake(anonymous)
    registered = register_client(client, "M360Owner")
    claimed = client.post("/api/m35/intake/claim", {"recovery_code": recovery_code}, expected=201)
    require(claimed.get("decision_id") == decision_id, "M36.0 perdió la decisión M34")
    require(claimed.get("product_code") == PRODUCT, "M36.0 recibió producto inesperado")
    client.post("/api/m35/fulfillment/prepare", {"product_code": PRODUCT}, expected=200)

    answers = demo_answers()
    diagnosis = client.post(
        "/api/diagnose",
        {"product_code": PRODUCT, "answers": answers, "strict": True},
        expected=200,
    )
    require(not (diagnosis.get("validation_errors") or []), "El formulario M36.0 no quedó válido")
    review_required = bool(
        diagnosis.get("risk") == "red"
        or diagnosis.get("review_required")
        or diagnosis.get("service_mode") == "blocked"
    )
    service_level = "solucion_revisada" if review_required else "documento_personalizado"
    draft = client.get(f"/api/drafts/product/{PRODUCT}", expected=200)
    client.post(
        "/api/drafts",
        {
            "product_code": PRODUCT,
            "answers": answers,
            "current_step": 999,
            "title": "Caso consumidor M36.0 fulfillment",
            "result": {**(draft.get("result") or {}), **diagnosis, "service_level": service_level},
        },
        expected=201,
    )
    linked = client.post(
        "/api/m35/commerce/order",
        {
            "product_code": PRODUCT,
            "service_level": service_level,
            "idempotency_key": "m360-order-" + uuid.uuid4().hex,
            "checkout_consent": True,
        },
        expected=201,
    )
    payment = client.post(
        "/api/m35/commerce/payment-intent",
        {
            "link_id": linked["link_id"],
            "provider": "sandbox_card",
            "idempotency_key": "m360-payment-" + uuid.uuid4().hex,
        },
        expected=201,
    )
    intent_id = payment.get("payment_intent", {}).get("id")
    require(intent_id, "M36.0 no obtuvo payment intent")
    paid = client.post(
        f"/api/payment-intents/{intent_id}/simulate",
        {"outcome": "approved"},
        expected=200,
    )
    require(paid.get("status") == "succeeded", "El pago sandbox M36.0 no quedó aprobado")
    finalized = client.post(
        "/api/m35/commerce/finalize",
        {"link_id": linked["link_id"], "case_consent": True},
        expected=201,
    )
    case_id = finalized.get("case_id")
    require(case_id and finalized.get("state") == "CASE_CREATED", "M36.0 necesita expediente M35.2 materializado")
    activation = client.get(f"/api/m35/activation/{case_id}", expected=200)
    require(activation.get("activation_status") == "ACTIVE", "M36.0 necesita M35.3 ACTIVE")
    return {
        "case_id": case_id,
        "owner": registered.get("user", {}).get("id"),
        "order_id": linked.get("order_id"),
        "document_count": int((activation.get("documents") or {}).get("count") or 0),
    }


def login_admin() -> Client:
    password = str(os.environ.get("LEGAL_DEMO_PASSWORD") or "")
    require(bool(password), "El smoke M36.0 exige una clave demo efímera inyectada por CI")
    admin = Client()
    logged = admin.post(
        "/api/auth/login",
        {
            "email": "ana@demo.legalaiz.it",
            "password": password,
            "mfa_code": "",
        },
        expected=200,
    )
    admin.csrf = str(logged.get("csrf_token") or logged.get("csrf") or "")
    require(bool(admin.csrf), "Login admin M36.0 no devolvió CSRF")
    require(logged.get("user", {}).get("role") == "admin", "M36.0 no autenticó rol admin")
    require(not logged.get("mfa_enrollment_required"), "El entorno CI M36.0 no debe exigir MFA demo")
    return admin


def main() -> int:
    owner = Client()
    case = create_activated_case(owner)
    case_id = case["case_id"]

    owner_denied = owner.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=403)
    require(owner_denied.get("code") in {"ROLE_FORBIDDEN", "FORBIDDEN", "AUTH_FORBIDDEN"} or "rol" in str(owner_denied.get("error") or "").lower(), "El cliente no fue bloqueado del intake M36.0")

    admin = login_admin()
    csrf = admin.csrf
    admin.csrf = ""
    csrf_denied = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=403)
    require(csrf_denied.get("code") == "CSRF_FAILED", "M36.0 aceptó activación admin sin CSRF")
    admin.csrf = csrf

    activated = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=201)
    require(activated.get("schema") == "legalai_m36_0_fulfillment_intake_v1", "Schema M36.0 inesperado")
    require(activated.get("case_id") == case_id, "M36.0 activó otro expediente")
    require(activated.get("order_id") == case["order_id"], "M36.0 perdió la orden M35")
    require(activated.get("journey_state") == "EN_REVISION_JURIDICA", f"M36.0 no avanzó M24 a revisión: {activated}")
    require(int(activated.get("document_count") or 0) == case["document_count"] >= 1, "M36.0 no cubrió todos los documentos")
    require(len(activated.get("desk_case_ids") or []) == case["document_count"], "M36.0 no creó una mesa por documento")
    require(len(set(activated.get("desk_case_ids") or [])) == case["document_count"], "M36.0 duplicó desk_case_id")
    governance = activated.get("governance") or {}
    require(governance.get("automatic_assignment") is False, "M36.0 asignó automáticamente")
    require(governance.get("automatic_legal_approval") is False, "M36.0 aprobó jurídicamente")
    require(governance.get("automatic_qa_approval") is False, "M36.0 aprobó QA")
    require(governance.get("automatic_release") is False, "M36.0 liberó automáticamente")
    require(governance.get("dual_approval_preserved") is True, "M36.0 debilitó aprobación dual")

    repeated = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=200)
    require(repeated.get("idempotent") is True, "Retry M36.0 no fue idempotente")
    require(repeated.get("fulfillment_intake_id") == activated.get("fulfillment_intake_id"), "Retry M36.0 cambió intake")
    require(repeated.get("desk_case_ids") == activated.get("desk_case_ids"), "Retry M36.0 cambió mesas")

    detail = admin.get(f"/api/m36/fulfillment/cases/{case_id}", expected=200)
    require(detail.get("fulfillment_intake_id") == activated.get("fulfillment_intake_id"), "Detalle M36.0 perdió intake")
    queue = admin.get("/api/m36/fulfillment", expected=200)
    item = next((row for row in queue.get("items") or [] if row.get("case_id") == case_id), None)
    require(item is not None, "La cola M36.0 no contiene el expediente activado")
    require(item.get("journey_state") == "EN_REVISION_JURIDICA", "La cola M36.0 perdió estado M24")
    require(int(item.get("document_count") or 0) == case["document_count"], "La cola M36.0 perdió cobertura documental")
    require(int(item.get("active_alerts") or 0) >= case["document_count"] * 2, "M36.0 debería reflejar responsables legal/QA sin asignar")

    raw = json.dumps({"activated": activated, "queue": queue}, ensure_ascii=False)
    for forbidden in (
        "owner_id",
        "activation_sha256",
        "document_snapshot_sha256",
        "receipt_number",
        "payment_intent_id",
        "problem_statement",
        "answers",
    ):
        require(forbidden not in raw, f"M36.0 filtró dato interno: {forbidden}")

    print(
        "M36.0 HTTP smoke PASS · "
        f"case={case_id} intake={activated.get('fulfillment_intake_id')} documents={case['document_count']} "
        f"desks={len(activated.get('desk_case_ids') or [])} journey={activated.get('journey_state')} "
        f"alerts={item.get('active_alerts')} assignment=manual dual_approval=preserved idempotent={repeated.get('idempotent')}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M36.0 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
