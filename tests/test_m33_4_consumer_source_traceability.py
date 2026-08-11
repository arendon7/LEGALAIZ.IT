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

from legalai_platform.consumer_legal_source_pack import CONSUMER_KINDS, consumer_source_ids
from legalai_platform.legal_source_registry import build_legal_source_manifest, get_legal_source
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_consumer_legal_finalize import consumer_route_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS


MECHANISMS = {
    "warranty_claim": "CO-D735-GARANTIA",
    "withdrawal_notice": "CO-CC-C192-2026",
    "payment_reversal_request": "CO-D587-REVERSAL",
    "recurring_debit_revocation": "CO-D587-REVERSAL",
    "ecommerce_non_delivery_termination": "CO-LEY2439-ECOMMERCE",
}


def _specs(selected: str, *, risk: str = "yellow") -> list[dict]:
    answers, result = consumer_route_fixture(selected)
    result["risk"] = risk
    return document_specs_m33_all(
        "CASE-M334-CONSUMER",
        "CO-CD-003",
        answers,
        result,
        PRODUCTS["CO-CD-003"],
        "2026-08-10T20:15:00-05:00",
        [],
    )


class ConsumerSourceTraceabilityM334Tests(unittest.TestCase):
    def test_recent_retract_decision_is_precise_and_current(self):
        source = get_legal_source("CO-CC-C192-2026")
        self.assertEqual("constitutional_decision", source.get("source_kind"))
        self.assertIn("24/06/2026", source["observed_status"])
        self.assertIn("15 días calendario", source["observed_status"])
        self.assertIn("condicionamiento vinculante", source["applicability"])

    def test_every_source_id_resolves_in_canonical_registry(self):
        for selected in MECHANISMS:
            for kind in CONSUMER_KINDS:
                with self.subTest(selected=selected, kind=kind):
                    for source_id in consumer_source_ids(kind, selected):
                        source = get_legal_source(source_id)
                        self.assertEqual(source_id, source["id"])

    def test_each_mechanism_gets_only_material_special_sources(self):
        for selected, expected in MECHANISMS.items():
            with self.subTest(selected=selected):
                specs = _specs(selected)
                mechanism = next(spec for spec in specs if spec.get("kind") == selected)
                ids = mechanism["legal_source_manifest"]["source_ids"]
                self.assertIn("CO-CONST-ART78", ids)
                self.assertIn("CO-LEY1480-CONSUMER", ids)
                self.assertIn(expected, ids)
                if selected != "warranty_claim":
                    self.assertNotIn("CO-D735-GARANTIA", ids)
                if selected != "withdrawal_notice":
                    self.assertNotIn("CO-CC-C192-2026", ids)

    def test_all_generated_consumer_outputs_receive_current_internal_manifests(self):
        specs = _specs("warranty_claim")
        selected = [spec for spec in specs if spec.get("kind") in CONSUMER_KINDS]
        self.assertEqual(4, len(selected))
        for spec in selected:
            self.assertEqual("M33.4", spec.get("legal_source_standard_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_status_m334"), spec.get("kind"))
            self.assertEqual("current", spec.get("source_manifest_gate_m334"), spec.get("kind"))
            self.assertEqual("warranty_claim", spec["legal_source_scope_m334"]["selected_mechanism"])

    def test_diagnosis_covers_full_decision_space_but_support_docs_follow_selected_route(self):
        specs = _specs("payment_reversal_request")
        by_kind = {spec["kind"]: spec for spec in specs if spec.get("kind") in CONSUMER_KINDS}
        diagnosis_ids = by_kind["consumer_mechanism_diagnosis"]["legal_source_manifest"]["source_ids"]
        evidence_ids = by_kind["consumer_evidence_matrix"]["legal_source_manifest"]["source_ids"]
        calendar_ids = by_kind["consumer_deadline_calendar"]["legal_source_manifest"]["source_ids"]
        self.assertIn("CO-D735-GARANTIA", diagnosis_ids)
        self.assertIn("CO-CC-C192-2026", diagnosis_ids)
        self.assertIn("CO-D587-REVERSAL", diagnosis_ids)
        self.assertIn("CO-D587-REVERSAL", evidence_ids)
        self.assertIn("CO-LEY1581-2012", evidence_ids)
        self.assertIn("CO-LEY527-ARTS6-7-14", evidence_ids)
        self.assertIn("CO-D587-REVERSAL", calendar_ids)
        self.assertNotIn("CO-D735-GARANTIA", calendar_ids)

    def test_structured_ids_urls_and_metadata_never_enter_public_sections(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                for spec in _specs(selected):
                    if spec.get("kind") not in CONSUMER_KINDS:
                        continue
                    public = json.dumps(spec.get("sections") or [], ensure_ascii=False)
                    internal = json.dumps(spec.get("internal_review_sections") or [], ensure_ascii=False)
                    for forbidden in (
                        "CO-CONST-ART78",
                        "CO-LEY1480-CONSUMER",
                        "CO-D587-REVERSAL",
                        "CO-CC-C192-2026",
                        "suin-juriscol.gov.co",
                    ):
                        self.assertNotIn(forbidden, public, spec.get("kind"))
                    self.assertIn("CONTROL DE FUENTES JURÍDICAS M33.4", internal)

    def test_retract_sources_include_ley2439_and_c192_but_not_reversal_regulation(self):
        ids = consumer_source_ids("withdrawal_notice", "withdrawal_notice")
        self.assertIn("CO-LEY2439-ECOMMERCE", ids)
        self.assertIn("CO-CC-C192-2026", ids)
        self.assertNotIn("CO-D587-REVERSAL", ids)

    def test_review_window_fails_closed_after_due_date(self):
        ids = consumer_source_ids("payment_reversal_request", "payment_reversal_request")
        manifest = build_legal_source_manifest(ids, as_of=date(2026, 11, 9))
        self.assertEqual("needs_reverification", manifest["status"])
        self.assertTrue(manifest["stale_source_ids"])
        self.assertEqual("release_block_reverification_required", manifest["legal_effect"])

    def test_red_case_preserves_existing_gate_without_m334_mutation(self):
        specs = _specs("warranty_claim", risk="red")
        self.assertFalse(any(spec.get("legal_source_manifest") for spec in specs))
        self.assertFalse(any(spec.get("legal_source_standard_m334") for spec in specs))


if __name__ == "__main__":
    unittest.main()
