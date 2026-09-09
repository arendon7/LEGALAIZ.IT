from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.review_reconciliation_m36_2 import (
    FULFILLMENT_REVIEW_STATE,
    ReviewLifecycleReconciler,
    ReviewReconciliationError,
    SYSTEM_ACTOR_ID,
)


ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Ana Admin"}
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
SPECIALIST = "USR-LEGAL"
QA = "USR-QA"
CASE_ID = "CASE-1"
DESKS = ["DSK-DOC-1", "DSK-DOC-2"]


class FakeWorkspace:
    def __init__(self):
        self.desks = {}
        for index, desk_id in enumerate(DESKS, 1):
            self.set_desk(desk_id, document_id=f"DOC-{index}")

    def set_desk(
        self,
        desk_id,
        *,
        document_id=None,
        status="legal_pending",
        revision_number=1,
        legal=False,
        qa=False,
        legal_actor=SPECIALIST,
        qa_actor=QA,
        release=False,
        open_findings=0,
        audit_valid=True,
    ):
        revision_id = f"REV-{revision_number:04d}"
        digest = (str(revision_number) * 64)[:64]
        approvals = {"legal": None, "qa": None}
        if legal:
            approvals["legal"] = {
                "decision": "approve",
                "revision_id": revision_id,
                "sha256": digest,
                "record_hash": "l" * 64,
                "actor": {"id": legal_actor, "role": "specialist"},
            }
        if qa:
            approvals["qa"] = {
                "decision": "approve",
                "revision_id": revision_id,
                "sha256": digest,
                "record_hash": "q" * 64,
                "actor": {"id": qa_actor, "role": "qa"},
            }
        findings = [
            {"finding_id": f"FND-{i}", "state": "open", "severity": "minor"}
            for i in range(open_findings)
        ]
        release_payload = None
        if release:
            release_payload = {
                "release_id": f"REL-{desk_id}",
                "revision_id": revision_id,
                "sha256": digest,
                "release_record_hash": "r" * 64,
            }
        self.desks[desk_id] = {
            "source_case_id": CASE_ID,
            "audit": {"valid": audit_valid, "last_hash": f"audit-{desk_id}-{revision_number}"},
            "workflow_status": status,
            "case": {
                "case_id": desk_id,
                "document_id": document_id or desk_id.replace("DSK-", ""),
                "current_revision_id": revision_id,
            },
            "revisions": [
                {
                    "revision_id": revision_id,
                    "revision_number": revision_number,
                    "sha256": digest,
                    "approvals": approvals,
                    "findings": findings,
                }
            ],
            "release": release_payload,
        }

    def detail(self, actor, desk_id):
        return json.loads(json.dumps(self.desks[desk_id]))


class FakeOperations:
    def __init__(self):
        self.hash_suffix = "base"
        self.assignment = {desk_id: {"specialist": SPECIALIST, "qa": QA} for desk_id in DESKS}

    def verify_chain(self, desk_id):
        return {"valid": True, "events": 3, "last_hash": f"ops-{desk_id}-{self.hash_suffix}"}

    def state(self, actor, desk_id):
        value = self.assignment[desk_id]
        return {
            "operations": {
                "assigned_specialist": {"id": value["specialist"]},
                "assigned_qa": {"id": value["qa"]},
            }
        }


class FakeJourney:
    ALLOWED = {
        "EN_REVISION_JURIDICA": {"OBSERVADO", "APROBADO_JURIDICAMENTE", "ESCALADO"},
        "OBSERVADO": {"CORREGIDO", "ESCALADO"},
        "CORREGIDO": {"EN_REVISION_JURIDICA", "ESCALADO"},
        "APROBADO_JURIDICAMENTE": {"EN_QA", "ESCALADO"},
        "EN_QA": {"OBSERVADO", "APROBADO_QA", "ESCALADO"},
        "APROBADO_QA": {"ENTREGADO", "ESCALADO"},
        "ESCALADO": {"EN_REVISION_JURIDICA", "CERRADO", "CANCELADO"},
    }

    def detail(self, con, case_id, actor):
        row = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        return {
            "case_id": case_id,
            "current_state": row["current_state"],
            "legal_approver_id": row["legal_approver_id"],
            "qa_approver_id": row["qa_approver_id"],
        }


