from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M353IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m35_3.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_3_activation_routes.py").read_text(encoding="utf-8")
        cls.center = (ROOT / "legalai_platform" / "case_activation_m35_3.py").read_text(encoding="utf-8")
        cls.index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        cls.frontend = (ROOT / "app" / "modules" / "case_activation_m35_3.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "app" / "modules" / "case_activation_m35_3.css").read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m352_handler(self):
        self.assertIn("from legalai_platform.http_handler_m35_3 import Handler", self.run_source)
        self.assertIn("from legalai_platform.http_handler_m35_2 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_GET()", self.handler)
        self.assertNotIn("def do_POST", self.handler)

    def test_activation_endpoint_is_client_only_get_and_owned_case_is_checked(self):
        self.assertIn('self.require_user(roles={"client"})', self.handler)
        self.assertIn('FROM cases WHERE id=? AND owner_id=?', self.center)
        self.assertIn('WHERE user_id=? AND case_id=?', self.center)
        self.assertIn("CASE_NOT_FOUND", self.center)
        self.assertIn("NOT_M35_COMMERCE_CASE", self.center)

    def test_positive_activation_requires_signed_payment_receipt_documents_and_m24(self):
        for marker in (
            'intent.get("status") != "succeeded"',
            "verify_events",
            'verified.get("checked") or 0) < 2',
            'receipt.startswith("RCPT-SBX-")',
            'document_count < 1',
            "JOURNEY_TRACE_MISSING",
            "JOURNEY_NOT_RECONCILED",
            'activation_status = "ACTIVE"',
        ):
            self.assertIn(marker, self.center)

    def test_public_activation_model_excludes_legal_payload_and_integrity_secrets(self):
        marker = 'return {\n            "schema": "legalai_m35_3_case_activation_v1"'
        self.assertIn(marker, self.center)
        public_segment = self.center[self.center.index(marker):]
        for forbidden in (
            '"answers"',
            '"result"',
            '"user_id"',
            '"handoff_id"',
            '"draft_id"',
            '"intake_id"',
            '"decision_id"',
            '"provider_reference"',
            '"signature"',
            '"payload_json"',
            '"idempotency_key"',
            '"draft_snapshot_sha256"',
            '"order_snapshot_sha256"',
        ):
            self.assertNotIn(forbidden, public_segment)

    def test_observability_never_logs_receipt_story_answers_or_payment_events(self):
        for forbidden in (
            "receipt_number=",
            "payment_intent_id=",
            "answers=",
            "problem_statement=",
            "payload_json=",
            "signature=",
        ):
            self.assertNotIn(forbidden, self.routes)
        self.assertIn("case_id=case_id", self.routes)
        self.assertIn("activation_status=result.get", self.routes)
        self.assertIn("documents_count=", self.routes)

    def test_frontend_assets_load_after_m352_and_are_accessible_responsive(self):
        self.assertIn("commerce_case_m35_2.css", self.index)
        self.assertIn("case_activation_m35_3.css", self.index)
        self.assertLess(self.index.index("commerce_case_m35_2.css"), self.index.index("case_activation_m35_3.css"))
        self.assertLess(self.index.index("commerce_case_m35_2.js"), self.index.index("case_activation_m35_3.js"))
        self.assertIn("@media(max-width:640px)", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn('aria-label="Confirmación de activación del expediente"', self.frontend)
        self.assertIn('role="status" aria-live="polite"', self.frontend)

    def test_frontend_never_infers_positive_activation_after_api_failure(self):
        self.assertIn("mountWarning(caseId", self.frontend)
        self.assertIn("No mostramos una confirmación positiva de compra", self.frontend)
        self.assertIn("NOT_M35_COMMERCE_CASE", self.frontend)
        self.assertIn("CASE_NOT_FOUND", self.frontend)
        self.assertIn("return mount(cache.get(caseId), caseId)", self.frontend)
        self.assertNotIn("localStorage", self.frontend)
        self.assertNotIn("sessionStorage", self.frontend)

    def test_frontend_discloses_sandbox_boundary_not_real_payment(self):
        self.assertIn("Sin cargo real", self.frontend)
        self.assertIn("Pago sandbox verificado", self.frontend)
        self.assertIn("Alcance de esta confirmación", self.frontend)
        self.assertIn("no acredita un cargo real", self.center)
        self.assertIn("no equivale a aprobación jurídica", self.center)

    def test_pending_recovery_points_back_to_same_checkout_without_second_payment_claim(self):
        self.assertIn("RETRY_DOCUMENT_PREPARATION", self.center)
        self.assertIn('f"/checkout/{order_id}"', self.center)
        self.assertIn("Reintentar preparación", self.frontend)
        self.assertNotIn("payment-intent", self.frontend)
        self.assertNotIn("/finalize", self.frontend)


if __name__ == "__main__":
    unittest.main()
