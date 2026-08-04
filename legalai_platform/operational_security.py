from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import socket
import struct

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class RateLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(window_seconds - (now - q[0])))
                return False, retry
            q.append(now)
            return True, 0


@dataclass(frozen=True)
class ScanResult:
    status: str
    engine: str
    detail: str


class MalwareScanner:
    def __init__(self, mode: str, profile: str):
        self.mode = (mode or "none").strip().lower()
        self.profile = profile

    def available(self) -> bool:
        if self.mode == "clamav":
            host = os.environ.get("LEGAL_CLAMAV_HOST", "").strip()
            if host:
                try:
                    with socket.create_connection((host, int(os.environ.get("LEGAL_CLAMAV_PORT", "3310"))), timeout=1.5):
                        return True
                except OSError:
                    return False
            return bool(shutil.which(os.environ.get("LEGAL_CLAMAV_COMMAND", "clamscan")))
        return self.mode == "none" and self.profile == "local"

    def scan(self, filename: str, data: bytes) -> ScanResult:
        if EICAR in data:
            raise ValueError("El archivo fue bloqueado por la prueba de detección antimalware.")
        if self.mode == "none":
            if self.profile != "local":
                raise RuntimeError("El escaneo antimalware es obligatorio fuera del perfil local.")
            return ScanResult("not_scanned_local", "none", "Escaneo externo no configurado en entorno local.")
        if self.mode != "clamav":
            raise RuntimeError("LEGAL_MALWARE_SCANNER debe ser none o clamav.")
        host = os.environ.get("LEGAL_CLAMAV_HOST", "").strip()
        if host:
            try:
                with socket.create_connection((host, int(os.environ.get("LEGAL_CLAMAV_PORT", "3310"))), timeout=10) as sock:
                    sock.sendall(b"zINSTREAM\0")
                    for pos in range(0, len(data), 64 * 1024):
                        chunk = data[pos:pos + 64 * 1024]
                        sock.sendall(struct.pack(">I", len(chunk)) + chunk)
                    sock.sendall(struct.pack(">I", 0))
                    response = sock.recv(4096).decode("utf-8", errors="replace").strip()
                if response.endswith("OK"):
                    return ScanResult("clean", "clamav-clamd", response)
                if "FOUND" in response:
                    raise ValueError("El archivo fue bloqueado por el escáner antimalware.")
                raise RuntimeError("ClamAV no devolvió un resultado concluyente.")
            except (OSError, TimeoutError) as exc:
                raise RuntimeError("No fue posible conectar con ClamAV.") from exc
        command = shutil.which(os.environ.get("LEGAL_CLAMAV_COMMAND", "clamscan"))
        if not command:
            raise RuntimeError("ClamAV está configurado pero clamscan o clamd no están disponibles.")
        suffix = Path(filename).suffix[:12]
        with tempfile.NamedTemporaryFile(prefix="legalaiz-scan-", suffix=suffix, delete=False) as fh:
            fh.write(data)
            temp_path = Path(fh.name)
        try:
            result = subprocess.run([command, "--no-summary", str(temp_path)], capture_output=True, text=True, timeout=45)
            output = (result.stdout + "\n" + result.stderr).strip()[-1000:]
            if result.returncode == 0:
                return ScanResult("clean", "clamav", output or "Sin hallazgos.")
            if result.returncode == 1:
                raise ValueError("El archivo fue bloqueado por el escáner antimalware.")
            raise RuntimeError("El escáner antimalware no pudo completar la revisión.")
        finally:
            temp_path.unlink(missing_ok=True)


def same_origin_allowed(origin: str | None, referer: str | None, public_base_url: str, *, required: bool) -> bool:
    if not required:
        return True
    expected = urlparse(public_base_url)
    candidate = origin or referer or ""
    if not candidate:
        return False
    parsed = urlparse(candidate)
    return parsed.scheme == expected.scheme and parsed.netloc == expected.netloc


def redact_event_detail(value):
    sensitive = {"password", "token", "secret", "authorization", "cookie", "csrf", "mfa_code", "recovery_codes"}
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.casefold() in sensitive else redact_event_detail(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_event_detail(x) for x in value]
    text = str(value)
    return text[:4000]


class ExternalAttestationRegistry:
    REQUIRED = ("postgres_runtime", "tls_certificate", "monitoring_alerts", "restore_drill_production", "load_test", "pentest", "privacy_approval", "incident_drill", "mac_windows_validation", "rollback_drill")

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "governance" / "m7" / "EXTERNAL_ATTESTATIONS.json"

    def load(self) -> dict:
        if not self.path.is_file():
            return {"schema": "legalaizit-m7-external-attestations-v1", "attestations": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"schema": "invalid", "attestations": []}

    def summary(self) -> dict:
        data = self.load()
        by_key = {x.get("key"): x for x in data.get("attestations", []) if isinstance(x, dict)}
        checks=[]
        for key in self.REQUIRED:
            item=by_key.get(key,{})
            evidence=str(item.get("evidence_path") or "")
            passed=bool(item.get("approved") and evidence and (self.root/evidence).is_file())
            checks.append({"key":key,"passed":passed,"approved_by":item.get("approved_by"),"approved_at":item.get("approved_at"),"evidence_path":evidence or None})
        return {"checks":checks,"passed":sum(x["passed"] for x in checks),"total":len(checks),"ready":all(x["passed"] for x in checks)}
