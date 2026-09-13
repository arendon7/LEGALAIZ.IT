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

from legalai_platform.legal_source_registry import get_legal_source
from legalai_platform.nda_legal_source_pack import NDA_BASE_SOURCE_IDS, nda_source_ids
from m33_4_nda_instrument_finalize import compose_nda_m33_instrument
from m33_document_presentation import split_internal_review_sections
from test_m33_0_nda_legal_review import nda_answers


class NdaSourceTraceabilityM334Tests(unittest.TestCase):
    def test_trade_secret_sources_are_official_and_narrowly_scoped(self):
        decision = get_legal_source("CAN-DEC486-SECRETS")
        colombian = get_legal_source("CO-LEY256-ART16")
        self.assertIn("artículos 260 a 265", decision["locator"])
        self.assertIn("comunidadandina.org", decision["official_url"])
        self.assertIn("secreto empresarial", " ".join(decision["topics"]))
        self.assertEqual("Ley 256 de 1996, artículo 16", colombian["title"])
        self.assertIn("vigente", colombian["observed_status"])
        self.assertIn("suin-juriscol.gov.co", colombian["official_url"])

    def test_default_nda_manifest_does_not_invent_personal_data_or_general_ai_law(self):
        answers = nda_answers()
        composition = compose_nda_m33_instrument(answers)
        manifest = composition.get("legal_source_manifest") or {}
        maturity = composition.get("maturity_answers") or {}

        self.assertEqual("M33.4", manifest.get("standard"))
        self.assertEqual("current", manifest.get("status"))
        self.assertEqual(NDA_BASE_SOURCE_IDS, manifest.get("source_ids"))
        self.assertNotIn("CO-LEY1581-2012", manifest.get("source_ids") or [])
        self.assertNotIn("CO-D1074-DATOS", manifest.get("source_ids") or [])
        self.assertEqual("applicable-law-only; no_general_ai_law_inferred", maturity.get("ai_legal_source_model_m334"))
        self.assertEqual("traceability_only; human_legal_review_required", manifest.get("legal_effect"))

    def test_personal_data_module_adds_only_applicable_data_sources(self):
        answers = nda_answers()
        answers["data"]["personal"] = True
        composition = compose_nda_m33_instrument(answers)
        source_ids = composition["legal_source_manifest"]["source_ids"]
        self.assertEqual(nda_source_ids(personal_data=True), source_ids)
        self.assertIn("CO-LEY1581-2012", source_ids)
        self.assertIn("CO-D1074-DATOS", source_ids)

    def test_structured_sources_remain_outside_signed_instrument(self):
        composition = compose_nda_m33_instrument(nda_answers())
        public, internal = split_internal_review_sections(composition.get("sections") or [])
        self.assertTrue(public)
        self.assertEqual(1, len(internal))

        public_text = json.dumps(public, ensure_ascii=False)
        internal_text = json.dumps(internal, ensure_ascii=False)
        for forbidden in ("CAN-DEC486-SECRETS", "CO-LEY256-ART16", "suin-juriscol.gov.co", "comunidadandina.org"):
            self.assertNotIn(forbidden, public_text)
        self.assertIn("CAN-DEC486-SECRETS", internal_text)
        self.assertIn("CO-LEY256-ART16", internal_text)
        self.assertIn("verificada 2026-08-10", internal_text)
        self.assertIn('"source_manifest_status": "current"', internal_text)

    def test_maturity_metadata_exposes_reverification_gate(self):
        composition = compose_nda_m33_instrument(nda_answers())
        maturity = composition.get("maturity_answers") or {}
        self.assertEqual("M33.4", maturity.get("legal_source_standard"))
        self.assertEqual("current", maturity.get("legal_source_gate_m334"))
        self.assertEqual(NDA_BASE_SOURCE_IDS, maturity.get("legal_source_ids_m334"))
        self.assertIn("human_legal_review_required", composition["legal_source_manifest"]["legal_effect"])


if __name__ == "__main__":
    unittest.main()
