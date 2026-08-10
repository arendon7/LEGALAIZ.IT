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
from m33_3_habeas_communication_guard import enforce_habeas_prior_communication
from m33_3_habeas_permanence_guard import enforce_habeas_permanence
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_consumer_legal_finalize import MECHANISMS, consumer_route_fixture
from tests.test_m33_0_debt_legal_finalize import debt_stage_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS, habeas_fixture, labor_fixture

SELECTIONS = {
    "CO-LA-001": ("calculation", "claim"),
    "CO-CD-001": (
        "habeas_consultation",
        "habeas_claim",
        "habeas_reiteration",
        "identity_theft_protocol",
        "habeas_authority_escalation",
        "habeas_evidence_matrix",
        "habeas_deadline_calendar",
    ),
}
CONSUMER_COMMON = ("consumer_mechanism_diagnosis", "consumer_evidence_matrix", "consumer_deadline_calendar")
DEBT_VISUAL_STAGES = (
    ("Enviar un cobro inicial", False, ("debt_diagnostic", "account_statement", "collection_evidence_matrix", "collection_letter")),
    ("Acordar un plan de pago", False, ("payment_agreement", "payment_schedule", "promissory_note", "instruction_letter")),
    ("Registrar o seguir pagos", False, ("payment_receipt",)),
    ("Cerrar la obligación", True, ("settlement_certificate",)),
)


def _load_habeas_parameters() -> dict:
    payload = json.loads((ROOT / "data" / "parameters.json").read_text(encoding="utf-8"))
    params = payload.get("CO-CD-001")
    if not isinstance(params, dict):
        raise RuntimeError("No existe configuración canónica CO-CD-001 en data/parameters.json.")
    threshold = params.get("small_obligation_reference_value")
    if threshold in (None, ""):
        raise RuntimeError("CO-CD-001 no define small_obligation_reference_value en parameters.json.")
    return params


HABEAS_PARAMETERS = _load_habeas_parameters()


def _specs(code: str, answers: dict, result: dict) -> list[dict]:
    return document_specs_m33_all("CASE-M33-VISUAL", code, answers, result, PRODUCTS[code], "2026-08-08T08:00:00-05:00", [])


def _attach_calendar_metadata(calculation: dict, audits: list) -> None:
    calculation["holiday_calendar_applied"] = bool(audits)
    calculation["deadline_is_preliminary"] = True
    calculation["business_day_calendar_engine"] = "M33.3-colombia-national-business-days-v1"
    calculation["business_day_calendar_scope"] = CALENDAR_SCOPE
    calculation["business_day_calendar_verified_at"] = RULESET_VERIFIED_AT
    calculation["business_day_counting_rule"] = COUNTING_RULE
    calculation["business_day_calendar_basis"] = list(CALENDAR_BASIS)
    calculation["business_day_calendar_limitations"] = list(CALENDAR_LIMITATIONS)
    payloads = []
    for sequence, audit in enumerate(audits, 1):
        payload = audit.to_dict(); payload["sequence"] = sequence; payloads.append(payload)
    calculation["business_day_calculations"] = payloads


def _habeas_visual_fixture() -> tuple[dict, dict]:
    """Completa de forma explícita la fixture sintética usada por el QA visual.

    No se infieren estados desde prosa libre. La muestra declara una obligación pagada
    y, para probar la nueva distinción M33.3, modela una comunicación física enviada
    21 días antes del reporte aunque el titular declare no haberla recibido. Así la
    evidencia demuestra que recepción y envío son hechos jurídicamente separados.
    """
    answers, result = habeas_fixture()
    answers = deepcopy(answers)
    result = deepcopy(result)
    if "obligación fue pagada" not in str(answers.get("facts_detail") or "").casefold():
        raise RuntimeError("La fixture visual CO-CD-001 dejó de describir una obligación pagada.")
    if not answers.get("payment_or_extinction_date"):
        raise RuntimeError("La fixture visual CO-CD-001 pagada carece de fecha de pago/extinción.")
    answers.update({
        "obligation_status": "Pagada",
        "obligation_amount": 5_000_000,
        "prior_communication_received": "No",
        "prior_communication_sent": "Sí",
        "prior_communication_date": "2023-10-20",
        "prior_communication_evidence": "Completa",
        "prior_communication_channel": "Dirección física registrada",
        "prior_communication_destination_verified": "Sí",
        "prior_communication_alternative_channel_agreed": "No aplica",
        "prior_communication_message_consultable": "No aplica",
        "prior_communication_content_sufficient": "Sí",
        "small_obligation_two_notices": "No aplica",
    })
    calculation = result.setdefault("calculation", {})
    calculation["small_obligation_reference_value"] = HABEAS_PARAMETERS["small_obligation_reference_value"]
    calculation["small_obligation_threshold_smmlv"] = HABEAS_PARAMETERS.get("small_obligation_threshold_smmlv")
    calculation["smmlv_reference_2026"] = HABEAS_PARAMETERS.get("smmlv_reference_2026")
    return answers, result


