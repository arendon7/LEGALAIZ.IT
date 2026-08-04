from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M30_PARTICIPANTS


def handle_m30_participant_get(handler, path, user):
    prefix = "/api/m30/participants"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/me"}:
            result = M30_PARTICIPANTS.client_summary(con, user) if user.get("role") == "client" else M30_PARTICIPANTS.professional_summary(con, user)
            handler.send_json(result); return True
        if path == f"{prefix}/summary":
            handler.send_json(M30_PARTICIPANTS.professional_summary(con, user)); return True
        if path == f"{prefix}/export":
            body = M30_PARTICIPANTS.export_snapshot(con, user)
            handler.send_bytes(body, "application/json", "LegalAIZit_M30_2_participantes_piloto.json"); return True
        handler.send_json({"error": "Ruta M30.2 no encontrada."}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    finally:
        con.close()


def handle_m30_participant_post(handler, path, user):
    prefix = "/api/m30/participants/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "invitations":
            result = M30_PARTICIPANTS.invite(con, data, user)
        elif suffix == "respond":
            result = M30_PARTICIPANTS.respond(con, data, user)
        elif suffix == "withdraw":
            result = M30_PARTICIPANTS.withdraw(con, data, user)
        elif suffix == "support":
            result = M30_PARTICIPANTS.create_support_ticket(con, data, user)
        else:
            return False
        handler.send_json(result); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError, TypeError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
