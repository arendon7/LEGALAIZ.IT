from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M25_PILOT_READINESS


def handle_m25_readiness_get(handler, path, user):
    prefix = "/api/m25/readiness"
    if not path.startswith(prefix):
        return False
    if user.get("role") not in {"admin", "specialist"}:
        handler.send_json({"error": "La auditoría M25 exige rol profesional."}, 403)
        return True
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/report"}:
            handler.send_json(M25_PILOT_READINESS.report(con)); return True
        handler.send_json({"error": "Ruta M25 no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m25_readiness_post(handler, path, user):
    prefix = "/api/m25/readiness/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "cohorts":
            result = M25_PILOT_READINESS.create_cohort(con, data, user)
        elif suffix.startswith("plans/"):
            plan_id = suffix.split("/")[1]
            result = M25_PILOT_READINESS.update_case_plan(con, plan_id, data, user)
        elif suffix.startswith("cohorts/") and suffix.endswith("/archive"):
            cohort_id = suffix.split("/")[1]
            result = M25_PILOT_READINESS.archive_cohort(con, cohort_id, data, user)
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
