from __future__ import annotations

"""Control de revisión, aprobación dual y liberación de paquetes extensos v2.17.

La liberación creada por esta capa es únicamente para piloto controlado. No habilita
firma, publicación comercial ni uso profesional. Cada ciclo queda vinculado a una
versión y hash exactos del paquete consolidado y de su evidencia de generación.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import os
from typing import Any
from zipfile import ZipFile, ZIP_DEFLATED
import json
import shutil
import uuid

from extensive_generation_v216 import MATURE_PRODUCTS

VERSION = "2.17"
GENERATION_VERSION = "2.16"

LEGAL_DECISIONS = {"approve", "reject"}
QA_DECISIONS = {"approve", "reject"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()



def _runtime_root(project_root: Path) -> Path:
    raw = os.environ.get("LEGAL_RUNTIME_DIR", "").strip()
    path = Path(raw).expanduser() if raw else Path(project_root) / "runtime"
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()

class ExtensiveReviewV217:
    def __init__(self, root: Path, workspace):
        self.root = Path(root)
        self.workspace = workspace
        self.release_dir = _runtime_root(self.root) / "controlled_releases_v217"
        self.release_dir.mkdir(parents=True, exist_ok=True)

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS extensive_review_cycles(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              package_document_id TEXT NOT NULL,
              package_version TEXT NOT NULL,
              package_sha256 TEXT NOT NULL,
              proof_id TEXT NOT NULL,
              proof_sha256 TEXT NOT NULL,
              status TEXT NOT NULL,
              legal_actor TEXT,
              legal_decision TEXT,
              legal_comment TEXT,
              legal_at TEXT,
              qa_actor TEXT,
              qa_decision TEXT,
              qa_comment TEXT,
              qa_at TEXT,
              release_actor TEXT,
              release_comment TEXT,
              release_at TEXT,
              release_path TEXT,
              release_sha256 TEXT,
              certificate_path TEXT,
              certificate_sha256 TEXT,
              version INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(package_document_id) REFERENCES documents(id),
              UNIQUE(case_id,package_document_id,package_version,package_sha256)
            );
            CREATE INDEX IF NOT EXISTS idx_ext_review_case
              ON extensive_review_cycles(case_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ext_review_status
              ON extensive_review_cycles(status,updated_at DESC);

            CREATE TABLE IF NOT EXISTS extensive_review_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              cycle_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              previous_event_hash TEXT,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(cycle_id) REFERENCES extensive_review_cycles(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ext_review_events
              ON extensive_review_events(cycle_id,id);
            """
        )

    def _event(self, con, cycle_id: str, event_type: str, actor: str, role: str, detail: Any) -> str:
        raw = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, sort_keys=True)
        prev = con.execute(
            "SELECT event_hash FROM extensive_review_events WHERE cycle_id=? ORDER BY id DESC LIMIT 1",
            (cycle_id,),
        ).fetchone()
        previous = prev["event_hash"] if prev else ""
        created = _now()
        payload = "|".join([cycle_id, event_type, actor, role, created, previous, raw])
        digest = sha256(payload.encode("utf-8")).hexdigest()
        con.execute(
            """INSERT INTO extensive_review_events(
                 cycle_id,event_type,actor,actor_role,detail_json,previous_event_hash,event_hash,created_at
               ) VALUES(?,?,?,?,?,?,?,?)""",
            (cycle_id, event_type, actor, role, raw, previous or None, digest, created),
        )
        return digest

    @staticmethod
    def verify_chain(events: list[dict[str, Any]]) -> bool:
        previous = ""
        for event in sorted(events, key=lambda x: x["id"]):
            payload = "|".join([
                event["cycle_id"], event["event_type"], event["actor"], event["actor_role"],
                event["created_at"], previous, event["detail_json"],
            ])
            digest = sha256(payload.encode("utf-8")).hexdigest()
            if (event.get("previous_event_hash") or "") != previous or event.get("event_hash") != digest:
                return False
            previous = digest
        return True

    @staticmethod
    def _case(con, case_id: str):
        return con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()

    @staticmethod
    def _package(con, case_id: str):
        return con.execute(
            """SELECT * FROM documents WHERE case_id=? AND kind='consolidated_package'
               ORDER BY updated_at DESC LIMIT 1""",
            (case_id,),
        ).fetchone()

    @staticmethod
    def _proof(con, case_id: str):
        return con.execute(
            """SELECT * FROM extensive_generation_proofs WHERE case_id=?
               ORDER BY rowid DESC LIMIT 1""",
            (case_id,),
        ).fetchone()

    def _current_binding(self, con, case_id: str) -> dict[str, Any]:
        case = self._case(con, case_id)
        if not case:
            raise ValueError("Expediente no encontrado.")
        if case["product_code"] not in MATURE_PRODUCTS:
            raise ValueError("El producto aún no tiene generación documental extensa habilitada.")
        if case["risk"] == "red":
            raise ValueError("Los casos rojos no pueden entrar a liberación automática; requieren escalamiento profesional.")
        package = self._package(con, case_id)
        if not package:
            raise ValueError("El expediente no tiene paquete jurídico consolidado.")
        package_path = Path(package["file_path"] or "")
        if not package_path.is_file():
            raise ValueError("El archivo físico del paquete consolidado no está disponible.")
        proof_row = self._proof(con, case_id)
        if not proof_row:
            raise ValueError("No existe evidencia de generación para el paquete.")
        proof = json.loads(proof_row["proof_json"])
        if proof.get("status") != "Cobertura extensa verificada":
            raise ValueError("La evidencia de generación no acredita cobertura extensa completa.")
        if proof.get("metrics", {}).get("unresolved_markers", 0):
            raise ValueError("El paquete contiene marcadores pendientes.")
        proof_package = next((x for x in proof.get("documents", []) if x.get("kind") == "consolidated_package"), None)
        package_hash = _sha(package_path)
        if not proof_package or proof_package.get("id") != package["id"]:
            raise ValueError("La evidencia no corresponde al paquete consolidado actual.")
        if proof_package.get("sha256") != package_hash:
            raise ValueError("El paquete cambió después de generar la evidencia; debe regenerarse la evidencia.")
        proof_path = Path(proof_row["proof_path"] or "")
        if not proof_path.is_file():
            raise ValueError("El archivo físico de evidencia no está disponible.")
        return {
            "case": dict(case),
            "package": dict(package),
            "package_path": package_path,
            "package_sha256": package_hash,
            "proof": proof,
            "proof_row": dict(proof_row),
            "proof_path": proof_path,
        }

    def _mark_obsolete(self, con, case_id: str, package_hash: str, actor: str = "system") -> int:
        rows = con.execute(
            """SELECT * FROM extensive_review_cycles
               WHERE case_id=? AND package_sha256<>? AND status<>'Obsoleto por regeneración'""",
            (case_id, package_hash),
        ).fetchall()
        for row in rows:
            con.execute(
                "UPDATE extensive_review_cycles SET status='Obsoleto por regeneración',version=version+1,updated_at=? WHERE id=?",
                (_now(), row["id"]),
            )
            self._event(con, row["id"], "cycle_obsoleted", actor, "system", {
                "previous_package_sha256": row["package_sha256"], "current_package_sha256": package_hash,
            })
        return len(rows)

    def _ensure_tasks(self, con, case_id: str) -> None:
        tasks = [
            ("Revisión jurídica del paquete extenso", "specialist"),
            ("QA independiente del paquete extenso", "admin"),
            ("Liberación controlada para piloto", "admin"),
        ]
        position = con.execute("SELECT COALESCE(MAX(position),0) FROM case_tasks WHERE case_id=?", (case_id,)).fetchone()[0]
        for label, role in tasks:
            exists = con.execute("SELECT 1 FROM case_tasks WHERE case_id=? AND label=?", (case_id, label)).fetchone()
            if exists:
                continue
            position += 1
            now = _now()
            con.execute(
                "INSERT INTO case_tasks VALUES(?,?,?,?,?,?,?,?)",
                ("TSK-" + uuid.uuid4().hex[:8].upper(), case_id, label, "Pendiente" if role == "specialist" else "Bloqueada", role, position, now, now),
            )

    def ensure_cycle(self, con, case_id: str, actor: str, role: str) -> dict[str, Any]:
        self.create_schema(con)
        binding = self._current_binding(con, case_id)
        self._mark_obsolete(con, case_id, binding["package_sha256"], actor)
        row = con.execute(
            """SELECT * FROM extensive_review_cycles
               WHERE case_id=? AND package_document_id=? AND package_version=? AND package_sha256=?""",
            (case_id, binding["package"]["id"], binding["package"]["version"], binding["package_sha256"]),
        ).fetchone()
        if not row:
            cycle_id = "ERC-" + uuid.uuid4().hex[:12].upper()
            now = _now()
            con.execute(
                """INSERT INTO extensive_review_cycles(
                     id,case_id,product_code,package_document_id,package_version,package_sha256,
                     proof_id,proof_sha256,status,version,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,1,?,?)""",
                (
                    cycle_id, case_id, binding["case"]["product_code"], binding["package"]["id"],
                    binding["package"]["version"], binding["package_sha256"], binding["proof"]["proof_id"],
                    binding["proof"]["proof_sha256"], "Pendiente de revisión jurídica", now, now,
                ),
            )
            self._event(con, cycle_id, "cycle_started", actor, role, {
                "package_version": binding["package"]["version"],
                "package_sha256": binding["package_sha256"],
                "proof_id": binding["proof"]["proof_id"],
                "proof_sha256": binding["proof"]["proof_sha256"],
            })
            self._ensure_tasks(con, case_id)
        return self.detail(con, case_id)

    def _cycle(self, con, case_id: str):
        return con.execute(
            "SELECT * FROM extensive_review_cycles WHERE case_id=? ORDER BY rowid DESC LIMIT 1",
            (case_id,),
        ).fetchone()

    @staticmethod
    def _task_status(con, case_id: str, label: str, status: str) -> None:
        con.execute("UPDATE case_tasks SET status=?,updated_at=? WHERE case_id=? AND label=?", (status, _now(), case_id, label))

    def legal_decision(self, con, case_id: str, decision: str, actor: str, role: str, comment: str = "") -> dict[str, Any]:
        if role != "specialist":
            raise PermissionError("La revisión jurídica requiere un usuario especialista.")
        if decision not in LEGAL_DECISIONS:
            raise ValueError("Decisión jurídica inválida.")
        self.ensure_cycle(con, case_id, actor, role)
        row = self._cycle(con, case_id)
        if row["status"] in ("Liberado para piloto controlado", "Obsoleto por regeneración"):
            raise ValueError("El ciclo no admite nuevas decisiones.")
        now = _now()
        status = "En QA independiente" if decision == "approve" else "Requiere ajustes jurídicos"
        con.execute(
            """UPDATE extensive_review_cycles SET status=?,legal_actor=?,legal_decision=?,legal_comment=?,legal_at=?,
               qa_actor=NULL,qa_decision=NULL,qa_comment=NULL,qa_at=NULL,release_actor=NULL,release_comment=NULL,
               release_at=NULL,release_path=NULL,release_sha256=NULL,certificate_path=NULL,certificate_sha256=NULL,
               version=version+1,updated_at=? WHERE id=?""",
            (status, actor, decision, (comment or "").strip()[:4000], now, now, row["id"]),
        )
        self._event(con, row["id"], "legal_decision", actor, role, {"decision": decision, "comment": comment, "status": status})
        self._task_status(con, case_id, "Revisión jurídica del paquete extenso", "Completada" if decision == "approve" else "Requiere ajuste")
        self._task_status(con, case_id, "QA independiente del paquete extenso", "Pendiente" if decision == "approve" else "Bloqueada")
        self._task_status(con, case_id, "Liberación controlada para piloto", "Bloqueada")
        con.execute("UPDATE cases SET review_status=?,status=?,specialist_id=?,updated_at=? WHERE id=?", (
            "Revisión jurídica aprobada" if decision == "approve" else "Requiere ajuste jurídico",
            "En QA" if decision == "approve" else "Requiere ajuste", actor, now, case_id,
        ))
        return self.detail(con, case_id)

    def qa_decision(self, con, case_id: str, decision: str, actor: str, role: str, comment: str = "") -> dict[str, Any]:
        if role != "admin":
            raise PermissionError("La aprobación QA requiere administración independiente.")
        if decision not in QA_DECISIONS:
            raise ValueError("Decisión QA inválida.")
        self.ensure_cycle(con, case_id, actor, role)
        row = self._cycle(con, case_id)
        if row["legal_decision"] != "approve":
            raise ValueError("QA solo puede decidir después de la aprobación jurídica de la misma versión.")
        if row["status"] in ("Liberado para piloto controlado", "Obsoleto por regeneración"):
            raise ValueError("El ciclo no admite nuevas decisiones.")
        now = _now()
        status = "Listo para liberación controlada" if decision == "approve" else "Requiere ajustes QA"
        con.execute(
            """UPDATE extensive_review_cycles SET status=?,qa_actor=?,qa_decision=?,qa_comment=?,qa_at=?,
               release_actor=NULL,release_comment=NULL,release_at=NULL,release_path=NULL,release_sha256=NULL,
               certificate_path=NULL,certificate_sha256=NULL,version=version+1,updated_at=? WHERE id=?""",
            (status, actor, decision, (comment or "").strip()[:4000], now, now, row["id"]),
        )
        self._event(con, row["id"], "qa_decision", actor, role, {"decision": decision, "comment": comment, "status": status})
        self._task_status(con, case_id, "QA independiente del paquete extenso", "Completada" if decision == "approve" else "Requiere ajuste")
        self._task_status(con, case_id, "Liberación controlada para piloto", "Pendiente" if decision == "approve" else "Bloqueada")
        con.execute("UPDATE cases SET review_status=?,status=?,updated_at=? WHERE id=?", (
            "Aprobación dual completada" if decision == "approve" else "Requiere ajuste QA",
            "Listo para liberación" if decision == "approve" else "Requiere ajuste", now, case_id,
        ))
        return self.detail(con, case_id)

    def release(self, con, case_id: str, actor: str, role: str, comment: str = "") -> dict[str, Any]:
        if role != "admin":
            raise PermissionError("La liberación controlada requiere administración.")
        self.ensure_cycle(con, case_id, actor, role)
        binding = self._current_binding(con, case_id)
        row = self._cycle(con, case_id)
        if row["legal_decision"] != "approve" or row["qa_decision"] != "approve":
            raise ValueError("La liberación exige aprobación jurídica y QA de la misma versión.")
        if row["package_sha256"] != binding["package_sha256"] or row["proof_sha256"] != binding["proof"]["proof_sha256"]:
            raise ValueError("La versión aprobada ya no coincide con el paquete o la evidencia actuales.")
        if row["status"] == "Liberado para piloto controlado" and row["release_path"] and Path(row["release_path"]).is_file():
            return self.detail(con, case_id)

        cycle_dir = self.release_dir / row["id"]
        cycle_dir.mkdir(parents=True, exist_ok=True)
        package_copy = cycle_dir / binding["package_path"].name
        proof_copy = cycle_dir / binding["proof_path"].name
        shutil.copy2(binding["package_path"], package_copy)
        shutil.copy2(binding["proof_path"], proof_copy)
        certificate = {
            "certificate_id": "CERT-" + uuid.uuid4().hex[:12].upper(),
            "cycle_id": row["id"],
            "case_id": case_id,
            "product_code": row["product_code"],
            "release_type": "Piloto controlado interno",
            "professional_use_authorized": False,
            "signature_authorized": False,
            "commercial_publication_authorized": False,
            "package": {"document_id": row["package_document_id"], "version": row["package_version"], "sha256": row["package_sha256"], "filename": package_copy.name},
            "generation_proof": {"proof_id": row["proof_id"], "sha256": row["proof_sha256"], "generation_version": GENERATION_VERSION, "filename": proof_copy.name},
            "legal_approval": {"actor": row["legal_actor"], "decision": row["legal_decision"], "comment": row["legal_comment"], "at": row["legal_at"]},
            "qa_approval": {"actor": row["qa_actor"], "decision": row["qa_decision"], "comment": row["qa_comment"], "at": row["qa_at"]},
            "release": {"actor": actor, "comment": (comment or "").strip()[:4000], "at": _now()},
            "warning": "Esta liberación acredita controles internos del piloto. No sustituye validación normativa vigente, asesoría profesional, firma ni autorización de uso comercial.",
        }
        certificate_raw = json.dumps(certificate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        certificate["certificate_payload_sha256"] = sha256(certificate_raw).hexdigest()
        certificate_path = cycle_dir / f"{row['id']}_certificado_liberacion_controlada_v217.json"
        certificate_path.write_text(json.dumps(certificate, ensure_ascii=False, indent=2), encoding="utf-8")
        certificate_file_sha256 = _sha(certificate_path)

        release_path = cycle_dir / f"LegalAIZit_{row['product_code']}_{case_id}_piloto_controlado_v217.zip"
        with ZipFile(release_path, "w", ZIP_DEFLATED) as zf:
            zf.write(package_copy, arcname=f"documento/{package_copy.name}")
            zf.write(proof_copy, arcname=f"evidencia/{proof_copy.name}")
            zf.write(certificate_path, arcname=f"control/{certificate_path.name}")
        release_hash = _sha(release_path)
        now = _now()
        con.execute(
            """UPDATE extensive_review_cycles SET status='Liberado para piloto controlado',release_actor=?,release_comment=?,
               release_at=?,release_path=?,release_sha256=?,certificate_path=?,certificate_sha256=?,version=version+1,updated_at=?
               WHERE id=?""",
            (actor, (comment or "").strip()[:4000], now, str(release_path), release_hash, str(certificate_path), certificate_file_sha256, now, row["id"]),
        )
        self._event(con, row["id"], "controlled_release", actor, role, {
            "release_sha256": release_hash, "certificate_sha256": certificate_file_sha256,
            "professional_use_authorized": False,
        })
        self._task_status(con, case_id, "Liberación controlada para piloto", "Completada")
        con.execute("UPDATE documents SET status='Aprobación dual · piloto controlado',updated_at=? WHERE id=?", (now, row["package_document_id"]))
        con.execute("UPDATE cases SET review_status='Liberado para piloto controlado',status='Piloto interno listo',updated_at=? WHERE id=?", (now, case_id))
        con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (
            case_id, "release", f"Paquete {row['package_version']} liberado únicamente para piloto controlado. Hash {release_hash[:16]}…", now,
        ))
        return self.detail(con, case_id)

    def detail(self, con, case_id: str) -> dict[str, Any]:
        self.create_schema(con)
        package = self._package(con, case_id)
        if package and Path(package["file_path"] or "").is_file():
            self._mark_obsolete(con, case_id, _sha(Path(package["file_path"])), "system")
        row = self._cycle(con, case_id)
        history = [dict(x) for x in con.execute(
            "SELECT * FROM extensive_review_cycles WHERE case_id=? ORDER BY rowid DESC", (case_id,),
        ).fetchall()]
        events: list[dict[str, Any]] = []
        if row:
            events = [dict(x) for x in con.execute(
                "SELECT * FROM extensive_review_events WHERE cycle_id=? ORDER BY id", (row["id"],),
            ).fetchall()]
        versions = self.workspace.version_catalog(con, package["id"]) if package else []
        current = dict(row) if row else None
        if current:
            current["release_available"] = bool(current.get("release_path") and Path(current["release_path"]).is_file())
            current["certificate_available"] = bool(current.get("certificate_path") and Path(current["certificate_path"]).is_file())
        return {
            "version": VERSION,
            "case_id": case_id,
            "cycle": current,
            "history": history,
            "events": events,
            "event_chain_valid": self.verify_chain(events) if events else True,
            "package": ({k: package[k] for k in ("id", "name", "version", "status", "updated_at")} if package else None),
            "versions": versions,
            "controls": {
                "legal_role": "specialist",
                "qa_role": "admin",
                "same_revision_required": True,
                "hash_revalidation_on_release": True,
                "professional_use_authorized": False,
                "release_scope": "Piloto controlado interno",
            },
        }

    def summary(self, con) -> dict[str, Any]:
        self.create_schema(con)
        for item in con.execute("SELECT id FROM cases WHERE product_code IN ('CO-EM-003','CO-AR-001','CO-LA-002','CO-EM-004')").fetchall():
            package = self._package(con, item["id"])
            path = Path(package["file_path"] or "") if package else None
            if path and path.is_file():
                self._mark_obsolete(con, item["id"], _sha(path), "system")
        rows = [dict(x) for x in con.execute(
            """SELECT c.id case_id,c.product_code,c.title,c.risk,c.status case_status,c.review_status,
                      r.id cycle_id,r.status cycle_status,r.package_version,r.updated_at,r.release_sha256
               FROM cases c LEFT JOIN extensive_review_cycles r ON r.id=(
                 SELECT x.id FROM extensive_review_cycles x WHERE x.case_id=c.id ORDER BY x.rowid DESC LIMIT 1
               ) WHERE c.product_code IN ('CO-EM-003','CO-AR-001','CO-LA-002','CO-EM-004')
               ORDER BY c.updated_at DESC"""
        ).fetchall()]
        counts: dict[str, int] = {}
        for row in rows:
            key = row.get("cycle_status") or "Sin ciclo"
            counts[key] = counts.get(key, 0) + 1
        return {
            "version": VERSION,
            "title": "Revisión, aprobación dual y liberación controlada",
            "cases": rows,
            "metrics": {"cases": len(rows), "cycles": sum(bool(x.get("cycle_id")) for x in rows), "released": sum(x.get("cycle_status") == "Liberado para piloto controlado" for x in rows)},
            "status_counts": counts,
            "professional_use_authorized": False,
        }

    def _released_artifact(self, con, case_id: str, column: str) -> Path | None:
        package = self._package(con, case_id)
        if not package:
            return None
        package_path = Path(package["file_path"] or "")
        if not package_path.is_file():
            return None
        self._mark_obsolete(con, case_id, _sha(package_path), "system")
        row = self._cycle(con, case_id)
        if not row or row["status"] != "Liberado para piloto controlado":
            return None
        if row["package_sha256"] != _sha(package_path):
            return None
        path = Path(row[column] or "")
        return path if path.is_file() else None

    def release_path(self, con, case_id: str) -> Path | None:
        return self._released_artifact(con, case_id, "release_path")

    def certificate_path(self, con, case_id: str) -> Path | None:
        return self._released_artifact(con, case_id, "certificate_path")
