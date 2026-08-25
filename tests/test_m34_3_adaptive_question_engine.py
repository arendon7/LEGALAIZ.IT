import sqlite3
import unittest

from legalai_platform.adaptive_question_m34_3 import (
    AdaptiveIntakeStore,
    AdaptiveQuestionEngine,
    QuestionContractRegistry,
)
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


class MemoryCrypto:
    PREFIX = b"encrypted-m343:"

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


def asserted_fact(fact_type, value="dato"):
    return {
        "fact_id": "fact_user_" + fact_type.replace(".", "_")[:30],
        "fact_type": fact_type,
        "value": value,
        "normalized_value": value,
        "provenance": "USER_ASSERTED",
        "confirmation_status": "UNCONFIRMED",
        "criticality": "HIGH",
        "source_reference": "test:direct-user-answer",
        "evidence_ids": [],
        "extraction_confidence": None,
        "legal_relevance": "HIGH",
        "created_at": None,
        "updated_at": None,
        "notes": "test",
    }


class M343QuestionContractTests(unittest.TestCase):
    def test_registry_covers_every_product_requirement_exactly_once(self):
        registry = QuestionContractRegistry()
        result = registry.validate()
        self.assertTrue(result.ok, "\n".join(result.errors))
        distinct_fact_types = {item["fact_type"] for item in registry.fact_questions}
        self.assertEqual(len(distinct_fact_types), 55)
        self.assertEqual(len(registry.products), 11)
        self.assertEqual(result.risk_contracts, 5)

    def test_deferred_facts_never_become_pre_recommendation_questions(self):
        registry = QuestionContractRegistry()
        deferred = [item for item in registry.fact_questions if item["requirement_mode"] == "FULFILLMENT_ONLY"]
        self.assertEqual(len(deferred), 14)
        for item in deferred:
            self.assertEqual(item["source_mode"], "DEFERRED")
            self.assertIsNone(item.get("prompt"))
            self.assertIsNone(registry.question_for_fact(item["fact_type"], set(item["products"])))

    def test_routing_contract_covers_all_11_products_without_recommendation_language(self):
        registry = QuestionContractRegistry()
        options = registry.broad_routing["options"]
        codes = {code for option in options for code in option["product_codes"]}
        self.assertEqual(codes, set(registry.products))
        self.assertNotIn("recomend", registry.broad_routing["prompt"].lower())


class M343EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveQuestionEngine()

    def state(self, **updates):
        state = {
            "stage": "FACTS_REVIEWED",
            "facts": [],
            "pending_fact_count": 0,
            "risk_signals": [],
            "contradictions": [],
            "candidate_products": [],
            "routing": {},
            "question_history": [],
        }
        state.update(updates)
        return state

    def test_without_topic_signal_engine_routes_instead_of_guessing_a_legal_question(self):
        step = self.engine.next_step(self.state())
        self.assertEqual(step["action"], "ROUTE_TOPIC")
        self.assertEqual(step["question"]["kind"], "ROUTING")
        self.assertEqual(step["product_scope"], [])

    def test_single_topic_signal_enters_questions_but_does_not_recommend(self):
        step = self.engine.next_step(
            self.state(candidate_products=[{
                "product_code": "CO-CD-003",
                "signal_score": 0.8,
                "status": "TOPIC_SIGNAL_ONLY",
            }])
        )
        self.assertEqual(step["action"], "ASK_QUESTION")
        self.assertEqual(step["product_scope"], ["CO-CD-003"])
        self.assertNotIn("recommendation", step)

    def test_two_close_labor_signals_require_neutral_disambiguation(self):
        step = self.engine.next_step(
            self.state(candidate_products=[
                {"product_code": "CO-LA-001", "signal_score": 0.72, "status": "TOPIC_SIGNAL_ONLY"},
                {"product_code": "CO-LA-002", "signal_score": 0.68, "status": "TOPIC_SIGNAL_ONLY"},
            ], routing={"broad": {"product_codes": ["CO-LA-001", "CO-LA-002"]}})
        )
        self.assertEqual(step["action"], "ROUTE_TOPIC")
        self.assertEqual(step["question"]["question_id"], "m34_route_laboral")

    def test_existing_usable_fact_is_not_asked_again(self):
        fact = asserted_fact("consumer.issue_type", "GARANTIA")
        self.assertTrue(fact_is_decision_usable(fact))
        step = self.engine.next_step(
            self.state(
                facts=[fact],
                candidate_products=[{"product_code": "CO-CD-003", "signal_score": 0.8, "status": "TOPIC_SIGNAL_ONLY"}],
            )
        )
        self.assertEqual(step["action"], "ASK_QUESTION")
        self.assertNotEqual(step["question"]["question_id"], "m34_consumer_issue_type")

    def test_fulfillment_only_facts_do_not_block_sufficiency(self):
        code = "CO-CD-003"
        required = self.engine.registry.requirements_for_product(code, "TRIAGE_REQUIRED")
        facts = [asserted_fact(fact_type, "dato") for fact_type in required]
        step = self.engine.next_step(
            self.state(
                facts=facts,
                candidate_products=[{"product_code": code, "signal_score": 0.9, "status": "TOPIC_SIGNAL_ONLY"}],
            )
        )
        self.assertEqual(step["action"], "READY_FOR_RECOMMENDATION")
        deferred = step["sufficiency"]["per_product"][code]["deferred_for_fulfillment"]
        self.assertIn("consumer.supplier", deferred)

    def test_uncertain_answer_is_not_counted_as_sufficient(self):
        fact = asserted_fact("consumer.issue_type", "NO_SE")
        known = self.engine.sufficient_fact_types([fact])
        self.assertNotIn("consumer.issue_type", known)

    def test_unconfirmed_risk_precedes_ordinary_questions(self):
        step = self.engine.next_step(
            self.state(
                candidate_products=[{"product_code": "CO-CD-003", "signal_score": 0.8, "status": "TOPIC_SIGNAL_ONLY"}],
                risk_signals=[{"code": "DEADLINE_RISK", "status": "UNCONFIRMED_SIGNAL"}],
            )
        )
        self.assertEqual(step["action"], "CONFIRM_RISK")
        self.assertEqual(step["reason_codes"], ["DEADLINE_RISK"])

    def test_confirmed_blocking_risk_escalates_instead_of_recommending(self):
        step = self.engine.next_step(
            self.state(
                candidate_products=[{"product_code": "CO-CD-003", "signal_score": 0.8, "status": "TOPIC_SIGNAL_ONLY"}],
                risk_signals=[{"code": "DEADLINE_RISK", "status": "CONFIRMED_BY_USER"}],
            )
        )
        self.assertEqual(step["action"], "ESCALATE")
        self.assertIn("DEADLINE_RISK", step["reason_codes"])

    def test_other_topic_is_out_of_catalog_not_forced_into_product(self):
        state = self.state(routing={"broad": {"question_id": "m34_route_topic", "value": "otro", "product_codes": []}})
        step = self.engine.next_step(state)
        self.assertEqual(step["action"], "OUT_OF_SCOPE")
        self.assertEqual(step["product_scope"], [])


