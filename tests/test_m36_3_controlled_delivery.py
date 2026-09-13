from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.controlled_delivery_m36_3 import (
    ControlledDeliveryCenter,
    ControlledDeliveryError,
    DELIVERY_CONFIRMATION,
    STATE_DELIVERED,
    STATE_PREPARED,
)


ADMIN_A = {"id": "USR-ADMIN-A", "role": "admin", "name": "Admin A"}
ADMIN_B = {"id": "USR-ADMIN-B", "role": "admin", "name": "Admin B"}
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
OTHER_CLIENT = {"id": "USR-OTHER", "role": "client", "name": "Otro"}
SPECIALIST = {"id": "USR-LEGAL", "role": "specialist", "name": "Abogado"}
CASE_ID = "CASE-DELIVERY-1"
PRODUCT = "CO-CD-003"
DESKS = ["DSK-1", "DSK-2"]


def digest(body: bytes) -> str:
    return sha256(body).hexdigest()


class FakeWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.releases = {}
        for index, desk_id in enumerate(DESKS, 1):
            body = f"released-document-{index}".encode("utf-8")
            path = root / f"{desk_id}.docx"
            path.write_bytes(body)
            self.releases[desk_id] = {
                "path": path,
                "release": {
                    "release_id": f"REL-{index}",
                    "revision_id": f"REV-{index:04d}",
                    "sha256": digest(body),
                    "release_record_hash": digest(f"release-record-{index}".encode()),
                    "filename": f"documento_final_{index}.docx",
                    "status": "released_exact_hash",
                },
            }

    def released_path(self, actor, desk_id):
        if str(actor.get("role") or "") != "admin":
            raise PermissionDenied("workspace profesional")
        item = self.releases[desk_id]
        return item["path"], dict(item["release"])


class FakeReconciler:
    def __init__(self):
        self.audit_valid = True
        self.qa_complete = True
        self.release_complete = True
        self.delivery_gate_ready = True
        self.proposed_path = []
        self.blockers = []

    def assess(self, actor, case_id):
        return {
            "schema": "fake-m36-2",
            "case_id": case_id,
            "product_code": PRODUCT,
            "m24_current_state": "APROBADO_QA",
            "qa_approval_complete": self.qa_complete,
            "release_complete": self.release_complete,
            "delivery_gate_ready": self.delivery_gate_ready,
            "proposed_path": list(self.proposed_path),
            "blockers": list(self.blockers),
            "desk_count": len(DESKS),
            "desks": [
                {"desk_id": desk_id, "document_id": f"DOC-{index}", "released": True}
                for index, desk_id in enumerate(DESKS, 1)
            ],
        }

    def history(self, actor, case_id):
        return {"case_id": case_id, "audit": {"valid": self.audit_valid, "events": 3}}


