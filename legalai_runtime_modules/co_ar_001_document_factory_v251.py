from __future__ import annotations

from pathlib import Path

from co_ar_001_document_factory_v250 import CoAr001DocumentFactoryV250
from document_standard_v33 import audit_docx_legal_standard
from docx_builder import build_docx
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_contractual_adapters import compose_lease_m33


class CoAr001DocumentFactoryV251(CoAr001DocumentFactoryV250):
    """CO-AR-001 M33.0: recompone el contrato principal y conserva anexos/actas v2.50."""

    VERSION = "2.51"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-ar-001-v251"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _render_m33_primary(answers: dict, target: Path):
        composition = compose_lease_m33(answers)
        build_docx(
            target,
            composition["title"],
            composition["subtitle"],
            [
                ("Producto", "CO-AR-001"),
                ("Estándar documental", "M33.0"),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            composition["sections"],
            product_code="CO-AR-001",
            enforce_legal_standard=True,
        )

    def render_documents(self, answers, target_folder):
        evaluation, generated, hashes = super().render_documents(answers, target_folder)
        target_folder = Path(target_folder)
        primary = next((item for item in generated if item.get("id") == "DOC-AR-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-AR-001 M33.0 no encontró el contrato principal generado.")
        target = target_folder / primary["filename"]
        self._render_m33_primary(answers, target)

        quality = assert_docx_quality(target, expected_product="CO-AR-001")
        visual = assert_visual_structure(target, expected_product="CO-AR-001")
        standard = audit_docx_legal_standard(target)
        if not standard["valid"]:
            raise ValueError(f"CO-AR-001 no supera el estándar M33.0: {standard['findings']}")
        primary["quality"] = {
            "valid": quality["valid"],
            "warnings": quality["warnings"],
            "metrics": quality["metrics"],
        }
        primary["visual_preflight"] = {
            "valid": visual["valid"],
            "warnings": visual["warnings"],
            "metrics": visual["metrics"],
            "requires_human_visual_review": True,
        }
        primary["document_standard"] = self.DOCUMENT_STANDARD
        primary["m33_preflight"] = standard
        hashes[primary["filename"]] = quality["sha256"]
        return evaluation, generated, hashes