class M343StoreTests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.store = AdaptiveIntakeStore(MemoryCrypto())
        self.store.create_schema(self.con)
        self.engine = AdaptiveQuestionEngine()

    def tearDown(self):
        self.con.close()

    def _session_ready_for_questions(self, problem="Compré un producto defectuoso y quiero revisar la garantía antes de reclamar."):
        created = self.store.create(self.con, problem)
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        payload["candidate_products"] = [{
            "product_code": "CO-CD-003",
            "signal_score": 0.9,
            "reason_codes": ["garantia"],
            "status": "TOPIC_SIGNAL_ONLY",
        }]
        payload["ai_processing_status"] = "LOCAL_EXTRACTION_COMPLETE"
        self.store._write_payload(self.con, row, payload, "FACTS_REVIEWED")
        self.con.commit()
        return created

    def test_fact_answer_creates_user_asserted_traceable_fact(self):
        created = self._session_ready_for_questions()
        step = self.store.next_step(self.con, created["recovery_code"], self.engine)
        self.assertEqual(step["action"], "ASK_QUESTION")
        result = self.store.answer(
            self.con,
            created["recovery_code"],
            self.engine,
            step["question"]["question_id"],
            step["question"]["options"][0]["value"] if step["question"]["options"] else "dato",
        )
        self.con.commit()
        recovered = self.store.recover(self.con, created["recovery_code"])
        asserted = [fact for fact in recovered["facts"] if fact["provenance"] == "USER_ASSERTED"]
        self.assertEqual(len(asserted), 1)
        self.assertTrue(asserted[0]["source_reference"].startswith("m34-question:"))
        self.assertTrue(fact_is_decision_usable(asserted[0]))
        self.assertIn(result["action"], {"ASK_QUESTION", "READY_FOR_RECOMMENDATION"})

    def test_answer_to_stale_question_is_rejected(self):
        created = self._session_ready_for_questions()
        with self.assertRaisesRegex(ValueError, "pregunta ya cambió"):
            self.store.answer(self.con, created["recovery_code"], self.engine, "fake_question", "x")

    def test_routing_answer_is_not_written_as_legal_fact(self):
        created = self.store.create(self.con, "Tengo una situación jurídica y no sé todavía a qué tema corresponde exactamente.")
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        self.store._write_payload(self.con, row, payload, "FACTS_NOT_FOUND")
        self.con.commit()
        step = self.store.next_step(self.con, created["recovery_code"], self.engine)
        self.assertEqual(step["action"], "ROUTE_TOPIC")
        result = self.store.answer(self.con, created["recovery_code"], self.engine, step["question"]["question_id"], "consumo")
        self.con.commit()
        recovered = self.store.recover(self.con, created["recovery_code"])
        self.assertEqual(recovered["facts"], [])
        self.assertEqual(result["product_scope"], ["CO-CD-003"])

    def test_m343_state_self_invalidates_when_original_problem_changes(self):
        created = self._session_ready_for_questions()
        self.store.next_step(self.con, created["recovery_code"], self.engine)
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        state = self.store._m343(payload)
        state["routing"] = {"broad": {"product_codes": ["CO-CD-003"]}}
        payload["problem_statement"] = "Ahora necesito revisar una fotomulta y su notificación."
        self.assertEqual(self.store._m343(payload)["routing"], {})


if __name__ == "__main__":
    unittest.main()
