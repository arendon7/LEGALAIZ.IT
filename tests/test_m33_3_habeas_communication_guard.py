from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_communication_guard import (
    COMMUNICATION_STANDARD,
    enforce_habeas_prior_communication,
    install_m33_3_habeas_communication_guard,
)


class HabeasCommunicationGuardM333Tests(unittest.TestCase):
    def base_answers(self) -> dict:
        return {
            "obligation_status": "Pagada",
            "obligation_amount": 5_000_000,
            "report_date": "2026-08-10",
            "prior_communication_received": "No",
            "prior_communication_sent": "Sí",
            "prior_communication_date": "2026-07-20",
            "prior_communication_evidence": "Completa",
            "prior_communication_channel": "Dirección física registrada",
            "prior_communication_destination_verified": "Sí",
            "prior_communication_alternative_channel_agreed": "No aplica",
            "prior_communication_message_consultable": "No aplica",
            "prior_communication_content_sufficient": "Sí",
            "small_obligation_two_notices": "No aplica",
        }

    def base_calculation(self) -> dict:
        return {
            "small_obligation_reference_value": 262_635.75,
            "issues": [
                {"id": "CD1-CALC-09", "risk": "yellow", "message": "legacy"},
            ],
        }

    def test_physical_send_can_be_supported_even_when_receipt_is_no(self):
        result = enforce_habeas_prior_communication(self.base_answers(), self.base_calculation())
        self.assertEqual(result["communication_standard"], COMMUNICATION_STANDARD)
        self.assertEqual(result["communication_status"], "preliminarily_supported")
        self.assertEqual(result["communication_lead_calendar_days"], 21)
        self.assertEqual(result["communication_received_status"], "No")
        self.assertTrue(result["communication_receipt_is_independent_fact"])
        self.assertNotIn("CD1-CALC-09", {item.get("id") for item in result["issues"]})

    def test_nineteen_days_is_preliminary_noncompliance(self):
        answers = self.base_answers(); answers["prior_communication_date"] = "2026-07-22"
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_lead_calendar_days"], 19)
        self.assertEqual(result["communication_status"], "noncompliance_preliminary")
        self.assertIn("CD1-M33-COMM-LEAD", {item.get("id") for item in result["issues"]})

    def test_electronic_channel_without_agreement_fails(self):
        answers = self.base_answers()
        answers["prior_communication_channel"] = "Correo electrónico"
        answers["prior_communication_alternative_channel_agreed"] = "No"
        answers["prior_communication_message_consultable"] = "Sí"
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_status"], "noncompliance_preliminary")
        self.assertIn("CD1-M33-COMM-ALT-CHANNEL", {item.get("id") for item in result["issues"]})

    def test_unknown_destination_fails_closed_without_calling_it_compliant(self):
        answers = self.base_answers(); answers["prior_communication_destination_verified"] = "No sé"
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_status"], "not_proven")
        self.assertIn("CD1-M33-COMM-DESTINATION", {item.get("id") for item in result["issues"]})

    def test_small_obligation_requires_two_notices_and_first_date(self):
        answers = self.base_answers()
        answers["obligation_amount"] = 200_000
        answers["small_obligation_two_notices"] = "No"
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertIs(result["small_obligation_preliminary"], True)
        self.assertEqual(result["communication_status"], "noncompliance_preliminary")
        self.assertIn("CD1-M33-COMM-SMALL-TWO-NOTICES", {item.get("id") for item in result["issues"]})

    def test_small_obligation_two_distinct_days_can_pass(self):
        answers = self.base_answers()
        answers["obligation_amount"] = 200_000
        answers["small_obligation_two_notices"] = "Sí"
        answers["prior_communication_first_date"] = "2026-07-18"
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_status"], "preliminarily_supported")
        self.assertEqual(result["communication_first_date"], "2026-07-18")

    def test_small_obligation_same_day_notices_do_not_pass(self):
        answers = self.base_answers()
        answers["obligation_amount"] = 200_000
        answers["small_obligation_two_notices"] = "Sí"
        answers["prior_communication_first_date"] = answers["prior_communication_date"]
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_status"], "noncompliance_preliminary")
        self.assertIn("CD1-M33-COMM-FIRST-DATE", {item.get("id") for item in result["issues"]})

    def test_missing_send_facts_never_invents_compliance(self):
        answers = self.base_answers()
        answers.pop("prior_communication_sent")
        answers.pop("prior_communication_date")
        result = enforce_habeas_prior_communication(answers, self.base_calculation())
        self.assertEqual(result["communication_status"], "not_proven")
        self.assertIsNone(result["prior_communication_date"])

    def test_noncompliance_consequence_depends_on_structured_obligation_status(self):
        paid = self.base_answers(); paid["prior_communication_sent"] = "No"
        paid_result = enforce_habeas_prior_communication(paid, self.base_calculation())
        self.assertIn("retiro inmediato", paid_result["communication_consequence_if_noncompliance"].casefold())

        unpaid = self.base_answers(); unpaid["prior_communication_sent"] = "No"; unpaid["obligation_status"] = "Vigente y en mora"
        unpaid_result = enforce_habeas_prior_communication(unpaid, self.base_calculation())
        self.assertIn("antes de un eventual nuevo reporte", unpaid_result["communication_consequence_if_noncompliance"].casefold())

        unknown = self.base_answers(); unknown["prior_communication_sent"] = "No"; unknown.pop("obligation_status")
        unknown_result = enforce_habeas_prior_communication(unknown, self.base_calculation())
        self.assertIn("no puede seleccionarse", unknown_result["communication_consequence_if_noncompliance"].casefold())

    def test_runtime_installer_is_idempotent(self):
        module = ModuleType("fake_habeas_communication_core")
        module.habeas_data_calc = lambda answers: self.base_calculation()
        self.assertTrue(install_m33_3_habeas_communication_guard(module))
        first = module.habeas_data_calc
        self.assertTrue(install_m33_3_habeas_communication_guard(module))
        self.assertIs(module.habeas_data_calc, first)
        result = module.habeas_data_calc(self.base_answers())
        self.assertEqual(result["communication_status"], "preliminarily_supported")


if __name__ == "__main__":
    unittest.main()
