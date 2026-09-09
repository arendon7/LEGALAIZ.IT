import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from legalai_platform.intelligent_intake_m34_1 import (
    IntelligentIntakeStore,
    MAX_PROBLEM_CHARS,
    MIN_PROBLEM_CHARS,
)


class MemoryCrypto:
    """Small deterministic crypto contract double; proves plaintext is not stored."""

    PREFIX = b"encrypted-test-v1:"

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


class IntelligentIntakeM341Tests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.store = IntelligentIntakeStore(MemoryCrypto(), retention_hours=72)
        self.store.create_schema(self.con)

    def tearDown(self):
        self.con.close()

    def test_create_keeps_problem_out_of_plaintext_database_columns(self):
        problem = "Trabajé durante cinco años y necesito entender qué puedo reclamar ahora."
        created = self.store.create(self.con, problem)
        self.con.commit()
        row = self.con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertNotIn(problem.encode("utf-8"), bytes(row["payload_encrypted"]))
        self.assertNotEqual(row["token_hash"], created["recovery_code"])
        self.assertNotIn(created["recovery_code"], str(tuple(row)))
        self.assertEqual(row["stage"], "PROBLEM_SUBMITTED")

    def test_recovery_code_round_trip_recovers_exact_user_statement(self):
        problem = "Compré un producto hace una semana y el proveedor no responde por la garantía."
        created = self.store.create(self.con, problem)
        self.con.commit()
        recovered = self.store.recover(self.con, created["recovery_code"])
        self.assertEqual(recovered["problem_statement"], problem)
        self.assertEqual(recovered["facts"], [])
        self.assertEqual(recovered["ai_processing_status"], "NOT_STARTED")

    def test_recovery_accepts_code_without_visual_separators(self):
        created = self.store.create(
            self.con,
            "Necesito revisar un cobro y tengo soportes de la obligación y los pagos realizados.",
        )
        compact = created["recovery_code"].replace("-", "").lower()
        recovered = self.store.recover(self.con, compact)
        self.assertEqual(recovered["id"], created["id"])

    def test_invalid_code_does_not_reveal_session_existence(self):
        with self.assertRaisesRegex(ValueError, "formato válido"):
            self.store.recover(self.con, "ABC")
        with self.assertRaisesRegex(ValueError, "no existe, expiró o ya no está activo"):
            self.store.recover(self.con, "AAAAAA-BBBBBB-CCCCCC-DDDDDD")

    def test_expired_session_is_fail_closed(self):
        created = self.store.create(
            self.con,
            "Una entidad de salud no ha respondido mi solicitud y necesito saber cómo continuar.",
        )
        expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0).isoformat()
        self.con.execute(
            "UPDATE intelligent_intake_sessions SET expires_at=? WHERE id=?",
            (expired, created["id"]),
        )
        self.con.commit()
        with self.assertRaisesRegex(ValueError, "no existe, expiró o ya no está activo"):
            self.store.recover(self.con, created["recovery_code"])
        row = self.con.execute(
            "SELECT status FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()
        self.assertEqual(row["status"], "Expirado")

    def test_edit_reencrypts_and_preserves_same_session(self):
        original = "Me terminaron el contrato y todavía no tengo claridad sobre los valores pendientes."
        corrected = "Me terminaron el contrato ayer y todavía no me han pagado los valores pendientes."
        created = self.store.create(self.con, original)
        self.con.commit()
        before = self.con.execute(
            "SELECT payload_encrypted FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()[0]
        updated = self.store.update_problem(self.con, created["recovery_code"], corrected)
        self.con.commit()
        after = self.con.execute(
            "SELECT payload_encrypted FROM intelligent_intake_sessions WHERE id=?",
            (created["id"],),
        ).fetchone()[0]
        self.assertEqual(updated["id"], created["id"])
        self.assertEqual(updated["problem_statement"], corrected)
        self.assertNotEqual(bytes(before), bytes(after))
        self.assertEqual(
            self.store.recover(self.con, created["recovery_code"])["problem_statement"],
            corrected,
        )

    def test_problem_statement_length_is_bounded(self):
        with self.assertRaises(ValueError):
            self.store.create(self.con, "x" * (MIN_PROBLEM_CHARS - 1))
        with self.assertRaises(ValueError):
            self.store.create(self.con, "x" * (MAX_PROBLEM_CHARS + 1))
        created = self.store.create(self.con, "x" * MIN_PROBLEM_CHARS)
        self.assertTrue(created["id"].startswith("INT-"))

    def test_whitespace_is_normalized_before_encryption(self):
        created = self.store.create(
            self.con,
            "  Tengo   una   deuda\ncon soportes y quiero documentar un acuerdo de pago.  ",
        )
        self.assertEqual(
            created["problem_statement"],
            "Tengo una deuda con soportes y quiero documentar un acuerdo de pago.",
        )


if __name__ == "__main__":
    unittest.main()
