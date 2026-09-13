from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.m37_0_journey_guard import install_m37_0_followup_guard
from legalai_platform.post_delivery_followup_m37_0 import (
    PostDeliveryFollowUpCenter,
    PostDeliveryFollowUpError,
    START_CONFIRMATION,
)
from legalai_platform.timing_reminders_m37_2 import TimingReminderCenter, TimingReminderError


CASE_ID = "CASE-TIMING-1"
PRODUCT = "CO-CD-003"
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
OTHER = {"id": "USR-OTHER", "role": "client", "name": "Otro"}
SPECIALIST = {"id": "USR-LEGAL", "role": "specialist", "name": "Especialista"}
ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Administración"}
BOGOTA = ZoneInfo("America/Bogota")
FIXED_NOW = datetime(2026, 8, 24, 15, 0, 0, tzinfo=BOGOTA)


class FakeEvidenceCenter:
    def __init__(self):
        self.items = {}
        self.tampered = set()

    @staticmethod
    def ensure_schema(con):
        con.execute(
            """CREATE TABLE IF NOT EXISTS m37_evidence_item(
               id TEXT PRIMARY KEY,case_id TEXT NOT NULL,follow_up_id TEXT NOT NULL
            )"""
        )

    def add(self, evidence_id, case_id, follow_up_id):
        self.items[evidence_id] = {
            "id": evidence_id,
            "case_id": case_id,
            "follow_up_id": follow_up_id,
        }

    def _item(self, con, case_id, evidence_id):
        row = self.items.get(evidence_id)
        if not row or row["case_id"] != case_id:
            from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeError
            raise EvidenceIntakeError("EVIDENCE_NOT_AVAILABLE", "El soporte no está disponible.", 404)
        return dict(row)

    def _verify_content(self, con, row):
        if row["id"] in self.tampered:
            from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeError
            raise EvidenceIntakeError("EVIDENCE_OBJECT_TAMPERED", "El soporte fue alterado.", 422)
        return b"synthetic-evidence"


