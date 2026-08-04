from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import uuid


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PaymentSandboxCenter:
    """Adaptador local que reproduce un flujo de pasarela sin procesar dinero real."""

    PROVIDERS = {
        "sandbox_card": "Tarjeta sandbox",
        "sandbox_pse": "PSE sandbox",
        "sandbox_free": "Continuar sin cobro",
    }

    def __init__(self, signing_key: bytes):
        self.signing_key = signing_key

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS payment_intents(
              id TEXT PRIMARY KEY,
              order_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              provider_reference TEXT NOT NULL UNIQUE,
              idempotency_key TEXT NOT NULL,
              amount INTEGER NOT NULL,
              currency TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(user_id,idempotency_key),
              FOREIGN KEY(order_id) REFERENCES checkout_orders(id),
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_payment_intents_order ON payment_intents(order_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS payment_sandbox_events(
              id TEXT PRIMARY KEY,
              intent_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL,
              signature TEXT NOT NULL,
              valid_signature INTEGER NOT NULL DEFAULT 1,
              actor TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(intent_id) REFERENCES payment_intents(id)
            );
            CREATE INDEX IF NOT EXISTS idx_payment_events_intent ON payment_sandbox_events(intent_id,created_at);
            """
        )

    def _signature(self, payload_json: str) -> str:
        return hmac.new(self.signing_key, payload_json.encode("utf-8"), "sha256").hexdigest()

    @staticmethod
    def _decode(row):
        if not row:
            return None
        out = dict(row)
        if out.get("payload_json"):
            out["payload"] = json.loads(out.pop("payload_json"))
        return out

    def create_intent(self, con, order, user_id: str, provider: str, idempotency_key: str) -> dict:
        if provider not in self.PROVIDERS:
            raise ValueError("Proveedor sandbox no admitido.")
        if not idempotency_key or len(idempotency_key) > 120:
            raise ValueError("Se requiere una clave de idempotencia válida.")
        if order["user_id"] != user_id:
            raise PermissionError("La orden no pertenece al usuario.")
        if order["status"] not in {"Pendiente", "Pago rechazado (sandbox)", "Pago pendiente (sandbox)"}:
            existing = con.execute(
                "SELECT * FROM payment_intents WHERE order_id=? ORDER BY created_at DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if existing:
                return self.intent(con, existing["id"])
            raise ValueError("La orden no admite un nuevo intento de pago.")
        existing = con.execute(
            "SELECT * FROM payment_intents WHERE user_id=? AND idempotency_key=?",
            (user_id, idempotency_key),
        ).fetchone()
        if existing:
            return self.intent(con, existing["id"])
        now = utc_iso()
        intent_id = "PAY-" + uuid.uuid4().hex[:14].upper()
        provider_ref = "SBX-" + uuid.uuid4().hex[:16].upper()
        con.execute(
            """INSERT INTO payment_intents(id,order_id,user_id,provider,provider_reference,
               idempotency_key,amount,currency,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                intent_id,
                order["id"],
                user_id,
                provider,
                provider_ref,
                idempotency_key,
                int(order["total"]),
                order.get("currency") or "COP",
                "created",
                now,
                now,
            ),
        )
        self._event(con, intent_id, "payment.intent.created", {"provider": provider, "amount": int(order["total"]), "currency": order.get("currency") or "COP"}, user_id)
        return self.intent(con, intent_id)

    def _event(self, con, intent_id: str, event_type: str, payload: dict, actor: str) -> dict:
        event_id = "PEV-" + uuid.uuid4().hex[:14].upper()
        body = {
            "event_id": event_id,
            "intent_id": intent_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": utc_iso(),
        }
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        signature = self._signature(raw)
        con.execute(
            """INSERT INTO payment_sandbox_events(id,intent_id,event_type,payload_json,payload_sha256,
               signature,valid_signature,actor,created_at) VALUES(?,?,?,?,?,?,1,?,?)""",
            (event_id, intent_id, event_type, raw, sha256(raw.encode()).hexdigest(), signature, actor, body["created_at"]),
        )
        return {**body, "signature": signature}

    def simulate(self, con, intent_id: str, outcome: str, actor: str) -> dict:
        row = con.execute("SELECT * FROM payment_intents WHERE id=?", (intent_id,)).fetchone()
        if not row:
            raise ValueError("Intento de pago no encontrado.")
        allowed = {"approved", "rejected", "pending"}
        if outcome not in allowed:
            raise ValueError("Resultado sandbox inválido.")
        status_map = {"approved": "succeeded", "rejected": "failed", "pending": "processing"}
        order_status = {
            "approved": "Pagado (sandbox)",
            "rejected": "Pago rechazado (sandbox)",
            "pending": "Pago pendiente (sandbox)",
        }[outcome]
        now = utc_iso()
        event = self._event(
            con,
            intent_id,
            f"payment.intent.{status_map[outcome]}",
            {"outcome": outcome, "provider_reference": row["provider_reference"], "amount": row["amount"]},
            actor,
        )
        con.execute("UPDATE payment_intents SET status=?,updated_at=? WHERE id=?", (status_map[outcome], now, intent_id))
        receipt = "RCPT-SBX-" + uuid.uuid4().hex[:10].upper() if outcome == "approved" else None
        con.execute(
            """UPDATE checkout_orders SET status=?,payment_method=?,receipt_number=COALESCE(?,receipt_number),
               updated_at=? WHERE id=?""",
            (order_status, self.PROVIDERS[row["provider"]], receipt, now, row["order_id"]),
        )
        result = self.intent(con, intent_id)
        result["event"] = event
        result["receipt_number"] = receipt
        return result

    def intent(self, con, intent_id: str) -> dict | None:
        row = con.execute("SELECT * FROM payment_intents WHERE id=?", (intent_id,)).fetchone()
        if not row:
            return None
        out = dict(row)
        events = con.execute(
            "SELECT * FROM payment_sandbox_events WHERE intent_id=? ORDER BY created_at,id",
            (intent_id,),
        ).fetchall()
        out["provider_label"] = self.PROVIDERS.get(out["provider"], out["provider"])
        out["events"] = [self._decode(x) for x in events]
        return out

    def order_intents(self, con, order_id: str, user_id: str | None = None) -> list[dict]:
        if user_id:
            rows = con.execute(
                "SELECT id FROM payment_intents WHERE order_id=? AND user_id=? ORDER BY created_at DESC",
                (order_id, user_id),
            ).fetchall()
        else:
            rows = con.execute("SELECT id FROM payment_intents WHERE order_id=? ORDER BY created_at DESC", (order_id,)).fetchall()
        return [self.intent(con, row["id"]) for row in rows]

    def verify_events(self, con, intent_id: str) -> dict:
        rows = con.execute("SELECT * FROM payment_sandbox_events WHERE intent_id=?", (intent_id,)).fetchall()
        errors = []
        for row in rows:
            raw = row["payload_json"]
            if sha256(raw.encode()).hexdigest() != row["payload_sha256"] or not hmac.compare_digest(self._signature(raw), row["signature"]):
                errors.append(row["id"])
        return {"checked": len(rows), "valid": len(rows) - len(errors), "errors": errors}
