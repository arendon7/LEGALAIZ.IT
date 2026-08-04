from __future__ import annotations

"""Registro verificable del QA visual integral de LegalAIZ.it v2.18.

La evidencia se genera con navegador Chromium real en dos tamaños de pantalla y
cuatro perfiles. Este módulo no declara certificación de accesibilidad ni uso
profesional; expone hashes, hallazgos y artefactos para auditoría interna.
"""

from hashlib import sha256
from pathlib import Path
from typing import Any
import json

VERSION = "2.18"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class VisualQaV218:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.qa_dir = self.root / "app" / "assets" / "compatibility" / "visual-qa-v218"
        self.screens_dir = self.qa_dir / "screenshots"
        self.manifest_path = self.qa_dir / "visual_qa_manifest.json"
        self.package_path = self.qa_dir / "LegalAIZit_Evidencia_QA_Visual_v2.18.zip"
        self.qa_dir.mkdir(parents=True, exist_ok=True)
        self.screens_dir.mkdir(parents=True, exist_ok=True)

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS visual_qa_baselines_v218(
              id TEXT PRIMARY KEY,
              version TEXT NOT NULL,
              manifest_sha256 TEXT NOT NULL,
              evidence_sha256 TEXT,
              status TEXT NOT NULL,
              captured_at TEXT,
              screen_count INTEGER NOT NULL DEFAULT 0,
              route_count INTEGER NOT NULL DEFAULT 0,
              open_high_findings INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )

    def init_baseline(self, con, now: str) -> None:
        data = self._load_manifest(required=False)
        manifest_hash = _sha(self.manifest_path) if self.manifest_path.is_file() else "pending"
        evidence_hash = _sha(self.package_path) if self.package_path.is_file() else None
        metrics = data.get("metrics", {}) if data else {}
        status = data.get("status", "Pendiente de captura") if data else "Pendiente de captura"
        con.execute(
            """INSERT INTO visual_qa_baselines_v218(
                 id,version,manifest_sha256,evidence_sha256,status,captured_at,
                 screen_count,route_count,open_high_findings,created_at,updated_at
               ) VALUES('VQA-218',?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 version=excluded.version,manifest_sha256=excluded.manifest_sha256,
                 evidence_sha256=excluded.evidence_sha256,status=excluded.status,
                 captured_at=excluded.captured_at,screen_count=excluded.screen_count,
                 route_count=excluded.route_count,open_high_findings=excluded.open_high_findings,
                 updated_at=excluded.updated_at""",
            (
                VERSION,
                manifest_hash,
                evidence_hash,
                status,
                data.get("captured_at") if data else None,
                int(metrics.get("screens", 0)),
                int(metrics.get("routes", 0)),
                int(metrics.get("open_high_findings", 0)),
                now,
                now,
            ),
        )

    def _load_manifest(self, required: bool = True) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            if required:
                raise FileNotFoundError("La evidencia visual v2.18 todavía no está disponible.")
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def summary(self, con=None) -> dict[str, Any]:
        data = self._load_manifest(required=False)
        if not data:
            return {
                "version": VERSION,
                "status": "Pendiente de captura",
                "metrics": {"screens": 0, "routes": 0, "viewports": 0, "roles": 0, "passed": 0, "failed": 0, "open_high_findings": 0},
                "screens": [],
                "findings": [],
                "evidence_available": False,
                "professional_use_authorized": False,
                "accessibility_certified": False,
            }
        integrity_errors = []
        for screen in data.get("screens", []):
            filename = Path(str(screen.get("filename", ""))).name
            path = self.screens_dir / filename
            if not path.is_file():
                integrity_errors.append({"filename": filename, "error": "missing"})
            elif screen.get("sha256") and _sha(path) != screen["sha256"]:
                integrity_errors.append({"filename": filename, "error": "sha256_mismatch"})
        package_hash = _sha(self.package_path) if self.package_path.is_file() else None
        result = dict(data)
        result.update(
            {
                "version": VERSION,
                "integrity_valid": not integrity_errors,
                "integrity_errors": integrity_errors,
                "manifest_sha256": _sha(self.manifest_path),
                "evidence_available": self.package_path.is_file(),
                "evidence_sha256": package_hash,
                "professional_use_authorized": False,
                "accessibility_certified": False,
            }
        )
        if con is not None:
            row = con.execute("SELECT * FROM visual_qa_baselines_v218 WHERE id='VQA-218'").fetchone()
            result["baseline"] = dict(row) if row else None
        return result

    def screenshot_path(self, filename: str) -> Path | None:
        clean = Path(filename or "").name
        if clean != filename or not clean.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return None
        target = (self.screens_dir / clean).resolve()
        try:
            if not target.is_relative_to(self.screens_dir.resolve()):
                return None
        except AttributeError:
            if not str(target).startswith(str(self.screens_dir.resolve())):
                return None
        return target if target.is_file() else None

    def evidence_path(self) -> Path | None:
        return self.package_path if self.package_path.is_file() else None
