from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlparse

import core_v11 as core
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    ApprovalDeskWorkspace,
    ImmutableRecordError,
    PermissionDenied,
    ReleaseBlocked,
)


PREFIX = "/api/m32/approval-desk"


@lru_cache(maxsize=1)
def workspace() -> ApprovalDeskWorkspace:
    return ApprovalDeskWorkspace(core.RUNTIME / "approval-desk")


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc)}, 403)
    elif isinstance(exc, ImmutableRecordError):
        handler.send_json({"error": str(exc)}, 409)
    elif isinstance(exc, ReleaseBlocked):
        handler.send_json({"error": str(exc)}, 422)
    elif isinstance(exc, (ApprovalDeskError, ValueError, TypeError, KeyError, OSError)):
        handler.send_json({"error": str(exc)}, 422)
    else:
        handler.send_json({"error": "Error interno de la Mesa Jurídica"}, 500)
    return True


def _suffix(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


def handle_m32_5_approval_desk_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _suffix(path)
        service = workspace()
        query = parse_qs(urlparse(handler.path).query)
        if not parts:
            status = query.get("status", [None])[0]
            handler.send_json(service.list_for_user(user, status=status)); return True
        if len(parts) >= 2 and parts[0] == "cases":
            case_id = parts[1]
            if len(parts) == 2:
                handler.send_json(service.detail(user, case_id)); return True
            if len(parts) == 3 and parts[2] == "compare":
                handler.send_json(service.compare(
                    user,
                    case_id,
                    query.get("from", [""])[0],
                    query.get("to", [""])[0],
                )); return True
            if len(parts) == 3 and parts[2] == "audit":
                handler.send_json(service.audit(user, case_id)); return True
            if len(parts) == 3 and parts[2] == "released-download":
                target, release = service.released_path(user, case_id)
                handler.send_file(target, download_name=release["filename"]); return True
            if len(parts) == 5 and parts[2] == "revisions" and parts[4] == "preview":
                handler.send_json(service.preview(user, case_id, parts[3])); return True
            if len(parts) == 5 and parts[2] == "revisions" and parts[4] == "preview.pdf":
                target = service.preview_pdf_path(user, case_id, parts[3])
                handler.send_bytes(target.read_bytes(), "application/pdf"); return True
        handler.send_json({"error": "Ruta M32.5 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


def handle_m32_5_approval_desk_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    try:
        parts = _suffix(path)
        service = workspace()
        if parts == ["bootstrap"]:
            data = handler.read_json()
            handler.send_json(service.bootstrap(user, limit=data.get("limit", 100)), 201); return True
        if len(parts) >= 3 and parts[0] == "cases":
            case_id = parts[1]
            action = parts[2]
            if action == "register-current" and len(parts) == 3:
                data = handler.read_json()
                handler.send_json(service.register_current_document(user, case_id, str(data.get("note") or "")), 201); return True
            if action == "upload-revision" and len(parts) == 3:
                fields, files = handler.read_multipart()
                if not files:
                    handler.send_json({"error": "No se recibió un archivo DOCX."}, 400); return True
                item = files[0]
                handler.send_json(service.upload_revision(
                    user,
                    case_id,
                    item["filename"],
                    item["data"],
                    fields.get("note", ""),
                ), 201); return True
            if action == "findings" and len(parts) == 3:
                handler.send_json(service.add_finding(user, case_id, handler.read_json()), 201); return True
            if action == "findings" and len(parts) == 5 and parts[4] == "resolve":
                handler.send_json(service.resolve_finding(user, case_id, parts[3], handler.read_json()), 201); return True
            if action == "approvals" and len(parts) == 3:
                handler.send_json(service.approve(user, case_id, handler.read_json()), 201); return True
            if action == "release" and len(parts) == 3:
                handler.send_json(service.release(user, case_id, handler.read_json()), 201); return True
        handler.send_json({"error": "Ruta M32.5 no encontrada."}, 404); return True
    except Exception as exc:
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "handle_m32_5_approval_desk_get",
    "handle_m32_5_approval_desk_post",
    "workspace",
]
