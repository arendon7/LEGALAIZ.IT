from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M351IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app" / "modules" / "fulfillment_bridge_m35_1.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "app" / "modules" / "fulfillment_bridge_m35_1.css").read_text(encoding="utf-8")
        cls.run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m35_1.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_1_fulfillment_routes.py").read_text(encoding="utf-8")
        cls.bridge = (ROOT / "legalai_platform" / "fulfillment_bridge_m35_1.py").read_text(encoding="utf-8")

    def test_runtime_activates_incremental_m351_handler(self):
        self.assertIn("from legalai_platform.http_handler_m35_1 import Handler", self.run_source)
        self.assertIn("http_handler_m35_0 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_POST()", self.handler)

    def test_prepare_requires_origin_client_session_and_csrf(self):
        self.assertIn("self.require_origin()", self.handler)
        self.assertIn('self.require_user(roles={"client"})', self.handler)
        self.assertIn("self.require_csrf()", self.handler)
        self.assertIn('PREPARE_PATH = "/api/m35/fulfillment/prepare"', self.routes)

    def test_local_user_answers_win_over_server_prefill(self):
        self.assertIn("const mergedAnswers = { ...serverAnswers, ...localAnswers };", self.js)
        self.assertLess(self.js.index("...serverAnswers"), self.js.index("...localAnswers"))
        self.assertIn("localStorage.setItem(draftKey(code)", self.js)
        self.assertIn("Puedes corregirlas", self.js)

    def test_prepare_does_not_create_checkout_or_case(self):
        prepare = self.bridge[self.bridge.index("def prepare(") :]
        self.assertNotIn("create_order(", prepare)
        self.assertNotIn("checkout_orders", prepare)
        self.assertNotIn("create_case(", prepare)
        self.assertNotIn("pay_order(", prepare)

    def test_bridge_does_not_copy_problem_statement_or_fact_ids_to_draft_result(self):
        prepare = self.bridge[self.bridge.index("def prepare(") :]
        self.assertNotIn('"problem_statement"', prepare)
        self.assertNotIn('"matched_fact_ids"', prepare)
        self.assertNotIn('"input_fingerprint"', prepare)
        bridge_result = prepare[prepare.index("bridge_result = {") : prepare.index("updated = self.self_service.save_draft")]
        self.assertNotIn("fact_id", bridge_result)
        self.assertIn('"triage_reused_question_ids"', bridge_result)

    def test_observability_does_not_log_answer_values_or_story(self):
        observe = self.routes[self.routes.index('"m35_fulfillment_prepared"') : self.routes.index("handler.send_json(result")]
        self.assertNotIn("answers", observe)
        self.assertNotIn("problem_statement", observe)
        self.assertNotIn("recovery_code", observe)
        self.assertNotIn("fact_id", observe)

    def test_assets_load_after_m350(self):
        self.assertIn("fulfillment_bridge_m35_1.css", self.index)
        self.assertIn("fulfillment_bridge_m35_1.js", self.index)
        self.assertLess(self.index.index("account_handoff_m35_0.css"), self.index.index("fulfillment_bridge_m35_1.css"))
        self.assertLess(self.index.index("account_handoff_m35_0.js"), self.index.index("fulfillment_bridge_m35_1.js"))
        self.assertIn("@media(max-width:640px)", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)

    def test_direct_product_visit_remains_valid_without_handoff(self):
        self.assertIn("A direct product visit without an M35 handoff is a normal path", self.js)
        self.assertIn("No existe un diagnóstico transferido", self.js)
        self.assertNotIn("location.href", self.js)

    def test_offer_is_explicitly_sandbox_and_not_commercially_approved(self):
        self.assertIn("pricing_status", self.bridge)
        self.assertIn("pricing_notice", self.bridge)
        self.assertIn("no constituyen una oferta comercial pública definitiva", self.js.lower())


if __name__ == "__main__":
    unittest.main()
