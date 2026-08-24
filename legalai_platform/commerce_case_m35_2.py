from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping
import uuid

import core_v11 as core
from legalai_platform.fulfillment_bridge_m35_1 import FulfillmentContextStore, utc_iso


SCHEMA_VERSION = "35.2.0"
PAID_ORDER_STATUSES = {"Pagado (sandbox)"}
ALLOWED_SERVICE_LEVELS = {"documento_personalizado", "solucion_revisada"}


class CommerceTraceError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class PaymentVerification:
    ok: bool
    checked_events: int
    intent_id: str


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _decode_json(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


class CommerceCaseTraceabilityStore(FulfillmentContextStore):
    """Puente fail-closed entre fulfillment, checkout sandbox, pago y expediente.

    La tabla M35.2 contiene sólo identificadores internos, estados y hashes de
    integridad. No duplica el relato M34 ni las respuestas del formulario.
    """

    def __init__(self, crypto, self_service, offer_provider, payments, case_journey, retention_hours: int = 72):
        super().__init__(crypto, self_service, offer_provider, retention_hours=retention_hours)
        self.payments = payments
        self.case_journey = case_journey

    def create_schema(self, con):
        super().create_schema(con)
        self.self_service.create_schema(con)
        self.payments.create_schema(con)
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m35_commerce_case_links(
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              handoff_id TEXT NOT NULL,
              intake_id TEXT NOT NULL,
              decision_id TEXT NOT NULL,
              draft_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              service_level TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              draft_snapshot_sha256 TEXT NOT NULL,
              order_snapshot_sha256 TEXT NOT NULL,
              order_id TEXT NOT NULL UNIQUE,
              payment_intent_id TEXT,
              case_id TEXT UNIQUE,
              state TEXT NOT NULL,
              checkout_consent_at TEXT NOT NULL,
              case_consent_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(user_id,idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_m35_commerce_user_product
              ON m35_commerce_case_links(user_id,product_code,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_m35_commerce_order
              ON m35_commerce_case_links(order_id);
            """
        )

    @staticmethod
    def _draft_snapshot(draft: Mapping[str, Any]) -> str:
        return _canonical_sha256(
            {
                "draft_id": draft.get("id"),
                "product_code": draft.get("product_code"),
                "title": draft.get("title"),
                "current_step": int(draft.get("current_step") or 0),
                "answers": draft.get("answers") or {},
            }
        )

    @staticmethod
    def _order_snapshot(order: Mapping[str, Any]) -> str:
        return _canonical_sha256(
            {
                "order_id": order.get("id"),
                "user_id": order.get("user_id"),
                "product_code": order.get("product_code"),
                "service_mode": order.get("service_mode"),
                "review_selected": bool(order.get("review_selected")),
                "document_price": int(order.get("document_price") or 0),
                "review_price": int(order.get("review_price") or 0),
                "total": int(order.get("total") or 0),
                "currency": order.get("currency") or "COP",
            }
        )

    @staticmethod
    def _public_link(row: Mapping[str, Any], order: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "link_id": row["id"],
            "product_code": row["product_code"],
            "service_level": row["service_level"],
            "order_id": row["order_id"],
            "payment_intent_id": row.get("payment_intent_id") if isinstance(row, dict) else row["payment_intent_id"],
            "case_id": row.get("case_id") if isinstance(row, dict) else row["case_id"],
            "state": row["state"],
            "schema_version": SCHEMA_VERSION,
        }
        if order:
            payload["order_status"] = order.get("status")
            payload["total"] = int(order.get("total") or 0)
            payload["currency"] = order.get("currency") or "COP"
        return payload

    def context_for_product(self, con, user_id: str, product_code: str) -> dict[str, Any]:
        self.create_schema(con)
        code = str(product_code or "").upper().strip()
        handoff = self._owned_handoff(con, user_id, code)
        if not handoff:
            return {"linked": False, "product_code": code, "schema_version": SCHEMA_VERSION}
        row = con.execute(
            """SELECT * FROM m35_commerce_case_links
               WHERE user_id=? AND handoff_id=? ORDER BY created_at DESC LIMIT 1""",
            (user_id, handoff["id"]),
        ).fetchone()
        payload = {
            "linked": True,
            "product_code": code,
            "handoff_state": handoff["status"],
            "draft_id": handoff["draft_id"],
            "schema_version": SCHEMA_VERSION,
        }
        if row:
            order = self.self_service.get_order(con, user_id, row["order_id"])
            payload["commerce"] = self._public_link(dict(row), order)
        return payload

    def link_by_order(self, con, user_id: str, order_id: str) -> dict[str, Any] | None:
        self.create_schema(con)
        row = con.execute(
            "SELECT * FROM m35_commerce_case_links WHERE user_id=? AND order_id=?",
            (user_id, str(order_id or "")),
        ).fetchone()
        if not row:
            return None
        order = self.self_service.get_order(con, user_id, row["order_id"])
        return self._public_link(dict(row), order)

    def _offer_level(self, product_code: str, service_level: str) -> dict[str, Any]:
        offer = self._public_offer(self.offer_provider(product_code))
        level = next((row for row in offer.get("service_levels", []) if row.get("id") == service_level), None)
        if not level or not level.get("checkout_enabled"):
            raise CommerceTraceError("SERVICE_LEVEL_NOT_CHECKOUTABLE", "El nivel de servicio no está disponible para checkout.", 422)
        return level

    @staticmethod
    def _validate_idempotency(value: Any) -> str:
        key = str(value or "").strip()
        if not key or len(key) > 120:
            raise CommerceTraceError("IDEMPOTENCY_KEY_REQUIRED", "Se requiere una clave de idempotencia válida.", 400)
        return key

    def create_linked_order(
        self,
        con,
        user_id: str,
        product_code: str,
        service_level: str,
        idempotency_key: str,
        checkout_consent: bool,
    ) -> dict[str, Any]:
        self.create_schema(con)
        if not checkout_consent:
            raise CommerceTraceError("CHECKOUT_CONSENT_REQUIRED", "Confirma que deseas continuar al checkout sandbox.", 400)
        code = str(product_code or "").upper().strip()
        level_id = str(service_level or "").strip().lower()
        if level_id not in ALLOWED_SERVICE_LEVELS:
            raise CommerceTraceError("INVALID_SERVICE_LEVEL", "Nivel de servicio inválido.", 422)
        idem = self._validate_idempotency(idempotency_key)

        existing = con.execute(
            "SELECT * FROM m35_commerce_case_links WHERE user_id=? AND idempotency_key=?",
            (user_id, idem),
        ).fetchone()
        if existing:
            row = dict(existing)
            if row["product_code"] != code or row["service_level"] != level_id:
                raise CommerceTraceError("IDEMPOTENCY_CONFLICT", "La clave de idempotencia ya fue usada con otro checkout.", 409)
            order = self.self_service.get_order(con, user_id, row["order_id"])
            if not order:
                raise CommerceTraceError("ORDER_TRACE_BROKEN", "La orden vinculada ya no está disponible.", 409)
            return {"idempotent": True, **self._public_link(row, order)}

        handoff = self._owned_handoff(con, user_id, code)
        if not handoff:
            raise CommerceTraceError("NO_TRANSFERRED_INTAKE", "No existe un diagnóstico transferido para esta solución.", 404)
        if handoff["status"] == "CASE_CREATED":
            raise CommerceTraceError("CASE_ALREADY_CREATED", "Este diagnóstico ya fue convertido en expediente.", 409)
        if handoff["status"] not in {"FULFILLMENT_STARTED", "CHECKOUT_STARTED"}:
            raise CommerceTraceError("FULFILLMENT_NOT_READY", "Completa primero la continuidad del formulario antes del checkout.", 409)

        draft = self.self_service.get_draft(con, user_id, handoff["draft_id"])
        if not draft or draft.get("product_code") != code:
            raise CommerceTraceError("DRAFT_NOT_AVAILABLE", "El borrador vinculado no está disponible.", 409)
        answers = draft.get("answers") or {}
        result = core.diagnose(code, answers, strict=True)
        if result.get("validation_errors"):
            raise CommerceTraceError("FULFILLMENT_INCOMPLETE", "Aún faltan datos obligatorios antes del checkout.", 422)

        forced_review = bool(
            result.get("risk") == "red"
            or result.get("review_required")
            or result.get("service_mode") == "blocked"
        )
        if forced_review and level_id != "solucion_revisada":
            raise CommerceTraceError("REVIEW_REQUIRED", "El nivel de riesgo exige solución revisada.", 409)
        level = self._offer_level(code, level_id)
        review_selected = level_id == "solucion_revisada"
        order = self.self_service.create_order(
            con,
            user_id,
            code,
            {**result, "service_level": level_id},
            review_selected=review_selected,
            service_level=level_id,
        )
        if int(order.get("total") or 0) != int(level.get("price") or 0) or (order.get("currency") or "COP") != "COP":
            raise CommerceTraceError("PRICE_SNAPSHOT_MISMATCH", "La orden no coincide con el precio canónico del nivel seleccionado.", 409)

        link_id = "CCL-" + uuid.uuid4().hex[:14].upper()
        now = utc_iso()
        con.execute(
            """INSERT INTO m35_commerce_case_links(
                 id,user_id,handoff_id,intake_id,decision_id,draft_id,product_code,service_level,
                 idempotency_key,draft_snapshot_sha256,order_snapshot_sha256,order_id,payment_intent_id,
                 case_id,state,checkout_consent_at,case_consent_at,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,'ORDER_CREATED',?,NULL,?,?)""",
            (
                link_id,
                user_id,
                handoff["id"],
                handoff["intake_id"],
                handoff["decision_id"],
                handoff["draft_id"],
                code,
                level_id,
                idem,
                self._draft_snapshot(draft),
                self._order_snapshot(order),
                order["id"],
                now,
                now,
                now,
            ),
        )
        con.execute("UPDATE m35_intake_handoffs SET status='CHECKOUT_STARTED',updated_at=? WHERE id=?", (now, handoff["id"]))
        core.audit(
            con,
            user_id,
            "m35_commerce_link",
            link_id,
            "order_created",
            {"order_id": order["id"], "product_code": code, "service_level": level_id, "total": order["total"]},
        )
        row = dict(con.execute("SELECT * FROM m35_commerce_case_links WHERE id=?", (link_id,)).fetchone())
        return {"idempotent": False, **self._public_link(row, order)}

    def _owned_link(self, con, user_id: str, link_id: str) -> dict[str, Any]:
        row = con.execute(
            "SELECT * FROM m35_commerce_case_links WHERE id=? AND user_id=?",
            (str(link_id or ""), user_id),
        ).fetchone()
        if not row:
            raise CommerceTraceError("COMMERCE_LINK_NOT_FOUND", "No encontramos el checkout vinculado.", 404)
        return dict(row)

    def create_linked_payment_intent(
        self,
        con,
        user_id: str,
        link_id: str,
        provider: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self.create_schema(con)
        row = self._owned_link(con, user_id, link_id)
        if row.get("case_id"):
            raise CommerceTraceError("CASE_ALREADY_CREATED", "La orden ya fue convertida en expediente.", 409)
        order = self.self_service.get_order(con, user_id, row["order_id"])
        if not order or self._order_snapshot(order) != row["order_snapshot_sha256"]:
            raise CommerceTraceError("ORDER_TRACE_BROKEN", "La orden ya no coincide con el snapshot certificado.", 409)
        idem = self._validate_idempotency(idempotency_key)

        current_id = row.get("payment_intent_id")
        if current_id:
            current = self.payments.intent(con, current_id)
            if current and current.get("status") in {"created", "processing", "succeeded"}:
                return {"link_id": row["id"], "payment_intent": current, "idempotent": True}

        intent = self.payments.create_intent(con, order, user_id, provider, idem)
        if intent.get("order_id") != order["id"] or int(intent.get("amount") or -1) != int(order["total"]):
            raise CommerceTraceError("PAYMENT_INTENT_MISMATCH", "El intento de pago no coincide con la orden vinculada.", 409)
        now = utc_iso()
        con.execute(
            "UPDATE m35_commerce_case_links SET payment_intent_id=?,state='PAYMENT_CREATED',updated_at=? WHERE id=?",
            (intent["id"], now, row["id"]),
        )
        core.audit(
            con,
            user_id,
            "m35_commerce_link",
            row["id"],
            "payment_intent_created",
            {"order_id": order["id"], "payment_intent_id": intent["id"], "provider": provider},
        )
        return {"link_id": row["id"], "payment_intent": intent, "idempotent": False}

    def verify_payment(self, con, user_id: str, row: Mapping[str, Any], order: Mapping[str, Any]) -> PaymentVerification:
        intent_id = str(row.get("payment_intent_id") or "")
        if not intent_id:
            raise CommerceTraceError("PAYMENT_INTENT_REQUIRED", "El checkout vinculado no tiene un intento de pago verificable.", 409)
        intent = self.payments.intent(con, intent_id)
        if not intent:
            raise CommerceTraceError("PAYMENT_INTENT_NOT_FOUND", "El intento de pago ya no está disponible.", 409)
        if intent.get("user_id") != user_id or intent.get("order_id") != order.get("id"):
            raise CommerceTraceError("PAYMENT_TRACE_BROKEN", "El pago no pertenece a la orden vinculada.", 409)
        if intent.get("status") != "succeeded" or order.get("status") not in PAID_ORDER_STATUSES:
            raise CommerceTraceError("PAYMENT_NOT_CONFIRMED", "El pago sandbox todavía no está confirmado.", 409)
        if int(intent.get("amount") or -1) != int(order.get("total") or 0) or (intent.get("currency") or "COP") != (order.get("currency") or "COP"):
            raise CommerceTraceError("PAYMENT_AMOUNT_MISMATCH", "El importe del pago no coincide con la orden.", 409)
        verified = self.payments.verify_events(con, intent_id)
        if verified.get("errors") or int(verified.get("checked") or 0) < 2 or verified.get("valid") != verified.get("checked"):
            raise CommerceTraceError("PAYMENT_EVENT_INTEGRITY_FAILED", "No fue posible verificar íntegramente los eventos del pago sandbox.", 409)
        return PaymentVerification(True, int(verified["checked"]), intent_id)

    def finalize_case_record(self, con, user: Mapping[str, Any], link_id: str, case_consent: bool) -> dict[str, Any]:
        self.create_schema(con)
        user_id = str(user.get("id") or "")
        if not case_consent:
            raise CommerceTraceError("CASE_CONSENT_REQUIRED", "Confirma que deseas crear el expediente con la información validada.", 400)
        row = self._owned_link(con, user_id, link_id)
        if row.get("case_id"):
            order = self.self_service.get_order(con, user_id, row["order_id"])
            return {"idempotent": True, **self._public_link(row, order)}

        order = self.self_service.get_order(con, user_id, row["order_id"])
        if not order or self._order_snapshot(order) != row["order_snapshot_sha256"]:
            raise CommerceTraceError("ORDER_TRACE_BROKEN", "La orden ya no coincide con el snapshot certificado.", 409)
        self.verify_payment(con, user_id, row, order)

        draft = self.self_service.get_draft(con, user_id, row["draft_id"])
        if not draft or draft.get("product_code") != row["product_code"]:
            raise CommerceTraceError("DRAFT_NOT_AVAILABLE", "El borrador vinculado no está disponible.", 409)
        if self._draft_snapshot(draft) != row["draft_snapshot_sha256"]:
            raise CommerceTraceError(
                "DRAFT_CHANGED_AFTER_CHECKOUT",
                "El formulario cambió después del checkout. Reconfirma el nivel de servicio antes de crear el expediente.",
                409,
            )

        level = self._offer_level(row["product_code"], row["service_level"])
        if int(level.get("price") or 0) != int(order.get("total") or 0):
            raise CommerceTraceError("PRICE_CHANGED_AFTER_CHECKOUT", "El precio canónico cambió después del checkout; genera una nueva orden.", 409)

        answers = draft.get("answers") or {}
        result = core.diagnose(row["product_code"], answers, strict=True)
        if result.get("validation_errors"):
            raise CommerceTraceError("FULFILLMENT_NO_LONGER_VALID", "La información dejó de cumplir los requisitos de generación.", 409)
        order_risk = (order.get("detail") or {}).get("risk")
        if order_risk and order_risk != result.get("risk"):
            raise CommerceTraceError("LEGAL_RESULT_CHANGED", "El resultado jurídico cambió después del checkout; se requiere una nueva confirmación.", 409)

        product = core.product(row["product_code"])
        if not product:
            raise CommerceTraceError("PRODUCT_NOT_FOUND", "Producto no encontrado.", 404)
        case_id = "LZ-" + uuid.uuid4().hex[:8].upper()
        timestamp = core.now()
        status = "Requiere especialista" if result.get("risk") == "red" else "Expediente abierto"
        con.execute(
            """INSERT INTO cases(
                 id,product_code,title,risk,status,owner_id,specialist_id,review_status,
                 created_at,updated_at,answers,result
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                case_id,
                row["product_code"],
                draft.get("title") or product.get("title") or row["product_code"],
                result.get("risk") or "yellow",
                status,
                user_id,
                None,
                "Pendiente",
                timestamp,
                timestamp,
                json.dumps(answers, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        core.create_tasks(con, case_id, result)
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "case", f"Caso creado desde checkout M35.2 con semáforo {result.get('risk_label') or result.get('risk') or 'por revisar'}.", timestamp),
        )
        core.audit(
            con,
            user_id,
            "case",
            case_id,
            "create_from_m35_commerce",
            {"order_id": order["id"], "commerce_link_id": row["id"], "risk": result.get("risk")},
        )
        completed_order = self.self_service.attach_case(con, user_id, order["id"], case_id)
        journey = self.case_journey.bootstrap_paid_generation(con, case_id, completed_order, user)
        con.execute("DELETE FROM service_drafts WHERE id=? AND user_id=?", (row["draft_id"], user_id))
        now = utc_iso()
        con.execute(
            """UPDATE m35_commerce_case_links
               SET case_id=?,state='CASE_CREATED_DOCUMENTS_PENDING',case_consent_at=?,updated_at=?
               WHERE id=?""",
            (case_id, now, now, row["id"]),
        )
        con.execute("UPDATE m35_intake_handoffs SET status='CASE_CREATED',updated_at=? WHERE id=?", (now, row["handoff_id"]))
        core.audit(
            con,
            user_id,
            "m35_commerce_link",
            row["id"],
            "case_created",
            {"case_id": case_id, "order_id": order["id"], "journey_state": journey.get("current_state")},
        )
        return {
            "idempotent": False,
            "link_id": row["id"],
            "order_id": order["id"],
            "case_id": case_id,
            "product_code": row["product_code"],
            "state": "CASE_CREATED_DOCUMENTS_PENDING",
            "journey_state": journey.get("current_state"),
            "payment_verified": True,
            "_answers": answers,
            "_result": result,
            "_title": draft.get("title") or product.get("title") or row["product_code"],
        }

    def mark_materialized(self, con, user_id: str, link_id: str, case_id: str, documents_count: int, delivery: Mapping[str, Any] | None) -> dict[str, Any]:
        self.create_schema(con)
        row = self._owned_link(con, user_id, link_id)
        if row.get("case_id") != case_id:
            raise CommerceTraceError("CASE_TRACE_BROKEN", "El expediente no coincide con el vínculo comercial.", 409)
        now = utc_iso()
        con.execute(
            "UPDATE m35_commerce_case_links SET state='CASE_CREATED',updated_at=? WHERE id=?",
            (now, row["id"]),
        )
        core.audit(
            con,
            user_id,
            "m35_commerce_link",
            row["id"],
            "documents_materialized",
            {"case_id": case_id, "documents": int(documents_count), "delivery_ready": bool(delivery)},
        )
        order = self.self_service.get_order(con, user_id, row["order_id"])
        return {"idempotent": False, **self._public_link({**row, "state": "CASE_CREATED"}, order)}


__all__ = [
    "ALLOWED_SERVICE_LEVELS",
    "CommerceCaseTraceabilityStore",
    "CommerceTraceError",
    "PaymentVerification",
    "SCHEMA_VERSION",
]
