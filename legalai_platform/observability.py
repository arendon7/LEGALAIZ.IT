from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import threading
import uuid

from legalai_platform.operational_security import redact_event_detail


class StructuredLogger:
    def __init__(self, root: Path):
        runtime_raw = os.environ.get("LEGAL_RUNTIME_DIR", "").strip()
        runtime = Path(runtime_raw).expanduser() if runtime_raw else Path(root) / "runtime"
        if not runtime.is_absolute():
            runtime = Path(root) / runtime
        self.base = runtime.resolve() / "logs"
        self.path = self.base / "application.jsonl"
        self.base.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max(256 * 1024, int(os.environ.get("LEGAL_LOG_MAX_BYTES", str(5 * 1024 * 1024))))
        self.retention = max(1, min(int(os.environ.get("LEGAL_LOG_RETENTION", "5")), 20))
        self._lock = threading.Lock()

    @staticmethod
    def request_id(value: str | None = None) -> str:
        clean = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")[:80]
        return clean or "REQ-" + uuid.uuid4().hex[:20].upper()

    def _rotate(self) -> None:
        if not self.path.is_file() or self.path.stat().st_size < self.max_bytes:
            return
        oldest = self.path.with_suffix(f".jsonl.{self.retention}")
        oldest.unlink(missing_ok=True)
        for index in range(self.retention - 1, 0, -1):
            source = self.path.with_suffix(f".jsonl.{index}")
            if source.is_file():
                source.replace(self.path.with_suffix(f".jsonl.{index + 1}"))
        self.path.replace(self.path.with_suffix(".jsonl.1"))

    def write(self, event: str, **fields):
        safe_fields = redact_event_detail(fields)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": str(event)[:120],
            **safe_fields,
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
        with self._lock:
            self._rotate()
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def tail(self, limit=100):
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, min(int(limit), 500)):]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out

    def probe(self) -> dict:
        writable = False
        error = None
        probe = self.base / ".write-probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            writable = probe.read_text(encoding="utf-8") == "ok"
        except OSError as exc:
            error = str(exc)
        finally:
            probe.unlink(missing_ok=True)
        return {
            "writable": writable,
            "path": str(self.path),
            "exists": self.path.is_file(),
            "size_bytes": self.path.stat().st_size if self.path.is_file() else 0,
            "max_bytes": self.max_bytes,
            "retention": self.retention,
            "error": error,
        }
