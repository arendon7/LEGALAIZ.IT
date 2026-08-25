from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_execution_board_v1 import EvidenceOperationsBoard
from legalai_platform.evidence_orchestration_v1_rc8_1 import EvidenceCampaignLedger
from legalai_platform.private_assignment_packets_v1 import (
    ASSIGNMENT_INPUT_SCHEMA,
    PrivateAssignmentPacketGenerator,
)
from legalai_platform.private_execution_dispatch_guard_v1 import (
    DISPATCH_MANIFEST_SCHEMA,
    PREFLIGHT_SCHEMA,
    PrivateDispatchGuardError,
    PrivateExecutionDispatchGuard,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "74ef44cd103e1e12477efc7ed8c7241aed765bb3"
ENV_FINGERPRINT = "e" * 64
MANAGER = {"id": "ops4.manager", "role": "admin"}


class V1OPS4PrivateExecutionDispatchGuardTests(unittest.TestCase):
    def _fixture(self, temp: str):
        ledger_path = Path(temp) / "campaigns.jsonl"
        ledger = EvidenceCampaignLedger(ROOT, ledger_path=ledger_path)
        created = ledger.create_campaign(
            environment_fingerprint=ENV_FINGERPRINT,
            source_revision=SOURCE_REVISION,
            actor=MANAGER,
        )
        campaign_id = created["campaign_id"]
        board = EvidenceOperationsBoard(ROOT, campaign_id=campaign_id, ledger_path=ledger_path).build()
        people = []
        assignments = []
        for index, control in enumerate(board["controls"], 1):
            executor_ref = f"P-EXE-{index:02d}"
            reviewer_ref = f"P-REV-{index:02d}"
            people.extend([
                {
                    "person_ref": executor_ref,
                    "display_name": f"OPS4 Executor {index:02d}",
                    "actor_id": f"ops4.exec.{index:02d}",
                    "roles": [control["executor_role"]],
                    "contact": f"ops4-executor-{index:02d}@private.invalid",
                },
                {
                    "person_ref": reviewer_ref,
                    "display_name": f"OPS4 Reviewer {index:02d}",
                    "actor_id": f"ops4.review.{index:02d}",
                    "roles": [control["reviewer_role"]],
                    "contact": f"ops4-reviewer-{index:02d}@private.invalid",
                },
            ])
            assignments.append({
                "control_ref": control["control_ref"],
                "executor_person_ref": executor_ref,
                "reviewer_person_ref": reviewer_ref,
            })
        assignment = Path(temp) / "assignment.json"
        assignment.write_text(json.dumps({
            "schema": ASSIGNMENT_INPUT_SCHEMA,
            "campaign_id": campaign_id,
            "people": people,
            "assignments": assignments,
        }), encoding="utf-8")
        os.chmod(assignment, 0o600)
        pack = Path(temp) / "ops3-pack"
        PrivateAssignmentPacketGenerator(ROOT, ledger_path=ledger_path).write(assignment, pack)
        return ledger, board, pack, people

    @staticmethod
    def _guard(ledger: EvidenceCampaignLedger) -> PrivateExecutionDispatchGuard:
        return PrivateExecutionDispatchGuard(ROOT, ledger_path=ledger.path)

    def test_preflight_current_pack_selects_only_ready_to_execute(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            result = self._guard(ledger).preflight(pack)
        self.assertEqual(result["schema"], PREFLIGHT_SCHEMA)
        self.assertTrue(result["source_board_current"])
        self.assertTrue(result["dispatch_allowed"])
        self.assertGreater(result["dispatchable_count"], 0)
        self.assertEqual(result["dispatchable_count"] + len(result["nondispatchable_controls"]), 22)
        self.assertTrue(all(row["status"] == "READY_TO_EXECUTE" for row in result["dispatchable_controls"]))
        self.assertFalse(result["network_delivery_performed"])
        self.assertFalse(result["control_execution_performed"])
        self.assertFalse(result["release_authorization_changed"])

    def test_preflight_output_is_redacted_from_people_and_actor_ids(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, people = self._fixture(temp)
            result = self._guard(ledger).preflight(pack)
        serialized = json.dumps(result, ensure_ascii=False)
        for person in people:
            self.assertNotIn(person["display_name"], serialized)
            self.assertNotIn(person["contact"], serialized)
            self.assertNotIn(person["actor_id"], serialized)
            self.assertNotIn(person["person_ref"], serialized)

    def test_any_campaign_event_makes_source_board_stale_and_blocks_dispatch(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, board, pack, _ = self._fixture(temp)
            ready = next(row for row in board["controls"] if row["work_status"] == "READY_TO_EXECUTE")
            ledger.start_control(
                board["campaign"]["campaign_id"],
                ready["control_ref"],
                actor={"id": "ops4.actual.executor", "role": ready["executor_role"]},
            )
            result = self._guard(ledger).preflight(pack)
            self.assertFalse(result["source_board_current"])
            self.assertFalse(result["dispatch_allowed"])
            self.assertEqual(result["dispatchable_count"], 0)
            self.assertIn("STALE_SOURCE_BOARD", result["blockers"])
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).write(pack, Path(temp) / "dispatch")

    def test_aborted_campaign_is_blocked_and_never_dispatches(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, board, pack, _ = self._fixture(temp)
            ledger.abort_campaign(board["campaign"]["campaign_id"], reason_code="CAMPAIGN_CANCELLED", actor=MANAGER)
            result = self._guard(ledger).preflight(pack)
        self.assertFalse(result["dispatch_allowed"])
        self.assertEqual(result["dispatchable_count"], 0)
        self.assertIn("CAMPAIGN_ABORTED", result["blockers"])
        self.assertIn("STALE_SOURCE_BOARD", result["blockers"])

    def test_write_copies_only_dispatchable_packets_and_uses_restrictive_permissions(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            guard = self._guard(ledger)
            preflight = guard.preflight(pack)
            output = Path(temp) / "dispatch"
            result = guard.write(pack, output)
            manifest = json.loads((output / "dispatch-manifest.json").read_text(encoding="utf-8"))
            packets = sorted((output / "controls").glob("*.md"))
            self.assertEqual(result["dispatchable_count"], preflight["dispatchable_count"])
            self.assertEqual(result["files_written"], preflight["dispatchable_count"] + 2)
            self.assertEqual(len(packets), preflight["dispatchable_count"])
            self.assertEqual(manifest["schema"], DISPATCH_MANIFEST_SCHEMA)
            self.assertEqual(manifest["controls"], preflight["dispatchable_count"])
            self.assertTrue(all(row["work_status"] == "READY_TO_EXECUTE" for row in manifest["packets"]))
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((output / "controls").stat().st_mode), 0o700)
            self.assertTrue(all(
                stat.S_IMODE(item.stat().st_mode) == 0o600
                for item in output.rglob("*") if item.is_file()
            ))

    def test_dispatch_manifest_and_readme_do_not_echo_private_identity(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, people = self._fixture(temp)
            output = Path(temp) / "dispatch"
            self._guard(ledger).write(pack, output)
            safe = (
                (output / "dispatch-manifest.json").read_text(encoding="utf-8")
                + (output / "README_PRIVATE.md").read_text(encoding="utf-8")
            )
        for person in people:
            self.assertNotIn(person["display_name"], safe)
            self.assertNotIn(person["contact"], safe)
            self.assertNotIn(person["actor_id"], safe)
            self.assertNotIn(person["person_ref"], safe)

    def test_dispatch_manifest_does_not_persist_private_packet_hashes(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            output = Path(temp) / "dispatch"
            self._guard(ledger).write(pack, output)
            manifest = json.loads((output / "dispatch-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["packet_hashes_persisted"])
        self.assertIn("source_board_sha256", manifest)
        self.assertIn("current_board_sha256", manifest)
        for row in manifest["packets"]:
            self.assertNotIn("sha256", json.dumps(row).lower())

    def test_preflight_and_write_never_mutate_campaign_ledger(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            before = ledger.path.read_bytes()
            guard = self._guard(ledger)
            guard.preflight(pack)
            after_preflight = ledger.path.read_bytes()
            guard.write(pack, Path(temp) / "dispatch")
            after_write = ledger.path.read_bytes()
        self.assertEqual(before, after_preflight)
        self.assertEqual(before, after_write)

    def test_missing_private_packet_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            first = next((pack / "controls").glob("*.md"))
            first.unlink()
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_symlink_private_packet_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            files = sorted((pack / "controls").glob("*.md"))
            victim, source = files[0], files[1]
            victim.unlink()
            victim.symlink_to(source)
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_packet_path_traversal_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            path = pack / "assignment-manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["packets"][0]["packet_file"] = "../escape.md"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_packet_binding_tamper_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            path = next((pack / "controls").glob("*.md"))
            text = path.read_text(encoding="utf-8").replace("- Campaña: `", "- Campaña alterada: `", 1)
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_manifest_extra_identity_field_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            path = pack / "assignment-manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["actor_id"] = "must-not-be-here"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_manifest_status_tamper_is_rejected_by_packet_binding(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            path = pack / "assignment-manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["packets"][0]["work_status"] = "VERIFIED"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).preflight(pack)

    def test_versionable_repo_pack_and_output_paths_are_rejected(self) -> None:
        versionable = ROOT / "docs" / "release"
        with self.assertRaises(PrivateDispatchGuardError):
            PrivateExecutionDispatchGuard(ROOT).preflight(versionable)
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            forbidden = ROOT / "docs" / "ops4-dispatch-must-not-exist"
            self.assertFalse(forbidden.exists())
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).write(pack, forbidden)
            self.assertFalse(forbidden.exists())

    def test_existing_dispatch_output_is_never_overwritten(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, pack, _ = self._fixture(temp)
            output = Path(temp) / "dispatch"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(PrivateDispatchGuardError):
                self._guard(ledger).write(pack, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_ops4_has_no_network_delivery_or_execution_primitives(self) -> None:
        source = (ROOT / "legalai_platform" / "private_execution_dispatch_guard_v1.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "requests", "urllib", "socket", ".start_control(", "link_evidence("):
            self.assertNotIn(forbidden, source)
        self.assertIn('DISPATCHABLE_STATUSES = frozenset({"READY_TO_EXECUTE"})', source)

    def test_cli_only_preflight_write_and_release_gate_remains_rc9(self) -> None:
        cli = (ROOT / "tools" / "v1_private_execution_dispatch.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn('add_parser("preflight"', cli)
        self.assertIn('add_parser("write"', cli)
        for forbidden in ("send", "deliver", "start-control", "link-evidence", "approve", "ratify", "authorize"):
            self.assertNotIn(f'add_parser("{forbidden}"', cli)
        self.assertIn("release_readiness_v1_rc9", release_cli)
        self.assertNotIn("private_execution_dispatch_guard_v1", release_cli)

    def test_ops4_has_no_runtime_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("private_execution_dispatch_guard_v1", run_source)
        self.assertNotIn("v1_private_execution_dispatch", run_source)


if __name__ == "__main__":
    unittest.main()
