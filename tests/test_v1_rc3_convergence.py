from __future__ import annotations

from pathlib import Path
import unittest

from legalai_platform import release_metadata
from legalai_platform.pilot_readiness_v1 import V1PilotReadinessGate
from legalai_platform.release_readiness_v1 import assess_release_readiness
from legalai_platform.v1_rc1_production_readiness import V1RC1ProductionReadinessGate
from legalai_platform.v1_rc2_release_assurance import V1RC2ReleaseAssuranceGate


ROOT = Path(__file__).resolve().parents[1]


class V1RC3ConvergenceTests(unittest.TestCase):
    def test_rc1_rc2_and_pilot_assurance_remain_composed(self) -> None:
        rc2 = V1RC2ReleaseAssuranceGate(ROOT)
        pilot = V1PilotReadinessGate(ROOT, rc2_gate=rc2)
        self.assertIs(pilot.rc2, rc2)
        self.assertIsInstance(rc2.rc1, V1RC1ProductionReadinessGate)

    def test_latest_release_readiness_gate_is_green_only_for_code_candidate(self) -> None:
        report = assess_release_readiness(ROOT)
        self.assertTrue(report["code_release_candidate"]["ready"], report)
        self.assertEqual(report["code_release_candidate"]["status"], "RC_CODE_READY")
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertEqual(report["real_legal_production"]["status"], "REAL_PRODUCTION_BLOCKED")
        self.assertFalse(report["commercial_v1"]["ready"])
        self.assertEqual(report["commercial_v1"]["status"], "COMMERCIAL_V1_BLOCKED")

    def test_release_metadata_is_not_promoted_by_convergence(self) -> None:
        self.assertEqual(release_metadata.MILESTONE, "M33.1")
        self.assertTrue(release_metadata.SYNTHETIC_DATA_ONLY)
        self.assertFalse(release_metadata.REAL_PRODUCTION_AUTHORIZED)
        self.assertFalse(release_metadata.REAL_PAYMENTS_AUTHORIZED)

    def test_all_release_assurance_policies_coexist_in_the_same_tree(self) -> None:
        required = (
            "config/v1_rc1_production_readiness.json",
            "config/v1_rc2_external_evidence_policy.json",
            "config/v1_pilot_readiness_policy.json",
            "config/v1/release_readiness_contract.json",
            "config/v1/production_attestations.json",
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_convergence_does_not_expose_a_new_release_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("release_readiness_v1_routes", run_source)
        self.assertNotIn("http_handler_release_v1", run_source)


if __name__ == "__main__":
    unittest.main()
