from __future__ import annotations

import json
from pathlib import Path
import unittest

from legalai_platform import release_metadata
from legalai_platform.release_readiness_v1 import assess_release_readiness


ROOT = Path(__file__).resolve().parents[1]


class V1ReleaseReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = assess_release_readiness(ROOT)

    def test_current_m34_m37_stack_is_code_release_candidate(self) -> None:
        candidate = self.report["code_release_candidate"]
        self.assertTrue(candidate["ready"], candidate)
        self.assertEqual(candidate["status"], "RC_CODE_READY")
        self.assertEqual(self.report["candidate_lineage"], "M37.3")

    def test_portfolio_floor_is_preserved(self) -> None:
        portfolio = self.report["code_release_candidate"]["portfolio"]
        self.assertEqual(portfolio["products"], 11)
        self.assertGreaterEqual(portfolio["questions"], 473)
        self.assertGreaterEqual(portfolio["rules"], 273)

    def test_canonical_release_is_not_prematurely_promoted(self) -> None:
        self.assertEqual(self.report["canonical_release"]["milestone"], "M33.1")
        self.assertEqual(release_metadata.MILESTONE, "M33.1")
        self.assertFalse(release_metadata.REAL_PRODUCTION_AUTHORIZED)
        self.assertFalse(release_metadata.REAL_PAYMENTS_AUTHORIZED)

    def test_real_legal_production_remains_fail_closed(self) -> None:
        real = self.report["real_legal_production"]
        self.assertFalse(real["ready"])
        self.assertEqual(real["status"], "REAL_PRODUCTION_BLOCKED")
        for required in (
            "REAL_PRODUCTION_AUTHORIZED",
            "POSTGRES_EXTERNAL_CERTIFIED",
            "POSTGRES_BACKUP_RESTORE_CERTIFIED",
            "POSTGRES_MIGRATION_CERTIFIED",
            "persistent_object_storage_certification",
            "managed_secrets_rotation_certification",
            "privileged_mfa_operational_verification",
            "legal_qa_operating_model_signoff",
        ):
            self.assertIn(required, real["blockers"])

    def test_commercial_v1_is_independently_blocked_by_real_payments(self) -> None:
        commercial = self.report["commercial_v1"]
        self.assertFalse(commercial["ready"])
        self.assertEqual(commercial["status"], "COMMERCIAL_V1_BLOCKED")
        self.assertIn("REAL_LEGAL_PRODUCTION_NOT_READY", commercial["blockers"])
        self.assertIn("REAL_PAYMENTS_AUTHORIZED", commercial["blockers"])
        self.assertIn("real_payment_provider_certification", commercial["blockers"])

    def test_all_required_external_attestations_are_unique_and_pending(self) -> None:
        contract = json.loads((ROOT / "config" / "v1" / "release_readiness_contract.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "config" / "v1" / "production_attestations.json").read_text(encoding="utf-8"))
        rows = registry["attestations"]
        ids = [row["id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        expected = set(contract["real_production_attestations"] + contract["commercial_v1_attestations"])
        self.assertEqual(set(ids), expected)
        for row in rows:
            self.assertEqual(row["status"], "PENDING_EXTERNAL_EVIDENCE")
            self.assertIsNone(row["evidence_ref"])

    def test_verified_status_without_evidence_ref_never_counts_as_verified(self) -> None:
        from legalai_platform.release_readiness_v1 import _verified_attestation

        indexed = {
            "x": {
                "id": "x",
                "status": "VERIFIED_EXTERNAL_EVIDENCE",
                "evidence_ref": None,
            }
        }
        self.assertFalse(_verified_attestation(indexed, "x", "VERIFIED_EXTERNAL_EVIDENCE"))
        indexed["x"]["evidence_ref"] = "audit://external/evidence-001"
        self.assertTrue(_verified_attestation(indexed, "x", "VERIFIED_EXTERNAL_EVIDENCE"))

    def test_report_contains_no_secret_material_or_connection_strings(self) -> None:
        raw = json.dumps(self.report, ensure_ascii=False).lower()
        for forbidden in (
            "postgresql://",
            "database_url",
            "legal_master_key",
            "bootstrap_admin_password",
            "legal_demo_password",
            "conflict_hash_key",
        ):
            self.assertNotIn(forbidden, raw)

    def test_governance_detects_no_unauthorized_promotion(self) -> None:
        governance = self.report["governance"]
        self.assertTrue(governance["release_candidate_is_not_production_authorization"])
        self.assertTrue(governance["human_legal_and_qa_approval_remain_required"])
        self.assertTrue(governance["missing_attestation_fails_closed"])
        self.assertFalse(governance["unauthorized_promotion_detected"])


if __name__ == "__main__":
    unittest.main()
