#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docx_builder import build_docx
from legalai_platform.colombian_business_calendar import (
    CALENDAR_BASIS,
    CALENDAR_LIMITATIONS,
    CALENDAR_SCOPE,
    COUNTING_RULE,
    RULESET_VERIFIED_AT,
    calculate_colombian_business_days,
)
from m33_2_analytical_reference_format import apply_m33_2_analytical_format
from m33_2_operational_reference_format import apply_m33_2_operational_format
from m33_2_procedural_reference_format import apply_m33_2_procedural_format
from m33_2_special_reference_format import apply_m33_2_special_format
from m33_2_special_pagination_finalize import apply_m33_2_special_pagination_finalize
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, health_fixture, sast_fixture, traffic_fixture

SELECTIONS = {
    "CO-SA-001": (
        "health_diagnostic", "health_petition", "health_reiteration", "health_supersalud",
        "health_history_request", "health_evidence", "health_calendar",
    ),
    "CO-TR-001": (
        "sast_report", "sast_traceability", "sast_registration", "sast_record_request",
        "sast_inspection", "sast_followup", "sast_package",
    ),
    "CO-TR-002": (
        "traffic_diagnostic", "traffic_record_request", "traffic_notification_claim",
        "traffic_hearing_request", "traffic_revocation_request", "traffic_registry_correction",
        "traffic_evidence_matrix", "traffic_filing_guide",
    ),
}


def _specs(code: str, answers: dict, result: dict) -> list[dict]:
    return document_specs_m33_all(
        "CASE-M33-W3-VISUAL", code, answers, result, PRODUCTS[code],
        "2026-08-09T12:00:00-05:00", [],
    )


def _m33_3_health_calendar_evidence(answers: dict, result: dict) -> tuple[dict, dict]:
    """Construye para QA visual un control general subsidiario de petición.

    La regla sectorial 24/48/72 horas permanece rectora. Este cálculo de 15 días
    hábiles solo demuestra la trazabilidad del calendario nacional para la referencia
    general de petición y se etiqueta expresamente como secundaria.
    """
    updated_answers = deepcopy(answers)
    updated_result = deepcopy(result)
    calculation = updated_result.setdefault("calculation", {})
    filing_raw = updated_answers.get("filing_date")
    if not filing_raw:
        return updated_answers, updated_result
    start = date.fromisoformat(str(filing_raw))
    audit = calculate_colombian_business_days(start, 15)
    calculation["preliminary_due_date"] = audit.due_date.isoformat()
    calculation["preliminary_business_days"] = 15
    calculation["term_category"] = "petición general subsidiaria"
    calculation["holiday_calendar_applied"] = True
    calculation["deadline_is_preliminary"] = True
    calculation["business_day_calendar_engine"] = "M33.3-colombia-national-business-days-v1"
    calculation["business_day_calendar_scope"] = CALENDAR_SCOPE
    calculation["business_day_calendar_verified_at"] = RULESET_VERIFIED_AT
    calculation["business_day_counting_rule"] = COUNTING_RULE
    calculation["business_day_calendar_basis"] = list(CALENDAR_BASIS)
    calculation["business_day_calendar_limitations"] = list(CALENDAR_LIMITATIONS)
    payload = audit.to_dict(); payload["sequence"] = 1
    calculation["business_day_calculations"] = [payload]
    return updated_answers, updated_result


