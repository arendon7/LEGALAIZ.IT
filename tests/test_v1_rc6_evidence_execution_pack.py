from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan, validate_plan_payload
from legalai_platform.release_readiness_v1_rc6 import assess_release_readiness


ROOT = Path(__file__).resolve().parents[1]


class V1RC6EvidenceExecutionPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.execution = EvidenceExecutionPlan(ROOT)
        self.validation = self.execution.validate()
        self.report = assess_release_readiness(ROOT)

    def test_execution_plan_is_structurally_complete_but_not_executed(self) -> None:
        summary = self.execution.summary()
        self.assertTrue(summary["structurally_ready"], summary)
        self.assertFalse(summary["execution_ready"])
        self.assertEqual(summary["controls"], 22)
        self.assertEqual(summary["pending"], 22)
        self.assertEqual(summary["executed"], 0)
        self.assertEqual(summary["evidence_refs_present"], 0)

    def test_exact_rc2_and_rc4_source_inventories_are_covered_once(self) -> None:
        self.assertTrue(self.validation.valid, self.validation.errors)
        self.assertEqual(self.validation.rc2_count, 10)
        self.assertEqual(self.validation.rc4_count, 12)
        controls = self.execution.plan["controls"]
        refs = [row["ref"] for row in controls]
        self.assertEqual(len(refs), len(set(refs)))

    def test_executor_and_reviewer_roles_are_separated_for_every_control(self) -> None:
        for row in self.execution.plan["controls"]:
            with self.subTest(ref=row["ref"]):
                self.assertTrue(row["executor_role"])
                self.assertTrue(row["reviewer_role"])
                self.assertNotEqual(row["executor_role"], row["reviewer_role"])

    def test_payment_provider_is_the_only_commercial_only_control(self) -> None:
        commercial = [row for row in self.execution.plan["controls"] if row["release_scope"] == "commercial_only"]
        self.assertEqual(len(commercial), 1)
        self.assertEqual(commercial[0]["ref"], "RC4:real_payment_provider_certification")
        production = [row for row in self.execution.plan["controls"] if row["release_scope"] == "real_production"]
        self.assertEqual(len(production), 21)

    def test_no_control_declares_implicit_equivalence_or_suppression(self) -> None:
        serialized = json.dumps(self.execution.plan, ensure_ascii=False, sort_keys=True)
        self.assertNotIn('"equivalent_to"', serialized)
        self.assertNotIn('"satisfies"', serialized)
        self.assertTrue(self.execution.plan["governance"]["control_equivalence_requires_versioned_policy_migration"])

    def test_plan_rejects_embedded_evidence_reference(self) -> None:
        mutated = deepcopy(self.execution.plan)
        mutated["controls"][0]["evidence_ref"] = "evidence://fabricated"
        result = validate_plan_payload(mutated, self.execution.rc2_policy, self.execution.rc4_attestations)
        self.assertFalse(result.valid)
        self.assertGreater(result.evidence_refs_present, 0)
        self.assertTrue(any("plan_must_not_embed_evidence_ref" in error for error in result.errors))

    def test_plan_rejects_missing_separation_of_duties(self) -> None:
        mutated = deepcopy(self.execution.plan)
        mutated["controls"][0]["reviewer_role"] = mutated["controls"][0]["executor_role"]
        result = validate_plan_payload(mutated, self.execution.rc2_policy, self.execution.rc4_attestations)
        self.assertFalse(result.valid)
        self.assertTrue(any("executor_reviewer_not_separated" in error for error in result.errors))

    def test_plan_rejects_secret_bearing_keys(self) -> None:
        mutated = deepcopy(self.execution.plan)
        mutated["api_key"] = "must-never-be-versioned"
        result = validate_plan_payload(mutated, self.execution.rc2_policy, self.execution.rc4_attestations)
        self.assertFalse(result.valid)
        self.assertTrue(any("secret_bearing_key_forbidden" in error for error in result.errors))

    def test_plan_rejects_dropped_source_control(self) -> None:
        mutated = deepcopy(self.execution.plan)
        mutated["controls"] = mutated["controls"][:-1]
        result = validate_plan_payload(mutated, self.execution.rc2_policy, self.execution.rc4_attestations)
        self.assertFalse(result.valid)
        self.assertTrue(any("rc4_inventory_mismatch" in error for error in result.errors))
        self.assertTrue(any("execution_inventory_count" in error for error in result.errors))

    def test_release_candidate_can_be_structurally_ready_while_real_go_live_remains_blocked(self) -> None:
        candidate = self.report["code_release_candidate"]
        real = self.report["real_legal_production"]
        commercial = self.report["commercial_v1"]
        pack = self.report["evidence_execution_pack"]
        self.assertTrue(candidate["ready"], candidate)
        self.assertEqual(candidate["status"], "RC_CODE_READY")
        self.assertFalse(real["ready"])
        self.assertEqual(real["status"], "REAL_PRODUCTION_BLOCKED")
        self.assertFalse(commercial["ready"])
        self.assertEqual(commercial["status"], "COMMERCIAL_V1_BLOCKED")
        self.assertFalse(pack["execution_ready"])
        self.assertEqual(pack["executed"], 0)

    def test_governance_does_not_allow_ci_to_convert_plan_into_evidence(self) -> None:
        governance = self.report["governance"]
        self.assertTrue(governance["execution_plan_completeness_is_not_external_evidence"])
        self.assertTrue(governance["ci_can_validate_execution_plan_structure_only"])
        self.assertFalse(governance["ci_can_mark_external_execution_complete"])
        self.assertFalse(governance["code_ci_can_authorize_real_production"])
        self.assertFalse(governance["code_ci_can_authorize_real_payments"])

    def test_cli_consumes_rc6_gate(self) -> None:
        source = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.release_readiness_v1_rc6 import assess_release_readiness", source)
        self.assertNotIn("from legalai_platform.release_readiness_v1_rc5 import assess_release_readiness", source)

    def test_rc6_does_not_expose_runtime_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("release_readiness_v1_rc6", run_source)
        self.assertNotIn("evidence_execution_plan_v1", run_source)
        self.assertNotIn("PENDING_EXTERNAL_EXECUTION", run_source)


if __name__ == "__main__":
    unittest.main()
