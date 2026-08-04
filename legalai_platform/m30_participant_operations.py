from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class M30ParticipantOperationsCenter:
    """Incorporación y seguimiento de participantes del piloto M30.2.

    La identidad permanece en la cuenta de usuario existente. Este módulo no
    recopila documentos de identidad, relatos jurídicos, datos clínicos ni
    valores económicos. La invitación y el consentimiento se vinculan a un
    cupo de la cohorte controlada y conservan evidencia auditable.
    """

    def __init__(self, root: Path, pilot_operations, pilot_center, audit_fn):
        self.root = Path(root).resolve()
        self.pilot_operations = pilot_operations
        self.pilot_center = pilot_center
        self.audit_fn = audit_fn
        self.policy_path = self.root / "config" / "m30_2_participant_operations_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.products = set(self.policy["pilot_products"])
        self.statuses = set(self.policy["participant_statuses"])
        self.support_categories = set(self.policy["support_categories"])
        self.support_issue_codes = set(self.policy["support_issue_codes"])

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
    def _token_hash(token: str) -> str:
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    @staticmethod
    def _mask_email(value: str | None) -> str:
        email = str(value or "")
        if "@" not in email:
            return "Sin correo"
        local, domain = email.split("@", 1)
        visible = local[:1] if local else "*"
        return f"{visible}***@{domain}"

    def _consent_hash(self) -> str:
        canonical = {
            "version": self.policy["consent_version"],
            "notice": self.policy["consent"]["notice"],
            "purposes": self.policy["consent"]["purposes"],
            "rights": self.policy["consent"]["rights"],
            "required_acknowledgements": self.policy["consent"]["required_acknowledgements"],
        }
        raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m30_pilot_participant(
              id TEXT PRIMARY KEY,
              cohort_id TEXT NOT NULL,
              case_plan_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('invited','accepted','declined','withdrawn','expired')),
              invitation_token_hash TEXT NOT NULL,
              invitation_version TEXT NOT NULL,
              invited_by_id TEXT NOT NULL,
              invited_by_name TEXT NOT NULL,
              invited_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              responded_at TEXT,
              accepted_at TEXT,
              withdrawn_at TEXT,
              consent_version TEXT NOT NULL DEFAULT '',
              consent_hash TEXT NOT NULL DEFAULT '',
              consent_snapshot_json TEXT NOT NULL DEFAULT '{}',
              retention_state TEXT NOT NULL DEFAULT 'active' CHECK(retention_state IN ('active','scheduled','legal_hold','anonymized')),
              retention_due_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(cohort_id) REFERENCES m25_pilot_cohort(id),
              FOREIGN KEY(case_plan_id) REFERENCES m25_pilot_case_plan(id),
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_participant_plan
              ON m30_pilot_participant(case_plan_id,status,created_at);
            CREATE INDEX IF NOT EXISTS idx_m30_participant_user
              ON m30_pilot_participant(user_id,status,created_at);
            CREATE TABLE IF NOT EXISTS m30_pilot_participant_event(
              id TEXT PRIMARY KEY,
              participant_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(participant_id) REFERENCES m30_pilot_participant(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m30_participant_event
              ON m30_pilot_participant_event(participant_id,created_at);
            """
        )

    def _require_professional(self, actor: dict[str, Any]) -> None:
        if actor.get("role") not in {"admin", "specialist"}:
            raise PermissionError("La gestión de participantes exige rol profesional.")

    def _event(self, con, participant_id: str, event_type: str, actor: dict[str, Any], detail: dict[str, Any]) -> None:
        con.execute(
            "INSERT INTO m30_pilot_participant_event(id,participant_id,event_type,actor_id,actor_role,detail_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()), participant_id, event_type, str(actor.get("id")), str(actor.get("role")),
                json.dumps(detail, ensure_ascii=False), self.now(),
            ),
        )

    def _expire_invitations(self, con) -> int:
        now = self.now()
        rows = con.execute(
            "SELECT id,case_plan_id FROM m30_pilot_participant WHERE status='invited' AND expires_at<?", (now,)
        ).fetchall()
        for row in rows:
            con.execute(
                "UPDATE m30_pilot_participant SET status='expired',responded_at=?,retention_state='scheduled',retention_due_at=?,updated_at=? WHERE id=?",
                (
                    now,
                    (datetime.now(timezone.utc) + timedelta(days=int(self.policy["retention"]["invitation_contact_days"]))).isoformat(timespec="seconds"),
                    now,
                    row["id"],
                ),
            )
            plan = con.execute("SELECT status FROM m25_pilot_case_plan WHERE id=?", (row["case_plan_id"],)).fetchone()
            if plan and plan["status"] == "recruited":
                con.execute("UPDATE m25_pilot_case_plan SET status='planned',updated_at=? WHERE id=?", (now, row["case_plan_id"]))
        if rows:
            con.commit()
        return len(rows)

    def _active_invitation_for_user(self, con, user_id: str):
        return con.execute(
            """SELECT p.*,c.title cohort_title,cp.archetype,u.name user_name,u.email user_email
               FROM m30_pilot_participant p
               JOIN m25_pilot_cohort c ON c.id=p.cohort_id
               JOIN m25_pilot_case_plan cp ON cp.id=p.case_plan_id
               JOIN users u ON u.id=p.user_id
               WHERE p.user_id=? AND p.status IN ('invited','accepted')
               ORDER BY p.created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()

    def _participant_rows(self, con) -> list[dict[str, Any]]:
        rows = con.execute(
            """SELECT p.*,u.name user_name,u.email user_email,cp.archetype,cp.status plan_status,cp.case_id,
                      c.title cohort_title
               FROM m30_pilot_participant p
               JOIN users u ON u.id=p.user_id
               JOIN m25_pilot_case_plan cp ON cp.id=p.case_plan_id
               JOIN m25_pilot_cohort c ON c.id=p.cohort_id
               ORDER BY p.created_at DESC"""
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["masked_email"] = self._mask_email(item.pop("user_email", ""))
            item.pop("invitation_token_hash", None)
            item.pop("consent_snapshot_json", None)
            result.append(item)
        return result

    def _support_sla_metrics(self, con) -> dict[str, Any]:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m30_pilot_support_ticket'").fetchone():
            return {"total": 0, "closed": 0, "within_sla": 0, "within_sla_rate": 0.0, "open_overdue": 0}
        rows = con.execute(
            "SELECT status,due_at,closed_at FROM m30_pilot_support_ticket WHERE opened_by_role='client'"
        ).fetchall()
        now = datetime.now(timezone.utc)
        closed = within = overdue = 0
        for row in rows:
            try:
                due = datetime.fromisoformat(str(row["due_at"]).replace("Z", "+00:00"))
            except ValueError:
                continue
            if row["status"] == "closed" and row["closed_at"]:
                closed += 1
                try:
                    done = datetime.fromisoformat(str(row["closed_at"]).replace("Z", "+00:00"))
                    within += int(done <= due)
                except ValueError:
                    pass
            elif row["status"] in {"open", "assigned"} and due < now:
                overdue += 1
        return {
            "total": len(rows), "closed": closed, "within_sla": within,
            "within_sla_rate": round(within / closed, 3) if closed else 0.0,
            "open_overdue": overdue,
        }

    def _metrics(self, con, active_cohort: dict[str, Any] | None) -> dict[str, Any]:
        rows = self._participant_rows(con)
        counts = {status: sum(row["status"] == status for row in rows) for status in self.statuses}
        target = int((active_cohort or {}).get("target_cases") or self.pilot_center.policy["target_cases"])
        accepted = counts.get("accepted", 0)
        invited = counts.get("invited", 0)
        responded = accepted + counts.get("declined", 0) + counts.get("withdrawn", 0)
        response_base = responded + invited
        retention_due = sum(
            row.get("retention_state") == "scheduled" and bool(row.get("retention_due_at")) for row in rows
        )
        return {
            "target": target,
            "counts": counts,
            "accepted_coverage": round(accepted / target, 3) if target else 0.0,
            "response_rate": round(responded / response_base, 3) if response_base else 0.0,
            "available_slots": max(0, target - accepted - invited),
            "consent_hash": self._consent_hash(),
            "retention_due_records": retention_due,
            "support_sla": self._support_sla_metrics(con),
        }

    def professional_summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_professional(actor)
        self.pilot_center.readiness.ensure_schema(con)
        self.pilot_center.ensure_schema(con)
        self.ensure_schema(con)
        self._expire_invitations(con)
        readiness = self.pilot_center.readiness.report(con)
        cohort = self.pilot_center._active_cohort(readiness)
        clients = [
            {"id": row["id"], "name": row["name"], "masked_email": self._mask_email(row["email"]), "verified": bool(row["verified"])}
            for row in con.execute("SELECT id,name,email,verified FROM users WHERE role='client' AND active=1 ORDER BY name").fetchall()
        ]
        return {
            "schema": "legalaizit-m30-2-participant-professional-summary-v1",
            "milestone": "M30.2",
            "version": self.policy["version"],
            "policy": self.policy,
            "active_cohort": cohort,
            "participants": self._participant_rows(con),
            "metrics": self._metrics(con, cohort),
            "available_clients": clients,
            "notice": "La identidad se mantiene en la cuenta existente. No se recopilan documentos de identidad, relatos del caso, datos clínicos ni valores económicos.",
        }

    def client_summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "client":
            raise PermissionError("Esta vista corresponde a participantes cliente.")
        self.pilot_center.ensure_schema(con)
        self.ensure_schema(con)
        self._expire_invitations(con)
        row = self._active_invitation_for_user(con, str(actor.get("id")))
        participant = None
        support = []
        if row:
            participant = dict(row)
            participant.pop("invitation_token_hash", None)
            snapshot = participant.pop("consent_snapshot_json", "{}")
            try:
                participant["consent_snapshot"] = json.loads(snapshot or "{}")
            except json.JSONDecodeError:
                participant["consent_snapshot"] = {}
            support = [dict(item) for item in con.execute(
                """SELECT id,category,priority,status,summary,due_at,resolution_code,created_at,updated_at,closed_at
                   FROM m30_pilot_support_ticket WHERE opened_by_id=? AND case_plan_id=? ORDER BY created_at DESC""",
                (str(actor.get("id")), participant["case_plan_id"]),
            ).fetchall()]
        return {
            "schema": "legalaizit-m30-2-participant-client-summary-v1",
            "milestone": "M30.2",
            "version": self.policy["version"],
            "policy": self.policy,
            "participant": participant,
            "support_tickets": support,
            "eligible": bool(participant and participant.get("status") in {"invited", "accepted"}),
            "notice": self.policy["consent"]["notice"],
        }

    def invite(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "admin":
            raise PermissionError("Solo administración puede invitar participantes.")
        self.pilot_center.readiness.ensure_schema(con)
        self.ensure_schema(con)
        self._expire_invitations(con)
        plan_id = str(data.get("case_plan_id") or "")
        user_id = str(data.get("user_id") or "")
        plan = con.execute(
            """SELECT cp.*,c.status cohort_status FROM m25_pilot_case_plan cp
               JOIN m25_pilot_cohort c ON c.id=cp.cohort_id WHERE cp.id=?""",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise LookupError("Cupo de piloto no encontrado.")
        if plan["product_code"] not in self.products or plan["cohort_status"] not in {"planned", "active"}:
            raise ValueError("El cupo no pertenece a una cohorte habilitada para M30.2.")
        if plan["status"] not in {"planned", "recruited"}:
            raise ValueError("Solo pueden invitarse participantes a cupos planificados o reclutados.")
        user = con.execute("SELECT id,name,email,role,active FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or user["role"] != "client" or not bool(user["active"]):
            raise ValueError("Seleccione una cuenta cliente activa.")
        if con.execute(
            "SELECT 1 FROM m30_pilot_participant WHERE case_plan_id=? AND status IN ('invited','accepted')", (plan_id,)
        ).fetchone():
            raise ValueError("Ese cupo ya tiene una invitación o participante activo.")
        if con.execute(
            "SELECT 1 FROM m30_pilot_participant WHERE user_id=? AND status IN ('invited','accepted')", (user_id,)
        ).fetchone():
            raise ValueError("La cuenta ya tiene una invitación o participación activa.")
        token = secrets.token_urlsafe(24)
        participant_id = str(uuid.uuid4())
        now_dt = datetime.now(timezone.utc)
        expires = now_dt + timedelta(days=int(self.policy["invitation_expiry_days"]))
        now = now_dt.isoformat(timespec="seconds")
        con.execute(
            """INSERT INTO m30_pilot_participant
               (id,cohort_id,case_plan_id,user_id,product_code,status,invitation_token_hash,invitation_version,
                invited_by_id,invited_by_name,invited_at,expires_at,created_at,updated_at)
               VALUES(?,?,?,?,?,'invited',?,?,?,?,?,?,?,?)""",
            (
                participant_id, plan["cohort_id"], plan_id, user_id, plan["product_code"], self._token_hash(token),
                self.policy["consent_version"], str(actor.get("id")), self._actor_name(actor), now,
                expires.isoformat(timespec="seconds"), now, now,
            ),
        )
        con.execute("UPDATE m25_pilot_case_plan SET status='recruited',updated_at=? WHERE id=?", (now, plan_id))
        self._event(con, participant_id, "invited", actor, {"product_code": plan["product_code"], "expires_at": expires.isoformat(timespec="seconds")})
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_participant", participant_id, "invite", {"plan_id": plan_id, "user_id": user_id, "product_code": plan["product_code"]})
        con.commit()
        summary = self.professional_summary(con, actor)
        summary["invitation"] = {
            "participant_id": participant_id,
            "token": token,
            "expires_at": expires.isoformat(timespec="seconds"),
            "delivery": "manual_demo_only",
            "warning": "El token se muestra una sola vez. La integración externa de correo permanece pendiente.",
        }
        return summary

    def respond(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "client":
            raise PermissionError("La respuesta a la invitación corresponde al participante cliente.")
        self.pilot_operations.ensure_schema(con)
        self.ensure_schema(con)
        self._expire_invitations(con)
        row = self._active_invitation_for_user(con, str(actor.get("id")))
        if not row or row["status"] != "invited":
            raise LookupError("No existe una invitación vigente para esta cuenta.")
        action = str(data.get("action") or "accept").lower()
        token = str(data.get("token") or "")
        if not secrets.compare_digest(self._token_hash(token), str(row["invitation_token_hash"])):
            raise ValueError("El código de invitación no es válido.")
        now_dt = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
        if expires < now_dt:
            self._expire_invitations(con)
            raise ValueError("La invitación venció. Solicite una nueva invitación al equipo del piloto.")
        now = now_dt.isoformat(timespec="seconds")
        if action == "decline":
            con.execute(
                """UPDATE m30_pilot_participant SET status='declined',responded_at=?,retention_state='scheduled',retention_due_at=?,updated_at=? WHERE id=?""",
                (
                    now,
                    (now_dt + timedelta(days=int(self.policy["retention"]["invitation_contact_days"]))).isoformat(timespec="seconds"),
                    now,
                    row["id"],
                ),
            )
            con.execute("UPDATE m25_pilot_case_plan SET status='planned',updated_at=? WHERE id=?", (now, row["case_plan_id"]))
            self._event(con, row["id"], "declined", actor, {})
            self.audit_fn(con, str(actor.get("id")), "m30_pilot_participant", row["id"], "decline", {})
            con.commit()
            return self.client_summary(con, actor)
        if action != "accept":
            raise ValueError("Respuesta de invitación no permitida.")
        required = self.policy["consent"]["required_acknowledgements"]
        if not all(data.get(key) is True for key in required):
            raise ValueError("Debe aceptar expresamente todas las condiciones del piloto.")
        if str(data.get("confirmation") or "").strip() != self.policy["consent"]["confirmation"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['consent']['confirmation']}")
        consent_snapshot = {
            "version": self.policy["consent_version"],
            "notice": self.policy["consent"]["notice"],
            "purposes": self.policy["consent"]["purposes"],
            "rights": self.policy["consent"]["rights"],
            "acknowledgements": {key: True for key in required},
            "confirmation": self.policy["consent"]["confirmation"],
            "accepted_at": now,
        }
        consent_hash = self._consent_hash()
        con.execute(
            """UPDATE m30_pilot_participant SET status='accepted',responded_at=?,accepted_at=?,consent_version=?,consent_hash=?,
               consent_snapshot_json=?,retention_state='active',retention_due_at=NULL,updated_at=? WHERE id=?""",
            (now, now, self.policy["consent_version"], consent_hash, json.dumps(consent_snapshot, ensure_ascii=False), now, row["id"]),
        )
        con.execute("UPDATE m25_pilot_case_plan SET status='recruited',updated_at=? WHERE id=?", (now, row["case_plan_id"]))
        enrollment_id = str(uuid.uuid4())
        current = con.execute("SELECT id FROM m24_pilot_enrollment WHERE user_id=?", (str(actor.get("id")),)).fetchone()
        if current:
            enrollment_id = current["id"]
        con.execute(
            """INSERT INTO m24_pilot_enrollment
               (id,user_id,status,consent_version,product_codes_json,non_production_ack,privacy_ack,no_representation_ack,
                fictitious_or_minimized_data_ack,confirmation_text,consented_at,withdrawn_at,created_at,updated_at)
               VALUES(?,?,'consented',?,?,1,1,1,1,?,?,NULL,?,?)
               ON CONFLICT(user_id) DO UPDATE SET status='consented',consent_version=excluded.consent_version,
                product_codes_json=excluded.product_codes_json,non_production_ack=1,privacy_ack=1,no_representation_ack=1,
                fictitious_or_minimized_data_ack=1,confirmation_text=excluded.confirmation_text,consented_at=excluded.consented_at,
                withdrawn_at=NULL,updated_at=excluded.updated_at""",
            (
                enrollment_id, str(actor.get("id")), self.policy["consent_version"], json.dumps([row["product_code"]]),
                self.policy["consent"]["confirmation"], now, now, now,
            ),
        )
        self._event(con, row["id"], "accepted", actor, {"consent_version": self.policy["consent_version"], "consent_hash": consent_hash})
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_participant", row["id"], "accept", {"consent_version": self.policy["consent_version"], "consent_hash": consent_hash})
        con.commit()
        return self.client_summary(con, actor)

    def withdraw(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "client":
            raise PermissionError("El retiro corresponde al participante cliente.")
        self.pilot_operations.ensure_schema(con)
        self.ensure_schema(con)
        row = self._active_invitation_for_user(con, str(actor.get("id")))
        if not row or row["status"] != "accepted":
            raise LookupError("No existe una participación activa para retirar.")
        if str(data.get("confirmation") or "").strip() != self.policy["consent"]["withdrawal_confirmation"]:
            raise ValueError(f"Debe escribir exactamente: {self.policy['consent']['withdrawal_confirmation']}")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds")
        due = (now_dt + timedelta(days=int(self.policy["retention"]["operational_days_after_withdrawal_or_closure"]))).isoformat(timespec="seconds")
        con.execute(
            """UPDATE m30_pilot_participant SET status='withdrawn',withdrawn_at=?,responded_at=?,retention_state='scheduled',
               retention_due_at=?,updated_at=? WHERE id=?""",
            (now, now, due, now, row["id"]),
        )
        con.execute("UPDATE m24_pilot_enrollment SET status='withdrawn',withdrawn_at=?,updated_at=? WHERE user_id=?", (now, now, str(actor.get("id"))))
        plan_status = con.execute("SELECT status FROM m25_pilot_case_plan WHERE id=?", (row["case_plan_id"],)).fetchone()
        if plan_status and plan_status["status"] in {"planned", "recruited"}:
            con.execute("UPDATE m25_pilot_case_plan SET status='cancelled',updated_at=? WHERE id=?", (now, row["case_plan_id"]))
        elif plan_status and plan_status["status"] == "in_progress":
            con.execute("UPDATE m25_pilot_case_plan SET status='blocked',updated_at=? WHERE id=?", (now, row["case_plan_id"]))
        self._event(con, row["id"], "withdrawn", actor, {"retention_due_at": due})
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_participant", row["id"], "withdraw", {"retention_due_at": due})
        con.commit()
        return self.client_summary(con, actor)

    def create_support_ticket(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "client":
            raise PermissionError("Este canal de soporte corresponde al participante cliente.")
        self.pilot_center.ensure_schema(con)
        self.ensure_schema(con)
        participant = self._active_invitation_for_user(con, str(actor.get("id")))
        if not participant or participant["status"] != "accepted":
            raise PermissionError("Debe existir una participación aceptada para utilizar soporte del piloto.")
        category = str(data.get("category") or "other")
        issue_code = str(data.get("issue_code") or "other")
        if category not in self.support_categories or issue_code not in self.support_issue_codes:
            raise ValueError("Categoría o código de soporte no permitido.")
        summary = self._clean_text(data.get("summary") or "", int(self.policy["support_summary_max_chars"]))
        if len(summary) < 8:
            raise ValueError("Describa brevemente la fricción, sin incluir hechos ni datos sensibles del caso.")
        priority = "medium" if category in {"access", "privacy", "document_generation"} else "low"
        now_dt = datetime.now(timezone.utc)
        due = (now_dt + timedelta(hours=int(self.pilot_center.support_priorities[priority]["sla_hours"]))).isoformat(timespec="seconds")
        ticket_id = str(uuid.uuid4())
        safe_summary = f"{issue_code}: {summary}"
        con.execute(
            """INSERT INTO m30_pilot_support_ticket
               (id,cohort_id,case_plan_id,case_id,opened_by_id,opened_by_role,category,priority,status,summary,due_at,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,'open',?,?,?,?)""",
            (
                ticket_id, participant["cohort_id"], participant["case_plan_id"], None,
                str(actor.get("id")), "client", category, priority, safe_summary, due,
                now_dt.isoformat(timespec="seconds"), now_dt.isoformat(timespec="seconds"),
            ),
        )
        self._event(con, participant["id"], "support_created", actor, {"ticket_id": ticket_id, "category": category, "issue_code": issue_code})
        self.audit_fn(con, str(actor.get("id")), "m30_pilot_support_ticket", ticket_id, "participant_create", {"category": category, "issue_code": issue_code, "priority": priority})
        con.commit()
        return self.client_summary(con, actor)

    def export_snapshot(self, con, actor: dict[str, Any]) -> bytes:
        payload = self.professional_summary(con, actor)
        payload["export"] = {
            "generated_at": self.now(),
            "privacy": "Correos enmascarados; sin documentos de identidad, relatos del caso, datos clínicos o valores económicos.",
            "retention_policy": "Provisional y sin borrado automático hasta aprobación final.",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
