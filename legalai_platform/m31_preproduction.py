from __future__ import annotations
from legalai_platform.release_metadata import MILESTONE, VERSION
from legalai_platform.database import runtime_status

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import sqlite3
import uuid


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


class M31PreproductionCenter:
    """Consolida la preparación técnica sin convertirla en autorización productiva."""

    def __init__(self, root: Path, settings, infrastructure, observability, external_attestations, audit_callback):
        self.root = Path(root)
        self.settings = settings
        self.infrastructure = infrastructure
        self.observability = observability
        self.external_attestations = external_attestations
        self.audit = audit_callback
        policy_path = self.root / "config" / "m31_1_preproduction_policy.json"
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        release_policy_path = self.root / "config" / "m31_4_release_policy.json"
        self.release_policy = json.loads(release_policy_path.read_text(encoding="utf-8")) if release_policy_path.is_file() else {}

    def ensure_schema(self, con: sqlite3.Connection) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m31_preproduction_snapshots(
              id TEXT PRIMARY KEY,
              profile TEXT NOT NULL,
              status TEXT NOT NULL,
              passed INTEGER NOT NULL,
              total INTEGER NOT NULL,
              blocking_json TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              snapshot_hash TEXT NOT NULL UNIQUE,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS m31_backup_drills(
              id TEXT PRIMARY KEY,
              backup_id TEXT NOT NULL,
              status TEXT NOT NULL,
              evidence_json TEXT NOT NULL,
              evidence_hash TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              completed_at TEXT,
              FOREIGN KEY(backup_id) REFERENCES infrastructure_backups(id)
            );
            CREATE TABLE IF NOT EXISTS m31_preproduction_decisions(
              id TEXT PRIMARY KEY,
              snapshot_id TEXT NOT NULL,
              decision TEXT NOT NULL,
              reason TEXT NOT NULL,
              production_authorized INTEGER NOT NULL DEFAULT 0,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(snapshot_id) REFERENCES m31_preproduction_snapshots(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m31_snapshot_created ON m31_preproduction_snapshots(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_m31_drill_created ON m31_backup_drills(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_m31_decision_created ON m31_preproduction_decisions(created_at DESC);
            """
        )

    @staticmethod
    def _actor(user: dict) -> str:
        return str(user.get("id") or user.get("email") or "unknown")

    @staticmethod
    def _admin(user: dict) -> None:
        if user.get("role") != "admin":
            raise PermissionError("El Centro de Preproducción exige rol administrador.")

    def _deployment_artifacts(self) -> dict:
        rows = []
        required = list(dict.fromkeys(self.policy.get("required_artifacts", []) + self.release_policy.get("required_artifacts", [])))
        for relative in required:
            path = self.root / relative
            rows.append({"path": relative, "present": path.is_file(), "size_bytes": path.stat().st_size if path.is_file() else 0})
        return {"rows": rows, "passed": all(row["present"] and row["size_bytes"] > 0 for row in rows)}

    def _runtime_probe(self) -> dict:
        runtime = Path(os.environ.get("LEGAL_RUNTIME_DIR", "").strip() or self.root / "runtime")
        if not runtime.is_absolute():
            runtime = self.root / runtime
        runtime.mkdir(parents=True, exist_ok=True)
        probe = runtime / ".m31-write-probe"
        writable = False
        error = None
        try:
            probe.write_text("m31", encoding="utf-8")
            writable = probe.read_text(encoding="utf-8") == "m31"
        except OSError as exc:
            error = str(exc)
        finally:
            probe.unlink(missing_ok=True)
        usage = shutil.disk_usage(runtime)
        return {
            "path": str(runtime.resolve()),
            "writable": writable,
            "free_bytes": usage.free,
            "total_bytes": usage.total,
            "free_ratio": round(usage.free / usage.total, 4) if usage.total else 0,
            "error": error,
        }

    def checks(self, con: sqlite3.Connection) -> dict:
        doctor = self.infrastructure.doctor(con)
        doctor_map = {row["key"]: row for row in doctor.get("checks", [])}
        external = self.external_attestations.summary()
        artifacts = self._deployment_artifacts()
        runtime = self._runtime_probe()
        log_probe = self.observability.probe()
        active_demo = con.execute("SELECT COUNT(*) FROM users WHERE active=1 AND lower(email) LIKE '%@demo.legalaiz.it'").fetchone()[0]
        backups = self.infrastructure.backups.list(con)
        verified_backups = [row for row in backups if row.get("status") == "Verificado"]
        mfa = self.infrastructure.mfa_coverage(con)

        rows = [
            {"key": "profile", "group": "environment", "label": "Perfil de preproducción", "passed": self.settings.profile == self.policy.get("target_profile"), "detail": self.settings.profile},
            {"key": "public_https", "group": "environment", "label": "URL pública HTTPS", "passed": self.settings.public_base_url.startswith("https://"), "detail": self.settings.public_base_url},
            {"key": "secure_cookies", "group": "security", "label": "Cookies Secure", "passed": bool(self.settings.secure_cookies), "detail": self.settings.secure_cookies},
            {"key": "origin_check", "group": "security", "label": "Control de origen", "passed": bool(self.settings.require_origin_check), "detail": self.settings.require_origin_check},
            {"key": "trusted_proxy", "group": "security", "label": "Proxy confiable configurado", "passed": bool(self.settings.trust_proxy and self.settings.trusted_proxy_ips), "detail": list(self.settings.trusted_proxy_ips)},
            {"key": "external_master_key", "group": "secrets", "label": "Llave maestra externa", "passed": self.infrastructure.secrets.origin in {"environment", "secret-file"}, "detail": self.infrastructure.secrets.origin},
            {"key": "malware_scanner", "group": "security", "label": "Antimalware disponible", "passed": bool(doctor_map.get("malware_scanner", {}).get("passed")), "detail": doctor_map.get("malware_scanner", {}).get("detail")},
            {"key": "mfa_privileged", "group": "identity", "label": "MFA en cuentas privilegiadas", "passed": mfa["required_users"] == mfa["enabled_required_users"] and mfa["required_users"] > 0, "detail": {"enabled": mfa["enabled_required_users"], "required": mfa["required_users"]}},
            {"key": "no_demo_accounts", "group": "identity", "label": "Cuentas demo desactivadas", "passed": active_demo == 0, "detail": active_demo},
            {"key": "verified_backup", "group": "continuity", "label": "Backup cifrado verificado", "passed": bool(verified_backups), "detail": {"total": len(backups), "verified": len(verified_backups)}},
            {"key": "observability", "group": "operations", "label": "Observabilidad estructurada operativa", "passed": bool(log_probe.get("writable")), "detail": log_probe},
            {"key": "deployment_artifacts", "group": "deployment", "label": "Artefactos de despliegue completos", "passed": artifacts["passed"], "detail": artifacts["rows"]},
            {"key": "runtime_writable", "group": "operations", "label": "Volumen runtime escribible", "passed": bool(runtime["writable"] and runtime["free_ratio"] >= 0.05), "detail": runtime},
            {"key": "database_adapter", "group": "data", "label": "Adaptador de datos disponible", "passed": self.settings.database_backend == "sqlite" or (self.settings.database_backend == "postgresql" and runtime_status().driver_available), "detail": {**runtime_status().public(), "external_certified": str(os.environ.get("LEGAL_POSTGRES_EXTERNAL_CERTIFIED", "false")).lower() in {"1","true","yes","si","sí"}, "notice": "M31.5 implementa PostgreSQL; la autorización externa y la evidencia de concurrencia/restauración siguen separadas."}},
            {"key": "external_attestations", "group": "external", "label": "Evidencias externas productivas", "passed": bool(external.get("ready")), "detail": {"passed": external.get("passed", 0), "total": external.get("total", 0)}},
            {"key": "production_gate", "group": "governance", "label": "Producción permanece bloqueada", "passed": True, "detail": {"production_authorized": False}},
        ]
        hard = set(self.policy.get("hard_preproduction_checks", []))
        hard_blocking = [row["key"] for row in rows if row["key"] in hard and not row["passed"]]
        production_blocking = [row["key"] for row in rows if not row["passed"]]
        passed = sum(bool(row["passed"]) for row in rows)
        return {
            "phase": MILESTONE,
            "version": VERSION,
            "checks": rows,
            "passed": passed,
            "total": len(rows),
            "preproduction_ready": not hard_blocking,
            "hard_blocking": hard_blocking,
            "production_ready": False,
            "production_blocking": production_blocking,
            "external_attestations": external,
            "notices": [
                f"{MILESTONE} habilita únicamente un entorno administrado de preproducción.",
                "No autoriza producción pública, pagos reales ni entrega documental automática.",
                "La certificación PostgreSQL, pentest, carga, restauración productiva y rollback siguen siendo evidencias externas obligatorias.",
            ],
        }

    def create_snapshot(self, con: sqlite3.Connection, user: dict) -> dict:
        self._admin(user)
        report = self.checks(con)
        snapshot_id = "M31-SNAP-" + uuid.uuid4().hex[:14].upper()
        created = utc_iso()
        detail = {**report, "captured_at": created, "captured_by": self._actor(user)}
        digest = canonical_hash(detail)
        status = "ready_for_managed_preproduction" if report["preproduction_ready"] else "blocked"
        con.execute(
            "INSERT INTO m31_preproduction_snapshots(id,profile,status,passed,total,blocking_json,detail_json,snapshot_hash,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (snapshot_id, self.settings.profile, status, report["passed"], report["total"], json.dumps(report["hard_blocking"], ensure_ascii=False), json.dumps(detail, ensure_ascii=False), digest, self._actor(user), created),
        )
        self.audit(con, self._actor(user), "m31_preproduction_snapshot", snapshot_id, "create", {"status": status, "snapshot_hash": digest})
        con.commit()
        return {"id": snapshot_id, "status": status, "snapshot_hash": digest, **report, "created_at": created}

    def run_backup_drill(self, con: sqlite3.Connection, user: dict, source_db: Path) -> dict:
        self._admin(user)
        created = utc_iso()
        backup = self.infrastructure.backups.create(con, source_db, self._actor(user))
        verification = self.infrastructure.backups.verify(con, backup["id"])
        evidence = {
            "backup": {key: backup.get(key) for key in ("id", "filename", "sha256", "size_bytes", "status")},
            "verification": verification,
            "source_database": "runtime/legalaizit.db",
            "restore_execution": "verification_in_temporary_directory",
            "production_restore_completed": False,
        }
        drill_id = "M31-DRILL-" + uuid.uuid4().hex[:14].upper()
        digest = canonical_hash(evidence)
        con.execute(
            "INSERT INTO m31_backup_drills(id,backup_id,status,evidence_json,evidence_hash,created_by,created_at,completed_at) VALUES(?,?,?,?,?,?,?,?)",
            (drill_id, backup["id"], "verified", json.dumps(evidence, ensure_ascii=False), digest, self._actor(user), created, utc_iso()),
        )
        self.audit(con, self._actor(user), "m31_backup_drill", drill_id, "verify", {"backup_id": backup["id"], "evidence_hash": digest})
        con.commit()
        return {"id": drill_id, "status": "verified", "evidence_hash": digest, **evidence}

    def record_decision(self, con: sqlite3.Connection, data: dict, user: dict) -> dict:
        self._admin(user)
        snapshot_id = str(data.get("snapshot_id") or "").strip()
        decision = str(data.get("decision") or "").strip()
        reason = str(data.get("reason") or "").strip()
        confirmation = str(data.get("confirmation") or "").strip()
        if decision not in self.policy.get("decision_values", []):
            raise ValueError("La decisión de preproducción no es válida.")
        if confirmation != self.policy.get("confirmation_phrase"):
            raise ValueError("La frase de confirmación no coincide.")
        if len(reason) < 20 or len(reason) > 1000:
            raise ValueError("La justificación debe tener entre 20 y 1000 caracteres.")
        snapshot = con.execute("SELECT * FROM m31_preproduction_snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if not snapshot:
            raise LookupError("Snapshot de preproducción no encontrado.")
        if decision == "ready_for_managed_preproduction" and snapshot["status"] != "ready_for_managed_preproduction":
            raise ValueError("No puede declararse listo un snapshot con compuertas duras pendientes.")
        decision_id = "M31-DEC-" + uuid.uuid4().hex[:14].upper()
        created = utc_iso()
        con.execute(
            "INSERT INTO m31_preproduction_decisions(id,snapshot_id,decision,reason,production_authorized,created_by,created_at) VALUES(?,?,?,?,0,?,?)",
            (decision_id, snapshot_id, decision, reason, self._actor(user), created),
        )
        self.audit(con, self._actor(user), "m31_preproduction_decision", decision_id, "record", {"snapshot_id": snapshot_id, "decision": decision, "production_authorized": False})
        con.commit()
        return {"id": decision_id, "snapshot_id": snapshot_id, "decision": decision, "reason": reason, "production_authorized": False, "created_at": created}

    def summary(self, con: sqlite3.Connection, user: dict) -> dict:
        self._admin(user)
        report = self.checks(con)
        snapshots = [dict(row) for row in con.execute("SELECT id,profile,status,passed,total,snapshot_hash,created_by,created_at FROM m31_preproduction_snapshots ORDER BY created_at DESC LIMIT 20").fetchall()]
        drills = [dict(row) for row in con.execute("SELECT id,backup_id,status,evidence_hash,created_by,created_at,completed_at FROM m31_backup_drills ORDER BY created_at DESC LIMIT 20").fetchall()]
        decisions = [dict(row) for row in con.execute("SELECT id,snapshot_id,decision,reason,production_authorized,created_by,created_at FROM m31_preproduction_decisions ORDER BY created_at DESC LIMIT 20").fetchall()]
        return {"policy": self.policy, "current": report, "snapshots": snapshots, "backup_drills": drills, "decisions": decisions, "production_authorized": False}

    def export_latest(self, con: sqlite3.Connection, user: dict) -> bytes:
        payload = self.summary(con, user)
        payload["exported_at"] = utc_iso()
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
