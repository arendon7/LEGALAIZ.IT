from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from legalai_platform.labor_liquidation_legal_source_pack import (
    LABOR_KINDS,
    LABOR_PARAMETERS_2026,
    evaluate_labor_parameters_m334,
    labor_source_ids,
)
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, labor_fixture


EXPECTED_KINDS = {
    "calculation",
    "claim",
    "evidence_matrix",
    "labor_diagnostic",
    "labor_support_request",
    "labor_deadline_calendar",
    "labor_evidence_index",
}


def _specs(*, risk: str = "yellow", mutate=None) -> list[dict]:
    answers, result = labor_fixture()
    result["risk"] = risk
    if mutate:
        mutate(answers, result)
    return document_specs_m33_all(
        "CASE-M334-LABOR",
        "CO-LA-001",
        answers,
        result,
        PRODUCTS["CO-LA-001"],
        "2026-08-10T21:20:00-05:00",
        [],
    )


class LaborSourceTraceabilityM334Tests(unittest.TestCase):
    def test_parameter_pack_tracks_current_2026_wage_status(self):
        p = LABOR_PARAMETERS_2026
        self.assertEqual(1_750_905, p["smlmv"])
        self.assertEqual(249_095, p["transport_aid"])
        self.assertEqual("Decreto 1469 de 2025", p["wage_decree"])
        self.assertEqual("2026-07-17", p["wage_status_decision_date"])
        self.assertEqual(
            "operative_pending_merits_decision_after_revocation_of_provisional_suspension",
            p["wage_current_status"],
        )
        self.assertIn("consejodeestado.gov.co", p["wage_status_url"])

    def test_every_source_id_resolves_in_canonical_registry(self):
        answers, result = labor_fixture()
        for kind in LABOR_KINDS:
            with self.subTest(kind=kind):
                for source_id in labor_source_ids(kind, answers, result):
                    source = get_legal_source(source_id)
                    self.assertEqual(source_id, source["id"])

    def test_all_seven_labor_outputs_receive_current_internal_manifests(self):
        current = _specs()
        labor_specs = [spec for spec in current if spec.get("kind") in LABOR_KINDS]
        self.assertEqual(EXPECTED_KINDS, {spec.get("kind") for spec in labor_specs})
        self.assertEqual(7, len(labor_specs))
        for spec in labor_specs:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_gate_m334"), spec.get("kind"))
            self.assertIn("labor_parameter_control_m334", spec)

    def test_calculation_manifest_contains_material_benefit_sources(self):
        calculation = next(spec for spec in _specs() if spec.get("kind") == "calculation")
        ids = calculation["legal_source_manifest"]["source_ids"]
        self.assertIn("CO-CST-LIQUIDATION-2026", ids)
        self.assertIn("CO-LEY50-ART99-CESANTIAS", ids)
        self.assertIn("CO-LEY52-ART1-CESANTIAS", ids)
        self.assertIn("CO-LEY1788-ART306-PRIMA", ids)
        self.assertIn("CO-LEY15-TRANSPORT", ids)
        self.assertNotIn("CO-LEY2466-ART62-PRESCRIPTION", ids)

    def test_claim_and_deadline_calendar_trace_current_prescription_rule(self):
        by_kind = {spec["kind"]: spec for spec in _specs() if spec.get("kind") in LABOR_KINDS}
        for kind in ("claim", "labor_deadline_calendar"):
            ids = by_kind[kind]["legal_source_manifest"]["source_ids"]
            self.assertIn("CO-CST-LIQUIDATION-2026", ids)
            self.assertIn("CO-LEY2466-ART62-PRESCRIPTION", ids)
        source = get_legal_source("CO-LEY2466-ART62-PRESCRIPTION")
        self.assertIn("tres años", source["observed_status"])
        self.assertIn("exigibilidad", source["observed_status"])

    def test_fixture_2026_parameters_are_numerically_compatible_but_entitlement_still_human(self):
        answers, result = labor_fixture()
        control = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 8, 10))
        self.assertEqual("verified_annual_values", control["status"])
        self.assertEqual("current_annual_values_human_entitlement_review_required", control["gate"])
        self.assertEqual("below_10_smlmv", control["indemnity_salary_band"])
        self.assertEqual(3_501_810, control["transport_threshold"])
        self.assertEqual(17_509_050, control["indemnity_10_smlmv_threshold"])
        self.assertTrue(any("no prueba" in warning.casefold() for warning in control["warnings"]))

    def test_wrong_transport_amount_blocks_parameter_reuse(self):
        answers, result = labor_fixture()
        answers["transport_aid"] = 250_000
        result["calculation"]["cesantias_base"] = 3_250_000
        result["calculation"]["prima_base"] = 3_250_000
        control = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 8, 10))
        self.assertEqual("needs_parameter_reverification", control["status"])
        self.assertEqual("release_block_labor_parameter_reverification_required", control["gate"])
        self.assertTrue(any("no coincide" in reason for reason in control["reasons"]))

    def test_transport_with_salary_above_two_smlmv_blocks(self):
        answers, result = labor_fixture()
        answers["monthly_salary"] = 3_600_000
        result["calculation"]["cesantias_base"] = 3_849_095
        result["calculation"]["prima_base"] = 3_849_095
        result["calculation"]["vacation_base"] = 3_600_000
        result["calculation"]["indemnity_base"] = 3_600_000
        control = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 8, 10))
        self.assertEqual("needs_parameter_reverification", control["status"])
        self.assertTrue(any("supera dos SMLMV" in reason for reason in control["reasons"]))

    def test_cross_year_relationship_requires_periodization(self):
        answers, result = labor_fixture()
        answers["start_date"] = "2025-12-01"
        control = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 8, 10))
        self.assertEqual("needs_parameter_reverification", control["status"])
        self.assertTrue(any("cruza años" in reason for reason in control["reasons"]))

    def test_current_wage_status_has_shorter_litigation_review_window(self):
        answers, result = labor_fixture()
        current = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 9, 9))
        self.assertEqual("verified_annual_values", current["status"])
        stale = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 9, 10))
        self.assertEqual("needs_parameter_reverification", stale["status"])
        self.assertTrue(any("estado procesal" in reason.casefold() for reason in stale["reasons"]))

    def test_inconsistent_30_day_indemnity_band_is_blocked(self):
        answers, result = labor_fixture()
        result = deepcopy(result)
        result["calculation"]["indemnity_days"] = 20
        control = evaluate_labor_parameters_m334(answers, result, as_of=date(2026, 8, 10))
        self.assertEqual("needs_parameter_reverification", control["status"])
        self.assertTrue(any("30 días" in reason for reason in control["reasons"]))

    def test_parameter_sensitive_documents_get_combined_release_gate(self):
        current = _specs()
        by_kind = {spec["kind"]: spec for spec in current if spec.get("kind") in LABOR_KINDS}
        for kind in ("calculation", "claim", "labor_diagnostic"):
            self.assertEqual("verified_annual_values", by_kind[kind]["labor_parameter_status_m334"])
            self.assertEqual("human_legal_and_qa_review_required", by_kind[kind]["release_gate_m334"])
        self.assertEqual("not_material_to_this_piece", by_kind["labor_deadline_calendar"]["labor_parameter_status_m334"])

    def test_structured_ids_urls_and_parameter_metadata_never_enter_public_sections(self):
        for spec in _specs():
            if spec.get("kind") not in LABOR_KINDS:
                continue
            public = json.dumps(spec.get("sections") or [], ensure_ascii=False)
            internal = json.dumps(spec.get("internal_review_sections") or [], ensure_ascii=False)
            for forbidden in (
                "CO-CST-LIQUIDATION-2026",
                "CO-LEY50-ART99-CESANTIAS",
                "CO-LEY2466-ART62-PRESCRIPTION",
                "suin-juriscol.gov.co",
                "consejodeestado.gov.co",
                "operative_pending_merits_decision_after_revocation_of_provisional_suspension",
            ):
                self.assertNotIn(forbidden, public, spec.get("kind"))
            self.assertIn("CONTROL DE FUENTES JURÍDICAS Y PARÁMETROS M33.4", internal)

    def test_normative_review_window_fails_closed_independently(self):
        answers, result = labor_fixture()
        ids = labor_source_ids("claim", answers, result)
        manifest = build_legal_source_manifest(ids, as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])
        self.assertEqual("release_block_reverification_required", manifest["legal_effect"])

    def test_red_case_preserves_existing_gate_without_m334_mutation(self):
        current = _specs(risk="red")
        self.assertTrue(current)
        self.assertFalse(any(spec.get("legal_source_manifest") for spec in current))
        self.assertFalse(any(spec.get("labor_parameter_control_m334") for spec in current))


if __name__ == "__main__":
    unittest.main()
