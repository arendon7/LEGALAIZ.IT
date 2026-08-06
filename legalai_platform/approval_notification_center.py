from __future__ import annotations

"""Centro auditable de notificaciones, escalamiento y calendario M32.7.

La capa complementa M32.6. No calcula términos legales ni acredita entrega de
mensajes. Los calendarios son configuraciones operativas explícitas y la salida
externa permanece en una cola hasta que un proveedor real registre despacho.
"""

from datetime import date, datetime, time, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.approval_desk_operations import (
    ApprovalDeskOperations,
    OperationsIntegrityError,
    PORTFOLIO_CODES,
)
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    PermissionDenied,
)


M32_7_SCHEMA = "M32.7"
BOGOTA = ZoneInfo("America/Bogota")
PROFESSIONAL_ROLES = frozenset({"specialist", "admin", "qa"})
SEVERITY_WEIGHT = {"info": 0, "medium": 1, "high": 2, "critical": 3}
_LOCK = RLock()

DEFAULT_CALENDAR = {
    "calendar_id": "operational-co",
    "name": "Calendario operativo Colombia",
    "timezone": "America/Bogota",
    "weekdays": [0, 1, 2, 3, 4],
    "open_time": "08:00",
    "close_time": "17:00",
    "holidays": [],
    "source": "admin_configured",
    "legal_deadline": False,
}
DEFAULT_POLICY = {
    "external_email_enabled": False,
    "external_min_severity": "high",
    "repeat_critical_hours": 24,
    "admin_escalation_after_hours": 0,
    "delivery_provider": None,
    "delivery_mode": "queue_only",
}


