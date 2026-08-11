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

from legalai_platform.habeas_data_legal_source_pack import HABEAS_KINDS, habeas_source_ids
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, habeas_fixture


def _specs(answers: dict, result: dict):
    return document_specs_m33_all(
        "CASE-M334-HABEAS",
        "CO-CD-001",
        answers,
        result,
        PRODUCTS["CO-CD-001"],
        "2026-08-10T19:52:00-05:00",
        [],
    )


class HabeasSourceTraceabilityM334Tests(unittest.TestCase):
    def test_transition_source_does_not_anticipate_general_law2573_regime(self):
        source = get_legal_source("CO-LEY2573-TRANSITION-2026")
        self.assertEqual("transitional_statute", source.get("source_kind"))
        self.assertIn("20/11/2026", source["observed_status"])
        self.assertIn("parágrafos 1 y 2", source["observed_status"])
        self.assertEqual("partial_immediate_only_before_2026-11-20", source.get("applicability"))
        self.assertIn("suin-juriscol.gov.co", source["official_url"])

    def test_sic_sources_are_official_and_keep_their_own_legal_weight(self):
        instruction = get_legal_source("CO-SIC-RES28170-2022")
        decision = get_legal_source("CO-SIC-RES107492-2025")
        self.assertEqual("administrative_instruction", instruction.get("source_kind"))
        self.assertEqual("administrative_decision", decision.get("source_kind"))
        self.assertIn("Circular Única", instruction["locator"])
        self.assertIn("sedeelectronica.sic.gov.co", decision["official_url"])
        self.assertIn("no equivalente", decision["applicability"])

    def test_all_seven_habeas_outputs_receive_current_internal_manifests(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        selected = [spec for spec in specs if spec.get("kind") in HABEAS_KINDS]
        self.assertEqual(7, len(selected))
        for spec in selected:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_gate_m334"), spec.get("kind"))
            self.assertEqual("human_legal_and_qa_review_required", spec.get("release_gate_m334"), spec.get("kind"))
            self.assertEqual(spec["legal_source_manifest"]["source_ids"], spec.get("legal_source_ids_m334"))
            self.assertIn("human_legal_review_required", spec["legal_source_manifest"]["legal_effect"])

    def test_sources_are_scoped_by_document_kind(self):
        answers, result = habeas_fixture()
        by_kind = {spec["kind"]: spec for spec in _specs(answers, result) if spec.get("kind") in HABEAS_KINDS}
        claim_ids = by_kind["habeas_claim"]["legal_source_manifest"]["source_ids"]
        reiteration_ids = by_kind["habeas_reiteration"]["legal_source_manifest"]["source_ids"]
        evidence_ids = by_kind["habeas_evidence_matrix"]["legal_source_manifest"]["source_ids"]
        calendar_ids = by_kind["habeas_deadline_calendar"]["legal_source_manifest"]["source_ids"]

        self.assertIn("CO-LEY2573-TRANSITION-2026", claim_ids)
        self.assertIn("CO-SIC-RES28170-2022", claim_ids)
        self.assertNotIn("CO-SIC-RES107492-2025", claim_ids)
        self.assertIn("CO-SIC-RES107492-2025", reiteration_ids)
        self.assertNotIn("CO-LEY2573-TRANSITION-2026", evidence_ids)
        self.assertIn("CO-LEY2573-TRANSITION-2026", calendar_ids)
        self.assertNotIn("CO-SIC-RES28170-2022", calendar_ids)

    def test_structured_source_ids_and_urls_never_enter_public_sections(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        for spec in specs:
            if spec.get("kind") not in HABEAS_KINDS:
                continue
            public_text = json.dumps(spec.get("sections") or [], ensure_ascii=False)
            internal_text = json.dumps(spec.get("internal_review_sections") or [], ensure_ascii=False)
            for forbidden in (
                "CO-CONST-ART15",
                "CO-LEY1266-ARTS12-13-16",
                "CO-LEY2573-TRANSITION-2026",
                "CO-SIC-RES28170-2022",
                "suin-juriscol.gov.co",
                "sedeelectronica.sic.gov.co",
            ):
                self.assertNotIn(forbidden, public_text, spec.get("kind"))
            self.assertIn("CONTROL DE FUENTES JURÍDICAS M33.4", internal_text)
            self.assertIn("verificada 2026-08-10", internal_text)

    def test_review_window_fails_closed_after_due_date(self):
        source_ids = habeas_source_ids("habeas_claim")
        manifest = build_legal_source_manifest(source_ids, as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])
        self.assertEqual("release_block_reverification_required", manifest["legal_effect"])

    def test_unverified_resolution_18924_is_not_promoted_to_registry_or_manifest(self):
        answers, result = habeas_fixture()
        payload = json.dumps(_specs(answers, result), ensure_ascii=False)
        self.assertNotIn("18924", payload)
        with self.assertRaises(KeyError):
            get_legal_source("CO-SIC-RES18924-2026")

    def test_red_case_preserves_existing_risk_gate_without_m334_mutation(self):
        answers, result = habeas_fixture()
        result["risk"] = "red"
        specs = _specs(answers, result)
        self.assertFalse(any(spec.get("legal_source_manifest") for spec in specs))
        self.assertFalse(any(spec.get("legal_source_standard_m334") for spec in specs))
        self.assertFalse(any(spec.get("release_gate_m334") for spec in specs))


if __name__ == "__main__":
    unittest.main()
