from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M341IntegrationContractTests(unittest.TestCase):
    def test_runtime_uses_incremental_m34_handler(self):
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.http_handler_m34_1 import Handler", run_source)
        handler_source = (ROOT / "legalai_platform" / "http_handler_m34_1.py").read_text(encoding="utf-8")
        self.assertIn("http_handler_m33_0 import Handler as BaseHandler", handler_source)
        self.assertIn("require_origin", handler_source)

    def test_recovery_secret_is_posted_in_body_not_url(self):
        route_source = (ROOT / "legalai_platform" / "routes" / "m34_1_intake_routes.py").read_text(encoding="utf-8")
        self.assertIn('f"{PREFIX}/recover"', route_source)
        self.assertNotIn("?recovery_code", route_source)
        self.assertNotIn("/recover/", route_source)

    def test_public_intake_does_not_claim_ai_processing_yet(self):
        backend_source = (ROOT / "legalai_platform" / "intelligent_intake_m34_1.py").read_text(encoding="utf-8")
        frontend_source = (ROOT / "app" / "modules" / "conversion_m29_5.js").read_text(encoding="utf-8")
        self.assertIn('"ai_processing_status": "NOT_STARTED"', backend_source)
        self.assertIn("todavía no presentamos inferencias ni conclusiones automáticas", frontend_source)
        self.assertIn("La siguiente capa del recorrido convertirá el relato en hechos candidatos", frontend_source)

    def test_frontend_escapes_problem_statement_before_rendering(self):
        frontend_source = (ROOT / "app" / "modules" / "conversion_m29_5.js").read_text(encoding="utf-8")
        self.assertIn("esc(session.problem_statement || '')", frontend_source)
        self.assertIn("esc(existing)", frontend_source)

    def test_recovery_form_is_not_nested_in_main_intake_form_template(self):
        frontend_source = (ROOT / "app" / "modules" / "conversion_m29_5.js").read_text(encoding="utf-8")
        self.assertIn("</form>${resumeIntakeContent()}", frontend_source)
        self.assertEqual(frontend_source.count('id="m341-intake-form"'), 1)
        self.assertEqual(frontend_source.count('id="m341-recover-form"'), 1)

    def test_css_is_loaded_and_mobile_rules_exist(self):
        index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "app" / "modules" / "intelligent_intake_m34_1.css").read_text(encoding="utf-8")
        self.assertIn("intelligent_intake_m34_1.css", index)
        self.assertIn("@media(max-width:900px)", css)
        self.assertIn(":focus-visible", css)


if __name__ == "__main__":
    unittest.main()