def _m33_3_consumer_calendar_evidence(answers: dict, result: dict) -> tuple[dict, dict]:
    updated_answers = deepcopy(answers); updated_result = deepcopy(result)
    calculation = updated_result.setdefault("calculation", {})
    start_raw = updated_answers.get("direct_claim_date") or updated_answers.get("prior_claim_date")
    if not start_raw:
        return updated_answers, updated_result
    start = date.fromisoformat(str(start_raw)); business_days = int(calculation.get("direct_claim_business_days") or 15)
    audit = calculate_colombian_business_days(start, business_days)
    calculation["direct_claim_due_date"] = audit.due_date.isoformat(); _attach_calendar_metadata(calculation, [audit])
    return updated_answers, updated_result


def _m33_3_habeas_calendar_evidence(answers: dict, result: dict) -> tuple[dict, dict]:
    """Recalcula fechas hábiles y activa las compuertas M33.3 de la evidencia."""
    updated_answers = deepcopy(answers); updated_result = deepcopy(result)
    calculation = updated_result.setdefault("calculation", {}); audits = []
    filing_raw = updated_answers.get("filing_date")
    if filing_raw:
        filing = date.fromisoformat(str(filing_raw))
        due = calculate_colombian_business_days(filing, 15)
        extension = calculate_colombian_business_days(due.due_date, 8)
        calculation["preliminary_due_date"] = due.due_date.isoformat()
        calculation["preliminary_due_with_extension"] = extension.due_date.isoformat(); audits.extend([due, extension])
    prior_raw = updated_answers.get("prior_claim_date")
    if prior_raw:
        prior = date.fromisoformat(str(prior_raw))
        legend = calculate_colombian_business_days(prior, 2)
        prior_due = calculate_colombian_business_days(prior, 15)
        updated_answers["extension_notified"] = "Sí"
        prior_max = calculate_colombian_business_days(prior_due.due_date, 8)
        calculation["claim_legend_due_date"] = legend.due_date.isoformat()
        calculation["prior_preliminary_due_date"] = prior_due.due_date.isoformat()
        calculation["prior_max_due_date"] = prior_max.due_date.isoformat(); audits.extend([legend, prior_due, prior_max])
    _attach_calendar_metadata(calculation, audits)
    calculation = enforce_habeas_prior_communication(updated_answers, calculation)
    if calculation.get("communication_status") != "preliminarily_supported":
        raise RuntimeError(
            "La fixture visual M33.3 de comunicación previa dejó de representar un envío "
            f"preliminarmente soportado: {calculation.get('communication_status')!r}."
        )
    updated_result["calculation"] = enforce_habeas_permanence(updated_answers, calculation)
    return updated_answers, updated_result


def _visible_metadata(code: str, spec: dict) -> list[tuple[str, str]]:
    if spec.get("internal_controls_externalized"):
        return []
    return [("Producto", code), ("Estándar documental", "M33.0"), ("Estado", "Candidato sujeto a revisión jurídica y QA")]


def _apply_presentation(target: Path, *, code: str, title: str) -> dict:
    procedural = apply_m33_2_procedural_format(target, product_code=code, title=title)
    if procedural.get("applied"): return procedural
    analytical = apply_m33_2_analytical_format(target, product_code=code, title=title)
    if analytical.get("applied"): return analytical
    operational = apply_m33_2_operational_format(target, product_code=code, title=title)
    if operational.get("applied"): return operational
    special = apply_m33_2_special_format(target, product_code=code, title=title)
    if special.get("applied"):
        pagination = apply_m33_2_special_pagination_finalize(target, product_code=code, title=title)
        if pagination.get("applied"):
            special = dict(special); special["pagination_profile"] = pagination.get("profile")
        return special
    return {"applied": False, "profile": "M33.2-base", "reason": "base_family"}


