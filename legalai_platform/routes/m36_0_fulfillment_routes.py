from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_operations import OperationsIntegrityError
from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.fulfillment_intake_m36_0 import FulfillmentIntakeCenter, FulfillmentIntakeError
from legalai_platform.routes.m32_6_approval_operations_routes import operations
from legalai_platform.routes.m35_3_activation_routes import activation_center
from legalai_platform.runtime_registry import M24_CASE_JOURNEY, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m36/fulfillment"


@lru_cache(maxsize=1)
def fulfillment_center() -> FulfillmentIntakeCenter:
    ops = operations()
    return FulfillmentIntakeCenter(
        activation_center(),
        ops.workspace,
        ops,
        M24_CASE_JOURNEY,
    )


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _observe(event: str, **fields) -> None:
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, FulfillmentIntakeError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, OperationsIntegrityError):
        handler.send_json({"error": str(exc), "code": "OPERATIONS_INTEGRITY_FAILED"}, 422)
    elif isinstance(exc, ApprovalDeskError):
        handler.send_json({"error": str(exc), "code": "APPROVAL_DESK_ERROR"}, 422)
    elif isinstance(exc, (ValueError, TypeError)):
        handler.send_json({"error": str(exc), "code": "INVALID_FULFILLMENT_INPUT"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la operación de fulfillment.", "code": "FULFILLMENT_INTERNAL_ERROR"}, 500)
    return True


def _rate_limit(handler, user: dict, action: str, limit: int, window: int) -> bool:
    ip = _ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m36:{action}:{user.get('id')}:{ip or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones de fulfillment.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def handle_m36_0_fulfillment_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "read", 120, 300):
        return True
    try:
        parts = _parts(path)
        center = fulfillment_center()
        if not parts:
            payload = center.queue(user)
        elif len(parts) == 2 and parts[0] == "cases":
            payload = center.detail(user, parts[1])
        else:
            handler.send_json({"error": "Ruta M36.0 no encontrada.", "code": "M36_0_NOT_FOUND"}, 404)
            return True
        _observe(
            "m36_fulfillment_read",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=parts[1] if len(parts) == 2 and parts[0] == "cases" else None,
            item_count=len(payload.get("items") or []) if isinstance(payload, dict) else 0,
        )
        handler.send_json(payload, 200)
        return True
    except Exception as exc:
        _observe(
            "m36_fulfillment_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


def handle_m36_0_fulfillment_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "write", 30, 300):
        return True
    try:
        parts = _parts(path)
        if len(parts) != 3 or parts[0] != "cases" or parts[2] != "activate":
            handler.send_json({"error": "Ruta M36.0 no encontrada.", "code": "M36_0_NOT_FOUND"}, 404)
            return True
        case_id = parts[1]
        result = fulfillment_center().activate(user, case_id)
        _observe(
            "m36_fulfillment_activated",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=case_id,
            fulfillment_intake_id=result.get("fulfillment_intake_id"),
            product_code=result.get("product_code"),
            document_count=result.get("document_count"),
            journey_state=result.get("journey_state"),
            idempotent=result.get("idempotent"),
            ip_hash=sha256(_ip(handler).encode("utf-8")).hexdigest()[:16] if _ip(handler) else "",
        )
        handler.send_json(result, 200 if result.get("idempotent") else 201)
        return True
    except Exception as exc:
        _observe(
            "m36_fulfillment_activation_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "fulfillment_center",
    "handle_m36_0_fulfillment_get",
    "handle_m36_0_fulfillment_post",
]
