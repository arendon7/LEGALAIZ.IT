from __future__ import annotations

import sqlite3
import unittest

from legalai_platform.m36_3_journey_guard import install_m36_3_delivery_guard


CASE_ID = "CASE-GUARD-1"


class DummyJourney:
    def __init__(self):
        self.calls = []

    def transition(self, con, case_id, target, reason, evidence, confirmation, actor):
        self.calls.append((case_id, target, evidence, actor.get("id")))
        return {"case_id": case_id, "current_state": target}


class M363JourneyGuardTests(unittest.TestCase):
    def db(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        return con

    @staticmethod
    def evidence(**overrides):
        payload = {
            "source": "m36_3_controlled_delivery",
            "delivery_id": "DLV-1",
            "package_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
            "release_snapshot_sha256": "c" * 64,
            "release_count": 2,
            "channel": "IN_APP",
            "download_confirmed": False,
            "external_notification_sent": False,
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def create_m36_tables(con, *, prepared=True):
        con.executescript(
            """
            CREATE TABLE m36_fulfillment_intake(id TEXT PRIMARY KEY,case_id TEXT NOT NULL);
            CREATE TABLE m36_controlled_delivery(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL,state TEXT NOT NULL,
              package_sha256 TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,
              release_snapshot_sha256 TEXT NOT NULL,release_count INTEGER NOT NULL
            );
            """
        )
        con.execute("INSERT INTO m36_fulfillment_intake VALUES('FUL-1',?)", (CASE_ID,))
        if prepared:
            con.execute(
                "INSERT INTO m36_controlled_delivery VALUES(?,?,?,?,?,?,?)",
                ("DLV-1", CASE_ID, "PREPARED", "a" * 64, "b" * 64, "c" * 64, 2),
            )
        con.commit()

    def test_historical_case_without_m36_tables_keeps_legacy_transition(self):
        con = self.db()
        journey = install_m36_3_delivery_guard(DummyJourney())
        result = journey.transition(con, "LEGACY-1", "ENTREGADO", "razón", {}, "confirm", {"id": "A"})
        self.assertEqual(result["current_state"], "ENTREGADO")
        self.assertEqual(len(journey.calls), 1)

    def test_m36_case_without_prepared_delivery_is_blocked(self):
        con = self.db()
        self.create_m36_tables(con, prepared=False)
        journey = install_m36_3_delivery_guard(DummyJourney())
        with self.assertRaisesRegex(ValueError, "PREPARED"):
            journey.transition(con, CASE_ID, "ENTREGADO", "razón", self.evidence(), "confirm", {"id": "A"})
        self.assertEqual(journey.calls, [])

    def test_exact_prepared_evidence_allows_internal_transition(self):
        con = self.db()
        self.create_m36_tables(con)
        journey = install_m36_3_delivery_guard(DummyJourney())
        result = journey.transition(con, CASE_ID, "ENTREGADO", "razón", self.evidence(), "confirm", {"id": "A"})
        self.assertEqual(result["current_state"], "ENTREGADO")
        self.assertEqual(len(journey.calls), 1)

    def test_hash_count_channel_or_claim_drift_is_blocked(self):
        for overrides in (
            {"package_sha256": "f" * 64},
            {"manifest_sha256": "f" * 64},
            {"release_snapshot_sha256": "f" * 64},
            {"release_count": 1},
            {"channel": "EMAIL"},
            {"download_confirmed": True},
            {"external_notification_sent": True},
        ):
            with self.subTest(overrides=overrides):
                con = self.db()
                self.create_m36_tables(con)
                journey = install_m36_3_delivery_guard(DummyJourney())
                with self.assertRaisesRegex(ValueError, "evidencia"):
                    journey.transition(con, CASE_ID, "ENTREGADO", "razón", self.evidence(**overrides), "confirm", {"id": "A"})
                self.assertEqual(journey.calls, [])
                con.close()

    def test_installation_is_idempotent(self):
        journey = DummyJourney()
        first = install_m36_3_delivery_guard(journey)
        wrapped = journey.transition
        second = install_m36_3_delivery_guard(journey)
        self.assertIs(first, second)
        self.assertIs(wrapped, journey.transition)


if __name__ == "__main__":
    unittest.main()