def _write_sample(output: Path, code: str, kind: str, spec: dict, records: list[dict]) -> None:
    target = output / f"{code}_{kind}_M33_0.docx"
    build_docx(target, spec["title"], spec.get("subtitle", ""), _visible_metadata(code, spec), spec["sections"], product_code=code, enforce_legal_standard=True, append_default_control=not bool(spec.get("internal_controls_externalized")))
    presentation = _apply_presentation(target, code=code, title=spec["title"])
    records.append({
        "product_code": code, "kind": kind, "sample": target.name,
        "document_standard": spec.get("document_standard"),
        "presentation_standard": "M33.2" if presentation.get("applied") else "M33.2-base",
        "presentation_profile": presentation.get("profile"), "pagination_profile": presentation.get("pagination_profile"),
        "calendar_standard": spec.get("calendar_standard"), "calendar_scope": spec.get("calendar_scope"),
        "calendar_ruleset_verified_at": spec.get("calendar_ruleset_verified_at"),
        "permanence_standard": spec.get("permanence_standard"),
        "permanence_ruleset_verified_at": spec.get("permanence_ruleset_verified_at"),
        "communication_standard": spec.get("communication_standard"),
        "communication_ruleset_verified_at": spec.get("communication_ruleset_verified_at"),
        "released": False, "legal_approval": "pending", "qa_approval": "pending",
        "internal_controls_externalized": bool(spec.get("internal_controls_externalized")),
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera muestras representativas de la segunda oleada M33.0.")
    parser.add_argument("--output", required=True, type=Path); args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True); records: list[dict] = []
    labor_answers, labor_result = labor_fixture()
    habeas_answers, habeas_result = _m33_3_habeas_calendar_evidence(*_habeas_visual_fixture())
    fixtures = {"CO-LA-001": (labor_answers, labor_result), "CO-CD-001": (habeas_answers, habeas_result)}
    for code, (answers, result) in fixtures.items():
        by_kind = {spec["kind"]: spec for spec in _specs(code, answers, result)}
        for kind in SELECTIONS[code]:
            if kind not in by_kind: raise RuntimeError(f"{code}: no se generó la muestra requerida {kind}.")
            _write_sample(output, code, kind, by_kind[kind], records)
    common_written = False
    for mechanism_kind in MECHANISMS:
        answers, result = _m33_3_consumer_calendar_evidence(*consumer_route_fixture(mechanism_kind))
        by_kind = {spec["kind"]: spec for spec in _specs("CO-CD-003", answers, result)}
        if mechanism_kind not in by_kind: raise RuntimeError(f"CO-CD-003: no se generó la ruta {mechanism_kind}.")
        if not common_written:
            for kind in CONSUMER_COMMON:
                if kind not in by_kind: raise RuntimeError(f"CO-CD-003: falta documento común {kind}.")
                _write_sample(output, "CO-CD-003", kind, by_kind[kind], records)
            common_written = True
        _write_sample(output, "CO-CD-003", mechanism_kind, by_kind[mechanism_kind], records)
    written_debt: set[str] = set()
    for stage, zero_balance, kinds in DEBT_VISUAL_STAGES:
        answers, result = debt_stage_fixture(stage, zero_balance=zero_balance)
        by_kind = {spec["kind"]: spec for spec in _specs("CO-CD-004", answers, result)}
        for kind in kinds:
            if kind in written_debt: continue
            if kind not in by_kind: raise RuntimeError(f"CO-CD-004/{stage}: no se generó la muestra requerida {kind}.")
            _write_sample(output, "CO-CD-004", kind, by_kind[kind], records); written_debt.add(kind)
    if len(written_debt) != 10: raise RuntimeError(f"CO-CD-004: se esperaban 10 piezas visuales y se generaron {len(written_debt)}.")
    manifest = output / "m33-procedural-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "manifest": str(manifest)}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
