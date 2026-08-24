from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.professional_assignment_m36_1 import (
    ProfessionalAssignmentCenter,
    ProfessionalAssignmentError,
)


ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Ana Admin"}
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}


class FakeFulfillment:
    def __init__(self):
        self.journey_state = "EN_REVISION_JURIDICA"
        self.desks = ["DSK-DOC-1", "DSK-DOC-2"]

    def detail(self, actor, case_id):
        return {
            "fulfillment_intake_id": "FUL-1",
            "case_id": case_id,
            "product_code": "CO-CD-003",
            "journey_state": self.journey_state,
            "desk_case_ids": list(self.desks),
            "document_count": len(self.desks),
        }


class FakeWorkspace:
    def detail(self, actor, desk_id):
        return {
            "source_case_id": "CASE-1",
            "audit": {"valid": True},
            "workflow_status": "legal_pending",
        }


class FakeOperations:
    def __init__(self):
        self.workspace = FakeWorkspace()
        self.assignments = {
            "DSK-DOC-1": {"specialist": None, "qa": None},
            "DSK-DOC-2": {"specialist": None, "qa": None},
        }
        self.update_calls: list[str] = []
        self.fail_once_on: str | None = None
        self.failed = False

    def professionals(self, actor):
        if actor.get("role") != "admin":
            raise PermissionDenied("admin only")
        return {
            "specialists": [
                {"id": "USR-LEGAL", "name": "Laura Legal", "role": "specialist", "specialty": "Consumo"},
                {"id": "USR-LEGAL-2", "name": "Luis Legal", "role": "specialist", "specialty": "Contratos"},
            ],
            "qa": [
                {"id": "USR-QA", "name": "Quinn QA", "role": "qa", "specialty": "QA"},
                {"id": "USR-ADMIN", "name": "Ana Admin", "role": "admin", "specialty": "Gobernanza"},
            ],
        }

    def verify_chain(self, desk_id):
        return {"valid": True, "events": 1, "last_hash": "a" * 64}

    def state(self, actor, desk_id):
        value = self.assignments[desk_id]
        return {
            "operations": {
                "assigned_specialist": {"id": value["specialist"]} if value["specialist"] else None,
                "assigned_qa": {"id": value["qa"]} if value["qa"] else None,
            }
        }

    def update_assignment(self, actor, desk_id, specialist_id, qa_id):
        self.update_calls.append(desk_id)
        if self.fail_once_on == desk_id and not self.failed:
            self.failed = True
            raise RuntimeError("synthetic assignment failure")
        self.assignments[desk_id] = {"specialist": specialist_id, "qa": qa_id}
        return self.state(actor, desk_id)


class FakeNotifications:
    def __init__(self):
        self.calls: list[str] = []
        self.fail_once_on: str | None = None
        self.failed = False

    def evaluate(self, actor, desk_id):
        self.calls.append(desk_id)
        if self.fail_once_on == desk_id and not self.failed:
            self.failed = True
            raise RuntimeError("synthetic notification failure")
        return {"created": [f"NTF-{desk_id}"]}


