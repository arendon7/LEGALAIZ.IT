from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class M24PilotOperationsCenter:
    """Controlled internal-pilot operations, privacy, support and release gates.

    The module is additive. It does not publish M23.2, approve legal content,
    process real payments, mutate active M21.1 documents or erase pilot data.
    """

    ENROLLMENT_CONFIRMATION = "ACEPTO PARTICIPAR EN EL PILOTO INTERNO"
    FEEDBACK_MAX = 1000
    INCIDENT_MAX = 2000

    def __init__(self, root: Path, release_governance, case_journey):
        self.root = Path(root)
        self.release_governance = release_governance
        self.case_journey = case_journey
        self.policy_path = self.root / "config" / "m24_8_pilot_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.product_codes = set(self.policy.get("pilot_products") or [])
        self.event_types = set(self.policy.get("event_types") or [])
        self.manual_checks = {row["id"]: row for row in self.policy.get("manual_validations") or []}

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    @staticmethod
    def _json(raw: Any, default: Any = None):
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {} if default is None else default

    @staticmethod
    def _redact_free_text(value: str, limit: int) -> str:
        value = re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", value)
        value = re.sub(r"(?<!\d)\d{7,}(?!\d)", "[dato numérico omitido]", value)
        return value

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m24_pilot_enrollment(
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL CHECK(status IN ('consented','withdrawn')),
              consent_version TEXT NOT NULL,
              product_codes_json TEXT NOT NULL,
              non_production_ack INTEGER NOT NULL,
              privacy_ack INTEGER NOT NULL,
              no_representation_ack INTEGER NOT NULL,
              fictitious_or_minimized_data_ack INTEGER NOT NULL,
              confirmation_text TEXT NOT NULL,
              consented_at TEXT,
              withdrawn_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS m24_pilot_event(
              id TEXT PRIMARY KEY,
              enrollment_id TEXT,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              case_id TEXT,
              product_code TEXT,
              event_type TEXT NOT NULL,
              duration_bucket TEXT,
              success INTEGER NOT NULL,
              error_code TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(enrollment_id) REFERENCES m24_pilot_enrollment(id),
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_pilot_event_created ON m24_pilot_event(created_at,event_type);
            CREATE TABLE IF NOT EXISTS m24_pilot_feedback(
              id TEXT PRIMARY KEY,
              enrollment_id TEXT NOT NULL,
              case_id TEXT,
              user_id TEXT NOT NULL,
              clarity INTEGER NOT NULL CHECK(clarity BETWEEN 1 AND 5),
              ease INTEGER NOT NULL CHECK(ease BETWEEN 1 AND 5),
              confidence INTEGER NOT NULL CHECK(confidence BETWEEN 1 AND 5),
              goal_met INTEGER NOT NULL,
              comment TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(enrollment_id) REFERENCES m24_pilot_enrollment(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_pilot_feedback_created ON m24_pilot_feedback(created_at);
            CREATE TABLE IF NOT EXISTS m24_pilot_incident(
              id TEXT PRIMARY KEY,
              reporter_id TEXT NOT NULL,
              reporter_role TEXT NOT NULL,
              case_id TEXT,
              category TEXT NOT NULL,
              severity TEXT NOT NULL CHECK(severity IN ('low','medium','high','critical')),
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('open','triaged','mitigated','closed')),
              owner_id TEXT,
              resolution_note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_pilot_incident_status ON m24_pilot_incident(status,severity,created_at);
            CREATE TABLE IF NOT EXISTS m24_pilot_manual_validation(
              check_id TEXT PRIMARY KEY,
              status TEXT NOT NULL CHECK(status IN ('pending','passed','failed','blocked')),
              evidence_note TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_name TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS m24_pilot_control(
              id INTEGER PRIMARY KEY CHECK(id=1),
              state TEXT NOT NULL CHECK(state IN ('frozen','active')),
              reason TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_name TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS m24_pilot_control_history(
              id TEXT PRIMARY KEY,
              from_state TEXT,
              to_state TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              reason TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        if not con.execute("SELECT 1 FROM m24_pilot_control WHERE id=1").fetchone():
            con.execute(
                "INSERT INTO m24_pilot_control(id,state,reason,actor_id,actor_name,updated_at) VALUES(1,'frozen',?,?,?,?)",
                ("Piloto congelado por defecto hasta activación expresa.", "SYSTEM", "Sistema", M24PilotOperationsCenter.now()),
            )

    def _enrollment(self, con, user_id: str) -> dict[str, Any] | None:
        row = con.execute("SELECT * FROM m24_pilot_enrollment WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["product_codes"] = self._json(item.pop("product_codes_json"), [])
        for key in ("non_production_ack", "privacy_ack", "no_representation_ack", "fictitious_or_minimized_data_ack"):
            item[key] = bool(item[key])
        return item

    def _control(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        return dict(con.execute("SELECT * FROM m24_pilot_control WHERE id=1").fetchone())

    def _case_access(self, con, case_id: str | None, actor: dict[str, Any]):
        if not case_id:
            return None
        row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not row or not self.case_journey.can_access(row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        return row

    def enroll(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "client":
            raise PermissionError("La inscripción al piloto corresponde a usuarios cliente.")
        action = str(data.get("action") or "consent").lower()
        now = self.now()
        if action == "withdraw":
            current = self._enrollment(con, str(actor.get("id")))
            if not current:
                raise LookupError("No existe una inscripción activa para retirar.")
            con.execute(
                "UPDATE m24_pilot_enrollment SET status='withdrawn',withdrawn_at=?,updated_at=? WHERE user_id=?",
                (now, now, str(actor.get("id"))),
            )
            con.commit()
            return self.client_summary(con, actor)
        confirmations = (
            data.get("non_production_ack"), data.get("privacy_ack"),
            data.get("no_representation_ack"), data.get("fictitious_or_minimized_data_ack"),
        )
        if not all(value is True for value in confirmations):
            raise ValueError("Debe aceptar expresamente las cuatro condiciones del piloto.")
        if str(data.get("confirmation") or "").strip() != self.ENROLLMENT_CONFIRMATION:
            raise ValueError(f"Debe escribir exactamente: {self.ENROLLMENT_CONFIRMATION}")
        products = [str(code).upper() for code in (data.get("product_codes") or [])]
        products = list(dict.fromkeys(products))
        if not products or any(code not in self.product_codes for code in products):
            raise ValueError("Seleccione al menos un producto habilitado para el piloto inicial.")
        record_id = str(uuid.uuid4())
        current = self._enrollment(con, str(actor.get("id")))
        if current:
            record_id = current["id"]
        con.execute(
            """INSERT INTO m24_pilot_enrollment
               (id,user_id,status,consent_version,product_codes_json,non_production_ack,privacy_ack,
                no_representation_ack,fictitious_or_minimized_data_ack,confirmation_text,consented_at,withdrawn_at,created_at,updated_at)
               VALUES(?,?, 'consented',?,?,?,?,?,?,?, ?,NULL,?,?)
               ON CONFLICT(user_id) DO UPDATE SET status='consented',consent_version=excluded.consent_version,
                product_codes_json=excluded.product_codes_json,non_production_ack=1,privacy_ack=1,
                no_representation_ack=1,fictitious_or_minimized_data_ack=1,confirmation_text=excluded.confirmation_text,
                consented_at=excluded.consented_at,withdrawn_at=NULL,updated_at=excluded.updated_at""",
            (
                record_id, str(actor.get("id")), self.policy["consent_version"], json.dumps(products), 1, 1, 1, 1,
                self.ENROLLMENT_CONFIRMATION, now, current.get("created_at") if current else now, now,
            ),
        )
        con.commit()
        return self.client_summary(con, actor)

    def record_event(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        event_type = str(data.get("event_type") or "").strip()
        if event_type not in self.event_types:
            raise ValueError("Tipo de evento no permitido por la política de minimización.")
        product_code = str(data.get("product_code") or "").upper() or None
        if product_code and product_code not in self.product_codes:
            raise ValueError("Producto fuera del piloto inicial.")
        case_row = self._case_access(con, str(data.get("case_id") or "") or None, actor)
        if case_row:
            case_product = str(case_row["product_code"])
            if product_code and case_product != product_code:
                raise ValueError("El producto del evento no coincide con el expediente.")
            product_code = case_product
        enrollment = self._enrollment(con, str(actor.get("id"))) if actor.get("role") == "client" else None
        if actor.get("role") == "client" and (not enrollment or enrollment.get("status") != "consented"):
            raise PermissionError("El registro de métricas exige consentimiento vigente del piloto.")
        duration = int(data.get("duration_ms") or 0)
        bucket = "under_30s" if duration < 30000 else "30s_to_2m" if duration < 120000 else "2m_to_10m" if duration < 600000 else "over_10m"
        error_code = re.sub(r"[^A-Z0-9_-]", "", str(data.get("error_code") or "").upper())[:60] or None
        con.execute(
            """INSERT INTO m24_pilot_event
               (id,enrollment_id,actor_id,actor_role,case_id,product_code,event_type,duration_bucket,success,error_code,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), enrollment.get("id") if enrollment else None, str(actor.get("id")), str(actor.get("role")),
             str(data.get("case_id") or "") or None, product_code, event_type, bucket, 1 if data.get("success", True) else 0,
             error_code, self.now()),
        )
        con.commit()
        return {"recorded": True, "event_type": event_type, "privacy": "no_narrative_no_free_text"}

    def submit_feedback(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "client":
            raise PermissionError("La retroalimentación del piloto corresponde a usuarios cliente.")
        enrollment = self._enrollment(con, str(actor.get("id")))
        if not enrollment or enrollment.get("status") != "consented":
            raise PermissionError("Debe existir consentimiento vigente para enviar retroalimentación.")
        case_id = str(data.get("case_id") or "") or None
        self._case_access(con, case_id, actor)
        ratings = {key: int(data.get(key) or 0) for key in ("clarity", "ease", "confidence")}
        if any(value < 1 or value > 5 for value in ratings.values()):
            raise ValueError("Las calificaciones deben estar entre 1 y 5.")
        comment = self._redact_free_text(data.get("comment") or "", self.FEEDBACK_MAX)
        con.execute(
            """INSERT INTO m24_pilot_feedback
               (id,enrollment_id,case_id,user_id,clarity,ease,confidence,goal_met,comment,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), enrollment["id"], case_id, str(actor.get("id")), ratings["clarity"], ratings["ease"],
             ratings["confidence"], 1 if data.get("goal_met") else 0, comment, self.now()),
        )
        con.commit()
        return {"recorded": True, "comment_redacted": comment != str(data.get("comment") or "").strip()}

    def report_incident(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        case_id = str(data.get("case_id") or "") or None
        self._case_access(con, case_id, actor)
        category = str(data.get("category") or "other").lower()
        if category not in {"legal_content", "privacy", "security", "document", "usability", "performance", "other"}:
            raise ValueError("Categoría de incidente inválida.")
        requested = str(data.get("severity") or "medium").lower()
        if actor.get("role") == "client" and requested in {"high", "critical"}:
            requested = "medium"
        if requested not in {"low", "medium", "high", "critical"}:
            raise ValueError("Severidad inválida.")
        title = self._redact_free_text(data.get("title") or "", 160)
        description = self._redact_free_text(data.get("description") or "", self.INCIDENT_MAX)
        if len(title) < 8 or len(description) < 20:
            raise ValueError("Describa el incidente con un título y detalle suficientes, sin datos sensibles.")
        incident_id = str(uuid.uuid4())
        now = self.now()
        con.execute(
            """INSERT INTO m24_pilot_incident
               (id,reporter_id,reporter_role,case_id,category,severity,title,description,status,owner_id,resolution_note,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?, 'open',NULL,'',?,?)""",
            (incident_id, str(actor.get("id")), str(actor.get("role")), case_id, category, requested, title, description, now, now),
        )
        con.commit()
        return {"recorded": True, "incident_id": incident_id, "severity": requested}

    def triage_incident(self, con, incident_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede clasificar y cerrar incidentes.")
        row = con.execute("SELECT * FROM m24_pilot_incident WHERE id=?", (incident_id,)).fetchone()
        if not row:
            raise LookupError("Incidente no encontrado.")
        status = str(data.get("status") or row["status"]).lower()
        severity = str(data.get("severity") or row["severity"]).lower()
        if status not in {"open", "triaged", "mitigated", "closed"} or severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("Estado o severidad inválidos.")
        note = self._redact_free_text(data.get("resolution_note") or "", 1500)
        if status in {"mitigated", "closed"} and len(note) < 20:
            raise ValueError("La mitigación o cierre exige una nota verificable.")
        con.execute(
            "UPDATE m24_pilot_incident SET status=?,severity=?,owner_id=?,resolution_note=?,updated_at=? WHERE id=?",
            (status, severity, str(actor.get("id")), note, self.now(), incident_id),
        )
        con.commit()
        return dict(con.execute("SELECT * FROM m24_pilot_incident WHERE id=?", (incident_id,)).fetchone())

    def set_manual_validation(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede registrar la validación manual de salida.")
        check_id = str(data.get("check_id") or "")
        status = str(data.get("status") or "pending").lower()
        if check_id not in self.manual_checks or status not in {"pending", "passed", "failed", "blocked"}:
            raise ValueError("Control manual o estado inválido.")
        note = self._redact_free_text(data.get("evidence_note") or "", 1200)
        if status != "pending" and len(note) < 15:
            raise ValueError("El resultado debe incluir evidencia o explicación suficiente.")
        con.execute(
            """INSERT INTO m24_pilot_manual_validation(check_id,status,evidence_note,actor_id,actor_name,updated_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(check_id) DO UPDATE SET status=excluded.status,
               evidence_note=excluded.evidence_note,actor_id=excluded.actor_id,actor_name=excluded.actor_name,updated_at=excluded.updated_at""",
            (check_id, status, note, str(actor.get("id")), self._actor_name(actor), self.now()),
        )
        con.commit()
        return self.manual_validations(con)

    def manual_validations(self, con) -> list[dict[str, Any]]:
        self.ensure_schema(con)
        saved = {row["check_id"]: dict(row) for row in con.execute("SELECT * FROM m24_pilot_manual_validation").fetchall()}
        return [{**item, **saved.get(check_id, {"status": "pending", "evidence_note": "", "actor_id": None, "actor_name": None, "updated_at": None})}
                for check_id, item in self.manual_checks.items()]

    def metrics(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        enrollments = con.execute("SELECT COUNT(*) FROM m24_pilot_enrollment WHERE status='consented'").fetchone()[0]
        event_rows = con.execute("SELECT event_type,COUNT(*) AS count,SUM(success) AS success FROM m24_pilot_event GROUP BY event_type ORDER BY event_type").fetchall()
        feedback = con.execute("SELECT COUNT(*) AS count,AVG(clarity) AS clarity,AVG(ease) AS ease,AVG(confidence) AS confidence,AVG(goal_met) AS goal_met FROM m24_pilot_feedback").fetchone()
        delivered = con.execute("SELECT COUNT(DISTINCT case_id) FROM m24_pilot_event WHERE event_type='delivered' AND success=1 AND case_id IS NOT NULL").fetchone()[0]
        incidents = con.execute("SELECT severity,status,COUNT(*) AS count FROM m24_pilot_incident GROUP BY severity,status").fetchall()
        return {
            "consented_participants": int(enrollments),
            "delivered_cases": int(delivered),
            "events": [{"event_type": row["event_type"], "count": int(row["count"]), "success": int(row["success"] or 0)} for row in event_rows],
            "feedback": {
                "count": int(feedback["count"] or 0),
                "average_clarity": round(float(feedback["clarity"] or 0), 2),
                "average_ease": round(float(feedback["ease"] or 0), 2),
                "average_confidence": round(float(feedback["confidence"] or 0), 2),
                "goal_met_rate": round(float(feedback["goal_met"] or 0), 2),
            },
            "incidents": [{"severity": row["severity"], "status": row["status"], "count": int(row["count"])} for row in incidents],
        }

    def release_gate(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        release = self.release_governance.summary(con)
        active_products = [row["product_code"] for row in release.get("products", []) if row.get("internal_pilot_active")]
        metrics = self.metrics(con)
        manual = self.manual_validations(con)
        gates = self.policy.get("gates") or {}
        high_open = sum(row["count"] for row in metrics["incidents"] if row["severity"] in {"high", "critical"} and row["status"] != "closed")
        checks = {
            "active_products": len(active_products) >= int(gates.get("minimum_active_products", 1)),
            "consented_participants": metrics["consented_participants"] >= int(gates.get("minimum_consented_participants", 4)),
            "delivered_cases": metrics["delivered_cases"] >= int(gates.get("minimum_delivered_cases", 4)),
            "feedback_responses": metrics["feedback"]["count"] >= int(gates.get("minimum_feedback_responses", 4)),
            "average_clarity": metrics["feedback"]["average_clarity"] >= float(gates.get("minimum_average_clarity", 4.0)),
            "average_ease": metrics["feedback"]["average_ease"] >= float(gates.get("minimum_average_ease", 4.0)),
            "no_open_high_or_critical_incidents": high_open <= int(gates.get("maximum_open_high_or_critical_incidents", 0)),
            "manual_validations": bool(manual) and all(row["status"] == "passed" for row in manual),
        }
        internal_ready = all(checks.values()) and self._control(con)["state"] == "active"
        return {
            "schema": "legalai_m24_8_release_gate_v1",
            "policy_version": self.policy["policy_version"],
            "control": self._control(con),
            "active_products": active_products,
            "checks": checks,
            "passed_checks": sum(1 for value in checks.values() if value),
            "total_checks": len(checks),
            "internal_pilot_ready": internal_ready,
            "public_production_ready": False,
            "public_blockers": [
                "M23.2 continúa sin publicación para clientes.",
                "El checkout sigue siendo sandbox y no procesa pagos reales.",
                "Se requiere aprobación jurídica y QA humana por producto.",
                "La salida pública exige revisión manual multidispositivo y de tecnologías de asistencia.",
            ],
            "metrics": metrics,
            "manual_validations": manual,
        }

    def set_control(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede activar o congelar el piloto.")
        action = str(data.get("action") or "").lower()
        if action not in {"activate", "freeze"}:
            raise ValueError("Acción de control inválida.")
        expected = self.policy["confirmations"][action]
        if str(data.get("confirmation") or "").strip() != expected:
            raise ValueError(f"Debe escribir exactamente: {expected}")
        reason = self._redact_free_text(data.get("reason") or "", 1200)
        if len(reason) < 20:
            raise ValueError("La decisión exige una justificación verificable.")
        current = self._control(con)
        target = "active" if action == "activate" else "frozen"
        gate_before = self.release_gate(con)
        if action == "activate":
            if not gate_before.get("active_products"):
                raise ValueError("Debe existir al menos un producto con aprobación dual y activación interna individual.")
            open_high = [row for row in gate_before["metrics"]["incidents"] if row["severity"] in {"high", "critical"} and row["status"] != "closed" and row["count"]]
            if open_high:
                raise ValueError("No puede activarse el piloto con incidentes altos o críticos abiertos.")
        now = self.now()
        con.execute(
            "UPDATE m24_pilot_control SET state=?,reason=?,actor_id=?,actor_name=?,updated_at=? WHERE id=1",
            (target, reason, str(actor.get("id")), self._actor_name(actor), now),
        )
        snapshot = {
            "release_gate_before": gate_before,
            "candidate_published": False,
            "active_legacy_generation_changed": False,
            "data_preserved": True,
        }
        con.execute(
            """INSERT INTO m24_pilot_control_history
               (id,from_state,to_state,actor_id,actor_role,reason,snapshot_json,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), current["state"], target, str(actor.get("id")), str(actor.get("role")), reason,
             json.dumps(snapshot, ensure_ascii=False), now),
        )
        con.commit()
        return self.release_gate(con)

    def client_summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        enrollment = self._enrollment(con, str(actor.get("id")))
        release = self.release_governance.summary(con)
        active_products = [row["product_code"] for row in release.get("products", []) if row.get("internal_pilot_active") and row["product_code"] in self.product_codes]
        eligible = bool(enrollment and enrollment.get("status") == "consented" and self._control(con)["state"] == "active" and set(enrollment["product_codes"]) & set(active_products))
        return {
            "schema": "legalai_m24_8_client_pilot_summary_v1",
            "policy": self.policy,
            "control": self._control(con),
            "enrollment": enrollment,
            "active_products": active_products,
            "eligible": eligible,
            "cases": [dict(row) for row in con.execute("SELECT id,title,product_code,status,updated_at FROM cases WHERE owner_id=? ORDER BY updated_at DESC LIMIT 20", (str(actor.get("id")),)).fetchall()],
            "feedback_count": int(con.execute("SELECT COUNT(*) FROM m24_pilot_feedback WHERE user_id=?", (str(actor.get("id")),)).fetchone()[0]),
            "notice": self.policy["notice"],
        }

    def admin_summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La operación agregada del piloto exige rol profesional.")
        incidents = [dict(row) for row in con.execute(
            "SELECT * FROM m24_pilot_incident ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, created_at DESC LIMIT 100"
        ).fetchall()]
        gate = self.release_gate(con)
        return {
            "schema": "legalai_m24_8_admin_pilot_summary_v1",
            "policy": self.policy,
            "release_gate": gate,
            "incidents": incidents,
            "control_history": [dict(row) for row in con.execute("SELECT * FROM m24_pilot_control_history ORDER BY created_at DESC LIMIT 30").fetchall()],
            "notice": self.policy["notice"],
            "can_govern": actor.get("role") == "admin",
        }

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        return self.client_summary(con, actor) if actor.get("role") == "client" else self.admin_summary(con, actor)
