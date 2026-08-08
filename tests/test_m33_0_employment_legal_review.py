from __future__ import annotations

from copy import deepcopy
import json
import unittest

from m33_employment_legal_finalize import compose_employment_m33_final
from tests.test_m33_0_contractual_wave import employment_answers


def rendered_text(composition: dict) -> str:
    return json.dumps(
        {"title": composition.get("title"), "sections": composition.get("sections")},
        ensure_ascii=False,
    )


class EmploymentLegalReviewM330Tests(unittest.TestCase):
    def test_august_2026_rules_are_current_and_technical_values_do_not_leak(self):
        composition = compose_employment_m33_final(employment_answers())
        text = rendered_text(composition)
        self.assertIn("cuarenta y dos (42) horas semanales", text)
        self.assertIn("7:00 p. m.", text)
        self.assertIn("recargo del 90 %", text)
        self.assertIn("1 de julio de 2027", text)
        self.assertIn("cinco (5) días", text)
        self.assertIn("No se requiere permiso previo del Ministerio del Trabajo", text)
        self.assertNotRegex(text, r"\bfixed\b")

    def test_indefinite_termination_pre_notice_cannot_be_penalized(self):
        composition = compose_employment_m33_final(employment_answers())
        text = rendered_text(composition)
        self.assertIn("preaviso de treinta (30) días calendario", text)
        self.assertIn("en ningún caso podrá pactarse o imponerse sanción", text)
        self.assertEqual(composition["title"], "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO")

    def test_fixed_term_and_work_labor_are_not_rendered_as_indefinite(self):
        fixed = employment_answers()
        fixed["contract"] = {"type": "fixed", "endDate": "2027-08-09"}
        fixed_composition = compose_employment_m33_final(fixed)
        fixed_text = rendered_text(fixed_composition)
        self.assertEqual(fixed_composition["title"], "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO FIJO")
        self.assertIn("cuatro (4) años", fixed_text)
        self.assertIn("30) días", fixed_text)
        self.assertNotIn("permanecerá vigente mientras subsistan las causas", fixed_text)

        work = employment_answers()
        work["contract"] = {"type": "work", "workDescription": "implementar el proyecto documental Alfa hasta su acta final de aceptación"}
        work_composition = compose_employment_m33_final(work)
        work_text = rendered_text(work_composition)
        self.assertIn("OBRA O LABOR DETERMINADA", work_composition["title"])
        self.assertIn("proyecto documental Alfa", work_text)
        self.assertIn("evidencia objetiva de su culminación", work_text)

    def test_missing_personal_data_is_not_invented_from_workplace(self):
        answers = employment_answers()
        answers["employer"].pop("domicile", None)
        answers["employerSignatory"].pop("identificationNumber", None)
        answers["worker"].pop("domicile", None)
        composition = compose_employment_m33_final(answers)
        text = rendered_text(composition)
        self.assertNotIn("identificación pendiente", text)
        self.assertNotIn("domicilio pendiente", text)
        # Medellín continúa apareciendo como lugar de trabajo, pero no se atribuye
        # como domicilio de la persona trabajadora por inferencia.
        self.assertNotIn("Carlos Andrés Pérez López, identificado(a) con documento No. 1.030.123.456, con domicilio en Medellín", text)

    def test_conditional_composition_keeps_continuous_clause_numbering_and_sources_externalizable(self):
        composition = compose_employment_m33_final(employment_answers())
        clauses = [section for section in composition["sections"] if section.get("_type") == "clause"]
        self.assertGreaterEqual(len(clauses), 35)
        self.assertEqual([section.get("clause_number") for section in clauses], list(range(1, len(clauses) + 1)))
        controls = [section for section in composition["sections"] if section.get("_type") == "control"]
        self.assertEqual(len(controls), 1)
        self.assertGreaterEqual(len(controls[0].get("bullets") or []), 8)
        self.assertIn("Ley 2466 de 2025", rendered_text(composition))


if __name__ == "__main__":
    unittest.main()
