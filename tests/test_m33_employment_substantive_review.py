from __future__ import annotations

import json
import unittest

from legalai_platform.legal_source_registry import get_legal_source
from m33_document_presentation import split_internal_review_sections
from m33_employment_substantive_review import compose_employment_m33_substantive
from tests.test_m33_0_contractual_wave import employment_answers


def public_text(composition: dict) -> str:
    public, _ = split_internal_review_sections(composition.get("sections") or [])
    return json.dumps(public, ensure_ascii=False)


class EmploymentSubstantiveReviewTests(unittest.TestCase):
    def test_probation_is_not_invented_when_interview_has_no_written_pact(self):
        composition = compose_employment_m33_substantive(employment_answers())
        text = public_text(composition)
        self.assertIn("no constituye por sí sola un pacto de período de prueba", text)
        self.assertIn("estipulado de manera expresa y por escrito", text)
        self.assertIn("dos (2) meses", text)
        self.assertIn("quinta parte del término inicialmente pactado", text)
        self.assertIn("contratos sucesivos", text)
        self.assertNotIn("se pacta un período de prueba de", text)

    def test_reformed_paid_leaves_are_expressed_without_turning_bicycle_day_into_automatic_right(self):
        composition = compose_employment_m33_substantive(employment_answers())
        text = public_text(composition)
        for expected in (
            "ejercer el sufragio",
            "grave calamidad doméstica",
            "citas médicas de urgencia",
            "citas programadas con especialistas",
            "obligaciones escolares como acudiente",
            "citaciones judiciales, administrativas o legales",
        ):
            self.assertIn(expected, text)
        self.assertIn("opera únicamente cuando sea acordado con EL EMPLEADOR", text)

    def test_disciplinary_due_process_includes_2025_reform_safeguards(self):
        composition = compose_employment_m33_substantive(employment_answers())
        text = public_text(composition)
        for expected in (
            "término no inferior a cinco (5) días",
            "Si los descargos son verbales, se levantará un acta",
            "principio de inmediatez",
            "uno (1) o dos (2) representantes sindicales",
            "medidas y ajustes razonables",
            "cuente con esas herramientas a disposición",
            "audiencia previa, la defensa y el debido proceso",
        ):
            self.assertIn(expected, text)

    def test_review_is_surgical_and_preserves_other_august_2026_rules(self):
        composition = compose_employment_m33_substantive(employment_answers())
        text = public_text(composition)
        self.assertIn("cuarenta y dos (42) horas semanales", text)
        self.assertIn("7:00 p. m.", text)
        self.assertIn("recargo del 90 %", text)
        self.assertIn("preaviso de treinta (30) días calendario", text)
        maturity = composition.get("maturity_answers") or {}
        self.assertEqual("2026-08-11", maturity.get("employment_substantive_review"))
        self.assertEqual("written_express_stipulation_required", maturity.get("probation_inference_policy"))

    def test_source_registry_locators_cover_the_three_reviewed_topics(self):
        cst = get_legal_source("CO-CST-EMPLOYMENT-2026")
        reform = get_legal_source("CO-LEY2466-2025")
        self.assertIn("57", cst["locator"])
        self.assertIn("77", cst["locator"])
        self.assertIn("78", cst["locator"])
        self.assertIn("período de prueba", " ".join(cst["topics"]))
        self.assertIn("licencias remuneradas", " ".join(reform["topics"]))
        self.assertIn("debido proceso disciplinario", " ".join(reform["topics"]))


if __name__ == "__main__":
    unittest.main()