class M362ReviewReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m362.db"
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

    def set_journey(self, state, legal=None, qa=None):
        con = self.db()
        con.execute(
            "UPDATE m24_case_journey SET current_state=?,legal_approver_id=?,qa_approver_id=? WHERE case_id=?",
            (state, legal, qa, CASE_ID),
        )
        con.commit(); con.close()

    def approve_legal_all(self):
        for index, desk_id in enumerate(DESKS, 1):
            self.workspace.set_desk(desk_id, document_id=f"DOC-{index}", status="qa_pending", legal=True)

    def approve_qa_all(self, *, released=False):
        for index, desk_id in enumerate(DESKS, 1):
            self.workspace.set_desk(
                desk_id,
                document_id=f"DOC-{index}",
                status="released" if released else "ready_to_release",
                legal=True,
                qa=True,
                release=released,
            )

    def m24_state(self):
        con = self.db()
        try:
            row = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (CASE_ID,)).fetchone()
            return dict(row)
        finally:
            con.close()

    def transition_rows(self):
        con = self.db()
        try:
            return [dict(row) for row in con.execute(
                "SELECT * FROM m24_case_transition WHERE case_id=? ORDER BY created_at,id", (CASE_ID,)
            ).fetchall()]
        finally:
            con.close()

    def reconciliation_rows(self):
        con = self.db()
        try:
            self.center.ensure_schema(con)
            return [dict(row) for row in con.execute(
                "SELECT * FROM m36_review_reconciliation_event WHERE case_id=? ORDER BY sequence", (CASE_ID,)
            ).fetchall()]
        finally:
            con.close()

    def test_canonical_m360_state_is_required(self):
        self.assertEqual(self.center.assess(ADMIN, CASE_ID)["m24_current_state"], "EN_REVISION_JURIDICA")
        con = self.db()
        con.execute("UPDATE m36_fulfillment_intake SET state='READY_FOR_REVIEW' WHERE case_id=?", (CASE_ID,))
        con.commit(); con.close()
        with self.assertRaises(ReviewReconciliationError) as caught:
            self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(caught.exception.code, "FULFILLMENT_NOT_READY")

    def test_non_admin_cannot_assess_or_reconcile(self):
        with self.assertRaises(PermissionDenied):
            self.center.assess(CLIENT, CASE_ID)
        with self.assertRaises(PermissionDenied):
            self.center.reconcile(CLIENT, CASE_ID)

    def test_partial_legal_approval_does_not_advance_case(self):
        self.workspace.set_desk(DESKS[0], status="qa_pending", legal=True)
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["aggregate_review_state"], "LEGAL_REVIEW")
        self.assertFalse(assessment["legal_approval_complete"])
        self.assertEqual(assessment["proposed_path"], [])
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertTrue(result["idempotent"])
        self.assertEqual(self.m24_state()["current_state"], "EN_REVISION_JURIDICA")
        self.assertEqual(self.reconciliation_rows(), [])

    def test_all_legal_approvals_reconcile_to_qa_without_creating_approval(self):
        self.approve_legal_all()
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["aggregate_review_state"], "LEGAL_APPROVED")
        self.assertEqual(assessment["proposed_path"], ["APROBADO_JURIDICAMENTE", "EN_QA"])
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertTrue(result["reconciled"])
        self.assertEqual(
            [(item["from"], item["to"]) for item in result["applied_transitions"]],
            [("EN_REVISION_JURIDICA", "APROBADO_JURIDICAMENTE"), ("APROBADO_JURIDICAMENTE", "EN_QA")],
        )
        state = self.m24_state()
        self.assertEqual(state["current_state"], "EN_QA")
        self.assertEqual(state["legal_approver_id"], SPECIALIST)
        self.assertIsNone(state["qa_approver_id"])
        rows = self.transition_rows()
        self.assertEqual([row["actor_id"] for row in rows], [SYSTEM_ACTOR_ID, SYSTEM_ACTOR_ID])
        evidence = json.loads(rows[0]["evidence_json"])
        self.assertEqual(evidence["human_legal_approver_id"], SPECIALIST)
        self.assertFalse(evidence["automatic_delivery"])

    def test_all_qa_approvals_can_reconcile_three_m24_hops_atomically(self):
        self.approve_qa_all()
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(
            [item["to"] for item in result["applied_transitions"]],
            ["APROBADO_JURIDICAMENTE", "EN_QA", "APROBADO_QA"],
        )
        state = self.m24_state()
        self.assertEqual(state["current_state"], "APROBADO_QA")
        self.assertEqual(state["legal_approver_id"], SPECIALIST)
        self.assertEqual(state["qa_approver_id"], QA)
        self.assertNotEqual(state["legal_approver_id"], state["qa_approver_id"])
        history = self.center.history(ADMIN, CASE_ID)
        self.assertTrue(history["audit"]["valid"])
        self.assertEqual(history["audit"]["events"], 3)

    def test_complete_retry_is_read_only_and_idempotent(self):
        self.approve_qa_all()
        first = self.center.reconcile(ADMIN, CASE_ID)
        before_events = self.reconciliation_rows()
        before_transitions = self.transition_rows()
        second = self.center.reconcile(ADMIN, CASE_ID)
        self.assertTrue(first["reconciled"])
        self.assertFalse(second["reconciled"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(self.reconciliation_rows(), before_events)
        self.assertEqual(self.transition_rows(), before_transitions)

    def test_release_only_opens_delivery_gate_and_never_marks_delivered(self):
        self.approve_qa_all(released=True)
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(result["m24_current_state"], "APROBADO_QA")
        self.assertTrue(result["release_complete"])
        self.assertTrue(result["delivery_gate_ready"])
        self.assertNotIn("ENTREGADO", [row["to_state"] for row in self.reconciliation_rows()])
        self.assertFalse(result["governance"]["automatic_delivery"])

    def test_observation_on_any_desk_prevents_partial_success(self):
        self.approve_legal_all()
        self.workspace.set_desk(DESKS[1], status="changes_required", legal=False, open_findings=1)
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["aggregate_review_state"], "OBSERVED")
        self.assertEqual(assessment["proposed_path"], ["OBSERVADO"])
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(result["m24_current_state"], "OBSERVADO")
        self.assertFalse(result["legal_approval_complete"])

    def test_operational_hash_change_alone_is_not_correction_evidence(self):
        self.workspace.set_desk(DESKS[0], status="changes_required", open_findings=1)
        self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(self.m24_state()["current_state"], "OBSERVADO")
        self.operations.hash_suffix = "priority-only-change"
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["proposed_path"], [])
        self.assertIn("CORRECTION_EVIDENCE_NOT_CHANGED", assessment["blockers"])

    def test_new_document_revision_after_observation_enables_correction_path(self):
        self.workspace.set_desk(DESKS[0], status="changes_required", open_findings=1)
        self.center.reconcile(ADMIN, CASE_ID)
        self.workspace.set_desk(DESKS[0], status="legal_pending", revision_number=2, open_findings=0)
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["proposed_path"], ["CORREGIDO", "EN_REVISION_JURIDICA"])
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(result["m24_current_state"], "EN_REVISION_JURIDICA")

    def test_regression_after_recorded_approval_escalates_instead_of_rewinding(self):
        self.approve_qa_all()
        self.center.reconcile(ADMIN, CASE_ID)
        self.workspace.set_desk(DESKS[1], status="changes_required", revision_number=2, open_findings=1)
        assessment = self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(assessment["proposed_path"], ["ESCALADO"])
        self.assertIn("EVIDENCE_REGRESSION_AFTER_APPROVAL", assessment["blockers"])
        result = self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(result["m24_current_state"], "ESCALADO")

    def test_assignment_drift_blocks_reconciliation(self):
        self.operations.assignment[DESKS[0]]["specialist"] = "USR-OTHER"
        with self.assertRaises(ReviewReconciliationError) as caught:
            self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(caught.exception.code, "ASSIGNMENT_DRIFT")

    def test_wrong_legal_actor_or_hash_fails_closed(self):
        self.workspace.set_desk(DESKS[0], status="qa_pending", legal=True, legal_actor="USR-OTHER")
        with self.assertRaises(ReviewReconciliationError) as caught:
            self.center.assess(ADMIN, CASE_ID)
        self.assertEqual(caught.exception.code, "LEGAL_APPROVAL_MISMATCH")

    def test_tampered_reconciliation_chain_blocks_history_and_further_reconcile(self):
        self.approve_legal_all()
        self.center.reconcile(ADMIN, CASE_ID)
        con = self.db()
        con.execute(
            "UPDATE m36_review_reconciliation_event SET aggregate_state='TAMPERED' WHERE case_id=? AND sequence=1",
            (CASE_ID,),
        )
        con.commit(); con.close()
        with self.assertRaises(ReviewReconciliationError) as caught:
            self.center.history(ADMIN, CASE_ID)
        self.assertEqual(caught.exception.code, "RECONCILIATION_CHAIN_INVALID")
        self.set_journey("APROBADO_JURIDICAMENTE", legal=SPECIALIST)
        with self.assertRaises(ReviewReconciliationError) as caught:
            self.center.reconcile(ADMIN, CASE_ID)
        self.assertEqual(caught.exception.code, "RECONCILIATION_CHAIN_INVALID")

    def test_public_assessment_does_not_expose_hashes_or_approver_record_hashes(self):
        self.approve_qa_all(released=True)
        assessment = self.center.assess(ADMIN, CASE_ID)
        raw = json.dumps(assessment, ensure_ascii=False).lower()
        for forbidden in ("revision_sha256", "record_hash", "evidence_fingerprint", "operations_audit_last_hash"):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
