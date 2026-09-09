import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M342IntegrationContractTests(unittest.TestCase):
    def test_run_activates_m342_without_erasing_m341_compatibility_marker(self):
        source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.http_handler_m34_2 import Handler", source)
        self.assertIn("http_handler_m34_1 import Handler  # compatibility marker", source)

    def test_m342_handler_inherits_m341_and_intercepts_only_new_routes(self):
        source = (ROOT / "legalai_platform" / "http_handler_m34_2.py").read_text(encoding="utf-8")
        self.assertIn("http_handler_m34_1 import Handler as BaseHandler", source)
        self.assertIn("ANALYZE_PATH", source)
        self.assertIn("FACT_DECISIONS_PATH", source)
        self.assertIn("return super().do_POST()", source)
        self.assertIn("require_origin", source)

    def test_public_api_keeps_recovery_secret_in_post_body(self):
        source = (ROOT / "app" / "modules" / "fact_review_m34_2.js").read_text(encoding="utf-8")
        self.assertIn("/api/m34/intake/analyze", source)
        self.assertIn("/api/m34/intake/facts/decide", source)
        self.assertIn("body:JSON.stringify({ recovery_code:currentCode", source)
        self.assertNotIn("?recovery_code=", source)

    def test_frontend_states_are_explicit_and_do_not_claim_recommendation(self):
        source = (ROOT / "app" / "modules" / "fact_review_m34_2.js").read_text(encoding="utf-8")
        self.assertIn("Esto es lo que entendimos de tu relato.", source)
        self.assertIn("Un dato automático nunca se vuelve confirmado por sí solo.", source)
        self.assertIn("Aún no estamos recomendando una solución.", source)
        self.assertNotIn("signal_score", source)
        self.assertNotIn("recommended_product", source)

    def test_index_loads_m342_assets_after_m341_foundation(self):
        source = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        self.assertIn("intelligent_intake_m34_1.css", source)
        self.assertIn("fact_review_m34_2.css", source)
        self.assertIn("fact_review_m34_2.js", source)
        self.assertLess(source.index("intelligent_intake_m34_1.css"), source.index("fact_review_m34_2.css"))

    def test_extraction_schema_preserves_unconfirmed_boundaries(self):
        schema = json.loads((ROOT / "config" / "m34" / "fact_extraction_result.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "34.2.0")
        self.assertEqual(schema["properties"]["candidate_products"]["maxItems"], 3)
        self.assertEqual(schema["properties"]["risk_signals"]["maxItems"], 8)
        self.assertEqual(schema["properties"]["candidate_products"]["items"]["properties"]["status"]["const"], "TOPIC_SIGNAL_ONLY")
        self.assertEqual(schema["properties"]["risk_signals"]["items"]["properties"]["status"]["const"], "UNCONFIRMED_SIGNAL")

    def test_css_contains_mobile_and_visible_focus_contracts(self):
        source = (ROOT / "app" / "modules" / "fact_review_m34_2.css").read_text(encoding="utf-8")
        self.assertIn("focus-visible", source)
        self.assertIn("@media(max-width:760px)", source)
        self.assertIn("@media(max-width:640px)", source)

    def test_observability_never_logs_fact_values_or_problem_text(self):
        source = (ROOT / "legalai_platform" / "routes" / "m34_2_fact_routes.py").read_text(encoding="utf-8")
        observation_blocks = [part for part in source.split("_safe_observe(")[1:]]
        self.assertTrue(observation_blocks)
        for block in observation_blocks:
            head = block.split(")", 1)[0]
            self.assertNotIn("problem_statement", head)
            self.assertNotIn("recovery_code", head)
            self.assertNotIn("fact.value", head)


if __name__ == "__main__":
    unittest.main()
