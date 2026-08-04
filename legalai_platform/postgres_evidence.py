from __future__ import annotations

"""Contratos de evidencia para la certificación PostgreSQL de LegalAIZ.it.

El módulo deliberadamente no acepta una bandera manual como prueba suficiente.
La compuerta M31.5 exige tres evidencias independientes: certificación técnica,
migración conciliada y restauración verificada sobre un destino desechable.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit
import json
import os

from . import release_metadata as release


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_url_identity(url: str) -> dict[str, str]:
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    return {
        "scheme": parsed.scheme or "postgresql",
        "host": parsed.hostname or "",
        "port": str(parsed.port or 5432),
        "database": (parsed.path or "/").lstrip("/") or "postgres",
        "user": parsed.username or "",
        "sslmode": str((query.get("sslmode") or [""])[0]),
    }


def connection_identity(
    values: Mapping[str, str] | None = None,
    *,
    prefix: str = "",
) -> dict[str, str]:
    env = values or os.environ
    url_key = f"{prefix}DATABASE_URL" if prefix else "DATABASE_URL"
    url_file_key = f"{prefix}DATABASE_URL_FILE" if prefix else "DATABASE_URL_FILE"
    direct = str(env.get(url_key, "")).strip()
    url_file = str(env.get(url_file_key, "")).strip()
    if not direct and url_file:
        path = Path(url_file).expanduser()
        if path.is_file():
            direct = path.read_text(encoding="utf-8").strip()
    if direct:
        identity = _safe_url_identity(direct)
    else:
        key = lambda name: f"{prefix}{name}" if prefix else name
        identity = {
            "scheme": "postgresql",
            "host": str(env.get(key("PGHOST"), "")).strip(),
            "port": str(env.get(key("PGPORT"), "5432")).strip(),
            "database": str(env.get(key("PGDATABASE"), "legalaiz")).strip(),
            "user": str(env.get(key("PGUSER"), "legalaiz")).strip(),
            "sslmode": str(env.get(key("PGSSLMODE"), "")).strip(),
        }
    schema_key = f"{prefix}LEGAL_POSTGRES_SCHEMA" if prefix else "LEGAL_POSTGRES_SCHEMA"
    identity["schema"] = str(env.get(schema_key, "public")).strip() or "public"
    return identity


def connection_fingerprint(
    values: Mapping[str, str] | None = None,
    *,
    prefix: str = "",
) -> str:
    identity = connection_identity(values, prefix=prefix)
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_report(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"La evidencia no es un objeto JSON: {path}")
    return value


@dataclass(frozen=True)
class GateCheck:
    key: str
    passed: bool
    detail: Any


def _report_identity(report: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    if report is None:
        return None, None
    return report.get("milestone"), report.get("version")


def evaluate_postgres_gate(
    certification: Mapping[str, Any] | None,
    migration: Mapping[str, Any] | None,
    backup_restore: Mapping[str, Any] | None,
) -> dict[str, Any]:
    checks: list[GateCheck] = []

    def add(key: str, passed: bool, detail: Any) -> None:
        checks.append(GateCheck(key, bool(passed), detail))

    for name, report in (
        ("certification", certification),
        ("migration", migration),
        ("backup_restore", backup_restore),
    ):
        add(f"{name}_present", report is not None, {"present": report is not None})
        if report is not None:
            milestone, version = _report_identity(report)
            add(
                f"{name}_release_identity",
                milestone == release.MILESTONE and version == release.VERSION,
                {
                    "expected": {"milestone": release.MILESTONE, "version": release.VERSION},
                    "actual": {"milestone": milestone, "version": version},
                },
            )
            add(f"{name}_ok", report.get("ok") is True, {"ok": report.get("ok")})

    if certification is not None:
        required = {
            "connection",
            "schema_bootstrap",
            "transaction_rollback",
            "upsert_and_row_contract",
            "serial_sequence",
            "concurrency",
        }
        successful = {
            str(item.get("key"))
            for item in certification.get("checks", [])
            if isinstance(item, Mapping) and item.get("passed") is True
        }
        add(
            "certification_required_checks",
            required.issubset(successful),
            {"required": sorted(required), "successful": sorted(successful)},
        )
        add(
            "certification_not_self_authorizing",
            certification.get("production_authorized") is False,
            {"production_authorized": certification.get("production_authorized")},
        )

    if migration is not None:
        verification = migration.get("verification") or {}
        add(
            "migration_verified",
            migration.get("verified") is True
            and verification.get("missing_rows", 1) == 0
            and verification.get("mismatched_rows", 1) == 0,
            {
                "verified": migration.get("verified"),
                "missing_rows": verification.get("missing_rows"),
                "mismatched_rows": verification.get("mismatched_rows"),
            },
        )
        add(
            "migration_sequences_reconciled",
            migration.get("sequences_reconciled") is True,
            {"sequences_reconciled": migration.get("sequences_reconciled")},
        )

    if backup_restore is not None:
        add(
            "restore_target_is_distinct",
            bool(backup_restore.get("source_fingerprint"))
            and backup_restore.get("source_fingerprint")
            != backup_restore.get("restore_fingerprint"),
            {
                "source_fingerprint": backup_restore.get("source_fingerprint"),
                "restore_fingerprint": backup_restore.get("restore_fingerprint"),
            },
        )
        add(
            "restore_data_reconciled",
            backup_restore.get("restored") is True
            and backup_restore.get("mismatched_tables", 1) == 0
            and backup_restore.get("missing_tables", 1) == 0,
            {
                "restored": backup_restore.get("restored"),
                "mismatched_tables": backup_restore.get("mismatched_tables"),
                "missing_tables": backup_restore.get("missing_tables"),
            },
        )
        add(
            "restore_destructive_guard",
            backup_restore.get("destructive_guard_confirmed") is True,
            {
                "destructive_guard_confirmed": backup_restore.get(
                    "destructive_guard_confirmed"
                )
            },
        )

    target_fingerprints = {
        str(value)
        for value in (
            certification.get("target_fingerprint") if certification else None,
            migration.get("target_fingerprint") if migration else None,
            backup_restore.get("source_fingerprint") if backup_restore else None,
        )
        if value
    }
    add(
        "same_source_environment",
        len(target_fingerprints) == 1,
        {"fingerprints": sorted(target_fingerprints)},
    )

    passed = sum(1 for item in checks if item.passed)
    ok = bool(checks) and passed == len(checks)
    return {
        "schema": "legalaizit-postgres-release-gate-v1",
        "generated_at": utc_now(),
        "milestone": release.MILESTONE,
        "version": release.VERSION,
        "build_id": release.BUILD_ID,
        "checks": [asdict(item) for item in checks],
        "passed": passed,
        "total": len(checks),
        "ok": ok,
        "postgres_preproduction_certified": ok,
        "production_authorized": False,
        "public_production_ready": False,
        "notice": (
            "La compuerta certifica únicamente PostgreSQL de preproducción. "
            "Producción pública requiere además pentest, carga, observabilidad, "
            "protección de datos y aprobaciones externas."
        ),
    }
