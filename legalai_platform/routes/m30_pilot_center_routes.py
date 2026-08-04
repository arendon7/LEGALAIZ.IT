from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M30_PILOT_CENTER


def handle_m30_pilot_center_get(handler, path, user):
    prefix = "/api/m30/pilot-center"
    if not path.startswith(prefix):
        return False
    if user.get("role") not in {"admin", "specialist"}:
        handler.send_json({"error": "El Centro Operativo del Piloto exige rol profesional."}, 403)
        return True
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/summary"}:
            handler.send_json(M30_PILOT_CENTER.summary(con, user)); return True
        if path == f"{prefix}/export":
            body = M30_PILOT_CENTER.export_snapshot(con, user)
            handler.send_bytes(body, "application/json", "LegalAIZit_M30_1_snapshot_piloto.json"); return True
        handler.send_json({"error": "Ruta M30.1 no encontrada."}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    finally:
        con.close()


def handle_m30_pilot_center_post(handler, path, user):
    prefix = "/api/m30/pilot-center/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix.startswith("plans/"):
            plan_id = suffix.split("/")[1]
            result = M30_PILOT_CENTER.update_plan(con, plan_id, data, user)
        elif suffix.startswith("cohorts/") and "/teams/" in suffix:
            parts = suffix.split("/")
            cohort_id, product_code = parts[1], parts[3]
            result = M30_PILOT_CENTER.assign_product_team(con, cohort_id, product_code, data, user)
        elif suffix.startswith("cohorts/") and suffix.endswith("/activate"):
            cohort_id = suffix.split("/")[1]
            result = M30_PILOT_CENTER.activate_cohort(con, cohort_id, data, user)
        elif suffix == "support-tickets":
            result = M30_PILOT_CENTER.create_ticket(con, data, user)
        elif suffix.startswith("support-tickets/"):
            ticket_id = suffix.split("/")[1]
            result = M30_PILOT_CENTER.update_ticket(con, ticket_id, data, user)
        elif suffix == "observations":
            result = M30_PILOT_CENTER.record_observation(con, data, user)
        elif suffix == "decisions":
            result = M30_PILOT_CENTER.record_decision(con, data, user)
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
