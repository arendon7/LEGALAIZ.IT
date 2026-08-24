from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeCenter, EvidenceIntakeError
from legalai_platform.routes.m37_0_post_delivery_followup_routes import followup_center
from legalai_platform.runtime_registry import INFRA, MALWARE_SCANNER, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m37/evidence"


@lru_cache(maxsize=1)
def evidence_center() -> EvidenceIntakeCenter:
    return EvidenceIntakeCenter(followup_center(), MALWARE_SCANNER, INFRA.objects)


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _ip_hash(handler) -> str:
    raw = _ip(handler)
    return sha256(raw.encode("utf-8")).hexdigest()[:16] if raw else "unknown"


def _observe(event: str, **fields) -> None:
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _rate_limit(handler, user: dict, action: str, limit: int, window: int) -> bool:
    allowed, retry = RATE_LIMITER.allow(
        f"m37-1:{action}:{user.get('id')}:{_ip(handler) or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones sobre soportes.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, EvidenceIntakeError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, PermissionError):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, KeyError)):
        handler.send_json({"error": str(exc), "code": "EVIDENCE_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la operación sobre el soporte.", "code": "EVIDENCE_INTERNAL_ERROR"}, 500)
    return True


def handle_m37_1_evidence_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = evidence_center()
        if len(parts) == 2 and parts[0] == "cases":
            if not _rate_limit(handler, user, "detail", 120, 300):
                return True
            payload = center.detail(user, parts[1])
            _observe(
                "m37_evidence_detail_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                evidence_items=(payload.get("metrics") or {}).get("evidence_items"),
                pending_review=(payload.get("metrics") or {}).get("pending_review"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "items" and parts[4] == "download":
            if not _rate_limit(handler, user, "download", 60, 300):
                return True
            body, name, mime_type, public = center.download(user, parts[1], parts[3])
            _observe(
                "m37_evidence_download_requested",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                evidence_id=parts[3],
                file_kind=public.get("file_kind"),
                size_bytes=len(body),
                ip_hash=_ip_hash(handler),
            )
            handler.send_bytes(body, mime_type, filename=name)
            return True
        handler.send_json({"error": "Ruta M37.1 no encontrada.", "code": "M37_1_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_evidence_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


def handle_m37_1_evidence_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = evidence_center()
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "tasks" and parts[4] == "upload":
            if not _rate_limit(handler, user, "upload", 20, 300):
                return True
            _fields, files = handler.read_multipart()
            if len(files) != 1:
                handler.send_json(
                    {"error": "Debe adjuntar exactamente un soporte por solicitud.", "code": "EVIDENCE_SINGLE_FILE_REQUIRED"},
                    400,
                )
                return True
            item = files[0]
            payload = center.upload(
                user,
                parts[1],
                parts[3],
                str(item.get("filename") or ""),
                item.get("data") or b"",
                str(item.get("content_type") or ""),
            )
            _observe(
                "m37_evidence_received",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                follow_up_id=parts[3],
                evidence_id=payload.get("evidence_id"),
                file_kind=payload.get("file_kind"),
                size_bytes=payload.get("size_bytes"),
                scan_status=(payload.get("security_scan") or {}).get("status"),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "items" and parts[4] == "review":
            if not _rate_limit(handler, user, "review", 60, 300):
                return True
            data = handler.read_json()
            payload = center.review(
                user,
                parts[1],
                parts[3],
                str(data.get("disposition") or ""),
                str(data.get("message_to_client") or ""),
            )
            _observe(
                "m37_evidence_review_recorded",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                evidence_id=parts[3],
                disposition=(payload.get("review") or {}).get("disposition"),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        handler.send_json({"error": "Ruta M37.1 no encontrada.", "code": "M37_1_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_evidence_write_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


__all__ = ["PREFIX", "evidence_center", "handle_m37_1_evidence_get", "handle_m37_1_evidence_post"]
