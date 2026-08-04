from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class M24CandidateGovernance:
    def __init__(self, root: Path, candidates, pilot_validation):
        self.root = Path(root).resolve()
        self.candidates = candidates
        self.pilot = pilot_validation

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def ensure_schema(con) -> None:
        con.execute("""
            CREATE TABLE IF NOT EXISTS m24_candidate_approvals (
                product_code TEXT NOT NULL,
                candidate_revision TEXT NOT NULL,
                approval_type TEXT NOT NULL CHECK (approval_type IN ('legal','qa')),
                decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')),
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (product_code, candidate_revision, approval_type)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS m24_candidate_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL,
                candidate_revision TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

    def _candidate_revision(self, code: str) -> str:
        detail = self.candidates.detail(code)
        if not detail:
            raise KeyError(code)
        return detail["candidate_revision"]

    def approvals(self, con, code: str) -> dict[str, Any]:
        self.ensure_schema(con)
        revision = self._candidate_revision(code)
        rows = con.execute(
            "SELECT * FROM m24_candidate_approvals WHERE product_code=? AND candidate_revision=? ORDER BY approval_type",
            (code, revision),
        ).fetchall()
        result = {"legal": {"status": "pending"}, "qa": {"status": "pending"}}
        for row in rows:
            item = dict(row)
            item["status"] = item.pop("decision")
            result[item["approval_type"]] = item
        legal = result["legal"]
        qa = result["qa"]
        distinct = legal.get("actor_id") and qa.get("actor_id") and legal.get("actor_id") != qa.get("actor_id")
        single_responsible = False
        disclosure = None
        table_exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='m24_human_approval_attestation'"
        ).fetchone()
        if table_exists:
            attestation = con.execute(
                "SELECT approval_model,independent_reviewers,disclosure FROM m24_human_approval_attestation ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if attestation:
                item = dict(attestation)
                single_responsible = item.get("approval_model") == "multi_stage_single_responsible" and not bool(item.get("independent_reviewers"))
                disclosure = item.get("disclosure")
        result["distinct_users"] = bool(distinct)
        result["independent_reviewers"] = bool(distinct)
        result["approval_model"] = "multi_stage_single_responsible" if single_responsible else "distinct_specialist_then_admin_qa"
        result["disclosure"] = disclosure
        result["complete"] = legal.get("status") == "approved" and qa.get("status") == "approved" and bool(distinct or single_responsible)
        return result

    def summary(self, con) -> dict[str, Any]:
        pilot = self.pilot.summary()
        products = []
        for row in pilot.get("products", []):
            code = row["product_code"]
            approvals = self.approvals(con, code)
            products.append({**row, "approvals": approvals, "pilot_release_ready": bool(row.get("passed") and approvals["complete"])})
        return {
            **pilot,
            "schema": "legalai_m24_3_candidate_governance_summary_v1",
            "approval_model": products[0]["approvals"].get("approval_model") if products else "distinct_specialist_then_admin_qa",
            "independent_reviewers": all(row["approvals"].get("independent_reviewers") for row in products) if products else True,
            "automatic_publication": False,
            "approved_for_pilot_count": sum(1 for row in products if row["pilot_release_ready"]),
            "products": products,
        }

    def detail(self, con, code: str) -> dict[str, Any] | None:
        detail = self.pilot.detail(code)
        if not detail:
            return None
        approvals = self.approvals(con, code)
        return {**detail, "approvals": approvals, "pilot_release_ready": bool(detail.get("passed") and approvals["complete"])}

    def decide(self, con, code: str, approval_type: str, decision: str, comment: str, actor: dict[str, Any]) -> dict[str, Any]:
        code = str(code or "").upper()
        approval_type = str(approval_type or "").lower()
        decision = str(decision or "").lower()
        comment = str(comment or "").strip()
        if code not in self.pilot.PILOT_CODES:
            raise ValueError("El producto no pertenece al piloto M24.3.")
        if approval_type not in {"legal", "qa"} or decision not in {"approved", "rejected"}:
            raise ValueError("Tipo de aprobación o decisión inválidos.")
        if len(comment) < 12:
            raise ValueError("La decisión debe incluir un comentario verificable de al menos 12 caracteres.")
        role = actor.get("role")
        if approval_type == "legal" and role != "specialist":
            raise PermissionError("La aprobación jurídica M24.3 exige rol especialista.")
        if approval_type == "qa" and role != "admin":
            raise PermissionError("La aprobación QA M24.3 exige rol administrador.")
        pilot_detail = self.pilot.detail(code)
        if not pilot_detail or not pilot_detail.get("passed"):
            raise ValueError("No puede aprobarse un producto con escenarios piloto pendientes o fallidos.")
        self.ensure_schema(con)
        revision = self._candidate_revision(code)
        current = self.approvals(con, code)
        if approval_type == "qa" and current["legal"].get("status") != "approved":
            raise ValueError("QA solo puede decidir después de la aprobación jurídica.")
        other = current["legal" if approval_type == "qa" else "qa"]
        if decision == "approved" and other.get("status") == "approved" and str(other.get("actor_id")) == str(actor.get("id")):
            raise ValueError("La aprobación dual exige usuarios distintos.")
        record = (
            code, revision, approval_type, decision, str(actor.get("id")), str(role),
            str(actor.get("name") or actor.get("email") or actor.get("id")), comment, self._now(),
        )
        con.execute("""
            INSERT INTO m24_candidate_approvals
            (product_code,candidate_revision,approval_type,decision,actor_id,actor_role,actor_name,comment,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(product_code,candidate_revision,approval_type) DO UPDATE SET
              decision=excluded.decision,actor_id=excluded.actor_id,actor_role=excluded.actor_role,
              actor_name=excluded.actor_name,comment=excluded.comment,created_at=excluded.created_at
        """, record)
        payload = {"approval_type": approval_type, "decision": decision, "comment": comment, "revision": revision}
        con.execute("""
            INSERT INTO m24_candidate_audit
            (product_code,candidate_revision,event_type,actor_id,actor_role,payload_json,created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (code, revision, f"{approval_type}_{decision}", str(actor.get("id")), str(role), json.dumps(payload, ensure_ascii=False), self._now()))
        con.commit()
        return self.detail(con, code)
