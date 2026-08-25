from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from legalai_platform.evidence_orchestration_v1_rc8 import (
    EvidenceAuditDossier,
    EvidenceCampaignError,
    EvidenceCampaignLedger,
)
from legalai_platform.release_readiness_v1_rc7 import assess_release_readiness as assess_rc7_release_readiness


ROOT = Path(__file__).resolve().parents[1]
RC8_ORCHESTRATION_BLOCKER = "RC8_EVIDENCE_ORCHESTRATION_INVALID"


def _empty_orchestration(error: str) -> dict[str, Any]:
    return {
        "structurally_ready": False,
        "controls": 0,
        "rc2_controls": 0,
        "rc4_controls": 0,
        "verified": 0,
        "campaign_ledger_integrity": "invalid",
        "campaigns": 0,
        "task_packets": 0,
        "task_packets_embed_evidence": False,
        "real_production_evidence_complete": False,
        "commercial_evidence_complete": False,
        "error": error,
    }


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """RC8 añade orquestación auditable sin convertir coordinación en autorización."""

    root = Path(root or ROOT)
    report = deepcopy(assess_rc7_release_readiness(root))
    try:
        ledger = EvidenceCampaignLedger(root)
        integrity = ledger.verify_chain()
        packets = ledger.all_task_packets()
        audit = EvidenceAuditDossier(root).build()
        packet_refs = [str(row.get("control_ref") or "") for row in packets]
        packet_evidence = any(row.get("evidence_ref") not in (None, "") for row in packets)
        campaigns = len({
            str(row.get("campaign_id") or "")
            for row in ledger._read_events()
            if row.get("event_type") == "CAMPAIGN_CREATED" and str(row.get("campaign_id") or "")
        })
        structural = bool(
            integrity.get("valid")
            and len(packets) == 22
            and len(packet_refs) == len(set(packet_refs)) == 22
            and not packet_evidence
            and audit.get("control_count") == 22
            and audit.get("rc2_count") == 10
            and audit.get("rc4_count") == 12
        )
        orchestration = {
            "structurally_ready": structural,
            "controls": int(audit.get("control_count") or 0),
            "rc2_controls": int(audit.get("rc2_count") or 0),
            "rc4_controls": int(audit.get("rc4_count") or 0),
            "verified": int((audit.get("summary") or {}).get("verified") or 0),
            "campaign_ledger_integrity": "valid" if integrity.get("valid") else "invalid",
            "campaigns": campaigns,
            "task_packets": len(packets),
            "task_packets_embed_evidence": packet_evidence,
            "real_production_evidence_complete": bool((audit.get("summary") or {}).get("real_production_evidence_complete")),
            "commercial_evidence_complete": bool((audit.get("summary") or {}).get("commercial_evidence_complete")),
            "error": None,
        }
    except (EvidenceCampaignError, OSError, ValueError, TypeError) as exc:
        orchestration = _empty_orchestration(type(exc).__name__)

    candidate = report["code_release_candidate"]
    checks = list(candidate.get("checks") or [])
    checks.extend([
        {
            "key": "rc8_evidence_orchestration_structure",
            "passed": bool(orchestration["structurally_ready"]),
            "detail": f"controls={orchestration['controls']} rc2={orchestration['rc2_controls']} rc4={orchestration['rc4_controls']}",
        },
        {
            "key": "rc8_operator_packets_do_not_embed_evidence",
            "passed": orchestration["task_packets"] == 22 and not orchestration["task_packets_embed_evidence"],
            "detail": f"task_packets={orchestration['task_packets']} embedded_evidence={orchestration['task_packets_embed_evidence']}",
        },
        {
            "key": "rc8_campaign_ledger_integrity",
            "passed": orchestration["campaign_ledger_integrity"] == "valid",
            "detail": f"campaign_ledger_integrity={orchestration['campaign_ledger_integrity']}",
        },
    ])
    candidate["checks"] = checks
    candidate["ready"] = all(bool(row.get("passed")) for row in checks)
    candidate["status"] = "RC_CODE_READY" if candidate["ready"] else "RC_CODE_BLOCKED"

    if not candidate["ready"]:
        real = report["real_legal_production"]
        real["blockers"] = list(dict.fromkeys(list(real.get("blockers") or []) + [RC8_ORCHESTRATION_BLOCKER]))
        real["ready"] = False
        real["status"] = "REAL_PRODUCTION_BLOCKED"
        commercial = report["commercial_v1"]
        commercial["blockers"] = list(dict.fromkeys(["REAL_LEGAL_PRODUCTION_NOT_READY"] + list(commercial.get("blockers") or [])))
        commercial["ready"] = False
        commercial["status"] = "COMMERCIAL_V1_BLOCKED"

    report["schema"] = "legalaiz-v1-release-readiness-report-v6"
    report["evidence_orchestration"] = orchestration
    governance = report["governance"]
    governance["campaign_events_are_coordination_only"] = True
    governance["campaign_evidence_link_is_not_registration"] = True
    governance["campaign_review_ready_is_not_approval"] = True
    governance["evidence_complete_is_not_release_authorization"] = True
    governance["campaign_plan_hash_is_pinned"] = True
    governance["campaign_dependencies_come_only_from_rc6"] = True
    governance["campaign_cannot_mutate_external_evidence_ledgers"] = True
    governance["campaign_cannot_mutate_release_metadata"] = True
    governance["campaign_cannot_authorize_real_production"] = True
    governance["campaign_cannot_authorize_real_payments"] = True

    return report


__all__ = ["RC8_ORCHESTRATION_BLOCKER", "assess_release_readiness"]
