from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M24_PROFESSIONAL_NETWORK


def handle_m24_professional_get(handler, path, user):
    prefix = "/api/m24/professional-network"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/me"}:
            handler.send_json(M24_PROFESSIONAL_NETWORK.summary(con, user)); return True
        handler.send_json({"error": "Ruta de red profesional no encontrada."}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    finally:
        con.close()


def handle_m24_professional_post(handler, path, user):
    prefix = "/api/m24/professional-network/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "profiles/invite":
            result = M24_PROFESSIONAL_NETWORK.invite_profile(con, data, user)
        elif suffix == "profiles/accept":
            result = M24_PROFESSIONAL_NETWORK.accept_invitation(con, data, user)
        elif suffix == "profiles/verify":
            result = M24_PROFESSIONAL_NETWORK.verify_profile(con, data, user)
        elif suffix == "profiles/availability":
            result = M24_PROFESSIONAL_NETWORK.set_availability(con, data, user)
        elif suffix == "assignments/offer":
            result = M24_PROFESSIONAL_NETWORK.offer_assignment(con, data, user)
        elif suffix.startswith("assignments/") and suffix.endswith("/decision"):
            assignment_id = suffix.split("/")[1]
            result = M24_PROFESSIONAL_NETWORK.decide_assignment(con, assignment_id, data, user)
        elif suffix.startswith("assignments/") and suffix.endswith("/resolve-conflict"):
            assignment_id = suffix.split("/")[1]
            result = M24_PROFESSIONAL_NETWORK.resolve_conflict(con, assignment_id, data, user)
        elif suffix.startswith("assignments/") and suffix.endswith("/complete"):
            assignment_id = suffix.split("/")[1]
            result = M24_PROFESSIONAL_NETWORK.complete_assignment(con, assignment_id, data, user)
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
