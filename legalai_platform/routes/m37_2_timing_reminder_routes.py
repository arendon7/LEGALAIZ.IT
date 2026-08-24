from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from urllib.parse import unquote

from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.evidence_intake_m37_1 import EvidenceIntakeError
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpError
from legalai_platform.routes.m37_0_post_delivery_followup_routes import followup_center
from legalai_platform.routes.m37_1_evidence_routes import evidence_center
from legalai_platform.runtime_registry import OBSERVABILITY, RATE_LIMITER
from legalai_platform.timing_reminders_m37_2 import TimingReminderCenter, TimingReminderError


PREFIX = "/api/m37/timing"


@lru_cache(maxsize=1)
def timing_center() -> TimingReminderCenter:
    return TimingReminderCenter(followup_center(), evidence_center())


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
        f"m37-2:{action}:{user.get('id')}:{_ip(handler) or 'unknown'}",
        limit,
        window,
    )
    if allowed:
        return True
    handler.send_json(
        {
            "error": "Se alcanzó temporalmente el límite de operaciones temporales.",
            "code": "RATE_LIMITED",
            "retry_after": retry,
        },
        429,
    )
    return False


def _error(handler, exc: Exception) -> bool:
    if isinstance(exc, TimingReminderError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, EvidenceIntakeError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PostDeliveryFollowUpError):
        handler.send_json({"error": str(exc), "code": exc.code}, exc.status)
    elif isinstance(exc, PermissionDenied):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, PermissionError):
        handler.send_json({"error": str(exc), "code": "PERMISSION_DENIED"}, 403)
    elif isinstance(exc, (ValueError, TypeError, LookupError, KeyError)):
        handler.send_json({"error": str(exc), "code": "TIMING_INPUT_INVALID"}, 422)
    else:
        handler.send_json({"error": "No fue posible completar la operación temporal.", "code": "TIMING_INTERNAL_ERROR"}, 500)
    return True


def handle_m37_2_timing_get(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = timing_center()
        if len(parts) == 2 and parts[0] == "cases":
            if not _rate_limit(handler, user, "detail", 120, 300):
                return True
            payload = center.detail(user, parts[1])
            _observe(
                "m37_timing_detail_read",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                date_records=(payload.get("metrics") or {}).get("date_records"),
                reminders=(payload.get("metrics") or {}).get("reminders"),
                due=(payload.get("metrics") or {}).get("due"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200)
            return True
        handler.send_json({"error": "Ruta M37.2 no encontrada.", "code": "M37_2_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_timing_read_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


def handle_m37_2_timing_post(handler, path: str, user: dict) -> bool:
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    parts = _parts(path)
    try:
        center = timing_center()
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "tasks" and parts[4] == "dates":
            if not _rate_limit(handler, user, "date", 40, 300):
                return True
            data = handler.read_json()
            payload = center.record_date(
                user,
                parts[1],
                parts[3],
                str(data.get("event_type") or ""),
                str(data.get("date") or ""),
                evidence_id=str(data.get("evidence_id") or "") or None,
                supersedes_date_record_id=str(data.get("supersedes_date_record_id") or "") or None,
            )
            _observe(
                "m37_date_recorded",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                follow_up_id=parts[3],
                date_record_id=payload.get("date_record_id"),
                event_type=payload.get("event_type"),
                provenance=payload.get("provenance"),
                evidence_referenced=payload.get("evidence_referenced"),
                superseded=bool(payload.get("supersedes_date_record_id")),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "tasks" and parts[4] == "reminders":
            if not _rate_limit(handler, user, "schedule", 40, 300):
                return True
            data = handler.read_json()
            payload = center.schedule_reminder(
                user,
                parts[1],
                parts[3],
                str(data.get("scheduled_for") or ""),
                source_date_record_id=str(data.get("source_date_record_id") or "") or None,
            )
            _observe(
                "m37_reminder_scheduled",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                follow_up_id=parts[3],
                reminder_id=payload.get("reminder_id"),
                status=payload.get("status"),
                source_date_linked=bool(payload.get("source_date_record_id")),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        if len(parts) == 5 and parts[0] == "cases" and parts[2] == "reminders" and parts[4] in {"acknowledge", "cancel"}:
            if not _rate_limit(handler, user, "reminder-action", 60, 300):
                return True
            action = "ACKNOWLEDGED" if parts[4] == "acknowledge" else "CANCELLED"
            payload = center.record_reminder_action(user, parts[1], parts[3], action)
            _observe(
                "m37_reminder_action_recorded",
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                case_id=parts[1],
                reminder_id=parts[3],
                status=payload.get("status"),
                idempotent=payload.get("idempotent"),
                ip_hash=_ip_hash(handler),
            )
            handler.send_json(payload, 200 if payload.get("idempotent") else 201)
            return True
        handler.send_json({"error": "Ruta M37.2 no encontrada.", "code": "M37_2_NOT_FOUND"}, 404)
        return True
    except Exception as exc:
        _observe(
            "m37_timing_write_blocked",
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            error_class=exc.__class__.__name__,
            ip_hash=_ip_hash(handler),
        )
        return _error(handler, exc)


__all__ = ["PREFIX", "timing_center", "handle_m37_2_timing_get", "handle_m37_2_timing_post"]
