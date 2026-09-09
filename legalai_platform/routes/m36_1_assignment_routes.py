from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.approval_notification_center import NotificationIntegrityError
from legalai_platform.professional_assignment_m36_1 import ProfessionalAssignmentCenter, ProfessionalAssignmentError
from legalai_platform.routes.m32_6_approval_operations_routes import operations
from legalai_platform.routes.m32_7_notification_center_routes import notification_center
from legalai_platform.routes.m36_0_fulfillment_routes import fulfillment_center
from legalai_platform.runtime_registry import OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m36/assignments"


@lru_cache(maxsize=1)
def assignment_center() -> ProfessionalAssignmentCenter:
    return ProfessionalAssignmentCenter(
        fulfillment_center(),
        operations(),
        notification_center(),
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


def _rate_limit(handler, user: dict, action: str, limit: int, window: int) -> bool:
    ip = _ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m36-1:{action}:{user.get('id')}:{ip or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones de asignación.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, ProfessionalAssignmentError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, NotificationIntegrityError):
        handler.send_json({"error": str(exc), "code": "NOTIFICATION_INTEGRITY_FAILED"}, 422)
    elif isinstance(exc, ApprovalDeskError):
        handler.send_json({"error": str(exc), "code": "APPROVAL_OPERATIONS_ERROR"}, 422)
    elif isinstance(exc, (ValueError, TypeError)):
        handler.send_json({"error": str(exc), "code": "INVALID_ASSIGNMENT_INPUT"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la asignación profesional.", "code": "ASSIGNMENT_INTERNAL_ERROR"}, 500)
    return True


def handle_m36_1_assignment_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "read", 120, 300):
        return True
    try:
        parts = _parts(path)
        center = assignment_center()
        if not parts:
            payload = center.queue(user)
        elif parts == ["professionals"]:
            payload = center.professionals(user)
        elif len(parts) == 2 and parts[0] == "cases":
            payload = center.detail(user, parts[1])
        else:
            handler.send_json({"error": "Ruta M36.1 no encontrada.", "code": "M36_1_NOT_FOUND"}, 404)
            return True
        _observe(
            "m36_professional_assignment_read",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=parts[1] if len(parts) == 2 and parts[0] == "cases" else None,
            item_count=len(payload.get("items") or []) if isinstance(payload, dict) else 0,
        )
        handler.send_json(payload, 200)
        return True
    except Exception as exc:
        _observe(
            "m36_professional_assignment_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


def handle_m36_1_assignment_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    if not _rate_limit(handler, user, "write", 30, 300):
        return True
    try:
        parts = _parts(path)
        if len(parts) != 3 or parts[0] != "cases" or parts[2] != "assign":
            handler.send_json({"error": "Ruta M36.1 no encontrada.", "code": "M36_1_NOT_FOUND"}, 404)
            return True
        data = handler.read_json()
        result = assignment_center().assign(
            user,
            parts[1],
            str(data.get("specialist_id") or ""),
            str(data.get("qa_id") or ""),
        )
        _observe(
            "m36_professional_assignment_completed",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            case_id=result.get("case_id"),
            assignment_id=result.get("assignment_id"),
            state=result.get("state"),
            desk_count=result.get("desk_count"),
            assigned_desks=result.get("assigned_desks"),
            notification_evaluations=result.get("notification_evaluations"),
            idempotent=result.get("idempotent"),
            ip_hash=sha256(_ip(handler).encode("utf-8")).hexdigest()[:16] if _ip(handler) else "",
        )
        handler.send_json(result, 200 if result.get("idempotent") else 201)
        return True
    except Exception as exc:
        _observe(
            "m36_professional_assignment_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
        )
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "assignment_center",
    "handle_m36_1_assignment_get",
    "handle_m36_1_assignment_post",
]
