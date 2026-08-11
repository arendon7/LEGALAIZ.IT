from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from datetime import date
from pathlib import Path
import re

from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure
from m33_document_presentation import APPROVAL_CANDIDATE_MODE, audit_m33_presentation, build_m33_presentation
from m33_services_release_polish import compose_services_m33_release


_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
_M33_SERVICES_SOURCE: ContextVar[dict | None] = ContextVar("m33_services_source", default=None)


class CoEm003DocumentFactoryV245(CoEm003DocumentFactoryV244):
    """CO-EM-003: contenido M33.0 con presentación contractual M33.2."""

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

    @staticmethod
    def _nested_dict(value) -> dict:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _format_identifier(value) -> str:
        text = str(value or "").strip()
        match = re.fullmatch(r"(\d{7,12})(?:-(\d))?", re.sub(r"[.]", "", text))
        if not match:
            return text
        base, check = match.groups()
        groups = []
        while base:
            groups.append(base[-3:])
            base = base[:-3]
        result = ".".join(reversed(groups))
        return f"{result}-{check}" if check else result

    @staticmethod
    def _format_cop(value) -> str:
        try:
            amount = int(round(float(value)))
        except (TypeError, ValueError):
            return str(value or "").strip()
        return f"COP ${amount:,}".replace(",", ".") + " M/CTE"

    @classmethod
    def _approval_cover_subtitle(cls, normalized: dict) -> str:
        client = cls._nested_dict(cls._nested_dict(normalized.get("client")).get("identification"))
        contractor = cls._nested_dict(cls._nested_dict(normalized.get("contractor")).get("identification"))
        dispute = cls._nested_dict(normalized.get("dispute"))
        disputes = cls._nested_dict(normalized.get("disputes"))
        term = cls._nested_dict(normalized.get("term"))
        schedule = cls._nested_dict(normalized.get("schedule"))
        client_name = str(client.get("name") or "EL CONTRATANTE")
        contractor_name = str(contractor.get("name") or "EL CONTRATISTA")
        city = str(dispute.get("city") or disputes.get("city") or client.get("domicile") or "").strip()
        start = cls._date_es(term.get("start_date") or schedule.get("start_date"))
        context = f"{client_name} · {contractor_name}"
        location_date = " · ".join(value for value in (city, start) if value)
        return f"{context}\n{location_date}" if location_date else context

    @classmethod
    def _presentation_answers(cls, normalized: dict, original: dict) -> dict:
        result = deepcopy(normalized)
        original = original if isinstance(original, dict) else {}
        for section_name, field_names in {
            "service": ("object", "expected_result", "professional"),
            "termination": ("rules", "cure_period"),
        }.items():
            source = original.get(section_name)
            if not isinstance(source, dict):
                continue
            target = result.setdefault(section_name, {})
            if not isinstance(target, dict):
                target = {}
                result[section_name] = target
            for field_name in field_names:
                value = source.get(field_name)
                if value not in (None, "", [], {}):
                    target[field_name] = deepcopy(value)
        return result

    @classmethod
    def _render_m33_primary(cls, normalized: dict, target: Path) -> dict:
        service = normalized.setdefault("service", {})
        if isinstance(service, dict):
            service.setdefault("professional", True)
        composition = compose_services_m33_release(normalized)
        client = cls._nested_dict(cls._nested_dict(normalized.get("client")).get("identification"))
        contractor = cls._nested_dict(cls._nested_dict(normalized.get("contractor")).get("identification"))
        fees = cls._nested_dict(normalized.get("fees"))
        term = cls._nested_dict(normalized.get("term"))
        schedule = cls._nested_dict(normalized.get("schedule"))

        client_name = str(client.get("name") or "PARTE CONTRATANTE")
        contractor_name = str(contractor.get("name") or "PARTE CONTRATISTA")
        start = cls._date_es(term.get("start_date") or schedule.get("start_date"))
        end = cls._date_es(term.get("end_date") or schedule.get("end_date"))
        object_text = str(service.get("object") or "").strip()
        fee_value = cls._format_cop(fees.get("amount"))

        return build_m33_presentation(
            path=target,
            title=composition["title"],
            subtitle=composition.get("subtitle") or "",
            metadata=[
                ("Producto", "CO-EM-003"),
                ("Contratante", client_name),
                ("Contratista", contractor_name),
                ("Estándar documental", "M33.0"),
                ("Estado", "Candidato sujeto a revisión jurídica y QA"),
            ],
            sections=composition["sections"],
            product_code="CO-EM-003",
            presentation_mode=APPROVAL_CANDIDATE_MODE,
            approval_subtitle=cls._approval_cover_subtitle(normalized),
            approval_metadata=[
                ("CONTRATANTE", client_name.upper()),
                ("NIT / DOCUMENTO", cls._format_identifier(client.get("identification_number"))),
                ("CONTRATISTA", contractor_name.upper()),
                ("NIT / DOCUMENTO", cls._format_identifier(contractor.get("identification_number"))),
                ("OBJETO", object_text),
                ("HONORARIOS", fee_value),
                ("INICIO", start.upper()),
                ("TERMINACIÓN", end.upper()),
            ],
        )

    def render_documents(self, answers, target_folder):
        original = _M33_SERVICES_SOURCE.get() or answers
        normalized = self._normalize_answers(answers)
        evaluation, generated, hashes = super().render_documents(normalized, target_folder)
        target_folder = Path(target_folder)
        primary = next((item for item in generated if item.get("id") == "DOC-EM-CONTRACT-001"), None)
        if not primary:
            raise RuntimeError("CO-EM-003 M33.0 no encontró el contrato principal generado.")
        target = target_folder / primary["filename"]
        presentation_answers = self._presentation_answers(normalized, original)
        review_evidence = self._render_m33_primary(presentation_answers, target)

        quality = assert_docx_quality(target, expected_product="CO-EM-003")
        visual = assert_visual_structure(target, expected_product="CO-EM-003")
        standard = audit_m33_presentation(target, APPROVAL_CANDIDATE_MODE)
        if not standard["valid"]:
            raise ValueError(f"CO-EM-003 no supera el estándar M33.2: {standard['findings']}")
        primary["quality"] = {"valid": quality["valid"], "warnings": quality["warnings"], "metrics": quality["metrics"]}
        primary["visual_preflight"] = {
            "valid": visual["valid"], "warnings": visual["warnings"], "metrics": visual["metrics"],
            "requires_human_visual_review": True,
        }
        primary["document_standard"] = self.DOCUMENT_STANDARD
        primary["presentation_standard"] = "M33.2"
        primary["presentation_mode"] = APPROVAL_CANDIDATE_MODE
        primary["review_evidence"] = review_evidence
        primary["approval_state"] = {"legal": "pending", "qa": "pending"}
        primary["release_rule"] = "Liberar únicamente el mismo SHA-256 aprobado por Jurídico y QA."
        primary["m33_preflight"] = standard
        hashes[primary["filename"]] = quality["sha256"]
        return evaluation, generated, hashes

    def generate(self, answers, actor=None):
        source = deepcopy(answers or {})
        token = _M33_SERVICES_SOURCE.set(source)
        try:
            return super().generate(answers, actor=actor)
        finally:
            _M33_SERVICES_SOURCE.reset(token)
