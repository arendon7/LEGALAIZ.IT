from __future__ import annotations

from datetime import date
from pathlib import Path

from co_ar_001_document_factory_v250 import CoAr001DocumentFactoryV250
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_document_presentation import APPROVAL_CANDIDATE_MODE, audit_m33_presentation, build_m33_presentation
from m33_lease_instrument_finalize import compose_lease_m33_instrument


_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


class CoAr001DocumentFactoryV251(CoAr001DocumentFactoryV250):
    """CO-AR-001: contenido M33.0 con presentación contractual M33.2."""

    VERSION = "2.51"
    DOCUMENT_STANDARD = "M33.0"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-ar-001-v251"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._m33_review_evidence: dict[str, dict] = {}

    @staticmethod
    def _party_block(answers: dict, prefix: str) -> dict:
        block = answers.get(prefix) if isinstance(answers.get(prefix), dict) else {}
        ident = block.get("identification") if isinstance(block.get("identification"), dict) else {}
        return ident

    @classmethod
    def _party_name(cls, answers: dict, prefix: str, fallback: str) -> str:
        ident = cls._party_block(answers, prefix)
        return str(ident.get("name") or ident.get("legalName") or ident.get("fullName") or fallback)

    @classmethod
    def _party_id(cls, answers: dict, prefix: str) -> str:
        ident = cls._party_block(answers, prefix)
        return str(ident.get("id_number") or ident.get("identificationNumber") or "").strip()

    @staticmethod
    def _date_es(value) -> str:
        text = str(value or "").strip()
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            return text
        return f"{parsed.day} de {_MONTHS[parsed.month]} de {parsed.year}"

    @staticmethod
    def _format_cop(value) -> str:
        try:
            amount = int(round(float(value)))
        except (TypeError, ValueError):
            return str(value or "").strip()
        return f"COP ${amount:,}".replace(",", ".") + " M/CTE"

    @classmethod
    def _cover_subtitle(cls, answers: dict) -> str:
        landlord = cls._party_name(answers, "landlord", "LA PARTE ARRENDADORA")
        tenant = cls._party_name(answers, "tenant", "LA PARTE ARRENDATARIA")
        prop = answers.get("property") if isinstance(answers.get("property"), dict) else {}
        ident = prop.get("identification") if isinstance(prop.get("identification"), dict) else {}
        address = str(ident.get("address") or "").strip()
        municipality = str(ident.get("municipality") or "").strip()
        return " · ".join(value for value in (landlord, tenant, address, municipality) if value)

    def _render_m33_primary(self, answers: dict, target: Path):
        composition = compose_lease_m33_instrument(answers)
        landlord = self._party_name(answers, "landlord", "LA PARTE ARRENDADORA")
        tenant = self._party_name(answers, "tenant", "LA PARTE ARRENDATARIA")
        prop = answers.get("property") if isinstance(answers.get("property"), dict) else {}
        prop_id = prop.get("identification") if isinstance(prop.get("identification"), dict) else {}
        rent = answers.get("rent") if isinstance(answers.get("rent"), dict) else {}
        delivery = answers.get("delivery") if isinstance(answers.get("delivery"), dict) else {}
        term = answers.get("term") if isinstance(answers.get("term"), dict) else {}
        use = answers.get("use") if isinstance(answers.get("use"), dict) else {}

        address = str(prop_id.get("address") or "").strip()
        municipality = str(prop_id.get("municipality") or "").strip()
        property_label = ", ".join(value for value in (address, municipality) if value)
        duration = term.get("duration_months")
        duration_text = f"{duration} MESES" if duration not in (None, "") else ""
        destination = str(use.get("destination") or "VIVIENDA URBANA").replace("_", " ").upper()

        evidence = build_m33_presentation(
            path=target,
            title=composition["title"],
            subtitle=composition.get("subtitle") or "",
            metadata=[
                ("Producto", "CO-AR-001"),
                ("Parte arrendadora", landlord),
                ("Parte arrendataria", tenant),
                ("Estándar documental", self.DOCUMENT_STANDARD),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            sections=composition["sections"],
            product_code="CO-AR-001",
            presentation_mode=APPROVAL_CANDIDATE_MODE,
            approval_subtitle=self._cover_subtitle(answers),
            approval_metadata=[
                ("ARRENDADOR", landlord.upper()),
                ("NIT / DOCUMENTO", self._party_id(answers, "landlord")),
                ("ARRENDATARIO", tenant.upper()),
                ("DOCUMENTO", self._party_id(answers, "tenant")),
                ("INMUEBLE", property_label),
                ("CANON MENSUAL", self._format_cop(rent.get("amount"))),
                ("INICIO", self._date_es(delivery.get("date")).upper()),
                ("DURACIÓN", duration_text),
                ("DESTINACIÓN", destination),
            ],
        )
        self._m33_review_evidence[target.name] = evidence

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
        standard = audit_m33_presentation(target, APPROVAL_CANDIDATE_MODE)
        if not standard["valid"]:
            raise ValueError(f"CO-AR-001 no supera el estándar M33.2: {standard['findings']}")
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
