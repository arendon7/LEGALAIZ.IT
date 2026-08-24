from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.review_reconciliation_m36_2 import ReviewLifecycleReconciler, ReviewReconciliationError
from legalai_platform.routes.m32_5_approval_desk_routes import workspace
from legalai_platform.routes.m32_6_approval_operations_routes import operations
from legalai_platform.runtime_registry import M24_CASE_JOURNEY, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m36/review-lifecycle"


@lru_cache(maxsize=1)
def reconciler() -> ReviewLifecycleReconciler:
    return ReviewLifecycleReconciler(workspace(), operations(), M24_CASE_JOURNEY)


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


def _rate_limit(handler, user: dict, action: str, limit: int, window: int) -> bool:
    ip = _ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m36-2:{action}:{user.get('id')}:{ip or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de reconciliaciones de revisión.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, ReviewReconciliationError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, PermissionError)):
        handler.send_json({"error": str(exc), "code": "RECONCILIATION_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible reconciliar el ciclo de revisión.", "code": "RECONCILIATION_INTERNAL_ERROR"}, 500)
    return True


def handle_m36_2_review_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "read", 120, 300):
        return True
    try:
        parts = _parts(path)
        if len(parts) == 2 and parts[0] == "cases":
            payload = reconciler().assess(user, parts[1])
        elif len(parts) == 3 and parts[0] == "cases" and parts[2] == "history":
            payload = reconciler().history(user, parts[1])
        else:
            handler.send_json({"error": "Ruta M36.2 no encontrada.", "code": "M36_2_NOT_FOUND"}, 404)
            return True
        _observe(
            "m36_review_reconciliation_read",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=parts[1] if len(parts) >= 2 and parts[0] == "cases" else None,
            current_state=payload.get("m24_current_state") if isinstance(payload, dict) else None,
            aggregate_state=payload.get("aggregate_review_state") if isinstance(payload, dict) else None,
            reconciliation_needed=payload.get("reconciliation_needed") if isinstance(payload, dict) else None,
        )
        handler.send_json(payload, 200)
        return True
    except Exception as exc:
        _observe(
            "m36_review_reconciliation_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


def handle_m36_2_review_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "write", 30, 300):
        return True
    try:
        parts = _parts(path)
        if len(parts) != 3 or parts[0] != "cases" or parts[2] != "reconcile":
            handler.send_json({"error": "Ruta M36.2 no encontrada.", "code": "M36_2_NOT_FOUND"}, 404)
            return True
        result = reconciler().reconcile(user, parts[1])
        _observe(
            "m36_review_reconciliation_completed",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=result.get("case_id"),
            m24_state=result.get("m24_current_state"),
            aggregate_state=result.get("aggregate_review_state"),
            applied_count=len(result.get("applied_transitions") or []),
            reconciled=result.get("reconciled"),
            idempotent=result.get("idempotent"),
            ip_hash=sha256(_ip(handler).encode("utf-8")).hexdigest()[:16] if _ip(handler) else "",
        )
        handler.send_json(result, 201 if result.get("reconciled") else 200)
        return True
    except Exception as exc:
        _observe(
            "m36_review_reconciliation_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "reconciler",
    "handle_m36_2_review_get",
    "handle_m36_2_review_post",
]
