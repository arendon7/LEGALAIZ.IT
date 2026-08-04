from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED
import base64
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import struct
import uuid

from legalai_platform.operational_security import MalwareScanner
from legalai_platform.database import runtime_status

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover - deployment doctor reports this explicitly
    AESGCM = None

ENC_MAGIC = b"LZAIZENC2\x00"
BACKUP_MAGIC = b"LZAIZBKP2\x00"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _read_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


@dataclass(frozen=True)
class AppSettings:
    profile: str
    app_env: str
    public_base_url: str
    secure_cookies: bool
    trust_proxy: bool
    object_storage_backend: str
    object_storage_encryption: bool
    database_backend: str
    database_url: str
    require_mfa_roles: tuple[str, ...]
    backup_retention: int
    max_upload_mb: int
    volume_encryption_confirmed: bool
    malware_scanner: str
    trusted_proxy_ips: tuple[str, ...]
    session_idle_minutes_client: int
    session_idle_minutes_privileged: int
    require_origin_check: bool
    master_key_file: str
    production_ready_claim: bool = False

    def public(self) -> dict:
        value = asdict(self)
        value["require_mfa_roles"] = list(self.require_mfa_roles)
        value.pop("database_url", None)
        value.pop("master_key_file", None)
        value["trusted_proxy_ips"] = list(self.trusted_proxy_ips)
        return value


def _runtime_root(project_root: Path) -> Path:
    raw = os.environ.get("LEGAL_RUNTIME_DIR", "").strip()
    path = Path(raw).expanduser() if raw else Path(project_root) / "runtime"
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()


def load_settings(root: Path) -> AppSettings:
    file_env = _read_env_file(root / ".env")
    env = {**file_env, **os.environ}
    profile = env.get("LEGAL_PROFILE", "local").strip().lower()
    if profile not in {"local", "pilot", "production"}:
        raise ValueError("LEGAL_PROFILE debe ser local, pilot o production.")
    app_env = env.get("LEGAL_APP_ENV", profile)
    secure_default = profile in {"pilot", "production"}
    mfa_default = "admin,specialist" if profile in {"pilot", "production"} else ""
    roles = tuple(x.strip() for x in env.get("LEGAL_REQUIRE_MFA_ROLES", mfa_default).split(",") if x.strip())
    settings = AppSettings(
        profile=profile,
        app_env=app_env,
        public_base_url=env.get("LEGAL_PUBLIC_BASE_URL", "http://127.0.0.1:8765"),
        secure_cookies=_parse_bool(env.get("LEGAL_SECURE_COOKIES"), secure_default),
        trust_proxy=_parse_bool(env.get("LEGAL_TRUST_PROXY"), False),
        object_storage_backend=env.get("LEGAL_OBJECT_STORAGE", "local-encrypted"),
        object_storage_encryption=_parse_bool(env.get("LEGAL_OBJECT_ENCRYPTION"), True),
        database_backend=env.get("LEGAL_DATABASE_BACKEND", "sqlite"),
        database_url=env.get("DATABASE_URL", ""),
        require_mfa_roles=roles,
        backup_retention=max(1, int(env.get("LEGAL_BACKUP_RETENTION", "10"))),
        max_upload_mb=max(1, int(env.get("LEGAL_MAX_UPLOAD_MB", "10"))),
        volume_encryption_confirmed=_parse_bool(env.get("LEGAL_VOLUME_ENCRYPTION_CONFIRMED"), profile == "local"),
        malware_scanner=env.get("LEGAL_MALWARE_SCANNER", "none").strip().lower(),
        trusted_proxy_ips=tuple(x.strip() for x in env.get("LEGAL_TRUSTED_PROXY_IPS", "127.0.0.1,::1").split(",") if x.strip()),
        session_idle_minutes_client=max(15, int(env.get("LEGAL_SESSION_IDLE_MINUTES_CLIENT", "120"))),
        session_idle_minutes_privileged=max(5, int(env.get("LEGAL_SESSION_IDLE_MINUTES_PRIVILEGED", "30"))),
        require_origin_check=_parse_bool(env.get("LEGAL_REQUIRE_ORIGIN_CHECK"), profile in {"pilot", "production"}),
        master_key_file=env.get("LEGAL_MASTER_KEY_FILE", "").strip(),
        production_ready_claim=False,
    )
    if settings.profile == "production" and settings.database_backend == "sqlite":
        # Runtime is intentionally conservative: production doctor will remain blocked.
        pass
    return settings


