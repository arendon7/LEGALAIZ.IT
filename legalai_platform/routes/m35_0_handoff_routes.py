from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.handoff_m35_0 import (
    AccountHandoffStore,
    HandoffConflictError,
    HandoffStateError,
)
from legalai_platform.runtime_registry import INFRA, OBSERVABILITY, RATE_LIMITER, SELF_SERVICE


PREFIX = "/api/m35/intake"
CLAIM_PATH = f"{PREFIX}/claim"


@lru_cache(maxsize=1)
def account_handoff() -> AccountHandoffStore:
    return AccountHandoffStore(INFRA.crypto, SELF_SERVICE)


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _safe_observe(event: str, **fields) -> None:
    """Never log recovery codes, narrative text, fact values or recommendation internals."""
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def handle_m35_0_handoff_post(handler, path: str, user: dict) -> bool:
    if path != CLAIM_PATH:
        return False

    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m35-handoff:{user['id']}:{ip or 'unknown'}",
        12,
        300,
    )
    if not allowed:
        handler.send_json(
            {
                "error": "Has realizado varios intentos seguidos. Intenta nuevamente más tarde.",
                "code": "RATE_LIMITED",
                "retry_after": retry,
            },
            429,
        )
        return True

    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise HandoffStateError("La solicitud debe tener un formato válido.")
        recovery_code = str(data.get("recovery_code") or "")
        con = core.db()
        try:
            store = account_handoff()
            store.create_schema(con)
            result = store.claim(con, recovery_code, user["id"])
            core.audit(
                con,
                user["id"],
                "m35_intake_handoff",
                result["handoff_id"],
                "claim",
                {
                    "intake_id": result["intake_id"],
                    "decision_id": result["decision_id"],
                    "product_code": result["product_code"],
                    "draft_id": result["draft_id"],
                    "idempotent": bool(result.get("idempotent")),
                },
            )
            con.commit()
        finally:
            con.close()
        _safe_observe(
            "m35_intake_claimed",
            handoff_id=result["handoff_id"],
            intake_id=result["intake_id"],
            decision_id=result["decision_id"],
            product_code=result["product_code"],
            draft_id=result["draft_id"],
            idempotent=bool(result.get("idempotent")),
            user_id=user["id"],
            ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
        )
        handler.send_json(result, 200 if result.get("idempotent") else 201)
        return True
    except HandoffConflictError as exc:
        handler.send_json({"error": str(exc), "code": "HANDOFF_CONFLICT"}, 409)
        return True
    except HandoffStateError as exc:
        handler.send_json({"error": str(exc), "code": "HANDOFF_STATE"}, 422)
        return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc), "code": "HANDOFF_FORBIDDEN"}, 403)
        return True
    except ValueError as exc:
        handler.send_json({"error": str(exc), "code": "HANDOFF_VALIDATION"}, 422)
        return True
    except Exception:
        _safe_observe("m35_handoff_internal_error", user_id=user.get("id"), path=path)
        handler.send_json(
            {
                "error": "No fue posible vincular el diagnóstico a tu cuenta en este momento.",
                "code": "HANDOFF_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = ["CLAIM_PATH", "PREFIX", "account_handoff", "handle_m35_0_handoff_post"]
