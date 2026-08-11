from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import date

from legalai_platform.sast_official_domains import SAST_OFFICIAL_DOMAINS
from legalai_platform.sast_legal_source_pack import SAST_KINDS, sast_source_ids, sast_temporal_control
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from test_m33_0_wave3 import PRODUCTS, sast_fixture


class SastSourceTraceabilityM334Tests(unittest.TestCase):
    def specs(self, answers=None, result=None):
        base_answers, base_result = sast_fixture()
        return document_specs_m33_all(
            "CASE-M334-SAST", "CO-TR-001", answers or base_answers, result or base_result,
            PRODUCTS["CO-TR-001"], "2026-08-10T23:55:00-05:00", [],
        )

    def test_all_seven_sast_pieces_receive_internal_traceability_without_public_rewrite(self):
        specs = self.specs()
        scoped = [spec for spec in specs if spec.get("kind") in SAST_KINDS]
        self.assertEqual(7, len(scoped))
        for spec in scoped:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"))
            self.assertTrue(spec.get("legal_source_scope_m334", {}).get("public_sections_unchanged"))
            self.assertEqual("human_legal_and_qa_review_required", spec.get("release_gate_m334"))

    def test_current_2026_fixture_does_not_treat_performance_concept_as_current_requirement(self):
        control = sast_temporal_control(sast_fixture()[0])
        self.assertEqual("2026-07-20", control["reference_date"])
        self.assertEqual("not_current_requirement", control["performance_concept"])
        self.assertEqual("manual_2024_with_transition", control["signage_regime"])

    def test_historical_2019_case_activates_only_historical_performance_window(self):
        answers, _ = sast_fixture()
        changed = deepcopy(answers); changed["observation_date"] = "2019-06-15"
        control = sast_temporal_control(changed)
        self.assertEqual("historical_window", control["performance_concept"])
        self.assertEqual("historical_signage_regime_required", control["signage_regime"])

    def test_missing_reference_date_fails_closed(self):
        answers, _ = sast_fixture(); changed = deepcopy(answers); changed.pop("observation_date", None)
        control = sast_temporal_control(changed)
        self.assertEqual("date_required", control["performance_concept"])
        self.assertEqual("date_required", control["signage_regime"])

    def test_speed_system_gets_metrology_source_but_non_speed_system_does_not(self):
        answers, result = sast_fixture()
        speed_ids = set(sast_source_ids("sast_report", answers, result))
        self.assertIn("CO-INM-R352-2020-VELOCIDAD", speed_ids)
        changed = deepcopy(answers); changed["device_type"] = "Sistema de control de carril exclusivo"
        non_speed_ids = set(sast_source_ids("sast_report", changed, result))
        self.assertNotIn("CO-INM-R352-2020-VELOCIDAD", non_speed_ids)

    def test_record_request_has_petition_and_transparency_sources(self):
        answers, result = sast_fixture()
        ids = set(sast_source_ids("sast_record_request", answers, result))
        self.assertTrue({"CO-LEY1755-PETICION-SAST", "CO-LEY1712-TRANSPARENCIA-SAST"}.issubset(ids))

    def test_transport_public_exception_is_source_not_automatic_factual_conclusion(self):
        answers, result = sast_fixture()
        ids = set(sast_source_ids("sast_report", answers, result))
        self.assertIn("CO-LEY2294-ART181-SAST", ids)
        source = get_legal_source("CO-LEY2294-ART181-SAST")
        self.assertIn("solo si", source["applicability"].casefold())

    def test_every_selected_source_resolves_in_registry(self):
        answers, result = sast_fixture()
        for kind in SAST_KINDS:
            for source_id in sast_source_ids(kind, answers, result):
                self.assertEqual(source_id, get_legal_source(source_id)["id"])

    def test_public_sections_do_not_leak_source_ids_urls_or_manifest(self):
        public = json.dumps([spec.get("sections") for spec in self.specs()], ensure_ascii=False)
        self.assertNotIn("CO-INM-2026-DESEMPENO", public)
        self.assertNotIn("source_manifest_status_m334", public)
        self.assertNotIn("https://inm.gov.co", public)

    def test_official_domain_extension_is_narrow(self):
        self.assertIn("inm.gov.co", SAST_OFFICIAL_DOMAINS)
        self.assertIn("mintransporte.gov.co", SAST_OFFICIAL_DOMAINS)
        self.assertNotIn("google.com", SAST_OFFICIAL_DOMAINS)

    def test_source_freshness_timebomb(self):
        answers, result = sast_fixture()
        manifest = build_legal_source_manifest(sast_source_ids("sast_report", answers, result), as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])


if __name__ == "__main__":
    unittest.main()
