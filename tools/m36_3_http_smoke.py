#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, BASE, register_client, require
from tools.m36_0_http_smoke import create_activated_case, login_admin
from tools.m36_2_http_smoke import SPECIALIST_EMAILS, approve, login_specialist, release


CONFIRMATION = "ENTREGAR SOLUCIÓN"


def prepare_reviewed_released_case(owner: Client, admin: Client) -> tuple[dict, list[str], str]:
    case = create_activated_case(owner)
    case_id = case["case_id"]
    fulfillment = admin.post(f"/api/m36/fulfillment/cases/{case_id}/activate", {}, expected=201)
    desk_ids = fulfillment.get("desk_case_ids") or []
    require(len(desk_ids) == case["document_count"] >= 1, "M36.3 necesita cobertura completa M36.0")

    directory = admin.get("/api/m36/assignments/professionals", expected=200)
    specialist = next(
        (item for item in directory.get("specialists") or [] if item.get("id") == "USR-COMM"),
        None,
    ) or next(
        (item for item in directory.get("specialists") or [] if item.get("id") in SPECIALIST_EMAILS),
        None,
    )
    qa = next((item for item in directory.get("qa") or [] if item.get("id") == "USR-ADMIN"), None)
    require(specialist is not None and qa is not None, "M36.3 no encontró par especialista/QA demo")
    require(specialist["id"] != qa["id"], "M36.3 requiere separación de funciones")
    assignment = admin.post(
        f"/api/m36/assignments/cases/{case_id}/assign",
        {"specialist_id": specialist["id"], "qa_id": qa["id"]},
        expected=201,
    )
    require(assignment.get("state") == "COMPLETE", "M36.3 necesita asignación M36.1 completa")
    legal = login_specialist(str(specialist["id"]))

    for desk_id in desk_ids:
        approve(legal, desk_id, "legal")
    reconciled_legal = admin.post(f"/api/m36/review-lifecycle/cases/{case_id}/reconcile", {}, expected=201)
    require(reconciled_legal.get("m24_current_state") == "EN_QA", "M36.3 no alcanzó EN_QA")

    for desk_id in desk_ids:
        approve(admin, desk_id, "qa")
    reconciled_qa = admin.post(f"/api/m36/review-lifecycle/cases/{case_id}/reconcile", {}, expected=201)
    require(reconciled_qa.get("m24_current_state") == "APROBADO_QA", "M36.3 no alcanzó APROBADO_QA")

    for desk_id in desk_ids:
        release(admin, desk_id)
    ready = admin.get(f"/api/m36/review-lifecycle/cases/{case_id}", expected=200)
    require(ready.get("delivery_gate_ready") is True, "M36.3 necesita delivery_gate_ready")
    require(ready.get("release_complete") is True, "M36.3 necesita liberación completa")
    return case, desk_ids, str(specialist["id"])


