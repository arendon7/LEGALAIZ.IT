from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.fact_extraction_m34_2 import FactExtractionService
from legalai_platform.routes.m34_1_intake_routes import intelligent_intake
from legalai_platform.runtime_registry import OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m34/intake"
ANALYZE_PATH = f"{PREFIX}/analyze"
FACT_DECISIONS_PATH = f"{PREFIX}/facts/decide"


@lru_cache(maxsize=1)
def fact_extraction() -> FactExtractionService:
    return FactExtractionService()


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _rate_limit(handler, purpose: str, limit: int, window_seconds: int) -> bool:
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m34-facts:{purpose}:{ip or 'unknown'}",
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
    """Never log recovery codes, fact values, problem text or candidate reasons."""
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _open_store():
    con = core.db()
    store = intelligent_intake()
    store.create_schema(con)
    return con, store


def handle_m34_2_fact_post(handler, path: str) -> bool:
    if path not in {ANALYZE_PATH, FACT_DECISIONS_PATH}:
        return False

    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe tener un formato válido.")
        recovery_code = str(data.get("recovery_code") or "")

        if path == ANALYZE_PATH:
            if not _rate_limit(handler, "analyze", 12, 300):
                return True
            con, store = _open_store()
            try:
                current = store.recover(con, recovery_code)
                extraction = fact_extraction().extract(
                    current["problem_statement"],
                    source_reference=f"intake:{current['id']}:problem_statement",
                )
                result = store.apply_extraction(con, recovery_code, extraction)
                con.commit()
            finally:
                con.close()
            provider = result.get("extraction_provider") or {}
            _safe_observe(
                "m34_fact_extraction_completed",
                intake_id=result["id"],
                stage=result["stage"],
                provider_id=str(provider.get("id") or "")[:120],
                provider_mode=str(provider.get("mode") or "")[:80],
                ai_enabled=bool(provider.get("ai_enabled")),
                fact_count=len(result.get("facts") or []),
                product_signal_count=len(result.get("candidate_products") or []),
                risk_signal_count=len(result.get("risk_signals") or []),
                ip_hash=sha256(_client_ip(handler).encode("utf-8")).hexdigest()[:16]
                if _client_ip(handler)
                else "",
            )
            handler.send_json(result)
            return True

        if not _rate_limit(handler, "decide", 24, 300):
            return True
        decisions = data.get("decisions")
        con, store = _open_store()
        try:
            result = store.confirm_fact_decisions(con, recovery_code, decisions)
            con.commit()
        finally:
            con.close()
        _safe_observe(
            "m34_fact_review_updated",
            intake_id=result["id"],
            stage=result["stage"],
            review_complete=bool(result.get("review_complete")),
            confirmed_fact_count=len(result.get("confirmed_facts") or []),
            pending_fact_count=int(result.get("pending_fact_count") or 0),
        )
        handler.send_json(result)
        return True
    except ValueError as exc:
        handler.send_json(
            {
                "error": str(exc),
                "code": "FACT_REVIEW_VALIDATION",
            },
            422,
        )
        return True
    except Exception:
        _safe_observe("m34_fact_internal_error", path=path)
        handler.send_json(
            {
                "error": "No fue posible estructurar o revisar los datos en este momento.",
                "code": "FACT_REVIEW_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = [
    "ANALYZE_PATH",
    "FACT_DECISIONS_PATH",
    "PREFIX",
    "fact_extraction",
    "handle_m34_2_fact_post",
]
