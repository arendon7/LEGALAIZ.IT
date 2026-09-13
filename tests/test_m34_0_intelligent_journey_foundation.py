import unittest

from legalai_platform.m34_intelligent_journey import (
    ConfirmationStatus,
    FactCriticality,
    FactProvenance,
    NextAction,
    fact_is_decision_usable,
    load_product_contracts,
    missing_recommendation_facts,
    portfolio_inventory,
    validate_foundation,
    validate_legal_fact,
)


EXPECTED_PRODUCTS = {
    "CO-AR-001",
    "CO-CD-001",
    "CO-CD-003",
    "CO-CD-004",
    "CO-EM-003",
    "CO-EM-004",
    "CO-LA-001",
    "CO-LA-002",
    "CO-SA-001",
    "CO-TR-001",
    "CO-TR-002",
}


def fact(
    fact_id="fact_test",
    fact_type="goal.requested_outcome",
    value="Resolver",
    provenance=FactProvenance.USER_ASSERTED.value,
    confirmation=ConfirmationStatus.UNCONFIRMED.value,
    criticality=FactCriticality.MEDIUM.value,
):
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "value": value,
        "provenance": provenance,
        "confirmation_status": confirmation,
        "criticality": criticality,
        "source_reference": "message_001",
        "extraction_confidence": 0.99,
    }


class M34FoundationTests(unittest.TestCase):
    def test_11_product_contracts_match_the_current_portfolio(self):
        contracts = load_product_contracts()
        self.assertEqual(set(contracts), EXPECTED_PRODUCTS)
        self.assertEqual(len(contracts), 11)

    def test_runtime_and_advanced_library_keep_the_no_regression_floor(self):
        inventory = portfolio_inventory()
        self.assertEqual(inventory.products, 11)
        self.assertGreaterEqual(inventory.questions, 473)
        self.assertGreaterEqual(inventory.rules, 273)
        self.assertEqual(set(inventory.interview_product_codes), EXPECTED_PRODUCTS)
        self.assertEqual(set(inventory.rule_product_codes), EXPECTED_PRODUCTS)
        self.assertEqual(set(inventory.advanced_product_codes), EXPECTED_PRODUCTS)

    def test_foundation_validator_is_fail_closed(self):
        result = validate_foundation()
        self.assertTrue(result.ok, "\n".join(result.errors))
        self.assertEqual(result.errors, ())

    def test_every_product_has_a_human_problem_and_minimum_fact_set(self):
        for code, contract in load_product_contracts().items():
            with self.subTest(code=code):
                self.assertTrue(contract["public_name"].strip())
                self.assertTrue(contract["human_problem"].strip())
                self.assertGreaterEqual(len(contract["minimum_recommendation_facts"]), 5)
                self.assertTrue(contract["critical_fact_domains"])
                self.assertTrue(contract["blocking_risks"])

    def test_ai_inference_cannot_be_silently_confirmed(self):
        candidate = fact(
            provenance=FactProvenance.AI_INFERRED.value,
            confirmation=ConfirmationStatus.CONFIRMED_BY_USER.value,
        )
        errors = validate_legal_fact(candidate)
        self.assertTrue(any("silently promoted" in error for error in errors))
        self.assertFalse(fact_is_decision_usable(candidate))

    def test_ai_inference_is_not_decision_usable_before_confirmation_event(self):
        candidate = fact(
            provenance=FactProvenance.AI_INFERRED.value,
            confirmation=ConfirmationStatus.UNCONFIRMED.value,
        )
        self.assertEqual(validate_legal_fact(candidate), ())
        self.assertFalse(fact_is_decision_usable(candidate))

    def test_document_extraction_requires_confirmation_before_decisive_use(self):
        extracted = fact(
            provenance=FactProvenance.DOCUMENT_EXTRACTED.value,
            confirmation=ConfirmationStatus.UNCONFIRMED.value,
        )
        confirmed = fact(
            fact_id="fact_doc_confirmed",
            provenance=FactProvenance.DOCUMENT_EXTRACTED.value,
            confirmation=ConfirmationStatus.CONFIRMED_BY_USER.value,
        )
        self.assertFalse(fact_is_decision_usable(extracted))
        self.assertTrue(fact_is_decision_usable(confirmed))

    def test_user_assertion_is_traceable_and_usable_as_an_assertion(self):
        asserted = fact()
        self.assertEqual(validate_legal_fact(asserted), ())
        self.assertTrue(fact_is_decision_usable(asserted))

    def test_disputed_fact_is_never_decision_usable(self):
        disputed = fact(
            provenance=FactProvenance.DISPUTED.value,
            confirmation=ConfirmationStatus.DISPUTED.value,
        )
        self.assertEqual(validate_legal_fact(disputed), ())
        self.assertFalse(fact_is_decision_usable(disputed))

    def test_missing_fact_engine_uses_product_contract_not_static_form_order(self):
        contract = load_product_contracts()["CO-EM-003"]
        required = contract["minimum_recommendation_facts"]
        supplied = [
            fact(
                fact_id=f"fact_{index}",
                fact_type=fact_type,
                value="confirmed",
            )
            for index, fact_type in enumerate(required[:-1], start=1)
        ]
        missing = missing_recommendation_facts("CO-EM-003", supplied)
        self.assertEqual(missing, (required[-1],))

    def test_only_four_m34_decision_outcomes_exist(self):
        self.assertEqual(
            {item.value for item in NextAction},
            {"RECOMMEND", "ASK_MORE", "ESCALATE", "OUT_OF_SCOPE"},
        )


if __name__ == "__main__":
    unittest.main()
