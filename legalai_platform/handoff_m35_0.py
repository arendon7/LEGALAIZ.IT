from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from legalai_platform.recommendation_m34_4 import RecommendationStore


SCHEMA_VERSION = "35.0.0"


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class HandoffConflictError(ValueError):
    pass


class HandoffStateError(ValueError):
    pass


class AccountHandoffStore(RecommendationStore):
    """One-time M34 recommendation ownership transfer into authenticated fulfillment.

    The encrypted M34 payload remains the source of detailed intake facts. The
    authenticated draft receives only non-sensitive linkage metadata so claiming an
    intake cannot downgrade the protection of the original narrative or fact values.
    """

    def __init__(self, crypto, self_service, retention_hours: int = 72):
        super().__init__(crypto, retention_hours=retention_hours)
        self.self_service = self_service

    def create_schema(self, con) -> None:
        super().create_schema(con)
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m35_intake_handoffs(
              id TEXT PRIMARY KEY,
              intake_id TEXT NOT NULL UNIQUE,
              user_id TEXT NOT NULL,
              decision_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              draft_id TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'CLAIMED'
                CHECK(status IN ('CLAIMED','FULFILLMENT_STARTED','ORDER_CREATED','CASE_CREATED','CANCELLED')),
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(intake_id) REFERENCES intelligent_intake_sessions(id),
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m35_handoffs_user_created
              ON m35_intake_handoffs(user_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_m35_handoffs_draft
              ON m35_intake_handoffs(draft_id);
            """
        )

    @staticmethod
    def _user_row(con, user_id: str):
        return con.execute(
            "SELECT id,role,active FROM users WHERE id=?",
            (str(user_id or ""),),
        ).fetchone()

    def _row_for_claim(self, con, token: str):
        normalized = self._normalize_token(token)
        if len(normalized) != 24:
            raise HandoffStateError("El código de continuidad no tiene un formato válido.")
        self.purge_expired(con)
        row = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE token_hash=?",
            (self._hash_token(normalized),),
        ).fetchone()
        if not row:
            raise HandoffStateError("El código no existe, expiró o ya no está disponible.")
        return row

    @staticmethod
    def _current_recommendation(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        state = payload.get("m34_4") or {}
        decision_id = str(state.get("current_decision_id") or "")
        decisions = state.get("decisions") or []
        record = next(
            (
                item for item in decisions
                if isinstance(item, dict) and str(item.get("decision_id") or "") == decision_id
            ),
            None,
        )
        if not record:
            raise HandoffStateError("El diagnóstico no tiene una recomendación vigente para transferir.")
        result = record.get("result") or {}
        if result.get("outcome") != "RECOMMEND":
            raise HandoffStateError("El diagnóstico actual no permite iniciar fulfillment automático.")
        primary = result.get("primary") or {}
        product_code = str(primary.get("product_code") or "")
        if not product_code:
            raise HandoffStateError("La recomendación vigente no identifica una solución transferible.")
        return record, primary

    @staticmethod
    def _public_handoff(row, *, idempotent: bool = False) -> dict[str, Any]:
        return {
            "ok": True,
            "handoff_id": row["id"],
            "intake_id": row["intake_id"],
            "decision_id": row["decision_id"],
            "product_code": row["product_code"],
            "draft_id": row["draft_id"],
            "status": row["status"],
            "idempotent": bool(idempotent),
            "next_action": "CONTINUE_FULFILLMENT",
            "next_route": f"/nuevo/{row['product_code']}",
            "notice": (
                "Tu diagnóstico quedó vinculado a tu cuenta. El formulario de fulfillment "
                "completará la información necesaria antes de checkout y expediente."
            ),
        }

    def handoff_for_intake(self, con, intake_id: str, user_id: str) -> dict[str, Any] | None:
        row = con.execute(
            "SELECT * FROM m35_intake_handoffs WHERE intake_id=? AND user_id=?",
            (str(intake_id or ""), str(user_id or "")),
        ).fetchone()
        return self._public_handoff(row, idempotent=True) if row else None

    def claim(self, con, token: str, user_id: str) -> dict[str, Any]:
        self.create_schema(con)
        user = self._user_row(con, user_id)
        if not user or not bool(user["active"]):
            raise PermissionError("La cuenta no está activa para reclamar este diagnóstico.")
        if user["role"] != "client":
            raise PermissionError("Sólo una cuenta cliente puede reclamar un diagnóstico anónimo.")

        row = self._row_for_claim(con, token)
        existing = con.execute(
            "SELECT * FROM m35_intake_handoffs WHERE intake_id=?",
            (row["id"],),
        ).fetchone()
        if existing:
            if existing["user_id"] == user_id:
                return self._public_handoff(existing, idempotent=True)
            raise HandoffConflictError("El diagnóstico ya fue transferido a otra cuenta.")

        if row["status"] != "Activo":
            raise HandoffStateError("El código no existe, expiró o ya no está disponible.")
        if row["transferred_user_id"]:
            raise HandoffConflictError("El diagnóstico ya fue transferido.")

        payload = self._decrypt(row)
        decision, primary = self._current_recommendation(payload)
        product_code = str(primary["product_code"])
        if product_code not in self.self_service.products:
            raise HandoffStateError("La solución recomendada ya no está disponible para fulfillment.")

        existing_draft = self.self_service.get_product_draft(con, user_id, product_code)
        if existing_draft:
            raise HandoffConflictError(
                "Ya tienes un formulario activo de esta solución. Continúalo o elimínalo antes de transferir otro diagnóstico."
            )

        handoff_id = "HOF-" + uuid.uuid4().hex[:16].upper()
        now = utc_iso()
        minimal_result = {
            "source": "m35_m34_handoff",
            "handoff_schema_version": SCHEMA_VERSION,
            "intake_id": row["id"],
            "decision_id": decision["decision_id"],
            "recommended_product_code": product_code,
            "eligibility": primary.get("eligibility"),
            "review_requirement": primary.get("review_requirement"),
            "fulfillment_status": "NOT_STARTED",
            "triage_reuse_status": "PENDING_SAFE_MAPPING",
            "notice": (
                "El triage M34 orienta la solución, pero no reemplaza las preguntas, soportes "
                "ni validaciones necesarias para generar el documento o expediente."
            ),
        }
        draft = self.self_service.save_draft(
            con,
            user_id,
            product_code,
            {},
            current_step=0,
            title=str(primary.get("public_title") or product_code),
            result=minimal_result,
        )

        con.execute(
            """INSERT INTO m35_intake_handoffs(
                 id,intake_id,user_id,decision_id,product_code,draft_id,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,'CLAIMED',?,?)""",
            (
                handoff_id,
                row["id"],
                user_id,
                decision["decision_id"],
                product_code,
                draft["id"],
                now,
                now,
            ),
        )

        payload["m35_0"] = {
            "schema_version": SCHEMA_VERSION,
            "handoff_id": handoff_id,
            "user_id": user_id,
            "decision_id": decision["decision_id"],
            "product_code": product_code,
            "draft_id": draft["id"],
            "claimed_at": now,
        }
        encrypted, digest = self._encrypt(row["id"], payload)
        cur = con.execute(
            """UPDATE intelligent_intake_sessions
               SET payload_encrypted=?,payload_sha256=?,status='Transferido',
                   stage='TRANSFERRED_TO_ACCOUNT',transferred_user_id=?,transferred_at=?,updated_at=?
               WHERE id=? AND status='Activo' AND transferred_user_id IS NULL""",
            (encrypted, digest, user_id, now, now, row["id"]),
        )
        if not cur.rowcount:
            raise HandoffConflictError("El diagnóstico cambió de estado durante la transferencia.")

        handoff = con.execute(
            "SELECT * FROM m35_intake_handoffs WHERE id=?",
            (handoff_id,),
        ).fetchone()
        return self._public_handoff(handoff, idempotent=False)


__all__ = [
    "AccountHandoffStore",
    "HandoffConflictError",
    "HandoffStateError",
    "SCHEMA_VERSION",
]
