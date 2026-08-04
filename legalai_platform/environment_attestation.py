from __future__ import annotations

"""Atestación segura del entorno para certificación PostgreSQL.

No serializa variables de entorno completas, contraseñas, URLs con credenciales,
rutas de secretos ni contenido de archivos sensibles.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys

from . import release_metadata as release
from .postgres_evidence import connection_fingerprint, connection_identity


def _tool_version(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"available": False, "version": None}
    try:
        result = subprocess.run(
            [path, "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        text = (result.stdout or result.stderr).strip().splitlines()
        version = text[0][:300] if text else None
    except Exception as exc:  # pragma: no cover - depende del host
        version = f"{type(exc).__name__}: {exc}"[:300]
    return {"available": True, "version": version}


def _driver_status() -> dict[str, Any]:
    try:
        version = importlib.metadata.version("psycopg")
        return {"available": True, "package": "psycopg", "version": version}
    except importlib.metadata.PackageNotFoundError:
        return {"available": False, "package": "psycopg", "version": None}


def _safe_identity(values: Mapping[str, str], *, prefix: str = "") -> dict[str, Any]:
    identity = connection_identity(values, prefix=prefix)
    configured = all(identity.get(key) for key in ("host", "database", "user"))
    return {
        "configured": configured,
        "identity": identity if configured else None,
        "fingerprint": connection_fingerprint(values, prefix=prefix) if configured else None,
    }


def collect_environment_attestation(
    values: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = values or os.environ
    source = _safe_identity(env)
    restore = _safe_identity(env, prefix="RESTORE_")
    tools = {name: _tool_version(name) for name in ("pg_dump", "pg_restore", "psql")}
    driver = _driver_status()
    distinct = bool(
        source["fingerprint"]
        and restore["fingerprint"]
        and source["fingerprint"] != restore["fingerprint"]
    )
    return {
        "schema": "legalaizit-environment-attestation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "milestone": release.MILESTONE,
        "version": release.VERSION,
        "build_id": release.BUILD_ID,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "executable_name": Path(sys.executable).name,
        },
        "driver": driver,
        "tools": tools,
        "source": source,
        "restore": restore,
        "restore_target_is_distinct": distinct,
        "execution_prerequisites": {
            "driver": driver["available"],
            "pg_dump": tools["pg_dump"]["available"],
            "pg_restore": tools["pg_restore"]["available"],
            "source_configured": source["configured"],
            "restore_configured": restore["configured"],
            "restore_target_is_distinct": distinct,
        },
        "contains_secret_material": False,
        "production_authorized": False,
    }
