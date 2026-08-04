from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


GEN_RE = re.compile(r"COLA002-[A-F0-9]{12}")


class CoLa002GovernanceV240:
    """Immutable revision and dual-approval workflow for CO-LA-002 generations."""

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

    def _folder(self, generation_id: str):
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

    def _events_path(self, generation_id):
        return self._folder(generation_id) / "audit_events.jsonl"

    def _event(self, generation_id, actor, action, details):
        path = self._events_path(generation_id)
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

    def _revision_dir(self, generation_id):
        p = self._folder(generation_id) / "revisions"
        p.mkdir(exist_ok=True)
        return p

    def _revision_files(self, generation_id):
        return sorted(self._revision_dir(generation_id).glob("revision-*.json"))

    def _load_revision(self, generation_id, revision_number):
        path = self._revision_dir(generation_id) / f"revision-{int(revision_number):04d}.json"
        if not path.is_file():
            raise FileNotFoundError("Revisión no encontrada.")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data.get("revision_hash")
        check = dict(data); check.pop("revision_hash", None)
        if expected != self._hash_obj(check):
            raise ValueError("La revisión no supera la verificación de integridad.")
        return data

    def _rebuild_package(self, generation_id, approved=False):
        folder = self._folder(generation_id)
        suffix = "_APROBADO.zip" if approved else ".zip"
        target = self.output_dir / f"{generation_id}{suffix}"
        with ZipFile(target, "w", ZIP_DEFLATED) as zf:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(folder)))
        return target

    def register_generation(self, result: dict, answers: dict, actor: dict):
        generation_id = result["generation_id"]
        folder = self._folder(generation_id)
        answers_path = folder / "answers.json"
        if not answers_path.exists():
            answers_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self._revision_files(generation_id):
            manifest = self._load_manifest(generation_id)
            snapshot = {
                "generation_id": generation_id,
                "revision_number": 1,
                "created_at": self._now(),
                "created_by": {"id": actor.get("id"), "role": actor.get("role")},
                "base_revision": None,
                "change_note": "Generación documental inicial.",
                "answers": answers,
                "selected_blocks": manifest.get("selected_blocks", []),
                "documents": manifest.get("documents", []),
                "document_hashes": manifest.get("hashes", {}),
            }
            snapshot["revision_hash"] = self._hash_obj(snapshot)
            path = self._revision_dir(generation_id) / "revision-0001.json"
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest.update({
                "version": "2.40",
                "current_revision": 1,
                "revision_hash": snapshot["revision_hash"],
                "workflow_status": "pending_legal_review",
                "legal_approval": {"status": "pending"},
                "qa_approval": {"status": "pending"},
                "released": False,
            })
            self._save_manifest(generation_id, manifest)
            self._event(generation_id, actor, "generation_registered", {"revision": 1, "revision_hash": snapshot["revision_hash"]})
            package = self._rebuild_package(generation_id)
            manifest["package_filename"] = package.name
            manifest["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
            self._save_manifest(generation_id, manifest)
        return self.summary(generation_id)

    def summary(self, generation_id):
        manifest = self._load_manifest(generation_id)
        revisions = []
        for path in self._revision_files(generation_id):
            item = json.loads(path.read_text(encoding="utf-8"))
            revisions.append({k: item.get(k) for k in ("revision_number", "created_at", "created_by", "base_revision", "change_note", "revision_hash")})
        events = []
        ep = self._events_path(generation_id)
        if ep.exists():
            events = [json.loads(x) for x in ep.read_text(encoding="utf-8").splitlines() if x.strip()]
        return {"manifest": manifest, "revisions": revisions, "events": events, "version": "2.40"}

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
        previous = self._load_revision(generation_id, current)
        snapshot = {
            "generation_id": generation_id,
            "revision_number": new_number,
            "created_at": self._now(),
            "created_by": {"id": actor.get("id"), "role": actor.get("role")},
            "base_revision": current,
            "base_revision_hash": previous["revision_hash"],
            "change_note": str(change_note).strip(),
            "answers": answers,
            "selected_blocks": evaluation.get("blocks", []),
            "documents": evaluation.get("documents", []),
        }
        snapshot["revision_hash"] = self._hash_obj(snapshot)
        path = self._revision_dir(generation_id) / f"revision-{new_number:04d}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.update({
            "current_revision": new_number,
            "revision_hash": snapshot["revision_hash"],
            "workflow_status": "pending_legal_review",
            "legal_approval": {"status": "pending"},
            "qa_approval": {"status": "pending"},
            "released": False,
            "approved_package_filename": None,
            "approved_package_sha256": None,
        })
        self._save_manifest(generation_id, manifest)
        self._event(generation_id, actor, "revision_created", {"revision": new_number, "base_revision": current, "revision_hash": snapshot["revision_hash"]})
        self._rebuild_package(generation_id)
        return self.summary(generation_id)

    @staticmethod
    def _flatten(value, prefix=""):
        out = {}
        if isinstance(value, dict):
            for key in sorted(value):
                out.update(CoLa002GovernanceV240._flatten(value[key], f"{prefix}.{key}" if prefix else key))
        elif isinstance(value, list):
            out[prefix] = value
        else:
            out[prefix] = value
        return out

    def compare(self, generation_id, from_revision, to_revision):
        left = self._load_revision(generation_id, from_revision)
        right = self._load_revision(generation_id, to_revision)
        a = self._flatten(left.get("answers", {})); b = self._flatten(right.get("answers", {}))
        keys = sorted(set(a) | set(b))
        changes = []
        for key in keys:
            if a.get(key) != b.get(key):
                changes.append({"path": key, "before": a.get(key), "after": b.get(key)})
        return {
            "generation_id": generation_id,
            "from_revision": int(from_revision),
            "to_revision": int(to_revision),
            "changes": changes,
            "change_count": len(changes),
            "from_hash": left["revision_hash"],
            "to_hash": right["revision_hash"],
            "version": "2.40",
        }

    def approve(self, generation_id, approval_type, decision, comment, actor):
        manifest = self._load_manifest(generation_id)
        approval_type = str(approval_type or "").lower()
        decision = str(decision or "").lower()
        if approval_type not in ("legal", "qa"):
            raise ValueError("Tipo de aprobación inválido.")
        if decision not in ("approved", "rejected"):
            raise ValueError("Decisión inválida.")
        if not str(comment or "").strip():
            raise ValueError("La decisión debe incluir comentario.")
        role = actor.get("role")
        if approval_type == "legal" and role not in ("specialist", "admin"):
            raise PermissionError("La aprobación jurídica requiere especialista jurídico o administrador.")
        if approval_type == "qa" and role != "admin":
            raise PermissionError("La aprobación QA requiere rol administrador.")
        if approval_type == "qa" and manifest.get("legal_approval", {}).get("status") != "approved":
            raise ValueError("QA solo puede decidir después de la aprobación jurídica.")
        other = manifest.get("legal_approval" if approval_type == "qa" else "qa_approval", {})
        if decision == "approved" and other.get("status") == "approved" and other.get("actor_id") == actor.get("id"):
            raise ValueError("La aprobación dual exige actores diferentes.")
        record = {
            "status": decision,
            "actor_id": actor.get("id"),
            "actor_role": role,
            "timestamp": self._now(),
            "comment": str(comment).strip(),
            "revision": manifest.get("current_revision"),
            "revision_hash": manifest.get("revision_hash"),
        }
        manifest[f"{approval_type}_approval"] = record
        if decision == "rejected":
            manifest["workflow_status"] = f"{approval_type}_rejected"
            manifest["released"] = False
        elif approval_type == "legal":
            manifest["workflow_status"] = "pending_qa_review"
        else:
            manifest["workflow_status"] = "approved"
        self._save_manifest(generation_id, manifest)
        self._event(generation_id, actor, f"{approval_type}_{decision}", {"revision": manifest.get("current_revision"), "comment": record["comment"]})
        if manifest.get("legal_approval", {}).get("status") == "approved" and manifest.get("qa_approval", {}).get("status") == "approved":
            approved = self._rebuild_package(generation_id, approved=True)
            manifest["released"] = True
            manifest["workflow_status"] = "released"
            manifest["released_at"] = self._now()
            manifest["approved_package_filename"] = approved.name
            manifest["approved_package_sha256"] = hashlib.sha256(approved.read_bytes()).hexdigest()
            self._save_manifest(generation_id, manifest)
            self._event(generation_id, actor, "package_released", {"revision": manifest.get("current_revision"), "sha256": manifest["approved_package_sha256"]})
        return self.summary(generation_id)

    def approved_package_path(self, generation_id):
        manifest = self._load_manifest(generation_id)
        if not manifest.get("released"):
            return None
        path = self.output_dir / str(manifest.get("approved_package_filename") or "")
        return path if path.is_file() else None
