from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


SCHEMA_VERSION = "35.3.0"
MATERIALIZED_JOURNEY_STATES = {
    "GENERADO",
    "EN_REVISION_JURIDICA",
    "OBSERVADO",
    "CORREGIDO",
    "APROBADO_JURIDICAMENTE",
    "EN_QA",
    "APROBADO_QA",
    "ENTREGADO",
    "EN_SEGUIMIENTO",
    "CERRADO",
    "ESCALADO",
}


class CaseActivationError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CaseActivationCenter:
    """Verified, PII-minimized read model for the M35 post-purchase experience.

    This component never creates orders, payments, cases, documents or approvals.
    It derives a client-facing activation view only after cross-checking the
    durable M35.2 commerce link, sandbox payment evidence, checkout order, case,
    document materialization and M24 journey.
    """

    def __init__(self, self_service, payments):
        self.self_service = self_service
        self.payments = payments

    @staticmethod
    def _table_exists(con, name: str) -> bool:
        return bool(
            con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone()
        )

    @staticmethod
    def _case(con, user_id: str, case_id: str):
        return con.execute(
            """SELECT id,product_code,title,risk,status,owner_id,review_status,created_at,updated_at
               FROM cases WHERE id=? AND owner_id=?""",
            (case_id, user_id),
        ).fetchone()

    def _link(self, con, user_id: str, case_id: str):
        if not self._table_exists(con, "m35_commerce_case_links"):
            return None
        return con.execute(
            """SELECT id,user_id,product_code,service_level,order_id,payment_intent_id,case_id,state,
                      checkout_consent_at,case_consent_at,created_at,updated_at
               FROM m35_commerce_case_links
               WHERE user_id=? AND case_id=?
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, case_id),
        ).fetchone()

    def _journey(self, con, case_id: str):
        if not self._table_exists(con, "m24_case_journey"):
            return None
        return con.execute(
            """SELECT case_id,product_code,current_state,legal_approver_id,qa_approver_id,
                      delivery_actor_id,created_at,updated_at
               FROM m24_case_journey WHERE case_id=?""",
            (case_id,),
        ).fetchone()

    def _generated_transition_exists(self, con, case_id: str) -> bool:
        if not self._table_exists(con, "m24_case_transition"):
            return False
        return bool(
            con.execute(
                "SELECT 1 FROM m24_case_transition WHERE case_id=? AND to_state='GENERADO' LIMIT 1",
                (case_id,),
            ).fetchone()
        )

    @staticmethod
    def _document_count(con, case_id: str) -> int:
        return int(
            con.execute(
                "SELECT COUNT(*) FROM documents WHERE case_id=? AND kind!='audit'",
                (case_id,),
            ).fetchone()[0]
        )

    @staticmethod
    def _service_label(order: Mapping[str, Any], service_level: str) -> str:
        detail = order.get("detail") or {}
        if isinstance(detail, dict) and detail.get("service_label"):
            return str(detail["service_label"])
        if service_level == "solucion_revisada":
            return "Solución revisada"
        if service_level == "documento_personalizado":
            return "Documento personalizado"
        return "Nivel de servicio"

    @staticmethod
    def _next_step(
        activation_status: str,
        journey_state: str,
        review_included: bool,
        risk: str,
        order_id: str,
    ) -> dict[str, str]:
        if activation_status == "DOCUMENTS_PENDING":
            return {
                "code": "RETRY_DOCUMENT_PREPARATION",
                "title": "Completa la preparación de los documentos",
                "detail": "El pago sandbox y el expediente están vinculados, pero la materialización documental aún no terminó.",
                "route": f"/checkout/{order_id}",
                "tab": "",
            }
        if journey_state in {"EN_REVISION_JURIDICA", "OBSERVADO", "CORREGIDO", "APROBADO_JURIDICAMENTE", "EN_QA"}:
            return {
                "code": "REVIEW_IN_PROGRESS",
                "title": "Sigue el estado de la revisión",
                "detail": "La solución permanece dentro del flujo de revisión aplicable. La aprobación jurídica y QA son controles separados.",
                "route": "",
                "tab": "revision",
            }
        if journey_state in {"APROBADO_QA", "ENTREGADO", "EN_SEGUIMIENTO", "CERRADO"}:
            return {
                "code": "REVIEW_DELIVERY_OR_FOLLOWUP",
                "title": "Revisa la versión disponible y sus siguientes pasos",
                "detail": "Consulta documentos, constancias de entrega y seguimiento antes de usar la solución fuera de la plataforma.",
                "route": "",
                "tab": "documentos" if journey_state == "APROBADO_QA" else "seguimiento",
            }
        if journey_state == "ESCALADO":
            return {
                "code": "ESCALATED_REVIEW",
                "title": "El expediente requiere revisión profesional",
                "detail": "Existe una escalación operativa. Consulta el estado de revisión antes de usar cualquier documento fuera de la plataforma.",
                "route": "",
                "tab": "revision",
            }
        if review_included or risk == "red":
            return {
                "code": "WAIT_FOR_REVIEW",
                "title": "Tus documentos quedaron listos para revisión",
                "detail": "La compra incluye o exige revisión profesional. Un documento generado no equivale todavía a una versión liberada para uso externo.",
                "route": "",
                "tab": "revision",
            }
        return {
            "code": "REVIEW_DRAFTS",
            "title": "Revisa los documentos generados",
            "detail": "Confirma nombres, fechas, valores y soportes. La generación automática no garantiza el resultado de un trámite o negociación.",
            "route": "",
            "tab": "documentos",
        }

    def build(self, con, user_id: str, case_id: str) -> dict[str, Any]:
        case_id = str(case_id or "").strip()
        if not case_id or len(case_id) > 80:
            raise CaseActivationError("CASE_ID_REQUIRED", "Expediente no indicado.", 400)

        case = self._case(con, user_id, case_id)
        if not case:
            raise CaseActivationError("CASE_NOT_FOUND", "Expediente no encontrado o sin acceso.", 404)
        case = dict(case)

        link_row = self._link(con, user_id, case_id)
        if not link_row:
            raise CaseActivationError(
                "NOT_M35_COMMERCE_CASE",
                "Este expediente no proviene del checkout trazable M35.",
                404,
            )
        link = dict(link_row)
        if link.get("product_code") != case.get("product_code") or link.get("case_id") != case_id:
            raise CaseActivationError("CASE_TRACE_BROKEN", "El expediente no coincide con su vínculo comercial.")
        if not str(link.get("checkout_consent_at") or "").strip():
            raise CaseActivationError("CHECKOUT_CONSENT_TRACE_MISSING", "No existe evidencia del consentimiento de checkout.")
        if not str(link.get("case_consent_at") or "").strip():
            raise CaseActivationError("CASE_CONSENT_TRACE_MISSING", "No existe evidencia del consentimiento para crear el expediente.")

        order = self.self_service.get_order(con, user_id, link["order_id"])
        if not order:
            raise CaseActivationError("ORDER_TRACE_BROKEN", "La orden vinculada al expediente no está disponible.")
        if order.get("case_id") != case_id or order.get("product_code") != case.get("product_code"):
            raise CaseActivationError("ORDER_CASE_MISMATCH", "La orden no coincide con el expediente vinculado.")
        if order.get("status") != "Completada":
            raise CaseActivationError("ORDER_NOT_COMPLETED", "La orden vinculada al expediente no está completada.")
        if not self.self_service.requires_m35_trace(order):
            raise CaseActivationError("ORDER_TRACE_FLAG_MISSING", "La orden perdió su marca de continuidad trazable.")
        service_level = str(link.get("service_level") or "")
        if service_level != str(order.get("service_mode") or ""):
            raise CaseActivationError("SERVICE_LEVEL_MISMATCH", "El nivel de servicio no coincide entre orden y vínculo comercial.")
        expected_review = service_level == "solucion_revisada"
        if bool(order.get("review_selected")) != expected_review:
            raise CaseActivationError("REVIEW_SELECTION_MISMATCH", "La selección de revisión no coincide con el nivel adquirido.")

        intent_id = str(link.get("payment_intent_id") or "")
        if not intent_id:
            raise CaseActivationError("PAYMENT_INTENT_REQUIRED", "No existe evidencia de pago vinculada al expediente.")
        intent = self.payments.intent(con, intent_id)
        if not intent:
            raise CaseActivationError("PAYMENT_INTENT_NOT_FOUND", "No existe evidencia de pago verificable.")
        if intent.get("user_id") != user_id or intent.get("order_id") != order.get("id"):
            raise CaseActivationError("PAYMENT_TRACE_BROKEN", "La evidencia de pago no pertenece a esta orden.")
        if intent.get("status") != "succeeded":
            raise CaseActivationError("PAYMENT_NOT_CONFIRMED", "El pago sandbox no está confirmado.")
        if int(intent.get("amount") or -1) != int(order.get("total") or 0):
            raise CaseActivationError("PAYMENT_AMOUNT_MISMATCH", "El importe confirmado no coincide con la orden.")
        if str(intent.get("currency") or "COP") != str(order.get("currency") or "COP"):
            raise CaseActivationError("PAYMENT_CURRENCY_MISMATCH", "La moneda confirmada no coincide con la orden.")
        verified = self.payments.verify_events(con, intent_id)
        if verified.get("errors") or int(verified.get("checked") or 0) < 2 or verified.get("valid") != verified.get("checked"):
            raise CaseActivationError("PAYMENT_EVENT_INTEGRITY_FAILED", "La cadena firmada del pago sandbox no pudo verificarse.")
        receipt = str(order.get("receipt_number") or "").strip()
        if not receipt.startswith("RCPT-SBX-"):
            raise CaseActivationError("SANDBOX_RECEIPT_MISSING", "La orden no conserva un comprobante sandbox válido.")

        document_count = self._document_count(con, case_id)
        journey_row = self._journey(con, case_id)
        journey = dict(journey_row) if journey_row else None
        link_state = str(link.get("state") or "")
        if link_state == "CASE_CREATED_DOCUMENTS_PENDING":
            activation_status = "DOCUMENTS_PENDING"
            journey_state = str((journey or {}).get("current_state") or "PENDING_DOCUMENT_MATERIALIZATION")
        elif link_state == "CASE_CREATED":
            if document_count < 1:
                raise CaseActivationError("DOCUMENT_TRACE_BROKEN", "El expediente se marcó como activado sin documentos materializados.")
            if not journey:
                raise CaseActivationError("JOURNEY_TRACE_MISSING", "El expediente activado no conserva recorrido operativo M24.")
            if str(journey.get("product_code") or "") != str(case.get("product_code") or ""):
                raise CaseActivationError("JOURNEY_PRODUCT_MISMATCH", "El recorrido operativo no corresponde al producto del expediente.")
            journey_state = str(journey.get("current_state") or "")
            if journey_state not in MATERIALIZED_JOURNEY_STATES:
                raise CaseActivationError("JOURNEY_NOT_RECONCILED", "El recorrido operativo aún no acredita la materialización documental.")
            if not self._generated_transition_exists(con, case_id):
                raise CaseActivationError("GENERATED_HISTORY_MISSING", "El recorrido no conserva evidencia histórica de generación documental.")
            activation_status = "ACTIVE"
        else:
            raise CaseActivationError("ACTIVATION_STATE_INVALID", "El vínculo comercial no está en un estado de activación válido.")

        review_included = bool(order.get("review_selected"))
        next_step = self._next_step(
            activation_status,
            journey_state,
            review_included,
            str(case.get("risk") or ""),
            str(order.get("id") or ""),
        )

        return {
            "schema": "legalai_m35_3_case_activation_v1",
            "schema_version": SCHEMA_VERSION,
            "activation_status": activation_status,
            "verified_at": _now(),
            "case": {
                "id": case_id,
                "product_code": case.get("product_code"),
                "title": case.get("title"),
                "risk": case.get("risk"),
                "status": case.get("status"),
                "review_status": case.get("review_status"),
            },
            "purchase_confirmation": {
                "environment": "sandbox",
                "real_charge": False,
                "order_id": order.get("id"),
                "order_status": order.get("status"),
                "receipt_number": receipt,
                "payment_method": order.get("payment_method") or intent.get("provider_label"),
                "payment_intent_id": intent_id,
                "payment_verified": True,
                "verified_event_count": int(verified.get("checked") or 0),
                "amount": int(order.get("total") or 0),
                "currency": order.get("currency") or "COP",
                "service_level": service_level,
                "service_label": self._service_label(order, service_level),
                "review_included": review_included,
            },
            "documents": {
                "count": document_count,
                "ready": activation_status == "ACTIVE" and document_count > 0,
            },
            "journey": {
                "current_state": journey_state,
                "legal_review_completed": bool((journey or {}).get("legal_approver_id")),
                "qa_completed": bool((journey or {}).get("qa_approver_id")),
                "delivered": bool((journey or {}).get("delivery_actor_id")),
            },
            "next_step": next_step,
            "notices": [
                "Este comprobante corresponde exclusivamente a un pago sandbox y no acredita un cargo real.",
                "La activación del expediente no equivale a aprobación jurídica, entrega ni garantía de resultado.",
                "Los controles internos de calidad y liberación documental son independientes del nivel comercial adquirido.",
            ],
        }


__all__ = [
    "CaseActivationCenter",
    "CaseActivationError",
    "MATERIALIZED_JOURNEY_STATES",
    "SCHEMA_VERSION",
]
