from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json

import core_v11 as core
from legalai_platform.commerce_case_m35_2 import CommerceCaseTraceabilityStore, CommerceTraceError
from legalai_platform.runtime_registry import (
    DELIVERY,
    INFRA,
    M24_CASE_JOURNEY,
    M24_CLIENT_INTAKE,
    OBSERVABILITY,
    PAYMENTS,
    RATE_LIMITER,
    SELF_SERVICE,
)


PREFIX = "/api/m35/commerce"
ORDER_PATH = f"{PREFIX}/order"
PAYMENT_PATH = f"{PREFIX}/payment-intent"
INVALIDATE_PATH = f"{PREFIX}/invalidate"
FINALIZE_PATH = f"{PREFIX}/finalize"
CONTEXT_PREFIX = f"{PREFIX}/context/"
ORDER_LOOKUP_PREFIX = f"{PREFIX}/order/"


@lru_cache(maxsize=1)
def commerce_store() -> CommerceCaseTraceabilityStore:
    return CommerceCaseTraceabilityStore(
        INFRA.crypto,
        SELF_SERVICE,
        M24_CLIENT_INTAKE.offer,
        PAYMENTS,
        M24_CASE_JOURNEY,
    )


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _observe(event: str, **fields) -> None:
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _rate_limit(handler, user: dict, bucket: str, limit: int = 30, window: int = 300) -> bool:
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(f"m35-commerce:{bucket}:{user['id']}:{ip or 'unknown'}", limit, window)
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Has realizado varias operaciones seguidas. Intenta nuevamente más tarde.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _public_finalize(result: dict) -> tuple[dict, dict]:
    private = {
        "answers": result.pop("_answers", {}),
        "result": result.pop("_result", {}),
        "title": result.pop("_title", ""),
    }
    return result, private


def _json_object(value) -> dict:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _pending_case_snapshot(con, user_id: str, case_id: str, product_code: str) -> tuple[dict, int]:
    row = con.execute(
        "SELECT id,product_code,title,owner_id,answers,result FROM cases WHERE id=? AND owner_id=?",
        (case_id, user_id),
    ).fetchone()
    if not row or str(row["product_code"] or "") != product_code:
        raise CommerceTraceError("CASE_TRACE_BROKEN", "El expediente pendiente no coincide con el vínculo comercial.", 409)
    count = int(
        con.execute(
            "SELECT COUNT(*) FROM documents WHERE case_id=? AND kind!='audit'",
            (case_id,),
        ).fetchone()[0]
    )
    return {
        "answers": _json_object(row["answers"]),
        "result": _json_object(row["result"]),
        "title": str(row["title"] or product_code),
    }, count


def handle_m35_2_commerce_get(handler, path: str, user: dict) -> bool:
    if path.startswith(CONTEXT_PREFIX):
        if not _rate_limit(handler, user, "context", 60, 300):
            return True
        product_code = path[len(CONTEXT_PREFIX):].upper().strip()
        if not product_code:
            handler.send_json({"error": "Producto no indicado.", "code": "PRODUCT_REQUIRED"}, 400)
            return True
        con = core.db()
        try:
            result = commerce_store().context_for_product(con, user["id"], product_code)
        finally:
            con.close()
        handler.send_json(result, 200)
        return True

    if path.startswith(ORDER_LOOKUP_PREFIX):
        if not _rate_limit(handler, user, "order-read", 60, 300):
            return True
        order_id = path[len(ORDER_LOOKUP_PREFIX):].strip()
        if not order_id:
            handler.send_json({"error": "Orden no indicada.", "code": "ORDER_REQUIRED"}, 400)
            return True
        con = core.db()
        try:
            result = commerce_store().link_by_order(con, user["id"], order_id)
        finally:
            con.close()
        if not result:
            handler.send_json({"error": "La orden no pertenece a una continuidad M35.2.", "code": "COMMERCE_LINK_NOT_FOUND"}, 404)
            return True
        handler.send_json(result, 200)
        return True
    return False


