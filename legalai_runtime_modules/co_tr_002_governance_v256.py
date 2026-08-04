from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


GEN_RE = re.compile(r"COTR002-[A-F0-9]{12}")


class CoTr002GovernanceV256:
    VERSION = "2.56"

    def __init__(self, root: Path, factory, release_gate=None):
        self.root = Path(root)
        self.factory = factory
        self.output_dir = factory.output_dir
        self.release_gate = release_gate

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash_obj(value: Any) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _folder(self, generation_id: str) -> Path:
        if not GEN_RE.fullmatch(generation_id or ""):
            raise ValueError("Identificador de generación inválido.")
        folder = self.output_dir / generation_id
        if not folder.is_dir():
            raise FileNotFoundError("Generación no encontrada.")
        return folder

    def _manifest_path(self, generation_id: str) -> Path:
        return self._folder(generation_id) / "manifest.json"

    def _load_manifest(self, generation_id: str) -> dict[str, Any]:
        return json.loads(self._manifest_path(generation_id).read_text(encoding="utf-8"))

    def _save_manifest(self, generation_id: str, manifest: dict[str, Any]) -> None:
        path = self._manifest_path(generation_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _revisions_dir(self, generation_id: str) -> Path:
        path = self._folder(generation_id) / "revisions"
        path.mkdir(exist_ok=True)
        return path

    def _revision_path(self, generation_id: str, number: int) -> Path:
        return self._revisions_dir(generation_id) / f"revision-{int(number):04d}.json"

    def _load_revision(self, generation_id: str, number: int) -> dict[str, Any]:
        path = self._revision_path(generation_id, number)
        if not path.is_file():
            raise FileNotFoundError("Revisión no encontrada.")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data.get("revision_hash")
        check = dict(data)
        check.pop("revision_hash", None)
        if expected != self._hash_obj(check):
            raise ValueError("La revisión no supera la verificación de integridad.")
        return data

    def _event_path(self, generation_id: str) -> Path:
        return self._folder(generation_id) / "audit_events.jsonl"

    def _event(self, generation_id: str, actor: dict[str, Any], action: str, details: dict[str, Any]) -> dict[str, Any]:
        path = self._event_path(generation_id)
        previous_hash = "0" * 64
        if path.exists():
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                previous_hash = json.loads(lines[-1])["event_hash"]
        payload = {
            "generation_id": generation_id,
            "timestamp": self._now(),
            "actor": {"id": actor.get("id"), "role": actor.get("role")},
            "action": action,
            "details": details,
            "previous_hash": previous_hash,
        }
        payload["event_hash"] = self._hash_obj(payload)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return payload

    def _snapshot(
        self,
        generation_id: str,
        revision_number: int,
        answers: dict[str, Any],
        actor: dict[str, Any],
        base_revision: int | None,
        change_note: str,
        evaluation: dict[str, Any],
        documents: list[str],
        hashes: dict[str, str],
    ) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "generation_id": generation_id,
            "revision_number": revision_number,
            "created_at": self._now(),
            "created_by": {"id": actor.get("id"), "role": actor.get("role")},
            "base_revision": base_revision,
            "change_note": change_note,
            "answers": answers,
            "answers_hash": self._hash_obj(answers),
            "evaluation_hash": self._hash_obj(evaluation),
            "selected_blocks": evaluation.get("blocks", []),
            "documents": documents,
            "document_hashes": hashes,
            "document_folder": f"documents/revision-{revision_number:04d}",
            "review_requirements": evaluation.get("review_requirements", []),
            "release_blockers": evaluation.get("release_blockers", []),
            "decision_trace": evaluation.get("decision_trace", []),
        }
        if base_revision:
            snapshot["base_revision_hash"] = self._load_revision(generation_id, base_revision)["revision_hash"]
        snapshot["revision_hash"] = self._hash_obj(snapshot)
        return snapshot

    def _write_snapshot(self, generation_id: str, snapshot: dict[str, Any]) -> None:
        path = self._revision_path(generation_id, snapshot["revision_number"])
        if path.exists():
            raise ValueError("La revisión ya existe y es inmutable.")
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    def _rebuild_draft_package(self, generation_id: str) -> Path:
        folder = self._folder(generation_id)
        target = self.output_dir / f"{generation_id}.zip"
        manifest = self._load_manifest(generation_id)
        manifest["package_filename"] = target.name
        manifest["package_sha256"] = None
        self._save_manifest(generation_id, manifest)
        temp = target.with_suffix(".zip.tmp")
        with ZipFile(temp, "w", ZIP_DEFLATED) as zf:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(folder)))
        temp.replace(target)
        manifest["package_sha256"] = self._hash_file(target)
        self._save_manifest(generation_id, manifest)
        return target

    def register_generation(self, result: dict[str, Any], answers: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        generation_id = result["generation_id"]
        manifest = self._load_manifest(generation_id)
        if not self._revision_path(generation_id, 1).exists():
            evaluation = self.factory.evaluator.evaluate(answers)
            snapshot = self._snapshot(
                generation_id,
                1,
                answers,
                actor,
                None,
                "Generación documental inicial.",
                evaluation,
                manifest.get("documents", []),
                manifest.get("hashes", {}),
            )
            self._write_snapshot(generation_id, snapshot)
            manifest.update(
                {
                    "version": self.VERSION,
                    "current_revision": 1,
                    "revision_hash": snapshot["revision_hash"],
                    "workflow_status": "blocked_professional_review" if evaluation.get("release_blockers") else "pending_legal_review",
                    "legal_approval": {"status": "pending"},
                    "qa_approval": {"status": "pending"},
                    "released": False,
                    "release_gate": {"status": "pending"},
                }
            )
            self._save_manifest(generation_id, manifest)
            self._event(generation_id, actor, "generation_registered", {"revision": 1, "revision_hash": snapshot["revision_hash"]})
            self._rebuild_draft_package(generation_id)
        return self.summary(generation_id)

    def summary(self, generation_id: str) -> dict[str, Any]:
        manifest = self._load_manifest(generation_id)
        revisions = []
        for path in sorted(self._revisions_dir(generation_id).glob("revision-*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            revisions.append(
                {
                    key: item.get(key)
                    for key in (
                        "revision_number",
                        "created_at",
                        "created_by",
                        "base_revision",
                        "change_note",
                        "revision_hash",
                        "document_folder",
                    )
                }
            )
        events = []
        event_path = self._event_path(generation_id)
        if event_path.exists():
            events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {"manifest": manifest, "revisions": revisions, "events": events, "version": self.VERSION}

    def create_revision(
        self,
        generation_id: str,
        answers: dict[str, Any],
        actor: dict[str, Any],
        base_revision: int,
        change_note: str,
    ) -> dict[str, Any]:
        manifest = self._load_manifest(generation_id)
        current = int(manifest.get("current_revision") or 1)
        if int(base_revision or 0) != current:
            raise ValueError("La revisión base no coincide con la revisión vigente.")
        if not str(change_note or "").strip():
            raise ValueError("Debe indicar el motivo del cambio.")
        evaluation = self.factory.evaluator.evaluate(answers)
        if evaluation.get("missing_fields"):
            raise ValueError("La nueva revisión tiene datos esenciales pendientes.")
        new_number = current + 1
        target = self._folder(generation_id) / "documents" / f"revision-{new_number:04d}"
        evaluation, documents, hashes = self.factory.render_documents(answers, target, generation_id=generation_id)
        snapshot = self._snapshot(
            generation_id,
            new_number,
            answers,
            actor,
            current,
            str(change_note).strip(),
            evaluation,
            documents,
            hashes,
        )
        self._write_snapshot(generation_id, snapshot)
        manifest.update(
            {
                "current_revision": new_number,
                "revision_hash": snapshot["revision_hash"],
                "document_folder": snapshot["document_folder"],
                "documents": documents,
                "hashes": hashes,
                "selected_blocks": evaluation.get("blocks", []),
                "review_requirements": evaluation.get("review_requirements", []),
                "release_blockers": evaluation.get("release_blockers", []),
                "decision_trace": evaluation.get("decision_trace", []),
                "workflow_status": "blocked_professional_review" if evaluation.get("release_blockers") else "pending_legal_review",
                "legal_approval": {"status": "pending"},
                "qa_approval": {"status": "pending"},
                "release_gate": {"status": "pending"},
                "released": False,
                "approved_package_filename": None,
                "approved_package_sha256": None,
            }
        )
        self._save_manifest(generation_id, manifest)
        self._event(
            generation_id,
            actor,
            "revision_created",
            {"revision": new_number, "base_revision": current, "revision_hash": snapshot["revision_hash"]},
        )
        self._rebuild_draft_package(generation_id)
        return self.summary(generation_id)

    @staticmethod
    def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(value, dict):
            for key in sorted(value):
                out.update(CoTr002GovernanceV256._flatten(value[key], f"{prefix}.{key}" if prefix else key))
        elif isinstance(value, list):
            out[prefix] = value
        else:
            out[prefix] = value
        return out

    def compare(self, generation_id: str, from_revision: int, to_revision: int) -> dict[str, Any]:
        left = self._load_revision(generation_id, from_revision)
        right = self._load_revision(generation_id, to_revision)
        a = self._flatten(left.get("answers", {}))
        b = self._flatten(right.get("answers", {}))
        changes = []
        for path in sorted(set(a) | set(b)):
            if a.get(path) != b.get(path):
                changes.append({"path": path, "before": a.get(path), "after": b.get(path)})
        return {
            "generation_id": generation_id,
            "from_revision": int(from_revision),
            "to_revision": int(to_revision),
            "change_count": len(changes),
            "changes": changes,
            "document_changes": {"before": left.get("documents", []), "after": right.get("documents", [])},
        }

    def approve(
        self,
        generation_id: str,
        approval_type: str,
        decision: str,
        comment: str,
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        if approval_type not in ("legal", "qa"):
            raise ValueError("Tipo de aprobación inválido.")
        if decision not in ("approved", "rejected"):
            raise ValueError("Decisión inválida.")
        if not str(comment or "").strip():
            raise ValueError("La aprobación o rechazo requiere comentario trazable.")
        if approval_type == "legal" and actor.get("role") not in ("specialist_legal", "specialist", "admin"):
            raise PermissionError("La aprobación jurídica requiere especialista jurídico o administrador.")
        if approval_type == "qa" and actor.get("role") not in ("qa", "admin"):
            raise PermissionError("La aprobación QA requiere rol QA o administrador.")

        manifest = self._load_manifest(generation_id)
        current = int(manifest.get("current_revision") or 1)
        if decision == "approved" and manifest.get("release_blockers"):
            raise ValueError("No puede aprobarse para publicación mientras existan bloqueos de liberación.")

        key = "legal_approval" if approval_type == "legal" else "qa_approval"
        pre_release_report = None
        if approval_type == "qa" and decision == "approved":
            legal = manifest.get("legal_approval", {})
            if legal.get("status") != "approved" or legal.get("revision") != current:
                raise ValueError("QA requiere aprobación jurídica vigente de la revisión actual.")
            if str(legal.get("actor_id")) == str(actor.get("id")):
                raise ValueError("La misma persona no puede completar las dos aprobaciones.")
            if self.release_gate is not None:
                pre_release_report = self.release_gate.pre_release(generation_id, actor)
                if not pre_release_report.get("valid"):
                    raise ValueError("La compuerta de liberación detectó bloqueos: " + "; ".join(pre_release_report.get("issues", [])))

        record = {
            "status": decision,
            "revision": current,
            "actor_id": actor.get("id"),
            "actor_role": actor.get("role"),
            "timestamp": self._now(),
            "comment": str(comment).strip(),
            "revision_hash": manifest.get("revision_hash"),
        }
        manifest[key] = record
        if decision == "rejected":
            manifest["workflow_status"] = "rejected_legal" if approval_type == "legal" else "rejected_qa"
            manifest["released"] = False
            manifest["release_gate"] = {"status": "not_run"}
        elif approval_type == "legal":
            manifest["workflow_status"] = "pending_qa_review"
            manifest["qa_approval"] = {"status": "pending"}
            manifest["released"] = False
            manifest["release_gate"] = {"status": "pending"}
        else:
            manifest["workflow_status"] = "approved"
            manifest["released"] = True
            manifest["release_gate"] = pre_release_report or {"status": "passed", "valid": True}

        self._save_manifest(generation_id, manifest)
        self._event(generation_id, actor, f"{approval_type}_{decision}", {"revision": current, "comment": record["comment"]})

        if manifest.get("released"):
            package = self._build_approved_package(generation_id)
            manifest = self._load_manifest(generation_id)
            manifest["approved_package_filename"] = package.name
            manifest["approved_package_sha256"] = self._hash_file(package)
            manifest["released_at"] = self._now()
            self._save_manifest(generation_id, manifest)
            self._event(
                generation_id,
                actor,
                "approved_package_released",
                {"revision": current, "sha256": manifest["approved_package_sha256"]},
            )
            if self.release_gate is not None:
                post = self.release_gate.post_release(generation_id)
                manifest = self._load_manifest(generation_id)
                manifest["release_gate_post"] = post
                if not post.get("valid"):
                    manifest["released"] = False
                    manifest["workflow_status"] = "release_integrity_failed"
                self._save_manifest(generation_id, manifest)
        return self.summary(generation_id)

    def _build_approved_package(self, generation_id: str) -> Path:
        folder = self._folder(generation_id)
        manifest = self._load_manifest(generation_id)
        revision = int(manifest["current_revision"])
        revision_dir = folder / "documents" / f"revision-{revision:04d}"
        target = self.output_dir / f"{generation_id}_APROBADO_R{revision:04d}.zip"
        manifest["approved_package_filename"] = target.name
        manifest["approved_package_sha256"] = None
        self._save_manifest(generation_id, manifest)
        temp = target.with_suffix(".zip.tmp")
        with ZipFile(temp, "w", ZIP_DEFLATED) as zf:
            for path in sorted(revision_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=f"documentos/{path.name}")
            zf.write(self._manifest_path(generation_id), arcname="manifest.json")
            zf.write(self._revision_path(generation_id, revision), arcname=f"revision-{revision:04d}.json")
            event_path = self._event_path(generation_id)
            if event_path.exists():
                zf.write(event_path, arcname="audit_events.jsonl")
            source_control = self.root / "app" / "assets" / "advanced-legal-library" / "CO-TR-002" / "SOURCE_VERIFICATION_V256.json"
            if source_control.is_file():
                zf.write(source_control, arcname="SOURCE_VERIFICATION_V256.json")
        temp.replace(target)
        return target

    def approved_package_path(self, generation_id: str) -> Path | None:
        manifest = self._load_manifest(generation_id)
        if not manifest.get("released"):
            return None
        path = self.output_dir / str(manifest.get("approved_package_filename") or "")
        return path if path.is_file() else None

    def verify_integrity(self, generation_id: str) -> dict[str, Any]:
        manifest = self._load_manifest(generation_id)
        issues: list[str] = []
        current = int(manifest.get("current_revision") or 1)

        revisions: list[dict[str, Any]] = []
        for number in range(1, current + 1):
            try:
                revision = self._load_revision(generation_id, number)
                revisions.append(revision)
            except Exception as exc:
                issues.append(f"Revisión {number}: {exc}")
        for index, revision in enumerate(revisions):
            number = int(revision.get("revision_number") or 0)
            if index == 0:
                if revision.get("base_revision") not in (None, 0):
                    issues.append("La revisión inicial tiene base indebida.")
            else:
                previous = revisions[index - 1]
                if revision.get("base_revision") != previous.get("revision_number"):
                    issues.append(f"Cadena de revisiones rota en revisión {number}.")
                if revision.get("base_revision_hash") != previous.get("revision_hash"):
                    issues.append(f"Hash base inválido en revisión {number}.")

        revision = revisions[-1] if revisions else None
        if revision:
            if manifest.get("revision_hash") != revision.get("revision_hash"):
                issues.append("El hash de la revisión vigente no coincide con el manifiesto.")
            folder = self._folder(generation_id) / revision["document_folder"]
            for filename, expected in revision.get("document_hashes", {}).items():
                path = folder / filename
                if not path.is_file():
                    issues.append(f"Falta documento: {filename}")
                elif self._hash_file(path) != expected:
                    issues.append(f"Hash de documento inválido: {filename}")

        previous_hash = "0" * 64
        event_path = self._event_path(generation_id)
        if event_path.exists():
            for line_number, line in enumerate(event_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    issues.append(f"Evento de auditoría inválido en línea {line_number}.")
                    continue
                event_hash = event.pop("event_hash", None)
                if event.get("previous_hash") != previous_hash:
                    issues.append(f"Cadena de auditoría rota en línea {line_number}.")
                expected_hash = self._hash_obj(event)
                if event_hash != expected_hash:
                    issues.append(f"Hash de auditoría inválido en línea {line_number}.")
                previous_hash = event_hash or ""

        package_name = manifest.get("package_filename")
        package_hash = manifest.get("package_sha256")
        if package_name and package_hash:
            package_path = self.output_dir / str(package_name)
            if not package_path.is_file():
                issues.append("Falta el paquete borrador registrado.")
            elif self._hash_file(package_path) != package_hash:
                issues.append("Hash del paquete borrador inválido.")

        if manifest.get("released"):
            legal = manifest.get("legal_approval", {})
            qa = manifest.get("qa_approval", {})
            if legal.get("status") != "approved" or legal.get("revision") != current:
                issues.append("Aprobación jurídica no vigente.")
            if qa.get("status") != "approved" or qa.get("revision") != current:
                issues.append("Aprobación QA no vigente.")
            if legal.get("revision_hash") != manifest.get("revision_hash") or qa.get("revision_hash") != manifest.get("revision_hash"):
                issues.append("Una aprobación no corresponde al hash de la revisión vigente.")
            if str(legal.get("actor_id")) == str(qa.get("actor_id")):
                issues.append("La aprobación dual fue realizada por la misma persona.")
            approved_name = manifest.get("approved_package_filename")
            approved_hash = manifest.get("approved_package_sha256")
            approved_path = self.output_dir / str(approved_name or "")
            if not approved_path.is_file():
                issues.append("Falta el paquete aprobado.")
            elif approved_hash and self._hash_file(approved_path) != approved_hash:
                issues.append("Hash del paquete aprobado inválido.")

        return {
            "generation_id": generation_id,
            "valid": not issues,
            "issues": issues,
            "current_revision": current,
            "revisions_checked": len(revisions),
            "audit_events_checked": sum(1 for line in event_path.read_text(encoding="utf-8").splitlines() if line.strip()) if event_path.exists() else 0,
        }
