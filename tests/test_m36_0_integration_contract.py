from __future__ import annotations

from pathlib import Path
import re
import unittest


class M360IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.run_source = (cls.root / "run.py").read_text(encoding="utf-8")
        cls.handler = (cls.root / "legalai_platform" / "http_handler_m36_0.py").read_text(encoding="utf-8")
        cls.routes = (cls.root / "legalai_platform" / "routes" / "m36_0_fulfillment_routes.py").read_text(encoding="utf-8")
        cls.center = (cls.root / "legalai_platform" / "fulfillment_intake_m36_0.py").read_text(encoding="utf-8")
        cls.smoke = (cls.root / "tools" / "m36_0_http_smoke.py").read_text(encoding="utf-8")
        cls.ci = (cls.root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m353_handler(self):
        self.assertIn("from legalai_platform.http_handler_m36_0 import Handler", self.run_source)
        self.assertIn("http_handler_m35_3 import Handler", self.run_source)
        self.assertIn("from legalai_platform.http_handler_m35_3 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_GET()", self.handler)
        self.assertIn("return super().do_POST()", self.handler)

    def test_write_route_is_exact_admin_intake_with_origin_and_csrf(self):
        self.assertIn('PREFIX = "/api/m36/fulfillment"', self.routes)
        self.assertIn('parts[2] != "activate"', self.routes)
        self.assertIn("self.require_origin()", self.handler)
        self.assertIn("self.require_csrf()", self.handler)
        self.assertIn("_require_admin", self.center)
        self.assertNotIn("update_assignment(", self.center)
        self.assertNotIn(".approve(", self.center)
        self.assertNotIn(".release(", self.center)

    def test_bridge_reuses_m35_activation_m32_review_and_m24_journey(self):
        self.assertIn("CaseActivationCenter", self.center)
        self.assertIn("ApprovalDeskWorkspace", self.center)
        self.assertIn("ApprovalDeskOperations", self.center)
        self.assertIn("STATE_REVIEW_INTAKE = \"EN_REVISION_JURIDICA\"", self.center)
        self.assertIn("m36_0_fulfillment_intake", self.center)
        self.assertIn("dual_approval_preserved", self.center)

    def test_intake_is_case_scoped_not_global_portfolio_sync(self):
        self.assertNotIn("sync_portfolio(", self.center)
        self.assertNotIn("bootstrap(", self.center)
        self.assertIn("WHERE case_id=? AND kind!='audit'", self.center)
        self.assertIn("desk_case_id", self.center)
        self.assertIn("case_id TEXT NOT NULL UNIQUE", self.center)
        self.assertIn("order_id TEXT NOT NULL", self.center)

    def test_public_payload_and_observability_do_not_expose_sensitive_payment_or_legal_payloads(self):
        public_block = self.center[self.center.index("def _public("):]
        for forbidden in (
            '"owner_id"',
            '"activation_sha256"',
            '"document_snapshot_sha256"',
            '"receipt_number"',
            '"payment_intent_id"',
            '"problem_statement"',
            '"answers"',
        ):
            self.assertNotIn(forbidden, public_block)
        for forbidden in ("receipt_number", "payment_intent_id", "problem_statement", "answers"):
            self.assertNotIn(forbidden, self.routes)

    def test_ci_generates_ephemeral_demo_password_and_runs_m360_smoke(self):
        self.assertIn("secrets.token_urlsafe(32)", self.ci)
        self.assertIn("export LEGAL_DEMO_PASSWORD", self.ci)
        self.assertIn("python tools/m36_0_http_smoke.py", self.ci)
        self.assertNotRegex(self.ci, re.compile(r"LEGAL_DEMO_PASSWORD:\s*['\"]?[A-Za-z0-9!#_-]{12,}"))

    def test_smoke_exercises_real_admin_rbac_csrf_idempotency_and_no_auto_approval(self):
        self.assertIn('"ana@demo.legalaiz.it"', self.smoke)
        self.assertIn("LEGAL_DEMO_PASSWORD", self.smoke)
        self.assertIn("expected=403", self.smoke)
        self.assertIn("CSRF_FAILED", self.smoke)
        self.assertIn("idempotent", self.smoke)
        self.assertIn("automatic_assignment", self.smoke)
        self.assertIn("automatic_legal_approval", self.smoke)
        self.assertIn("automatic_qa_approval", self.smoke)
        self.assertIn("automatic_release", self.smoke)
        self.assertIn("dual_approval", self.smoke)


if __name__ == "__main__":
    unittest.main()
