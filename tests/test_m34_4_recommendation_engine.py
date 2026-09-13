import json
import sqlite3
import unittest

from legalai_platform.adaptive_question_m34_3 import AdaptiveQuestionEngine
from legalai_platform.recommendation_m34_4 import (
    ExplainableRecommendationEngine,
    RecommendationContractRegistry,
    RecommendationStore,
)


class MemoryCrypto:
    PREFIX = b"encrypted-m344:"

    def encrypt(self, raw: bytes, aad: bytes) -> bytes:
        return self.PREFIX + len(aad).to_bytes(2, "big") + aad + raw[::-1]

    def decrypt(self, encrypted: bytes):
        if not encrypted.startswith(self.PREFIX):
            raise ValueError("bad envelope")
        payload = encrypted[len(self.PREFIX):]
        aad_length = int.from_bytes(payload[:2], "big")
        aad = payload[2:2 + aad_length]
        return payload[2 + aad_length:][::-1], aad


def memory_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("CREATE TABLE users(id TEXT PRIMARY KEY)")
    return con


def fact(fact_type, value, index=0):
    return {
        "fact_id": f"fact_test_{index}_{fact_type.replace('.', '_')[:24]}",
        "fact_type": fact_type,
        "value": value,
        "normalized_value": value,
        "provenance": "USER_ASSERTED",
        "confirmation_status": "UNCONFIRMED",
        "criticality": "HIGH",
        "source_reference": "m34-question:test",
        "evidence_ids": [],
        "extraction_confidence": None,
        "legal_relevance": "HIGH",
        "created_at": None,
        "updated_at": None,
        "notes": "test",
    }


def substantive_value(contract):
    answer_type = contract.get("answer_type")
    options = contract.get("options") or []
    if answer_type == "select":
        choices = [item["value"] for item in options if str(item.get("value", "")).lower() not in {"no_se", "uncertain"}]
        if not choices:
            raise AssertionError(contract.get("question_contract_id"))
        return choices[0]
    if answer_type == "multiselect":
        return [options[0]["value"]]
    if answer_type == "date":
        return "2026-08-01"
    if answer_type == "money_cop":
        return {"amount_cop": 1800000, "currency": "COP"}
    if answer_type == "number":
        return 1
    if answer_type in {"text", "textarea"}:
        return "dato suficiente para orientar la solución"
    if answer_type == "boolean":
        return True
    raise AssertionError(answer_type)


class RecommendationFixture:
    def __init__(self):
        self.adaptive = AdaptiveQuestionEngine()
        self.recommendation = ExplainableRecommendationEngine()

    def ready_state(self, code, overrides=None):
        overrides = overrides or {}
        facts = []
        for index, fact_type in enumerate(self.adaptive.registry.requirements_for_product(code, "TRIAGE_REQUIRED")):
            contract = self.adaptive.registry.question_for_fact(fact_type, {code})
            if not contract:
                raise AssertionError(f"No question for {code}/{fact_type}")
            value = overrides.get(fact_type, substantive_value(contract))
            facts.append(fact(fact_type, value, index))
        state = {
            "stage": "QUESTIONING",
            "facts": facts,
            "pending_fact_count": 0,
            "risk_signals": [],
            "contradictions": [],
            "candidate_products": [{"product_code": code, "signal_score": 0.9, "status": "TOPIC_SIGNAL_ONLY"}],
            "routing": {},
            "question_history": [],
        }
        gate = self.adaptive.next_step(state)
        if gate["action"] != "READY_FOR_RECOMMENDATION":
            raise AssertionError(f"{code} fixture not ready: {gate}")
        return state, gate


class M344RecommendationContractTests(unittest.TestCase):
    def test_contract_registry_matches_all_11_product_contracts(self):
        registry = RecommendationContractRegistry()
        result = registry.validate()
        self.assertTrue(result.ok, "\n".join(result.errors))
        self.assertEqual(result.contracts, 11)
        self.assertEqual(set(registry.contracts), set(registry.product_contracts))

    def test_public_score_policy_is_explicitly_non_numeric(self):
        registry = RecommendationContractRegistry()
        self.assertEqual(registry.payload["public_score_policy"], "NEVER_EXPOSE_NUMERIC_FIT_SCORE")
        self.assertEqual(registry.payload["max_alternatives"], 2)


