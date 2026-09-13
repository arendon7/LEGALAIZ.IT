from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M353ReadOnlyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.center = (ROOT / "legalai_platform" / "case_activation_m35_3.py").read_text(encoding="utf-8")
        cls.handler = (ROOT / "legalai_platform" / "http_handler_m35_3.py").read_text(encoding="utf-8")
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_3_activation_routes.py").read_text(encoding="utf-8")
        cls.frontend = (ROOT / "app" / "modules" / "case_activation_m35_3.js").read_text(encoding="utf-8")

    def test_activation_center_is_strictly_read_only(self):
        upper = self.center.upper()
        self.assertNotIn("INSERT INTO", upper)
        self.assertNotIn("UPDATE ", upper)
        self.assertNotIn("DELETE FROM", upper)
        self.assertNotIn(".COMMIT(", upper)
        self.assertIn("SELECT ", upper)

    def test_incremental_handler_adds_get_only(self):
        self.assertIn("def do_GET", self.handler)
        self.assertNotIn("def do_POST", self.handler)
        self.assertIn("return super().do_GET()", self.handler)
        self.assertIn('roles={"client"}', self.handler)

    def test_route_never_mutates_commerce_payment_case_or_documents(self):
        upper = self.routes.upper()
        for marker in ("INSERT INTO", "UPDATE ", "DELETE FROM", "CREATE TABLE", "FINALIZE_PATH", "PAYMENT_PATH"):
            self.assertNotIn(marker, upper)
        self.assertIn("activation_center().build", self.routes)

    def test_frontend_does_not_call_mutating_m35_endpoints(self):
        self.assertIn("/api/m35/activation/", self.frontend)
        for forbidden in (
            "/api/m35/commerce/order",
            "/api/m35/commerce/payment-intent",
            "/api/m35/commerce/finalize",
            "/api/m35/commerce/invalidate",
            "method:'POST'",
            'method: "POST"',
        ):
            self.assertNotIn(forbidden, self.frontend)

    def test_read_model_declares_sandbox_and_non_approval_boundaries(self):
        self.assertIn('"real_charge": False', self.center)
        self.assertIn("no acredita un cargo real", self.center)
        self.assertIn("no equivale a aprobación jurídica", self.center)
        self.assertIn("controles internos de calidad", self.center)


if __name__ == "__main__":
    unittest.main()
