from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SelfServiceCenter:
    """Persistencia de borradores y checkout demostrativo.

    El checkout no procesa dinero real. Su propósito es validar el flujo comercial,
    conservar trazabilidad y separar claramente documento autoservicio de revisión
    profesional opcional u obligatoria.
    """

    def __init__(self, products, portal):
        self.products = {p["code"]: p for p in products}
        self.portal = portal

    def create_schema(self, con):
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS service_drafts(
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              title TEXT NOT NULL,
              answers TEXT NOT NULL,
              result TEXT,
              current_step INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'En progreso',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(user_id, product_code),
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_service_drafts_user_updated
              ON service_drafts(user_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS checkout_orders(
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              case_id TEXT,
              service_mode TEXT NOT NULL,
              review_selected INTEGER NOT NULL DEFAULT 0,
              document_price INTEGER NOT NULL,
              review_price INTEGER NOT NULL DEFAULT 0,
              total INTEGER NOT NULL,
              currency TEXT NOT NULL DEFAULT 'COP',
              status TEXT NOT NULL DEFAULT 'Pendiente',
              payment_method TEXT,
              receipt_number TEXT,
              detail TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_checkout_user_created
              ON checkout_orders(user_id, created_at DESC);
            """
        )

    @staticmethod
    def _decode(row):
        if not row:
            return None
        out = dict(row)
        for key in ("answers", "result", "detail"):
            if key in out and out[key]:
                try:
                    out[key] = json.loads(out[key])
                except (TypeError, json.JSONDecodeError):
                    pass
        if "review_selected" in out:
            out["review_selected"] = bool(out["review_selected"])
        return out

    @staticmethod
    def requires_m35_trace(order) -> bool:
        return bool((order or {}).get("detail", {}).get("commerce_trace_required"))

    @staticmethod
    def _missing_table_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "no such table" in text or ("does not exist" in text and "m35_intake_handoffs" in text)

    def _active_m35_handoff(self, con, user_id, product_code):
        try:
            return con.execute(
                """SELECT id,status FROM m35_intake_handoffs
                   WHERE user_id=? AND product_code=? AND status!='CANCELLED'
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, product_code),
            ).fetchone()
        except Exception as exc:
            if self._missing_table_error(exc):
                return None
            raise

    def save_draft(self, con, user_id, product_code, answers, current_step=0, title="", result=None):
        if product_code not in self.products:
            raise ValueError("Producto no encontrado.")
        answers = answers or {}
        existing = con.execute(
            "SELECT id,created_at FROM service_drafts WHERE user_id=? AND product_code=?",
            (user_id, product_code),
        ).fetchone()
        now = utc_iso()
        draft_id = existing["id"] if existing else "DRF-" + uuid.uuid4().hex[:12].upper()
        public = self.portal.product(product_code) or {}
        title = (title or public.get("title") or self.products[product_code].get("title") or product_code).strip()[:240]
        payload = (
            draft_id,
            user_id,
            product_code,
            title,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False) if result is not None else None,
            max(0, int(current_step or 0)),
            "En progreso",
            existing["created_at"] if existing else now,
            now,
        )
        con.execute(
            """INSERT INTO service_drafts(id,user_id,product_code,title,answers,result,current_step,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id,product_code) DO UPDATE SET
                 title=excluded.title,answers=excluded.answers,result=excluded.result,
                 current_step=excluded.current_step,status='En progreso',updated_at=excluded.updated_at""",
            payload,
        )
        return self.get_draft(con, user_id, draft_id)

    def list_drafts(self, con, user_id):
        rows = con.execute(
            "SELECT * FROM service_drafts WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [self._decode(row) for row in rows]

    def get_draft(self, con, user_id, draft_id):
        return self._decode(
            con.execute(
                "SELECT * FROM service_drafts WHERE id=? AND user_id=?",
                (draft_id, user_id),
            ).fetchone()
        )

    def get_product_draft(self, con, user_id, product_code):
        return self._decode(
            con.execute(
                "SELECT * FROM service_drafts WHERE user_id=? AND product_code=?",
                (user_id, product_code),
            ).fetchone()
        )

    def delete_draft(self, con, user_id, draft_id):
        cur = con.execute(
            "DELETE FROM service_drafts WHERE id=? AND user_id=?",
            (draft_id, user_id),
        )
        return bool(cur.rowcount)

    def create_order(self, con, user_id, product_code, result, review_selected=False, service_level=None, trace_context=None):
        public = self.portal.product(product_code)
        if not public:
            raise ValueError("Producto no encontrado.")
        active_handoff = self._active_m35_handoff(con, user_id, product_code)
        trace_context = trace_context or {}
        if active_handoff:
            if not trace_context:
                raise ValueError("Este diagnóstico debe continuar por el checkout trazable M35.2.")
            if str(trace_context.get("handoff_id") or "") != str(active_handoff["id"]):
                raise ValueError("El checkout no corresponde al diagnóstico transferido.")
        elif trace_context:
            raise ValueError("No existe un diagnóstico transferido que autorice este checkout trazable.")

        result = result or {}
        requested_level = str(service_level or result.get("service_level") or "").strip().lower()
        if requested_level not in {"", "documento_personalizado", "solucion_revisada"}:
            raise ValueError("Nivel de servicio inválido para checkout.")
        service_mode = result.get("service_mode") or "self_service"
        if service_mode == "blocked" or requested_level == "solucion_revisada":
            review_selected = True
        if requested_level == "documento_personalizado" and service_mode == "blocked":
            raise ValueError("El nivel de riesgo exige seleccionar solución revisada.")
        if not requested_level:
            requested_level = "solucion_revisada" if review_selected else "documento_personalizado"
        service_mode = requested_level
        document_price = int(public.get("price_auto") or 0)
        review_price = int(public.get("price_review") or 0) if review_selected else 0
        order_id = "ORD-" + uuid.uuid4().hex[:12].upper()
        now = utc_iso()
        detail = {
            "product_title": public.get("title"),
            "documents": result.get("documents_expected") or public.get("documents") or [],
            "service_label": "Solución revisada" if review_selected else "Documento personalizado",
            "service_level": requested_level,
            "risk": result.get("risk"),
            "environment": "Pago simulado de prototipo; no realiza cargo real.",
            "commerce_trace_required": bool(active_handoff),
        }
        con.execute(
            """INSERT INTO checkout_orders(
                 id,user_id,product_code,service_mode,review_selected,document_price,
                 review_price,total,currency,status,detail,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,'Pendiente',?,?,?)""",
            (
                order_id,
                user_id,
                product_code,
                service_mode,
                int(bool(review_selected)),
                document_price,
                review_price,
                document_price + review_price,
                "COP",
                json.dumps(detail, ensure_ascii=False),
                now,
                now,
            ),
        )
        return self.get_order(con, user_id, order_id)

    def get_order(self, con, user_id, order_id, admin=False):
        clause = "id=?" if admin else "id=? AND user_id=?"
        params = (order_id,) if admin else (order_id, user_id)
        return self._decode(con.execute(f"SELECT * FROM checkout_orders WHERE {clause}", params).fetchone())

    def list_orders(self, con, user_id):
        rows = con.execute(
            "SELECT * FROM checkout_orders WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [self._decode(row) for row in rows]

    def pay_order(self, con, user_id, order_id, payment_method):
        order = self.get_order(con, user_id, order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if self.requires_m35_trace(order):
            raise ValueError("Esta orden exige un intento de pago sandbox trazable M35.2.")
        if order["status"] == "Pagado (simulado)":
            return order
        allowed = {"Tarjeta de prueba", "PSE de prueba", "Continuar sin cobro"}
        if payment_method not in allowed:
            raise ValueError("Selecciona un medio de pago de demostración válido.")
        now = utc_iso()
        receipt = "RCPT-" + uuid.uuid4().hex[:10].upper()
        con.execute(
            """UPDATE checkout_orders SET status='Pagado (simulado)',payment_method=?,
               receipt_number=?,updated_at=? WHERE id=? AND user_id=?""",
            (payment_method, receipt, now, order_id, user_id),
        )
        return self.get_order(con, user_id, order_id)

    def attach_case(self, con, user_id, order_id, case_id, trace_context=False):
        order = self.get_order(con, user_id, order_id)
        if not order:
            raise ValueError("Orden no encontrada.")
        if self.requires_m35_trace(order) and not trace_context:
            raise ValueError("Esta orden sólo puede convertirse en expediente mediante el ledger M35.2.")
        if order["status"] not in {"Pagado (simulado)", "Pagado (sandbox)"}:
            raise ValueError("La orden debe confirmarse antes de generar el expediente.")
        con.execute(
            "UPDATE checkout_orders SET case_id=?,status='Completada',updated_at=? WHERE id=? AND user_id=?",
            (case_id, utc_iso(), order_id, user_id),
        )
        return self.get_order(con, user_id, order_id)

    def summary(self, con, user_id):
        return {
            "drafts": self.list_drafts(con, user_id),
            "orders": self.list_orders(con, user_id)[:10],
        }
