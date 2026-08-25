from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.evidence_orchestration_v1_rc8 import (
    EvidenceAuditDossier,
    EvidenceCampaignError,
    EvidenceCampaignIntegrityError,
    EvidenceCampaignLedger,
)
from legalai_platform.release_readiness_v1_rc8 import assess_release_readiness


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "0e8573b032f4ab0968cfc38f9d551db0e6a5be5f"
ENV_FINGERPRINT = "a" * 64
MANAGER = {"id": "campaign.manager", "role": "admin"}


class V1RC8EvidenceOrchestrationTests(unittest.TestCase):
    def test_all_22_controls_have_unique_safe_operator_packets(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            packets = ledger.all_task_packets()
        self.assertEqual(len(packets), 22)
        self.assertEqual(len({row["control_ref"] for row in packets}), 22)
        self.assertEqual(sum(row["source_framework"] == "RC2" for row in packets), 10)
        self.assertEqual(sum(row["source_framework"] == "RC4" for row in packets), 12)
        self.assertTrue(all(row["evidence_ref"] is None for row in packets))
        self.assertTrue(all(row["coordination_only"] for row in packets))
        self.assertTrue(all(row["release_authorization"] is False for row in packets))

    def test_campaign_pins_exact_plan_hash_revision_and_environment_fingerprint(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            event = ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            payload = event["payload"]
            self.assertEqual(payload["plan_sha256"], ledger.plan_sha256)
            self.assertEqual(payload["source_revision"], SOURCE_REVISION)
            self.assertEqual(payload["environment_fingerprint"], ENV_FINGERPRINT)
            self.assertEqual(payload["control_count"], 22)
            self.assertEqual(payload["rc2_count"], 10)
            self.assertEqual(payload["rc4_count"], 12)

    def test_environment_fingerprint_must_be_opaque_sha256(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            with self.assertRaises(EvidenceCampaignError):
                ledger.create_campaign(
                    environment_fingerprint="production.example.com",
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )

    def test_source_revision_requires_full_git_sha(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            with self.assertRaises(EvidenceCampaignError):
                ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision="0e8573b",
                    actor=MANAGER,
                )

    def test_plan_drift_blocks_further_campaign_actions(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            shutil.copytree(ROOT / "config", root / "config")
            ledger = EvidenceCampaignLedger(root, ledger_path=Path(temp) / "campaigns.jsonl")
            created = ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            plan_path = root / "config" / "v1" / "evidence_execution_plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            payload["notice"] = payload["notice"] + " changed-after-campaign"
            plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaises(EvidenceCampaignIntegrityError):
                ledger.start_control(
                    created["campaign_id"],
                    "RC2:postgres_runtime",
                    actor={"id": "executor.platform", "role": "platform"},
                )

    def test_ledger_hash_chain_detects_tampering(self) -> None:
        with TemporaryDirectory() as temp:
            path = Path(temp) / "campaigns.jsonl"
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=path)
            ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            row = json.loads(path.read_text(encoding="utf-8").strip())
            row["actor"]["id"] = "tampered.actor"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertFalse(ledger.verify_chain()["valid"])

    def test_dependencies_are_read_from_rc6_and_block_start_until_verified(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        dependent = next(row for row in plan["controls"] if row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
                created = ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                with self.assertRaises(EvidenceCampaignError):
                    ledger.start_control(
                        created["campaign_id"],
                        dependent["ref"],
                        actor={"id": "executor.dep", "role": dependent["executor_role"]},
                    )

    def test_control_without_dependencies_can_be_started_only_by_declared_executor_role(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        independent = next(row for row in plan["controls"] if not row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
                created = ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                event = ledger.start_control(
                    created["campaign_id"],
                    independent["ref"],
                    actor={"id": "executor.allowed", "role": independent["executor_role"]},
                )
                self.assertEqual(event["event_type"], "CONTROL_STARTED")

    def test_fabricated_evidence_event_cannot_be_linked(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
                created = ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                with self.assertRaises(EvidenceCampaignError):
                    ledger.link_evidence(
                        created["campaign_id"],
                        "RC4:postgres_external_certification",
                        "ATT-FABRICATED",
                        actor=MANAGER,
                    )

    def test_clean_audit_has_22_controls_and_no_verified_evidence(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                audit = EvidenceAuditDossier(ROOT).build()
        self.assertEqual(audit["control_count"], 22)
        self.assertEqual(audit["rc2_count"], 10)
        self.assertEqual(audit["rc4_count"], 12)
        self.assertEqual(audit["summary"]["verified"], 0)
        self.assertFalse(audit["summary"]["real_production_evidence_complete"])
        self.assertFalse(audit["summary"]["commercial_evidence_complete"])
        self.assertFalse(audit["summary"]["release_authorized"])
        self.assertFalse(audit["summary"]["commercial_authorized"])

    def test_evidence_complete_campaign_state_still_does_not_authorize_release(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            created = ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            fake_audit = {
                "summary": {"verified": 22, "dependency_blocked": 0},
            }
            with patch("legalai_platform.evidence_orchestration_v1_rc8.EvidenceAuditDossier.build", return_value=fake_audit):
                state = ledger.campaign_state(created["campaign_id"])
        self.assertEqual(state["status"], "EVIDENCE_COMPLETE")
        self.assertFalse(state["release_authorized"])
        self.assertFalse(state["commercial_authorized"])

    def test_campaign_policy_forbids_mutation_and_auto_authorization(self) -> None:
        with TemporaryDirectory() as temp:
            ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
            governance = ledger.policy["governance"]
        self.assertTrue(governance["campaign_cannot_mutate_evidence_ledgers"])
        self.assertTrue(governance["campaign_cannot_mutate_release_metadata"])
        self.assertTrue(governance["campaign_cannot_authorize_real_production"])
        self.assertTrue(governance["campaign_cannot_authorize_real_payments"])
        self.assertTrue(governance["evidence_complete_is_not_release_authorization"])
        self.assertTrue(governance["control_equivalence_is_never_inferred"])

    def test_release_readiness_stays_code_ready_but_real_and_commercial_blocked_clean(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                report = assess_release_readiness(ROOT)
        self.assertTrue(report["code_release_candidate"]["ready"], report["code_release_candidate"])
        self.assertEqual(report["code_release_candidate"]["status"], "RC_CODE_READY")
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertFalse(report["commercial_v1"]["ready"])
        orchestration = report["evidence_orchestration"]
        self.assertTrue(orchestration["structurally_ready"])
        self.assertEqual(orchestration["controls"], 22)
        self.assertEqual(orchestration["verified"], 0)
        self.assertEqual(orchestration["campaigns"], 0)

    def test_campaign_cli_has_no_approval_ratification_or_authorization_command(self) -> None:
        source = (ROOT / "tools" / "v1_evidence_campaign.py").read_text(encoding="utf-8")
        self.assertNotIn('add_parser("approve', source)
        self.assertNotIn('add_parser("ratify', source)
        self.assertNotIn('add_parser("authorize', source)
        self.assertNotIn('add_parser("go-live', source)

    def test_release_audit_chain_is_rc8_to_rc7_to_rc6(self) -> None:
        cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        rc8 = (ROOT / "legalai_platform" / "release_readiness_v1_rc8.py").read_text(encoding="utf-8")
        rc7 = (ROOT / "legalai_platform" / "release_readiness_v1_rc7.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.release_readiness_v1_rc8 import assess_release_readiness", cli)
        self.assertIn(
            "from legalai_platform.release_readiness_v1_rc7 import assess_release_readiness as assess_rc7_release_readiness",
            rc8,
        )
        self.assertIn(
            "from legalai_platform.release_readiness_v1_rc6 import assess_release_readiness as assess_rc6_release_readiness",
            rc7,
        )

    def test_rc8_does_not_expose_runtime_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("release_readiness_v1_rc8", run_source)
        self.assertNotIn("evidence_orchestration_v1_rc8", run_source)
        self.assertNotIn("evidence-campaigns.jsonl", run_source)


if __name__ == "__main__":
    unittest.main()
