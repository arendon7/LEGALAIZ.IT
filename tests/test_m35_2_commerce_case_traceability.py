import json
import sqlite3
import unittest

import core_v11 as core
from payment_sandbox_backend import PaymentSandboxCenter
from self_service_backend import SelfServiceCenter
from legalai_platform.commerce_case_m35_2 import CommerceCaseTraceabilityStore, CommerceTraceError


class MemoryCrypto:
    PREFIX = b"encrypted-m352:"

    def encrypt(self, raw: bytes, aad: bytes) -> bytes:
        return self.PREFIX + len(aad).to_bytes(2, "big") + aad + raw[::-1]

    def decrypt(self, encrypted: bytes):
        if not encrypted.startswith(self.PREFIX):
            raise ValueError("bad envelope")
        payload = encrypted[len(self.PREFIX):]
        aad_length = int.from_bytes(payload[:2], "big")
        aad = payload[2:2 + aad_length]
        return payload[2 + aad_length:][::-1], aad


class FakePortal:
    def __init__(self):
        self.price_auto = 19900
        self.price_review = 79900

    def product(self, code):
        if code != "CO-CD-003":
            return None
        return {
            "code": code,
            "title": "Reclamo de consumo",
            "price_auto": self.price_auto,
            "price_review": self.price_review,
            "documents": ["Reclamación"],
        }


