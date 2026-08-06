from __future__ import annotations

from functools import lru_cache
from urllib.parse import unquote, urlparse

import core_v11 as core
from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.contact_governance import ContactGovernanceIntegrityError
from legalai_platform.contact_governance_enforcement import EnforcedContactGovernance


PREFIX = "/api/m32/contact-governance"


@lru_cache(maxsize=1)
def contact_governance() -> EnforcedContactGovernance:
    return EnforcedContactGovernance(core.RUNTIME / "approval-desk")


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc)}, 403)
    elif isinstance(exc, ContactGovernanceIntegrityError):
        handler.send_json({"error": str(exc)}, 422)
    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError)):
        handler.send_json({"error": str(exc)}, 422)
    else:
        handler.send_json({"error": "Error interno del gobierno de contacto"}, 500)
    return True


def handle_m32_9_governance_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = contact_governance()
        if not parts:
            handler.send_json(service.dashboard(user)); return True
        if parts == ["policy"]:
            handler.send_json(service.policy(user)); return True
        if parts == ["notices"]:
            handler.send_json(service.notices(user)); return True
        if len(parts) == 2 and parts[0] == "subjects":
            handler.send_json(service.subject(user, parts[1])); return True
        handler.send_json({"error": "Ruta M32.9 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


def handle_m32_9_governance_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = contact_governance()
        data = handler.read_json()
        if parts == ["policy"]:
            handler.send_json(service.update_policy(user, data), 201); return True
        if parts == ["notices"]:
            handler.send_json(service.create_notice_version(user, data), 201); return True
        if len(parts) == 4 and parts[0] == "notices" and parts[3] == "activate":
            handler.send_json(service.activate_notice(user, parts[1], int(parts[2])), 201); return True
        if parts == ["relationships"]:
            handler.send_json(service.record_relationship(user, data), 201); return True
        if parts == ["preferences"]:
            handler.send_json(service.record_preference(user, data), 201); return True
        if parts == ["suppressions"]:
            handler.send_json(service.add_suppression(user, data), 201); return True
        if len(parts) == 3 and parts[0] == "suppressions" and parts[2] == "lift":
            handler.send_json(service.lift_suppression(user, parts[1], str(data.get("reason") or "")), 201); return True
        if parts == ["evaluate"]:
            handler.send_json(service.evaluate(
                user,
                subject_id=str(data.get("subject_id") or ""),
                purpose=str(data.get("purpose") or ""),
                channel=str(data.get("channel") or ""),
                scheduled_at=data.get("scheduled_at"),
                context_reference=str(data.get("context_reference") or "manual-evaluation"),
                record=True,
            ), 201); return True
        handler.send_json({"error": "Ruta M32.9 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "contact_governance",
    "handle_m32_9_governance_get",
    "handle_m32_9_governance_post",
]