class FakeJourney:
    DELIVERY_CONFIRMATION = DELIVERY_CONFIRMATION

    def detail(self, con, case_id, actor):
        row = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        return dict(row)

    def transition(self, con, case_id, target, reason, evidence, confirmation, actor):
        row = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            raise LookupError("journey")
        if row["current_state"] != "APROBADO_QA" or target != "ENTREGADO":
            raise ValueError("transición inválida")
        if confirmation != DELIVERY_CONFIRMATION:
            raise ValueError("confirmación inválida")
        transition_id = f"TR-{con.execute('SELECT COUNT(*) FROM m24_case_transition').fetchone()[0] + 1}"
        created_at = "2026-08-24T09:30:00-05:00"
        con.execute(
            """INSERT INTO m24_case_transition(
                 id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                transition_id,
                case_id,
                "APROBADO_QA",
                "ENTREGADO",
                actor["id"],
                actor["role"],
                actor.get("name") or actor["id"],
                reason,
                json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )
        con.execute(
            "UPDATE m24_case_journey SET current_state='ENTREGADO',delivery_actor_id=?,updated_at=? WHERE case_id=?",
            (actor["id"], created_at, case_id),
        )
        con.commit()
        return self.detail(con, case_id, actor)


class CrashAfterM24Center(ControlledDeliveryCenter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crash_once = True

    def _finalize_after_m24(self, con, row, actor):
        if self.crash_once:
            self.crash_once = False
            raise RuntimeError("synthetic crash after committed M24 delivery")
        return super()._finalize_after_m24(con, row, actor)


class M363ControlledDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db_path = root / "m363.db"
        self.delivery_root = root / "deliveries"
        self.workspace = FakeWorkspace(root / "released")
        self.reconciler = FakeReconciler()
        self.journey = FakeJourney()
        con = self.db()
        con.executescript(
            """
            CREATE TABLE cases(
              id TEXT PRIMARY KEY,product_code TEXT NOT NULL,owner_id TEXT,status TEXT
            );
            CREATE TABLE audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
            );
            CREATE TABLE m36_fulfillment_intake(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL,state TEXT NOT NULL,
              product_code TEXT NOT NULL,desk_case_ids_json TEXT NOT NULL
            );
            CREATE TABLE m36_professional_assignment(
              id TEXT PRIMARY KEY,fulfillment_intake_id TEXT NOT NULL,case_id TEXT NOT NULL,
              specialist_id TEXT NOT NULL,qa_id TEXT NOT NULL,state TEXT NOT NULL
            );
            CREATE TABLE m24_case_journey(
              case_id TEXT PRIMARY KEY,current_state TEXT NOT NULL,
              legal_approver_id TEXT,qa_approver_id TEXT,delivery_actor_id TEXT,updated_at TEXT
            );
            CREATE TABLE m24_case_transition(
              id TEXT PRIMARY KEY,case_id TEXT NOT NULL,from_state TEXT,to_state TEXT NOT NULL,
              actor_id TEXT NOT NULL,actor_role TEXT NOT NULL,actor_name TEXT NOT NULL,
              reason TEXT NOT NULL,evidence_json TEXT NOT NULL,created_at TEXT NOT NULL
            );
            """
        )
        con.execute("INSERT INTO cases VALUES(?,?,?,?)", (CASE_ID, PRODUCT, CLIENT["id"], "Activo"))
        con.execute(
            "INSERT INTO m36_fulfillment_intake VALUES(?,?,?,?,?)",
            ("FUL-1", CASE_ID, "EN_REVISION_JURIDICA", PRODUCT, json.dumps(DESKS)),
        )
        con.execute(
            "INSERT INTO m36_professional_assignment VALUES(?,?,?,?,?,?)",
            ("ASN-1", "FUL-1", CASE_ID, SPECIALIST["id"], "USR-QA", "COMPLETE"),
        )
        con.execute(
            "INSERT INTO m24_case_journey VALUES(?,?,?,?,?,?)",
            (CASE_ID, "APROBADO_QA", SPECIALIST["id"], "USR-QA", None, "2026-08-24T09:00:00-05:00"),
        )
        con.commit(); con.close()
        self.center = self.new_center()

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def new_center(self, cls=ControlledDeliveryCenter):
        return cls(
            self.reconciler,
            self.workspace,
            self.journey,
            db_factory=self.db,
            delivery_root=self.delivery_root,
        )

    def delivery_row(self):
        con = self.db()
        try:
            self.center.ensure_schema(con)
            row = con.execute("SELECT * FROM m36_controlled_delivery WHERE case_id=?", (CASE_ID,)).fetchone()
            return dict(row) if row else None
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

    def prepare_without_transition(self):
        con = self.db()
        try:
            case, fulfillment, assignment, assessment = self.center._preflight(ADMIN_A, CASE_ID, con)
            return self.center._prepare_new(con, ADMIN_A, case, fulfillment, assignment, assessment)
        finally:
            con.close()

    def test_confirmation_and_admin_are_mandatory(self):
        with self.assertRaises(PermissionDenied):
            self.center.deliver(CLIENT, CASE_ID, DELIVERY_CONFIRMATION)
        with self.assertRaises(ControlledDeliveryError) as caught:
            self.center.deliver(ADMIN_A, CASE_ID, "entregar")
        self.assertEqual(caught.exception.code, "DELIVERY_CONFIRMATION_REQUIRED")
        self.assertIsNone(self.delivery_row())

    def test_delivery_package_contains_only_exact_released_bytes(self):
        result = self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        self.assertEqual(result["state"], STATE_DELIVERED)
        self.assertFalse(result["idempotent"])
        row = self.delivery_row()
        with ZipFile(row["package_path"]) as archive:
            names = set(archive.namelist())
            self.assertEqual(
                {name for name in names if name.startswith("documentos_finales/")},
                {"documentos_finales/documento_final_1.docx", "documentos_finales/documento_final_2.docx"},
            )
            for index in (1, 2):
                expected = f"released-document-{index}".encode()
                self.assertEqual(archive.read(f"documentos_finales/documento_final_{index}.docx"), expected)
            manifest = json.loads(archive.read("MANIFEST.json"))
            self.assertEqual(manifest["delivery_channel"], "IN_APP")
            self.assertTrue(manifest["controls"]["dual_human_approval_verified"])
            self.assertFalse(manifest["controls"]["external_notification_sent"])
            receipt = json.loads(archive.read("CONSTANCIA_PUESTA_A_DISPOSICION.json"))
            self.assertFalse(receipt["download_confirmed"])
            self.assertFalse(receipt["external_delivery_confirmed"])

    def test_complete_retry_is_idempotent_without_second_package_or_transition(self):
        first = self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        row_before = self.delivery_row()
        second = self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        row_after = self.delivery_row()
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["delivery_id"], second["delivery_id"])
        self.assertEqual(row_before["package_sha256"], row_after["package_sha256"])
        self.assertEqual(len(self.transition_rows()), 1)
        con = self.db()
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM m36_controlled_delivery").fetchone()[0], 1)
        finally:
            con.close()

    def test_crash_after_m24_is_recovered_without_changing_delivery_actor(self):
        crashing = self.new_center(CrashAfterM24Center)
        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            crashing.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        con = self.db()
        try:
            row = dict(con.execute("SELECT * FROM m36_controlled_delivery WHERE case_id=?", (CASE_ID,)).fetchone())
            journey = dict(con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (CASE_ID,)).fetchone())
            transition = dict(con.execute("SELECT * FROM m24_case_transition WHERE case_id=?", (CASE_ID,)).fetchone())
        finally:
            con.close()
        self.assertEqual(row["state"], STATE_PREPARED)
        self.assertEqual(journey["current_state"], "ENTREGADO")
        recovered = self.center.deliver(ADMIN_B, CASE_ID, DELIVERY_CONFIRMATION)
        self.assertTrue(recovered["idempotent"])
        final = self.delivery_row()
        self.assertEqual(final["state"], STATE_DELIVERED)
        self.assertEqual(final["delivered_by"], ADMIN_A["id"])
        self.assertEqual(final["delivered_at"], transition["created_at"])
        self.assertEqual(final["m24_transition_id"], transition["id"])
        self.assertEqual(len(self.transition_rows()), 1)

    def test_prepared_retry_revalidates_m362_before_delivery(self):
        self.prepare_without_transition()
        self.reconciler.audit_valid = False
        with self.assertRaises(ControlledDeliveryError) as caught:
            self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        self.assertEqual(caught.exception.code, "RECONCILIATION_CHAIN_INVALID")
        self.assertEqual(self.delivery_row()["state"], STATE_PREPARED)
        self.assertEqual(self.transition_rows(), [])

    def test_release_record_or_file_drift_blocks_prepared_delivery(self):
        self.prepare_without_transition()
        self.workspace.releases[DESKS[0]]["release"]["release_record_hash"] = "f" * 64
        with self.assertRaises(ControlledDeliveryError) as caught:
            self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        self.assertEqual(caught.exception.code, "RELEASE_SNAPSHOT_DRIFT")
        self.assertEqual(self.transition_rows(), [])

    def test_package_tampering_blocks_detail_download_and_retry(self):
        self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        row = self.delivery_row()
        Path(row["package_path"]).write_bytes(b"tampered")
        for operation in (
            lambda: self.center.detail(ADMIN_A, CASE_ID),
            lambda: self.center.detail(CLIENT, CASE_ID),
            lambda: self.center.download(CLIENT, CASE_ID),
            lambda: self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION),
        ):
            with self.assertRaises(ControlledDeliveryError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "DELIVERY_PACKAGE_TAMPERED")

    def test_owner_can_read_and_request_download_but_other_users_cannot(self):
        delivered = self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        owner_detail = self.center.detail(CLIENT, CASE_ID)
        self.assertEqual(owner_detail["delivery_id"], delivered["delivery_id"])
        for actor in (OTHER_CLIENT, SPECIALIST):
            with self.assertRaises(PermissionDenied):
                self.center.detail(actor, CASE_ID)
            with self.assertRaises(PermissionDenied):
                self.center.download(actor, CASE_ID)
        target, name, download_view = self.center.download(CLIENT, CASE_ID)
        self.assertTrue(target.is_file())
        self.assertEqual(name, delivered["package_name"])
        self.assertEqual(download_view["download_requests"], 1)
        self.assertTrue(download_view["governance"]["download_request_is_not_receipt_confirmation"])
        con = self.db()
        try:
            event = dict(con.execute("SELECT * FROM m36_delivery_access_event").fetchone())
            self.assertEqual(event["action"], "DOWNLOAD_REQUESTED")
            audit = [dict(row) for row in con.execute(
                "SELECT * FROM audit_log WHERE action='download_requested'"
            ).fetchall()]
            self.assertEqual(len(audit), 1)
            self.assertNotIn("received", audit[0]["action"])
        finally:
            con.close()

    def test_public_model_excludes_internal_paths_release_ids_and_approvers(self):
        payload = self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        raw = json.dumps(payload, ensure_ascii=False).lower()
        for forbidden in (
            "package_path",
            "release_id",
            "revision_id",
            "release_record_hash",
            "specialist_id",
            "qa_id",
            "owner_id",
            "m24_transition_id",
            "fulfillment_intake_id",
            "assignment_id",
        ):
            self.assertNotIn(forbidden, raw)
        self.assertIn("package_sha256", payload)
        self.assertIn("manifest_sha256", payload)

    def test_queue_distinguishes_prepared_from_delivered(self):
        self.prepare_without_transition()
        queue = self.center.queue(ADMIN_A)
        self.assertEqual(queue["metrics"]["prepared"], 1)
        self.assertEqual(queue["metrics"]["delivered_in_app"], 0)
        self.assertIn("no acredita descarga", queue["notice"])
        with self.assertRaises(PermissionDenied):
            self.center.queue(CLIENT)

    def test_gate_not_ready_never_creates_package_or_ledger(self):
        self.reconciler.delivery_gate_ready = False
        self.reconciler.release_complete = False
        with self.assertRaises(ControlledDeliveryError) as caught:
            self.center.deliver(ADMIN_A, CASE_ID, DELIVERY_CONFIRMATION)
        self.assertEqual(caught.exception.code, "RELEASE_GATE_INCOMPLETE")
        self.assertIsNone(self.delivery_row())
        self.assertFalse(self.delivery_root.exists() and any(self.delivery_root.rglob("*.zip")))


if __name__ == "__main__":
    unittest.main()
