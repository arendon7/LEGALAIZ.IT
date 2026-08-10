from __future__ import annotations

from pathlib import Path
import re

from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_document_presentation import APPROVAL_CANDIDATE_MODE, audit_m33_presentation, build_m33_presentation
from m33_nda_instrument_finalize import compose_nda_m33_instrument


class CoEm004DocumentFactoryV248(CoEm004DocumentFactoryV247):
    """CO-EM-004: contenido M33.0 con presentación contractual M33.2."""

    VERSION = "2.48"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-em-004-v248"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._m33_review_evidence: dict[str, dict] = {}

    @staticmethod
    def _party_identification(answers: dict, prefix: str) -> dict:
        block = answers.get(prefix) if isinstance(answers.get(prefix), dict) else {}
        return block.get("identification") if isinstance(block.get("identification"), dict) else {}

    @classmethod
    def _party_name(cls, answers: dict, prefix: str, fallback: str) -> str:
        identification = cls._party_identification(answers, prefix)
        return str(identification.get("name") or identification.get("legalName") or identification.get("fullName") or fallback)

    @classmethod
    def _party_id(cls, answers: dict, prefix: str) -> str:
        identification = cls._party_identification(answers, prefix)
        return cls._format_identifier(identification.get("id_number") or identification.get("identificationNumber"))

    @staticmethod
    def _format_identifier(value) -> str:
        text = str(value or "").strip()
        compact = text.replace(".", "")
        match = re.fullmatch(r"(\d{7,12})(?:-(\d))?", compact)
        if not match:
            return text
        base, check = match.groups()
        groups = []
        while base:
            groups.append(base[-3:])
            base = base[:-3]
        formatted = ".".join(reversed(groups))
        return f"{formatted}-{check}" if check else formatted

    @classmethod
    def _cover_subtitle(cls, answers: dict) -> str:
        party_a = cls._party_name(answers, "party_a", "LA PRIMERA PARTE")
        party_b = cls._party_name(answers, "party_b", "LA SEGUNDA PARTE")
        agreement = answers.get("agreement") if isinstance(answers.get("agreement"), dict) else {}
        reference = str(agreement.get("reference") or "").strip()
        return " · ".join(value for value in (party_a, party_b, reference) if value)

    def _render_m33_primary(self, answers: dict, target: Path):
        composition = compose_nda_m33_instrument(answers)
        party_a = self._party_name(answers, "party_a", "LA PRIMERA PARTE")
        party_b = self._party_name(answers, "party_b", "LA SEGUNDA PARTE")
        agreement = answers.get("agreement") if isinstance(answers.get("agreement"), dict) else {}
        term = answers.get("term_remedies") if isinstance(answers.get("term_remedies"), dict) else {}
        reference = str(agreement.get("reference") or "").strip()
        purpose = str(agreement.get("purpose") or "").strip()
        agreement_type = str(agreement.get("type") or "").replace("_", " ").upper()
        years = term.get("agreement_years")
        validity = f"{years} AÑOS" if years not in (None, "") else ""

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
            approval_metadata=[
                ("PRIMERA PARTE", party_a.upper()),
                ("NIT / DOCUMENTO", self._party_id(answers, "party_a")),
                ("SEGUNDA PARTE", party_b.upper()),
                ("NIT / DOCUMENTO", self._party_id(answers, "party_b")),
                ("MODALIDAD", agreement_type),
                ("FINALIDAD", purpose),
                ("REFERENCIA", reference),
                ("VIGENCIA", validity),
            ],
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
            raise ValueError(f"CO-EM-004 no supera el estándar M33.2: {standard['findings']}")
        primary["quality"] = {"valid": quality["valid"], "warnings": quality["warnings"], "metrics": quality["metrics"]}
        primary["visual_preflight"] = {
            "valid": visual["valid"], "warnings": visual["warnings"], "metrics": visual["metrics"],
            "requires_human_visual_review": True,
        }
        primary["document_standard"] = self.DOCUMENT_STANDARD
        primary["presentation_standard"] = "M33.2"
        primary["presentation_mode"] = APPROVAL_CANDIDATE_MODE
        primary["review_evidence"] = self._m33_review_evidence.get(primary["filename"], {})
        primary["approval_state"] = {"legal": "pending", "qa": "pending"}
        primary["release_rule"] = "Liberar únicamente el mismo SHA-256 aprobado por Jurídico y QA."
        primary["m33_preflight"] = standard
        hashes[primary["filename"]] = quality["sha256"]
        return evaluation, generated, hashes
