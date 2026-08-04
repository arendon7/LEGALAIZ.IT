from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M30_SIMULATION


def handle_m30_simulation_get(handler, path, user):
    prefix="/api/m30/simulation"
    if not path.startswith(prefix): return False
    con=core.db()
    try:
        if path in {prefix,f"{prefix}/summary"}:
            handler.send_json(M30_SIMULATION.summary(con,user)); return True
        if path==f"{prefix}/export":
            handler.send_bytes(M30_SIMULATION.export_snapshot(con,user),"application/json","LegalAIZit_M30_4_simulacion_cohorte.json"); return True
        handler.send_json({"error":"Ruta M30.4 no encontrada."},404); return True
    except PermissionError as exc:
        handler.send_json({"error":str(exc)},403); return True
    finally: con.close()


def handle_m30_simulation_post(handler,path,user):
    prefix="/api/m30/simulation/"
    if not path.startswith(prefix): return False
    suffix=path[len(prefix):].strip("/"); data=handler.read_json(); con=core.db()
    try:
        if suffix=="runs": result=M30_SIMULATION.create_run(con,data,user)
        elif suffix.startswith("runs/") and suffix.endswith("/execute"):
            result=M30_SIMULATION.execute_run(con,suffix.split("/")[1],data,user)
        elif suffix.startswith("runs/") and suffix.endswith("/decision"):
            result=M30_SIMULATION.record_decision(con,suffix.split("/")[1],data,user)
        else: return False
        handler.send_json(result); return True
    except LookupError as exc:
        handler.send_json({"error":str(exc)},404); return True
    except PermissionError as exc:
        handler.send_json({"error":str(exc)},403); return True
    except (ValueError,KeyError,TypeError) as exc:
        handler.send_json({"error":str(exc)},422); return True
    finally: con.close()