class SecretManager:
    def __init__(self, root: Path, settings: AppSettings):
        self.root = Path(root)
        self.settings = settings
        self.secret_dir = _runtime_root(self.root) / "secrets"
        self.secret_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.secret_dir / "master.key"
        self.key, self.origin = self._load_key()

    @staticmethod
    def _decode_key(value: str) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        except Exception as exc:
            raise ValueError("LEGAL_MASTER_KEY no es Base64 URL-safe válida.") from exc
        if len(raw) != 32:
            raise ValueError("LEGAL_MASTER_KEY debe representar exactamente 32 bytes.")
        return raw

    def _load_key(self) -> tuple[bytes, str]:
        env_value = os.environ.get("LEGAL_MASTER_KEY")
        if env_value:
            return self._decode_key(env_value), "environment"
        secret_file = os.environ.get("LEGAL_MASTER_KEY_FILE") or self.settings.master_key_file
        if secret_file:
            secret_path = Path(secret_file)
            if not secret_path.is_file():
                raise RuntimeError("LEGAL_MASTER_KEY_FILE no existe o no es legible.")
            return self._decode_key(secret_path.read_text(encoding="utf-8").strip()), "secret-file"
        if self.key_path.is_file():
            return self._decode_key(self.key_path.read_text(encoding="utf-8").strip()), "runtime-file"
        if self.settings.profile in {"pilot", "production"}:
            raise RuntimeError("Pilot y production requieren LEGAL_MASTER_KEY o LEGAL_MASTER_KEY_FILE desde un gestor de secretos.")
        raw = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        self.key_path.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass
        return raw, "generated-local"

    @property
    def fingerprint(self) -> str:
        return sha256(self.key).hexdigest()[:16]


class CryptoBox:
    def __init__(self, key: bytes):
        if AESGCM is None:
            raise RuntimeError("Se requiere el paquete cryptography para cifrado AES-256-GCM.")
        if len(key) != 32:
            raise ValueError("La llave maestra debe tener 32 bytes.")
        self.aes = AESGCM(key)

    def encrypt(self, data: bytes, aad: bytes, magic: bytes = ENC_MAGIC) -> bytes:
        nonce = secrets.token_bytes(12)
        ciphertext = self.aes.encrypt(nonce, data, aad)
        return magic + struct.pack(">H", len(aad)) + aad + nonce + ciphertext

    def decrypt(self, payload: bytes, expected_magic: bytes = ENC_MAGIC) -> tuple[bytes, bytes]:
        if not payload.startswith(expected_magic):
            raise ValueError("Formato cifrado no reconocido.")
        pos = len(expected_magic)
        aad_len = struct.unpack(">H", payload[pos:pos + 2])[0]
        pos += 2
        aad = payload[pos:pos + aad_len]
        pos += aad_len
        nonce = payload[pos:pos + 12]
        ciphertext = payload[pos + 12:]
        return self.aes.decrypt(nonce, ciphertext, aad), aad


