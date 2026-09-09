from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

import core_v11 as core
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.m37_0_journey_guard import install_m37_0_followup_guard
from legalai_platform.post_delivery_followup_m37_0 import (
    PostDeliveryFollowUpCenter,
    PostDeliveryFollowUpError,
    START_CONFIRMATION,
)


CASE_ID = "CASE-FOLLOWUP-1"
PRODUCT = "CO-CD-003"
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
OTHER = {"id": "USR-OTHER", "role": "client", "name": "Otro cliente"}
SPECIALIST = {"id": "USR-LEGAL", "role": "specialist", "name": "Especialista"}
ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Administración"}
ADMIN_RETRY = {"id": "USR-ADMIN-2", "role": "admin", "name": "Administración 2"}


class CrashAfterM24Start(PostDeliveryFollowUpCenter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crash_once = True

    def _finalize_start(self, con, enrollment, actor):
        if self.crash_once:
            self.crash_once = False
            raise RuntimeError("synthetic crash after M24 EN_SEGUIMIENTO")
        return super()._finalize_start(con, enrollment, actor)


class M370PostDeliveryFollowUpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "m370.db"
        self.journey = M24CaseJourneyCenter(core.ROOT)
        install_m37_0_followup_guard(self.journey)
        con = self.db()
        con.executescript(
            """
            CREATE TABLE cases(
              id TEXT PRIMARY KEY,
              product_code TEXT NOT NULL,
              owner_id TEXT,
              specialist_id TEXT,
              status TEXT,
              result TEXT NOT NULL DEFAULT '{}',
              risk TEXT,
              updated_at TEXT
            );
            CREATE TABLE documents(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL
            );
            CREATE TABLE audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
            );
            CREATE TABLE m36_controlled_delivery(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              owner_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              state TEXT NOT NULL,
              delivered_at TEXT
            );
            """
        )
        con.execute(
            "INSERT INTO cases(id,product_code,owner_id,specialist_id,status,result,risk,updated_at) VALUES(?,?,?,?,?,?,?,?)",
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
               (case_id,product_code,current_state,legal_approver_id,qa_approver_id,delivery_actor_id,diagnosis_json,route_json,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                CASE_ID, PRODUCT, "ENTREGADO", SPECIALIST["id"], ADMIN["id"], ADMIN["id"],
                "{}", "{}", "2026-08-24T09:00:00+00:00", "2026-08-24T10:05:00+00:00",
            ),
        )
        con.execute(
            """INSERT INTO m24_case_transition
               (id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                "TR-DELIVERY", CASE_ID, "APROBADO_QA", "ENTREGADO", ADMIN["id"], "admin", "Administración",
                "Entrega controlada sintética previa al seguimiento M37.0.", "{}", "2026-08-24T10:05:00+00:00",
            ),
        )
        self.journey._create_default_followups(con, CASE_ID, PRODUCT, ADMIN["id"])
        con.commit(); con.close()
        self.center = PostDeliveryFollowUpCenter(self.journey, db_factory=self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def enrollment(self):
        con = self.db()
        try:
            self.center.ensure_schema(con)
            row = con.execute("SELECT * FROM m37_followup_enrollment WHERE case_id=?", (CASE_ID,)).fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def events(self):
        con = self.db()
        try:
            self.center.ensure_schema(con)
            return [dict(row) for row in con.execute(
                "SELECT * FROM m37_followup_event WHERE case_id=? ORDER BY sequence", (CASE_ID,)
            ).fetchall()]
        finally:
            con.close()

    def journey_state(self):
        con = self.db()
        try:
            return con.execute("SELECT current_state FROM m24_case_journey WHERE case_id=?", (CASE_ID,)).fetchone()[0]
        finally:
            con.close()

    def transition_count(self, target="EN_SEGUIMIENTO"):
        con = self.db()
        try:
            return con.execute(
                "SELECT COUNT(*) FROM m24_case_transition WHERE case_id=? AND to_state=?", (CASE_ID, target)
            ).fetchone()[0]
        finally:
            con.close()

    def start(self, actor=CLIENT):
        return self.center.start(actor, CASE_ID, START_CONFIRMATION)

    def test_contract_registry_matches_all_m24_generated_tasks_exactly(self):
        validation = self.center.validate_contracts()
        self.assertEqual(validation, {"valid": True, "products": 11, "tasks": 44})
        for code, plan in self.journey.plans.items():
            expected = [plan["delivery_action"], *(plan.get("required_actions") or [])]
            configured = [
                item["label_exact"]
                for item in self.center.contracts["products"][code]["tasks"]
            ]
            self.assertEqual(configured, expected)

    def test_read_before_start_is_non_mutating_and_uses_operational_timing_only(self):
        before = self.transition_count()
        detail = self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(detail["lifecycle"], "AVAILABLE")
        self.assertFalse(detail["started"])
        self.assertEqual(self.journey_state(), "ENTREGADO")
        self.assertEqual(self.transition_count(), before)
        self.assertFalse(detail["governance"]["legal_deadline_calculation"])
        self.assertTrue(detail["governance"]["operational_checkpoint_is_not_legal_deadline"])
        for task in detail["tasks"]:
            self.assertFalse(task["timing"]["is_legal_deadline"])
            self.assertFalse(task["timing"]["legal_deadline_verified"])

    def test_delivery_m36_3_is_mandatory(self):
        con = self.db()
        con.execute("DELETE FROM m36_controlled_delivery WHERE case_id=?", (CASE_ID,))
        con.commit(); con.close()
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(caught.exception.code, "FOLLOWUP_NOT_AVAILABLE")
        with self.assertRaises(PostDeliveryFollowUpError):
            self.start()
        self.assertIsNone(self.enrollment())

    def test_start_requires_exact_confirmation_and_is_idempotent(self):
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.start(CLIENT, CASE_ID, "INICIAR")
        self.assertEqual(caught.exception.code, "FOLLOWUP_CONFIRMATION_REQUIRED")
        first = self.start()
        second = self.start()
        self.assertEqual(first["lifecycle"], "ACTIVE")
        self.assertEqual(first["m24_current_state"], "EN_SEGUIMIENTO")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(self.transition_count(), 1)
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.events()[0]["event_type"], "FOLLOW_UP_STARTED")

    def test_start_reuses_m24_tasks_without_duplication(self):
        before = self.center.detail(CLIENT, CASE_ID)["metrics"]["tasks"]
        started = self.start()
        after = started["metrics"]["tasks"]
        con = self.db()
        count = con.execute("SELECT COUNT(*) FROM m24_case_follow_up WHERE case_id=?", (CASE_ID,)).fetchone()[0]
        con.close()
        self.assertEqual(before, 4)
        self.assertEqual(after, before)
        self.assertEqual(count, before)

    def test_crash_after_m24_is_recoverable_and_preserves_original_actor(self):
        crashing = CrashAfterM24Start(self.journey, db_factory=self.db)
        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            crashing.start(CLIENT, CASE_ID, START_CONFIRMATION)
        self.assertEqual(self.journey_state(), "EN_SEGUIMIENTO")
        self.assertEqual(self.enrollment()["state"], "PREPARED")
        recovered = self.center.start(ADMIN_RETRY, CASE_ID, START_CONFIRMATION)
        self.assertEqual(recovered["lifecycle"], "ACTIVE")
        row = self.enrollment()
        self.assertEqual(row["started_by"], CLIENT["id"])
        self.assertEqual(self.transition_count(), 1)
        self.assertEqual(len(self.events()), 1)

    def test_other_client_is_hidden(self):
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.detail(OTHER, CASE_ID)
        self.assertEqual(caught.exception.code, "FOLLOWUP_NOT_AVAILABLE")
        self.assertEqual(caught.exception.status, 404)
        self.start()
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.record_task(OTHER, CASE_ID, self.center.detail(CLIENT, CASE_ID)["tasks"][0]["follow_up_id"], "completed", "Acción ajena no autorizada")
        self.assertEqual(caught.exception.status, 404)

    def test_client_completion_is_self_reported_not_verified(self):
        started = self.start()
        task = started["tasks"][0]
        result = self.center.record_task(
            CLIENT,
            CASE_ID,
            task["follow_up_id"],
            "completed",
            "Radicación reportada por el cliente con soporte pendiente de revisión.",
        )
        updated = next(item for item in result["tasks"] if item["follow_up_id"] == task["follow_up_id"])
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["completion"]["class"], "SELF_REPORTED")
        self.assertFalse(updated["completion"]["evidence_verified"])
        self.assertFalse(updated["completion"]["legal_effect_verified"])
        raw_events = json.dumps(self.events(), ensure_ascii=False)
        self.assertNotIn("Radicación reportada por el cliente", raw_events)

    def test_professional_record_is_not_evidence_verification(self):
        started = self.start(ADMIN)
        task = started["tasks"][0]
        result = self.center.record_task(
            SPECIALIST,
            CASE_ID,
            task["follow_up_id"],
            "completed",
            "Especialista registra la actuación sin validar todavía su efecto jurídico.",
        )
        updated = next(item for item in result["tasks"] if item["follow_up_id"] == task["follow_up_id"])
        self.assertEqual(updated["completion"]["class"], "PROFESSIONAL_RECORDED")
        self.assertFalse(updated["completion"]["evidence_verified"])
        self.assertFalse(updated["completion"]["legal_effect_verified"])

    def test_generic_m24_update_is_blocked_after_enrollment(self):
        started = self.start()
        task_id = started["tasks"][0]["follow_up_id"]
        con = self.db()
        try:
            with self.assertRaises(PermissionError):
                self.journey.update_follow_up(
                    con,
                    CASE_ID,
                    task_id,
                    "completed",
                    "Intento de bypass directo del control M37.0.",
                    CLIENT,
                )
        finally:
            con.close()
        controlled = self.center.record_task(
            CLIENT,
            CASE_ID,
            task_id,
            "completed",
            "Actualización realizada mediante la compuerta M37.0.",
        )
        self.assertEqual(controlled["metrics"]["completed"], 1)

    def test_all_required_tasks_only_make_close_ready_without_closing_case(self):
        current = self.start()
        for index, task in enumerate(current["tasks"], 1):
            current = self.center.record_task(
                CLIENT,
                CASE_ID,
                task["follow_up_id"],
                "completed",
                f"Actividad operacional número {index} reportada como completada por el titular.",
            )
        self.assertTrue(current["close_readiness"]["ready"])
        self.assertFalse(current["close_readiness"]["automatic_close"])
        self.assertEqual(current["m24_current_state"], "EN_SEGUIMIENTO")
        self.assertEqual(self.journey_state(), "EN_SEGUIMIENTO")
        self.assertEqual(self.transition_count("CERRADO"), 0)

    def test_task_retry_is_idempotent_and_does_not_duplicate_event(self):
        task_id = self.start()["tasks"][0]["follow_up_id"]
        note = "Constancia operacional registrada para verificar la idempotencia M37.0."
        first = self.center.record_task(CLIENT, CASE_ID, task_id, "completed", note)
        events_after_first = len(self.events())
        second = self.center.record_task(CLIENT, CASE_ID, task_id, "completed", note)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(len(self.events()), events_after_first)

    def test_tampered_m37_event_chain_blocks_read_and_writes(self):
        task_id = self.start()["tasks"][0]["follow_up_id"]
        con = self.db()
        con.execute(
            "UPDATE m37_followup_event SET payload_json=? WHERE case_id=? AND sequence=1",
            ('{"tampered":true}', CASE_ID),
        )
        con.commit(); con.close()
        with self.assertRaises(PostDeliveryFollowUpError) as caught:
            self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(caught.exception.code, "FOLLOWUP_AUDIT_INVALID")
        with self.assertRaises(PostDeliveryFollowUpError):
            self.center.record_task(CLIENT, CASE_ID, task_id, "completed", "Intento posterior a manipulación de la cadena.")

    def test_public_model_minimizes_internal_followup_plumbing(self):
        detail = self.start()
        raw = json.dumps(detail, ensure_ascii=False).lower()
        for forbidden in (
            "task_ids_json",
            "prepared_by",
            "started_by",
            "m24_transition_id",
            "event_hash",
            "previous_hash",
            "actor_id",
            "owner_id",
            "specialist_id",
            "note\":",
        ):
            self.assertNotIn(forbidden, raw)
        self.assertIn("note_present", raw)


if __name__ == "__main__":
    unittest.main()
