from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from co_tr_002_document_factory_v256 import SENTINEL_RE


class CoTr002ReleaseGateV256:
    VERSION = "2.56"

    def __init__(self, root: Path, evaluator, validation, governance=None):
        self.root = Path(root)
        self.evaluator = evaluator
        self.validation = validation
        self.governance = governance

    def bind_governance(self, governance) -> None:
        self.governance = governance

    def static(self) -> dict[str, Any]:
        validation = self.validation.summary()
        issues = list(validation.get("issues", []))
        if not getattr(self.evaluator, "BASE_AVAILABLE", False):
            issues.append("La base canónica v2.54 no está disponible en esta ejecución.")
        required_files = [
            "co_tr_002_v256.py",
            "co_tr_002_document_factory_v256.py",
            "co_tr_002_governance_v256.py",
            "co_tr_002_validation_v256.py",
            "co_tr_002_release_gate_v256.py",
            "co_tr_002_service_v256.py",
            "co_tr_002_api_v256.py",
        ]
        missing = [name for name in required_files if not (self.root / name).is_file()]
        issues.extend(f"Falta archivo de cierre: {name}" for name in missing)
        return {
            "version": self.VERSION,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": issues,
            "validation": validation,
            "base_v254_available": bool(getattr(self.evaluator, "BASE_AVAILABLE", False)),
        }

    def _document_checks(self, generation_id: str, revision: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if self.governance is None:
            return ["La compuerta no está vinculada al gobierno documental."]
        folder = self.governance._folder(generation_id) / revision["document_folder"]
        for filename in revision.get("documents", []):
            path = folder / filename
            if not path.is_file():
                issues.append(f"Falta documento de revisión: {filename}")
                continue
            if path.suffix.lower() != ".docx":
                issues.append(f"Formato documental no permitido: {filename}")
                continue
            try:
                with ZipFile(path) as zf:
                    if zf.testzip() is not None or "word/document.xml" not in zf.namelist():
                        issues.append(f"Estructura OOXML inválida: {filename}")
                        continue
                    xml = "\n".join(
                        zf.read(name).decode("utf-8", errors="ignore")
                        for name in zf.namelist()
                        if name.endswith(".xml")
                    )
                    if SENTINEL_RE.search(xml):
                        issues.append(f"Marcador no resuelto en {filename}")
                    if "BORRADOR CONTROLADO" not in xml:
                        issues.append(f"Falta advertencia de borrador controlado en {filename}")
            except Exception as exc:
                issues.append(f"No fue posible revisar {filename}: {exc}")
        return issues

    def pre_release(self, generation_id: str, qa_actor: dict[str, Any]) -> dict[str, Any]:
        if self.governance is None:
            return {"version": self.VERSION, "valid": False, "status": "blocked", "issues": ["Gobierno no vinculado."]}
        issues: list[str] = []
        static = self.static()
        issues.extend(static.get("issues", []))
        summary = self.governance.summary(generation_id)
        manifest = summary["manifest"]
        current = int(manifest.get("current_revision") or 1)
        if manifest.get("release_blockers"):
            issues.extend(str(item) for item in manifest.get("release_blockers", []))
        legal = manifest.get("legal_approval", {})
        if legal.get("status") != "approved" or legal.get("revision") != current:
            issues.append("No existe aprobación jurídica vigente para la revisión actual.")
        if legal.get("revision_hash") != manifest.get("revision_hash"):
            issues.append("La aprobación jurídica no corresponde al hash vigente.")
        if str(legal.get("actor_id")) == str(qa_actor.get("id")):
            issues.append("La persona QA coincide con quien aprobó jurídicamente.")
        if qa_actor.get("role") not in ("qa", "admin"):
            issues.append("El actor propuesto no tiene rol QA.")

        integrity = self.governance.verify_integrity(generation_id)
        if not integrity.get("valid"):
            issues.extend(integrity.get("issues", []))
        try:
            revision = self.governance._load_revision(generation_id, current)
            issues.extend(self._document_checks(generation_id, revision))
        except Exception as exc:
            issues.append(f"No fue posible revisar la revisión vigente: {exc}")

        return {
            "version": self.VERSION,
            "generation_id": generation_id,
            "revision": current,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": list(dict.fromkeys(issues)),
            "integrity": integrity,
            "source_control": self.validation.validate_sources(),
            "checks": [
                "base_v254",
                "closure_validation",
                "source_freshness",
                "no_release_blockers",
                "current_legal_approval",
                "independent_qa",
                "revision_and_audit_integrity",
                "docx_structure",
                "no_unresolved_markers",
            ],
        }

    def post_release(self, generation_id: str) -> dict[str, Any]:
        if self.governance is None:
            return {"version": self.VERSION, "valid": False, "status": "blocked", "issues": ["Gobierno no vinculado."]}
        manifest = self.governance._load_manifest(generation_id)
        issues: list[str] = []
        if not manifest.get("released"):
            issues.append("El manifiesto no registra liberación.")
        if manifest.get("workflow_status") != "approved":
            issues.append("El flujo no quedó en estado aprobado.")
        gate = manifest.get("release_gate", {})
        if gate.get("valid") is not True:
            issues.append("La compuerta previa no quedó aprobada.")
        integrity = self.governance.verify_integrity(generation_id)
        if not integrity.get("valid"):
            issues.extend(integrity.get("issues", []))
        package = self.governance.approved_package_path(generation_id)
        if package is None:
            issues.append("No existe paquete aprobado verificable.")
        else:
            try:
                with ZipFile(package) as zf:
                    names = set(zf.namelist())
                    if "manifest.json" not in names or not any(name.startswith("documentos/") for name in names):
                        issues.append("El paquete aprobado no contiene manifiesto y documentos.")
                    if "SOURCE_VERIFICATION_V256.json" not in names:
                        issues.append("El paquete aprobado no incluye el control de fuentes.")
            except Exception as exc:
                issues.append(f"Paquete aprobado inválido: {exc}")
        return {
            "version": self.VERSION,
            "generation_id": generation_id,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": list(dict.fromkeys(issues)),
            "integrity": integrity,
            "approved_package": package.name if package else None,
        }

    def report(self, generation_id: str | None = None) -> dict[str, Any]:
        if generation_id is None:
            return self.static()
        if self.governance is None:
            return {"version": self.VERSION, "valid": False, "issues": ["Gobierno no vinculado."]}
        manifest = self.governance._load_manifest(generation_id)
        return {
            "version": self.VERSION,
            "generation_id": generation_id,
            "released": bool(manifest.get("released")),
            "workflow_status": manifest.get("workflow_status"),
            "release_gate": manifest.get("release_gate"),
            "release_gate_post": manifest.get("release_gate_post"),
            "integrity": self.governance.verify_integrity(generation_id),
        }
