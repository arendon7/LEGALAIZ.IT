from __future__ import annotations

from typing import Any

from legalai_platform.evidence_orchestration_v1_rc8 import (
    CAMPAIGN_SCHEMA,
    EVENT_TYPES,
    EvidenceAuditDossier,
    EvidenceCampaignError,
    EvidenceCampaignIntegrityError,
    EvidenceCampaignLedger as EvidenceCampaignLedgerRC8,
    EvidenceCampaignPermissionError,
)


STATE_SCHEMA = "legalaiz-v1-rc8-1-campaign-state-v1"


class EvidenceCampaignLedger(EvidenceCampaignLedgerRC8):
    """RC8.1: read model de campaña con semántica de bloqueo no ambigua.

    Conserva sin cambios el ledger, los tipos de evento, los permisos, el plan
    RC6, la evidencia RC2/RC7 y todas las reglas de ejecución de RC8. Únicamente
    refina el estado agregado de campaña: una dependencia pendiente bloquea el
    control afectado, no la campaña completa.
    """

    def campaign_state(self, campaign_id: str) -> dict[str, Any]:
        created = self._campaign_created(campaign_id)
        events = self._campaign_events(campaign_id)
        payload = created.get("payload") or {}
        plan_current = str(payload.get("plan_sha256") or "") == self.plan_sha256
        aborted = any(row.get("event_type") == "CAMPAIGN_ABORTED" for row in events)

        latest_by_control: dict[str, dict[str, Any]] = {}
        for row in events:
            ref = str(row.get("control_ref") or "")
            if ref:
                latest_by_control[ref] = row

        explicit_block_refs = sorted(
            ref
            for ref, row in latest_by_control.items()
            if row.get("event_type") == "CONTROL_BLOCKED"
        )

        audit = EvidenceAuditDossier(self.root, campaign_ledger=self).build(campaign_id=campaign_id)
        summary = audit.get("summary") or {}
        verified = int(summary.get("verified") or 0)
        dependency_blocked = int(summary.get("dependency_blocked") or 0)

        global_blockers: list[str] = []
        if not plan_current:
            global_blockers.append("PLAN_DRIFT")
        if explicit_block_refs:
            global_blockers.append("EXPLICIT_CONTROL_BLOCK")

        if aborted:
            status = "ABORTED"
        elif global_blockers:
            status = "BLOCKED"
        elif verified == len(self.controls):
            status = "EVIDENCE_COMPLETE"
        elif any(row.get("event_type") == "CONTROL_REVIEW_READY" for row in events):
            status = "READY_FOR_REVIEW"
        elif len(events) > 1:
            status = "IN_PROGRESS"
        else:
            status = "CREATED"

        return {
            "schema": STATE_SCHEMA,
            "campaign_id": campaign_id,
            "status": status,
            "plan_hash_current": plan_current,
            "pinned_plan_sha256": payload.get("plan_sha256"),
            "current_plan_sha256": self.plan_sha256,
            "source_revision": payload.get("source_revision"),
            "environment_fingerprint": payload.get("environment_fingerprint"),
            "events": len(events),
            "verified_controls": verified,
            "total_controls": len(self.controls),
            "dependency_blocked_controls": dependency_blocked,
            "dependency_constraints_active": dependency_blocked > 0,
            "explicitly_blocked_controls": explicit_block_refs,
            "global_blockers": global_blockers,
            "release_authorized": False,
            "commercial_authorized": False,
            "governance": {
                "dependency_block_is_control_local": True,
                "campaign_block_requires_global_or_explicit_blocker": True,
                "evidence_complete_is_not_release_authorization": True,
                "ledger_and_event_semantics_inherited_from_rc8": True,
            },
        }


__all__ = [
    "CAMPAIGN_SCHEMA",
    "EVENT_TYPES",
    "STATE_SCHEMA",
    "EvidenceAuditDossier",
    "EvidenceCampaignError",
    "EvidenceCampaignIntegrityError",
    "EvidenceCampaignLedger",
    "EvidenceCampaignPermissionError",
]
