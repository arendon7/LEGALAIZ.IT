from __future__ import annotations

"""Integridad y verificación de paquetes de evidencia PostgreSQL M31.6."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from . import release_metadata as release
from .postgres_evidence import file_sha256

SENSITIVE_KEYS = {
    "password", "passwd", "secret", "token", "private_key", "master_key",
    "database_url", "authorization", "cookie", "api_key",
}


def _find_sensitive_keys(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            current = f"{path}.{key}"
            if normalized in SENSITIVE_KEYS or normalized.endswith("_password"):
                findings.append(current)
            findings.extend(_find_sensitive_keys(item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_find_sensitive_keys(item, f"{path}[{index}]"))
    return findings


def build_evidence_manifest(directory: Path, names: Iterable[str]) -> dict[str, Any]:
    directory = directory.resolve()
    artifacts: list[dict[str, Any]] = []
    for name in names:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"La evidencia no es un objeto JSON: {name}")
        sensitive = _find_sensitive_keys(payload)
        if sensitive:
            raise ValueError(f"La evidencia {name} contiene claves sensibles: {sensitive}")
        artifacts.append({
            "name": name,
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
            "schema": payload.get("schema"),
            "milestone": payload.get("milestone"),
            "version": payload.get("version"),
            "ok": payload.get("ok"),
        })
    return {
        "schema": "legalaizit-postgres-evidence-bundle-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "milestone": release.MILESTONE,
        "version": release.VERSION,
        "build_id": release.BUILD_ID,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "contains_secret_material": False,
        "production_authorized": False,
    }


def verify_evidence_manifest(directory: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    directory = directory.resolve()
    failures: list[dict[str, Any]] = []
    if manifest.get("milestone") != release.MILESTONE or manifest.get("version") != release.VERSION:
        failures.append({"key": "bundle_release_identity", "actual": {
            "milestone": manifest.get("milestone"), "version": manifest.get("version")
        }})
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        failures.append({"key": "artifacts", "error": "missing_or_empty"})
        artifacts = []
    for item in artifacts:
        if not isinstance(item, Mapping):
            failures.append({"key": "artifact", "error": "invalid_entry"})
            continue
        name = str(item.get("name", ""))
        if not name or Path(name).name != name:
            failures.append({"key": "artifact_name", "name": name})
            continue
        path = directory / name
        if not path.is_file():
            failures.append({"key": "artifact_missing", "name": name})
            continue
        actual_hash = file_sha256(path)
        if actual_hash != item.get("sha256"):
            failures.append({"key": "artifact_hash", "name": name})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append({"key": "artifact_json", "name": name, "error": str(exc)})
            continue
        sensitive = _find_sensitive_keys(payload)
        if sensitive:
            failures.append({"key": "artifact_sensitive_keys", "name": name, "paths": sensitive})
        if payload.get("milestone") != release.MILESTONE or payload.get("version") != release.VERSION:
            failures.append({"key": "artifact_release_identity", "name": name})
    ok = not failures
    return {
        "schema": "legalaizit-postgres-evidence-verification-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "milestone": release.MILESTONE,
        "version": release.VERSION,
        "checked_artifacts": len(artifacts),
        "failures": failures,
        "ok": ok,
        "production_authorized": False,
    }
