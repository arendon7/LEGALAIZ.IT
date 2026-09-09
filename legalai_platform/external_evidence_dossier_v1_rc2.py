from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable, Mapping
from uuid import uuid4


SCHEMA_VERSION = "V1-RC2"
POLICY_SCHEMA = "legalaizit-v1-rc2-external-evidence-policy-v1"
ASSURANCE = "hardened_v1_rc2"
EVENT_TYPES = frozenset({"EVIDENCE_REGISTERED", "DOMAIN_APPROVED", "RELEASE_RATIFIED", "REVOKED"})
_LOCK = RLock()


class ExternalEvidenceError(RuntimeError):
    pass


class ExternalEvidenceIntegrityError(ExternalEvidenceError):
    pass


class ExternalEvidencePermissionError(ExternalEvidenceError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ExternalEvidenceError(f"{field} es obligatorio.")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalEvidenceError(f"{field} debe usar ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ExternalEvidenceError(f"{field} debe incluir zona horaria.")
    return parsed.astimezone(timezone.utc)


def _safe_actor(actor: Mapping[str, Any], allowed_roles: set[str]) -> dict[str, str]:
    actor_id = str(actor.get("id") or "").strip()
    role = str(actor.get("role") or "").strip().casefold()
    if not actor_id or not re.fullmatch(r"[A-Za-z0-9._@-]{2,160}", actor_id):
        raise ExternalEvidencePermissionError("El actor de evidencia no es válido.")
    if role not in allowed_roles:
        raise ExternalEvidencePermissionError("El rol no está autorizado para el dossier de release.")
    return {"id": actor_id, "role": role}


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_under(base: Path, relative: str, field: str) -> tuple[Path, str]:
    raw = str(relative or "").strip().replace("\\", "/")
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or ".." in candidate.parts:
        raise ExternalEvidenceError(f"{field} debe ser una ruta relativa segura.")
    base_resolved = base.resolve()
    resolved = (base_resolved / candidate).resolve()
    try:
        normalized = resolved.relative_to(base_resolved).as_posix()
    except ValueError as exc:
        raise ExternalEvidenceError(f"{field} sale del repositorio de evidencia.") from exc
    return resolved, normalized


class ExternalEvidenceDossier:
    """Dossier append-only para evidencia externa de readiness V1.

    No expone endpoints, no cambia release metadata y no activa proveedores. Los
    eventos internos conservan actores, referencias y hashes; `summary()` devuelve
    únicamente control + estado para que los read models públicos no filtren esos
    datos de gobierno.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        dossier_path: str | Path | None = None,
        evidence_root: str | Path | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self.root = Path(root).resolve()
        self.policy_path = self.root / "config" / "v1_rc2_external_evidence_policy.json"
        if not self.policy_path.is_file():
            raise ExternalEvidenceError("Falta la política V1-RC2 de evidencia externa.")
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self._validate_policy()
        runtime = Path(str(os.environ.get("LEGAL_RUNTIME_DIR") or (self.root / "runtime"))).expanduser()
        default_path = runtime / "release-readiness" / "external-evidence-dossier.jsonl"
        self.path = Path(dossier_path or os.environ.get("LEGAL_EXTERNAL_EVIDENCE_DOSSIER") or default_path).expanduser().resolve()
        default_evidence_root = self.path.parent / "evidence"
        self.evidence_root = Path(evidence_root or os.environ.get("LEGAL_EXTERNAL_EVIDENCE_ROOT") or default_evidence_root).expanduser().resolve()
        self.now_factory = now_factory or _now

    @property
    def controls(self) -> tuple[str, ...]:
        return tuple((self.policy.get("controls") or {}).keys())

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != POLICY_SCHEMA or self.policy.get("assurance") != ASSURANCE:
            raise ExternalEvidenceError("Política V1-RC2 inválida.")
        roles = set(self.policy.get("runtime_roles") or [])
        if not {"admin", "specialist", "qa"}.issubset(roles):
            raise ExternalEvidenceError("La política RC2 perdió roles profesionales canónicos.")
        ratifiers = set(self.policy.get("release_ratifier_roles") or [])
        if not ratifiers or not ratifiers.issubset(roles):
            raise ExternalEvidenceError("Los roles de ratificación RC2 son inválidos.")
        controls = self.policy.get("controls") or {}
        if len(controls) != 10:
            raise ExternalEvidenceError("RC2 debe gobernar exactamente diez atestaciones externas.")
        for key, item in controls.items():
            if not re.fullmatch(r"[a-z0-9_]{3,80}", str(key)):
                raise ExternalEvidenceError("RC2 contiene una clave de control inválida.")
            domain_roles = set((item or {}).get("domain_approver_roles") or [])
            if not domain_roles or not domain_roles.issubset(roles):
                raise ExternalEvidenceError(f"Roles de dominio inválidos para {key}.")
            days = int((item or {}).get("max_validity_days") or 0)
            if days < 1 or days > 365:
                raise ExternalEvidenceError(f"Vigencia operativa inválida para {key}.")

    def has_events(self) -> bool:
        return self.path.is_file() and bool(self.path.stat().st_size)

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        events: list[dict[str, Any]] = []
        try:
            for raw in self.path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise ExternalEvidenceIntegrityError("El dossier contiene un evento inválido.")
                events.append(row)
        except (OSError, json.JSONDecodeError) as exc:
            raise ExternalEvidenceIntegrityError("No fue posible leer íntegramente el dossier RC2.") from exc
        return events

    def verify_chain(self) -> dict[str, Any]:
        previous = "0" * 64
        try:
            events = self._read_events()
        except ExternalEvidenceIntegrityError:
            return {"valid": False, "events": 0, "failed_sequence": 1, "last_hash": previous}
        for expected_sequence, event in enumerate(events, 1):
            stored_hash = str(event.get("event_hash") or "")
            candidate = dict(event)
            candidate.pop("event_hash", None)
            calculated = sha256(_canonical_json(candidate).encode("utf-8")).hexdigest()
            if (
                event.get("schema_version") != SCHEMA_VERSION
                or int(event.get("sequence") or 0) != expected_sequence
                or str(event.get("event_type") or "") not in EVENT_TYPES
                or str(event.get("previous_hash") or "") != previous
                or stored_hash != calculated
            ):
                return {
                    "valid": False,
                    "events": len(events),
                    "failed_sequence": expected_sequence,
                    "last_hash": previous,
                }
            previous = stored_hash
        return {"valid": True, "events": len(events), "failed_sequence": None, "last_hash": previous}

    def _append(self, event_type: str, control: str, actor: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ExternalEvidenceError("Tipo de evento RC2 inválido.")
        if control not in self.controls:
            raise ExternalEvidenceError("Control RC2 desconocido.")
        safe_actor = _safe_actor(actor, set(self.policy.get("runtime_roles") or []))
        with _LOCK:
            integrity = self.verify_chain()
            if not integrity.get("valid"):
                raise ExternalEvidenceIntegrityError("La cadena RC2 está alterada; no se admiten nuevas actuaciones.")
            sequence = int(integrity.get("events") or 0) + 1
            now = self.now_factory().astimezone(timezone.utc)
            event = {
                "schema_version": SCHEMA_VERSION,
                "sequence": sequence,
                "event_id": f"EVD-{uuid4().hex.upper()}",
                "event_type": event_type,
                "control": control,
                "created_at": now.isoformat(timespec="seconds"),
                "actor": safe_actor,
                "payload": dict(payload),
                "previous_hash": str(integrity.get("last_hash") or "0" * 64),
            }
            event["event_hash"] = sha256(_canonical_json(event).encode("utf-8")).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return dict(event)

    def _events_for(self, control: str) -> list[dict[str, Any]]:
        return [row for row in self._read_events() if str(row.get("control") or "") == control]

    def _event_by_id(self, event_id: str) -> dict[str, Any] | None:
        return next((row for row in self._read_events() if str(row.get("event_id") or "") == str(event_id)), None)

    def _active_registration(self, control: str) -> dict[str, Any] | None:
        events = self._events_for(control)
        revoked = {
            str((row.get("payload") or {}).get("target_event_id") or "")
            for row in events
            if row.get("event_type") == "REVOKED"
        }
        registrations = [
            row for row in events
            if row.get("event_type") == "EVIDENCE_REGISTERED" and str(row.get("event_id") or "") not in revoked
        ]
        return registrations[-1] if registrations else None

    def register_evidence(
        self,
        control: str,
        evidence_path: str,
        *,
        observed_at: str,
        valid_until: str,
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        if control not in self.controls:
            raise ExternalEvidenceError("Control RC2 desconocido.")
        if self._active_registration(control):
            raise ExternalEvidenceError("Existe evidencia activa; debe revocarse antes de registrar un reemplazo.")
        file_path, normalized = _resolve_under(self.evidence_root, evidence_path, "evidence_path")
        if not file_path.is_file():
            raise ExternalEvidenceError("El archivo de evidencia no existe.")
        observed = _parse_dt(observed_at, "observed_at")
        valid = _parse_dt(valid_until, "valid_until")
        now = self.now_factory().astimezone(timezone.utc)
        max_days = int(self.policy["controls"][control]["max_validity_days"])
        if observed > now + timedelta(minutes=5):
            raise ExternalEvidenceError("observed_at no puede estar en el futuro.")
        if valid <= observed or valid > observed + timedelta(days=max_days):
            raise ExternalEvidenceError("valid_until excede la política operativa RC2.")
        if valid <= now:
            raise ExternalEvidenceError("No se puede registrar evidencia ya vencida.")
        return self._append(
            "EVIDENCE_REGISTERED",
            control,
            actor,
            {
                "evidence_path": normalized,
                "evidence_sha256": _sha256_file(file_path),
                "evidence_size": int(file_path.stat().st_size),
                "observed_at": observed.isoformat(timespec="seconds"),
                "valid_until": valid.isoformat(timespec="seconds"),
            },
        )

    def approve_domain(self, control: str, evidence_event_id: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        registration = self._event_by_id(evidence_event_id)
        if not registration or registration.get("event_type") != "EVIDENCE_REGISTERED" or registration.get("control") != control:
            raise ExternalEvidenceError("La aprobación no referencia evidencia RC2 válida.")
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalEvidenceError("La evidencia ya no es la referencia activa del control.")
        safe_actor = _safe_actor(actor, set(self.policy.get("runtime_roles") or []))
        allowed = set(self.policy["controls"][control].get("domain_approver_roles") or [])
        if safe_actor["role"] not in allowed:
            raise ExternalEvidencePermissionError("El rol no puede aprobar el dominio de este control.")
        existing = [
            row for row in self._events_for(control)
            if row.get("event_type") == "DOMAIN_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ]
        if existing:
            if str((existing[-1].get("actor") or {}).get("id") or "") == safe_actor["id"]:
                return dict(existing[-1])
            raise ExternalEvidenceError("La evidencia ya tiene una aprobación de dominio registrada.")
        return self._append(
            "DOMAIN_APPROVED",
            control,
            safe_actor,
            {
                "evidence_event_id": evidence_event_id,
                "domain": str(self.policy["controls"][control].get("domain") or ""),
            },
        )

    def ratify_release(self, control: str, evidence_event_id: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalEvidenceError("La evidencia no está activa para ratificación.")
        domain = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "DOMAIN_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ), None)
        if not domain:
            raise ExternalEvidenceError("La ratificación requiere aprobación de dominio previa.")
        safe_actor = _safe_actor(actor, set(self.policy.get("runtime_roles") or []))
        if safe_actor["role"] not in set(self.policy.get("release_ratifier_roles") or []):
            raise ExternalEvidencePermissionError("El rol no puede ratificar release RC2.")
        domain_actor_id = str((domain.get("actor") or {}).get("id") or "")
        if safe_actor["id"] == domain_actor_id:
            raise ExternalEvidencePermissionError("Aprobación de dominio y ratificación de release requieren actores distintos.")
        existing = [
            row for row in self._events_for(control)
            if row.get("event_type") == "RELEASE_RATIFIED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ]
        if existing:
            if str((existing[-1].get("actor") or {}).get("id") or "") == safe_actor["id"]:
                return dict(existing[-1])
            raise ExternalEvidenceError("La evidencia ya tiene ratificación de release registrada.")
        return self._append(
            "RELEASE_RATIFIED",
            control,
            safe_actor,
            {"evidence_event_id": evidence_event_id},
        )

    def revoke(self, control: str, evidence_event_id: str, *, reason_code: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalEvidenceError("Sólo puede revocarse la evidencia activa del control.")
        safe_actor = _safe_actor(actor, set(self.policy.get("release_ratifier_roles") or []))
        reason = str(reason_code or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]{3,64}", reason):
            raise ExternalEvidenceError("reason_code RC2 inválido.")
        return self._append(
            "REVOKED",
            control,
            safe_actor,
            {"target_event_id": evidence_event_id, "reason_code": reason},
        )

    def _control_internal(self, control: str) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active:
            return {"key": control, "passed": False, "status": "MISSING_EVIDENCE"}
        payload = active.get("payload") or {}
        try:
            file_path, _normalized = _resolve_under(self.evidence_root, str(payload.get("evidence_path") or ""), "evidence_path")
            exists = file_path.is_file()
            digest_ok = exists and _sha256_file(file_path) == str(payload.get("evidence_sha256") or "")
            size_ok = exists and int(file_path.stat().st_size) == int(payload.get("evidence_size") or -1)
            valid_until = _parse_dt(str(payload.get("valid_until") or ""), "valid_until")
            fresh = valid_until > self.now_factory().astimezone(timezone.utc)
        except (ExternalEvidenceError, OSError, ValueError, TypeError):
            exists = digest_ok = size_ok = fresh = False
            valid_until = None
        domain = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "DOMAIN_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == active.get("event_id")
        ), None)
        ratified = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "RELEASE_RATIFIED"
            and (row.get("payload") or {}).get("evidence_event_id") == active.get("event_id")
        ), None)
        separation_ok = bool(
            domain and ratified
            and str((domain.get("actor") or {}).get("id") or "")
            != str((ratified.get("actor") or {}).get("id") or "")
        )
        if not exists:
            status = "EVIDENCE_FILE_MISSING"
        elif not digest_ok or not size_ok:
            status = "EVIDENCE_INTEGRITY_MISMATCH"
        elif not fresh:
            status = "EVIDENCE_EXPIRED"
        elif not domain:
            status = "DOMAIN_APPROVAL_REQUIRED"
        elif not ratified:
            status = "RELEASE_RATIFICATION_REQUIRED"
        elif not separation_ok:
            status = "SEPARATION_OF_DUTIES_INVALID"
        else:
            status = "VERIFIED_FOR_RELEASE_GATE"
        return {
            "key": control,
            "passed": status == "VERIFIED_FOR_RELEASE_GATE",
            "status": status,
            "evidence_event_id": active.get("event_id"),
            "evidence_path": payload.get("evidence_path"),
            "evidence_sha256": payload.get("evidence_sha256"),
            "valid_until": valid_until.isoformat(timespec="seconds") if valid_until else None,
            "domain_approval_event_id": domain.get("event_id") if domain else None,
            "release_ratification_event_id": ratified.get("event_id") if ratified else None,
            "domain_actor_id": (domain.get("actor") or {}).get("id") if domain else None,
            "release_actor_id": (ratified.get("actor") or {}).get("id") if ratified else None,
        }

    def internal_summary(self) -> dict[str, Any]:
        integrity = self.verify_chain()
        if not integrity.get("valid"):
            return {
                "schema": "legalaizit-v1-rc2-external-evidence-summary-v1",
                "assurance": ASSURANCE,
                "ready": False,
                "passed": 0,
                "total": len(self.controls),
                "integrity": "invalid",
                "checks": [{"key": key, "passed": False, "status": "DOSSIER_INTEGRITY_INVALID"} for key in self.controls],
            }
        checks = [self._control_internal(key) for key in self.controls]
        return {
            "schema": "legalaizit-v1-rc2-external-evidence-summary-v1",
            "assurance": ASSURANCE,
            "ready": all(row["passed"] for row in checks),
            "passed": sum(1 for row in checks if row["passed"]),
            "total": len(checks),
            "integrity": "valid",
            "events": int(integrity.get("events") or 0),
            "checks": checks,
        }

    def summary(self) -> dict[str, Any]:
        internal = self.internal_summary()
        return {
            "schema": internal["schema"],
            "assurance": internal["assurance"],
            "ready": bool(internal.get("ready")),
            "passed": int(internal.get("passed") or 0),
            "total": int(internal.get("total") or 0),
            "integrity": str(internal.get("integrity") or "invalid"),
            "checks": [
                {"key": str(row.get("key") or ""), "passed": bool(row.get("passed")), "status": str(row.get("status") or "UNKNOWN")}
                for row in internal.get("checks") or []
            ],
        }


__all__ = [
    "ASSURANCE",
    "ExternalEvidenceDossier",
    "ExternalEvidenceError",
    "ExternalEvidenceIntegrityError",
    "ExternalEvidencePermissionError",
]
