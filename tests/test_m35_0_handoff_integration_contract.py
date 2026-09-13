from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M350HandoffIntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app" / "modules" / "account_handoff_m35_0.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "app" / "modules" / "account_handoff_m35_0.css").read_text(encoding="utf-8")
        cls.run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m35_0.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_0_handoff_routes.py").read_text(encoding="utf-8")
        cls.store = (ROOT / "legalai_platform" / "handoff_m35_0.py").read_text(encoding="utf-8")

    def test_runtime_activates_incremental_m350_handler(self):
        self.assertIn("from legalai_platform.http_handler_m35_0 import Handler", self.run_source)
        self.assertIn("http_handler_m34_4 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_POST()", self.handler)

    def test_claim_requires_origin_authenticated_client_and_csrf(self):
        self.assertIn("self.require_origin()", self.handler)
        self.assertIn('self.require_user(roles={"client"})', self.handler)
        self.assertIn("self.require_csrf()", self.handler)
        self.assertIn('CLAIM_PATH = f"{PREFIX}/claim"', self.routes)

    def test_recovery_secret_stays_out_of_url_localstorage_and_logs(self):
        self.assertIn("sessionStorage.setItem(CLAIM_KEY", self.js)
        self.assertIn("sessionStorage.removeItem(CLAIM_KEY)", self.js)
        self.assertNotIn("localStorage.setItem(CLAIM_KEY", self.js)
        self.assertNotIn("?recovery_code=", self.js)
        self.assertNotIn("?recovery_code=", self.routes)
        observe = self.routes[
            self.routes.index('"m35_intake_claimed"') : self.routes.index("handler.send_json(result")
        ]
        self.assertNotIn("recovery_code", observe)
        self.assertNotIn("problem_statement", observe)
        self.assertNotIn("fact_value", observe)

    def test_account_is_requested_only_after_explicit_recommendation_continue(self):
        self.assertIn("Continuar con esta solución", self.js)
        self.assertIn("data-m350-continue", self.js)
        self.assertIn("storePendingClaim(code)", self.js)
        self.assertIn("go('/login')", self.js)
        self.assertNotIn("claimPending()", self.js[: self.js.index("async function continueRecommendation")])

    def test_public_registration_reuses_existing_auth_api(self):
        self.assertIn("/api/auth/register", self.js)
        self.assertIn("consent:", self.js)
        self.assertIn("state.user = result.user", self.js)
        self.assertIn("state.csrf = result.csrf_token", self.js)
        self.assertIn("await claimPending({ reloadAfter: true })", self.js)

    def test_handoff_does_not_copy_narrative_or_fact_values_to_service_draft(self):
        minimal = self.store[self.store.index("minimal_result = {") : self.store.index("draft = self.self_service.save_draft")]
        self.assertNotIn("problem_statement", minimal)
        self.assertNotIn('"facts"', minimal)
        self.assertNotIn("input_fingerprint", minimal)
        self.assertIn('"decision_id"', minimal)
        self.assertIn('"intake_id"', minimal)
        self.assertIn('"triage_reuse_status": "PENDING_SAFE_MAPPING"', minimal)

    def test_transfer_is_one_time_and_existing_product_draft_is_not_overwritten(self):
        self.assertIn("intake_id TEXT NOT NULL UNIQUE", self.store)
        self.assertIn("WHERE id=? AND status='Activo' AND transferred_user_id IS NULL", self.store)
        self.assertIn("existing_draft = self.self_service.get_product_draft", self.store)
        conflict_block = self.store[
            self.store.index("if existing_draft:") : self.store.index("handoff_id =")
        ]
        self.assertIn("raise HandoffConflictError", conflict_block)
        self.assertNotIn("save_draft", conflict_block)

    def test_assets_load_after_m344_and_include_accessibility_contracts(self):
        self.assertIn("account_handoff_m35_0.css", self.index)
        self.assertIn("account_handoff_m35_0.js", self.index)
        self.assertLess(
            self.index.index("recommendation_m34_4.css"),
            self.index.index("account_handoff_m35_0.css"),
        )
        self.assertLess(
            self.index.index("recommendation_m34_4.js"),
            self.index.index("account_handoff_m35_0.js"),
        )
        self.assertIn(":focus-visible", self.css)
        self.assertIn("@media(max-width:640px)", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)


if __name__ == "__main__":
    unittest.main()
