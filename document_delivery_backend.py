from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
import html
import json
import re
import uuid


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "archivo")).strip("._") or "archivo"


class DocumentDeliveryCenter:
    """Linaje, integridad y entrega agrupada de los documentos del expediente."""

    def __init__(self, root: Path, templates: list[dict]):
        self.root = Path(root)
        self.generated = Path(os.environ.get("LEGAL_RUNTIME_DIR", "")).expanduser() / "generated" if os.environ.get("LEGAL_RUNTIME_DIR") else self.root / "runtime" / "generated"
        self.package_dir = self.generated / "packages"
        self.package_dir.mkdir(parents=True, exist_ok=True)
        self.templates = templates
        self.template_by_kind = {(x.get("product_code"), x.get("kind")): x for x in templates}

    def create_schema(self, con):
        columns = {row[1] for row in con.execute("PRAGMA table_info(documents)")}
        additions = {
            "content_sha256": "TEXT",
            "template_id": "TEXT",
            "template_revision_id": "INTEGER",
            "template_hash": "TEXT",
            "canonical_status": "TEXT",
            "generation_engine": "TEXT",
            "lineage_json": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                con.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS document_packages(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              file_path TEXT NOT NULL,
              manifest_json TEXT NOT NULL,
              manifest_sha256 TEXT NOT NULL,
              package_sha256 TEXT NOT NULL,
              status TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_document_packages_case ON document_packages(case_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS document_package_items(
              package_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              version TEXT NOT NULL,
              name TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              PRIMARY KEY(package_id,document_id,version),
              FOREIGN KEY(package_id) REFERENCES document_packages(id),
              FOREIGN KEY(document_id) REFERENCES documents(id)
            );
            """
        )

    @staticmethod
    def _file_bytes(row) -> bytes:
        path = Path(row["file_path"] or "")
        if not path.is_file():
            raise FileNotFoundError(f"No se encontró {row['name']}.")
        return path.read_bytes()

    def _factory_state(self, con, template_id: str | None) -> dict:
        if not template_id:
            return {}
        row = con.execute(
            """SELECT s.current_revision_id,s.publication_revision_id,s.workflow_status,
               v.content_hash FROM canonical_template_state s
               LEFT JOIN canonical_template_versions v ON v.id=s.current_revision_id
               WHERE s.template_id=?""",
            (template_id,),
        ).fetchone()
        return dict(row) if row else {}

    def annotate_case(self, con, case_id: str) -> list[dict]:
        rows = con.execute("SELECT * FROM documents WHERE case_id=? ORDER BY created_at,id", (case_id,)).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                body = self._file_bytes(row)
                digest = sha256(body).hexdigest()
            except FileNotFoundError:
                digest = None
            template = self.template_by_kind.get((row["product_code"], row["kind"]))
            template_id = template.get("template_id") if template else None
            state = self._factory_state(con, template_id)
            version = str(row["version"] or "")
            canonical_primary = row["generation_engine"] == "canonical-primary-v2.7" or version.startswith("canonical-")
            approved_factory = version.startswith("factory-") and bool(state.get("publication_revision_id"))
            if canonical_primary:
                try:
                    lineage = json.loads(row["lineage_json"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    lineage = {}
                lineage.update({
                    "generation_engine": "canonical-primary-v2.7",
                    "template_id": row["template_id"] or template_id,
                    "template_revision_id": row["template_revision_id"],
                    "template_hash": row["template_hash"],
                    "canonical_status": row["canonical_status"] or "Fuente y trazabilidad aprobadas para piloto controlado",
                    "professional_use_authorized": False,
                })
                canonical_status = lineage["canonical_status"]
                template_id = lineage["template_id"]
            else:
                canonical_status = (
                    "Plantilla con aprobación dual para piloto" if approved_factory
                    else (template.get("canonical_status") if template else "Documento auxiliar sin plantilla de fábrica")
                )
                lineage = {
                    "generation_engine": "factory-approved" if approved_factory else "structured-product-generator",
                    "template_id": template_id,
                    "template_revision_id": state.get("publication_revision_id") if approved_factory else state.get("current_revision_id"),
                    "template_hash": state.get("content_hash"),
                    "factory_status": state.get("workflow_status"),
                    "canonical_status": canonical_status,
                    "professional_use_authorized": False,
                }
            con.execute(
                """UPDATE documents SET content_sha256=?,template_id=?,template_revision_id=?,template_hash=?,
                   canonical_status=?,generation_engine=?,lineage_json=? WHERE id=?""",
                (
                    digest,
                    template_id,
                    lineage["template_revision_id"],
                    lineage["template_hash"],
                    canonical_status,
                    lineage["generation_engine"],
                    json.dumps(lineage, ensure_ascii=False, sort_keys=True),
                    row["id"],
                ),
            )
            item.update(
                {
                    "content_sha256": digest,
                    "template_id": template_id,
                    "template_revision_id": lineage["template_revision_id"],
                    "template_hash": lineage["template_hash"],
                    "canonical_status": canonical_status,
                    "generation_engine": lineage["generation_engine"],
                    "lineage": lineage,
                }
            )
            out.append(item)
        return out

    def summary(self, con, case_id: str) -> dict:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise ValueError("Expediente no encontrado.")
        docs = self.annotate_case(con, case_id)
        latest = con.execute(
            "SELECT * FROM document_packages WHERE case_id=? ORDER BY created_at DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        return {
            "case_id": case_id,
            "product_code": case["product_code"],
            "risk": case["risk"],
            "documents": [self._public_document(x) for x in docs],
            "latest_package": self._public_package(latest) if latest else None,
            "notice": "El paquete acredita integridad y linaje técnico; no convierte las plantillas en documentos jurídicos canónicos aprobados.",
        }

    @staticmethod
    def _public_document(row: dict) -> dict:
        return {
            key: row.get(key)
            for key in (
                "id", "kind", "name", "mime_type", "version", "status", "content_sha256",
                "template_id", "template_revision_id", "template_hash", "canonical_status", "generation_engine",
            )
        }

    @staticmethod
    def _public_package(row) -> dict:
        obj = dict(row)
        obj.pop("file_path", None)
        try:
            obj["manifest"] = json.loads(obj.pop("manifest_json"))
        except Exception:
            obj.pop("manifest_json", None)
        return obj

    def _summary_html(self, case, items: list[dict]) -> str:
        rows = "".join(
            f"<tr><td>{html.escape(x['name'])}</td><td>{html.escape(x['version'])}</td><td>{html.escape(x.get('status') or '')}</td><td><code>{html.escape((x.get('sha256') or '')[:16])}…</code></td></tr>"
            for x in items
        )
        return f"""<!doctype html><html lang='es'><meta charset='utf-8'><title>Paquete {html.escape(case['id'])}</title>
        <style>body{{font-family:Arial,sans-serif;color:#1f1f1f;max-width:900px;margin:40px auto;line-height:1.5}}h1{{color:#0D1324}}.gold{{color:#9b7742}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border:1px solid #ddd;text-align:left}}th{{background:#F7F5F1}}.notice{{padding:14px;background:#fff8e8;border-left:4px solid #C9A96E}}</style>
        <h1>LegalAIZ.it</h1><p class='gold'>Más que respuestas, soluciones.</p><h2>Paquete documental del expediente {html.escape(case['id'])}</h2>
        <p>Producto: {html.escape(case['product_code'])} · Riesgo: {html.escape(case['risk'])} · Estado: {html.escape(case['status'])}</p>
        <table><thead><tr><th>Archivo</th><th>Versión</th><th>Estado</th><th>SHA-256</th></tr></thead><tbody>{rows}</tbody></table>
        <p class='notice'><b>Control de uso:</b> este paquete demuestra integridad, versiones y trazabilidad técnica. Los documentos no están autorizados para uso profesional hasta incorporar, cotejar y aprobar las fuentes jurídicas canónicas.</p></html>"""

    def build(self, con, case_id: str, created_by: str) -> dict:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise ValueError("Expediente no encontrado.")
        docs = self.annotate_case(con, case_id)
        package_id = "PKG-" + uuid.uuid4().hex[:14].upper()
        created_at = utc_iso()
        items = []
        payloads = []
        used_names = set()
        for doc in docs:
            try:
                body = self._file_bytes(doc)
            except FileNotFoundError:
                continue
            name = safe_name(doc["name"])
            if name in used_names:
                name = f"{doc['id']}_{name}"
            used_names.add(name)
            digest = sha256(body).hexdigest()
            item = {
                "document_id": doc["id"],
                "kind": doc["kind"],
                "name": name,
                "version": str(doc["version"] or ""),
                "status": doc["status"],
                "sha256": digest,
                "size_bytes": len(body),
                "template_id": doc.get("template_id"),
                "template_revision_id": doc.get("template_revision_id"),
                "template_hash": doc.get("template_hash"),
                "canonical_status": doc.get("canonical_status"),
                "generation_engine": doc.get("generation_engine"),
            }
            items.append(item)
            payloads.append((f"documentos/{name}", body))
        pdf_previews = []
        for row in con.execute(
            """SELECT p.* FROM document_pdf_previews p JOIN documents d ON d.id=p.document_id
               WHERE d.case_id=? ORDER BY p.created_at""", (case_id,)
        ).fetchall():
            path = Path(row["file_path"] or "")
            if not path.is_file():
                continue
            body = path.read_bytes()
            name = safe_name(path.name)
            payloads.append((f"vistas_pdf/{name}", body))
            pdf_previews.append({
                "preview_id": row["id"], "document_id": row["document_id"], "name": name,
                "sha256": sha256(body).hexdigest(), "size_bytes": len(body),
                "document_sha256": row["document_sha256"], "created_at": row["created_at"],
            })
        acceptances = []
        for row in con.execute(
            "SELECT * FROM document_acceptances WHERE case_id=? AND status='Vigente' ORDER BY created_at", (case_id,)
        ).fetchall():
            path = Path(row["receipt_path"] or "")
            if not path.is_file():
                continue
            body = path.read_bytes()
            name = safe_name(path.name)
            payloads.append((f"constancias_aceptacion/{name}", body))
            acceptances.append({
                "acceptance_id": row["id"], "document_id": row["document_id"], "name": name,
                "sha256": sha256(body).hexdigest(), "size_bytes": len(body),
                "receipt_sha256": row["receipt_sha256"], "receipt_hmac": row["receipt_hmac"],
                "created_at": row["created_at"], "status": row["status"],
            })
        manifest = {
            "schema": "legalaizit-document-package-v2.7",
            "package_id": package_id,
            "case": {
                "id": case["id"],
                "product_code": case["product_code"],
                "title": case["title"],
                "risk": case["risk"],
                "status": case["status"],
                "review_status": case["review_status"],
            },
            "created_at": created_at,
            "created_by": created_by,
            "files": items,
            "pdf_previews": pdf_previews,
            "acceptances": acceptances,
            "professional_use_authorized": False,
            "control": "Integridad y linaje técnico verificados. Uso profesional pendiente de fuente canónica y aprobación correspondiente.",
        }
        manifest_raw = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        manifest_hash = sha256(manifest_raw).hexdigest()
        filename = safe_name(f"LegalAIZit_{case_id}_paquete_documental_{package_id}.zip")
        self.package_dir.mkdir(parents=True, exist_ok=True)
        target = self.package_dir / filename
        with ZipFile(target, "w", ZIP_DEFLATED) as z:
            for arcname, body in payloads:
                z.writestr(arcname, body)
            z.writestr("MANIFEST.json", manifest_raw)
            z.writestr("RESUMEN.html", self._summary_html(case, items).encode("utf-8"))
            z.writestr(
                "LEEME.txt",
                ("LegalAIZ.it — Paquete documental\n\n"
                 "Este ZIP reúne los documentos vigentes, vistas PDF, constancias de aceptación disponibles y hashes SHA-256.\n"
                 "No acredita aprobación jurídica canónica ni autoriza uso profesional.\n").encode("utf-8"),
            )
        package_hash = sha256(target.read_bytes()).hexdigest()
        con.execute(
            """INSERT INTO document_packages(id,case_id,file_path,manifest_json,manifest_sha256,
               package_sha256,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (package_id, case_id, str(target), manifest_raw.decode("utf-8"), manifest_hash, package_hash, "Generado", created_by, created_at),
        )
        for item in items:
            con.execute(
                "INSERT INTO document_package_items(package_id,document_id,version,name,sha256,size_bytes) VALUES(?,?,?,?,?,?)",
                (package_id, item["document_id"], item["version"], item["name"], item["sha256"], item["size_bytes"]),
            )
        return {
            "id": package_id,
            "case_id": case_id,
            "name": filename,
            "manifest_sha256": manifest_hash,
            "package_sha256": package_hash,
            "files": len(items),
            "created_at": created_at,
            "status": "Generado",
        }

    def package(self, con, package_id: str):
        row = con.execute("SELECT * FROM document_packages WHERE id=?", (package_id,)).fetchone()
        return self._public_package(row) if row else None

    def package_path(self, con, package_id: str) -> Path | None:
        row = con.execute("SELECT file_path FROM document_packages WHERE id=?", (package_id,)).fetchone()
        if not row:
            return None
        path = Path(row["file_path"])
        return path if path.is_file() else None

    def verify(self, con, package_id: str) -> dict:
        row = con.execute("SELECT * FROM document_packages WHERE id=?", (package_id,)).fetchone()
        if not row:
            raise ValueError("Paquete no encontrado.")
        path = Path(row["file_path"])
        if not path.is_file():
            raise ValueError("El archivo del paquete no está disponible.")
        package_hash = sha256(path.read_bytes()).hexdigest()
        errors = []
        manifest = json.loads(row["manifest_json"])
        with ZipFile(path) as z:
            for item in manifest.get("files", []):
                arc = f"documentos/{item['name']}"
                try:
                    body = z.read(arc)
                except KeyError:
                    errors.append({"file": arc, "error": "ausente"})
                    continue
                if sha256(body).hexdigest() != item["sha256"]:
                    errors.append({"file": arc, "error": "hash inválido"})
        return {
            "package_id": package_id,
            "package_hash_valid": package_hash == row["package_sha256"],
            "files_checked": len(manifest.get("files", [])),
            "valid": package_hash == row["package_sha256"] and not errors,
            "errors": errors,
        }
