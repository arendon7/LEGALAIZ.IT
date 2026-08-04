from __future__ import annotations

from urllib.parse import unquote

import core_v11 as core
from legalai_platform.runtime_registry import M24_PILOT, M24_PILOT_GOVERNANCE


def _authorized(user):
    return user.get("role") in {"specialist", "admin"}


def handle_m24_pilot_get(handler, path, user):
    prefix = "/api/m24/pilot-validation"
    if not path.startswith(prefix):
        return False
    if not _authorized(user):
        handler.send_json({"error": "Solo especialistas y administradores pueden consultar el piloto jurídico."}, 403)
        return True
    con = core.db()
    try:
        if path == prefix:
            handler.send_json(M24_PILOT_GOVERNANCE.summary(con)); return True
        suffix = path[len(prefix):].strip("/")
        parts = suffix.split("/") if suffix else []
        if len(parts) >= 3 and parts[1] == "evidence":
            code = parts[0].upper(); filename = unquote("/".join(parts[2:]))
            evidence = M24_PILOT.evidence_path(code, filename)
            if not evidence:
                handler.send_json({"error": "La evidencia no existe o no superó integridad."}, 404); return True
            handler.send_file(evidence, download_name=evidence.name); return True
        if len(parts) == 1:
            detail = M24_PILOT_GOVERNANCE.detail(con, parts[0].upper())
            handler.send_json(detail or {}, 200 if detail else 404); return True
        handler.send_json({"error": "Ruta de piloto no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m24_pilot_post(handler, path, user):
    prefix = "/api/m24/pilot-validation/"
    if not path.startswith(prefix) or not path.endswith("/approvals"):
        return False
    if not _authorized(user):
        handler.send_json({"error": "Sin permisos para registrar decisiones del piloto."}, 403); return True
    code = path[len(prefix):].split("/", 1)[0].upper()
    data = handler.read_json()
    con = core.db()
    try:
        result = M24_PILOT_GOVERNANCE.decide(
            con, code, data.get("approval_type"), data.get("decision"), data.get("comment"), user
        )
        handler.send_json(result); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
