from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import date

from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from legalai_platform.traffic_legal_source_pack import TRAFFIC_KINDS, traffic_case_control, traffic_source_ids
from legalai_platform.traffic_official_domains import TRAFFIC_OFFICIAL_DOMAINS
from m33_wave3_runtime import document_specs_m33_all
from test_m33_0_wave3 import PRODUCTS, traffic_fixture


class TrafficSourceTraceabilityM334Tests(unittest.TestCase):
    def specs(self, answers=None, result=None):
        base_answers, base_result = traffic_fixture()
        return document_specs_m33_all(
            "CASE-M334-TRAFFIC",
            "CO-TR-002",
            answers or base_answers,
            result or base_result,
            PRODUCTS["CO-TR-002"],
            "2026-08-11T00:10:00-05:00",
            [],
        )

    def test_eight_traffic_outputs_receive_m334_without_public_rewrite(self):
        specs = self.specs()
        self.assertEqual(8, len(specs))
        self.assertEqual(TRAFFIC_KINDS, {str(spec.get("kind") or "") for spec in specs})
        for spec in specs:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"))
            self.assertTrue(spec.get("legal_source_scope_m334", {}).get("public_sections_unchanged"))
            if spec.get("kind") == "traffic_revocation_request":
                self.assertEqual("release_block_verified_sanction_act_required", spec.get("release_gate_m334"))
            elif spec.get("kind") == "traffic_registry_correction":
                self.assertEqual("release_block_registry_source_act_required", spec.get("release_gate_m334"))
            else:
                self.assertEqual("release_block_critical_human_review_required", spec.get("release_gate_m334"))

    def test_owner_sources_keep_c038_and_c321_together(self):
        answers, result = traffic_fixture()
        ids = set(traffic_source_ids("traffic_hearing_request", answers, result))
        self.assertTrue({
            "CO-LEY2161-ART10-PROPIETARIO",
            "CO-D998-2022-PROPIETARIO",
            "CO-CC-C038-2020",
            "CO-CC-C321-2022",
        }.issubset(ids))
        c038 = get_legal_source("CO-CC-C038-2020")
        c321 = get_legal_source("CO-CC-C321-2022")
        self.assertIn("mera titularidad", c038["applicability"].casefold())
        self.assertIn("no autoriza", c321["applicability"].casefold())

    def test_case_control_never_converts_title_into_automatic_liability(self):
        control = traffic_case_control(traffic_fixture()[0])
        owner = control["owner_liability"]
        self.assertFalse(owner["automatic_from_title"])
        self.assertFalse(owner["third_party_conduct_imputed_from_title"])
        self.assertTrue(owner["own_statutory_duty_requires_culpability_proof"])
        self.assertTrue(owner["administrative_contraventional_process_required"])

    def test_late_actual_knowledge_and_address_difference_remain_evidentiary_not_nullity(self):
        control = traffic_case_control(traffic_fixture()[0])
        self.assertEqual("does_not_automatically_equal_valid_notification", control["late_actual_knowledge_effect"])
        self.assertEqual("apparent_difference_requires_historical_runt_and_postal_proof", control["address_status"])
        self.assertEqual("no_automatic_nullity_liability_prescription_revocation_or_registry_correction", control["legal_effect"])

    def test_caducity_and_prescription_fail_closed_with_demo_dates(self):
        control = traffic_case_control(traffic_fixture()[0])
        self.assertEqual("verified_detection_and_sanction_act_dates_required", control["caducity_control"])
        self.assertEqual("verified_payment_order_notice_required", control["prescription_control"])
        self.assertFalse(control["revocation_ready"])

    def test_verified_dates_only_open_human_evaluation_not_automatic_expiry(self):
        answers, _ = traffic_fixture()
        changed = deepcopy(answers)
        changed["sanction_resolution"] = "Resolución 123 de 2025"
        changed["sanction_date"] = "2025-08-01"
        changed["payment_order_date"] = "2026-01-10"
        control = traffic_case_control(changed)
        self.assertEqual("dates_available_human_legal_evaluation_required", control["caducity_control"])
        self.assertEqual("payment_order_date_available_notice_and_interruptive_effect_must_be_verified", control["prescription_control"])
        self.assertTrue(control["revocation_ready"])

    def test_notification_claim_gets_photodetection_and_cpaca_notification_sources(self):
        answers, result = traffic_fixture()
        ids = set(traffic_source_ids("traffic_notification_claim", answers, result))
        self.assertTrue({
            "CO-LEY1843-FOTODETECCION",
            "CO-MT-VALIDACION-10D",
            "CO-CPACA-NOTIF-67-69",
        }.issubset(ids))
        self.assertNotIn("CO-CPACA-REVOC-93-96", ids)

    def test_revocation_gets_cpaca_and_limitation_sources_but_remains_blocked_without_act(self):
        answers, result = traffic_fixture()
        ids = set(traffic_source_ids("traffic_revocation_request", answers, result))
        self.assertTrue({"CO-CPACA-REVOC-93-96", "CO-LEY769-159-161", "CO-LEY1843-FOTODETECCION"}.issubset(ids))
        rev = next(spec for spec in self.specs() if spec.get("kind") == "traffic_revocation_request")
        self.assertFalse(rev["traffic_case_control_m334"]["revocation_ready"])
        self.assertEqual("release_block_verified_sanction_act_required", rev["release_gate_m334"])

    def test_registry_correction_requires_source_act_and_uses_runt_simit_regime(self):
        answers, result = traffic_fixture()
        ids = set(traffic_source_ids("traffic_registry_correction", answers, result))
        self.assertTrue({"CO-LEY769-RUNT-SIMIT", "CO-LEY1755-PETICION-TRANSITO"}.issubset(ids))
        registry = next(spec for spec in self.specs() if spec.get("kind") == "traffic_registry_correction")
        self.assertFalse(registry["traffic_case_control_m334"]["registry_correction_ready"])
        self.assertEqual("release_block_registry_source_act_required", registry["release_gate_m334"])

    def test_record_request_gets_petition_source(self):
        answers, result = traffic_fixture()
        ids = set(traffic_source_ids("traffic_record_request", answers, result))
        self.assertIn("CO-LEY1755-PETICION-TRANSITO", ids)
        self.assertIn("CO-LEY769-RUNT-SIMIT", ids)

    def test_every_selected_source_resolves_in_registry(self):
        answers, result = traffic_fixture()
        for kind in TRAFFIC_KINDS:
            for source_id in traffic_source_ids(kind, answers, result):
                self.assertEqual(source_id, get_legal_source(source_id)["id"])

    def test_public_sections_do_not_leak_internal_source_metadata(self):
        public = json.dumps([spec.get("sections") for spec in self.specs()], ensure_ascii=False)
        for forbidden in (
            "CO-CC-C038-2020",
            "source_manifest_status_m334",
            "release_block_registry_source_act_required",
            "https://www.corteconstitucional.gov.co",
        ):
            self.assertNotIn(forbidden, public)

    def test_official_domain_extension_is_narrow(self):
        self.assertIn("corteconstitucional.gov.co", TRAFFIC_OFFICIAL_DOMAINS)
        self.assertIn("mintransporte.gov.co", TRAFFIC_OFFICIAL_DOMAINS)
        self.assertNotIn("google.com", TRAFFIC_OFFICIAL_DOMAINS)
        self.assertNotIn("ambitojuridico.com", TRAFFIC_OFFICIAL_DOMAINS)

    def test_source_freshness_timebomb(self):
        answers, result = traffic_fixture()
        manifest = build_legal_source_manifest(
            traffic_source_ids("traffic_diagnostic", answers, result),
            as_of=date(2026, 11, 9),
        )
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])


if __name__ == "__main__":
    unittest.main()
