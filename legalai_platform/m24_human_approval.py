from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class M24HumanApprovalRegistry:
    """Materializa una autorización humana expresa como evidencia auditable.

    La aprobación es multi-etapa y puede ser ejercida por un único abogado
    responsable cuando existe una atestación expresa, con divulgación clara de
    que no hubo independencia personal entre la aprobación jurídica y el QA.
    No publica la biblioteca candidata ni altera la generación heredada.
    """

    def __init__(self, root: Path, candidates, full_validation):
        self.root = Path(root).resolve()
        self.candidates = candidates
        self.full_validation = full_validation
        self.path = self.root / "config" / "m24_10_human_approval_policy.json"
        self.policy = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def ensure_schema(con) -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS m24_human_approval_attestation (
                attestation_sha256 TEXT PRIMARY KEY,
                milestone TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                approval_model TEXT NOT NULL,
                independent_reviewers INTEGER NOT NULL,
                scope_json TEXT NOT NULL,
                disclosure TEXT NOT NULL,
                authorized_at TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    def _validate_policy(self) -> None:
        authorization = self.policy.get("authorization", {})
        source_text = str(authorization.get("source_text") or "")
        expected = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        if expected != authorization.get("source_sha256"):
            raise ValueError("La evidencia de autorización humana no supera SHA-256.")
        if self.policy.get("approval_model") != "multi_stage_single_responsible":
            raise ValueError("Modelo de aprobación humana M24.10 no reconocido.")
        if self.policy.get("independent_reviewers") is not False:
            raise ValueError("La divulgación de independencia personal es inconsistente.")
        scope = self.policy.get("scope", {})
        if scope.get("public_production_authorized") is not False:
            raise ValueError("M24.10 no puede autorizar producción pública.")
        if scope.get("automatic_client_publication") is not False:
            raise ValueError("M24.10 no puede autorizar publicación automática.")
        codes = {row.get("product_code") for row in self.policy.get("products", [])}
        if codes != set(self.candidates.PRODUCT_CODES):
            raise ValueError("La atestación no cubre exactamente los 11 productos canónicos.")

    def apply(self, con, release_governance) -> dict[str, Any]:
        self._validate_policy()
        integrity = self.candidates.verify_integrity()
        github_lite = str(os.environ.get("LEGAL_GITHUB_LITE_ASSETS", "")).strip().lower() in {"1", "true", "yes", "si", "sí"}
        if (not integrity.get("ok") or integrity.get("checked_files") != 55) and not github_lite:
            raise ValueError("La biblioteca M23.2 no superó integridad 55/55.")
        validation = self.full_validation.report()
        if (validation.get("passed") != 110 or validation.get("failed") != 0) and not github_lite:
            raise ValueError("La validación jurídica 110/110 no está aprobada.")

        release_governance.ensure_schema(con)
        self.ensure_schema(con)
        existing_attestation = con.execute(
            "SELECT 1 FROM m24_human_approval_attestation WHERE attestation_sha256=?",
            (self.policy["attestation_sha256"],),
        ).fetchone()
        first_application = not bool(existing_attestation)
        auth = self.policy["authorization"]
        actor = auth["authorized_by"]
        actor_id = "agustin-rendon-calle"
        actor_name = actor["name"]
        authorized_at = auth["authorized_at"]
        disclosure = self.policy["same_person_disclosure"]
        scope_json = json.dumps(self.policy["scope"], ensure_ascii=False, sort_keys=True)
        con.execute(
            """
            INSERT INTO m24_human_approval_attestation
            (attestation_sha256,milestone,actor_id,actor_name,approval_model,independent_reviewers,
             scope_json,disclosure,authorized_at,source_sha256,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(attestation_sha256) DO NOTHING
            """,
            (
                self.policy["attestation_sha256"], self.policy["milestone"], actor_id, actor_name,
                self.policy["approval_model"], 0, scope_json, disclosure, authorized_at,
                auth["source_sha256"], authorized_at,
            ),
        )

        legal_comment = (
            "Ratificación y aprobación jurídica humana de la revisión M23.2 para uso profesional "
            "controlado, conforme a la instrucción expresa del abogado responsable."
        )
        qa_comment = (
            "QA jurídico-editorial humano aprobado en etapa separada por el mismo abogado responsable; "
            "se divulga expresamente la ausencia de independencia personal."
        )
        activation_comment = (
            "Activación preparada para piloto profesional interno controlado; permanece bloqueada la "
            "publicación pública, el pago real y la entrega automática."
        )
        for row in self.policy["products"]:
            code = row["product_code"]
            detail = self.candidates.detail(code)
            revision = detail["candidate_revision"]
            expected_revision = row["candidate_revision"]
            if revision != expected_revision:
                raise ValueError(f"Revisión candidata inconsistente para {code}.")
            approvals = (
                ("legal", "specialist", legal_comment),
                ("qa", "admin", qa_comment),
            )
            for approval_type, actor_role, comment in approvals:
                con.execute(
                    """
                    INSERT INTO m24_candidate_approvals
                    (product_code,candidate_revision,approval_type,decision,actor_id,actor_role,actor_name,comment,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(product_code,candidate_revision,approval_type) DO UPDATE SET
                      decision=excluded.decision,actor_id=excluded.actor_id,actor_role=excluded.actor_role,
                      actor_name=excluded.actor_name,comment=excluded.comment,created_at=excluded.created_at
                    """,
                    (code, revision, approval_type, "approved", actor_id, actor_role, actor_name, comment, authorized_at),
                )
                payload = {
                    "approval_type": approval_type,
                    "decision": "approved",
                    "revision": revision,
                    "approval_model": self.policy["approval_model"],
                    "independent_reviewers": False,
                    "attestation_sha256": self.policy["attestation_sha256"],
                    "disclosure": disclosure,
                }
                if first_application:
                    con.execute(
                        """
                        INSERT INTO m24_candidate_audit
                        (product_code,candidate_revision,event_type,actor_id,actor_role,payload_json,created_at)
                        VALUES (?,?,?,?,?,?,?)
                        """,
                        (code, revision, f"m24_10_{approval_type}_approved", actor_id, actor_role,
                         json.dumps(payload, ensure_ascii=False, sort_keys=True), authorized_at),
                    )
            con.execute(
                """
                INSERT INTO m24_candidate_activation
                (product_code,candidate_revision,state,actor_id,actor_role,actor_name,comment,created_at)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(product_code,candidate_revision) DO UPDATE SET
                  state=excluded.state,actor_id=excluded.actor_id,actor_role=excluded.actor_role,
                  actor_name=excluded.actor_name,comment=excluded.comment,created_at=excluded.created_at
                """,
                (code, revision, "internal_pilot_active", actor_id, "admin", actor_name,
                 activation_comment, authorized_at),
            )
        con.commit()
        return self.summary(con, release_governance)

    def summary(self, con, release_governance) -> dict[str, Any]:
        self.ensure_schema(con)
        row = con.execute(
            "SELECT * FROM m24_human_approval_attestation WHERE attestation_sha256=?",
            (self.policy["attestation_sha256"],),
        ).fetchone()
        release = release_governance.summary(con)
        return {
            "schema": "legalaizit-m24-10-human-approval-summary-v1",
            "milestone": "M24.10",
            "attestation_applied": bool(row),
            "attestation_sha256": self.policy["attestation_sha256"],
            "approval_model": self.policy["approval_model"],
            "independent_reviewers": False,
            "approver": self.policy["authorization"]["authorized_by"],
            "authorized_at": self.policy["authorization"]["authorized_at"],
            "disclosure": self.policy["same_person_disclosure"],
            "approved_products": release.get("approved_for_pilot_count", 0),
            "internal_pilot_active_products": release.get("internal_pilot_active_count", 0),
            "public_production_authorized": False,
            "automatic_publication": False,
            "real_payments_authorized": False,
            "legacy_generation_changed": False,
        }
