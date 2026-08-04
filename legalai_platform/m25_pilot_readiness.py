from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class M25PilotReadinessCenter:
    """Auditoría y planeación del piloto real controlado de M25.

    El módulo no inscribe usuarios reales, no procesa pagos, no publica M23.2,
    no entrega documentos automáticamente y no modifica revisiones activas.
    """

    def __init__(self, root: Path, candidates, full_validation, release_governance, pilot_operations, human_approval):
        self.root = Path(root).resolve()
        self.candidates = candidates
        self.full_validation = full_validation
        self.release_governance = release_governance
        self.pilot_operations = pilot_operations
        self.human_approval = human_approval
        self.policy_path = self.root / "config" / "m25_0_pilot_readiness_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.product_codes = tuple(self.policy["pilot_products"])
        self.archetypes = tuple(self.policy["case_archetypes"])

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _table_exists(con, table: str) -> bool:
        row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        return bool(row)

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
            CREATE TABLE IF NOT EXISTS m25_pilot_cohort(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('planned','active','completed','archived')),
              target_cases INTEGER NOT NULL,
              product_codes_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_by_name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              archived_at TEXT,
              archive_reason TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS m25_pilot_case_plan(
              id TEXT PRIMARY KEY,
              cohort_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              archetype TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('planned','recruited','in_progress','completed','blocked','cancelled')),
              case_id TEXT,
              assigned_specialist_id TEXT,
              independent_reviewer_id TEXT,
              qa_reviewer_id TEXT,
              evidence_note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(cohort_id) REFERENCES m25_pilot_cohort(id),
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_m25_case_plan_unique
              ON m25_pilot_case_plan(cohort_id,product_code,archetype);
            CREATE INDEX IF NOT EXISTS idx_m25_case_plan_status
              ON m25_pilot_case_plan(cohort_id,status,product_code);
            CREATE TABLE IF NOT EXISTS m25_readiness_decision(
              id TEXT PRIMARY KEY,
              decision TEXT NOT NULL CHECK(decision IN ('hold','proceed_internal_pilot','close_pilot')),
              actor_id TEXT NOT NULL,
              actor_name TEXT NOT NULL,
              reason TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )

    def _registry_products(self) -> list[dict[str, Any]]:
        path = self.root / "config" / "legal_products_registry.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return list(payload.get("products") or [])

    def _runtime_counts(self) -> dict[str, Any]:
        interviews = json.loads((self.root / "data" / "interviews.json").read_text(encoding="utf-8"))
        rules = json.loads((self.root / "data" / "rules.json").read_text(encoding="utf-8"))
        return {
            "products": len(interviews),
            "questions": sum(len(value.get("questions") or []) for value in interviews.values()),
            "rules": sum(len(value or []) for value in rules.values()),
            "question_counts": {code: len((interviews.get(code) or {}).get("questions") or []) for code in interviews},
            "rule_counts": {code: len(rules.get(code) or []) for code in rules},
        }

    def _capability_inventory(self) -> list[dict[str, Any]]:
        rows = []
        for item in self.policy.get("capabilities") or []:
            evidence = str(item.get("evidence") or "")
            is_db_evidence = evidence.startswith("m25_")
            exists = is_db_evidence or (self.root / evidence).exists()
            rows.append({**item, "evidence_exists": bool(exists)})
        return rows

    def _product_readiness(self) -> list[dict[str, Any]]:
        registry = {row["product_code"]: row for row in self._registry_products()}
        runtime = self._runtime_counts()
        human_products = {
            row["product_code"]: row
            for row in (self.human_approval.policy.get("products") or [])
        }
        rows = []
        for code in self.product_codes:
            reg = registry.get(code) or {}
            base = self.root / "app" / "assets" / "advanced-legal-library" / code
            interview_file = base / "ENTREVISTA.json"
            rules_file = base / "REGLAS.json"
            sources_file = base / "FUENTES.json"
            templates_file = base / "PLANTILLAS.json"
            approval = human_products.get(code) or {}
            checks = {
                "registry_present": bool(reg),
                "runtime_questions_present": runtime["question_counts"].get(code, 0) > 0,
                "runtime_rules_present": runtime["rule_counts"].get(code, 0) > 0,
                "interview_asset_present": interview_file.exists(),
                "rules_asset_present": rules_file.exists(),
                "sources_asset_present": sources_file.exists(),
                "templates_asset_present": templates_file.exists(),
                "catalog_legal_approved": approval.get("legal_decision") == "approved",
                "catalog_qa_approved": approval.get("qa_decision") == "approved",
                "internal_pilot_active": approval.get("activation_state") == "internal_pilot_active",
                "case_specific_review_required": approval.get("case_specific_review_required") is True,
            }
            rows.append({
                "product_code": code,
                "public_name": reg.get("public_name") or code,
                "questions": runtime["question_counts"].get(code, 0),
                "rules": runtime["rule_counts"].get(code, 0),
                "checks": checks,
                "ready_for_planned_pilot": all(checks.values()),
            })
        return rows

    def _cohorts(self, con) -> list[dict[str, Any]]:
        self.ensure_schema(con)
        rows = []
        for row in con.execute("SELECT * FROM m25_pilot_cohort ORDER BY created_at DESC").fetchall():
            item = dict(row)
            item["product_codes"] = self._json(item.pop("product_codes_json"), [])
            plans = [dict(x) for x in con.execute(
                "SELECT * FROM m25_pilot_case_plan WHERE cohort_id=? ORDER BY product_code,archetype", (item["id"],)
            ).fetchall()]
            item["plans"] = plans
            item["plan_counts"] = {
                "total": len(plans),
                "completed": sum(x["status"] == "completed" for x in plans),
                "in_progress": sum(x["status"] == "in_progress" for x in plans),
                "blocked": sum(x["status"] == "blocked" for x in plans),
            }
            rows.append(item)
        return rows

    def _pilot_metrics(self, con) -> dict[str, Any]:
        metrics = {
            "consented_participants": 0,
            "delivered_cases": 0,
            "feedback_responses": 0,
            "average_clarity": 0.0,
            "average_ease": 0.0,
            "average_confidence": 0.0,
            "goal_met_rate": 0.0,
            "open_high_or_critical_incidents": 0,
            "manual_checks_passed": 0,
            "manual_checks_total": len(self.pilot_operations.manual_checks),
            "pilot_control_state": "frozen",
        }
        if self._table_exists(con, "m24_pilot_enrollment"):
            metrics["consented_participants"] = con.execute(
                "SELECT COUNT(*) FROM m24_pilot_enrollment WHERE status='consented'"
            ).fetchone()[0]
        if self._table_exists(con, "m24_pilot_event"):
            metrics["delivered_cases"] = con.execute(
                "SELECT COUNT(DISTINCT case_id) FROM m24_pilot_event WHERE event_type='delivered' AND success=1 AND case_id IS NOT NULL"
            ).fetchone()[0]
        if self._table_exists(con, "m24_pilot_feedback"):
            row = con.execute(
                "SELECT COUNT(*),COALESCE(AVG(clarity),0),COALESCE(AVG(ease),0),COALESCE(AVG(confidence),0),COALESCE(AVG(goal_met),0) FROM m24_pilot_feedback"
            ).fetchone()
            metrics.update({
                "feedback_responses": int(row[0]),
                "average_clarity": round(float(row[1]), 2),
                "average_ease": round(float(row[2]), 2),
                "average_confidence": round(float(row[3]), 2),
                "goal_met_rate": round(float(row[4]), 3),
            })
        if self._table_exists(con, "m24_pilot_incident"):
            metrics["open_high_or_critical_incidents"] = con.execute(
                "SELECT COUNT(*) FROM m24_pilot_incident WHERE severity IN ('high','critical') AND status!='closed'"
            ).fetchone()[0]
        if self._table_exists(con, "m24_pilot_manual_validation"):
            metrics["manual_checks_passed"] = con.execute(
                "SELECT COUNT(*) FROM m24_pilot_manual_validation WHERE status='passed'"
            ).fetchone()[0]
        if self._table_exists(con, "m24_pilot_control"):
            row = con.execute("SELECT state FROM m24_pilot_control WHERE id=1").fetchone()
            metrics["pilot_control_state"] = row[0] if row else "frozen"
        return metrics

    def report(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        integrity = self.candidates.verify_integrity()
        validation = self.full_validation.report()
        release = self.release_governance.summary(con)
        approval = self.human_approval.summary(con, self.release_governance)
        products = self._product_readiness()
        capabilities = self._capability_inventory()
        cohorts = self._cohorts(con)
        metrics = self._pilot_metrics(con)
        resolved_registry = all(
            (row.get("questionnaire_binding") or {}).get("status") == "resolved_m21_1_runtime"
            for row in self._registry_products()
        )
        planned_cases = sum(item["plan_counts"]["total"] for item in cohorts if item["status"] in {"planned", "active"})
        plan_template_path = self.root / "config" / "m25_0_pilot_case_plan_template.json"
        plan_template = json.loads(plan_template_path.read_text(encoding="utf-8")) if plan_template_path.is_file() else {}
        template_slots = list(plan_template.get("slots") or [])
        independent_review_assigned = sum(
            1 for cohort in cohorts for plan in cohort["plans"]
            if plan.get("independent_reviewer_id") and plan.get("independent_reviewer_id") != plan.get("assigned_specialist_id")
        )
        core_checks = {
            "candidate_integrity_55_of_55": bool(integrity.get("ok") and integrity.get("checked_files") == 55),
            "legal_scenarios_110_of_110": validation.get("passed") == 110 and validation.get("failed") == 0,
            "catalog_human_approval_11_of_11": approval.get("approved_products") == 11,
            "internal_activation_11_of_11": release.get("internal_pilot_active_count") == 11,
            "registry_runtime_bindings_resolved": resolved_registry,
            "four_pilot_products_ready": all(row["ready_for_planned_pilot"] for row in products),
            "pilot_plan_template_has_20_slots": len(template_slots) == self.policy["target_cases_total"],
            "active_cohort_has_20_slots": planned_cases >= self.policy["target_cases_total"],
            "independent_review_planned_for_all_slots": planned_cases > 0 and independent_review_assigned >= planned_cases,
        }
        planning_ready = all(core_checks[key] for key in (
            "candidate_integrity_55_of_55",
            "legal_scenarios_110_of_110",
            "catalog_human_approval_11_of_11",
            "internal_activation_11_of_11",
            "registry_runtime_bindings_resolved",
            "four_pilot_products_ready",
            "pilot_plan_template_has_20_slots",
        ))
        execution_ready = planning_ready and core_checks["active_cohort_has_20_slots"] and core_checks["independent_review_planned_for_all_slots"]
        thresholds = self.policy["pilot_success_thresholds"]
        evidence_gate = {
            "completed_cases": metrics["delivered_cases"] >= thresholds["minimum_completed_cases"],
            "feedback_volume": metrics["feedback_responses"] >= thresholds["minimum_completed_cases"],
            "clarity": metrics["average_clarity"] >= thresholds["minimum_average_clarity"],
            "ease": metrics["average_ease"] >= thresholds["minimum_average_ease"],
            "confidence": metrics["average_confidence"] >= thresholds["minimum_average_confidence"],
            "goal_met": metrics["goal_met_rate"] >= thresholds["minimum_goal_met_rate"],
            "incidents": metrics["open_high_or_critical_incidents"] <= thresholds["maximum_open_high_or_critical_incidents"],
            "manual_validations": metrics["manual_checks_total"] > 0 and metrics["manual_checks_passed"] == metrics["manual_checks_total"],
        }
        blockers = []
        if not core_checks["active_cohort_has_20_slots"]:
            blockers.append("Crear una cohorte M25 con 20 expedientes planificados: cinco por cada producto piloto.")
        if not core_checks["independent_review_planned_for_all_slots"]:
            blockers.append("Asignar un segundo revisor humano independiente a cada expediente del piloto.")
        blockers.extend([
            "Validar términos y condiciones, privacidad, retracto/devoluciones y reglas comerciales antes de pagos reales.",
            "Validar precios, costo por revisión, margen y tiempos con datos del piloto.",
            "Mantener pagos reales, producción pública y entrega desatendida bloqueados durante M25.0.",
        ])
        return {
            "schema": "legalaizit-m25-0-readiness-report-v1",
            "milestone": "M25.0",
            "base": "M24.10",
            "status": "planning_ready" if planning_ready else "planning_blocked",
            "planning_ready": planning_ready,
            "pilot_execution_ready": execution_ready,
            "public_production_ready": False,
            "real_payments_ready": False,
            "automatic_delivery_ready": False,
            "core_checks": core_checks,
            "evidence_gate": evidence_gate,
            "runtime_counts": self._runtime_counts(),
            "candidate_integrity": integrity,
            "full_validation": {"passed": validation.get("passed"), "failed": validation.get("failed")},
            "catalog_approval": approval,
            "products": products,
            "capabilities": capabilities,
            "pilot_plan_template": {"slot_count": len(template_slots), "contains_personal_data": plan_template.get("contains_personal_data", False), "pre_enrolled_users": plan_template.get("pre_enrolled_users", False)},
            "cohorts": cohorts,
            "pilot_metrics": metrics,
            "blockers": blockers,
            "notice": "M25.0 prepara y audita el piloto real controlado. No constituye autorización de producción pública.",
        }

    def create_cohort(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede crear una cohorte de piloto M25.")
        if str(data.get("confirmation") or "").strip() != self.policy["confirmations"]["create_cohort"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['confirmations']['create_cohort']}")
        title = " ".join(str(data.get("title") or "Piloto M25 · Cohorte controlada").split())[:120]
        if len(title) < 8:
            raise ValueError("Indique un nombre claro para la cohorte.")
        if con.execute("SELECT 1 FROM m25_pilot_cohort WHERE status IN ('planned','active')").fetchone():
            raise ValueError("Ya existe una cohorte M25 planificada o activa. Archívela antes de crear otra.")
        now = self.now()
        cohort_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m25_pilot_cohort
               (id,title,status,target_cases,product_codes_json,created_by,created_by_name,created_at,updated_at)
               VALUES(?,?, 'planned',?,?,?,?,?,?)""",
            (
                cohort_id, title, self.policy["target_cases_total"], json.dumps(self.product_codes),
                str(actor.get("id")), str(actor.get("name") or actor.get("email") or "Administrador"), now, now,
            ),
        )
        for code in self.product_codes:
            for archetype in self.archetypes:
                con.execute(
                    """INSERT INTO m25_pilot_case_plan
                       (id,cohort_id,product_code,archetype,status,created_at,updated_at)
                       VALUES(?,?,?,?, 'planned',?,?)""",
                    (str(uuid.uuid4()), cohort_id, code, archetype, now, now),
                )
        con.commit()
        return self.report(con)

    def update_case_plan(self, con, plan_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La planeación del piloto exige rol profesional.")
        row = con.execute("SELECT * FROM m25_pilot_case_plan WHERE id=?", (plan_id,)).fetchone()
        if not row:
            raise LookupError("Plan de expediente no encontrado.")
        status = str(data.get("status") or row["status"])
        if status not in {"planned", "recruited", "in_progress", "completed", "blocked", "cancelled"}:
            raise ValueError("Estado de plan no permitido.")
        assigned = str(data.get("assigned_specialist_id") or row["assigned_specialist_id"] or "") or None
        independent = str(data.get("independent_reviewer_id") or row["independent_reviewer_id"] or "") or None
        qa = str(data.get("qa_reviewer_id") or row["qa_reviewer_id"] or "") or None
        if assigned and independent and assigned == independent:
            raise ValueError("El revisor independiente debe ser una persona distinta del especialista asignado.")
        note = " ".join(str(data.get("evidence_note") or row["evidence_note"] or "").split())[:1000]
        case_id = str(data.get("case_id") or row["case_id"] or "") or None
        if case_id and not con.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
            raise LookupError("El expediente vinculado no existe.")
        con.execute(
            """UPDATE m25_pilot_case_plan SET status=?,case_id=?,assigned_specialist_id=?,independent_reviewer_id=?,
               qa_reviewer_id=?,evidence_note=?,updated_at=? WHERE id=?""",
            (status, case_id, assigned, independent, qa, note, self.now(), plan_id),
        )
        con.commit()
        return self.report(con)

    def archive_cohort(self, con, cohort_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede archivar la cohorte.")
        if str(data.get("confirmation") or "").strip() != self.policy["confirmations"]["archive_cohort"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['confirmations']['archive_cohort']}")
        row = con.execute("SELECT * FROM m25_pilot_cohort WHERE id=?", (cohort_id,)).fetchone()
        if not row:
            raise LookupError("Cohorte no encontrada.")
        reason = " ".join(str(data.get("reason") or "").split())[:1000]
        if len(reason) < 12:
            raise ValueError("Registre una razón suficiente para el archivo.")
        now = self.now()
        con.execute(
            "UPDATE m25_pilot_cohort SET status='archived',archive_reason=?,archived_at=?,updated_at=? WHERE id=?",
            (reason, now, now, cohort_id),
        )
        con.commit()
        return self.report(con)
