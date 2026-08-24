from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import uuid
from zipfile import ZipFile

import core_v11 as core
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeCenter, EvidenceIntakeError
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.m37_0_journey_guard import install_m37_0_followup_guard
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpCenter, START_CONFIRMATION
from legalai_platform.operational_security import EICAR


CASE_ID = "CASE-EVIDENCE-1"
PRODUCT = "CO-CD-003"
CLIENT = {"id": "USR-CLIENT", "role": "client", "name": "Cliente"}
OTHER = {"id": "USR-OTHER", "role": "client", "name": "Otro"}
SPECIALIST = {"id": "USR-LEGAL", "role": "specialist", "name": "Especialista"}
OTHER_SPECIALIST = {"id": "USR-OTHER-LEGAL", "role": "specialist", "name": "Otro especialista"}
ADMIN = {"id": "USR-ADMIN", "role": "admin", "name": "Administración"}


class FakeScanner:
    def __init__(self, mode="clean"):
        self.mode = mode
        self.calls = []

    def scan(self, filename, data):
        self.calls.append((filename, len(data)))
        if EICAR in data or self.mode == "blocked":
            raise ValueError("bloqueado por antimalware")
        if self.mode == "unavailable":
            raise RuntimeError("escáner no disponible")
        if self.mode == "local":
            return SimpleNamespace(status="not_scanned_local", engine="none", detail="local")
        return SimpleNamespace(status="clean", engine="fake", detail="ok")


class FakeEncryptedObjectStore:
    """Test double that preserves the encrypted-store trust boundary."""

    def __init__(self):
        self.objects = {}

    def create_schema(self, con):
        return None

    @staticmethod
    def is_reference(value):
        return bool(value and str(value).startswith("lzobj://"))

    def put(self, con, namespace, original_name, data, content_type, owner_id=None):
        object_id = "OBJ-" + uuid.uuid4().hex[:20].upper()
        reference = f"lzobj://{object_id}"
        plain = bytes(data)
        # The test double does not implement crypto, but never stores plaintext bytes as its
        # persisted representation. Integrity is checked before returning plaintext.
        cipher = b"TEST-ENC\x00" + plain[::-1]
        self.objects[reference] = {
            "plaintext": plain,
            "ciphertext": cipher,
            "ciphertext_sha256": sha256(cipher).hexdigest(),
        }
        return {
            "id": object_id,
            "reference": reference,
            "plaintext_sha256": sha256(plain).hexdigest(),
            "ciphertext_sha256": sha256(cipher).hexdigest(),
            "size_bytes": len(plain),
            "encrypted": True,
        }

    def get(self, con, reference):
        item = self.objects.get(reference)
        if not item:
            raise FileNotFoundError("objeto no registrado")
        if sha256(item["ciphertext"]).hexdigest() != item["ciphertext_sha256"]:
            raise ValueError("ciphertext alterado")
        return item["plaintext"]

    def tamper(self, reference):
        self.objects[reference]["ciphertext"] = b"tampered"


def pdf_bytes(text=b"support"):
    return b"%PDF-1.4\n" + text + b"\n%%EOF\n"


def docx_bytes(*, active=False, embedded=False):
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
        if active:
            archive.writestr("word/vbaProject.bin", b"macro")
        if embedded:
            archive.writestr("word/embeddings/object1.bin", b"ole")
    return stream.getvalue()


