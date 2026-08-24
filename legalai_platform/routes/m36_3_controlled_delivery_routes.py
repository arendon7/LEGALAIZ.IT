from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.controlled_delivery_m36_3 import ControlledDeliveryCenter, ControlledDeliveryError
from legalai_platform.routes.m32_5_approval_desk_routes import workspace
from legalai_platform.routes.m36_2_review_reconciliation_routes import reconciler
from legalai_platform.runtime_registry import M24_CASE_JOURNEY, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m36/delivery"


@lru_cache(maxsize=1)
def delivery_center() -> ControlledDeliveryCenter:
    return ControlledDeliveryCenter(reconciler(), workspace(), M24_CASE_JOURNEY)


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
        f"m36-3:{action}:{user.get('id')}:{_ip(handler) or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones de entrega.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, ControlledDeliveryError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, PermissionError)):
        handler.send_json({"error": str(exc), "code": "DELIVERY_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la operación de entrega.", "code": "DELIVERY_INTERNAL_ERROR"}, 500)
    return True


def handle_m36_3_delivery_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        center = delivery_center()
        if not parts:
            if not _rate_limit(handler, user, "queue", 60, 300):
                return True
            payload = center.queue(user)
            _observe(
                "m36_delivery_queue_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                cases=(payload.get("metrics") or {}).get("cases"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        if len(parts) == 2 and parts[0] == "cases":
            if not _rate_limit(handler, user, "detail", 120, 300):
                return True
            payload = center.detail(user, parts[1])
            _observe(
                "m36_delivery_detail_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                delivery_id=payload.get("delivery_id"),
                state=payload.get("state"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        if len(parts) == 3 and parts[0] == "cases" and parts[2] == "download":
            if not _rate_limit(handler, user, "download", 30, 300):
                return True
            target, name, payload = center.download(user, parts[1])
            _observe(
                "m36_delivery_download_requested",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                delivery_id=payload.get("delivery_id"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_file(target, download_name=name)
            return True
        handler.send_json({"error": "Ruta M36.3 no encontrada.", "code": "M36_3_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m36_delivery_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


def handle_m36_3_delivery_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "deliver", 12, 300):
        return True
    try:
        parts = _parts(path)
        if len(parts) != 3 or parts[0] != "cases" or parts[2] != "deliver":
            handler.send_json({"error": "Ruta M36.3 no encontrada.", "code": "M36_3_NOT_FOUND"}, 404)
            return True
        data = handler.read_json()
        result = delivery_center().deliver(user, parts[1], str(data.get("confirmation") or ""))
        _observe(
            "m36_delivery_completed",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=parts[1],
            delivery_id=result.get("delivery_id"),
            state=result.get("state"),
            document_count=result.get("document_count"),
            idempotent=result.get("idempotent"),
            ip_hash=_ip_hash(handler),
        )
        handler.send_json(result, 200 if result.get("idempotent") else 201)
        return True
    except Exception as exc:
        _observe(
            "m36_delivery_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "delivery_center",
    "handle_m36_3_delivery_get",
    "handle_m36_3_delivery_post",
]
