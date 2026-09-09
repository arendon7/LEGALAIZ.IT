from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from legalai_platform.external_attestation_dossier_v1_rc7 import ExternalAttestationDossier, ExternalAttestationError
from legalai_platform.external_evidence_bundle_v1 import EvidenceBundleError, EvidenceBundleValidator
from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier, ExternalEvidenceError
from legalai_platform.release_readiness_v1_rc6 import assess_release_readiness as assess_rc6_release_readiness


ROOT = Path(__file__).resolve().parents[1]
RC7_RC2_BUNDLE_PREFIX = "RC7_RC2_BUNDLE:"
RC7_RC4_LEDGER_INTEGRITY = "RC7_RC4_ATTESTATION_LEDGER_INTEGRITY"


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _rc2_bundle_state(root: Path) -> dict[str, Any]:
    try:
        dossier = ExternalEvidenceDossier(root)
        internal = dossier.internal_summary()
    except ExternalEvidenceError:
        return {
            "available": False,
            "integrity": "invalid",
            "bundle_validated": 0,
            "total": 10,
            "checks": [],
        }
    checks: list[dict[str, Any]] = []
    validated_count = 0
    for row in internal.get("checks") or []:
        control = str(row.get("key") or "")
        evidence_path = str(row.get("evidence_path") or "").strip()
        bundle_valid = False
        if evidence_path:
            candidate = Path(evidence_path.replace("\\", "/"))
            if candidate.name == "manifest.json" and candidate.parent.as_posix() not in {"", "."}:
                try:
                    validator = EvidenceBundleValidator(root, dossier.evidence_root, now_factory=dossier.now_factory)
                    bundle = validator.validate(candidate.parent.as_posix(), expected_control_ref=f"RC2:{control}")
                    bundle_valid = bundle.manifest_sha256 == str(row.get("evidence_sha256") or "")
                except (EvidenceBundleError, OSError, ValueError, TypeError):
                    bundle_valid = False
        if bundle_valid:
            validated_count += 1
        checks.append(
            {
                "key": control,
                "rc2_gate_passed": bool(row.get("passed")),
                "bundle_valid": bundle_valid,
                "status": (
                    "BUNDLE_VALIDATED"
                    if bundle_valid
                    else ("NO_ACTIVE_BUNDLE" if not evidence_path else "BUNDLE_INVALID")
                ),
            }
        )
    return {
        "available": True,
        "integrity": str(internal.get("integrity") or "invalid"),
        "bundle_validated": validated_count,
        "total": len(checks),
        "checks": checks,
    }