class M371EvidenceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db_path = root / "m371.db"
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
             "Entrega sintética previa a evidencia M37.1.", "{}", "2026-08-24T10:05:00+00:00"),
        )
        self.journey._create_default_followups(con, CASE_ID, PRODUCT, ADMIN["id"])
        con.commit(); con.close()
        self.followup = PostDeliveryFollowUpCenter(self.journey, db_factory=self.db)
        started = self.followup.start(CLIENT, CASE_ID, START_CONFIRMATION)
        self.task_id = started["tasks"][0]["follow_up_id"]
        self.scanner = FakeScanner()
        self.objects = FakeEncryptedObjectStore()
        self.center = EvidenceIntakeCenter(
            self.followup,
            self.scanner,
            self.objects,
            db_factory=self.db,
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

    def upload(self, actor=CLIENT, filename="radicado.pdf", body=None):
        return self.center.upload(actor, CASE_ID, self.task_id, filename, body or pdf_bytes(), "application/octet-stream")

    def new_center(self, scanner):
        return EvidenceIntakeCenter(self.followup, scanner, FakeEncryptedObjectStore(), db_factory=self.db)

    def test_contract_is_fail_closed_and_requires_encrypted_store(self):
        validation = self.center.validate_contract()
        self.assertEqual(validation["types"], 5)
        self.assertEqual(validation["max_file_bytes"], core.MAX_UPLOAD)
        self.assertEqual(validation["max_items_per_case"], 30)
        governance = self.center.contract["governance"]
        self.assertTrue(governance["encrypted_object_store_required"])
        self.assertFalse(governance["upload_completes_task"])
        self.assertFalse(governance["review_completes_task"])

    def test_pdf_upload_uses_encrypted_reference_and_does_not_complete_task(self):
        before = self.task_status()
        body = pdf_bytes()
        result = self.upload(body=body)
        self.assertEqual(result["state"], "RECEIVED")
        self.assertEqual(result["file_kind"], "PDF")
        self.assertEqual(result["mime_type"], "application/pdf")
        self.assertEqual(result["review"]["status"], "PENDING_REVIEW")
        self.assertTrue(result["integrity"]["encrypted_at_rest"])
        self.assertTrue(result["integrity"]["stored_object_intact"])
        self.assertFalse(result["governance"]["upload_completed_task"])
        self.assertFalse(result["claimed_content_type_trusted"])
        self.assertEqual(self.task_status(), before)
        self.assertEqual(len(self.scanner.calls), 1)
        row = self.rows("m37_evidence_item")[0]
        self.assertTrue(row["object_ref"].startswith("lzobj://"))
        self.assertEqual(len(row["plaintext_sha256"]), 64)
        stored = self.objects.objects[row["object_ref"]]
        self.assertNotEqual(stored["ciphertext"], body)
        public_raw = json.dumps(result).lower()
        for forbidden in ("plaintext_sha256", "object_ref", "uploader_id", "ciphertext"):
            self.assertNotIn(forbidden, public_raw)

    def test_invalid_extension_or_signature_is_rejected_without_persistence(self):
        for filename, body, code in (
            ("support.exe", b"MZ", "EVIDENCE_TYPE_NOT_ALLOWED"),
            ("fake.pdf", b"not-a-pdf", "EVIDENCE_SIGNATURE_MISMATCH"),
            ("fake.png", b"not-a-png", "EVIDENCE_SIGNATURE_MISMATCH"),
        ):
            with self.subTest(filename=filename):
                with self.assertRaises(EvidenceIntakeError) as caught:
                    self.center.upload(CLIENT, CASE_ID, self.task_id, filename, body)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.rows("m37_evidence_item"), [])
        self.assertEqual(self.objects.objects, {})

    def test_docx_rejects_active_and_embedded_content(self):
        for body in (docx_bytes(active=True), docx_bytes(embedded=True)):
            with self.assertRaises(EvidenceIntakeError) as caught:
                self.center.upload(CLIENT, CASE_ID, self.task_id, "unsafe.docx", body)
            self.assertEqual(caught.exception.code, "EVIDENCE_DOCX_ACTIVE_CONTENT")
        clean = self.center.upload(CLIENT, CASE_ID, self.task_id, "clean.docx", docx_bytes())
        self.assertEqual(clean["file_kind"], "DOCX")

    def test_malware_or_unavailable_scanner_fails_closed(self):
        blocked = self.new_center(FakeScanner("blocked"))
        with self.assertRaises(EvidenceIntakeError) as caught:
            blocked.upload(CLIENT, CASE_ID, self.task_id, "x.pdf", pdf_bytes())
        self.assertEqual(caught.exception.code, "EVIDENCE_MALWARE_BLOCKED")
        unavailable = self.new_center(FakeScanner("unavailable"))
        with self.assertRaises(EvidenceIntakeError) as caught:
            unavailable.upload(CLIENT, CASE_ID, self.task_id, "x.pdf", pdf_bytes())
        self.assertEqual(caught.exception.code, "EVIDENCE_SCAN_UNAVAILABLE")

    def test_local_demo_scan_state_is_transparent_not_called_clean(self):
        local = self.new_center(FakeScanner("local"))
        result = local.upload(CLIENT, CASE_ID, self.task_id, "x.pdf", pdf_bytes())
        self.assertTrue(result["security_scan"]["local_demo_unscanned"])
        self.assertFalse(result["security_scan"]["external_scan_completed"])

    def test_upload_requires_active_m37_task_snapshot(self):
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.center.upload(CLIENT, CASE_ID, "TASK-NOT-OURS", "x.pdf", pdf_bytes())
        self.assertEqual(caught.exception.code, "EVIDENCE_TASK_NOT_AVAILABLE")
        con = self.db()
        con.execute("UPDATE m37_followup_enrollment SET state='PREPARED' WHERE case_id=?", (CASE_ID,))
        con.commit(); con.close()
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.upload()
        self.assertEqual(caught.exception.code, "EVIDENCE_FOLLOWUP_NOT_ACTIVE")

    def test_cross_tenant_access_is_hidden(self):
        item = self.upload()
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.center.detail(OTHER, CASE_ID)
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.center.download(OTHER, CASE_ID, item["evidence_id"])
        self.assertEqual(caught.exception.status, 404)

    def test_client_and_unassigned_specialist_cannot_review(self):
        item = self.upload()
        for actor in (CLIENT, OTHER_SPECIALIST):
            with self.subTest(actor=actor["id"]):
                with self.assertRaises((PermissionDenied, EvidenceIntakeError)):
                    self.center.review(actor, CASE_ID, item["evidence_id"], "ACKNOWLEDGED_FOR_FOLLOWUP")
        self.assertEqual(self.rows("m37_evidence_review"), [])

    def test_assigned_specialist_review_is_append_only_and_not_legal_verification(self):
        item = self.upload()
        before = self.task_status()
        result = self.center.review(
            SPECIALIST,
            CASE_ID,
            item["evidence_id"],
            "NEEDS_CLARIFICATION",
            "Aporta una constancia donde sea visible la fecha de radicación.",
        )
        self.assertFalse(result["idempotent"])
        review = result["review"]
        self.assertEqual(review["status"], "REVIEWED_FOR_INTAKE")
        self.assertEqual(review["disposition"], "NEEDS_CLARIFICATION")
        self.assertFalse(review["authenticity_verified"])
        self.assertFalse(review["legal_sufficiency_verified"])
        self.assertFalse(review["legal_effect_verified"])
        self.assertEqual(self.task_status(), before)
        rows = self.rows("m37_evidence_review")
        self.assertEqual([row["sequence"] for row in rows], [1])
        second = self.center.review(SPECIALIST, CASE_ID, item["evidence_id"], "ACKNOWLEDGED_FOR_FOLLOWUP", "")
        self.assertEqual(second["review_count"], 2)
        self.assertEqual([row["sequence"] for row in self.rows("m37_evidence_review")], [1, 2])

    def test_identical_review_retry_is_idempotent(self):
        item = self.upload()
        first = self.center.review(SPECIALIST, CASE_ID, item["evidence_id"], "ACKNOWLEDGED_FOR_FOLLOWUP")
        second = self.center.review(SPECIALIST, CASE_ID, item["evidence_id"], "ACKNOWLEDGED_FOR_FOLLOWUP")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(len(self.rows("m37_evidence_review")), 1)

    def test_clarification_and_not_relevant_require_explanation(self):
        item = self.upload()
        for disposition in ("NEEDS_CLARIFICATION", "NOT_RELEVANT_TO_TASK"):
            with self.subTest(disposition=disposition):
                with self.assertRaises(EvidenceIntakeError) as caught:
                    self.center.review(SPECIALIST, CASE_ID, item["evidence_id"], disposition, "corto")
                self.assertEqual(caught.exception.code, "EVIDENCE_REVIEW_MESSAGE_REQUIRED")

    def test_encrypted_object_tampering_blocks_detail_download_and_review(self):
        item = self.upload()
        row = self.rows("m37_evidence_item")[0]
        self.objects.tamper(row["object_ref"])
        for operation in (
            lambda: self.center.detail(CLIENT, CASE_ID),
            lambda: self.center.download(CLIENT, CASE_ID, item["evidence_id"]),
            lambda: self.center.review(SPECIALIST, CASE_ID, item["evidence_id"], "ACKNOWLEDGED_FOR_FOLLOWUP"),
        ):
            with self.assertRaises(EvidenceIntakeError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "EVIDENCE_OBJECT_TAMPERED")

    def test_download_returns_exact_plaintext_after_integrity_check(self):
        body = pdf_bytes(b"exact bytes")
        item = self.upload(body=body)
        data, name, mime_type, public = self.center.download(CLIENT, CASE_ID, item["evidence_id"])
        self.assertEqual(data, body)
        self.assertEqual(name, "radicado.pdf")
        self.assertEqual(mime_type, "application/pdf")
        self.assertEqual(public["evidence_id"], item["evidence_id"])

    def test_upload_and_review_events_share_m37_chain_without_review_message(self):
        item = self.upload(filename="../../radicado.pdf")
        self.center.review(
            SPECIALIST,
            CASE_ID,
            item["evidence_id"],
            "NEEDS_CLARIFICATION",
            "Necesitamos una constancia con sello o número visible.",
        )
        con = self.db()
        try:
            integrity = self.followup.verify_chain(con, CASE_ID)
            events = [dict(row) for row in con.execute(
                "SELECT event_type,payload_json FROM m37_followup_event WHERE case_id=? ORDER BY sequence",
                (CASE_ID,),
            ).fetchall()]
        finally:
            con.close()
        self.assertTrue(integrity["valid"])
        self.assertEqual([row["event_type"] for row in events][-2:], ["EVIDENCE_RECEIVED", "EVIDENCE_REVIEW_RECORDED"])
        raw = json.dumps(events, ensure_ascii=False)
        self.assertNotIn("Necesitamos una constancia", raw)
        self.assertEqual(item["filename"], "radicado.pdf")

    def test_upload_does_not_change_m37_close_readiness_or_m24_task(self):
        before = self.followup.detail(CLIENT, CASE_ID)
        self.upload()
        after = self.followup.detail(CLIENT, CASE_ID)
        self.assertEqual(before["metrics"]["completed"], after["metrics"]["completed"])
        self.assertEqual(before["close_readiness"], after["close_readiness"])

    def test_task_quota_fails_before_object_persistence(self):
        self.center.contract["max_items_per_task"] = 1
        self.upload(body=pdf_bytes(b"one"))
        object_count = len(self.objects.objects)
        with self.assertRaises(EvidenceIntakeError) as caught:
            self.upload(filename="two.pdf", body=pdf_bytes(b"two"))
        self.assertEqual(caught.exception.code, "EVIDENCE_TASK_ITEM_QUOTA")
        self.assertEqual(len(self.objects.objects), object_count)


if __name__ == "__main__":
    unittest.main()
