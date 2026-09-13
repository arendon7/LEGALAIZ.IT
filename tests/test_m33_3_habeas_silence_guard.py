from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_silence_guard import (
    SIC_SILENCE_AUTHORITY,
    enforce_habeas_silence_scope,
    install_m33_3_habeas_silence_guard,
)


class HabeasSilenceGuardM333Tests(unittest.TestCase):
    def _calculation(self) -> dict:
        return {
            "prior_term_overdue_preliminary": True,
            "silence_acceptance_preliminary": True,
            "issues": [
                {"id": "CD1-CALC-14", "risk": "yellow", "message": "Término vencido."},
                {"id": "CD1-CALC-15", "risk": "yellow", "message": "Aceptación preliminar por silencio."},
            ],
            "assumptions": [],
        }

    def test_ordinary_overdue_claim_never_inherits_favorable_silence(self):
        answers = {
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "No",
        }
        calculation = enforce_habeas_silence_scope(answers, self._calculation())
        self.assertFalse(calculation["silence_acceptance_preliminary"])
        self.assertFalse(calculation["silence_identity_theft_scope_verified"])
        issue_ids = {item["id"] for item in calculation["issues"]}
        self.assertIn("CD1-CALC-14", issue_ids)
        self.assertNotIn("CD1-CALC-15", issue_ids)
        self.assertIn("CD1-M33-SILENCE-SCOPE", issue_ids)

    def test_coexisting_identity_theft_route_does_not_reclassify_prior_claim(self):
        answers = {
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "Sí",
            "identity_theft_discovery_date": "2026-08-01",
            "prior_claim_date": "2026-07-20",
        }
        calculation = enforce_habeas_silence_scope(answers, self._calculation())
        self.assertFalse(calculation["silence_acceptance_preliminary"])
        self.assertFalse(calculation["silence_identity_theft_scope_verified"])
        self.assertIn("CD1-M33-SILENCE-SCOPE", {item["id"] for item in calculation["issues"]})

    def test_explicit_identity_theft_claim_can_model_favorable_silence(self):
        answers = {
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "Sí",
            "prior_claim_identity_theft": "Sí",
            "identity_theft_discovery_date": "2026-07-01",
            "prior_claim_date": "2026-07-20",
        }
        calculation = enforce_habeas_silence_scope(answers, self._calculation())
        self.assertTrue(calculation["silence_acceptance_preliminary"])
        self.assertTrue(calculation["silence_identity_theft_scope_verified"])
        issue_ids = {item["id"] for item in calculation["issues"]}
        self.assertIn("CD1-CALC-15", issue_ids)
        self.assertNotIn("CD1-M33-SILENCE-SCOPE", issue_ids)
        self.assertIn("únicamente respecto del reclamo de posible suplantación", next(item["message"] for item in calculation["issues"] if item["id"] == "CD1-CALC-15"))

    def test_identity_claim_chronology_must_be_possible(self):
        answers = {
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "Sí",
            "prior_claim_identity_theft": "Sí",
            "identity_theft_discovery_date": "2026-08-01",
            "prior_claim_date": "2026-07-20",
        }
        calculation = enforce_habeas_silence_scope(answers, self._calculation())
        self.assertFalse(calculation["silence_acceptance_preliminary"])
        self.assertFalse(calculation["silence_identity_theft_scope_verified"])
        self.assertIn("CD1-M33-SILENCE-CHRONOLOGY", {item["id"] for item in calculation["issues"]})

    def test_guard_is_idempotent_and_exposes_authority_reference(self):
        answers = {
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "No",
        }
        calculation = enforce_habeas_silence_scope(answers, self._calculation())
        calculation = enforce_habeas_silence_scope(answers, calculation)
        self.assertEqual(calculation["silence_authority_reference"], SIC_SILENCE_AUTHORITY)
        self.assertEqual(sum(item.get("id") == "CD1-M33-SILENCE-SCOPE" for item in calculation["issues"]), 1)
        marker = "El vencimiento de un reclamo y el efecto favorable del silencio son controles distintos."
        self.assertEqual(sum(marker in text for text in calculation["assumptions"]), 1)

    def test_runtime_installer_wraps_habeas_calculator_only_once(self):
        module = ModuleType("fake_habeas_core")

        def habeas_data_calc(answers):
            return self._calculation()

        module.habeas_data_calc = habeas_data_calc
        self.assertTrue(install_m33_3_habeas_silence_guard(module))
        first = module.habeas_data_calc
        self.assertTrue(install_m33_3_habeas_silence_guard(module))
        self.assertIs(module.habeas_data_calc, first)
        result = module.habeas_data_calc({
            "prior_claim": "Sí",
            "prior_claim_complete": "Sí",
            "response_received": "No",
            "identity_theft": "No",
        })
        self.assertFalse(result["silence_acceptance_preliminary"])


if __name__ == "__main__":
    unittest.main()
