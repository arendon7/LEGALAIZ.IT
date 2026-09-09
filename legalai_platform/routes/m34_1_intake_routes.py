from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

import core_v11 as core
from legalai_platform.intelligent_intake_m34_1 import IntelligentIntakeStore
from legalai_platform.runtime_registry import INFRA, OBSERVABILITY, RATE_LIMITER


PREFIX = "/api/m34/intake"


@lru_cache(maxsize=1)
def intelligent_intake() -> IntelligentIntakeStore:
    return IntelligentIntakeStore(INFRA.crypto)


def _client_context(handler) -> tuple[str, str]:
    ip = ""
    try:
        ip = str(handler.client_address[0] or "")[:128]
    except Exception:
        pass
    user_agent = str(handler.headers.get("User-Agent") or "")[:500]
    return ip, user_agent


def _rate_limit(handler, purpose: str, limit: int, window_seconds: int) -> bool:
    ip, _ = _client_context(handler)
    allowed, retry = RATE_LIMITER.allow(
        f"m34-intake:{purpose}:{ip or 'unknown'}",
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
    """Never send problem text, recovery codes or decrypted payloads to observability."""
    try:
        OBSERVABILITY.write(event, **fields)
    except Exception:
        pass


def _open_store():
    con = core.db()
    intelligent_intake().create_schema(con)
    return con, intelligent_intake()


def handle_m34_1_intake_post(handler, path: str) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False

    try:
        data = handler.read_json()
        if not isinstance(data, dict):
            raise ValueError("La solicitud debe tener un formato válido.")

        if path == f"{PREFIX}/start":
            if not _rate_limit(handler, "start", 12, 300):
                return True
            con, store = _open_store()
            try:
                result = store.create(con, str(data.get("problem_statement") or ""))
                con.commit()
            finally:
                con.close()
            ip, _ = _client_context(handler)
            _safe_observe(
                "m34_intake_started",
                intake_id=result["id"],
                stage=result["stage"],
                ip_hash=sha256(ip.encode("utf-8")).hexdigest()[:16] if ip else "",
            )
            handler.send_json(result, 201)
            return True

        if path == f"{PREFIX}/recover":
            if not _rate_limit(handler, "recover", 10, 300):
                return True
            con, store = _open_store()
            try:
                result = store.recover(con, str(data.get("recovery_code") or ""))
                con.commit()
            finally:
                con.close()
            _safe_observe(
                "m34_intake_recovered",
                intake_id=result["id"],
                stage=result["stage"],
            )
            handler.send_json(result)
            return True

        if path == f"{PREFIX}/problem":
            if not _rate_limit(handler, "update", 20, 300):
                return True
            con, store = _open_store()
            try:
                result = store.update_problem(
                    con,
                    str(data.get("recovery_code") or ""),
                    str(data.get("problem_statement") or ""),
                )
                con.commit()
            finally:
                con.close()
            _safe_observe(
                "m34_intake_problem_updated",
                intake_id=result["id"],
                stage=result["stage"],
            )
            handler.send_json(result)
            return True

        handler.send_json({"error": "Ruta de intake no encontrada."}, 404)
        return True
    except ValueError as exc:
        # Avoid distinguishing token existence from expiry/transfer in public API.
        handler.send_json({"error": str(exc), "code": "INTAKE_VALIDATION"}, 422)
        return True
    except Exception:
        _safe_observe("m34_intake_internal_error", path=path)
        handler.send_json(
            {
                "error": "No fue posible guardar el diagnóstico en este momento.",
                "code": "INTAKE_INTERNAL_ERROR",
            },
            500,
        )
        return True


__all__ = ["PREFIX", "handle_m34_1_intake_post", "intelligent_intake"]