class FakeJourney:
    def bootstrap_paid_generation(self, con, case_id, order, user):
        return {"current_state": "PAID_GENERATION", "case_id": case_id, "order_id": order["id"]}


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
          id TEXT PRIMARY KEY,product_code TEXT NOT NULL,title TEXT NOT NULL,risk TEXT NOT NULL,status TEXT NOT NULL,
          owner_id TEXT,specialist_id TEXT,review_status TEXT NOT NULL DEFAULT 'Pendiente',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          answers TEXT NOT NULL,result TEXT NOT NULL
        );
        CREATE TABLE case_tasks(
          id TEXT PRIMARY KEY,case_id TEXT,label TEXT,status TEXT,owner_role TEXT,position INTEGER,created_at TEXT,updated_at TEXT
        );
        CREATE TABLE activity(
          id INTEGER PRIMARY KEY AUTOINCREMENT,case_id TEXT,kind TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL
        );
        CREATE TABLE audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
        );
        """
    )
    con.executemany(
        "INSERT INTO users(id,role,active) VALUES(?,?,?)",
        [("USR-A", "client", 1), ("USR-B", "client", 1)],
    )
    return con


class M352CommerceCaseTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.con = memory_db()
        self.portal = FakePortal()
        self.self_service = SelfServiceCenter([{"code": "CO-CD-003", "title": "Reclamo de consumo"}], self.portal)
        self.payments = PaymentSandboxCenter(b"m35-2-test-signing-key")
        self.offer_price_auto = 19900
        self.offer_price_reviewed = 99800
        self.store = CommerceCaseTraceabilityStore(
            MemoryCrypto(),
            self.self_service,
            self.offer,
            self.payments,
            FakeJourney(),
        )
        self.store.create_schema(self.con)
        created = self.store.create(
            self.con,
            "Compré un producto defectuoso y ya confirmé la solución de consumo que deseo continuar.",
        )
        self.intake_id = created["id"]
        self.answers = {
            "request_mode": "Garantía legal",
            "purchase_date": "2026-08-20",
            "detail": "Producto defectuoso con falla confirmada y solicitud concreta de garantía.",
        }
        draft = self.self_service.save_draft(
            self.con,
            "USR-A",
            "CO-CD-003",
            self.answers,
            current_step=3,
            title="Caso de consumo trazable",
            result={"source": "m35_m34_handoff"},
        )
        self.draft_id = draft["id"]
        self.handoff_id = "HOF-M352-TEST"
        self.con.execute(
            """INSERT INTO m35_intake_handoffs(
                 id,intake_id,user_id,decision_id,product_code,draft_id,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?, 'FULFILLMENT_STARTED','2026-08-23T20:00:00+00:00','2026-08-23T20:00:00+00:00')""",
            (
                self.handoff_id,
                self.intake_id,
                "USR-A",
                "REC-M352-TEST",
                "CO-CD-003",
                self.draft_id,
            ),
        )
        self.con.commit()
        self.diagnosis = {
            "validation_errors": [],
            "risk": "green",
            "risk_label": "Verde",
            "review_required": False,
            "service_mode": "self_service",
            "documents_expected": ["Reclamación"],
            "triggered_rules": [],
        }
        self.original_diagnose = core.diagnose
        self.original_create_tasks = core.create_tasks
        core.diagnose = lambda code, answers, strict=False: dict(self.diagnosis)
        core.create_tasks = lambda con, case_id, result: None

    def tearDown(self):
        core.diagnose = self.original_diagnose
        core.create_tasks = self.original_create_tasks
        self.con.close()

    def offer(self, code):
        return {
            "product_code": code,
            "public_name": "Reclamo de consumo",
            "pricing_status": "sandbox_reference_not_commercially_approved",
            "pricing_notice": "Sandbox",
            "service_levels": [
                {
                    "id": "orientacion",
                    "label": "Orientación jurídica",
                    "price": 0,
                    "checkout_enabled": False,
                    "includes": [],
                },
                {
                    "id": "documento_personalizado",
                    "label": "Documento personalizado",
                    "price": self.offer_price_auto,
                    "checkout_enabled": True,
                    "includes": [],
                },
                {
                    "id": "solucion_revisada",
                    "label": "Solución revisada",
                    "price": self.offer_price_reviewed,
                    "checkout_enabled": True,
                    "includes": [],
                },
            ],
        }

    def create_order(self, key="order-key-1", level="documento_personalizado", consent=True):
        return self.store.create_linked_order(
            self.con,
            "USR-A",
            "CO-CD-003",
            level,
            key,
            consent,
        )

    def create_and_approve_payment(self, order_result=None, payment_key="payment-key-1"):
        order_result = order_result or self.create_order()
        linked = self.store.create_linked_payment_intent(
            self.con,
            "USR-A",
            order_result["link_id"],
            "sandbox_card",
            payment_key,
        )
        intent = linked["payment_intent"]
        self.payments.simulate(self.con, intent["id"], "approved", "USR-A")
        return order_result, intent

    def test_checkout_requires_explicit_consent_and_complete_fulfillment(self):
        with self.assertRaisesRegex(CommerceTraceError, "checkout sandbox"):
            self.create_order(consent=False)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 0)
        self.diagnosis["validation_errors"] = [{"field": "supplier", "message": "Falta proveedor"}]
        with self.assertRaises(CommerceTraceError) as ctx:
            self.create_order(key="order-incomplete")
        self.assertEqual(ctx.exception.code, "FULFILLMENT_INCOMPLETE")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 0)

    def test_generic_checkout_and_legacy_payment_are_blocked_for_active_handoff(self):
        with self.assertRaisesRegex(ValueError, "checkout trazable M35.2"):
            self.self_service.create_order(
                self.con,
                "USR-A",
                "CO-CD-003",
                self.diagnosis,
                service_level="documento_personalizado",
            )
        linked = self.create_order()
        with self.assertRaisesRegex(ValueError, "pago sandbox trazable M35.2"):
            self.self_service.pay_order(self.con, "USR-A", linked["order_id"], "Tarjeta de prueba")
        order = self.self_service.get_order(self.con, "USR-A", linked["order_id"])
        self.assertEqual(order["status"], "Pendiente")
        self.assertTrue(order["detail"]["commerce_trace_required"])

    def test_unlinked_direct_checkout_remains_compatible(self):
        direct = self.self_service.create_order(
            self.con,
            "USR-B",
            "CO-CD-003",
            self.diagnosis,
            service_level="documento_personalizado",
        )
        self.assertEqual(direct["status"], "Pendiente")
        self.assertFalse(direct["detail"]["commerce_trace_required"])

    def test_order_is_idempotent_and_parallel_checkout_is_blocked(self):
        first = self.create_order()
        repeated = self.create_order()
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(first["order_id"], repeated["order_id"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 1)
        self.self_service.save_draft(
            self.con,
            "USR-A",
            "CO-CD-003",
            {**self.answers, "detail": "Texto corregido después del checkout con suficiente extensión."},
            current_step=3,
            title="Caso de consumo trazable",
            result={},
        )
        with self.assertRaises(CommerceTraceError) as ctx:
            self.create_order(key="different-key")
        self.assertEqual(ctx.exception.code, "ACTIVE_CHECKOUT_EXISTS")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 1)

    def test_checkout_can_be_invalidated_before_payment_then_recreated(self):
        first = self.create_order()
        invalidated = self.store.invalidate_checkout(self.con, "USR-A", first["link_id"])
        self.assertEqual(invalidated["state"], "INVALIDATED")
        order = self.self_service.get_order(self.con, "USR-A", first["order_id"])
        self.assertEqual(order["status"], "Cancelada (M35.2)")
        status = self.con.execute("SELECT status FROM m35_intake_handoffs WHERE id=?", (self.handoff_id,)).fetchone()[0]
        self.assertEqual(status, "FULFILLMENT_STARTED")
        second = self.create_order(key="order-key-2")
        self.assertNotEqual(first["order_id"], second["order_id"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 2)

    def test_checkout_cannot_be_invalidated_after_payment_intent_exists(self):
        order = self.create_order()
        self.store.create_linked_payment_intent(self.con, "USR-A", order["link_id"], "sandbox_card", "pay-lock")
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.invalidate_checkout(self.con, "USR-A", order["link_id"])
        self.assertEqual(ctx.exception.code, "PAYMENT_INTENT_ALREADY_CREATED")

    def test_red_or_blocked_result_forces_reviewed_service(self):
        self.diagnosis.update({"risk": "red", "risk_label": "Rojo", "review_required": True, "service_mode": "blocked"})
        with self.assertRaises(CommerceTraceError) as ctx:
            self.create_order()
        self.assertEqual(ctx.exception.code, "REVIEW_REQUIRED")
        reviewed = self.create_order(key="reviewed-key", level="solucion_revisada")
        order = self.self_service.get_order(self.con, "USR-A", reviewed["order_id"])
        self.assertEqual(order["total"], 99800)
        self.assertTrue(order["review_selected"])

    def test_order_snapshot_tampering_blocks_payment_intent(self):
        linked = self.create_order()
        self.con.execute("UPDATE checkout_orders SET total=total+1 WHERE id=?", (linked["order_id"],))
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.create_linked_payment_intent(self.con, "USR-A", linked["link_id"], "sandbox_card", "payment-tamper")
        self.assertEqual(ctx.exception.code, "ORDER_TRACE_BROKEN")

    def test_payment_intent_is_idempotent_and_cross_user_access_is_denied(self):
        linked = self.create_order()
        first = self.store.create_linked_payment_intent(self.con, "USR-A", linked["link_id"], "sandbox_card", "payment-key")
        second = self.store.create_linked_payment_intent(self.con, "USR-A", linked["link_id"], "sandbox_card", "payment-key")
        self.assertEqual(first["payment_intent"]["id"], second["payment_intent"]["id"])
        self.assertTrue(second["idempotent"])
        self.assertIsNone(self.store.link_by_order(self.con, "USR-B", linked["order_id"]))
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.create_linked_payment_intent(self.con, "USR-B", linked["link_id"], "sandbox_card", "other-user")
        self.assertEqual(ctx.exception.code, "COMMERCE_LINK_NOT_FOUND")

    def test_legacy_simulated_payment_is_not_sufficient_for_m352_finalize(self):
        linked = self.create_order()
        self.con.execute(
            "UPDATE checkout_orders SET status='Pagado (simulado)',payment_method='Tarjeta de prueba' WHERE id=?",
            (linked["order_id"],),
        )
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertEqual(ctx.exception.code, "PAYMENT_INTENT_REQUIRED")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)

    def test_tampered_payment_event_blocks_case_creation(self):
        linked, intent = self.create_and_approve_payment()
        event = self.con.execute(
            "SELECT id FROM payment_sandbox_events WHERE intent_id=? ORDER BY created_at LIMIT 1",
            (intent["id"],),
        ).fetchone()
        self.con.execute("UPDATE payment_sandbox_events SET payload_json='{}' WHERE id=?", (event["id"],))
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertEqual(ctx.exception.code, "PAYMENT_EVENT_INTEGRITY_FAILED")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)

    def test_draft_change_after_checkout_blocks_finalization(self):
        linked, _ = self.create_and_approve_payment()
        self.self_service.save_draft(
            self.con,
            "USR-A",
            "CO-CD-003",
            {**self.answers, "detail": "Una modificación material posterior al checkout cambia el snapshot."},
            current_step=3,
            title="Caso de consumo trazable",
            result={},
        )
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertEqual(ctx.exception.code, "DRAFT_CHANGED_AFTER_CHECKOUT")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)

    def test_price_or_legal_result_change_after_checkout_blocks_finalization(self):
        linked, _ = self.create_and_approve_payment()
        self.offer_price_auto = 20900
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertEqual(ctx.exception.code, "PRICE_CHANGED_AFTER_CHECKOUT")
        self.offer_price_auto = 19900
        self.diagnosis.update({"risk": "yellow", "risk_label": "Amarillo"})
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertEqual(ctx.exception.code, "LEGAL_RESULT_CHANGED")

    def test_case_requires_explicit_consent(self):
        linked, _ = self.create_and_approve_payment()
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], False)
        self.assertEqual(ctx.exception.code, "CASE_CONSENT_REQUIRED")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)

    def test_successful_finalize_creates_exactly_one_case_and_is_idempotent(self):
        linked, _ = self.create_and_approve_payment()
        first = self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertFalse(first["idempotent"])
        self.assertTrue(first["payment_verified"])
        self.assertEqual(first["state"], "CASE_CREATED_DOCUMENTS_PENDING")
        case = self.con.execute("SELECT * FROM cases WHERE id=?", (first["case_id"],)).fetchone()
        self.assertIsNotNone(case)
        self.assertEqual(json.loads(case["answers"]), self.answers)
        self.assertEqual(case["owner_id"], "USR-A")
        order = self.self_service.get_order(self.con, "USR-A", linked["order_id"])
        self.assertEqual(order["status"], "Completada")
        self.assertEqual(order["case_id"], first["case_id"])
        self.assertIsNone(self.self_service.get_draft(self.con, "USR-A", self.draft_id))
        handoff = self.con.execute("SELECT status FROM m35_intake_handoffs WHERE id=?", (self.handoff_id,)).fetchone()
        self.assertEqual(handoff["status"], "CASE_CREATED")
        second = self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["case_id"], first["case_id"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 1)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM checkout_orders").fetchone()[0], 1)

    def test_materialization_only_closes_the_exact_case_link(self):
        linked, _ = self.create_and_approve_payment()
        created = self.store.finalize_case_record(self.con, {"id": "USR-A", "role": "client"}, linked["link_id"], True)
        with self.assertRaises(CommerceTraceError) as ctx:
            self.store.mark_materialized(self.con, "USR-A", linked["link_id"], "LZ-WRONG", 1, {})
        self.assertEqual(ctx.exception.code, "CASE_TRACE_BROKEN")
        final = self.store.mark_materialized(self.con, "USR-A", linked["link_id"], created["case_id"], 2, {"ready": True})
        self.assertEqual(final["state"], "CASE_CREATED")

    def test_ledger_does_not_duplicate_story_or_answers(self):
        self.create_order()
        row = dict(self.con.execute("SELECT * FROM m35_commerce_case_links").fetchone())
        serialized = json.dumps(row, ensure_ascii=False)
        self.assertNotIn("producto defectuoso", serialized.lower())
        self.assertNotIn("Garantía legal", serialized)
        self.assertNotIn("request_mode", serialized)
        self.assertIn("draft_snapshot_sha256", row)
        self.assertEqual(len(row["draft_snapshot_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
