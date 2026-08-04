from __future__ import annotations

from legalai_platform.release_metadata import MILESTONE

import core_v11 as core
from legalai_platform.runtime_registry import M31_PREPRODUCTION


def handle_m31_preproduction_get(handler, path, user):
    prefix = "/api/m31/preproduction"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/summary"}:
            handler.send_json(M31_PREPRODUCTION.summary(con, user)); return True
        if path == f"{prefix}/export":
            handler.send_bytes(M31_PREPRODUCTION.export_latest(con, user), "application/json", "LegalAIZit_M31_1_preproduction.json"); return True
        handler.send_json({"error": f"Ruta {MILESTONE} no encontrada."}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    finally:
        con.close()


def handle_m31_preproduction_post(handler, path, user):
    prefix = "/api/m31/preproduction/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):].strip("/")
    data = handler.read_json()
    con = core.db()
    try:
        if suffix == "snapshots":
            result = M31_PREPRODUCTION.create_snapshot(con, user)
        elif suffix == "backup-drills":
            result = M31_PREPRODUCTION.run_backup_drill(con, user, core.DB)
        elif suffix == "decisions":
            result = M31_PREPRODUCTION.record_decision(con, data, user)
        else:
            return False
        handler.send_json(result, 201); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, TypeError, KeyError, OSError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
