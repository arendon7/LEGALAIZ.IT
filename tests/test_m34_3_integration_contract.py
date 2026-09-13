import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M343IntegrationContractTests(unittest.TestCase):
    def test_runtime_activates_incremental_m343_handler(self):
        run = (ROOT / "run.py").read_text(encoding="utf-8")
        handler = (ROOT / "legalai_platform" / "http_handler_m34_3.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.http_handler_m34_3 import Handler", run)
        self.assertIn("http_handler_m34_2 import Handler as BaseHandler", handler)
        self.assertIn("http_handler_m34_2 import Handler  # compatibility marker", run)

    def test_recovery_secret_stays_in_post_body(self):
        routes = (ROOT / "legalai_platform" / "routes" / "m34_3_question_routes.py").read_text(encoding="utf-8")
        frontend = (ROOT / "app" / "modules" / "adaptive_questions_m34_3.js").read_text(encoding="utf-8")
        self.assertIn('method:\'POST\'', frontend)
        self.assertIn("recovery_code:currentCode", frontend)
        self.assertNotIn("?recovery_code", frontend)
        self.assertNotIn("recovery_code=", frontend)
        self.assertNotIn("handler.path", routes)

    def test_frontend_does_not_render_product_scores_or_outcome_probabilities(self):
        frontend = (ROOT / "app" / "modules" / "adaptive_questions_m34_3.js").read_text(encoding="utf-8")
        lowered = frontend.lower()
        self.assertNotIn("signal_score", frontend)
        self.assertNotIn("fit_score", frontend)
        self.assertNotIn("probabilidad de ganar", lowered)
        self.assertNotIn("chance de ganar", lowered)
        self.assertIn("Todavía no hemos emitido una recomendación", frontend)

    def test_index_loads_m343_assets_after_m342(self):
        index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        self.assertIn("adaptive_questions_m34_3.css", index)
        self.assertIn("adaptive_questions_m34_3.js", index)
        self.assertLess(index.index("fact_review_m34_2.css"), index.index("adaptive_questions_m34_3.css"))
        self.assertLess(index.index("fact_review_m34_2.js"), index.index("adaptive_questions_m34_3.js"))

    def test_observability_has_no_answer_value_problem_or_recovery_secret(self):
        routes = (ROOT / "legalai_platform" / "routes" / "m34_3_question_routes.py").read_text(encoding="utf-8")
        for forbidden in (
            "problem_statement=",
            "recovery_code=recovery_code",
            "answer_value=",
            "value=data.get",
        ):
            self.assertNotIn(forbidden, routes)
        self.assertIn("question_id=question_id[:120]", routes)

    def test_question_contracts_preserve_pre_auth_data_minimization(self):
        registry = json.loads((ROOT / "config" / "m34" / "question_contracts.json").read_text(encoding="utf-8"))
        prohibited = set(registry["data_minimization"]["prohibited_direct_collection"])
        self.assertTrue({"full_name", "government_id", "email", "phone"}.issubset(prohibited))
        for question in registry["fact_questions"]:
            if question["requirement_mode"] == "FULFILLMENT_ONLY":
                self.assertIsNone(question["prompt"])
                self.assertEqual(question["source_mode"], "DEFERRED")

    def test_css_has_mobile_focus_and_reduced_motion_contracts(self):
        css = (ROOT / "app" / "modules" / "adaptive_questions_m34_3.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:700px)", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion:reduce", css)


if __name__ == "__main__":
    unittest.main()
