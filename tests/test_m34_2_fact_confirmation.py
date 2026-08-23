import sqlite3
import unittest

from legalai_platform.fact_extraction_m34_2 import FactExtractionService
from legalai_platform.intelligent_intake_m34_1 import IntelligentIntakeStore
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


class MemoryCrypto:
    PREFIX = b"encrypted-m342:"

    def encrypt(self, raw: bytes, aad: bytes) -> bytes:
        return self.PREFIX + len(aad).to_bytes(2, "big") + aad + raw[::-1]

    def decrypt(self, encrypted: bytes):
        if not encrypted.startswith(self.PREFIX):
            raise ValueError("bad envelope")
        payload = encrypted[len(self.PREFIX):]
        aad_length = int.from_bytes(payload[:2], "big")
        aad = payload[2:2 + aad_length]
        raw = payload[2 + aad_length:][::-1]
        return raw, aad


def memory_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("CREATE TABLE users(id TEXT PRIMARY KEY)")
    return con


class FactConfirmationM342Tests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.store = IntelligentIntakeStore(MemoryCrypto())
        self.store.create_schema(self.con)
        self.service = FactExtractionService()

    def tearDown(self):
        self.con.close()

    def _create_and_extract(self, narrative):
        created = self.store.create(self.con, narrative)
        extraction = self.service.extract(
            narrative,
            f"intake:{created['id']}:problem_statement",
        )
        state = self.store.apply_extraction(self.con, created["recovery_code"], extraction)
        self.con.commit()
        return created, state

    def test_confirm_creates_new_user_confirmed_fact_and_supersedes_candidate(self):
        created, state = self._create_and_extract(
            "Tengo una fotomulta y nunca me notificaron el comparendo. Quiero revisar qué hacer."
        )
        candidate = next(fact for fact in state["facts"] if fact["fact_type"] == "traffic.notification_status")
        result = self.store.confirm_fact_decisions(
            self.con,
            created["recovery_code"],
            [{"fact_id": candidate["fact_id"], "action": "CONFIRM"}],
        )
        original = next(fact for fact in result["facts"] if fact["fact_id"] == candidate["fact_id"])
        confirmed = next(fact for fact in result["facts"] if fact.get("source_reference") == candidate["fact_id"])
        self.assertEqual(original["provenance"], "AI_INFERRED")
        self.assertEqual(original["confirmation_status"], "SUPERSEDED")
        self.assertEqual(confirmed["provenance"], "USER_CONFIRMED")
        self.assertEqual(confirmed["confirmation_status"], "CONFIRMED_BY_USER")
        self.assertEqual(confirmed["value"], candidate["value"])
        self.assertFalse(fact_is_decision_usable(original))
        self.assertTrue(fact_is_decision_usable(confirmed))

    def test_edit_creates_user_confirmed_value_without_rewriting_candidate(self):
        created, state = self._create_and_extract(
            "Tengo una fotomulta y nunca me notificaron el comparendo. Quiero revisar qué hacer."
        )
        candidate = next(fact for fact in state["facts"] if fact["fact_type"] == "traffic.notification_status")
        result = self.store.confirm_fact_decisions(
            self.con,
            created["recovery_code"],
            [{"fact_id": candidate["fact_id"], "action": "EDIT", "value": "La notificación llegó a una dirección antigua"}],
        )
        original = next(fact for fact in result["facts"] if fact["fact_id"] == candidate["fact_id"])
        confirmed = next(fact for fact in result["facts"] if fact.get("source_reference") == candidate["fact_id"])
        self.assertEqual(original["value"], "NOT_NOTIFIED")
        self.assertEqual(original["confirmation_status"], "SUPERSEDED")
        self.assertEqual(confirmed["value"], "La notificación llegó a una dirección antigua")
        self.assertTrue(fact_is_decision_usable(confirmed))

    def test_dispute_keeps_machine_candidate_but_never_makes_it_usable(self):
        created, state = self._create_and_extract(
            "Compré un producto defectuoso y quiero reclamar la garantía. Pagué con tarjeta de crédito."
        )
        candidate = next(fact for fact in state["facts"] if fact["fact_type"] == "payment.method")
        result = self.store.confirm_fact_decisions(
            self.con,
            created["recovery_code"],
            [{"fact_id": candidate["fact_id"], "action": "DISPUTE"}],
        )
        disputed = next(fact for fact in result["facts"] if fact["fact_id"] == candidate["fact_id"])
        self.assertEqual(disputed["provenance"], "AI_INFERRED")
        self.assertEqual(disputed["confirmation_status"], "DISPUTED")
        self.assertFalse(fact_is_decision_usable(disputed))

    def test_partial_review_remains_pending_until_every_candidate_is_decided(self):
        created, state = self._create_and_extract(
            "Me despidieron el 15/08/2026. Mi salario era $2.500.000 y no me pagaron la liquidación. Quiero reclamar."
        )
        self.assertGreaterEqual(len(state["facts"]), 2)
        candidate = state["facts"][0]
        result = self.store.confirm_fact_decisions(
            self.con,
            created["recovery_code"],
            [{"fact_id": candidate["fact_id"], "action": "CONFIRM"}],
        )
        self.assertFalse(result["review_complete"])
        self.assertEqual(result["stage"], "FACTS_PENDING_CONFIRMATION")
        self.assertGreater(result["pending_fact_count"], 0)

    def test_review_complete_when_every_candidate_is_decided(self):
        created, state = self._create_and_extract(
            "Compré un producto defectuoso y quiero reclamar la garantía. Pagué con tarjeta de crédito."
        )
        decisions = [
            {"fact_id": fact["fact_id"], "action": "CONFIRM"}
            for fact in state["facts"]
        ]
        result = self.store.confirm_fact_decisions(self.con, created["recovery_code"], decisions)
        self.assertTrue(result["review_complete"])
        self.assertEqual(result["stage"], "FACTS_REVIEWED")
        self.assertEqual(result["pending_fact_count"], 0)
        self.assertEqual(len(result["confirmed_facts"]), len(state["facts"]))

    def test_editing_problem_invalidates_all_previous_extraction(self):
        created, state = self._create_and_extract(
            "Compré un producto defectuoso y quiero reclamar la garantía. Pagué con tarjeta de crédito."
        )
        self.assertTrue(state["facts"])
        updated = self.store.update_problem(
            self.con,
            created["recovery_code"],
            "Necesito revisar una compra, pero todavía no sé si corresponde garantía o alguna otra reclamación.",
        )
        self.assertEqual(updated["stage"], "PROBLEM_SUBMITTED")
        self.assertEqual(updated["facts"], [])
        self.assertEqual(updated["candidate_products"], [])
        self.assertIsNone(updated["extraction_provider"])
        self.assertEqual(updated["ai_processing_status"], "NOT_STARTED")

    def test_reanalysis_after_user_confirmation_requires_editing_narrative_first(self):
        created, state = self._create_and_extract(
            "Tengo una fotomulta y nunca me notificaron el comparendo. Quiero revisar qué hacer."
        )
        candidate = state["facts"][0]
        self.store.confirm_fact_decisions(
            self.con,
            created["recovery_code"],
            [{"fact_id": candidate["fact_id"], "action": "CONFIRM"}],
        )
        extraction = self.service.extract(
            state["problem_statement"],
            f"intake:{created['id']}:problem_statement",
        )
        with self.assertRaisesRegex(ValueError, "Ya confirmaste datos"):
            self.store.apply_extraction(self.con, created["recovery_code"], extraction)


if __name__ == "__main__":
    unittest.main()
