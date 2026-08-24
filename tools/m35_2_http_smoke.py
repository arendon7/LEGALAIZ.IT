#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, recommended_consumer_intake, register_client, require


PRODUCT = "CO-CD-003"


def demo_answers() -> dict:
    script = r"""
import fs from 'node:fs';
import { buildDemoAnswers } from './app/modules/demo_form_values_m32.js';
const interviews = JSON.parse(fs.readFileSync('./data/interviews.json', 'utf8'));
const questions = interviews['CO-CD-003']?.questions || [];
console.log(JSON.stringify(buildDemoAnswers(questions)));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    answers = json.loads(completed.stdout.strip() or "{}")
    require(isinstance(answers, dict) and len(answers) >= 10, "No se generaron respuestas demo completas para CO-CD-003")
    return answers


def case_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("cases", "items", "results"):
            if isinstance(value.get(key), list):
                return value[key]
    return []


def main() -> int:
    anonymous = Client()
    recovery_code, decision_id = recommended_consumer_intake(anonymous)

    client = Client()
    register_client(client, "Commerce")
    claimed = client.post("/api/m35/intake/claim", {"recovery_code": recovery_code}, expected=201)
    require(claimed.get("decision_id") == decision_id, "M35.2 perdió la decisión M34.4 durante el claim")
    require(claimed.get("product_code") == PRODUCT, "Producto inesperado en el claim M35.2")

    prepared = client.post("/api/m35/fulfillment/prepare", {"product_code": PRODUCT}, expected=200)
    require(prepared.get("draft_id") == claimed.get("draft_id"), "M35.1/M35.2 no conservaron el mismo draft")

    answers = demo_answers()
    diagnosis = client.post(
        "/api/diagnose",
        {"product_code": PRODUCT, "answers": answers, "strict": True},
        expected=200,
    )
    require(not (diagnosis.get("validation_errors") or []), f"El formulario demo CO-CD-003 no quedó válido: {diagnosis.get('validation_errors')}")
    review_required = bool(
        diagnosis.get("risk") == "red"
        or diagnosis.get("review_required")
        or diagnosis.get("service_mode") == "blocked"
    )
    service_level = "solucion_revisada" if review_required else "documento_personalizado"

    draft = client.get(f"/api/drafts/product/{PRODUCT}", expected=200)
    saved = client.post(
        "/api/drafts",
        {
            "product_code": PRODUCT,
            "answers": answers,
            "current_step": 999,
            "title": "Caso consumidor M35.2 trazable",
            "result": {**(draft.get("result") or {}), **diagnosis, "service_level": service_level},
        },
        expected=201,
    )
    require(saved.get("answers") == answers, "El servidor no conservó las respuestas completas antes del checkout")

    # Generic order endpoint must not bypass an active M35 handoff.
    generic_order = client.post(
        "/api/checkout/orders",
        {
            "product_code": PRODUCT,
            "result": diagnosis,
            "service_level": service_level,
            "review_selected": review_required,
        },
        expected=400,
    )
    require("checkout trazable m35.2" in str(generic_order.get("error") or "").lower(), "El checkout genérico no quedó bloqueado por M35.2")

    order_key = "m352-order-" + uuid.uuid4().hex
    linked = client.post(
        "/api/m35/commerce/order",
        {
            "product_code": PRODUCT,
            "service_level": service_level,
            "idempotency_key": order_key,
            "checkout_consent": True,
        },
        expected=201,
    )
    require(linked.get("order_id"), "M35.2 no creó order_id")
    require(linked.get("link_id"), "M35.2 no creó link_id")
    require(linked.get("state") == "ORDER_CREATED", "Estado inicial de commerce inesperado")
    repeated_order = client.post(
        "/api/m35/commerce/order",
        {
            "product_code": PRODUCT,
            "service_level": service_level,
            "idempotency_key": order_key,
            "checkout_consent": True,
        },
        expected=200,
    )
    require(repeated_order.get("idempotent") is True, "La orden M35.2 no fue idempotente")
    require(repeated_order.get("order_id") == linked.get("order_id"), "La idempotencia creó una segunda orden")

    before_payment = client.get("/api/self-service", expected=200)
    require(len(before_payment.get("orders") or []) == 1, "M35.2 creó más de una orden antes del pago")
    require(case_list(client.get("/api/cases", expected=200)) == [], "Existía un caso antes del pago M35.2")

    legacy_payment = client.post(
        f"/api/checkout/orders/{linked['order_id']}/pay",
        {"payment_method": "Tarjeta de prueba"},
        expected=400,
    )
    require("pago sandbox trazable m35.2" in str(legacy_payment.get("error") or "").lower(), "El pago legacy no quedó bloqueado")

    payment_key = "m352-payment-" + uuid.uuid4().hex
    payment = client.post(
        "/api/m35/commerce/payment-intent",
        {
            "link_id": linked["link_id"],
            "provider": "sandbox_card",
            "idempotency_key": payment_key,
        },
        expected=201,
    )
    intent_id = payment.get("payment_intent", {}).get("id")
    require(intent_id, "No se creó payment intent M35.2")
    payment_repeat = client.post(
        "/api/m35/commerce/payment-intent",
        {
            "link_id": linked["link_id"],
            "provider": "sandbox_card",
            "idempotency_key": payment_key,
        },
        expected=200,
    )
    require(payment_repeat.get("idempotent") is True, "El payment intent M35.2 no fue idempotente")
    require(payment_repeat.get("payment_intent", {}).get("id") == intent_id, "La idempotencia creó otro payment intent")

    simulated = client.post(
        f"/api/payment-intents/{intent_id}/simulate",
        {"outcome": "approved"},
        expected=200,
    )
    require(simulated.get("status") == "succeeded", "El pago sandbox M35.2 no quedó succeeded")
    paid_order = client.get(f"/api/checkout/orders/{linked['order_id']}", expected=200)
    require(paid_order.get("status") == "Pagado (sandbox)", "La orden no quedó Pagado (sandbox)")
    require(not case_list(client.get("/api/cases", expected=200)), "El pago creó automáticamente un caso, violando el segundo consentimiento")

    # The historical generic case endpoint must fail closed as well.
    legacy_case = client.post(
        "/api/cases",
        {
            "product_code": PRODUCT,
            "answers": answers,
            "title": "Intento de bypass M35.2",
            "order_id": linked["order_id"],
        },
        expected=409,
    )
    require("checkout trazable" in str(legacy_case.get("error") or "").lower(), "El endpoint genérico de casos no quedó bloqueado")
    require(not case_list(client.get("/api/cases", expected=200)), "El intento legacy creó un caso")

    finalized = client.post(
        "/api/m35/commerce/finalize",
        {"link_id": linked["link_id"], "case_consent": True},
        expected=201,
    )
    require(finalized.get("case_id"), "M35.2 no devolvió case_id")
    require(finalized.get("state") == "CASE_CREATED", f"M35.2 no cerró materialización documental: {finalized}")
    require(finalized.get("documents_ready") is True, "El caso quedó sin documentos en el escenario canónico")
    require(int(finalized.get("documents_count") or 0) >= 1, "No se materializó ningún documento")

    repeat_final = client.post(
        "/api/m35/commerce/finalize",
        {"link_id": linked["link_id"], "case_consent": True},
        expected=200,
    )
    require(repeat_final.get("idempotent") is True, "Finalize repetido no fue idempotente")
    require(repeat_final.get("case_id") == finalized.get("case_id"), "Finalize repetido creó otro expediente")

    completed_order = client.get(f"/api/checkout/orders/{linked['order_id']}", expected=200)
    require(completed_order.get("status") == "Completada", "La orden no quedó completada tras el expediente")
    require(completed_order.get("case_id") == finalized.get("case_id"), "La orden no apunta al expediente exacto")
    client.get(f"/api/drafts/product/{PRODUCT}", expected=404)

    cases = case_list(client.get("/api/cases", expected=200))
    matching = [row for row in cases if row.get("id") == finalized.get("case_id") or row.get("case_id") == finalized.get("case_id")]
    require(len(matching) == 1, f"Se esperaba exactamente un expediente M35.2 y se encontraron {len(matching)}")
    after = client.get("/api/self-service", expected=200)
    require(len(after.get("orders") or []) == 1, "M35.2 terminó con más de una orden")

    context = client.get(f"/api/m35/commerce/context/{PRODUCT}", expected=200)
    require(context.get("linked") is True, "El contexto final perdió el handoff")
    require(context.get("handoff_state") == "CASE_CREATED", "El handoff final no quedó CASE_CREATED")
    require(context.get("commerce", {}).get("case_id") == finalized.get("case_id"), "El ledger final no conserva el expediente exacto")
    require(context.get("commerce", {}).get("state") == "CASE_CREATED", "El ledger final no quedó materializado")
    unrelated = client.get("/api/m35/commerce/context/CO-AR-001", expected=200)
    require(unrelated.get("linked") is False, "M35.2 vinculó un producto no reclamado")

    print(
        "M35.2 HTTP smoke PASS · "
        f"service={service_level} order={linked['order_id']} signed_payment=verified "
        f"payment_auto_case=blocked legacy=blocked case={finalized['case_id']} "
        f"documents={finalized.get('documents_count')} idempotent=True checkout_orders=1 cases=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M35.2 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