class M372TimingReminderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m372.db"
        self.journey = M24CaseJourneyCenter(core.ROOT)
        install_m37_0_followup_guard(self.journey)
        con = self.db()
        con.executescript(
            """
            CREATE TABLE cases(
              id TEXT PRIMARY KEY,product_code TEXT NOT NULL,owner_id TEXT,
              specialist_id TEXT,status TEXT,result TEXT NOT NULL DEFAULT '{}',risk TEXT,updated_at TEXT
            );
            CREATE TABLE documents(id TEXT PRIMARY KEY,case_id TEXT NOT NULL);
            CREATE TABLE audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,entity_type TEXT,entity_id TEXT,
              action TEXT,detail TEXT,created_at TEXT NOT NULL
            );
            CREATE TABLE m36_controlled_delivery(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL UNIQUE,owner_id TEXT NOT NULL,
              product_code TEXT NOT NULL,state TEXT NOT NULL,delivered_at TEXT
            );
            """
        )
        con.execute(
            "INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)",
            (CASE_ID, PRODUCT, CLIENT["id"], SPECIALIST["id"], "Activo", "{}", "green", "2026-08-24T10:00:00+00:00"),
        )
        con.execute("INSERT INTO documents VALUES(?,?)", ("DOC-1", CASE_ID))
        con.execute(
            "INSERT INTO m36_controlled_delivery VALUES(?,?,?,?,?,?)",
            ("DLV-1", CASE_ID, CLIENT["id"], PRODUCT, "DELIVERED_IN_APP", "2026-08-24T10:05:00+00:00"),
        )
        self.journey.ensure_schema(con)
        con.execute(
            """INSERT INTO m24_case_journey
               (case_id,product_code,current_state,legal_approver_id,qa_approver_id,delivery_actor_id,
                diagnosis_json,route_json,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (CASE_ID, PRODUCT, "ENTREGADO", SPECIALIST["id"], ADMIN["id"], ADMIN["id"], "{}", "{}",
             "2026-08-24T09:00:00+00:00", "2026-08-24T10:05:00+00:00"),
        )
        con.execute(
            """INSERT INTO m24_case_transition
               (id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            ("TR-DELIVERY", CASE_ID, "APROBADO_QA", "ENTREGADO", ADMIN["id"], "admin", "Administración",
             "Entrega sintética previa a M37.2.", "{}", "2026-08-24T10:05:00+00:00"),
        )
        self.journey._create_default_followups(con, CASE_ID, PRODUCT, ADMIN["id"])
        con.commit(); con.close()
        self.followup = PostDeliveryFollowUpCenter(self.journey, db_factory=self.db)
        started = self.followup.start(CLIENT, CASE_ID, START_CONFIRMATION)
        self.task_id = started["tasks"][0]["follow_up_id"]
        self.second_task_id = started["tasks"][1]["follow_up_id"]
        con = self.db()
        con.execute("UPDATE m24_case_follow_up SET due_at=? WHERE id=?", ("2026-08-29T15:00:00+00:00", self.task_id))
        con.commit(); con.close()
        self.evidence = FakeEvidenceCenter()
        self.center = TimingReminderCenter(
            self.followup,
            self.evidence,
            db_factory=self.db,
            now_provider=lambda: FIXED_NOW,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def task_status(self):
        con = self.db()
        try:
            return con.execute("SELECT status FROM m24_case_follow_up WHERE id=?", (self.task_id,)).fetchone()[0]
        finally:
            con.close()

    def rows(self, table):
        con = self.db()
        try:
            return [dict(row) for row in con.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()]
        finally:
            con.close()

    def event_payloads(self):
        con = self.db()
        try:
            return [
                {"type": row["event_type"], "payload": json.loads(row["payload_json"])}
                for row in con.execute("SELECT event_type,payload_json FROM m37_followup_event WHERE case_id=? ORDER BY sequence", (CASE_ID,)).fetchall()
            ]
        finally:
            con.close()

    def record_date(self, actor=CLIENT, **kwargs):
        return self.center.record_date(
            actor,
            CASE_ID,
            kwargs.pop("follow_up_id", self.task_id),
            kwargs.pop("event_type", "ACTION_PERFORMED"),
            kwargs.pop("date_value", "2026-08-20"),
            **kwargs,
        )

    def test_contract_preserves_operational_not_legal_boundary(self):
        validation = self.center.validate_contract()
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["timezone"], "America/Bogota")
        governance = self.center.contract["governance"]
        self.assertTrue(governance["m24_due_at_is_operational_checkpoint_only"])
        for key in (
            "date_record_is_legal_deadline",
            "date_record_legal_deadline_verified",
            "evidence_reference_verifies_date",
            "professional_record_verifies_legal_deadline",
            "business_calendar_calculation",
            "statutory_deadline_calculation",
            "automatic_close",
            "automatic_escalation",
        ):
            self.assertFalse(governance[key])

    def test_existing_m24_due_at_is_exposed_only_as_operational_checkpoint(self):
        detail = self.center.detail(CLIENT, CASE_ID)
        checkpoint = next(item for item in detail["operational_checkpoints"] if item["follow_up_id"] == self.task_id)
        self.assertEqual(checkpoint["kind"], "OPERATIONAL_CHECKPOINT")
        self.assertEqual(checkpoint["source"], "M24_EXISTING_DUE_AT")
        self.assertFalse(checkpoint["is_legal_deadline"])
        self.assertFalse(checkpoint["legal_deadline_verified"])
        self.assertFalse(detail["governance"]["business_calendar_calculation"])
        self.assertFalse(detail["governance"]["statutory_deadline_calculation"])

    def test_client_date_is_user_asserted_and_never_legal_deadline(self):
        before = self.task_status()
        result = self.record_date()
        self.assertEqual(result["provenance"], "USER_ASSERTED")
        self.assertEqual(result["timing"]["kind"], "RECORDED_EVENT_DATE")
        self.assertFalse(result["timing"]["is_legal_deadline"])
        self.assertFalse(result["timing"]["legal_deadline_verified"])
        self.assertFalse(result["timing"]["evidence_reference_verifies_date"])
        self.assertEqual(self.task_status(), before)
        event = self.event_payloads()[-1]
        self.assertEqual(event["type"], "DATE_RECORDED")
        self.assertNotIn("date_value", event["payload"])
        self.assertNotIn("date", event["payload"])
        self.assertFalse(event["payload"]["legal_deadline_verified"])

    def test_professional_record_is_not_legal_deadline_verification(self):
        result = self.record_date(actor=SPECIALIST, event_type="AUTHORITY_RECEIPT_REPORTED")
        self.assertEqual(result["provenance"], "PROFESSIONAL_RECORDED")
        self.assertFalse(result["timing"]["is_legal_deadline"])
        self.assertFalse(result["timing"]["legal_deadline_verified"])

    def test_evidence_link_is_same_task_and_does_not_verify_date(self):
        self.evidence.add("EVD-1", CASE_ID, self.task_id)
        result = self.record_date(event_type="AUTHORITY_RECEIPT_REPORTED", evidence_id="EVD-1")
        self.assertTrue(result["evidence_referenced"])
        self.assertFalse(result["timing"]["evidence_reference_verifies_date"])
        self.evidence.add("EVD-OTHER", CASE_ID, self.second_task_id)
        with self.assertRaises(TimingReminderError) as caught:
            self.record_date(evidence_id="EVD-OTHER")
        self.assertEqual(caught.exception.code, "TIMING_EVIDENCE_TASK_MISMATCH")

    def test_tampered_evidence_blocks_linked_date_record(self):
        self.evidence.add("EVD-BAD", CASE_ID, self.task_id)
        self.evidence.tampered.add("EVD-BAD")
        from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeError
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.record_date(evidence_id="EVD-BAD")
        self.assertEqual(caught.exception.code, "EVIDENCE_OBJECT_TAMPERED")
        self.assertEqual(self.rows("m37_timing_date_record"), [])

    def test_date_correction_is_append_only_and_cannot_fork(self):
        original = self.record_date(date_value="2026-08-20")
        corrected = self.record_date(
            date_value="2026-08-21",
            supersedes_date_record_id=original["date_record_id"],
        )
        self.assertEqual(corrected["supersedes_date_record_id"], original["date_record_id"])
        self.assertEqual(len(self.rows("m37_timing_date_record")), 2)
        detail = self.center.detail(CLIENT, CASE_ID)
        old = next(item for item in detail["date_records"] if item["date_record_id"] == original["date_record_id"])
        new = next(item for item in detail["date_records"] if item["date_record_id"] == corrected["date_record_id"])
        self.assertTrue(old["superseded"])
        self.assertFalse(new["superseded"])
        with self.assertRaises(TimingReminderError) as caught:
            self.record_date(date_value="2026-08-22", supersedes_date_record_id=original["date_record_id"])
        self.assertEqual(caught.exception.code, "TIMING_DATE_ALREADY_SUPERSEDED")

    def test_exact_date_retry_is_idempotent(self):
        first = self.record_date()
        second = self.record_date()
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["date_record_id"], first["date_record_id"])
        self.assertEqual(len(self.rows("m37_timing_date_record")), 1)

    def test_date_range_is_bounded_without_statutory_computation(self):
        for value in ("1899-12-31", "2027-08-26", "20/08/2026"):
            with self.subTest(value=value):
                with self.assertRaises(TimingReminderError):
                    self.record_date(date_value=value)

    def test_date_hash_tampering_blocks_read_and_new_writes(self):
        item = self.record_date()
        con = self.db()
        con.execute("UPDATE m37_timing_date_record SET date_value='2026-08-22' WHERE id=?", (item["date_record_id"],))
        con.commit(); con.close()
        with self.assertRaises(TimingReminderError) as caught:
            self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(caught.exception.code, "TIMING_DATE_RECORD_TAMPERED")
        with self.assertRaises(TimingReminderError):
            self.record_date(date_value="2026-08-23")

    def test_reminder_is_operational_and_does_not_change_task(self):
        before = self.task_status()
        result = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25")
        self.assertEqual(result["status"], "SCHEDULED")
        self.assertFalse(result["timing"]["is_legal_deadline"])
        self.assertFalse(result["timing"]["legal_deadline_verified"])
        self.assertFalse(result["governance"]["acknowledgement_completes_task"])
        self.assertFalse(result["governance"]["due_completes_task"])
        self.assertFalse(result["governance"]["automatic_external_notification"])
        self.assertEqual(self.task_status(), before)

    def test_due_is_derived_in_read_model_without_persisted_due_event(self):
        result = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-24")
        self.assertEqual(result["status"], "DUE")
        before_events = len(self.rows("m37_timing_reminder_event"))
        detail = self.center.detail(CLIENT, CASE_ID)
        reminder = next(item for item in detail["reminders"] if item["reminder_id"] == result["reminder_id"])
        self.assertEqual(reminder["status"], "DUE")
        self.assertEqual(len(self.rows("m37_timing_reminder_event")), before_events)
        self.assertEqual(self.task_status(), "pending")

    def test_acknowledgement_is_append_only_idempotent_and_never_completes_task(self):
        reminder = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25")
        first = self.center.record_reminder_action(CLIENT, CASE_ID, reminder["reminder_id"], "ACKNOWLEDGED")
        second = self.center.record_reminder_action(CLIENT, CASE_ID, reminder["reminder_id"], "ACKNOWLEDGED")
        self.assertEqual(first["status"], "ACKNOWLEDGED")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        events = self.rows("m37_timing_reminder_event")
        self.assertEqual([row["action"] for row in events], ["SCHEDULED", "ACKNOWLEDGED"])
        self.assertEqual(self.task_status(), "pending")

    def test_cancelled_reminder_rejects_opposite_terminal_action(self):
        reminder = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25")
        cancelled = self.center.record_reminder_action(SPECIALIST, CASE_ID, reminder["reminder_id"], "CANCELLED")
        self.assertEqual(cancelled["status"], "CANCELLED")
        with self.assertRaises(TimingReminderError) as caught:
            self.center.record_reminder_action(CLIENT, CASE_ID, reminder["reminder_id"], "ACKNOWLEDGED")
        self.assertEqual(caught.exception.code, "TIMING_REMINDER_TERMINAL")

    def test_reminder_can_reference_only_current_date_same_task(self):
        date_record = self.record_date()
        reminder = self.center.schedule_reminder(
            CLIENT, CASE_ID, self.task_id, "2026-08-25", source_date_record_id=date_record["date_record_id"]
        )
        self.assertEqual(reminder["source_date_record_id"], date_record["date_record_id"])
        corrected = self.record_date(date_value="2026-08-21", supersedes_date_record_id=date_record["date_record_id"])
        detail = self.center.detail(CLIENT, CASE_ID)
        existing = next(item for item in detail["reminders"] if item["reminder_id"] == reminder["reminder_id"])
        self.assertTrue(existing["source_date_superseded"])
        with self.assertRaises(TimingReminderError) as caught:
            self.center.schedule_reminder(
                CLIENT, CASE_ID, self.task_id, "2026-08-26", source_date_record_id=date_record["date_record_id"]
            )
        self.assertEqual(caught.exception.code, "TIMING_SOURCE_DATE_SUPERSEDED")
        self.assertFalse(corrected["superseded"])

    def test_reminder_hash_and_event_hash_tampering_fail_closed(self):
        reminder = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25")
        con = self.db()
        con.execute("UPDATE m37_timing_reminder SET scheduled_for='2026-08-26' WHERE id=?", (reminder["reminder_id"],))
        con.commit(); con.close()
        with self.assertRaises(TimingReminderError) as caught:
            self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(caught.exception.code, "TIMING_REMINDER_TAMPERED")

    def test_cross_tenant_is_hidden_by_parent_followup_boundary(self):
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.detail(OTHER, CASE_ID)
        self.assertEqual(caught.exception.code, "FOLLOWUP_NOT_AVAILABLE")
        self.assertEqual(caught.exception.status, 404)

    def test_closed_case_is_readable_but_new_timing_writes_are_blocked(self):
        self.record_date()
        con = self.db()
        con.execute("UPDATE m24_case_journey SET current_state='CERRADO' WHERE case_id=?", (CASE_ID,))
        con.commit(); con.close()
        detail = self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(detail["metrics"]["date_records"], 1)
        with self.assertRaises(TimingReminderError) as caught:
            self.record_date(date_value="2026-08-21")
        self.assertEqual(caught.exception.code, "TIMING_FOLLOWUP_READ_ONLY")

    def test_m37_chain_remains_valid_and_contains_no_date_value(self):
        date_record = self.record_date()
        reminder = self.center.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25", source_date_record_id=date_record["date_record_id"])
        self.center.record_reminder_action(CLIENT, CASE_ID, reminder["reminder_id"], "ACKNOWLEDGED")
        con = self.db()
        try:
            integrity = self.followup.verify_chain(con, CASE_ID)
        finally:
            con.close()
        self.assertTrue(integrity["valid"])
        payloads = self.event_payloads()
        raw = json.dumps(payloads, ensure_ascii=False)
        self.assertNotIn("2026-08-20", raw)
        self.assertNotIn("2026-08-25", raw)
        self.assertIn("DATE_RECORDED", raw)
        self.assertIn("REMINDER_SCHEDULED", raw)
        self.assertIn("REMINDER_ACKNOWLEDGED", raw)


if __name__ == "__main__":
    unittest.main()
