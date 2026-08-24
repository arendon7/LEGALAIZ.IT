import json
import sqlite3
import unittest

from payment_sandbox_backend import PaymentSandboxCenter
from self_service_backend import SelfServiceCenter
from legalai_platform.case_activation_m35_3 import CaseActivationCenter, CaseActivationError


class FakePortal:
    def product(self, code):
        if code != "CO-CD-003":
            return None
        return {
            "code": code,
            "title": "Reclamo de consumo",
            "price_auto": 19900,
            "price_review": 79900,
            "documents": ["Reclamación"],
        }


def memory_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(
        """
        CREATE TABLE users(
          id TEXT PRIMARY KEY,
          role TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE cases(
          id TEXT PRIMARY KEY,
          product_code TEXT NOT NULL,
          title TEXT NOT NULL,
          risk TEXT NOT NULL,
          status TEXT NOT NULL,
          owner_id TEXT,
          specialist_id TEXT,
          review_status TEXT NOT NULL DEFAULT 'Pendiente',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          answers TEXT NOT NULL DEFAULT '{}',
          result TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE documents(
          id TEXT PRIMARY KEY,
          case_id TEXT NOT NULL,
          kind TEXT NOT NULL
        );
        CREATE TABLE m24_case_journey(
          case_id TEXT PRIMARY KEY,
          product_code TEXT NOT NULL,
          current_state TEXT NOT NULL,
          legal_approver_id TEXT,
          qa_approver_id TEXT,
          delivery_actor_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE m35_commerce_case_links(
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          product_code TEXT NOT NULL,
          service_level TEXT NOT NULL,
          order_id TEXT NOT NULL,
          payment_intent_id TEXT,
          case_id TEXT,
          state TEXT NOT NULL,
          checkout_consent_at TEXT NOT NULL,
          case_consent_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        """
    )
    con.executemany(
        "INSERT INTO users(id,role,active) VALUES(?,?,?)",
        [("USR-A", "client", 1), ("USR-B", "client", 1)],
    )
    return con


