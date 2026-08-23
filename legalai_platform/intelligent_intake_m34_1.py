from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import secrets
import uuid


MIN_PROBLEM_CHARS = 20
MAX_PROBLEM_CHARS = 8000


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def future_iso(hours: int = 72) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


class IntelligentIntakeStore:
    """Persistencia cifrada para el intake M34 anterior a la selección de producto.

    El intake no exige autenticación ni product_code. El código de continuidad funciona
    como secreto bearer: sólo se almacena su hash SHA-256 y el relato jurídico queda
    cifrado con la misma infraestructura criptográfica usada por LegalAIZ.it.

    M34.1 sólo conserva el relato y el estado del journey. No realiza inferencias IA.
    """

    def __init__(self, crypto, retention_hours: int = 72):
        self.crypto = crypto
        self.retention_hours = max(1, int(retention_hours))

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS intelligent_intake_sessions(
              id TEXT PRIMARY KEY,
              token_hash TEXT NOT NULL UNIQUE,
              payload_encrypted BLOB NOT NULL,
              payload_sha256 TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'Activo',
              stage TEXT NOT NULL DEFAULT 'PROBLEM_SUBMITTED',
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              transferred_user_id TEXT,
              transferred_at TEXT,
              FOREIGN KEY(transferred_user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_intelligent_intake_active
              ON intelligent_intake_sessions(status,expires_at);
            """
        )

    @staticmethod
    def _normalize_token(token: str) -> str:
        return "".join(ch for ch in str(token or "").strip().upper() if ch.isalnum())

    @classmethod
    def _hash_token(cls, token: str) -> str:
        return sha256(cls._normalize_token(token).encode("utf-8")).hexdigest()

    @staticmethod
    def _format_token(raw: str) -> str:
        compact = "".join(ch for ch in raw.upper() if ch.isalnum())[:24]
        return "-".join(compact[i:i + 6] for i in range(0, len(compact), 6))

    def _new_token(self) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return self._format_token("".join(secrets.choice(alphabet) for _ in range(24)))

    @staticmethod
    def _aad(session_id: str) -> bytes:
        return f"m34-intelligent-intake:{session_id}".encode("utf-8")

    def _encrypt(self, session_id: str, payload: dict) -> tuple[bytes, str]:
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        encrypted = self.crypto.encrypt(raw, self._aad(session_id))
        return encrypted, sha256(raw).hexdigest()

    def _decrypt(self, row) -> dict:
        raw, aad = self.crypto.decrypt(bytes(row["payload_encrypted"]))
        if aad != self._aad(row["id"]):
            raise ValueError("La sesión cifrada no corresponde al intake solicitado.")
        if sha256(raw).hexdigest() != row["payload_sha256"]:
            raise ValueError("La sesión no supera la verificación de integridad.")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("La sesión cifrada tiene un formato inválido.")
        return payload

    @staticmethod
    def normalize_problem(problem_statement: str) -> str:
        problem = " ".join(str(problem_statement or "").strip().split())
        if len(problem) < MIN_PROBLEM_CHARS:
            raise ValueError(
                "Cuéntanos un poco más para poder organizar tu situación."
            )
        if len(problem) > MAX_PROBLEM_CHARS:
            raise ValueError(
                f"La descripción puede tener máximo {MAX_PROBLEM_CHARS} caracteres."
            )
        return problem

    def purge_expired(self, con) -> int:
        now = utc_iso()
        cur = con.execute(
            """UPDATE intelligent_intake_sessions
               SET status='Expirado',updated_at=?
               WHERE status='Activo' AND expires_at<=?""",
            (now, now),
        )
        return int(cur.rowcount or 0)

    def create(self, con, problem_statement: str) -> dict:
        self.purge_expired(con)
        problem = self.normalize_problem(problem_statement)
        session_id = "INT-" + uuid.uuid4().hex[:16].upper()
        recovery_code = self._new_token()
        now = utc_iso()
        expires = future_iso(self.retention_hours)
        payload = {
            "problem_statement": problem,
            "facts": [],
            "contradictions": [],
            "risk_signals": [],
            "candidate_products": [],
            "ai_processing_status": "NOT_STARTED",
            "privacy": "Relato de intake cifrado. M34.1 no ejecuta inferencias de IA.",
        }
        encrypted, digest = self._encrypt(session_id, payload)
        con.execute(
            """INSERT INTO intelligent_intake_sessions(
                 id,token_hash,payload_encrypted,payload_sha256,status,stage,
                 expires_at,created_at,updated_at
               ) VALUES(?,?,?,?,'Activo','PROBLEM_SUBMITTED',?,?,?)""",
            (
                session_id,
                self._hash_token(recovery_code),
                encrypted,
                digest,
                expires,
                now,
                now,
            ),
        )
        return {
            "id": session_id,
            "recovery_code": recovery_code,
            "stage": "PROBLEM_SUBMITTED",
            "status": "Activo",
            "expires_at": expires,
            "problem_statement": problem,
            "ai_processing_status": "NOT_STARTED",
            "notice": (
                "Guarda este código si quieres retomar el diagnóstico. "
                "LegalAIZ.it no almacena el código en texto claro."
            ),
        }

    def recover(self, con, token: str) -> dict:
        normalized = self._normalize_token(token)
        if len(normalized) != 24:
            raise ValueError("El código de continuidad no tiene un formato válido.")
        self.purge_expired(con)
        row = con.execute(
            """SELECT * FROM intelligent_intake_sessions
               WHERE token_hash=? AND status='Activo'""",
            (self._hash_token(normalized),),
        ).fetchone()
        if not row:
            raise ValueError("El código no existe, expiró o ya no está activo.")
        payload = self._decrypt(row)
        return {
            "id": row["id"],
            "stage": row["stage"],
            "status": row["status"],
            "expires_at": row["expires_at"],
            "problem_statement": payload.get("problem_statement") or "",
            "facts": payload.get("facts") or [],
            "contradictions": payload.get("contradictions") or [],
            "risk_signals": payload.get("risk_signals") or [],
            "candidate_products": payload.get("candidate_products") or [],
            "ai_processing_status": payload.get("ai_processing_status") or "NOT_STARTED",
        }

    def update_problem(self, con, token: str, problem_statement: str) -> dict:
        current = self.recover(con, token)
        problem = self.normalize_problem(problem_statement)
        row = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=? AND status='Activo'",
            (current["id"],),
        ).fetchone()
        if not row:
            raise ValueError("La sesión ya no está activa.")
        payload = self._decrypt(row)
        payload.update(
            {
                "problem_statement": problem,
                "facts": [],
                "contradictions": [],
                "risk_signals": [],
                "candidate_products": [],
                "ai_processing_status": "NOT_STARTED",
            }
        )
        encrypted, digest = self._encrypt(row["id"], payload)
        now = utc_iso()
        con.execute(
            """UPDATE intelligent_intake_sessions
               SET payload_encrypted=?,payload_sha256=?,stage='PROBLEM_SUBMITTED',updated_at=?
               WHERE id=? AND status='Activo'""",
            (encrypted, digest, now, row["id"]),
        )
        return {
            **current,
            "problem_statement": problem,
            "stage": "PROBLEM_SUBMITTED",
            "ai_processing_status": "NOT_STARTED",
        }

    def summary(self, con) -> dict:
        self.purge_expired(con)
        rows = con.execute(
            "SELECT status,COUNT(*) total FROM intelligent_intake_sessions GROUP BY status"
        ).fetchall()
        counts = {row["status"]: int(row["total"] or 0) for row in rows}
        return {
            "active": counts.get("Activo", 0),
            "expired": counts.get("Expirado", 0),
            "transferred": counts.get("Transferido", 0),
            "retention_hours": self.retention_hours,
        }


__all__ = [
    "IntelligentIntakeStore",
    "MAX_PROBLEM_CHARS",
    "MIN_PROBLEM_CHARS",
]
