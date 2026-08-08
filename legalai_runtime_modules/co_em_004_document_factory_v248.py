from __future__ import annotations

from pathlib import Path

from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_document_presentation import (
    APPROVAL_CANDIDATE_MODE,
    audit_m33_presentation,
    build_m33_presentation,
)
from m33_nda_legal_finalize import compose_nda_m33_final


class CoEm004DocumentFactoryV248(CoEm004DocumentFactoryV247):
    """CO-EM-004 M33.0: recompone el NDA principal y preserva anexos/actas existentes."""

    VERSION = "2.48"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-em-004-v248"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._m33_review_evidence: dict[str, dict] = {}

    @staticmethod
    def _party_name(answers: dict, prefix: str, fallback: str) -> str:
        block = answers.get(prefix) if isinstance(answers.get(prefix), dict) else {}
        identification = block.get("identification") if isinstance(block.get("identification"), dict) else {}
        return str(
            identification.get("name")
            or identification.get("legalName")
            or identification.get("fullName")
            or fallback
        )

    @classmethod
    def _cover_subtitle(cls, answers: dict) -> str:
        party_a = cls._party_name(answers, "party_a", "LA PRIMERA PARTE")
        party_b = cls._party_name(answers, "party_b", "LA SEGUNDA PARTE")
        agreement = answers.get("agreement") if isinstance(answers.get("agreement"), dict) else {}
        reference = str(agreement.get("reference") or "").strip()
        return " · ".join(value for value in (party_a, party_b, reference) if value)

    def _render_m33_primary(self, answers: dict, target: Path):
        composition = compose_nda_m33_final(answers)
        party_a = self._party_name(answers, "party_a", "LA PRIMERA PARTE")
        party_b = self._party_name(answers, "party_b", "LA SEGUNDA PARTE")
        evidence = build_m33_presentation(
            path=target,
            title=composition["title"],
            subtitle=composition.get("subtitle") or "",
            metadata=[
                ("Producto", "CO-EM-004"),
                ("Primera parte", party_a),
                ("Segunda parte", party_b),
                ("Estándar documental", self.DOCUMENT_STANDARD),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            sections=composition["sections"],
            product_code="CO-EM-004",
            presentation_mode=APPROVAL_CANDIDATE_MODE,
            approval_subtitle=self._cover_subtitle(answers),
        )
        self._m33_review_evidence[target.name] = evidence

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
        standard = audit_m33_presentation(target, APPROVAL_CANDIDATE_MODE)
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
        primary["presentation_mode"] = APPROVAL_CANDIDATE_MODE
        primary["review_evidence"] = self._m33_review_evidence.get(primary["filename"], {})
        primary["approval_state"] = {"legal": "pending", "qa": "pending"}
        primary["release_rule"] = "Liberar únicamente el mismo SHA-256 aprobado por Jurídico y QA."
        primary["m33_preflight"] = standard
        hashes[primary["filename"]] = quality["sha256"]
        return evaluation, generated, hashes