class NotificationIntegrityError(ApprovalDeskError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_segment(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ApprovalDeskError(f"{field} contiene caracteres no permitidos.")
    return text


def _actor(user: dict[str, Any]) -> dict[str, str]:
    actor_id = str(user.get("id") or "").strip()
    role = str(user.get("role") or "").strip().casefold()
    if not actor_id or role not in PROFESSIONAL_ROLES:
        raise PermissionDenied("La operación requiere un actor profesional autenticado.")
    return {"id": actor_id, "role": role, "name": str(user.get("name") or "").strip()}


def _parse_datetime(value: str | datetime, field: str = "fecha") -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            raise ApprovalDeskError(f"{field} es obligatoria.")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ApprovalDeskError(f"{field} debe usar formato ISO 8601.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BOGOTA)
    return parsed.astimezone(BOGOTA)


def _clock(value: str, field: str) -> time:
    try:
        parsed = time.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ApprovalDeskError(f"{field} debe usar formato HH:MM.") from exc
    if parsed.second or parsed.microsecond:
        raise ApprovalDeskError(f"{field} no admite segundos.")
    return parsed


def _clean_text(value: Any, limit: int = 1000) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "")).strip()[:limit]


class BusinessCalendar:
    """Calendario operativo explícito; no representa un calendario judicial."""

    def __init__(self, config: dict[str, Any]):
        self.config = self.validate(config)
        self.timezone = ZoneInfo(self.config["timezone"])
        self.weekdays = set(self.config["weekdays"])
        self.opens = _clock(self.config["open_time"], "open_time")
        self.closes = _clock(self.config["close_time"], "close_time")
        self.holidays = {date.fromisoformat(item) for item in self.config["holidays"]}

    @staticmethod
    def validate(config: dict[str, Any]) -> dict[str, Any]:
        source = dict(DEFAULT_CALENDAR)
        source.update(config or {})
        calendar_id = _safe_segment(source.get("calendar_id"), "calendar_id")
        weekdays = sorted({int(item) for item in source.get("weekdays", [])})
        if not weekdays or any(item < 0 or item > 6 for item in weekdays):
            raise ApprovalDeskError("El calendario debe incluir días de semana entre 0 y 6.")
        opens = _clock(source.get("open_time"), "open_time")
        closes = _clock(source.get("close_time"), "close_time")
        if datetime.combine(date.today(), closes) <= datetime.combine(date.today(), opens):
            raise ApprovalDeskError("La hora de cierre debe ser posterior a la apertura.")
        try:
            ZoneInfo(str(source.get("timezone") or ""))
        except Exception as exc:
            raise ApprovalDeskError("La zona horaria del calendario no es válida.") from exc
        holidays = sorted({date.fromisoformat(str(item)).isoformat() for item in source.get("holidays", [])})
        if len(holidays) > 500:
            raise ApprovalDeskError("El calendario no puede contener más de 500 cierres explícitos.")
        return {
            "calendar_id": calendar_id,
            "name": _clean_text(source.get("name") or calendar_id, 120),
            "timezone": str(source.get("timezone")),
            "weekdays": weekdays,
            "open_time": opens.strftime("%H:%M"),
            "close_time": closes.strftime("%H:%M"),
            "holidays": holidays,
            "source": "admin_configured",
            "legal_deadline": False,
        }

    def is_open_day(self, value: date) -> bool:
        return value.weekday() in self.weekdays and value not in self.holidays

    def _bounds(self, value: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(value, self.opens, self.timezone),
            datetime.combine(value, self.closes, self.timezone),
        )

    def next_open(self, value: datetime) -> datetime:
        current = _parse_datetime(value).astimezone(self.timezone)
        for _ in range(370):
            opens, closes = self._bounds(current.date())
            if self.is_open_day(current.date()):
                if current < opens:
                    return opens
                if current < closes:
                    return current
            next_day = current.date() + timedelta(days=1)
            current = datetime.combine(next_day, time.min, self.timezone)
        raise ApprovalDeskError("No fue posible encontrar una jornada disponible en el calendario.")

    def add_business_hours(self, start: datetime, hours: float) -> datetime:
        amount = float(hours)
        if amount <= 0 or amount > 8760:
            raise ApprovalDeskError("Las horas hábiles deben estar entre 0 y 8.760.")
        remaining = amount * 3600
        current = self.next_open(start)
        guard = 0
        while remaining > 0:
            guard += 1
            if guard > 10000:
                raise ApprovalDeskError("El cálculo excedió el límite seguro del calendario.")
            _, closes = self._bounds(current.date())
            available = max(0.0, (closes - current).total_seconds())
            if available <= 0:
                current = self.next_open(closes + timedelta(seconds=1))
                continue
            consumed = min(remaining, available)
            current += timedelta(seconds=consumed)
            remaining -= consumed
            if remaining > 0:
                current = self.next_open(current + timedelta(seconds=1))
        return current.astimezone(BOGOTA)

    def business_hours_between(self, start: datetime, end: datetime) -> float:
        left = _parse_datetime(start).astimezone(self.timezone)
        right = _parse_datetime(end).astimezone(self.timezone)
        direction = 1
        if right < left:
            left, right = right, left
            direction = -1
        cursor = left
        seconds = 0.0
        guard = 0
        while cursor < right:
            guard += 1
            if guard > 10000:
                raise ApprovalDeskError("El cálculo excedió el límite seguro del calendario.")
            if not self.is_open_day(cursor.date()):
                cursor = self.next_open(cursor)
                if cursor >= right:
                    break
            opens, closes = self._bounds(cursor.date())
            segment_start = max(cursor, opens)
            segment_end = min(right, closes)
            if segment_end > segment_start:
                seconds += (segment_end - segment_start).total_seconds()
            if right <= closes:
                break
            cursor = self.next_open(closes + timedelta(seconds=1))
        return round(direction * seconds / 3600, 2)


class ApprovalNotificationCenter:
    """Bandejas, escalamiento, carga y cola externa con auditoría append-only."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        operations: ApprovalDeskOperations | None = None,
        db_factory: Callable[[], Any] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self.root = Path(root or (core.RUNTIME / "approval-desk")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.operations = operations or ApprovalDeskOperations(self.root)
        self.db_factory = db_factory or core.db
        self.now_factory = now_factory or (lambda: datetime.now(BOGOTA))
        self.center_dir = self.root / "notification-center"
        self.center_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.center_dir / "events.jsonl"

    def _now(self) -> datetime:
        return self.now_factory().astimezone(BOGOTA)

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise NotificationIntegrityError("La bitácora M32.7 contiene un registro inválido.")
                events.append(item)
        return events

    def verify_chain(self) -> dict[str, Any]:
        previous = "0" * 64
        events = self._read_events()
        for expected, event in enumerate(events, 1):
            stored_hash = str(event.get("event_hash") or "")
            candidate = dict(event)
            candidate.pop("event_hash", None)
            calculated = sha256(_canonical_json(candidate).encode("utf-8")).hexdigest()
            if int(event.get("sequence") or 0) != expected or event.get("previous_hash") != previous or stored_hash != calculated:
                return {"valid": False, "events": len(events), "failed_sequence": expected, "last_hash": previous}
            previous = stored_hash
        return {"valid": True, "events": len(events), "failed_sequence": None, "last_hash": previous}

    def _append(self, event_type: str, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        actor = _actor(user)
        with _LOCK:
            integrity = self.verify_chain()
            if not integrity["valid"]:
                raise NotificationIntegrityError("La cadena M32.7 está alterada; no se admiten nuevas actuaciones.")
            sequence = int(integrity["events"]) + 1
            event = {
                "schema_version": M32_7_SCHEMA,
                "sequence": sequence,
                "event_id": f"NTF-EVT-{sequence:07d}",
                "event_type": event_type,
                "created_at": self._now().isoformat(timespec="seconds"),
                "actor": actor,
                "payload": payload,
                "previous_hash": integrity["last_hash"],
            }
            event["event_hash"] = sha256(_canonical_json(event).encode("utf-8")).hexdigest()
            with self.events_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return event

    def _state(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "calendar": dict(DEFAULT_CALENDAR),
            "policy": dict(DEFAULT_POLICY),
            "notifications": {},
            "outbox": {},
            "schedules": {},
        }
        for event in self._read_events():
            payload = event.get("payload") or {}
            kind = event.get("event_type")
            if kind == "calendar.updated":
                state["calendar"] = dict(payload.get("calendar") or DEFAULT_CALENDAR)
            elif kind == "policy.updated":
                state["policy"].update(payload.get("policy") or {})
            elif kind == "notification.created":
                item = dict(payload.get("notification") or {})
                item["read_by"] = {}
                item["acknowledged_by"] = None
                item["snoozed_until"] = None
                state["notifications"][item["notification_id"]] = item
            elif kind == "notification.read":
                item = state["notifications"].get(payload.get("notification_id"))
                if item:
                    item["read_by"][payload.get("user_id")] = event.get("created_at")
            elif kind == "notification.acknowledged":
                item = state["notifications"].get(payload.get("notification_id"))
                if item:
                    item["acknowledged_by"] = {"actor": event.get("actor"), "created_at": event.get("created_at"), "comment": payload.get("comment")}
            elif kind == "notification.snoozed":
                item = state["notifications"].get(payload.get("notification_id"))
                if item:
                    item["snoozed_until"] = payload.get("until")
            elif kind == "outbox.queued":
                message = dict(payload.get("message") or {})
                state["outbox"][message["message_id"]] = message
            elif kind == "outbox.cancelled":
                message = state["outbox"].get(payload.get("message_id"))
                if message:
                    message["status"] = "cancelled"
                    message["cancelled_at"] = event.get("created_at")
                    message["cancellation_reason"] = payload.get("reason")
            elif kind == "calendar.deadline_applied":
                state["schedules"][payload.get("case_id")] = dict(payload)
        return state

    def _users(self) -> list[dict[str, Any]]:
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            email = ",email" if "email" in columns else ",NULL AS email"
            active = "AND active=1" if "active" in columns else ""
            rows = [dict(row) for row in con.execute(
                f"SELECT id,name,role{email} FROM users WHERE role IN ('specialist','admin','qa') {active} ORDER BY role,name"
            ).fetchall()]
        finally:
            con.close()
        return rows

    def _assert_notification_access(self, user: dict[str, Any], item: dict[str, Any]) -> None:
        if user.get("role") == "admin":
            return
        if str(item.get("recipient_id")) != str(user.get("id")):
            raise PermissionDenied("La notificación pertenece a otra bandeja profesional.")

    @staticmethod
    def _severity_at_least(value: str, threshold: str) -> bool:
        return SEVERITY_WEIGHT.get(value, -1) >= SEVERITY_WEIGHT.get(threshold, 2)

    def calendar(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        state = self._state()
        config = BusinessCalendar.validate(state["calendar"])
        return {
            "schema_version": M32_7_SCHEMA,
            "calendar": config,
            "calendar_sha256": sha256(_canonical_json(config).encode("utf-8")).hexdigest(),
            "notice": "Calendario operativo configurable. No sustituye el cómputo profesional de términos legales ni calendarios oficiales.",
            "capabilities": {"manage": user.get("role") == "admin"},
        }

    def update_calendar(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar el calendario operativo.")
        current = self._state()["calendar"]
        candidate = dict(current)
        candidate.update(payload or {})
        validated = BusinessCalendar.validate(candidate)
        event = self._append("calendar.updated", user, {
            "calendar": validated,
            "declaration": "Configuración operativa; no es un calendario oficial de términos.",
        })
        return {"event": event, **self.calendar(user)}

    def policy(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        policy = dict(self._state()["policy"])
        if user.get("role") != "admin":
            policy.pop("delivery_provider", None)
        return {
            "schema_version": M32_7_SCHEMA,
            "policy": policy,
            "external_delivery_active": False,
            "notice": "M32.7 únicamente crea una cola auditable; no acredita entrega externa.",
            "capabilities": {"manage": user.get("role") == "admin"},
        }

    def update_policy(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar la política de notificaciones.")
        allowed = {
            "external_email_enabled",
            "external_min_severity",
            "repeat_critical_hours",
            "admin_escalation_after_hours",
        }
        if set(payload or {}) - allowed:
            raise ApprovalDeskError("La política contiene campos no permitidos.")
        current = dict(self._state()["policy"])
        if "external_email_enabled" in payload:
            current["external_email_enabled"] = bool(payload["external_email_enabled"])
        if "external_min_severity" in payload:
            severity = str(payload["external_min_severity"]).casefold()
            if severity not in {"high", "critical"}:
                raise ApprovalDeskError("La severidad externa mínima debe ser high o critical.")
            current["external_min_severity"] = severity
        for field in ("repeat_critical_hours", "admin_escalation_after_hours"):
            if field in payload:
                value = int(payload[field])
                if value < 0 or value > 168:
                    raise ApprovalDeskError(f"{field} debe estar entre 0 y 168 horas.")
                current[field] = value
        current["delivery_provider"] = None
        current["delivery_mode"] = "queue_only"
        event = self._append("policy.updated", user, {"policy": current})
        return {"event": event, **self.policy(user)}

    def _recipients(self, row: dict[str, Any], alert: dict[str, Any], users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        operations = row.get("operations") or {}
        specialist_id = (operations.get("assigned_specialist") or {}).get("id")
        qa_id = (operations.get("assigned_qa") or {}).get("id")
        by_id = {str(item["id"]): item for item in users}
        admins = [item for item in users if item.get("role") == "admin"]
        code = alert.get("code")
        recipients: list[dict[str, Any]] = []

        def include(user_id: str | None) -> None:
            if user_id and str(user_id) in by_id:
                recipients.append(by_id[str(user_id)])

        if code in {"operations_chain_invalid", "approval_chain_invalid", "specialist_unassigned", "qa_unassigned", "separation_conflict", "deadline_missing"}:
            recipients.extend(admins)
        elif code == "legal_pending":
            include(specialist_id)
            if not specialist_id:
                recipients.extend(admins)
        elif code in {"qa_pending", "ready_to_release"}:
            include(qa_id)
            if code == "ready_to_release":
                recipients.extend(admins)
        else:
            include(specialist_id)
            include(qa_id)
            if alert.get("severity") == "critical" or row.get("sla", {}).get("status") == "overdue":
                recipients.extend(admins)
        unique: dict[str, dict[str, Any]] = {}
        for item in recipients:
            unique[str(item["id"])] = item
        return list(unique.values())

    def _notification_base(self, row: dict[str, Any], alert: dict[str, Any], recipient: dict[str, Any], revision_id: str) -> str:
        parts = [
            row.get("desk_case_id"),
            alert.get("code"),
            recipient.get("id"),
            revision_id,
            row.get("sla", {}).get("due_at"),
        ]
        return sha256("|".join(str(item or "") for item in parts).encode("utf-8")).hexdigest()

    def _repeat_allowed(self, existing: list[dict[str, Any]], severity: str, policy: dict[str, Any]) -> bool:
        if not existing:
            return True
        if severity != "critical":
            return False
        hours = int(policy.get("repeat_critical_hours") or 0)
        if hours <= 0:
            return False
        last = max(_parse_datetime(item["created_at"]) for item in existing)
        return self._now() - last >= timedelta(hours=hours)

    def evaluate(self, user: dict[str, Any], case_id: str | None = None) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede ejecutar la evaluación de escalamiento.")
        if not self.verify_chain()["valid"]:
            raise NotificationIntegrityError("La evaluación está bloqueada por una cadena M32.7 inválida.")
        portfolio = self.operations.portfolio(user)
        rows = portfolio.get("cases", [])
        if case_id:
            case_value = _safe_segment(case_id, "case_id")
            rows = [row for row in rows if row.get("desk_case_id") == case_value]
            if not rows:
                raise PermissionDenied("El expediente no está disponible en el alcance administrativo.")
        users = self._users()
        state = self._state()
        policy = state["policy"]
        created: list[str] = []
        queued: list[str] = []
        suppressed = 0
        notifications = list(state["notifications"].values())
        for row in rows:
            detail = self.operations.workspace.detail(user, row["desk_case_id"])
            revision_id = str(detail.get("case", {}).get("current_revision_id") or "none")
            for alert in row.get("alerts", []):
                if alert.get("acknowledged"):
                    continue
                for recipient in self._recipients(row, alert, users):
                    base = self._notification_base(row, alert, recipient, revision_id)
                    existing = [item for item in notifications if item.get("base_fingerprint") == base]
                    if not self._repeat_allowed(existing, str(alert.get("severity")), policy):
                        suppressed += 1
                        continue
                    notification_id = "NTF-" + uuid4().hex[:18].upper()
                    escalation = SEVERITY_WEIGHT.get(str(alert.get("severity")), 1)
                    if row.get("sla", {}).get("status") == "overdue":
                        escalation = max(escalation, 3)
                    notification = {
                        "notification_id": notification_id,
                        "recipient_id": str(recipient["id"]),
                        "recipient_name": recipient.get("name"),
                        "case_id": row.get("desk_case_id"),
                        "source_case_id": row.get("source_case_id"),
                        "product_code": row.get("product_code"),
                        "title": alert.get("title"),
                        "description": alert.get("description"),
                        "alert_code": alert.get("code"),
                        "severity": alert.get("severity"),
                        "escalation_level": escalation,
                        "workflow_status": row.get("status"),
                        "sla_status": row.get("sla", {}).get("status"),
                        "due_at": row.get("sla", {}).get("due_at"),
                        "revision_id": revision_id,
                        "base_fingerprint": base,
                        "created_at": self._now().isoformat(timespec="seconds"),
                        "channel": "in_app",
                    }
                    self._append("notification.created", user, {"notification": notification})
                    notifications.append(notification)
                    created.append(notification_id)
                    if (
                        policy.get("external_email_enabled")
                        and recipient.get("email")
                        and self._severity_at_least(str(alert.get("severity")), str(policy.get("external_min_severity")))
                    ):
                        message_id = "OUT-" + uuid4().hex[:18].upper()
                        message = {
                            "message_id": message_id,
                            "notification_id": notification_id,
                            "channel": "email",
                            "recipient_id": str(recipient["id"]),
                            "recipient": str(recipient.get("email")),
                            "subject": f"LegalAIZ.it · {alert.get('title')}",
                            "body": (
                                f"Producto {row.get('product_code')} · expediente {row.get('desk_case_id')}. "
                                "Ingrese a la Mesa Jurídica para consultar el detalle protegido."
                            ),
                            "status": "queued",
                            "queued_at": self._now().isoformat(timespec="seconds"),
                            "provider": None,
                            "delivery_evidence": None,
                            "contains_document_content": False,
                        }
                        self._append("outbox.queued", user, {"message": message})
                        queued.append(message_id)
        event = self._append("evaluation.completed", user, {
            "case_id": case_id,
            "evaluated_cases": len(rows),
            "created_notifications": len(created),
            "queued_external": len(queued),
            "suppressed_duplicates": suppressed,
            "external_delivery_performed": False,
        })
        return {
            "schema_version": M32_7_SCHEMA,
            "event": event,
            "evaluated_cases": len(rows),
            "created_notifications": created,
            "queued_messages": queued,
            "suppressed_duplicates": suppressed,
            "external_delivery_performed": False,
            "audit": self.verify_chain(),
        }

    def inbox(self, user: dict[str, Any], *, include_all: bool = False, limit: int = 100) -> dict[str, Any]:
        _actor(user)
        if include_all and user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede consultar todas las bandejas.")
        state = self._state()
        now = self._now()
        rows: list[dict[str, Any]] = []
        for item in state["notifications"].values():
            if not include_all and str(item.get("recipient_id")) != str(user.get("id")):
                continue
            snoozed = item.get("snoozed_until") and _parse_datetime(item["snoozed_until"]) > now
            copy = dict(item)
            copy["read"] = str(user.get("id")) in item.get("read_by", {})
            copy["acknowledged"] = bool(item.get("acknowledged_by"))
            copy["snoozed"] = bool(snoozed)
            copy["active"] = not copy["acknowledged"] and not copy["snoozed"]
            rows.append(copy)
        rows.sort(key=lambda item: (
            item.get("acknowledged", False),
            item.get("read", False),
            -SEVERITY_WEIGHT.get(str(item.get("severity")), 0),
            str(item.get("created_at") or ""),
        ))
        rows = rows[: max(1, min(int(limit), 500))]
        return {
            "schema_version": M32_7_SCHEMA,
            "scope": "all" if include_all else "personal",
            "metrics": {
                "total": len(rows),
                "unread": sum(not item["read"] for item in rows),
                "active": sum(item["active"] for item in rows),
                "critical": sum(item["active"] and item.get("severity") == "critical" for item in rows),
                "snoozed": sum(item["snoozed"] for item in rows),
            },
            "notifications": rows,
            "audit": self.verify_chain(),
        }

    def _notification(self, notification_id: str) -> dict[str, Any]:
        item = self._state()["notifications"].get(_safe_segment(notification_id, "notification_id"))
        if not item:
            raise ApprovalDeskError("La notificación no existe.")
        return item

    def mark_read(self, user: dict[str, Any], notification_id: str) -> dict[str, Any]:
        item = self._notification(notification_id)
        self._assert_notification_access(user, item)
        if str(user.get("id")) in item.get("read_by", {}):
            return self.inbox(user)
        self._append("notification.read", user, {"notification_id": item["notification_id"], "user_id": str(user["id"])})
        return self.inbox(user)

    def acknowledge(self, user: dict[str, Any], notification_id: str, comment: str = "") -> dict[str, Any]:
        item = self._notification(notification_id)
        self._assert_notification_access(user, item)
        if item.get("acknowledged_by"):
            raise ApprovalDeskError("La notificación ya fue reconocida.")
        self._append("notification.acknowledged", user, {
            "notification_id": item["notification_id"],
            "comment": _clean_text(comment, 1000),
            "underlying_alert_resolved": False,
        })
        return self.inbox(user)

    def snooze(self, user: dict[str, Any], notification_id: str, until: str) -> dict[str, Any]:
        item = self._notification(notification_id)
        self._assert_notification_access(user, item)
        target = _parse_datetime(until, "until")
        if target <= self._now() or target > self._now() + timedelta(days=30):
            raise ApprovalDeskError("El aplazamiento debe estar entre ahora y 30 días.")
        self._append("notification.snoozed", user, {
            "notification_id": item["notification_id"],
            "until": target.isoformat(timespec="seconds"),
            "underlying_alert_resolved": False,
        })
        return self.inbox(user)

    def outbox(self, user: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede consultar la cola externa.")
        rows = list(self._state()["outbox"].values())
        rows.sort(key=lambda item: str(item.get("queued_at") or ""), reverse=True)
        return {
            "schema_version": M32_7_SCHEMA,
            "metrics": {
                "queued": sum(item.get("status") == "queued" for item in rows),
                "cancelled": sum(item.get("status") == "cancelled" for item in rows),
                "delivered": 0,
            },
            "messages": rows,
            "external_delivery_active": False,
            "notice": "Los mensajes están en cola; no existe evidencia de entrega externa.",
        }

    def cancel_message(self, user: dict[str, Any], message_id: str, reason: str) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede cancelar mensajes en cola.")
        state = self._state()
        item = state["outbox"].get(_safe_segment(message_id, "message_id"))
        if not item:
            raise ApprovalDeskError("El mensaje no existe.")
        if item.get("status") != "queued":
            raise ApprovalDeskError("El mensaje ya no está pendiente en la cola.")
        self._append("outbox.cancelled", user, {
            "message_id": item["message_id"],
            "reason": _clean_text(reason, 500) or "Cancelación administrativa",
        })
        return self.outbox(user)

    def schedule_case(
        self,
        user: dict[str, Any],
        case_id: str,
        business_hours: float,
        start_at: str | None = None,
    ) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede aplicar un calendario al expediente.")
        case_value = _safe_segment(case_id, "case_id")
        self.operations.state(user, case_value)
        calendar_payload = self.calendar(user)
        calendar = BusinessCalendar(calendar_payload["calendar"])
        start = _parse_datetime(start_at, "start_at") if start_at else self._now()
        due = calendar.add_business_hours(start, float(business_hours))
        operation = self.operations.update_deadline(user, case_value, due.isoformat(), max(1, int(round(float(business_hours)))))
        schedule = {
            "case_id": case_value,
            "calendar": calendar.config,
            "calendar_sha256": calendar_payload["calendar_sha256"],
            "start_at": start.isoformat(timespec="seconds"),
            "due_at": due.isoformat(timespec="seconds"),
            "business_hours": float(business_hours),
            "legal_deadline": False,
        }
        event = self._append("calendar.deadline_applied", user, schedule)
        return {"event": event, "schedule": schedule, "operations": operation["state"], "business_sla": self.case_business_sla(user, case_value)}

    def case_business_sla(self, user: dict[str, Any], case_id: str) -> dict[str, Any] | None:
        case_value = _safe_segment(case_id, "case_id")
        self.operations.state(user, case_value)
        schedule = self._state()["schedules"].get(case_value)
        if not schedule:
            return None
        calendar = BusinessCalendar(schedule["calendar"])
        due = _parse_datetime(schedule["due_at"])
        now = self._now()
        remaining = calendar.business_hours_between(now, due)
        total = max(0.01, float(schedule["business_hours"]))
        if now > due:
            status = "overdue"
        elif remaining <= max(1.0, total * 0.2):
            status = "at_risk"
        else:
            status = "in_time"
        return {
            **schedule,
            "status": status,
            "business_hours_remaining": remaining,
            "percent_elapsed": max(0, min(100, round((1 - max(remaining, 0) / total) * 100))),
            "notice": "Cálculo operativo; requiere validación profesional si se relaciona con un término legal.",
        }

    def workload(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        users = self._users()
        if user.get("role") != "admin":
            users = [item for item in users if str(item["id"]) == str(user.get("id"))]
        portfolio = self.operations.portfolio(user)
        rows: list[dict[str, Any]] = []
        for professional in users:
            legal = qa = overdue = at_risk = alerts = critical = 0
            for case in portfolio.get("cases", []):
                operations = case.get("operations") or {}
                is_legal = (operations.get("assigned_specialist") or {}).get("id") == professional["id"]
                is_qa = (operations.get("assigned_qa") or {}).get("id") == professional["id"]
                if not (is_legal or is_qa):
                    continue
                legal += bool(is_legal)
                qa += bool(is_qa)
                overdue += case.get("sla", {}).get("status") == "overdue"
                at_risk += case.get("sla", {}).get("status") == "at_risk"
                active = [item for item in case.get("alerts", []) if not item.get("acknowledged")]
                alerts += len(active)
                critical += sum(item.get("severity") == "critical" for item in active)
            score = round(legal * 2 + qa * 1.5 + overdue * 5 + at_risk * 3 + critical * 4, 1)
            rows.append({
                "professional": professional,
                "legal_assignments": legal,
                "qa_assignments": qa,
                "overdue": overdue,
                "at_risk": at_risk,
                "active_alerts": alerts,
                "critical_alerts": critical,
                "load_score": score,
                "load_band": "critical" if score >= 30 else "high" if score >= 18 else "balanced" if score >= 6 else "available",
            })
        rows.sort(key=lambda item: item["load_score"], reverse=True)
        return {
            "schema_version": M32_7_SCHEMA,
            "scope": "all" if user.get("role") == "admin" else "personal",
            "professionals": rows,
            "notice": "El puntaje sirve para distribución operativa y no mide calidad jurídica ni productividad individual.",
        }

    def case_notifications(self, user: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_value = _safe_segment(case_id, "case_id")
        operation = self.operations.state(user, case_value)
        rows = [item for item in self._state()["notifications"].values() if item.get("case_id") == case_value]
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {
            "schema_version": M32_7_SCHEMA,
            "case_id": case_value,
            "notifications": rows,
            "business_sla": self.case_business_sla(user, case_value),
            "operations": operation,
            "audit": self.verify_chain(),
        }

    def dashboard(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        inbox = self.inbox(user)
        workload = self.workload(user)
        calendar = self.calendar(user)
        policy = self.policy(user)
        outbox = self.outbox(user) if user.get("role") == "admin" else None
        return {
            "schema_version": M32_7_SCHEMA,
            "inbox": inbox,
            "workload": workload,
            "calendar": calendar,
            "policy": policy,
            "outbox": outbox,
            "audit": self.verify_chain(),
            "capabilities": {
                "evaluate": user.get("role") == "admin",
                "manage_calendar": user.get("role") == "admin",
                "manage_policy": user.get("role") == "admin",
                "view_outbox": user.get("role") == "admin",
            },
            "notice": (
                "Las notificaciones M32.7 apoyan la operación. No sustituyen revisión profesional, "
                "términos legales ni constancias de entrega externa."
            ),
        }


__all__ = [
    "ApprovalNotificationCenter",
    "BusinessCalendar",
    "NotificationIntegrityError",
    "M32_7_SCHEMA",
    "DEFAULT_CALENDAR",
    "DEFAULT_POLICY",
    "PORTFOLIO_CODES",
]
