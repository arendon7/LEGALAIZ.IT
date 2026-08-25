from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.external_attestation_dossier_v1_rc7 import (
    ExternalAttestationDossier,
    ExternalAttestationPermissionError,
)
from legalai_platform.external_evidence_bundle_v1 import (
    BUNDLE_SCHEMA,
    EvidenceBundleError,
    EvidenceBundleValidator,
    register_rc2_bundle,
)
from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier
from legalai_platform.release_readiness_v1_rc7 import assess_release_readiness


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _control(ref: str) -> dict:
    plan = EvidenceExecutionPlan(ROOT).plan
    return next(row for row in plan["controls"] if row["ref"] == ref)


def _write_bundle(
    evidence_root: Path,
    control_ref: str,
    *,
    bundle_name: str = "bundle",
    observed_at: datetime | None = None,
    valid_until: datetime | None = None,
) -> Path:
    control = _control(control_ref)
    bundle = evidence_root / bundle_name
    bundle.mkdir(parents=True, exist_ok=True)
    artifacts = []
    required = [name for name in control["required_artifacts"] if name != "sha256_manifest"]
    for name in required:
        path = bundle / f"{name}.txt"
        path.write_text(f"synthetic evidence for {control_ref} / {name}\n", encoding="utf-8")
        artifacts.append(
            {
                "name": name,
                "path": path.name,
                "sha256": _sha(path),
                "size": path.stat().st_size,
            }
        )
    observed = observed_at or (NOW - timedelta(hours=1))
    maximum = int(control["max_validity_days"])
    valid = valid_until or (observed + timedelta(days=min(maximum, 30)))
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "schema_version": 1,
        "control_ref": control_ref,
        "source_framework": control["source_framework"],
        "source_id": control["source_id"],
        "environment": control["environment"],
        "observed_at": observed.isoformat(),
        "valid_until": valid.isoformat(),
        "executor": {"id": "executor.synthetic", "role": control["executor_role"]},
        "redaction": {
            "performed": True,
            "declaration": "Synthetic fixture only; secrets and personal data are excluded from this evidence bundle.",
        },
        "artifacts": artifacts,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle


