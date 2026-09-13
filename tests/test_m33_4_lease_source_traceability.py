from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from co_ar_001_test_fixtures_v249 import complete_answers
from legalai_platform.lease_legal_source_pack import LEASE_SOURCE_IDS
from legalai_platform.legal_source_registry import get_legal_source
from m33_document_presentation import split_internal_review_sections
from m33_lease_instrument_finalize import compose_lease_m33_instrument


class LeaseSourceTraceabilityM334Tests(unittest.TestCase):
    def test_lease_manifest_is_current_and_complete(self):
        composition = compose_lease_m33_instrument(complete_answers())
        manifest = composition.get("legal_source_manifest") or {}

        self.assertEqual("M33.4", manifest.get("standard"))
        self.assertEqual("current", manifest.get("status"))
        self.assertEqual(LEASE_SOURCE_IDS, manifest.get("source_ids"))
        self.assertEqual([], manifest.get("stale_source_ids"))
        self.assertEqual("traceability_only; human_legal_review_required", manifest.get("legal_effect"))

        expected = {
            "CO-LEY820-2003",
            "CO-D3130-2003",
            "CO-D1077-ARRENDAMIENTO",
            "CO-LEY675-2001",
            "CO-CC-ARRENDAMIENTO",
            "CO-LEY1581-2012",
            "CO-D1074-DATOS",
            "CO-LEY527-ARTS6-7-14",
            "CO-CC-C426-2023",
        }
        self.assertEqual(expected, set(manifest["source_ids"]))

    def test_compiled_decree_is_not_misrepresented_as_current_standalone_rule(self):
        source = get_legal_source("CO-D3130-2003")
        self.assertIn("compilado en el Decreto 1077 de 2015", source["observed_status"])
        current_compilation = get_legal_source("CO-D1077-ARRENDAMIENTO")
        self.assertIn("vigente", current_compilation["observed_status"])

    def test_constitutional_caucion_source_is_official_and_narrowly_described(self):
        source = get_legal_source("CO-CC-C426-2023")
        self.assertEqual("Corte Constitucional de Colombia", source["authority"])
        self.assertIn("artículo 22", source["locator"])
        self.assertIn("por los cargos examinados", source["locator"])
        self.assertIn("corteconstitucional.gov.co", source["official_url"])

    def test_internal_control_contains_structured_ids_but_signed_sections_do_not(self):
        composition = compose_lease_m33_instrument(complete_answers())
        public, internal = split_internal_review_sections(composition.get("sections") or [])
        self.assertTrue(public)
        self.assertEqual(1, len(internal))

        public_text = json.dumps(public, ensure_ascii=False)
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertNotIn("CO-LEY820-2003", public_text)
        self.assertNotIn("suin-juriscol.gov.co", public_text)
        self.assertNotIn("corteconstitucional.gov.co", public_text)
        self.assertIn("CO-LEY820-2003", internal_text)
        self.assertIn("CO-D1077-ARRENDAMIENTO", internal_text)
        self.assertIn("CO-CC-C426-2023", internal_text)
        self.assertIn("verificada 2026-08-10", internal_text)
        self.assertIn('"source_manifest_status": "current"', internal_text)

    def test_maturity_metadata_exposes_release_gate_without_certifying_legality(self):
        composition = compose_lease_m33_instrument(complete_answers())
        maturity = composition.get("maturity_answers") or {}
        self.assertEqual("M33.4", maturity.get("legal_source_standard"))
        self.assertEqual("current", maturity.get("legal_source_gate_m334"))
        self.assertEqual(LEASE_SOURCE_IDS, maturity.get("legal_source_ids_m334"))
        self.assertIn("human_legal_review_required", composition["legal_source_manifest"]["legal_effect"])


if __name__ == "__main__":
    unittest.main()
