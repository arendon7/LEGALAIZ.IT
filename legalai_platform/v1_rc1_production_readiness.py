from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from legalai_platform import release_metadata
from legalai_platform.deployment_environment import production_startup_report
from legalai_platform.operational_security import ExternalAttestationRegistry


_TRUE = {"1", "true", "yes", "si", "sí", "on"}


class V1RC1ReadinessError(RuntimeError):
    pass


def _flag(value: str | None) -> bool:
    return str(value or "").strip().lower() in _TRUE


def _provider(value: str | None) -> str:
    return str(value or "").strip().lower()


class V1RC1ProductionReadinessGate:
    """Compone seguridad de arranque, evidencia externa y autorización comercial.

    La clase no habilita proveedores ni escribe estado. Su salida es un read model
    determinista y minimizado. La autorización comercial requiere simultáneamente
    configuración segura, evidencia externa, flags humanos, proveedores no-sandbox
    y metadata de release que lo permita.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        policy_path = self.root / "config" / "v1_rc1_production_readiness.json"
        if not policy_path.is_file():
            raise V1RC1ReadinessError("Falta la política V1-RC1 de production readiness.")
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self._validate_policy()

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != "legalaizit-v1-rc1-production-readiness-v1":
            raise V1RC1ReadinessError("Schema V1-RC1 inválido.")
        startup = self.policy.get("startup") or {}
        commercial = self.policy.get("commercial_launch") or {}
        if startup.get("profile") != "production" or startup.get("database_backend") != "postgresql":
            raise V1RC1ReadinessError("La política RC1 debe exigir production + PostgreSQL.")
        required_roles = set(startup.get("required_mfa_roles") or [])
        if not {"admin", "specialist"}.issubset(required_roles):
            raise V1RC1ReadinessError("RC1 debe exigir MFA para admin y specialist.")
        expected_attestations = set(ExternalAttestationRegistry.REQUIRED)
        if set(self.policy.get("external_attestations") or []) != expected_attestations:
            raise V1RC1ReadinessError("RC1 debe cubrir exactamente las atestaciones externas canónicas.")
        metadata = commercial.get("release_metadata") or {}
        expected_metadata = {
            "REAL_PRODUCTION_AUTHORIZED": True,
            "REAL_PAYMENTS_AUTHORIZED": True,
            "SYNTHETIC_DATA_ONLY": False,
        }
        if metadata != expected_metadata:
            raise V1RC1ReadinessError("La frontera de release metadata RC1 fue debilitada.")

    def external_summary(self) -> dict:
        raw = ExternalAttestationRegistry(self.root).summary()
        checks = raw.get("checks") or []
        missing = [str(row.get("key")) for row in checks if not row.get("passed")]
        return {
            "ready": bool(raw.get("ready")),
            "passed": int(raw.get("passed") or 0),
            "total": int(raw.get("total") or 0),
            "missing": missing,
        }

    @staticmethod
    def release_metadata_summary() -> dict:
        return {
            "REAL_PRODUCTION_AUTHORIZED": bool(release_metadata.REAL_PRODUCTION_AUTHORIZED),
            "REAL_PAYMENTS_AUTHORIZED": bool(release_metadata.REAL_PAYMENTS_AUTHORIZED),
            "SYNTHETIC_DATA_ONLY": bool(release_metadata.SYNTHETIC_DATA_ONLY),
        }

    def evaluate(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        external_summary: Mapping[str, object] | None = None,
    ) -> dict:
        env: Mapping[str, str] = os.environ if environ is None else environ
        startup = production_startup_report(env)
        external_raw = dict(external_summary) if external_summary is not None else self.external_summary()
        external = {
            "ready": bool(external_raw.get("ready")),
            "passed": int(external_raw.get("passed") or 0),
            "total": int(external_raw.get("total") or 0),
            "missing": list(external_raw.get("missing") or []),
        }
        metadata = self.release_metadata_summary()
        commercial_policy = self.policy["commercial_launch"]

        env_approvals = [
            {"key": name, "passed": _flag(env.get(name))}
            for name in commercial_policy.get("required_true") or []
        ]
        payment_provider = _provider(env.get(commercial_policy["payment_provider_env"]))
        communications_provider = _provider(env.get(commercial_policy["communications_provider_env"]))
        payment_provider_real = payment_provider not in set(commercial_policy.get("disallowed_payment_providers") or [])
        communications_provider_real = communications_provider not in set(commercial_policy.get("disallowed_communications_providers") or [])
        metadata_checks = [
            {"key": key, "passed": metadata.get(key) is expected}
            for key, expected in (commercial_policy.get("release_metadata") or {}).items()
        ]

        controlled_validation_ready = bool(startup.get("applies") and startup.get("safe") and external.get("ready"))
        commercial_checks = [
            *env_approvals,
            {"key": "payment_provider_real", "passed": payment_provider_real},
            {"key": "communications_provider_real", "passed": communications_provider_real},
            *metadata_checks,
        ]
        commercial_blockers = [row["key"] for row in commercial_checks if not row["passed"]]
        commercial_launch_ready = bool(controlled_validation_ready and not commercial_blockers)
        launch_requested = _flag(env.get("LEGAL_PRODUCTION_LAUNCH_AUTHORIZED"))
        safe_launch_claim = bool(not launch_requested or commercial_launch_ready)

        if not startup.get("applies"):
            state = "NOT_PRODUCTION_PROFILE"
        elif not startup.get("safe"):
            state = "BLOCKED_CONFIGURATION"
        elif not external.get("ready"):
            state = "BLOCKED_EXTERNAL_EVIDENCE"
        elif not commercial_launch_ready:
            state = "READY_FOR_CONTROLLED_PRODUCTION_VALIDATION"
        else:
            state = "COMMERCIAL_LAUNCH_READY"
        if launch_requested and not safe_launch_claim:
            state = "BLOCKED_UNSAFE_LAUNCH_CLAIM"

        return {
            "schema": "legalaizit-v1-rc1-production-readiness-report-v1",
            "candidate": str(self.policy.get("candidate") or "V1-RC1"),
            "state": state,
            "startup": startup,
            "external_attestations": external,
            "release_metadata": metadata,
            "commercial": {
                "launch_requested": launch_requested,
                "controlled_validation_ready": controlled_validation_ready,
                "commercial_launch_ready": commercial_launch_ready,
                "safe_launch_claim": safe_launch_claim,
                "checks": commercial_checks,
                "blockers": commercial_blockers,
                "payment_provider_class": "real" if payment_provider_real else "sandbox_or_disabled",
                "communications_provider_class": "real" if communications_provider_real else "sandbox_or_disabled",
            },
            "notices": list(self.policy.get("principles") or []),
        }

    def assert_safe_launch_claim(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        external_summary: Mapping[str, object] | None = None,
    ) -> dict:
        report = self.evaluate(environ, external_summary=external_summary)
        if not (report.get("commercial") or {}).get("safe_launch_claim"):
            blockers = ", ".join((report.get("commercial") or {}).get("blockers") or [])
            raise V1RC1ReadinessError(f"Lanzamiento comercial V1 bloqueado: {blockers}")
        return report


__all__ = ["V1RC1ProductionReadinessGate", "V1RC1ReadinessError"]
