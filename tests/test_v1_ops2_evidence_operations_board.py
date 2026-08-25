from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_board_v1 import (
    BOARD_SCHEMA,
    EvidenceOperationsBoard,
    EvidenceOperationsBoardError,
)
from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.evidence_orchestration_v1_rc8_1 import EvidenceCampaignLedger


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "2b922ed8edce80e2db85420cc5b7a84a57b514b2"
ENV_FINGERPRINT = "c" * 64
MANAGER = {"id": "campaign.manager", "role": "admin"}


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


class V1OPS2EvidenceOperationsBoardTests(unittest.TestCase):
    def _campaign(self, temp: str) -> tuple[EvidenceCampaignLedger, str]:
        path = Path(temp) / "campaigns.jsonl"
        ledger = EvidenceCampaignLedger(ROOT, ledger_path=path)
        event = ledger.create_campaign(
            environment_fingerprint=ENV_FINGERPRINT,
            source_revision=SOURCE_REVISION,
            actor=MANAGER,
        )
        return ledger, event["campaign_id"]

    def test_template_covers_exact_22_controls_and_preserves_ops1_waves(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                board = EvidenceOperationsBoard(ROOT, ledger_path=Path(temp) / "campaigns.jsonl").build()
        self.assertEqual(board["schema"], BOARD_SCHEMA)
        self.assertEqual(board["mode"], "TEMPLATE")
        self.assertEqual(len(board["controls"]), 22)
        self.assertEqual(sum(row["source_framework"] == "RC2" for row in board["controls"]), 10)
        self.assertEqual(sum(row["source_framework"] == "RC4" for row in board["controls"]), 12)
        self.assertEqual([row["wave"] for row in board["controls"]], sorted(row["wave"] for row in board["controls"]))
        self.assertFalse(board["campaign"]["bound"])

    def test_clean_template_requires_campaign_for_root_controls_and_waits_for_dependencies(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                board = EvidenceOperationsBoard(ROOT, ledger_path=Path(temp) / "campaigns.jsonl").build()
        by_status = board["summary"]["status_counts"]
        self.assertGreater(by_status.get("CAMPAIGN_REQUIRED", 0), 0)
        self.assertGreater(by_status.get("WAITING_FOR_DEPENDENCY", 0), 0)
        self.assertEqual(board["summary"]["verified_controls"], 0)
        self.assertFalse(board["summary"]["release_authorized"])
        self.assertFalse(board["summary"]["commercial_authorized"])

    def test_build_is_deterministic_and_does_not_create_campaign_ledger(self) -> None:
        with TemporaryDirectory() as temp:
            ledger_path = Path(temp) / "campaigns.jsonl"
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                first = EvidenceOperationsBoard(ROOT, ledger_path=ledger_path).build()
                second = EvidenceOperationsBoard(ROOT, ledger_path=ledger_path).build()
        self.assertEqual(first, second)
        self.assertFalse(ledger_path.exists())

    def test_bound_campaign_is_redacted_and_root_controls_become_ready(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._campaign(temp)
                board = EvidenceOperationsBoard(
                    ROOT,
                    campaign_id=campaign_id,
                    ledger_path=ledger.path,
                ).build()
        self.assertEqual(board["mode"], "CAMPAIGN_BOUND")
        self.assertEqual(board["campaign"]["campaign_id"], campaign_id)
        self.assertEqual(board["campaign"]["status"], "CREATED")
        self.assertGreater(board["summary"]["status_counts"].get("READY_TO_EXECUTE", 0), 0)
        self.assertFalse(board["campaign"]["release_authorized"])
        self.assertFalse(board["campaign"]["commercial_authorized"])

    def test_started_control_is_coordination_not_execution_claim(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        independent = next(row for row in plan["controls"] if not row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._campaign(temp)
                ledger.start_control(
                    campaign_id,
                    independent["ref"],
                    actor={"id": "executor.allowed", "role": independent["executor_role"]},
                )
                board = EvidenceOperationsBoard(
                    ROOT,
                    campaign_id=campaign_id,
                    ledger_path=ledger.path,
                ).build()
        row = next(item for item in board["controls"] if item["control_ref"] == independent["ref"])
        self.assertEqual(row["work_status"], "EXECUTION_COORDINATION_STARTED")
        self.assertEqual(row["next_action"], "COMPLETE_EXTERNAL_EXECUTION_AND_BUNDLE")
        self.assertFalse(row["evidence_verified"])

    def test_explicit_control_block_is_visible_without_actor_or_reason_payload(self) -> None:
        plan = EvidenceExecutionPlan(ROOT).plan
        independent = next(row for row in plan["controls"] if not row.get("prerequisites"))
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._campaign(temp)
                ledger.block_control(
                    campaign_id,
                    independent["ref"],
                    reason_code="EXTERNAL_DEPENDENCY_FAILED",
                    actor=MANAGER,
                )
                board = EvidenceOperationsBoard(
                    ROOT,
                    campaign_id=campaign_id,
                    ledger_path=ledger.path,
                ).build()
        row = next(item for item in board["controls"] if item["control_ref"] == independent["ref"])
        self.assertEqual(board["campaign"]["status"], "BLOCKED")
        self.assertEqual(row["work_status"], "CONTROL_BLOCKED")
        serialized = json.dumps(board, ensure_ascii=False)
        self.assertNotIn("EXTERNAL_DEPENDENCY_FAILED", serialized)
        self.assertNotIn("campaign.manager", serialized)

    def test_aborted_campaign_is_terminal_and_never_authorized(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._campaign(temp)
                ledger.abort_campaign(campaign_id, reason_code="CAMPAIGN_CANCELLED", actor=MANAGER)
                board = EvidenceOperationsBoard(
                    ROOT,
                    campaign_id=campaign_id,
                    ledger_path=ledger.path,
                ).build()
        self.assertEqual(board["campaign"]["status"], "ABORTED")
        self.assertTrue(all(
            row["work_status"] in {"CAMPAIGN_ABORTED", "VERIFIED"}
            for row in board["controls"]
        ))
        self.assertFalse(board["summary"]["release_authorized"])
        self.assertFalse(board["summary"]["commercial_authorized"])

    def test_plan_drift_fails_closed_at_campaign_level(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            shutil.copytree(ROOT / "config", root / "config")
            ledger_path = Path(temp) / "campaigns.jsonl"
            ledger = EvidenceCampaignLedger(root, ledger_path=ledger_path)
            event = ledger.create_campaign(
                environment_fingerprint=ENV_FINGERPRINT,
                source_revision=SOURCE_REVISION,
                actor=MANAGER,
            )
            plan_path = root / "config" / "v1" / "evidence_execution_plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            payload["notice"] = str(payload.get("notice") or "") + " ops2-drift"
            plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaises(EvidenceOperationsBoardError):
                EvidenceOperationsBoard(
                    root,
                    campaign_id=event["campaign_id"],
                    ledger_path=ledger_path,
                ).build()

    def test_tampered_campaign_ledger_fails_closed(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                ledger, campaign_id = self._campaign(temp)
                row = json.loads(ledger.path.read_text(encoding="utf-8").strip())
                row["actor"]["id"] = "tampered.actor"
                ledger.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
                with self.assertRaises(EvidenceOperationsBoardError):
                    EvidenceOperationsBoard(
                        ROOT,
                        campaign_id=campaign_id,
                        ledger_path=ledger.path,
                    ).build()

    def test_board_contains_no_forbidden_internal_keys(self) -> None:
        forbidden = {
            "evidence_ref", "evidence_event_id", "actor", "actor_id",
            "environment_fingerprint", "password", "token", "api_key",
            "secret", "credential", "private_key", "connection_string",
        }
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                board = EvidenceOperationsBoard(ROOT, ledger_path=Path(temp) / "campaigns.jsonl").build()
        self.assertFalse(forbidden & {key.casefold() for key in _walk_keys(board)})

    def test_markdown_explains_statuses_and_non_authorization_boundary(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                instance = EvidenceOperationsBoard(ROOT, ledger_path=Path(temp) / "campaigns.jsonl")
                markdown = instance.to_markdown(instance.build())
        self.assertIn("Mesa operativa de evidencia", markdown)
        self.assertIn("CAMPAIGN_REQUIRED", markdown)
        self.assertIn("WAITING_FOR_DEPENDENCY", markdown)
        self.assertIn("no autoriza producción ni pagos", markdown)
        self.assertNotIn("environment_fingerprint", markdown)
        self.assertNotIn("evidence_event_id", markdown)

    def test_cli_is_read_only_and_release_gate_remains_rc9(self) -> None:
        source = (ROOT / "tools" / "v1_evidence_execution_board.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn('add_parser("show"', source)
        self.assertIn('add_parser("write"', source)
        self.assertNotIn('add_parser("start', source)
        self.assertNotIn('add_parser("link', source)
        self.assertNotIn('add_parser("approve', source)
        self.assertNotIn('add_parser("ratify', source)
        self.assertNotIn('add_parser("authorize', source)
        self.assertIn("release_readiness_v1_rc9", release_cli)
        self.assertNotIn("evidence_execution_board_v1", release_cli)

    def test_ops2_does_not_expose_runtime_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("evidence_execution_board_v1", run_source)
        self.assertNotIn("v1_evidence_execution_board", run_source)


if __name__ == "__main__":
    unittest.main()
