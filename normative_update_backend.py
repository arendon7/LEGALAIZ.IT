from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO, StringIO
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED
import csv
import json
import re
import uuid


SEVERITIES = {"Baja", "Media", "Alta", "Crítica"}
UPDATE_STATUSES = {
    "Detectada", "Referencia verificada", "En análisis", "Impacto propuesto",
    "Implementación pendiente", "Controlada", "Descartada",
}
IMPACT_ACTIONS = {
    "Sin cambio", "Modificar pregunta", "Modificar regla", "Modificar plantilla",
    "Modificar bloque", "Modificar fuente", "Modificar parámetro",
    "Suspender publicación", "Revalidar producto", "Modificar proceso",
}
COMPONENT_TYPES = {"Producto", "Pregunta", "Regla", "Plantilla", "Bloque", "Fuente", "Parámetro", "Proceso"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _date_after(frequency: str) -> str:
    days = {"Semanal": 7, "Quincenal": 15, "Mensual": 30, "Trimestral": 90}.get(frequency, 30)
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _j(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _hash_obj(value) -> str:
    return sha256(_j(value).encode("utf-8")).hexdigest()


def _valid_sha(value: str | None) -> bool:
    return not value or bool(re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()))


class NormativeUpdateCenter:
    """Manual, auditable normative-change control for the local pilot.

    The center deliberately does not scrape, interpret or apply legal changes automatically.
    It registers official references, maps product impact and enforces legal + QA gates.
    """

    def __init__(self, registry: dict, products: list[dict], interviews: dict, rules: dict,
                 templates: list[dict], sources: dict):
        self.registry = registry or {"sources": [], "profiles": [], "principles": []}
        self.products = {x["code"]: x for x in products}
        self.interviews = interviews
        self.rules = rules
        self.templates = {(x.get("id") or x.get("template_id")): x for x in templates}
        self.sources = sources
        self.registry_sources = {x["id"]: x for x in self.registry.get("sources", [])}

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS normative_source_registry(
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              authority TEXT NOT NULL,
              source_type TEXT NOT NULL,
              url TEXT NOT NULL,
              scope_json TEXT NOT NULL,
              product_codes_json TEXT NOT NULL,
              frequency TEXT NOT NULL,
              notes TEXT,
              active INTEGER NOT NULL DEFAULT 1,
              official INTEGER NOT NULL DEFAULT 1,
              registry_reviewed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS normative_watch_profiles(
              product_code TEXT PRIMARY KEY,
              frequency TEXT NOT NULL,
              owner_specialty TEXT NOT NULL,
              topics_json TEXT NOT NULL,
              source_ids_json TEXT NOT NULL,
              last_checked_at TEXT,
              next_review_at TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'Vigente',
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS normative_monitor_checks(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              product_code TEXT NOT NULL,
              source_id TEXT NOT NULL,
              result TEXT NOT NULL,
              notes TEXT NOT NULL,
              checked_by TEXT NOT NULL,
              checked_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_norm_checks_product ON normative_monitor_checks(product_code,checked_at DESC);
            CREATE TABLE IF NOT EXISTS normative_updates(
              id TEXT PRIMARY KEY,
              source_id TEXT NOT NULL,
              title TEXT NOT NULL,
              authority TEXT NOT NULL,
              document_type TEXT NOT NULL,
              identifier TEXT,
              publication_date TEXT,
              effective_date TEXT,
              source_url TEXT NOT NULL,
              source_sha256 TEXT,
              record_hash TEXT NOT NULL,
              abstract TEXT NOT NULL,
              severity TEXT NOT NULL,
              evidence_status TEXT NOT NULL DEFAULT 'Pendiente',
              status TEXT NOT NULL DEFAULT 'Detectada',
              detected_by TEXT NOT NULL,
              assigned_to TEXT,
              verified_by TEXT,
              verified_at TEXT,
              verification_comment TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_norm_updates_queue ON normative_updates(status,severity,updated_at DESC);
            CREATE TABLE IF NOT EXISTS normative_update_products(
              update_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              relevance TEXT NOT NULL,
              release_hold INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY(update_id,product_code),
              FOREIGN KEY(update_id) REFERENCES normative_updates(id)
            );
            CREATE INDEX IF NOT EXISTS idx_norm_product_hold ON normative_update_products(product_code,release_hold);
            CREATE TABLE IF NOT EXISTS normative_impacts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              update_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              component_type TEXT NOT NULL,
              component_id TEXT NOT NULL,
              action TEXT NOT NULL,
              status TEXT NOT NULL,
              rationale TEXT NOT NULL,
              proposed_change TEXT,
              legal_effect TEXT NOT NULL,
              component_snapshot_hash TEXT NOT NULL,
              proposed_by TEXT NOT NULL,
              legal_decision TEXT NOT NULL,
              legal_by TEXT NOT NULL,
              legal_at TEXT NOT NULL,
              legal_comment TEXT,
              qa_decision TEXT,
              qa_by TEXT,
              qa_at TEXT,
              qa_comment TEXT,
              implementation_evidence TEXT,
              implementation_hash TEXT,
              implemented_by TEXT,
              implemented_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              proposal_version INTEGER NOT NULL DEFAULT 1,
              FOREIGN KEY(update_id) REFERENCES normative_updates(id)
            );
            CREATE INDEX IF NOT EXISTS idx_norm_impacts_update ON normative_impacts(update_id,status,id);
            CREATE INDEX IF NOT EXISTS idx_norm_impacts_product ON normative_impacts(product_code,status,id);
            CREATE TABLE IF NOT EXISTS normative_update_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              update_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              previous_event_hash TEXT,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(update_id) REFERENCES normative_updates(id)
            );
            CREATE INDEX IF NOT EXISTS idx_norm_events_update ON normative_update_events(update_id,id);
            """
        )
        self._seed_registry(con)

    def _seed_registry(self, con) -> None:
        reviewed = self.registry.get("registry_reviewed_at") or _now()[:10]
        for x in self.registry.get("sources", []):
            con.execute(
                """INSERT INTO normative_source_registry(id,name,authority,source_type,url,scope_json,product_codes_json,
                   frequency,notes,active,official,registry_reviewed_at) VALUES(?,?,?,?,?,?,?,?,?,1,1,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,authority=excluded.authority,source_type=excluded.source_type,
                   url=excluded.url,scope_json=excluded.scope_json,product_codes_json=excluded.product_codes_json,
                   frequency=excluded.frequency,notes=excluded.notes,active=1,official=1,registry_reviewed_at=excluded.registry_reviewed_at""",
                (x["id"], x["name"], x["authority"], x["source_type"], x["url"], _j(x.get("scope", [])),
                 _j(x.get("products", [])), x.get("frequency", "Mensual"), x.get("notes", ""), reviewed),
            )
        now = _now()
        for x in self.registry.get("profiles", []):
            con.execute(
                """INSERT INTO normative_watch_profiles(product_code,frequency,owner_specialty,topics_json,source_ids_json,
                   last_checked_at,next_review_at,status,updated_at) VALUES(?,?,?,?,?,NULL,?,'Vigente',?)
                   ON CONFLICT(product_code) DO UPDATE SET frequency=excluded.frequency,owner_specialty=excluded.owner_specialty,
                   topics_json=excluded.topics_json,source_ids_json=excluded.source_ids_json,
                   status='Vigente',updated_at=excluded.updated_at""",
                (x["product_code"], x.get("frequency", "Mensual"), x.get("owner_specialty", "Jurídico"),
                 _j(x.get("topics", [])), _j(x.get("source_ids", [])), _date_after(x.get("frequency", "Mensual")), now),
            )

    def _event(self, con, update_id: str, event_type: str, actor: str, role: str, detail) -> str:
        prev = con.execute(
            "SELECT event_hash FROM normative_update_events WHERE update_id=? ORDER BY id DESC LIMIT 1", (update_id,)
        ).fetchone()
        previous = prev[0] if prev else ""
        created = _now()
        detail_json = _j(detail)
        payload = "|".join([update_id, event_type, actor, role, created, previous, detail_json])
        digest = sha256(payload.encode("utf-8")).hexdigest()
        con.execute(
            """INSERT INTO normative_update_events(update_id,event_type,actor,actor_role,detail_json,
               previous_event_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?)""",
            (update_id, event_type, actor, role, detail_json, previous or None, digest, created),
        )
        return digest

    @staticmethod
    def verify_chain(events: list[dict]) -> bool:
        previous = ""
        for event in events:
            payload = "|".join([
                event["update_id"], event["event_type"], event["actor"], event["actor_role"],
                event["created_at"], previous, event["detail_json"],
            ])
            if sha256(payload.encode("utf-8")).hexdigest() != event["event_hash"]:
                return False
            if (event.get("previous_event_hash") or "") != previous:
                return False
            previous = event["event_hash"]
        return True

    def _source(self, con, source_id: str):
        return con.execute("SELECT * FROM normative_source_registry WHERE id=? AND active=1", (source_id,)).fetchone()

    def _update(self, con, update_id: str):
        return con.execute(
            """SELECT n.*,s.name source_name,u.name assigned_name FROM normative_updates n
               JOIN normative_source_registry s ON s.id=n.source_id
               LEFT JOIN users u ON u.id=n.assigned_to WHERE n.id=?""", (update_id,)
        ).fetchone()

    def _component_snapshot(self, product_code: str, component_type: str, component_id: str):
        if product_code not in self.products:
            raise ValueError("Producto no encontrado.")
        if component_type == "Producto":
            if component_id not in (product_code, "producto"):
                raise ValueError("El identificador de producto no coincide.")
            return self.products[product_code]
        if component_type == "Pregunta":
            for q in self.interviews.get(product_code, {}).get("questions", []):
                if q.get("id") == component_id:
                    return q
            raise ValueError("Pregunta no encontrada en la entrevista vigente.")
        if component_type == "Regla":
            for r in self.rules.get(product_code, []):
                if r.get("id") == component_id:
                    return r
            raise ValueError("Regla no encontrada en la versión vigente.")
        if component_type == "Plantilla":
            t = self.templates.get(component_id)
            if not t or t.get("product_code") != product_code:
                raise ValueError("Plantilla no encontrada para el producto.")
            return t
        if component_type == "Bloque":
            for t in self.templates.values():
                if t.get("product_code") != product_code:
                    continue
                for b in t.get("blocks", []):
                    if b.get("id") == component_id:
                        return {"template_id": (t.get("id") or t.get("template_id")), **b}
            raise ValueError("Bloque no encontrado para el producto.")
        if component_type == "Fuente":
            for s in self.sources.get(product_code, []):
                if s.get("id") == component_id:
                    return s
            raise ValueError("Fuente jurídica no encontrada para el producto.")
        if component_type in {"Parámetro", "Proceso"}:
            if len((component_id or "").strip()) < 3:
                raise ValueError("Registre un identificador estable del parámetro o proceso.")
            return {"product_code": product_code, "type": component_type, "id": component_id}
        raise ValueError("Tipo de componente no permitido.")

    def component_options(self, product_code: str) -> dict:
        return {
            "product": [{"id": product_code, "label": self.products.get(product_code, {}).get("title", product_code)}],
            "questions": [{"id": x.get("id"), "label": x.get("label")} for x in self.interviews.get(product_code, {}).get("questions", [])],
            "rules": [{"id": x.get("id"), "label": x.get("message")} for x in self.rules.get(product_code, [])],
            "templates": [{"id": (x.get("id") or x.get("template_id")), "label": x.get("name") or x.get("title") or x.get("id") or x.get("template_id")} for x in self.templates.values() if x.get("product_code") == product_code],
            "blocks": [{"id": b.get("id"), "label": b.get("heading") or b.get("text", "")[:100], "template_id": (t.get("id") or t.get("template_id"))}
                       for t in self.templates.values() if t.get("product_code") == product_code for b in t.get("blocks", [])],
            "sources": [{"id": x.get("id"), "label": x.get("title")} for x in self.sources.get(product_code, [])],
        }

    def register_update(self, con, source_id: str, title: str, document_type: str, source_url: str,
                        abstract: str, severity: str, product_codes: list[str], actor: str, role: str,
                        identifier: str = "", publication_date: str | None = None,
                        effective_date: str | None = None, source_sha256: str | None = None,
                        relevance: str = "Potencial") -> dict:
        if role != "admin":
            raise PermissionError("Solo administración puede registrar una novedad normativa.")
        source = self._source(con, source_id)
        if not source:
            raise ValueError("Fuente oficial no registrada o inactiva.")
        title = (title or "").strip()
        abstract = (abstract or "").strip()
        document_type = (document_type or "").strip()
        source_url = (source_url or "").strip()
        if len(title) < 12 or len(abstract) < 40 or len(document_type) < 3:
            raise ValueError("Título, tipo documental y resumen sustancial son obligatorios.")
        if severity not in SEVERITIES:
            raise ValueError("Severidad inválida.")
        parsed = urlparse(source_url)
        registry_host = urlparse(source["url"]).hostname or ""
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("La referencia debe usar una URL HTTPS oficial.")
        if parsed.hostname != registry_host and not parsed.hostname.endswith("." + registry_host):
            raise ValueError("La URL no pertenece al dominio de la fuente oficial seleccionada.")
        if not _valid_sha(source_sha256):
            raise ValueError("El SHA-256 de la fuente debe contener 64 caracteres hexadecimales.")
        codes = sorted(set(product_codes or []))
        if not codes or any(code not in self.products for code in codes):
            raise ValueError("Seleccione al menos un producto válido.")
        now = _now()
        uid = "NOR-" + uuid.uuid4().hex[:12].upper()
        canonical_record = {
            "source_id": source_id, "title": title, "document_type": document_type,
            "identifier": (identifier or "").strip(), "publication_date": publication_date,
            "effective_date": effective_date, "source_url": source_url,
            "source_sha256": (source_sha256 or "").lower() or None, "abstract": abstract,
            "severity": severity, "products": codes,
        }
        con.execute(
            """INSERT INTO normative_updates(id,source_id,title,authority,document_type,identifier,publication_date,
               effective_date,source_url,source_sha256,record_hash,abstract,severity,evidence_status,status,detected_by,
               created_at,updated_at,version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'Pendiente','Detectada',?,?,?,1)""",
            (uid, source_id, title, source["authority"], document_type, canonical_record["identifier"], publication_date,
             effective_date, source_url, canonical_record["source_sha256"], _hash_obj(canonical_record), abstract,
             severity, actor, now, now),
        )
        hold = 1 if severity in {"Alta", "Crítica"} else 0
        for code in codes:
            con.execute(
                "INSERT INTO normative_update_products(update_id,product_code,relevance,release_hold) VALUES(?,?,?,?)",
                (uid, code, relevance, hold),
            )
        self._event(con, uid, "update_registered", actor, role, {"record_hash": _hash_obj(canonical_record), "products": codes, "release_hold": bool(hold)})
        return self.detail(con, uid)

    def verify_reference(self, con, update_id: str, actor: str, role: str, comment: str,
                         source_sha256: str | None = None) -> dict:
        if role != "admin":
            raise PermissionError("La verificación de identidad de la referencia requiere administración.")
        row = self._update(con, update_id)
        if not row:
            raise ValueError("Novedad no encontrada.")
        if row["status"] in {"Controlada", "Descartada"}:
            raise ValueError("La novedad ya está cerrada.")
        comment = (comment or "").strip()
        if len(comment) < 25:
            raise ValueError("Registre cómo se verificó la identidad de la referencia oficial.")
        if not _valid_sha(source_sha256):
            raise ValueError("SHA-256 inválido.")
        digest = (source_sha256 or row["source_sha256"] or "").lower() or None
        now = _now()
        con.execute(
            """UPDATE normative_updates SET evidence_status='Referencia oficial verificada',status='Referencia verificada',
               source_sha256=?,verified_by=?,verified_at=?,verification_comment=?,updated_at=?,version=version+1 WHERE id=?""",
            (digest, actor, now, comment, now, update_id),
        )
        self._event(con, update_id, "reference_verified", actor, role, {"source_sha256": digest, "comment": comment})
        return self.detail(con, update_id)

    def claim(self, con, update_id: str, actor: str, role: str, expected_version=None) -> dict:
        if role != "specialist":
            raise PermissionError("Solo un especialista puede tomar el análisis jurídico.")
        row = self._update(con, update_id)
        if not row:
            raise ValueError("Novedad no encontrada.")
        if expected_version is not None and int(expected_version) != int(row["version"]):
            raise ValueError("La novedad cambió. Actualice antes de tomarla.")
        if row["evidence_status"] != "Referencia oficial verificada":
            raise ValueError("La referencia oficial debe verificarse antes del análisis jurídico.")
        if row["assigned_to"] not in (None, actor):
            raise PermissionError("La novedad está asignada a otro especialista.")
        if row["status"] in {"Controlada", "Descartada"}:
            raise ValueError("La novedad ya está cerrada.")
        con.execute(
            "UPDATE normative_updates SET assigned_to=?,status='En análisis',updated_at=?,version=version+1 WHERE id=?",
            (actor, _now(), update_id),
        )
        self._event(con, update_id, "update_claimed", actor, role, {})
        return self.detail(con, update_id)

    def submit_impact(self, con, update_id: str, product_code: str, component_type: str, component_id: str,
                      action: str, rationale: str, proposed_change: str, legal_effect: str,
                      actor: str, role: str, expected_version=None) -> dict:
        if role != "specialist":
            raise PermissionError("La propuesta de impacto requiere especialista jurídico.")
        row = self._update(con, update_id)
        if not row:
            raise ValueError("Novedad no encontrada.")
        if row["assigned_to"] != actor:
            raise PermissionError("Debe ser el especialista asignado a la novedad.")
        if expected_version is not None and int(expected_version) != int(row["version"]):
            raise ValueError("La novedad cambió; actualice antes de proponer impacto.")
        if product_code not in [x[0] for x in con.execute("SELECT product_code FROM normative_update_products WHERE update_id=?", (update_id,)).fetchall()]:
            raise ValueError("El producto no está vinculado a esta novedad.")
        if component_type not in COMPONENT_TYPES or action not in IMPACT_ACTIONS:
            raise ValueError("Tipo de componente o acción no permitida.")
        rationale = (rationale or "").strip()
        proposed_change = (proposed_change or "").strip()
        legal_effect = (legal_effect or "").strip()
        if len(rationale) < 50 or len(legal_effect) < 50:
            raise ValueError("La motivación y el efecto jurídico deben tener al menos 50 caracteres.")
        if action != "Sin cambio" and len(proposed_change) < 30:
            raise ValueError("Describa el cambio propuesto con al menos 30 caracteres.")
        snapshot = self._component_snapshot(product_code, component_type, component_id)
        now = _now()
        cur = con.execute(
            """INSERT INTO normative_impacts(update_id,product_code,component_type,component_id,action,status,rationale,
               proposed_change,legal_effect,component_snapshot_hash,proposed_by,legal_decision,legal_by,legal_at,
               created_at,updated_at,proposal_version) VALUES(?,?,?,?,?,'Listo para QA',?,?,?,?,?,'Aprobado',?,?,?, ?,1)""",
            (update_id, product_code, component_type, component_id, action, rationale, proposed_change or None,
             legal_effect, _hash_obj(snapshot), actor, actor, now, now, now),
        )
        impact_id = cur.lastrowid
        con.execute(
            "UPDATE normative_updates SET status='Impacto propuesto',updated_at=?,version=version+1 WHERE id=?",
            (now, update_id),
        )
        if action in {"Suspender publicación", "Revalidar producto"}:
            con.execute(
                "UPDATE normative_update_products SET release_hold=1 WHERE update_id=? AND product_code=?",
                (update_id, product_code),
            )
        self._event(con, update_id, "impact_submitted", actor, role, {
            "impact_id": impact_id, "product_code": product_code, "component_type": component_type,
            "component_id": component_id, "action": action, "snapshot_hash": _hash_obj(snapshot),
        })
        return self.detail(con, update_id)

    def qa_impact(self, con, impact_id: int, decision: str, actor: str, role: str, comment: str) -> dict:
        if role != "admin":
            raise PermissionError("El QA de impacto requiere administración.")
        row = con.execute("SELECT * FROM normative_impacts WHERE id=?", (impact_id,)).fetchone()
        if not row:
            raise ValueError("Impacto no encontrado.")
        if row["status"] != "Listo para QA":
            raise ValueError("El impacto no está listo para QA.")
        if decision not in {"Aprobado", "Rechazado"}:
            raise ValueError("Decisión de QA inválida.")
        if str(row['legal_by']) == str(actor):
            raise ValueError("La aprobación jurídica y el QA deben corresponder a personas distintas.")
        comment = (comment or "").strip()
        if len(comment) < 25:
            raise ValueError("Registre el control técnico aplicado.")
        now = _now()
        if decision == "Rechazado":
            status = "Requiere ajuste"
        elif row["action"] == "Sin cambio":
            status = "Controlado"
        else:
            status = "Cambio aprobado"
        con.execute(
            """UPDATE normative_impacts SET status=?,qa_decision=?,qa_by=?,qa_at=?,qa_comment=?,updated_at=? WHERE id=?""",
            (status, decision, actor, now, comment, now, impact_id),
        )
        update_status = "Implementación pendiente" if status == "Cambio aprobado" else "Impacto propuesto"
        con.execute(
            "UPDATE normative_updates SET status=?,updated_at=?,version=version+1 WHERE id=?",
            (update_status, now, row["update_id"]),
        )
        self._event(con, row["update_id"], "impact_qa_decision", actor, role, {
            "impact_id": impact_id, "decision": decision, "result_status": status, "comment": comment,
        })
        return self.detail(con, row["update_id"])

    def mark_implemented(self, con, impact_id: int, evidence: str, actor: str, role: str) -> dict:
        if role != "admin":
            raise PermissionError("Solo administración puede registrar implementación técnica.")
        row = con.execute("SELECT * FROM normative_impacts WHERE id=?", (impact_id,)).fetchone()
        if not row:
            raise ValueError("Impacto no encontrado.")
        if row["status"] != "Cambio aprobado":
            raise ValueError("El impacto no tiene un cambio aprobado pendiente de implementación.")
        evidence = (evidence or "").strip()
        if len(evidence) < 35:
            raise ValueError("Registre evidencia verificable de implementación.")
        now = _now()
        digest = sha256(evidence.encode("utf-8")).hexdigest()
        con.execute(
            """UPDATE normative_impacts SET status='Implementado',implementation_evidence=?,implementation_hash=?,
               implemented_by=?,implemented_at=?,updated_at=? WHERE id=?""",
            (evidence, digest, actor, now, now, impact_id),
        )
        self._event(con, row["update_id"], "impact_implemented", actor, role, {"impact_id": impact_id, "evidence_hash": digest})
        return self.detail(con, row["update_id"])

    def finalize(self, con, update_id: str, actor: str, role: str, comment: str) -> dict:
        if role != "admin":
            raise PermissionError("El cierre de la novedad requiere administración.")
        row = self._update(con, update_id)
        if not row:
            raise ValueError("Novedad no encontrada.")
        impacts = con.execute("SELECT status FROM normative_impacts WHERE update_id=?", (update_id,)).fetchall()
        if not impacts:
            raise ValueError("Debe existir al menos un análisis de impacto.")
        pending = [x[0] for x in impacts if x[0] not in {"Controlado", "Implementado"}]
        if pending:
            raise ValueError("Todos los impactos deben estar controlados o implementados antes del cierre.")
        comment = (comment or "").strip()
        if len(comment) < 30:
            raise ValueError("Registre una conclusión de cierre sustancial.")
        now = _now()
        con.execute(
            "UPDATE normative_updates SET status='Controlada',updated_at=?,version=version+1 WHERE id=?", (now, update_id)
        )
        con.execute("UPDATE normative_update_products SET release_hold=0 WHERE update_id=?", (update_id,))
        self._event(con, update_id, "update_controlled", actor, role, {"comment": comment, "impacts": len(impacts)})
        return self.detail(con, update_id)

    def discard(self, con, update_id: str, actor: str, role: str, reason: str) -> dict:
        if role != "admin":
            raise PermissionError("Solo administración puede descartar una novedad.")
        reason = (reason or "").strip()
        if len(reason) < 30:
            raise ValueError("Registre una razón de descarte sustancial.")
        row = self._update(con, update_id)
        if not row:
            raise ValueError("Novedad no encontrada.")
        con.execute("UPDATE normative_updates SET status='Descartada',updated_at=?,version=version+1 WHERE id=?", (_now(), update_id))
        con.execute("UPDATE normative_update_products SET release_hold=0 WHERE update_id=?", (update_id,))
        self._event(con, update_id, "update_discarded", actor, role, {"reason": reason})
        return self.detail(con, update_id)

    def record_monitor_check(self, con, product_code: str, source_id: str, result: str, notes: str,
                             actor: str, role: str) -> dict:
        if role not in {"specialist", "admin"}:
            raise PermissionError("El control de vigilancia requiere equipo jurídico o administración.")
        if product_code not in self.products or not self._source(con, source_id):
            raise ValueError("Producto o fuente inválida.")
        result = (result or "").strip()
        notes = (notes or "").strip()
        if result not in {"Sin novedades", "Novedad registrada", "Revisión pendiente"}:
            raise ValueError("Resultado de vigilancia inválido.")
        if len(notes) < 20:
            raise ValueError("Registre alcance y criterio de la revisión.")
        now = _now()
        con.execute(
            "INSERT INTO normative_monitor_checks(product_code,source_id,result,notes,checked_by,checked_at) VALUES(?,?,?,?,?,?)",
            (product_code, source_id, result, notes, actor, now),
        )
        profile = con.execute("SELECT frequency FROM normative_watch_profiles WHERE product_code=?", (product_code,)).fetchone()
        con.execute(
            "UPDATE normative_watch_profiles SET last_checked_at=?,next_review_at=?,updated_at=? WHERE product_code=?",
            (now, _date_after(profile["frequency"] if profile else "Mensual"), now, product_code),
        )
        return {"ok": True, "product_code": product_code, "source_id": source_id, "result": result, "checked_at": now}

    def product_holds(self, con) -> dict[str, list[dict]]:
        rows = con.execute(
            """SELECT p.product_code,p.update_id,p.relevance,n.title,n.severity,n.status
               FROM normative_update_products p JOIN normative_updates n ON n.id=p.update_id
               WHERE p.release_hold=1 AND n.status NOT IN ('Controlada','Descartada')
               ORDER BY CASE n.severity WHEN 'Crítica' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Media' THEN 3 ELSE 4 END,n.updated_at DESC"""
        ).fetchall()
        out: dict[str, list[dict]] = {}
        for row in rows:
            out.setdefault(row["product_code"], []).append(dict(row))
        return out

    def summary(self, con, actor: str | None = None, role: str | None = None) -> dict:
        sources = [dict(x) for x in con.execute("SELECT * FROM normative_source_registry WHERE active=1 ORDER BY authority,name").fetchall()]
        profiles = [dict(x) for x in con.execute("SELECT * FROM normative_watch_profiles ORDER BY product_code").fetchall()]
        for p in profiles:
            p["topics"] = _loads(p.pop("topics_json"), [])
            p["source_ids"] = _loads(p.pop("source_ids_json"), [])
            p["title"] = self.products.get(p["product_code"], {}).get("title", p["product_code"])
            p["checks"] = con.execute("SELECT COUNT(*) FROM normative_monitor_checks WHERE product_code=?", (p["product_code"],)).fetchone()[0]
        rows = [dict(x) for x in con.execute(
            """SELECT n.*,s.name source_name,u.name assigned_name FROM normative_updates n
               JOIN normative_source_registry s ON s.id=n.source_id LEFT JOIN users u ON u.id=n.assigned_to
               ORDER BY CASE n.status WHEN 'Implementación pendiente' THEN 1 WHEN 'Impacto propuesto' THEN 2
               WHEN 'En análisis' THEN 3 WHEN 'Referencia verificada' THEN 4 WHEN 'Detectada' THEN 5 ELSE 6 END,
               CASE n.severity WHEN 'Crítica' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Media' THEN 3 ELSE 4 END,n.updated_at DESC"""
        ).fetchall()]
        updates = []
        broken = 0
        for row in rows:
            products = [dict(x) for x in con.execute("SELECT * FROM normative_update_products WHERE update_id=? ORDER BY product_code", (row["id"],)).fetchall()]
            impacts = [dict(x) for x in con.execute("SELECT id,status,action,product_code FROM normative_impacts WHERE update_id=? ORDER BY id", (row["id"],)).fetchall()]
            events = [dict(x) for x in con.execute("SELECT * FROM normative_update_events WHERE update_id=? ORDER BY id", (row["id"],)).fetchall()]
            chain_valid = self.verify_chain(events) if events else True
            broken += 0 if chain_valid else 1
            updates.append({**row, "products": products, "impacts": impacts, "chain_valid": chain_valid})
        holds = self.product_holds(con)
        return {
            "metrics": {
                "official_sources": len(sources), "watch_profiles": len(profiles), "updates": len(updates),
                "open_updates": sum(x["status"] not in {"Controlada", "Descartada"} for x in updates),
                "release_holds": sum(len(x) for x in holds.values()),
                "pending_qa": con.execute("SELECT COUNT(*) FROM normative_impacts WHERE status='Listo para QA'").fetchone()[0],
                "pending_implementation": con.execute("SELECT COUNT(*) FROM normative_impacts WHERE status='Cambio aprobado'").fetchone()[0],
                "broken_chains": broken,
            },
            "sources": sources,
            "profiles": profiles,
            "updates": updates,
            "holds": holds,
            "products": [{"code": x, "title": self.products[x].get("title", x)} for x in sorted(self.products)],
            "specialists": [dict(x) for x in con.execute("SELECT id,name,email,specialty FROM users WHERE role='specialist' AND active=1 ORDER BY name").fetchall()],
            "principles": self.registry.get("principles", []),
            "notice": "El módulo no consulta ni interpreta Internet automáticamente. Cada novedad debe verificarse contra la fuente oficial, analizarse jurídicamente y pasar QA antes de modificar el producto.",
        }

    def detail(self, con, update_id: str) -> dict | None:
        row = self._update(con, update_id)
        if not row:
            return None
        products = [dict(x) for x in con.execute("SELECT * FROM normative_update_products WHERE update_id=? ORDER BY product_code", (update_id,)).fetchall()]
        impacts = [dict(x) for x in con.execute(
            """SELECT i.*,u.name proposed_name,l.name legal_name,q.name qa_name,m.name implemented_name
               FROM normative_impacts i LEFT JOIN users u ON u.id=i.proposed_by LEFT JOIN users l ON l.id=i.legal_by
               LEFT JOIN users q ON q.id=i.qa_by LEFT JOIN users m ON m.id=i.implemented_by
               WHERE i.update_id=? ORDER BY i.id""", (update_id,)
        ).fetchall()]
        events = [dict(x) for x in con.execute("SELECT * FROM normative_update_events WHERE update_id=? ORDER BY id DESC", (update_id,)).fetchall()]
        source = dict(self._source(con, row["source_id"]))
        options = {x["product_code"]: self.component_options(x["product_code"]) for x in products}
        return {
            "update": dict(row), "source": source, "products": products, "impacts": impacts,
            "events": events, "chain_valid": self.verify_chain(list(reversed(events))) if events else True,
            "component_options": options,
        }

    def export_bytes(self, con, update_id: str | None = None) -> bytes:
        memory = BytesIO()
        with ZipFile(memory, "w", ZIP_DEFLATED) as z:
            if update_id:
                details = [self.detail(con, update_id)]
                if not details[0]:
                    raise ValueError("Novedad no encontrada.")
            else:
                ids = [x[0] for x in con.execute("SELECT id FROM normative_updates ORDER BY created_at").fetchall()]
                details = [self.detail(con, x) for x in ids]
            z.writestr("00_MANIFIESTO.json", json.dumps({
                "schema": "legalaizit.normative-control.v1", "exported_at": _now(),
                "registry_reviewed_at": self.registry.get("registry_reviewed_at"),
                "updates": len(details), "principles": self.registry.get("principles", []),
            }, ensure_ascii=False, indent=2, default=str))
            z.writestr("01_REGISTRO_FUENTES_OFICIALES.json", json.dumps(self.registry.get("sources", []), ensure_ascii=False, indent=2))
            z.writestr("02_PERFILES_VIGILANCIA.json", json.dumps(self.registry.get("profiles", []), ensure_ascii=False, indent=2))
            z.writestr("03_NOVEDADES_E_IMPACTOS.json", json.dumps(details, ensure_ascii=False, indent=2, default=str))
            sio = StringIO(); writer = csv.writer(sio)
            writer.writerow(["novedad", "severidad", "estado", "producto", "hold_release", "impacto", "acción", "estado_impacto", "hash_componente"])
            for detail in details:
                update = detail["update"]
                impacts_by_product = {}
                for i in detail["impacts"]:
                    impacts_by_product.setdefault(i["product_code"], []).append(i)
                for p in detail["products"]:
                    items = impacts_by_product.get(p["product_code"], []) or [None]
                    for i in items:
                        writer.writerow([
                            update["id"], update["severity"], update["status"], p["product_code"], p["release_hold"],
                            i["id"] if i else "", i["action"] if i else "", i["status"] if i else "",
                            i["component_snapshot_hash"] if i else "",
                        ])
            z.writestr("04_MATRIZ_IMPACTO.csv", "\ufeff" + sio.getvalue())
            z.writestr("05_INSTRUCCIONES.md", """# Control de actualización normativa\n\n- Este paquete no certifica vigencia ni equivalencia jurídica.\n- La detección o registro de una novedad no altera automáticamente el producto.\n- Las fuentes deben verificarse en sus portales oficiales y en el texto íntegro aplicable.\n- Todo impacto requiere motivación jurídica, snapshot del componente, QA e implementación trazable.\n- Las novedades altas o críticas pueden bloquear el release hasta su cierre controlado.\n""")
        return memory.getvalue()
