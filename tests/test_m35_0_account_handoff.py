import sqlite3
import unittest

from legalai_platform.handoff_m35_0 import (
    AccountHandoffStore,
    HandoffConflictError,
    HandoffStateError,
)


class MemoryCrypto:
    PREFIX = b"encrypted-m350:"

    def encrypt(self, raw: bytes, aad: bytes) -> bytes:
        return self.PREFIX + len(aad).to_bytes(2, "big") + aad + raw[::-1]

    def decrypt(self, encrypted: bytes):
        if not encrypted.startswith(self.PREFIX):
            raise ValueError("bad envelope")
        payload = encrypted[len(self.PREFIX):]
        aad_length = int.from_bytes(payload[:2], "big")
        aad = payload[2:2 + aad_length]
        return payload[2 + aad_length:][::-1], aad


class FakeSelfService:
    def __init__(self):
        self.products = {"CO-CD-003": {"code": "CO-CD-003"}}
        self.drafts = {}
        self.counter = 0

    def get_product_draft(self, con, user_id, product_code):
        return self.drafts.get((user_id, product_code))

    def save_draft(self, con, user_id, product_code, answers, current_step=0, title="", result=None):
        self.counter += 1
        draft = {
            "id": f"DRF-TEST-{self.counter}",
            "user_id": user_id,
            "product_code": product_code,
            "answers": answers,
            "current_step": current_step,
            "title": title,
            "result": result,
            "status": "En progreso",
        }
        self.drafts[(user_id, product_code)] = draft
        return draft


def memory_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute(
        """CREATE TABLE users(
             id TEXT PRIMARY KEY,
             role TEXT NOT NULL,
             active INTEGER NOT NULL DEFAULT 1
           )"""
    )
    con.executemany(
        "INSERT INTO users(id,role,active) VALUES(?,?,?)",
        [
            ("USR-A", "client", 1),
            ("USR-B", "client", 1),
            ("USR-S", "specialist", 1),
            ("USR-OFF", "client", 0),
        ],
    )
    return con


