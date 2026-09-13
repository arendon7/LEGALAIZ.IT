from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "app" / "modules" / "guided_journey_m38_1.js"
CSS = ROOT / "app" / "modules" / "guided_journey_m38_1.css"
INDEX = ROOT / "app" / "index.html"


class GuidedJourneyM381Tests(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")
        self.index = INDEX.read_text(encoding="utf-8")

    def test_six_stage_user_journey_is_explicit(self):
        for label in (
            "Cuéntanos tu situación",
            "Confirma los datos",
            "Completa lo necesario",
            "Revisa tu ruta",
            "Guarda y continúa",
            "Completa la solución",
        ):
            self.assertIn(label, self.js)
        self.assertIn('aria-label="Tu recorrido en LegalAIZ.it"', self.js)
        self.assertIn('aria-current="step"', self.js)

    def test_each_stage_explains_saved_missing_output_and_next_step(self):
        for label in ("Ya guardamos", "Qué falta", "Qué obtendrás", "Siguiente paso"):
            self.assertIn(label, self.js)
        self.assertIn("No empiezas de cero", self.js)
        self.assertIn("tus cambios manuales siempre prevalecen", self.js)

    def test_public_architecture_jargon_is_replaced_at_render_boundary(self):
        self.assertIn("criterios de las soluciones disponibles", self.js)
        self.assertIn("Etapa completada", self.js)
        self.assertIn("evaluar tu ruta", self.js)
        self.assertIn("datos específicos de la solución", self.js)
        self.assertIn("document.querySelectorAll('.m344-trace').forEach(element => element.remove())", self.js)

    def test_overlay_is_data_blind_and_does_not_change_security_or_commerce(self):
        forbidden = (
            "api(", "fetch(", "localStorage", "sessionStorage", "recovery_code",
            "problem_statement", "fact_id", "payment", "checkout", "create-case",
        )
        for token in forbidden:
            self.assertNotIn(token, self.js)
        self.assertNotIn("input.value", self.js)
        self.assertNotIn("textarea", self.js)

    def test_overlay_does_not_create_legal_outcome_or_auto_approval_claims(self):
        lowered = self.js.lower()
        for claim in ("probabilidad de ganar", "resultado garantizado", "aprobación automática", "vigencia automática"):
            self.assertNotIn(claim, lowered)
        self.assertIn("borrador controlado, revisable y trazable", lowered)

    def test_assets_load_last_after_certified_m35_flow(self):
        js_marker = './modules/guided_journey_m38_1.js'
        css_marker = './modules/guided_journey_m38_1.css'
        self.assertIn(js_marker, self.index)
        self.assertIn(css_marker, self.index)
        self.assertGreater(self.index.index(js_marker), self.index.index('./modules/case_activation_m35_3.js'))
        self.assertGreater(self.index.index(css_marker), self.index.index('./modules/case_activation_m35_3.css'))

    def test_existing_recovery_and_handoff_ownership_remain_in_certified_modules(self):
        m341 = (ROOT / "app" / "modules" / "conversion_m29_5.js").read_text(encoding="utf-8")
        m350 = (ROOT / "app" / "modules" / "account_handoff_m35_0.js").read_text(encoding="utf-8")
        m351 = (ROOT / "app" / "modules" / "fulfillment_bridge_m35_1.js").read_text(encoding="utf-8")
        self.assertIn("/api/m34/intake/recover", m341)
        self.assertIn("/api/m35/intake/claim", m350)
        self.assertIn("/api/m35/fulfillment/prepare", m351)
        self.assertNotIn("/api/m34/intake/recover", self.js)
        self.assertNotIn("/api/m35/intake/claim", self.js)
        self.assertNotIn("/api/m35/fulfillment/prepare", self.js)

    def test_responsive_and_reduced_motion_contracts_are_present(self):
        self.assertIn("@media(max-width:900px)", self.css)
        self.assertIn("@media(max-width:560px)", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)
        self.assertIn("overflow-x:auto", self.css)


if __name__ == "__main__":
    unittest.main()
