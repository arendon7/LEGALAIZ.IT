from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from legalai_platform.debt_legal_source_pack import (
    DEBT_INTEREST_PARAMETER_KINDS,
    DEBT_KINDS,
    debt_source_ids,
    evaluate_interest_parameter_m334,
)
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_debt_legal_finalize import debt_stage_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS


STAGES = (
    "Enviar un cobro inicial",
    "Negociar una solución",
    "Acordar un plan de pago",
    "Registrar o seguir pagos",
    "Cerrar la obligación",
)


def _specs(stage: str, *, zero_balance: bool = False, risk: str = "yellow", mutate=None) -> list[dict]:
    answers, result = debt_stage_fixture(stage, zero_balance=zero_balance)
    result["risk"] = risk
    if mutate:
        mutate(answers, result)
    return document_specs_m33_all(
        "CASE-M334-DEBT",
        "CO-CD-004",
        answers,
        result,
        PRODUCTS["CO-CD-004"],
        "2026-08-10T20:45:00-05:00",
        [],
    )


class DebtSourceTraceabilityM334Tests(unittest.TestCase):
    def test_every_source_id_resolves_in_canonical_registry(self):
        for stage in STAGES:
            answers, _ = debt_stage_fixture(stage, zero_balance=stage == "Cerrar la obligación")
            for kind in DEBT_KINDS:
                with self.subTest(stage=stage, kind=kind):
                    for source_id in debt_source_ids(kind, answers):
                        source = get_legal_source(source_id)
                        self.assertEqual(source_id, source["id"])

    def test_all_generated_debt_outputs_receive_current_internal_manifests(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                current = _specs(stage, zero_balance=stage == "Cerrar la obligación")
                debt_specs = [spec for spec in current if spec.get("kind") in DEBT_KINDS]
                self.assertTrue(debt_specs)
                for spec in debt_specs:
                    self.assertEqual("M33.4", spec.get("legal_source_standard_m334"), spec.get("kind"))
                    self.assertEqual("current", spec.get("source_manifest_status_m334"), spec.get("kind"))
                    self.assertEqual("current", spec.get("source_manifest_gate_m334"), spec.get("kind"))
                    self.assertIn("interest_parameter_control_m334", spec)

    def test_promissory_note_has_title_executive_and_interest_sources(self):
        current = _specs("Acordar un plan de pago")
        note = next(spec for spec in current if spec.get("kind") == "promissory_note")
        ids = note["legal_source_manifest"]["source_ids"]
        self.assertIn("CO-COM-TITULOS-PAGARE", ids)
        self.assertIn("CO-CGP-ART422", ids)
        self.assertIn("CO-COM-INTERESES-884-886", ids)
        self.assertIn("CO-D1454-1989-INTERESES", ids)
        self.assertNotIn("CO-LEY2300-COBRANZA", ids)

    def test_collection_law_is_traced_conditionally_not_generalized(self):
        current = _specs("Enviar un cobro inicial")
        letter = next(spec for spec in current if spec.get("kind") == "collection_letter")
        ids = letter["legal_source_manifest"]["source_ids"]
        self.assertIn("CO-LEY2300-COBRANZA", ids)
        source = get_legal_source("CO-LEY2300-COBRANZA")
        self.assertEqual("conditional_scope_human_review_required", source["applicability"])
        self.assertEqual(
            "conditional_scope_human_review_required",
            letter["legal_source_scope_m334"]["collection_law_2300"],
        )

    def test_credit_reporting_source_only_activates_on_explicit_yes(self):
        answers, _ = debt_stage_fixture("Enviar un cobro inicial")
        self.assertNotIn("CO-LEY1266-REPORTING", debt_source_ids("collection_letter", answers))
        answers["credit_reporting"] = "Sí"
        self.assertIn("CO-LEY1266-REPORTING", debt_source_ids("collection_letter", answers))

    def test_demo_interest_parameter_blocks_release_even_while_law_manifest_is_current(self):
        current = _specs("Acordar un plan de pago")
        agreement = next(spec for spec in current if spec.get("kind") == "payment_agreement")
        self.assertEqual("current", agreement["source_manifest_status_m334"])
        self.assertEqual("needs_exact_period_reverification", agreement["interest_parameter_status_m334"])
        self.assertEqual(
            "release_block_interest_parameter_reverification_required",
            agreement["interest_parameter_gate_m334"],
        )
        self.assertEqual(
            "release_block_interest_parameter_reverification_required",
            agreement["release_gate_m334"],
        )
        reasons = " ".join(agreement["interest_parameter_control_m334"].get("reasons") or []).casefold()
        self.assertIn("demostrativa", reasons)
        self.assertIn("url oficial", reasons)

    def test_exact_official_july_parameter_can_pass_only_inside_its_period(self):
        answers, result = debt_stage_fixture("Acordar un plan de pago")
        answers["document_date"] = "2026-07-15"
        c = result["calculation"]
        c["interest_resolution"] = "Resolución 0965 de 2026"
        c["interest_official_url"] = "https://www.superfinanciera.gov.co/publicaciones/10116173/superfinanciera-certifica-el-interes-bancario-corriente/"
        c["interest_valid_from"] = "2026-07-01"
        c["interest_valid_to"] = "2026-07-31"
        c["interest_modality"] = "consumo y ordinario"
        c["maximum_reference_ea"] = 28.79
        control = evaluate_interest_parameter_m334(answers, result)
        self.assertEqual("verified_exact_period", control["status"])
        self.assertEqual("current_exact_period", control["gate"])

        answers["document_date"] = "2026-08-15"
        stale_period = evaluate_interest_parameter_m334(answers, result)
        self.assertEqual("needs_exact_period_reverification", stale_period["status"])
        self.assertTrue(any("fuera del período" in reason for reason in stale_period["reasons"]))

    def test_numeric_limit_without_official_resolution_and_url_never_passes(self):
        answers, result = debt_stage_fixture("Acordar un plan de pago")
        c = result["calculation"]
        c["interest_resolution"] = ""
        c["interest_official_url"] = ""
        c["maximum_reference_ea"] = 99.99
        control = evaluate_interest_parameter_m334(answers, result)
        self.assertEqual("needs_exact_period_reverification", control["status"])
        self.assertNotEqual("current_exact_period", control["gate"])

    def test_no_interest_makes_parameter_gate_not_applicable(self):
        answers, result = debt_stage_fixture("Acordar un plan de pago")
        answers["interest_agreed"] = "No"
        control = evaluate_interest_parameter_m334(answers, result)
        self.assertEqual("not_applicable", control["status"])
        self.assertEqual("not_applicable", control["gate"])

    def test_structured_ids_urls_and_parameter_metadata_never_enter_public_sections(self):
        current = _specs("Acordar un plan de pago")
        for spec in current:
            if spec.get("kind") not in DEBT_KINDS:
                continue
            public = json.dumps(spec.get("sections") or [], ensure_ascii=False)
            internal = json.dumps(spec.get("internal_review_sections") or [], ensure_ascii=False)
            for forbidden in (
                "CO-COM-TITULOS-PAGARE",
                "CO-COM-INTERESES-884-886",
                "CO-CGP-ART422",
                "suin-juriscol.gov.co",
                "superfinanciera.gov.co",
            ):
                self.assertNotIn(forbidden, public, spec.get("kind"))
            self.assertIn("CONTROL DE FUENTES JURÍDICAS Y PARÁMETROS M33.4", internal)

    def test_review_window_fails_closed_independently_of_parameter_gate(self):
        answers, _ = debt_stage_fixture("Acordar un plan de pago")
        ids = debt_source_ids("promissory_note", answers)
        manifest = build_legal_source_manifest(ids, as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])
        self.assertEqual("release_block_reverification_required", manifest["legal_effect"])

    def test_red_case_preserves_existing_gate_without_m334_mutation(self):
        current = _specs("Acordar un plan de pago", risk="red")
        self.assertTrue(current)
        self.assertFalse(any(spec.get("legal_source_manifest") for spec in current))
        self.assertFalse(any(spec.get("interest_parameter_control_m334") for spec in current))


if __name__ == "__main__":
    unittest.main()
