from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlparse

import core_v11 as core
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    ImmutableRecordError,
    PermissionDenied,
    ReleaseBlocked,
)
from legalai_platform.approval_notification_center import NotificationIntegrityError
from legalai_platform.transactional_communications import CommunicationsIntegrityError
from legalai_platform.contact_governance_enforcement import EnforcedGovernedTransactionalCommunications


PREFIX = "/api/m32/communications"


@lru_cache(maxsize=1)
def communications() -> EnforcedGovernedTransactionalCommunications:
    return EnforcedGovernedTransactionalCommunications(core.RUNTIME / "approval-desk")


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc)}, 403)
    elif isinstance(exc, ImmutableRecordError):
        handler.send_json({"error": str(exc)}, 409)
    elif isinstance(exc, (CommunicationsIntegrityError, NotificationIntegrityError, ReleaseBlocked)):
        handler.send_json({"error": str(exc)}, 422)
    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError)):
        handler.send_json({"error": str(exc)}, 422)
    else:
        handler.send_json({"error": "Error interno de comunicaciones transaccionales"}, 500)
    return True


def handle_m32_8_communications_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = communications()
        query = parse_qs(urlparse(handler.path).query)
        if not parts:
            handler.send_json(service.dashboard(user)); return True
        if parts == ["queue"]:
            handler.send_json(service.queue(
                user,
                status=query.get("status", [None])[0],
                limit=int(query.get("limit", ["200"])[0]),
            )); return True
        if parts == ["templates"]:
            handler.send_json(service.templates(user)); return True
        if parts == ["policy"]:
            handler.send_json(service.policy(user)); return True
        if len(parts) == 2 and parts[0] == "cases":
            handler.send_json(service.case_communications(user, parts[1])); return True
        handler.send_json({"error": "Ruta M32.8 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


def handle_m32_8_communications_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = communications()
        data = handler.read_json()
        if parts == ["sync"]:
            handler.send_json(service.sync_outbox(user), 201); return True
        if parts == ["process"]:
            handler.send_json(service.process(user, limit=data.get("limit")), 201); return True
        if parts == ["policy"]:
            handler.send_json(service.update_policy(user, data), 201); return True
        if parts == ["templates"]:
            handler.send_json(service.create_template_version(user, data), 201); return True
        if len(parts) == 4 and parts[0] == "templates" and parts[3] == "activate":
            handler.send_json(service.activate_template(user, parts[1], int(parts[2])), 201); return True
        if len(parts) == 3 and parts[0] == "dispatches" and parts[2] == "cancel":
            handler.send_json(service.cancel(user, parts[1], str(data.get("reason") or "")), 201); return True
        if len(parts) == 3 and parts[0] == "dispatches" and parts[2] == "receipt":
            handler.send_json(service.record_receipt(
                user,
                parts[1],
                provider_status=str(data.get("provider_status") or ""),
                provider_event_id=str(data.get("provider_event_id") or ""),
                occurred_at=data.get("occurred_at"),
                detail=str(data.get("detail") or ""),
                synthetic=bool(data.get("synthetic", True)),
            ), 201); return True
        handler.send_json({"error": "Ruta M32.8 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "communications",
    "handle_m32_8_communications_get",
    "handle_m32_8_communications_post",
]