def _find(specs: list[dict], requested: str) -> dict:
    by_kind = {str(spec.get("kind")): spec for spec in specs}
    if requested in by_kind:
        return by_kind[requested]
    tokens = {
        "health_diagnostic": ("diagnóstico", "salud"), "health_petition": ("petición", "reclamo"),
        "health_reiteration": ("reiteración",), "health_supersalud": ("supersalud",),
        "health_history_request": ("historia clínica",), "health_evidence": ("matriz", "radicación"),
        "health_calendar": ("calendario", "seguimiento"), "sast_report": ("informe", "sast"),
        "sast_traceability": ("trazabilidad", "sast"), "sast_registration": ("autorización", "gestión", "sast"),
        "sast_record_request": ("petición", "expediente", "sast"), "sast_inspection": ("inspección", "sast"),
        "sast_followup": ("reiteración", "sast"), "sast_package": ("resumen", "sast"),
        "traffic_diagnostic": ("diagnóstico", "fotodetección"),
        "traffic_record_request": ("expediente", "estado procesal"),
        "traffic_notification_claim": ("notificación", "irregular"),
        "traffic_hearing_request": ("audiencia", "pruebas"),
        "traffic_revocation_request": ("revocación", "directa"),
        "traffic_registry_correction": ("corrección", "registros"),
        "traffic_evidence_matrix": ("matriz", "términos"),
        "traffic_filing_guide": ("radicación", "cierre"),
    }[requested]
    for spec in specs:
        title = str(spec.get("title") or "").casefold()
        if all(token.casefold() in title for token in tokens):
            return spec
    raise RuntimeError(f"No se encontró muestra {requested}; disponibles: {sorted(by_kind)}")


def _metadata(code: str, result: dict, spec: dict) -> list[tuple[str, str]]:
    if spec.get("internal_controls_externalized"):
        return []
    return [
        ("Producto", code), ("Estándar documental", "M33.0"),
        ("Nivel de riesgo", str(result.get("risk") or "por verificar")),
        ("Estado", "Candidato sujeto a revisión jurídica y QA"),
    ]


def _apply_presentation(target: Path, *, code: str, title: str) -> dict:
    procedural = apply_m33_2_procedural_format(target, product_code=code, title=title)
    if procedural.get("applied"):
        return procedural
    analytical = apply_m33_2_analytical_format(target, product_code=code, title=title)
    if analytical.get("applied"):
        return analytical
    operational = apply_m33_2_operational_format(target, product_code=code, title=title)
    if operational.get("applied"):
        return operational
    special = apply_m33_2_special_format(target, product_code=code, title=title)
    if special.get("applied"):
        pagination = apply_m33_2_special_pagination_finalize(target, product_code=code, title=title)
        if pagination.get("applied"):
            special = dict(special); special["pagination_profile"] = pagination.get("profile")
        return special
    return {"applied": False, "profile": "M33.2-base", "reason": "base_family"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera muestras representativas M33.0 de salud y tránsito.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    health_answers, health_result = _m33_3_health_calendar_evidence(*health_fixture())
    fixtures = {
        "CO-SA-001": (health_answers, health_result),
        "CO-TR-001": sast_fixture(),
        "CO-TR-002": traffic_fixture(),
    }
    records = []
    for code, (answers, result) in fixtures.items():
        current = _specs(code, answers, result)
        for requested in SELECTIONS[code]:
            spec = _find(current, requested); target = output / f"{code}_{requested}_M33_0.docx"
            build_docx(
                target, spec["title"], spec.get("subtitle", ""), _metadata(code, result, spec),
                spec["sections"], product_code=code, enforce_legal_standard=True,
                append_default_control=not bool(spec.get("internal_controls_externalized")),
            )
            presentation = _apply_presentation(target, code=code, title=spec["title"])
            records.append({
                "product_code": code, "requested_kind": requested, "actual_kind": spec.get("kind"),
                "sample": target.name, "document_standard": "M33.0",
                "presentation_standard": "M33.2" if presentation.get("applied") else "M33.2-base",
                "presentation_profile": presentation.get("profile"),
                "pagination_profile": presentation.get("pagination_profile"),
                "calendar_standard": spec.get("calendar_standard"),
                "calendar_scope": spec.get("calendar_scope"),
                "calendar_ruleset_verified_at": spec.get("calendar_ruleset_verified_at"),
                "risk": result.get("risk"),
                "released": False, "legal_approval": "pending", "qa_approval": "pending",
                "internal_controls_externalized": bool(spec.get("internal_controls_externalized")),
            })
    manifest = output / "m33-wave3-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