class M353CaseActivationTests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.self_service = SelfServiceCenter(
            [{"code": "CO-CD-003", "title": "Reclamo de consumo"}],
            FakePortal(),
        )
        self.payments = PaymentSandboxCenter(b"m35-3-activation-signing-key")
        self.self_service.create_schema(self.con)
        self.payments.create_schema(self.con)
        self.center = CaseActivationCenter(self.self_service, self.payments)
        self.case_id = "LZ-M353A001"
        now = "2026-08-24T02:30:00+00:00"
        self.con.execute(
            """INSERT INTO cases(
                 id,product_code,title,risk,status,owner_id,specialist_id,review_status,
                 created_at,updated_at,answers,result
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.case_id,
                "CO-CD-003",
                "Garantía de consumo",
                "green",
                "Expediente abierto",
                "USR-A",
                None,
                "Pendiente",
                now,
                now,
                json.dumps({"private_answer": "never expose"}),
                json.dumps({"route": "Garantía"}),
            ),
        )
        detail = {
            "product_title": "Reclamo de consumo",
            "documents": ["Reclamación"],
            "service_label": "Solución revisada",
            "service_level": "solucion_revisada",
            "risk": "green",
            "environment": "Pago simulado de prototipo; no realiza cargo real.",
            "commerce_trace_required": True,
        }
        self.order_id = "ORD-M353A001"
        self.con.execute(
            """INSERT INTO checkout_orders(
                 id,user_id,product_code,case_id,service_mode,review_selected,document_price,
                 review_price,total,currency,status,payment_method,receipt_number,detail,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.order_id,
                "USR-A",
                "CO-CD-003",
                None,
                "solucion_revisada",
                1,
                19900,
                79900,
                99800,
                "COP",
                "Pendiente",
                None,
                None,
                json.dumps(detail),
                now,
                now,
            ),
        )
        order = self.self_service.get_order(self.con, "USR-A", self.order_id)
        intent = self.payments.create_intent(
            self.con,
            order,
            "USR-A",
            "sandbox_card",
            "m353-payment-key",
        )
        self.intent_id = intent["id"]
        self.payments.simulate(self.con, self.intent_id, "approved", "USR-A")
        self.self_service.attach_case(self.con, "USR-A", self.order_id, self.case_id, trace_context=True)
        self.link_id = "CCL-M353A001"
        self.con.execute(
            """INSERT INTO m35_commerce_case_links(
                 id,user_id,product_code,service_level,order_id,payment_intent_id,case_id,state,
                 checkout_consent_at,case_consent_at,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.link_id,
                "USR-A",
                "CO-CD-003",
                "solucion_revisada",
                self.order_id,
                self.intent_id,
                self.case_id,
                "CASE_CREATED",
                now,
                now,
                now,
                now,
            ),
        )
        self.con.execute(
            "INSERT INTO documents(id,case_id,kind) VALUES('DOC-M353-1',?,'generated')",
            (self.case_id,),
        )
        self.con.execute(
            """INSERT INTO m24_case_journey(
                 case_id,product_code,current_state,legal_approver_id,qa_approver_id,delivery_actor_id,created_at,updated_at
               ) VALUES(?,?, 'GENERADO',NULL,NULL,NULL,?,?)""",
            (self.case_id, "CO-CD-003", now, now),
        )
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def assert_code(self, expected, fn):
        with self.assertRaises(CaseActivationError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)
        return ctx.exception

    def test_active_read_model_cross_checks_purchase_case_documents_and_journey(self):
        result = self.center.build(self.con, "USR-A", self.case_id)
        self.assertEqual(result["activation_status"], "ACTIVE")
        self.assertEqual(result["case"]["id"], self.case_id)
        self.assertEqual(result["purchase_confirmation"]["order_id"], self.order_id)
        self.assertEqual(result["purchase_confirmation"]["payment_intent_id"], self.intent_id)
        self.assertTrue(result["purchase_confirmation"]["payment_verified"])
        self.assertGreaterEqual(result["purchase_confirmation"]["verified_event_count"], 2)
        self.assertTrue(result["purchase_confirmation"]["receipt_number"].startswith("RCPT-SBX-"))
        self.assertEqual(result["purchase_confirmation"]["amount"], 99800)
        self.assertEqual(result["purchase_confirmation"]["currency"], "COP")
        self.assertTrue(result["purchase_confirmation"]["review_included"])
        self.assertEqual(result["documents"], {"count": 1, "ready": True})
        self.assertEqual(result["journey"]["current_state"], "GENERADO")
        self.assertEqual(result["next_step"]["code"], "WAIT_FOR_REVIEW")
        self.assertFalse(result["purchase_confirmation"]["real_charge"])

    def test_public_model_does_not_expose_story_answers_handoffs_hashes_or_payment_signatures(self):
        raw = json.dumps(self.center.build(self.con, "USR-A", self.case_id), ensure_ascii=False)
        for forbidden in (
            "private_answer",
            "never expose",
            "handoff_id",
            "draft_id",
            "intake_id",
            "decision_id",
            "snapshot_sha256",
            "provider_reference",
            "signature",
            "payload_json",
            "idempotency_key",
            "user_id",
        ):
            self.assertNotIn(forbidden, raw)

    def test_other_user_gets_not_found_without_cross_tenant_disclosure(self):
        exc = self.assert_code("CASE_NOT_FOUND", lambda: self.center.build(self.con, "USR-B", self.case_id))
        self.assertEqual(exc.status, 404)

    def test_legacy_case_without_m35_link_is_not_presented_as_purchase_confirmation(self):
        self.con.execute(
            """INSERT INTO cases(id,product_code,title,risk,status,owner_id,review_status,created_at,updated_at,answers,result)
               VALUES('LZ-LEGACY','CO-CD-003','Legacy','green','Expediente abierto','USR-A','Pendiente','x','x','{}','{}')"""
        )
        exc = self.assert_code("NOT_M35_COMMERCE_CASE", lambda: self.center.build(self.con, "USR-A", "LZ-LEGACY"))
        self.assertEqual(exc.status, 404)

    def test_tampered_signed_payment_event_blocks_positive_activation(self):
        self.con.execute(
            "UPDATE payment_sandbox_events SET signature='tampered' WHERE intent_id=? LIMIT 1",
            (self.intent_id,),
        )
        self.assert_code("PAYMENT_EVENT_INTEGRITY_FAILED", lambda: self.center.build(self.con, "USR-A", self.case_id))

    def test_invalid_sandbox_receipt_blocks_positive_activation(self):
        self.con.execute(
            "UPDATE checkout_orders SET receipt_number='RCPT-LEGACY-123' WHERE id=?",
            (self.order_id,),
        )
        self.assert_code("SANDBOX_RECEIPT_MISSING", lambda: self.center.build(self.con, "USR-A", self.case_id))

    def test_case_created_without_documents_fails_closed(self):
        self.con.execute("DELETE FROM documents WHERE case_id=?", (self.case_id,))
        self.assert_code("DOCUMENT_TRACE_BROKEN", lambda: self.center.build(self.con, "USR-A", self.case_id))

    def test_case_created_without_m24_journey_fails_closed(self):
        self.con.execute("DELETE FROM m24_case_journey WHERE case_id=?", (self.case_id,))
        self.assert_code("JOURNEY_TRACE_MISSING", lambda: self.center.build(self.con, "USR-A", self.case_id))

    def test_unreconciled_journey_fails_closed(self):
        self.con.execute("UPDATE m24_case_journey SET current_state='INICIADO' WHERE case_id=?", (self.case_id,))
        self.assert_code("JOURNEY_NOT_RECONCILED", lambda: self.center.build(self.con, "USR-A", self.case_id))

    def test_pending_materialization_is_visible_but_never_called_active(self):
        self.con.execute(
            "UPDATE m35_commerce_case_links SET state='CASE_CREATED_DOCUMENTS_PENDING' WHERE id=?",
            (self.link_id,),
        )
        self.con.execute("DELETE FROM documents WHERE case_id=?", (self.case_id,))
        self.con.execute("DELETE FROM m24_case_journey WHERE case_id=?", (self.case_id,))
        result = self.center.build(self.con, "USR-A", self.case_id)
        self.assertEqual(result["activation_status"], "DOCUMENTS_PENDING")
        self.assertFalse(result["documents"]["ready"])
        self.assertEqual(result["next_step"]["code"], "RETRY_DOCUMENT_PREPARATION")
        self.assertEqual(result["next_step"]["route"], f"/checkout/{self.order_id}")

    def test_order_case_mismatch_is_detected(self):
        self.con.execute("UPDATE checkout_orders SET case_id=NULL WHERE id=?", (self.order_id,))
        self.assert_code("ORDER_CASE_MISMATCH", lambda: self.center.build(self.con, "USR-A", self.case_id))


if __name__ == "__main__":
    unittest.main()
