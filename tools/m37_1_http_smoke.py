#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, BASE, ORIGIN, register_client, require
from tools.m36_0_http_smoke import login_admin
from tools.m36_2_http_smoke import login_specialist
from tools.m36_3_http_smoke import CONFIRMATION, prepare_reviewed_released_case


FOLLOWUP_CONFIRMATION = "INICIAR SEGUIMIENTO"


def multipart_post(
    client: Client,
    path: str,
    filename: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    expected: int = 201,
) -> dict:
    boundary = "----LegalAIZM371" + uuid.uuid4().hex
    chunks = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Origin": ORIGIN,
        "User-Agent": "LegalAIZ-M37.1-CI-Smoke",
    }
    if client.csrf:
        headers["X-CSRF-Token"] = client.csrf
    request = Request(BASE + path, data=b"".join(chunks), method="POST", headers=headers)
    try:
        with client.opener.open(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
            if response.status != expected:
                raise AssertionError(f"{path}: HTTP {response.status}, esperado {expected}: {payload}")
            return payload
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            payload = {"raw": raw}
        if exc.code != expected:
            raise AssertionError(f"{path}: HTTP {exc.code}, esperado {expected}: {payload}") from exc
        return payload


def raw_download(client: Client, path: str) -> tuple[bytes, dict[str, str]]:
    request = Request(BASE + path, method="GET", headers={"User-Agent": "LegalAIZ-M37.1-CI-Smoke"})
    try:
        with client.opener.open(request, timeout=10) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{path}: descarga HTTP {exc.code}: {body}") from exc


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
    require(delivered.get("state") == "DELIVERED_IN_APP", "M37.1 necesita entrega M36.3 válida")

    started = owner.post(
        f"/api/m37/follow-up/cases/{case_id}/start",
        {"confirmation": FOLLOWUP_CONFIRMATION},
        expected=201,
    )
    require(started.get("lifecycle") == "ACTIVE", "M37.1 necesita seguimiento M37.0 ACTIVE")
    require(started.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.1 necesita M24 EN_SEGUIMIENTO")
    tasks = started.get("tasks") or []
    require(bool(tasks), "M37.1 no encontró actividades de seguimiento")
    task = tasks[0]
    task_id = str(task.get("follow_up_id") or "")
    task_status_before = str(task.get("status") or "")

    unavailable = owner.get(f"/api/m37/evidence/cases/{case_id}", expected=200)
    require((unavailable.get("metrics") or {}).get("evidence_items") == 0, "M37.1 inventó soportes antes de la carga")

    csrf = owner.csrf
    owner.csrf = ""
    csrf_denied = multipart_post(
        owner,
        f"/api/m37/evidence/cases/{case_id}/tasks/{task_id}/upload",
        "radicado.pdf",
        b"%PDF-1.4\nsmoke\n%%EOF\n",
        expected=403,
    )
    require(csrf_denied.get("code") == "CSRF_FAILED", "M37.1 aceptó upload sin CSRF")
    owner.csrf = csrf

    fake = multipart_post(
        owner,
        f"/api/m37/evidence/cases/{case_id}/tasks/{task_id}/upload",
        "falso.pdf",
        b"esto no es pdf",
        expected=422,
    )
    require(fake.get("code") == "EVIDENCE_SIGNATURE_MISMATCH", "M37.1 confió en extensión sin firma real")

    body = b"%PDF-1.4\nconstancia de radicacion smoke\n%%EOF\n"
    upload_path = f"/api/m37/evidence/cases/{case_id}/tasks/{task_id}/upload"
    uploaded = multipart_post(
        owner,
        upload_path,
        "../../constancia_radicacion.pdf",
        body,
        content_type="application/octet-stream",
        expected=201,
    )
    evidence_id = str(uploaded.get("evidence_id") or "")
    require(bool(evidence_id), "M37.1 no devolvió evidence_id")
    require(uploaded.get("idempotent") is False, "Primer upload M37.1 se marcó idempotente")
    require(uploaded.get("filename") == "constancia_radicacion.pdf", "M37.1 no neutralizó el nombre de archivo")
    require(uploaded.get("file_kind") == "PDF", "M37.1 clasificó mal el PDF")
    require(uploaded.get("mime_type") == "application/pdf", "M37.1 confió en Content-Type declarado")
    require(uploaded.get("claimed_content_type_trusted") is False, "M37.1 presentó Content-Type del cliente como confiable")
    require(uploaded.get("review", {}).get("status") == "PENDING_REVIEW", "M37.1 inventó revisión al recibir archivo")
    require(uploaded.get("governance", {}).get("upload_completed_task") is False, "M37.1 completó tarea por upload")
    require(uploaded.get("governance", {}).get("authenticity_verified") is False, "M37.1 inventó autenticidad")
    require(uploaded.get("security_scan", {}).get("local_demo_unscanned") is True, "M37.1 demo local no transparentó ausencia de escáner externo")

    repeated_upload = multipart_post(
        owner,
        upload_path,
        "../../constancia_radicacion.pdf",
        body,
        content_type="application/octet-stream",
        expected=200,
    )
    require(repeated_upload.get("idempotent") is True, "Retry exacto M37.1 no fue idempotente")
    require(repeated_upload.get("evidence_id") == evidence_id, "Retry exacto M37.1 creó otro evidence_id")
    after_retry = owner.get(f"/api/m37/evidence/cases/{case_id}", expected=200)
    require((after_retry.get("metrics") or {}).get("evidence_items") == 1, "Retry exacto M37.1 duplicó el soporte")

    followup_after_upload = owner.get(f"/api/m37/follow-up/cases/{case_id}", expected=200)
    task_after_upload = next(item for item in followup_after_upload.get("tasks") or [] if item.get("follow_up_id") == task_id)
    require(task_after_upload.get("status") == task_status_before, "M37.1 alteró la tarea al recibir evidencia")
    require(followup_after_upload.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.1 alteró lifecycle al recibir evidencia")

    other = Client()
    register_client(other, "M371Other")
    hidden = other.get(f"/api/m37/evidence/cases/{case_id}", expected=404)
    require(hidden.get("code") == "FOLLOWUP_NOT_AVAILABLE", "M37.1 reveló evidencia cross-tenant")

    client_review = owner.post(
        f"/api/m37/evidence/cases/{case_id}/items/{evidence_id}/review",
        {"disposition": "ACKNOWLEDGED_FOR_FOLLOWUP", "message_to_client": ""},
        expected=403,
    )
    require(client_review.get("code") == "PERMISSION_DENIED", "Cliente pudo revisar jurídicamente su propio soporte")

    specialist = login_specialist(specialist_id)
    reviewed = specialist.post(
        f"/api/m37/evidence/cases/{case_id}/items/{evidence_id}/review",
        {
            "disposition": "NEEDS_CLARIFICATION",
            "message_to_client": "Aporta una constancia donde se vea claramente la fecha de radicación.",
        },
        expected=201,
    )
    review = reviewed.get("review") or {}
    require(review.get("status") == "REVIEWED_FOR_INTAKE", "M37.1 no registró revisión")
    require(review.get("disposition") == "NEEDS_CLARIFICATION", "M37.1 perdió la disposición profesional")
    require(review.get("authenticity_verified") is False, "M37.1 convirtió revisión en autenticidad")
    require(review.get("legal_sufficiency_verified") is False, "M37.1 convirtió revisión en suficiencia jurídica")
    require(review.get("legal_effect_verified") is False, "M37.1 convirtió revisión en efecto jurídico")

    repeated = specialist.post(
        f"/api/m37/evidence/cases/{case_id}/items/{evidence_id}/review",
        {
            "disposition": "NEEDS_CLARIFICATION",
            "message_to_client": "Aporta una constancia donde se vea claramente la fecha de radicación.",
        },
        expected=200,
    )
    require(repeated.get("idempotent") is True, "Retry M37.1 duplicó la misma revisión")

    detail = owner.get(f"/api/m37/evidence/cases/{case_id}", expected=200)
    require((detail.get("metrics") or {}).get("evidence_items") == 1, "M37.1 perdió o duplicó el soporte")
    require((detail.get("metrics") or {}).get("needs_clarification") == 1, "M37.1 perdió el requerimiento de aclaración")
    require(detail.get("governance", {}).get("review_completes_task") is False, "M37.1 declaró review como cumplimiento")

    downloaded, headers = raw_download(owner, str(uploaded.get("download_url") or ""))
    require(downloaded == body, "M37.1 no devolvió exactamente los bytes almacenados")
    require("attachment" in headers.get("content-disposition", "").lower(), "M37.1 no forzó descarga como attachment")

    final_followup = owner.get(f"/api/m37/follow-up/cases/{case_id}", expected=200)
    final_task = next(item for item in final_followup.get("tasks") or [] if item.get("follow_up_id") == task_id)
    require(final_task.get("status") == task_status_before, "Review M37.1 alteró el estado M24 de la tarea")
    require(final_followup.get("m24_current_state") == "EN_SEGUIMIENTO", "M37.1 cerró o escaló automáticamente")

    raw = json.dumps({"upload": uploaded, "retry": repeated_upload, "review": reviewed, "detail": detail}, ensure_ascii=False).lower()
    for forbidden in (
        "file_path",
        "object_ref",
        "plaintext_sha256",
        "sha256",
        "uploader_id",
        "reviewer_id",
        "scan_engine",
        "scan_detail",
        "payment_intent_id",
        "problem_statement",
        "answers",
    ):
        require(forbidden not in raw, f"M37.1 filtró dato interno: {forbidden}")

    print(
        "M37.1 HTTP smoke PASS · "
        f"case={case_id} desks={len(desk_ids)} evidence=1 review=NEEDS_CLARIFICATION "
        f"m24={final_followup.get('m24_current_state')} task_unchanged=true upload_idempotent=true "
        "local_scan_transparent=true authenticity_verified=false legal_sufficiency_verified=false "
        "auto_close=false cross_tenant=hidden review_idempotent=true"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M37.1 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
