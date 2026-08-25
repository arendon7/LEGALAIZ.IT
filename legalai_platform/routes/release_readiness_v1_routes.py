from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.release_readiness_v1 import ReleaseReadinessV1
from legalai_platform.runtime_registry import INFRA, OBSERVABILITY, RATE_LIMITER, SETTINGS


PREFIX = "/api/release/v1/readiness"


@lru_cache(maxsize=1)
def readiness_center() -> ReleaseReadinessV1:
    return ReleaseReadinessV1(core.ROOT, SETTINGS, INFRA, core.PRODUCTS, core.INTERVIEWS)


def _ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _ip_hash(handler) -> str:
    raw = _ip(handler)
    return sha256(raw.encode("utf-8")).hexdigest()[:16] if raw else "unknown"


def _observe(event: str, **fields) -> None:
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def handle_release_readiness_get(handler, path: str, user: dict) -> bool:
    if path != PREFIX:
        return False
    allowed, retry = RATE_LIMITER.allow(
        f"v1-readiness:{user.get('id')}:{_ip(handler) or 'unknown'}",
        60,
        300,
    )
    if not allowed:
        handler.send_json(
            {
                "error": "Se alcanzó temporalmente el límite de consultas de readiness.",
                "code": "RATE_LIMITED",
                "retry_after": retry,
            },
            429,
        )
        return True

    con = core.db()
    try:
        payload = readiness_center().assess(con)
    except Exception:
        _observe("v1_release_readiness_failed", actor_role=user.get("role"), ip_hash=_ip_hash(handler))
        handler.send_json(
            {
                "error": "No fue posible evaluar la preparación del release.",
                "code": "V1_READINESS_INTERNAL_ERROR",
            },
            500,
        )
        return True
    finally:
        con.close()

    readiness = payload.get("readiness") or {}
    _observe(
        "v1_release_readiness_read",
        actor_role=user.get("role"),
        platform_ready=bool(readiness.get("platform_ready")),
        commercial_ready=bool(readiness.get("commercial_ready")),
        activation_authorized=bool(readiness.get("activation_authorized")),
        blockers=len(payload.get("blocking") or []),
        payment_blockers=len(payload.get("payment_blocking") or []),
        ip_hash=_ip_hash(handler),
    )
    handler.send_json(payload, 200)
    return True


__all__ = ["PREFIX", "handle_release_readiness_get", "readiness_center"]
