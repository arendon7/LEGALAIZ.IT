from __future__ import annotations

"""Gobierno de consentimientos, preferencias y supresiones M32.9.

La capa distingue finalidades operativas, transaccionales, comerciales y de
cobranza. No sustituye la valoración jurídica de cada tratamiento ni habilita
canales reales. Las decisiones se apoyan en evidencia versionada y una cadena
append-only independiente.
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
from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.transactional_communications import TransactionalCommunications


M32_9_SCHEMA = "M32.9"
BOGOTA = ZoneInfo("America/Bogota")
PROFESSIONAL_ROLES = frozenset({"specialist", "admin", "qa"})
CHANNELS = frozenset({"email", "sms", "whatsapp", "phone"})
PURPOSES = frozenset({
    "professional_operational",
    "service_transactional",
    "commercial_marketing",
    "collections",
})
RELATIONSHIP_TYPES = frozenset({"professional", "client", "vendor", "counterparty"})
RELATIONSHIP_BASES = frozenset({"contract", "user_request", "legal_obligation", "consent", "operational_relationship"})
PREFERENCE_BASES = frozenset({"consent", "contract", "user_request", "legal_obligation", "operational_relationship"})
SUPPRESSION_SCOPES = frozenset({"global", "channel", "purpose", "purpose_channel"})
_LOCK = RLock()

DEFAULT_POLICY = {
    "timezone": "America/Bogota",
    "weekdays": [0, 1, 2, 3, 4],
    "weekday_open": "07:00",
    "weekday_close": "19:00",
    "saturday_open": "08:00",
    "saturday_close": "15:00",
    "holidays": [],
    "official_holiday_calendar": False,
    "max_contacts_per_day": 1,
    "max_channels_per_7_days": 1,
    "commercial_requires_explicit_consent": True,
    "collections_requires_authorized_channel": True,
    "real_contact_enabled": False,
}

DEFAULT_NOTICE = {
    "notice_id": "contact-governance",
    "version": 1,
    "name": "Aviso de canales y finalidades",
    "text": (
        "LegalAIZ.it informa de manera diferenciada las finalidades de contacto, "
        "los canales elegidos, los derechos del titular y los mecanismos para "
        "modificar preferencias, revocar autorizaciones o solicitar supresión."
    ),
    "status": "active",
    "created_by": {"id": "system", "role": "system", "name": "LegalAIZ.it"},
    "created_at": "2026-08-06T11:00:00-05:00",
}


class ContactGovernanceIntegrityError(ApprovalDeskError):
    pass


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
        text_value = str(value or "").strip()
        if not text_value:
            raise ApprovalDeskError(f"{field} es obligatoria.")
        try:
            parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ApprovalDeskError(f"{field} debe usar formato ISO 8601.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BOGOTA)
    return parsed.astimezone(BOGOTA)


def _clock(value: Any, field: str) -> time:
    try:
        parsed = time.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ApprovalDeskError(f"{field} debe usar formato HH:MM.") from exc
    if parsed.second or parsed.microsecond:
        raise ApprovalDeskError(f"{field} no admite segundos.")
    return parsed


def _actor(user: dict[str, Any]) -> dict[str, str]:
    actor_id = str(user.get("id") or "").strip()
    role = str(user.get("role") or "").strip().casefold()
    if not actor_id or role not in PROFESSIONAL_ROLES:
        raise PermissionDenied("La operación requiere un actor profesional autenticado.")
    return {"id": actor_id, "role": role, "name": _clean_text(user.get("name"), 120)}


def _notice_hash(notice: dict[str, Any]) -> str:
    material = {
        "notice_id": notice["notice_id"],
        "version": int(notice["version"]),
        "name": notice["name"],
        "text": notice["text"],
    }
    return sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _preference_key(subject_id: str, purpose: str, channel: str) -> str:
    return f"{subject_id}|{purpose}|{channel}"


class ContactGovernance:
    """Registro append-only y motor de decisión de contacto M32.9."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        db_factory: Callable[[], Any] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self.root = Path(root or (core.RUNTIME / "approval-desk")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_factory = db_factory or core.db
        self.now_factory = now_factory or (lambda: datetime.now(BOGOTA))
        self.directory = self.root / "contact-governance"
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
                raise ContactGovernanceIntegrityError("La bitácora M32.9 contiene un registro inválido.")
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
                raise ContactGovernanceIntegrityError("La cadena M32.9 está alterada; no se admiten nuevas actuaciones.")
            sequence = int(integrity["events"]) + 1
            event = {
                "schema_version": M32_9_SCHEMA,
                "sequence": sequence,
                "event_id": f"CGV-EVT-{sequence:07d}",
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
    def _default_notice() -> dict[str, Any]:
        notice = dict(DEFAULT_NOTICE)
        notice["notice_sha256"] = _notice_hash(notice)
        notice["approved_by"] = {"id": "system", "role": "system", "name": "LegalAIZ.it"}
        notice["approved_at"] = notice["created_at"]
        return notice

    def _state(self) -> dict[str, Any]:
        notice = self._default_notice()
        state: dict[str, Any] = {
            "policy": dict(DEFAULT_POLICY),
            "notices": {notice["notice_id"]: {str(notice["version"]): notice}},
            "active_notices": {notice["notice_id"]: int(notice["version"])},
            "relationships": {},
            "preferences": {},
            "suppressions": {},
            "decisions": [],
            "contacts": [],
        }
        for event in self._read_events():
            payload = event.get("payload") or {}
            kind = event.get("event_type")
            if kind == "policy.updated":
                state["policy"].update(payload.get("policy") or {})
            elif kind == "notice.version_created":
                item = dict(payload.get("notice") or {})
                state["notices"].setdefault(item["notice_id"], {})[str(item["version"])] = item
            elif kind == "notice.activated":
                notice_id = payload.get("notice_id")
                version = int(payload.get("version") or 0)
                state["active_notices"][notice_id] = version
                item = state["notices"].get(notice_id, {}).get(str(version))
                if item:
                    item["status"] = "active"
                    item["approved_by"] = event.get("actor")
                    item["approved_at"] = event.get("created_at")
            elif kind == "relationship.recorded":
                item = dict(payload.get("relationship") or {})
                state["relationships"][item["subject_id"]] = item
            elif kind == "preference.recorded":
                item = dict(payload.get("preference") or {})
                state["preferences"][_preference_key(item["subject_id"], item["purpose"], item["channel"])] = item
            elif kind == "suppression.added":
                item = dict(payload.get("suppression") or {})
                item["active"] = True
                state["suppressions"][item["suppression_id"]] = item
            elif kind == "suppression.lifted":
                item = state["suppressions"].get(payload.get("suppression_id"))
                if item:
                    item["active"] = False
                    item["lifted_at"] = event.get("created_at")
                    item["lifted_by"] = event.get("actor")
                    item["lift_reason"] = payload.get("reason")
            elif kind == "decision.recorded":
                state["decisions"].append(dict(payload.get("decision") or {}))
            elif kind == "contact.recorded":
                state["contacts"].append(dict(payload.get("contact") or {}))
        return state

    def _subject_profile(self, subject_id: str) -> dict[str, Any] | None:
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            active_col = "active" if "active" in columns else "1 AS active"
            row = con.execute(
                f"SELECT id,name,role,{active_col} FROM users WHERE id=?",
                (subject_id,),
            ).fetchone()
        finally:
            con.close()
        return dict(row) if row else None

    @staticmethod
    def _validate_policy(payload: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "timezone", "weekdays", "weekday_open", "weekday_close",
            "saturday_open", "saturday_close", "holidays",
            "max_contacts_per_day", "max_channels_per_7_days",
            "commercial_requires_explicit_consent",
            "collections_requires_authorized_channel",
        }
        if set(payload or {}) - allowed:
            raise ApprovalDeskError("La política contiene campos no permitidos.")
        candidate = dict(current)
        candidate.update(payload or {})
        try:
            ZoneInfo(str(candidate.get("timezone") or ""))
        except Exception as exc:
            raise ApprovalDeskError("La zona horaria no es válida.") from exc
        weekdays = sorted({int(item) for item in candidate.get("weekdays", [])})
        if not weekdays or any(item < 0 or item > 6 for item in weekdays):
            raise ApprovalDeskError("Los días hábiles deben estar entre 0 y 6.")
        weekday_open = _clock(candidate.get("weekday_open"), "weekday_open")
        weekday_close = _clock(candidate.get("weekday_close"), "weekday_close")
        saturday_open = _clock(candidate.get("saturday_open"), "saturday_open")
        saturday_close = _clock(candidate.get("saturday_close"), "saturday_close")
        if weekday_close <= weekday_open or saturday_close <= saturday_open:
            raise ApprovalDeskError("La hora de cierre debe ser posterior a la apertura.")
        holidays = sorted({date.fromisoformat(str(item)).isoformat() for item in candidate.get("holidays", [])})
        if len(holidays) > 500:
            raise ApprovalDeskError("No se admiten más de 500 cierres explícitos.")
        for field, minimum, maximum in (
            ("max_contacts_per_day", 1, 20),
            ("max_channels_per_7_days", 1, 4),
        ):
            value = int(candidate.get(field) or 0)
            if value < minimum or value > maximum:
                raise ApprovalDeskError(f"{field} debe estar entre {minimum} y {maximum}.")
            candidate[field] = value
        candidate.update({
            "timezone": str(candidate["timezone"]),
            "weekdays": weekdays,
            "weekday_open": weekday_open.strftime("%H:%M"),
            "weekday_close": weekday_close.strftime("%H:%M"),
            "saturday_open": saturday_open.strftime("%H:%M"),
            "saturday_close": saturday_close.strftime("%H:%M"),
            "holidays": holidays,
            "official_holiday_calendar": False,
            "real_contact_enabled": False,
            "commercial_requires_explicit_consent": bool(candidate.get("commercial_requires_explicit_consent", True)),
            "collections_requires_authorized_channel": bool(candidate.get("collections_requires_authorized_channel", True)),
        })
        return candidate

    def policy(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        return {
            "schema_version": M32_9_SCHEMA,
            "policy": dict(self._state()["policy"]),
            "real_contact_active": False,
            "notice": (
                "Los horarios y límites son una compuerta operativa conservadora. "
                "No sustituyen la interpretación jurídica ni un calendario oficial."
            ),
            "capabilities": {"manage": user.get("role") == "admin"},
        }

    def update_policy(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar la política de contacto.")
        current = self._state()["policy"]
        policy = self._validate_policy(payload, current)
        event = self._append("policy.updated", user, {"policy": policy})
        return {"event": event, **self.policy(user)}

    def notices(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        state = self._state()
        rows: list[dict[str, Any]] = []
        for notice_id, versions in state["notices"].items():
            active_version = state["active_notices"].get(notice_id)
            for version_text, raw in versions.items():
                item = dict(raw)
                item["active"] = int(version_text) == int(active_version or 0)
                item["can_activate"] = (
                    user.get("role") in {"admin", "qa"}
                    and not item["active"]
                    and str((item.get("created_by") or {}).get("id")) != str(user.get("id"))
                )
                rows.append(item)
        rows.sort(key=lambda item: (item["notice_id"], -int(item["version"])))
        return {
            "schema_version": M32_9_SCHEMA,
            "notices": rows,
            "active_notices": state["active_notices"],
            "notice": "Cada autorización conserva la versión y el SHA-256 del aviso informado.",
        }

    def create_notice_version(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede crear versiones del aviso.")
        notice_id = _safe_segment(payload.get("notice_id") or "contact-governance", "notice_id")
        state = self._state()
        versions = state["notices"].get(notice_id, {})
        version = max([int(item) for item in versions] or [0]) + 1
        name = _clean_text(payload.get("name") or notice_id, 120)
        text_value = str(payload.get("text") or "").strip()
        if not text_value or len(text_value) > 8000:
            raise ApprovalDeskError("El aviso debe tener entre 1 y 8.000 caracteres.")
        notice = {
            "notice_id": notice_id,
            "version": version,
            "name": name,
            "text": text_value,
            "status": "draft",
            "created_by": _actor(user),
            "created_at": self._now().isoformat(timespec="seconds"),
        }
        notice["notice_sha256"] = _notice_hash(notice)
        event = self._append("notice.version_created", user, {"notice": notice})
        return {"event": event, "notice": notice, "requires_independent_activation": True}

    def activate_notice(self, user: dict[str, Any], notice_id: str, version: int) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("La activación requiere administración o QA.")
        notice_key = _safe_segment(notice_id, "notice_id")
        state = self._state()
        item = state["notices"].get(notice_key, {}).get(str(int(version)))
        if not item:
            raise ApprovalDeskError("La versión del aviso no existe.")
        if str((item.get("created_by") or {}).get("id")) == str(user.get("id")):
            raise PermissionDenied("La persona creadora no puede activar su propia versión.")
        if item.get("notice_sha256") != _notice_hash(item):
            raise ContactGovernanceIntegrityError("El aviso no coincide con su SHA-256.")
        if state["active_notices"].get(notice_key) == int(version):
            return self.notices(user)
        event = self._append("notice.activated", user, {
            "notice_id": notice_key,
            "version": int(version),
            "notice_sha256": item["notice_sha256"],
            "separation_of_duties": True,
        })
        return {"event": event, **self.notices(user)}

    def record_relationship(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede registrar relaciones de contacto.")
        subject_id = _safe_segment(payload.get("subject_id"), "subject_id")
        relationship_type = str(payload.get("relationship_type") or "").strip().casefold()
        lawful_basis = str(payload.get("lawful_basis") or "").strip().casefold()
        status = str(payload.get("status") or "active").strip().casefold()
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ApprovalDeskError("El tipo de relación no es válido.")
        if lawful_basis not in RELATIONSHIP_BASES:
            raise ApprovalDeskError("La base declarada de la relación no es válida.")
        if status not in {"active", "inactive"}:
            raise ApprovalDeskError("El estado de la relación debe ser active o inactive.")
        evidence_reference = str(payload.get("evidence_reference") or "").strip()
        if status == "active" and not evidence_reference:
            raise ApprovalDeskError("La relación activa requiere una referencia de evidencia.")
        relationship = {
            "subject_id": subject_id,
            "relationship_type": relationship_type,
            "lawful_basis": lawful_basis,
            "status": status,
            "evidence_sha256": sha256(evidence_reference.encode("utf-8")).hexdigest() if evidence_reference else None,
            "evidence_reference_stored": False,
            "recorded_at": self._now().isoformat(timespec="seconds"),
            "recorded_by": _actor(user),
        }
        event = self._append("relationship.recorded", user, {"relationship": relationship})
        return {"event": event, "relationship": relationship}

    def _active_notice(self, state: dict[str, Any]) -> dict[str, Any]:
        notice_id = "contact-governance"
        version = state["active_notices"].get(notice_id)
        notice = state["notices"].get(notice_id, {}).get(str(version))
        if not notice:
            raise ApprovalDeskError("No existe un aviso de contacto activo.")
        if notice.get("notice_sha256") != _notice_hash(notice):
            raise ContactGovernanceIntegrityError("El aviso activo fue alterado.")
        return notice

    def record_preference(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("El registro verificado de preferencias requiere administración o QA.")
        subject_id = _safe_segment(payload.get("subject_id"), "subject_id")
        purpose = str(payload.get("purpose") or "").strip().casefold()
        channel = str(payload.get("channel") or "").strip().casefold()
        state_value = str(payload.get("state") or "").strip().casefold()
        basis = str(payload.get("basis") or "consent").strip().casefold()
        if purpose not in PURPOSES:
            raise ApprovalDeskError("La finalidad no es válida.")
        if channel not in CHANNELS:
            raise ApprovalDeskError("El canal no es válido.")
        if state_value not in {"granted", "denied"}:
            raise ApprovalDeskError("La preferencia debe ser granted o denied.")
        if basis not in PREFERENCE_BASES:
            raise ApprovalDeskError("La base de la preferencia no es válida.")
        if purpose in {"commercial_marketing", "collections"} and state_value == "granted" and basis != "consent":
            raise ApprovalDeskError("Marketing y cobranza requieren consentimiento para habilitar el canal en esta compuerta.")
        evidence_reference = str(payload.get("evidence_reference") or "").strip()
        if state_value == "granted" and not evidence_reference:
            raise ApprovalDeskError("Una autorización concedida requiere referencia de evidencia.")
        current = self._state()
        notice = self._active_notice(current)
        preference = {
            "preference_id": "PREF-" + uuid4().hex[:18].upper(),
            "subject_id": subject_id,
            "purpose": purpose,
            "channel": channel,
            "state": state_value,
            "basis": basis,
            "notice_id": notice["notice_id"],
            "notice_version": int(notice["version"]),
            "notice_sha256": notice["notice_sha256"],
            "evidence_sha256": sha256(evidence_reference.encode("utf-8")).hexdigest() if evidence_reference else None,
            "evidence_reference_stored": False,
            "reason": _clean_text(payload.get("reason"), 500),
            "recorded_at": self._now().isoformat(timespec="seconds"),
            "recorded_by": _actor(user),
        }
        event = self._append("preference.recorded", user, {"preference": preference})
        return {"event": event, "preference": preference}

    def add_suppression(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("La supresión requiere administración o QA.")
        subject_id = _safe_segment(payload.get("subject_id"), "subject_id")
        scope = str(payload.get("scope") or "global").strip().casefold()
        channel = str(payload.get("channel") or "").strip().casefold() or None
        purpose = str(payload.get("purpose") or "").strip().casefold() or None
        if scope not in SUPPRESSION_SCOPES:
            raise ApprovalDeskError("El alcance de supresión no es válido.")
        if scope in {"channel", "purpose_channel"} and channel not in CHANNELS:
            raise ApprovalDeskError("La supresión requiere un canal válido.")
        if scope in {"purpose", "purpose_channel"} and purpose not in PURPOSES:
            raise ApprovalDeskError("La supresión requiere una finalidad válida.")
        reason = _clean_text(payload.get("reason"), 500)
        if not reason:
            raise ApprovalDeskError("La supresión requiere un motivo.")
        suppression = {
            "suppression_id": "SUP-" + uuid4().hex[:18].upper(),
            "subject_id": subject_id,
            "scope": scope,
            "channel": channel,
            "purpose": purpose,
            "reason": reason,
            "source": _clean_text(payload.get("source") or "verified_request", 120),
            "added_at": self._now().isoformat(timespec="seconds"),
            "added_by": _actor(user),
            "active": True,
        }
        event = self._append("suppression.added", user, {"suppression": suppression})
        return {"event": event, "suppression": suppression}

    def lift_suppression(self, user: dict[str, Any], suppression_id: str, reason: str) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede levantar una supresión.")
        suppression_key = _safe_segment(suppression_id, "suppression_id")
        state = self._state()
        item = state["suppressions"].get(suppression_key)
        if not item:
            raise ApprovalDeskError("La supresión no existe.")
        if not item.get("active"):
            return self.subject(user, item["subject_id"])
        reason_value = _clean_text(reason, 500)
        if not reason_value:
            raise ApprovalDeskError("El levantamiento requiere un motivo.")
        event = self._append("suppression.lifted", user, {
            "suppression_id": suppression_key,
            "reason": reason_value,
        })
        return {"event": event, **self.subject(user, item["subject_id"])}

    @staticmethod
    def _suppression_matches(item: dict[str, Any], purpose: str, channel: str) -> bool:
        if not item.get("active"):
            return False
        scope = item.get("scope")
        if scope == "global":
            return True
        if scope == "channel":
            return item.get("channel") == channel
        if scope == "purpose":
            return item.get("purpose") == purpose
        return item.get("purpose") == purpose and item.get("channel") == channel

    @staticmethod
    def _inside_contact_window(at: datetime, policy: dict[str, Any]) -> tuple[bool, str]:
        zone = ZoneInfo(policy["timezone"])
        local = at.astimezone(zone)
        if local.date().isoformat() in set(policy.get("holidays", [])):
            return False, "configured_holiday"
        weekday = local.weekday()
        if weekday == 6:
            return False, "sunday"
        if weekday == 5:
            opens = _clock(policy["saturday_open"], "saturday_open")
            closes = _clock(policy["saturday_close"], "saturday_close")
            return (opens <= local.time() < closes, "outside_saturday_window")
        if weekday not in set(policy.get("weekdays", [])):
            return False, "configured_closed_day"
        opens = _clock(policy["weekday_open"], "weekday_open")
        closes = _clock(policy["weekday_close"], "weekday_close")
        return (opens <= local.time() < closes, "outside_weekday_window")

    def _frequency_reasons(self, state: dict[str, Any], subject_id: str, purpose: str, channel: str, at: datetime) -> list[str]:
        if purpose not in {"commercial_marketing", "collections"}:
            return []
        contacts = [
            item for item in state["contacts"]
            if item.get("subject_id") == subject_id
            and item.get("purpose") == purpose
            and _parse_datetime(item["occurred_at"]) <= at
        ]
        day_start = at.replace(hour=0, minute=0, second=0, microsecond=0)
        same_day = [item for item in contacts if _parse_datetime(item["occurred_at"]) >= day_start]
        reasons: list[str] = []
        if len(same_day) >= int(state["policy"]["max_contacts_per_day"]):
            reasons.append("daily_frequency_limit")
        seven_days = at - timedelta(days=7)
        channels = {
            item.get("channel") for item in contacts
            if _parse_datetime(item["occurred_at"]) >= seven_days
        }
        if channel not in channels and len(channels) >= int(state["policy"]["max_channels_per_7_days"]):
            reasons.append("weekly_channel_limit")
        return reasons

    def evaluate(
        self,
        user: dict[str, Any],
        *,
        subject_id: str,
        purpose: str,
        channel: str,
        scheduled_at: str | datetime | None = None,
        context_reference: str = "",
        record: bool = True,
    ) -> dict[str, Any]:
        _actor(user)
        subject_key = _safe_segment(subject_id, "subject_id")
        purpose_value = str(purpose or "").strip().casefold()
        channel_value = str(channel or "").strip().casefold()
        if purpose_value not in PURPOSES:
            raise ApprovalDeskError("La finalidad no es válida.")
        if channel_value not in CHANNELS:
            raise ApprovalDeskError("El canal no es válido.")
        at = _parse_datetime(scheduled_at, "scheduled_at") if scheduled_at else self._now()
        state = self._state()
        profile = self._subject_profile(subject_key)
        relationship = state["relationships"].get(subject_key)
        preference = state["preferences"].get(_preference_key(subject_key, purpose_value, channel_value))
        suppressions = [
            item for item in state["suppressions"].values()
            if item.get("subject_id") == subject_key and self._suppression_matches(item, purpose_value, channel_value)
        ]
        reasons: list[str] = []
        basis = None
        if suppressions:
            reasons.append("active_suppression")
        if purpose_value == "professional_operational":
            if not profile or not bool(profile.get("active")) or profile.get("role") not in PROFESSIONAL_ROLES:
                reasons.append("inactive_or_nonprofessional_subject")
            else:
                basis = "internal_operational_policy"
        else:
            if not relationship or relationship.get("status") != "active":
                reasons.append("active_relationship_missing")
            else:
                basis = relationship.get("lawful_basis")
            if preference and preference.get("state") == "denied":
                reasons.append("preference_denied")
            if purpose_value == "commercial_marketing":
                if state["policy"].get("commercial_requires_explicit_consent") and (
                    not preference or preference.get("state") != "granted" or preference.get("basis") != "consent"
                ):
                    reasons.append("explicit_marketing_consent_missing")
                else:
                    basis = "consent"
            elif purpose_value == "collections":
                if state["policy"].get("collections_requires_authorized_channel") and (
                    not preference or preference.get("state") != "granted" or preference.get("basis") != "consent"
                ):
                    reasons.append("authorized_collection_channel_missing")
                else:
                    basis = "consent"
            elif purpose_value == "service_transactional":
                if relationship and relationship.get("lawful_basis") not in {"contract", "user_request", "legal_obligation", "consent"}:
                    reasons.append("transactional_basis_insufficient")
        if purpose_value in {"commercial_marketing", "collections"}:
            inside, window_reason = self._inside_contact_window(at, state["policy"])
            if not inside:
                reasons.append(window_reason)
            reasons.extend(self._frequency_reasons(state, subject_key, purpose_value, channel_value, at))
        reasons = sorted(set(reasons))
        allowed = not reasons
        decision = {
            "decision_id": "DEC-" + uuid4().hex[:18].upper(),
            "subject_id": subject_key,
            "purpose": purpose_value,
            "channel": channel_value,
            "scheduled_at": at.isoformat(timespec="seconds"),
            "allowed": allowed,
            "outcome": "allowed" if allowed else "blocked",
            "reasons": reasons,
            "declared_basis": basis,
            "relationship_status": relationship.get("status") if relationship else None,
            "preference_state": preference.get("state") if preference else None,
            "active_suppressions": [item["suppression_id"] for item in suppressions],
            "context_sha256": sha256(str(context_reference or "").encode("utf-8")).hexdigest(),
            "context_reference_stored": False,
            "real_contact_performed": False,
            "legal_conclusion": False,
            "decided_at": self._now().isoformat(timespec="seconds"),
        }
        if record:
            event = self._append("decision.recorded", user, {"decision": decision})
            return {"event": event, "decision": decision}
        return {"decision": decision}

    def record_contact(
        self,
        user: dict[str, Any],
        *,
        decision_id: str,
        subject_id: str,
        purpose: str,
        channel: str,
        dispatch_id: str,
        occurred_at: str | datetime | None = None,
        synthetic: bool = True,
    ) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede registrar ejecuciones de contacto.")
        if not synthetic:
            raise ApprovalDeskError("M32.9 solo admite contactos sintéticos mientras no exista un proveedor real validado.")
        state = self._state()
        decision_key = _safe_segment(decision_id, "decision_id")
        decision = next((item for item in state["decisions"] if item.get("decision_id") == decision_key), None)
        if not decision or not decision.get("allowed"):
            raise ApprovalDeskError("El contacto requiere una decisión permitida y trazable.")
        contact = {
            "contact_id": "CNT-" + uuid4().hex[:18].upper(),
            "decision_id": decision_key,
            "subject_id": _safe_segment(subject_id, "subject_id"),
            "purpose": str(purpose).casefold(),
            "channel": str(channel).casefold(),
            "dispatch_id": _safe_segment(dispatch_id, "dispatch_id"),
            "occurred_at": (_parse_datetime(occurred_at) if occurred_at else self._now()).isoformat(timespec="seconds"),
            "synthetic": True,
            "real_contact": False,
        }
        event = self._append("contact.recorded", user, {"contact": contact})
        return {"event": event, "contact": contact}

    def subject(self, user: dict[str, Any], subject_id: str) -> dict[str, Any]:
        _actor(user)
        subject_key = _safe_segment(subject_id, "subject_id")
        if user.get("role") == "specialist" and str(user.get("id")) != subject_key:
            raise PermissionDenied("El especialista solo puede consultar sus propias preferencias.")
        state = self._state()
        preferences = [item for item in state["preferences"].values() if item.get("subject_id") == subject_key]
        suppressions = [item for item in state["suppressions"].values() if item.get("subject_id") == subject_key]
        decisions = [item for item in state["decisions"] if item.get("subject_id") == subject_key][-50:]
        contacts = [item for item in state["contacts"] if item.get("subject_id") == subject_key][-50:]
        return {
            "schema_version": M32_9_SCHEMA,
            "subject_id": subject_key,
            "profile": self._subject_profile(subject_key),
            "relationship": state["relationships"].get(subject_key),
            "preferences": preferences,
            "suppressions": suppressions,
            "decisions": decisions,
            "contacts": contacts,
            "audit": self.verify_chain(),
        }

    def dashboard(self, user: dict[str, Any]) -> dict[str, Any]:
        _actor(user)
        state = self._state()
        preferences = list(state["preferences"].values())
        suppressions = list(state["suppressions"].values())
        decisions = state["decisions"]
        if user.get("role") == "specialist":
            preferences = [item for item in preferences if item.get("subject_id") == str(user.get("id"))]
            suppressions = [item for item in suppressions if item.get("subject_id") == str(user.get("id"))]
            decisions = [item for item in decisions if item.get("subject_id") == str(user.get("id"))]
        return {
            "schema_version": M32_9_SCHEMA,
            "metrics": {
                "relationships": len(state["relationships"]),
                "granted_preferences": sum(item.get("state") == "granted" for item in preferences),
                "denied_preferences": sum(item.get("state") == "denied" for item in preferences),
                "active_suppressions": sum(item.get("active") for item in suppressions),
                "blocked_decisions": sum(not item.get("allowed") for item in decisions),
                "synthetic_contacts": len(state["contacts"]),
            },
            "recent_decisions": list(reversed(decisions[-25:])),
            "policy": self.policy(user),
            "notices": self.notices(user),
            "audit": self.verify_chain(),
            "capabilities": {
                "manage": user.get("role") == "admin",
                "verify_requests": user.get("role") in {"admin", "qa"},
                "activate_notice": user.get("role") in {"admin", "qa"},
            },
            "notice": (
                "Las decisiones M32.9 son controles operativos trazables. No constituyen por sí mismas "
                "una conclusión jurídica sobre la licitud del tratamiento."
            ),
        }


class GovernedTransactionalCommunications(TransactionalCommunications):
    """Extiende M32.8 y aplica la compuerta M32.9 antes de procesar."""

    def __init__(self, *args, governance: ContactGovernance | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.governance = governance or ContactGovernance(
            self.root,
            db_factory=self.db_factory,
            now_factory=self.now_factory,
        )

    def process(self, user: dict[str, Any], *, limit: int | None = None) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede procesar despachos.")
        state = self._state()
        policy = state["policy"]
        cap = max(1, min(int(limit or policy["batch_size"]), int(policy["batch_size"]), 200))
        now = self._now()
        eligible = [
            item for item in state["dispatches"].values()
            if item.get("status") in {"queued", "retry_scheduled"}
            and _parse_datetime(item.get("next_attempt_at"), "next_attempt_at") <= now
        ]
        eligible.sort(key=lambda item: (str(item.get("next_attempt_at")), str(item.get("dispatch_id"))))
        allowed_ids: list[str] = []
        blocked_ids: list[str] = []
        decisions: dict[str, dict[str, Any]] = {}
        for dispatch in eligible[:cap]:
            result = self.governance.evaluate(
                user,
                subject_id=str(dispatch.get("recipient_id") or ""),
                purpose="professional_operational",
                channel=str(dispatch.get("channel") or "email"),
                scheduled_at=now,
                context_reference=str(dispatch.get("dispatch_id") or ""),
                record=True,
            )
            decision = result["decision"]
            decisions[dispatch["dispatch_id"]] = decision
            if decision["allowed"]:
                allowed_ids.append(dispatch["dispatch_id"])
            else:
                self._append("dispatch.dead_lettered", user, {
                    "dispatch_id": dispatch["dispatch_id"],
                    "attempt": int(dispatch.get("attempts") or 0),
                    "error_code": "governance_blocked",
                    "reason": ",".join(decision["reasons"])[:500],
                    "governance_decision_id": decision["decision_id"],
                })
                blocked_ids.append(dispatch["dispatch_id"])
        if allowed_ids:
            result = super().process(user, limit=len(allowed_ids))
        else:
            result = {
                "schema_version": "M32.8",
                "accepted_sandbox": [],
                "retry_scheduled": [],
                "dead_lettered": [],
                "real_delivery_performed": False,
                "audit": self.verify_chain(),
            }
        for dispatch_id in result.get("accepted_sandbox", []):
            decision = decisions.get(dispatch_id)
            if decision:
                self.governance.record_contact(
                    user,
                    decision_id=decision["decision_id"],
                    subject_id=decision["subject_id"],
                    purpose=decision["purpose"],
                    channel=decision["channel"],
                    dispatch_id=dispatch_id,
                    occurred_at=now,
                    synthetic=True,
                )
        result["governance_blocked"] = blocked_ids
        result["governance_audit"] = self.governance.verify_chain()
        result["real_contact_performed"] = False
        return result

    def dashboard(self, user: dict[str, Any]) -> dict[str, Any]:
        payload = super().dashboard(user)
        payload["contact_governance"] = self.governance.dashboard(user)
        payload["schema_version"] = M32_9_SCHEMA
        return payload


__all__ = [
    "ContactGovernance",
    "GovernedTransactionalCommunications",
    "ContactGovernanceIntegrityError",
    "M32_9_SCHEMA",
    "DEFAULT_POLICY",
    "DEFAULT_NOTICE",
    "CHANNELS",
    "PURPOSES",
]
