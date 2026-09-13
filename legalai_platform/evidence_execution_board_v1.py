from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from legalai_platform.evidence_execution_runbook_v1 import (
    EvidenceExecutionRunbook,
    EvidenceExecutionRunbookError,
)
from legalai_platform.evidence_orchestration_v1_rc8_1 import (
    EvidenceAuditDossier,
    EvidenceCampaignError,
    EvidenceCampaignIntegrityError,
    EvidenceCampaignLedger,
)


BOARD_SCHEMA = "legalaiz-v1-ops2-evidence-operations-board-v1"
FORBIDDEN_OUTPUT_KEYS = frozenset({
    "evidence_ref",
    "evidence_event_id",
    "actor",
    "actor_id",
    "environment_fingerprint",
    "password",
    "token",
    "api_key",
    "secret",
    "credential",
    "private_key",
    "connection_string",
})
ACTIONABLE_STATUSES = frozenset({
    "READY_TO_EXECUTE",
    "EXECUTION_COORDINATION_STARTED",
    "EVIDENCE_LINKED",
    "REVIEW_REQUIRED",
    "REVIEW_COORDINATION_READY",
    "RATIFICATION_REQUIRED",
    "EVIDENCE_EXPIRED",
    "INTEGRITY_FAILURE",
    "CONTROL_BLOCKED",
})


class EvidenceOperationsBoardError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().casefold() in FORBIDDEN_OUTPUT_KEYS:
                findings.append(child_path)
            findings.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return findings


