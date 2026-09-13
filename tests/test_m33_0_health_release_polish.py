from __future__ import annotations

import unittest
from copy import deepcopy

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, health_fixture


def specs_for(answers=None, result=None):
    if answers is None or result is None:
        answers, result = health_fixture()
    return document_specs_m33_all(
        "CASE-HEALTH-POLISH",
        "CO-SA-001",
        answers,
        result,
        PRODUCTS["CO-SA-001"],
        "2026-08-08T12:25:00-05:00",
        [],
    )


def text(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class HealthReleasePolishM330Tests(unittest.TestCase):
    def test_medication_provider_is_not_assumed_to_be_clinical_history_custodian(self):
        history = next(spec for spec in specs_for() if spec.get("kind") == "health_history_request")
        body = text(history)
        self.assertIn("Prestador/custodio por verificar", body)
        self.assertNotIn("['Prestador/custodio', 'Medicamentos Demo S.A.S.']", body)

    def test_explicit_history_custodian_is_used_and_petition_language_is_natural(self):
        answers, result = health_fixture()
        answers = deepcopy(answers)
        answers["history_custodian"] = "Clínica Tratante Demo S.A.S."
        specs = specs_for(answers, deepcopy(result))
        history = next(spec for spec in specs if spec.get("kind") == "health_history_request")
        petition = next(spec for spec in specs if spec.get("kind") == "health_petition")
        self.assertIn("Clínica Tratante Demo S.A.S.", text(history))
        petition_text = text(petition)
        self.assertIn("aplicar la regla sectorial correspondiente:", petition_text)
        self.assertNotIn("debe validarla y aplicar Con", petition_text)
        self.assertNotIn("debe validarla y aplicar Máximo", petition_text)


if __name__ == "__main__":
    unittest.main()
