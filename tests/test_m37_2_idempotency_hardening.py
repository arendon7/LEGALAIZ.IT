from __future__ import annotations

import unittest

from legalai_platform.timing_reminders_m37_2_hardening import HardenedTimingReminderCenter
from tests.test_m37_2_timing_reminders import (
    CASE_ID,
    CLIENT,
    FIXED_NOW,
    M372TimingReminderTests,
)


class M372IdempotencyHardeningTests(unittest.TestCase):
    def setUp(self):
        self.fixture = M372TimingReminderTests(methodName="test_contract_preserves_operational_not_legal_boundary")
        self.fixture.setUp()
        self.center = HardenedTimingReminderCenter(
            self.fixture.followup,
            self.fixture.evidence,
            db_factory=self.fixture.db,
            now_provider=lambda: FIXED_NOW,
        )

    def tearDown(self):
        self.fixture.tearDown()

    def test_exact_date_retry_succeeds_after_task_quota_is_full(self):
        self.center.contract["max_date_records_per_task"] = 1
        first = self.center.record_date(CLIENT, CASE_ID, self.fixture.task_id, "ACTION_PERFORMED", "2026-08-20")
        second = self.center.record_date(CLIENT, CASE_ID, self.fixture.task_id, "ACTION_PERFORMED", "2026-08-20")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["date_record_id"], first["date_record_id"])
        self.assertEqual(len(self.fixture.rows("m37_timing_date_record")), 1)

    def test_exact_correction_retry_survives_parent_already_superseded_by_same_record(self):
        self.center.contract["max_date_records_per_task"] = 2
        original = self.center.record_date(CLIENT, CASE_ID, self.fixture.task_id, "ACTION_PERFORMED", "2026-08-20")
        corrected = self.center.record_date(
            CLIENT,
            CASE_ID,
            self.fixture.task_id,
            "ACTION_PERFORMED",
            "2026-08-21",
            supersedes_date_record_id=original["date_record_id"],
        )
        retry = self.center.record_date(
            CLIENT,
            CASE_ID,
            self.fixture.task_id,
            "ACTION_PERFORMED",
            "2026-08-21",
            supersedes_date_record_id=original["date_record_id"],
        )
        self.assertTrue(retry["idempotent"])
        self.assertEqual(retry["date_record_id"], corrected["date_record_id"])
        self.assertEqual(len(self.fixture.rows("m37_timing_date_record")), 2)

    def test_exact_reminder_retry_succeeds_after_task_quota_is_full(self):
        self.center.contract["max_reminders_per_task"] = 1
        first = self.center.schedule_reminder(CLIENT, CASE_ID, self.fixture.task_id, "2026-08-25")
        second = self.center.schedule_reminder(CLIENT, CASE_ID, self.fixture.task_id, "2026-08-25")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["reminder_id"], first["reminder_id"])
        self.assertEqual(len(self.fixture.rows("m37_timing_reminder")), 1)


if __name__ == "__main__":
    unittest.main()
