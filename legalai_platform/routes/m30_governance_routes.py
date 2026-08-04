from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M30_GOVERNANCE


def handle_m30_governance_get(handler, path, user):
    prefix = "/api/m30/governance"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/me"}:
            result = M30_GOVERNANCE.client_summary(con, user) if user.get("role") == "client" else M30_GOVERNANCE.summary(con, user)
            handler.send_json(result); return True
        if path == f"{prefix}/summary":
            handler.send_json(M30_GOVERNANCE.summary(con, user)); return True
        if path == f"{prefix}/export":
            body = M30_GOVERNANCE.export_snapshot(con, user)
            handler.send_bytes(body, "application/json", "LegalAIZit_M30_3_gobernanza_piloto.json"); return True
        handler.send_json({"error": "Ruta M30.3 no encontrada."}, 404); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError, TypeError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()


def handle_m30_governance_post(handler, path, user):
    prefix = "/api/m30/governance/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "communications":
            result = M30_GOVERNANCE.queue_communication(con, data, user)
        elif suffix.startswith("communications/"):
            communication_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.update_communication(con, communication_id, data, user)
        elif suffix == "incidents":
            result = M30_GOVERNANCE.report_incident(con, data, user)
        elif suffix.startswith("incidents/"):
            incident_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.triage_incident(con, incident_id, data, user)
        elif suffix == "retention":
            result = M30_GOVERNANCE.create_retention_request(con, data, user)
        elif suffix.startswith("retention/") and suffix.endswith("/approve"):
            request_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.approve_retention(con, request_id, data, user)
        elif suffix.startswith("retention/") and suffix.endswith("/execute"):
            request_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.execute_retention(con, request_id, data, user)
        elif suffix == "closures":
            result = M30_GOVERNANCE.prepare_closure(con, data, user)
        elif suffix.startswith("closures/") and suffix.endswith("/approve"):
            closure_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.approve_closure(con, closure_id, data, user)
        elif suffix.startswith("closures/") and suffix.endswith("/execute"):
            closure_id = suffix.split("/")[1]
            result = M30_GOVERNANCE.execute_closure(con, closure_id, data, user)
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
