from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from legalai_platform.review_reconciliation_m36_2 import FULFILLMENT_REVIEW_STATE, ReviewLifecycleReconciler
from test_m36_2_review_reconciliation import (
    ADMIN,
    CASE_ID,
    DESKS,
    QA,
    SPECIALIST,
    FakeJourney,
    FakeOperations,
    FakeWorkspace,
)


class M362ObservationHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m362-observed.db"
        self.workspace = FakeWorkspace()
        self.operations = FakeOperations()
        self.journey = FakeJourney()
        con = self.db()
        con.executescript(
            """
            CREATE TABLE audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
            );
            CREATE TABLE m36_fulfillment_intake(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL,state TEXT NOT NULL,product_code TEXT,
              desk_case_ids_json TEXT NOT NULL
            );
            CREATE TABLE m36_professional_assignment(
              id TEXT PRIMARY KEY,fulfillment_intake_id TEXT NOT NULL,case_id TEXT NOT NULL,
              specialist_id TEXT NOT NULL,qa_id TEXT NOT NULL,state TEXT NOT NULL,
              completed_desk_ids_json TEXT NOT NULL,notified_desk_ids_json TEXT NOT NULL
            );
            CREATE TABLE m24_case_journey(
              case_id TEXT PRIMARY KEY,current_state TEXT NOT NULL,
              legal_approver_id TEXT,qa_approver_id TEXT,updated_at TEXT
            );
            CREATE TABLE m24_case_transition(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL,from_state TEXT,to_state TEXT NOT NULL,
              actor_id TEXT NOT NULL,actor_role TEXT NOT NULL,actor_name TEXT NOT NULL,
              reason TEXT NOT NULL,evidence_json TEXT NOT NULL,created_at TEXT NOT NULL
            );
            """
        )
        con.execute(
            "INSERT INTO m36_fulfillment_intake(id,case_id,state,product_code,desk_case_ids_json) VALUES(?,?,?,?,?)",
            ("FUL-1", CASE_ID, FULFILLMENT_REVIEW_STATE, "CO-CD-003", json.dumps(DESKS)),
        )
        con.execute(
            """INSERT INTO m36_professional_assignment(
                 id,fulfillment_intake_id,case_id,specialist_id,qa_id,state,
                 completed_desk_ids_json,notified_desk_ids_json
               ) VALUES(?,?,?,?,?,'COMPLETE',?,?)""",
            ("ASN-1", "FUL-1", CASE_ID, SPECIALIST, QA, json.dumps(DESKS), json.dumps(DESKS)),
        )
        con.execute(
            "INSERT INTO m24_case_journey(case_id,current_state,updated_at) VALUES(?,?,?)",
            (CASE_ID, "EN_REVISION_JURIDICA", "2026-08-23T00:00:00-05:00"),
        )
        con.commit(); con.close()
        self.center = ReviewLifecycleReconciler(
            self.workspace,
            self.operations,
            self.journey,
            db_factory=self.db,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def test_changed_revision_that_remains_observed_is_not_a_correction(self):
        self.workspace.set_desk(DESKS[0], status="changes_required", open_findings=1)
        first = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(first["m24_current_state"], "OBSERVADO")

        self.workspace.set_desk(
            DESKS[0],
            status="changes_required",
            revision_number=2,
            open_findings=1,
        )
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["m24_current_state"], "OBSERVADO")
        self.assertEqual(assessment["aggregate_review_state"], "OBSERVED")
        self.assertEqual(assessment["proposed_path"], [])
        self.assertIn("OBSERVATION_STILL_ACTIVE", assessment["blockers"])

        retry = self.center.reconcile(ADMIN, CASE_ID)
        self.assertTrue(retry["idempotent"])
        self.assertEqual(retry["m24_current_state"], "OBSERVADO")
        self.assertEqual(retry["applied_transitions"], [])


if __name__ == "__main__":
    unittest.main()
