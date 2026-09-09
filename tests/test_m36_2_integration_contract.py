from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M362IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m361_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m36_2.py")
        self.assertIn("from legalai_platform.http_handler_m36_2 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m36_1 import Handler as BaseHandler", handler)
        self.assertIn("return super().do_GET()", handler)
        self.assertIn("return super().do_POST()", handler)

    def test_write_route_is_exact_admin_reconcile_with_origin_and_csrf(self):
        handler = self.read("legalai_platform/http_handler_m36_2.py")
        routes = self.read("legalai_platform/routes/m36_2_review_reconciliation_routes.py")
        self.assertIn('PREFIX = "/api/m36/review-lifecycle"', routes)
        self.assertIn('parts[2] != "reconcile"', routes)
        self.assertIn("require_origin", handler)
        self.assertIn("require_user", handler)
        self.assertIn("require_csrf", handler)
        self.assertNotIn('data.get("target")', routes)
        self.assertNotIn('payload.get("target")', routes)

    def test_canonical_m360_review_state_is_consumed_not_reinvented(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn('FULFILLMENT_REVIEW_STATE = "EN_REVISION_JURIDICA"', source)
        self.assertNotIn('!= "READY_FOR_REVIEW"', source)
        self.assertIn("m36_fulfillment_intake", source)
        self.assertIn("m36_professional_assignment", source)

    def test_human_m32_approvals_are_source_of_truth_and_all_desks_are_required(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn('item.get("legal_decision") == "approve"', source)
        self.assertIn('item.get("qa_decision") == "approve"', source)
        self.assertIn("all(", source)
        self.assertIn("LEGAL_APPROVAL_MISMATCH", source)
        self.assertIn("QA_APPROVAL_MISMATCH", source)
        self.assertIn("ASSIGNMENT_DRIFT", source)
        self.assertIn("DUAL_APPROVAL_INVALID", source)

    def test_system_actor_does_not_impersonate_human_approvers(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn('SYSTEM_ACTOR_ID = "system-m36-2"', source)
        self.assertIn('"human_legal_approver_id": legal_approver', source)
        self.assertIn('"human_qa_approver_id": qa_approver', source)
        self.assertIn('"derived_state_is_not_new_legal_approval": True', source)
        self.assertIn('"system_actor_does_not_impersonate_approvers": True', source)

    def test_delivery_is_explicitly_outside_m362(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn('if target == "ENTREGADO"', source)
        self.assertIn("DELIVERY_OUT_OF_SCOPE", source)
        self.assertIn('"automatic_delivery": False', source)
        self.assertIn('"delivery_requires_separate_gate": True', source)
        self.assertIn('"delivery_gate_ready"', source)

    def test_correction_requires_review_material_not_m326_operational_churn(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn("def _review_material", source)
        self.assertIn("def _changed_since_event", source)
        self.assertIn('"approval_audit_last_hash"', source)
        review_material = source[source.index("def _review_material"):source.index("def _changed_since_event")]
        self.assertNotIn('"operations_audit_last_hash"', review_material)
        self.assertIn("CORRECTION_EVIDENCE_NOT_CHANGED", source)

    def test_reconciliation_history_is_hash_linked_and_public_model_hides_evidence_payload(self):
        source = self.read("legalai_platform/review_reconciliation_m36_2.py")
        self.assertIn("previous_hash TEXT NOT NULL", source)
        self.assertIn("event_hash TEXT NOT NULL UNIQUE", source)
        self.assertIn("RECONCILIATION_CHAIN_INVALID", source)
        history_select = 'SELECT id,sequence,from_state,to_state,aggregate_state,initiated_by,'
        self.assertIn(history_select, source)
        public_history = source[source.index("def history"):]
        self.assertNotIn('"evidence_json":', public_history)
        self.assertNotIn('"evidence_fingerprint":', public_history)

    def test_observability_uses_state_and_ids_not_legal_payloads_or_hashes(self):
        routes = self.read("legalai_platform/routes/m36_2_review_reconciliation_routes.py")
        self.assertIn("aggregate_state", routes)
        self.assertIn("applied_count", routes)
        for forbidden in ("problem_statement", "answers", "revision_sha256", "record_hash", "evidence_json"):
            self.assertNotIn(forbidden, routes)

    def test_http_smoke_is_wired_after_m361(self):
        smoke = self.read("tools/m36_2_http_smoke.py") if (ROOT / "tools/m36_2_http_smoke.py").is_file() else ""
        self.assertIn("M36.2 HTTP smoke PASS", smoke)
        self.assertIn("/api/m36/review-lifecycle/cases/", smoke)
        ci = self.read(".github/workflows/ci.yml")
        self.assertIn("python tools/m36_1_http_smoke.py", ci)
        self.assertIn("python tools/m36_2_http_smoke.py", ci)
        self.assertLess(ci.index("python tools/m36_1_http_smoke.py"), ci.index("python tools/m36_2_http_smoke.py"))


if __name__ == "__main__":
    unittest.main()
