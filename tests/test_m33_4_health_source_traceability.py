from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import date

from m33_4_health_source_finalize import _sector_term
from legalai_platform.health_official_domains import HEALTH_OFFICIAL_DOMAINS
from legalai_platform.health_legal_source_pack import HEALTH_KINDS, health_source_ids
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from test_m33_0_wave3 import PRODUCTS, health_fixture


class HealthSourceTraceabilityM334Tests(unittest.TestCase):
    def specs(self, answers=None, result=None):
        base_answers, base_result = health_fixture()
        return document_specs_m33_all(
            "CASE-M334-HEALTH",
            "CO-SA-001",
            answers or base_answers,
            result or base_result,
            PRODUCTS["CO-SA-001"],
            "2026-08-10T23:45:00-05:00",
            [],
        )

    def test_all_seven_health_pieces_receive_internal_m334_traceability_even_on_red_risk(self):
        specs = self.specs()
        health_specs = [spec for spec in specs if spec.get("kind") in HEALTH_KINDS]
        self.assertEqual(7, len(health_specs))
        for spec in health_specs:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"))
            self.assertEqual("release_block_critical_human_review_required", spec.get("release_gate_m334"))
            self.assertTrue(spec.get("legal_source_scope_m334", {}).get("public_sections_unchanged"))

    def test_prioritized_fixture_uses_48_continuous_hours_as_maximum_not_waiting_permission(self):
        specs = self.specs()
        for kind in {"health_diagnostic", "health_petition", "health_reiteration", "health_supersalud", "health_calendar"}:
            spec = next(item for item in specs if item.get("kind") == kind)
            control = spec["health_sector_term_control_m334"]
            self.assertEqual(48, control["hours"])
            self.assertEqual("hours_continuous_maximum", control["counting"])
            self.assertIn("not_permission_to_delay", control["legal_effect"])

    def test_sector_term_guard_maps_vital_simple_and_unclassified_fail_closed(self):
        self.assertEqual(24, _sector_term("vital")["hours"])
        self.assertEqual(72, _sector_term("simple")["hours"])
        unknown = _sector_term("unclassified")
        self.assertIsNone(unknown["hours"])
        self.assertEqual("classification_required", unknown["status"])

    def test_history_request_has_specific_record_privacy_and_interoperability_sources(self):
        answers, result = health_fixture()
        ids = set(health_source_ids("health_history_request", answers, result))
        self.assertTrue({
            "CO-LEY1751-SALUD",
            "CO-RES1995-HISTORIA",
            "CO-RES839-2017-HISTORIA",
            "CO-LEY1581-2012",
            "CO-LEY2015-HCE",
        }.issubset(ids))

    def test_medication_case_has_recent_constitutional_references_without_making_tutela_automatic(self):
        answers, result = health_fixture()
        diagnostic = set(health_source_ids("health_diagnostic", answers, result))
        petition = set(health_source_ids("health_petition", answers, result))
        self.assertIn("CO-CC-T125-2026-SALUD", diagnostic)
        self.assertIn("CO-CC-T125-2026-SALUD", petition)
        self.assertIn("CO-CC-T008-2025-SALUD", diagnostic)
        self.assertIn("CO-CP86-TUTELA", diagnostic)
        self.assertNotIn("CO-CP86-TUTELA", petition)

    def test_supersalud_administrative_and_jurisdictional_sources_remain_distinct(self):
        answers, result = health_fixture()
        supersalud = set(health_source_ids("health_supersalud", answers, result))
        self.assertIn("CO-SNS-CIRC10-2023-PQR", supersalud)
        self.assertIn("CO-LEY1949-ART6-SNS", supersalud)
        self.assertNotEqual(
            get_legal_source("CO-SNS-CIRC10-2023-PQR")["source_kind"],
            get_legal_source("CO-LEY1949-ART6-SNS")["source_kind"],
        )

    def test_every_source_selected_by_every_health_kind_resolves_in_registry(self):
        answers, result = health_fixture()
        for kind in HEALTH_KINDS:
            for source_id in health_source_ids(kind, answers, result):
                self.assertEqual(source_id, get_legal_source(source_id)["id"])

    def test_official_domain_extension_is_strictly_sectoral(self):
        self.assertIn("www.supersalud.gov.co", HEALTH_OFFICIAL_DOMAINS)
        self.assertIn("www.corteconstitucional.gov.co", HEALTH_OFFICIAL_DOMAINS)
        self.assertNotIn("google.com", HEALTH_OFFICIAL_DOMAINS)
        self.assertNotIn("wikipedia.org", HEALTH_OFFICIAL_DOMAINS)

    def test_public_sections_do_not_leak_internal_ids_urls_or_manifest(self):
        specs = self.specs()
        public = json.dumps([spec.get("sections") for spec in specs], ensure_ascii=False)
        self.assertNotIn("CO-SNS-CIRC10-2023-PQR", public)
        self.assertNotIn("CO-CC-T125-2026-SALUD", public)
        self.assertNotIn("source_manifest_status_m334", public)
        self.assertNotIn("https://www.suin-juriscol.gov.co", public)

    def test_source_freshness_timebomb_blocks_after_review_window(self):
        answers, result = health_fixture()
        ids = health_source_ids("health_petition", answers, result)
        manifest = build_legal_source_manifest(ids, as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])

    def test_active_tutela_adds_tutela_sources_to_followup_without_changing_public_generation(self):
        answers, result = health_fixture()
        changed = deepcopy(answers)
        changed["active_tutela"] = "Sí"
        ids = set(health_source_ids("health_reiteration", changed, result))
        self.assertTrue({"CO-CP86-TUTELA", "CO-D2591-TUTELA"}.issubset(ids))
        specs = self.specs(changed, result)
        self.assertEqual(7, len([spec for spec in specs if spec.get("kind") in HEALTH_KINDS]))


if __name__ == "__main__":
    unittest.main()
