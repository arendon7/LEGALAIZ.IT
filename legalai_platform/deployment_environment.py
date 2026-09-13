from __future__ import annotations

import base64
import os
from hashlib import sha256
from typing import Mapping
from urllib.parse import urlparse


_TRUE = {"1", "true", "yes", "si", "sí", "on"}
_FALSE = {"0", "false", "no", "off"}
_PLACEHOLDER_MARKERS = ("change_me", "changeme", "set_in_", "set-real", "set_real", "replace_me", "example")


class ProductionConfigurationError(RuntimeError):
    """Señala una configuración production que no puede iniciar de forma segura."""


def _flag(value: str | None, default: bool = False) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return default


def _configured(value: str | None) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    folded = raw.casefold()
    return not any(marker in folded for marker in _PLACEHOLDER_MARKERS)


def _roles(value: str | None) -> set[str]:
    return {item.strip().lower() for item in str(value or "").split(",") if item.strip()}


def _public_https(value: str | None) -> bool:
    raw = str(value or "").strip()
    if not _configured(raw):
        return False
    parsed = urlparse(raw)
    host = (parsed.hostname or "").casefold()
    return parsed.scheme == "https" and bool(host) and host not in {"localhost", "127.0.0.1", "::1"}


def _trusted_proxy_configured(value: str | None) -> bool:
    items = {item.strip() for item in str(value or "").split(",") if item.strip()}
    if not items:
        return False
    return not bool(items & {"*", "0.0.0.0/0", "::/0"})


def prepare_deployment_environment() -> None:
    """Normaliza variables del proveedor y bloquea un profile production inseguro.

    Render publica RENDER_EXTERNAL_URL automáticamente. La usamos como origen
    público si no existe una configuración explícita. Para cifrado, Render genera
    un secreto opaco; se deriva determinísticamente una llave AES de 32 bytes sin
    registrar ni persistir el secreto fuente. El perfil local/demo queda intacto;
    sólo `LEGAL_PROFILE=production` activa la compuerta V1-RC1 de arranque.
    """
    external_url = str(os.environ.get("RENDER_EXTERNAL_URL", "")).strip()
    if external_url and not str(os.environ.get("LEGAL_PUBLIC_BASE_URL", "")).strip():
        os.environ["LEGAL_PUBLIC_BASE_URL"] = external_url.rstrip("/")

    seed = str(os.environ.get("LEGAL_MASTER_KEY_SEED", ""))
    if seed and not str(os.environ.get("LEGAL_MASTER_KEY", "")).strip():
        derived = sha256(seed.encode("utf-8")).digest()
        encoded = base64.urlsafe_b64encode(derived).decode("ascii").rstrip("=")
        os.environ["LEGAL_MASTER_KEY"] = encoded

    assert_production_startup_environment()


def production_startup_report(environ: Mapping[str, str] | None = None) -> dict:
    """Evalúa únicamente requisitos de arranque del perfil production.

    No consulta expedientes, no activa proveedores y no incluye valores de secretos
    en la salida. Las aprobaciones jurídicas/comerciales se evalúan en la compuerta
    V1-RC1 separada; este reporte se limita a impedir un servidor production con una
    configuración técnica evidentemente insegura.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    profile = str(env.get("LEGAL_PROFILE", "local") or "local").strip().lower()
    if profile != "production":
        return {
            "schema": "legalaizit-v1-rc1-production-startup-v1",
            "applies": False,
            "profile": profile,
            "safe": True,
            "checks": [],
            "blockers": [],
        }

    master_key_present = any(
        _configured(env.get(name))
        for name in ("LEGAL_MASTER_KEY", "LEGAL_MASTER_KEY_FILE", "LEGAL_MASTER_KEY_SEED")
    )
    mfa_roles = _roles(env.get("LEGAL_REQUIRE_MFA_ROLES"))
    database_url = str(env.get("DATABASE_URL", "") or "").strip()
    bootstrap_email = str(env.get("LEGAL_BOOTSTRAP_ADMIN_EMAIL", "") or "").strip().lower()
    bootstrap_password = str(env.get("LEGAL_BOOTSTRAP_ADMIN_PASSWORD", "") or "").strip()
    bootstrap_pair_ok = not bootstrap_email and not bootstrap_password
    if bootstrap_email or bootstrap_password:
        bootstrap_pair_ok = bool(
            bootstrap_email
            and bootstrap_password
            and "@demo.legalaiz.it" not in bootstrap_email
            and _configured(bootstrap_password)
        )

    checks = [
        ("app_env", str(env.get("LEGAL_APP_ENV", "")).strip().lower() == "production"),
        ("public_https", _public_https(env.get("LEGAL_PUBLIC_BASE_URL"))),
        ("secure_cookies", _flag(env.get("LEGAL_SECURE_COOKIES"))),
        ("origin_check", _flag(env.get("LEGAL_REQUIRE_ORIGIN_CHECK"))),
        ("trust_proxy", _flag(env.get("LEGAL_TRUST_PROXY"))),
        ("trusted_proxy_ips", _trusted_proxy_configured(env.get("LEGAL_TRUSTED_PROXY_IPS"))),
        ("demo_accounts_disabled", not _flag(env.get("LEGAL_ALLOW_DEMO_ACCOUNTS"))),
        ("public_demo_disabled", not _flag(env.get("LEGAL_PUBLIC_DEMO_MODE"))),
        ("database_postgresql", str(env.get("LEGAL_DATABASE_BACKEND", "")).strip().lower() == "postgresql"),
        ("database_url_managed", _configured(database_url) and database_url.lower().startswith(("postgresql://", "postgres://"))),
        ("postgres_external_certified", _flag(env.get("LEGAL_POSTGRES_EXTERNAL_CERTIFIED"))),
        ("object_encryption", _flag(env.get("LEGAL_OBJECT_ENCRYPTION"), True)),
        ("volume_encryption_confirmed", _flag(env.get("LEGAL_VOLUME_ENCRYPTION_CONFIRMED"))),
        ("malware_scanner_clamav", str(env.get("LEGAL_MALWARE_SCANNER", "")).strip().lower() == "clamav"),
        ("mfa_admin_specialist", {"admin", "specialist"}.issubset(mfa_roles)),
        ("managed_master_key", master_key_present),
        ("bootstrap_admin_safe", bootstrap_pair_ok),
    ]
    public_checks = [{"key": key, "passed": bool(passed)} for key, passed in checks]
    blockers = [row["key"] for row in public_checks if not row["passed"]]
    return {
        "schema": "legalaizit-v1-rc1-production-startup-v1",
        "applies": True,
        "profile": "production",
        "safe": not blockers,
        "checks": public_checks,
        "blockers": blockers,
        "notice": "La compuerta de arranque no autoriza lanzamiento comercial, pagos reales ni comunicaciones externas.",
    }


def assert_production_startup_environment(environ: Mapping[str, str] | None = None) -> dict:
    report = production_startup_report(environ)
    if report.get("applies") and not report.get("safe"):
        keys = ", ".join(report.get("blockers") or [])
        raise ProductionConfigurationError(f"Perfil production bloqueado por configuración insegura: {keys}")
    return report


__all__ = [
    "ProductionConfigurationError",
    "assert_production_startup_environment",
    "prepare_deployment_environment",
    "production_startup_report",
]
