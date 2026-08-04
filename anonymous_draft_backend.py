from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import secrets
import uuid


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def future_iso(days: int = 14) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


class AnonymousDraftCenter:
    """Continuidad anónima cifrada mediante un código de recuperación.

    El servidor nunca almacena el código en texto claro. Las respuestas se cifran
    con la llave local de la infraestructura. El código puede transferirse una sola
    vez a una cuenta autenticada y expira por defecto a los 14 días.
    """

    def __init__(self, crypto, products, self_service, retention_days: int = 14):
        self.crypto = crypto
        self.products = {p["code"]: p for p in products}
        self.self_service = self_service
        self.retention_days = max(1, int(retention_days))

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS anonymous_service_drafts(
              id TEXT PRIMARY KEY,
              token_hash TEXT NOT NULL UNIQUE,
              product_code TEXT NOT NULL,
              payload_encrypted BLOB NOT NULL,
              payload_sha256 TEXT NOT NULL,
              current_step INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'Activo',
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              transferred_user_id TEXT,
              transferred_at TEXT,
              FOREIGN KEY(transferred_user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_anon_drafts_expiry
              ON anonymous_service_drafts(status,expires_at);
            """
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return sha256((token or "").strip().upper().encode("utf-8")).hexdigest()

    @staticmethod
    def _format_token(raw: str) -> str:
        compact = "".join(ch for ch in raw.upper() if ch.isalnum())[:20]
        return "-".join(compact[i:i + 5] for i in range(0, len(compact), 5))

    def _new_token(self) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return self._format_token("".join(secrets.choice(alphabet) for _ in range(20)))

    @staticmethod
    def _aad(draft_id: str, product_code: str) -> bytes:
        return f"anonymous-draft:{draft_id}:{product_code}".encode("utf-8")

    def _encrypt(self, draft_id: str, product_code: str, payload: dict) -> tuple[bytes, str]:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return self.crypto.encrypt(raw, self._aad(draft_id, product_code)), sha256(raw).hexdigest()

    def _decrypt(self, row) -> dict:
        raw, aad = self.crypto.decrypt(bytes(row["payload_encrypted"]))
        expected_aad = self._aad(row["id"], row["product_code"])
        if aad != expected_aad:
            raise ValueError("La continuidad cifrada no corresponde al formulario solicitado.")
        if sha256(raw).hexdigest() != row["payload_sha256"]:
            raise ValueError("La continuidad no supera la verificación de integridad.")
        return json.loads(raw.decode("utf-8"))

    def purge_expired(self, con) -> int:
        cur = con.execute(
            "UPDATE anonymous_service_drafts SET status='Expirado',updated_at=? WHERE status='Activo' AND expires_at<=?",
            (utc_iso(), utc_iso()),
        )
        return int(cur.rowcount or 0)

    def save(self, con, product_code: str, answers: dict, current_step: int = 0, token: str | None = None, result=None) -> dict:
        if product_code not in self.products:
            raise ValueError("Producto no encontrado.")
        self.purge_expired(con)
        row = None
        if token:
            row = con.execute(
                "SELECT * FROM anonymous_service_drafts WHERE token_hash=? AND status='Activo'",
                (self._hash_token(token),),
            ).fetchone()
            if not row:
                raise ValueError("El código no existe, expiró o ya fue transferido.")
            if row["product_code"] != product_code:
                raise ValueError("El código corresponde a otra solución jurídica.")
            draft_id = row["id"]
            recovery_code = self._format_token(token)
        else:
            draft_id = "ADR-" + uuid.uuid4().hex[:14].upper()
            recovery_code = self._new_token()
        payload = {
            "answers": answers or {},
            "result": result,
            "privacy": "Continuidad anónima cifrada. No sustituye la creación de una cuenta ni un expediente.",
        }
        encrypted, digest = self._encrypt(draft_id, product_code, payload)
        now = utc_iso()
        expires = row["expires_at"] if row else future_iso(self.retention_days)
        con.execute(
            """INSERT INTO anonymous_service_drafts(
                 id,token_hash,product_code,payload_encrypted,payload_sha256,current_step,status,
                 expires_at,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,'Activo',?,?,?)
               ON CONFLICT(id) DO UPDATE SET payload_encrypted=excluded.payload_encrypted,
                 payload_sha256=excluded.payload_sha256,current_step=excluded.current_step,
                 updated_at=excluded.updated_at""",
            (
                draft_id,
                self._hash_token(recovery_code),
                product_code,
                encrypted,
                digest,
                max(0, int(current_step or 0)),
                expires,
                row["created_at"] if row else now,
                now,
            ),
        )
        return {
            "id": draft_id,
            "recovery_code": recovery_code,
            "product_code": product_code,
            "current_step": max(0, int(current_step or 0)),
            "expires_at": expires,
            "status": "Activo",
            "notice": "Guarda este código. LegalAIZ.it no puede mostrarlo de nuevo ni recuperar el formulario sin él.",
        }

    def recover(self, con, token: str) -> dict:
        self.purge_expired(con)
        row = con.execute(
            "SELECT * FROM anonymous_service_drafts WHERE token_hash=? AND status='Activo'",
            (self._hash_token(token),),
        ).fetchone()
        if not row:
            raise ValueError("El código no existe, expiró o ya fue transferido.")
        payload = self._decrypt(row)
        return {
            "id": row["id"],
            "product_code": row["product_code"],
            "answers": payload.get("answers") or {},
            "result": payload.get("result"),
            "current_step": int(row["current_step"] or 0),
            "expires_at": row["expires_at"],
            "status": row["status"],
        }

    def transfer(self, con, token: str, user_id: str) -> dict:
        draft = self.recover(con, token)
        saved = self.self_service.save_draft(
            con,
            user_id,
            draft["product_code"],
            draft["answers"],
            current_step=draft["current_step"],
            result=draft.get("result"),
        )
        now = utc_iso()
        cur = con.execute(
            """UPDATE anonymous_service_drafts SET status='Transferido',transferred_user_id=?,
               transferred_at=?,updated_at=? WHERE id=? AND status='Activo'""",
            (user_id, now, now, draft["id"]),
        )
        if not cur.rowcount:
            raise ValueError("La continuidad ya fue transferida o dejó de estar activa.")
        return {
            "ok": True,
            "anonymous_draft_id": draft["id"],
            "draft": saved,
            "notice": "El formulario quedó guardado en tu cuenta y el código anónimo fue invalidado.",
        }

    def summary(self, con) -> dict:
        self.purge_expired(con)
        rows = con.execute(
            "SELECT status,COUNT(*) total FROM anonymous_service_drafts GROUP BY status"
        ).fetchall()
        counts = {row["status"]: row["total"] for row in rows}
        return {
            "active": int(counts.get("Activo", 0)),
            "transferred": int(counts.get("Transferido", 0)),
            "expired": int(counts.get("Expirado", 0)),
            "retention_days": self.retention_days,
        }
