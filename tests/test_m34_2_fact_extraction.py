import unittest

from legalai_platform.fact_extraction_m34_2 import (
    ConservativeNarrativeProvider,
    FactExtractionService,
)
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


class UnknownFactProvider:
    provider_id = "test.unknown-fact"
    provider_mode = "TEST"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {
            "facts": [{
                "fact_type": "invented.legal_conclusion",
                "value": "ganara el caso",
                "confidence": 0.99,
                "criticality": "HIGH",
                "legal_relevance": "CRITICAL",
            }],
            "candidate_products": [],
            "risk_signals": [],
            "contradictions": [],
        }


class UnknownRiskProvider:
    provider_id = "test.unknown-risk"
    provider_mode = "TEST"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {
            "facts": [],
            "candidate_products": [],
            "risk_signals": [{"code": "MADE_UP_RISK", "confidence": 0.9}],
            "contradictions": [],
        }


class PromotionAttemptProvider:
    provider_id = "test.promotion-attempt"
    provider_mode = "TEST"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {
            "facts": [{
                "fact_type": "goal.requested_outcome",
                "value": "reclamar_o_solicitar",
                "confidence": 0.8,
                "criticality": "MEDIUM",
                "legal_relevance": "MEDIUM",
                "provenance": "USER_CONFIRMED",
                "confirmation_status": "CONFIRMED_BY_USER",
            }],
            "candidate_products": [],
            "risk_signals": [],
            "contradictions": [],
        }


class BadMetadataProvider:
    provider_id = "provider id with spaces and secrets"
    provider_mode = "unsafe mode"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {"facts": [], "candidate_products": [], "risk_signals": [], "contradictions": []}


class OversizedValueProvider:
    provider_id = "test.oversized"
    provider_mode = "TEST"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {
            "facts": [{
                "fact_type": "goal.requested_outcome",
                "value": "x" * 5000,
                "confidence": 0.8,
                "criticality": "MEDIUM",
                "legal_relevance": "MEDIUM",
            }],
            "candidate_products": [],
            "risk_signals": [],
            "contradictions": [],
        }


class UnsafeReasonProvider:
    provider_id = "test.unsafe-reason"
    provider_mode = "TEST"
    ai_enabled = True

    def extract(self, problem_statement, allowed_fact_types):
        return {
            "facts": [],
            "candidate_products": [{
                "product_code": "CO-LA-001",
                "signal_score": 0.7,
                "reason_codes": ["raw narrative must not be copied here"],
            }],
            "risk_signals": [],
            "contradictions": [],
        }


class FactExtractionM342Tests(unittest.TestCase):
    def test_local_provider_extracts_only_candidates_not_decision_facts(self):
        service = FactExtractionService(ConservativeNarrativeProvider())
        result = service.extract(
            "Me despidieron el 15/08/2026. Mi salario era $2.500.000 y no me pagaron la liquidación. Quiero reclamar.",
            "intake:INT-TEST:problem_statement",
        )
        self.assertEqual(result["provider"]["mode"], "LOCAL_CONSERVATIVE")
        self.assertFalse(result["provider"]["ai_enabled"])
        fact_types = {fact["fact_type"] for fact in result["facts"]}
        self.assertIn("employment.end_date", fact_types)
        self.assertIn("employment.compensation_basis", fact_types)
        self.assertIn("employment.pending_concepts", fact_types)
        self.assertIn("goal.requested_outcome", fact_types)
        self.assertTrue(result["requires_user_confirmation"])
        self.assertEqual(result["next_action"], "CONFIRM_FACTS")
        for fact in result["facts"]:
            self.assertEqual(fact["provenance"], "AI_INFERRED")
            self.assertEqual(fact["confirmation_status"], "UNCONFIRMED")
            self.assertFalse(fact_is_decision_usable(fact))
        self.assertIn("CO-LA-001", {item["product_code"] for item in result["candidate_products"]})

    def test_provider_cannot_promote_its_output_to_confirmed(self):
        result = FactExtractionService(PromotionAttemptProvider()).extract(
            "Quiero reclamar un incumplimiento y revisar qué puedo hacer.",
            "intake:INT-TEST:problem_statement",
        )
        fact = result["facts"][0]
        self.assertEqual(fact["provenance"], "AI_INFERRED")
        self.assertEqual(fact["confirmation_status"], "UNCONFIRMED")
        self.assertFalse(fact_is_decision_usable(fact))

    def test_unknown_fact_type_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "tipo de hecho no permitido"):
            FactExtractionService(UnknownFactProvider()).extract(
                "Tengo un problema jurídico suficientemente descrito para esta prueba.",
                "intake:INT-TEST:problem_statement",
            )

    def test_unknown_risk_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Señal de riesgo no soportada"):
            FactExtractionService(UnknownRiskProvider()).extract(
                "Tengo un problema jurídico suficientemente descrito para esta prueba.",
                "intake:INT-TEST:problem_statement",
            )

    def test_invalid_provider_metadata_fails_before_provider_output_is_trusted(self):
        with self.assertRaisesRegex(ValueError, "identificador del proveedor"):
            FactExtractionService(BadMetadataProvider()).extract(
                "Tengo un problema jurídico suficientemente descrito para esta prueba.",
                "intake:INT-TEST:problem_statement",
            )

    def test_oversized_fact_value_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "excede el límite"):
            FactExtractionService(OversizedValueProvider()).extract(
                "Tengo un problema jurídico suficientemente descrito para esta prueba.",
                "intake:INT-TEST:problem_statement",
            )

    def test_reason_codes_must_be_codes_not_free_form_narrative(self):
        with self.assertRaisesRegex(ValueError, "Código de razón inválido"):
            FactExtractionService(UnsafeReasonProvider()).extract(
                "Tengo un problema jurídico suficientemente descrito para esta prueba.",
                "intake:INT-TEST:problem_statement",
            )

    def test_local_provider_detects_explicit_risk_without_calling_it_a_conclusion(self):
        result = FactExtractionService().extract(
            "Tengo una demanda en curso en un juzgado y una audiencia judicial. Necesito revisar qué hacer.",
            "intake:INT-TEST:problem_statement",
        )
        risks = {item["code"]: item for item in result["risk_signals"]}
        self.assertIn("LITIGATION_ACTIVE", risks)
        self.assertEqual(risks["LITIGATION_ACTIVE"]["status"], "UNCONFIRMED_SIGNAL")

    def test_product_signals_are_not_recommendations(self):
        result = FactExtractionService().extract(
            "Tengo una fotomulta y nunca me notificaron el comparendo. Quiero revisar el caso.",
            "intake:INT-TEST:problem_statement",
        )
        self.assertTrue(result["candidate_products"])
        self.assertTrue(all(item["status"] == "TOPIC_SIGNAL_ONLY" for item in result["candidate_products"]))
        self.assertNotIn("recommendation", result)
        self.assertNotIn("recommended_product", result)


if __name__ == "__main__":
    unittest.main()
