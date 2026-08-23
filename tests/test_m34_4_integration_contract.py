from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M344IntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app" / "modules" / "recommendation_m34_4.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "app" / "modules" / "recommendation_m34_4.css").read_text(encoding="utf-8")
        cls.run = (ROOT / "run.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m34_4.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m34_4_recommendation_routes.py").read_text(encoding="utf-8")
        cls.engine = (ROOT / "legalai_platform" / "recommendation_m34_4.py").read_text(encoding="utf-8")

    def test_index_loads_m344_assets_after_m343(self):
        self.assertIn("recommendation_m34_4.css", self.index)
        self.assertIn("recommendation_m34_4.js", self.index)
        self.assertLess(
            self.index.index("adaptive_questions_m34_3.css"),
            self.index.index("recommendation_m34_4.css"),
        )
        self.assertLess(
            self.index.index("adaptive_questions_m34_3.js"),
            self.index.index("recommendation_m34_4.js"),
        )

    def test_runtime_activates_incremental_m344_handler(self):
        self.assertIn("from legalai_platform.http_handler_m34_4 import Handler", self.run)
        self.assertIn("http_handler_m34_3 import Handler as BaseHandler", self.handler)
        self.assertIn("return super().do_POST()", self.handler)
        self.assertIn("self.require_origin()", self.handler)

    def test_recovery_secret_stays_in_post_body(self):
        self.assertIn('body:JSON.stringify({ recovery_code:code })', self.js)
        self.assertIn('data.get("recovery_code")', self.routes)
        self.assertNotIn("?recovery_code=", self.js)
        self.assertNotIn("?recovery_code=", self.routes)

    def test_recommendation_requires_explicit_user_action(self):
        self.assertIn("data-m344-request", self.js)
        self.assertIn("Ver mi recomendación", self.js)
        self.assertIn("requestRecommendation(request)", self.js)
        mount_section = self.js[self.js.index("function mount()") : self.js.index("function scheduleMount()")]
        self.assertNotIn("/api/m34/intake/recommendation", mount_section)
        self.assertNotIn("requestRecommendation(", mount_section)

    def test_frontend_explains_fit_not_legal_outcome_probability(self):
        self.assertIn("Adecuación al producto no significa probabilidad de ganar", self.js)
        self.assertNotIn("fit_score", self.js)
        self.assertNotIn("signal_score", self.js)
        self.assertNotIn("probabilidad de éxito", self.js.lower())

    def test_public_result_does_not_expose_fact_plumbing_or_fingerprint(self):
        public_block = self.engine[
            self.engine.index("def _public_result") : self.engine.index("def recommend(")
        ]
        self.assertNotIn('result["input_fingerprint"]', public_block)
        public_eval = self.engine[
            self.engine.index("def _public_evaluation") : self.engine.index("def decide(")
        ]
        self.assertIn('"matched_fact_ids"', public_eval)
        self.assertIn('"matched_fact_types"', public_eval)
        self.assertIn("private_keys", public_eval)

    def test_internal_audit_keeps_fact_links_and_fingerprint_encrypted(self):
        self.assertIn('"input_fingerprint": input_fingerprint', self.engine)
        self.assertIn('"usable_fact_ids"', self.engine)
        self.assertIn('"matched_fact_ids"', self.engine)
        self.assertIn('"matched_fact_types"', self.engine)
        self.assertIn('payload.setdefault(\n            "m34_4"', self.engine)

    def test_observability_avoids_story_fact_values_secret_and_fingerprint(self):
        observe_call = self.routes[
            self.routes.index('"m34_recommendation_decided"') : self.routes.index("handler.send_json(result)")
        ]
        for prohibited in (
            "problem_statement",
            "fact_value",
            "recovery_code",
            "input_fingerprint",
            "matched_fact_ids",
            "matched_fact_types",
        ):
            self.assertNotIn(prohibited, observe_call)

    def test_css_has_mobile_focus_and_reduced_motion_contracts(self):
        self.assertIn("@media(max-width:640px)", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)


if __name__ == "__main__":
    unittest.main()
