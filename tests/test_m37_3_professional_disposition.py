from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeCenter
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.m37_0_journey_guard import install_m37_0_followup_guard
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpCenter, PostDeliveryFollowUpError, START_CONFIRMATION
from legalai_platform.professional_disposition_m37_3 import (
    ProfessionalDispositionCenter,
    ProfessionalDispositionError,
    TARGET_CLOSE,
    TARGET_ESCALATE,
)
from legalai_platform.timing_reminders_m37_2_hardening import HardenedTimingReminderCenter
from tests.test_m37_1_evidence_intake import FakeEncryptedObjectStore, FakeScanner, pdf_bytes


CASE_ID = "CASE-DISPOSITION-1"
PRODUCT = "CO-CD-003"
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
OTHER = {"id": "USR-OTHER", "role": "client", "name": "Otro"}
SPECIALIST = {"id": "USR-LEGAL", "role": "specialist", "name": "Especialista"}
OTHER_SPECIALIST = {"id": "USR-OTHER-LEGAL", "role": "specialist", "name": "Otro especialista"}
ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Administración"}
BOGOTA = ZoneInfo("America/Bogota")
FIXED_NOW = datetime(2026, 8, 24, 15, 0, 0, tzinfo=BOGOTA)
CLOSE_INTERNAL = "Revisé el estado integral del seguimiento y no identifico actuaciones pendientes dentro del alcance contratado."
CLOSE_PUBLIC = "El seguimiento contratado fue completado y el expediente se cierra administrativamente sin afirmar un resultado jurídico externo."
ESC_INTERNAL = "Durante el seguimiento apareció una circunstancia que exige una nueva revisión jurídica controlada antes de continuar."
ESC_PUBLIC = "El expediente requiere una nueva revisión profesional antes de continuar con el seguimiento actual."