class EvidenceOperationsBoard:
    """Read model operativo de OPS1 + RC8.1; nunca escribe en campaña o dossiers."""

    def __init__(
        self,
        root: str | Path,
        *,
        campaign_id: str | None = None,
        ledger_path: str | Path | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.campaign_id = str(campaign_id or "").strip() or None
        try:
            self.runbook = EvidenceExecutionRunbook(self.root)
            self.runbook_payload = self.runbook.build()
            self.ledger = EvidenceCampaignLedger(self.root, ledger_path=ledger_path)
        except (EvidenceExecutionRunbookError, EvidenceCampaignError) as exc:
            raise EvidenceOperationsBoardError(str(exc)) from exc

    def _campaign_context(self) -> tuple[dict[str, Any], dict[str, str]]:
        if not self.campaign_id:
            return {
                "bound": False,
                "status": "CAMPAIGN_REQUIRED",
                "plan_hash_current": True,
                "verified_controls": 0,
                "total_controls": int(self.runbook_payload["controls"]),
                "dependency_constraints_active": True,
                "explicitly_blocked_controls": [],
                "global_blockers": [],
                "release_authorized": False,
                "commercial_authorized": False,
            }, {}

        integrity = self.ledger.verify_chain()
        if not integrity.get("valid"):
            raise EvidenceOperationsBoardError("La cadena RC8.1 está alterada; el tablero falla cerrado.")

        try:
            state = self.ledger.campaign_state(self.campaign_id)
            events = self.ledger._campaign_events(self.campaign_id)
        except (EvidenceCampaignError, EvidenceCampaignIntegrityError) as exc:
            raise EvidenceOperationsBoardError(str(exc)) from exc

        latest: dict[str, str] = {}
        for row in events:
            ref = str(row.get("control_ref") or "")
            event_type = str(row.get("event_type") or "")
            if ref:
                latest[ref] = event_type

        safe_state = {
            "bound": True,
            "campaign_id": self.campaign_id,
            "status": str(state.get("status") or "UNKNOWN"),
            "plan_hash_current": bool(state.get("plan_hash_current")),
            "verified_controls": int(state.get("verified_controls") or 0),
            "total_controls": int(state.get("total_controls") or self.runbook_payload["controls"]),
            "dependency_constraints_active": bool(state.get("dependency_constraints_active")),
            "explicitly_blocked_controls": list(state.get("explicitly_blocked_controls") or []),
            "global_blockers": list(state.get("global_blockers") or []),
            "release_authorized": False,
            "commercial_authorized": False,
        }
        return safe_state, latest

    def _audit(self) -> dict[str, Any]:
        try:
            dossier = (
                EvidenceAuditDossier(self.root, campaign_ledger=self.ledger)
                if self.campaign_id
                else EvidenceAuditDossier(self.root)
            )
            return dossier.build(campaign_id=self.campaign_id)
        except (EvidenceCampaignError, EvidenceCampaignIntegrityError) as exc:
            raise EvidenceOperationsBoardError(str(exc)) from exc

    @staticmethod
    def _work_status(
        *,
        campaign_bound: bool,
        campaign_status: str,
        audit_row: dict[str, Any],
        latest_event: str | None,
        explicitly_blocked: bool,
    ) -> str:
        status = str(audit_row.get("status") or "PENDING").upper()
        if status == "VERIFIED":
            return "VERIFIED"
        if campaign_status == "ABORTED":
            return "CAMPAIGN_ABORTED"
        if explicitly_blocked or latest_event == "CONTROL_BLOCKED":
            return "CONTROL_BLOCKED"
        if status == "BLOCKED_BY_PLAN_DRIFT":
            return "PLAN_DRIFT"
        if status == "BLOCKED_BY_DEPENDENCY":
            return "WAITING_FOR_DEPENDENCY"
        if status == "TAMPERED":
            return "INTEGRITY_FAILURE"
        if status == "EXPIRED":
            return "EVIDENCE_EXPIRED"
        if status == "REVIEW_REQUIRED":
            return "REVIEW_REQUIRED"
        if status == "RATIFICATION_REQUIRED":
            return "RATIFICATION_REQUIRED"
        if not campaign_bound:
            return "CAMPAIGN_REQUIRED"
        if latest_event == "CONTROL_REVIEW_READY":
            return "REVIEW_COORDINATION_READY"
        if bool(audit_row.get("campaign_evidence_linked")) or latest_event == "EVIDENCE_LINKED":
            return "EVIDENCE_LINKED"
        if latest_event == "CONTROL_STARTED":
            return "EXECUTION_COORDINATION_STARTED"
        return "READY_TO_EXECUTE"

    @staticmethod
    def _next_action(status: str) -> str:
        return {
            "CAMPAIGN_REQUIRED": "CREATE_CAMPAIGN",
            "READY_TO_EXECUTE": "EXECUTE_EXTERNAL_CONTROL",
            "EXECUTION_COORDINATION_STARTED": "COMPLETE_EXTERNAL_EXECUTION_AND_BUNDLE",
            "EVIDENCE_LINKED": "COMPLETE_CANONICAL_REVIEW",
            "REVIEW_REQUIRED": "COMPLETE_CANONICAL_REVIEW",
            "REVIEW_COORDINATION_READY": "COMPLETE_CANONICAL_REVIEW",
            "RATIFICATION_REQUIRED": "COMPLETE_CANONICAL_RATIFICATION",
            "WAITING_FOR_DEPENDENCY": "WAIT_FOR_PREREQUISITE_VERIFICATION",
            "CONTROL_BLOCKED": "RESOLVE_EXTERNAL_BLOCK",
            "PLAN_DRIFT": "REBASE_CAMPAIGN_ON_CURRENT_PLAN",
            "EVIDENCE_EXPIRED": "REEXECUTE_OR_REPLACE_EXPIRED_EVIDENCE",
            "INTEGRITY_FAILURE": "QUARANTINE_AND_REMEDIATE_EVIDENCE",
            "CAMPAIGN_ABORTED": "NO_FURTHER_EXECUTION",
            "VERIFIED": "NONE",
        }.get(status, "ASSESS_CANONICAL_STATE")

    @staticmethod
    def _next_role(status: str, packet: dict[str, Any]) -> str | None:
        if status in {"READY_TO_EXECUTE", "EXECUTION_COORDINATION_STARTED", "EVIDENCE_EXPIRED", "INTEGRITY_FAILURE"}:
            return str(packet["executor_role"])
        if status in {"EVIDENCE_LINKED", "REVIEW_REQUIRED", "REVIEW_COORDINATION_READY"}:
            return str(packet["reviewer_role"])
        return None

    def build(self) -> dict[str, Any]:
        campaign, latest_events = self._campaign_context()
        audit = self._audit()
        audit_rows = {str(row["control_ref"]): row for row in audit.get("controls") or []}
        explicit = set(campaign["explicitly_blocked_controls"])

        controls: list[dict[str, Any]] = []
        for packet in self.runbook_payload["packets"]:
            ref = str(packet["control_ref"])
            row = dict(audit_rows.get(ref) or {
                "control_ref": ref,
                "status": "PENDING",
                "dependency_blockers": list(packet.get("prerequisites") or []),
                "campaign_evidence_linked": False,
            })
            work_status = self._work_status(
                campaign_bound=bool(campaign["bound"]),
                campaign_status=str(campaign["status"]),
                audit_row=row,
                latest_event=latest_events.get(ref),
                explicitly_blocked=ref in explicit,
            )
            controls.append({
                "sequence": int(packet["sequence"]),
                "wave": int(packet["wave"]),
                "control_ref": ref,
                "source_framework": packet["source_framework"],
                "source_id": packet["source_id"],
                "domain": packet["domain"],
                "environment": packet["environment"],
                "release_scope": packet["release_scope"],
                "executor_role": packet["executor_role"],
                "reviewer_role": packet["reviewer_role"],
                "prerequisites": list(packet.get("prerequisites") or []),
                "dependency_blockers": list(row.get("dependency_blockers") or []),
                "work_status": work_status,
                "next_action": self._next_action(work_status),
                "next_role": self._next_role(work_status, packet),
                "evidence_verified": work_status == "VERIFIED",
                "campaign_coordination_state": latest_events.get(ref) if campaign["bound"] else None,
                "artifact_type": packet["artifact_type"],
                "required_artifacts": list(packet["required_artifacts"]),
                "max_validity_days": packet["max_validity_days"],
                "redaction_policy": packet["redaction_policy"],
                "assignment_status": "ROLE_DEFINED_PERSON_NOT_ASSIGNED",
            })

        status_counts: dict[str, int] = {}
        for row in controls:
            status_counts[row["work_status"]] = status_counts.get(row["work_status"], 0) + 1

        waves: list[dict[str, Any]] = []
        for wave in self.runbook_payload["waves"]:
            number = int(wave["wave"])
            members = [row for row in controls if row["wave"] == number]
            waves.append({
                "wave": number,
                "controls": [row["control_ref"] for row in members],
                "count": len(members),
                "verified": sum(row["work_status"] == "VERIFIED" for row in members),
                "actionable": sum(row["work_status"] in ACTIONABLE_STATUSES for row in members),
                "waiting": sum(row["work_status"] in {"WAITING_FOR_DEPENDENCY", "CAMPAIGN_REQUIRED"} for row in members),
                "blocked": sum(row["work_status"] in {
                    "CONTROL_BLOCKED", "PLAN_DRIFT", "INTEGRITY_FAILURE", "CAMPAIGN_ABORTED"
                } for row in members),
            })

        next_actions = [
            {
                "control_ref": row["control_ref"],
                "wave": row["wave"],
                "status": row["work_status"],
                "action": row["next_action"],
                "role": row["next_role"],
            }
            for row in controls
            if row["next_action"] not in {"NONE", "WAIT_FOR_PREREQUISITE_VERIFICATION", "NO_FURTHER_EXECUTION"}
        ]

        result = {
            "schema": BOARD_SCHEMA,
            "schema_version": 1,
            "mode": "CAMPAIGN_BOUND" if campaign["bound"] else "TEMPLATE",
            "source_runbook_schema": self.runbook_payload["schema"],
            "source_runbook_sha256": self.runbook_payload["runbook_sha256"],
            "source_plan_sha256": self.runbook_payload["source_plan_sha256"],
            "campaign": campaign,
            "controls": controls,
            "waves": waves,
            "summary": {
                "total_controls": len(controls),
                "verified_controls": sum(row["work_status"] == "VERIFIED" for row in controls),
                "status_counts": status_counts,
                "next_actions": next_actions,
                "production_evidence_complete": bool(audit.get("summary", {}).get("real_production_evidence_complete")),
                "commercial_evidence_complete": bool(audit.get("summary", {}).get("commercial_evidence_complete")),
                "release_authorized": False,
                "commercial_authorized": False,
            },
            "governance": {
                "derived_from_ops1_and_rc8_1": True,
                "board_is_read_only": True,
                "board_is_not_evidence": True,
                "board_is_not_campaign_ledger": True,
                "board_is_not_review_approval": True,
                "board_is_not_release_ratification": True,
                "board_is_not_production_authorization": True,
                "board_is_not_payment_authorization": True,
                "contains_actor_identifier": False,
                "contains_environment_fingerprint": False,
                "contains_evidence_reference": False,
                "contains_evidence_payload": False,
                "mutates_campaign": False,
                "mutates_evidence_ledgers": False,
                "mutates_release_metadata": False,
            },
        }
        forbidden = _forbidden_paths(result)
        if forbidden:
            raise EvidenceOperationsBoardError(
                "El tablero contiene claves prohibidas: " + ", ".join(forbidden)
            )
        result["board_sha256"] = sha256(_canonical_json(result).encode("utf-8")).hexdigest()
        return result

    def to_markdown(self, board: dict[str, Any] | None = None) -> str:
        data = board or self.build()
        campaign = data["campaign"]
        lines = [
            "# LegalAIZ.it — Mesa operativa de evidencia V1",
            "",
            f"- Modo: **{data['mode']}**",
            f"- Campaña: **{campaign['status']}**",
            f"- Controles verificados: **{data['summary']['verified_controls']}/{data['summary']['total_controls']}**",
            f"- Digest del tablero: `{data['board_sha256']}`",
            "",
            "> Este tablero es una vista derivada y read-only. No ejecuta controles, no registra evidencia, no aprueba, no ratifica y no autoriza producción ni pagos.",
            "",
        ]
        if campaign["bound"]:
            lines.extend([
                f"- Campaign ID: `{campaign['campaign_id']}`",
                f"- Plan vigente para campaña: **{'sí' if campaign['plan_hash_current'] else 'no'}**",
                "",
            ])
        else:
            lines.extend([
                "- Siguiente paso global: **crear una campaña RC8.1** antes de coordinar ejecución.",
                "",
            ])

        lines.extend([
            "## Leyenda operativa",
            "",
            "- `CAMPAIGN_REQUIRED`: existe planificación, pero todavía no una campaña fijada.",
            "- `READY_TO_EXECUTE`: prerequisitos satisfechos; la ejecución real sigue siendo externa.",
            "- `EXECUTION_COORDINATION_STARTED`: se registró coordinación, no ejecución material.",
            "- `EVIDENCE_LINKED`: existe vínculo de coordinación; aún no equivale a aprobación.",
            "- `REVIEW_REQUIRED` / `REVIEW_COORDINATION_READY`: revisión humana canónica pendiente.",
            "- `RATIFICATION_REQUIRED`: ratificación del dossier pendiente.",
            "- `WAITING_FOR_DEPENDENCY`: depende de otro control todavía no verificado.",
            "- `VERIFIED`: evidencia canónica vigente y verificada.",
            "- `CONTROL_BLOCKED`, `PLAN_DRIFT`, `INTEGRITY_FAILURE`, `EVIDENCE_EXPIRED`: requieren remediación.",
            "",
            "## Olas",
            "",
        ])

        by_ref = {row["control_ref"]: row for row in data["controls"]}
        for wave in data["waves"]:
            lines.extend([
                f"### Ola {wave['wave']} · {wave['count']} controles",
                "",
                f"- Verificados: {wave['verified']}",
                f"- Accionables: {wave['actionable']}",
                f"- En espera: {wave['waiting']}",
                f"- Bloqueados: {wave['blocked']}",
                "",
            ])
            for ref in wave["controls"]:
                row = by_ref[ref]
                role = row["next_role"] or "según dossier/gobierno canónico"
                blockers = ", ".join(row["dependency_blockers"]) or "ninguno"
                lines.extend([
                    f"#### `{ref}` · `{row['work_status']}`",
                    "",
                    f"- Dominio: `{row['domain']}`",
                    f"- Ejecuta: `{row['executor_role']}`",
                    f"- Revisa: `{row['reviewer_role']}`",
                    f"- Dependencias pendientes: {blockers}",
                    f"- Siguiente acción: `{row['next_action']}`",
                    f"- Rol siguiente: `{role}`",
                    f"- Persona asignada: **no gestionada por OPS2**",
                    "",
                ])

        lines.extend([
            "## Límites de gobierno",
            "",
            "La mesa no sustituye RC2/RC7, no modifica RC8.1, no altera RC9/RC10 y no cambia las decisiones humanas versionadas. Incluso con 22/22 controles verificados, `REAL_PRODUCTION_AUTHORIZED` y `REAL_PAYMENTS_AUTHORIZED` siguen requiriendo sus decisiones separadas.",
            "",
        ])
        return "\n".join(lines)


__all__ = [
    "ACTIONABLE_STATUSES",
    "BOARD_SCHEMA",
    "EvidenceOperationsBoard",
    "EvidenceOperationsBoardError",
]
