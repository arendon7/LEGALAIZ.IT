from __future__ import annotations

import json
import unittest

from m33_document_presentation import split_internal_review_sections
from m33_employment_instrument_finalize import compose_employment_m33_instrument
from tests.test_m33_0_contractual_wave import employment_answers


def public_text(composition: dict) -> str:
    public, _ = split_internal_review_sections(composition.get("sections") or [])
    return json.dumps(public, ensure_ascii=False)


class EmploymentInstrumentFinalizeM330Tests(unittest.TestCase):
    def test_visible_contract_has_natural_contractions(self):
        text = public_text(compose_employment_m33_instrument(employment_answers()))
        self.assertNotIn("a EL EMPLEADOR", text)
        self.assertNotIn("de EL EMPLEADOR", text)
        self.assertIn("al EMPLEADOR", text)

    def test_monitoring_clause_has_correct_agreement(self):
        text = public_text(compose_employment_m33_instrument(employment_answers()))
        self.assertIn(
            "Ni la entrega de un equipo empresarial ni el uso de una red corporativa eliminan por sí solos toda expectativa legítima de privacidad.",
            text,
        )
        self.assertNotIn("no elimina por sí solos", text)

    def test_editorial_layer_does_not_remove_governance_control(self):
        composition = compose_employment_m33_instrument(employment_answers())
        _, internal = split_internal_review_sections(composition.get("sections") or [])
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertIn("Fuente jurídica de control", internal_text)
        self.assertTrue(composition.get("maturity_answers", {}).get("employment_instrument_finalized"))


if __name__ == "__main__":
    unittest.main()
