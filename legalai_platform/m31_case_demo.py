from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
import json
import re
import shutil
import tempfile
import threading
import uuid

from legalai_platform.professional_contract_docx import build_professional_docx


class M31CaseDemoCenter:
    """Expedientes sintéticos completos con versiones, aprobación dual y liberación.

    El centro M31.8 no sustituye los expedientes ordinarios. Crea una cohorte
    explícitamente sintética para demostrar el flujo completo sobre los once
    productos: datos, diagnóstico, generación, nueva revisión, aprobación jurídica,
    QA independiente, paquete final y verificación criptográfica.
    """

    SCHEMA = "legalaizit_m31_8_case_demo_v1"
    VERSION = "5.0.7"
    MILESTONE = "M31.8"
    CASE_PREFIX = "M318-"
    SENTINELS = (
        "{{", "}}", "undefined", "<null>", "NULL", "N/A", "<none>",
        "[definir]", "[pendiente de diligenciar]", "[completar]",
        "Pendiente de diligenciar", "Pendiente por diligenciar",
        "Pendiente por definir", "Por definir",
    )

    def __init__(
        self,
        root: Path,
        runtime: Path,
        factory,
        templates: list[dict[str, Any]],
        products: list[dict[str, Any]],
        interviews: dict[str, Any],
        answer_source,
        diagnose,
        audit,
        now,
    ):
        self.root = Path(root).resolve()
        self.runtime = Path(runtime).resolve()
        self.factory = factory
        self.templates = list(templates)
        self.products = {row["code"]: row for row in products}
        self.interviews = interviews
        self.answer_source = answer_source
        self.diagnose = diagnose
        self.audit = audit
        self.now = now
        self.output_root = self.runtime / "demo_cases_m31_8"
        self.logo_path = self.root / "app" / "assets" / "logo-legalaizit-docx.png"
        self.validated_root = self.root / "governance" / "m24_4" / "validated_documents"
        self._lock = threading.Lock()

    @staticmethod
    def _safe(value: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "archivo")).strip("._")
        return clean[:180] or "archivo"

    @staticmethod
    def _hash(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _json_hash(value: Any) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _row(row) -> dict[str, Any] | None:
        return dict(row) if row else None

    @staticmethod
    def _actor(con, actor_id: str) -> dict[str, Any]:
        row = con.execute("SELECT id,name,email,role,specialty,verified FROM users WHERE id=?", (actor_id,)).fetchone()
        if not row:
            raise ValueError("El usuario aprobador no existe.")
        return dict(row)

    @staticmethod
    def _write_zip(target: Path, files: list[tuple[Path, str]]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for source, arcname in files:
                archive.write(source, arcname)

    @classmethod
    def _docx_sentinels(cls, path: Path) -> list[str]:
        try:
            with ZipFile(path) as archive:
                xml = "\n".join(
                    archive.read(name).decode("utf-8", errors="replace")
                    for name in archive.namelist()
                    if name.startswith("word/") and name.endswith(".xml")
                )
        except Exception:
            return ["invalid_docx"]
        lowered = xml.lower()
        return [token for token in cls.SENTINELS if token.lower() in lowered]

    def ensure_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m31_8_demo_runs(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              product_code TEXT NOT NULL UNIQUE,
              workflow_status TEXT NOT NULL,
              active_revision_id TEXT,
              released_revision_id TEXT,
              legal_reviewer_id TEXT NOT NULL,
              qa_reviewer_id TEXT NOT NULL,
              package_path TEXT,
              package_sha256 TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(legal_reviewer_id) REFERENCES users(id),
              FOREIGN KEY(qa_reviewer_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS m31_8_demo_revisions(
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              revision_no INTEGER NOT NULL,
              answers_json TEXT NOT NULL,
              result_json TEXT NOT NULL,
              answers_sha256 TEXT NOT NULL,
              document_set_sha256 TEXT,
              revision_sha256 TEXT,
              status TEXT NOT NULL,
              change_note TEXT,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(run_id,revision_no),
              FOREIGN KEY(run_id) REFERENCES m31_8_demo_runs(id)
            );
            CREATE TABLE IF NOT EXISTS m31_8_demo_documents(
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              template_id TEXT NOT NULL,
              title TEXT NOT NULL,
              file_name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(revision_id,template_id),
              FOREIGN KEY(run_id) REFERENCES m31_8_demo_runs(id),
              FOREIGN KEY(revision_id) REFERENCES m31_8_demo_revisions(id)
            );
            CREATE TABLE IF NOT EXISTS m31_8_demo_approvals(
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              approval_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              decision TEXT NOT NULL,
              comment TEXT,
              revision_sha256 TEXT NOT NULL,
              mode TEXT NOT NULL DEFAULT 'interactive_demo',
              created_at TEXT NOT NULL,
              UNIQUE(run_id,revision_id,approval_type),
              FOREIGN KEY(run_id) REFERENCES m31_8_demo_runs(id),
              FOREIGN KEY(revision_id) REFERENCES m31_8_demo_revisions(id),
              FOREIGN KEY(actor_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS m31_8_demo_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              actor_id TEXT,
              event_type TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              previous_hash TEXT,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES m31_8_demo_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m318_revision_run ON m31_8_demo_revisions(run_id,revision_no DESC);
            CREATE INDEX IF NOT EXISTS idx_m318_docs_revision ON m31_8_demo_documents(revision_id,template_id);
            CREATE INDEX IF NOT EXISTS idx_m318_approvals_revision ON m31_8_demo_approvals(revision_id,approval_type);
            """
        )

    def _event(self, con, run_id: str, case_id: str, actor_id: str | None, event_type: str, detail: Any) -> None:
        created_at = self.now()
        previous = con.execute(
            "SELECT event_hash FROM m31_8_demo_events WHERE run_id=? ORDER BY id DESC LIMIT 1", (run_id,)
        ).fetchone()
        previous_hash = previous[0] if previous else ""
        canonical = {
            "run_id": run_id,
            "case_id": case_id,
            "actor_id": actor_id,
            "event_type": event_type,
            "detail": detail,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }
        event_hash = self._json_hash(canonical)
        con.execute(
            "INSERT INTO m31_8_demo_events(run_id,case_id,actor_id,event_type,detail_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (run_id, case_id, actor_id, event_type, json.dumps(detail, ensure_ascii=False), previous_hash or None, event_hash, created_at),
        )

    def _specialist_for(self, code: str) -> str:
        if code.startswith("CO-LA"):
            return "USR-LAB"
        if code.startswith("CO-TR"):
            return "USR-TRANSIT"
        return "USR-COMM"

    def _templates_for(self, code: str) -> list[dict[str, Any]]:
        return sorted((t for t in self.templates if t.get("product_code") == code), key=lambda x: x["template_id"])

    def _validated_assets(self, code: str) -> list[Path]:
        source = self.validated_root / code
        manifest = source / "manifest.json"
        if not manifest.is_file():
            return []
        try:
            expected = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
        except (OSError, json.JSONDecodeError):
            return []
        result: list[Path] = []
        for name, digest in expected.items():
            path = source / name
            if path.is_file() and path.suffix.lower() in {".docx", ".pdf"} and self._hash(path) == digest:
                result.append(path)
        return sorted(result)

    def _editable_fields(self, code: str, answers: dict[str, Any]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for question in self.interviews.get(code, {}).get("questions", []):
            if question.get("type") not in {"text", "textarea", "number", "date", "email", "select"}:
                continue
            fields.append({
                "id": question["id"],
                "label": question.get("label") or question["id"],
                "type": question.get("type") or "text",
                "required": bool(question.get("required")),
                "options": list(question.get("options") or []),
                "value": answers.get(question["id"]),
            })
            if len(fields) >= 8:
                break
        return fields

    def _case_id(self, code: str) -> str:
        return self.CASE_PREFIX + code.replace("CO-", "").replace("-", "")

    def _run_id(self, code: str) -> str:
        return "RUN-" + self._case_id(code)

    def _revision_dir(self, case_id: str, revision_no: int) -> Path:
        return self.output_root / case_id / f"revision_{revision_no:03d}"

    def _cohort_package_path(self) -> Path:
        return self.output_root / f"LegalAIZit_M31_8_COHORTE_EXPEDIENTES_FINAL_DEMO_v{self.VERSION}.zip"

    def _invalidate_cohort_package(self) -> None:
        package = self._cohort_package_path()
        if package.exists():
            package.unlink()

    def build_cohort_package(self, con) -> dict[str, Any] | None:
        """Construye una entrega global únicamente cuando los 11 casos están liberados."""
        rows = con.execute(
            "SELECT case_id,product_code,package_path,package_sha256,released_revision_id FROM m31_8_demo_runs ORDER BY product_code"
        ).fetchall()
        if len(rows) != len(self.products) or any(not row["package_path"] or not row["released_revision_id"] for row in rows):
            self._invalidate_cohort_package()
            return None
        staging = Path(tempfile.mkdtemp(prefix="m31_8_cohort_", dir=str(self.output_root)))
        package = self._cohort_package_path()
        try:
            files: list[tuple[Path, str]] = []
            case_rows: list[dict[str, Any]] = []
            for row in rows:
                source = Path(row["package_path"])
                if not source.is_file() or self._hash(source) != row["package_sha256"]:
                    raise ValueError(f"El paquete del expediente {row['case_id']} no supera integridad.")
                arcname = f"expedientes/{source.name}"
                files.append((source, arcname))
                case_rows.append({
                    "case_id": row["case_id"],
                    "product_code": row["product_code"],
                    "package": source.name,
                    "sha256": row["package_sha256"],
                    "size_bytes": source.stat().st_size,
                })
            manifest = {
                "schema": "legalaizit_m31_8_cohort_release_manifest_v1",
                "milestone": self.MILESTONE,
                "version": self.VERSION,
                "generated_at": self.now(),
                "case_count": len(case_rows),
                "product_count": len({row['product_code'] for row in case_rows}),
                "active_document_count": con.execute(
                    "SELECT COUNT(*) FROM m31_8_demo_documents d JOIN m31_8_demo_runs r ON r.active_revision_id=d.revision_id"
                ).fetchone()[0],
                "production_authorized": False,
                "data_classification": "synthetic_no_real_personal_data",
                "cases": case_rows,
            }
            manifest_path = staging / "MANIFEST_COHORTE.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append((manifest_path, manifest_path.name))
            checksums = staging / "SHA256SUMS.txt"
            checksums.write_text(
                "\n".join(f"{self._hash(source)}  {arcname}" for source, arcname in sorted(files, key=lambda x: x[1])) + "\n",
                encoding="utf-8",
            )
            files.append((checksums, checksums.name))
            tmp_package = staging / package.name
            self._write_zip(tmp_package, files)
            package.parent.mkdir(parents=True, exist_ok=True)
            tmp_package.replace(package)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return {
            "name": package.name,
            "sha256": self._hash(package),
            "size_bytes": package.stat().st_size,
            "download_path": package.name,
            "case_count": 11,
            "document_count": 76,
        }

    def _create_case_record(self, con, code: str, answers: dict[str, Any], result: dict[str, Any], actor: str) -> tuple[str, str]:
        case_id = self._case_id(code)
        run_id = self._run_id(code)
        product = self.products[code]
        created_at = self.now()
        legal_reviewer = self._specialist_for(code)
        qa_reviewer = "USR-ADMIN"
        existing = con.execute("SELECT id FROM cases WHERE id=?", (case_id,)).fetchone()
        if not existing:
            con.execute(
                "INSERT INTO cases(id,product_code,title,risk,status,owner_id,specialist_id,review_status,created_at,updated_at,answers,result) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    case_id, code, f"Demo realista · {product.get('title', code)}", result["risk"],
                    "Borrador documental", "USR-CLIENT", legal_reviewer, "Pendiente de revisión jurídica",
                    created_at, created_at, json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False),
                ),
            )
            tasks = (
                ("Confirmar datos sintéticos del expediente", "Completada", "client"),
                ("Generar revisión documental íntegra", "Completada", "system"),
                ("Aprobar jurídicamente la revisión exacta", "Pendiente", "specialist"),
                ("Ejecutar QA independiente sobre la misma revisión", "Bloqueada", "admin"),
                ("Liberar paquete final trazable", "Bloqueada", "admin"),
            )
            for position, (label, status, owner_role) in enumerate(tasks, 1):
                con.execute(
                    "INSERT INTO case_tasks(id,case_id,label,status,owner_role,position,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (f"TSK-{uuid.uuid4().hex[:10].upper()}", case_id, label, status, owner_role, position, created_at, created_at),
                )
            con.execute(
                "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
                (case_id, "m31_8_demo", "Expediente sintético M31.8 creado para demostración integral.", created_at),
            )
        con.execute(
            "INSERT INTO m31_8_demo_runs(id,case_id,product_code,workflow_status,active_revision_id,released_revision_id,legal_reviewer_id,qa_reviewer_id,package_path,package_sha256,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
            (run_id, case_id, code, "Borrador documental", None, None, legal_reviewer, qa_reviewer, None, None, actor, created_at, created_at),
        )
        return run_id, case_id

    def _generate_revision(
        self,
        con,
        run_id: str,
        case_id: str,
        code: str,
        answers: dict[str, Any],
        result: dict[str, Any],
        actor: str,
        note: str,
    ) -> dict[str, Any]:
        count = con.execute("SELECT COUNT(*) FROM m31_8_demo_revisions WHERE run_id=?", (run_id,)).fetchone()[0]
        revision_no = int(count) + 1
        revision_id = f"REV-{uuid.uuid4().hex[:12].upper()}"
        created_at = self.now()
        revision_dir = self._revision_dir(case_id, revision_no)
        self._invalidate_cohort_package()
        if revision_dir.exists():
            shutil.rmtree(revision_dir)
        revision_dir.mkdir(parents=True, exist_ok=True)
        answers_hash = self._json_hash(answers)
        con.execute(
            "INSERT INTO m31_8_demo_revisions(id,run_id,revision_no,answers_json,result_json,answers_sha256,document_set_sha256,revision_sha256,status,change_note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (revision_id, run_id, revision_no, json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False), answers_hash, None, None, "Generando documentos", note, actor, created_at),
        )
        documents: list[dict[str, Any]] = []
        file_hashes: list[str] = []
        for index, template in enumerate(self._templates_for(code), 1):
            validation = self.factory.validate(template["template_id"], template)
            if not validation.get("valid"):
                raise ValueError(f"Plantilla inválida {template['template_id']}: {'; '.join(validation.get('errors') or [])}")
            preview = self.factory.render(template, answers)
            filename = self._safe(
                f"{case_id}_R{revision_no:03d}_{index:02d}_{template.get('filename_suffix') or template['kind']}.docx"
            )
            target = revision_dir / filename
            sections = preview.get("sections") or []
            sanitizer = getattr(self.answer_source, "_sanitize_demo_sections", None)
            if callable(sanitizer):
                sections = sanitizer(sections)
            build_professional_docx(
                target,
                title=preview["title"],
                subtitle=preview.get("subtitle") or f"{self.products[code].get('title', code)} · expediente {case_id}",
                metadata=[
                    ("Expediente", case_id),
                    ("Producto", code),
                    ("Plantilla", template["template_id"]),
                    ("Revisión", str(revision_no)),
                    ("Clasificación", "Datos sintéticos de demostración"),
                    ("Generado", created_at),
                ],
                sections=sections,
                logo_path=self.logo_path if self.logo_path.is_file() else None,
                footer="LegalAIZ.it · expediente sintético · revisión controlada",
            )
            bad = self._docx_sentinels(target)
            if bad:
                raise ValueError(f"El documento {filename} contiene marcadores no resueltos: {', '.join(bad)}")
            digest = self._hash(target)
            file_hashes.append(digest)
            doc_id = f"M318DOC-{uuid.uuid4().hex[:12].upper()}"
            con.execute(
                "INSERT INTO m31_8_demo_documents(id,run_id,revision_id,template_id,title,file_name,file_path,sha256,size_bytes,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, run_id, revision_id, template["template_id"], preview["title"], filename, str(target), digest, target.stat().st_size, "Borrador de revisión", created_at),
            )
            kind = f"m31_8:{template['template_id']}"
            current = con.execute("SELECT id FROM documents WHERE case_id=? AND kind=?", (case_id, kind)).fetchone()
            if current:
                public_id = current["id"]
                con.execute(
                    "UPDATE documents SET name=?,mime_type=?,file_path=?,updated_at=?,version=?,status=? WHERE id=?",
                    (filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", str(target), created_at, f"M31.8-r{revision_no}", "Borrador de revisión", public_id),
                )
            else:
                public_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
                con.execute(
                    "INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,version,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (public_id, case_id, code, kind, filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", str(target), None, created_at, created_at, f"M31.8-r{revision_no}", "Borrador de revisión"),
                )
            con.execute(
                "INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",
                (public_id, f"M31.8-r{revision_no}", created_at, note, str(target)),
            )
            documents.append({
                "id": doc_id,
                "document_id": public_id,
                "template_id": template["template_id"],
                "title": preview["title"],
                "name": filename,
                "sha256": digest,
                "size_bytes": target.stat().st_size,
            })
        document_set_hash = sha256("\n".join(sorted(file_hashes)).encode("utf-8")).hexdigest()
        revision_hash = self._json_hash({
            "run_id": run_id,
            "revision_no": revision_no,
            "answers_sha256": answers_hash,
            "document_set_sha256": document_set_hash,
        })
        con.execute(
            "UPDATE m31_8_demo_revisions SET document_set_sha256=?,revision_sha256=?,status=? WHERE id=?",
            (document_set_hash, revision_hash, "Pendiente de revisión jurídica", revision_id),
        )
        con.execute(
            "UPDATE m31_8_demo_runs SET workflow_status=?,active_revision_id=?,released_revision_id=NULL,package_path=NULL,package_sha256=NULL,updated_at=? WHERE id=?",
            ("Pendiente de revisión jurídica", revision_id, created_at, run_id),
        )
        con.execute(
            "UPDATE cases SET answers=?,result=?,risk=?,status=?,review_status=?,specialist_id=?,updated_at=? WHERE id=?",
            (json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False), result["risk"], "En revisión documental", "Pendiente de revisión jurídica", self._specialist_for(code), created_at, case_id),
        )
        con.execute(
            "UPDATE case_tasks SET status=CASE WHEN label='Aprobar jurídicamente la revisión exacta' THEN 'Pendiente' ELSE CASE WHEN label IN ('Ejecutar QA independiente sobre la misma revisión','Liberar paquete final trazable') THEN 'Bloqueada' ELSE status END END,updated_at=? WHERE case_id=?",
            (created_at, case_id),
        )
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "document_revision", f"Se generó la revisión {revision_no} con {len(documents)} documentos y hash {revision_hash[:12]}…", created_at),
        )
        self._event(con, run_id, case_id, actor, "revision_generated", {
            "revision_id": revision_id,
            "revision_no": revision_no,
            "documents": len(documents),
            "revision_sha256": revision_hash,
            "note": note,
        })
        self.audit(con, actor, "m31_8_demo_revision", revision_id, "generate", {
            "case_id": case_id, "revision_no": revision_no, "documents": len(documents), "revision_sha256": revision_hash,
        })
        return {
            "revision_id": revision_id,
            "revision_no": revision_no,
            "revision_sha256": revision_hash,
            "document_set_sha256": document_set_hash,
            "documents": documents,
        }

    def _approval(self, con, run_id: str, approval_type: str, actor_id: str, decision: str, comment: str, mode: str) -> dict[str, Any]:
        if approval_type not in {"legal", "qa"}:
            raise ValueError("Tipo de aprobación inválido.")
        if decision not in {"approve", "reject"}:
            raise ValueError("Decisión inválida.")
        run = con.execute("SELECT * FROM m31_8_demo_runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            raise ValueError("Expediente demo no encontrado.")
        revision = con.execute("SELECT * FROM m31_8_demo_revisions WHERE id=?", (run["active_revision_id"],)).fetchone()
        if not revision:
            raise ValueError("El expediente no tiene revisión activa.")
        actor = self._actor(con, actor_id)
        if approval_type == "legal":
            if actor["role"] != "specialist":
                raise PermissionError("La aprobación jurídica requiere un usuario especialista.")
            if actor_id != run["legal_reviewer_id"]:
                raise PermissionError("El especialista no está asignado a este expediente.")
        else:
            if actor["role"] != "admin":
                raise PermissionError("La aprobación de QA requiere administración.")
            legal = con.execute(
                "SELECT * FROM m31_8_demo_approvals WHERE run_id=? AND revision_id=? AND approval_type='legal' AND decision='approve'",
                (run_id, revision["id"]),
            ).fetchone()
            if not legal:
                raise ValueError("QA solo puede decidir después de la aprobación jurídica de la misma revisión.")
            if legal["actor_id"] == actor_id:
                raise ValueError("La aprobación jurídica y QA deben ser realizados por personas distintas.")
            if legal["revision_sha256"] != revision["revision_sha256"]:
                raise ValueError("La aprobación jurídica no corresponde a la revisión activa.")
        created_at = self.now()
        approval_id = f"APR-{uuid.uuid4().hex[:12].upper()}"
        con.execute(
            "INSERT INTO m31_8_demo_approvals(id,run_id,revision_id,approval_type,actor_id,actor_role,decision,comment,revision_sha256,mode,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id,revision_id,approval_type) DO UPDATE SET actor_id=excluded.actor_id,actor_role=excluded.actor_role,decision=excluded.decision,comment=excluded.comment,revision_sha256=excluded.revision_sha256,mode=excluded.mode,created_at=excluded.created_at",
            (approval_id, run_id, revision["id"], approval_type, actor_id, actor["role"], decision, comment, revision["revision_sha256"], mode, created_at),
        )
        if decision == "reject":
            workflow = "Devuelto para ajustes"
            review_status = "Devuelto"
            document_status = "Requiere ajustes"
        elif approval_type == "legal":
            workflow = "Pendiente de QA independiente"
            review_status = "Aprobación jurídica registrada"
            document_status = "Aprobado jurídicamente · pendiente QA"
        else:
            workflow = "Aprobado para liberación"
            review_status = "Aprobación dual completa"
            document_status = "Aprobado para liberación"
        con.execute("UPDATE m31_8_demo_runs SET workflow_status=?,updated_at=? WHERE id=?", (workflow, created_at, run_id))
        con.execute("UPDATE m31_8_demo_revisions SET status=? WHERE id=?", (workflow, revision["id"]))
        con.execute("UPDATE m31_8_demo_documents SET status=? WHERE revision_id=?", (document_status, revision["id"]))
        con.execute("UPDATE documents SET status=?,updated_at=? WHERE case_id=? AND kind LIKE 'm31_8:%'", (document_status, created_at, run["case_id"]))
        con.execute("UPDATE cases SET status=?,review_status=?,updated_at=? WHERE id=?", (workflow, review_status, created_at, run["case_id"]))
        if approval_type == "legal" and decision == "approve":
            con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Aprobar jurídicamente la revisión exacta'", (created_at, run["case_id"]))
            con.execute("UPDATE case_tasks SET status='Pendiente',updated_at=? WHERE case_id=? AND label='Ejecutar QA independiente sobre la misma revisión'", (created_at, run["case_id"]))
        elif approval_type == "qa" and decision == "approve":
            con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Ejecutar QA independiente sobre la misma revisión'", (created_at, run["case_id"]))
            con.execute("UPDATE case_tasks SET status='Pendiente',updated_at=? WHERE case_id=? AND label='Liberar paquete final trazable'", (created_at, run["case_id"]))
        else:
            con.execute("UPDATE case_tasks SET status='Pendiente',updated_at=? WHERE case_id=? AND label='Aprobar jurídicamente la revisión exacta'", (created_at, run["case_id"]))
            con.execute("UPDATE case_tasks SET status='Bloqueada',updated_at=? WHERE case_id=? AND label IN ('Ejecutar QA independiente sobre la misma revisión','Liberar paquete final trazable')", (created_at, run["case_id"]))
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (run["case_id"], f"m31_8_{approval_type}", f"{approval_type.upper()}: {decision}. {comment}", created_at),
        )
        self._event(con, run_id, run["case_id"], actor_id, f"{approval_type}_decision", {
            "decision": decision, "comment": comment, "revision_id": revision["id"], "revision_sha256": revision["revision_sha256"], "mode": mode,
        })
        self.audit(con, actor_id, "m31_8_demo_revision", revision["id"], f"{approval_type}_{decision}", {
            "case_id": run["case_id"], "revision_sha256": revision["revision_sha256"], "mode": mode,
        })
        return {"ok": True, "workflow_status": workflow, "revision_id": revision["id"], "revision_sha256": revision["revision_sha256"]}

    def approve(self, con, case_id: str, approval_type: str, actor_id: str, decision: str = "approve", comment: str = "", mode: str = "interactive_demo") -> dict[str, Any]:
        self.ensure_schema(con)
        run = con.execute("SELECT id FROM m31_8_demo_runs WHERE case_id=?", (case_id,)).fetchone()
        if not run:
            raise ValueError("Expediente demo no encontrado.")
        return self._approval(con, run["id"], approval_type, actor_id, decision, comment, mode)

    def _release_certificate(self, target: Path, case: dict[str, Any], revision: dict[str, Any], approvals: list[dict[str, Any]], package_manifest: dict[str, Any]) -> None:
        rows = []
        for approval in approvals:
            rows.append({
                "heading": "Aprobación jurídica" if approval["approval_type"] == "legal" else "Control de QA",
                "type": "section",
                "text": (
                    f"Decisión: {approval['decision']}. Responsable: {approval.get('actor_name') or approval['actor_id']} "
                    f"({approval['actor_role']}). Fecha: {approval['created_at']}. Hash de revisión: {approval['revision_sha256']}."
                ),
                "bullets": [approval.get("comment") or "Sin observaciones adicionales."],
            })
        rows.append({
            "heading": "Control de integridad",
            "type": "control",
            "text": "La liberación corresponde exclusivamente a la revisión y al conjunto documental identificados en este certificado.",
            "table": [
                ["Revisión", str(revision["revision_no"])],
                ["Hash de revisión", revision["revision_sha256"]],
                ["Hash documental", revision["document_set_sha256"]],
                ["Documentos", str(package_manifest["document_count"])],
                ["Clasificación", "Expediente sintético para demostración controlada"],
            ],
        })
        build_professional_docx(
            target,
            title="Certificado de liberación documental",
            subtitle=f"Expediente {case['id']} · {case['product_code']}",
            metadata=[
                ("Estado", "Liberado para demostración"),
                ("Revisión", str(revision["revision_no"])),
                ("Fecha", package_manifest["released_at"]),
                ("Uso", "Demostración y piloto controlado"),
            ],
            sections=rows,
            logo_path=self.logo_path if self.logo_path.is_file() else None,
            footer="LegalAIZ.it · certificado de liberación sintética M31.8",
        )

    def release(self, con, case_id: str, actor_id: str, mode: str = "interactive_demo") -> dict[str, Any]:
        self.ensure_schema(con)
        actor = self._actor(con, actor_id)
        if actor["role"] != "admin":
            raise PermissionError("La liberación final requiere administración.")
        run = con.execute("SELECT * FROM m31_8_demo_runs WHERE case_id=?", (case_id,)).fetchone()
        if not run:
            raise ValueError("Expediente demo no encontrado.")
        revision = con.execute("SELECT * FROM m31_8_demo_revisions WHERE id=?", (run["active_revision_id"],)).fetchone()
        if not revision:
            raise ValueError("El expediente no tiene revisión activa.")
        approvals = [dict(row) for row in con.execute(
            "SELECT a.*,u.name actor_name FROM m31_8_demo_approvals a LEFT JOIN users u ON u.id=a.actor_id WHERE a.run_id=? AND a.revision_id=? ORDER BY CASE a.approval_type WHEN 'legal' THEN 1 ELSE 2 END",
            (run["id"], revision["id"]),
        ).fetchall()]
        amap = {row["approval_type"]: row for row in approvals}
        if not all(amap.get(kind, {}).get("decision") == "approve" for kind in ("legal", "qa")):
            raise ValueError("La liberación exige aprobación jurídica y QA aprobados sobre la misma revisión.")
        if amap["legal"]["actor_id"] == amap["qa"]["actor_id"]:
            raise ValueError("La aprobación jurídica y QA deben pertenecer a personas distintas.")
        if any(row["revision_sha256"] != revision["revision_sha256"] for row in approvals):
            raise ValueError("Las aprobaciones no corresponden a la revisión activa.")
        case = self._row(con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())
        docs = [dict(row) for row in con.execute(
            "SELECT * FROM m31_8_demo_documents WHERE revision_id=? ORDER BY template_id", (revision["id"],)
        ).fetchall()]
        if not docs:
            raise ValueError("La revisión no contiene documentos.")
        release_root = self.output_root / case_id / f"release_r{revision['revision_no']:03d}"
        staging = Path(tempfile.mkdtemp(prefix="m31_8_release_", dir=str(self.output_root)))
        released_at = self.now()
        try:
            files: list[tuple[Path, str]] = []
            file_rows: list[dict[str, Any]] = []
            for doc in docs:
                path = Path(doc["file_path"])
                if not path.is_file() or self._hash(path) != doc["sha256"]:
                    raise ValueError(f"El documento {doc['file_name']} no supera la verificación de integridad.")
                files.append((path, f"documentos_finales/{doc['file_name']}"))
                file_rows.append({
                    "type": "final_docx", "template_id": doc["template_id"], "name": doc["file_name"],
                    "sha256": doc["sha256"], "size_bytes": doc["size_bytes"],
                })
            for source in self._validated_assets(case["product_code"]):
                target = staging / "referencias_validadas" / self._safe(source.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                digest = self._hash(target)
                files.append((target, f"referencias_validadas/{target.name}"))
                file_rows.append({"type": "validated_reference", "name": target.name, "sha256": digest, "size_bytes": target.stat().st_size})
            expediente = {
                "schema": "legalaizit_m31_8_case_snapshot_v1",
                "case_id": case_id,
                "product_code": case["product_code"],
                "title": case["title"],
                "risk": case["risk"],
                "answers": json.loads(revision["answers_json"]),
                "result": json.loads(revision["result_json"]),
                "revision_no": revision["revision_no"],
                "revision_sha256": revision["revision_sha256"],
                "data_classification": "synthetic_no_real_personal_data",
            }
            expediente_path = staging / "EXPEDIENTE.json"
            expediente_path.write_text(json.dumps(expediente, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append((expediente_path, "EXPEDIENTE.json"))
            approval_payload = {
                "schema": "legalaizit_m31_8_dual_approval_v1",
                "case_id": case_id,
                "revision_id": revision["id"],
                "revision_sha256": revision["revision_sha256"],
                "distinct_people": True,
                "approvals": approvals,
                "mode": mode,
                "notice": "Aprobaciones sintéticas para demostración; no acreditan revisión de un expediente real.",
            }
            approvals_path = staging / "APROBACIONES.json"
            approvals_path.write_text(json.dumps(approval_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append((approvals_path, "APROBACIONES.json"))
            manifest = {
                "schema": "legalaizit_m31_8_case_release_manifest_v1",
                "milestone": self.MILESTONE,
                "version": self.VERSION,
                "case_id": case_id,
                "product_code": case["product_code"],
                "revision_id": revision["id"],
                "revision_no": revision["revision_no"],
                "revision_sha256": revision["revision_sha256"],
                "document_set_sha256": revision["document_set_sha256"],
                "document_count": len(docs),
                "released_at": released_at,
                "released_by": actor_id,
                "production_authorized": False,
                "data_classification": "synthetic_no_real_personal_data",
                "files": file_rows,
            }
            certificate = staging / "CERTIFICADO_DE_LIBERACION.docx"
            self._release_certificate(certificate, case, revision, approvals, manifest)
            files.append((certificate, certificate.name))
            file_rows.append({"type": "release_certificate", "name": certificate.name, "sha256": self._hash(certificate), "size_bytes": certificate.stat().st_size})
            manifest_path = staging / "MANIFEST.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append((manifest_path, "MANIFEST.json"))
            checksum_path = staging / "SHA256SUMS.txt"
            checksum_path.write_text("\n".join(f"{self._hash(path)}  {arc}" for path, arc in sorted(files, key=lambda x: x[1])) + "\n", encoding="utf-8")
            files.append((checksum_path, "SHA256SUMS.txt"))
            package_name = self._safe(f"LegalAIZit_{case_id}_{case['product_code']}_FINAL_DEMO_R{revision['revision_no']:03d}_v{self.VERSION}.zip")
            package = staging / package_name
            self._write_zip(package, files)
            if release_root.exists():
                shutil.rmtree(release_root)
            release_root.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(release_root)
            package = release_root / package_name
            package_hash = self._hash(package)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        con.execute(
            "UPDATE m31_8_demo_runs SET workflow_status='Liberado para demostración',released_revision_id=?,package_path=?,package_sha256=?,updated_at=? WHERE id=?",
            (revision["id"], str(package), package_hash, released_at, run["id"]),
        )
        con.execute("UPDATE m31_8_demo_revisions SET status='Liberado para demostración' WHERE id=?", (revision["id"],))
        con.execute("UPDATE m31_8_demo_documents SET status='Final demo liberado' WHERE revision_id=?", (revision["id"],))
        con.execute("UPDATE documents SET status='Final demo liberado',updated_at=? WHERE case_id=? AND kind LIKE 'm31_8:%'", (released_at, case_id))
        con.execute("UPDATE cases SET status='Liberado para demostración',review_status='Aprobado jurídicamente y por QA',updated_at=? WHERE id=?", (released_at, case_id))
        con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Liberar paquete final trazable'", (released_at, case_id))
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "m31_8_release", f"Paquete final liberado con {len(docs)} documentos y hash {package_hash[:12]}…", released_at),
        )
        self._event(con, run["id"], case_id, actor_id, "package_released", {
            "revision_id": revision["id"], "package_sha256": package_hash, "documents": len(docs), "mode": mode,
        })
        self.audit(con, actor_id, "m31_8_demo_case", case_id, "release", {
            "revision_id": revision["id"], "package_sha256": package_hash, "documents": len(docs), "mode": mode,
        })
        cohort_package = None
        released_count = con.execute(
            "SELECT COUNT(*) FROM m31_8_demo_runs WHERE workflow_status='Liberado para demostración' AND package_path IS NOT NULL"
        ).fetchone()[0]
        if int(released_count) == len(self.products):
            cohort_package = self.build_cohort_package(con)
        return {
            "ok": True,
            "case_id": case_id,
            "revision_id": revision["id"],
            "documents": len(docs),
            "package": {
                "name": package.name,
                "sha256": package_hash,
                "size_bytes": package.stat().st_size,
                "download_path": f"{case_id}/{package.relative_to(self.output_root / case_id).as_posix()}",
            },
            "cohort_package": cohort_package,
        }

    def bootstrap(self, con, actor: str, *, reset: bool = False, auto_release: bool = True) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Ya existe una preparación de expedientes demo en curso.")
        try:
            self.ensure_schema(con)
            if reset:
                self._reset_unlocked(con, actor)
            for code in sorted(self.products):
                answers = dict(self.answer_source.answers_for_product(code))
                if code == "CO-LA-002":
                    answers.update({
                        "weekly_hours": 44,
                        "max_daily_hours": 8,
                        "planned_overtime_daily": 2,
                        "planned_overtime_weekly": 8,
                        "probation": "Sí",
                        "probation_months": 2,
                    })
                result = self.diagnose(code, answers, strict=True)
                errors = result.get("validation_errors") or []
                if errors:
                    raise ValueError(f"Datos demo inválidos para {code}: {'; '.join(x['message'] for x in errors)}")
                run_id, case_id = self._create_case_record(con, code, answers, result, actor)
                run = con.execute("SELECT active_revision_id FROM m31_8_demo_runs WHERE id=?", (run_id,)).fetchone()
                if not run["active_revision_id"]:
                    self._generate_revision(con, run_id, case_id, code, answers, result, actor, "Revisión inicial sintética M31.8")
                if auto_release:
                    current = con.execute("SELECT workflow_status FROM m31_8_demo_runs WHERE id=?", (run_id,)).fetchone()
                    if current["workflow_status"] == "Pendiente de revisión jurídica":
                        self._approval(con, run_id, "legal", self._specialist_for(code), "approve", "Revisión jurídica sintética aprobada para mostrar el flujo integral.", "seeded_demo")
                    current = con.execute("SELECT workflow_status FROM m31_8_demo_runs WHERE id=?", (run_id,)).fetchone()
                    if current["workflow_status"] == "Pendiente de QA independiente":
                        self._approval(con, run_id, "qa", "USR-ADMIN", "approve", "QA sintético aprobado sobre la misma revisión y hash.", "seeded_demo")
                    current = con.execute("SELECT workflow_status FROM m31_8_demo_runs WHERE id=?", (run_id,)).fetchone()
                    if current["workflow_status"] == "Aprobado para liberación":
                        self.release(con, case_id, "USR-ADMIN", mode="seeded_demo")
            con.commit()
            return self.summary(con)
        finally:
            self._lock.release()

    def revise(self, con, case_id: str, actor_id: str, answers_patch: dict[str, Any], note: str) -> dict[str, Any]:
        self.ensure_schema(con)
        actor = self._actor(con, actor_id)
        if actor["role"] not in {"client", "specialist", "admin"}:
            raise PermissionError("El usuario no puede editar el expediente.")
        run = con.execute("SELECT * FROM m31_8_demo_runs WHERE case_id=?", (case_id,)).fetchone()
        if not run:
            raise ValueError("Expediente demo no encontrado.")
        revision = con.execute("SELECT * FROM m31_8_demo_revisions WHERE id=?", (run["active_revision_id"],)).fetchone()
        answers = json.loads(revision["answers_json"])
        allowed = {q["id"] for q in self.interviews.get(run["product_code"], {}).get("questions", [])}
        unknown = sorted(set(answers_patch or {}) - allowed)
        if unknown:
            raise ValueError("Campos no reconocidos: " + ", ".join(unknown))
        for key, value in (answers_patch or {}).items():
            if value not in (None, ""):
                answers[key] = value
        result = self.diagnose(run["product_code"], answers, strict=True)
        errors = result.get("validation_errors") or []
        if errors:
            raise ValueError("; ".join(x["message"] for x in errors))
        generated = self._generate_revision(
            con, run["id"], case_id, run["product_code"], answers, result, actor_id,
            note.strip() or "Ajuste controlado de datos del expediente",
        )
        con.commit()
        return generated

    def _reset_unlocked(self, con, actor: str) -> None:
        self.ensure_schema(con)
        case_rows = con.execute("SELECT case_id,id FROM m31_8_demo_runs").fetchall()
        case_ids = [row["case_id"] for row in case_rows]
        con.execute("DELETE FROM m31_8_demo_events")
        con.execute("DELETE FROM m31_8_demo_approvals")
        con.execute("DELETE FROM m31_8_demo_documents")
        con.execute("DELETE FROM m31_8_demo_revisions")
        con.execute("DELETE FROM m31_8_demo_runs")
        for case_id in case_ids:
            con.execute("DELETE FROM document_versions WHERE document_id IN (SELECT id FROM documents WHERE case_id=? AND kind LIKE 'm31_8:%')", (case_id,))
            con.execute("DELETE FROM documents WHERE case_id=? AND kind LIKE 'm31_8:%'", (case_id,))
            con.execute("DELETE FROM case_tasks WHERE case_id=?", (case_id,))
            con.execute("DELETE FROM activity WHERE case_id=?", (case_id,))
            con.execute("DELETE FROM reviews WHERE case_id=?", (case_id,))
            con.execute("DELETE FROM cases WHERE id=?", (case_id,))
        shutil.rmtree(self.output_root, ignore_errors=True)
        self.audit(con, actor, "m31_8_demo", "cohort", "reset", {"cases": len(case_ids)})

    def reset(self, con, actor: str) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Ya existe una operación demo en curso.")
        try:
            self._reset_unlocked(con, actor)
            con.commit()
            return {"ok": True, "cases_removed": 11}
        finally:
            self._lock.release()

    def _run_public(self, con, row) -> dict[str, Any]:
        run = dict(row)
        case = self._row(con.execute("SELECT * FROM cases WHERE id=?", (run["case_id"],)).fetchone())
        revision = self._row(con.execute("SELECT * FROM m31_8_demo_revisions WHERE id=?", (run["active_revision_id"],)).fetchone())
        approvals = [dict(x) for x in con.execute(
            "SELECT a.*,u.name actor_name FROM m31_8_demo_approvals a LEFT JOIN users u ON u.id=a.actor_id WHERE a.run_id=? AND a.revision_id=? ORDER BY CASE a.approval_type WHEN 'legal' THEN 1 ELSE 2 END",
            (run["id"], run["active_revision_id"]),
        ).fetchall()]
        docs = [dict(x) for x in con.execute(
            "SELECT id,template_id,title,file_name,sha256,size_bytes,status FROM m31_8_demo_documents WHERE revision_id=? ORDER BY template_id",
            (run["active_revision_id"],),
        ).fetchall()]
        answers = json.loads(revision["answers_json"]) if revision else {}
        package = None
        if run.get("package_path"):
            path = Path(run["package_path"])
            if path.is_file():
                package = {
                    "name": path.name,
                    "sha256": run["package_sha256"],
                    "size_bytes": path.stat().st_size,
                    "download_path": f"{run['case_id']}/{path.relative_to(self.output_root / run['case_id']).as_posix()}",
                }
        return {
            "run_id": run["id"],
            "case_id": run["case_id"],
            "product_code": run["product_code"],
            "title": case["title"] if case else self.products[run["product_code"]].get("title"),
            "risk": case["risk"] if case else None,
            "workflow_status": run["workflow_status"],
            "review_status": case["review_status"] if case else None,
            "revision": {
                "id": revision["id"], "number": revision["revision_no"],
                "sha256": revision["revision_sha256"], "document_set_sha256": revision["document_set_sha256"],
                "status": revision["status"], "change_note": revision["change_note"], "created_at": revision["created_at"],
            } if revision else None,
            "documents": docs,
            "document_count": len(docs),
            "approvals": approvals,
            "legal_reviewer_id": run["legal_reviewer_id"],
            "qa_reviewer_id": run["qa_reviewer_id"],
            "editable_fields": self._editable_fields(run["product_code"], answers),
            "package": package,
            "updated_at": run["updated_at"],
        }

    def summary(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        rows = con.execute("SELECT * FROM m31_8_demo_runs ORDER BY product_code").fetchall()
        cases = [self._run_public(con, row) for row in rows]
        cohort_path = self._cohort_package_path()
        cohort_package = None
        if cohort_path.is_file():
            cohort_package = {
                "name": cohort_path.name,
                "sha256": self._hash(cohort_path),
                "size_bytes": cohort_path.stat().st_size,
                "download_path": cohort_path.name,
                "case_count": 11,
                "document_count": 76,
            }
        return {
            "schema": self.SCHEMA,
            "milestone": self.MILESTONE,
            "version": self.VERSION,
            "status": "ready" if len(cases) == len(self.products) else "not_prepared",
            "production_authorized": False,
            "data_classification": "synthetic_no_real_personal_data",
            "metrics": {
                "cases": len(cases),
                "products": len({row["product_code"] for row in cases}),
                "documents": sum(row["document_count"] for row in cases),
                "released_cases": sum(row["workflow_status"] == "Liberado para demostración" for row in cases),
                "dual_approved_cases": sum(len([a for a in row["approvals"] if a["decision"] == "approve"]) == 2 for row in cases),
                "unresolved_documents": 0,
            },
            "cases": cases,
            "cohort_package": cohort_package,
            "credentials": {
                "client": "juan@demo.legalaiz.it",
                "labor_specialist": "maria@demo.legalaiz.it",
                "contracts_specialist": "carlos@demo.legalaiz.it",
                "transit_specialist": "laura@demo.legalaiz.it",
                "qa_admin": "ana@demo.legalaiz.it",
                "password": "LegalAIZDemo2026!",
            },
            "notice": "Los expedientes, personas, aprobaciones y soportes de esta cohorte son sintéticos. El flujo demuestra controles reales, pero no autoriza uso sobre casos de terceros.",
        }

    def detail(self, con, case_id: str) -> dict[str, Any] | None:
        self.ensure_schema(con)
        row = con.execute("SELECT * FROM m31_8_demo_runs WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        result = self._run_public(con, row)
        result["events"] = [dict(x) for x in con.execute(
            "SELECT actor_id,event_type,detail_json,previous_hash,event_hash,created_at FROM m31_8_demo_events WHERE run_id=? ORDER BY id DESC",
            (row["id"],),
        ).fetchall()]
        result["revisions"] = [dict(x) for x in con.execute(
            "SELECT id,revision_no,answers_sha256,document_set_sha256,revision_sha256,status,change_note,created_by,created_at FROM m31_8_demo_revisions WHERE run_id=? ORDER BY revision_no DESC",
            (row["id"],),
        ).fetchall()]
        return result

    def file_path(self, relative: str) -> Path | None:
        if not relative:
            return None
        candidate = (self.output_root / relative).resolve()
        try:
            candidate.relative_to(self.output_root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def verify(self, con) -> dict[str, Any]:
        self.ensure_schema(con)
        failures: list[dict[str, Any]] = []
        checked = 0
        for row in con.execute("SELECT case_id,package_path,package_sha256 FROM m31_8_demo_runs ORDER BY product_code").fetchall():
            docs = con.execute(
                "SELECT d.file_name,d.file_path,d.sha256 FROM m31_8_demo_documents d JOIN m31_8_demo_runs r ON r.active_revision_id=d.revision_id WHERE r.case_id=?",
                (row["case_id"],),
            ).fetchall()
            for doc in docs:
                checked += 1
                path = Path(doc["file_path"])
                if not path.is_file():
                    failures.append({"case_id": row["case_id"], "file": doc["file_name"], "error": "missing"})
                elif self._hash(path) != doc["sha256"]:
                    failures.append({"case_id": row["case_id"], "file": doc["file_name"], "error": "hash_mismatch"})
                elif self._docx_sentinels(path):
                    failures.append({"case_id": row["case_id"], "file": doc["file_name"], "error": "unresolved_sentinel"})
            if row["package_path"]:
                checked += 1
                package = Path(row["package_path"])
                if not package.is_file():
                    failures.append({"case_id": row["case_id"], "file": package.name, "error": "missing_package"})
                elif self._hash(package) != row["package_sha256"]:
                    failures.append({"case_id": row["case_id"], "file": package.name, "error": "package_hash_mismatch"})
                else:
                    try:
                        with ZipFile(package) as archive:
                            bad = archive.testzip()
                            names = set(archive.namelist())
                        if bad:
                            failures.append({"case_id": row["case_id"], "file": package.name, "error": f"zip_error:{bad}"})
                        for required in {"MANIFEST.json", "SHA256SUMS.txt", "EXPEDIENTE.json", "APROBACIONES.json", "CERTIFICADO_DE_LIBERACION.docx"} - names:
                            failures.append({"case_id": row["case_id"], "file": package.name, "error": f"missing:{required}"})
                    except Exception as exc:
                        failures.append({"case_id": row["case_id"], "file": package.name, "error": str(exc)})
        cohort = self._cohort_package_path()
        if cohort.is_file():
            checked += 1
            try:
                with ZipFile(cohort) as archive:
                    bad = archive.testzip()
                    names = set(archive.namelist())
                    manifest = json.loads(archive.read("MANIFEST_COHORTE.json"))
                if bad:
                    failures.append({"case_id": "cohort", "file": cohort.name, "error": f"zip_error:{bad}"})
                if manifest.get("case_count") != 11 or manifest.get("active_document_count") != 76:
                    failures.append({"case_id": "cohort", "file": cohort.name, "error": "invalid_metrics"})
                if len([name for name in names if name.startswith("expedientes/") and name.endswith(".zip")]) != 11:
                    failures.append({"case_id": "cohort", "file": cohort.name, "error": "invalid_case_package_count"})
            except Exception as exc:
                failures.append({"case_id": "cohort", "file": cohort.name, "error": str(exc)})
        else:
            failures.append({"case_id": "cohort", "file": cohort.name, "error": "missing_cohort_package"})
        summary = self.summary(con)
        return {
            "ok": not failures and summary["metrics"]["cases"] == 11 and summary["metrics"]["documents"] == 76 and summary["metrics"]["released_cases"] == 11,
            "checked": checked,
            "failures": failures,
            "metrics": summary["metrics"],
        }