def handle_m35_2_commerce_post(handler, path: str, user: dict) -> bool:
    if path not in {ORDER_PATH, PAYMENT_PATH, INVALIDATE_PATH, FINALIZE_PATH}:
        return False
    if not _rate_limit(handler, user, path.rsplit("/", 1)[-1], 20, 300):
        return True
    ip = _client_ip(handler)
    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise CommerceTraceError("INVALID_JSON", "La solicitud debe tener un formato válido.", 400)
        store = commerce_store()

        if path == ORDER_PATH:
            con = core.db()
            try:
                result = store.create_linked_order(
                    con,
                    user["id"],
                    data.get("product_code"),
                    data.get("service_level"),
                    data.get("idempotency_key"),
                    bool(data.get("checkout_consent")),
                )
                con.commit()
            finally:
                con.close()
            _observe(
                "m35_commerce_order_linked",
                link_id=result.get("link_id"),
                order_id=result.get("order_id"),
                product_code=result.get("product_code"),
                service_level=result.get("service_level"),
                idempotent=bool(result.get("idempotent")),
                user_id=user["id"],
                ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
            )
            handler.send_json(result, 200 if result.get("idempotent") else 201)
            return True

        if path == INVALIDATE_PATH:
            con = core.db()
            try:
                result = store.invalidate_checkout(con, user["id"], data.get("link_id"))
                con.commit()
            finally:
                con.close()
            _observe(
                "m35_commerce_checkout_invalidated",
                link_id=result.get("link_id"),
                order_id=result.get("order_id"),
                product_code=result.get("product_code"),
                idempotent=bool(result.get("idempotent")),
                user_id=user["id"],
            )
            handler.send_json(result, 200)
            return True

        if path == PAYMENT_PATH:
            con = core.db()
            try:
                result = store.create_linked_payment_intent(
                    con,
                    user["id"],
                    data.get("link_id"),
                    str(data.get("provider") or "sandbox_card"),
                    data.get("idempotency_key"),
                )
                con.commit()
            finally:
                con.close()
            intent = result.get("payment_intent") or {}
            public = {
                "link_id": result.get("link_id"),
                "idempotent": bool(result.get("idempotent")),
                "payment_intent": {
                    "id": intent.get("id"),
                    "order_id": intent.get("order_id"),
                    "provider": intent.get("provider"),
                    "provider_label": intent.get("provider_label"),
                    "amount": int(intent.get("amount") or 0),
                    "currency": intent.get("currency") or "COP",
                    "status": intent.get("status"),
                },
            }
            _observe(
                "m35_commerce_payment_intent_linked",
                link_id=result.get("link_id"),
                payment_intent_id=intent.get("id"),
                provider=intent.get("provider"),
                idempotent=bool(result.get("idempotent")),
                user_id=user["id"],
                ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
            )
            handler.send_json(public, 200 if result.get("idempotent") else 201)
            return True

        # FINALIZE phase A: commit verified commercial/case linkage. Document
        # generation and M24 reconciliation happen only after that durable state.
        con = core.db()
        try:
            raw = store.finalize_case_record(
                con,
                user,
                data.get("link_id"),
                bool(data.get("case_consent")),
            )
            public, private = _public_finalize(dict(raw))
            con.commit()
        finally:
            con.close()

        existing_documents = 0
        if public.get("idempotent"):
            if public.get("state") != "CASE_CREATED_DOCUMENTS_PENDING":
                handler.send_json({**public, "documents_ready": public.get("state") == "CASE_CREATED"}, 200)
                return True
            # A previous attempt already created the exact case. Resume from the
            # immutable case snapshot rather than creating another case or order.
            con = core.db()
            try:
                private, existing_documents = _pending_case_snapshot(
                    con,
                    user["id"],
                    public["case_id"],
                    public["product_code"],
                )
            finally:
                con.close()
            public["idempotent"] = False
            public["resumed"] = True

        case_id = public["case_id"]
        try:
            # If a previous attempt committed documents but failed during M24
            # reconciliation, reuse them. generate_case_documents is invoked only
            # when there is no materialized non-audit document for the case.
            if existing_documents < 1:
                con = core.db()
                try:
                    _, existing_documents = _pending_case_snapshot(
                        con,
                        user["id"],
                        case_id,
                        public["product_code"],
                    )
                finally:
                    con.close()
            if existing_documents < 1:
                documents = core.generate_case_documents(
                    case_id,
                    public["product_code"],
                    private["answers"],
                    private["result"],
                    actor=user["id"],
                    note="Generación inicial desde M35.2 — checkout sandbox trazable",
                )
                documents_count = len(documents or [])
            else:
                documents_count = existing_documents

            # FINALIZE phase C: documents already exist. Re-verify signed payment
            # evidence inside mark_materialized and only then reconcile M24 to GENERADO.
            con = core.db()
            try:
                delivery = DELIVERY.summary(con, case_id)
                finalized = store.mark_materialized(
                    con,
                    user["id"],
                    public["link_id"],
                    case_id,
                    documents_count,
                    delivery,
                )
                con.commit()
            finally:
                con.close()
            result = {
                **public,
                **finalized,
                "case_id": case_id,
                "documents_ready": True,
                "documents_count": documents_count,
                "document_delivery": delivery,
            }
            _observe(
                "m35_commerce_case_materialized",
                link_id=public.get("link_id"),
                order_id=public.get("order_id"),
                case_id=case_id,
                product_code=public.get("product_code"),
                documents_count=documents_count,
                resumed=bool(public.get("resumed")),
                user_id=user["id"],
            )
            handler.send_json(result, 200 if public.get("resumed") else 201)
            return True
        except CommerceTraceError as exc:
            _observe(
                "m35_commerce_case_reconciliation_blocked",
                link_id=public.get("link_id"),
                order_id=public.get("order_id"),
                case_id=case_id,
                product_code=public.get("product_code"),
                code=exc.code,
                user_id=user["id"],
            )
            handler.send_json(
                {
                    **public,
                    "documents_ready": False,
                    "state": "CASE_CREATED_DOCUMENTS_PENDING",
                    "error": str(exc),
                    "code": exc.code,
                    "notice": "El expediente permanece registrado, pero la reconciliación final quedó bloqueada y no se crearán duplicados.",
                },
                exc.status,
            )
            return True
        except Exception as exc:
            _observe(
                "m35_commerce_case_documents_pending",
                link_id=public.get("link_id"),
                order_id=public.get("order_id"),
                case_id=case_id,
                product_code=public.get("product_code"),
                error_class=exc.__class__.__name__,
                user_id=user["id"],
            )
            handler.send_json(
                {
                    **public,
                    "documents_ready": False,
                    "state": "CASE_CREATED_DOCUMENTS_PENDING",
                    "notice": (
                        "El expediente y el checkout quedaron registrados, pero la materialización documental "
                        "requiere reintento controlado. No se creó una segunda orden ni un segundo expediente."
                    ),
                },
                202,
            )
            return True

    except CommerceTraceError as exc:
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
        return True
    except PermissionError:
        handler.send_json({"error": "No tienes permisos para operar este checkout.", "code": "COMMERCE_FORBIDDEN"}, 403)
        return True
    except ValueError as exc:
        handler.send_json({"error": str(exc), "code": "COMMERCE_VALIDATION"}, 422)
        return True
    except Exception as exc:
        _observe(
            "m35_commerce_internal_error",
            user_id=user.get("id"),
            path=path,
            error_class=exc.__class__.__name__,
        )
        handler.send_json(
            {"error": "No fue posible completar la transición comercial.", "code": "COMMERCE_INTERNAL_ERROR"},
            500,
        )
        return True


__all__ = [
    "CONTEXT_PREFIX",
    "FINALIZE_PATH",
    "INVALIDATE_PATH",
    "ORDER_LOOKUP_PREFIX",
    "ORDER_PATH",
    "PAYMENT_PATH",
    "PREFIX",
    "commerce_store",
    "handle_m35_2_commerce_get",
    "handle_m35_2_commerce_post",
]
