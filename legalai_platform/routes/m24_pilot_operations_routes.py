from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M24_PILOT_OPERATIONS


def handle_m24_pilot_operations_get(handler, path, user):
    prefix = "/api/m24/pilot-operations"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/me"}:
            handler.send_json(M24_PILOT_OPERATIONS.summary(con, user)); return True
        if path == f"{prefix}/release-gate":
            if user.get("role") not in {"admin", "specialist"}:
                handler.send_json({"error": "La compuerta de salida exige rol profesional."}, 403); return True
            handler.send_json(M24_PILOT_OPERATIONS.release_gate(con)); return True
        handler.send_json({"error": "Ruta de operación del piloto no encontrada."}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    finally:
        con.close()


def handle_m24_pilot_operations_post(handler, path, user):
    prefix = "/api/m24/pilot-operations/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "enrollment":
            result = M24_PILOT_OPERATIONS.enroll(con, data, user)
        elif suffix == "events":
            result = M24_PILOT_OPERATIONS.record_event(con, data, user)
        elif suffix == "feedback":
            result = M24_PILOT_OPERATIONS.submit_feedback(con, data, user)
        elif suffix == "incidents":
            result = M24_PILOT_OPERATIONS.report_incident(con, data, user)
        elif suffix == "manual-validations":
            result = M24_PILOT_OPERATIONS.set_manual_validation(con, data, user)
        elif suffix == "control":
            result = M24_PILOT_OPERATIONS.set_control(con, data, user)
        elif suffix.startswith("incidents/") and suffix.endswith("/triage"):
            incident_id = suffix.split("/")[1]
            result = M24_PILOT_OPERATIONS.triage_incident(con, incident_id, data, user)
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
