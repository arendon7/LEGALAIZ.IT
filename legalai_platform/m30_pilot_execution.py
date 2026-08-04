from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class M30PilotExecutionCenter:
    """Centro operativo del piloto controlado.

    Consolida planeación, responsables, soporte, observaciones estructuradas y
    decisiones. No publica productos, no procesa pagos reales, no entrega
    documentos automáticamente y no reemplaza la revisión jurídica por caso.
    """

    def __init__(self, root: Path, readiness, pilot_operations, audit_fn):
        self.root = Path(root).resolve()
        self.readiness = readiness
        self.pilot_operations = pilot_operations
        self.audit_fn = audit_fn
        self.policy_path = self.root / "config" / "m30_1_pilot_execution_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.support_categories = set(self.policy["support_categories"])
        self.support_priorities = dict(self.policy["support_priorities"])
        self.support_statuses = set(self.policy["support_statuses"])
        self.observation_stages = set(self.policy["observation_stages"])
        self.observation_outcomes = set(self.policy["observation_outcomes"])
        self.issue_codes = set(self.policy["issue_codes"])
        self.duration_buckets = set(self.policy["duration_buckets"])

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    @staticmethod
    def _clean_text(value: Any, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", text)
        text = re.sub(r"(?<!\d)\d{7,}(?!\d)", "[dato numérico omitido]", text)
        return text

    @staticmethod
    def _json(raw: Any, default: Any):
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m30_pilot_support_ticket(
              id TEXT PRIMARY KEY,
              cohort_id TEXT,
              case_plan_id TEXT,
              case_id TEXT,
              opened_by_id TEXT NOT NULL,
              opened_by_role TEXT NOT NULL,
              category TEXT NOT NULL,
              priority TEXT NOT NULL CHECK(priority IN ('low','medium','high','critical')),
              status TEXT NOT NULL CHECK(status IN ('open','assigned','resolved','closed')),
              summary TEXT NOT NULL,
              owner_id TEXT,
              due_at TEXT NOT NULL,
              resolution_code TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              closed_at TEXT,
              FOREIGN KEY(cohort_id) REFERENCES m25_pilot_cohort(id),
              FOREIGN KEY(case_plan_id) REFERENCES m25_pilot_case_plan(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(owner_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_support_status
              ON m30_pilot_support_ticket(status,priority,due_at);
            CREATE TABLE IF NOT EXISTS m30_pilot_observation(
              id TEXT PRIMARY KEY,
              cohort_id TEXT,
              case_plan_id TEXT NOT NULL,
              case_id TEXT,
              stage TEXT NOT NULL,
              outcome TEXT NOT NULL,
              issue_code TEXT NOT NULL,
              duration_bucket TEXT NOT NULL,
              observer_id TEXT NOT NULL,
              observer_role TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(cohort_id) REFERENCES m25_pilot_cohort(id),
              FOREIGN KEY(case_plan_id) REFERENCES m25_pilot_case_plan(id),
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_observation_plan
              ON m30_pilot_observation(case_plan_id,stage,created_at);
            CREATE TABLE IF NOT EXISTS m30_pilot_decision(
              id TEXT PRIMARY KEY,
              cohort_id TEXT NOT NULL,
              product_code TEXT,
              decision TEXT NOT NULL CHECK(decision IN ('hold','repeat','proceed_limited')),
              reason_code TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_name TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(cohort_id) REFERENCES m25_pilot_cohort(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_decision_created
              ON m30_pilot_decision(cohort_id,product_code,created_at);
            """
        )

    def _require_professional(self, actor: dict[str, Any]) -> None:
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("El Centro Operativo del Piloto exige rol profesional.")

    def _active_cohort(self, report: dict[str, Any]) -> dict[str, Any] | None:
        return next((row for row in report.get("cohorts") or [] if row.get("status") in {"planned", "active"}), None)

    def _professionals(self, con) -> list[dict[str, Any]]:
        rows = con.execute(
            "SELECT id,name,role,specialty,verified,active FROM users WHERE role IN ('specialist','admin') AND active=1 ORDER BY role,name"
        ).fetchall()
        return [
            {
                "id": row["id"], "name": row["name"], "role": row["role"],
                "specialty": row["specialty"], "verified": bool(row["verified"]),
            }
            for row in rows
        ]

    def _tickets(self, con) -> list[dict[str, Any]]:
        rows = con.execute(
            """SELECT t.*,u.name owner_name FROM m30_pilot_support_ticket t
               LEFT JOIN users u ON u.id=t.owner_id
               ORDER BY CASE t.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
                        CASE t.status WHEN 'open' THEN 1 WHEN 'assigned' THEN 2 WHEN 'resolved' THEN 3 ELSE 4 END,
                        t.created_at DESC LIMIT 200"""
        ).fetchall()
        now = datetime.now(timezone.utc)
        items = []
        for row in rows:
            item = dict(row)
            try:
                due = datetime.fromisoformat(str(item["due_at"]).replace("Z", "+00:00"))
                item["overdue"] = item["status"] in {"open", "assigned"} and due < now
            except ValueError:
                item["overdue"] = False
            items.append(item)
        return items

    def _observations(self, con) -> dict[str, Any]:
        rows = con.execute(
            "SELECT stage,outcome,issue_code,COUNT(*) AS count FROM m30_pilot_observation GROUP BY stage,outcome,issue_code ORDER BY stage,outcome"
        ).fetchall()
        total = sum(int(row["count"]) for row in rows)
        friction = sum(int(row["count"]) for row in rows if row["outcome"] in {"friction", "blocked"})
        return {
            "total": total,
            "friction_count": friction,
            "friction_rate": round(friction / total, 3) if total else 0.0,
            "rows": [dict(row) for row in rows],
        }

    def _decisions(self, con) -> list[dict[str, Any]]:
        return [dict(row) for row in con.execute(
            "SELECT * FROM m30_pilot_decision ORDER BY created_at DESC LIMIT 50"
        ).fetchall()]

    def _role_coverage(self, cohort: dict[str, Any] | None) -> dict[str, Any]:
        plans = list((cohort or {}).get("plans") or [])
        total = len(plans)
        assigned = sum(bool(row.get("assigned_specialist_id")) for row in plans)
        independent = sum(
            bool(row.get("independent_reviewer_id")) and row.get("independent_reviewer_id") != row.get("assigned_specialist_id")
            for row in plans
        )
        qa = sum(bool(row.get("qa_reviewer_id")) for row in plans)
        complete = sum(
            bool(row.get("assigned_specialist_id"))
            and bool(row.get("independent_reviewer_id"))
            and row.get("independent_reviewer_id") != row.get("assigned_specialist_id")
            and bool(row.get("qa_reviewer_id"))
            for row in plans
        )
        return {"total": total, "assigned": assigned, "independent": independent, "qa": qa, "complete": complete}

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.readiness.ensure_schema(con)
        self.pilot_operations.ensure_schema(con)
        self.ensure_schema(con)
        readiness = self.readiness.report(con)
        gate = self.pilot_operations.release_gate(con)
        cohort = self._active_cohort(readiness)
        role_coverage = self._role_coverage(cohort)
        tickets = self._tickets(con)
        observations = self._observations(con)
        open_critical_support = sum(
            row["priority"] in {"high", "critical"} and row["status"] in {"open", "assigned"}
            for row in tickets
        )
        checks = {
            "planning_ready": bool(readiness.get("planning_ready")),
            "cohort_created": bool(cohort and cohort.get("plan_counts", {}).get("total") == self.policy["target_cases"]),
            "all_roles_assigned": role_coverage["total"] > 0 and role_coverage["complete"] == role_coverage["total"],
            "pilot_control_active": gate.get("control", {}).get("state") == "active",
            "no_high_or_critical_incidents": bool(gate.get("checks", {}).get("no_open_high_or_critical_incidents")),
            "no_high_or_critical_support": open_critical_support == 0,
        }
        launch_ready = all(checks.values())
        final_checks = {
            **checks,
            "completed_cases": bool(readiness.get("evidence_gate", {}).get("completed_cases")),
            "feedback_volume": bool(readiness.get("evidence_gate", {}).get("feedback_volume")),
            "clarity": bool(readiness.get("evidence_gate", {}).get("clarity")),
            "ease": bool(readiness.get("evidence_gate", {}).get("ease")),
            "confidence": bool(readiness.get("evidence_gate", {}).get("confidence")),
            "goal_met": bool(readiness.get("evidence_gate", {}).get("goal_met")),
            "manual_validations": bool(readiness.get("evidence_gate", {}).get("manual_validations")),
        }
        return {
            "schema": "legalaizit-m30-1-pilot-center-summary-v1",
            "milestone": "M30.1",
            "version": self.policy["version"],
            "policy": self.policy,
            "readiness": readiness,
            "release_gate": gate,
            "active_cohort": cohort,
            "role_coverage": role_coverage,
            "professionals": self._professionals(con),
            "support_tickets": tickets,
            "support_metrics": {
                "total": len(tickets),
                "open": sum(row["status"] in {"open", "assigned"} for row in tickets),
                "overdue": sum(bool(row.get("overdue")) for row in tickets),
                "high_or_critical_open": open_critical_support,
            },
            "observations": observations,
            "decisions": self._decisions(con),
            "launch_gate": {
                "checks": checks,
                "passed": sum(bool(value) for value in checks.values()),
                "total": len(checks),
                "ready": launch_ready,
            },
            "evidence_gate": {
                "checks": final_checks,
                "passed": sum(bool(value) for value in final_checks.values()),
                "total": len(final_checks),
                "ready": all(final_checks.values()),
            },
            "public_production_ready": False,
            "real_payments_ready": False,
            "automatic_delivery_ready": False,
            "notice": "Centro operativo para piloto controlado. No autoriza producción pública, pagos reales ni entrega desatendida.",
        }

    def update_plan(self, con, plan_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m25_pilot_case_plan WHERE id=?", (plan_id,)).fetchone()
        if not row:
            raise LookupError("Cupo de piloto no encontrado.")
        professionals = {row["id"]: row for row in self._professionals(con)}
        assigned = str(data.get("assigned_specialist_id") or row["assigned_specialist_id"] or "") or None
        independent = str(data.get("independent_reviewer_id") or row["independent_reviewer_id"] or "") or None
        qa = str(data.get("qa_reviewer_id") or row["qa_reviewer_id"] or "") or None
        if assigned and (assigned not in professionals or professionals[assigned]["role"] != "specialist"):
            raise ValueError("El especialista asignado debe ser un profesional activo.")
        if independent and (independent not in professionals or professionals[independent]["role"] != "specialist"):
            raise ValueError("El revisor independiente debe ser un especialista activo.")
        if qa and qa not in professionals:
            raise ValueError("El responsable QA debe pertenecer al equipo profesional activo.")
        if assigned and independent and assigned == independent:
            raise ValueError("El especialista y el revisor independiente deben ser personas distintas.")
        if qa and assigned and qa == assigned:
            raise ValueError("El responsable QA debe ser distinto del especialista del expediente.")
        status = str(data.get("status") or row["status"])
        if status not in set(self.policy["plan_statuses"]):
            raise ValueError("Estado de cupo no permitido.")
        case_id = str(data.get("case_id") or row["case_id"] or "") or None
        if case_id:
            case = con.execute("SELECT id,product_code FROM cases WHERE id=?", (case_id,)).fetchone()
            if not case:
                raise LookupError("El expediente vinculado no existe.")
            if case["product_code"] != row["product_code"]:
                raise ValueError("El expediente no corresponde al producto planificado.")
        if status in {"in_progress", "completed"} and not (assigned and independent and qa):
            raise ValueError("Antes de avanzar deben asignarse especialista, revisor independiente y QA.")
        if status == "completed" and not case_id:
            raise ValueError("Un cupo completado debe estar vinculado a un expediente.")
        note = self._clean_text(data.get("evidence_note") or row["evidence_note"] or "", 800)
        if status == "completed" and len(note) < 12:
            raise ValueError("Registre evidencia suficiente para cerrar el cupo.")
        now = self.now()
        con.execute(
            """UPDATE m25_pilot_case_plan SET status=?,case_id=?,assigned_specialist_id=?,independent_reviewer_id=?,
               qa_reviewer_id=?,evidence_note=?,updated_at=? WHERE id=?""",
            (status, case_id, assigned, independent, qa, note, now, plan_id),
        )
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_case_plan", plan_id, "update", {
            "status": status, "assigned": assigned, "independent": independent, "qa": qa, "case_id": case_id,
        })
        con.commit()
        return self.summary(con, actor)

    def assign_product_team(self, con, cohort_id: str, product_code: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        if product_code not in set(self.policy["pilot_products"]):
            raise ValueError("Producto fuera del piloto inicial.")
        if not con.execute("SELECT 1 FROM m25_pilot_cohort WHERE id=? AND status IN ('planned','active')", (cohort_id,)).fetchone():
            raise LookupError("Cohorte activa o planificada no encontrada.")
        professionals = {row["id"]: row for row in self._professionals(con)}
        assigned = str(data.get("assigned_specialist_id") or "")
        independent = str(data.get("independent_reviewer_id") or "")
        qa = str(data.get("qa_reviewer_id") or "")
        if not assigned or assigned not in professionals or professionals[assigned]["role"] != "specialist":
            raise ValueError("Seleccione un especialista activo para el producto.")
        if not independent or independent not in professionals or professionals[independent]["role"] != "specialist":
            raise ValueError("Seleccione un revisor independiente activo.")
        if not qa or qa not in professionals:
            raise ValueError("Seleccione un responsable QA activo.")
        if assigned == independent or assigned == qa:
            raise ValueError("El especialista debe ser distinto del revisor independiente y del responsable QA.")
        now = self.now()
        result = con.execute(
            """UPDATE m25_pilot_case_plan SET assigned_specialist_id=?,independent_reviewer_id=?,qa_reviewer_id=?,updated_at=?
               WHERE cohort_id=? AND product_code=? AND status IN ('planned','recruited','in_progress','blocked')""",
            (assigned, independent, qa, now, cohort_id, product_code),
        )
        if result.rowcount <= 0:
            raise LookupError("No existen cupos editables para ese producto.")
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_product_team", f"{cohort_id}:{product_code}", "assign", {
            "assigned": assigned, "independent": independent, "qa": qa, "updated_slots": result.rowcount,
        })
        con.commit()
        return self.summary(con, actor)

    def activate_cohort(self, con, cohort_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede activar una cohorte.")
        self.ensure_schema(con)
        if str(data.get("confirmation") or "").strip() != self.policy["confirmations"]["activate_cohort"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['confirmations']['activate_cohort']}")
        row = con.execute("SELECT * FROM m25_pilot_cohort WHERE id=?", (cohort_id,)).fetchone()
        if not row:
            raise LookupError("Cohorte no encontrada.")
        plans = [dict(item) for item in con.execute("SELECT * FROM m25_pilot_case_plan WHERE cohort_id=?", (cohort_id,)).fetchall()]
        coverage = self._role_coverage({"plans": plans})
        if coverage["total"] != self.policy["target_cases"] or coverage["complete"] != coverage["total"]:
            raise ValueError("Los 20 cupos deben tener especialista, revisor independiente y QA antes de activar la cohorte.")
        now = self.now()
        con.execute("UPDATE m25_pilot_cohort SET status='active',updated_at=? WHERE id=?", (now, cohort_id))
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_cohort", cohort_id, "activate", {"role_coverage": coverage})
        con.commit()
        return self.summary(con, actor)

    def create_ticket(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        category = str(data.get("category") or "").strip()
        priority = str(data.get("priority") or "medium").strip()
        if category not in self.support_categories:
            raise ValueError("Categoría de soporte no permitida.")
        if priority not in self.support_priorities:
            raise ValueError("Prioridad de soporte no permitida.")
        summary = self._clean_text(data.get("summary"), int(self.policy["privacy"]["support_summary_max_chars"]))
        if len(summary) < 8:
            raise ValueError("Describa la fricción de forma breve, sin narrar hechos del caso.")
        cohort_id = str(data.get("cohort_id") or "") or None
        plan_id = str(data.get("case_plan_id") or "") or None
        case_id = str(data.get("case_id") or "") or None
        if cohort_id and not con.execute("SELECT 1 FROM m25_pilot_cohort WHERE id=?", (cohort_id,)).fetchone():
            raise LookupError("Cohorte no encontrada.")
        if plan_id and not con.execute("SELECT 1 FROM m25_pilot_case_plan WHERE id=?", (plan_id,)).fetchone():
            raise LookupError("Cupo de piloto no encontrado.")
        if case_id and not con.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
            raise LookupError("Expediente no encontrado.")
        now_dt = datetime.now(timezone.utc)
        due_at = (now_dt + timedelta(hours=int(self.support_priorities[priority]["sla_hours"]))).isoformat(timespec="seconds")
        ticket_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m30_pilot_support_ticket
               (id,cohort_id,case_plan_id,case_id,opened_by_id,opened_by_role,category,priority,status,summary,due_at,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?, 'open',?,?,?,?)""",
            (ticket_id, cohort_id, plan_id, case_id, str(actor.get("id")), str(actor.get("role")), category, priority, summary, due_at, now_dt.isoformat(timespec="seconds"), now_dt.isoformat(timespec="seconds")),
        )
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_support_ticket", ticket_id, "create", {"category": category, "priority": priority})
        con.commit()
        return self.summary(con, actor)

    def update_ticket(self, con, ticket_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m30_pilot_support_ticket WHERE id=?", (ticket_id,)).fetchone()
        if not row:
            raise LookupError("Solicitud de soporte no encontrada.")
        status = str(data.get("status") or row["status"])
        if status not in self.support_statuses:
            raise ValueError("Estado de soporte no permitido.")
        owner_id = str(data.get("owner_id") or row["owner_id"] or "") or None
        if owner_id and not con.execute("SELECT 1 FROM users WHERE id=? AND role IN ('specialist','admin') AND active=1", (owner_id,)).fetchone():
            raise ValueError("El responsable de soporte debe ser un profesional activo.")
        resolution = self._clean_text(data.get("resolution_code") or row["resolution_code"] or "", 120)
        if status in {"resolved", "closed"} and len(resolution) < 3:
            raise ValueError("Seleccione o registre un código breve de resolución.")
        now = self.now()
        closed_at = now if status == "closed" else row["closed_at"]
        con.execute(
            "UPDATE m30_pilot_support_ticket SET status=?,owner_id=?,resolution_code=?,closed_at=?,updated_at=? WHERE id=?",
            (status, owner_id, resolution, closed_at, now, ticket_id),
        )
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_support_ticket", ticket_id, "update", {"status": status, "owner_id": owner_id, "resolution_code": resolution})
        con.commit()
        return self.summary(con, actor)

    def record_observation(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        stage = str(data.get("stage") or "")
        outcome = str(data.get("outcome") or "")
        issue_code = str(data.get("issue_code") or "none")
        duration_bucket = str(data.get("duration_bucket") or "under_5m")
        if stage not in self.observation_stages or outcome not in self.observation_outcomes:
            raise ValueError("Etapa o resultado de observación no permitido.")
        if issue_code not in self.issue_codes or duration_bucket not in self.duration_buckets:
            raise ValueError("Código de fricción o duración no permitido.")
        plan_id = str(data.get("case_plan_id") or "")
        plan = con.execute("SELECT * FROM m25_pilot_case_plan WHERE id=?", (plan_id,)).fetchone()
        if not plan:
            raise LookupError("Cupo de piloto no encontrado.")
        obs_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m30_pilot_observation
               (id,cohort_id,case_plan_id,case_id,stage,outcome,issue_code,duration_bucket,observer_id,observer_role,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (obs_id, plan["cohort_id"], plan_id, plan["case_id"], stage, outcome, issue_code, duration_bucket, str(actor.get("id")), str(actor.get("role")), self.now()),
        )
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_observation", obs_id, "create", {"stage": stage, "outcome": outcome, "issue_code": issue_code, "duration_bucket": duration_bucket})
        con.commit()
        return self.summary(con, actor)

    def record_decision(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede registrar una decisión de piloto.")
        self.ensure_schema(con)
        if str(data.get("confirmation") or "").strip() != self.policy["confirmations"]["record_decision"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['confirmations']['record_decision']}")
        cohort_id = str(data.get("cohort_id") or "")
        if not con.execute("SELECT 1 FROM m25_pilot_cohort WHERE id=?", (cohort_id,)).fetchone():
            raise LookupError("Cohorte no encontrada.")
        decision = str(data.get("decision") or "")
        reason_code = str(data.get("reason_code") or "")
        product_code = str(data.get("product_code") or "") or None
        if decision not in set(self.policy["decisions"]):
            raise ValueError("Decisión no permitida.")
        if reason_code not in set(self.policy["decision_reason_codes"]):
            raise ValueError("Motivo de decisión no permitido.")
        if product_code and product_code not in set(self.policy["pilot_products"]):
            raise ValueError("Producto fuera del piloto inicial.")
        snapshot = self.summary(con, actor)
        decision_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m30_pilot_decision
               (id,cohort_id,product_code,decision,reason_code,actor_id,actor_name,snapshot_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (decision_id, cohort_id, product_code, decision, reason_code, str(actor.get("id")), self._actor_name(actor), json.dumps(snapshot, ensure_ascii=False), self.now()),
        )
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_decision", decision_id, "create", {"decision": decision, "reason_code": reason_code, "product_code": product_code})
        con.commit()
        return self.summary(con, actor)

    def export_snapshot(self, con, actor: dict[str, Any]) -> bytes:
        payload = self.summary(con, actor)
        payload["export"] = {
            "generated_at": self.now(),
            "privacy": "Sin correos, documentos de identidad, relatos del caso ni valores económicos.",
            "immutable_source": "Snapshot del estado operativo al momento de la exportación.",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
