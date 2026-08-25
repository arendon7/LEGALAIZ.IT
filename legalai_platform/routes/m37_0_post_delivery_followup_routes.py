from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.post_delivery_followup_m37_0 import (
    PostDeliveryFollowUpCenter,
    PostDeliveryFollowUpError,
)
from legalai_platform.runtime_registry import M24_CASE_JOURNEY, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m37/follow-up"


@lru_cache(maxsize=1)
def followup_center() -> PostDeliveryFollowUpCenter:
    return PostDeliveryFollowUpCenter(M24_CASE_JOURNEY)


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
        f"m37-0:{action}:{user.get('id')}:{_ip(handler) or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones de seguimiento.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PostDeliveryFollowUpError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, PermissionError):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, KeyError)):
        handler.send_json({"error": str(exc), "code": "FOLLOWUP_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la operación de seguimiento.", "code": "FOLLOWUP_INTERNAL_ERROR"}, 500)
    return True


def handle_m37_0_followup_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = followup_center()
        if not parts:
            if not _rate_limit(handler, user, "queue", 60, 300):
                return True
            payload = center.queue(user)
            _observe(
                "m37_followup_queue_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                cases=(payload.get("metrics") or {}).get("cases"),
                active=(payload.get("metrics") or {}).get("active"),
                overdue_tasks=(payload.get("metrics") or {}).get("overdue_tasks"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        if len(parts) == 2 and parts[0] == "cases":
            if not _rate_limit(handler, user, "detail", 120, 300):
                return True
            payload = center.detail(user, parts[1])
            _observe(
                "m37_followup_detail_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                lifecycle=payload.get("lifecycle"),
                task_count=(payload.get("metrics") or {}).get("tasks"),
                overdue=(payload.get("metrics") or {}).get("overdue"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        handler.send_json({"error": "Ruta M37.0 no encontrada.", "code": "M37_0_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_followup_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


def handle_m37_0_followup_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = followup_center()
        if len(parts) == 3 and parts[0] == "cases" and parts[2] == "start":
            if not _rate_limit(handler, user, "start", 12, 300):
                return True
            data = handler.read_json()
            payload = center.start(user, parts[1], str(data.get("confirmation") or ""))
            _observe(
                "m37_followup_started",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                lifecycle=payload.get("lifecycle"),
                task_count=(payload.get("metrics") or {}).get("tasks"),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        if len(parts) == 4 and parts[0] == "cases" and parts[2] == "tasks":
            if not _rate_limit(handler, user, "task", 60, 300):
                return True
            data = handler.read_json()
            payload = center.record_task(
                user,
                parts[1],
                parts[3],
                str(data.get("status") or ""),
                str(data.get("note") or ""),
            )
            _observe(
                "m37_followup_task_recorded",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                follow_up_id=parts[3],
                idempotent=payload.get("idempotent"),
                completed=(payload.get("metrics") or {}).get("completed"),
                pending=(payload.get("metrics") or {}).get("pending"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        handler.send_json({"error": "Ruta M37.0 no encontrada.", "code": "M37_0_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_followup_write_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


__all__ = ["PREFIX", "followup_center", "handle_m37_0_followup_get", "handle_m37_0_followup_post"]
