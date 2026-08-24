#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, recommended_consumer_intake, register_client, require


def main() -> int:
    anonymous = Client()
    recovery_code, decision_id = recommended_consumer_intake(anonymous)

    account = Client()
    register_client(account, "Bridge")
    claimed = account.post("/api/m35/intake/claim", {"recovery_code": recovery_code}, expected=201)
    require(claimed.get("decision_id") == decision_id, "El claim perdió la decisión M34.4")
    require(claimed.get("product_code") == "CO-CD-003", "Producto inesperado para M35.1")

    before = account.get("/api/self-service", expected=200)
    require((before.get("orders") or []) == [], "Una cuenta nueva no debería iniciar con órdenes")

    prepared = account.post(
        "/api/m35/fulfillment/prepare",
        {"product_code": "CO-CD-003"},
        expected=200,
    )
    require(prepared.get("draft_id") == claimed.get("draft_id"), "M35.1 cambió el draft del handoff")
    require(prepared.get("eligible_prefill_count", 0) >= 1, "El escenario consumidor no reutilizó ningún dato seguro")
    require(prepared.get("applied_prefill_count", 0) >= 1, "La primera preparación no aplicó prefill")
    require(prepared.get("offer", {}).get("pricing_status") == "sandbox_reference_not_commercially_approved", "La oferta perdió su estado sandbox")
    levels = {row.get("id"): row for row in prepared.get("offer", {}).get("service_levels", [])}
    require("documento_personalizado" in levels, "Falta nivel documental canónico")
    require("solucion_revisada" in levels, "Falta nivel revisado canónico")

    answers = prepared.get("answers") or {}
    require("purchase_date" in answers or "request_mode" in answers, "No apareció ninguno de los mappings de consumo esperados")
    prohibited = {"provider_name", "email", "phone", "address", "requester_name", "requester_id"}
    require(not (set(answers) & prohibited), f"M35.1 prellenó identificadores prohibidos: {set(answers) & prohibited}")

    draft = account.get("/api/drafts/product/CO-CD-003", expected=200)
    require(draft.get("answers") == answers, "El draft servidor no coincide con la preparación")
    result = draft.get("result") or {}
    require(result.get("triage_reuse_status") == "SAFE_MAPPING_APPLIED", "Draft sin estado de mapping M35.1")
    require(result.get("commercial_offer", {}).get("pricing_status") == "sandbox_reference_not_commercially_approved", "Draft sin snapshot de oferta sandbox")
    serialized = json.dumps(draft, ensure_ascii=False).lower()
    require("compré un producto defectuoso" not in serialized, "El relato M34 fue copiado al draft")
    require("input_fingerprint" not in serialized, "Fingerprint interno M34 llegó al draft")
    require("matched_fact_ids" not in serialized, "IDs internos M34 llegaron al draft")

    # User-edited fulfillment answer must win over any later M34-derived preparation.
    edited_answers = dict(draft.get("answers") or {})
    edited_answers["purchase_date"] = "2026-08-20"
    account.post(
        "/api/drafts",
        {
            "product_code": "CO-CD-003",
            "answers": edited_answers,
            "current_step": draft.get("current_step") or 0,
            "title": draft.get("title") or "Caso consumidor M35.1",
            "result": draft.get("result") or {},
        },
        expected=200,
    )
    repeated = account.post(
        "/api/m35/fulfillment/prepare",
        {"product_code": "CO-CD-003"},
        expected=200,
    )
    require(repeated.get("answers", {}).get("purchase_date") == "2026-08-20", "Una preparación posterior sobrescribió la edición del usuario")
    require(repeated.get("applied_prefill_count") == 0, "La segunda preparación debería respetar todos los campos ya existentes")

    other = account.post(
        "/api/m35/fulfillment/prepare",
        {"product_code": "CO-AR-001"},
        expected=404,
    )
    require(other.get("code") == "NO_TRANSFERRED_INTAKE", "M35.1 permitió preparar un producto no reclamado")

    after = account.get("/api/self-service", expected=200)
    require((after.get("orders") or []) == [], "Preparar fulfillment creó una orden antes de consentimiento/checkout")

    print(
        "M35.1 HTTP smoke PASS · "
        f"product=CO-CD-003 eligible={prepared.get('eligible_prefill_count')} "
        f"applied={prepared.get('applied_prefill_count')} user_edit=preserved "
        "offer=sandbox checkout_orders=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M35.1 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