class M373ProfessionalDispositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m373.db"
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
             "Entrega sintética previa a M37.3.", "{}", "2026-08-24T10:05:00+00:00"),
        )
        self.journey._create_default_followups(con, CASE_ID, PRODUCT, ADMIN["id"])
        con.commit(); con.close()

        self.followup = PostDeliveryFollowUpCenter(self.journey, db_factory=self.db)
        started = self.followup.start(CLIENT, CASE_ID, START_CONFIRMATION)
        self.task_ids = [item["follow_up_id"] for item in started["tasks"]]
        self.task_id = self.task_ids[0]
        self.scanner = FakeScanner()
        self.objects = FakeEncryptedObjectStore()
        self.evidence = EvidenceIntakeCenter(self.followup, self.scanner, self.objects, db_factory=self.db)
        self.timing = HardenedTimingReminderCenter(
            self.followup,
            self.evidence,
            db_factory=self.db,
            now_provider=lambda: FIXED_NOW,
        )
        self.center = ProfessionalDispositionCenter(
            self.followup,
            self.evidence,
            self.timing,
            db_factory=self.db,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def rows(self, table):
        con = self.db()
        try:
            return [dict(row) for row in con.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()]
        finally:
            con.close()

    def complete_all_tasks(self):
        for task_id in self.task_ids:
            self.followup.record_task(
                SPECIALIST,
                CASE_ID,
                task_id,
                "completed",
                "Actividad de seguimiento revisada y registrada por el especialista.",
            )

    def close(self, actor=SPECIALIST, **overrides):
        return self.center.dispose(
            actor,
            CASE_ID,
            TARGET_CLOSE,
            overrides.get("reason_code", "FOLLOW_UP_SCOPE_COMPLETED"),
            overrides.get("internal_reason", CLOSE_INTERNAL),
            overrides.get("client_summary", CLOSE_PUBLIC),
            overrides.get("confirmation", "CERRAR SEGUIMIENTO"),
        )

    def escalate(self, actor=SPECIALIST, **overrides):
        return self.center.dispose(
            actor,
            CASE_ID,
            TARGET_ESCALATE,
            overrides.get("reason_code", "LEGAL_REVIEW_REQUIRED"),
            overrides.get("internal_reason", ESC_INTERNAL),
            overrides.get("client_summary", ESC_PUBLIC),
            overrides.get("confirmation", "ESCALAR SEGUIMIENTO"),
        )

    def test_contract_distinguishes_scope_close_from_legal_success(self):
        validation = self.center.validate_contract()
        self.assertTrue(validation["valid"])
        governance = self.center.contract["governance"]
        self.assertTrue(governance["close_requires_assigned_specialist"])
        self.assertTrue(governance["m24_transition_uses_client_summary_only"])
        for key in (
            "admin_may_close_without_specialist",
            "client_may_dispose_case",
            "internal_reason_exposed_to_client",
            "disposition_is_legal_success",
            "disposition_verifies_external_effect",
            "disposition_verifies_evidence_authenticity",
            "disposition_verifies_legal_deadline",
            "automatic_close",
            "automatic_escalation",
            "external_notification",
        ):
            self.assertFalse(governance[key])

    def test_incomplete_tasks_block_close_but_not_escalation(self):
        assessment = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertIn("REQUIRED_TASKS_NOT_COMPLETED", assessment["close_gate"]["blockers"])
        self.assertFalse(assessment["close_gate"]["ready"])
        self.assertTrue(assessment["escalation_gate"]["ready"])
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.close()
        self.assertEqual(caught.exception.code, "DISPOSITION_CLOSE_BLOCKED")
        escalated = self.escalate()
        self.assertEqual(escalated["m24_current_state"], "ESCALADO")
        self.assertEqual(escalated["disposition"]["target"], "ESCALADO")
        self.assertFalse(escalated["disposition"]["governance"]["legal_success_verified"])

    def test_only_assigned_specialist_can_close(self):
        self.complete_all_tasks()
        admin_view = self.center.assessment(ADMIN, CASE_ID)
        self.assertTrue(admin_view["close_gate"]["ready"])
        self.assertFalse(admin_view["close_gate"]["actor_can_execute"])
        with self.assertRaises(PermissionDenied):
            self.close(actor=ADMIN)
        with self.assertRaises(PostDeliveryFollowUpError):
            self.close(actor=OTHER_SPECIALIST)
        with self.assertRaises(PermissionDenied):
            self.close(actor=CLIENT)

    def test_admin_or_assigned_specialist_may_escalate_but_client_cannot(self):
        admin_result = self.escalate(actor=ADMIN)
        self.assertEqual(admin_result["m24_current_state"], "ESCALADO")
        self.assertEqual(admin_result["disposition"]["actor_role"], "admin")

    def test_cross_tenant_assessment_is_hidden(self):
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.assessment(OTHER, CASE_ID)
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.code, "FOLLOWUP_NOT_AVAILABLE")

    def test_pending_evidence_blocks_close(self):
        self.complete_all_tasks()
        uploaded = self.evidence.upload(CLIENT, CASE_ID, self.task_id, "radicado.pdf", pdf_bytes(), "application/pdf")
        self.assertEqual(uploaded["review"]["status"], "PENDING_REVIEW")
        assessment = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertIn("EVIDENCE_PENDING_REVIEW", assessment["close_gate"]["blockers"])
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.close()
        self.assertEqual(caught.exception.code, "DISPOSITION_CLOSE_BLOCKED")

    def test_needs_clarification_blocks_close_until_resolved_by_new_review(self):
        self.complete_all_tasks()
        uploaded = self.evidence.upload(CLIENT, CASE_ID, self.task_id, "radicado.pdf", pdf_bytes(), "application/pdf")
        evidence_id = uploaded["evidence_id"]
        self.evidence.review(
            SPECIALIST,
            CASE_ID,
            evidence_id,
            "NEEDS_CLARIFICATION",
            "El soporte requiere una aclaración adicional antes de concluir el seguimiento.",
        )
        assessment = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertIn("EVIDENCE_NEEDS_CLARIFICATION", assessment["close_gate"]["blockers"])
        self.evidence.review(SPECIALIST, CASE_ID, evidence_id, "ACKNOWLEDGED_FOR_FOLLOWUP", "")
        ready = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertEqual(ready["close_gate"]["blockers"], [])
        self.assertTrue(ready["close_gate"]["ready"])

    def test_active_reminder_blocks_close_and_acknowledge_reopens_gate(self):
        self.complete_all_tasks()
        reminder = self.timing.schedule_reminder(CLIENT, CASE_ID, self.task_id, "2026-08-25")
        assessment = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertIn("ACTIVE_REMINDER", assessment["close_gate"]["blockers"])
        self.timing.record_reminder_action(CLIENT, CASE_ID, reminder["reminder_id"], "ACKNOWLEDGED")
        ready = self.center.assessment(SPECIALIST, CASE_ID)
        self.assertNotIn("ACTIVE_REMINDER", ready["close_gate"]["blockers"])
        self.assertTrue(ready["close_gate"]["ready"])

    def test_close_transitions_once_and_exposes_only_client_summary(self):
        self.complete_all_tasks()
        result = self.close()
        self.assertFalse(result["idempotent"])
        self.assertEqual(result["m24_current_state"], "CERRADO")
        disposition = result["disposition"]
        self.assertEqual(disposition["status"], "COMPLETED")
        self.assertEqual(disposition["target"], "CERRADO")
        self.assertEqual(disposition["client_summary"], CLOSE_PUBLIC)
        self.assertNotIn("internal_reason", disposition)
        self.assertFalse(disposition["governance"]["legal_success_verified"])
        transitions = [row for row in self.rows("m24_case_transition") if row["to_state"] == "CERRADO"]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]["reason"], CLOSE_PUBLIC)
        self.assertNotIn(CLOSE_INTERNAL, transitions[0]["reason"])
        evidence = json.loads(transitions[0]["evidence_json"])
        self.assertFalse(evidence["internal_reason_exposed"])
        self.assertFalse(evidence["legal_success_verified"])
        public_raw = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(CLOSE_INTERNAL, public_raw)

    def test_exact_close_retry_is_idempotent_without_second_transition_or_event(self):
        self.complete_all_tasks()
        first = self.close()
        event_count = len(self.rows("m37_disposition_event"))
        followup_event_count = len(self.rows("m37_followup_event"))
        second = self.close()
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["disposition"]["disposition_id"], first["disposition"]["disposition_id"])
        self.assertEqual(len([row for row in self.rows("m24_case_transition") if row["to_state"] == "CERRADO"]), 1)
        self.assertEqual(len(self.rows("m37_disposition_event")), event_count)
        self.assertEqual(len(self.rows("m37_followup_event")), followup_event_count)

    def test_different_retry_after_prepared_or_completed_is_rejected(self):
        self.complete_all_tasks()
        self.close()
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.close(internal_reason=CLOSE_INTERNAL + " Cambio incompatible.")
        self.assertEqual(caught.exception.code, "DISPOSITION_ALREADY_PREPARED")

    def test_crash_after_m24_commit_is_recovered_without_second_transition(self):
        self.complete_all_tasks()
        original_finalize = self.center._finalize

        def crash_after_transition(*args, **kwargs):
            raise RuntimeError("synthetic crash after M24 commit")

        self.center._finalize = crash_after_transition
        with self.assertRaises(RuntimeError):
            self.close()
        self.center._finalize = original_finalize
        self.assertEqual(len([row for row in self.rows("m24_case_transition") if row["to_state"] == "CERRADO"]), 1)
        intent = self.rows("m37_disposition_intent")
        self.assertEqual(len(intent), 1)
        prepared_events = self.rows("m37_disposition_event")
        self.assertEqual([row["action"] for row in prepared_events], ["PREPARED"])
        recovered = self.close()
        self.assertTrue(recovered["idempotent"])
        self.assertEqual(recovered["disposition"]["status"], "COMPLETED")
        self.assertEqual(len([row for row in self.rows("m24_case_transition") if row["to_state"] == "CERRADO"]), 1)
        self.assertEqual([row["action"] for row in self.rows("m37_disposition_event")], ["PREPARED", "COMPLETED"])

    def test_intent_tampering_blocks_read_and_retry(self):
        self.complete_all_tasks()
        self.close()
        con = self.db()
        con.execute("UPDATE m37_disposition_intent SET client_summary='alterado' WHERE case_id=?", (CASE_ID,))
        con.commit(); con.close()
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.center.assessment(SPECIALIST, CASE_ID)
        self.assertEqual(caught.exception.code, "DISPOSITION_INTENT_TAMPERED")

    def test_event_chain_tampering_blocks_read(self):
        self.complete_all_tasks()
        self.close()
        con = self.db()
        con.execute("UPDATE m37_disposition_event SET previous_hash='tampered' WHERE sequence=2")
        con.commit(); con.close()
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.center.assessment(SPECIALIST, CASE_ID)
        self.assertEqual(caught.exception.code, "DISPOSITION_EVENT_CHAIN_TAMPERED")

    def test_followup_ledger_does_not_duplicate_internal_or_client_reason(self):
        self.complete_all_tasks()
        self.close()
        rows = self.rows("m37_followup_event")
        payloads = [str(row["payload_json"]) for row in rows if row["event_type"] in {"DISPOSITION_PREPARED", "FOLLOW_UP_CLOSED"}]
        self.assertTrue(payloads)
        for payload in payloads:
            self.assertNotIn(CLOSE_INTERNAL, payload)
            self.assertNotIn(CLOSE_PUBLIC, payload)
        self.assertTrue(any(json.loads(payload).get("internal_reason_in_ledger") is False for payload in payloads))

    def test_wrong_confirmation_and_short_visible_summary_fail_before_intent(self):
        self.complete_all_tasks()
        with self.assertRaises(ProfessionalDispositionError) as caught:
            self.close(confirmation="cerrar")
        self.assertEqual(caught.exception.code, "DISPOSITION_CONFIRMATION_REQUIRED")
        with self.assertRaises(ProfessionalDispositionError) as caught2:
            self.close(client_summary="Muy corto")
        self.assertEqual(caught2.exception.code, "DISPOSITION_CLIENT_SUMMARY_INVALID")
        self.center.ensure_schema(self.db())
        self.assertEqual(self.rows("m37_disposition_intent"), [])


if __name__ == "__main__":
    unittest.main()
