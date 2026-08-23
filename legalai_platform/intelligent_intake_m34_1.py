from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import secrets
import uuid

from legalai_platform.m34_intelligent_journey import (
    fact_is_decision_usable,
    validate_legal_fact,
)


MIN_PROBLEM_CHARS = 20
MAX_PROBLEM_CHARS = 8000
MAX_FACT_DECISIONS = 64
MAX_USER_CORRECTION_CHARS = 2000
MAX_USER_LIST_ITEMS = 20


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def future_iso(hours: int = 72) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


class IntelligentIntakeStore:
    """Persistencia cifrada para el journey M34 previo a la selección de producto.

    El código de continuidad funciona como secreto bearer: sólo se almacena su hash
    SHA-256 y el relato jurídico, hechos candidatos y decisiones permanecen dentro
    del payload cifrado.

    M34.2 permite almacenar hechos estructurados y decisiones humanas sin convertir
    silenciosamente una inferencia de máquina en un hecho confirmado.
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
            raise ValueError("Cuéntanos un poco más para poder organizar tu situación.")
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

    def _active_row(self, con, token: str):
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
        return row

    def _write_payload(self, con, row, payload: dict, stage: str) -> None:
        encrypted, digest = self._encrypt(row["id"], payload)
        con.execute(
            """UPDATE intelligent_intake_sessions
               SET payload_encrypted=?,payload_sha256=?,stage=?,updated_at=?
               WHERE id=? AND status='Activo'""",
            (encrypted, digest, stage, utc_iso(), row["id"]),
        )

    @staticmethod
    def _public_state(row, payload: dict) -> dict:
        facts = payload.get("facts") or []
        confirmed = [fact for fact in facts if fact_is_decision_usable(fact)]
        pending = [
            fact
            for fact in facts
            if fact.get("provenance") == "AI_INFERRED"
            and fact.get("confirmation_status") == "UNCONFIRMED"
        ]
        return {
            "id": row["id"],
            "stage": row["stage"],
            "status": row["status"],
            "expires_at": row["expires_at"],
            "problem_statement": payload.get("problem_statement") or "",
            "facts": facts,
            "confirmed_facts": confirmed,
            "pending_fact_count": len(pending),
            "contradictions": payload.get("contradictions") or [],
            "risk_signals": payload.get("risk_signals") or [],
            "candidate_products": payload.get("candidate_products") or [],
            "ai_processing_status": payload.get("ai_processing_status") or "NOT_STARTED",
            "extraction_provider": payload.get("extraction_provider"),
            "extraction_schema_version": payload.get("extraction_schema_version"),
            "fact_review_completed_at": payload.get("fact_review_completed_at"),
        }

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
            "extraction_provider": None,
            "extraction_schema_version": None,
            "fact_review_completed_at": None,
            "privacy": "Relato y hechos de intake cifrados; no constituyen una conclusión jurídica.",
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
        row = self._active_row(con, token)
        payload = self._decrypt(row)
        return self._public_state(row, payload)

    def update_problem(self, con, token: str, problem_statement: str) -> dict:
        row = self._active_row(con, token)
        problem = self.normalize_problem(problem_statement)
        payload = self._decrypt(row)
        payload.update(
            {
                "problem_statement": problem,
                "facts": [],
                "contradictions": [],
                "risk_signals": [],
                "candidate_products": [],
                "ai_processing_status": "NOT_STARTED",
                "extraction_provider": None,
                "extraction_schema_version": None,
                "fact_review_completed_at": None,
            }
        )
        self._write_payload(con, row, payload, "PROBLEM_SUBMITTED")
        refreshed = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=?",
            (row["id"],),
        ).fetchone()
        return self._public_state(refreshed, payload)

    def apply_extraction(self, con, token: str, extraction: dict) -> dict:
        row = self._active_row(con, token)
        payload = self._decrypt(row)
        current_facts = payload.get("facts") or []
        if any(fact_is_decision_usable(fact) for fact in current_facts):
            raise ValueError(
                "Ya confirmaste datos de este relato. Para volver a analizarlo, edita primero la descripción."
            )

        facts = extraction.get("facts") or []
        if not isinstance(facts, list):
            raise ValueError("La extracción no contiene una lista válida de hechos.")
        for fact in facts:
            errors = validate_legal_fact(fact)
            if errors:
                raise ValueError(f"La extracción contiene un hecho inválido: {'; '.join(errors)}")
            if fact.get("provenance") != "AI_INFERRED" or fact.get("confirmation_status") != "UNCONFIRMED":
                raise ValueError("Los hechos automáticos deben ingresar como AI_INFERRED y UNCONFIRMED.")

        provider = extraction.get("provider") or {}
        if not isinstance(provider, dict) or not provider.get("id"):
            raise ValueError("La extracción no identifica el proveedor que estructuró los hechos.")

        payload.update(
            {
                "facts": facts,
                "contradictions": extraction.get("contradictions") or [],
                "risk_signals": extraction.get("risk_signals") or [],
                "candidate_products": extraction.get("candidate_products") or [],
                "ai_processing_status": (
                    "AI_EXTRACTION_COMPLETE"
                    if provider.get("ai_enabled")
                    else "LOCAL_EXTRACTION_COMPLETE"
                ),
                "extraction_provider": provider,
                "extraction_schema_version": extraction.get("schema_version"),
                "fact_review_completed_at": None,
            }
        )
        stage = "FACTS_PENDING_CONFIRMATION" if facts else "FACTS_NOT_FOUND"
        self._write_payload(con, row, payload, stage)
        refreshed = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=?",
            (row["id"],),
        ).fetchone()
        return {
            **self._public_state(refreshed, payload),
            "requires_user_confirmation": bool(facts),
            "next_action": extraction.get("next_action") or ("CONFIRM_FACTS" if facts else "ASK_MORE"),
            "notice": extraction.get("notice"),
        }

    @staticmethod
    def _normalize_user_correction(candidate: dict, raw_value):
        original = candidate.get("value")
        if isinstance(original, list):
            if isinstance(raw_value, list):
                items = [str(item).strip() for item in raw_value]
            else:
                items = [item.strip() for item in str(raw_value or "").split(",")]
            items = [item for item in items if item]
            if not items or len(items) > MAX_USER_LIST_ITEMS:
                raise ValueError("La corrección de la lista no tiene un formato válido.")
            if any(len(item) > 200 for item in items):
                raise ValueError("Uno de los valores corregidos es demasiado largo.")
            return items, items

        if isinstance(original, dict):
            if "amount_cop" in original:
                amount_source = raw_value.get("amount_cop") if isinstance(raw_value, dict) else raw_value
                digits = "".join(ch for ch in str(amount_source or "") if ch.isdigit())
                if not digits:
                    raise ValueError("La corrección del valor monetario debe contener una cifra.")
                amount = int(digits)
                if amount <= 0 or amount > 10**15:
                    raise ValueError("La corrección del valor monetario está fuera del rango permitido.")
                corrected = dict(original)
                corrected["amount_cop"] = amount
                normalized = dict(candidate.get("normalized_value") or {})
                normalized.update({"amount_cop": amount, "currency": "COP"})
                return corrected, normalized
            if not isinstance(raw_value, dict):
                raise ValueError("Este dato estructurado debe conservar su formato original.")
            serialized = json.dumps(raw_value, ensure_ascii=False, sort_keys=True)
            if len(serialized) > MAX_USER_CORRECTION_CHARS:
                raise ValueError("La corrección estructurada es demasiado extensa.")
            return raw_value, raw_value

        if isinstance(original, bool):
            if isinstance(raw_value, bool):
                return raw_value, raw_value
            folded = str(raw_value or "").strip().lower()
            if folded in {"si", "sí", "true", "1"}:
                return True, True
            if folded in {"no", "false", "0"}:
                return False, False
            raise ValueError("La corrección debe indicar sí o no.")

        if isinstance(original, (int, float)) and not isinstance(original, bool):
            try:
                number = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("La corrección debe ser numérica.") from exc
            if abs(number) > 10**15:
                raise ValueError("La corrección numérica está fuera del rango permitido.")
            value = int(number) if isinstance(original, int) and number.is_integer() else number
            return value, value

        corrected = " ".join(str(raw_value or "").strip().split())
        if not corrected:
            raise ValueError("La corrección no puede quedar vacía.")
        if len(corrected) > MAX_USER_CORRECTION_CHARS:
            raise ValueError("La corrección es demasiado extensa.")
        return corrected, corrected

    @staticmethod
    def _confirmed_fact(candidate: dict, value, normalized_value, action: str) -> dict:
        now = utc_iso()
        fact = {
            "fact_id": "fact_user_" + uuid.uuid4().hex[:16],
            "fact_type": candidate["fact_type"],
            "value": value,
            "normalized_value": normalized_value,
            "provenance": "USER_CONFIRMED",
            "confirmation_status": "CONFIRMED_BY_USER",
            "criticality": candidate.get("criticality") or "MEDIUM",
            "source_reference": candidate["fact_id"],
            "evidence_ids": list(candidate.get("evidence_ids") or []),
            "extraction_confidence": None,
            "legal_relevance": candidate.get("legal_relevance"),
            "created_at": now,
            "updated_at": now,
            "notes": (
                "Hecho confirmado por el usuario a partir de un candidato estructurado."
                if action == "CONFIRM"
                else "Hecho corregido y confirmado por el usuario; sustituye el candidato estructurado."
            ),
        }
        errors = validate_legal_fact(fact)
        if errors:
            raise ValueError(f"No fue posible crear el hecho confirmado: {'; '.join(errors)}")
        return fact

    def confirm_fact_decisions(self, con, token: str, decisions: list[dict]) -> dict:
        if not isinstance(decisions, list) or not decisions:
            raise ValueError("Debes revisar al menos un dato antes de continuar.")
        if len(decisions) > MAX_FACT_DECISIONS:
            raise ValueError("La cantidad de decisiones de hechos excede el límite permitido.")

        row = self._active_row(con, token)
        payload = self._decrypt(row)
        facts = list(payload.get("facts") or [])
        candidates = {
            str(fact.get("fact_id")): fact
            for fact in facts
            if fact.get("provenance") == "AI_INFERRED"
        }
        if not candidates:
            raise ValueError("No hay hechos candidatos pendientes de revisión.")

        seen: set[str] = set()
        new_confirmed: list[dict] = []
        now = utc_iso()
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError("La decisión de un hecho tiene un formato inválido.")
            fact_id = str(decision.get("fact_id") or "")
            action = str(decision.get("action") or "").upper()
            if fact_id in seen:
                raise ValueError(f"El hecho {fact_id} fue decidido más de una vez.")
            seen.add(fact_id)
            candidate = candidates.get(fact_id)
            if not candidate:
                raise ValueError("Uno de los hechos ya no está disponible para revisión.")
            if candidate.get("confirmation_status") != "UNCONFIRMED":
                raise ValueError("Uno de los hechos ya fue revisado previamente.")
            if action not in {"CONFIRM", "EDIT", "DISPUTE"}:
                raise ValueError("Acción de revisión no soportada.")

            if action == "DISPUTE":
                candidate["confirmation_status"] = "DISPUTED"
                candidate["updated_at"] = now
                candidate["notes"] = "El usuario indicó que este candidato no corresponde a los hechos."
                continue

            if action == "EDIT":
                if "value" not in decision:
                    raise ValueError("La corrección requiere un nuevo valor.")
                value, normalized_value = self._normalize_user_correction(candidate, decision.get("value"))
            else:
                value = candidate.get("value")
                normalized_value = candidate.get("normalized_value", value)

            candidate["confirmation_status"] = "SUPERSEDED"
            candidate["updated_at"] = now
            new_confirmed.append(
                self._confirmed_fact(candidate, value, normalized_value, action)
            )

        facts.extend(new_confirmed)
        remaining = [
            fact
            for fact in facts
            if fact.get("provenance") == "AI_INFERRED"
            and fact.get("confirmation_status") == "UNCONFIRMED"
        ]
        review_complete = not remaining
        payload["facts"] = facts
        payload["fact_review_completed_at"] = now if review_complete else None
        stage = "FACTS_REVIEWED" if review_complete else "FACTS_PENDING_CONFIRMATION"
        self._write_payload(con, row, payload, stage)
        refreshed = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=?",
            (row["id"],),
        ).fetchone()
        return {
            **self._public_state(refreshed, payload),
            "review_complete": review_complete,
            "new_confirmed_fact_ids": [fact["fact_id"] for fact in new_confirmed],
            "notice": (
                "Los datos confirmados ya tienen una procedencia separada del candidato automático. "
                "Aún no constituyen una recomendación jurídica."
            ),
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
    "MAX_FACT_DECISIONS",
    "MAX_PROBLEM_CHARS",
    "MIN_PROBLEM_CHARS",
]
