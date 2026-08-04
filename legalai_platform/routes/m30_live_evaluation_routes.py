from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M30_LIVE_EVALUATION


def handle_m30_live_evaluation_get(handler,path,user):
    prefix="/api/m30/live-evaluation"
    if not path.startswith(prefix): return False
    con=core.db()
    try:
        if path in {prefix,f"{prefix}/summary"}: handler.send_json(M30_LIVE_EVALUATION.summary(con,user)); return True
        if path==f"{prefix}/export": handler.send_bytes(M30_LIVE_EVALUATION.export_snapshot(con,user),"application/json","LegalAIZit_M30_5_evaluacion_go_no_go.json"); return True
        handler.send_json({"error":"Ruta M30.5 no encontrada."},404); return True
    except PermissionError as exc: handler.send_json({"error":str(exc)},403); return True
    finally: con.close()


def handle_m30_live_evaluation_post(handler,path,user):
    prefix="/api/m30/live-evaluation/"
    if not path.startswith(prefix): return False
    suffix=path[len(prefix):].strip("/"); data=handler.read_json(); con=core.db()
    try:
        if suffix=="evaluations": result=M30_LIVE_EVALUATION.create_evaluation(con,data,user)
        elif suffix.startswith("evaluations/") and suffix.endswith("/proposal"):
            result=M30_LIVE_EVALUATION.propose_decision(con,suffix.split("/")[1],data,user)
        elif suffix.startswith("evaluations/") and suffix.endswith("/approvals"):
            result=M30_LIVE_EVALUATION.approve(con,suffix.split("/")[1],data,user)
        else: return False
        handler.send_json(result); return True
    except LookupError as exc: handler.send_json({"error":str(exc)},404); return True
    except PermissionError as exc: handler.send_json({"error":str(exc)},403); return True
    except (ValueError,KeyError,TypeError) as exc: handler.send_json({"error":str(exc)},422); return True
    finally: con.close()
