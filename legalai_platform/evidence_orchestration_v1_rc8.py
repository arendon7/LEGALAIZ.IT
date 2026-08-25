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
from legalai_platform.external_attestation_dossier_v1_rc7 import ExternalAttestationDossier, ExternalAttestationError
from legalai_platform.external_evidence_bundle_v1 import EvidenceBundleError, EvidenceBundleValidator
from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier, ExternalEvidenceError


SCHEMA_VERSION = "V1-RC8"
POLICY_SCHEMA = "legalaiz-v1-rc8-evidence-campaign-policy-v1"
CAMPAIGN_SCHEMA = "legalaiz-v1-rc8-evidence-campaign-v1"
EVENT_TYPES = frozenset({
    "CAMPAIGN_CREATED",
    "CONTROL_STARTED",
    "EVIDENCE_LINKED",
    "CONTROL_REVIEW_READY",
    "CONTROL_BLOCKED",
    "CAMPAIGN_ABORTED",
})
FORBIDDEN_SECRET_KEYS = frozenset({
    "password", "passwords", "token", "tokens", "api_key", "api_keys",
    "secret", "secrets", "credential", "credentials", "private_key", "private_keys",
    "recovery_code", "recovery_codes", "connection_string",
})
_LOCK = RLock()


class EvidenceCampaignError(RuntimeError):
    pass


class EvidenceCampaignIntegrityError(EvidenceCampaignError):
    pass


class EvidenceCampaignPermissionError(EvidenceCampaignError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_actor(actor: Mapping[str, Any]) -> dict[str, str]:
    actor_id = str(actor.get("id") or "").strip()
    role = str(actor.get("role") or "").strip().casefold()
    if not re.fullmatch(r"[A-Za-z0-9._@-]{2,160}", actor_id):
        raise EvidenceCampaignPermissionError("Actor de campaña inválido.")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,80}", role):
        raise EvidenceCampaignPermissionError("Rol de campaña inválido.")
    return {"id": actor_id, "role": role}


def _safe_reason(value: Any) -> str:
    reason = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_]{3,64}", reason):
        raise EvidenceCampaignError("reason_code de campaña inválido.")
    return reason


def _forbidden_key_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().casefold() in FORBIDDEN_SECRET_KEYS:
                findings.append(child_path)
            findings.extend(_forbidden_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_forbidden_key_paths(child, f"{path}[{index}]"))
    return findings


def _plan_sha256(root: Path) -> str:
    path = root / "config" / "v1" / "evidence_execution_plan.json"
    if not path.is_file():
        raise EvidenceCampaignError("Falta el execution plan RC6.")
    return sha256(path.read_bytes()).hexdigest()


def _safe_source_revision(value: Any) -> str:
    revision = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise EvidenceCampaignError("source_revision debe ser un SHA Git completo de 40 caracteres.")
    return revision


def _safe_environment_fingerprint(value: Any) -> str:
    fingerprint = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise EvidenceCampaignError("environment_fingerprint debe ser un SHA-256 opaco de 64 caracteres.")
    return fingerprint


def _control_status_from_native(status: str, passed: bool) -> str:
    if passed:
        return "VERIFIED"
    upper = str(status or "").upper()
    if "EXPIRED" in upper:
        return "EXPIRED"
    if "INTEGRITY" in upper or "TAMPER" in upper or "BUNDLE_INVALID" in upper:
        return "TAMPERED"
    if upper in {"DOMAIN_APPROVAL_REQUIRED", "INDEPENDENT_REVIEW_REQUIRED"}:
        return "REVIEW_REQUIRED"
    if upper == "RELEASE_RATIFICATION_REQUIRED":
        return "RATIFICATION_REQUIRED"
    if upper in {"MISSING_EVIDENCE", "NO_ACTIVE_BUNDLE", "DOSSIER_UNAVAILABLE"}:
        return "MISSING"
    return "PENDING"