class M350AccountHandoffTests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.self_service = FakeSelfService()
        self.store = AccountHandoffStore(MemoryCrypto(), self.self_service)
        self.store.create_schema(self.con)

    def tearDown(self):
        self.con.close()

    def _recommended_intake(self):
        created = self.store.create(
            self.con,
            "Compré un producto defectuoso y quiero continuar con la solución recomendada.",
        )
        row = self.store._active_row(self.con, created["recovery_code"])
        payload = self.store._decrypt(row)
        payload["facts"] = [
            {
                "fact_id": "fact_sensitive_demo",
                "fact_type": "consumer.issue_type",
                "value": "GARANTIA",
                "normalized_value": "GARANTIA",
                "provenance": "USER_ASSERTED",
                "confirmation_status": "UNCONFIRMED",
                "criticality": "HIGH",
                "source_reference": "m34-question:test",
                "evidence_ids": [],
                "extraction_confidence": None,
                "legal_relevance": "HIGH",
                "created_at": None,
                "updated_at": None,
                "notes": "valor que debe permanecer cifrado",
            }
        ]
        payload["m34_4"] = {
            "schema_version": "34.4.0",
            "current_decision_id": "REC-TEST-0001",
            "decisions": [
                {
                    "decision_id": "REC-TEST-0001",
                    "schema_version": "34.4.0",
                    "decided_at": "2026-08-23T22:00:00+00:00",
                    "input_fingerprint": "private-fingerprint",
                    "result": {
                        "outcome": "RECOMMEND",
                        "primary": {
                            "product_code": "CO-CD-003",
                            "public_title": "Reclamar por una compra o servicio que salió mal",
                            "eligibility": "PASS",
                            "review_requirement": "RISK_BASED",
                        },
                        "alternatives": [],
                    },
                }
            ],
        }
        self.store._write_payload(self.con, row, payload, "RECOMMENDED")
        self.con.commit()
        return created

    def test_claim_transfers_once_and_creates_minimal_fulfillment_draft(self):
        created = self._recommended_intake()
        result = self.store.claim(self.con, created["recovery_code"], "USR-A")
        self.con.commit()

        self.assertFalse(result["idempotent"])
        self.assertEqual(result["product_code"], "CO-CD-003")
        self.assertEqual(result["decision_id"], "REC-TEST-0001")
        self.assertEqual(result["next_route"], "/nuevo/CO-CD-003")
        draft = self.self_service.drafts[("USR-A", "CO-CD-003")]
        self.assertEqual(draft["answers"], {})
        self.assertEqual(draft["result"]["decision_id"], "REC-TEST-0001")
        serialized = str(draft)
        self.assertNotIn("producto defectuoso", serialized.lower())
        self.assertNotIn("GARANTIA", serialized)
        self.assertNotIn("private-fingerprint", serialized)
        self.assertNotIn("fact_sensitive_demo", serialized)

        row = self.con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=?", (created["id"],)
        ).fetchone()
        self.assertEqual(row["status"], "Transferido")
        self.assertEqual(row["stage"], "TRANSFERRED_TO_ACCOUNT")
        self.assertEqual(row["transferred_user_id"], "USR-A")
        self.assertTrue(row["transferred_at"])
        payload = self.store._decrypt(row)
        self.assertEqual(payload["m35_0"]["handoff_id"], result["handoff_id"])
        self.assertEqual(payload["facts"][0]["value"], "GARANTIA")

    def test_same_user_reclaim_is_idempotent_without_second_draft(self):
        created = self._recommended_intake()
        first = self.store.claim(self.con, created["recovery_code"], "USR-A")
        self.con.commit()
        second = self.store.claim(self.con, created["recovery_code"], "USR-A")
        self.assertEqual(first["handoff_id"], second["handoff_id"])
        self.assertEqual(first["draft_id"], second["draft_id"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(self.self_service.counter, 1)

    def test_other_account_cannot_steal_transferred_intake(self):
        created = self._recommended_intake()
        self.store.claim(self.con, created["recovery_code"], "USR-A")
        self.con.commit()
        with self.assertRaises(HandoffConflictError):
            self.store.claim(self.con, created["recovery_code"], "USR-B")

    def test_non_client_or_inactive_account_cannot_claim(self):
        created = self._recommended_intake()
        with self.assertRaises(PermissionError):
            self.store.claim(self.con, created["recovery_code"], "USR-S")
        with self.assertRaises(PermissionError):
            self.store.claim(self.con, created["recovery_code"], "USR-OFF")
        row = self.con.execute(
            "SELECT status,transferred_user_id FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()
        self.assertEqual(row["status"], "Activo")
        self.assertIsNone(row["transferred_user_id"])

    def test_existing_product_draft_blocks_before_transfer_to_avoid_data_loss(self):
        created = self._recommended_intake()
        self.self_service.drafts[("USR-A", "CO-CD-003")] = {
            "id": "DRF-EXISTING",
            "answers": {"existing": "matter"},
        }
        with self.assertRaises(HandoffConflictError):
            self.store.claim(self.con, created["recovery_code"], "USR-A")
        row = self.con.execute(
            "SELECT status,transferred_user_id FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()
        self.assertEqual(row["status"], "Activo")
        self.assertIsNone(row["transferred_user_id"])
        self.assertEqual(self.self_service.drafts[("USR-A", "CO-CD-003")]["answers"]["existing"], "matter")

    def test_without_current_recommendation_claim_fails_closed(self):
        created = self.store.create(
            self.con,
            "Tengo una situación jurídica pero todavía no he completado el diagnóstico.",
        )
        with self.assertRaises(HandoffStateError):
            self.store.claim(self.con, created["recovery_code"], "USR-A")
        row = self.con.execute(
            "SELECT status FROM intelligent_intake_sessions WHERE id=?", (created["id"],)
        ).fetchone()
        self.assertEqual(row["status"], "Activo")


if __name__ == "__main__":
    unittest.main()
