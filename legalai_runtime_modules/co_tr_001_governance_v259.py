from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from co_tr_001_governance_v258 import CoTr001GovernanceV258, GEN_RE


class CoTr001GovernanceV259(CoTr001GovernanceV258):
    """Gobierno documental de cierre con compuerta previa y posterior a liberación."""

    VERSION = "2.59"

    def __init__(self, root: Path, factory):
        super().__init__(root, factory)
        self.release_gate = None

    def bind_release_gate(self, release_gate) -> None:
        self.release_gate = release_gate

    def approve(
        self,
        generation_id: str,
        approval_type: str,
        decision: str,
        comment: str,
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        comment = str(comment or "").strip()
        if not comment:
            raise ValueError("Toda aprobación o rechazo debe incluir un comentario trazable.")

        if approval_type == "qa" and decision == "approved":
            if self.release_gate is None:
                raise ValueError("La compuerta de liberación no está vinculada.")
            pre = self.release_gate.pre_release(generation_id, actor)
            manifest = self._load_manifest(generation_id)
            manifest["release_gate"] = pre
            self._save_manifest(generation_id, manifest)
            if not pre.get("valid"):
                self._event(
                    generation_id,
                    actor,
                    "release_gate_blocked",
                    {"revision": manifest.get("current_revision"), "issues": pre.get("issues", [])},
                )
                raise ValueError("La compuerta previa bloqueó la liberación: %s" % "; ".join(pre.get("issues", [])))

        result = super().approve(generation_id, approval_type, decision, comment, actor)

        if approval_type == "qa" and decision == "approved":
            post = self.release_gate.post_release(generation_id)
            manifest = self._load_manifest(generation_id)
            manifest["release_gate_post"] = post
            if not post.get("valid"):
                manifest["released"] = False
                manifest["workflow_status"] = "release_gate_failed"
                self._save_manifest(generation_id, manifest)
                self._event(
                    generation_id,
                    actor,
                    "post_release_gate_failed",
                    {"revision": manifest.get("current_revision"), "issues": post.get("issues", [])},
                )
                raise ValueError("La verificación posterior a liberación falló: %s" % "; ".join(post.get("issues", [])))
            self._save_manifest(generation_id, manifest)
            self._event(
                generation_id,
                actor,
                "post_release_gate_passed",
                {"revision": manifest.get("current_revision"), "approved_package": post.get("approved_package")},
            )
            result = self.summary(generation_id)
        return result

    def _build_approved_package(self, generation_id: str) -> Path:
        folder = self._folder(generation_id)
        manifest = self._load_manifest(generation_id)
        revision = int(manifest["current_revision"])
        revision_dir = folder / "documents" / ("revision-%04d" % revision)
        target = self.output_dir / ("%s_APROBADO_R%04d.zip" % (generation_id, revision))
        temp = target.with_suffix(".zip.tmp")
        source_dir = self.root / "app" / "assets" / "advanced-legal-library" / "CO-TR-001"
        source_files = (
            "FUENTES_V259.json",
            "SOURCE_VERIFICATION_V259.json",
            "REGRESSION_MATRIX_V259.json",
            "GOBIERNO_V259.json",
        )
        with ZipFile(temp, "w", ZIP_DEFLATED) as zf:
            for path in sorted(revision_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname="documentos/" + path.name)
            zf.write(self._manifest_path(generation_id), arcname="manifest.json")
            zf.write(self._revision_path(generation_id, revision), arcname="revision-%04d.json" % revision)
            event_path = self._event_path(generation_id)
            if event_path.exists():
                zf.write(event_path, arcname="audit_events.jsonl")
            for name in source_files:
                path = source_dir / name
                if path.is_file():
                    zf.write(path, arcname="control_fuentes/" + name)
            closure = {
                "version": self.VERSION,
                "product_id": "CO-TR-001",
                "generation_id": generation_id,
                "revision": revision,
                "revision_hash": manifest.get("revision_hash"),
                "legal_approval": manifest.get("legal_approval"),
                "qa_approval": manifest.get("qa_approval"),
                "release_gate": manifest.get("release_gate"),
            }
            zf.writestr("closure_evidence.json", json.dumps(closure, ensure_ascii=False, indent=2))
        temp.replace(target)
        return target

    def verify_integrity(self, generation_id: str) -> dict[str, Any]:
        result = dict(super().verify_integrity(generation_id))
        issues = list(result.get("issues", []))
        manifest = self._load_manifest(generation_id)

        draft_name = str(manifest.get("package_filename") or "")
        draft_hash = manifest.get("package_sha256")
        if draft_name and draft_hash:
            draft_path = self.output_dir / draft_name
            if not draft_path.is_file():
                issues.append("Falta paquete borrador: %s" % draft_name)
            elif self._hash_file(draft_path) != draft_hash:
                issues.append("Hash del paquete borrador inválido.")

        if manifest.get("released"):
            approved_name = str(manifest.get("approved_package_filename") or "")
            approved_hash = manifest.get("approved_package_sha256")
            approved_path = self.output_dir / approved_name
            if not approved_name or not approved_path.is_file():
                issues.append("Falta paquete aprobado.")
            elif not approved_hash or self._hash_file(approved_path) != approved_hash:
                issues.append("Hash del paquete aprobado inválido.")

        result["issues"] = list(dict.fromkeys(issues))
        result["valid"] = not result["issues"]
        result["version"] = self.VERSION
        return result
