from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.recommendation_m34_4 import (
    ExplainableRecommendationEngine,
    RecommendationStore,
)
from legalai_platform.routes.m34_3_question_routes import adaptive_engine
from legalai_platform.runtime_registry import INFRA, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m34/intake"
RECOMMENDATION_PATH = f"{PREFIX}/recommendation"


@lru_cache(maxsize=1)
def recommendation_store() -> RecommendationStore:
    return RecommendationStore(INFRA.crypto)


@lru_cache(maxsize=1)
def recommendation_engine() -> ExplainableRecommendationEngine:
    return ExplainableRecommendationEngine()


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _rate_limit(handler, limit: int = 20, window_seconds: int = 300) -> bool:
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m34-recommendation:{ip or 'unknown'}",
        limit,
        window_seconds,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Has realizado varios intentos seguidos. Intenta nuevamente más tarde.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _safe_observe(event: str, **fields) -> None:
    """Recommendation telemetry excludes fact values, narrative, recovery secret and fingerprint."""
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def handle_m34_4_recommendation_post(handler, path: str) -> bool:
    if path != RECOMMENDATION_PATH:
        return False
    try:
        if not _rate_limit(handler):
            return True
        data = handler.read_json()
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe tener un formato válido.")
        recovery_code = str(data.get("recovery_code") or "")
        con = core.db()
        store = recommendation_store()
        store.create_schema(con)
        try:
            result = store.recommend(
                con,
                recovery_code,
                adaptive_engine(),
                recommendation_engine(),
            )
            con.commit()
        finally:
            con.close()

        primary = result.get("primary") or {}
        _safe_observe(
            "m34_recommendation_decided",
            decision_id=str(result.get("decision_id") or "")[:40],
            outcome=str(result.get("outcome") or "")[:40],
            primary_product_code=str(primary.get("product_code") or "")[:40],
            eligibility=str(primary.get("eligibility") or "")[:40],
            alternative_count=len(result.get("alternatives") or []),
            reason_count=len(result.get("reason_codes") or []),
            idempotent=bool(result.get("idempotent")),
            ip_hash=sha256(_client_ip(handler).encode("utf-8")).hexdigest()[:16]
            if _client_ip(handler)
            else "",
        )
        handler.send_json(result)
        return True
    except ValueError as exc:
        handler.send_json({"error": str(exc), "code": "M34_4_VALIDATION"}, 422)
        return True
    except Exception:
        _safe_observe("m34_recommendation_internal_error", path=path)
        handler.send_json(
            {
                "error": "No fue posible evaluar la recomendación en este momento.",
                "code": "M34_4_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = [
    "PREFIX",
    "RECOMMENDATION_PATH",
    "handle_m34_4_recommendation_post",
    "recommendation_engine",
    "recommendation_store",
]
