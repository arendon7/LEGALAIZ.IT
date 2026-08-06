from __future__ import annotations

from functools import lru_cache
from urllib.parse import unquote

import core_v11 as core
from legalai_platform.approval_desk_operations import (
    ApprovalDeskOperations,
    OperationsIntegrityError,
)
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    ImmutableRecordError,
    PermissionDenied,
    ReleaseBlocked,
)


PREFIX = "/api/m32/approval-operations"


@lru_cache(maxsize=1)
def operations() -> ApprovalDeskOperations:
    return ApprovalDeskOperations(core.RUNTIME / "approval-desk")


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc)}, 403)
    elif isinstance(exc, ImmutableRecordError):
        handler.send_json({"error": str(exc)}, 409)
    elif isinstance(exc, (OperationsIntegrityError, ReleaseBlocked)):
        handler.send_json({"error": str(exc)}, 422)
    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError)):
        handler.send_json({"error": str(exc)}, 422)
    else:
        handler.send_json({"error": "Error interno de la operación documental"}, 500)
    return True


def handle_m32_6_operations_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = operations()
        if not parts:
            handler.send_json(service.portfolio(user)); return True
        if parts == ["professionals"]:
            handler.send_json(service.professionals(user)); return True
        if len(parts) >= 2 and parts[0] == "cases":
            case_id = parts[1]
            if len(parts) == 2:
                handler.send_json(service.case_detail(user, case_id)); return True
            if len(parts) == 3 and parts[2] == "dossier":
                handler.send_json(service.build_dossier(user, case_id)); return True
            if len(parts) == 3 and parts[2] == "dossier-download":
                target, filename = service.export_dossier(user, case_id)
                handler.send_file(target, download_name=filename); return True
        handler.send_json({"error": "Ruta M32.6 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


def handle_m32_6_operations_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _parts(path)
        service = operations()
        if parts == ["portfolio", "sync"]:
            data = handler.read_json()
            handler.send_json(service.sync_portfolio(user, limit=data.get("limit", 500)), 201); return True
        if len(parts) >= 3 and parts[0] == "cases":
            case_id = parts[1]
            action = parts[2]
            data = handler.read_json()
            if action == "assignment" and len(parts) == 3:
                handler.send_json(service.update_assignment(
                    user,
                    case_id,
                    str(data.get("specialist_id") or ""),
                    str(data.get("qa_id") or ""),
                ), 201); return True
            if action == "priority" and len(parts) == 3:
                handler.send_json(service.update_priority(user, case_id, str(data.get("priority") or "")), 201); return True
            if action == "deadline" and len(parts) == 3:
                handler.send_json(service.update_deadline(
                    user,
                    case_id,
                    str(data.get("due_at") or ""),
                    data.get("sla_hours"),
                ), 201); return True
            if action == "notes" and len(parts) == 3:
                handler.send_json(service.add_note(user, case_id, str(data.get("text") or "")), 201); return True
            if action == "alerts" and len(parts) == 5 and parts[4] == "acknowledge":
                handler.send_json(service.acknowledge_alert(
                    user,
                    case_id,
                    parts[3],
                    str(data.get("comment") or ""),
                ), 201); return True
        handler.send_json({"error": "Ruta M32.6 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "handle_m32_6_operations_get",
    "handle_m32_6_operations_post",
    "operations",
]
