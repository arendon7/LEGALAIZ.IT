from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeError
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpError
from legalai_platform.professional_disposition_m37_3 import (
    ProfessionalDispositionCenter,
    ProfessionalDispositionError,
    TARGET_CLOSE,
    TARGET_ESCALATE,
)
from legalai_platform.routes.m37_0_post_delivery_followup_routes import followup_center
from legalai_platform.routes.m37_1_evidence_routes import evidence_center
from legalai_platform.routes.m37_2_timing_reminder_routes import timing_center
from legalai_platform.runtime_registry import OBSERVABILITY, RATE_LIMITER
from legalai_platform.timing_reminders_m37_2 import TimingReminderError


PREFIX = "/api/m37/disposition"


@lru_cache(maxsize=1)
def disposition_center() -> ProfessionalDispositionCenter:
    return ProfessionalDispositionCenter(followup_center(), evidence_center(), timing_center())


def _parts(path: str) -> list[str]:
    raw = path[len(PREFIX):].strip("/")
    return [unquote(part) for part in raw.split("/") if part]


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


def _rate_limit(handler, user: dict, action: str, limit: int, window: int) -> bool:
    allowed, retry = RATE_LIMITER.allow(
        f"m37-3:{action}:{user.get('id')}:{_ip(handler) or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de decisiones de seguimiento.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, ProfessionalDispositionError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, EvidenceIntakeError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, TimingReminderError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PostDeliveryFollowUpError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, PermissionError):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, KeyError)):
        handler.send_json({"error": str(exc), "code": "DISPOSITION_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la decisión de seguimiento.", "code": "DISPOSITION_INTERNAL_ERROR"}, 500)
    return True


def handle_m37_3_disposition_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        if len(parts) == 2 and parts[0] == "cases":
            if not _rate_limit(handler, user, "assessment", 120, 300):
                return True
            payload = disposition_center().assessment(user, parts[1])
            _observe(
                "m37_disposition_assessment_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                m24_state=payload.get("m24_current_state"),
                close_ready=(payload.get("close_gate") or {}).get("ready"),
                close_blockers=len((payload.get("close_gate") or {}).get("blockers") or []),
                escalation_ready=(payload.get("escalation_gate") or {}).get("ready"),
                disposition_status=(payload.get("disposition") or {}).get("status"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        handler.send_json({"error": "Ruta M37.3 no encontrada.", "code": "M37_3_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_disposition_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


def handle_m37_3_disposition_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        if len(parts) == 3 and parts[0] == "cases" and parts[2] in {"close", "escalate"}:
            action = parts[2]
            if not _rate_limit(handler, user, action, 20, 300):
                return True
            data = handler.read_json()
            target = TARGET_CLOSE if action == "close" else TARGET_ESCALATE
            payload = disposition_center().dispose(
                user,
                parts[1],
                target,
                str(data.get("reason_code") or ""),
                str(data.get("internal_reason") or ""),
                str(data.get("client_summary") or ""),
                str(data.get("confirmation") or ""),
            )
            disposition = payload.get("disposition") or {}
            _observe(
                "m37_disposition_recorded",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                disposition_id=disposition.get("disposition_id"),
                target=disposition.get("target"),
                reason_code=disposition.get("reason_code"),
                status=disposition.get("status"),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        handler.send_json({"error": "Ruta M37.3 no encontrada.", "code": "M37_3_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_disposition_write_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


__all__ = [
    "PREFIX",
    "disposition_center",
    "handle_m37_3_disposition_get",
    "handle_m37_3_disposition_post",
]
