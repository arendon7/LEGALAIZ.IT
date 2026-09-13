#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform import release_metadata
from legalai_platform.deployment_environment import production_startup_report
from legalai_platform.operational_security import ExternalAttestationRegistry
from legalai_platform.v1_rc1_production_readiness import V1RC1ProductionReadinessGate


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def secure_shape() -> dict[str, str]:
    return {
        "LEGAL_PROFILE": "production",
        "LEGAL_APP_ENV": "production",
        "LEGAL_PUBLIC_BASE_URL": "https://rc1.legalaiz.test",
        "LEGAL_SECURE_COOKIES": "true",
        "LEGAL_REQUIRE_ORIGIN_CHECK": "true",
        "LEGAL_TRUST_PROXY": "true",
        "LEGAL_TRUSTED_PROXY_IPS": "10.50.0.10",
        "LEGAL_ALLOW_DEMO_ACCOUNTS": "false",
        "LEGAL_PUBLIC_DEMO_MODE": "false",
        "LEGAL_DATABASE_BACKEND": "postgresql",
        "DATABASE_URL": "postgresql://runtime-user@db.internal/legalaiz",
        "LEGAL_POSTGRES_EXTERNAL_CERTIFIED": "true",
        "LEGAL_OBJECT_ENCRYPTION": "true",
        "LEGAL_VOLUME_ENCRYPTION_CONFIRMED": "true",
        "LEGAL_MALWARE_SCANNER": "clamav",
        "LEGAL_REQUIRE_MFA_ROLES": "admin,specialist",
        "LEGAL_MASTER_KEY_SEED": "ci-managed-secret-material",
        "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "false",
        "LEGAL_REAL_PAYMENTS_AUTHORIZED": "false",
        "LEGAL_PAYMENT_PROVIDER": "sandbox",
        "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "false",
        "LEGAL_COMMUNICATION_PROVIDER": "disabled",
        "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_PRIVACY_FINAL_APPROVED": "false",
    }


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def main() -> int:
    gate = V1RC1ProductionReadinessGate(ROOT)
    env = secure_shape()
    startup = production_startup_report(env)
    require(startup.get("safe") is True, f"La forma production segura no pasa startup: {startup.get('blockers')}")

    unsafe = dict(env)
    unsafe["LEGAL_ALLOW_DEMO_ACCOUNTS"] = "true"
    unsafe_report = production_startup_report(unsafe)
    require(unsafe_report.get("safe") is False, "RC1 dejó arrancar production con cuentas demo")
    require("demo_accounts_disabled" in unsafe_report.get("blockers", []), "RC1 no identifica cuentas demo como bloqueo")

    external_total = len(ExternalAttestationRegistry.REQUIRED)
    external = {"ready": True, "passed": external_total, "total": external_total, "missing": []}
    report = gate.evaluate(env, external_summary=external)
    require(report["commercial"]["controlled_validation_ready"] is True, "RC1 no distingue validación production controlada")
    require(report["commercial"]["commercial_launch_ready"] is False, "RC1 autorizó lanzamiento comercial con metadata RC0/M33")
    require(report["state"] == "READY_FOR_CONTROLLED_PRODUCTION_VALIDATION", "Estado RC1 inesperado con launch desactivado")

    forced = dict(env)
    forced.update({
        "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "true",
        "LEGAL_REAL_PAYMENTS_AUTHORIZED": "true",
        "LEGAL_PAYMENT_PROVIDER": "verified-payment-adapter",
        "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "true",
        "LEGAL_COMMUNICATION_PROVIDER": "verified-transactional-adapter",
        "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "true",
        "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "true",
        "LEGAL_PRIVACY_FINAL_APPROVED": "true",
    })
    forced_report = gate.evaluate(forced, external_summary=external)
    require(forced_report["commercial"]["safe_launch_claim"] is False, "Variables de entorno sobreescribieron una prohibición de release metadata")
    require(forced_report["state"] == "BLOCKED_UNSAFE_LAUNCH_CLAIM", "RC1 no bloqueó claim comercial prematuro")

    require(release_metadata.REAL_PRODUCTION_AUTHORIZED is False, "RC1 esperaba REAL_PRODUCTION_AUTHORIZED=false en la línea actual")
    require(release_metadata.REAL_PAYMENTS_AUTHORIZED is False, "RC1 esperaba REAL_PAYMENTS_AUTHORIZED=false en la línea actual")
    require(release_metadata.SYNTHETIC_DATA_ONLY is True, "RC1 esperaba SYNTHETIC_DATA_ONLY=true en la línea actual")

    template = parse_env(ROOT / ".env.production.example")
    template_report = production_startup_report(template)
    require(template_report.get("safe") is False, "La plantilla production quedó desplegable con placeholders")
    require(template.get("LEGAL_PRODUCTION_LAUNCH_AUTHORIZED") == "false", "La plantilla habilita launch por defecto")
    require(template.get("LEGAL_REAL_PAYMENTS_AUTHORIZED") == "false", "La plantilla habilita pagos reales por defecto")
    require(template.get("LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED") == "false", "La plantilla habilita comunicaciones externas por defecto")

    print(
        "V1-RC1 readiness gate PASS · "
        f"startup_checks={len(startup.get('checks') or [])} fail_closed=true external_contract={external_total} "
        "controlled_validation=allowed_when_evidence_green commercial_launch=blocked_by_release_metadata "
        "template=non_runnable providers=not_auto_enabled secrets=not_reported"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"V1-RC1 readiness gate FAIL: {exc}", file=sys.stderr)
        raise