class M344RecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        self.fx = RecommendationFixture()

    def test_each_canonical_product_can_be_recommended_from_a_clean_ready_state(self):
        failures = []
        for code in sorted(self.fx.adaptive.products):
            state, gate = self.fx.ready_state(code)
            result = self.fx.recommendation.decide(state, gate)
            if result.get("outcome") != "RECOMMEND":
                failures.append(f"{code}: {result.get('outcome')} {result.get('reason_codes')}")
                continue
            if result.get("primary", {}).get("product_code") != code:
                failures.append(f"{code}: primary={result.get('primary', {}).get('product_code')}")
            public = {key: value for key, value in result.items() if key != "_internal"}
            serialized = json.dumps(public, ensure_ascii=False).lower()
            if "fit_score" in serialized or "signal_score" in serialized or '"score"' in serialized:
                failures.append(f"{code}: score numérico filtrado a salida pública")
            if "matched_fact_ids" in serialized or "matched_fact_types" in serialized:
                failures.append(f"{code}: metadata de hechos filtrada a salida pública")
        if failures:
            self.fail("\n".join(failures))

    def test_public_employment_is_outside_private_labor_product(self):
        state, gate = self.fx.ready_state("CO-LA-001", {"employment.relationship_scope": "empleo_publico"})
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "OUT_OF_SCOPE")
        self.assertIn("PUBLIC_EMPLOYMENT_OUTSIDE_PRODUCT", result["reason_codes"])

    def test_service_with_explicit_subordination_escalates_instead_of_recommending_service_contract(self):
        state, gate = self.fx.ready_state("CO-EM-003", {"services.autonomy": "horario_subordinacion"})
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "ESCALATE")
        self.assertIn("SUBORDINATION_SIGNAL_REQUIRES_REVIEW", result["reason_codes"])
        self.assertIn("CO-LA-002", result["possible_alternative_codes"])

    def test_commercial_lease_is_not_forced_into_urban_housing_product(self):
        state, gate = self.fx.ready_state("CO-AR-001", {"lease.property_use": "comercial"})
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "OUT_OF_SCOPE")
        self.assertIn("NON_RESIDENTIAL_LEASE_OUTSIDE_PRODUCT", result["reason_codes"])

    def test_notified_traffic_case_is_conditional_not_false_no_notification_claim(self):
        state, gate = self.fx.ready_state("CO-TR-002", {"traffic.notification_status": "NOTIFIED"})
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "RECOMMEND")
        self.assertEqual(result["primary"]["eligibility"], "CONDITIONAL")
        self.assertTrue(result["primary"]["warnings"])
        self.assertNotIn("no me notificaron", result["notice"].lower())

    def test_unresolved_risk_is_defense_in_depth_escalation(self):
        state, gate = self.fx.ready_state("CO-CD-003")
        state["risk_signals"] = [{"code": "DEADLINE_RISK", "status": "USER_UNCERTAIN"}]
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "ESCALATE")
        self.assertIn("DEADLINE_RISK", result["reason_codes"])

    def test_non_ready_gate_returns_ask_more_not_recommend(self):
        state = {
            "stage": "FACTS_REVIEWED",
            "facts": [],
            "pending_fact_count": 0,
            "risk_signals": [],
            "contradictions": [],
            "candidate_products": [{"product_code": "CO-CD-003", "signal_score": 0.9, "status": "TOPIC_SIGNAL_ONLY"}],
            "routing": {},
            "question_history": [],
        }
        gate = self.fx.adaptive.next_step(state)
        self.assertEqual(gate["action"], "ASK_QUESTION")
        result = self.fx.recommendation.decide(state, gate)
        self.assertEqual(result["outcome"], "ASK_MORE")


class M344RecommendationStoreTests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.store = RecommendationStore(MemoryCrypto())
        self.store.create_schema(self.con)
        self.adaptive = AdaptiveQuestionEngine()
        self.recommendation = ExplainableRecommendationEngine()
        self.fx = RecommendationFixture()

    def tearDown(self):
        self.con.close()

    def _ready_session(self):
        created = self.store.create(
            self.con,
            "Compré un producto defectuoso y quiero reclamar la garantía con tarjeta de crédito.",
        )
        state, _ = self.fx.ready_state("CO-CD-003")
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        payload["facts"] = state["facts"]
        payload["candidate_products"] = state["candidate_products"]
        payload["ai_processing_status"] = "LOCAL_EXTRACTION_COMPLETE"
        self.store._write_payload(self.con, row, payload, "QUESTIONING")
        self.con.commit()
        return created

    def test_same_inputs_reuse_exact_decision_id_and_keep_fingerprint_private(self):
        created = self._ready_session()
        first = self.store.recommend(self.con, created["recovery_code"], self.adaptive, self.recommendation)
        self.con.commit()
        second = self.store.recommend(self.con, created["recovery_code"], self.adaptive, self.recommendation)
        self.assertEqual(first["decision_id"], second["decision_id"])
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertNotIn("input_fingerprint", first)
        self.assertNotIn("input_fingerprint", second)
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        decisions = payload["m34_4"]["decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertTrue(decisions[0].get("input_fingerprint"))

    def test_decision_record_keeps_internal_ranking_encrypted_but_public_result_strips_it(self):
        created = self._ready_session()
        result = self.store.recommend(self.con, created["recovery_code"], self.adaptive, self.recommendation)
        self.con.commit()
        self.assertNotIn("_internal", result)
        self.assertNotIn("input_fingerprint", result)
        self.assertNotIn("matched_fact_ids", result.get("primary", {}))
        self.assertNotIn("matched_fact_types", result.get("primary", {}))
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        records = payload["m34_4"]["decisions"]
        self.assertEqual(len(records), 1)
        self.assertIn("_internal", records[0]["result"])
        self.assertTrue(records[0].get("input_fingerprint"))
        self.assertEqual(records[0]["decision_id"], result["decision_id"])


if __name__ == "__main__":
    unittest.main()
