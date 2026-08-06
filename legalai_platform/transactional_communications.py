from __future__ import annotations

"""Comunicaciones transaccionales auditables M32.8.

Esta capa consume la cola externa M32.7, conserva plantillas versionadas y
registra intentos, aceptación y recibos sintéticos. El proveedor incluido es
exclusivamente sandbox: no realiza entrega externa real ni acredita recepción.
"""

from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.approval_notification_center import (
    ApprovalNotificationCenter,
    NotificationIntegrityError,
)


M32_8_SCHEMA = "M32.8"
BOGOTA = ZoneInfo("America/Bogota")
PROFESSIONAL_ROLES = frozenset({"specialist", "admin", "qa"})
TERMINAL_STATUSES = frozenset({
    "delivered_sandbox",
    "bounced_sandbox",
    "rejected_sandbox",
    "complained_sandbox",
    "cancelled",
    "dead_letter",
})
RECEIPT_STATUSES = frozenset({"delivered", "bounced", "rejected", "complained", "deferred"})
ALLOWED_TEMPLATE_VARIABLES = frozenset({
    "title",
    "product_code",
    "case_id",
    "due_at",
    "recipient_name",
})
_LOCK = RLock()

DEFAULT_POLICY = {
    "sandbox_enabled": True,
    "provider": "sandbox",
    "real_delivery_enabled": False,
    "max_attempts": 3,
    "initial_backoff_seconds": 60,
    "max_backoff_seconds": 3600,
    "batch_size": 25,
}

DEFAULT_TEMPLATE = {
    "template_id": "professional-alert",
    "version": 1,
    "name": "Alerta profesional protegida",
    "subject": "LegalAIZ.it · {{title}}",
    "body": (
        "Hola {{recipient_name}}.\n\n"
        "Existe una actuación pendiente para el producto {{product_code}} "
        "en el expediente {{case_id}}. Fecha objetivo: {{due_at}}.\n\n"
        "Ingrese a la Mesa Jurídica de LegalAIZ.it para consultar el detalle protegido. "
        "Este mensaje no contiene el documento ni información reservada del cliente."
    ),
    "created_by": {"id": "system", "role": "system", "name": "LegalAIZ.it"},
    "created_at": "2026-08-06T09:00:00-05:00",
    "status": "active",
    "contains_document_content": False,
    "attachments_allowed": False,
}


class CommunicationsIntegrityError(ApprovalDeskError):
    pass


class DeliveryAttemptError(ApprovalDeskError):
    def __init__(self, message: str, *, code: str = "provider_error", retryable: bool = True):
        super().__init__(message)
        self.code = str(code or "provider_error")[:80]
        self.retryable = bool(retryable)


class DeliveryProvider(Protocol):
    name: str
    real_delivery: bool

    def deliver(self, *, address: str, subject: str, body: str, idempotency_key: str) -> dict[str, Any]: ...


class SandboxEmailProvider:
    name = "sandbox"
    real_delivery = False

    def deliver(self, *, address: str, subject: str, body: str, idempotency_key: str) -> dict[str, Any]:
        if not _valid_email(address):
            raise DeliveryAttemptError("El destinatario no tiene un correo válido.", code="invalid_recipient", retryable=False)
        if not subject.strip() or not body.strip():
            raise DeliveryAttemptError("La plantilla produjo un mensaje vacío.", code="empty_message", retryable=False)
        return {
            "provider": self.name,
            "provider_message_id": "SBX-" + sha256(idempotency_key.encode("utf-8")).hexdigest()[:24].upper(),
            "status": "accepted",
            "real_delivery": False,
            "sandbox": True,
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_segment(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ApprovalDeskError(f"{field} contiene caracteres no permitidos.")
    return text


def _clean_text(value: Any, limit: int = 1000) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "")).strip()[:limit]


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


