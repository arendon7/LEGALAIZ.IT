from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.external_evidence_bundle_v1 import EvidenceBundleError, EvidenceBundleValidator


SCHEMA_VERSION = "V1-RC7"
POLICY_SCHEMA = "legalaiz-v1-rc7-external-attestation-policy-v1"
EVENT_TYPES = frozenset({"EVIDENCE_REGISTERED", "REVIEW_APPROVED", "RELEASE_RATIFIED", "REVOKED"})
VERIFIED_STATUS = "VERIFIED_EXTERNAL_EVIDENCE"
_LOCK = RLock()


class ExternalAttestationError(RuntimeError):
    pass


class ExternalAttestationIntegrityError(ExternalAttestationError):
    pass


class ExternalAttestationPermissionError(ExternalAttestationError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_actor(actor: Mapping[str, Any], allowed_roles: set[str]) -> dict[str, str]:
    actor_id = str(actor.get("id") or "").strip()
    role = str(actor.get("role") or "").strip().casefold()
    if not actor_id or not re.fullmatch(r"[A-Za-z0-9._@-]{2,160}", actor_id):
        raise ExternalAttestationPermissionError("El actor de atestación no es válido.")
    if role not in allowed_roles:
        raise ExternalAttestationPermissionError("El rol no está autorizado para el ledger RC7.")
    return {"id": actor_id, "role": role}


class ExternalAttestationDossier:
    """Ledger append-only para las doce atestaciones RC4.

    La evidencia vive fuera del repositorio. El ledger conserva referencias,
    hashes y actuaciones de gobierno; nunca modifica el registro estático de
    atestaciones ni los flags de autorización de release.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        dossier_path: str | Path | None = None,
        evidence_root: str | Path | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        policy_path = self.root / "config" / "v1" / "rc7_external_attestation_policy.json"
        if not policy_path.is_file():
            raise ExternalAttestationError("Falta la política RC7 de atestaciones externas.")
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        plan = EvidenceExecutionPlan(self.root)
        validation = plan.validate()
        if not validation.valid:
            raise ExternalAttestationError("El execution pack RC6 es inválido.")
        self.plan_rows = {
            str(row["source_id"]): row
            for row in plan.plan["controls"]
            if str(row.get("source_framework") or "") == "RC4"
        }
        static_path = self.root / "config" / "v1" / "production_attestations.json"
        static_payload = json.loads(static_path.read_text(encoding="utf-8"))
        self.static_attestations = {
            str(row.get("id") or ""): row
            for row in static_payload.get("attestations") or []
            if isinstance(row, dict) and str(row.get("id") or "")
        }
        self._validate_policy()
        runtime = Path(str(os.environ.get("LEGAL_RUNTIME_DIR") or (self.root / "runtime"))).expanduser()
        default_path = runtime / "release-readiness" / "rc4-external-attestations.jsonl"
        self.path = Path(dossier_path or os.environ.get("LEGAL_RC4_ATTESTATION_DOSSIER") or default_path).expanduser().resolve()
        default_evidence_root = self.path.parent / "evidence"
        self.evidence_root = Path(evidence_root or os.environ.get("LEGAL_EXTERNAL_EVIDENCE_ROOT") or default_evidence_root).expanduser().resolve()
        self.now_factory = now_factory or _now

    @property
    def controls(self) -> tuple[str, ...]:
        return tuple(self.plan_rows)

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != POLICY_SCHEMA:
            raise ExternalAttestationError("Política RC7 inválida.")
        if set(self.policy.get("event_types") or []) != set(EVENT_TYPES):
            raise ExternalAttestationError("La política RC7 perdió tipos de evento canónicos.")
        roles = set(self.policy.get("runtime_actor_roles") or [])
        registration_roles = set(self.policy.get("registration_roles") or [])
        ratifiers = set(self.policy.get("release_ratifier_roles") or [])
        if not {"admin", "qa", "specialist"}.issubset(roles):
            raise ExternalAttestationError("RC7 perdió roles profesionales canónicos.")
        if not registration_roles or not registration_roles.issubset(roles):
            raise ExternalAttestationError("Roles de registro RC7 inválidos.")
        if not ratifiers or not ratifiers.issubset(roles):
            raise ExternalAttestationError("Roles de ratificación RC7 inválidos.")
        if len(self.plan_rows) != 12 or set(self.plan_rows) != set(self.static_attestations):
            raise ExternalAttestationError("RC7 debe gobernar exactamente las doce atestaciones RC4.")
        for control, row in self.plan_rows.items():
            executor = str(row.get("executor_role") or "")
            reviewer = str(row.get("reviewer_role") or "")
            if executor not in roles or reviewer not in roles:
                raise ExternalAttestationError(f"Roles operativos RC7 inválidos para {control}.")
            if executor == reviewer:
                raise ExternalAttestationError(f"RC7 perdió separación ejecutor/revisor para {control}.")
            if str(self.static_attestations[control].get("owner_role") or "") != executor:
                raise ExternalAttestationError(f"Owner estático y ejecutor RC6 divergen para {control}.")

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for raw in self.path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise ExternalAttestationIntegrityError("Evento RC7 inválido.")
                rows.append(row)
        except (OSError, json.JSONDecodeError) as exc:
            raise ExternalAttestationIntegrityError("No fue posible leer íntegramente el ledger RC7.") from exc
        return rows

    def verify_chain(self) -> dict[str, Any]:
        previous = "0" * 64
        try:
            events = self._read_events()
        except ExternalAttestationIntegrityError:
            return {"valid": False, "events": 0, "failed_sequence": 1, "last_hash": previous}
        for expected_sequence, event in enumerate(events, 1):
            stored = str(event.get("event_hash") or "")
            candidate = dict(event)
            candidate.pop("event_hash", None)
            calculated = sha256(_canonical_json(candidate).encode("utf-8")).hexdigest()
            if (
                event.get("schema_version") != SCHEMA_VERSION
                or int(event.get("sequence") or 0) != expected_sequence
                or str(event.get("event_type") or "") not in EVENT_TYPES
                or str(event.get("control") or "") not in self.plan_rows
                or str(event.get("previous_hash") or "") != previous
                or stored != calculated
            ):
                return {
                    "valid": False,
                    "events": len(events),
                    "failed_sequence": expected_sequence,
                    "last_hash": previous,
                }
            previous = stored
        return {"valid": True, "events": len(events), "failed_sequence": None, "last_hash": previous}

    def _append(self, event_type: str, control: str, actor: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        if event_type not in EVENT_TYPES or control not in self.plan_rows:
            raise ExternalAttestationError("Evento o control RC7 inválido.")
        safe_actor = _safe_actor(actor, set(self.policy.get("runtime_actor_roles") or []))
        with _LOCK:
            integrity = self.verify_chain()
            if not integrity.get("valid"):
                raise ExternalAttestationIntegrityError("La cadena RC7 está alterada; no admite nuevas actuaciones.")
            event = {
                "schema_version": SCHEMA_VERSION,
                "sequence": int(integrity.get("events") or 0) + 1,
                "event_id": f"ATT-{uuid4().hex.upper()}",
                "event_type": event_type,
                "control": control,
                "created_at": self.now_factory().astimezone(timezone.utc).isoformat(timespec="seconds"),
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

    def register_bundle(self, control: str, bundle_path: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        if control not in self.plan_rows:
            raise ExternalAttestationError("Atestación RC4 desconocida.")
        if self._active_registration(control):
            raise ExternalAttestationError("Existe evidencia activa; debe revocarse antes de reemplazarla.")
        safe_actor = _safe_actor(actor, set(self.policy.get("registration_roles") or []))
        validator = EvidenceBundleValidator(self.root, self.evidence_root, now_factory=self.now_factory)
        try:
            bundle = validator.validate(bundle_path, expected_control_ref=f"RC4:{control}")
        except EvidenceBundleError as exc:
            raise ExternalAttestationError(str(exc)) from exc
        if safe_actor["id"] == bundle.executor["id"]:
            raise ExternalAttestationPermissionError("Ejecutor técnico y registrador de evidencia deben ser actores distintos.")
        return self._append(
            "EVIDENCE_REGISTERED",
            control,
            safe_actor,
            {
                "bundle_path": bundle.bundle_path,
                "manifest_path": bundle.manifest_path,
                "manifest_sha256": bundle.manifest_sha256,
                "observed_at": bundle.observed_at,
                "valid_until": bundle.valid_until,
                "environment": bundle.environment,
                "executor": dict(bundle.executor),
                "artifact_count": bundle.artifact_count,
            },
        )

    def approve_review(self, control: str, evidence_event_id: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        registration = self._event_by_id(evidence_event_id)
        if not registration or registration.get("event_type") != "EVIDENCE_REGISTERED" or registration.get("control") != control:
            raise ExternalAttestationError("La revisión no referencia evidencia RC7 válida.")
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalAttestationError("La evidencia ya no es la referencia activa.")
        reviewer_role = str(self.plan_rows[control].get("reviewer_role") or "")
        safe_actor = _safe_actor(actor, {reviewer_role})
        payload = registration.get("payload") or {}
        forbidden_ids = {
            str((registration.get("actor") or {}).get("id") or ""),
            str((payload.get("executor") or {}).get("id") or ""),
        }
        if safe_actor["id"] in forbidden_ids:
            raise ExternalAttestationPermissionError("Ejecutor, registrador y revisor deben ser actores distintos.")
        existing = [
            row for row in self._events_for(control)
            if row.get("event_type") == "REVIEW_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ]
        if existing:
            if str((existing[-1].get("actor") or {}).get("id") or "") == safe_actor["id"]:
                return dict(existing[-1])
            raise ExternalAttestationError("La evidencia ya tiene revisión independiente registrada.")
        return self._append("REVIEW_APPROVED", control, safe_actor, {"evidence_event_id": evidence_event_id})

    def ratify_release(self, control: str, evidence_event_id: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalAttestationError("La evidencia no está activa para ratificación.")
        review = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "REVIEW_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ), None)
        if not review:
            raise ExternalAttestationError("La ratificación requiere revisión independiente previa.")
        safe_actor = _safe_actor(actor, set(self.policy.get("release_ratifier_roles") or []))
        payload = active.get("payload") or {}
        forbidden_ids = {
            str((payload.get("executor") or {}).get("id") or ""),
            str((active.get("actor") or {}).get("id") or ""),
            str((review.get("actor") or {}).get("id") or ""),
        }
        if safe_actor["id"] in forbidden_ids:
            raise ExternalAttestationPermissionError("Ratificación requiere un cuarto actor independiente.")
        existing = [
            row for row in self._events_for(control)
            if row.get("event_type") == "RELEASE_RATIFIED"
            and (row.get("payload") or {}).get("evidence_event_id") == evidence_event_id
        ]
        if existing:
            if str((existing[-1].get("actor") or {}).get("id") or "") == safe_actor["id"]:
                return dict(existing[-1])
            raise ExternalAttestationError("La evidencia ya tiene ratificación registrada.")
        return self._append("RELEASE_RATIFIED", control, safe_actor, {"evidence_event_id": evidence_event_id})

    def revoke(self, control: str, evidence_event_id: str, *, reason_code: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active or active.get("event_id") != evidence_event_id:
            raise ExternalAttestationError("Sólo puede revocarse la evidencia activa.")
        safe_actor = _safe_actor(actor, set(self.policy.get("release_ratifier_roles") or []))
        reason = str(reason_code or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]{3,64}", reason):
            raise ExternalAttestationError("reason_code RC7 inválido.")
        return self._append("REVOKED", control, safe_actor, {"target_event_id": evidence_event_id, "reason_code": reason})

    def _control_internal(self, control: str) -> dict[str, Any]:
        active = self._active_registration(control)
        if not active:
            return {"key": control, "passed": False, "status": "MISSING_EVIDENCE"}
        payload = active.get("payload") or {}
        try:
            validator = EvidenceBundleValidator(self.root, self.evidence_root, now_factory=self.now_factory)
            bundle = validator.validate(str(payload.get("bundle_path") or ""), expected_control_ref=f"RC4:{control}")
            bundle_ok = bundle.manifest_sha256 == str(payload.get("manifest_sha256") or "")
        except (EvidenceBundleError, OSError, ValueError, TypeError):
            bundle_ok = False
            bundle = None
        review = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "REVIEW_APPROVED"
            and (row.get("payload") or {}).get("evidence_event_id") == active.get("event_id")
        ), None)
        ratified = next((
            row for row in reversed(self._events_for(control))
            if row.get("event_type") == "RELEASE_RATIFIED"
            and (row.get("payload") or {}).get("evidence_event_id") == active.get("event_id")
        ), None)
        actor_ids = [
            str((payload.get("executor") or {}).get("id") or ""),
            str((active.get("actor") or {}).get("id") or ""),
            str((review.get("actor") or {}).get("id") or "") if review else "",
            str((ratified.get("actor") or {}).get("id") or "") if ratified else "",
        ]
        separation_ok = bool(review and ratified and all(actor_ids) and len(set(actor_ids)) == 4)
        if not bundle_ok:
            status = "EVIDENCE_BUNDLE_INTEGRITY_INVALID"
        elif not review:
            status = "INDEPENDENT_REVIEW_REQUIRED"
        elif not ratified:
            status = "RELEASE_RATIFICATION_REQUIRED"
        elif not separation_ok:
            status = "SEPARATION_OF_DUTIES_INVALID"
        else:
            status = VERIFIED_STATUS
        return {
            "key": control,
            "passed": status == VERIFIED_STATUS,
            "status": status,
            "evidence_event_id": active.get("event_id"),
            "evidence_ref": f"rc7-attestation://{active.get('event_id')}" if status == VERIFIED_STATUS else None,
            "manifest_sha256": payload.get("manifest_sha256"),
            "valid_until": bundle.valid_until if bundle else payload.get("valid_until"),
            "review_event_id": review.get("event_id") if review else None,
            "ratification_event_id": ratified.get("event_id") if ratified else None,
        }

    def internal_summary(self) -> dict[str, Any]:
        integrity = self.verify_chain()
        if not integrity.get("valid"):
            checks = [{"key": key, "passed": False, "status": "DOSSIER_INTEGRITY_INVALID"} for key in self.controls]
        else:
            checks = [self._control_internal(key) for key in self.controls]
        return {
            "schema": "legalaiz-v1-rc7-external-attestation-summary-v1",
            "ready": bool(integrity.get("valid")) and all(row["passed"] for row in checks),
            "passed": sum(1 for row in checks if row["passed"]),
            "total": len(checks),
            "integrity": "valid" if integrity.get("valid") else "invalid",
            "checks": checks,
        }

    def summary(self) -> dict[str, Any]:
        internal = self.internal_summary()
        return {
            "schema": internal["schema"],
            "ready": internal["ready"],
            "passed": internal["passed"],
            "total": internal["total"],
            "integrity": internal["integrity"],
            "checks": [
                {"key": row["key"], "passed": row["passed"], "status": row["status"]}
                for row in internal["checks"]
            ],
        }


__all__ = [
    "ExternalAttestationDossier",
    "ExternalAttestationError",
    "ExternalAttestationIntegrityError",
    "ExternalAttestationPermissionError",
    "VERIFIED_STATUS",
]
