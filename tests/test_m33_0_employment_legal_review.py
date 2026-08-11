from __future__ import annotations

from copy import deepcopy
import json
import unittest

from m33_document_presentation import split_internal_review_sections
from m33_employment_release_polish import compose_employment_m33_release
from tests.test_m33_0_contractual_wave import employment_answers


def rendered_text(composition: dict) -> str:
    return json.dumps(
        {"title": composition.get("title"), "sections": composition.get("sections")},
        ensure_ascii=False,
    )


def public_text(composition: dict) -> str:
    public, _ = split_internal_review_sections(composition.get("sections") or [])
    return json.dumps(public, ensure_ascii=False)


class EmploymentLegalReviewM330Tests(unittest.TestCase):
    def test_august_2026_rules_are_current_and_technical_values_do_not_leak(self):
        composition = compose_employment_m33_release(employment_answers())
        text = rendered_text(composition)
        self.assertIn("cuarenta y dos (42) horas semanales", text)
        self.assertIn("7:00 p. m.", text)
        self.assertIn("recargo del 90 %", text)
        self.assertIn("1 de julio de 2027", text)
        self.assertIn("cinco (5) días", text)
        self.assertIn("No se requiere permiso previo del Ministerio del Trabajo", text)
        self.assertNotRegex(text, r"\bfixed\b")

    def test_indefinite_termination_pre_notice_cannot_be_penalized(self):
        composition = compose_employment_m33_release(employment_answers())
        text = rendered_text(composition)
        self.assertIn("preaviso de treinta (30) días calendario", text)
        self.assertIn("en ningún caso podrá pactarse o imponerse sanción", text)
        self.assertEqual(composition["title"], "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO")

    def test_fixed_term_and_work_labor_are_not_rendered_as_indefinite(self):
        fixed = employment_answers()
        fixed["contract"] = {"type": "fixed", "endDate": "2027-08-09"}
        fixed_composition = compose_employment_m33_release(fixed)
        fixed_text = rendered_text(fixed_composition)
        self.assertEqual(fixed_composition["title"], "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO FIJO")
        self.assertIn("cuatro (4) años", fixed_text)
        self.assertIn("30) días", fixed_text)
        self.assertNotIn("permanecerá vigente mientras subsistan las causas", fixed_text)

        work = employment_answers()
        work["contract"] = {"type": "work", "workDescription": "implementar el proyecto documental Alfa hasta su acta final de aceptación"}
        work_composition = compose_employment_m33_release(work)
        work_text = rendered_text(work_composition)
        self.assertIn("OBRA O LABOR DETERMINADA", work_composition["title"])
        self.assertIn("proyecto documental Alfa", work_text)
        self.assertIn("evidencia objetiva de su culminación", work_text)

    def test_missing_personal_data_is_not_invented_from_workplace(self):
        answers = employment_answers()
        answers["employer"].pop("domicile", None)
        answers["employerSignatory"].pop("identificationNumber", None)
        answers["worker"].pop("domicile", None)
        composition = compose_employment_m33_release(answers)
        text = rendered_text(composition)
        self.assertNotIn("identificación pendiente", text)
        self.assertNotIn("domicilio pendiente", text)
        self.assertNotIn("Carlos Andrés Pérez López, con documento No. 1.030.123.456, con domicilio en Medellín", text)

    def test_conditional_composition_keeps_continuous_clause_numbering_and_sources_externalizable(self):
        composition = compose_employment_m33_release(employment_answers())
        clauses = [section for section in composition["sections"] if section.get("_type") == "clause"]
        self.assertGreaterEqual(len(clauses), 35)
        self.assertEqual([section.get("clause_number") for section in clauses], list(range(1, len(clauses) + 1)))
        controls = [section for section in composition["sections"] if section.get("_type") == "control"]
        self.assertEqual(len(controls), 1)
        self.assertGreaterEqual(len(controls[0].get("bullets") or []), 8)
        self.assertIn("Ley 2466 de 2025", rendered_text(composition))

    def test_considerations_are_substantive_and_signed_copy_is_clean(self):
        composition = compose_employment_m33_release(employment_answers())
        considerations = next(
            section for section in composition["sections"]
            if str(section.get("heading") or "").strip().casefold() == "consideraciones"
        )
        self.assertEqual(6, len(considerations.get("paragraphs") or []))
        text = public_text(composition).casefold()
        self.assertIn("primacía de la realidad", text)
        self.assertIn("derechos ciertos e indiscutibles", text)
        # "Expediente" puede ser un objeto legítimo del cargo jurídico; lo que no
        # puede llegar al instrumento es lenguaje de workspace/gobierno LegalAIZ.it.
        for forbidden in (
            "constan en la ficha",
            "consta en la ficha",
            "definido en el expediente",
            "la plataforma",
            "aprobación jurídica",
            "jurídico y qa",
            "liberar únicamente el mismo sha",
        ):
            self.assertNotIn(forbidden, text)

    def test_salary_is_in_cop_and_words_without_artificial_non_salary_exclusion(self):
        composition = compose_employment_m33_release(employment_answers())
        text = rendered_text(composition)
        self.assertIn("COP $4.200.000 (cuatro millones doscientos mil pesos moneda corriente)", text)
        self.assertIn("La denominación contractual o contable de un pago no puede excluir su naturaleza salarial", text)
        self.assertIn("conceptos específicos cuya naturaleza y finalidad sean compatibles con la ley", text)

    def test_direction_privacy_and_evaluation_have_material_limits(self):
        composition = compose_employment_m33_release(employment_answers())
        text = rendered_text(composition)
        self.assertIn("no constituye insubordinación ni autoriza represalias", text)
        self.assertIn("no elimina por sí solos toda expectativa legítima de privacidad", text)
        self.assertIn("sin revisión humana responsable", text)
        self.assertIn("posibilidad de controvertir la información relevante", text)

    def test_termination_liquidation_and_signature_do_not_waive_worker_rights(self):
        composition = compose_employment_m33_release(employment_answers())
        text = rendered_text(composition)
        self.assertIn("estabilidad laboral reforzada", text)
        self.assertIn("no implica renuncia a derechos ciertos e indiscutibles", text)
        self.assertIn("preservarse sin modificaciones posteriores", text)
        self.assertIn("nueva versión, otrosí o instrumento válido", text)
        self.assertNotIn("La plataforma conservará", text)


if __name__ == "__main__":
    unittest.main()
