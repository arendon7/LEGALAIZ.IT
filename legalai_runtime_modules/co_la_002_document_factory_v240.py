from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239
from document_standard_v33 import audit_docx_legal_standard
from docx_builder import build_docx
from m33_contractual_adapters import compose_employment_m33


class CoLa002DocumentFactoryV240(CoLa002DocumentFactoryV239):
    """CO-LA-002 M33.0: conserva paquete v2.39 y recompone solo el contrato principal."""

    VERSION = "2.40"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-la-002-v240"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _contract(self, answers: dict, evaluation: dict, target: Path):
        composition = compose_employment_m33(answers)
        build_docx(
            target,
            composition["title"],
            composition["subtitle"],
            [
                ("Producto", "CO-LA-002"),
                ("Estándar documental", self.DOCUMENT_STANDARD),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            composition["sections"],
            product_code="CO-LA-002",
            enforce_legal_standard=True,
        )

    def generate(self, answers, actor=None):
        manifest = super().generate(answers, actor=actor)
        manifest["version"] = self.VERSION
        manifest["document_standard"] = self.DOCUMENT_STANDARD
        manifest["status"] = "draft_generated"
        manifest["released"] = False

        folder = self.output_dir / manifest["generation_id"]
        primary = next((item for item in manifest.get("documents", []) if item.get("id") == "DOC-LA-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-LA-002 M33.0 no encontró el contrato principal generado.")
        primary_path = folder / primary["filename"]
        standard = audit_docx_legal_standard(primary_path)
        if not standard["valid"]:
            raise ValueError(f"CO-LA-002 no supera el estándar M33.0: {standard['findings']}")
        primary["document_standard"] = self.DOCUMENT_STANDARD
        primary["m33_preflight"] = standard

        # Reescribe el manifiesto versionado y recompone el ZIP para que la evidencia
        # descargable corresponda a la fábrica M33.0, sin alterar el esquema histórico.
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package = self.output_dir / f"{manifest['generation_id']}.zip"
        with ZipFile(package, "w", ZIP_DEFLATED) as archive:
            for path in sorted(folder.iterdir()):
                if path.is_file():
                    archive.write(path, arcname=path.name)
        manifest["package_filename"] = package.name
        manifest["package_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