class V1RC7EvidenceIntakeLedgerTests(unittest.TestCase):
    def test_valid_bundle_requires_real_files_hashes_sizes_and_required_artifacts(self) -> None:
        with TemporaryDirectory() as temp:
            evidence_root = Path(temp)
            bundle = _write_bundle(evidence_root, "RC4:postgres_external_certification")
            validator = EvidenceBundleValidator(ROOT, evidence_root, now_factory=lambda: NOW)
            result = validator.validate(bundle.name, expected_control_ref="RC4:postgres_external_certification")
            self.assertEqual(result.source_framework, "RC4")
            self.assertEqual(result.source_id, "postgres_external_certification")
            self.assertGreater(result.artifact_count, 0)
            self.assertEqual(len(result.manifest_sha256), 64)

    def test_artifact_tampering_is_rejected(self) -> None:
        with TemporaryDirectory() as temp:
            evidence_root = Path(temp)
            bundle = _write_bundle(evidence_root, "RC4:persistent_object_storage_certification")
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            artifact = bundle / manifest["artifacts"][0]["path"]
            artifact.write_text("tampered after manifest\n", encoding="utf-8")
            validator = EvidenceBundleValidator(ROOT, evidence_root, now_factory=lambda: NOW)
            with self.assertRaises(EvidenceBundleError):
                validator.validate(bundle.name)

    def test_path_traversal_is_rejected(self) -> None:
        with TemporaryDirectory() as temp:
            evidence_root = Path(temp)
            bundle = _write_bundle(evidence_root, "RC4:managed_secrets_rotation_certification")
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"][0]["path"] = "../outside.txt"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            validator = EvidenceBundleValidator(ROOT, evidence_root, now_factory=lambda: NOW)
            with self.assertRaises(EvidenceBundleError):
                validator.validate(bundle.name)

    def test_expired_and_overlong_evidence_are_rejected(self) -> None:
        with TemporaryDirectory() as temp:
            evidence_root = Path(temp)
            expired = _write_bundle(
                evidence_root,
                "RC4:malware_scanner_operational_verification",
                bundle_name="expired",
                observed_at=NOW - timedelta(days=3),
                valid_until=NOW - timedelta(days=1),
            )
            validator = EvidenceBundleValidator(ROOT, evidence_root, now_factory=lambda: NOW)
            with self.assertRaises(EvidenceBundleError):
                validator.validate(expired.name)

            control = _control("RC4:malware_scanner_operational_verification")
            observed = NOW - timedelta(hours=1)
            overlong = _write_bundle(
                evidence_root,
                "RC4:malware_scanner_operational_verification",
                bundle_name="overlong",
                observed_at=observed,
                valid_until=observed + timedelta(days=int(control["max_validity_days"]) + 1),
            )
            with self.assertRaises(EvidenceBundleError):
                validator.validate(overlong.name)

    def test_manifest_rejects_secret_bearing_keys(self) -> None:
        with TemporaryDirectory() as temp:
            evidence_root = Path(temp)
            bundle = _write_bundle(evidence_root, "RC4:privileged_mfa_operational_verification")
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["api_key"] = "forbidden-even-in-a-test-manifest"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            validator = EvidenceBundleValidator(ROOT, evidence_root, now_factory=lambda: NOW)
            with self.assertRaises(EvidenceBundleError):
                validator.validate(bundle.name)

    def test_rc2_bundle_registration_does_not_bypass_existing_approval_chain(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            evidence_root = base / "evidence"
            evidence_root.mkdir()
            bundle = _write_bundle(evidence_root, "RC2:load_test")
            dossier = ExternalEvidenceDossier(
                ROOT,
                dossier_path=base / "rc2.jsonl",
                evidence_root=evidence_root,
                now_factory=lambda: NOW,
            )
            registered = register_rc2_bundle(dossier, bundle.name, actor={"id": "registrar.rc2", "role": "admin"})
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "load_test")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "DOMAIN_APPROVAL_REQUIRED")

            domain_role = dossier.policy["controls"]["load_test"]["domain_approver_roles"][0]
            dossier.approve_domain(
                "load_test",
                registered["event_id"],
                actor={"id": "domain.rc2", "role": domain_role},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "load_test")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "RELEASE_RATIFICATION_REQUIRED")

            ratifier_role = dossier.policy["release_ratifier_roles"][0]
            dossier.ratify_release(
                "load_test",
                registered["event_id"],
                actor={"id": "ratifier.rc2", "role": ratifier_role},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "load_test")
            self.assertTrue(check["passed"])
            self.assertEqual(check["status"], "VERIFIED_FOR_RELEASE_GATE")

    def test_rc4_registration_review_and_ratification_are_three_separate_gates_after_execution(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            evidence_root = base / "evidence"
            evidence_root.mkdir()
            bundle = _write_bundle(evidence_root, "RC4:postgres_external_certification")
            dossier = ExternalAttestationDossier(
                ROOT,
                dossier_path=base / "rc4.jsonl",
                evidence_root=evidence_root,
                now_factory=lambda: NOW,
            )
            registered = dossier.register_bundle(
                "postgres_external_certification",
                bundle.name,
                actor={"id": "registrar.rc4", "role": "admin"},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "postgres_external_certification")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "INDEPENDENT_REVIEW_REQUIRED")

            reviewer_role = _control("RC4:postgres_external_certification")["reviewer_role"]
            dossier.approve_review(
                "postgres_external_certification",
                registered["event_id"],
                actor={"id": "reviewer.rc4", "role": reviewer_role},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "postgres_external_certification")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "RELEASE_RATIFICATION_REQUIRED")

            dossier.ratify_release(
                "postgres_external_certification",
                registered["event_id"],
                actor={"id": "ratifier.rc4", "role": "qa"},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "postgres_external_certification")
            self.assertTrue(check["passed"])
            self.assertEqual(check["status"], "VERIFIED_EXTERNAL_EVIDENCE")

            dossier.revoke(
                "postgres_external_certification",
                registered["event_id"],
                reason_code="RETEST_REQUIRED",
                actor={"id": "revoker.rc4", "role": "admin"},
            )
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "postgres_external_certification")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "MISSING_EVIDENCE")

    def test_rc4_separation_rejects_same_actor_across_stages(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            evidence_root = base / "evidence"
            evidence_root.mkdir()
            bundle = _write_bundle(evidence_root, "RC4:postgres_external_certification")
            dossier = ExternalAttestationDossier(
                ROOT,
                dossier_path=base / "rc4.jsonl",
                evidence_root=evidence_root,
                now_factory=lambda: NOW,
            )
            registered = dossier.register_bundle(
                "postgres_external_certification",
                bundle.name,
                actor={"id": "shared.actor", "role": "admin"},
            )
            reviewer_role = _control("RC4:postgres_external_certification")["reviewer_role"]
            with self.assertRaises(ExternalAttestationPermissionError):
                dossier.approve_review(
                    "postgres_external_certification",
                    registered["event_id"],
                    actor={"id": "shared.actor", "role": reviewer_role},
                )

    def test_rc4_bundle_integrity_is_rechecked_after_ratification(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            evidence_root = base / "evidence"
            evidence_root.mkdir()
            bundle = _write_bundle(evidence_root, "RC4:persistent_object_storage_certification")
            dossier = ExternalAttestationDossier(
                ROOT,
                dossier_path=base / "rc4.jsonl",
                evidence_root=evidence_root,
                now_factory=lambda: NOW,
            )
            registered = dossier.register_bundle(
                "persistent_object_storage_certification",
                bundle.name,
                actor={"id": "registrar.storage", "role": "admin"},
            )
            reviewer_role = _control("RC4:persistent_object_storage_certification")["reviewer_role"]
            dossier.approve_review(
                "persistent_object_storage_certification",
                registered["event_id"],
                actor={"id": "reviewer.storage", "role": reviewer_role},
            )
            dossier.ratify_release(
                "persistent_object_storage_certification",
                registered["event_id"],
                actor={"id": "ratifier.storage", "role": "qa"},
            )
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            artifact = bundle / manifest["artifacts"][0]["path"]
            artifact.write_text("tampered after ratification\n", encoding="utf-8")
            check = next(row for row in dossier.summary()["checks"] if row["key"] == "persistent_object_storage_certification")
            self.assertFalse(check["passed"])
            self.assertEqual(check["status"], "EVIDENCE_BUNDLE_INTEGRITY_INVALID")

    def test_runtime_ledgers_do_not_mutate_static_attestation_registry(self) -> None:
        static_path = ROOT / "config" / "v1" / "production_attestations.json"
        before = static_path.read_bytes()
        with TemporaryDirectory() as temp:
            base = Path(temp)
            evidence_root = base / "evidence"
            evidence_root.mkdir()
            bundle = _write_bundle(evidence_root, "RC4:postgres_external_certification")
            dossier = ExternalAttestationDossier(
                ROOT,
                dossier_path=base / "rc4.jsonl",
                evidence_root=evidence_root,
                now_factory=lambda: NOW,
            )
            dossier.register_bundle(
                "postgres_external_certification",
                bundle.name,
                actor={"id": "registrar.static", "role": "admin"},
            )
        self.assertEqual(static_path.read_bytes(), before)

    def test_clean_runtime_keeps_code_ready_but_real_and_commercial_blocked(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                report = assess_release_readiness(ROOT)
        self.assertTrue(report["code_release_candidate"]["ready"], report["code_release_candidate"])
        self.assertEqual(report["code_release_candidate"]["status"], "RC_CODE_READY")
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertFalse(report["commercial_v1"]["ready"])
        runtime = report["runtime_external_evidence"]
        self.assertEqual(runtime["rc2_bundle_gate"]["bundle_validated"], 0)
        self.assertEqual(runtime["rc4_attestation_ledger"]["passed"], 0)
        self.assertFalse(runtime["static_attestation_registry_mutated"])
        self.assertFalse(runtime["release_authorization_mutated"])

    def test_governance_preserves_no_auto_authorization_boundary(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                governance = assess_release_readiness(ROOT)["governance"]
        self.assertTrue(governance["external_evidence_registration_is_not_approval"])
        self.assertTrue(governance["external_evidence_review_is_not_release_ratification"])
        self.assertTrue(governance["runtime_evidence_ledgers_are_append_only"])
        self.assertTrue(governance["runtime_evidence_cannot_mutate_release_authorization"])
        self.assertFalse(governance["code_ci_can_authorize_real_production"])
        self.assertFalse(governance["code_ci_can_authorize_real_payments"])

    def test_rc7_has_no_runtime_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("release_readiness_v1_rc7", run_source)
        self.assertNotIn("external_attestation_dossier_v1_rc7", run_source)
        self.assertNotIn("external_evidence_bundle_v1", run_source)

    def test_cli_consumes_rc7_gate(self) -> None:
        source = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.release_readiness_v1_rc7 import assess_release_readiness", source)
        self.assertNotIn("from legalai_platform.release_readiness_v1_rc6 import assess_release_readiness", source)


if __name__ == "__main__":
    unittest.main()
