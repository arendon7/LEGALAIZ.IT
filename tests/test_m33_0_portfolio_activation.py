from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import (
    PRODUCTS as WAVE2_PRODUCTS,
    consumer_fixture,
    debt_fixture,
    habeas_fixture,
    labor_fixture,
)
from tests.test_m33_0_wave3 import (
    PRODUCTS as WAVE3_PRODUCTS,
    health_fixture,
    sast_fixture,
    traffic_fixture,
)


class PortfolioActivationM330Tests(unittest.TestCase):
    def test_active_runtime_uses_m33_across_three_waves(self):
        import run

        # Primera oleada: fábricas versionadas dedicadas.
        self.assertEqual(run.COEM003_FACTORY_V244.VERSION, "2.45")
        self.assertEqual(run.COEM004_FACTORY_V247.VERSION, "2.48")
        self.assertEqual(run.COAR001_FACTORY_V250.VERSION, "2.51")
        self.assertEqual(run.COLA002_FACTORY_V239.VERSION, "2.40")

        # Segunda y tercera oleada: compositor genérico activo sin cambiar la API.
        self.assertIs(run.document_specs, document_specs_m33_all)
        self.assertIs(run._application_services.document_specs, document_specs_m33_all)
        self.assertIs(run._runtime_registry.core.document_specs, document_specs_m33_all)

    def test_wave2_non_red_outputs_are_m33_but_red_gate_stays_historical(self):
        fixtures = {
            "CO-LA-001": labor_fixture(),
            "CO-CD-001": habeas_fixture(),
            "CO-CD-003": consumer_fixture("warranty_claim"),
            "CO-CD-004": debt_fixture(),
        }
        for code, (answers, result) in fixtures.items():
            specs = document_specs_m33_all("CASE", code, answers, result, WAVE2_PRODUCTS[code], "2026-08-07", [])
            self.assertTrue(specs)
            self.assertTrue(all(spec.get("document_standard") == "M33.0" for spec in specs), code)

        answers, result = consumer_fixture("warranty_claim")
        result["risk"] = "red"
        specs = document_specs_m33_all("CASE", "CO-CD-003", answers, result, WAVE2_PRODUCTS["CO-CD-003"], "2026-08-07", [])
        self.assertTrue(specs)
        self.assertTrue(all(spec.get("document_standard") != "M33.0" for spec in specs))

    def test_wave3_can_compose_critical_drafts_without_marking_them_released(self):
        fixtures = {
            "CO-SA-001": health_fixture(),
            "CO-TR-001": sast_fixture(),
            "CO-TR-002": traffic_fixture(),
        }
        for code, (answers, result) in fixtures.items():
            specs = document_specs_m33_all("CASE", code, answers, result, WAVE3_PRODUCTS[code], "2026-08-07", [])
            self.assertTrue(specs)
            self.assertTrue(all(spec.get("document_standard") == "M33.0" for spec in specs), code)
            combined = " ".join(str(spec.get("sections")) for spec in specs).casefold()
            if code in {"CO-SA-001", "CO-TR-001"}:
                # Salud y SAST ya externalizan la gobernanza de la copia cliente.
                # El bloqueo se verifica en los campos de gobierno, no imprimiendo
                # instrucciones de aprobación dentro del instrumento visible.
                self.assertTrue(all(spec.get("legal_approval") == "pending" for spec in specs))
                self.assertTrue(all(spec.get("qa_approval") == "pending" for spec in specs))
                self.assertTrue(all(spec.get("released") is False for spec in specs))
                self.assertTrue(all(spec.get("requires_human_review") for spec in specs))
                self.assertTrue(all(spec.get("critical_human_review") for spec in specs))
                self.assertNotIn("control de uso, fuentes y revisión", combined)
                self.assertNotIn("documento candidato interno", combined)
            else:
                self.assertIn("aprobación jurídica", combined)
                self.assertIn("qa", combined)
                self.assertNotIn("released = true", combined)

    def test_unknown_product_keeps_historical_document_specs_behavior(self):
        product = {"code": "CO-XX-999", "title": "Producto externo a M33"}
        result = {"risk": "green", "calculation": {}}
        specs = document_specs_m33_all("CASE", "CO-XX-999", {}, result, product, "2026-08-07", [])
        self.assertTrue(specs)
        self.assertTrue(all(spec.get("document_standard") != "M33.0" for spec in specs))


if __name__ == "__main__":
    unittest.main()