class EncryptedObjectStore:
    """Almacenamiento local cifrado. El adaptador S3 se deja configurado, no fingido."""

    def __init__(self, root: Path, secrets_manager: SecretManager, settings: AppSettings):
        self.root = Path(root)
        self.settings = settings
        self.base = _runtime_root(self.root) / "object_store"
        self.base.mkdir(parents=True, exist_ok=True)
        self.crypto = CryptoBox(secrets_manager.key)

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS infrastructure_objects(
              id TEXT PRIMARY KEY,
              namespace TEXT NOT NULL,
              original_name TEXT NOT NULL,
              stored_path TEXT NOT NULL,
              content_type TEXT,
              plaintext_sha256 TEXT NOT NULL,
              ciphertext_sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              encrypted INTEGER NOT NULL DEFAULT 1,
              owner_id TEXT,
              created_at TEXT NOT NULL,
              last_verified_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_infra_objects_namespace ON infrastructure_objects(namespace,created_at DESC);
            """
        )

    @staticmethod
    def is_reference(value: str | None) -> bool:
        return bool(value and value.startswith("lzobj://"))

    @staticmethod
    def object_id_from_reference(value: str) -> str:
        return value.split("lzobj://", 1)[1]

    def put(self, con, namespace: str, original_name: str, data: bytes, content_type: str, owner_id: str | None = None) -> dict:
        object_id = "OBJ-" + uuid.uuid4().hex[:20].upper()
        plain_hash = sha256(data).hexdigest()
        aad_obj = {
            "object_id": object_id,
            "namespace": namespace,
            "original_name": original_name,
            "content_type": content_type,
            "plaintext_sha256": plain_hash,
        }
        aad = json.dumps(aad_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encrypted = self.crypto.encrypt(data, aad)
        rel = Path(namespace.replace("..", "_").strip("/")) / f"{object_id}.lzenc"
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encrypted)
        cipher_hash = sha256(encrypted).hexdigest()
        con.execute(
            """INSERT INTO infrastructure_objects(id,namespace,original_name,stored_path,content_type,plaintext_sha256,ciphertext_sha256,size_bytes,encrypted,owner_id,created_at)
               VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            (object_id, namespace, original_name, str(path), content_type, plain_hash, cipher_hash, len(data), owner_id, utc_iso()),
        )
        return {
            "id": object_id,
            "reference": f"lzobj://{object_id}",
            "plaintext_sha256": plain_hash,
            "ciphertext_sha256": cipher_hash,
            "size_bytes": len(data),
            "encrypted": True,
            "stored_path": str(path),
        }

    def _row(self, con, reference_or_id: str):
        if self.is_reference(reference_or_id):
            object_id = self.object_id_from_reference(reference_or_id)
            return con.execute("SELECT * FROM infrastructure_objects WHERE id=?", (object_id,)).fetchone()
        row = con.execute("SELECT * FROM infrastructure_objects WHERE id=?", (reference_or_id,)).fetchone()
        if row:
            return row
        return con.execute("SELECT * FROM infrastructure_objects WHERE stored_path=?", (str(reference_or_id),)).fetchone()

    def get(self, con, reference_or_id: str) -> bytes:
        row = self._row(con, reference_or_id)
        if not row:
            raise FileNotFoundError("Objeto cifrado no registrado.")
        path = Path(row["stored_path"])
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != row["ciphertext_sha256"]:
            raise ValueError("El objeto cifrado no supera la verificación de integridad.")
        data, aad = self.crypto.decrypt(payload)
        metadata = json.loads(aad.decode("utf-8"))
        if metadata.get("object_id") != row["id"] or sha256(data).hexdigest() != row["plaintext_sha256"]:
            raise ValueError("El objeto descifrado no coincide con su metadato de integridad.")
        con.execute("UPDATE infrastructure_objects SET last_verified_at=? WHERE id=?", (utc_iso(), row["id"]))
        return data

    def verify_all(self, con, limit: int = 500) -> dict:
        rows = con.execute("SELECT id FROM infrastructure_objects ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        errors = []
        for row in rows:
            try:
                self.get(con, row["id"])
            except Exception as exc:
                errors.append({"id": row["id"], "error": str(exc)})
        return {"checked": len(rows), "valid": len(rows) - len(errors), "errors": errors}

    def summary(self, con) -> dict:
        row = con.execute(
            "SELECT COUNT(*) total,COALESCE(SUM(size_bytes),0) bytes,COALESCE(SUM(CASE WHEN encrypted=1 THEN 1 ELSE 0 END),0) encrypted FROM infrastructure_objects"
        ).fetchone()
        return {"backend": "local-encrypted", "total": row["total"], "bytes": row["bytes"], "encrypted": row["encrypted"]}


class MfaManager:
    def __init__(self, crypto: CryptoBox, issuer: str = "LegalAIZ.it"):
        self.crypto = crypto
        self.issuer = issuer

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS mfa_credentials(
              user_id TEXT PRIMARY KEY,
              secret_encrypted BLOB NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 0,
              pending INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              enabled_at TEXT,
              last_used_step INTEGER,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS mfa_recovery_codes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              code_hash TEXT NOT NULL,
              used_at TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_mfa_recovery_user ON mfa_recovery_codes(user_id,used_at);
            """
        )

    @staticmethod
    def _new_secret() -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_secret(secret: str) -> bytes:
        return base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)

    @classmethod
    def totp(cls, secret: str, timestamp: int | None = None, step: int = 30, digits: int = 6) -> tuple[str, int]:
        import time
        counter = int((timestamp if timestamp is not None else time.time()) // step)
        digest = hmac.new(cls._decode_secret(secret), counter.to_bytes(8, "big"), "sha1").digest()
        offset = digest[-1] & 0x0F
        value = (int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF) % (10 ** digits)
        return str(value).zfill(digits), counter

    def _encrypt_secret(self, user_id: str, secret: str) -> bytes:
        return self.crypto.encrypt(secret.encode("ascii"), f"mfa:{user_id}".encode("utf-8"))

    def _decrypt_secret(self, user_id: str, payload: bytes) -> str:
        raw, aad = self.crypto.decrypt(payload)
        if aad != f"mfa:{user_id}".encode("utf-8"):
            raise ValueError("El secreto MFA no corresponde al usuario.")
        return raw.decode("ascii")

    def status(self, con, user_id: str) -> dict:
        row = con.execute("SELECT enabled,pending,created_at,enabled_at FROM mfa_credentials WHERE user_id=?", (user_id,)).fetchone()
        recovery = con.execute("SELECT COUNT(*) FROM mfa_recovery_codes WHERE user_id=? AND used_at IS NULL", (user_id,)).fetchone()[0]
        return {
            "configured": bool(row),
            "enabled": bool(row and row["enabled"]),
            "pending": bool(row and row["pending"]),
            "created_at": row["created_at"] if row else None,
            "enabled_at": row["enabled_at"] if row else None,
            "recovery_codes_remaining": recovery,
        }

    def enroll(self, con, user_id: str, email: str) -> dict:
        secret = self._new_secret()
        con.execute("DELETE FROM mfa_recovery_codes WHERE user_id=?", (user_id,))
        con.execute("DELETE FROM mfa_credentials WHERE user_id=?", (user_id,))
        con.execute(
            "INSERT INTO mfa_credentials(user_id,secret_encrypted,enabled,pending,created_at) VALUES(?,?,0,1,?)",
            (user_id, self._encrypt_secret(user_id, secret), utc_iso()),
        )
        label = f"LegalAIZ.it:{email}"
        uri = f"otpauth://totp/{label}?secret={secret}&issuer=LegalAIZ.it&algorithm=SHA1&digits=6&period=30"
        return {"secret": secret, "otpauth_uri": uri, "notice": "Confirme un código antes de activar MFA."}

    def confirm(self, con, user_id: str, code: str) -> dict:
        row = con.execute("SELECT * FROM mfa_credentials WHERE user_id=? AND pending=1", (user_id,)).fetchone()
        if not row:
            raise ValueError("No existe una inscripción MFA pendiente.")
        secret = self._decrypt_secret(user_id, row["secret_encrypted"])
        ok, used_step = self._verify_totp(secret, code, row["last_used_step"])
        if not ok:
            raise ValueError("Código MFA inválido.")
        recovery = ["-".join([secrets.token_hex(2).upper(), secrets.token_hex(2).upper(), secrets.token_hex(2).upper()]) for _ in range(10)]
        con.execute("DELETE FROM mfa_recovery_codes WHERE user_id=?", (user_id,))
        con.executemany(
            "INSERT INTO mfa_recovery_codes(user_id,code_hash,created_at) VALUES(?,?,?)",
            [(user_id, sha256(x.encode("utf-8")).hexdigest(), utc_iso()) for x in recovery],
        )
        con.execute(
            "UPDATE mfa_credentials SET enabled=1,pending=0,enabled_at=?,last_used_step=? WHERE user_id=?",
            (utc_iso(), used_step, user_id),
        )
        return {"enabled": True, "recovery_codes": recovery}

    def _verify_totp(self, secret: str, code: str, last_used_step: int | None = None) -> tuple[bool, int | None]:
        import time
        clean = "".join(ch for ch in str(code or "") if ch.isdigit())
        now = int(time.time())
        for offset in (-1, 0, 1):
            expected, step = self.totp(secret, now + offset * 30)
            if hmac.compare_digest(expected, clean) and (last_used_step is None or step > int(last_used_step)):
                return True, step
        return False, None

    def verify_login(self, con, user_id: str, code: str) -> bool:
        row = con.execute("SELECT * FROM mfa_credentials WHERE user_id=? AND enabled=1", (user_id,)).fetchone()
        if not row:
            return True
        clean = (code or "").strip().upper()
        if clean:
            recovery_hash = sha256(clean.encode("utf-8")).hexdigest()
            rec = con.execute("SELECT id FROM mfa_recovery_codes WHERE user_id=? AND code_hash=? AND used_at IS NULL", (user_id, recovery_hash)).fetchone()
            if rec:
                con.execute("UPDATE mfa_recovery_codes SET used_at=? WHERE id=?", (utc_iso(), rec["id"]))
                return True
        secret = self._decrypt_secret(user_id, row["secret_encrypted"])
        ok, step = self._verify_totp(secret, clean, row["last_used_step"])
        if ok:
            con.execute("UPDATE mfa_credentials SET last_used_step=? WHERE user_id=?", (step, user_id))
        return ok

    def disable(self, con, user_id: str) -> None:
        con.execute("DELETE FROM mfa_recovery_codes WHERE user_id=?", (user_id,))
        con.execute("DELETE FROM mfa_credentials WHERE user_id=?", (user_id,))


class BackupCenter:
    def __init__(self, root: Path, crypto: CryptoBox, retention: int = 10):
        self.root = Path(root)
        self.crypto = crypto
        self.retention = retention
        self.base = _runtime_root(self.root) / "backups"
        self.base.mkdir(parents=True, exist_ok=True)

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS infrastructure_backups(
              id TEXT PRIMARY KEY,
              filename TEXT NOT NULL,
              file_path TEXT NOT NULL,
              status TEXT NOT NULL,
              encrypted INTEGER NOT NULL DEFAULT 1,
              sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              manifest_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              verified_at TEXT,
              verification_detail TEXT
            );
            """
        )

    def _sqlite_snapshot(self, source_db: Path, target_db: Path) -> None:
        source = sqlite3.connect(source_db)
        target = sqlite3.connect(target_db)
        try:
            source.backup(target)
        finally:
            target.close(); source.close()

    def create(self, con, source_db: Path, actor: str) -> dict:
        backup_id = "BKP-" + uuid.uuid4().hex[:16].upper()
        created = utc_iso()
        with TemporaryDirectory(prefix="legalaiz-backup-") as temp_dir:
            temp = Path(temp_dir)
            snapshot_db = temp / "legalaizit.db"
            self._sqlite_snapshot(source_db, snapshot_db)
            check_con = sqlite3.connect(snapshot_db)
            try:
                integrity = check_con.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                check_con.close()
            manifest = {
                "backup_id": backup_id,
                "created_at": created,
                "database": "sqlite",
                "database_integrity": integrity,
                "included": ["runtime/legalaizit.db", "data/*.json", "runtime/object_store", "canonical_sources"],
                "restore_mode": "offline-controlled",
            }
            archive = BytesIO()
            with ZipFile(archive, "w", ZIP_DEFLATED) as z:
                z.write(snapshot_db, "runtime/legalaizit.db")
                for folder_name in ("data", "canonical_sources", "runtime/object_store"):
                    folder = self.root / folder_name
                    if folder.exists():
                        for path in folder.rglob("*"):
                            if path.is_file():
                                z.write(path, path.relative_to(self.root).as_posix())
                z.writestr("BACKUP_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            aad = json.dumps({"backup_id": backup_id, "created_at": created}, sort_keys=True).encode("utf-8")
            encrypted = self.crypto.encrypt(archive.getvalue(), aad, BACKUP_MAGIC)
        filename = f"LegalAIZit_{backup_id}_{created[:10]}.lzbackup"
        path = self.base / filename
        path.write_bytes(encrypted)
        digest = sha256(encrypted).hexdigest()
        con.execute(
            """INSERT INTO infrastructure_backups(id,filename,file_path,status,encrypted,sha256,size_bytes,manifest_json,created_by,created_at)
               VALUES(?,?,?,'Creado',1,?,?,?,?,?)""",
            (backup_id, filename, str(path), digest, len(encrypted), json.dumps(manifest, ensure_ascii=False), actor, created),
        )
        self._apply_retention(con)
        return {"id": backup_id, "filename": filename, "sha256": digest, "size_bytes": len(encrypted), "status": "Creado", "manifest": manifest}

    def _apply_retention(self, con):
        rows = con.execute("SELECT id,file_path FROM infrastructure_backups ORDER BY created_at DESC").fetchall()
        for row in rows[self.retention:]:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            finally:
                con.execute("DELETE FROM infrastructure_backups WHERE id=?", (row["id"],))

    def verify(self, con, backup_id: str) -> dict:
        row = con.execute("SELECT * FROM infrastructure_backups WHERE id=?", (backup_id,)).fetchone()
        if not row:
            raise ValueError("Backup no encontrado.")
        path = Path(row["file_path"])
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != row["sha256"]:
            detail = "Hash externo inválido."
            con.execute("UPDATE infrastructure_backups SET status='Inválido',verification_detail=? WHERE id=?", (detail, backup_id))
            raise ValueError(detail)
        archive, _ = self.crypto.decrypt(payload, BACKUP_MAGIC)
        with TemporaryDirectory(prefix="legalaiz-verify-") as temp_dir:
            temp = Path(temp_dir)
            with ZipFile(BytesIO(archive)) as z:
                bad = z.testzip()
                if bad:
                    raise ValueError(f"Entrada ZIP corrupta: {bad}")
                z.extract("runtime/legalaizit.db", temp)
                manifest = json.loads(z.read("BACKUP_MANIFEST.json").decode("utf-8"))
            db_path = temp / "runtime" / "legalaizit.db"
            db_con = sqlite3.connect(db_path)
            integrity = db_con.execute("PRAGMA integrity_check").fetchone()[0]
            db_con.close()
        if integrity != "ok":
            raise ValueError("La base restaurable no supera integrity_check.")
        verified_at = utc_iso()
        detail = json.dumps({"integrity": integrity, "manifest": manifest}, ensure_ascii=False)
        con.execute("UPDATE infrastructure_backups SET status='Verificado',verified_at=?,verification_detail=? WHERE id=?", (verified_at, detail, backup_id))
        return {"id": backup_id, "status": "Verificado", "verified_at": verified_at, "integrity": integrity, "manifest": manifest}

    def list(self, con) -> list[dict]:
        return [dict(x) for x in con.execute("SELECT id,filename,status,encrypted,sha256,size_bytes,created_by,created_at,verified_at,verification_detail FROM infrastructure_backups ORDER BY created_at DESC").fetchall()]

    def row(self, con, backup_id: str):
        return con.execute("SELECT * FROM infrastructure_backups WHERE id=?", (backup_id,)).fetchone()


class InfrastructureCenter:
    def __init__(self, root: Path, settings: AppSettings):
        self.root = Path(root)
        self.settings = settings
        self.secrets = SecretManager(self.root, settings)
        self.crypto = CryptoBox(self.secrets.key)
        self.objects = EncryptedObjectStore(self.root, self.secrets, settings)
        self.mfa = MfaManager(self.crypto)
        self.backups = BackupCenter(self.root, self.crypto, settings.backup_retention)

    def create_schema(self, con):
        self.objects.create_schema(con)
        self.mfa.create_schema(con)
        self.backups.create_schema(con)
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS infrastructure_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS migration_runs(
              id TEXT PRIMARY KEY,
              target TEXT NOT NULL,
              status TEXT NOT NULL,
              manifest_hash TEXT,
              detail_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )

    def event(self, con, event_type: str, actor: str, detail) -> None:
        con.execute(
            "INSERT INTO infrastructure_events(event_type,actor,detail_json,created_at) VALUES(?,?,?,?)",
            (event_type, actor, json.dumps(detail, ensure_ascii=False, sort_keys=True), utc_iso()),
        )

    def mfa_coverage(self, con) -> dict:
        rows = con.execute(
            """SELECT u.id,u.name,u.email,u.role,COALESCE(m.enabled,0) enabled
               FROM users u LEFT JOIN mfa_credentials m ON m.user_id=u.id WHERE u.active=1 ORDER BY u.role,u.name"""
        ).fetchall()
        required = [dict(x) for x in rows if x["role"] in self.settings.require_mfa_roles]
        return {
            "required_roles": list(self.settings.require_mfa_roles),
            "required_users": len(required),
            "enabled_required_users": sum(bool(x["enabled"]) for x in required),
            "users": [dict(x) for x in rows],
        }

    def doctor(self, con) -> dict:
        mfa = self.mfa_coverage(con)
        backups = self.backups.list(con)
        object_summary = self.objects.summary(con)
        checks = [
            {"key": "master_key", "label": "Llave maestra administrada", "passed": self.secrets.origin in {"environment", "secret-file"} or self.settings.profile == "local", "detail": self.secrets.origin},
            {"key": "aes_gcm", "label": "Cifrado AES-256-GCM disponible", "passed": AESGCM is not None, "detail": "cryptography" if AESGCM else "dependencia ausente"},
            {"key": "secure_cookies", "label": "Cookies Secure para despliegue", "passed": self.settings.secure_cookies or self.settings.profile == "local", "detail": self.settings.secure_cookies},
            {"key": "public_https", "label": "URL pública HTTPS", "passed": self.settings.public_base_url.startswith("https://") or self.settings.profile == "local", "detail": self.settings.public_base_url},
            {"key": "mfa", "label": "MFA de roles obligatorios", "passed": mfa["required_users"] == mfa["enabled_required_users"], "detail": {"enabled": mfa["enabled_required_users"], "required": mfa["required_users"]}},
            {"key": "object_storage", "label": "Almacenamiento cifrado operativo", "passed": self.settings.object_storage_backend == "local-encrypted" and self.settings.object_storage_encryption, "detail": object_summary},
            {"key": "volume_encryption", "label": "Cifrado del volumen/base confirmado", "passed": self.settings.volume_encryption_confirmed or self.settings.profile == "local", "detail": self.settings.volume_encryption_confirmed},
            {"key": "malware_scanner", "label": "Escaneo antimalware operativo", "passed": MalwareScanner(self.settings.malware_scanner, self.settings.profile).available(), "detail": self.settings.malware_scanner},
            {"key": "verified_backup", "label": "Backup cifrado verificado", "passed": any(x["status"] == "Verificado" for x in backups), "detail": {"backups": len(backups), "verified": sum(x["status"] == "Verificado" for x in backups)}},
            {"key": "database", "label": "Base adecuada al perfil", "passed": self.settings.database_backend == "postgresql" if self.settings.profile == "production" else self.settings.database_backend in {"sqlite", "postgresql"}, "detail": runtime_status().public()},
            {"key": "postgres_runtime", "label": "Runtime PostgreSQL certificado externamente", "passed": self.settings.database_backend == "postgresql" and runtime_status().driver_available and _parse_bool(os.environ.get("LEGAL_POSTGRES_EXTERNAL_CERTIFIED"), False), "detail": {"adapter_implemented": True, "driver_available": runtime_status().driver_available, "external_certified": _parse_bool(os.environ.get("LEGAL_POSTGRES_EXTERNAL_CERTIFIED"), False), "notice": "M31.5 implementa el adaptador; la certificación exige ejecutar tools/postgres_certify.py en la infraestructura objetivo."}},
            {"key": "canonical_sources", "label": "Fuentes jurídicas canónicas incorporadas", "passed": con.execute("SELECT COUNT(*) FROM canonical_source_files WHERE verified=1").fetchone()[0] > 0, "detail": "No se sustituye por infraestructura."},
        ]
        blocking = [x for x in checks if not x["passed"]]
        return {
            "profile": self.settings.profile,
            "checks": checks,
            "passed": len(checks) - len(blocking),
            "total": len(checks),
            "ready": not blocking,
            "blocking": [x["key"] for x in blocking],
            "notice": "Este diagnóstico no autoriza publicación jurídica ni despliegue productivo. PostgreSQL permanece como migración preparada, no como runtime certificado.",
        }

    def summary(self, con) -> dict:
        recent_events = [dict(x) for x in con.execute("SELECT * FROM infrastructure_events ORDER BY id DESC LIMIT 40").fetchall()]
        return {
            "settings": self.settings.public(),
            "secret_management": {"origin": self.secrets.origin, "fingerprint": self.secrets.fingerprint},
            "objects": self.objects.summary(con),
            "mfa": self.mfa_coverage(con),
            "backups": self.backups.list(con),
            "doctor": self.doctor(con),
            "events": recent_events,
            "database_migration": {
                "current_runtime": self.settings.database_backend,
                "target": "postgresql",
                "status": "Adaptador implementado; certificación externa pendiente" if not _parse_bool(os.environ.get("LEGAL_POSTGRES_EXTERNAL_CERTIFIED"), False) else "Certificación externa declarada",
                "runtime": runtime_status().public(),
                "artifacts": ["deploy/docker-compose.postgres-preproduction.yml", "tools/export_postgres_schema.py", "tools/migrate_sqlite_to_postgres.py", "tools/postgres_certify.py", "deploy/PREPRODUCTION_RUNBOOK_M31_4.md"],
            },
        }


def read_reference_bytes(con, object_store: EncryptedObjectStore, reference: str) -> bytes:
    if object_store.is_reference(reference) or str(reference).endswith('.lzenc'):
        return object_store.get(con, reference)
    return Path(reference).read_bytes()
