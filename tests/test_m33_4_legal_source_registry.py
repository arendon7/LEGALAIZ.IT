from __future__ import annotations

from datetime import date
import json
import unittest

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    build_legal_source_manifest,
    validate_registry,
)
from m33_document_presentation import split_internal_review_sections
from m33_services_release_polish import compose_services_m33_release
from tests.test_m33_0_services_reference import services_answers


class LegalSourceRegistryM334Tests(unittest.TestCase):
    def test_registry_is_structurally_valid_and_official_only(self):
        validate_registry()
        self.assertGreaterEqual(len(LEGAL_SOURCE_REGISTRY), 11)
        for source_id, source in LEGAL_SOURCE_REGISTRY.items():
            self.assertTrue(source_id)
            self.assertTrue(str(source["official_url"]).startswith("https://"))
            self.assertIn("verified_on", source)
            self.assertIn("review_due_on", source)
            self.assertTrue(source["topics"])

    def test_manifest_separates_current_verification_from_legal_effect(self):
        ids = ["CO-CST-ART23-2025", "CO-LEY2024-ART3", "CO-LEY1581-2012"]
        manifest = build_legal_source_manifest(ids, as_of=date(2026, 8, 10))

        self.assertEqual("M33.4", manifest["standard"])
        self.assertEqual("current", manifest["status"])
        self.assertEqual([], manifest["stale_source_ids"])
        self.assertEqual("traceability_only; human_legal_review_required", manifest["legal_effect"])
        self.assertEqual(ids, manifest["source_ids"])
        self.assertTrue(all(item["freshness_status"] == "current" for item in manifest["sources"]))

    def test_manifest_fails_closed_after_review_due_date(self):
        manifest = build_legal_source_manifest(
            ["CO-CST-ART23-2025", "CO-LEY2024-ART3"],
            as_of=date(2026, 11, 9),
        )
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertEqual(
            ["CO-CST-ART23-2025", "CO-LEY2024-ART3"],
            manifest["stale_source_ids"],
        )
        self.assertEqual("release_block_reverification_required", manifest["legal_effect"])

    def test_ci_forces_periodic_legal_reverification(self):
        self.assertLessEqual(
            date.today(),
            REVIEW_DUE_ON,
            "M33.4: venció la ventana de verificación normativa; revalidar fuentes oficiales y renovar review_due_on.",
        )

    def test_services_release_carries_auditable_manifest_without_polluting_signed_instrument(self):
        composition = compose_services_m33_release(services_answers())
        manifest = composition.get("legal_source_manifest") or {}
        self.assertEqual("M33.4", manifest.get("standard"))
        self.assertIn("CO-CST-ART23-2025", manifest.get("source_ids") or [])
        self.assertIn("CO-LEY2024-ART3", manifest.get("source_ids") or [])
        self.assertIn("CO-D1072-SGRL-SGSST", manifest.get("source_ids") or [])
        self.assertIn("CO-LEY1581-2012", manifest.get("source_ids") or [])
        self.assertIn("CO-LEY527-ARTS6-7-14", manifest.get("source_ids") or [])
        self.assertNotIn("CO-LEY2277-ART89", manifest.get("source_ids") or [])

        public, internal = split_internal_review_sections(composition.get("sections") or [])
        public_text = json.dumps(public, ensure_ascii=False)
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertNotIn("suin-juriscol.gov.co", public_text)
        self.assertNotIn("CO-CST-ART23-2025", public_text)
        self.assertIn("CO-CST-ART23-2025", internal_text)
        self.assertIn("verificada 2026-08-10", internal_text)
        self.assertIn("source_manifest_status", internal_text)

    def test_natural_person_services_adds_independent_ibc_source(self):
        answers = services_answers()
        answers["contractor"]["identification"]["type"] = "natural_person"
        composition = compose_services_m33_release(answers)
        manifest = composition["legal_source_manifest"]
        self.assertIn("CO-LEY2277-ART89", manifest["source_ids"])
        self.assertEqual("M33.4", composition["maturity_answers"]["legal_source_standard"])
        self.assertEqual(manifest["status"], composition["maturity_answers"]["legal_source_gate_m334"])


if __name__ == "__main__":
    unittest.main()