class EvidenceCampaignLedger:
    """Ledger append-only de coordinación; nunca sustituye evidencia o autorización."""

    def __init__(
        self,
        root: str | Path,
        *,
        ledger_path: str | Path | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        policy_path = self.root / "config" / "v1" / "rc8_evidence_campaign_policy.json"
        if not policy_path.is_file():
            raise EvidenceCampaignError("Falta la política RC8 de campañas.")
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.plan = EvidenceExecutionPlan(self.root)
        validation = self.plan.validate()
        if not validation.valid:
            raise EvidenceCampaignError("El execution plan RC6 no es estructuralmente válido.")
        self.controls = {str(row["ref"]): row for row in self.plan.plan["controls"]}
        self._validate_policy()
        runtime = Path(str(os.environ.get("LEGAL_RUNTIME_DIR") or (self.root / "runtime"))).expanduser()
        default_path = runtime / "release-readiness" / "evidence-campaigns.jsonl"
        self.path = Path(
            ledger_path or os.environ.get("LEGAL_EVIDENCE_CAMPAIGN_LEDGER") or default_path
        ).expanduser().resolve()
        self.now_factory = now_factory or _now

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != POLICY_SCHEMA or self.policy.get("campaign_schema") != CAMPAIGN_SCHEMA:
            raise EvidenceCampaignError("Política o schema de campaña RC8 inválidos.")
        if set(self.policy.get("event_types") or []) != set(EVENT_TYPES):
            raise EvidenceCampaignError("La política RC8 perdió tipos de evento canónicos.")
        managers = set(self.policy.get("manager_roles") or [])
        if not {"admin", "qa"}.issubset(managers):
            raise EvidenceCampaignError("La política RC8 perdió roles mínimos de gobierno.")
        governance = self.policy.get("governance") or {}
        required_true = (
            "append_only", "hash_chain_required", "campaign_pins_exact_plan_hash",
            "campaign_pins_source_revision", "environment_fingerprint_required",
            "campaign_events_are_coordination_only", "evidence_link_is_not_evidence_registration",
            "review_ready_is_not_review_approval", "evidence_complete_is_not_release_authorization",
            "dependencies_are_read_from_execution_plan_only", "control_equivalence_is_never_inferred",
            "campaign_cannot_mutate_evidence_ledgers", "campaign_cannot_mutate_release_metadata",
            "campaign_cannot_authorize_real_production", "campaign_cannot_authorize_real_payments",
            "secrets_forbidden",
        )
        for key in required_true:
            if governance.get(key) is not True:
                raise EvidenceCampaignError(f"Gobierno RC8 inválido: {key}.")
        if _forbidden_key_paths(self.policy):
            raise EvidenceCampaignError("La política RC8 contiene claves capaces de almacenar secretos.")

    @property
    def plan_sha256(self) -> str:
        return _plan_sha256(self.root)

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
                    raise EvidenceCampaignIntegrityError("Evento RC8 inválido.")
                rows.append(row)
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceCampaignIntegrityError("No fue posible leer íntegramente el ledger RC8.") from exc
        return rows

    def verify_chain(self) -> dict[str, Any]:
        previous = "0" * 64
        try:
            events = self._read_events()
        except EvidenceCampaignIntegrityError:
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
                or str(event.get("previous_hash") or "") != previous
                or stored != calculated
            ):
                return {"valid": False, "events": len(events), "failed_sequence": expected_sequence, "last_hash": previous}
            previous = stored
        return {"valid": True, "events": len(events), "failed_sequence": None, "last_hash": previous}

    def _append(
        self,
        event_type: str,
        campaign_id: str,
        actor: Mapping[str, Any],
        payload: Mapping[str, Any],
        *,
        control_ref: str | None = None,
    ) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise EvidenceCampaignError("Tipo de evento RC8 inválido.")
        if control_ref is not None and control_ref not in self.controls:
            raise EvidenceCampaignError("Control RC8 desconocido.")
        safe_actor = _safe_actor(actor)
        safe_payload = dict(payload)
        if _forbidden_key_paths(safe_payload):
            raise EvidenceCampaignError("El evento RC8 contiene claves capaces de almacenar secretos.")
        with _LOCK:
            integrity = self.verify_chain()
            if not integrity.get("valid"):
                raise EvidenceCampaignIntegrityError("La cadena RC8 está alterada; no admite nuevas actuaciones.")
            event = {
                "schema_version": SCHEMA_VERSION,
                "sequence": int(integrity.get("events") or 0) + 1,
                "event_id": f"CMP-EVT-{uuid4().hex.upper()}",
                "event_type": event_type,
                "campaign_id": campaign_id,
                "control_ref": control_ref,
                "created_at": self.now_factory().astimezone(timezone.utc).isoformat(timespec="seconds"),
                "actor": safe_actor,
                "payload": safe_payload,
                "previous_hash": str(integrity.get("last_hash") or "0" * 64),
            }
            event["event_hash"] = sha256(_canonical_json(event).encode("utf-8")).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return dict(event)

    def _campaign_events(self, campaign_id: str) -> list[dict[str, Any]]:
        return [row for row in self._read_events() if str(row.get("campaign_id") or "") == campaign_id]

    def _campaign_created(self, campaign_id: str) -> dict[str, Any]:
        created = next((row for row in self._campaign_events(campaign_id) if row.get("event_type") == "CAMPAIGN_CREATED"), None)
        if not created:
            raise EvidenceCampaignError("Campaña RC8 desconocida.")
        return created

    def _assert_manager(self, actor: Mapping[str, Any]) -> dict[str, str]:
        safe = _safe_actor(actor)
        if safe["role"] not in set(self.policy.get("manager_roles") or []):
            raise EvidenceCampaignPermissionError("El rol no puede administrar campañas RC8.")
        return safe

    def _assert_plan_current(self, campaign_id: str) -> dict[str, Any]:
        created = self._campaign_created(campaign_id)
        pinned = str((created.get("payload") or {}).get("plan_sha256") or "")
        if pinned != self.plan_sha256:
            raise EvidenceCampaignIntegrityError("El execution plan cambió después de crear la campaña.")
        return created

    def create_campaign(
        self,
        *,
        environment_fingerprint: str,
        source_revision: str,
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        safe_actor = self._assert_manager(actor)
        fingerprint = _safe_environment_fingerprint(environment_fingerprint)
        revision = _safe_source_revision(source_revision)
        campaign_id = f"CMP-{uuid4().hex.upper()}"
        return self._append(
            "CAMPAIGN_CREATED",
            campaign_id,
            safe_actor,
            {
                "campaign_schema": CAMPAIGN_SCHEMA,
                "plan_schema": str(self.plan.plan.get("schema") or ""),
                "plan_schema_version": int(self.plan.plan.get("schema_version") or 0),
                "plan_sha256": self.plan_sha256,
                "source_revision": revision,
                "environment_fingerprint": fingerprint,
                "control_count": len(self.controls),
                "rc2_count": sum(1 for row in self.controls.values() if row.get("source_framework") == "RC2"),
                "rc4_count": sum(1 for row in self.controls.values() if row.get("source_framework") == "RC4"),
            },
        )

    def task_packet(self, control_ref: str) -> dict[str, Any]:
        row = self.controls.get(control_ref)
        if not row:
            raise EvidenceCampaignError("Control RC8 desconocido.")
        packet = {
            "schema": "legalaiz-v1-rc8-operator-task-packet-v1",
            "control_ref": control_ref,
            "source_framework": row["source_framework"],
            "source_id": row["source_id"],
            "domain": row["domain"],
            "environment": row["environment"],
            "executor_role": row["executor_role"],
            "reviewer_role": row["reviewer_role"],
            "release_scope": row["release_scope"],
            "artifact_type": row["artifact_type"],
            "required_artifacts": list(row["required_artifacts"]),
            "max_validity_days": row["max_validity_days"],
            "prerequisites": list(row.get("prerequisites") or []),
            "redaction_policy": row["redaction_policy"],
            "bundle_schema": "legalaiz-v1-external-evidence-bundle-v1",
            "operator_checklist": [
                "Confirmar que las dependencias declaradas por RC6 estén verificadas antes de ejecutar.",
                "Ejecutar el control en el entorno exacto declarado por RC6.",
                "Recolectar únicamente los artefactos obligatorios y redactar información sensible.",
                "Construir manifest.json con hashes SHA-256 y tamaños reales de los artefactos.",
                "Ingresar la evidencia mediante el dossier canónico RC2 o RC7 según source_framework.",
                "No considerar el registro, la revisión ni la ratificación como autorización de go-live.",
            ],
            "evidence_ref": None,
            "coordination_only": True,
            "release_authorization": False,
        }
        if _forbidden_key_paths(packet):
            raise EvidenceCampaignError("El task packet RC8 contiene claves prohibidas.")
        return packet

    def all_task_packets(self) -> list[dict[str, Any]]:
        return [self.task_packet(ref) for ref in self.controls]

    def _current_evidence(self, control_ref: str) -> dict[str, Any]:
        framework, source_id = control_ref.split(":", 1)
        if framework == "RC2":
            try:
                dossier = ExternalEvidenceDossier(self.root)
                internal = dossier.internal_summary()
                row = next((item for item in internal.get("checks") or [] if str(item.get("key") or "") == source_id), {})
                passed = bool(row.get("passed"))
                native_status = str(row.get("status") or "MISSING_EVIDENCE")
                evidence_path = str(row.get("evidence_path") or "").strip()
                if passed:
                    bundle_valid = False
                    candidate = Path(evidence_path.replace("\\", "/"))
                    if candidate.name == "manifest.json" and candidate.parent.as_posix() not in {"", "."}:
                        try:
                            validator = EvidenceBundleValidator(self.root, dossier.evidence_root, now_factory=dossier.now_factory)
                            validator.validate(candidate.parent.as_posix(), expected_control_ref=control_ref)
                            bundle_valid = True
                        except (EvidenceBundleError, OSError, ValueError, TypeError):
                            bundle_valid = False
                    if not bundle_valid:
                        passed = False
                        native_status = "BUNDLE_INVALID"
                return {"evidence_event_id": row.get("evidence_event_id"), "native_status": native_status, "passed": passed}
            except ExternalEvidenceError:
                return {"evidence_event_id": None, "native_status": "DOSSIER_UNAVAILABLE", "passed": False}
        if framework == "RC4":
            try:
                dossier = ExternalAttestationDossier(self.root)
                internal = dossier.internal_summary()
                row = next((item for item in internal.get("checks") or [] if str(item.get("key") or "") == source_id), {})
                return {
                    "evidence_event_id": row.get("evidence_event_id"),
                    "native_status": str(row.get("status") or "MISSING_EVIDENCE"),
                    "passed": bool(row.get("passed")),
                }
            except ExternalAttestationError:
                return {"evidence_event_id": None, "native_status": "DOSSIER_UNAVAILABLE", "passed": False}
        return {"evidence_event_id": None, "native_status": "DOSSIER_UNAVAILABLE", "passed": False}

    def _verified_controls(self) -> set[str]:
        return {ref for ref in self.controls if self._current_evidence(ref)["passed"]}

    def start_control(self, campaign_id: str, control_ref: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_plan_current(campaign_id)
        row = self.controls.get(control_ref)
        if not row:
            raise EvidenceCampaignError("Control RC8 desconocido.")
        safe_actor = _safe_actor(actor)
        if safe_actor["role"] != str(row.get("executor_role") or ""):
            raise EvidenceCampaignPermissionError("Sólo el rol ejecutor RC6 puede iniciar este control.")
        verified = self._verified_controls()
        blockers = [dep for dep in row.get("prerequisites") or [] if dep not in verified]
        if blockers:
            raise EvidenceCampaignError("Dependencias no verificadas: " + ", ".join(blockers))
        return self._append("CONTROL_STARTED", campaign_id, safe_actor, {"plan_sha256": self.plan_sha256}, control_ref=control_ref)

    def link_evidence(
        self,
        campaign_id: str,
        control_ref: str,
        evidence_event_id: str,
        *,
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._assert_plan_current(campaign_id)
        safe_actor = self._assert_manager(actor)
        current = self._current_evidence(control_ref)
        current_id = str(current.get("evidence_event_id") or "")
        supplied = str(evidence_event_id or "").strip()
        if not supplied or supplied != current_id:
            raise EvidenceCampaignError("La referencia no coincide con la evidencia activa del dossier canónico.")
        return self._append(
            "EVIDENCE_LINKED",
            campaign_id,
            safe_actor,
            {"evidence_event_id": supplied, "native_status_at_link": current["native_status"]},
            control_ref=control_ref,
        )

    def mark_review_ready(self, campaign_id: str, control_ref: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_plan_current(campaign_id)
        safe_actor = self._assert_manager(actor)
        state = self._current_evidence(control_ref)
        if not state.get("evidence_event_id"):
            raise EvidenceCampaignError("No existe evidencia activa para marcar coordinación de revisión.")
        canonical = _control_status_from_native(str(state["native_status"]), bool(state["passed"]))
        if canonical not in {"REVIEW_REQUIRED", "RATIFICATION_REQUIRED", "VERIFIED"}:
            raise EvidenceCampaignError("La evidencia todavía no está en una etapa revisable.")
        return self._append(
            "CONTROL_REVIEW_READY",
            campaign_id,
            safe_actor,
            {"evidence_event_id": state["evidence_event_id"], "native_status_at_mark": state["native_status"], "approval_performed": False},
            control_ref=control_ref,
        )

    def block_control(
        self,
        campaign_id: str,
        control_ref: str,
        *,
        reason_code: str,
        actor: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._assert_plan_current(campaign_id)
        safe_actor = _safe_actor(actor)
        row = self.controls.get(control_ref)
        if not row:
            raise EvidenceCampaignError("Control RC8 desconocido.")
        allowed = set(self.policy.get("manager_roles") or []) | {str(row.get("executor_role") or "")}
        if safe_actor["role"] not in allowed:
            raise EvidenceCampaignPermissionError("El rol no puede bloquear este control.")
        return self._append("CONTROL_BLOCKED", campaign_id, safe_actor, {"reason_code": _safe_reason(reason_code)}, control_ref=control_ref)

    def abort_campaign(self, campaign_id: str, *, reason_code: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_plan_current(campaign_id)
        safe_actor = self._assert_manager(actor)
        return self._append("CAMPAIGN_ABORTED", campaign_id, safe_actor, {"reason_code": _safe_reason(reason_code)})

    def campaign_state(self, campaign_id: str) -> dict[str, Any]:
        created = self._campaign_created(campaign_id)
        events = self._campaign_events(campaign_id)
        payload = created.get("payload") or {}
        plan_current = str(payload.get("plan_sha256") or "") == self.plan_sha256
        aborted = any(row.get("event_type") == "CAMPAIGN_ABORTED" for row in events)
        latest_by_control: dict[str, dict[str, Any]] = {}
        for row in events:
            ref = str(row.get("control_ref") or "")
            if ref:
                latest_by_control[ref] = row
        explicit_blocks = [row for row in latest_by_control.values() if row.get("event_type") == "CONTROL_BLOCKED"]
        audit = EvidenceAuditDossier(self.root, campaign_ledger=self).build(campaign_id=campaign_id)
        verified = int(audit["summary"]["verified"])
        if aborted:
            status = "ABORTED"
        elif not plan_current or explicit_blocks or int(audit["summary"]["dependency_blocked"]) > 0:
            status = "BLOCKED"
        elif verified == len(self.controls):
            status = "EVIDENCE_COMPLETE"
        elif any(row.get("event_type") == "CONTROL_REVIEW_READY" for row in events):
            status = "READY_FOR_REVIEW"
        elif len(events) > 1:
            status = "IN_PROGRESS"
        else:
            status = "CREATED"
        return {
            "schema": "legalaiz-v1-rc8-campaign-state-v1",
            "campaign_id": campaign_id,
            "status": status,
            "plan_hash_current": plan_current,
            "pinned_plan_sha256": payload.get("plan_sha256"),
            "current_plan_sha256": self.plan_sha256,
            "source_revision": payload.get("source_revision"),
            "environment_fingerprint": payload.get("environment_fingerprint"),
            "events": len(events),
            "verified_controls": verified,
            "total_controls": len(self.controls),
            "release_authorized": False,
            "commercial_authorized": False,
        }


class EvidenceAuditDossier:
    """Read model de plan + evidencia + coordinación, sin modificar ninguna fuente."""

    def __init__(self, root: str | Path, *, campaign_ledger: EvidenceCampaignLedger | None = None) -> None:
        self.root = Path(root).resolve()
        self.plan = EvidenceExecutionPlan(self.root)
        validation = self.plan.validate()
        if not validation.valid:
            raise EvidenceCampaignError("El execution plan RC6 no es válido.")
        self.controls = {str(row["ref"]): row for row in self.plan.plan["controls"]}
        self.campaign_ledger = campaign_ledger

    def _native_states(self) -> dict[str, dict[str, Any]]:
        states: dict[str, dict[str, Any]] = {}
        try:
            dossier = ExternalEvidenceDossier(self.root)
            rc2 = dossier.internal_summary()
            for row in rc2.get("checks") or []:
                ref = f"RC2:{row.get('key')}"
                passed = bool(row.get("passed"))
                native_status = str(row.get("status") or "MISSING_EVIDENCE")
                evidence_path = str(row.get("evidence_path") or "").strip()
                if passed:
                    bundle_valid = False
                    candidate = Path(evidence_path.replace("\\", "/"))
                    if candidate.name == "manifest.json" and candidate.parent.as_posix() not in {"", "."}:
                        try:
                            validator = EvidenceBundleValidator(self.root, dossier.evidence_root, now_factory=dossier.now_factory)
                            validator.validate(candidate.parent.as_posix(), expected_control_ref=ref)
                            bundle_valid = True
                        except (EvidenceBundleError, OSError, ValueError, TypeError):
                            bundle_valid = False
                    if not bundle_valid:
                        passed = False
                        native_status = "BUNDLE_INVALID"
                states[ref] = {
                    "native_status": native_status,
                    "passed": passed,
                    "evidence_event_id": row.get("evidence_event_id"),
                }
        except ExternalEvidenceError:
            pass
        try:
            rc4 = ExternalAttestationDossier(self.root).internal_summary()
            for row in rc4.get("checks") or []:
                ref = f"RC4:{row.get('key')}"
                states[ref] = {
                    "native_status": str(row.get("status") or "MISSING_EVIDENCE"),
                    "passed": bool(row.get("passed")),
                    "evidence_event_id": row.get("evidence_event_id"),
                }
        except ExternalAttestationError:
            pass
        return states

    def build(self, *, campaign_id: str | None = None) -> dict[str, Any]:
        native = self._native_states()
        verified = {ref for ref, row in native.items() if bool(row.get("passed"))}
        campaign_events: list[dict[str, Any]] = []
        plan_current = True
        if campaign_id and self.campaign_ledger:
            created = self.campaign_ledger._campaign_created(campaign_id)
            campaign_events = self.campaign_ledger._campaign_events(campaign_id)
            plan_current = str((created.get("payload") or {}).get("plan_sha256") or "") == _plan_sha256(self.root)

        controls: list[dict[str, Any]] = []
        dependency_blocked = 0
        status_counts: dict[str, int] = {}
        for ref, plan_row in self.controls.items():
            state = native.get(ref) or {"native_status": "MISSING_EVIDENCE", "passed": False, "evidence_event_id": None}
            canonical = _control_status_from_native(str(state["native_status"]), bool(state["passed"]))
            blockers = [dep for dep in plan_row.get("prerequisites") or [] if dep not in verified]
            if blockers and canonical != "VERIFIED":
                canonical = "BLOCKED_BY_DEPENDENCY"
                dependency_blocked += 1
            if not plan_current and canonical != "VERIFIED":
                canonical = "BLOCKED_BY_PLAN_DRIFT"
            active_id = str(state.get("evidence_event_id") or "")
            linked = bool(campaign_id and active_id and any(
                row.get("event_type") == "EVIDENCE_LINKED"
                and row.get("control_ref") == ref
                and str((row.get("payload") or {}).get("evidence_event_id") or "") == active_id
                for row in campaign_events
            ))
            status_counts[canonical] = status_counts.get(canonical, 0) + 1
            controls.append({
                "control_ref": ref,
                "source_framework": plan_row["source_framework"],
                "source_id": plan_row["source_id"],
                "domain": plan_row["domain"],
                "environment": plan_row["environment"],
                "release_scope": plan_row["release_scope"],
                "executor_role": plan_row["executor_role"],
                "reviewer_role": plan_row["reviewer_role"],
                "prerequisites": list(plan_row.get("prerequisites") or []),
                "dependency_blockers": blockers,
                "status": canonical,
                "native_status": state["native_status"],
                "passed": bool(state["passed"]),
                "evidence_event_id": state.get("evidence_event_id"),
                "campaign_evidence_linked": linked,
            })

        production = [row for row in controls if row["release_scope"] == "real_production"]
        commercial_only = [row for row in controls if row["release_scope"] == "commercial_only"]
        verified_count = sum(1 for row in controls if row["status"] == "VERIFIED")
        production_complete = bool(production) and all(row["status"] == "VERIFIED" for row in production)
        commercial_complete = production_complete and bool(commercial_only) and all(row["status"] == "VERIFIED" for row in commercial_only)
        return {
            "schema": "legalaiz-v1-rc8-evidence-audit-dossier-v1",
            "plan_sha256": _plan_sha256(self.root),
            "plan_schema": self.plan.plan.get("schema"),
            "control_count": len(controls),
            "rc2_count": sum(1 for row in controls if row["source_framework"] == "RC2"),
            "rc4_count": sum(1 for row in controls if row["source_framework"] == "RC4"),
            "campaign_id": campaign_id,
            "plan_hash_current_for_campaign": plan_current,
            "controls": controls,
            "summary": {
                "verified": verified_count,
                "total": len(controls),
                "dependency_blocked": dependency_blocked,
                "status_counts": status_counts,
                "real_production_evidence_complete": production_complete,
                "commercial_evidence_complete": commercial_complete,
                "release_authorized": False,
                "commercial_authorized": False,
            },
            "governance": {
                "audit_is_read_only": True,
                "evidence_complete_is_not_release_authorization": True,
                "rc2_and_rc4_controls_remain_independent": True,
                "dependencies_come_only_from_rc6": True,
            },
        }


__all__ = [
    "CAMPAIGN_SCHEMA",
    "EVENT_TYPES",
    "EvidenceAuditDossier",
    "EvidenceCampaignError",
    "EvidenceCampaignIntegrityError",
    "EvidenceCampaignLedger",
    "EvidenceCampaignPermissionError",
]