def _rc4_runtime_state(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        dossier = ExternalAttestationDossier(root)
        public = dossier.summary()
        internal = dossier.internal_summary()
        indexed = {str(row.get("key") or ""): row for row in internal.get("checks") or []}
        return public, indexed
    except ExternalAttestationError:
        controls = (
            "postgres_external_certification",
            "postgres_backup_restore_exercise",
            "postgres_migration_certification",
            "persistent_object_storage_certification",
            "managed_secrets_rotation_certification",
            "privileged_mfa_operational_verification",
            "malware_scanner_operational_verification",
            "monitoring_alerting_incident_response",
            "privacy_data_protection_go_live_review",
            "legal_qa_operating_model_signoff",
            "disaster_recovery_restore_exercise",
            "real_payment_provider_certification",
        )
        public = {
            "schema": "legalaiz-v1-rc7-external-attestation-summary-v1",
            "ready": False,
            "passed": 0,
            "total": len(controls),
            "integrity": "invalid",
            "checks": [{"key": key, "passed": False, "status": "DOSSIER_UNAVAILABLE"} for key in controls],
        }
        return public, {key: {"key": key, "passed": False, "status": "DOSSIER_UNAVAILABLE"} for key in controls}


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """RC7 añade ingreso verificable de evidencia sin autorizar release.

    RC2 mantiene su dossier append-only y sus aprobaciones originales. RC7 exige
    además que la evidencia RC2 aprobada sea un bundle íntegro. Las doce
    atestaciones RC4 se leen desde un ledger append-only separado; el archivo
    estático versionado nunca se muta en runtime.
    """

    root = Path(root or ROOT)
    report = deepcopy(assess_rc6_release_readiness(root))
    rc2_bundle = _rc2_bundle_state(root)
    rc4_public, rc4_internal = _rc4_runtime_state(root)

    candidate = report["code_release_candidate"]
    checks = list(candidate.get("checks") or [])
    rc4_keys = set(rc4_internal)
    checks.extend(
        [
            {
                "key": "rc7_rc4_attestation_policy_inventory",
                "passed": len(rc4_keys) == 12,
                "detail": f"rc4_ledger_controls={len(rc4_keys)} expected=12",
            },
            {
                "key": "rc7_runtime_evidence_does_not_mutate_static_registry",
                "passed": True,
                "detail": "runtime ledgers are overlays; config/v1/production_attestations.json remains versioned input",
            },
            {
                "key": "rc7_bundle_gate_preserves_rc2_approval_chain",
                "passed": True,
                "detail": "bundle validation is additive to RC2 DOMAIN_APPROVED + RELEASE_RATIFIED",
            },
        ]
    )
    candidate["checks"] = checks
    candidate["ready"] = all(bool(row.get("passed")) for row in checks)
    candidate["status"] = "RC_CODE_READY" if candidate["ready"] else "RC_CODE_BLOCKED"

    real = report["real_legal_production"]
    real_blockers = list(real.get("blockers") or [])
    for row in rc2_bundle.get("checks") or []:
        if bool(row.get("rc2_gate_passed")) and not bool(row.get("bundle_valid")):
            real_blockers.append(RC7_RC2_BUNDLE_PREFIX + str(row.get("key") or "UNKNOWN"))

    real_attestation_state = dict(real.get("attestations_verified") or {})
    real_control_ids = set(real_attestation_state)
    for control in real_control_ids:
        runtime = rc4_internal.get(control) or {}
        if bool(runtime.get("passed")):
            real_attestation_state[control] = True
            real_blockers = [item for item in real_blockers if item != control]
    if str(rc4_public.get("integrity") or "invalid") != "valid":
        real_blockers.append(RC7_RC4_LEDGER_INTEGRITY)
    real["attestations_verified"] = real_attestation_state
    real["blockers"] = _dedupe(real_blockers)
    real["ready"] = bool(candidate["ready"] and not real["blockers"])
    real["status"] = "REAL_PRODUCTION_READY" if real["ready"] else "REAL_PRODUCTION_BLOCKED"

    commercial = report["commercial_v1"]
    commercial_blockers = [
        item for item in list(commercial.get("blockers") or []) if item != "REAL_LEGAL_PRODUCTION_NOT_READY"
    ]
    commercial_attestation_state = dict(commercial.get("attestations_verified") or {})
    for control in list(commercial_attestation_state):
        runtime = rc4_internal.get(control) or {}
        if bool(runtime.get("passed")):
            commercial_attestation_state[control] = True
            commercial_blockers = [item for item in commercial_blockers if item != control]
    if not real["ready"]:
        commercial_blockers.insert(0, "REAL_LEGAL_PRODUCTION_NOT_READY")
    commercial["attestations_verified"] = commercial_attestation_state
    commercial["blockers"] = _dedupe(commercial_blockers)
    commercial["ready"] = bool(candidate["ready"] and real["ready"] and not commercial["blockers"])
    commercial["status"] = "COMMERCIAL_V1_READY" if commercial["ready"] else "COMMERCIAL_V1_BLOCKED"

    report["schema"] = "legalaiz-v1-release-readiness-report-v5"
    report["runtime_external_evidence"] = {
        "rc2_bundle_gate": rc2_bundle,
        "rc4_attestation_ledger": rc4_public,
        "static_attestation_registry_mutated": False,
        "release_authorization_mutated": False,
    }
    governance = report["governance"]
    governance["external_evidence_registration_is_not_approval"] = True
    governance["external_evidence_review_is_not_release_ratification"] = True
    governance["runtime_evidence_ledgers_are_append_only"] = True
    governance["runtime_evidence_cannot_mutate_release_authorization"] = True
    governance["rc2_approvals_remain_required_after_bundle_validation"] = True
    governance["rc4_static_attestation_registry_is_immutable_runtime_input"] = True

    return report


__all__ = [
    "RC7_RC2_BUNDLE_PREFIX",
    "RC7_RC4_LEDGER_INTEGRITY",
    "assess_release_readiness",
]
