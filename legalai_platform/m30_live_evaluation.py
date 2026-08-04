from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class M30LivePilotEvaluationCenter:
    """Evaluación inmutable de una cohorte real limitada y decisión go/no-go.

    Solo consume señales estructuradas ya existentes. No exporta relatos del caso,
    datos de contacto ni contenido documental y nunca habilita producción pública.
    """

    def __init__(self, root: Path, audit_fn):
        self.root = Path(root).resolve()
        self.audit_fn = audit_fn
        self.policy_path = self.root / "config" / "m30_5_live_pilot_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    @staticmethod
    def _json(raw: Any, default: Any):
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw or "")
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _table(con, name: str) -> bool:
        return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m30_live_evaluation(
              id TEXT PRIMARY KEY,cohort_id TEXT NOT NULL,cohort_title TEXT NOT NULL,status TEXT NOT NULL,
              metrics_json TEXT NOT NULL,checks_json TEXT NOT NULL,comparison_json TEXT NOT NULL,
              recommendation TEXT NOT NULL,proposed_decision TEXT NOT NULL DEFAULT '',proposal_reason TEXT NOT NULL DEFAULT '',
              proposed_by_id TEXT,proposed_by_name TEXT,proposed_at TEXT,formal_decision TEXT NOT NULL DEFAULT '',
              created_by_id TEXT NOT NULL,created_by_name TEXT NOT NULL,created_at TEXT NOT NULL,finalized_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_m30_live_eval_created ON m30_live_evaluation(created_at);
            CREATE TABLE IF NOT EXISTS m30_live_approval(
              id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,approval_type TEXT NOT NULL CHECK(approval_type IN ('legal','qa')),
              decision TEXT NOT NULL CHECK(decision IN ('approved','rejected')),actor_id TEXT NOT NULL,actor_name TEXT NOT NULL,
              actor_role TEXT NOT NULL,comment TEXT NOT NULL,created_at TEXT NOT NULL,
              UNIQUE(evaluation_id,approval_type),FOREIGN KEY(evaluation_id) REFERENCES m30_live_evaluation(id)
            );
            """
        )

    def _require_professional(self, actor: dict[str, Any]) -> None:
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La evaluación del piloto exige rol profesional.")

    def _cohort(self, con):
        if not self._table(con, "m25_pilot_cohort"):
            return None
        return con.execute(
            "SELECT * FROM m25_pilot_cohort WHERE status IN ('planned','active','completed') ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    def _plans(self, con, cohort_id: str) -> list[dict[str, Any]]:
        if not self._table(con, "m25_pilot_case_plan"):
            return []
        return [dict(r) for r in con.execute(
            "SELECT * FROM m25_pilot_case_plan WHERE cohort_id=? ORDER BY product_code,archetype", (cohort_id,)
        ).fetchall()]

    @staticmethod
    def _avg(rows, key: str) -> float:
        values=[float(row[key]) for row in rows if row.get(key) is not None]
        return round(sum(values)/len(values),2) if values else 0.0

    def _live_metrics(self, con, cohort) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if not cohort:
            return {"cohort_exists":False,"total_plans":0,"completed_cases":0}, []
        cohort_id=cohort["id"]; plans=self._plans(con,cohort_id); case_ids=[p["case_id"] for p in plans if p.get("case_id")]
        total=len(plans); completed=sum(p["status"]=="completed" for p in plans); blocked=sum(p["status"]=="blocked" for p in plans)
        participants=[]
        if self._table(con,"m30_pilot_participant"):
            participants=[dict(r) for r in con.execute("SELECT * FROM m30_pilot_participant WHERE cohort_id=?",(cohort_id,)).fetchall()]
        accepted=[p for p in participants if p["status"]=="accepted"]
        consented=[p for p in accepted if p.get("consent_version") and p.get("consent_hash")]
        feedback=[]
        if case_ids and self._table(con,"m24_pilot_feedback"):
            q=",".join("?" for _ in case_ids)
            feedback=[dict(r) for r in con.execute(f"SELECT clarity,ease,confidence,goal_met,case_id FROM m24_pilot_feedback WHERE case_id IN ({q})",tuple(case_ids)).fetchall()]
        support=[]
        if self._table(con,"m30_pilot_support_ticket"):
            support=[dict(r) for r in con.execute("SELECT status,due_at,closed_at,priority FROM m30_pilot_support_ticket WHERE cohort_id=?",(cohort_id,)).fetchall()]
        closed=[r for r in support if r["status"]=="closed" and r.get("closed_at")]
        within=0
        for row in closed:
            try: within += int(datetime.fromisoformat(str(row["closed_at"]).replace("Z","+00:00")) <= datetime.fromisoformat(str(row["due_at"]).replace("Z","+00:00")))
            except (TypeError,ValueError): pass
        incidents=[]
        if self._table(con,"m24_pilot_incident"):
            if case_ids:
                q=",".join("?" for _ in case_ids)
                incidents=[dict(r) for r in con.execute(f"SELECT severity,status FROM m24_pilot_incident WHERE case_id IS NULL OR case_id IN ({q})",tuple(case_ids)).fetchall()]
            else:
                incidents=[dict(r) for r in con.execute("SELECT severity,status FROM m24_pilot_incident WHERE case_id IS NULL").fetchall()]
        manual=[]
        if self._table(con,"m24_pilot_manual_validation"):
            manual=[dict(r) for r in con.execute("SELECT status FROM m24_pilot_manual_validation").fetchall()]
        observations=[]
        plan_ids=[p["id"] for p in plans]
        if plan_ids and self._table(con,"m30_pilot_observation"):
            q=",".join("?" for _ in plan_ids)
            observations=[dict(r) for r in con.execute(f"SELECT outcome,case_plan_id FROM m30_pilot_observation WHERE case_plan_id IN ({q})",tuple(plan_ids)).fetchall()]
        product_metrics=[]
        for code in self.policy["pilot_products"]:
            pp=[p for p in plans if p["product_code"]==code]; pcases={p["case_id"] for p in pp if p.get("case_id")}
            pf=[f for f in feedback if f.get("case_id") in pcases]
            product_metrics.append({"product_code":code,"planned":len(pp),"completed":sum(p["status"]=="completed" for p in pp),"feedback_count":len(pf),"average_clarity":self._avg(pf,"clarity"),"average_ease":self._avg(pf,"ease"),"average_confidence":self._avg(pf,"confidence"),"goal_met_rate":round(sum(bool(f["goal_met"]) for f in pf)/len(pf),3) if pf else 0.0})
        qa_ready=sum(bool(p.get("qa_reviewer_id")) and len(str(p.get("evidence_note") or ""))>=12 for p in plans if p["status"]=="completed")
        metrics={
          "cohort_exists":True,"cohort_status":cohort["status"],"total_plans":total,"completed_cases":completed,"blocked_cases":blocked,
          "completion_rate":round(completed/total,3) if total else 0.0,"accepted_participants":len(accepted),"consented_participants":len(consented),
          "consent_coverage":round(len(consented)/len(accepted),3) if accepted else 0.0,"feedback_responses":len(feedback),
          "average_clarity":self._avg(feedback,"clarity"),"average_ease":self._avg(feedback,"ease"),"average_confidence":self._avg(feedback,"confidence"),
          "goal_met_rate":round(sum(bool(f["goal_met"]) for f in feedback)/len(feedback),3) if feedback else 0.0,
          "manual_validation_rate":round(sum(r["status"]=="passed" for r in manual)/len(manual),3) if manual else 0.0,
          "document_qa_rate":round(qa_ready/completed,3) if completed else 0.0,"support_tickets":len(support),
          "support_sla_rate":round(within/len(closed),3) if closed else (1.0 if not support else 0.0),
          "friction_rate":round(sum(r["outcome"] in {"friction","blocked"} for r in observations)/len(observations),3) if observations else 0.0,
          "high_or_critical_incidents":sum(r["severity"] in {"high","critical"} and r["status"]!="closed" for r in incidents),
          "product_coverage":sum(row["completed"]>0 and row["feedback_count"]>0 for row in product_metrics)
        }
        return metrics,product_metrics

    def _checks(self, metrics: dict[str, Any]) -> dict[str, bool]:
        t=self.policy["thresholds"]
        return {
          "minimum_real_cases":metrics.get("completed_cases",0)>=self.policy["minimum_real_cases"],
          "product_coverage":metrics.get("product_coverage",0)>=self.policy["minimum_product_coverage"],
          "completion_rate":metrics.get("completion_rate",0)>=t["completion_rate"],"average_clarity":metrics.get("average_clarity",0)>=t["average_clarity"],
          "average_ease":metrics.get("average_ease",0)>=t["average_ease"],"average_confidence":metrics.get("average_confidence",0)>=t["average_confidence"],
          "goal_met_rate":metrics.get("goal_met_rate",0)>=t["goal_met_rate"],"consent_coverage":metrics.get("consent_coverage",0)>=t["consent_coverage"],
          "manual_validation_rate":metrics.get("manual_validation_rate",0)>=t["manual_validation_rate"],"document_qa_rate":metrics.get("document_qa_rate",0)>=t["document_qa_rate"],
          "support_sla_rate":metrics.get("support_sla_rate",0)>=t["support_sla_rate"],"friction_rate":metrics.get("friction_rate",0)<=t["friction_rate_max"],
          "incidents":metrics.get("high_or_critical_incidents",0)<=t["high_or_critical_incidents_max"],"blocked_cases":metrics.get("blocked_cases",0)<=t["blocked_cases_max"]
        }

    @staticmethod
    def _recommend(metrics: dict[str, Any], checks: dict[str, bool]) -> str:
        if metrics.get("high_or_critical_incidents",0)>0 or metrics.get("manual_validation_rate",0)<1 or metrics.get("document_qa_rate",0)<1:
            return "no_go"
        if all(checks.values()): return "go_limited"
        return "extend_pilot"

    def _simulation(self, con) -> dict[str, Any] | None:
        if not self._table(con,"m30_simulation_run"): return None
        row=con.execute("SELECT id,title,profile,status,metrics_json,recommendation,decision,executed_at FROM m30_simulation_run WHERE status IN ('completed','decision_recorded') ORDER BY COALESCE(executed_at,created_at) DESC LIMIT 1").fetchone()
        if not row: return None
        item=dict(row); item["metrics"]=self._json(item.pop("metrics_json","{}"),{}); return item

    @staticmethod
    def _comparison(metrics: dict[str, Any], simulation: dict[str, Any] | None) -> dict[str, Any]:
        if not simulation: return {"available":False,"rows":[]}
        sim=simulation.get("metrics") or {}; keys=["completion_rate","average_clarity","average_ease","average_confidence","goal_met_rate","support_rate","high_or_critical_incidents"]
        rows=[]
        live_map={**metrics,"support_rate":round(metrics.get("support_tickets",0)/metrics.get("completed_cases",1),3) if metrics.get("completed_cases") else 0.0}
        for key in keys:
            a=sim.get(key); b=live_map.get(key)
            if a is None or b is None: continue
            rows.append({"metric":key,"simulation":a,"live":b,"delta":round(float(b)-float(a),3)})
        return {"available":True,"simulation_id":simulation["id"],"simulation_title":simulation["title"],"rows":rows}

    def _approvals(self, con, evaluation_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in con.execute("SELECT * FROM m30_live_approval WHERE evaluation_id=? ORDER BY approval_type",(evaluation_id,)).fetchall()]

    def _evaluation(self, con, row) -> dict[str, Any]:
        item=dict(row); item["metrics"]=self._json(item.pop("metrics_json"),{}); item["checks"]=self._json(item.pop("checks_json"),{}); item["comparison"]=self._json(item.pop("comparison_json"),{}); item["approvals"]=self._approvals(con,item["id"]); return item

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor); self.ensure_schema(con)
        cohort=self._cohort(con); metrics,products=self._live_metrics(con,cohort); checks=self._checks(metrics); simulation=self._simulation(con); comparison=self._comparison(metrics,simulation)
        rows=con.execute("SELECT * FROM m30_live_evaluation ORDER BY created_at DESC LIMIT 30").fetchall(); evaluations=[self._evaluation(con,r) for r in rows]
        return {"schema":"legalaizit-m30-5-live-summary-v1","milestone":"M30.5","version":self.policy["version"],"policy":self.policy,
          "cohort":{"id":cohort["id"],"title":cohort["title"],"status":cohort["status"]} if cohort else None,"live_metrics":metrics,"product_metrics":products,
          "checks":checks,"passed_checks":sum(checks.values()),"total_checks":len(checks),"recommendation":self._recommend(metrics,checks),"comparison":comparison,
          "latest_evaluation":evaluations[0] if evaluations else None,"evaluations":evaluations,"production_authorized":False,
          "notice":"Un resultado go_limited autoriza únicamente continuar el piloto controlado. Producción pública, pagos reales y entrega automática permanecen bloqueados."}

    def create_evaluation(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role")!="admin": raise PermissionError("Solo administración puede congelar una evaluación real.")
        self.ensure_schema(con)
        if str(data.get("confirmation") or "").strip()!=self.policy["confirmations"]["snapshot"]: raise ValueError("Confirmación de evaluación incorrecta.")
        cohort=self._cohort(con)
        if not cohort: raise ValueError("No existe una cohorte real para evaluar.")
        metrics,products=self._live_metrics(con,cohort); checks=self._checks(metrics)
        if metrics.get("accepted_participants",0)<self.policy["minimum_real_cases"] or metrics.get("feedback_responses",0)<self.policy["minimum_real_cases"]:
            raise ValueError("Se requieren al menos cuatro participantes aceptados y cuatro respuestas de experiencia para crear la evaluación.")
        comparison=self._comparison(metrics,self._simulation(con)); eid=str(uuid.uuid4()); now=self.now(); recommendation=self._recommend(metrics,checks)
        snapshot={**metrics,"product_metrics":products}
        con.execute("INSERT INTO m30_live_evaluation(id,cohort_id,cohort_title,status,metrics_json,checks_json,comparison_json,recommendation,created_by_id,created_by_name,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (eid,cohort["id"],cohort["title"],"snapshot",json.dumps(snapshot,ensure_ascii=False),json.dumps(checks),json.dumps(comparison,ensure_ascii=False),recommendation,str(actor.get("id")),self._actor_name(actor),now))
        self.audit_fn(con,str(actor.get("id")),"m30_live_evaluation",eid,"create",{"recommendation":recommendation,"cohort_id":cohort["id"]}); con.commit(); return self.summary(con,actor)

    def propose_decision(self, con, evaluation_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role")!="admin": raise PermissionError("Solo administración puede proponer la decisión.")
        self.ensure_schema(con); row=con.execute("SELECT * FROM m30_live_evaluation WHERE id=?",(evaluation_id,)).fetchone()
        if not row: raise LookupError("Evaluación no encontrada.")
        if row["status"] not in {"snapshot","rejected"}: raise ValueError("La evaluación ya tiene una propuesta vigente o fue formalizada.")
        if str(data.get("confirmation") or "").strip()!=self.policy["confirmations"]["proposal"]: raise ValueError("Confirmación de propuesta incorrecta.")
        decision=str(data.get("decision") or ""); reason=" ".join(str(data.get("reason") or "").split())[:1200]
        if decision not in self.policy["decisions"]: raise ValueError("Decisión no permitida.")
        if len(reason)<30: raise ValueError("Documente un fundamento verificable de al menos 30 caracteres.")
        con.execute("DELETE FROM m30_live_approval WHERE evaluation_id=?",(evaluation_id,)); now=self.now()
        con.execute("UPDATE m30_live_evaluation SET status='proposed',proposed_decision=?,proposal_reason=?,proposed_by_id=?,proposed_by_name=?,proposed_at=?,formal_decision='',finalized_at=NULL WHERE id=?",
          (decision,reason,str(actor.get("id")),self._actor_name(actor),now,evaluation_id))
        self.audit_fn(con,str(actor.get("id")),"m30_live_evaluation",evaluation_id,"propose",{"decision":decision}); con.commit(); return self.summary(con,actor)

    def approve(self, con, evaluation_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con); row=con.execute("SELECT * FROM m30_live_evaluation WHERE id=?",(evaluation_id,)).fetchone()
        if not row: raise LookupError("Evaluación no encontrada.")
        if row["status"]!="proposed": raise ValueError("La evaluación no tiene una propuesta pendiente.")
        approval_type=str(data.get("approval_type") or ""); decision=str(data.get("decision") or "approved")
        if approval_type=="legal" and actor.get("role")!="specialist": raise PermissionError("La aprobación jurídica exige especialista.")
        if approval_type=="qa" and actor.get("role")!="admin": raise PermissionError("La aprobación QA exige administración.")
        if approval_type not in {"legal","qa"} or decision not in {"approved","rejected"}: raise ValueError("Aprobación inválida.")
        phrase=self.policy["confirmations"]["legal_approval" if approval_type=="legal" else "qa_approval"]
        if str(data.get("confirmation") or "").strip()!=phrase: raise ValueError("Confirmación de aprobación incorrecta.")
        existing=con.execute("SELECT actor_id FROM m30_live_approval WHERE evaluation_id=?",(evaluation_id,)).fetchall()
        if any(r["actor_id"]==str(actor.get("id")) for r in existing): raise ValueError("Una misma persona no puede emitir las dos aprobaciones.")
        comment=" ".join(str(data.get("comment") or "").split())[:800]
        if len(comment)<12: raise ValueError("Incluya una justificación breve de la aprobación.")
        con.execute("INSERT INTO m30_live_approval(id,evaluation_id,approval_type,decision,actor_id,actor_name,actor_role,comment,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET evaluation_id=excluded.evaluation_id,approval_type=excluded.approval_type,decision=excluded.decision,actor_id=excluded.actor_id,actor_name=excluded.actor_name,actor_role=excluded.actor_role,comment=excluded.comment,created_at=excluded.created_at",
          (str(uuid.uuid4()),evaluation_id,approval_type,decision,str(actor.get("id")),self._actor_name(actor),str(actor.get("role")),comment,self.now()))
        approvals=self._approvals(con,evaluation_id)
        if any(a["decision"]=="rejected" for a in approvals):
            con.execute("UPDATE m30_live_evaluation SET status='rejected' WHERE id=?",(evaluation_id,))
        elif {a["approval_type"] for a in approvals if a["decision"]=="approved"}=={"legal","qa"}:
            con.execute("UPDATE m30_live_evaluation SET status='formalized',formal_decision=proposed_decision,finalized_at=? WHERE id=?",(self.now(),evaluation_id))
        self.audit_fn(con,str(actor.get("id")),"m30_live_evaluation",evaluation_id,"approve",{"type":approval_type,"decision":decision}); con.commit(); return self.summary(con,actor)

    def export_snapshot(self, con, actor: dict[str, Any]) -> bytes:
        summary=self.summary(con,actor); latest=summary.get("latest_evaluation")
        safe=None
        if latest:
            safe={k:v for k,v in latest.items() if k not in {"created_by_id","created_by_name","proposed_by_id","proposed_by_name","approvals"}}
            safe["approvals"]=[{"approval_type":a["approval_type"],"decision":a["decision"],"actor_role":a["actor_role"],"created_at":a["created_at"]} for a in latest.get("approvals",[])]
        payload={"schema":"legalaizit-m30-5-export-v1","milestone":"M30.5","version":self.policy["version"],"evaluation":safe,"production_authorized":False,"blocked":["public_production","real_payments","automatic_document_delivery"]}
        return json.dumps(payload,ensure_ascii=False,indent=2).encode("utf-8")
