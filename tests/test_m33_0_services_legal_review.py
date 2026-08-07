from __future__ import annotations

from copy import deepcopy
import json
import unittest

from m33_services_legal_review import compose_services_m33_reviewed
from tests.test_m33_0_services_reference import services_answers


def rendered_text(composition: dict) -> str:
    return json.dumps(
        {"title": composition.get("title"), "sections": composition.get("sections")},
        ensure_ascii=False,
    )


class ServicesLegalReviewM330Tests(unittest.TestCase):
    def test_legal_entity_does_not_receive_personal_40_percent_ibc_matrix(self):
        answers = services_answers()
        answers.setdefault("service", {})["professional"] = True
        composition = compose_services_m33_reviewed(answers)
        text = rendered_text(composition)

        self.assertIn("persona jurídica", text)
        self.assertIn("No se calcula IBC personal como porcentaje del valor de este contrato", text)
        self.assertNotIn("40 % del valor mensualizado sin IVA", text)
        self.assertNotIn("PILA\", \"Periodo ejecutado y pago mes vencido", text)
        self.assertIn("Ley 2466 de 2025", text)
        self.assertIn("artículo 183", text)
        self.assertIn("Ley 1955 de 2019", text)

    def test_natural_person_keeps_conditional_ibc_and_risk_logic(self):
        answers = services_answers()
        answers["contractor"]["identification"]["type"] = "natural_person"
        answers["contractor"]["identification"]["name"] = "Ana María Consultora"
        answers.setdefault("ai", {})["used"] = True
        composition = compose_services_m33_reviewed(answers)
        text = rendered_text(composition)

        self.assertIn("cuarenta por ciento (40 %)", text)
        self.assertIn("artículo 89 de la Ley 2277 de 2022", text)
        self.assertIn("USO DE INTELIGENCIA ARTIFICIAL", text)
        self.assertIn("Decreto 1072 de 2015", text)

    def test_payment_dates_ai_insurance_and_liability_are_rule_driven(self):
        answers = services_answers()
        composition = compose_services_m33_reviewed(answers)
        text = rendered_text(composition)

        self.assertNotRegex(text, r"\bfixed\b")
        self.assertIn("15 de agosto de 2026", text)
        self.assertIn("15 de octubre de 2026", text)
        self.assertIn("no se pacta un límite cuantitativo general", text)
        self.assertNotIn("USO DE INTELIGENCIA ARTIFICIAL", text)
        self.assertNotIn("SEGUROS", text)
        self.assertIn("Ley 2024 de 2020", text)

        activated = deepcopy(answers)
        activated.setdefault("ai", {})["used"] = True
        activated.setdefault("risk", {})["insurance_required"] = True
        activated["risk"]["insurance"] = "póliza de responsabilidad civil profesional"
        activated["risk"]["liability_cap"] = "COP $48.000.000"
        activated_text = rendered_text(compose_services_m33_reviewed(activated))
        self.assertIn("USO DE INTELIGENCIA ARTIFICIAL", activated_text)
        self.assertIn("SEGUROS", activated_text)
        self.assertIn("COP $48.000.000", activated_text)

    def test_professional_title_is_explicitly_configurable(self):
        answers = services_answers()
        answers.setdefault("service", {})["professional"] = False
        composition = compose_services_m33_reviewed(answers)
        self.assertEqual(composition["title"], "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES")

        answers["service"]["professional"] = True
        composition = compose_services_m33_reviewed(answers)
        self.assertEqual(composition["title"], "CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES INDEPENDIENTES")


if __name__ == "__main__":
    unittest.main()
