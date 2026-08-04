from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import re
import sqlite3
import uuid


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_RE = re.compile(r"^[0-9+()\-\s]{7,24}$")


class CommercialExperienceCenter:
    """Captura comercial y medición agregada sin hechos jurídicos ni identificadores analíticos."""

    PURPOSES = {"demo", "empresa", "alianza"}
    AUDIENCES = {"persona", "empresa", "aliado"}
    ROLES = {"decision", "legal", "operaciones", "tecnologia", "otro"}
    EVENTS = {
        "route_view", "cta_click", "solution_finder_started", "solution_finder_completed",
        "lead_form_started", "lead_submitted", "login_started", "wizard_started",
        "search_used", "document_viewed", "performance_sample",
    }
    SURFACES = {
        "home", "solutions", "product", "people", "business", "trust", "about",
        "finder", "demo", "login", "dashboard", "wizard", "cases", "documents",
        "help", "accessibility", "admin_experience", "other",
    }
    DEVICES = {"mobile", "tablet", "desktop", "unknown"}
    METRIC_BUCKETS = {
        "none", "fast", "needs_improvement", "slow", "small", "medium", "large",
    }

    def ensure_schema(self, con: sqlite3.Connection) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m29_commercial_leads(
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                organization TEXT,
                role TEXT NOT NULL,
                audience TEXT NOT NULL,
                purpose TEXT NOT NULL,
                consent INTEGER NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            );
            CREATE INDEX IF NOT EXISTS idx_m29_commercial_leads_created
                ON m29_commercial_leads(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_m29_commercial_leads_email
                ON m29_commercial_leads(email, created_at DESC);

            CREATE TABLE IF NOT EXISTS m29_experience_metrics(
                day TEXT NOT NULL,
                event TEXT NOT NULL,
                surface TEXT NOT NULL,
                device TEXT NOT NULL,
                metric_bucket TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(day, event, surface, device, metric_bucket)
            );
            """
        )

    @staticmethod
    def _clean(value, *, maximum: int) -> str:
        return " ".join(str(value or "").strip().split())[:maximum]

    def capture_lead(self, con: sqlite3.Connection, payload: dict) -> dict:
        self.ensure_schema(con)
        if not isinstance(payload, dict):
            raise ValueError("La solicitud comercial debe enviarse como un objeto JSON.")
        if self._clean(payload.get("website"), maximum=120):
            raise ValueError("No fue posible validar la solicitud.")

        name = self._clean(payload.get("name"), maximum=120)
        email = self._clean(payload.get("email"), maximum=180).lower()
        phone = self._clean(payload.get("phone"), maximum=24)
        organization = self._clean(payload.get("organization"), maximum=140)
        role = self._clean(payload.get("role"), maximum=24).lower()
        audience = self._clean(payload.get("audience"), maximum=24).lower()
        purpose = self._clean(payload.get("purpose"), maximum=24).lower()
        consent = bool(payload.get("consent"))

        if len(name) < 3:
            raise ValueError("Escribe tu nombre completo.")
        if not _EMAIL_RE.fullmatch(email):
            raise ValueError("Escribe un correo electrónico válido.")
        if phone and not _PHONE_RE.fullmatch(phone):
            raise ValueError("Revisa el número de teléfono.")
        if organization and len(organization) < 2:
            raise ValueError("Revisa el nombre de la organización.")
        if role not in self.ROLES:
            raise ValueError("Selecciona tu rol.")
        if audience not in self.AUDIENCES:
            raise ValueError("Selecciona el tipo de organización o usuario.")
        if purpose not in self.PURPOSES:
            raise ValueError("Selecciona el motivo de contacto.")
        if not consent:
            raise ValueError("Debes autorizar el contacto y tratamiento de estos datos.")

        now = datetime.now(timezone.utc)
        duplicate_after = (now - timedelta(minutes=15)).isoformat(timespec="seconds")
        duplicate = con.execute(
            "SELECT id FROM m29_commercial_leads WHERE email=? AND purpose=? AND created_at>=? ORDER BY created_at DESC LIMIT 1",
            (email, purpose, duplicate_after),
        ).fetchone()
        if duplicate:
            return {
                "ok": True,
                "request_id": duplicate[0],
                "duplicate": True,
                "message": "Ya recibimos una solicitud reciente con este correo.",
            }

        request_id = "L29-" + uuid.uuid4().hex[:12].upper()
        created_at = now.isoformat(timespec="seconds")
        con.execute(
            """INSERT INTO m29_commercial_leads(
                id,created_at,name,email,phone,organization,role,audience,purpose,consent,source,status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request_id, created_at, name, email, phone or None, organization or None,
             role, audience, purpose, 1, "public_site_m29_5", "new"),
        )
        con.commit()
        return {
            "ok": True,
            "request_id": request_id,
            "duplicate": False,
            "message": "Solicitud recibida. El equipo podrá continuar el contacto por los datos autorizados.",
        }

    def capture_metric(self, con: sqlite3.Connection, payload: dict) -> dict:
        self.ensure_schema(con)
        if not isinstance(payload, dict) or payload.get("consent") is not True:
            return {"ok": False, "recorded": False}
        event = self._clean(payload.get("event"), maximum=48).lower()
        surface = self._clean(payload.get("surface"), maximum=48).lower()
        device = self._clean(payload.get("device"), maximum=16).lower()
        metric_bucket = self._clean(payload.get("metric_bucket"), maximum=32).lower() or "none"
        if event not in self.EVENTS or surface not in self.SURFACES or device not in self.DEVICES:
            raise ValueError("Evento de experiencia no permitido.")
        if metric_bucket not in self.METRIC_BUCKETS:
            raise ValueError("Categoría de rendimiento no permitida.")
        day = datetime.now(timezone.utc).date().isoformat()
        con.execute(
            """INSERT INTO m29_experience_metrics(day,event,surface,device,metric_bucket,count)
               VALUES(?,?,?,?,?,1)
               ON CONFLICT(day,event,surface,device,metric_bucket)
               DO UPDATE SET count=count+1""",
            (day, event, surface, device, metric_bucket),
        )
        con.commit()
        return {"ok": True, "recorded": True}

    def admin_summary(self, con: sqlite3.Connection, *, days: int = 30) -> dict:
        self.ensure_schema(con)
        days = max(1, min(int(days or 30), 90))
        since = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
        metric_rows = con.execute(
            "SELECT day,event,surface,device,metric_bucket,count FROM m29_experience_metrics WHERE day>=? ORDER BY day",
            (since,),
        ).fetchall()
        lead_rows = con.execute(
            """SELECT id,created_at,name,email,phone,organization,role,audience,purpose,status
               FROM m29_commercial_leads ORDER BY created_at DESC LIMIT 100"""
        ).fetchall()
        by_event = Counter()
        by_surface = Counter()
        by_device = Counter()
        performance = Counter()
        daily = Counter()
        for day, event, surface, device, bucket, count in metric_rows:
            by_event[event] += count
            by_surface[surface] += count
            by_device[device] += count
            daily[day] += count
            if event == "performance_sample":
                performance[bucket] += count
        leads = [
            {
                "id": row[0], "created_at": row[1], "name": row[2], "email": row[3],
                "phone": row[4], "organization": row[5], "role": row[6],
                "audience": row[7], "purpose": row[8], "status": row[9],
            }
            for row in lead_rows
        ]
        return {
            "window_days": days,
            "privacy_model": "aggregate_opt_in_no_case_ids_no_search_text",
            "events_total": sum(by_event.values()),
            "leads_total": len(leads),
            "by_event": dict(by_event.most_common()),
            "by_surface": dict(by_surface.most_common()),
            "by_device": dict(by_device.most_common()),
            "performance": dict(performance.most_common()),
            "daily": [{"day": day, "count": daily[day]} for day in sorted(daily)],
            "leads": leads,
        }
