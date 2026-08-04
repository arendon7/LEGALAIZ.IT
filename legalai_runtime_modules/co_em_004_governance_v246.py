from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


GEN_RE = re.compile(r"COEM004-[A-F0-9]{12}")


class CoEm004GovernanceV246:
    VERSION = "2.46"

    def __init__(self, root: Path, factory):
        self.root = Path(root)
        self.factory = factory
        self.output_dir = factory.output_dir

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash_obj(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _folder(self, generation_id):
        if not GEN_RE.fullmatch(generation_id or ""):
            raise ValueError("Identificador de generación inválido.")
        folder = self.output_dir / generation_id
        if not folder.is_dir():
            raise FileNotFoundError("Generación no encontrada.")
        return folder

    def _manifest_path(self, generation_id):
        return self._folder(generation_id) / "manifest.json"

    def _load_manifest(self, generation_id):
        return json.loads(self._manifest_path(generation_id).read_text(encoding="utf-8"))

    def _save_manifest(self, generation_id, manifest):
        path = self._manifest_path(generation_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _revisions_dir(self, generation_id):
        path = self._folder(generation_id) / "revisions"
        path.mkdir(exist_ok=True)
        return path

    def _revision_path(self, generation_id, number):
        return self._revisions_dir(generation_id) / f"revision-{int(number):04d}.json"

    def _load_revision(self, generation_id, number):
        path = self._revision_path(generation_id, number)
        if not path.is_file():
            raise FileNotFoundError("Revisión no encontrada.")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data.get("revision_hash")
        check = dict(data); check.pop("revision_hash", None)
        if expected != self._hash_obj(check):
            raise ValueError("La revisión no supera la verificación de integridad.")
        return data

    def _event_path(self, generation_id):
        return self._folder(generation_id) / "audit_events.jsonl"

    def _event(self, generation_id, actor, action, details):
        path = self._event_path(generation_id)
        previous_hash = "0" * 64
        if path.exists():
            lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
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

    def _snapshot(self, generation_id, revision_number, answers, actor, base_revision, change_note, evaluation, documents, hashes):
        snapshot = {
            "generation_id": generation_id,
            "revision_number": revision_number,
            "created_at": self._now(),
            "created_by": {"id": actor.get("id"), "role": actor.get("role")},
            "base_revision": base_revision,
            "change_note": change_note,
            "answers": answers,
            "selected_blocks": evaluation.get("blocks", []),
            "documents": documents,
            "document_hashes": hashes,
            "document_folder": f"documents/revision-{revision_number:04d}",
            "review_requirements": evaluation.get("review_requirements", []),
        }
        if base_revision:
            snapshot["base_revision_hash"] = self._load_revision(generation_id, base_revision)["revision_hash"]
        snapshot["revision_hash"] = self._hash_obj(snapshot)
        return snapshot

    def _write_snapshot(self, generation_id, snapshot):
        path = self._revision_path(generation_id, snapshot["revision_number"])
        if path.exists():
            raise ValueError("La revisión ya existe y es inmutable.")
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    def _rebuild_draft_package(self, generation_id):
        folder = self._folder(generation_id)
        target = self.output_dir / f"{generation_id}.zip"
        with ZipFile(target, "w", ZIP_DEFLATED) as zf:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(folder)))
        return target

    def register_generation(self, result, answers, actor):
        generation_id = result["generation_id"]
        manifest = self._load_manifest(generation_id)
        if not self._revision_path(generation_id, 1).exists():
            evaluation = self.factory.evaluator.evaluate(answers)
            snapshot = self._snapshot(generation_id, 1, answers, actor, None, "Generación documental inicial.", evaluation, manifest.get("documents", []), manifest.get("hashes", {}))
            self._write_snapshot(generation_id, snapshot)
            manifest.update({
                "version": self.VERSION,
                "current_revision": 1,
                "revision_hash": snapshot["revision_hash"],
                "workflow_status": "pending_legal_review",
                "legal_approval": {"status": "pending"},
                "qa_approval": {"status": "pending"},
                "released": False,
            })
            self._save_manifest(generation_id, manifest)
            self._event(generation_id, actor, "generation_registered", {"revision": 1, "revision_hash": snapshot["revision_hash"]})
            package = self._rebuild_draft_package(generation_id)
            manifest["package_filename"] = package.name
            manifest["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
            self._save_manifest(generation_id, manifest)
        return self.summary(generation_id)

    def summary(self, generation_id):
        manifest = self._load_manifest(generation_id)
        revisions = []
        for path in sorted(self._revisions_dir(generation_id).glob("revision-*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            revisions.append({k: item.get(k) for k in ("revision_number", "created_at", "created_by", "base_revision", "change_note", "revision_hash", "document_folder")})
        events = []
        event_path = self._event_path(generation_id)
        if event_path.exists():
            events = [json.loads(x) for x in event_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return {"manifest": manifest, "revisions": revisions, "events": events, "version": self.VERSION}

    def create_revision(self, generation_id, answers, actor, base_revision, change_note):
        manifest = self._load_manifest(generation_id)
        current = int(manifest.get("current_revision") or 1)
        if int(base_revision or 0) != current:
            raise ValueError("La revisión base no coincide con la revisión vigente.")
        if not str(change_note or "").strip():
            raise ValueError("Debe indicar el motivo del cambio.")
        evaluation = self.factory.evaluator.evaluate(answers)
        if evaluation.get("blocked"):
            raise ValueError("La nueva revisión contiene bloqueos jurídicos.")
        if evaluation.get("missing_fields"):
            raise ValueError("La nueva revisión tiene datos esenciales pendientes.")
        new_number = current + 1
        target = self._folder(generation_id) / "documents" / f"revision-{new_number:04d}"
        evaluation, documents, hashes = self.factory.render_documents(answers, target)
        snapshot = self._snapshot(generation_id, new_number, answers, actor, current, str(change_note).strip(), evaluation, documents, hashes)
        self._write_snapshot(generation_id, snapshot)
        manifest.update({
            "current_revision": new_number,
            "revision_hash": snapshot["revision_hash"],
            "document_folder": snapshot["document_folder"],
            "documents": documents,
            "hashes": hashes,
            "selected_blocks": evaluation.get("blocks", []),
            "review_requirements": evaluation.get("review_requirements", []),
            "workflow_status": "pending_legal_review",
            "legal_approval": {"status": "pending"},
            "qa_approval": {"status": "pending"},
            "released": False,
            "approved_package_filename": None,
            "approved_package_sha256": None,
        })
        self._save_manifest(generation_id, manifest)
        self._event(generation_id, actor, "revision_created", {"revision": new_number, "base_revision": current, "revision_hash": snapshot["revision_hash"]})
        package = self._rebuild_draft_package(generation_id)
        manifest["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
        self._save_manifest(generation_id, manifest)
        return self.summary(generation_id)

    @staticmethod
    def _flatten(value, prefix=""):
        out = {}
        if isinstance(value, dict):
            for key in sorted(value):
                out.update(CoEm004GovernanceV246._flatten(value[key], f"{prefix}.{key}" if prefix else key))
        elif isinstance(value, list):
            out[prefix] = value
        else:
            out[prefix] = value
        return out

    def compare(self, generation_id, from_revision, to_revision):
        left = self._load_revision(generation_id, from_revision)
        right = self._load_revision(generation_id, to_revision)
        a = self._flatten(left.get("answers", {})); b = self._flatten(right.get("answers", {}))
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

    def approve(self, generation_id, approval_type, decision, comment, actor):
        if approval_type not in ("legal", "qa"):
            raise ValueError("Tipo de aprobación inválido.")
        if decision not in ("approved", "rejected"):
            raise ValueError("Decisión inválida.")
        if approval_type == "legal" and actor.get("role") not in ("specialist", "admin"):
            raise PermissionError("La aprobación jurídica requiere especialista o administrador.")
        if approval_type == "qa" and actor.get("role") != "admin":
            raise PermissionError("La aprobación QA requiere administrador.")
        manifest = self._load_manifest(generation_id)
        current = int(manifest.get("current_revision") or 1)
        key = "legal_approval" if approval_type == "legal" else "qa_approval"
        if approval_type == "qa":
            legal = manifest.get("legal_approval", {})
            if legal.get("status") != "approved" or legal.get("revision") != current:
                raise ValueError("QA requiere aprobación jurídica vigente de la revisión actual.")
            if str(legal.get("actor_id")) == str(actor.get("id")):
                raise ValueError("La misma persona no puede completar las dos aprobaciones.")
        record = {
            "status": decision,
            "revision": current,
            "actor_id": actor.get("id"),
            "actor_role": actor.get("role"),
            "timestamp": self._now(),
            "comment": str(comment or "").strip(),
            "revision_hash": manifest.get("revision_hash"),
        }
        manifest[key] = record
        if decision == "rejected":
            manifest["workflow_status"] = "rejected_legal" if approval_type == "legal" else "rejected_qa"
            manifest["released"] = False
        elif approval_type == "legal":
            manifest["workflow_status"] = "pending_qa_review"
            manifest["qa_approval"] = {"status": "pending"}
            manifest["released"] = False
        else:
            manifest["workflow_status"] = "approved"
            manifest["released"] = True
        self._save_manifest(generation_id, manifest)
        self._event(generation_id, actor, f"{approval_type}_{decision}", {"revision": current, "comment": record["comment"]})
        if manifest.get("released"):
            package = self._build_approved_package(generation_id)
            manifest["approved_package_filename"] = package.name
            manifest["approved_package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
            manifest["released_at"] = self._now()
            self._save_manifest(generation_id, manifest)
            self._event(generation_id, actor, "approved_package_released", {"revision": current, "sha256": manifest["approved_package_sha256"]})
        return self.summary(generation_id)

    def _build_approved_package(self, generation_id):
        folder = self._folder(generation_id)
        manifest = self._load_manifest(generation_id)
        revision = int(manifest["current_revision"])
        revision_dir = folder / "documents" / f"revision-{revision:04d}"
        target = self.output_dir / f"{generation_id}_APROBADO_R{revision:04d}.zip"
        with ZipFile(target, "w", ZIP_DEFLATED) as zf:
            for path in sorted(revision_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=f"documentos/{path.name}")
            zf.write(self._manifest_path(generation_id), arcname="manifest.json")
            zf.write(self._revision_path(generation_id, revision), arcname=f"revision-{revision:04d}.json")
            event_path = self._event_path(generation_id)
            if event_path.exists():
                zf.write(event_path, arcname="audit_events.jsonl")
        return target

    def approved_package_path(self, generation_id):
        manifest = self._load_manifest(generation_id)
        if not manifest.get("released"):
            return None
        path = self.output_dir / str(manifest.get("approved_package_filename") or "")
        return path if path.is_file() else None
