from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.fulfillment_bridge_m35_1 import FulfillmentContextStore
from legalai_platform.handoff_m35_0 import HandoffStateError
from legalai_platform.runtime_registry import INFRA, M24_CLIENT_INTAKE, OBSERVABILITY, RATE_LIMITER, SELF_SERVICE


PREPARE_PATH = "/api/m35/fulfillment/prepare"


@lru_cache(maxsize=1)
def fulfillment_context() -> FulfillmentContextStore:
    return FulfillmentContextStore(INFRA.crypto, SELF_SERVICE, M24_CLIENT_INTAKE.offer)


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


def handle_m35_1_fulfillment_post(handler, path: str, user: dict) -> bool:
    if path != PREPARE_PATH:
        return False
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(f"m35-fulfillment:{user['id']}:{ip or 'unknown'}", 30, 300)
    if not allowed:
        handler.send_json(
            {
                "error": "Has realizado varias preparaciones seguidas. Intenta nuevamente más tarde.",
                "code": "RATE_LIMITED",
                "retry_after": retry,
            },
            429,
        )
        return True
    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe tener un formato válido.")
        product_code = str(data.get("product_code") or "").upper().strip()
        if not product_code:
            raise ValueError("Debes indicar la solución que estás continuando.")
        con = core.db()
        try:
            store = fulfillment_context()
            result = store.prepare(con, user["id"], product_code)
            core.audit(
                con,
                user["id"],
                "m35_fulfillment_bridge",
                result["handoff_id"],
                "prepare",
                {
                    "product_code": product_code,
                    "draft_id": result["draft_id"],
                    "eligible_prefill_count": result["eligible_prefill_count"],
                    "applied_prefill_count": result["applied_prefill_count"],
                    "prefilled_question_ids": result["prefilled_question_ids"],
                    "pricing_status": (result.get("offer") or {}).get("pricing_status"),
                },
            )
            con.commit()
        finally:
            con.close()
        _observe(
            "m35_fulfillment_prepared",
            handoff_id=result["handoff_id"],
            draft_id=result["draft_id"],
            product_code=product_code,
            eligible_prefill_count=result["eligible_prefill_count"],
            applied_prefill_count=result["applied_prefill_count"],
            user_id=user["id"],
            ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
        )
        handler.send_json(result, 200)
        return True
    except LookupError as exc:
        handler.send_json({"error": str(exc), "code": "NO_TRANSFERRED_INTAKE"}, 404)
        return True
    except HandoffStateError as exc:
        handler.send_json({"error": str(exc), "code": "FULFILLMENT_STATE"}, 409)
        return True
    except ValueError as exc:
        handler.send_json({"error": str(exc), "code": "FULFILLMENT_VALIDATION"}, 422)
        return True
    except Exception:
        _observe("m35_fulfillment_internal_error", user_id=user.get("id"), path=path)
        handler.send_json(
            {
                "error": "No fue posible preparar el contexto de fulfillment.",
                "code": "FULFILLMENT_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = ["PREPARE_PATH", "fulfillment_context", "handle_m35_1_fulfillment_post"]
