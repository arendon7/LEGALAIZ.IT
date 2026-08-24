from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.case_activation_m35_3 import CaseActivationCenter, CaseActivationError
from legalai_platform.runtime_registry import OBSERVABILITY, PAYMENTS, RATE_LIMITER, SELF_SERVICE


PREFIX = "/api/m35/activation/"


@lru_cache(maxsize=1)
def activation_center() -> CaseActivationCenter:
    return CaseActivationCenter(SELF_SERVICE, PAYMENTS)


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


def handle_m35_3_activation_get(handler, path: str, user: dict) -> bool:
    if not path.startswith(PREFIX):
        return False
    case_id = path[len(PREFIX):].strip()
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m35-activation:read:{user['id']}:{ip or 'unknown'}",
        60,
        300,
    )
    if not allowed:
        handler.send_json(
            {
                "error": "Has consultado el estado varias veces seguidas. Intenta nuevamente más tarde.",
                "code": "RATE_LIMITED",
                "retry_after": retry,
            },
            429,
        )
        return True

    con = core.db()
    try:
        result = activation_center().build(con, user["id"], case_id)
    except CaseActivationError as exc:
        _observe(
            "m35_case_activation_blocked",
            case_id=case_id,
            code=exc.code,
            user_id=user["id"],
            ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
        )
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
        return True
    except Exception as exc:
        _observe(
            "m35_case_activation_internal_error",
            case_id=case_id,
            user_id=user["id"],
            error_class=exc.__class__.__name__,
        )
        handler.send_json(
            {"error": "No fue posible verificar la activación del expediente.", "code": "ACTIVATION_INTERNAL_ERROR"},
            500,
        )
        return True
    finally:
        con.close()

    purchase = result.get("purchase_confirmation") or {}
    _observe(
        "m35_case_activation_verified",
        case_id=case_id,
        order_id=purchase.get("order_id"),
        product_code=(result.get("case") or {}).get("product_code"),
        activation_status=result.get("activation_status"),
        journey_state=(result.get("journey") or {}).get("current_state"),
        documents_count=(result.get("documents") or {}).get("count"),
        user_id=user["id"],
    )
    handler.send_json(result, 200)
    return True


__all__ = ["PREFIX", "activation_center", "handle_m35_3_activation_get"]
