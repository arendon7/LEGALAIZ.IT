from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import json
import re
import uuid

from docx_builder import build_docx
from document_standard_v33 import STANDARD_VERSION, validate_rendered_sections


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "documento")).strip("._") or "documento"


class CanonicalGenerationCenter:
    """Puerta única para generación primaria desde plantillas canónicas.

    La aprobación dual de una plantilla no basta. Se exige también fuente verificada,
    trazabilidad completa, decisión final de publicación y conformidad documental M33.0.
    """

    def __init__(self, root: Path, factory, traceability, canonical, normative, products: list[dict]):
        self.root = Path(root)
        self.generated = Path(os.environ.get("LEGAL_RUNTIME_DIR", "")).expanduser() / "generated" if os.environ.get("LEGAL_RUNTIME_DIR") else self.root / "runtime" / "generated"
        self.generated.mkdir(parents=True, exist_ok=True)
        self.factory = factory
        self.traceability = traceability
        self.canonical = canonical
        self.normative = normative
        self.products = {x["code"]: x for x in products}

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS canonical_generation_runs(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              mode TEXT NOT NULL,
              gate_json TEXT NOT NULL,
              gate_sha256 TEXT NOT NULL,
              documents_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_canonical_generation_case ON canonical_generation_runs(case_id,created_at DESC);
            """
        )

    def _latest_publication(self, con, code: str):
        row = con.execute(
            """SELECT * FROM canonical_publication_decisions WHERE product_code=?
               ORDER BY id DESC LIMIT 1""",
            (code,),
        ).fetchone()
        return dict(row) if row else None

    def _canonical_state(self, con, code: str):
        row = con.execute("SELECT * FROM canonical_package_state WHERE product_code=?", (code,)).fetchone()
        return dict(row) if row else None

    def _critical_issues(self, con, code: str) -> list[dict]:
        return [dict(x) for x in con.execute(
            """SELECT id,title,detail,status,severity FROM canonical_cotejo_issues
               WHERE product_code=? AND severity='Crítica' AND status NOT IN ('Resuelta','Aceptada como limitación')
               ORDER BY id""",
            (code,),
        ).fetchall()]

    def _normative_holds(self, con, code: str) -> list[dict]:
        try:
            return list(self.normative.product_holds(con).get(code, []))
        except Exception:
            return []

    def readiness(self, con, code: str) -> dict:
        code = str(code or "").upper()
        trace_gate = self.traceability.gate(con, code)
        publication = self._latest_publication(con, code)
        state = self._canonical_state(con, code)
        critical = self._critical_issues(con, code)
        normative_holds = self._normative_holds(con, code)
        published_templates = self.factory.published_for_product(con, code)

        checks = [
            {
                "key": "verified_source",
                "label": "Fuente binaria verificada",
                "passed": trace_gate.get("verified_source_files", 0) > 0,
                "detail": trace_gate.get("verified_source_files", 0),
            },
            {
                "key": "traceability",
                "label": "Bloques obligatorios cotejados",
                "passed": bool(trace_gate.get("passed")),
                "detail": {
                    "approved": trace_gate.get("approved_blocks", 0),
                    "required": trace_gate.get("required_blocks", 0),
                },
            },
            {
                "key": "canonical_package",
                "label": "Paquete canónico aprobado",
                "passed": bool(
                    state
                    and state.get("stage") == "Aprobado para piloto"
                    and state.get("legal_approval_status") == "Aprobado"
                    and state.get("qa_status") == "Aprobado"
                ),
                "detail": state or {},
            },
            {
                "key": "factory_templates",
                "label": "Plantillas con aprobación dual",
                "passed": bool(published_templates),
                "detail": [x.get("template_id") for x in published_templates],
            },
            {
                "key": "publication_decision",
                "label": "Decisión final de publicación",
                "passed": bool(publication and publication.get("decision") == "Autorizar piloto controlado"),
                "detail": publication or {},
            },
            {
                "key": "critical_issues",
                "label": "Sin brechas críticas abiertas",
                "passed": not critical,
                "detail": critical,
            },
            {
                "key": "normative",
                "label": "Sin alertas normativas bloqueantes",
                "passed": not normative_holds,
                "detail": normative_holds,
            },
        ]
        ready = all(bool(x["passed"]) for x in checks)
        reasons = [x["label"] for x in checks if not x["passed"]]
        gate = {
            "product_code": code,
            "product_title": self.products.get(code, {}).get("title", code),
            "ready": ready,
            "passed_checks": sum(bool(x["passed"]) for x in checks),
            "total_checks": len(checks),
            "score": round(sum(bool(x["passed"]) for x in checks) * 100 / max(1, len(checks))),
            "checks": checks,
            "reasons": reasons,
            "traceability_gate": trace_gate,
            "published_templates": len(published_templates),
            "document_standard": STANDARD_VERSION,
            "notice": "La generación primaria solo se habilita cuando todas las puertas recaen sobre fuentes, bloques y revisiones vigentes; la salida final queda además sujeta al preflight documental M33.0.",
        }
        raw = json.dumps(gate, ensure_ascii=False, sort_keys=True, default=str)
        gate["snapshot_sha256"] = sha256(raw.encode("utf-8")).hexdigest()
        return gate

    def summary(self, con) -> dict:
        rows = [self.readiness(con, code) for code in sorted(self.products)]
        return {
            "products": rows,
            "metrics": {
                "products": len(rows),
                "ready": sum(bool(x["ready"]) for x in rows),
                "average_score": round(sum(x["score"] for x in rows) / max(1, len(rows))),
                "blocked": sum(not x["ready"] for x in rows),
            },
            "document_standard": STANDARD_VERSION,
            "notice": "En la base demostrativa ninguna solución debe aparecer lista mientras no se incorporen y aprueben los originales jurídicos.",
        }

    def generate(self, con, case_id: str, actor_id: str) -> dict:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise ValueError("Expediente no encontrado.")
        if case["risk"] == "red":
            raise ValueError("Un expediente bloqueado no puede generar una versión primaria automática.")
        gate = self.readiness(con, case["product_code"])
        if not gate["ready"]:
            raise ValueError("Generación primaria bloqueada: " + "; ".join(gate["reasons"]))
        templates = self.factory.published_for_product(con, case["product_code"])
        if not templates:
            raise ValueError("No existen plantillas publicadas para el producto.")
        answers = json.loads(case["answers"])
        created = []
        now = utc_iso()
        for tpl in templates:
            content = tpl["content"]
            preview = self.factory.render(content, answers)
            semantic_qa = validate_rendered_sections(preview["sections"], product_code=case["product_code"])
            if not semantic_qa["valid"]:
                raise ValueError(
                    "Generación primaria bloqueada por estándar documental "
                    f"{STANDARD_VERSION} en {tpl['template_id']}: {semantic_qa['errors']}"
                )
            filename = safe_name(
                f"{case['product_code']}_{case_id}_{content.get('filename_suffix', content['kind'])}_canonico_r{tpl['revision_id']}.docx"
            )
            target = self.generated / filename
            build_docx(
                target,
                preview["title"],
                preview["subtitle"],
                [
                    ("Expediente", case_id),
                    ("Plantilla", tpl["template_id"]),
                    ("Revisión canónica", str(tpl["revision_id"])),
                    ("Hash de plantilla", tpl["content_hash"]),
                    ("Puerta de publicación", gate["snapshot_sha256"]),
                    ("Estándar documental", STANDARD_VERSION),
                ],
                preview["sections"],
                enforce_legal_standard=True,
                product_code=case["product_code"],
            )
            digest = sha256(target.read_bytes()).hexdigest()
            existing = con.execute(
                "SELECT * FROM documents WHERE case_id=? AND kind=?", (case_id, content["kind"])
            ).fetchone()
            document_id = existing["id"] if existing else "DOC-" + uuid.uuid4().hex[:8].upper()
            version = f"canonical-{tpl['revision_id']}"
            lineage = {
                "generation_engine": "canonical-primary-v2.7",
                "document_standard": STANDARD_VERSION,
                "semantic_qa": semantic_qa,
                "template_id": tpl["template_id"],
                "template_revision_id": tpl["revision_id"],
                "template_hash": tpl["content_hash"],
                "publication_gate_hash": gate["snapshot_sha256"],
                "professional_use_authorized": False,
                "authorization_scope": "Piloto controlado sujeto a revisión del caso y condiciones del producto",
            }
            if existing:
                con.execute(
                    """UPDATE documents SET name=?,mime_type=?,file_path=?,content_sha256=?,updated_at=?,version=?,status=?,
                       template_id=?,template_revision_id=?,template_hash=?,canonical_status=?,generation_engine=?,lineage_json=?
                       WHERE id=?""",
                    (
                        filename,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        str(target),
                        digest,
                        now,
                        version,
                        "Generado desde fuente canónica aprobada para piloto",
                        tpl["template_id"],
                        tpl["revision_id"],
                        tpl["content_hash"],
                        f"Fuente, trazabilidad y estándar documental {STANDARD_VERSION} validados para piloto controlado",
                        "canonical-primary-v2.7",
                        json.dumps(lineage, ensure_ascii=False, sort_keys=True),
                        document_id,
                    ),
                )
            else:
                con.execute(
                    """INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,
                       version,status,content_sha256,template_id,template_revision_id,template_hash,canonical_status,generation_engine,lineage_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        document_id,
                        case_id,
                        case["product_code"],
                        content["kind"],
                        filename,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        str(target),
                        None,
                        now,
                        now,
                        version,
                        "Generado desde fuente canónica aprobada para piloto",
                        digest,
                        tpl["template_id"],
                        tpl["revision_id"],
                        tpl["content_hash"],
                        f"Fuente, trazabilidad y estándar documental {STANDARD_VERSION} validados para piloto controlado",
                        "canonical-primary-v2.7",
                        json.dumps(lineage, ensure_ascii=False, sort_keys=True),
                    ),
                )
            con.execute(
                "INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",
                (
                    document_id,
                    version,
                    now,
                    f"Generación primaria v2.7 con estándar {STANDARD_VERSION} desde {tpl['template_id']} revisión {tpl['revision_id']} y puerta {gate['snapshot_sha256']}.",
                    str(target),
                ),
            )
            created.append(
                {
                    "id": document_id,
                    "kind": content["kind"],
                    "name": filename,
                    "version": version,
                    "sha256": digest,
                    "template_id": tpl["template_id"],
                    "revision_id": tpl["revision_id"],
                    "document_standard": STANDARD_VERSION,
                    "semantic_qa": semantic_qa,
                }
            )
        run_id = "CGR-" + uuid.uuid4().hex[:14].upper()
        con.execute(
            """INSERT INTO canonical_generation_runs(id,case_id,product_code,mode,gate_json,gate_sha256,
               documents_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                case_id,
                case["product_code"],
                "canonical-primary-v2.7",
                json.dumps(gate, ensure_ascii=False, sort_keys=True, default=str),
                gate["snapshot_sha256"],
                json.dumps(created, ensure_ascii=False, sort_keys=True),
                actor_id,
                now,
            ),
        )
        con.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, case_id))
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "canonical_generation", f"Se generaron {len(created)} documentos desde la puerta canónica v2.7 con estándar {STANDARD_VERSION}.", now),
        )
        return {
            "ok": True,
            "run_id": run_id,
            "case_id": case_id,
            "gate_sha256": gate["snapshot_sha256"],
            "document_standard": STANDARD_VERSION,
            "documents": created,
        }
