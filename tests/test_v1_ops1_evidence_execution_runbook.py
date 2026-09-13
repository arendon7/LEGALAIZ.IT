from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_runbook_v1 import (
    EvidenceExecutionRunbook,
    EvidenceExecutionRunbookError,
    FORBIDDEN_OUTPUT_KEYS,
    RUNBOOK_SCHEMA,
)


ROOT = Path(__file__).resolve().parents[1]


def _walk_keys(value: object) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key).casefold())
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


class V1OPS1EvidenceExecutionRunbookTests(unittest.TestCase):
    def _build(self) -> dict[str, object]:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(Path(temp) / "runtime")}, clear=False):
                return EvidenceExecutionRunbook(ROOT).build()

    def test_runbook_covers_exact_22_canonical_controls_once(self) -> None:
        data = self._build()
        refs = [row["control_ref"] for row in data["packets"]]
        plan = json.loads((ROOT / "config" / "v1" / "evidence_execution_plan.json").read_text(encoding="utf-8"))
        expected = {row["ref"] for row in plan["controls"]}
        self.assertEqual(data["schema"], RUNBOOK_SCHEMA)
        self.assertEqual(data["controls"], 22)
        self.assertEqual(len(refs), 22)
        self.assertEqual(len(set(refs)), 22)
        self.assertEqual(set(refs), expected)

    def test_waves_are_topological_and_never_run_dependency_in_same_or_future_wave(self) -> None:
        data = self._build()
        wave_by_ref = {
            ref: wave["wave"]
            for wave in data["waves"]
            for ref in wave["controls"]
        }
        for packet in data["packets"]:
            for dependency in packet["prerequisites"]:
                self.assertLess(wave_by_ref[dependency], wave_by_ref[packet["control_ref"]])

    def test_every_packet_preserves_rc8_task_packet_contract_and_role_separation(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(Path(temp) / "runtime")}, clear=False):
                runbook = EvidenceExecutionRunbook(ROOT)
                data = runbook.build()
                for packet in data["packets"]:
                    canonical = dict(runbook.ledger.task_packet(packet["control_ref"]))
                    self.assertEqual(packet["executor_role"], canonical["executor_role"])
                    self.assertEqual(packet["reviewer_role"], canonical["reviewer_role"])
                    self.assertNotEqual(packet["executor_role"], packet["reviewer_role"])
                    self.assertEqual(packet["required_artifacts"], canonical["required_artifacts"])
                    self.assertEqual(packet["prerequisites"], canonical["prerequisites"])
                    self.assertEqual(packet["redaction_policy"], canonical["redaction_policy"])
                    self.assertEqual(packet["bundle_schema"], canonical["bundle_schema"])

    def test_all_controls_remain_pending_external_execution_and_unassigned_to_people(self) -> None:
        data = self._build()
        self.assertEqual(data["status"], "READY_FOR_HUMAN_EXTERNAL_EXECUTION")
        for packet in data["packets"]:
            self.assertEqual(packet["execution_status"], "PENDING_EXTERNAL_EXECUTION")
            self.assertEqual(packet["assignment_status"], "ROLE_DEFINED_PERSON_NOT_ASSIGNED")
            self.assertIn("sha256_manifest", packet["required_artifacts"])

    def test_runbook_contains_no_evidence_actor_fingerprint_or_secret_bearing_keys(self) -> None:
        data = self._build()
        keys = set(_walk_keys(data))
        self.assertFalse(keys.intersection(FORBIDDEN_OUTPUT_KEYS))
        text = json.dumps(data, ensure_ascii=False)
        for forbidden_literal in (
            '"evidence_event_id"',
            '"evidence_ref"',
            '"environment_fingerprint"',
            '"actor_id"',
        ):
            self.assertNotIn(forbidden_literal, text)

    def test_build_is_deterministic_and_does_not_create_campaign_ledger(self) -> None:
        with TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(runtime)}, clear=False):
                runbook = EvidenceExecutionRunbook(ROOT)
                ledger_path = runbook.ledger.path
                self.assertFalse(ledger_path.exists())
                first = runbook.build()
                second = runbook.build()
                self.assertEqual(first, second)
                self.assertFalse(ledger_path.exists())
                self.assertEqual(first["runbook_sha256"], second["runbook_sha256"])

    def test_markdown_is_complete_human_readable_and_preserves_non_authorization_boundary(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(Path(temp) / "runtime")}, clear=False):
                runbook = EvidenceExecutionRunbook(ROOT)
                data = runbook.build()
                markdown = runbook.to_markdown(data)
        for packet in data["packets"]:
            self.assertIn(f"`{packet['control_ref']}`", markdown)
        self.assertIn("No ejecuta controles", markdown)
        self.assertIn("no autoriza producción ni pagos", markdown)
        self.assertIn("RC9 Evidence Audit Pack", markdown)
        self.assertIn("RC10 Custody Export", markdown)
        self.assertIn(data["runbook_sha256"], markdown)

    def test_coordination_commands_are_templates_not_evidence_or_credentials(self) -> None:
        data = self._build()
        for packet in data["packets"]:
            commands = "\n".join(packet["coordination_commands"].values())
            self.assertIn("<CAMPAIGN_ID>", commands)
            self.assertIn("<EXECUTOR_ID>", commands)
            self.assertIn(f'--actor-role "{packet["executor_role"]}"', commands)
            self.assertNotIn("--evidence-event-id", commands)
            self.assertNotIn("password", commands.casefold())
            self.assertNotIn("api-key", commands.casefold())

    def test_global_flow_ends_in_human_versioned_authorization_not_ci_promotion(self) -> None:
        data = self._build()
        flow = " ".join(data["global_flow"])
        self.assertIn("decisiones humanas versionadas", flow)
        governance = data["governance"]
        self.assertTrue(governance["runbook_is_not_production_authorization"])
        self.assertTrue(governance["runbook_is_not_payment_authorization"])
        self.assertFalse(governance["mutates_campaign"])
        self.assertFalse(governance["mutates_evidence_ledgers"])
        self.assertFalse(governance["mutates_release_metadata"])

    def test_cli_is_read_only_composition_and_release_gate_remains_rc9(self) -> None:
        cli = (ROOT / "tools" / "v1_evidence_execution_runbook.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("show"', cli)
        self.assertIn('sub.add_parser("write"', cli)
        self.assertIn("release_readiness_v1_rc9", release_cli)
        self.assertNotIn("ops1", release_cli.casefold())
        for mutator in (
            "create_campaign(",
            "start_control(",
            "link_evidence(",
            "mark_review_ready(",
            "register_bundle(",
            "approve_review(",
            "ratify_release(",
        ):
            self.assertNotIn(mutator, cli)

    def test_ops1_does_not_expose_runtime_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("evidence_execution_runbook_v1", run_source)
        self.assertNotIn("v1_evidence_execution_runbook", run_source)


if __name__ == "__main__":
    unittest.main()
