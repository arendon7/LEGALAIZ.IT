from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M352IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m35_2.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_2_commerce_routes.py").read_text(encoding="utf-8")
        cls.store = (ROOT / "legalai_platform" / "commerce_case_m35_2.py").read_text(encoding="utf-8")
        cls.self_service = (ROOT / "self_service_backend.py").read_text(encoding="utf-8")
        cls.js = (ROOT / "app" / "modules" / "commerce_case_m35_2.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "app" / "modules" / "commerce_case_m35_2.css").read_text(encoding="utf-8")
        cls.index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")

    def test_runtime_activates_incremental_m352_handler(self):
        self.assertIn("from legalai_platform.http_handler_m35_2 import Handler", self.run_source)
        self.assertIn("http_handler_m35_1 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_POST()", self.handler)
        self.assertIn("return super().do_GET()", self.handler)

    def test_all_m352_posts_require_origin_client_and_csrf(self):
        self.assertIn("self.require_origin()", self.handler)
        self.assertIn('self.require_user(roles={"client"})', self.handler)
        self.assertIn("self.require_csrf()", self.handler)
        self.assertIn('PREFIX = "/api/m35/commerce"', self.routes)
        self.assertIn("RATE_LIMITER.allow", self.routes)

    def test_ledger_contains_only_links_states_and_hashes_not_story_or_answers(self):
        schema = self.store[self.store.index("CREATE TABLE IF NOT EXISTS m35_commerce_case_links") : self.store.index("CREATE INDEX IF NOT EXISTS idx_m35_commerce_user_product")]
        self.assertNotIn("problem_statement", schema)
        self.assertNotIn("answers", schema)
        self.assertNotIn("fact_id", schema)
        self.assertIn("draft_snapshot_sha256", schema)
        self.assertIn("order_snapshot_sha256", schema)

    def test_private_case_materialization_values_are_removed_before_http_response(self):
        self.assertIn('result.pop("_answers", {})', self.routes)
        self.assertIn('result.pop("_result", {})', self.routes)
        self.assertIn('result.pop("_title", "")', self.routes)
        self.assertIn('private["answers"]', self.routes)
        self.assertNotIn('"_answers":', self.routes)

    def test_document_failure_preserves_case_as_pending_instead_of_false_success(self):
        self.assertIn('"state": "CASE_CREATED_DOCUMENTS_PENDING"', self.routes)
        self.assertIn("documents_ready", self.routes)
        self.assertIn("202", self.routes)
        self.assertIn("materialización documental", self.routes)
        self.assertIn("CASE_CREATED_DOCUMENTS_PENDING", self.store)

    def test_legacy_checkout_payment_and_case_bypasses_are_blocked(self):
        self.assertIn("checkout trazable M35.2", self.self_service)
        self.assertIn("pago sandbox trazable M35.2", self.self_service)
        self.assertIn("ledger M35.2", self.self_service)
        self.assertIn("_install_legacy_case_guard", self.handler)
        self.assertIn("continuidad M35 activa", self.handler)

    def test_signed_sandbox_payment_is_mandatory_for_m352(self):
        self.assertIn('PAID_ORDER_STATUSES = {"Pagado (sandbox)"}', self.store)
        self.assertIn("verify_events", self.store)
        self.assertIn("PAYMENT_EVENT_INTEGRITY_FAILED", self.store)
        self.assertNotIn('PAID_ORDER_STATUSES = {"Pagado (simulado)"', self.store)

    def test_two_explicit_user_consents_are_required(self):
        self.assertIn("data-m352-checkout-consent", self.js)
        self.assertIn("checkout_consent:true", self.js)
        self.assertIn("data-m352-case-consent", self.js)
        self.assertIn("case_consent:true", self.js)
        self.assertIn("Confirma expresamente la creación del expediente", self.js)

    def test_payment_does_not_automatically_create_case(self):
        payment_branch = self.js[self.js.index("if (!paid) {") : self.js.index("const consent = document.querySelector('[data-m352-case-consent]')")]
        self.assertIn("/simulate", payment_branch)
        self.assertIn("return;", payment_branch)
        self.assertNotIn("FINALIZE_PATH", payment_branch)
        self.assertNotIn("/api/cases", payment_branch)

    def test_direct_unlinked_product_keeps_legacy_flow(self):
        self.assertIn("if (!context.linked) return originalStartCheckout?.();", self.js)
        self.assertIn("if (!link) return originalPayCheckout?.(orderId, method);", self.js)

    def test_pending_checkout_can_be_invalidated_only_explicitly(self):
        self.assertIn("data-m352-invalidate", self.js)
        self.assertIn("INVALIDATE_PATH", self.js)
        self.assertIn("PAYMENT_INTENT_ALREADY_CREATED", self.store)
        self.assertIn("ACTIVE_CHECKOUT_EXISTS", self.store)

    def test_assets_load_after_m351_and_keep_accessibility_contracts(self):
        self.assertIn("commerce_case_m35_2.css", self.index)
        self.assertIn("commerce_case_m35_2.js", self.index)
        self.assertLess(self.index.index("fulfillment_bridge_m35_1.css"), self.index.index("commerce_case_m35_2.css"))
        self.assertLess(self.index.index("fulfillment_bridge_m35_1.js"), self.index.index("commerce_case_m35_2.js"))
        self.assertIn("@media(max-width:640px)", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)
        self.assertIn(":focus-visible", self.css)

    def test_observability_uses_ids_and_counts_not_legal_payloads(self):
        self.assertNotIn("problem_statement", self.routes)
        self.assertNotIn("recovery_code", self.routes)
        self.assertNotIn("draft_snapshot_sha256", self.routes)
        self.assertNotIn("order_snapshot_sha256", self.routes)
        observe_calls = [chunk for chunk in self.routes.split("_observe(")[1:]]
        for chunk in observe_calls:
            call = chunk.split(")", 1)[0]
            self.assertNotIn("private[", call)
            self.assertNotIn("answers=", call)


if __name__ == "__main__":
    unittest.main()
