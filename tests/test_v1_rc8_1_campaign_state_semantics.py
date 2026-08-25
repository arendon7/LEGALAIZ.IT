from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.evidence_orchestration_v1_rc8_1 import (
    STATE_SCHEMA,
    EvidenceCampaignLedger,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "cc851815bcb0d4c999c5682d363deb007945e4a2"
ENV_FINGERPRINT = "b" * 64
MANAGER = {"id": "campaign.manager", "role": "admin"}


class V1RC81CampaignStateSemanticsTests(unittest.TestCase):
    def _create(self, temp: str) -> tuple[EvidenceCampaignLedger, str]:
        ledger = EvidenceCampaignLedger(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
        event = ledger.create_campaign(
            environment_fingerprint=ENV_FINGERPRINT,
            source_revision=SOURCE_REVISION,
            actor=MANAGER,
        )
        return ledger, event["campaign_id"]

    def test_new_campaign_is_created_not_globally_blocked_by_normal_dependencies(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._create(temp)
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["schema"], STATE_SCHEMA)
        self.assertEqual(state["status"], "CREATED")
        self.assertGreater(state["dependency_blocked_controls"], 0)
        self.assertTrue(state["dependency_constraints_active"])
        self.assertEqual(state["global_blockers"], [])
        self.assertEqual(state["explicitly_blocked_controls"], [])
        self.assertFalse(state["release_authorized"])
        self.assertFalse(state["commercial_authorized"])

    def test_started_campaign_is_in_progress_even_when_later_controls_wait_on_dependencies(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        independent = next(row for row in plan["controls"] if not row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._create(temp)
                ledger.start_control(
                    campaign_id,
                    independent["ref"],
                    actor={"id": "executor.allowed", "role": independent["executor_role"]},
                )
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["status"], "IN_PROGRESS")
        self.assertGreater(state["dependency_blocked_controls"], 0)
        self.assertEqual(state["global_blockers"], [])

    def test_unmet_dependency_still_blocks_the_affected_control_locally(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        dependent = next(row for row in plan["controls"] if row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._create(temp)
                with self.assertRaisesRegex(Exception, "Dependencias no verificadas"):
                    ledger.start_control(
                        campaign_id,
                        dependent["ref"],
                        actor={"id": "executor.dep", "role": dependent["executor_role"]},
                    )
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["status"], "CREATED")
        self.assertTrue(state["dependency_constraints_active"])

    def test_explicit_control_block_is_a_real_global_campaign_blocker(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        independent = next(row for row in plan["controls"] if not row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._create(temp)
                ledger.block_control(
                    campaign_id,
                    independent["ref"],
                    reason_code="EXTERNAL_DEPENDENCY_FAILED",
                    actor=MANAGER,
                )
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["status"], "BLOCKED")
        self.assertIn("EXPLICIT_CONTROL_BLOCK", state["global_blockers"])
        self.assertEqual(state["explicitly_blocked_controls"], [independent["ref"]])

    def test_plan_drift_remains_fail_closed_and_globally_blocked(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            shutil.copytree(ROOT / "config", root / "config")
            ledger = EvidenceCampaignLedger(root, ledger_path=Path(temp) / "campaigns.jsonl")
            event = ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            plan_path = root / "config" / "v1" / "evidence_execution_plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            payload["notice"] = str(payload.get("notice") or "") + " rc8-1-drift"
            plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            state = ledger.campaign_state(event["campaign_id"])
        self.assertEqual(state["status"], "BLOCKED")
        self.assertFalse(state["plan_hash_current"])
        self.assertIn("PLAN_DRIFT", state["global_blockers"])

    def test_abort_remains_terminal_without_becoming_authorization(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._create(temp)
                ledger.abort_campaign(campaign_id, reason_code="CAMPAIGN_CANCELLED", actor=MANAGER)
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["status"], "ABORTED")
        self.assertFalse(state["release_authorized"])
        self.assertFalse(state["commercial_authorized"])

    def test_evidence_complete_still_does_not_authorize_go_live(self) -> None:
        with TemporaryDirectory() as temp:
            ledger, campaign_id = self._create(temp)
            fake_audit = {"summary": {"verified": 22, "dependency_blocked": 0}}
            with patch(
                "legalai_platform.evidence_orchestration_v1_rc8_1.EvidenceAuditDossier.build",
                return_value=fake_audit,
            ):
                state = ledger.campaign_state(campaign_id)
        self.assertEqual(state["status"], "EVIDENCE_COMPLETE")
        self.assertEqual(state["global_blockers"], [])
        self.assertFalse(state["release_authorized"])
        self.assertFalse(state["commercial_authorized"])
        self.assertTrue(state["governance"]["dependency_block_is_control_local"])
        self.assertTrue(state["governance"]["evidence_complete_is_not_release_authorization"])

    def test_operator_cli_uses_rc8_1_overlay_and_still_has_no_authorization_commands(self) -> None:
        source = (ROOT / "tools" / "v1_evidence_campaign.py").read_text(encoding="utf-8")
        self.assertIn("evidence_orchestration_v1_rc8_1", source)
        self.assertNotIn('add_parser("approve', source)
        self.assertNotIn('add_parser("ratify', source)
        self.assertNotIn('add_parser("authorize', source)
        self.assertNotIn('add_parser("go-live', source)

    def test_runtime_still_does_not_expose_campaign_or_release_activation_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("evidence_orchestration_v1_rc8_1", run_source)
        self.assertNotIn("evidence-campaigns.jsonl", run_source)


if __name__ == "__main__":
    unittest.main()
