from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from zipfile import ZipFile

from co_tr_001_document_factory_v259 import SENTINEL_RE


class CoTr001ReleaseGateV259:
    VERSION = "2.59"
    PRODUCT_ID = "CO-TR-001"

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
            issues.append("La base canónica v2.58 no está disponible en esta ejecución.")
        required_files = [
            "co_tr_001_v259.py",
            "co_tr_001_document_factory_v259.py",
            "co_tr_001_governance_v259.py",
            "co_tr_001_validation_v259.py",
            "co_tr_001_release_gate_v259.py",
            "co_tr_001_service_v259.py",
            "co_tr_001_api_v259.py",
        ]
        missing = [name for name in required_files if not (self.root / name).is_file()]
        issues.extend("Falta archivo de cierre: %s" % name for name in missing)
        return {
            "version": self.VERSION,
            "product_id": self.PRODUCT_ID,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": list(dict.fromkeys(issues)),
            "validation": validation,
            "base_v258_available": bool(getattr(self.evaluator, "BASE_AVAILABLE", False)),
        }

    def _document_checks(self, generation_id: str, revision: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if self.governance is None:
            return ["La compuerta no está vinculada al gobierno documental."]
        folder = self.governance._folder(generation_id) / revision["document_folder"]
        for filename in revision.get("documents", []):
            path = folder / filename
            if not path.is_file():
                issues.append("Falta documento de revisión: %s" % filename)
                continue
            if path.suffix.lower() != ".docx":
                issues.append("Formato documental no permitido: %s" % filename)
                continue
            try:
                with ZipFile(path) as zf:
                    bad = zf.testzip()
                    if bad is not None or "word/document.xml" not in zf.namelist():
                        issues.append("Estructura OOXML inválida: %s" % filename)
                        continue
                    xml = "\n".join(
                        zf.read(name).decode("utf-8", errors="ignore")
                        for name in zf.namelist()
                        if name.endswith(".xml")
                    )
                    if SENTINEL_RE.search(xml):
                        issues.append("Marcador no resuelto en %s" % filename)
                    if "BORRADOR CONTROLADO" not in xml:
                        issues.append("Falta advertencia de borrador controlado en %s" % filename)
                    if "Versión 2.59" not in xml:
                        issues.append("El documento no identifica la versión 2.59: %s" % filename)
            except Exception as exc:
                issues.append("No fue posible revisar %s: %s" % (filename, exc))
        return issues

    def pre_release(self, generation_id: str, qa_actor: dict[str, Any]) -> dict[str, Any]:
        if self.governance is None:
            return {
                "version": self.VERSION,
                "valid": False,
                "status": "blocked",
                "issues": ["Gobierno no vinculado."],
            }
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

        source_control = self.validation.validate_sources()
        if not source_control.get("valid"):
            issues.extend(source_control.get("issues", []))
        if source_control.get("firm_decision_found"):
            issues.append("Se detectó una decisión firme no incorporada a la versión canónica.")

        integrity = self.governance.verify_integrity(generation_id)
        if not integrity.get("valid"):
            issues.extend(integrity.get("issues", []))
        try:
            revision = self.governance._load_revision(generation_id, current)
            issues.extend(self._document_checks(generation_id, revision))
        except Exception as exc:
            issues.append("No fue posible revisar la revisión vigente: %s" % exc)

        return {
            "version": self.VERSION,
            "generation_id": generation_id,
            "revision": current,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": list(dict.fromkeys(issues)),
            "integrity": integrity,
            "source_control": source_control,
            "checks": [
                "base_v258",
                "closure_validation",
                "source_freshness",
                "firm_decision_control",
                "no_release_blockers",
                "current_legal_approval",
                "independent_qa",
                "revision_and_audit_integrity",
                "docx_structure",
                "no_unresolved_markers",
                "version_identity",
            ],
        }

    def post_release(self, generation_id: str) -> dict[str, Any]:
        if self.governance is None:
            return {
                "version": self.VERSION,
                "valid": False,
                "status": "blocked",
                "issues": ["Gobierno no vinculado."],
            }
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
                    mandatory = {
                        "manifest.json",
                        "closure_evidence.json",
                        "control_fuentes/FUENTES_V259.json",
                        "control_fuentes/SOURCE_VERIFICATION_V259.json",
                        "control_fuentes/REGRESSION_MATRIX_V259.json",
                        "control_fuentes/GOBIERNO_V259.json",
                    }
                    missing = sorted(mandatory - names)
                    if missing:
                        issues.append("El paquete aprobado no contiene: %s" % ", ".join(missing))
                    if not any(name.startswith("documentos/") and name.endswith(".docx") for name in names):
                        issues.append("El paquete aprobado no contiene documentos DOCX.")
                    closure = json.loads(zf.read("closure_evidence.json").decode("utf-8"))
                    if closure.get("version") != self.VERSION:
                        issues.append("La evidencia de cierre no corresponde a v2.59.")
            except Exception as exc:
                issues.append("Paquete aprobado inválido: %s" % exc)
        return {
            "version": self.VERSION,
            "generation_id": generation_id,
            "valid": not issues,
            "status": "passed" if not issues else "blocked",
            "issues": list(dict.fromkeys(issues)),
            "integrity": integrity,
            "approved_package": package.name if package else None,
        }

    def report(self, generation_id: Optional[str] = None) -> dict[str, Any]:
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
