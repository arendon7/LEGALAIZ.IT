from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping
import uuid

from legalai_platform import release_metadata
from legalai_platform.v1_rc2_release_assurance import V1RC2ReleaseAssuranceGate


UTC = timezone.utc
_TRUE = {"1", "true", "yes", "si", "sí", "on"}
_PILOT_ID = re.compile(r"^PILOT-[A-Z0-9][A-Z0-9-]{3,39}$")
_ALLOWED_EVENTS = {"PLAN_REGISTERED", "APPROVAL_RECORDED", "PILOT_RATIFIED", "PLAN_REVOKED"}


class PilotReadinessError(RuntimeError):
    pass


class PilotReadinessPermissionError(PilotReadinessError):
    pass


class PilotReadinessIntegrityError(PilotReadinessError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise PilotReadinessError(f"{field} debe ser fecha ISO YYYY-MM-DD.") from exc


def _flag(value: object) -> bool:
    return str(value or "").strip().lower() in _TRUE


def _provider(value: object) -> str:
    return str(value or "").strip().lower()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _event_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sequence": int(row["sequence"]),
        "event_id": str(row["event_id"]),
        "event_type": str(row["event_type"]),
        "pilot_id": str(row["pilot_id"]),
        "plan_hash": str(row["plan_hash"]),
        "actor_id": str(row["actor_id"]),
        "actor_role": str(row["actor_role"]),
        "payload": dict(row.get("payload") or {}),
        "previous_hash": str(row.get("previous_hash") or ""),
        "created_at": str(row["created_at"]),
    }


@dataclass(frozen=True)
class PilotPlan:
    pilot_id: str
    mode: str
    starts_on: str
    ends_on: str
    max_users: int
    max_tenants: int
    product_codes: tuple[str, ...]
    data_scope: str
    payment_mode: str
    external_communications: str
    purpose: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "pilot_id": self.pilot_id,
            "mode": self.mode,
            "starts_on": self.starts_on,
            "ends_on": self.ends_on,
            "max_users": self.max_users,
            "max_tenants": self.max_tenants,
            "product_codes": list(self.product_codes),
            "data_scope": self.data_scope,
            "payment_mode": self.payment_mode,
            "external_communications": self.external_communications,
            "purpose": self.purpose,
        }


