from __future__ import annotations

from pathlib import Path
import unittest


class M361IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.center = (cls.root / "legalai_platform" / "professional_assignment_m36_1.py").read_text(encoding="utf-8")
        cls.routes = (cls.root / "legalai_platform" / "routes" / "m36_1_assignment_routes.py").read_text(encoding="utf-8")
        cls.handler = (cls.root / "legalai_platform" / "http_handler_m36_1.py").read_text(encoding="utf-8")
        cls.run_source = (cls.root / "run.py").read_text(encoding="utf-8")
        cls.smoke = (cls.root / "tools" / "m36_1_http_smoke.py").read_text(encoding="utf-8")
        cls.ci = (cls.root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m360_handler(self):
        self.assertIn("from legalai_platform.http_handler_m36_1 import Handler", self.run_source)
        self.assertIn("http_handler_m36_0 import Handler", self.run_source)
        self.assertIn("from legalai_platform.http_handler_m36_0 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_GET()", self.handler)
        self.assertIn("return super().do_POST()", self.handler)

    def test_assignment_is_manual_case_level_saga_not_matching_algorithm(self):
        self.assertIn("m36_professional_assignment", self.center)
        self.assertIn("completed_desk_ids_json", self.center)
        self.assertIn("notified_desk_ids_json", self.center)
        self.assertIn('"manual_selection_required": True', self.center)
        self.assertIn('"automatic_matching": False', self.center)
        self.assertNotIn("recommended_specialist", self.center)
        self.assertNotIn("auto_assign", self.center)

    def test_existing_m32_assignment_and_notification_engines_are_reused(self):
        self.assertIn("ApprovalDeskOperations", self.center)
        self.assertIn("ApprovalNotificationCenter", self.center)
        self.assertIn("self.operations.update_assignment", self.center)
        self.assertIn("self.notifications.evaluate", self.center)
        self.assertNotIn("UPDATE cases SET specialist_id", self.center)
        self.assertNotIn("notification.created", self.center)

    def test_separation_and_no_approval_or_release_are_explicit(self):
        self.assertIn("SEPARATION_OF_DUTIES_REQUIRED", self.center)
        self.assertIn("specialist_id == qa_id", self.center)
        self.assertIn('"automatic_legal_approval": False', self.center)
        self.assertIn('"automatic_qa_approval": False', self.center)
        self.assertIn('"automatic_release": False', self.center)
        self.assertIn('"dual_approval_preserved": True', self.center)
        self.assertNotIn("self.operations.workspace.approve", self.center)
        self.assertNotIn("self.operations.workspace.release", self.center)

    def test_completed_retry_has_read_only_short_circuit(self):
        complete_guard = self.center.index('if existing.get("state") == "COMPLETE"')
        first_mutation_after_existing = self.center.index("self.operations.update_assignment", complete_guard)
        early_return = self.center.index("return self._public(existing", complete_guard)
        self.assertLess(early_return, first_mutation_after_existing)
        self.assertIn("ASSIGNMENT_LEDGER_INVALID", self.center[complete_guard:first_mutation_after_existing])

    def test_api_is_admin_gated_same_origin_csrf_and_exact_assign_action(self):
        self.assertIn('PREFIX = "/api/m36/assignments"', self.routes)
        self.assertIn('parts[2] != "assign"', self.routes)
        self.assertIn("self.require_origin()", self.handler)
        self.assertIn("self.require_csrf()", self.handler)
        self.assertIn("_require_admin", self.center)
        self.assertIn("RATE_LIMITER", self.routes)

    def test_observability_omits_legal_and_payment_payloads(self):
        for forbidden in ("problem_statement", "receipt_number", "payment_intent_id", "document_snapshot_sha256", "activation_sha256"):
            self.assertNotIn(forbidden, self.routes)
        self.assertIn("desk_count", self.routes)
        self.assertIn("notification_evaluations", self.routes)
        self.assertIn("idempotent", self.routes)

    def test_http_smoke_proves_manual_assignment_handoff_and_no_approval(self):
        self.assertIn("CSRF_FAILED", self.smoke)
        self.assertIn("automatic_matching", self.smoke)
        self.assertIn("automatic_legal_approval", self.smoke)
        self.assertIn("automatic_qa_approval", self.smoke)
        self.assertIn("automatic_release", self.smoke)
        self.assertIn("dual_approval_preserved", self.smoke)
        self.assertIn("notification-center/cases", self.smoke)
        self.assertIn("legal_pending", self.smoke)
        self.assertIn("idempotent", self.smoke)

    def test_ci_runs_m361_after_m360(self):
        self.assertIn("python tools/m36_0_http_smoke.py", self.ci)
        self.assertIn("python tools/m36_1_http_smoke.py", self.ci)
        self.assertLess(
            self.ci.index("python tools/m36_0_http_smoke.py"),
            self.ci.index("python tools/m36_1_http_smoke.py"),
        )


if __name__ == "__main__":
    unittest.main()
