from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlparse

import core_v11 as core
from legalai_platform.approval_notification_center import (
    ApprovalNotificationCenter,
    NotificationIntegrityError,
)
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    ImmutableRecordError,
    PermissionDenied,
    ReleaseBlocked,
)


PREFIX = "/api/m32/notification-center"


@lru_cache(maxsize=1)
def notification_center() -> ApprovalNotificationCenter:
    return ApprovalNotificationCenter(core.RUNTIME / "approval-desk")


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc)}, 403)
    elif isinstance(exc, ImmutableRecordError):
        handler.send_json({"error": str(exc)}, 409)
    elif isinstance(exc, (NotificationIntegrityError, ReleaseBlocked)):
        handler.send_json({"error": str(exc)}, 422)
    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError)):
        handler.send_json({"error": str(exc)}, 422)
    else:
        handler.send_json({"error": "Error interno del centro de notificaciones"}, 500)
    return True


def handle_m32_7_notification_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = notification_center()
        query = parse_qs(urlparse(handler.path).query)
        if not parts:
            handler.send_json(service.dashboard(user)); return True
        if parts == ["inbox"]:
            include_all = query.get("scope", ["personal"])[0] == "all"
            limit = int(query.get("limit", ["100"])[0])
            handler.send_json(service.inbox(user, include_all=include_all, limit=limit)); return True
        if parts == ["workload"]:
            handler.send_json(service.workload(user)); return True
        if parts == ["calendar"]:
            handler.send_json(service.calendar(user)); return True
        if parts == ["policy"]:
            handler.send_json(service.policy(user)); return True
        if parts == ["outbox"]:
            handler.send_json(service.outbox(user)); return True
        if len(parts) == 2 and parts[0] == "cases":
            handler.send_json(service.case_notifications(user, parts[1])); return True
        handler.send_json({"error": "Ruta M32.7 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


def handle_m32_7_notification_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = notification_center()
        data = handler.read_json()
        if parts == ["evaluate"]:
            handler.send_json(service.evaluate(user, data.get("case_id")), 201); return True
        if parts == ["calendar"]:
            handler.send_json(service.update_calendar(user, data), 201); return True
        if parts == ["policy"]:
            handler.send_json(service.update_policy(user, data), 201); return True
        if len(parts) == 3 and parts[0] == "cases" and parts[2] == "schedule":
            handler.send_json(service.schedule_case(
                user,
                parts[1],
                float(data.get("business_hours") or 0),
                data.get("start_at"),
            ), 201); return True
        if len(parts) == 3 and parts[0] == "notifications":
            notification_id = parts[1]
            if parts[2] == "read":
                handler.send_json(service.mark_read(user, notification_id), 201); return True
            if parts[2] == "acknowledge":
                handler.send_json(service.acknowledge(user, notification_id, str(data.get("comment") or "")), 201); return True
            if parts[2] == "snooze":
                handler.send_json(service.snooze(user, notification_id, str(data.get("until") or "")), 201); return True
        if len(parts) == 3 and parts[0] == "outbox" and parts[2] == "cancel":
            handler.send_json(service.cancel_message(user, parts[1], str(data.get("reason") or "")), 201); return True
        handler.send_json({"error": "Ruta M32.7 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "handle_m32_7_notification_get",
    "handle_m32_7_notification_post",
    "notification_center",
]
