from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class M30PilotSimulationCenter:
    """Simulación sintética de una cohorte completa de piloto.

    No crea usuarios, expedientes, documentos ni consentimientos. Produce señales
    agregadas para probar compuertas y documentar una decisión limitada.
    """

    def __init__(self, root: Path, audit_fn):
        self.root = Path(root).resolve()
        self.audit_fn = audit_fn
        self.policy_path = self.root / "config" / "m30_4_simulated_cohort_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m30_simulation_run(
              id TEXT PRIMARY KEY,title TEXT NOT NULL,profile TEXT NOT NULL,status TEXT NOT NULL,
              target_cases INTEGER NOT NULL,metrics_json TEXT NOT NULL DEFAULT '{}',checks_json TEXT NOT NULL DEFAULT '{}',
              recommendation TEXT NOT NULL DEFAULT '',decision TEXT NOT NULL DEFAULT '',decision_reason TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL,created_by_name TEXT NOT NULL,created_at TEXT NOT NULL,executed_at TEXT,decided_at TEXT
            );
            CREATE TABLE IF NOT EXISTS m30_simulation_case(
              id TEXT PRIMARY KEY,run_id TEXT NOT NULL,sequence INTEGER NOT NULL,product_code TEXT NOT NULL,archetype TEXT NOT NULL,
              outcome TEXT NOT NULL,duration_bucket TEXT NOT NULL,clarity REAL NOT NULL,ease REAL NOT NULL,confidence REAL NOT NULL,
              goal_met INTEGER NOT NULL,manual_validation INTEGER NOT NULL,document_qa INTEGER NOT NULL,support_required INTEGER NOT NULL,
              incident_severity TEXT NOT NULL,issue_code TEXT NOT NULL,created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES m30_simulation_run(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_sim_case_run ON m30_simulation_case(run_id,sequence);
            """
        )

    def _require_professional(self, actor: dict[str, Any]) -> None:
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La simulación del piloto exige rol profesional.")

    def _rows(self, con, run_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in con.execute(
            "SELECT * FROM m30_simulation_case WHERE run_id=? ORDER BY sequence", (run_id,)
        ).fetchall()]

    @staticmethod
    def _json(raw: Any) -> dict[str, Any]:
        try:
            return json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

    def _run_dict(self, con, row) -> dict[str, Any]:
        item = dict(row)
        item["metrics"] = self._json(item.pop("metrics_json", "{}"))
        item["checks"] = self._json(item.pop("checks_json", "{}"))
        cases = self._rows(con, item["id"])
        item["case_count"] = len(cases)
        item["product_metrics"] = self._product_metrics(cases)
        return item

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        rows = con.execute("SELECT * FROM m30_simulation_run ORDER BY created_at DESC LIMIT 20").fetchall()
        runs = [self._run_dict(con, row) for row in rows]
        return {
            "schema": "legalaizit-m30-4-simulation-summary-v1", "milestone": "M30.4", "version": self.policy["version"],
            "policy": self.policy, "latest_run": runs[0] if runs else None, "runs": runs,
            "production_authorized": False,
            "notice": "La simulación usa únicamente datos sintéticos y no habilita producción pública, pagos ni entrega automática."
        }

    def create_run(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede crear una simulación.")
        self.ensure_schema(con)
        if str(data.get("confirmation") or "").strip() != self.policy["confirmations"]["create"]:
            raise ValueError("Confirmación de creación incorrecta.")
        title = " ".join(str(data.get("title") or "").split())[:120]
        if len(title) < 5:
            raise ValueError("Indique un nombre claro para la simulación.")
        profile = str(data.get("profile") or "baseline")
        if profile not in self.policy["profiles"]:
            raise ValueError("Perfil de simulación no permitido.")
        if con.execute("SELECT 1 FROM m30_simulation_run WHERE status='draft'").fetchone():
            raise ValueError("Ya existe una simulación pendiente de ejecutar.")
        run_id = str(uuid.uuid4()); now = self.now()
        con.execute("INSERT INTO m30_simulation_run(id,title,profile,status,target_cases,created_by,created_by_name,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (run_id,title,profile,"draft",self.policy["target_cases"],str(actor.get("id")),self._actor_name(actor),now))
        self.audit_fn(con,str(actor.get("id")),"m30_simulation_run",run_id,"create",{"profile":profile,"synthetic_only":True})
        con.commit()
        return self.summary(con,actor)

    def _synthetic_cases(self, profile: str) -> list[dict[str, Any]]:
        spec = self.policy["profiles"][profile]
        products = self.policy["pilot_products"]; archetypes = self.policy["archetypes"]
        rows=[]; sequence=0
        for product in products:
            for archetype in archetypes:
                sequence += 1
                outcome = "success"
                if sequence > 20-int(spec["blocked_cases"]): outcome = "blocked"
                elif sequence > 20-int(spec["blocked_cases"])-int(spec["friction_cases"]): outcome = "friction"
                offset=float(spec["score_offset"])
                complexity = 0.15 if archetype in {"contradictory_answers","high_risk_escalation"} else 0.0
                rows.append({
                    "sequence":sequence,"product_code":product,"archetype":archetype,"outcome":outcome,
                    "duration_bucket":"over_45m" if outcome=="blocked" else ("30_to_45m" if outcome=="friction" else "15_to_30m"),
                    "clarity":max(1.0,min(5.0,4.7+offset-complexity-(0.45 if outcome=="blocked" else 0.15 if outcome=="friction" else 0))),
                    "ease":max(1.0,min(5.0,4.5+offset-complexity-(0.55 if outcome=="blocked" else 0.2 if outcome=="friction" else 0))),
                    "confidence":max(1.0,min(5.0,4.6+offset-complexity-(0.5 if outcome=="blocked" else 0.15 if outcome=="friction" else 0))),
                    "goal_met":outcome!="blocked","manual_validation":outcome!="blocked" or profile!="stress",
                    "document_qa":outcome!="blocked","support_required":sequence<=int(spec["support_cases"]),
                    "incident_severity":"high" if sequence<=int(spec["high_incidents"]) else "none",
                    "issue_code":"none" if outcome=="success" else ("workflow_blocked" if outcome=="blocked" else "guidance_needed")
                })
        return rows

    @staticmethod
    def _avg(rows, key: str) -> float:
        return round(sum(float(row[key]) for row in rows)/len(rows),2) if rows else 0.0

    def _metrics(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total=len(rows); completed=sum(row["outcome"]!="blocked" for row in rows); success=sum(row["outcome"]=="success" for row in rows)
        return {
            "total_cases":total,"completed_cases":completed,"successful_cases":success,
            "completion_rate":round(completed/total,3) if total else 0,"success_rate":round(success/total,3) if total else 0,
            "average_clarity":self._avg(rows,"clarity"),"average_ease":self._avg(rows,"ease"),"average_confidence":self._avg(rows,"confidence"),
            "goal_met_rate":round(sum(bool(row["goal_met"]) for row in rows)/total,3) if total else 0,
            "manual_validation_rate":round(sum(bool(row["manual_validation"]) for row in rows)/total,3) if total else 0,
            "document_qa_rate":round(sum(bool(row["document_qa"]) for row in rows)/total,3) if total else 0,
            "support_rate":round(sum(bool(row["support_required"]) for row in rows)/total,3) if total else 0,
            "high_or_critical_incidents":sum(row["incident_severity"] in {"high","critical"} for row in rows),
            "friction_cases":sum(row["outcome"]=="friction" for row in rows),"blocked_cases":sum(row["outcome"]=="blocked" for row in rows)
        }

    def _checks(self, metrics: dict[str, Any]) -> dict[str, bool]:
        t=self.policy["thresholds"]
        return {
            "completion_rate":metrics["completion_rate"]>=t["completion_rate"],"success_rate":metrics["success_rate"]>=t["success_rate"],
            "average_clarity":metrics["average_clarity"]>=t["average_clarity"],"average_ease":metrics["average_ease"]>=t["average_ease"],
            "average_confidence":metrics["average_confidence"]>=t["average_confidence"],"goal_met_rate":metrics["goal_met_rate"]>=t["goal_met_rate"],
            "manual_validation_rate":metrics["manual_validation_rate"]>=t["manual_validation_rate"],"document_qa_rate":metrics["document_qa_rate"]>=t["document_qa_rate"],
            "support_rate":metrics["support_rate"]<=t["support_rate_max"],"incidents":metrics["high_or_critical_incidents"]<=t["high_or_critical_incidents_max"]
        }

    @staticmethod
    def _recommend(metrics: dict[str, Any], checks: dict[str, bool]) -> str:
        if metrics["high_or_critical_incidents"] or metrics["completion_rate"]<0.8 or metrics["success_rate"]<0.7:
            return "hold"
        if all(checks.values()): return "proceed_limited"
        return "extend"

    def _product_metrics(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        products=[]
        for code in self.policy["pilot_products"]:
            group=[row for row in rows if row["product_code"]==code]
            if group: products.append({"product_code":code,**self._metrics(group)})
        return products

    def execute_run(self, con, run_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin": raise PermissionError("Solo administración puede ejecutar la simulación.")
        self.ensure_schema(con)
        row=con.execute("SELECT * FROM m30_simulation_run WHERE id=?",(run_id,)).fetchone()
        if not row: raise LookupError("Simulación no encontrada.")
        if row["status"]!="draft": raise ValueError("La simulación ya fue ejecutada.")
        if str(data.get("confirmation") or "").strip()!=self.policy["confirmations"]["execute"]:
            raise ValueError("Confirmación de ejecución incorrecta.")
        rows=self._synthetic_cases(row["profile"]); now=self.now()
        for item in rows:
            con.execute("""INSERT INTO m30_simulation_case(id,run_id,sequence,product_code,archetype,outcome,duration_bucket,clarity,ease,confidence,goal_met,manual_validation,document_qa,support_required,incident_severity,issue_code,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (str(uuid.uuid4()),run_id,item["sequence"],item["product_code"],item["archetype"],item["outcome"],item["duration_bucket"],item["clarity"],item["ease"],item["confidence"],int(item["goal_met"]),int(item["manual_validation"]),int(item["document_qa"]),int(item["support_required"]),item["incident_severity"],item["issue_code"],now))
        metrics=self._metrics(rows); checks=self._checks(metrics); recommendation=self._recommend(metrics,checks)
        con.execute("UPDATE m30_simulation_run SET status='completed',metrics_json=?,checks_json=?,recommendation=?,executed_at=? WHERE id=?",
                    (json.dumps(metrics,ensure_ascii=False),json.dumps(checks,ensure_ascii=False),recommendation,now,run_id))
        self.audit_fn(con,str(actor.get("id")),"m30_simulation_run",run_id,"execute",{"profile":row["profile"],"recommendation":recommendation,"checks_passed":sum(checks.values())})
        con.commit(); return self.summary(con,actor)

    def record_decision(self, con, run_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role")!="admin": raise PermissionError("Solo administración puede documentar la decisión simulada.")
        self.ensure_schema(con); row=con.execute("SELECT * FROM m30_simulation_run WHERE id=?",(run_id,)).fetchone()
        if not row: raise LookupError("Simulación no encontrada.")
        if row["status"]!="completed": raise ValueError("La simulación debe estar completada y sin decisión previa.")
        if str(data.get("confirmation") or "").strip()!=self.policy["confirmations"]["decision"]: raise ValueError("Confirmación de decisión incorrecta.")
        decision=str(data.get("decision") or "")
        if decision not in self.policy["decisions"]: raise ValueError("Decisión no permitida.")
        reason=" ".join(str(data.get("reason") or "").split())[:1000]
        if len(reason)<25: raise ValueError("Documente una razón verificable de al menos 25 caracteres.")
        if decision!=row["recommendation"] and len(reason)<60: raise ValueError("Una decisión distinta de la recomendación exige una justificación más amplia.")
        now=self.now(); con.execute("UPDATE m30_simulation_run SET status='decision_recorded',decision=?,decision_reason=?,decided_at=? WHERE id=?",(decision,reason,now,run_id))
        self.audit_fn(con,str(actor.get("id")),"m30_simulation_run",run_id,"decision",{"decision":decision,"recommendation":row["recommendation"],"production_authorized":False})
        con.commit(); return self.summary(con,actor)

    def export_snapshot(self, con, actor: dict[str, Any]) -> bytes:
        data=self.summary(con,actor)
        data["export_notice"]="Contiene únicamente escenarios y métricas sintéticas; no contiene usuarios, expedientes ni documentos."
        return json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8")
