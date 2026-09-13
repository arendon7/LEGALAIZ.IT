from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier, ExternalEvidenceError
from legalai_platform.release_readiness_v1 import assess_release_readiness as assess_base_release_readiness


ROOT = Path(__file__).resolve().parents[1]
RC2_EXTERNAL_BLOCKER_PREFIX = "RC2_EXTERNAL_EVIDENCE:"
RC2_INTEGRITY_BLOCKER = "RC2_EXTERNAL_EVIDENCE_DOSSIER_INTEGRITY"
RC2_POLICY_BLOCKER = "RC2_EXTERNAL_EVIDENCE_POLICY_INVALID"


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _load_rc2_summary(root: Path) -> tuple[dict[str, Any], bool]:
    try:
        dossier = ExternalEvidenceDossier(root)
        return dossier.summary(), True
    except ExternalEvidenceError:
        return {
            "schema": "legalaizit-v1-rc2-external-evidence-summary-v1",
            "assurance": "hardened_v1_rc2",
            "ready": False,
            "passed": 0,
            "total": 0,
            "integrity": "invalid_policy",
            "checks": [],
        }, False


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """Converge RC4 con el dossier RC2 como superset de assurance.

    RC5 no traduce ni da por equivalentes controles de modelos distintos. Para
    producción jurídica real exige simultáneamente el gate RC4 y las diez
    atestaciones append-only RC2. Así se evita que una evolución del inventario
    de evidencia retire controles ya certificados en fases anteriores.
    """

    root = Path(root or ROOT)
    report = deepcopy(assess_base_release_readiness(root))
    rc4_real_ready = bool(report["real_legal_production"].get("ready"))
    rc4_commercial_ready = bool(report["commercial_v1"].get("ready"))

    rc2_summary, rc2_policy_valid = _load_rc2_summary(root)
    rc2_checks = list(rc2_summary.get("checks") or [])
    rc2_control_ids = [str(row.get("key") or "") for row in rc2_checks]
    rc2_integrity_valid = str(rc2_summary.get("integrity") or "invalid") == "valid"
    rc2_inventory_valid = rc2_policy_valid and len(rc2_control_ids) == 10 and len(set(rc2_control_ids)) == 10
    rc2_ready = bool(rc2_summary.get("ready")) and rc2_integrity_valid and rc2_inventory_valid

    rc4_attestation_ids = list(report["real_legal_production"].get("attestations_verified") or {})
    rc4_attestation_ids.extend(list(report["commercial_v1"].get("attestations_verified") or {}))

    candidate = report["code_release_candidate"]
    candidate_checks = list(candidate.get("checks") or [])
    candidate_checks.extend(
        [
            {
                "key": "rc2_external_evidence_policy_valid",
                "passed": rc2_policy_valid,
                "detail": "política RC2 válida" if rc2_policy_valid else "política RC2 ausente o inválida",
            },
            {
                "key": "rc2_external_evidence_inventory_preserved",
                "passed": rc2_inventory_valid,
                "detail": f"rc2_controls={len(rc2_control_ids)} expected=10",
            },
            {
                "key": "rc4_external_attestation_inventory_preserved",
                "passed": len(rc4_attestation_ids) == 12 and len(set(rc4_attestation_ids)) == 12,
                "detail": f"rc4_attestations={len(rc4_attestation_ids)} expected=12",
            },
        ]
    )
    candidate["checks"] = candidate_checks
    candidate["ready"] = all(bool(row.get("passed")) for row in candidate_checks)
    candidate["status"] = "RC_CODE_READY" if candidate["ready"] else "RC_CODE_BLOCKED"

    rc2_blockers: list[str] = []
    if not rc2_policy_valid:
        rc2_blockers.append(RC2_POLICY_BLOCKER)
    elif not rc2_integrity_valid:
        rc2_blockers.append(RC2_INTEGRITY_BLOCKER)
    rc2_blockers.extend(
        RC2_EXTERNAL_BLOCKER_PREFIX + str(row.get("key") or "UNKNOWN")
        for row in rc2_checks
        if not bool(row.get("passed"))
    )

    real = report["real_legal_production"]
    real["blockers"] = _dedupe(list(real.get("blockers") or []) + rc2_blockers)
    real["ready"] = bool(candidate["ready"] and rc4_real_ready and rc2_ready)
    real["status"] = "REAL_PRODUCTION_READY" if real["ready"] else "REAL_PRODUCTION_BLOCKED"
    real["legacy_rc2_evidence_gate"] = {
        "required": True,
        "ready": rc2_ready,
        "policy_valid": rc2_policy_valid,
        "integrity": str(rc2_summary.get("integrity") or "invalid"),
        "passed": int(rc2_summary.get("passed") or 0),
        "total": int(rc2_summary.get("total") or 0),
        "checks": rc2_checks,
    }

    commercial = report["commercial_v1"]
    commercial_blockers = [
        item for item in list(commercial.get("blockers") or []) if item != "REAL_LEGAL_PRODUCTION_NOT_READY"
    ]
    if not real["ready"]:
        commercial_blockers.insert(0, "REAL_LEGAL_PRODUCTION_NOT_READY")
    commercial["blockers"] = _dedupe(commercial_blockers)
    commercial["ready"] = bool(candidate["ready"] and rc4_commercial_ready and real["ready"])
    commercial["status"] = "COMMERCIAL_V1_READY" if commercial["ready"] else "COMMERCIAL_V1_BLOCKED"

    report["schema"] = "legalaiz-v1-release-readiness-report-v3"
    report["assurance_superset"] = {
        "strategy": "RC4_PLUS_RC2_INDEPENDENT_GATES",
        "real_production_requires_both": True,
        "rc4_attestation_gate_ready": rc4_real_ready,
        "rc2_dossier_gate_ready": rc2_ready,
        "rc2_policy_valid": rc2_policy_valid,
        "rc4_attestation_count": len(rc4_attestation_ids),
        "rc2_control_count": len(rc2_control_ids),
        "rc2_controls": rc2_control_ids,
        "rule": "Ningún control RC2 se considera sustituido por una atestación RC4 sin una migración de política explícita y versionada.",
    }
    governance = report["governance"]
    governance["legacy_rc2_evidence_required_for_real_production"] = True
    governance["assurance_controls_cannot_be_silently_dropped"] = True

    return report


__all__ = [
    "RC2_EXTERNAL_BLOCKER_PREFIX",
    "RC2_INTEGRITY_BLOCKER",
    "RC2_POLICY_BLOCKER",
    "assess_release_readiness",
]
