from __future__ import annotations

from pathlib import Path

from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
from document_standard_v33 import audit_docx_legal_standard
from docx_builder import build_docx
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_contractual_adapters import compose_nda_m33


class CoEm004DocumentFactoryV248(CoEm004DocumentFactoryV247):
    """CO-EM-004 M33.0: recompone el NDA principal y preserva anexos/actas existentes."""

    VERSION = "2.48"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-em-004-v248"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _render_m33_primary(answers: dict, target: Path):
        composition = compose_nda_m33(answers)
        build_docx(
            target,
            composition["title"],
            composition["subtitle"],
            [
                ("Producto", "CO-EM-004"),
                ("Estándar documental", "M33.0"),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            composition["sections"],
            product_code="CO-EM-004",
            enforce_legal_standard=True,
        )

    def render_documents(self, answers, target_folder):
        evaluation, generated, hashes = super().render_documents(answers, target_folder)
        target_folder = Path(target_folder)
        primary = next((item for item in generated if item.get("id") == "DOC-EM4-NDA-001"), None)
        if not primary:
            raise RuntimeError("CO-EM-004 M33.0 no encontró el NDA principal generado.")
        target = target_folder / primary["filename"]
        self._render_m33_primary(answers, target)

        quality = assert_docx_quality(target, expected_product="CO-EM-004")
        visual = assert_visual_structure(target, expected_product="CO-EM-004")
        standard = audit_docx_legal_standard(target)
        if not standard["valid"]:
            raise ValueError(f"CO-EM-004 no supera el estándar M33.0: {standard['findings']}")
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
