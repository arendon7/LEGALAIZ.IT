from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from legalai_platform.evidence_audit_pack_v1_rc9 import (
    EvidenceAuditPack,
    EvidenceAuditPackError,
    PACK_SCHEMA,
)
from legalai_platform.release_readiness_v1_rc8 import assess_release_readiness as assess_rc8_release_readiness


ROOT = Path(__file__).resolve().parents[1]
RC9_AUDIT_PACK_STRUCTURE = "RC9_AUDIT_PACK_STRUCTURE_INVALID"
RC9_AUDIT_PACK_RUNTIME = "RC9_AUDIT_PACK_RUNTIME_INVALID"


def _block_real_and_commercial(report: dict[str, Any], blocker: str) -> None:
    real = report["real_legal_production"]
    real["blockers"] = list(dict.fromkeys(list(real.get("blockers") or []) + [blocker]))
    real["ready"] = False
    real["status"] = "REAL_PRODUCTION_BLOCKED"

    commercial = report["commercial_v1"]
    commercial["blockers"] = list(
        dict.fromkeys(["REAL_LEGAL_PRODUCTION_NOT_READY"] + list(commercial.get("blockers") or []))
    )
    commercial["ready"] = False
    commercial["status"] = "COMMERCIAL_V1_BLOCKED"


def _static_assurance(root: Path) -> dict[str, Any]:
    try:
        packer = EvidenceAuditPack(root)
        controls = list(packer.audit.controls.values())
        rc2 = sum(1 for row in controls if row.get("source_framework") == "RC2")
        rc4 = sum(1 for row in controls if row.get("source_framework") == "RC4")
        governance = packer.policy.get("governance") or {}
        valid = bool(
            len(controls) == 22
            and rc2 == 10
            and rc4 == 12
            and set(packer.policy.get("formats") or []) == {"json", "markdown"}
            and governance.get("read_only") is True
            and governance.get("deterministic_snapshot") is True
            and governance.get("evidence_payloads_forbidden") is True
            and governance.get("actor_identifiers_forbidden") is True
            and governance.get("environment_fingerprint_forbidden") is True
            and governance.get("audit_pack_cannot_authorize_real_production") is True
            and governance.get("audit_pack_cannot_authorize_real_payments") is True
        )
        return {
            "valid": valid,
            "controls": len(controls),
            "rc2_controls": rc2,
            "rc4_controls": rc4,
            "formats": sorted(packer.policy.get("formats") or []),
            "read_only": governance.get("read_only") is True,
            "deterministic_snapshot": governance.get("deterministic_snapshot") is True,
            "redaction_policy_valid": bool(
                governance.get("evidence_payloads_forbidden") is True
                and governance.get("actor_identifiers_forbidden") is True
                and governance.get("environment_fingerprint_forbidden") is True
                and governance.get("authorization_evidence_reference_forbidden") is True
            ),
            "error": None,
        }
    except (EvidenceAuditPackError, OSError, ValueError, TypeError) as exc:
        return {
            "valid": False,
            "controls": 0,
            "rc2_controls": 0,
            "rc4_controls": 0,
            "formats": [],
            "read_only": False,
            "deterministic_snapshot": False,
            "redaction_policy_valid": False,
            "error": type(exc).__name__,
        }


def _runtime_assurance(root: Path) -> dict[str, Any]:
    try:
        packer = EvidenceAuditPack(root)
        first = packer.build()
        second = packer.build()
        stable = first.get("snapshot_sha256") == second.get("snapshot_sha256")
        boundaries = first.get("boundaries") or {}
        valid = bool(
            first.get("schema") == PACK_SCHEMA
            and stable
            and int((first.get("scope") or {}).get("control_count") or 0) == 22
            and boundaries.get("read_only") is True
            and boundaries.get("contains_evidence_payloads") is False
            and boundaries.get("contains_evidence_artifact_hashes") is False
            and boundaries.get("contains_actor_identifiers") is False
            and boundaries.get("contains_environment_fingerprint") is False
            and boundaries.get("contains_authorization_evidence_reference") is False
            and boundaries.get("authorizes_real_production") is False
            and boundaries.get("authorizes_real_payments") is False
        )
        return {
            "valid": valid,
            "schema": str(first.get("schema") or ""),
            "snapshot_sha256": str(first.get("snapshot_sha256") or ""),
            "deterministic": stable,
            "verified": int((first.get("evidence") or {}).get("verified") or 0),
            "total": int((first.get("evidence") or {}).get("total") or 0),
            "campaign_bound": bool((first.get("scope") or {}).get("campaign_bound")),
            "error": None,
        }
    except (EvidenceAuditPackError, OSError, ValueError, TypeError) as exc:
        return {
            "valid": False,
            "schema": "",
            "snapshot_sha256": "",
            "deterministic": False,
            "verified": 0,
            "total": 0,
            "campaign_bound": False,
            "error": type(exc).__name__,
        }


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """RC9 exige auditabilidad estructural y runtime sin convertir reporte en autorización."""

    root = Path(root or ROOT)
    report = deepcopy(assess_rc8_release_readiness(root))
    static = _static_assurance(root)
    runtime = _runtime_assurance(root)

    candidate = report["code_release_candidate"]
    checks = list(candidate.get("checks") or [])
    checks.extend([
        {
            "key": "rc9_evidence_audit_pack_structure",
            "passed": bool(static["valid"]),
            "detail": f"controls={static['controls']} rc2={static['rc2_controls']} rc4={static['rc4_controls']} formats={','.join(static['formats'])}",
        },
        {
            "key": "rc9_evidence_audit_pack_redaction_policy",
            "passed": bool(static["redaction_policy_valid"] and static["read_only"]),
            "detail": f"read_only={static['read_only']} redaction={static['redaction_policy_valid']}",
        },
    ])
    candidate["checks"] = checks
    candidate["ready"] = all(bool(row.get("passed")) for row in checks)
    candidate["status"] = "RC_CODE_READY" if candidate["ready"] else "RC_CODE_BLOCKED"

    if not candidate["ready"]:
        _block_real_and_commercial(report, RC9_AUDIT_PACK_STRUCTURE)
    if not runtime["valid"]:
        _block_real_and_commercial(report, RC9_AUDIT_PACK_RUNTIME)

    report["schema"] = "legalaiz-v1-release-readiness-report-v7"
    report["evidence_audit_pack"] = {
        "structure": static,
        "runtime_snapshot": runtime,
    }
    governance = report["governance"]
    governance["audit_pack_is_read_only"] = True
    governance["audit_pack_snapshot_is_deterministic"] = True
    governance["audit_pack_contains_evidence_payloads"] = False
    governance["audit_pack_contains_actor_identifiers"] = False
    governance["audit_pack_contains_environment_fingerprint"] = False
    governance["audit_pack_contains_authorization_evidence_reference"] = False
    governance["audit_pack_runtime_health_is_not_code_readiness"] = True
    governance["audit_pack_runtime_health_is_required_for_go_live"] = True
    governance["audit_pack_cannot_authorize_real_production"] = True
    governance["audit_pack_cannot_authorize_real_payments"] = True

    return report


__all__ = [
    "RC9_AUDIT_PACK_RUNTIME",
    "RC9_AUDIT_PACK_STRUCTURE",
    "assess_release_readiness",
]
