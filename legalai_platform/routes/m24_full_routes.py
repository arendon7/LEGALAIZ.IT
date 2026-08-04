from __future__ import annotations

from urllib.parse import unquote

import core_v11 as core
from legalai_platform.runtime_registry import M24_FULL, M24_RELEASE_GOVERNANCE, M24_HUMAN_APPROVAL


def _authorized(user):
    return user.get("role") in {"specialist", "admin"}


def handle_m24_full_get(handler, path, user):
    prefix = "/api/m24/full-validation"
    if not path.startswith(prefix):
        return False
    if not _authorized(user):
        handler.send_json({"error": "Solo especialistas y administradores pueden consultar la validación integral."}, 403)
        return True
    con = core.db()
    try:
        if path == prefix:
            handler.send_json(M24_RELEASE_GOVERNANCE.summary(con)); return True
        if path == prefix + "/human-approval":
            handler.send_json(M24_HUMAN_APPROVAL.summary(con, M24_RELEASE_GOVERNANCE)); return True
        suffix = path[len(prefix):].strip("/")
        parts = suffix.split("/") if suffix else []
        if len(parts) >= 3 and parts[1] == "evidence":
            code = parts[0].upper(); filename = unquote("/".join(parts[2:]))
            evidence = M24_FULL.evidence_path(code, filename)
            if not evidence:
                handler.send_json({"error": "La evidencia no existe o no superó integridad."}, 404); return True
            handler.send_file(evidence, download_name=evidence.name); return True
        if len(parts) == 1:
            detail = M24_RELEASE_GOVERNANCE.detail(con, parts[0].upper())
            handler.send_json(detail or {}, 200 if detail else 404); return True
        handler.send_json({"error": "Ruta de validación integral no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m24_full_post(handler, path, user):
    prefix = "/api/m24/full-validation/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):]
    code, _, action_path = suffix.partition("/")
    code = code.upper()
    if action_path not in {"approvals", "activation"}:
        return False
    if not _authorized(user):
        handler.send_json({"error": "Sin permisos para registrar decisiones de M24.4."}, 403); return True
    data = handler.read_json()
    con = core.db()
    try:
        if action_path == "approvals":
            result = M24_RELEASE_GOVERNANCE.decide(
                con, code, data.get("approval_type"), data.get("decision"), data.get("comment"), user
            )
        else:
            result = M24_RELEASE_GOVERNANCE.set_activation(
                con, code, data.get("action"), data.get("comment"), data.get("confirmation"), user
            )
        handler.send_json(result); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
