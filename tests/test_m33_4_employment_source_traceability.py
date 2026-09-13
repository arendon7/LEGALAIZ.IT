from __future__ import annotations

import json
import unittest

from legalai_platform.employment_legal_source_pack import EMPLOYMENT_SOURCE_IDS
from legalai_platform.legal_source_registry import get_legal_source
from m33_document_presentation import split_internal_review_sections
from m33_employment_instrument_finalize import compose_employment_m33_instrument
from tests.test_m33_0_contractual_wave import employment_answers


class EmploymentSourceTraceabilityM334Tests(unittest.TestCase):
    def test_employment_manifest_is_current_and_complete(self):
        composition = compose_employment_m33_instrument(employment_answers())
        manifest = composition.get("legal_source_manifest") or {}
        self.assertEqual("M33.4", manifest.get("standard"))
        self.assertEqual("current", manifest.get("status"))
        self.assertEqual(EMPLOYMENT_SOURCE_IDS, manifest.get("source_ids"))
        self.assertEqual([], manifest.get("stale_source_ids"))
        self.assertEqual("traceability_only; human_legal_review_required", manifest.get("legal_effect"))

        expected = {
            "CO-CST-EMPLOYMENT-2026",
            "CO-LEY2466-2025",
            "CO-LEY2101-2021",
            "CO-LEY2191-2022",
            "CO-D1072-SGRL-SGSST",
            "CO-LEY1010-2006",
            "CO-LEY1581-2012",
            "CO-D1074-DATOS",
            "CO-LEY527-ARTS6-7-14",
        }
        self.assertEqual(expected, set(manifest["source_ids"]))

    def test_reform_and_jornada_sources_are_individually_traceable(self):
        reform = get_legal_source("CO-LEY2466-2025")
        jornada = get_legal_source("CO-LEY2101-2021")
        desconexion = get_legal_source("CO-LEY2191-2022")
        self.assertIn("reforma laboral", reform["title"].casefold() + " " + " ".join(reform["topics"]).casefold())
        self.assertIn("42 horas", " ".join(jornada["topics"]))
        self.assertEqual("vigente", desconexion["observed_status"])

    def test_internal_sources_do_not_pollute_signed_employment_instrument(self):
        composition = compose_employment_m33_instrument(employment_answers())
        public, internal = split_internal_review_sections(composition.get("sections") or [])
        self.assertTrue(public)
        self.assertEqual(1, len(internal))

        public_text = json.dumps(public, ensure_ascii=False)
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertNotIn("CO-LEY2466-2025", public_text)
        self.assertNotIn("suin-juriscol.gov.co", public_text)
        self.assertIn("CO-LEY2466-2025", internal_text)
        self.assertIn("CO-LEY2101-2021", internal_text)
        self.assertIn("CO-LEY2191-2022", internal_text)
        self.assertIn("verificada 2026-08-10", internal_text)
        self.assertIn('"source_manifest_status": "current"', internal_text)

    def test_maturity_metadata_exposes_reverification_gate(self):
        composition = compose_employment_m33_instrument(employment_answers())
        maturity = composition.get("maturity_answers") or {}
        self.assertEqual("M33.4", maturity.get("legal_source_standard"))
        self.assertEqual("current", maturity.get("legal_source_gate_m334"))
        self.assertEqual(EMPLOYMENT_SOURCE_IDS, maturity.get("legal_source_ids_m334"))
        self.assertIn("human_legal_review_required", composition["legal_source_manifest"]["legal_effect"])


if __name__ == "__main__":
    unittest.main()
