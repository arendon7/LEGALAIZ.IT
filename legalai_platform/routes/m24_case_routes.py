from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M24_CASE_JOURNEY


def handle_m24_case_get(handler, path, user):
    prefix = "/api/m24/case-journeys"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path == prefix:
            handler.send_json(M24_CASE_JOURNEY.list_for_actor(con, user)); return True
        suffix = path[len(prefix):].strip("/")
        if suffix and "/" not in suffix:
            try:
                handler.send_json(M24_CASE_JOURNEY.ensure_case(con, suffix, user)); return True
            except LookupError as exc:
                handler.send_json({"error": str(exc)}, 404); return True
        handler.send_json({"error": "Ruta de recorrido jurídico no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m24_case_post(handler, path, user):
    prefix = "/api/m24/case-journeys/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):]
    case_id, _, action = suffix.partition("/")
    if action not in {"transition", "follow-up"}:
        return False
    data = handler.read_json()
    con = core.db()
    try:
        if action == "transition":
            result = M24_CASE_JOURNEY.transition(
                con,
                case_id,
                data.get("target_state"),
                data.get("reason"),
                data.get("evidence") or {},
                data.get("confirmation") or "",
                user,
            )
        else:
            result = M24_CASE_JOURNEY.update_follow_up(
                con,
                case_id,
                data.get("follow_up_id"),
                data.get("status"),
                data.get("note"),
                user,
            )
        handler.send_json(result); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
