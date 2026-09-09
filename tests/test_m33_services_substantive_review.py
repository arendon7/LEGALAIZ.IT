from __future__ import annotations

import json
import unittest

from legalai_platform.legal_source_registry import get_legal_source
from m33_document_presentation import split_internal_review_sections
from m33_services_release_polish import compose_services_m33_release
from tests.test_m33_0_services_reference import services_answers


def public_text(composition: dict) -> str:
    public, _ = split_internal_review_sections(composition.get("sections") or [])
    return json.dumps(public, ensure_ascii=False)


def section_text(composition: dict, phrase: str) -> str:
    for section in composition.get("sections") or []:
        if phrase.casefold() in str(section.get("heading") or "").casefold():
            values = [str(section.get("text") or "")]
            values.extend(str(item) for item in section.get("paragraphs") or [])
            return "\n".join(value for value in values if value)
    return ""


class ServicesSubstantiveReviewTests(unittest.TestCase):
    def test_legal_entity_contract_is_not_described_as_labor_contract_with_the_company(self):
        composition = compose_services_m33_release(services_answers())
        text = public_text(composition)
        self.assertIn("vínculo comercial entre las personas jurídicas comparecientes", text)
        self.assertIn("relaciones reales de las personas naturales", text)
        self.assertNotIn("naturaleza jurídica del vínculo será determinada por la realidad de su ejecución", text)

    def test_laborality_guard_applies_reality_analysis_to_natural_people(self):
        composition = compose_services_m33_release(services_answers())
        text = section_text(composition, "PREVENCIÓN DEL RIESGO DE LABORALIDAD")
        self.assertIn("persona jurídica", text)
        self.assertIn("persona natural", text)
        self.assertIn("artículos 22 y 23", text)
        self.assertIn("prestación personal, subordinación continuada y remuneración", text)
        self.assertIn("no equivale por sí sola a subordinación", text)

    def test_article_34_solidarity_cannot_be_disclaimed_by_contract(self):
        composition = compose_services_m33_release(services_answers())
        laborality = section_text(composition, "PREVENCIÓN DEL RIESGO DE LABORALIDAD")
        social_security = section_text(composition, "SEGURIDAD SOCIAL DEL CONTRATISTA")
        verification = section_text(composition, "VERIFICACIÓN DE APORTES")
        self.assertIn("artículo 34", laborality)
        self.assertIn("solidaridad", social_security)
        self.assertIn("no constituye renuncia, exclusión ni limitación", social_security)
        self.assertIn("ninguna estipulación de este contrato podrá interpretarse como exclusión", verification)
        self.assertIn("responsabilidad imperativa", verification)

    def test_new_sources_resolve_and_are_in_internal_manifest(self):
        composition = compose_services_m33_release(services_answers())
        ids = (composition.get("legal_source_manifest") or {}).get("source_ids") or []
        self.assertIn("CO-CST-ART22-2025", ids)
        self.assertIn("CO-CST-ART34-2025", ids)
        art22 = get_legal_source("CO-CST-ART22-2025")
        art34 = get_legal_source("CO-CST-ART34-2025")
        self.assertIn("persona natural", " ".join(art22.get("topics") or []))
        self.assertIn("solidaridad laboral", " ".join(art34.get("topics") or []))
        _, internal = split_internal_review_sections(composition.get("sections") or [])
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertIn("CO-CST-ART22-2025", internal_text)
        self.assertIn("CO-CST-ART34-2025", internal_text)

    def test_review_preserves_payment_ip_and_termination_rules(self):
        composition = compose_services_m33_release(services_answers())
        text = public_text(composition)
        self.assertIn("Ley 2024 de 2020", text)
        self.assertIn("treinta días calendario después de aceptación y factura válida", text)
        self.assertIn("Toda cesión deberá constar por escrito", text)
        self.assertIn("incumplimiento grave o acuerdo", text)
        self.assertIn("diez días hábiles", text)
        self.assertIn("Si se ha pactado terminación sin causa o por conveniencia", text)
        self.assertIn("preaviso expresamente convenido", text)
        self.assertNotIn("terminación sin causa con preaviso de treinta días", text)

    def test_natural_person_does_not_receive_legal_entity_guard(self):
        answers = services_answers()
        answers["contractor"]["identification"]["type"] = "natural_person"
        composition = compose_services_m33_release(answers)
        text = public_text(composition)
        self.assertNotIn("vínculo comercial entre las personas jurídicas comparecientes", text)
        self.assertIn("cuarenta por ciento (40 %)", text)
        self.assertIn("artículo 89 de la Ley 2277 de 2022", text)


if __name__ == "__main__":
    unittest.main()
