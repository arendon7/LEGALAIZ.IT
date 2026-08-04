from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legalai_platform.m24_candidate_governance import M24CandidateGovernance


class M24ReleaseGovernance(M24CandidateGovernance):
    """Dual approval plus explicit internal-pilot activation for all products.

    Activation is deliberately limited to professional internal pilot access.
    It does not mutate product.json, does not replace active M21.1 generation,
    and does not publish candidate documents to clients.
    """

    ACTIVATION_CONFIRMATION = "ACTIVAR PILOTO INTERNO"

    @staticmethod
    def ensure_schema(con) -> None:
        M24CandidateGovernance.ensure_schema(con)
        con.execute("""
            CREATE TABLE IF NOT EXISTS m24_candidate_activation (
                product_code TEXT NOT NULL,
                candidate_revision TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('inactive','internal_pilot_active')),
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (product_code, candidate_revision)
            )
        """)

    def activation(self, con, code: str) -> dict[str, Any]:
        self.ensure_schema(con)
        revision = self._candidate_revision(code)
        row = con.execute(
            "SELECT * FROM m24_candidate_activation WHERE product_code=? AND candidate_revision=?",
            (code, revision),
        ).fetchone()
        if not row:
            return {"state": "inactive", "internal_pilot_active": False}
        item = dict(row)
        item["internal_pilot_active"] = item.get("state") == "internal_pilot_active"
        return item

    def summary(self, con) -> dict[str, Any]:
        validated = self.pilot.summary()
        products = []
        for row in validated.get("products", []):
            code = row["product_code"]
            approvals = self.approvals(con, code)
            activation = self.activation(con, code)
            release_ready = bool(row.get("passed") and approvals["complete"])
            products.append({
                **row,
                "approvals": approvals,
                "pilot_release_ready": release_ready,
                "activation": activation,
                "internal_pilot_active": bool(release_ready and activation.get("internal_pilot_active")),
            })
        return {
            **validated,
            "schema": "legalai_m24_4_release_governance_summary_v1",
            "approval_model": products[0]["approvals"].get("approval_model") if products else "distinct_specialist_then_admin_qa",
            "independent_reviewers": all(row["approvals"].get("independent_reviewers") for row in products) if products else True,
            "activation_model": "explicit_admin_internal_pilot_only",
            "automatic_publication": False,
            "client_publication": False,
            "approved_for_pilot_count": sum(1 for row in products if row["pilot_release_ready"]),
            "internal_pilot_active_count": sum(1 for row in products if row["internal_pilot_active"]),
            "products": products,
        }

    def detail(self, con, code: str) -> dict[str, Any] | None:
        detail = self.pilot.detail(code)
        if not detail:
            return None
        approvals = self.approvals(con, code)
        activation = self.activation(con, code)
        release_ready = bool(detail.get("passed") and approvals["complete"])
        return {
            **detail,
            "approvals": approvals,
            "pilot_release_ready": release_ready,
            "activation": activation,
            "internal_pilot_active": bool(release_ready and activation.get("internal_pilot_active")),
        }

    def decide(self, con, code: str, approval_type: str, decision: str, comment: str, actor: dict[str, Any]) -> dict[str, Any]:
        code = str(code or "").upper()
        if code not in self.pilot.PILOT_CODES:
            raise ValueError("El producto no pertenece a la validación integral M24.4.")
        return super().decide(con, code, approval_type, decision, comment, actor)

    def set_activation(self, con, code: str, action: str, comment: str, confirmation: str, actor: dict[str, Any]) -> dict[str, Any]:
        code = str(code or "").upper()
        action = str(action or "").lower()
        comment = str(comment or "").strip()
        confirmation = str(confirmation or "").strip()
        if code not in self.pilot.PILOT_CODES:
            raise ValueError("El producto no pertenece a la validación integral M24.4.")
        if actor.get("role") != "admin":
            raise PermissionError("La activación controlada exige rol administrador.")
        if action not in {"activate", "deactivate"}:
            raise ValueError("Acción de activación inválida.")
        if len(comment) < 20:
            raise ValueError("La activación debe incluir una justificación verificable de al menos 20 caracteres.")
        if action == "activate" and confirmation != self.ACTIVATION_CONFIRMATION:
            raise ValueError(f"Para activar debe escribir exactamente: {self.ACTIVATION_CONFIRMATION}")
        self.ensure_schema(con)
        detail = self.detail(con, code)
        if not detail or not detail.get("passed"):
            raise ValueError("No puede activarse un producto con escenarios pendientes o fallidos.")
        if action == "activate" and not detail.get("approvals", {}).get("complete"):
            raise ValueError("La activación exige aprobación jurídica y QA por usuarios distintos.")
        integrity = self.candidates.verify_integrity()
        if action == "activate" and not integrity.get("ok"):
            raise ValueError("La biblioteca candidata no superó la verificación de integridad.")
        revision = self._candidate_revision(code)
        state = "internal_pilot_active" if action == "activate" else "inactive"
        now = datetime.now(timezone.utc).isoformat()
        record = (
            code, revision, state, str(actor.get("id")), str(actor.get("role")),
            str(actor.get("name") or actor.get("email") or actor.get("id")), comment, now,
        )
        con.execute("""
            INSERT INTO m24_candidate_activation
            (product_code,candidate_revision,state,actor_id,actor_role,actor_name,comment,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(product_code,candidate_revision) DO UPDATE SET
              state=excluded.state,actor_id=excluded.actor_id,actor_role=excluded.actor_role,
              actor_name=excluded.actor_name,comment=excluded.comment,created_at=excluded.created_at
        """, record)
        payload = {
            "action": action,
            "state": state,
            "revision": revision,
            "scope": "internal_professional_pilot_only",
            "client_publication": False,
            "active_legacy_generation_changed": False,
            "comment": comment,
        }
        con.execute("""
            INSERT INTO m24_candidate_audit
            (product_code,candidate_revision,event_type,actor_id,actor_role,payload_json,created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (code, revision, f"internal_pilot_{action}", str(actor.get("id")), str(actor.get("role")), json.dumps(payload, ensure_ascii=False), now))
        con.commit()
        return self.detail(con, code)