class M361ProfessionalAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m361.db"
        con = self.db()
        con.execute(
            """CREATE TABLE audit_log(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
               )"""
        )
        con.commit(); con.close()
        self.fulfillment = FakeFulfillment()
        self.operations = FakeOperations()
        self.notifications = FakeNotifications()
        self.center = ProfessionalAssignmentCenter(
            self.fulfillment,
            self.operations,
            self.notifications,
            db_factory=self.db,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def ledger(self):
        con = self.db()
        try:
            self.center.ensure_schema(con)
            row = con.execute("SELECT * FROM m36_professional_assignment WHERE case_id='CASE-1'").fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def audit_count(self):
        con = self.db()
        try:
            return con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        finally:
            con.close()

    def assign(self, specialist="USR-LEGAL", qa="USR-QA"):
        return self.center.assign(ADMIN, "CASE-1", specialist, qa)

    def test_success_assigns_every_desk_evaluates_handoff_and_preserves_governance(self):
        result = self.assign()
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(result["assigned_desks"], 2)
        self.assertEqual(result["notification_evaluations"], 2)
        self.assertTrue(result["all_desks_assigned"])
        self.assertTrue(result["handoff_evaluated"])
        self.assertEqual(self.operations.update_calls, ["DSK-DOC-1", "DSK-DOC-2"])
        self.assertEqual(self.notifications.calls, ["DSK-DOC-1", "DSK-DOC-2"])
        self.assertFalse(result["governance"]["automatic_matching"])
        self.assertFalse(result["governance"]["automatic_legal_approval"])
        self.assertFalse(result["governance"]["automatic_qa_approval"])
        self.assertFalse(result["governance"]["automatic_release"])
        self.assertTrue(result["governance"]["dual_approval_preserved"])

    def test_non_admin_cannot_assign_or_read_directory(self):
        with self.assertRaises(PermissionDenied):
            self.center.professionals(CLIENT)
        with self.assertRaises(PermissionDenied):
            self.center.assign(CLIENT, "CASE-1", "USR-LEGAL", "USR-QA")

    def test_separation_of_duties_is_fail_closed(self):
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.center.assign(ADMIN, "CASE-1", "USR-ADMIN", "USR-ADMIN")
        self.assertEqual(caught.exception.code, "SEPARATION_OF_DUTIES_REQUIRED")
        self.assertIsNone(self.ledger())

    def test_unknown_or_wrong_role_professionals_are_rejected(self):
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.center.assign(ADMIN, "CASE-1", "USR-NOT-THERE", "USR-QA")
        self.assertEqual(caught.exception.code, "SPECIALIST_NOT_AVAILABLE")
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.center.assign(ADMIN, "CASE-1", "USR-LEGAL", "USR-NOT-THERE")
        self.assertEqual(caught.exception.code, "QA_NOT_AVAILABLE")

    def test_unassignable_journey_blocks_before_ledger(self):
        self.fulfillment.journey_state = "GENERADO"
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.assign()
        self.assertEqual(caught.exception.code, "JOURNEY_NOT_ASSIGNABLE")
        self.assertIsNone(self.ledger())

    def test_existing_different_assignment_blocks_without_overwrite(self):
        self.operations.assignments["DSK-DOC-1"] = {"specialist": "USR-LEGAL-2", "qa": "USR-QA"}
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.assign()
        self.assertEqual(caught.exception.code, "EXISTING_ASSIGNMENT_CONFLICT")
        self.assertEqual(self.operations.assignments["DSK-DOC-1"]["specialist"], "USR-LEGAL-2")
        self.assertIsNone(self.ledger())

    def test_partial_assignment_failure_is_checkpointed_and_retry_resumes(self):
        self.operations.fail_once_on = "DSK-DOC-2"
        with self.assertRaises(RuntimeError):
            self.assign()
        row = self.ledger()
        self.assertEqual(row["state"], "PARTIAL")
        self.assertIn("DSK-DOC-1", row["completed_desk_ids_json"])
        self.assertEqual(self.operations.update_calls, ["DSK-DOC-1", "DSK-DOC-2"])

        result = self.assign()
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(self.operations.update_calls, ["DSK-DOC-1", "DSK-DOC-2", "DSK-DOC-2"])
        self.assertEqual(self.notifications.calls, ["DSK-DOC-1", "DSK-DOC-2"])

    def test_notification_failure_keeps_assignment_complete_but_handoff_recoverable(self):
        self.notifications.fail_once_on = "DSK-DOC-2"
        with self.assertRaises(RuntimeError):
            self.assign()
        row = self.ledger()
        self.assertEqual(row["state"], "ASSIGNED")
        self.assertIn("DSK-DOC-1", row["notified_desk_ids_json"])
        self.assertEqual(self.operations.update_calls, ["DSK-DOC-1", "DSK-DOC-2"])

        result = self.assign()
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(self.operations.update_calls, ["DSK-DOC-1", "DSK-DOC-2"])
        self.assertEqual(self.notifications.calls, ["DSK-DOC-1", "DSK-DOC-2", "DSK-DOC-2"])

    def test_complete_retry_is_strictly_read_only(self):
        first = self.assign()
        row_before = self.ledger()
        audit_before = self.audit_count()
        ops_before = list(self.operations.update_calls)
        notifications_before = list(self.notifications.calls)

        second = self.assign()
        row_after = self.ledger()
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["assignment_id"], first["assignment_id"])
        self.assertEqual(row_after, row_before)
        self.assertEqual(self.audit_count(), audit_before)
        self.assertEqual(self.operations.update_calls, ops_before)
        self.assertEqual(self.notifications.calls, notifications_before)

    def test_second_professional_pair_is_not_silent_reassignment(self):
        self.assign()
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.center.assign(ADMIN, "CASE-1", "USR-LEGAL-2", "USR-QA")
        self.assertIn(caught.exception.code, {"EXISTING_ASSIGNMENT_CONFLICT", "ASSIGNMENT_REQUEST_CONFLICT"})
        self.assertEqual(self.operations.assignments["DSK-DOC-1"]["specialist"], "USR-LEGAL")

    def test_complete_ledger_with_missing_checkpoint_is_rejected(self):
        self.assign()
        con = self.db()
        con.execute("UPDATE m36_professional_assignment SET notified_desk_ids_json='[\"DSK-DOC-1\"]' WHERE case_id='CASE-1'")
        con.commit(); con.close()
        with self.assertRaises(ProfessionalAssignmentError) as caught:
            self.assign()
        self.assertEqual(caught.exception.code, "ASSIGNMENT_LEDGER_INVALID")

    def test_queue_reports_complete_and_partial_without_claiming_review(self):
        self.assign()
        queue = self.center.queue(ADMIN)
        self.assertEqual(queue["metrics"]["complete"], 1)
        self.assertEqual(queue["metrics"]["partial"], 0)
        self.assertIn("No constituye revisión", queue["notice"])


if __name__ == "__main__":
    unittest.main()
