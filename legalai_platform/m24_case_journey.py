from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class M24CaseJourneyCenter:
    """Auditable end-to-end case journey for the controlled M24.6 client journey.

    The journey is additive: it does not mutate canonical document revisions,
    publish M23.2, or replace the legacy case status. It records a stricter
    operational state machine, follow-up plan and immutable transitions.
    """

    DELIVERY_CONFIRMATION = "ENTREGAR SOLUCIÓN"
    STATES = (
        "INICIADO", "DIAGNOSTICADO", "INFORMACION_INCOMPLETA", "LISTO_PARA_PAGO",
        "PAGADO", "LISTO_PARA_GENERAR", "GENERADO", "EN_REVISION_JURIDICA",
        "OBSERVADO", "CORREGIDO", "APROBADO_JURIDICAMENTE", "EN_QA",
        "APROBADO_QA", "ENTREGADO", "EN_SEGUIMIENTO", "CERRADO", "ESCALADO", "CANCELADO",
    )
    TERMINAL_STATES = {"CERRADO", "CANCELADO"}
    ALLOWED = {
        "INICIADO": {"DIAGNOSTICADO", "CANCELADO"},
        "DIAGNOSTICADO": {"INFORMACION_INCOMPLETA", "LISTO_PARA_PAGO", "ESCALADO", "CANCELADO"},
        "INFORMACION_INCOMPLETA": {"DIAGNOSTICADO", "CANCELADO"},
        "LISTO_PARA_PAGO": {"PAGADO", "CANCELADO"},
        "PAGADO": {"LISTO_PARA_GENERAR", "ESCALADO"},
        "LISTO_PARA_GENERAR": {"GENERADO", "ESCALADO"},
        "GENERADO": {"EN_REVISION_JURIDICA", "ESCALADO"},
        "EN_REVISION_JURIDICA": {"OBSERVADO", "APROBADO_JURIDICAMENTE", "ESCALADO"},
        "OBSERVADO": {"CORREGIDO", "ESCALADO"},
        "CORREGIDO": {"EN_REVISION_JURIDICA", "ESCALADO"},
        "APROBADO_JURIDICAMENTE": {"EN_QA", "ESCALADO"},
        "EN_QA": {"OBSERVADO", "APROBADO_QA", "ESCALADO"},
        "APROBADO_QA": {"ENTREGADO", "ESCALADO"},
        "ENTREGADO": {"EN_SEGUIMIENTO", "CERRADO", "ESCALADO"},
        "EN_SEGUIMIENTO": {"CERRADO", "ESCALADO"},
        "ESCALADO": {"EN_REVISION_JURIDICA", "CERRADO", "CANCELADO"},
        "CERRADO": set(),
        "CANCELADO": set(),
    }

    def __init__(self, root: Path):
        self.root = Path(root)
        self.plan_path = self.root / "config" / "m24_5_follow_up_plans.json"
        payload = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.plan_notice = payload.get("notice", "")
        self.plans = payload.get("products", {})

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m24_case_journey(
              case_id TEXT PRIMARY KEY,
              product_code TEXT NOT NULL,
              current_state TEXT NOT NULL,
              legal_approver_id TEXT,
              qa_approver_id TEXT,
              delivery_actor_id TEXT,
              diagnosis_json TEXT NOT NULL DEFAULT '{}',
              route_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE TABLE IF NOT EXISTS m24_case_transition(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              from_state TEXT,
              to_state TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              actor_name TEXT NOT NULL,
              reason TEXT NOT NULL,
              evidence_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_case_transition_case
              ON m24_case_transition(case_id,created_at);
            CREATE TABLE IF NOT EXISTS m24_case_follow_up(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              action_label TEXT NOT NULL,
              due_at TEXT,
              status TEXT NOT NULL CHECK(status IN ('pending','completed','cancelled','overdue')),
              note TEXT NOT NULL DEFAULT '',
              actor_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_case_follow_up_case
              ON m24_case_follow_up(case_id,status,due_at);
            """
        )

    @staticmethod
    def _json(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    def _case(self, con, case_id: str):
        return con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()

    def can_access(self, case_row, actor: dict[str, Any]) -> bool:
        if not case_row:
            return False
        role = actor.get("role")
        actor_id = str(actor.get("id") or "")
        if role == "admin":
            return True
        if role == "client":
            return str(case_row["owner_id"] or "") == actor_id
        if role == "specialist":
            return str(case_row["specialist_id"] or "") == actor_id
        return False

    def _initial_route(self, case_row) -> dict[str, Any]:
        result = self._json(case_row["result"])
        return {
            "risk": case_row["risk"],
            "route": result.get("route") or "Ruta jurídica pendiente de confirmación",
            "review_required": bool(result.get("review_required") or case_row["risk"] == "red"),
            "source": "legacy_case_result_read_only",
        }

    def ensure_case(self, con, case_id: str, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        case_row = self._case(con, case_id)
        if not case_row or not self.can_access(case_row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        existing = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        if not existing:
            now = self.now()
            route = self._initial_route(case_row)
            con.execute(
                """INSERT INTO m24_case_journey
                   (case_id,product_code,current_state,diagnosis_json,route_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (case_id, case_row["product_code"], "INICIADO", case_row["result"] or "{}", json.dumps(route, ensure_ascii=False), now, now),
            )
            con.execute(
                """INSERT INTO m24_case_transition
                   (id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), case_id, None, "INICIADO", str(actor.get("id")), str(actor.get("role")), self._actor_name(actor),
                 "Creación del recorrido operativo M24.6 sin alterar el estado histórico del expediente.", "{}", now),
            )
            con.commit()
        return self.detail(con, case_id, actor)

    def _role_can_target(self, target: str, actor: dict[str, Any], case_row) -> bool:
        role = actor.get("role")
        actor_id = str(actor.get("id") or "")
        if target == "APROBADO_JURIDICAMENTE":
            return role == "specialist" and str(case_row["specialist_id"] or "") == actor_id
        if target in {"EN_QA", "APROBADO_QA", "ENTREGADO"}:
            return role == "admin"
        if target in {"GENERADO", "EN_REVISION_JURIDICA", "OBSERVADO", "CORREGIDO", "LISTO_PARA_GENERAR"}:
            return role in {"specialist", "admin"}
        if target == "PAGADO":
            return role in {"client", "admin"}
        if target in {"DIAGNOSTICADO", "INFORMACION_INCOMPLETA", "LISTO_PARA_PAGO", "EN_SEGUIMIENTO", "CERRADO", "ESCALADO", "CANCELADO"}:
            return role in {"client", "specialist", "admin"}
        return role in {"specialist", "admin"}

    def _available(self, state: str, actor: dict[str, Any], case_row) -> list[str]:
        return sorted(target for target in self.ALLOWED.get(state, set()) if self._role_can_target(target, actor, case_row))

    def _document_count(self, con, case_id: str) -> int:
        return int(con.execute("SELECT COUNT(*) FROM documents WHERE case_id=?", (case_id,)).fetchone()[0])

    def _followups(self, con, case_id: str) -> list[dict[str, Any]]:
        now = self.now()
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM m24_case_follow_up WHERE case_id=? ORDER BY COALESCE(due_at,'9999'),created_at", (case_id,)
        ).fetchall()]
        for row in rows:
            if row["status"] == "pending" and row.get("due_at") and row["due_at"] < now:
                row["effective_status"] = "overdue"
            else:
                row["effective_status"] = row["status"]
        return rows

    def _checkout_order(self, con, case_id: str) -> dict[str, Any] | None:
        table = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='checkout_orders'").fetchone()
        if not table:
            return None
        row = con.execute(
            "SELECT id,product_code,service_mode,review_selected,document_price,review_price,total,currency,status,payment_method,receipt_number,detail,created_at,updated_at FROM checkout_orders WHERE case_id=? ORDER BY updated_at DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        if not row:
            return None
        out = dict(row)
        out["review_selected"] = bool(out.get("review_selected"))
        out["detail"] = self._json(out.get("detail"))
        return out

    def detail(self, con, case_id: str, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        case_row = self._case(con, case_id)
        if not case_row or not self.can_access(case_row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        journey = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        if not journey:
            return self.ensure_case(con, case_id, actor)
        transitions = [dict(row) for row in con.execute(
            "SELECT * FROM m24_case_transition WHERE case_id=? ORDER BY created_at,id", (case_id,)
        ).fetchall()]
        followups = self._followups(con, case_id)
        plan = self.plans.get(case_row["product_code"], {})
        current = journey["current_state"]
        return {
            "schema": "legalai_m24_6_case_journey_detail_v1",
            "milestone": "M24.6",
            "case_id": case_id,
            "product_code": case_row["product_code"],
            "current_state": current,
            "terminal": current in self.TERMINAL_STATES,
            "available_transitions": self._available(current, actor, case_row),
            "legal_approver_id": journey["legal_approver_id"],
            "qa_approver_id": journey["qa_approver_id"],
            "delivery_actor_id": journey["delivery_actor_id"],
            "document_count": self._document_count(con, case_id),
            "route": self._json(journey["route_json"]),
            "diagnosis": self._json(journey["diagnosis_json"]),
            "follow_up_plan": plan,
            "follow_up_notice": self.plan_notice,
            "follow_ups": followups,
            "transitions": transitions,
            "commerce": self._checkout_order(con, case_id),
            "governance": {
                "legacy_case_status_unchanged": True,
                "candidate_library_published": False,
                "automatic_delivery": False,
                "dual_approval_required": True,
                "distinct_approvers_required": True,
            },
        }

    def list_for_actor(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        role = actor.get("role")
        if role == "admin":
            rows = con.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
        elif role == "client":
            rows = con.execute("SELECT * FROM cases WHERE owner_id=? ORDER BY updated_at DESC", (actor.get("id"),)).fetchall()
        elif role == "specialist":
            rows = con.execute("SELECT * FROM cases WHERE specialist_id=? ORDER BY updated_at DESC", (actor.get("id"),)).fetchall()
        else:
            rows = []
        items = []
        for row in rows:
            item = self.ensure_case(con, row["id"], actor)
            items.append({
                "case_id": item["case_id"], "product_code": item["product_code"],
                "current_state": item["current_state"], "terminal": item["terminal"],
                "available_transitions": item["available_transitions"],
                "pending_follow_ups": sum(1 for x in item["follow_ups"] if x["effective_status"] in {"pending", "overdue"}),
            })
        return {
            "schema": "legalai_m24_6_case_journey_list_v1",
            "milestone": "M24.6",
            "items": items,
            "metrics": {
                "cases": len(items),
                "closed": sum(1 for x in items if x["current_state"] == "CERRADO"),
                "escalated": sum(1 for x in items if x["current_state"] == "ESCALADO"),
                "pending_follow_ups": sum(x["pending_follow_ups"] for x in items),
            },
        }

    def _create_default_followups(self, con, case_id: str, product_code: str, actor_id: str) -> None:
        existing = con.execute("SELECT COUNT(*) FROM m24_case_follow_up WHERE case_id=?", (case_id,)).fetchone()[0]
        if existing:
            return
        plan = self.plans.get(product_code, {})
        days = int(plan.get("initial_follow_up_days") or 5)
        due = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
        now = self.now()
        actions = list(plan.get("required_actions") or [])
        if plan.get("delivery_action"):
            actions.insert(0, plan["delivery_action"])
        for index, label in enumerate(actions):
            action_due = due if index == 0 else None
            con.execute(
                """INSERT INTO m24_case_follow_up
                   (id,case_id,action_label,due_at,status,note,actor_id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), case_id, str(label), action_due, "pending", "", actor_id, now, now),
            )

    def transition(self, con, case_id: str, target: str, reason: str, evidence: dict[str, Any], confirmation: str, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        target = str(target or "").upper().strip()
        reason = str(reason or "").strip()
        evidence = evidence if isinstance(evidence, dict) else {}
        case_row = self._case(con, case_id)
        if not case_row or not self.can_access(case_row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        self.ensure_case(con, case_id, actor)
        journey = con.execute("SELECT * FROM m24_case_journey WHERE case_id=?", (case_id,)).fetchone()
        current = journey["current_state"]
        if target not in self.STATES:
            raise ValueError("Estado objetivo inválido.")
        if target not in self.ALLOWED.get(current, set()):
            raise ValueError(f"Transición no permitida: {current} → {target}.")
        if not self._role_can_target(target, actor, case_row):
            raise PermissionError("El rol actual no puede registrar esta transición.")
        if len(reason) < 20:
            raise ValueError("La transición exige una justificación verificable de al menos 20 caracteres.")
        doc_count = self._document_count(con, case_id)
        if target in {"GENERADO", "EN_REVISION_JURIDICA", "APROBADO_JURIDICAMENTE", "EN_QA", "APROBADO_QA", "ENTREGADO"} and doc_count < 1:
            raise ValueError("El expediente no tiene documentos vinculados para continuar.")
        actor_id = str(actor.get("id"))
        legal_approver = journey["legal_approver_id"]
        qa_approver = journey["qa_approver_id"]
        if target == "APROBADO_JURIDICAMENTE":
            legal_approver = actor_id
        if target == "APROBADO_QA":
            if not legal_approver:
                raise ValueError("QA no puede aprobar antes de la aprobación jurídica.")
            if legal_approver == actor_id:
                raise ValueError("La aprobación jurídica y QA deben corresponder a usuarios distintos.")
            qa_approver = actor_id
        if target == "ENTREGADO":
            if not legal_approver or not qa_approver or legal_approver == qa_approver:
                raise ValueError("La entrega exige aprobación jurídica y QA por usuarios distintos.")
            if str(confirmation or "").strip() != self.DELIVERY_CONFIRMATION:
                raise ValueError(f"Para entregar debe escribir exactamente: {self.DELIVERY_CONFIRMATION}")
        if target == "CERRADO" and len(reason) < 30:
            raise ValueError("El cierre exige una conclusión verificable de al menos 30 caracteres.")
        now = self.now()
        delivery_actor = actor_id if target == "ENTREGADO" else journey["delivery_actor_id"]
        con.execute(
            """UPDATE m24_case_journey SET current_state=?,legal_approver_id=?,qa_approver_id=?,delivery_actor_id=?,updated_at=? WHERE case_id=?""",
            (target, legal_approver, qa_approver, delivery_actor, now, case_id),
        )
        con.execute(
            """INSERT INTO m24_case_transition
               (id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), case_id, current, target, actor_id, str(actor.get("role")), self._actor_name(actor), reason,
             json.dumps(evidence, ensure_ascii=False, sort_keys=True), now),
        )
        if target == "ENTREGADO":
            self._create_default_followups(con, case_id, case_row["product_code"], actor_id)
        con.execute(
            "INSERT INTO audit_log(actor,entity_type,entity_id,action,detail,created_at) VALUES(?,?,?,?,?,?)",
            (actor_id, "m24_case_journey", case_id, "transition", json.dumps({"from": current, "to": target, "reason": reason}, ensure_ascii=False), now),
        )
        con.commit()
        return self.detail(con, case_id, actor)

    def bootstrap_paid_generation(self, con, case_id: str, order: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        """Register the verified client flow already completed by checkout and generation.

        This method is intentionally narrow and idempotent. It never approves,
        delivers or publishes a legal document. It only reconciles the operational
        M24 journey with a paid sandbox order and documents generated by the legacy
        create_case transaction.
        """
        self.ensure_schema(con)
        case_row = self._case(con, case_id)
        if not case_row or not self.can_access(case_row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        if str(order.get("case_id") or "") != case_id:
            raise ValueError("La orden no está vinculada al expediente indicado.")
        if str(order.get("product_code") or "") != str(case_row["product_code"]):
            raise ValueError("La orden no corresponde al producto del expediente.")
        if str(order.get("status") or "") not in {"Completada", "Pagado (simulado)", "Pagado (sandbox)"}:
            raise ValueError("La orden no tiene confirmación de pago válida.")
        if self._document_count(con, case_id) < 1:
            raise ValueError("No existen documentos generados para reconciliar el recorrido.")
        detail = self.ensure_case(con, case_id, actor)
        if detail["current_state"] != "INICIADO":
            return detail
        sequence = [
            ("DIAGNOSTICADO", str(actor.get("id")), str(actor.get("role")), self._actor_name(actor), "El formulario y las reglas del producto produjeron un diagnóstico trazable."),
            ("LISTO_PARA_PAGO", str(actor.get("id")), str(actor.get("role")), self._actor_name(actor), "El usuario confirmó el alcance, las exclusiones y el nivel de servicio seleccionado."),
            ("PAGADO", str(actor.get("id")), str(actor.get("role")), self._actor_name(actor), "La orden sandbox fue confirmada antes de crear el expediente."),
            ("LISTO_PARA_GENERAR", "system-m24-6", "system", "LegalAIZ.it", "La orden pagada y los datos validados habilitaron la generación controlada."),
            ("GENERADO", "system-m24-6", "system", "LegalAIZ.it", "El expediente contiene documentos generados y queda pendiente de las revisiones aplicables."),
        ]
        current = "INICIADO"
        base = datetime.now(timezone.utc)
        evidence = {
            "source": "m24_6_checkout_case_bootstrap",
            "order_id": order.get("id"),
            "order_status": order.get("status"),
            "service_mode": order.get("service_mode"),
            "review_selected": bool(order.get("review_selected")),
            "document_count": self._document_count(con, case_id),
        }
        for index, (target, actor_id, actor_role, actor_name, reason) in enumerate(sequence, 1):
            created_at = (base + timedelta(microseconds=index)).isoformat(timespec="microseconds")
            con.execute(
                """INSERT INTO m24_case_transition
                   (id,case_id,from_state,to_state,actor_id,actor_role,actor_name,reason,evidence_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), case_id, current, target, actor_id, actor_role, actor_name, reason,
                 json.dumps(evidence, ensure_ascii=False, sort_keys=True), created_at),
            )
            current = target
        now = self.now()
        con.execute("UPDATE m24_case_journey SET current_state='GENERADO',updated_at=? WHERE case_id=?", (now, case_id))
        con.execute(
            "INSERT INTO audit_log(actor,entity_type,entity_id,action,detail,created_at) VALUES(?,?,?,?,?,?)",
            (str(actor.get("id")), "m24_case_journey", case_id, "bootstrap_paid_generation", json.dumps(evidence, ensure_ascii=False), now),
        )
        con.commit()
        return self.detail(con, case_id, actor)

    def update_follow_up(self, con, case_id: str, follow_up_id: str, status: str, note: str, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        case_row = self._case(con, case_id)
        if not case_row or not self.can_access(case_row, actor):
            raise LookupError("Expediente no encontrado o sin acceso.")
        status = str(status or "").lower().strip()
        note = str(note or "").strip()
        if status not in {"pending", "completed", "cancelled"}:
            raise ValueError("Estado de seguimiento inválido.")
        if len(note) < 10:
            raise ValueError("El seguimiento exige una nota de al menos 10 caracteres.")
        row = con.execute("SELECT * FROM m24_case_follow_up WHERE id=? AND case_id=?", (follow_up_id, case_id)).fetchone()
        if not row:
            raise LookupError("Actividad de seguimiento no encontrada.")
        now = self.now()
        con.execute(
            "UPDATE m24_case_follow_up SET status=?,note=?,actor_id=?,updated_at=? WHERE id=?",
            (status, note, str(actor.get("id")), now, follow_up_id),
        )
        con.execute(
            "INSERT INTO audit_log(actor,entity_type,entity_id,action,detail,created_at) VALUES(?,?,?,?,?,?)",
            (str(actor.get("id")), "m24_case_follow_up", follow_up_id, "update", json.dumps({"status": status, "note": note}, ensure_ascii=False), now),
        )
        con.commit()
        return self.detail(con, case_id, actor)
