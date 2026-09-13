#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, recommended_consumer_intake, register_client, require
from tools.m35_2_http_smoke import demo_answers


PRODUCT = "CO-CD-003"


def main() -> int:
    anonymous = Client()
    recovery_code, decision_id = recommended_consumer_intake(anonymous)

    client = Client()
    register_client(client, "Activation")
    claimed = client.post("/api/m35/intake/claim", {"recovery_code": recovery_code}, expected=201)
    require(claimed.get("decision_id") == decision_id, "M35.3 perdió la decisión de origen")
    require(claimed.get("product_code") == PRODUCT, "M35.3 recibió producto inesperado")
    client.post("/api/m35/fulfillment/prepare", {"product_code": PRODUCT}, expected=200)

    answers = demo_answers()
    diagnosis = client.post(
        "/api/diagnose",
        {"product_code": PRODUCT, "answers": answers, "strict": True},
        expected=200,
    )
    require(not (diagnosis.get("validation_errors") or []), "El formulario de smoke M35.3 no quedó válido")
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
            "title": "Caso consumidor M35.3 activación",
            "result": {**(draft.get("result") or {}), **diagnosis, "service_level": service_level},
        },
        expected=201,
    )

    linked = client.post(
        "/api/m35/commerce/order",
        {
            "product_code": PRODUCT,
            "service_level": service_level,
            "idempotency_key": "m353-order-" + uuid.uuid4().hex,
            "checkout_consent": True,
        },
        expected=201,
    )
    payment = client.post(
        "/api/m35/commerce/payment-intent",
        {
            "link_id": linked["link_id"],
            "provider": "sandbox_card",
            "idempotency_key": "m353-payment-" + uuid.uuid4().hex,
        },
        expected=201,
    )
    intent_id = payment.get("payment_intent", {}).get("id")
    require(intent_id, "M35.3 no obtuvo payment intent")
    simulated = client.post(
        f"/api/payment-intents/{intent_id}/simulate",
        {"outcome": "approved"},
        expected=200,
    )
    require(simulated.get("status") == "succeeded", "El pago sandbox M35.3 no quedó succeeded")

    finalized = client.post(
        "/api/m35/commerce/finalize",
        {"link_id": linked["link_id"], "case_consent": True},
        expected=201,
    )
    case_id = finalized.get("case_id")
    require(case_id and finalized.get("state") == "CASE_CREATED", "M35.3 no recibió un caso M35.2 materializado")
    require(finalized.get("documents_ready") is True, "El caso de activación no tiene documentos listos")

    activation = client.get(f"/api/m35/activation/{case_id}", expected=200)
    require(activation.get("schema") == "legalai_m35_3_case_activation_v1", "Schema de activación inesperado")
    require(activation.get("activation_status") == "ACTIVE", f"El expediente no quedó ACTIVE: {activation}")
    case_view = activation.get("case") or {}
    purchase = activation.get("purchase_confirmation") or {}
    documents = activation.get("documents") or {}
    journey = activation.get("journey") or {}
    next_step = activation.get("next_step") or {}
    require(case_view.get("id") == case_id, "La activación apunta a otro expediente")
    require(case_view.get("product_code") == PRODUCT, "La activación apunta a otro producto")
    require(purchase.get("order_id") == linked.get("order_id"), "La activación apunta a otra orden")
    require(purchase.get("payment_intent_id") == intent_id, "La activación apunta a otro payment intent")
    require(purchase.get("payment_verified") is True, "La activación no verificó el pago")
    require(int(purchase.get("verified_event_count") or 0) >= 2, "La activación no verificó suficientes eventos firmados")
    require(str(purchase.get("receipt_number") or "").startswith("RCPT-SBX-"), "Falta comprobante sandbox válido")
    require(purchase.get("real_charge") is False, "M35.3 presentó el sandbox como cobro real")
    require(int(purchase.get("amount") or -1) == int(linked.get("total") or 0), "El total de activación cambió")
    require(purchase.get("currency") == "COP", "La moneda de activación cambió")
    require(int(documents.get("count") or 0) >= 1 and documents.get("ready") is True, "La activación no acreditó documentos")
    require(journey.get("current_state") not in {None, "INICIADO"}, "El journey M24 no quedó reconciliado")
    require(next_step.get("code"), "La activación no ofrece siguiente paso")

    serialized = json.dumps(activation, ensure_ascii=False)
    for forbidden in (
        "problem_statement",
        "answers",
        "handoff_id",
        "draft_id",
        "intake_id",
        "decision_id",
        "provider_reference",
        "signature",
        "payload_json",
        "idempotency_key",
        "snapshot_sha256",
        "user_id",
    ):
        require(forbidden not in serialized, f"M35.3 filtró campo privado: {forbidden}")

    other = Client()
    register_client(other, "ActivationOther")
    foreign = other.get(f"/api/m35/activation/{case_id}", expected=404)
    require(foreign.get("code") == "CASE_NOT_FOUND", "El endpoint reveló la existencia del expediente a otra cuenta")

    print(
        "M35.3 HTTP smoke PASS · "
        f"case={case_id} order={purchase.get('order_id')} receipt=sandbox-verified "
        f"payment_events={purchase.get('verified_event_count')} documents={documents.get('count')} "
        f"journey={journey.get('current_state')} next={next_step.get('code')} cross_tenant=blocked"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M35.3 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