def raw_download(client: Client, path: str) -> tuple[bytes, dict[str, str]]:
    request = Request(BASE + path, method="GET", headers={"User-Agent": "LegalAIZ-M36.3-CI-Smoke"})
    try:
        with client.opener.open(request, timeout=10) as response:
            body = response.read()
            return body, {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{path}: descarga HTTP {exc.code}: {body}") from exc


def main() -> int:
    owner = Client()
    admin = login_admin()
    case, desk_ids, specialist_id = prepare_reviewed_released_case(owner, admin)
    case_id = case["case_id"]

    unavailable = owner.get(f"/api/m36/delivery/cases/{case_id}", expected=404)
    require(unavailable.get("code") == "DELIVERY_NOT_AVAILABLE", "M36.3 presentó entrega antes de ejecutarla")

    bypass = admin.post(
        f"/api/m24/case-journeys/{case_id}/transition",
        {
            "target_state": "ENTREGADO",
            "reason": "Intento sintético de omitir la compuerta controlada M36.3 durante CI.",
            "evidence": {},
            "confirmation": CONFIRMATION,
        },
        expected=409,
    )
    require(bypass.get("code") == "M36_CONTROLLED_DELIVERY_REQUIRED", "M24 permitió bypass de M36.3")

    csrf = admin.csrf
    admin.csrf = ""
    csrf_denied = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": CONFIRMATION},
        expected=403,
    )
    require(csrf_denied.get("code") == "CSRF_FAILED", "M36.3 aceptó entrega sin CSRF")
    admin.csrf = csrf

    wrong_confirmation = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": "ENTREGAR"},
        expected=422,
    )
    require(wrong_confirmation.get("code") == "DELIVERY_CONFIRMATION_REQUIRED", "M36.3 aceptó confirmación débil")

    owner_denied = owner.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": CONFIRMATION},
        expected=403,
    )
    require(owner_denied.get("code") == "PERMISSION_DENIED", "Cliente pudo ejecutar entrega M36.3")

    delivered = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": CONFIRMATION},
        expected=201,
    )
    require(delivered.get("schema") == "legalai_m36_3_controlled_delivery_v1", "Schema M36.3 inesperado")
    require(delivered.get("state") == "DELIVERED_IN_APP", "M36.3 no finalizó entrega in-app")
    require(delivered.get("delivery_channel") == "IN_APP", "M36.3 declaró canal incorrecto")
    require(int(delivered.get("document_count") or 0) == len(desk_ids), "M36.3 perdió cobertura documental")
    require(delivered.get("idempotent") is False, "Primera entrega M36.3 apareció idempotente")
    require(len(str(delivered.get("package_sha256") or "")) == 64, "M36.3 no devolvió hash del paquete")
    governance = delivered.get("governance") or {}
    require(governance.get("source_is_m32_released_exact_hash") is True, "M36.3 no acredita fuente M32 liberada")
    require(governance.get("dual_human_approval_preserved") is True, "M36.3 debilitó aprobación dual")
    require(governance.get("automatic_legal_approval") is False, "M36.3 inventó aprobación legal")
    require(governance.get("automatic_qa_approval") is False, "M36.3 inventó aprobación QA")
    require(governance.get("external_notification_sent") is False, "M36.3 declaró notificación externa inexistente")
    require(governance.get("download_request_is_not_receipt_confirmation") is True, "M36.3 confundió descarga con recepción")

    journey = admin.get(f"/api/m24/case-journeys/{case_id}", expected=200)
    require(journey.get("current_state") == "ENTREGADO", "M36.3 no reconcilió M24 a ENTREGADO")

    repeated = admin.post(
        f"/api/m36/delivery/cases/{case_id}/deliver",
        {"confirmation": CONFIRMATION},
        expected=200,
    )
    require(repeated.get("idempotent") is True, "Retry M36.3 no fue idempotente")
    require(repeated.get("delivery_id") == delivered.get("delivery_id"), "Retry M36.3 creó otro delivery")
    require(repeated.get("package_sha256") == delivered.get("package_sha256"), "Retry M36.3 cambió paquete")

    owner_detail = owner.get(f"/api/m36/delivery/cases/{case_id}", expected=200)
    require(owner_detail.get("delivery_id") == delivered.get("delivery_id"), "Titular recibió otra entrega")
    require(owner_detail.get("download_requests") == 0, "M36.3 inventó descarga antes de solicitarla")

    other = Client()
    register_client(other, "M363Other")
    hidden = other.get(f"/api/m36/delivery/cases/{case_id}", expected=404)
    require(hidden.get("code") == "DELIVERY_NOT_AVAILABLE", "M36.3 reveló entrega a otro cliente")

    body, headers = raw_download(owner, str(owner_detail.get("download_url") or ""))
    require(body.startswith(b"PK"), "M36.3 no devolvió un ZIP válido")
    require("attachment" in headers.get("content-disposition", "").lower(), "M36.3 no forzó descarga del paquete")
    after_download = owner.get(f"/api/m36/delivery/cases/{case_id}", expected=200)
    require(after_download.get("download_requests") == 1, "M36.3 no registró DOWNLOAD_REQUESTED")
    require(after_download.get("governance", {}).get("download_request_is_not_receipt_confirmation") is True, "M36.3 convirtió request en constancia de recibo")

    queue = admin.get("/api/m36/delivery", expected=200)
    item = next((row for row in queue.get("items") or [] if row.get("case_id") == case_id), None)
    require(item is not None, "Cola M36.3 perdió el expediente entregado")
    require(item.get("state") == "DELIVERED_IN_APP", "Cola M36.3 expone estado incorrecto")

    raw = json.dumps({"delivered": delivered, "owner": after_download, "queue_item": item}, ensure_ascii=False).lower()
    for forbidden in (
        "package_path",
        "release_id",
        "revision_id",
        "release_record_hash",
        "specialist_id",
        "qa_id",
        "owner_id",
        "m24_transition_id",
        "problem_statement",
        "answers",
        "payment_intent_id",
    ):
        require(forbidden not in raw, f"M36.3 filtró dato interno: {forbidden}")

    print(
        "M36.3 HTTP smoke PASS · "
        f"case={case_id} desks={len(desk_ids)} legal={specialist_id} qa=USR-ADMIN "
        f"delivery={delivered.get('delivery_id')} state={delivered.get('state')} m24={journey.get('current_state')} "
        f"download_requests={after_download.get('download_requests')} external_notification=false "
        "cross_tenant=hidden idempotent=true"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M36.3 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
