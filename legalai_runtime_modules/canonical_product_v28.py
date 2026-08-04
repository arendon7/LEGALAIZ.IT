from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
import uuid

from docx_builder import build_docx


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "documento")).strip("._") or "documento"



def _runtime_root(project_root: Path) -> Path:
    raw = os.environ.get("LEGAL_RUNTIME_DIR", "").strip()
    path = Path(raw).expanduser() if raw else Path(project_root) / "runtime"
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()

class FirstCanonicalProductV28:
    """Primer producto candidato físicamente estructurado para cotejo.

    Esta capa NO suplanta Ingesta Canónica. El archivo candidato permite desarrollar,
    generar y probar el recorrido completo mientras el binario original permanece
    pendiente. Toda salida queda marcada como candidata, no canónica y no publicable.
    """

    CODE = "CO-EM-003"

    def __init__(self, root: Path, factory, templates: list[dict], interviews: dict, rules: dict):
        self.root = Path(root)
        self.factory = factory
        self.templates = [x for x in templates if x.get("product_code") == self.CODE]
        self.interview = interviews.get(self.CODE, {})
        self.rules = rules.get(self.CODE, [])
        self.candidate_dir = self.root / "canonical_sources" / "candidates" / self.CODE
        self.generated = _runtime_root(self.root) / "generated"
        self.generated.mkdir(parents=True, exist_ok=True)
        self.map_path = self.root / "data" / "co_em_003_candidate_map.json"

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS canonical_candidate_sources(
              id TEXT PRIMARY KEY,
              product_code TEXT NOT NULL,
              candidate_version TEXT NOT NULL,
              source_name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              original_source_name TEXT NOT NULL,
              original_binary_embedded INTEGER NOT NULL DEFAULT 0,
              original_identity_verified INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_source_product_version
              ON canonical_candidate_sources(product_code,candidate_version,mime_type);
            CREATE TABLE IF NOT EXISTS candidate_generation_runs_v28(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              source_snapshot_json TEXT NOT NULL,
              source_snapshot_sha256 TEXT NOT NULL,
              documents_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_candidate_v28_case ON candidate_generation_runs_v28(case_id,created_at DESC);
            """
        )

    def init_baseline(self, con) -> None:
        manifest_path = self.candidate_dir / "source_manifest.json"
        if not manifest_path.exists():
            return
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        now = utc_iso()
        files = [
            (self.candidate_dir / manifest["candidate_docx"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            (self.candidate_dir / "LegalAIZit_CO-EM-003_Candidato_Estructurado_v2.8.pdf", "application/pdf"),
        ]
        for path, mime in files:
            if not path.exists():
                continue
            digest = sha256(path.read_bytes()).hexdigest()
            ident = "CCS-" + sha256(f"{self.CODE}|2.8|{mime}".encode()).hexdigest()[:14].upper()
            con.execute(
                """INSERT INTO canonical_candidate_sources(
                   id,product_code,candidate_version,source_name,file_path,mime_type,sha256,
                   original_source_name,original_binary_embedded,original_identity_verified,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(product_code,candidate_version,mime_type) DO UPDATE SET
                     source_name=excluded.source_name,file_path=excluded.file_path,sha256=excluded.sha256,
                     status=excluded.status,updated_at=excluded.updated_at""",
                (
                    ident, self.CODE, "2.8", path.name, str(path), mime, digest,
                    manifest.get("original_source_name", "LegalAIZit_Paquete_01_Prestacion_de_Servicios_v1.docx"),
                    0, 0, "Candidato estructurado - pendiente cotejo contra original", now, now,
                ),
            )

    def _source_rows(self, con) -> list[dict]:
        rows = con.execute(
            "SELECT * FROM canonical_candidate_sources WHERE product_code=? ORDER BY mime_type", (self.CODE,)
        ).fetchall()
        return [dict(x) for x in rows]

    def _map(self) -> dict:
        if not self.map_path.exists():
            return {"fragments": [], "limitations": ["Mapa candidato no disponible."]}
        return json.loads(self.map_path.read_text(encoding="utf-8"))

    def summary(self, con) -> dict:
        source_rows = self._source_rows(con)
        cmap = self._map()
        template_rows = []
        for tpl in self.templates:
            state = con.execute(
                """SELECT s.current_revision_id,s.workflow_status,s.publication_revision_id,v.content_hash
                   FROM canonical_template_state s
                   JOIN canonical_template_versions v ON v.id=s.current_revision_id
                   WHERE s.template_id=?""",
                (tpl["template_id"],),
            ).fetchone()
            template_rows.append(
                {
                    "template_id": tpl["template_id"],
                    "kind": tpl["kind"],
                    "title": tpl["title"],
                    "blocks": len(tpl.get("blocks", [])),
                    "current_revision_id": state["current_revision_id"] if state else None,
                    "workflow_status": state["workflow_status"] if state else "Sin inicializar",
                    "publication_revision_id": state["publication_revision_id"] if state else None,
                    "content_hash": state["content_hash"] if state else None,
                }
            )
        return {
            "product_code": self.CODE,
            "title": "Contrato de prestación de servicios independientes",
            "candidate_version": "2.8",
            "status": "Candidato estructurado físicamente incorporado",
            "professional_use_authorized": False,
            "publication_authorized": False,
            "original_source": {
                "name": "LegalAIZit_Paquete_01_Prestacion_de_Servicios_v1.docx",
                "binary_embedded": False,
                "identity_verified": False,
                "blocking_reason": "El archivo de File Library es una referencia y sus bytes originales no están montados en el entorno de construcción.",
            },
            "candidate_sources": [
                {**x, "file_path": None, "download_url": "/api/v28/co-em-003/candidate-package"}
                for x in source_rows
            ],
            "metrics": {
                "templates": len(template_rows),
                "blocks": sum(x["blocks"] for x in template_rows),
                "questions": len(self.interview.get("questions", [])),
                "rules": len(self.rules),
                "mapped_fragments": len(cmap.get("fragments", [])),
                "published_templates": sum(bool(x["publication_revision_id"]) for x in template_rows),
            },
            "templates": template_rows,
            "fragments": cmap.get("fragments", []),
            "limitations": cmap.get("limitations", []),
            "next_actions": [
                "Incorporar el DOCX original por Ingesta Canónica.",
                "Verificar identidad y SHA-256 del original.",
                "Cotejar cada bloque y anexo contra el fragmento fuente exacto.",
                "Obtener aprobación jurídica y QA de la misma revisión.",
                "Superar la puerta de publicación antes de uso profesional.",
            ],
        }

    def package_bytes(self, con) -> bytes:
        summary = self.summary(con)
        from io import BytesIO
        out = BytesIO()
        with ZipFile(out, "w", ZIP_DEFLATED) as z:
            for name in [
                "LegalAIZit_CO-EM-003_Candidato_Estructurado_v2.8.docx",
                "LegalAIZit_CO-EM-003_Candidato_Estructurado_v2.8.pdf",
                "source_manifest.json",
                "co_em_003_candidate_map.json",
                "LEEME.txt",
            ]:
                path = self.candidate_dir / name
                if path.exists():
                    z.write(path, arcname=name)
            z.writestr("ESTADO_V28.json", json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return out.getvalue()

    def _template_revision(self, con, template_id: str):
        row = con.execute(
            """SELECT s.current_revision_id,s.workflow_status,v.content_hash
               FROM canonical_template_state s
               JOIN canonical_template_versions v ON v.id=s.current_revision_id
               WHERE s.template_id=?""",
            (template_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Plantilla {template_id} no inicializada.")
        content = self.factory.revision_content(con, template_id, row["current_revision_id"])
        if not content:
            raise ValueError(f"No fue posible leer la revisión de {template_id}.")
        return dict(row), content

    def generate(self, con, case_id: str, actor_id: str) -> dict:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise ValueError("Expediente no encontrado.")
        if case["product_code"] != self.CODE:
            raise ValueError("La generación candidata v2.8 solo está habilitada para CO-EM-003.")
        if case["risk"] == "red":
            raise ValueError("El expediente está bloqueado por riesgo alto y no puede generar un contrato de servicios.")
        answers = json.loads(case["answers"])
        now = utc_iso()
        source_rows = self._source_rows(con)
        source_snapshot = {
            "product_code": self.CODE,
            "candidate_version": "2.8",
            "sources": [{k: v for k, v in x.items() if k != "file_path"} for x in source_rows],
            "original_binary_embedded": False,
            "original_identity_verified": False,
            "professional_use_authorized": False,
        }
        snapshot_json = json.dumps(source_snapshot, ensure_ascii=False, sort_keys=True, default=str)
        snapshot_hash = sha256(snapshot_json.encode()).hexdigest()
        created = []
        for tpl in self.templates:
            state, content = self._template_revision(con, tpl["template_id"])
            preview = self.factory.render(content, answers)
            filename = safe_name(
                f"{self.CODE}_{case_id}_{content.get('filename_suffix', content.get('kind','documento'))}_candidato_v2.8_r{state['current_revision_id']}.docx"
            )
            target = self.generated / filename
            candidate_sections = [x for x in preview["sections"] if x.get("_type") != "control"]
            build_docx(
                target,
                preview["title"],
                preview["subtitle"],
                [
                    ("Expediente", case_id),
                    ("Producto", self.CODE),
                    ("Plantilla", tpl["template_id"]),
                    ("Revisión de trabajo", str(state["current_revision_id"])),
                    ("Hash de plantilla", state["content_hash"] or "No registrado"),
                    ("Fuente", "Candidato estructurado v2.8 - original pendiente"),
                ],
                candidate_sections,
                footer="LegalAIZ.it · CO-EM-003 · Candidato v2.8 · No canónico · Pendiente cotejo original",
                append_default_control=False,
            )
            digest = sha256(target.read_bytes()).hexdigest()
            existing = con.execute(
                "SELECT * FROM documents WHERE case_id=? AND kind=?", (case_id, content["kind"])
            ).fetchone()
            document_id = existing["id"] if existing else "DOC-" + uuid.uuid4().hex[:8].upper()
            version = f"candidate-2.8-r{state['current_revision_id']}"
            lineage = {
                "generation_engine": "structured-candidate-v2.8",
                "template_id": tpl["template_id"],
                "template_revision_id": state["current_revision_id"],
                "template_hash": state["content_hash"],
                "candidate_source_snapshot_sha256": snapshot_hash,
                "original_binary_embedded": False,
                "original_identity_verified": False,
                "professional_use_authorized": False,
                "publication_authorized": False,
            }
            values = (
                filename,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                str(target), digest, now, version,
                "Borrador candidato estructurado - pendiente cotejo original",
                tpl["template_id"], state["current_revision_id"], state["content_hash"],
                "No canónico - original pendiente", "structured-candidate-v2.8",
                json.dumps(lineage, ensure_ascii=False, sort_keys=True), document_id,
            )
            if existing:
                con.execute(
                    """UPDATE documents SET name=?,mime_type=?,file_path=?,content_sha256=?,updated_at=?,version=?,status=?,
                       template_id=?,template_revision_id=?,template_hash=?,canonical_status=?,generation_engine=?,lineage_json=?
                       WHERE id=?""",
                    values,
                )
            else:
                con.execute(
                    """INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,
                       version,status,content_sha256,template_id,template_revision_id,template_hash,canonical_status,generation_engine,lineage_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        document_id, case_id, self.CODE, content["kind"], filename,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        str(target), None, now, now, version,
                        "Borrador candidato estructurado - pendiente cotejo original", digest,
                        tpl["template_id"], state["current_revision_id"], state["content_hash"],
                        "No canónico - original pendiente", "structured-candidate-v2.8",
                        json.dumps(lineage, ensure_ascii=False, sort_keys=True),
                    ),
                )
            con.execute(
                "INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",
                (
                    document_id, version, now,
                    f"Generación candidata v2.8 desde {tpl['template_id']}; original jurídico pendiente de incorporación y cotejo.",
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
                    "revision_id": state["current_revision_id"],
                    "included_blocks": preview.get("included_blocks", []),
                    "excluded_blocks": preview.get("excluded_blocks", []),
                }
            )
        run_id = "V28-" + uuid.uuid4().hex[:14].upper()
        con.execute(
            """INSERT INTO candidate_generation_runs_v28(id,case_id,product_code,source_snapshot_json,
               source_snapshot_sha256,documents_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)""",
            (
                run_id, case_id, self.CODE, snapshot_json, snapshot_hash,
                json.dumps(created, ensure_ascii=False, sort_keys=True), actor_id, now,
            ),
        )
        con.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, case_id))
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (
                case_id, "candidate_generation_v28",
                f"Se generó un paquete candidato v2.8 de {len(created)} documentos. El original jurídico sigue pendiente de cotejo.",
                now,
            ),
        )
        return {
            "ok": True,
            "run_id": run_id,
            "case_id": case_id,
            "source_snapshot_sha256": snapshot_hash,
            "documents": created,
            "status": "Borrador candidato estructurado - no canónico",
            "professional_use_authorized": False,
            "notice": "Estos documentos permiten probar el flujo completo, pero no sustituyen el paquete original ni pueden publicarse profesionalmente.",
        }
