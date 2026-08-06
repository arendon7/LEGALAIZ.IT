from __future__ import annotations

import unittest

from scripts.run_m32_3_verified_portfolio import VERIFIED_CALCULATIONS, VERIFIED_OVERRIDES


class M323VerifiedCasesTests(unittest.TestCase):
    def test_salud_usa_claves_exactas_de_la_fabrica(self):
        answers = VERIFIED_OVERRIDES["CO-SA-001"]
        self.assertEqual(answers["entity"], "EPS Demo S.A.")
        self.assertEqual(answers["entity_type"], "EPS")
        self.assertEqual(answers["petitioner_name"], answers["patient_name"])
        self.assertEqual(answers["representation_support"], "No aplica: actúa en nombre propio")
        self.assertEqual(answers["medical_support"], "Sí")
        self.assertEqual(answers["continuity_risk"], "Sí")
        self.assertEqual(answers["secure_delivery"], "Sí")
        calculation = VERIFIED_CALCULATIONS["CO-SA-001"]
        self.assertIn("Pendiente", calculation["preliminary_business_days"])
        self.assertIn("festivos", calculation["preliminary_due_date"])

    def test_consumo_modela_garantia_sin_inventar_vencimiento(self):
        answers = VERIFIED_OVERRIDES["CO-CD-003"]
        self.assertEqual(answers["request_mode"], "Garantía legal")
        self.assertEqual(answers["problem_type"], "Producto defectuoso")
        self.assertEqual(answers["order_or_contract"], "PED-DEMO-2026-001")
        calculation = VERIFIED_CALCULATIONS["CO-CD-003"]
        eligibility = calculation["mechanism_eligibility"]
        self.assertTrue(eligibility["warranty"])
        self.assertFalse(eligibility["withdrawal"])
        self.assertFalse(eligibility["reversal"])
        self.assertIn("Pendiente de cómputo", calculation["direct_claim_due_date"])
        self.assertIn("No aplica", calculation["withdrawal_due_date"])

    def test_transito_conserva_hitos_distintos_y_entrega_no_acreditada(self):
        answers = VERIFIED_OVERRIDES["CO-TR-002"]
        self.assertEqual(answers["event_date"], "2026-06-15")
        self.assertEqual(answers["validation_date"], "2026-06-16")
        self.assertEqual(answers["sent_date"], "2026-06-18")
        self.assertEqual(answers["delivery_date"], "No acreditada en la muestra")
        self.assertEqual(answers["first_knowledge_date"], "2026-07-10")
        self.assertEqual(len({answers["event_date"], answers["validation_date"], answers["sent_date"], answers["first_knowledge_date"]}), 4)
        self.assertIn("preliminar", VERIFIED_CALCULATIONS["CO-TR-002"]["validation_to_sent_weekdays_preliminary"])


if __name__ == "__main__":
    unittest.main()
