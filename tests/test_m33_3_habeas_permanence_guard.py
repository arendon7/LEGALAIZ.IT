from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_permanence_finalize import finalize_habeas_permanence_m33_3
from m33_3_habeas_permanence_guard import (
    PERMANENCE_STANDARD,
    RULESET_VERIFIED_AT,
    enforce_habeas_permanence,
    install_m33_3_habeas_permanence_guard,
)


class HabeasPermanenceGuardM333Tests(unittest.TestCase):
    def _calc(self) -> dict:
        return {
            "issues": [],
            "assumptions": [],
            "paid_negative_expiry_preliminary": None,
            "unpaid_negative_expiry_preliminary": None,
        }

    def _paid_calculation(self) -> dict:
        return enforce_habeas_permanence(
            {
                "obligation_status": "Pagada",
                "mora_start_date": "2023-08-11",
                "payment_or_extinction_date": "2024-08-10",
            },
            self._calc(),
        )

    def test_paid_route_uses_double_mora_and_marks_exact_anniversary_as_completed(self):
        calculation = self._paid_calculation()
        self.assertEqual(calculation["mora_duration_days"], 365)
        self.assertEqual(calculation["paid_negative_expiry_preliminary"], "2026-08-10")
        self.assertEqual(calculation["permanence_applicable_expiry"], "2026-08-10")
        self.assertTrue(calculation["permanence_term_completed_at_reference"])
        self.assertIn("CD1-CALC-12", {item["id"] for item in calculation["issues"]})

    def test_paid_route_caps_long_mora_at_four_civil_years(self):
        answers = {
            "obligation_status": "Extinguida por otro modo",
            "mora_start_date": "2017-01-01",
            "payment_or_extinction_date": "2021-01-01",
        }
        calculation = enforce_habeas_permanence(answers, self._calc())
        self.assertEqual(calculation["paid_negative_expiry_preliminary"], "2025-01-01")
        self.assertEqual(calculation["permanence_route"], "paid_or_extinguished")
        self.assertTrue(calculation["permanence_evidence_complete"])

    def test_unpaid_route_caducity_is_eight_civil_years_and_exact_day_counts(self):
        answers = {
            "obligation_status": "Vigente y en mora",
            "mora_start_date": "2018-08-10",
        }
        calculation = enforce_habeas_permanence(answers, self._calc())
        self.assertEqual(calculation["unpaid_negative_expiry_preliminary"], "2026-08-10")
        self.assertEqual(calculation["permanence_applicable_expiry"], "2026-08-10")
        self.assertTrue(calculation["permanence_term_completed_at_reference"])
        self.assertIn("CD1-CALC-13", {item["id"] for item in calculation["issues"]})
        message = next(item["message"] for item in calculation["issues"] if item["id"] == "CD1-CALC-13")
        self.assertIn("no extingue", message.casefold())

    def test_paid_status_without_dates_fails_closed_without_inventing_expiry(self):
        calculation = enforce_habeas_permanence(
            {"obligation_status": "Pagada"},
            self._calc(),
        )
        ids = {item["id"] for item in calculation["issues"]}
        self.assertIn("CD1-M33-PERM-MORA-MISSING", ids)
        self.assertIn("CD1-M33-PERM-EXTINCTION-MISSING", ids)
        self.assertIsNone(calculation["permanence_applicable_expiry"])
        self.assertFalse(calculation["permanence_evidence_complete"])
        self.assertIsNone(calculation["permanence_term_completed_at_reference"])

    def test_unpaid_status_without_mora_date_cannot_claim_eight_year_caducity(self):
        calculation = enforce_habeas_permanence(
            {"obligation_status": "Vigente y en mora"},
            self._calc(),
        )
        self.assertIn("CD1-M33-PERM-MORA-MISSING", {item["id"] for item in calculation["issues"]})
        self.assertIsNone(calculation["permanence_applicable_expiry"])
        self.assertFalse(calculation["permanence_evidence_complete"])

    def test_disputed_or_unrecognized_route_keeps_veracity_issue_primary(self):
        calculation = enforce_habeas_permanence(
            {
                "obligation_status": "No reconocida por el titular",
                "mora_start_date": "2020-01-01",
            },
            self._calc(),
        )
        self.assertEqual(calculation["permanence_route"], "disputed_or_unrecognized")
        self.assertIsNone(calculation["permanence_applicable_expiry"])
        self.assertFalse(calculation["permanence_evidence_complete"])
        issue = next(item for item in calculation["issues"] if item["id"] == "CD1-M33-PERM-STATUS")
        self.assertIn("no puede utilizarse para validar", issue["message"].casefold())

    def test_ruleset_is_auditable_and_does_not_use_law_2573_to_change_article_13(self):
        calculation = enforce_habeas_permanence(
            {
                "obligation_status": "Vigente y en mora",
                "mora_start_date": "2025-01-01",
            },
            self._calc(),
        )
        self.assertEqual(calculation["permanence_standard"], PERMANENCE_STANDARD)
        self.assertEqual(calculation["permanence_ruleset_verified_at"], RULESET_VERIFIED_AT)
        self.assertFalse(calculation["permanence_law_2573_changes_article_13"])
        basis = " ".join(calculation["permanence_legal_basis"])
        self.assertIn("Ley Estatutaria 1266", basis)
        self.assertIn("Resolución SIC 28170", basis)

    def test_visible_table_exposes_only_applicable_route_as_primary(self):
        calculation = self._paid_calculation()
        specs = [{
            "kind": "habeas_consultation",
            "sections": [{
                "heading": "V. CONTROL TEMPORAL PRELIMINAR",
                "table": [
                    ["Variable", "Dato disponible", "Uso jurídico"],
                    ["Retiro preliminar del dato pagado", "10 de agosto de 2026", "viejo"],
                    ["Caducidad preliminar del dato insoluto", "11 de agosto de 2031", "viejo"],
                ],
            }],
        }]
        finalized = finalize_habeas_permanence_m33_3(specs, {"calculation": calculation})
        table = finalized[0]["sections"][0]["table"]
        by_label = {row[0]: row for row in table[1:]}
        self.assertEqual(by_label["Retiro preliminar del dato pagado"][1], "10 de agosto de 2026")
        self.assertEqual(by_label["Caducidad preliminar del dato insoluto"][1], "No aplica como ruta principal")
        self.assertEqual(by_label["Ruta temporal aplicable"][1], "Obligación pagada o extinguida")
        self.assertIn("Término preliminar cumplido", by_label["Ruta temporal aplicable"][2])

    def test_deadline_calendar_replaces_two_hypotheses_without_increasing_table_rows(self):
        calculation = self._paid_calculation()
        original_table = [
            ["Variable", "Dato disponible", "Uso jurídico"],
            ["Inicio de mora", "11 de agosto de 2023", "control"],
            ["Pago o extinción", "10 de agosto de 2024", "control"],
            ["Duración de mora", "365", "control"],
            ["Retiro preliminar del dato pagado", "10 de agosto de 2026", "hipótesis"],
            ["Caducidad preliminar del dato insoluto", "11 de agosto de 2031", "hipótesis"],
        ]
        specs = [{
            "kind": "habeas_deadline_calendar",
            "sections": [{"heading": "4. HITOS DE PERMANENCIA", "table": original_table}],
        }]
        finalized = finalize_habeas_permanence_m33_3(specs, {"calculation": calculation})
        section = finalized[0]["sections"][0]
        table = section["table"]
        self.assertEqual(len(table), len(original_table))
        labels = [row[0] for row in table]
        self.assertNotIn("Retiro preliminar del dato pagado", labels)
        self.assertNotIn("Caducidad preliminar del dato insoluto", labels)
        self.assertIn("Ruta temporal aplicable", labels)
        self.assertIn("Fecha aplicable / corte M33.3", labels)
        self.assertNotIn("paragraphs", section)
        by_label = {row[0]: row for row in table[1:]}
        self.assertEqual(by_label["Fecha aplicable / corte M33.3"][1], "10 de agosto de 2026")
        self.assertIn("no declara pago", by_label["Fecha aplicable / corte M33.3"][2].casefold())

    def test_runtime_installer_is_idempotent(self):
        module = ModuleType("fake_habeas_permanence_core")

        def habeas_data_calc(answers):
            return self._calc()

        module.habeas_data_calc = habeas_data_calc
        self.assertTrue(install_m33_3_habeas_permanence_guard(module))
        first = module.habeas_data_calc
        self.assertTrue(install_m33_3_habeas_permanence_guard(module))
        self.assertIs(first, module.habeas_data_calc)
        result = module.habeas_data_calc({
            "obligation_status": "Vigente y en mora",
            "mora_start_date": "2018-08-10",
        })
        self.assertTrue(result["permanence_term_completed_at_reference"])


if __name__ == "__main__":
    unittest.main()
