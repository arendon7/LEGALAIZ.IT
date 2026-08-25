from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.adaptive_question_m34_3 import AdaptiveIntakeStore, AdaptiveQuestionEngine
from legalai_platform.runtime_registry import INFRA, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m34/intake"
NEXT_STEP_PATH = f"{PREFIX}/next-step"
ANSWER_PATH = f"{PREFIX}/answer"


@lru_cache(maxsize=1)
def adaptive_store() -> AdaptiveIntakeStore:
    return AdaptiveIntakeStore(INFRA.crypto)


@lru_cache(maxsize=1)
def adaptive_engine() -> AdaptiveQuestionEngine:
    return AdaptiveQuestionEngine()


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0] or "")[:128]
    except Exception:
        return ""


def _rate_limit(handler, purpose: str, limit: int, window_seconds: int) -> bool:
    ip = _client_ip(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m34-questions:{purpose}:{ip or 'unknown'}",
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
    """M34.3 telemetry never receives answer values, problem text or recovery secrets."""
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _open_store():
    con = core.db()
    store = adaptive_store()
    store.create_schema(con)
    return con, store


def handle_m34_3_question_post(handler, path: str) -> bool:
    if path not in {NEXT_STEP_PATH, ANSWER_PATH}:
        return False
    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe tener un formato válido.")
        recovery_code = str(data.get("recovery_code") or "")

        if path == NEXT_STEP_PATH:
            if not _rate_limit(handler, "next", 40, 300):
                return True
            con, store = _open_store()
            try:
                result = store.next_step(con, recovery_code, adaptive_engine())
                con.commit()
            finally:
                con.close()
            _safe_observe(
                "m34_next_step",
                action=str(result.get("action") or "")[:80],
                stage=str(result.get("stage") or "")[:80],
                product_scope_count=len(result.get("product_scope") or []),
                ready_product_count=len((result.get("sufficiency") or {}).get("ready_product_codes") or []),
                reason_count=len(result.get("reason_codes") or []),
                ip_hash=sha256(_client_ip(handler).encode("utf-8")).hexdigest()[:16]
                if _client_ip(handler)
                else "",
            )
            handler.send_json(result)
            return True

        if not _rate_limit(handler, "answer", 60, 300):
            return True
        question_id = str(data.get("question_id") or "")
        if not question_id:
            raise ValueError("La respuesta debe identificar la pregunta vigente.")
        if "value" not in data:
            raise ValueError("La respuesta no contiene un valor.")
        con, store = _open_store()
        try:
            result = store.answer(
                con,
                recovery_code,
                adaptive_engine(),
                question_id,
                data.get("value"),
            )
            con.commit()
        finally:
            con.close()
        _safe_observe(
            "m34_question_answered",
            question_id=question_id[:120],
            next_action=str(result.get("action") or "")[:80],
            next_stage=str(result.get("stage") or "")[:80],
            product_scope_count=len(result.get("product_scope") or []),
        )
        handler.send_json(result)
        return True
    except ValueError as exc:
        handler.send_json({"error": str(exc), "code": "M34_3_VALIDATION"}, 422)
        return True
    except Exception:
        _safe_observe("m34_question_internal_error", path=path)
        handler.send_json(
            {
                "error": "No fue posible continuar el diagnóstico en este momento.",
                "code": "M34_3_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = [
    "ANSWER_PATH",
    "NEXT_STEP_PATH",
    "PREFIX",
    "adaptive_engine",
    "adaptive_store",
    "handle_m34_3_question_post",
]