class PilotAuthorizationDossier:
    """Dossier append-only para un plan de piloto acotado y sus aprobaciones.

    El archivo es un ledger local con detección de alteraciones. No es WORM ni una
    firma externa. Las respuestas públicas de `summary()` minimizan actores, hashes
    y contenido libre del propósito.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        dossier_path: str | Path | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        policy_path = self.root / "config" / "v1_pilot_readiness_policy.json"
        if not policy_path.is_file():
            raise PilotReadinessError("Falta la política V1 Pilot Readiness.")
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self._validate_policy()
        self.product_codes = self._load_product_codes()
        raw_path = dossier_path or os.environ.get("LEGAL_PILOT_DOSSIER_PATH") or (
            self.root / "runtime" / "release" / "v1_pilot_readiness.jsonl"
        )
        self.dossier_path = Path(raw_path).resolve()
        self.now_factory = now_factory or _now

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != "legalaizit-v1-pilot-readiness-policy-v1":
            raise PilotReadinessError("Schema V1 Pilot Readiness inválido.")
        if int(self.policy.get("max_duration_days") or 0) <= 0:
            raise PilotReadinessError("La duración máxima del piloto debe ser positiva.")
        if int(self.policy.get("max_users") or 0) <= 0 or int(self.policy.get("max_tenants") or 0) <= 0:
            raise PilotReadinessError("Los límites de usuarios y tenants deben ser positivos.")
        modes = self.policy.get("modes") or {}
        if set(modes) != {"SYNTHETIC_CONTROLLED", "REAL_CLIENT_CONTROLLED"}:
            raise PilotReadinessError("La política debe conservar los dos modos canónicos de piloto.")
        approvals = self.policy.get("required_approvals") or {}
        if set(approvals) != {"legal", "qa", "privacy", "security_operations"}:
            raise PilotReadinessError("La política debe exigir jurídico, QA, privacidad y seguridad/operaciones.")
        if set(approvals.get("legal") or []) != {"specialist"}:
            raise PilotReadinessError("La aprobación jurídica debe pertenecer a specialist.")
        if set(approvals.get("qa") or []) != {"qa"}:
            raise PilotReadinessError("La aprobación QA debe pertenecer a qa.")
        ratifiers = set(self.policy.get("ratifier_roles") or [])
        if not ratifiers or not ratifiers.issubset({"admin", "qa"}):
            raise PilotReadinessError("Los roles de ratificación de piloto son inválidos.")

    def _load_product_codes(self) -> tuple[str, ...]:
        path = self.root / "config" / "m34" / "product_contracts.json"
        if not path.is_file():
            raise PilotReadinessError("Faltan contratos canónicos M34 para validar alcance de piloto.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        codes = tuple(str(row.get("product_code") or "") for row in payload.get("contracts") or [])
        if len(codes) != 11 or len(set(codes)) != 11 or any(not code for code in codes):
            raise PilotReadinessError("El portafolio M34 no conserva exactamente 11 productos canónicos.")
        return codes

    def _rows_unverified(self) -> list[dict[str, Any]]:
        if not self.dossier_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for raw in self.dossier_path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    row = json.loads(raw)
                    if not isinstance(row, dict):
                        raise ValueError("row")
                    rows.append(row)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise PilotReadinessIntegrityError("El dossier de piloto no puede leerse de forma íntegra.") from exc
        return rows

    def verify_chain(self) -> dict[str, Any]:
        rows = self._rows_unverified()
        previous = ""
        for index, row in enumerate(rows, 1):
            if int(row.get("sequence") or 0) != index:
                raise PilotReadinessIntegrityError("Secuencia inválida en dossier de piloto.")
            if str(row.get("event_type") or "") not in _ALLOWED_EVENTS:
                raise PilotReadinessIntegrityError("Evento desconocido en dossier de piloto.")
            if str(row.get("previous_hash") or "") != previous:
                raise PilotReadinessIntegrityError("Cadena previous_hash inválida en dossier de piloto.")
            candidate = _event_candidate(row)
            expected = _digest(candidate)
            if str(row.get("event_hash") or "") != expected:
                raise PilotReadinessIntegrityError("Hash inválido en dossier de piloto.")
            previous = expected
        return {"valid": True, "events": len(rows), "head_hash": previous}

    def _rows(self) -> list[dict[str, Any]]:
        self.verify_chain()
        return self._rows_unverified()

    def _append(
        self,
        *,
        event_type: str,
        pilot_id: str,
        plan_hash: str,
        actor: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if event_type not in _ALLOWED_EVENTS:
            raise PilotReadinessError("Evento de piloto no permitido.")
        actor_id = str(actor.get("id") or "").strip()
        actor_role = str(actor.get("role") or "").strip()
        if not actor_id or not actor_role:
            raise PilotReadinessPermissionError("La actuación requiere actor autenticado y rol explícito.")
        rows = self._rows()
        previous = str(rows[-1].get("event_hash") or "") if rows else ""
        row: dict[str, Any] = {
            "sequence": len(rows) + 1,
            "event_id": f"PLE-{uuid.uuid4().hex[:16].upper()}",
            "event_type": event_type,
            "pilot_id": pilot_id,
            "plan_hash": plan_hash,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "payload": dict(payload),
            "previous_hash": previous,
            "created_at": _iso(self.now_factory()),
        }
        row["event_hash"] = _digest(_event_candidate(row))
        self.dossier_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dossier_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return row

    def _validate_plan(self, raw: Mapping[str, Any]) -> PilotPlan:
        pilot_id = str(raw.get("pilot_id") or "").strip().upper()
        if not _PILOT_ID.fullmatch(pilot_id):
            raise PilotReadinessError("pilot_id inválido; use PILOT- seguido de un identificador estable.")
        mode = str(raw.get("mode") or "").strip().upper()
        mode_policy = (self.policy.get("modes") or {}).get(mode)
        if not mode_policy:
            raise PilotReadinessError("Modo de piloto inválido.")
        starts = _parse_date(raw.get("starts_on"), "starts_on")
        ends = _parse_date(raw.get("ends_on"), "ends_on")
        if ends < starts:
            raise PilotReadinessError("ends_on no puede ser anterior a starts_on.")
        duration = (ends - starts).days + 1
        if duration > int(self.policy["max_duration_days"]):
            raise PilotReadinessError("El piloto excede la duración máxima permitida por política.")
        max_users = int(raw.get("max_users") or 0)
        max_tenants = int(raw.get("max_tenants") or 0)
        if not 1 <= max_users <= int(self.policy["max_users"]):
            raise PilotReadinessError("max_users excede el límite del piloto.")
        if not 1 <= max_tenants <= int(self.policy["max_tenants"]):
            raise PilotReadinessError("max_tenants excede el límite del piloto.")
        products = tuple(sorted({str(value or "").strip() for value in raw.get("product_codes") or [] if str(value or "").strip()}))
        if not products or any(code not in self.product_codes for code in products):
            raise PilotReadinessError("El alcance de productos debe ser un subconjunto no vacío del portafolio canónico.")
        data_scope = str(raw.get("data_scope") or "").strip().upper()
        if data_scope != str(mode_policy.get("data_scope") or ""):
            raise PilotReadinessError("data_scope no coincide con el modo de piloto.")
        payment_mode = str(raw.get("payment_mode") or "").strip().upper()
        if payment_mode not in set(mode_policy.get("payment_modes") or []):
            raise PilotReadinessError("payment_mode no está permitido para este modo de piloto.")
        communications = str(raw.get("external_communications") or "").strip().upper()
        if communications not in set(mode_policy.get("communication_modes") or []):
            raise PilotReadinessError("external_communications no está permitido para este modo de piloto.")
        purpose = " ".join(str(raw.get("purpose") or "").split())
        if not 20 <= len(purpose) <= 500:
            raise PilotReadinessError("El propósito del piloto debe tener entre 20 y 500 caracteres.")
        return PilotPlan(
            pilot_id=pilot_id,
            mode=mode,
            starts_on=starts.isoformat(),
            ends_on=ends.isoformat(),
            max_users=max_users,
            max_tenants=max_tenants,
            product_codes=products,
            data_scope=data_scope,
            payment_mode=payment_mode,
            external_communications=communications,
            purpose=purpose,
        )

    @staticmethod
    def _plan_hash(plan: PilotPlan) -> str:
        return _digest(plan.as_dict())

    def _window_status(self, plan: PilotPlan) -> str:
        today = self.now_factory().astimezone(UTC).date()
        starts = _parse_date(plan.starts_on, "starts_on")
        ends = _parse_date(plan.ends_on, "ends_on")
        if today < starts:
            return "UPCOMING"
        if today > ends:
            return "EXPIRED"
        return "ACTIVE"

    def _active_plan_from_rows(self, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], PilotPlan] | None:
        registered: dict[str, dict[str, Any]] = {}
        revoked: set[str] = set()
        for row in rows:
            event_type = str(row.get("event_type") or "")
            plan_hash = str(row.get("plan_hash") or "")
            if event_type == "PLAN_REGISTERED":
                registered[plan_hash] = row
            elif event_type == "PLAN_REVOKED":
                revoked.add(plan_hash)
        active = [row for key, row in registered.items() if key not in revoked]
        if len(active) > 1:
            raise PilotReadinessIntegrityError("El dossier contiene más de un plan de piloto activo.")
        if not active:
            return None
        row = active[0]
        plan = self._validate_plan(dict((row.get("payload") or {}).get("plan") or {}))
        if self._plan_hash(plan) != str(row.get("plan_hash") or ""):
            raise PilotReadinessIntegrityError("El hash del plan activo no coincide con su contenido.")
        return row, plan

    def active_plan(self) -> tuple[dict[str, Any], PilotPlan] | None:
        return self._active_plan_from_rows(self._rows())

    def register_plan(self, plan_data: Mapping[str, Any], *, actor: Mapping[str, Any]) -> dict[str, Any]:
        if str(actor.get("role") or "") != "admin":
            raise PilotReadinessPermissionError("Sólo administración puede registrar el plan de piloto.")
        rows = self._rows()
        if self._active_plan_from_rows(rows):
            raise PilotReadinessError("Ya existe un plan de piloto activo; debe revocarse antes de registrar otro.")
        plan = self._validate_plan(plan_data)
        plan_hash = self._plan_hash(plan)
        row = self._append(
            event_type="PLAN_REGISTERED",
            pilot_id=plan.pilot_id,
            plan_hash=plan_hash,
            actor=actor,
            payload={"plan": plan.as_dict()},
        )
        return {"pilot_id": plan.pilot_id, "plan_hash": plan_hash, "event_id": row["event_id"]}

    def _approval_rows(self, rows: list[dict[str, Any]], plan_hash: str) -> dict[str, dict[str, Any]]:
        approvals: dict[str, dict[str, Any]] = {}
        for row in rows:
            if str(row.get("plan_hash") or "") != plan_hash or str(row.get("event_type") or "") != "APPROVAL_RECORDED":
                continue
            domain = str((row.get("payload") or {}).get("domain") or "")
            if domain in approvals:
                raise PilotReadinessIntegrityError("Existe más de una aprobación para el mismo dominio y plan.")
            approvals[domain] = row
        return approvals

    def record_approval(self, domain: str, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        domain = str(domain or "").strip().lower()
        allowed = set((self.policy.get("required_approvals") or {}).get(domain) or [])
        if not allowed:
            raise PilotReadinessError("Dominio de aprobación de piloto inválido.")
        actor_role = str(actor.get("role") or "").strip()
        actor_id = str(actor.get("id") or "").strip()
        if actor_role not in allowed or not actor_id:
            raise PilotReadinessPermissionError("El actor no puede aprobar este dominio de piloto.")
        rows = self._rows()
        active = self._active_plan_from_rows(rows)
        if not active:
            raise PilotReadinessError("No existe plan de piloto activo.")
        _registered, plan = active
        plan_hash = self._plan_hash(plan)
        approvals = self._approval_rows(rows, plan_hash)
        if domain in approvals:
            existing = approvals[domain]
            if str(existing.get("actor_id") or "") == actor_id and str(existing.get("actor_role") or "") == actor_role:
                return {"pilot_id": plan.pilot_id, "domain": domain, "idempotent": True}
            raise PilotReadinessError("El dominio ya tiene una aprobación; el plan debe revocarse para cambiarla.")
        separation_pairs = [tuple(pair) for pair in (self.policy.get("separation") or {}).get("approval_pairs") or []]
        for left, right in separation_pairs:
            other = right if domain == left else left if domain == right else None
            if other and other in approvals and str(approvals[other].get("actor_id") or "") == actor_id:
                raise PilotReadinessPermissionError("La separación de funciones impide usar el mismo actor en estas aprobaciones.")
        row = self._append(
            event_type="APPROVAL_RECORDED",
            pilot_id=plan.pilot_id,
            plan_hash=plan_hash,
            actor=actor,
            payload={"domain": domain},
        )
        return {"pilot_id": plan.pilot_id, "domain": domain, "event_id": row["event_id"], "idempotent": False}

    def ratify(self, *, actor: Mapping[str, Any]) -> dict[str, Any]:
        actor_role = str(actor.get("role") or "").strip()
        actor_id = str(actor.get("id") or "").strip()
        if actor_role not in set(self.policy.get("ratifier_roles") or []) or not actor_id:
            raise PilotReadinessPermissionError("El actor no puede ratificar el piloto.")
        rows = self._rows()
        active = self._active_plan_from_rows(rows)
        if not active:
            raise PilotReadinessError("No existe plan de piloto activo.")
        _registered, plan = active
        plan_hash = self._plan_hash(plan)
        approvals = self._approval_rows(rows, plan_hash)
        required = set((self.policy.get("required_approvals") or {}).keys())
        missing = sorted(required - set(approvals))
        if missing:
            raise PilotReadinessError("Faltan aprobaciones de piloto: " + ", ".join(missing))
        distinct_domains = set((self.policy.get("separation") or {}).get("ratifier_distinct_from") or [])
        if any(str(approvals[domain].get("actor_id") or "") == actor_id for domain in distinct_domains):
            raise PilotReadinessPermissionError("El ratificador debe ser distinto de los aprobadores jurídico y QA.")
        existing = [
            row for row in rows
            if str(row.get("plan_hash") or "") == plan_hash and str(row.get("event_type") or "") == "PILOT_RATIFIED"
        ]
        if existing:
            row = existing[0]
            if str(row.get("actor_id") or "") == actor_id and str(row.get("actor_role") or "") == actor_role:
                return {"pilot_id": plan.pilot_id, "ratified": True, "idempotent": True}
            raise PilotReadinessError("El plan ya fue ratificado por otro actor; no se sobreescribe.")
        row = self._append(
            event_type="PILOT_RATIFIED",
            pilot_id=plan.pilot_id,
            plan_hash=plan_hash,
            actor=actor,
            payload={"approved_domains": sorted(required)},
        )
        return {"pilot_id": plan.pilot_id, "ratified": True, "event_id": row["event_id"], "idempotent": False}

    def revoke(self, *, reason_code: str, actor: Mapping[str, Any]) -> dict[str, Any]:
        actor_role = str(actor.get("role") or "").strip()
        if actor_role not in set(self.policy.get("ratifier_roles") or []):
            raise PilotReadinessPermissionError("El actor no puede revocar el plan de piloto.")
        reason = str(reason_code or "").strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", reason):
            raise PilotReadinessError("reason_code de revocación inválido.")
        rows = self._rows()
        active = self._active_plan_from_rows(rows)
        if not active:
            raise PilotReadinessError("No existe plan activo para revocar.")
        _registered, plan = active
        plan_hash = self._plan_hash(plan)
        row = self._append(
            event_type="PLAN_REVOKED",
            pilot_id=plan.pilot_id,
            plan_hash=plan_hash,
            actor=actor,
            payload={"reason_code": reason},
        )
        return {"pilot_id": plan.pilot_id, "revoked": True, "event_id": row["event_id"]}

    def summary(self) -> dict[str, Any]:
        try:
            rows = self._rows()
        except PilotReadinessIntegrityError:
            return {
                "schema": "legalaizit-v1-pilot-dossier-summary-v1",
                "integrity": "invalid",
                "ready": False,
                "active_plan": None,
                "approvals": [],
                "ratified": False,
            }
        active = self._active_plan_from_rows(rows)
        if not active:
            return {
                "schema": "legalaizit-v1-pilot-dossier-summary-v1",
                "integrity": "valid",
                "ready": False,
                "active_plan": None,
                "approvals": [
                    {"domain": domain, "passed": False, "status": "NO_ACTIVE_PLAN"}
                    for domain in (self.policy.get("required_approvals") or {})
                ],
                "ratified": False,
            }
        _registered, plan = active
        plan_hash = self._plan_hash(plan)
        approvals = self._approval_rows(rows, plan_hash)
        approval_summary = [
            {
                "domain": domain,
                "passed": domain in approvals,
                "status": "APPROVED" if domain in approvals else "APPROVAL_REQUIRED",
            }
            for domain in (self.policy.get("required_approvals") or {})
        ]
        ratified = any(
            str(row.get("plan_hash") or "") == plan_hash and str(row.get("event_type") or "") == "PILOT_RATIFIED"
            for row in rows
        )
        window_status = self._window_status(plan)
        return {
            "schema": "legalaizit-v1-pilot-dossier-summary-v1",
            "integrity": "valid",
            "ready": bool(all(item["passed"] for item in approval_summary) and ratified),
            "active_plan": {
                "pilot_id": plan.pilot_id,
                "mode": plan.mode,
                "starts_on": plan.starts_on,
                "ends_on": plan.ends_on,
                "window_status": window_status,
                "max_users": plan.max_users,
                "max_tenants": plan.max_tenants,
                "product_count": len(plan.product_codes),
                "data_scope": plan.data_scope,
                "payment_mode": plan.payment_mode,
                "external_communications": plan.external_communications,
            },
            "approvals": approval_summary,
            "ratified": ratified,
        }


class V1PilotReadinessGate:
    """Read model final para preparación y eventual autorización de piloto.

    No escribe configuración ni cambia release metadata. Un plan con clientes reales
    sólo puede quedar listo cuando la metadata versionada permita producción real.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        dossier: PilotAuthorizationDossier | None = None,
        rc2_gate: V1RC2ReleaseAssuranceGate | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.dossier = dossier or PilotAuthorizationDossier(self.root)
        self.policy = self.dossier.policy
        self.rc2 = rc2_gate or V1RC2ReleaseAssuranceGate(self.root)

    @staticmethod
    def _metadata() -> dict[str, bool]:
        return {
            "REAL_PRODUCTION_AUTHORIZED": bool(release_metadata.REAL_PRODUCTION_AUTHORIZED),
            "REAL_PAYMENTS_AUTHORIZED": bool(release_metadata.REAL_PAYMENTS_AUTHORIZED),
            "SYNTHETIC_DATA_ONLY": bool(release_metadata.SYNTHETIC_DATA_ONLY),
        }

    def evaluate(self, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
        env: Mapping[str, str] = os.environ if environ is None else environ
        rc2 = self.rc2.evaluate(env)
        pilot = self.dossier.summary()
        plan = pilot.get("active_plan") or {}
        mode = str(plan.get("mode") or "")
        window_status = str(plan.get("window_status") or "")
        window_active = window_status == "ACTIVE"
        technical_ready = bool(rc2.get("ready_for_controlled_production_validation"))
        governance_ready = bool(pilot.get("integrity") == "valid" and pilot.get("ready"))
        preparation_ready = bool(technical_ready and governance_ready)
        metadata = self._metadata()

        real_client_checks = [
            {
                "key": key,
                "passed": metadata.get(key) is expected,
            }
            for key, expected in (self.policy.get("real_client_release_metadata") or {}).items()
        ]
        payment_mode = str(plan.get("payment_mode") or "")
        communications_mode = str(plan.get("external_communications") or "")

        payment_checks: list[dict[str, Any]] = []
        if payment_mode == "REAL_PROVIDER":
            payment_cfg = self.policy.get("real_payment_env") or {}
            payment_checks = [
                {"key": "REAL_PAYMENTS_AUTHORIZED", "passed": metadata.get("REAL_PAYMENTS_AUTHORIZED") is True},
                {"key": str(payment_cfg.get("authorization") or "LEGAL_REAL_PAYMENTS_AUTHORIZED"), "passed": _flag(env.get(str(payment_cfg.get("authorization") or "")))},
                {
                    "key": "payment_provider_real",
                    "passed": _provider(env.get(str(payment_cfg.get("provider") or "")))
                    not in set(payment_cfg.get("disallowed_providers") or []),
                },
            ]

        communication_checks: list[dict[str, Any]] = []
        if communications_mode == "REAL_PROVIDER":
            comm_cfg = self.policy.get("real_communications_env") or {}
            communication_checks = [
                {"key": str(comm_cfg.get("authorization") or "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED"), "passed": _flag(env.get(str(comm_cfg.get("authorization") or "")))},
                {
                    "key": "communications_provider_real",
                    "passed": _provider(env.get(str(comm_cfg.get("provider") or "")))
                    not in set(comm_cfg.get("disallowed_providers") or []),
                },
            ]

        real_client_blockers = [row["key"] for row in [*real_client_checks, *payment_checks, *communication_checks] if not row["passed"]]
        if mode == "SYNTHETIC_CONTROLLED":
            mode_ready = bool(preparation_ready and window_active and metadata.get("SYNTHETIC_DATA_ONLY") is True)
        elif mode == "REAL_CLIENT_CONTROLLED":
            mode_ready = bool(preparation_ready and window_active and not real_client_blockers)
        else:
            mode_ready = False

        execution_request_env = str(self.policy.get("execution_request_env") or "LEGAL_PILOT_EXECUTION_REQUESTED")
        execution_requested = _flag(env.get(execution_request_env))
        safe_execution_claim = bool(not execution_requested or mode_ready)

        if not technical_ready:
            state = "BLOCKED_RC2_ASSURANCE"
        elif not governance_ready:
            state = "BLOCKED_PILOT_GOVERNANCE"
        elif window_status == "UPCOMING":
            state = "READY_AWAITING_PILOT_WINDOW"
        elif window_status == "EXPIRED":
            state = "BLOCKED_PILOT_WINDOW_EXPIRED"
        elif mode == "SYNTHETIC_CONTROLLED" and mode_ready:
            state = "READY_FOR_SYNTHETIC_CONTROLLED_PILOT"
        elif mode == "REAL_CLIENT_CONTROLLED" and real_client_blockers:
            state = "BLOCKED_REAL_CLIENT_AUTHORIZATION"
        elif mode == "REAL_CLIENT_CONTROLLED" and mode_ready:
            state = "REAL_CLIENT_PILOT_READY"
        else:
            state = "BLOCKED_PILOT_POLICY"
        if execution_requested and not safe_execution_claim:
            state = "BLOCKED_UNSAFE_PILOT_EXECUTION_CLAIM"

        return {
            "schema": "legalaizit-v1-pilot-readiness-report-v1",
            "candidate": str(self.policy.get("candidate") or "V1-PILOT-READINESS"),
            "state": state,
            "rc2": {
                "state": str(rc2.get("state") or "UNKNOWN"),
                "controlled_validation_ready": technical_ready,
            },
            "pilot": pilot,
            "release_metadata": metadata,
            "readiness": {
                "technical_preparation_ready": preparation_ready,
                "pilot_window_active": window_active,
                "pilot_mode_ready": mode_ready,
                "execution_requested": execution_requested,
                "safe_execution_claim": safe_execution_claim,
                "real_client_blockers": real_client_blockers if mode == "REAL_CLIENT_CONTROLLED" else [],
            },
            "notices": list(self.policy.get("principles") or []),
        }

    def assert_safe_execution_claim(self, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
        report = self.evaluate(environ)
        if not (report.get("readiness") or {}).get("safe_execution_claim"):
            blockers = (report.get("readiness") or {}).get("real_client_blockers") or [str(report.get("state") or "UNKNOWN")]
            raise PilotReadinessError("Ejecución de piloto bloqueada: " + ", ".join(str(item) for item in blockers))
        return report


__all__ = [
    "PilotAuthorizationDossier",
    "PilotPlan",
    "PilotReadinessError",
    "PilotReadinessIntegrityError",
    "PilotReadinessPermissionError",
    "V1PilotReadinessGate",
]
