from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from legalai_platform.release_readiness_v1_rc5 import (
    RC2_EXTERNAL_BLOCKER_PREFIX,
    RC2_POLICY_BLOCKER,
    _load_rc2_summary,
    assess_release_readiness,
)


ROOT = Path(__file__).resolve().parents[1]


class V1RC5EvidenceSupersetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = assess_release_readiness(ROOT)

    def test_code_candidate_preserves_both_assurance_inventories(self) -> None:
        candidate = self.report["code_release_candidate"]
        superset = self.report["assurance_superset"]
        self.assertTrue(candidate["ready"], candidate)
        self.assertEqual(candidate["status"], "RC_CODE_READY")
        self.assertEqual(superset["strategy"], "RC4_PLUS_RC2_INDEPENDENT_GATES")
        self.assertEqual(superset["rc2_control_count"], 10)
        self.assertEqual(superset["rc4_attestation_count"], 12)
        self.assertTrue(superset["real_production_requires_both"])

    def test_rc2_controls_missing_from_rc4_cannot_be_silently_dropped(self) -> None:
        real = self.report["real_legal_production"]
        for control in (
            "tls_certificate",
            "load_test",
            "pentest",
            "mac_windows_validation",
            "rollback_drill",
        ):
            self.assertIn(RC2_EXTERNAL_BLOCKER_PREFIX + control, real["blockers"])
        self.assertFalse(real["ready"])
        self.assertEqual(real["status"], "REAL_PRODUCTION_BLOCKED")

    def test_current_rc2_dossier_is_a_required_fail_closed_gate(self) -> None:
        gate = self.report["real_legal_production"]["legacy_rc2_evidence_gate"]
        self.assertTrue(gate["required"])
        self.assertTrue(gate["policy_valid"])
        self.assertEqual(gate["total"], 10)
        self.assertFalse(gate["ready"])
        self.assertEqual(gate["passed"], 0)

    def test_commercial_v1_inherits_real_production_superset_block(self) -> None:
        commercial = self.report["commercial_v1"]
        self.assertFalse(commercial["ready"])
        self.assertEqual(commercial["status"], "COMMERCIAL_V1_BLOCKED")
        self.assertIn("REAL_LEGAL_PRODUCTION_NOT_READY", commercial["blockers"])

    def test_governance_declares_no_silent_assurance_reduction(self) -> None:
        governance = self.report["governance"]
        self.assertTrue(governance["legacy_rc2_evidence_required_for_real_production"])
        self.assertTrue(governance["assurance_controls_cannot_be_silently_dropped"])
        self.assertFalse(governance["code_ci_can_authorize_real_production"])
        self.assertFalse(governance["code_ci_can_authorize_real_payments"])

    def test_invalid_rc2_policy_fails_closed_without_becoming_a_release_candidate(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            policy_dir = root / "config"
            policy_dir.mkdir(parents=True)
            (policy_dir / "v1_rc2_external_evidence_policy.json").write_text("{}", encoding="utf-8")
            summary, policy_valid = _load_rc2_summary(root)
        self.assertFalse(policy_valid)
        self.assertFalse(summary["ready"])
        self.assertEqual(summary["integrity"], "invalid_policy")

    def test_release_audit_cli_uses_rc5_superset_gate(self) -> None:
        source = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.release_readiness_v1_rc5 import assess_release_readiness", source)
        self.assertNotIn("from legalai_platform.release_readiness_v1 import assess_release_readiness", source)

    def test_rc5_does_not_add_a_runtime_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("release_readiness_v1_rc5", run_source)
        self.assertNotIn("RC2_EXTERNAL_EVIDENCE_POLICY_INVALID", run_source)


if __name__ == "__main__":
    unittest.main()