def _actor(user: dict[str, Any]) -> dict[str, str]:
    actor_id = str(user.get("id") or "").strip()
    role = str(user.get("role") or "").strip().casefold()
    if not actor_id or role not in PROFESSIONAL_ROLES:
        raise PermissionDenied("La operación requiere un actor profesional autenticado.")
    return {"id": actor_id, "role": role, "name": _clean_text(user.get("name"), 120)}


def _valid_email(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(re.fullmatch(r"[^\s@]{1,64}@[^\s@]{1,190}", text))


def _template_hash(template: dict[str, Any]) -> str:
    material = {
        "template_id": template["template_id"],
        "version": int(template["version"]),
        "subject": template["subject"],
        "body": template["body"],
        "contains_document_content": False,
        "attachments_allowed": False,
    }
    return sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _validate_template(payload: dict[str, Any], *, template_id: str, version: int) -> dict[str, Any]:
    subject = str(payload.get("subject") or "").strip()
    body = str(payload.get("body") or "").strip()
    name = _clean_text(payload.get("name") or template_id, 120)
    if not subject or len(subject) > 180:
        raise ApprovalDeskError("El asunto debe tener entre 1 y 180 caracteres.")
    if not body or len(body) > 5000:
        raise ApprovalDeskError("El cuerpo debe tener entre 1 y 5.000 caracteres.")
    variables = set(re.findall(r"{{\s*([A-Za-z0-9_]+)\s*}}", subject + "\n" + body))
    unknown = sorted(variables - ALLOWED_TEMPLATE_VARIABLES)
    if unknown:
        raise ApprovalDeskError("La plantilla contiene variables no permitidas: " + ", ".join(unknown))
    if "{{" in re.sub(r"{{\s*[A-Za-z0-9_]+\s*}}", "", subject + body):
        raise ApprovalDeskError("La plantilla contiene un marcador inválido o incompleto.")
    return {
        "template_id": _safe_segment(template_id, "template_id"),
        "version": int(version),
        "name": name,
        "subject": subject,
        "body": body,
        "status": "draft",
        "contains_document_content": False,
        "attachments_allowed": False,
    }


def _render(template: dict[str, Any], context: dict[str, Any]) -> tuple[str, str, str]:
    values = {key: _clean_text(context.get(key) or "Sin información", 500) for key in ALLOWED_TEMPLATE_VARIABLES}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in ALLOWED_TEMPLATE_VARIABLES:
            raise ApprovalDeskError(f"La variable {key} no está permitida.")
        return values[key]

    subject = re.sub(r"{{\s*([A-Za-z0-9_]+)\s*}}", replace, template["subject"])
    body = re.sub(r"{{\s*([A-Za-z0-9_]+)\s*}}", replace, template["body"])
    if "{{" in subject or "{{" in body:
        raise ApprovalDeskError("La plantilla conserva variables sin resolver.")
    rendered_hash = sha256((subject + "\n" + body).encode("utf-8")).hexdigest()
    return subject, body, rendered_hash


class TransactionalCommunications:
    """Plantillas, cola de despacho, reintentos y evidencia sintética M32.8."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        notification_center: ApprovalNotificationCenter | None = None,
        db_factory: Callable[[], Any] | None = None,
        now_factory: Callable[[], datetime] | None = None,
        provider: DeliveryProvider | None = None,
    ):
        self.root = Path(root or (core.RUNTIME / "approval-desk")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.notification_center = notification_center or ApprovalNotificationCenter(self.root)
        self.db_factory = db_factory or core.db
        self.now_factory = now_factory or (lambda: datetime.now(BOGOTA))
        self.provider = provider or SandboxEmailProvider()
        self.directory = self.root / "transactional-communications"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / "events.jsonl"

    def _now(self) -> datetime:
        value = self.now_factory()
        if value.tzinfo is None:
            value = value.replace(tzinfo=BOGOTA)
        return value.astimezone(BOGOTA)

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.events_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise CommunicationsIntegrityError("La bitácora M32.8 contiene un registro inválido.")
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
                raise CommunicationsIntegrityError("La cadena M32.8 está alterada; no se admiten nuevas actuaciones.")
            sequence = int(integrity["events"]) + 1
            event = {
                "schema_version": M32_8_SCHEMA,
                "sequence": sequence,
                "event_id": f"COM-EVT-{sequence:07d}",
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

    @staticmethod
    def _default_template() -> dict[str, Any]:
        item = dict(DEFAULT_TEMPLATE)
        item["template_sha256"] = _template_hash(item)
        item["approved_by"] = {"id": "system", "role": "system", "name": "LegalAIZ.it"}
        item["approved_at"] = item["created_at"]
        return item

    def _state(self) -> dict[str, Any]:
        default = self._default_template()
        state: dict[str, Any] = {
            "policy": dict(DEFAULT_POLICY),
            "templates": {default["template_id"]: {str(default["version"]): default}},
            "active_templates": {default["template_id"]: int(default["version"])},
            "dispatches": {},
            "receipt_ids": set(),
        }
        for event in self._read_events():
            payload = event.get("payload") or {}
            kind = event.get("event_type")
            if kind == "policy.updated":
                state["policy"].update(payload.get("policy") or {})
            elif kind == "template.version_created":
                template = dict(payload.get("template") or {})
                state["templates"].setdefault(template["template_id"], {})[str(template["version"])] = template
            elif kind == "template.activated":
                template_id = payload.get("template_id")
                version = int(payload.get("version") or 0)
                state["active_templates"][template_id] = version
                template = state["templates"].get(template_id, {}).get(str(version))
                if template:
                    template["status"] = "active"
                    template["approved_by"] = event.get("actor")
                    template["approved_at"] = event.get("created_at")
            elif kind == "dispatch.imported":
                dispatch = dict(payload.get("dispatch") or {})
                dispatch["receipts"] = []
                state["dispatches"][dispatch["dispatch_id"]] = dispatch
            elif kind == "dispatch.claimed":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["status"] = "processing"
                    item["claimed_at"] = event.get("created_at")
            elif kind == "dispatch.attempted":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["attempts"] = int(payload.get("attempt") or item.get("attempts") or 0)
                    item["last_attempt_at"] = event.get("created_at")
                    item["last_error_code"] = payload.get("error_code")
            elif kind == "dispatch.retry_scheduled":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["status"] = "retry_scheduled"
                    item["next_attempt_at"] = payload.get("next_attempt_at")
                    item["last_error_code"] = payload.get("error_code")
            elif kind == "dispatch.accepted":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["status"] = "accepted_sandbox"
                    item["accepted_at"] = event.get("created_at")
                    item["provider"] = payload.get("provider")
                    item["provider_message_id"] = payload.get("provider_message_id")
                    item["rendered_sha256"] = payload.get("rendered_sha256")
                    item["real_delivery"] = False
            elif kind == "dispatch.receipt_recorded":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                receipt_id = payload.get("provider_event_id")
                if receipt_id:
                    state["receipt_ids"].add(receipt_id)
                if item:
                    receipt = {
                        "provider_event_id": receipt_id,
                        "provider_status": payload.get("provider_status"),
                        "occurred_at": payload.get("occurred_at"),
                        "recorded_at": event.get("created_at"),
                        "synthetic": True,
                        "detail": payload.get("detail"),
                    }
                    item["receipts"].append(receipt)
                    status = payload.get("provider_status")
                    if status == "deferred":
                        item["status"] = "retry_scheduled"
                        item["next_attempt_at"] = payload.get("next_attempt_at")
                    else:
                        item["status"] = f"{status}_sandbox"
            elif kind == "dispatch.cancelled":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["status"] = "cancelled"
                    item["cancelled_at"] = event.get("created_at")
                    item["cancellation_reason"] = payload.get("reason")
            elif kind == "dispatch.dead_lettered":
                item = state["dispatches"].get(payload.get("dispatch_id"))
                if item:
                    item["status"] = "dead_letter"
                    item["dead_lettered_at"] = event.get("created_at")
                    item["last_error_code"] = payload.get("error_code")
        return state

    def _resolve_recipient(self, recipient_id: str) -> dict[str, Any] | None:
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            active_clause = "AND active=1" if "active" in columns else ""
            email_column = "email" if "email" in columns else "NULL AS email"
            row = con.execute(
                f"SELECT id,name,role,{email_column} FROM users WHERE id=? {active_clause}",
                (recipient_id,),
            ).fetchone()
        finally:
            con.close()
        return dict(row) if row else None

    def policy(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        return {
            "schema_version": M32_8_SCHEMA,
            "policy": dict(self._state()["policy"]),
            "real_delivery_active": False,
            "notice": "El proveedor M32.8 opera exclusivamente en sandbox y no acredita entrega externa real.",
            "capabilities": {"manage": user.get("role") == "admin"},
        }

    def update_policy(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar la política de comunicaciones.")
        allowed = {"sandbox_enabled", "max_attempts", "initial_backoff_seconds", "max_backoff_seconds", "batch_size"}
        if set(payload or {}) - allowed:
            raise ApprovalDeskError("La política contiene campos no permitidos.")
        current = dict(self._state()["policy"])
        if "sandbox_enabled" in payload:
            current["sandbox_enabled"] = bool(payload["sandbox_enabled"])
        bounds = {
            "max_attempts": (1, 10),
            "initial_backoff_seconds": (5, 86400),
            "max_backoff_seconds": (5, 604800),
            "batch_size": (1, 200),
        }
        for field, (minimum, maximum) in bounds.items():
            if field in payload:
                value = int(payload[field])
                if value < minimum or value > maximum:
                    raise ApprovalDeskError(f"{field} debe estar entre {minimum} y {maximum}.")
                current[field] = value
        if current["max_backoff_seconds"] < current["initial_backoff_seconds"]:
            raise ApprovalDeskError("El backoff máximo no puede ser inferior al inicial.")
        current["provider"] = "sandbox"
        current["real_delivery_enabled"] = False
        event = self._append("policy.updated", user, {"policy": current})
        return {"event": event, **self.policy(user)}

    def templates(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        state = self._state()
        rows: list[dict[str, Any]] = []
        for template_id, versions in state["templates"].items():
            active = state["active_templates"].get(template_id)
            for version_text, raw in versions.items():
                item = dict(raw)
                item["active"] = int(version_text) == int(active or 0)
                item["can_activate"] = (
                    user.get("role") in {"admin", "qa"}
                    and not item["active"]
                    and str((item.get("created_by") or {}).get("id")) != str(user.get("id"))
                )
                rows.append(item)
        rows.sort(key=lambda item: (item["template_id"], -int(item["version"])))
        return {
            "schema_version": M32_8_SCHEMA,
            "templates": rows,
            "active_templates": state["active_templates"],
            "allowed_variables": sorted(ALLOWED_TEMPLATE_VARIABLES),
            "notice": "Las plantillas no admiten adjuntos ni contenido documental del expediente.",
        }

    def create_template_version(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede crear versiones de plantilla.")
        template_id = _safe_segment(payload.get("template_id") or "professional-alert", "template_id")
        state = self._state()
        existing = state["templates"].get(template_id, {})
        version = max([int(value) for value in existing] or [0]) + 1
        template = _validate_template(payload, template_id=template_id, version=version)
        template["created_by"] = _actor(user)
        template["created_at"] = self._now().isoformat(timespec="seconds")
        template["template_sha256"] = _template_hash(template)
        event = self._append("template.version_created", user, {"template": template})
        return {"event": event, "template": template, "requires_independent_activation": True}

    def activate_template(self, user: dict[str, Any], template_id: str, version: int) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("La activación requiere administración o QA.")
        template_key = _safe_segment(template_id, "template_id")
        state = self._state()
        template = state["templates"].get(template_key, {}).get(str(int(version)))
        if not template:
            raise ApprovalDeskError("La versión de plantilla no existe.")
        if str((template.get("created_by") or {}).get("id")) == str(user.get("id")):
            raise PermissionDenied("La persona creadora no puede activar su propia versión.")
        if state["active_templates"].get(template_key) == int(version):
            return self.templates(user)
        event = self._append("template.activated", user, {
            "template_id": template_key,
            "version": int(version),
            "template_sha256": template["template_sha256"],
            "separation_of_duties": True,
        })
        return {"event": event, **self.templates(user)}

    def _active_template(self, state: dict[str, Any], template_id: str) -> dict[str, Any]:
        version = state["active_templates"].get(template_id)
        template = state["templates"].get(template_id, {}).get(str(version))
        if not template:
            raise ApprovalDeskError("No existe una plantilla activa para el despacho.")
        if template.get("template_sha256") != _template_hash(template):
            raise CommunicationsIntegrityError("La plantilla activa no coincide con su SHA-256.")
        return template

    def sync_outbox(self, user: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede sincronizar la cola M32.7.")
        if not self.notification_center.verify_chain()["valid"]:
            raise NotificationIntegrityError("La sincronización está bloqueada por una cadena M32.7 inválida.")
        state = self._state()
        source = self.notification_center._state()
        imported_sources = {item.get("source_message_id") for item in state["dispatches"].values()}
        template = self._active_template(state, "professional-alert")
        imported: list[str] = []
        skipped = 0
        for message in source["outbox"].values():
            if message.get("status") != "queued" or message.get("message_id") in imported_sources:
                skipped += 1
                continue
            notification = source["notifications"].get(message.get("notification_id")) or {}
            context = {
                "title": notification.get("title") or "Actuación pendiente",
                "product_code": notification.get("product_code") or "Sin producto",
                "case_id": notification.get("case_id") or "Sin expediente",
                "due_at": notification.get("due_at") or "Sin fecha objetivo",
                "recipient_name": notification.get("recipient_name") or "profesional",
            }
            dispatch_id = "DSP-" + uuid4().hex[:18].upper()
            idempotency_key = sha256(
                f"{message.get('message_id')}|{template['template_sha256']}|{message.get('recipient_id')}".encode("utf-8")
            ).hexdigest()
            dispatch = {
                "dispatch_id": dispatch_id,
                "source_message_id": message.get("message_id"),
                "notification_id": message.get("notification_id"),
                "recipient_id": str(message.get("recipient_id") or ""),
                "recipient_hint": message.get("recipient_hint"),
                "recipient_address_stored": False,
                "channel": "email",
                "template_id": template["template_id"],
                "template_version": int(template["version"]),
                "template_sha256": template["template_sha256"],
                "context": context,
                "contains_document_content": False,
                "attachments": [],
                "status": "queued",
                "attempts": 0,
                "next_attempt_at": self._now().isoformat(timespec="seconds"),
                "idempotency_key": idempotency_key,
                "imported_at": self._now().isoformat(timespec="seconds"),
                "provider": "sandbox",
                "real_delivery": False,
            }
            self._append("dispatch.imported", user, {"dispatch": dispatch})
            imported.append(dispatch_id)
        event = self._append("outbox.sync_completed", user, {
            "imported": len(imported),
            "skipped": skipped,
            "source_chain_valid": True,
            "real_delivery_performed": False,
        })
        return {
            "schema_version": M32_8_SCHEMA,
            "event": event,
            "imported_dispatches": imported,
            "skipped": skipped,
            "real_delivery_performed": False,
            "audit": self.verify_chain(),
        }

    def _retry_delay(self, attempt: int, policy: dict[str, Any]) -> int:
        initial = int(policy["initial_backoff_seconds"])
        maximum = int(policy["max_backoff_seconds"])
        return min(maximum, initial * (2 ** max(0, attempt - 1)))

    def process(self, user: dict[str, Any], *, limit: int | None = None) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede procesar despachos.")
        if not self.verify_chain()["valid"]:
            raise CommunicationsIntegrityError("El procesamiento está bloqueado por una cadena M32.8 inválida.")
        if not self.notification_center.verify_chain()["valid"]:
            raise NotificationIntegrityError("El procesamiento está bloqueado por una cadena M32.7 inválida.")
        state = self._state()
        policy = state["policy"]
        if not policy.get("sandbox_enabled"):
            raise ApprovalDeskError("El proveedor sandbox está deshabilitado y no existe un proveedor real autorizado.")
        cap = max(1, min(int(limit or policy["batch_size"]), int(policy["batch_size"]), 200))
        now = self._now()
        eligible = [
            item for item in state["dispatches"].values()
            if item.get("status") in {"queued", "retry_scheduled"}
            and _parse_datetime(item.get("next_attempt_at"), "next_attempt_at") <= now
        ]
        eligible.sort(key=lambda item: (str(item.get("next_attempt_at")), str(item.get("dispatch_id"))))
        accepted: list[str] = []
        retried: list[str] = []
        dead_lettered: list[str] = []
        for dispatch in eligible[:cap]:
            dispatch_id = dispatch["dispatch_id"]
            attempt = int(dispatch.get("attempts") or 0) + 1
            self._append("dispatch.claimed", user, {"dispatch_id": dispatch_id, "attempt": attempt})
            recipient = self._resolve_recipient(dispatch["recipient_id"])
            try:
                if not recipient or not _valid_email(recipient.get("email")):
                    raise DeliveryAttemptError("No existe un correo activo y válido para el destinatario.", code="recipient_unavailable", retryable=False)
                template = state["templates"].get(dispatch["template_id"], {}).get(str(dispatch["template_version"]))
                if not template or template.get("template_sha256") != dispatch.get("template_sha256"):
                    raise DeliveryAttemptError("La versión de plantilla del despacho no está disponible o fue alterada.", code="template_integrity", retryable=False)
                subject, body, rendered_hash = _render(template, dispatch["context"])
                result = self.provider.deliver(
                    address=str(recipient["email"]),
                    subject=subject,
                    body=body,
                    idempotency_key=dispatch["idempotency_key"],
                )
                if bool(result.get("real_delivery")):
                    raise DeliveryAttemptError("M32.8 no autoriza proveedores de entrega real.", code="real_delivery_blocked", retryable=False)
                self._append("dispatch.attempted", user, {
                    "dispatch_id": dispatch_id,
                    "attempt": attempt,
                    "provider": str(result.get("provider") or self.provider.name),
                    "error_code": None,
                    "recipient_address_stored": False,
                })
                self._append("dispatch.accepted", user, {
                    "dispatch_id": dispatch_id,
                    "provider": str(result.get("provider") or self.provider.name),
                    "provider_message_id": _clean_text(result.get("provider_message_id"), 160),
                    "rendered_sha256": rendered_hash,
                    "sandbox": True,
                    "real_delivery": False,
                    "recipient_address_stored": False,
                })
                accepted.append(dispatch_id)
            except DeliveryAttemptError as exc:
                self._append("dispatch.attempted", user, {
                    "dispatch_id": dispatch_id,
                    "attempt": attempt,
                    "provider": getattr(self.provider, "name", "sandbox"),
                    "error_code": exc.code,
                    "recipient_address_stored": False,
                })
                if exc.retryable and attempt < int(policy["max_attempts"]):
                    next_attempt = now + timedelta(seconds=self._retry_delay(attempt, policy))
                    self._append("dispatch.retry_scheduled", user, {
                        "dispatch_id": dispatch_id,
                        "attempt": attempt,
                        "next_attempt_at": next_attempt.isoformat(timespec="seconds"),
                        "error_code": exc.code,
                    })
                    retried.append(dispatch_id)
                else:
                    self._append("dispatch.dead_lettered", user, {
                        "dispatch_id": dispatch_id,
                        "attempt": attempt,
                        "error_code": exc.code,
                        "reason": _clean_text(str(exc), 500),
                    })
                    dead_lettered.append(dispatch_id)
            except Exception:
                self._append("dispatch.attempted", user, {
                    "dispatch_id": dispatch_id,
                    "attempt": attempt,
                    "provider": getattr(self.provider, "name", "sandbox"),
                    "error_code": "unexpected_provider_error",
                    "recipient_address_stored": False,
                })
                if attempt < int(policy["max_attempts"]):
                    next_attempt = now + timedelta(seconds=self._retry_delay(attempt, policy))
                    self._append("dispatch.retry_scheduled", user, {
                        "dispatch_id": dispatch_id,
                        "attempt": attempt,
                        "next_attempt_at": next_attempt.isoformat(timespec="seconds"),
                        "error_code": "unexpected_provider_error",
                    })
                    retried.append(dispatch_id)
                else:
                    self._append("dispatch.dead_lettered", user, {
                        "dispatch_id": dispatch_id,
                        "attempt": attempt,
                        "error_code": "unexpected_provider_error",
                        "reason": "Error no clasificado del proveedor sandbox.",
                    })
                    dead_lettered.append(dispatch_id)
        event = self._append("batch.processed", user, {
            "eligible": len(eligible),
            "processed": min(len(eligible), cap),
            "accepted_sandbox": len(accepted),
            "retry_scheduled": len(retried),
            "dead_lettered": len(dead_lettered),
            "real_delivery_performed": False,
        })
        return {
            "schema_version": M32_8_SCHEMA,
            "event": event,
            "accepted_sandbox": accepted,
            "retry_scheduled": retried,
            "dead_lettered": dead_lettered,
            "real_delivery_performed": False,
            "audit": self.verify_chain(),
        }

    def record_receipt(
        self,
        user: dict[str, Any],
        dispatch_id: str,
        *,
        provider_status: str,
        provider_event_id: str,
        occurred_at: str | None = None,
        detail: str = "",
        synthetic: bool = True,
    ) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("El registro de recibos requiere administración o QA.")
        if not synthetic:
            raise ApprovalDeskError("M32.8 solo admite recibos sintéticos hasta configurar un proveedor real validado.")
        dispatch_key = _safe_segment(dispatch_id, "dispatch_id")
        status = str(provider_status or "").strip().casefold()
        if status not in RECEIPT_STATUSES:
            raise ApprovalDeskError("El estado del recibo no es válido.")
        event_id = _safe_segment(provider_event_id, "provider_event_id")
        state = self._state()
        dispatch = state["dispatches"].get(dispatch_key)
        if not dispatch:
            raise ApprovalDeskError("El despacho no existe.")
        if event_id in state["receipt_ids"]:
            return self.queue(user)
        if dispatch.get("status") not in {"accepted_sandbox", "retry_scheduled", "delivered_sandbox", "bounced_sandbox"}:
            raise ApprovalDeskError("El despacho no admite recibos en su estado actual.")
        occurred = _parse_datetime(occurred_at, "occurred_at") if occurred_at else self._now()
        payload = {
            "dispatch_id": dispatch_key,
            "provider_event_id": event_id,
            "provider_status": status,
            "occurred_at": occurred.isoformat(timespec="seconds"),
            "detail": _clean_text(detail, 500),
            "synthetic": True,
            "real_delivery_evidence": False,
        }
        if status == "deferred":
            delay = self._retry_delay(max(1, int(dispatch.get("attempts") or 1)), state["policy"])
            payload["next_attempt_at"] = (self._now() + timedelta(seconds=delay)).isoformat(timespec="seconds")
        event = self._append("dispatch.receipt_recorded", user, payload)
        return {"event": event, **self.queue(user)}

    def cancel(self, user: dict[str, Any], dispatch_id: str, reason: str) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede cancelar despachos.")
        dispatch_key = _safe_segment(dispatch_id, "dispatch_id")
        state = self._state()
        dispatch = state["dispatches"].get(dispatch_key)
        if not dispatch:
            raise ApprovalDeskError("El despacho no existe.")
        if dispatch.get("status") in TERMINAL_STATUSES:
            raise ApprovalDeskError("El despacho ya está en un estado terminal.")
        event = self._append("dispatch.cancelled", user, {
            "dispatch_id": dispatch_key,
            "reason": _clean_text(reason, 500) or "Cancelación administrativa",
            "provider_recall_performed": False,
        })
        return {"event": event, **self.queue(user)}

    def queue(self, user: dict[str, Any], *, status: str | None = None, limit: int = 200) -> dict[str, Any]:
        _actor(user)
        rows = list(self._state()["dispatches"].values())
        if user.get("role") == "specialist":
            rows = [item for item in rows if str(item.get("recipient_id")) == str(user.get("id"))]
        if status:
            status_value = str(status).strip().casefold()
            rows = [item for item in rows if item.get("status") == status_value]
        rows.sort(key=lambda item: str(item.get("imported_at") or ""), reverse=True)
        rows = rows[: max(1, min(int(limit), 500))]
        counts: dict[str, int] = {}
        for item in rows:
            counts[item.get("status") or "unknown"] = counts.get(item.get("status") or "unknown", 0) + 1
        return {
            "schema_version": M32_8_SCHEMA,
            "scope": "personal" if user.get("role") == "specialist" else "professional",
            "metrics": {
                "total": len(rows),
                "queued": counts.get("queued", 0),
                "retry_scheduled": counts.get("retry_scheduled", 0),
                "accepted_sandbox": counts.get("accepted_sandbox", 0),
                "delivered_sandbox": counts.get("delivered_sandbox", 0),
                "bounced_sandbox": counts.get("bounced_sandbox", 0),
                "dead_letter": counts.get("dead_letter", 0),
                "cancelled": counts.get("cancelled", 0),
            },
            "dispatches": rows,
            "real_delivery_active": False,
            "recipient_addresses_stored": any(item.get("recipient_address_stored", True) for item in rows),
            "contains_document_content": any(item.get("contains_document_content", True) for item in rows),
            "audit": self.verify_chain(),
        }

    def case_communications(self, user: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_key = _safe_segment(case_id, "case_id")
        operation = self.notification_center.operations.state(user, case_key)
        rows = [
            item for item in self._state()["dispatches"].values()
            if str((item.get("context") or {}).get("case_id")) == case_key
        ]
        if user.get("role") == "specialist":
            rows = [item for item in rows if str(item.get("recipient_id")) == str(user.get("id"))]
        rows.sort(key=lambda item: str(item.get("imported_at") or ""), reverse=True)
        return {
            "schema_version": M32_8_SCHEMA,
            "case_id": case_key,
            "communications": rows,
            "operations": operation,
            "real_delivery_active": False,
            "audit": self.verify_chain(),
        }

    def dashboard(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        return {
            "schema_version": M32_8_SCHEMA,
            "queue": self.queue(user),
            "policy": self.policy(user),
            "templates": self.templates(user),
            "audit": self.verify_chain(),
            "source_audit": self.notification_center.verify_chain(),
            "capabilities": {
                "sync": user.get("role") == "admin",
                "process": user.get("role") == "admin",
                "manage_policy": user.get("role") == "admin",
                "create_template": user.get("role") == "admin",
                "record_receipt": user.get("role") in {"admin", "qa"},
            },
            "notice": (
                "M32.8 aporta trazabilidad de plantillas y despachos en sandbox. "
                "No envía correos reales ni sustituye constancias emitidas por un proveedor validado."
            ),
        }


__all__ = [
    "TransactionalCommunications",
    "CommunicationsIntegrityError",
    "DeliveryAttemptError",
    "SandboxEmailProvider",
    "M32_8_SCHEMA",
    "DEFAULT_POLICY",
    "DEFAULT_TEMPLATE",
]
