from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED
import json
import os
import shutil
import sqlite3
import uuid

from core_v11 import *  # noqa: F401,F403
import core_v11 as core
from security import (
    LOCKOUT_ATTEMPTS,
    hash_password,
    idle_expiry,
    is_future,
    lockout_expiry,
    new_token,
    password_needs_rehash,
    session_expiry,
    token_hash,
    utc_iso,
    verify_password,
)
from legalai_platform.operational_security import redact_event_detail
from legalai_platform.runtime_registry import *  # noqa: F401,F403

def _add_column(con: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def create_security_schema(con: sqlite3.Connection) -> None:
    _add_column(con, "users", "password_hash TEXT")
    _add_column(con, "users", "failed_attempts INTEGER NOT NULL DEFAULT 0")
    _add_column(con, "users", "locked_until TEXT")
    _add_column(con, "users", "active INTEGER NOT NULL DEFAULT 1")
    _add_column(con, "users", "created_at TEXT")
    _add_column(con, "users", "last_login_at TEXT")
    _add_column(con, "attachments", "sha256 TEXT")
    _add_column(con, "attachments", "detected_type TEXT")
    _add_column(con, "attachments", "security_status TEXT")
    _add_column(con, "attachments", "uploaded_by TEXT")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions(
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          token_hash TEXT NOT NULL UNIQUE,
          csrf_token TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          ip_address TEXT,
          user_agent TEXT,
          revoked INTEGER NOT NULL DEFAULT 0,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id,revoked,expires_at);
        CREATE TABLE IF NOT EXISTS security_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id TEXT,
          event_type TEXT NOT NULL,
          outcome TEXT NOT NULL,
          ip_address TEXT,
          user_agent TEXT,
          detail TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at DESC);
        """
    )
    _add_column(con, "sessions", "auth_level TEXT NOT NULL DEFAULT 'full'")
    _add_column(con, "sessions", "mfa_verified_at TEXT")
    _add_column(con, "sessions", "idle_expires_at TEXT")
    _add_column(con, "sessions", "reauthenticated_at TEXT")
    _add_column(con, "security_events", "previous_hash TEXT")
    _add_column(con, "security_events", "event_hash TEXT")



def rebase_portable_paths(con: sqlite3.Connection) -> int:
    """Reubica rutas absolutas de la distribución cuando la carpeta cambia de equipo.

    Los archivos demo se empaquetan junto al proyecto, pero SQLite conserva la ruta
    usada al construir el ZIP. En cada arranque se corrigen únicamente rutas locales
    ausentes cuyo nombre existe dentro del runtime actual. Referencias cifradas u
    objetos externos no se modifican.
    """
    mappings = [
        ("documents", "id", "file_path", core.GENERATED),
        ("document_versions", "id", "file_path", core.GENERATED),
        ("attachments", "id", "file_path", core.UPLOADS),
        ("document_packages", "id", "file_path", core.GENERATED / "packages"),
        ("document_pdf_previews", "id", "file_path", core.GENERATED / "pdf_previews"),
        ("document_acceptances", "id", "receipt_path", core.GENERATED / "acceptance_receipts"),
        ("infrastructure_backups", "id", "file_path", core.RUNTIME / "backups"),
    ]
    changed = 0
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, key, column, base in mappings:
        if table not in tables:
            continue
        columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if key not in columns or column not in columns:
            continue
        for row in con.execute(f"SELECT {key},{column} FROM {table} WHERE {column} IS NOT NULL AND {column}!=''").fetchall():
            raw = str(row[column])
            if raw.startswith(("encobj:", "object:", "s3://", "az://")):
                continue
            current = Path(raw)
            candidate = Path(base) / current.name
            try:
                current_resolved = current.resolve()
                candidate_resolved = candidate.resolve()
                belongs_to_current_root = current_resolved.is_relative_to(core.ROOT.resolve())
            except (OSError, RuntimeError, ValueError):
                current_resolved = current
                candidate_resolved = candidate
                belongs_to_current_root = False
            # Una ruta ya válida dentro del runtime activo no requiere reescritura,
            # aunque LEGAL_RUNTIME_DIR esté fuera de la carpeta del proyecto.
            if current.is_file() and (belongs_to_current_root or current_resolved == candidate_resolved):
                continue
            if candidate.is_file() and current_resolved != candidate_resolved:
                con.execute(f"UPDATE {table} SET {column}=? WHERE {key}=?", (str(candidate), row[key]))
                changed += 1
    return changed

def _allow_demo_accounts() -> bool:
    raw = str(os.environ.get("LEGAL_ALLOW_DEMO_ACCOUNTS", "")).strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "si", "sí"}
    return SETTINGS.profile == "local" and SETTINGS.app_env != "pilot-local"


def init_db(reset: bool = False):
    allow_demo = _allow_demo_accounts()
    if reset:
        # A reset explícito debe retirar artefactos demo huérfanos, no solo recrear SQLite.
        # Se preservan secretos, respaldos y almacenamiento cifrado de infraestructura.
        for folder in (core.GENERATED, core.UPLOADS):
            shutil.rmtree(folder, ignore_errors=True)
            folder.mkdir(parents=True, exist_ok=True)
    core.init_db(reset=reset, seed_demo_data=allow_demo)
    con = core.db()
    create_security_schema(con)
    FACTORY.create_schema(con)
    FACTORY.init_baselines(con)
    CANONICAL.create_schema(con)
    CANONICAL.init_baselines(con)
    TRACEABILITY.create_schema(con)
    INTAKE.create_schema(con)
    REVIEW.create_schema(con)
    REVIEW.init_jobs(con)
    BATCHES.create_schema(con)
    NORMATIVE.create_schema(con)
    INFRA.create_schema(con)
    UX.create_schema(con)
    WORKFLOW.create_schema(con)
    WORKSPACE.create_schema(con)
    SELF_SERVICE.create_schema(con)
    ANON_DRAFTS.create_schema(con)
    PAYMENTS.create_schema(con)
    DELIVERY.create_schema(con)
    PDF_ACCEPTANCE.create_schema(con)
    M24_PILOT_OPERATIONS.ensure_schema(con)
    M24_PROFESSIONAL_NETWORK.ensure_schema(con)
    M24_HUMAN_APPROVAL.apply(con, M24_RELEASE_GOVERNANCE)
    M25_PILOT_READINESS.ensure_schema(con)
    M31_PREPRODUCTION.ensure_schema(con)
    M31_CASE_DEMO.ensure_schema(con)
    CANONICAL_GENERATION.create_schema(con)
    COEM003_V28.create_schema(con)
    RELEASE_V217.create_schema(con)
    VISUAL_QA_V218.create_schema(con)
    VALIDATION_V219.create_schema(con)
    CHANGE_CONTROL_V220.create_schema(con)
    RELEASE_CYCLE_V221.create_schema(con)
    COEM003_V28.init_baseline(con)
    PRIORITY_V29.create_schema(con)
    PRIORITY_V29.init_baseline(con)
    ACTIVATION_V210.create_schema(con)
    if allow_demo:
        WORKFLOW.init_demo(con)
        WORKSPACE.init_demo_versions(con)
    rebase_portable_paths(con)
    VISUAL_QA_V218.init_baseline(con, core.now())
    password = hash_password(DEMO_PASSWORD)
    t = utc_iso()
    con.execute(
        "UPDATE users SET password_hash=COALESCE(password_hash,?),active=1,created_at=COALESCE(created_at,?)",
        (password, t),
    )
    if allow_demo:
        # La clave local se rota en cada inicio para evitar credenciales empaquetadas.
        con.execute("UPDATE users SET password_hash=?,active=1 WHERE lower(email) LIKE '%@demo.legalaiz.it'", (password,))
    else:
        con.execute("UPDATE users SET active=0 WHERE lower(email) LIKE '%@demo.legalaiz.it'")
    bootstrap_email = str(os.environ.get("LEGAL_BOOTSTRAP_ADMIN_EMAIL", "")).strip().lower()
    bootstrap_password = str(os.environ.get("LEGAL_BOOTSTRAP_ADMIN_PASSWORD", ""))
    if bootstrap_email and bootstrap_password:
        bootstrap_name = str(os.environ.get("LEGAL_BOOTSTRAP_ADMIN_NAME", "Administrador LegalAIZ.it")).strip() or "Administrador LegalAIZ.it"
        bootstrap_specialty = str(os.environ.get("LEGAL_BOOTSTRAP_ADMIN_SPECIALTY", "Gobernanza jurídica y producto")).strip()
        bootstrap_hash = hash_password(bootstrap_password)
        existing = con.execute("SELECT id FROM users WHERE lower(email)=?", (bootstrap_email,)).fetchone()
        if existing:
            con.execute("UPDATE users SET name=?,role='admin',specialty=?,verified=1,active=1,password_hash=?,created_at=COALESCE(created_at,?) WHERE id=?", (bootstrap_name, bootstrap_specialty, bootstrap_hash, t, existing["id"]))
        else:
            con.execute("INSERT INTO users(id,name,email,role,specialty,verified,password_hash,active,created_at) VALUES(?,?,?,?,?,?,?,?,?)", ("USR-BOOTSTRAP-ADMIN", bootstrap_name, bootstrap_email, "admin", bootstrap_specialty, 1, bootstrap_hash, 1, t))
    con.commit()
    con.close()


def security_event(con, user_id, event_type, outcome, ip, user_agent, detail=""):
    clean_detail = redact_event_detail(detail)
    if not isinstance(clean_detail, str):
        clean_detail = json.dumps(clean_detail, ensure_ascii=False, sort_keys=True)
    created = utc_iso()
    previous = con.execute("SELECT event_hash FROM security_events WHERE event_hash IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    previous_hash = previous[0] if previous else ""
    canonical = json.dumps({"user_id": user_id, "event_type": event_type, "outcome": outcome, "ip": ip, "user_agent": (user_agent or "")[:500], "detail": clean_detail[:4000], "created_at": created, "previous_hash": previous_hash}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    event_hash = sha256(canonical.encode("utf-8")).hexdigest()
    con.execute(
        "INSERT INTO security_events(user_id,event_type,outcome,ip_address,user_agent,detail,created_at,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, event_type, outcome, ip, (user_agent or "")[:500], clean_detail[:4000], created, previous_hash or None, event_hash),
    )


def public_user(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "specialty": row["specialty"],
        "verified": bool(row["verified"]),
    }


def authenticate(email: str, password: str, ip: str, user_agent: str, mfa_code: str = ""):
    email = (email or "").strip().lower()
    allowed, retry = RATE_LIMITER.allow(f"login-ip:{ip}", 12, 300)
    if not allowed:
        return None, {"message": "Demasiados intentos. Intente nuevamente más tarde.", "code": "RATE_LIMITED", "retry_after": retry}
    con = core.db()
    row = con.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
    if not row or not row["active"]:
        security_event(con, row["id"] if row else None, "login", "denied", ip, user_agent, "Cuenta inexistente o inactiva")
        con.commit(); con.close()
        return None, "Credenciales inválidas."
    if is_future(row["locked_until"]):
        security_event(con, row["id"], "login", "locked", ip, user_agent, "Cuenta temporalmente bloqueada")
        con.commit(); con.close()
        return None, "Cuenta temporalmente bloqueada por intentos fallidos."
    if not verify_password(password or "", row["password_hash"] or ""):
        attempts = int(row["failed_attempts"] or 0) + 1
        locked = lockout_expiry() if attempts >= LOCKOUT_ATTEMPTS else None
        con.execute("UPDATE users SET failed_attempts=?,locked_until=? WHERE id=?", (attempts, locked, row["id"]))
        security_event(con, row["id"], "login", "denied", ip, user_agent, {"failed_attempts": attempts})
        con.commit(); con.close()
        return None, "Credenciales inválidas."
    if password_needs_rehash(row["password_hash"]):
        con.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), row["id"]))
        security_event(con, row["id"], "password_hash", "upgraded", ip, user_agent, {"algorithm": "scrypt"})
    mfa_status = INFRA.mfa.status(con, row["id"])
    mfa_required = row["role"] in SETTINGS.require_mfa_roles
    if mfa_status.get("enabled") and not INFRA.mfa.verify_login(con, row["id"], mfa_code or ""):
        security_event(con, row["id"], "mfa_login", "denied", ip, user_agent, {"configured": True})
        con.commit(); con.close()
        return None, {"message": "Se requiere un código MFA válido.", "code": "MFA_REQUIRED"}
    restricted = bool(mfa_required and not mfa_status.get("enabled"))
    token = new_token(32); csrf = new_token(24); sid = "SES-" + uuid.uuid4().hex[:16].upper(); t = utc_iso()
    auth_level = "password_only" if restricted else "full"
    mfa_verified_at = t if mfa_status.get("enabled") else None
    con.execute("UPDATE users SET failed_attempts=0,locked_until=NULL,last_login_at=? WHERE id=?", (t, row["id"]))
    con.execute(
        "INSERT INTO sessions(id,user_id,token_hash,csrf_token,created_at,expires_at,last_seen_at,ip_address,user_agent,revoked,auth_level,mfa_verified_at,idle_expires_at,reauthenticated_at) VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,?)",
        (sid, row["id"], token_hash(token), csrf, t, session_expiry(), t, ip, user_agent[:500], auth_level, mfa_verified_at, idle_expiry(row["role"], client_minutes=SETTINGS.session_idle_minutes_client, privileged_minutes=SETTINGS.session_idle_minutes_privileged), t),
    )
    security_event(con, row["id"], "login", "restricted" if restricted else "success", ip, user_agent, {"session_id": sid, "auth_level": auth_level})
    con.commit(); row = con.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone(); user = public_user(row); con.close()
    return {"token": token, "csrf": csrf, "session_id": sid, "user": user, "mfa_enrollment_required": restricted, "auth_level": auth_level}, None


def get_session(token: str | None):
    if not token: return None
    con = core.db()
    row = con.execute(
        """SELECT s.*,u.name,u.email,u.role,u.specialty,u.verified,u.active
           FROM sessions s JOIN users u ON u.id=s.user_id
           WHERE s.token_hash=? AND s.revoked=0 AND s.expires_at>? AND u.active=1""",
        (token_hash(token), utc_iso()),
    ).fetchone()
    if not row:
        con.close(); return None
    if row["idle_expires_at"] and not is_future(row["idle_expires_at"]):
        con.execute("UPDATE sessions SET revoked=1 WHERE id=?", (row["id"],))
        security_event(con, row["user_id"], "session", "idle_expired", row["ip_address"] or "", row["user_agent"] or "", {"session_id": row["id"]})
        con.commit(); con.close(); return None
    next_idle = idle_expiry(row["role"], client_minutes=SETTINGS.session_idle_minutes_client, privileged_minutes=SETTINGS.session_idle_minutes_privileged)
    con.execute("UPDATE sessions SET last_seen_at=?,idle_expires_at=? WHERE id=?", (utc_iso(), next_idle, row["id"]))
    con.commit(); con.close()
    return {"id": row["id"], "csrf": row["csrf_token"], "auth_level": row["auth_level"] or "full", "mfa_enrollment_required": (row["auth_level"] or "full") != "full", "user": {"id": row["user_id"], "name": row["name"], "email": row["email"], "role": row["role"], "specialty": row["specialty"], "verified": bool(row["verified"])}}


def case_scope(user):
    role = user["role"]
    if role == "admin":
        return "1=1", []
    if role == "client":
        return "c.owner_id=?", [user["id"]]
    return "(c.specialist_id=? OR c.specialist_id IS NULL)", [user["id"]]


def can_access_case(user, cid):
    con = core.db()
    row = con.execute("SELECT id,owner_id,specialist_id FROM cases WHERE id=?", (cid,)).fetchone()
    con.close()
    if not row:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] == "client":
        return row["owner_id"] == user["id"]
    return row["specialist_id"] in (None, user["id"])


def scoped_dashboard(user):
    clause, params = case_scope(user)
    con = core.db()
    cases = [dict(x) for x in con.execute(
        f"SELECT c.id,c.product_code,c.title,c.risk,c.status,c.owner_id,c.specialist_id,c.review_status,c.created_at,c.updated_at,u.name specialist_name FROM cases c LEFT JOIN users u ON u.id=c.specialist_id WHERE {clause} ORDER BY c.updated_at DESC",
        params,
    ).fetchall()]
    docs = [dict(x) for x in con.execute(
        f"SELECT d.id,d.name,d.case_id,d.created_at,d.status FROM documents d JOIN cases c ON c.id=d.case_id WHERE {clause} ORDER BY d.updated_at DESC LIMIT 8",
        params,
    ).fetchall()]
    acts = [dict(x) for x in con.execute(
        f"SELECT a.* FROM activity a JOIN cases c ON c.id=a.case_id WHERE {clause} ORDER BY a.id DESC LIMIT 12",
        params,
    ).fetchall()]
    reviews = [dict(x) for x in con.execute(
        f"SELECT c.id,c.title,c.product_code,c.risk,c.review_status,c.updated_at FROM cases c WHERE {clause} AND c.review_status!='Aprobado' ORDER BY CASE c.risk WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END,c.updated_at DESC",
        params,
    ).fetchall()]
    ids = [x["id"] for x in cases]
    pending_tasks = 0
    if ids:
        placeholders = ",".join("?" for _ in ids)
        pending_tasks = con.execute(
            f"SELECT COUNT(*) FROM case_tasks WHERE case_id IN ({placeholders}) AND status IN ('Pendiente','Bloqueada')", ids
        ).fetchone()[0]
    con.close()
    return {
        "role": user["role"],
        "user": user,
        "stats": {
            "cases": len(cases), "green": sum(x["risk"] == "green" for x in cases),
            "yellow": sum(x["risk"] == "yellow" for x in cases), "red": sum(x["risk"] == "red" for x in cases),
            "documents": len(docs), "pending_reviews": len(reviews), "pending_tasks": pending_tasks,
        },
        "cases": cases[:8], "documents": docs, "activity": acts, "reviews": reviews,
    }


def scoped_cases(user):
    clause, params = case_scope(user)
    con = core.db()
    rows = [dict(x) for x in con.execute(
        f"SELECT c.id,c.product_code,c.title,c.risk,c.status,c.owner_id,c.specialist_id,c.review_status,c.created_at,c.updated_at,u.name specialist_name FROM cases c LEFT JOIN users u ON u.id=c.specialist_id WHERE {clause} ORDER BY c.updated_at DESC", params
    ).fetchall()]
    con.close(); return rows


def safe_case_detail(user, cid):
    if not can_access_case(user, cid):
        return None
    obj = core.case_detail(cid)
    if not obj:
        return None
    con = core.db()
    try:
        delivery = DELIVERY.summary(con, cid)
        con.commit()
    finally:
        con.close()
    lineage = {item["id"]: item for item in delivery.get("documents", [])}
    for item in obj.get("documents", []):
        item.update(lineage.get(item.get("id"), {}))
    obj["document_delivery"] = {
        "latest_package": delivery.get("latest_package"),
        "notice": delivery.get("notice"),
    }
    for item in obj.get("attachments", []):
        item.pop("file_path", None)
    return obj


def secure_case_export_bytes(user, cid):
    if not can_access_case(user, cid):
        return None
    case = core.case_detail(cid)
    if not case:
        return None
    export_case = json.loads(json.dumps(case, ensure_ascii=False, default=str))
    for item in export_case.get("attachments", []):
        item.pop("file_path", None)
    out = BytesIO()
    from zipfile import ZIP_DEFLATED
    with ZipFile(out, "w", ZIP_DEFLATED) as z:
        z.writestr("expediente.json", json.dumps(export_case, ensure_ascii=False, indent=2))
        con = core.db()
        for doc in case.get("documents", []):
            row = con.execute("SELECT file_path,name FROM documents WHERE id=?", (doc["id"],)).fetchone()
            if row and row["file_path"] and Path(row["file_path"]).exists():
                z.write(row["file_path"], arcname=f"documentos/{core.safe_filename(row['name'])}")
        for att in case.get("attachments", []):
            raw = con.execute("SELECT file_path,name FROM attachments WHERE id=?", (att["id"],)).fetchone()
            if raw and raw["file_path"]:
                try:
                    body = read_reference_bytes(con, INFRA.objects, raw["file_path"])
                    z.writestr(f"soportes/{att['id']}_{core.safe_filename(raw['name'])}", body)
                except Exception:
                    pass
        con.commit(); con.close()
    return out.getvalue()


def scoped_documents(user):
    clause, params = case_scope(user)
    con = core.db()
    rows = [dict(x) for x in con.execute(
        f"""SELECT d.id,d.case_id,d.product_code,d.kind,d.name,d.mime_type,d.created_at,d.updated_at,
                   d.version,d.status,d.content_sha256,d.template_id,d.template_revision_id,d.template_hash,
                   d.canonical_status,d.generation_engine
            FROM documents d JOIN cases c ON c.id=d.case_id
            WHERE {clause} ORDER BY d.updated_at DESC""", params
    ).fetchall()]
    con.close(); return rows


def document_row(user, did):
    con = core.db()
    row = con.execute("SELECT d.*,c.owner_id,c.specialist_id FROM documents d JOIN cases c ON c.id=d.case_id WHERE d.id=?", (did,)).fetchone()
    if not row:
        con.close(); return None
    allowed = user["role"] == "admin" or (user["role"] == "client" and row["owner_id"] == user["id"]) or (user["role"] == "specialist" and row["specialist_id"] in (None, user["id"]))
    if not allowed:
        con.close(); return None
    obj = dict(row)
    if obj.get("lineage_json"):
        try:
            obj["lineage"] = json.loads(obj["lineage_json"])
        except (TypeError, json.JSONDecodeError):
            obj["lineage"] = None
    obj["versions"] = [dict(x) for x in con.execute("SELECT * FROM document_versions WHERE document_id=? ORDER BY id DESC", (did,)).fetchall()]
    con.close(); return obj


def attachment_row(user, aid):
    con = core.db()
    row = con.execute("SELECT a.*,c.owner_id,c.specialist_id FROM attachments a JOIN cases c ON c.id=a.case_id WHERE a.id=?", (aid,)).fetchone()
    con.close()
    if not row:
        return None
    if user["role"] == "admin": return dict(row)
    if user["role"] == "client" and row["owner_id"] == user["id"]: return dict(row)
    if user["role"] == "specialist" and row["specialist_id"] in (None, user["id"]): return dict(row)
    return None


def validate_upload(filename: str, data: bytes):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOADS:
        raise ValueError("Tipo de archivo no permitido. Use PDF, DOCX, XLSX, PNG, JPG o TXT.")
    detected = None
    if ext == ".pdf" and data.startswith(b"%PDF-"):
        detected = ALLOWED_UPLOADS[ext]
    elif ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = ALLOWED_UPLOADS[ext]
    elif ext in (".jpg", ".jpeg") and data.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    elif ext == ".txt":
        if b"\x00" in data:
            raise ValueError("El archivo de texto contiene bytes no permitidos.")
        data.decode("utf-8")
        detected = "text/plain"
    elif ext in (".docx", ".xlsx"):
        if not data.startswith(b"PK\x03\x04"):
            raise ValueError("El archivo Office no tiene una estructura ZIP válida.")
        try:
            with ZipFile(BytesIO(data)) as z:
                names = z.namelist()
                if len(names) > 2000 or sum(i.file_size for i in z.infolist()) > 50 * 1024 * 1024:
                    raise ValueError("El archivo Office excede los límites seguros de expansión.")
                if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                    raise ValueError("El archivo Office contiene rutas internas no permitidas.")
                required = "word/" if ext == ".docx" else "xl/"
                if "[Content_Types].xml" not in names or not any(name.startswith(required) for name in names):
                    raise ValueError("El contenido no coincide con la extensión declarada.")
                if any(name.lower().endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".vbs", ".ps1")) for name in names):
                    raise ValueError("El archivo Office contiene macros o componentes ejecutables no permitidos.")
                compressed = max(1, len(data))
                expanded = sum(i.file_size for i in z.infolist())
                if expanded / compressed > 100:
                    raise ValueError("El archivo Office presenta una relación de expansión insegura.")
        except BadZipFile as exc:
            raise ValueError("El archivo Office está dañado o no es válido.") from exc
        detected = ALLOWED_UPLOADS[ext]
    if not detected:
        raise ValueError("El contenido del archivo no coincide con su extensión.")
    lower = data.lower()
    if ext == ".pdf" and any(marker in lower for marker in (b"/javascript", b"/js ", b"/launch", b"/openaction")):
        raise ValueError("El PDF contiene acciones activas no permitidas.")
    scan = MALWARE_SCANNER.scan(filename, data)
    return detected, sha256(data).hexdigest(), f"{scan.status}:{scan.engine}:{scan.detail}"[:1000]


def security_overview():
    con = core.db()
    active = con.execute("SELECT COUNT(*) FROM sessions WHERE revoked=0 AND expires_at>?", (utc_iso(),)).fetchone()[0]
    rows = [dict(x) for x in con.execute(
        """SELECT s.id,s.user_id,u.name,u.role,s.created_at,s.expires_at,s.idle_expires_at,s.last_seen_at,s.ip_address,s.revoked,s.auth_level,s.mfa_verified_at
           FROM sessions s JOIN users u ON u.id=s.user_id ORDER BY s.created_at DESC LIMIT 30"""
    ).fetchall()]
    events = [dict(x) for x in con.execute(
        "SELECT id,user_id,event_type,outcome,ip_address,detail,created_at FROM security_events ORDER BY id DESC LIMIT 40"
    ).fetchall()]
    uploads = [dict(x) for x in con.execute(
        "SELECT id,case_id,name,size_bytes,sha256,detected_type,security_status,uploaded_by,created_at FROM attachments ORDER BY created_at DESC LIMIT 30"
    ).fetchall()]
    con.close()
    return {"active_sessions": active, "sessions": rows, "events": events, "uploads": uploads}


def release_readiness_with_normative(con):
    obj = BATCHES.readiness(con)
    holds = NORMATIVE.product_holds(con)
    for product in obj.get("products", []):
        code = product.get("product_code")
        open_holds = holds.get(code, [])
        check = {
            "key": "normative",
            "label": "Sin alertas normativas abiertas",
            "passed": not open_holds,
            "detail": open_holds,
        }
        product.setdefault("checks", []).append(check)
        product["total_checks"] = len(product["checks"])
        product["passed_checks"] = sum(bool(x.get("passed")) for x in product["checks"])
        product["score"] = round(product["passed_checks"] * 100 / max(1, product["total_checks"]))
        product["ready"] = product["passed_checks"] == product["total_checks"]
        product["normative_holds"] = open_holds
    products = obj.get("products", [])
    obj["metrics"]["ready"] = sum(bool(x.get("ready")) for x in products)
    obj["metrics"]["average_score"] = round(sum(x.get("score", 0) for x in products) / max(1, len(products)))
    obj["metrics"]["normative_holds"] = sum(len(x) for x in holds.values())
    obj["notice"] = "La matriz integra ocho puertas. Una alerta normativa abierta bloquea el release, pero su ausencia no reemplaza las aprobaciones jurídicas, técnicas y comerciales."
    return obj


def current_api_actor(user):
    """Translate the authenticated application actor without trusting request payload roles."""
    role = str((user or {}).get("role") or "").strip()
    if role == "client":
        role = "user"
    return {"id": str((user or {}).get("id") or ""), "role": role}


def api_prefix_match(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def api_generation_action(path, prefix):
    parts = [part for part in str(path or "").split("/") if part]
    prefix_parts = [part for part in prefix.split("/") if part]
    if parts[:len(prefix_parts)] != prefix_parts or len(parts) != len(prefix_parts) + 2:
        return None, None
    return parts[-2], parts[-1]
