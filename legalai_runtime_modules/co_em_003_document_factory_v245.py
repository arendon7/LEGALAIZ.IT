from __future__ import annotations

from datetime import date
from pathlib import Path

from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_document_presentation import (
    APPROVAL_CANDIDATE_MODE,
    audit_m33_presentation,
    build_m33_presentation,
)
from m33_services_legal_finalize import compose_services_m33_final


_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


class CoEm003DocumentFactoryV245(CoEm003DocumentFactoryV244):
    """CO-EM-003 M33.0: nueva revisión documental sobre la fábrica histórica v2.44."""

    VERSION = "2.45"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = self.root / "data" / "generated" / "co-em-003-v245"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _date_es(value) -> str:
        text = str(value or "").strip()
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            return text
        return f"{parsed.day} de {_MONTHS[parsed.month]} de {parsed.year}"

    @classmethod
    def _approval_cover_subtitle(cls, normalized: dict) -> str:
        client = normalized.get("client", {}).get("identification", {})
        contractor = normalized.get("contractor", {}).get("identification", {})
        client_name = str(client.get("name") or "EL CONTRATANTE")
        contractor_name = str(contractor.get("name") or "EL CONTRATISTA")
        city = str(
            normalized.get("dispute", {}).get("city")
            or normalized.get("disputes", {}).get("city")
            or client.get("domicile")
            or ""
        ).strip()
        start = cls._date_es(normalized.get("schedule", {}).get("start_date") or normalized.get("term", {}).get("start_date"))
        context = f"{client_name} · {contractor_name}"
        location_date = " · ".join(value for value in (city, start) if value)
        return f"{context}\n{location_date}" if location_date else context

    @classmethod
    def _render_m33_primary(cls, normalized: dict, target: Path) -> dict:
        # Compatibilidad del producto CO-EM-003: la familia vigente es profesional
        # por defecto, pero la entrevista puede desactivarlo expresamente.
        service = normalized.setdefault("service", {})
        if isinstance(service, dict):
            service.setdefault("professional", True)
        composition = compose_services_m33_final(normalized)
        client = normalized.get("client", {}).get("identification", {})
        contractor = normalized.get("contractor", {}).get("identification", {})
        return build_m33_presentation(
            path=target,
            title=composition["title"],
            subtitle=composition.get("subtitle") or "",
            metadata=[
                ("Producto", "CO-EM-003"),
                ("Contratante", str(client.get("name") or "Parte contratante")),
                ("Contratista", str(contractor.get("name") or "Parte contratista")),
                ("Estándar documental", "M33.0"),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            sections=composition["sections"],
            product_code="CO-EM-003",
            presentation_mode=APPROVAL_CANDIDATE_MODE,
            approval_subtitle=cls._approval_cover_subtitle(normalized),
        )

    def render_documents(self, answers, target_folder):
        normalized = self._normalize_answers(answers)
        evaluation, generated, hashes = super().render_documents(normalized, target_folder)
        target_folder = Path(target_folder)
        primary = next((item for item in generated if item.get("id") == "DOC-EM-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-EM-003 M33.0 no encontró el contrato principal generado.")
        target = target_folder / primary["filename"]
        review_evidence = self._render_m33_primary(normalized, target)

        quality = assert_docx_quality(target, expected_product="CO-EM-003")
        visual = assert_visual_structure(target, expected_product="CO-EM-003")
        standard = audit_m33_presentation(target, APPROVAL_CANDIDATE_MODE)
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
        primary["presentation_mode"] = APPROVAL_CANDIDATE_MODE
        primary["review_evidence"] = review_evidence
        primary["approval_state"] = {"legal": "pending", "qa": "pending"}
        primary["release_rule"] = "Liberar únicamente el mismo SHA-256 aprobado por Jurídico y QA."
        primary["m33_preflight"] = standard
        hashes[primary["filename"]] = quality["sha256"]
        return evaluation, generated, hashes
