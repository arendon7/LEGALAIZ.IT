from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from legalai_platform.evidence_orchestration_v1_rc8 import EvidenceAuditDossier
from legalai_platform.evidence_orchestration_v1_rc8_1 import (
    EvidenceCampaignError,
    EvidenceCampaignLedger,
)
from legalai_platform.release_readiness_v1_rc8 import assess_release_readiness


POLICY_SCHEMA = "legalaiz-v1-rc9-evidence-audit-pack-policy-v1"
PACK_SCHEMA = "legalaiz-v1-rc9-evidence-audit-pack-v1"
MARKDOWN_SCHEMA = "legalaiz-v1-rc9-evidence-audit-markdown-v1"


class EvidenceAuditPackError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _key_paths(value: Any, wanted: set[str], path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().casefold()
            child_path = f"{path}.{key}"
            if key_text in wanted:
                findings.append(child_path)
            findings.extend(_key_paths(child, wanted, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_key_paths(child, wanted, f"{path}[{index}]"))
    return findings


def _safe_markdown(value: Any) -> str:
    text = str(value if value is not None else "—")
    return text.replace("|", "\\|").replace("\n", " ").strip() or "—"


def _next_action(status: str) -> str:
    return {
        "VERIFIED": "PRESERVE_EVIDENCE_FRESHNESS",
        "BLOCKED_BY_DEPENDENCY": "VERIFY_PREREQUISITES",
        "BLOCKED_BY_PLAN_DRIFT": "REVIEW_PLAN_DRIFT_AND_RECREATE_CAMPAIGN",
        "MISSING": "EXECUTE_CONTROL_AND_REGISTER_EVIDENCE",
        "REVIEW_REQUIRED": "COMPLETE_INDEPENDENT_REVIEW",
        "RATIFICATION_REQUIRED": "COMPLETE_RELEASE_RATIFICATION",
        "TAMPERED": "REPLACE_INVALID_EVIDENCE",
        "EXPIRED": "REEXECUTE_CONTROL_AND_REPLACE_EVIDENCE",
        "PENDING": "CONTINUE_CANONICAL_EVIDENCE_WORKFLOW",
    }.get(str(status or ""), "REVIEW_CONTROL_STATE")


def _authorization_view(section: Mapping[str, Any]) -> dict[str, Any]:
    decision = section.get("authorization_decision") or {}
    return {
        "release_status": str(section.get("status") or "UNKNOWN"),
        "ready": bool(section.get("ready")),
        "decision_status": str(decision.get("decision_status") or "MISSING"),
        "decision_source": str(decision.get("source") or "MISSING"),
        "metadata_authorized": bool(decision.get("metadata_authorized")),
        "decision_evidence_present": bool(decision.get("evidence_present")),
        "provenance_valid": bool(decision.get("provenance_valid")),
        "state_consistent": bool(decision.get("state_consistent")),
        "unauthorized_promotion": bool(decision.get("unauthorized_promotion")),
        "blockers": [str(item) for item in section.get("blockers") or []],
    }


class EvidenceAuditPack:
    """Compone un snapshot de auditoría redactado sin modificar fuentes de verdad.

    El pack consume RC6/RC2/RC7/RC8.1 y la procedencia de autorización existente.
    Nunca registra evidencia, aprueba, ratifica ni altera release metadata.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        policy_path = self.root / "config" / "v1" / "rc9_evidence_audit_pack_policy.json"
        if not policy_path.is_file():
            raise EvidenceAuditPackError("Falta la política RC9 de audit pack.")
        try:
            self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceAuditPackError("No fue posible leer la política RC9.") from exc
        self._validate_policy()
        try:
            self.ledger = EvidenceCampaignLedger(self.root)
            self.audit = EvidenceAuditDossier(self.root, campaign_ledger=self.ledger)
        except EvidenceCampaignError as exc:
            raise EvidenceAuditPackError(str(exc)) from exc

    def _validate_policy(self) -> None:
        policy = self.policy
        if policy.get("schema") != POLICY_SCHEMA or int(policy.get("schema_version") or 0) != 1:
            raise EvidenceAuditPackError("Política RC9 inválida.")
        if int(policy.get("expected_control_count") or 0) != 22:
            raise EvidenceAuditPackError("RC9 debe cubrir exactamente 22 controles.")
        counts = policy.get("expected_framework_counts") or {}
        if counts != {"RC2": 10, "RC4": 12}:
            raise EvidenceAuditPackError("RC9 perdió la cobertura 10 RC2 + 12 RC4.")
        if set(policy.get("formats") or []) != {"json", "markdown"}:
            raise EvidenceAuditPackError("RC9 debe conservar JSON y Markdown.")
        forbidden = {str(item).strip().casefold() for item in policy.get("forbidden_output_keys") or []}
        required_forbidden = {
            "actor", "actors", "evidence_event_id", "evidence_path", "bundle_path",
            "manifest_path", "environment_fingerprint", "password", "token", "api_key",
            "secret", "credential", "private_key", "connection_string",
        }
        if not required_forbidden.issubset(forbidden):
            raise EvidenceAuditPackError("La política RC9 perdió reglas mínimas de redacción.")
        governance = policy.get("governance") or {}
        required_true = {
            "read_only", "deterministic_snapshot", "evidence_payloads_forbidden",
            "evidence_artifact_hashes_forbidden", "actor_identifiers_forbidden",
            "environment_fingerprint_forbidden", "authorization_evidence_reference_forbidden",
            "control_statuses_are_derived_not_written", "campaign_state_is_derived_not_written",
            "audit_pack_cannot_execute_controls", "audit_pack_cannot_register_evidence",
            "audit_pack_cannot_approve_or_ratify_evidence", "audit_pack_cannot_mutate_release_metadata",
            "audit_pack_cannot_authorize_real_production", "audit_pack_cannot_authorize_real_payments",
            "evidence_complete_is_not_release_authorization",
        }
        missing = sorted(key for key in required_true if governance.get(key) is not True)
        if missing:
            raise EvidenceAuditPackError("Gobierno RC9 incompleto: " + ", ".join(missing))

    @property
    def forbidden_output_keys(self) -> set[str]:
        return {str(item).strip().casefold() for item in self.policy.get("forbidden_output_keys") or []}

    def _validate_output(self, payload: Mapping[str, Any]) -> None:
        findings = _key_paths(payload, self.forbidden_output_keys)
        if findings:
            raise EvidenceAuditPackError("El audit pack contiene claves prohibidas: " + ", ".join(findings))
        controls = payload.get("controls") or []
        if len(controls) != 22:
            raise EvidenceAuditPackError("El audit pack no contiene los 22 controles canónicos.")
        frameworks = {
            "RC2": sum(1 for row in controls if row.get("source_framework") == "RC2"),
            "RC4": sum(1 for row in controls if row.get("source_framework") == "RC4"),
        }
        if frameworks != {"RC2": 10, "RC4": 12}:
            raise EvidenceAuditPackError("El audit pack perdió el superset RC2 + RC4.")

    def build(self, *, campaign_id: str | None = None) -> dict[str, Any]:
        integrity = self.ledger.verify_chain()
        if not integrity.get("valid"):
            raise EvidenceAuditPackError("El ledger de campaña RC8/RC8.1 no supera integridad; audit pack fail-closed.")

        try:
            audit = self.audit.build(campaign_id=campaign_id)
            campaign_state = self.ledger.campaign_state(campaign_id) if campaign_id else None
        except EvidenceCampaignError as exc:
            raise EvidenceAuditPackError(str(exc)) from exc

        readiness = assess_release_readiness(self.root)
        controls: list[dict[str, Any]] = []
        for row in audit.get("controls") or []:
            status = str(row.get("status") or "PENDING")
            controls.append({
                "control_ref": str(row.get("control_ref") or ""),
                "source_framework": str(row.get("source_framework") or ""),
                "source_id": str(row.get("source_id") or ""),
                "domain": str(row.get("domain") or ""),
                "release_scope": str(row.get("release_scope") or ""),
                "status": status,
                "prerequisites": [str(item) for item in row.get("prerequisites") or []],
                "dependency_blockers": [str(item) for item in row.get("dependency_blockers") or []],
                "campaign_evidence_linked": bool(row.get("campaign_evidence_linked")),
                "next_action": _next_action(status),
            })

        audit_summary = audit.get("summary") or {}
        campaign_view = None
        if campaign_state:
            campaign_view = {
                "campaign_id": str(campaign_state.get("campaign_id") or ""),
                "status": str(campaign_state.get("status") or "UNKNOWN"),
                "source_revision": str(campaign_state.get("source_revision") or ""),
                "plan_hash_current": bool(campaign_state.get("plan_hash_current")),
                "event_count": int(campaign_state.get("events") or 0),
                "verified_controls": int(campaign_state.get("verified_controls") or 0),
                "total_controls": int(campaign_state.get("total_controls") or 0),
                "dependency_blocked_controls": int(campaign_state.get("dependency_blocked_controls") or 0),
                "dependency_constraints_active": bool(campaign_state.get("dependency_constraints_active")),
                "explicitly_blocked_controls": [
                    str(item) for item in campaign_state.get("explicitly_blocked_controls") or []
                ],
                "global_blockers": [str(item) for item in campaign_state.get("global_blockers") or []],
            }

        real = _authorization_view(readiness.get("real_legal_production") or {})
        commercial = _authorization_view(readiness.get("commercial_v1") or {})
        code = readiness.get("code_release_candidate") or {}

        next_actions: list[str] = []
        if not campaign_id:
            next_actions.append("CREATE_VERSIONED_EVIDENCE_CAMPAIGN")
        elif campaign_view and not campaign_view["plan_hash_current"]:
            next_actions.append("REVIEW_PLAN_DRIFT_AND_CREATE_REPLACEMENT_CAMPAIGN")
        if any(row["status"] == "TAMPERED" for row in controls):
            next_actions.append("REPLACE_INVALID_OR_TAMPERED_EVIDENCE")
        if any(row["status"] == "EXPIRED" for row in controls):
            next_actions.append("REEXECUTE_EXPIRED_CONTROLS")
        if any(row["status"] in {"MISSING", "PENDING"} for row in controls):
            next_actions.append("EXECUTE_PENDING_CONTROLS_AND_REGISTER_CANONICAL_EVIDENCE")
        if any(row["status"] == "REVIEW_REQUIRED" for row in controls):
            next_actions.append("COMPLETE_INDEPENDENT_EVIDENCE_REVIEW")
        if any(row["status"] == "RATIFICATION_REQUIRED" for row in controls):
            next_actions.append("COMPLETE_RELEASE_RATIFICATION")
        if bool(audit_summary.get("real_production_evidence_complete")) and not real["provenance_valid"]:
            next_actions.append("OBTAIN_VERSIONED_HUMAN_PRODUCTION_AUTHORIZATION")
        if bool(audit_summary.get("commercial_evidence_complete")) and not commercial["provenance_valid"]:
            next_actions.append("OBTAIN_VERSIONED_HUMAN_COMMERCIAL_AUTHORIZATION")
        if not next_actions and not (real["ready"] and commercial["ready"]):
            next_actions.append("REVIEW_REMAINING_RELEASE_BLOCKERS")

        core = {
            "campaign": campaign_view,
            "scope": {
                "control_count": len(controls),
                "rc2_controls": sum(1 for row in controls if row["source_framework"] == "RC2"),
                "rc4_controls": sum(1 for row in controls if row["source_framework"] == "RC4"),
                "plan_sha256": str(audit.get("plan_sha256") or ""),
                "plan_schema": str(audit.get("plan_schema") or ""),
                "campaign_bound": bool(campaign_id),
            },
            "evidence": {
                "verified": int(audit_summary.get("verified") or 0),
                "total": int(audit_summary.get("total") or 0),
                "dependency_blocked": int(audit_summary.get("dependency_blocked") or 0),
                "status_counts": {
                    str(key): int(value)
                    for key, value in sorted((audit_summary.get("status_counts") or {}).items())
                },
                "real_production_evidence_complete": bool(
                    audit_summary.get("real_production_evidence_complete")
                ),
                "commercial_evidence_complete": bool(audit_summary.get("commercial_evidence_complete")),
            },
            "controls": controls,
            "release": {
                "code_candidate": {
                    "status": str(code.get("status") or "UNKNOWN"),
                    "ready": bool(code.get("ready")),
                },
                "real_legal_production": real,
                "commercial_v1": commercial,
                "authorization_state_inconsistent": bool(
                    (readiness.get("governance") or {}).get("authorization_state_inconsistent")
                ),
                "unauthorized_promotion_detected": bool(
                    (readiness.get("governance") or {}).get("unauthorized_promotion_detected")
                ),
            },
            "next_actions": list(dict.fromkeys(next_actions)),
            "boundaries": {
                "read_only": True,
                "deterministic_snapshot": True,
                "contains_evidence_payloads": False,
                "contains_evidence_artifact_hashes": False,
                "contains_actor_identifiers": False,
                "contains_environment_fingerprint": False,
                "contains_authorization_evidence_reference": False,
                "executes_controls": False,
                "registers_evidence": False,
                "approves_or_ratifies_evidence": False,
                "mutates_release_metadata": False,
                "authorizes_real_production": False,
                "authorizes_real_payments": False,
                "evidence_complete_is_release_authorization": False,
            },
        }
        self._validate_output(core)
        snapshot_sha256 = sha256(_canonical_json(core).encode("utf-8")).hexdigest()
        pack = {
            "schema": PACK_SCHEMA,
            "schema_version": 1,
            "snapshot_sha256": snapshot_sha256,
            **core,
        }
        self._validate_output(pack)
        return pack

    def to_markdown(self, pack: Mapping[str, Any]) -> str:
        if pack.get("schema") != PACK_SCHEMA:
            raise EvidenceAuditPackError("El payload no es un audit pack RC9 válido.")
        self._validate_output(pack)
        evidence = pack.get("evidence") or {}
        release = pack.get("release") or {}
        real = release.get("real_legal_production") or {}
        commercial = release.get("commercial_v1") or {}
        campaign = pack.get("campaign")

        lines = [
            "# LegalAIZ.it — V1 Evidence Audit Pack",
            "",
            f"Schema de presentación: `{MARKDOWN_SCHEMA}`",
            f"Snapshot: `{_safe_markdown(pack.get('snapshot_sha256'))}`",
            "",
            "## Estado ejecutivo",
            "",
            f"- Código: **{_safe_markdown((release.get('code_candidate') or {}).get('status'))}**.",
            f"- Producción jurídica real: **{_safe_markdown(real.get('release_status'))}**.",
            f"- V1 comercial: **{_safe_markdown(commercial.get('release_status'))}**.",
            f"- Evidencia verificada: **{int(evidence.get('verified') or 0)}/{int(evidence.get('total') or 0)}** controles.",
            f"- Evidencia completa de producción: **{'sí' if evidence.get('real_production_evidence_complete') else 'no'}**.",
            f"- Evidencia completa comercial: **{'sí' if evidence.get('commercial_evidence_complete') else 'no'}**.",
        ]
        if campaign:
            lines.extend([
                f"- Campaña: `{_safe_markdown(campaign.get('campaign_id'))}` · **{_safe_markdown(campaign.get('status'))}**.",
                f"- Plan de campaña vigente: **{'sí' if campaign.get('plan_hash_current') else 'no'}**.",
                f"- Restricciones locales por dependencia: **{int(campaign.get('dependency_blocked_controls') or 0)}**.",
            ])
        else:
            lines.append("- Snapshot no vinculado a una campaña específica.")

        lines.extend([
            "",
            "## Controles de evidencia",
            "",
            "| Control | Dominio | Alcance | Estado | Dependencias pendientes | Próxima acción |",
            "|---|---|---|---|---|---|",
        ])
        for row in pack.get("controls") or []:
            blockers = ", ".join(row.get("dependency_blockers") or []) or "—"
            lines.append(
                "| " + " | ".join([
                    _safe_markdown(row.get("control_ref")),
                    _safe_markdown(row.get("domain")),
                    _safe_markdown(row.get("release_scope")),
                    _safe_markdown(row.get("status")),
                    _safe_markdown(blockers),
                    _safe_markdown(row.get("next_action")),
                ]) + " |"
            )

        lines.extend([
            "",
            "## Procedencia de autorización",
            "",
            "| Gate | Decisión | Fuente | Evidencia de decisión | Procedencia válida | Listo |",
            "|---|---|---|---|---|---|",
            "| Producción jurídica real | "
            + " | ".join([
                _safe_markdown(real.get("decision_status")),
                _safe_markdown(real.get("decision_source")),
                "sí" if real.get("decision_evidence_present") else "no",
                "sí" if real.get("provenance_valid") else "no",
                "sí" if real.get("ready") else "no",
            ])
            + " |",
            "| V1 comercial | "
            + " | ".join([
                _safe_markdown(commercial.get("decision_status")),
                _safe_markdown(commercial.get("decision_source")),
                "sí" if commercial.get("decision_evidence_present") else "no",
                "sí" if commercial.get("provenance_valid") else "no",
                "sí" if commercial.get("ready") else "no",
            ])
            + " |",
            "",
            "## Próximas actuaciones",
            "",
        ])
        for action in pack.get("next_actions") or []:
            lines.append(f"- `{_safe_markdown(action)}`")
        if not pack.get("next_actions"):
            lines.append("- Sin actuación automática derivada. Revisar decisión humana de release.")

        lines.extend([
            "",
            "## Límites de gobierno",
            "",
            "Este reporte es de solo lectura. No ejecuta controles, no registra evidencia, no aprueba ni ratifica evidencia, no modifica metadata de release y no autoriza producción ni pagos. Evidencia completa y autorización son estados jurídicos-operativos distintos.",
            "",
        ])
        rendered = "\n".join(lines)
        forbidden_literals = (
            "evidence_event_id", "evidence_path", "bundle_path", "manifest_path",
            "environment_fingerprint", "connection_string",
        )
        if any(literal in rendered for literal in forbidden_literals):
            raise EvidenceAuditPackError("La presentación Markdown contiene material interno prohibido.")
        return rendered


__all__ = [
    "MARKDOWN_SCHEMA",
    "PACK_SCHEMA",
    "POLICY_SCHEMA",
    "EvidenceAuditPack",
    "EvidenceAuditPackError",
]
