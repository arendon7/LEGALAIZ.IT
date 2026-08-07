from __future__ import annotations

from pathlib import Path

from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from document_standard_v33 import audit_docx_legal_standard
from docx_builder import build_docx
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_services_legal_review import compose_services_m33_reviewed


class CoEm003DocumentFactoryV245(CoEm003DocumentFactoryV244):
    """CO-EM-003 M33.0: nueva revisión documental sobre la fábrica histórica v2.44."""

    VERSION = "2.45"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = self.root / "data" / "generated" / "co-em-003-v245"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _render_m33_primary(normalized: dict, target: Path):
        composition = compose_services_m33_reviewed(normalized)
        client = normalized.get("client", {}).get("identification", {})
        contractor = normalized.get("contractor", {}).get("identification", {})
        build_docx(
            target,
            composition["title"],
            composition["subtitle"],
            [
                ("Producto", "CO-EM-003"),
                ("Contratante", str(client.get("name") or "Parte contratante")),
                ("Contratista", str(contractor.get("name") or "Parte contratista")),
                ("Estándar documental", "M33.0"),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            composition["sections"],
            product_code="CO-EM-003",
            enforce_legal_standard=True,
        )

    def render_documents(self, answers, target_folder):
        normalized = self._normalize_answers(answers)
        evaluation, generated, hashes = super().render_documents(normalized, target_folder)
        target_folder = Path(target_folder)
        primary = next((item for item in generated if item.get("id") == "DOC-EM-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-EM-003 M33.0 no encontró el contrato principal generado.")
        target = target_folder / primary["filename"]
        self._render_m33_primary(normalized, target)

        quality = assert_docx_quality(target, expected_product="CO-EM-003")
        visual = assert_visual_structure(target, expected_product="CO-EM-003")
        standard = audit_docx_legal_standard(target)
        if not standard["valid"]:
            raise ValueError(f"CO-EM-003 no supera el estándar M33.0: {standard['findings']}")
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
