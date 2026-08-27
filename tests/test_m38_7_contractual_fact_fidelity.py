from __future__ import annotations

from copy import deepcopy
import unittest

from m33_services_release_polish import compose_services_m33_release
from scripts.generate_m32_3_full_portfolio import _services_answers


def _visible_text(composition: dict) -> str:
    values: list[str] = []
    for section in composition.get("sections") or []:
        if not isinstance(section, dict):
            continue
        values.append(str(section.get("heading") or ""))
        values.append(str(section.get("text") or ""))
        values.extend(str(item) for item in section.get("paragraphs") or [])
        values.extend(str(item) for item in section.get("bullets") or [])
        for row in section.get("table") or []:
            values.extend(str(cell) for cell in row)
    return "\n".join(values)


class M387ContractualFactFidelityTests(unittest.TestCase):
    def test_rich_services_answers_reach_material_contract_clauses(self):
        answers = _services_answers()
        composition = compose_services_m33_release(answers)
        text = _visible_text(composition)

        expected_facts = (
            answers["scope"]["acceptance_criteria"],
            answers["schedule"]["duration"],
            answers["schedule"]["milestones"],
            answers["execution"]["arrangement"],
            answers["execution"]["place"],
            answers["execution"]["team"],
            answers["execution"]["subcontracting"],
            answers["execution"]["dependencies"],
            answers["fees"]["invoice"],
            answers["fees"]["expenses"],
            answers["fees"]["retentions"],
            answers["independence"]["direction"],
            answers["independence"]["personnel"],
            answers["independence"]["social_security"],
            answers["confidentiality"]["categories"],
            answers["confidentiality"]["term"],
            answers["data"]["roles"],
            answers["data"]["security"],
            answers["ip"]["preexisting"],
            answers["ip"]["results"],
            answers["ip"]["third_party"],
            answers["ai"]["rules"],
            answers["risk"]["allocation"],
            answers["risk"]["liability"],
            answers["risk"]["insurance"],
            answers["closure"]["transition"],
            answers["closure"]["return_destroy"],
        )
        for fact in expected_facts:
            with self.subTest(fact=fact):
                self.assertIn(str(fact).rstrip(".;"), text)

        self.assertNotIn("negotiation_conciliation_courts", text)
        self.assertIn("negociación directa, posterior conciliación", text)
        self.assertTrue(composition["maturity_answers"]["m38_7_contractual_fact_fidelity"])

    def test_overlay_does_not_mutate_answers_and_preserves_clause_sequence_and_sources(self):
        answers = _services_answers()
        before = deepcopy(answers)
        composition = compose_services_m33_release(answers)
        self.assertEqual(answers, before)

        clauses = [section for section in composition["sections"] if section.get("_type") == "clause"]
        self.assertGreater(len(clauses), 40)
        self.assertEqual([section.get("clause_number") for section in clauses], list(range(1, len(clauses) + 1)))

        controls = [section for section in composition["sections"] if section.get("_type") == "control"]
        self.assertEqual(len(controls), 1)
        self.assertTrue(controls[0].get("source_ids"))
        self.assertEqual(controls[0].get("source_manifest_status"), composition["legal_source_manifest"]["status"])

    def test_optional_empty_or_sentinel_facts_do_not_leak_into_contract(self):
        answers = _services_answers()
        answers["data"]["security"] = "undefined"
        answers["risk"]["insurance"] = "N/A"
        answers["closure"]["return_destroy"] = "NULL"
        answers["execution"]["team"] = ""
        composition = compose_services_m33_release(answers)
        text = _visible_text(composition)

        self.assertNotIn("Como medidas de seguridad específicamente confirmadas para la ejecución se aplicarán: undefined", text)
        self.assertNotIn("En materia de aseguramiento se registró como condición de gestión: N/A", text)
        self.assertNotIn("Respecto de información, soportes y credenciales al cierre se aplicará la siguiente condición confirmada: NULL", text)
        self.assertNotIn("Para este contrato, la estructura de equipo confirmada es:", text)

    def test_ai_fact_is_not_resurrected_when_ai_module_is_inactive(self):
        answers = _services_answers()
        answers["ai"]["used"] = False
        answers["ai"]["rules"] = "regla que no debe aparecer si el módulo está inactivo"
        composition = compose_services_m33_release(answers)
        text = _visible_text(composition)

        self.assertNotIn("INTELIGENCIA ARTIFICIAL Y SERVICIOS EN LA NUBE", text)
        self.assertNotIn("regla que no debe aparecer si el módulo está inactivo", text)

    def test_fact_fidelity_is_additive_not_a_replacement_of_existing_legal_language(self):
        answers = _services_answers()
        composition = compose_services_m33_release(answers)
        text = _visible_text(composition)

        self.assertIn("Cada parte responderá por daños directos, ciertos, demostrables", text)
        self.assertIn("El presente contrato no establece exclusividad general", text)
        self.assertIn("La terminación no extingue las obligaciones", text)
        self.assertIn("Ley 1581 de 2012", text)
        self.assertIn("PARÁGRAFO", text)


if __name__ == "__main__":
    unittest.main()
