from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_law2573_transition import (
    TRANSITION_STANDARD,
    enforce_law2573_transition,
    finalize_law2573_transition,
    install_m33_3_habeas_law2573_guard,
)


class HabeasLaw2573TransitionM333Tests(unittest.TestCase):
    def answers(self) -> dict:
        return {
            "filing_date": "2026-08-07",
            "identity_theft": "Sí",
            "identity_theft_correction_requested": "Sí",
            "identity_theft_security_noncompliance_verified": "No sé",
        }

    def calculation(self) -> dict:
        return {"reference_date": "2026-08-07", "issues": []}

    def test_august_2026_only_immediate_paragraphs_are_active(self):
        result = enforce_law2573_transition(self.answers(), self.calculation())
        self.assertEqual(result["law2573_transition_standard"], TRANSITION_STANDARD)
        self.assertEqual(result["law2573_transition_phase"], "partial_immediate_only")
        self.assertEqual(result["law2573_article5_paragraph1_status"], "in_force_regulatory_mandate")
        self.assertEqual(result["law2573_article5_paragraph2_status"], "not_proven_security_noncompliance")
        self.assertEqual(result["law2573_articles_6_to_10_status"], "deferred_until_2026-11-20")
        self.assertTrue(result["law2573_human_review_required"])

    def test_paragraph2_candidate_requires_correction_verified_breach_and_complete_support(self):
        answers = self.answers()
        answers["identity_theft_security_noncompliance_verified"] = "Sí"
        answers["identity_theft_security_noncompliance_support"] = "Completo"
        result = enforce_law2573_transition(answers, self.calculation())
        self.assertEqual(result["law2573_article5_paragraph2_status"], "preliminary_candidate_human_review_required")
        self.assertTrue(result["law2573_human_review_required"])
        self.assertTrue(any("revisión jurídica humana" in reason for reason in result["law2573_transition_reasons"]))

    def test_alleged_fraud_alone_never_activates_paragraph2(self):
        answers = self.answers()
        answers["identity_theft_correction_requested"] = "No sé"
        answers["identity_theft_security_noncompliance_verified"] = "No sé"
        result = enforce_law2573_transition(answers, self.calculation())
        self.assertNotEqual(result["law2573_article5_paragraph2_status"], "preliminary_candidate_human_review_required")

    def test_no_correction_request_blocks_paragraph2_candidate(self):
        answers = self.answers(); answers["identity_theft_correction_requested"] = "No"
        answers["identity_theft_security_noncompliance_verified"] = "Sí"
        answers["identity_theft_security_noncompliance_support"] = "Completo"
        result = enforce_law2573_transition(answers, self.calculation())
        self.assertEqual(result["law2573_article5_paragraph2_status"], "not_applicable_without_correction_request")

    def test_verified_breach_with_partial_support_fails_closed(self):
        answers = self.answers()
        answers["identity_theft_security_noncompliance_verified"] = "Sí"
        answers["identity_theft_security_noncompliance_support"] = "Parcial"
        result = enforce_law2573_transition(answers, self.calculation())
        self.assertEqual(result["law2573_article5_paragraph2_status"], "not_proven_security_support")
        self.assertTrue(result["law2573_human_review_required"])

    def test_pre_promulgation_case_does_not_apply_law(self):
        calculation = {"reference_date": "2026-05-19"}
        result = enforce_law2573_transition(self.answers(), calculation)
        self.assertEqual(result["law2573_transition_phase"], "pre_promulgation")
        self.assertEqual(result["law2573_article5_paragraph1_status"], "not_yet_effective")
        self.assertEqual(result["law2573_article5_paragraph2_status"], "not_yet_effective")

    def test_general_effective_date_changes_phase_but_not_to_automatic_relief(self):
        calculation = {"reference_date": "2026-11-20"}
        result = enforce_law2573_transition(self.answers(), calculation)
        self.assertEqual(result["law2573_transition_phase"], "general_regime_effective")
        self.assertEqual(result["law2573_articles_6_to_10_status"], "general_regime_effective_article_by_article_review")
        self.assertNotEqual(result["law2573_article5_paragraph2_status"], "preliminary_candidate_human_review_required")

    def test_identity_protocol_replaces_overbroad_deferred_sentence(self):
        calculation = enforce_law2573_transition(self.answers(), self.calculation())
        specs = [{
            "kind": "identity_theft_protocol",
            "sections": [{
                "heading": "2. RÉGIMEN JURÍDICO Y CONTROL TEMPORAL",
                "numbered": [
                    "Base vigente.",
                    "Mientras no haya entrado en vigor el régimen general diferido de la Ley 2573 de 2026, la ruta debe operar con las reglas actualmente vigentes de la Ley 1266 de 2008 y la Ley 2157 de 2021, sin anticipar términos, cargas o efectos futuros.",
                ],
            }],
        }]
        finalized = finalize_law2573_transition(specs, self.answers(), {"calculation": calculation})
        numbered = finalized[0]["sections"][0]["numbered"]
        text = " ".join(numbered)
        self.assertNotIn("Mientras no haya entrado en vigor el régimen general diferido", text)
        self.assertIn("parágrafos 1 y 2 del artículo 5", text)
        self.assertIn("artículos 6 a 10", text)
        self.assertIn("no están demostrados todos los presupuestos", text)

    def test_runtime_installer_is_idempotent(self):
        module = ModuleType("fake_law2573_core")
        module.habeas_data_calc = lambda answers: self.calculation()
        self.assertTrue(install_m33_3_habeas_law2573_guard(module))
        first = module.habeas_data_calc
        self.assertTrue(install_m33_3_habeas_law2573_guard(module))
        self.assertIs(module.habeas_data_calc, first)
        result = module.habeas_data_calc(self.answers())
        self.assertEqual(result["law2573_transition_phase"], "partial_immediate_only")


if __name__ == "__main__":
    unittest.main()
