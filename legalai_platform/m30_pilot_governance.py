from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class M30PilotGovernanceCenter:
    """Comunicaciones, incidentes, retención y cierre del piloto M30.3.

    Esta capa no envía correos, no elimina expedientes ni documentos jurídicos y
    no habilita producción pública. Las acciones irreversibles sobre los datos
    operativos del piloto exigen aprobación jurídica y QA de personas distintas.
    """

    def __init__(self, root: Path, pilot_operations, pilot_center, participants, audit_fn):
        self.root = Path(root).resolve()
        self.pilot_operations = pilot_operations
        self.pilot_center = pilot_center
        self.participants = participants
        self.audit_fn = audit_fn
        self.policy_path = self.root / "config" / "m30_3_closure_incident_retention_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))

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
    def _mask_email(value: str | None) -> str:
        email = str(value or "")
        if "@" not in email:
            return "Sin correo"
        local, domain = email.split("@", 1)
        return f"{local[:1] or '*'}***@{domain}"

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _json(raw: Any, default: Any):
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _add_business_days(start: datetime, days: int) -> datetime:
        current = start
        remaining = int(days)
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:
                remaining -= 1
        return current

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m30_pilot_communication(
              id TEXT PRIMARY KEY,
              cohort_id TEXT,
              participant_id TEXT,
              user_id TEXT,
              audience_ref TEXT NOT NULL DEFAULT '',
              template_code TEXT NOT NULL,
              channel TEXT NOT NULL CHECK(channel IN ('account','manual_export')),
              status TEXT NOT NULL CHECK(status IN ('ready','exported','acknowledged','cancelled')),
              subject TEXT NOT NULL,
              body TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              created_by_id TEXT NOT NULL,
              created_by_name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              exported_at TEXT,
              acknowledged_at TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m30_communication_status
              ON m30_pilot_communication(status,template_code,created_at);
            CREATE INDEX IF NOT EXISTS idx_m30_communication_user
              ON m30_pilot_communication(user_id,status,created_at);

            CREATE TABLE IF NOT EXISTS m30_pilot_incident_governance(
              incident_id TEXT PRIMARY KEY,
              detected_at TEXT NOT NULL,
              area_notified_at TEXT,
              personal_data_affected INTEGER NOT NULL DEFAULT 0,
              data_classes_json TEXT NOT NULL DEFAULT '[]',
              affected_records_bucket TEXT NOT NULL DEFAULT 'unknown',
              containment_status TEXT NOT NULL DEFAULT 'not_started',
              regulatory_assessment TEXT NOT NULL DEFAULT 'pending',
              report_due_at TEXT,
              reported_at TEXT,
              reporting_channel TEXT NOT NULL DEFAULT '',
              legal_hold INTEGER NOT NULL DEFAULT 0,
              root_cause_code TEXT NOT NULL DEFAULT 'unknown',
              next_update_at TEXT,
              assessment_note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(incident_id) REFERENCES m24_pilot_incident(id)
            );

            CREATE TABLE IF NOT EXISTS m30_pilot_retention_request(
              id TEXT PRIMARY KEY,
              participant_id TEXT NOT NULL,
              action_type TEXT NOT NULL CHECK(action_type IN ('purge_invitation_record','pseudonymize_pilot_participation')),
              status TEXT NOT NULL CHECK(status IN ('pending_legal','pending_qa','approved','executed','cancelled','blocked_legal_hold')),
              due_at TEXT NOT NULL,
              rationale_code TEXT NOT NULL,
              legal_approver_id TEXT,
              legal_approver_name TEXT,
              legal_approved_at TEXT,
              qa_approver_id TEXT,
              qa_approver_name TEXT,
              qa_approved_at TEXT,
              created_by_id TEXT NOT NULL,
              created_by_name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              executed_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_m30_retention_open_participant
              ON m30_pilot_retention_request(participant_id)
              WHERE status IN ('pending_legal','pending_qa','approved','blocked_legal_hold');

            CREATE TABLE IF NOT EXISTS m30_pilot_retention_tombstone(
              id TEXT PRIMARY KEY,
              participant_hash TEXT NOT NULL,
              product_code TEXT NOT NULL,
              terminal_status TEXT NOT NULL,
              consent_hash TEXT NOT NULL,
              event_digest TEXT NOT NULL,
              action_type TEXT NOT NULL,
              cohort_id TEXT NOT NULL,
              closed_at TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS m30_pilot_closure(
              id TEXT PRIMARY KEY,
              cohort_id TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('close','extend','hold')),
              reason_code TEXT NOT NULL,
              summary TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending_legal','pending_qa','approved','closed','cancelled')),
              snapshot_json TEXT NOT NULL,
              legal_approver_id TEXT,
              legal_approver_name TEXT,
              legal_approved_at TEXT,
              qa_approver_id TEXT,
              qa_approver_name TEXT,
              qa_approved_at TEXT,
              created_by_id TEXT NOT NULL,
              created_by_name TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              closed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_m30_closure_cohort ON m30_pilot_closure(cohort_id,status,created_at);
            """
        )

    def _require_professional(self, actor: dict[str, Any]) -> None:
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La gobernanza del piloto exige rol profesional.")

    def _active_cohort(self, con) -> dict[str, Any] | None:
        self.pilot_center.readiness.ensure_schema(con)
        report = self.pilot_center.readiness.report(con)
        return self.pilot_center._active_cohort(report)

    def _communication_rows(self, con, user_id: str | None = None) -> list[dict[str, Any]]:
        sql = """SELECT c.*,u.email user_email,u.name user_name,p.product_code
                 FROM m30_pilot_communication c
                 LEFT JOIN users u ON u.id=c.user_id
                 LEFT JOIN m30_pilot_participant p ON p.id=c.participant_id"""
        params: tuple[Any, ...] = ()
        if user_id:
            sql += " WHERE c.user_id=?"
            params = (user_id,)
        sql += " ORDER BY c.created_at DESC LIMIT 200"
        rows = []
        for row in con.execute(sql, params).fetchall():
            item = dict(row)
            item["masked_email"] = self._mask_email(item.pop("user_email", ""))
            rows.append(item)
        return rows

    def _incident_rows(self, con) -> list[dict[str, Any]]:
        rows = con.execute(
            """SELECT i.*,g.detected_at,g.area_notified_at,g.personal_data_affected,g.data_classes_json,
                      g.affected_records_bucket,g.containment_status,g.regulatory_assessment,g.report_due_at,
                      g.reported_at,g.reporting_channel,g.legal_hold,g.root_cause_code,g.next_update_at,g.assessment_note
               FROM m24_pilot_incident i
               LEFT JOIN m30_pilot_incident_governance g ON g.incident_id=i.id
               ORDER BY CASE i.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
                        CASE i.status WHEN 'open' THEN 1 WHEN 'triaged' THEN 2 WHEN 'mitigated' THEN 3 ELSE 4 END,
                        i.created_at DESC LIMIT 200"""
        ).fetchall()
        now = datetime.now(timezone.utc)
        result = []
        for row in rows:
            item = dict(row)
            item["data_classes"] = self._json(item.pop("data_classes_json", "[]"), [])
            item["personal_data_affected"] = bool(item.get("personal_data_affected"))
            item["legal_hold"] = bool(item.get("legal_hold"))
            item["report_overdue"] = False
            if item.get("report_due_at") and item.get("regulatory_assessment") == "report_required" and not item.get("reported_at"):
                try:
                    item["report_overdue"] = datetime.fromisoformat(str(item["report_due_at"]).replace("Z", "+00:00")) < now
                except ValueError:
                    pass
            result.append(item)
        return result

    def _participant_legal_hold(self, con, participant: dict[str, Any]) -> bool:
        plan = con.execute("SELECT case_id FROM m25_pilot_case_plan WHERE id=?", (participant["case_plan_id"],)).fetchone()
        case_id = plan["case_id"] if plan else None
        sql = """SELECT 1 FROM m24_pilot_incident i
                 JOIN m30_pilot_incident_governance g ON g.incident_id=i.id
                 WHERE i.status!='closed' AND g.legal_hold=1 AND (i.case_id=? OR i.case_id IS NULL) LIMIT 1"""
        return bool(con.execute(sql, (case_id,)).fetchone())

    def _retention_due(self, participant: dict[str, Any], plan: dict[str, Any] | None) -> tuple[str, str] | None:
        status = participant.get("status")
        retention = self.policy["retention"]
        if status in {"declined", "expired"}:
            base = participant.get("responded_at") or participant.get("expires_at") or participant.get("updated_at")
            days = int(retention["invitation_days_after_decline_or_expiry"])
            action = "purge_invitation_record"
        elif status == "withdrawn":
            base = participant.get("withdrawn_at") or participant.get("updated_at")
            days = int(retention["participant_days_after_withdrawal_or_cohort_closure"])
            action = "pseudonymize_pilot_participation"
        elif status == "accepted" and plan and plan.get("status") in {"completed", "cancelled"}:
            base = plan.get("updated_at")
            days = int(retention["participant_days_after_withdrawal_or_cohort_closure"])
            action = "pseudonymize_pilot_participation"
        else:
            return None
        try:
            due = datetime.fromisoformat(str(base).replace("Z", "+00:00")) + timedelta(days=days)
        except (TypeError, ValueError):
            due = datetime.now(timezone.utc) + timedelta(days=days)
        return action, due.isoformat(timespec="seconds")

    def _retention_candidates(self, con) -> list[dict[str, Any]]:
        rows = con.execute(
            """SELECT p.*,u.name user_name,u.email user_email,cp.status plan_status,cp.updated_at plan_updated_at
               FROM m30_pilot_participant p
               JOIN users u ON u.id=p.user_id
               JOIN m25_pilot_case_plan cp ON cp.id=p.case_plan_id
               ORDER BY p.updated_at DESC"""
        ).fetchall()
        result = []
        for row in rows:
            participant = dict(row)
            plan = {"status": participant.pop("plan_status"), "updated_at": participant.pop("plan_updated_at")}
            due = self._retention_due(participant, plan)
            if not due:
                continue
            existing = con.execute(
                "SELECT id,status FROM m30_pilot_retention_request WHERE participant_id=? ORDER BY created_at DESC LIMIT 1",
                (participant["id"],),
            ).fetchone()
            result.append({
                "participant_id": participant["id"], "user_name": participant["user_name"],
                "masked_email": self._mask_email(participant.pop("user_email", "")),
                "product_code": participant["product_code"], "participant_status": participant["status"],
                "plan_status": plan["status"], "action_type": due[0], "due_at": due[1],
                "legal_hold": self._participant_legal_hold(con, participant),
                "request_id": existing["id"] if existing else None,
                "request_status": existing["status"] if existing else None,
            })
        return result

    def _retention_requests(self, con) -> list[dict[str, Any]]:
        return [dict(row) for row in con.execute(
            "SELECT * FROM m30_pilot_retention_request ORDER BY created_at DESC LIMIT 200"
        ).fetchall()]

    def _closure_gate(self, con, cohort: dict[str, Any] | None) -> dict[str, Any]:
        center = self.pilot_center.summary(con, {"id": "SYSTEM", "name": "Sistema", "role": "admin"})
        plans = list((cohort or {}).get("plans") or [])
        incidents = self._incident_rows(con)
        participants = self.participants._participant_rows(con)
        checks = {
            "cohort_exists": bool(cohort),
            "terminal_case_plans": bool(plans) and all(row.get("status") in {"completed", "cancelled"} for row in plans),
            "no_high_or_critical_incidents": not any(row.get("severity") in {"high", "critical"} and row.get("status") != "closed" for row in incidents),
            "no_high_or_critical_support": int(center.get("support_metrics", {}).get("high_or_critical_open") or 0) == 0,
            "no_pending_invitations": not any(row.get("status") == "invited" for row in participants),
            "evidence_gate": bool(center.get("evidence_gate", {}).get("ready")),
        }
        return {"checks": checks, "passed": sum(bool(v) for v in checks.values()), "total": len(checks), "ready": all(checks.values())}

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.pilot_operations.ensure_schema(con)
        self.pilot_center.ensure_schema(con)
        self.participants.ensure_schema(con)
        self.ensure_schema(con)
        cohort = self._active_cohort(con)
        communications = self._communication_rows(con)
        incidents = self._incident_rows(con)
        closures = [dict(row) for row in con.execute("SELECT * FROM m30_pilot_closure ORDER BY created_at DESC LIMIT 50").fetchall()]
        return {
            "schema": "legalaizit-m30-3-governance-summary-v1", "milestone": "M30.3", "version": self.policy["version"],
            "policy": self.policy, "active_cohort": cohort, "communications": communications,
            "communication_metrics": {
                "ready": sum(row["status"] == "ready" for row in communications),
                "exported": sum(row["status"] == "exported" for row in communications),
                "acknowledged": sum(row["status"] == "acknowledged" for row in communications),
            },
            "incidents": incidents,
            "incident_metrics": {
                "open": sum(row["status"] != "closed" for row in incidents),
                "high_or_critical_open": sum(row["severity"] in {"high", "critical"} and row["status"] != "closed" for row in incidents),
                "regulatory_pending": sum(row.get("personal_data_affected") and row.get("regulatory_assessment") == "pending" for row in incidents),
                "report_overdue": sum(bool(row.get("report_overdue")) for row in incidents),
            },
            "retention_candidates": self._retention_candidates(con),
            "retention_requests": self._retention_requests(con),
            "retention_tombstones": [dict(row) for row in con.execute("SELECT * FROM m30_pilot_retention_tombstone ORDER BY created_at DESC LIMIT 100").fetchall()],
            "closure_gate": self._closure_gate(con, cohort), "closures": closures,
            "notice": "Las comunicaciones no se envían externamente. La eliminación automática permanece bloqueada y los plazos regulatorios requieren verificación jurídica del caso concreto.",
        }

    def client_summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "client":
            raise PermissionError("Esta vista corresponde al participante cliente.")
        self.ensure_schema(con)
        rows = self._communication_rows(con, str(actor.get("id")))
        return {
            "schema": "legalaizit-m30-3-client-communications-v1", "milestone": "M30.3", "version": self.policy["version"],
            "communications": rows, "notice": "Los avisos no incluyen hechos jurídicos ni datos sensibles."
        }

    def queue_communication(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.ensure_schema(con)
        template_code = str(data.get("template_code") or "")
        template = self.policy["communication_templates"].get(template_code)
        if not template:
            raise ValueError("Plantilla de comunicación no permitida.")
        participant_id = str(data.get("participant_id") or "") or None
        participant = None
        if participant_id:
            participant = con.execute("SELECT * FROM m30_pilot_participant WHERE id=?", (participant_id,)).fetchone()
            if not participant:
                raise LookupError("Participante no encontrado.")
        if template_code != "pilot_closure_notice" and not participant:
            raise ValueError("La comunicación seleccionada exige un participante.")
        cohort = self._active_cohort(con)
        targets = [participant] if participant else con.execute(
            "SELECT * FROM m30_pilot_participant WHERE cohort_id=? AND status IN ('accepted','withdrawn')", ((cohort or {}).get("id"),)
        ).fetchall()
        if not targets:
            raise ValueError("No existen destinatarios elegibles.")
        created = []
        now = self.now()
        for target in targets:
            duplicate = con.execute(
                "SELECT 1 FROM m30_pilot_communication WHERE participant_id=? AND template_code=? AND status!='cancelled'",
                (target["id"], template_code),
            ).fetchone()
            if duplicate:
                continue
            communication_id = str(uuid.uuid4())
            canonical = {"template_code": template_code, "participant_id": target["id"], "version": self.policy["version"]}
            con.execute(
                """INSERT INTO m30_pilot_communication
                   (id,cohort_id,participant_id,user_id,audience_ref,template_code,channel,status,subject,body,payload_hash,
                    created_by_id,created_by_name,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,'ready',?,?,?,?,?,?,?)""",
                (communication_id, target["cohort_id"], target["id"], target["user_id"], "", template_code,
                 str(data.get("channel") or "account"), template["subject"], template["body"],
                 self._hash(json.dumps(canonical, sort_keys=True)), str(actor.get("id")), self._actor_name(actor), now, now),
            )
            created.append(communication_id)
        con.commit()
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_communication", ",".join(created) or "none", "queue", {"template_code": template_code, "created": len(created)})
        con.commit()
        result = self.summary(con, actor)
        result["created_communications"] = created
        return result

    def update_communication(self, con, communication_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m30_pilot_communication WHERE id=?", (communication_id,)).fetchone()
        if not row:
            raise LookupError("Comunicación no encontrada.")
        status = str(data.get("status") or "acknowledged")
        if actor.get("role") == "client":
            if row["user_id"] != str(actor.get("id")) or status != "acknowledged":
                raise PermissionError("Solo puede confirmar sus propias comunicaciones.")
        else:
            self._require_professional(actor)
        if status not in self.policy["communication_statuses"]:
            raise ValueError("Estado de comunicación inválido.")
        now = self.now()
        con.execute(
            """UPDATE m30_pilot_communication SET status=?,exported_at=CASE WHEN ?='exported' THEN ? ELSE exported_at END,
               acknowledged_at=CASE WHEN ?='acknowledged' THEN ? ELSE acknowledged_at END,updated_at=? WHERE id=?""",
            (status, status, now, status, now, now, communication_id),
        )
        con.commit()
        return self.client_summary(con, actor) if actor.get("role") == "client" else self.summary(con, actor)

    def report_incident(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.pilot_operations.ensure_schema(con)
        self.ensure_schema(con)
        bucket = str(data.get("affected_records_bucket") or "unknown")
        if bucket not in self.policy["incident"]["affected_record_buckets"]:
            raise ValueError("Rango de registros afectados inválido.")
        requested_classes = [str(x) for x in (data.get("data_classes") or [])]
        if any(x not in self.policy["incident"]["data_classes"] for x in requested_classes):
            raise ValueError("Clase de datos afectada inválida.")
        classes = list(dict.fromkeys(requested_classes))
        payload = {
            "case_id": data.get("case_id"), "category": data.get("category"), "severity": data.get("severity"),
            "title": data.get("title"), "description": data.get("description"),
        }
        created = self.pilot_operations.report_incident(con, payload, actor)
        incident_id = created["incident_id"]
        now_dt = datetime.now(timezone.utc)
        area_notified = now_dt if actor.get("role") in {"admin", "specialist"} else None
        affected = bool(data.get("personal_data_affected"))
        due = self._add_business_days(area_notified, int(self.policy["incident"]["regulatory_business_days"])) if affected and area_notified else None
        now = now_dt.isoformat(timespec="seconds")
        con.execute(
            """INSERT INTO m30_pilot_incident_governance
               (incident_id,detected_at,area_notified_at,personal_data_affected,data_classes_json,affected_records_bucket,
                containment_status,regulatory_assessment,report_due_at,legal_hold,root_cause_code,next_update_at,created_at,updated_at)
               VALUES(?,?,?,?,?,?, 'not_started','pending',?,?, 'unknown',?,?,?)""",
            (incident_id, now, area_notified.isoformat(timespec="seconds") if area_notified else None, 1 if affected else 0,
             json.dumps(classes), bucket, due.isoformat(timespec="seconds") if due else None, 1 if affected else 0,
             (now_dt + timedelta(hours=24)).isoformat(timespec="seconds"), now, now),
        )
        con.commit()
        return self.client_summary(con, actor) if actor.get("role") == "client" else self.summary(con, actor)

    def triage_incident(self, con, incident_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede clasificar incidentes y su reporte regulatorio.")
        self.ensure_schema(con)
        incident = con.execute("SELECT * FROM m24_pilot_incident WHERE id=?", (incident_id,)).fetchone()
        if not incident:
            raise LookupError("Incidente no encontrado.")
        governance = con.execute("SELECT * FROM m30_pilot_incident_governance WHERE incident_id=?", (incident_id,)).fetchone()
        if not governance:
            raise LookupError("El incidente no tiene ficha de gobernanza M30.3.")
        containment = str(data.get("containment_status") or governance["containment_status"])
        assessment = str(data.get("regulatory_assessment") or governance["regulatory_assessment"])
        root_cause = str(data.get("root_cause_code") or governance["root_cause_code"])
        if containment not in self.policy["incident"]["containment_statuses"]:
            raise ValueError("Estado de contención inválido.")
        if assessment not in self.policy["incident"]["regulatory_assessments"]:
            raise ValueError("Evaluación regulatoria inválida.")
        if root_cause not in self.policy["incident"]["root_cause_codes"]:
            raise ValueError("Causa raíz inválida.")
        personal_data = bool(data.get("personal_data_affected", governance["personal_data_affected"]))
        area_notified = governance["area_notified_at"] or self.now()
        area_dt = datetime.fromisoformat(str(area_notified).replace("Z", "+00:00"))
        due = self._add_business_days(area_dt, int(self.policy["incident"]["regulatory_business_days"])) if personal_data else None
        reported_at = str(data.get("reported_at") or governance["reported_at"] or "") or None
        channel = str(data.get("reporting_channel") or governance["reporting_channel"] or "")
        if assessment == "report_required" and str(data.get("status") or incident["status"]) == "closed" and (not reported_at or channel not in self.policy["incident"]["reporting_channels"]):
            raise ValueError("El cierre exige fecha y canal del reporte regulatorio cuando fue determinado como obligatorio.")
        status = str(data.get("status") or incident["status"])
        if status == "closed" and incident["severity"] in {"high", "critical"} and containment not in {"contained", "monitoring", "recovered"}:
            raise ValueError("Un incidente grave no puede cerrarse sin contención verificable.")
        triage = self.pilot_operations.triage_incident(con, incident_id, {
            "status": status, "severity": data.get("severity") or incident["severity"],
            "resolution_note": data.get("resolution_note") or governance["assessment_note"] or "Evaluación y acciones documentadas en la ficha M30.3.",
        }, actor)
        note = self._clean_text(data.get("assessment_note") or data.get("resolution_note") or "", 1500)
        legal_hold = bool(data.get("legal_hold", personal_data and status != "closed"))
        con.execute(
            """UPDATE m30_pilot_incident_governance SET area_notified_at=?,personal_data_affected=?,data_classes_json=?,
               affected_records_bucket=?,containment_status=?,regulatory_assessment=?,report_due_at=?,reported_at=?,
               reporting_channel=?,legal_hold=?,root_cause_code=?,next_update_at=?,assessment_note=?,updated_at=? WHERE incident_id=?""",
            (area_notified, 1 if personal_data else 0,
             json.dumps([x for x in (data.get("data_classes") or self._json(governance["data_classes_json"], [])) if x in self.policy["incident"]["data_classes"]]),
             str(data.get("affected_records_bucket") or governance["affected_records_bucket"]), containment, assessment,
             due.isoformat(timespec="seconds") if due else None, reported_at, channel, 1 if legal_hold else 0, root_cause,
             str(data.get("next_update_at") or governance["next_update_at"] or "") or None, note, self.now(), incident_id),
        )
        con.commit()
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_incident_governance", incident_id, "triage", {"status": triage["status"], "assessment": assessment, "legal_hold": legal_hold})
        con.commit()
        return self.summary(con, actor)

    def create_retention_request(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede iniciar una depuración controlada.")
        self.participants.ensure_schema(con)
        self.ensure_schema(con)
        participant_id = str(data.get("participant_id") or "")
        row = con.execute(
            """SELECT p.*,cp.status plan_status,cp.updated_at plan_updated_at FROM m30_pilot_participant p
               JOIN m25_pilot_case_plan cp ON cp.id=p.case_plan_id WHERE p.id=?""", (participant_id,)
        ).fetchone()
        if not row:
            raise LookupError("Participante no encontrado.")
        participant = dict(row)
        plan = {"status": participant.pop("plan_status"), "updated_at": participant.pop("plan_updated_at")}
        due = self._retention_due(participant, plan)
        if not due:
            raise ValueError("El registro todavía no es elegible para retención terminal.")
        hold = self._participant_legal_hold(con, participant)
        request_id = str(uuid.uuid4())
        now = self.now()
        con.execute(
            """INSERT INTO m30_pilot_retention_request
               (id,participant_id,action_type,status,due_at,rationale_code,created_by_id,created_by_name,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (request_id, participant_id, due[0], "blocked_legal_hold" if hold else "pending_legal", due[1],
             str(data.get("rationale_code") or "purpose_completed"), str(actor.get("id")), self._actor_name(actor), now, now),
        )
        con.commit()
        return self.summary(con, actor)

    def approve_retention(self, con, request_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m30_pilot_retention_request WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise LookupError("Solicitud de retención no encontrada.")
        stage = str(data.get("stage") or "")
        now = self.now()
        if stage == "legal":
            if actor.get("role") != "specialist" or row["status"] != "pending_legal":
                raise PermissionError("La aprobación jurídica exige especialista y estado pendiente jurídico.")
            if str(data.get("confirmation") or "") != self.policy["confirmations"]["legal_retention_approval"]:
                raise ValueError("Confirmación jurídica incorrecta.")
            con.execute("UPDATE m30_pilot_retention_request SET status='pending_qa',legal_approver_id=?,legal_approver_name=?,legal_approved_at=?,updated_at=? WHERE id=?",
                        (str(actor.get("id")), self._actor_name(actor), now, now, request_id))
        elif stage == "qa":
            if actor.get("role") != "admin" or row["status"] != "pending_qa":
                raise PermissionError("La aprobación QA exige administración y estado pendiente QA.")
            if row["legal_approver_id"] == str(actor.get("id")):
                raise ValueError("Las aprobaciones jurídica y QA deben pertenecer a personas distintas.")
            if str(data.get("confirmation") or "") != self.policy["confirmations"]["qa_retention_approval"]:
                raise ValueError("Confirmación QA incorrecta.")
            con.execute("UPDATE m30_pilot_retention_request SET status='approved',qa_approver_id=?,qa_approver_name=?,qa_approved_at=?,updated_at=? WHERE id=?",
                        (str(actor.get("id")), self._actor_name(actor), now, now, request_id))
        else:
            raise ValueError("Etapa de aprobación inválida.")
        con.commit()
        return self.summary(con, actor)

    def execute_retention(self, con, request_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede ejecutar la depuración aprobada.")
        self.pilot_operations.ensure_schema(con)
        self.pilot_center.ensure_schema(con)
        self.participants.ensure_schema(con)
        self.ensure_schema(con)
        request = con.execute("SELECT * FROM m30_pilot_retention_request WHERE id=?", (request_id,)).fetchone()
        if not request or request["status"] != "approved":
            raise ValueError("La solicitud debe estar aprobada jurídica y técnicamente.")
        if str(data.get("confirmation") or "") != self.policy["confirmations"]["execute_retention"]:
            raise ValueError("Confirmación de ejecución incorrecta.")
        due = datetime.fromisoformat(str(request["due_at"]).replace("Z", "+00:00"))
        if due > datetime.now(timezone.utc):
            raise ValueError("La fecha de retención todavía no se ha cumplido.")
        participant_row = con.execute("SELECT * FROM m30_pilot_participant WHERE id=?", (request["participant_id"],)).fetchone()
        if not participant_row:
            raise LookupError("El registro participante ya no existe.")
        participant = dict(participant_row)
        if self._participant_legal_hold(con, participant):
            con.execute("UPDATE m30_pilot_retention_request SET status='blocked_legal_hold',updated_at=? WHERE id=?", (self.now(), request_id))
            con.commit()
            raise ValueError("La ejecución quedó bloqueada por legal hold.")
        event_rows = [dict(row) for row in con.execute("SELECT event_type,detail_json,created_at FROM m30_pilot_participant_event WHERE participant_id=? ORDER BY created_at", (participant["id"],)).fetchall()]
        participant_hash = self._hash(participant["id"])
        event_digest = self._hash(json.dumps(event_rows, ensure_ascii=False, sort_keys=True))
        now = self.now()
        con.execute(
            """INSERT INTO m30_pilot_retention_tombstone
               (id,participant_hash,product_code,terminal_status,consent_hash,event_digest,action_type,cohort_id,closed_at,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), participant_hash, participant["product_code"], participant["status"], participant["consent_hash"],
             event_digest, request["action_type"], participant["cohort_id"], now, now),
        )
        alias = f"anon:{participant_hash[:16]}"
        con.execute("UPDATE m30_pilot_support_ticket SET opened_by_id=?,opened_by_role='anonymized',summary='[contenido depurado por política de retención]',case_plan_id=NULL,case_id=NULL WHERE opened_by_id=?", (alias, participant["user_id"]))
        con.execute("UPDATE m30_pilot_communication SET participant_id=NULL,user_id=NULL,audience_ref=?,body='[contenido depurado por política de retención]',updated_at=? WHERE participant_id=?", (participant_hash, now, participant["id"]))
        enrollment = con.execute("SELECT id FROM m24_pilot_enrollment WHERE user_id=?", (participant["user_id"],)).fetchone()
        if enrollment:
            con.execute("DELETE FROM m24_pilot_event WHERE enrollment_id=?", (enrollment["id"],))
            con.execute("DELETE FROM m24_pilot_feedback WHERE enrollment_id=?", (enrollment["id"],))
            con.execute("DELETE FROM m24_pilot_enrollment WHERE id=?", (enrollment["id"],))
        con.execute("DELETE FROM m30_pilot_participant_event WHERE participant_id=?", (participant["id"],))
        con.execute("DELETE FROM m30_pilot_participant WHERE id=?", (participant["id"],))
        con.execute("UPDATE m30_pilot_retention_request SET status='executed',executed_at=?,updated_at=? WHERE id=?", (now, now, request_id))
        con.commit()
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_retention_request", request_id, "execute", {"action": request["action_type"], "participant_hash": participant_hash})
        con.commit()
        return self.summary(con, actor)

    def prepare_closure(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede preparar el cierre de cohorte.")
        self.ensure_schema(con)
        cohort = self._active_cohort(con)
        if not cohort:
            raise LookupError("No existe una cohorte activa o planificada.")
        decision = str(data.get("decision") or "close")
        reason = str(data.get("reason_code") or "other")
        if decision not in self.policy["closure"]["decisions"] or reason not in self.policy["closure"]["reason_codes"]:
            raise ValueError("Decisión o motivo de cierre inválidos.")
        gate = self._closure_gate(con, cohort)
        if decision == "close" and not gate["ready"]:
            raise ValueError("La cohorte no cumple todas las compuertas de cierre.")
        summary = self._clean_text(data.get("summary") or "", 1200)
        if len(summary) < 20:
            raise ValueError("El cierre exige una síntesis verificable de al menos 20 caracteres.")
        now = self.now()
        closure_id = str(uuid.uuid4())
        snapshot = {"gate": gate, "cohort_id": cohort["id"], "decision": decision, "created_at": now}
        con.execute(
            """INSERT INTO m30_pilot_closure
               (id,cohort_id,decision,reason_code,summary,status,snapshot_json,created_by_id,created_by_name,created_at,updated_at)
               VALUES(?,?,?,?,?,'pending_legal',?,?,?,?,?)""",
            (closure_id, cohort["id"], decision, reason, summary, json.dumps(snapshot, ensure_ascii=False),
             str(actor.get("id")), self._actor_name(actor), now, now),
        )
        con.commit()
        return self.summary(con, actor)

    def approve_closure(self, con, closure_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m30_pilot_closure WHERE id=?", (closure_id,)).fetchone()
        if not row:
            raise LookupError("Cierre no encontrado.")
        stage = str(data.get("stage") or "")
        now = self.now()
        if stage == "legal":
            if actor.get("role") != "specialist" or row["status"] != "pending_legal":
                raise PermissionError("La aprobación jurídica exige especialista y estado pendiente jurídico.")
            if str(data.get("confirmation") or "") != self.policy["confirmations"]["legal_closure_approval"]:
                raise ValueError("Confirmación jurídica incorrecta.")
            con.execute("UPDATE m30_pilot_closure SET status='pending_qa',legal_approver_id=?,legal_approver_name=?,legal_approved_at=?,updated_at=? WHERE id=?",
                        (str(actor.get("id")), self._actor_name(actor), now, now, closure_id))
        elif stage == "qa":
            if actor.get("role") != "admin" or row["status"] != "pending_qa":
                raise PermissionError("La aprobación QA exige administración y estado pendiente QA.")
            if row["legal_approver_id"] == str(actor.get("id")):
                raise ValueError("Las aprobaciones jurídica y QA deben pertenecer a personas distintas.")
            if str(data.get("confirmation") or "") != self.policy["confirmations"]["qa_closure_approval"]:
                raise ValueError("Confirmación QA incorrecta.")
            con.execute("UPDATE m30_pilot_closure SET status='approved',qa_approver_id=?,qa_approver_name=?,qa_approved_at=?,updated_at=? WHERE id=?",
                        (str(actor.get("id")), self._actor_name(actor), now, now, closure_id))
        else:
            raise ValueError("Etapa de aprobación inválida.")
        con.commit()
        return self.summary(con, actor)

    def execute_closure(self, con, closure_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede ejecutar el cierre aprobado.")
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m30_pilot_closure WHERE id=?", (closure_id,)).fetchone()
        if not row or row["status"] != "approved":
            raise ValueError("El cierre debe estar aprobado jurídica y técnicamente.")
        if str(data.get("confirmation") or "") != self.policy["confirmations"]["execute_closure"]:
            raise ValueError("Confirmación de cierre incorrecta.")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds")
        if row["decision"] == "close":
            cohort = self._active_cohort(con)
            gate = self._closure_gate(con, cohort)
            if not gate["ready"]:
                raise ValueError("Las compuertas dejaron de cumplirse; prepare nuevamente el cierre.")
            self.queue_communication(con, {"template_code": "pilot_closure_notice", "channel": "account"}, actor)
            con.execute("UPDATE m25_pilot_cohort SET status='completed',updated_at=? WHERE id=?", (now, row["cohort_id"]))
            due = (now_dt + timedelta(days=int(self.policy["retention"]["participant_days_after_withdrawal_or_cohort_closure"]))).isoformat(timespec="seconds")
            con.execute("UPDATE m30_pilot_participant SET retention_state='scheduled',retention_due_at=?,updated_at=? WHERE cohort_id=? AND status='accepted'", (due, now, row["cohort_id"]))
        con.execute("UPDATE m30_pilot_closure SET status='closed',closed_at=?,updated_at=? WHERE id=?", (now, now, closure_id))
        con.commit()
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_closure", closure_id, "execute", {"decision": row["decision"]})
        con.commit()
        return self.summary(con, actor)

    def export_snapshot(self, con, actor: dict[str, Any]) -> bytes:
        data = self.summary(con, actor)
        for row in data.get("communications", []):
            row.pop("user_id", None)
            row.pop("participant_id", None)
            row.pop("body", None)
        data["export_notice"] = "No contiene correos completos, relatos jurídicos ni cuerpos de comunicación."
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
