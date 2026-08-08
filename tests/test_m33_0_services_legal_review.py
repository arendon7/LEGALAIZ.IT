from __future__ import annotations

from copy import deepcopy
import json
import unittest

from m33_services_instrument_finalize import compose_services_m33_instrument
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
        composition = compose_services_m33_instrument(answers)
        text = rendered_text(composition)

        self.assertIn("persona jurídica", text)
        self.assertIn("No se calcula IBC personal como porcentaje del valor de este contrato", text)
        self.assertNotIn("40 % del valor mensualizado sin IVA", text)
        self.assertNotIn("cuarenta por ciento (40 %)", text)
        self.assertNotIn("PILA\", \"Periodo ejecutado y pago mes vencido", text)
        self.assertIn("Ley 2466 de 2025", text)
        self.assertIn("artículo 183", text)
        self.assertIn("Ley 1955 de 2019", text)

    def test_natural_person_keeps_conditional_ibc_and_risk_logic(self):
        answers = services_answers()
        answers["contractor"]["identification"]["type"] = "natural_person"
        answers["contractor"]["identification"]["name"] = "Ana María Consultora"
        answers.setdefault("ai", {})["used"] = True
        composition = compose_services_m33_instrument(answers)
        text = rendered_text(composition)

        self.assertIn("cuarenta por ciento (40 %)", text)
        self.assertIn("artículo 89 de la Ley 2277 de 2022", text)
        self.assertIn("INTELIGENCIA ARTIFICIAL", text)
        self.assertIn("Decreto 1072 de 2015", text)

    def test_payment_dates_ai_insurance_and_liability_are_rule_driven(self):
        answers = services_answers()
        composition = compose_services_m33_instrument(answers)
        text = rendered_text(composition)

        self.assertNotRegex(text, r"\bfixed\b")
        self.assertIn("15 de agosto de 2026", text)
        self.assertIn("15 de octubre de 2026", text)
        self.assertIn("no se pacta un límite cuantitativo general", text)
        self.assertNotIn("INTELIGENCIA ARTIFICIAL", text)
        self.assertNotIn("SEGUROS", text)
        self.assertIn("Ley 2024 de 2020", text)

        activated = deepcopy(answers)
        activated.setdefault("ai", {})["used"] = True
        activated.setdefault("risk", {})["insurance_required"] = True
        activated["risk"]["insurance"] = "póliza de responsabilidad civil profesional"
        activated["risk"]["liability_cap"] = "COP $48.000.000"
        activated_text = rendered_text(compose_services_m33_instrument(activated))
        self.assertIn("INTELIGENCIA ARTIFICIAL", activated_text)
        self.assertIn("SEGUROS", activated_text)
        self.assertIn("COP $48.000.000", activated_text)

    def test_professional_title_is_explicitly_configurable(self):
        answers = services_answers()
        answers.setdefault("service", {})["professional"] = False
        composition = compose_services_m33_instrument(answers)
        self.assertEqual(composition["title"], "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES")

        answers["service"]["professional"] = True
        composition = compose_services_m33_instrument(answers)
        self.assertEqual(composition["title"], "CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES INDEPENDIENTES")

    def test_conditional_modules_leave_continuous_clause_numbering(self):
        answers = services_answers()
        composition = compose_services_m33_instrument(answers)
        clauses = [section for section in composition["sections"] if section.get("_type") == "clause"]
        self.assertGreaterEqual(len(clauses), 40)
        self.assertEqual([section.get("clause_number") for section in clauses], list(range(1, len(clauses) + 1)))
        text = rendered_text(composition)
        self.assertNotIn("Que Las partes", text)
        self.assertNotIn("Que La coordinación", text)
        self.assertNotIn("los actividades", text)

    def test_client_facing_instrument_has_substantive_considerations_and_no_internal_platform_language(self):
        composition = compose_services_m33_instrument(services_answers())
        considerations = next(
            item for item in composition["sections"]
            if str(item.get("heading") or "").strip().casefold() == "consideraciones"
        )
        self.assertEqual(6, len(considerations.get("paragraphs") or []))
        text = rendered_text(composition)
        self.assertIn("entregables, hitos, criterios objetivos de aceptación", text)
        self.assertIn("buena fe, la realidad de la ejecución", text)
        self.assertNotIn("La plataforma conservará", text)
        self.assertNotIn("aprobación jurídica", text.casefold())
        self.assertNotIn("jurídico y qa", text.casefold())

    def test_no_exclusivity_answer_controls_commercial_restriction_clause(self):
        answers = services_answers()
        answers["independence"]["no_exclusivity"] = "no existe exclusividad salvo conflicto específico informado y aceptado"
        text = rendered_text(compose_services_m33_instrument(answers))
        self.assertIn("no establece exclusividad general ni obligación de no competencia", text)
        self.assertIn("podrá prestar servicios a terceros", text)
        self.assertNotIn("La exclusividad se limita al proyecto", text)

    def test_fees_are_formatted_in_cop_and_words(self):
        text = rendered_text(compose_services_m33_instrument(services_answers()))
        self.assertIn("COP $48.000.000", text)
        self.assertIn("cuarenta y ocho millones de pesos moneda corriente", text)
        self.assertIn("treinta días calendario después de aceptación y factura válida", text)

    def test_termination_signature_and_notifications_are_operational(self):
        answers = services_answers()
        answers["termination"]["rules"] = "incumplimiento grave, acuerdo o terminación sin causa con preaviso de treinta días"
        answers["termination"]["cure_period"] = "diez días hábiles"
        composition = compose_services_m33_instrument(answers)
        text = rendered_text(composition)
        self.assertIn("preaviso de treinta días", text)
        self.assertIn("diez días hábiles", text)
        self.assertIn("juridica@demo.legalaiz.it", text)
        self.assertIn("contratos@demo.legalaiz.it", text)
        self.assertIn("última firma necesaria", text)
        self.assertIn("nueva versión, adenda u otro instrumento válido", text)


if __name__ == "__main__":
    unittest.main()
