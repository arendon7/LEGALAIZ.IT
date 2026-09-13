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
    ASSIGNMENT_MANIFEST_SCHEMA,
    PrivateAssignmentError,
    PrivateAssignmentPacketGenerator,
    VALIDATION_SCHEMA,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "8404a409ed0fc3e168e4fa370869cd2444ee8345"
ENV_FINGERPRINT = "d" * 64
MANAGER = {"id": "ops3.manager", "role": "admin"}


class V1OPS3PrivateAssignmentPacketsTests(unittest.TestCase):
    def _fixture(self, temp: str):
        ledger_path = Path(temp) / "campaigns.jsonl"
        ledger = EvidenceCampaignLedger(ROOT, ledger_path=ledger_path)
        campaign = ledger.create_campaign(
            environment_fingerprint=ENV_FINGERPRINT,
            source_revision=SOURCE_REVISION,
            actor=MANAGER,
        )
        campaign_id = campaign["campaign_id"]
        board = EvidenceOperationsBoard(
            ROOT,
            campaign_id=campaign_id,
            ledger_path=ledger_path,
        ).build()
        people = []
        assignments = []
        for index, control in enumerate(board["controls"], 1):
            executor_ref = f"P-EXE-{index:02d}"
            reviewer_ref = f"P-REV-{index:02d}"
            people.extend([
                {
                    "person_ref": executor_ref,
                    "display_name": f"Executor Private {index:02d}",
                    "actor_id": f"ops3.exec.{index:02d}",
                    "roles": [control["executor_role"]],
                    "contact": f"executor{index:02d}@private.invalid",
                },
                {
                    "person_ref": reviewer_ref,
                    "display_name": f"Reviewer Private {index:02d}",
                    "actor_id": f"ops3.review.{index:02d}",
                    "roles": [control["reviewer_role"]],
                    "contact": f"reviewer{index:02d}@private.invalid",
                },
            ])
            assignments.append({
                "control_ref": control["control_ref"],
                "executor_person_ref": executor_ref,
                "reviewer_person_ref": reviewer_ref,
            })
        payload = {
            "schema": ASSIGNMENT_INPUT_SCHEMA,
            "campaign_id": campaign_id,
            "people": people,
            "assignments": assignments,
        }
        path = Path(temp) / "private-assignments.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(path, 0o600)
        return ledger, board, path, payload

    @staticmethod
    def _generator(ledger: EvidenceCampaignLedger) -> PrivateAssignmentPacketGenerator:
        return PrivateAssignmentPacketGenerator(ROOT, ledger_path=ledger.path)

    def test_complete_assignment_validates_exact_22_controls_and_sod(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, board, path, _ = self._fixture(temp)
            validated = self._generator(ledger).validate(path)
        self.assertEqual(validated["schema"], VALIDATION_SCHEMA)
        self.assertEqual(validated["controls"], 22)
        self.assertEqual(len(validated["assignments"]), len(board["controls"]))
        self.assertTrue(validated["separation_of_duties_valid"])
        self.assertFalse(validated["repository_persistence_allowed"])
        self.assertFalse(validated["ledger_mutation_allowed"])
        self.assertFalse(validated["release_authorization_changed"])

    def test_public_validation_summary_does_not_echo_private_identity_fields(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            generator = self._generator(ledger)
            summary = generator.public_validation_summary(generator.validate(path))
        serialized = json.dumps(summary, ensure_ascii=False)
        for key in ("display_name", "actor_id", "contact", "people", "assignments"):
            self.assertNotIn(key, summary)
        for field in ("display_name", "actor_id", "contact"):
            self.assertNotIn(payload["people"][0][field], serialized)

    def test_missing_or_duplicate_control_is_rejected_fail_closed(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            payload["assignments"].pop()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

            _, _, path2, payload2 = self._fixture(temp)
            payload2["assignments"].append(dict(payload2["assignments"][0]))
            path2.write_text(json.dumps(payload2), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path2)

    def test_same_person_cannot_execute_and_review_same_control(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            payload["assignments"][0]["reviewer_person_ref"] = payload["assignments"][0]["executor_person_ref"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

    def test_role_mismatch_is_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, board, path, payload = self._fixture(temp)
            first = payload["assignments"][0]
            executor = next(p for p in payload["people"] if p["person_ref"] == first["executor_person_ref"])
            executor["roles"] = [board["controls"][0]["reviewer_role"]]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

    def test_duplicate_actor_id_cannot_hide_same_identity_behind_two_refs(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            payload["people"][1]["actor_id"] = payload["people"][0]["actor_id"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

    def test_unknown_secret_bearing_or_extra_fields_are_rejected(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            payload["password"] = "must-never-be-here"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

    def test_assignment_input_inside_versionable_repo_path_is_rejected_before_parse(self) -> None:
        tracked = ROOT / "docs" / "release" / "V1_OPS2_EVIDENCE_OPERATIONS_BOARD.md"
        with self.assertRaises(PrivateAssignmentError):
            PrivateAssignmentPacketGenerator(ROOT).validate(tracked)

    def test_output_inside_versionable_repo_path_is_rejected_without_creation(self) -> None:
        forbidden = ROOT / "docs" / "ops3-private-output-must-not-exist"
        self.assertFalse(forbidden.exists())
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, _ = self._fixture(temp)
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).write(path, forbidden)
        self.assertFalse(forbidden.exists())

    def test_write_creates_private_manifest_and_22_packets_with_restrictive_permissions(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            output = Path(temp) / "private-packets"
            result = self._generator(ledger).write(path, output)
            manifest = json.loads((output / "assignment-manifest.json").read_text(encoding="utf-8"))
            packet_files = sorted((output / "controls").glob("*.md"))
            self.assertEqual(result["packet_files"], 22)
            self.assertEqual(result["files_written"], 24)
            self.assertEqual(manifest["schema"], ASSIGNMENT_MANIFEST_SCHEMA)
            self.assertEqual(len(manifest["packets"]), 22)
            self.assertEqual(len(packet_files), 22)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((output / "controls").stat().st_mode), 0o700)
            self.assertTrue(all(
                stat.S_IMODE(item.stat().st_mode) == 0o600
                for item in output.rglob("*") if item.is_file()
            ))
            private_text = packet_files[0].read_text(encoding="utf-8")
            self.assertTrue(any(person["display_name"] in private_text for person in payload["people"]))
            self.assertIn("CONFIDENCIAL / DATOS PERSONALES", private_text)

    def test_manifest_and_readme_are_redacted_while_private_packet_has_minimum_identity(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            output = Path(temp) / "private-packets"
            self._generator(ledger).write(path, output)
            safe_text = (
                (output / "assignment-manifest.json").read_text(encoding="utf-8")
                + (output / "README_PRIVATE.md").read_text(encoding="utf-8")
            )
            private_text = next((output / "controls").glob("*.md")).read_text(encoding="utf-8")
        for person in payload["people"]:
            self.assertNotIn(person["display_name"], safe_text)
            self.assertNotIn(person["contact"], safe_text)
            self.assertNotIn(person["actor_id"], safe_text)
        self.assertTrue(any(person["actor_id"] in private_text for person in payload["people"]))

    def test_write_never_copies_input_or_persists_hashes_of_private_packets(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, _ = self._fixture(temp)
            output = Path(temp) / "private-packets"
            self._generator(ledger).write(path, output)
            names = {item.name for item in output.rglob("*") if item.is_file()}
            manifest = json.loads((output / "assignment-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn(path.name, names)
        self.assertFalse(manifest["input_copied"])
        self.assertFalse(manifest["packet_hashes_persisted"])

    def test_validate_and_write_do_not_mutate_campaign_ledger(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, _ = self._fixture(temp)
            before = ledger.path.read_bytes()
            generator = self._generator(ledger)
            generator.validate(path)
            after_validate = ledger.path.read_bytes()
            generator.write(path, Path(temp) / "private-packets")
            after_write = ledger.path.read_bytes()
        self.assertEqual(before, after_validate)
        self.assertEqual(before, after_write)

    def test_existing_output_is_never_overwritten(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, _ = self._fixture(temp)
            output = Path(temp) / "private-packets"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).write(path, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_aborted_campaign_cannot_receive_assignment_packets(self) -> None:
        with TemporaryDirectory() as temp, patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
            ledger, _, path, payload = self._fixture(temp)
            ledger.abort_campaign(payload["campaign_id"], reason_code="CAMPAIGN_CANCELLED", actor=MANAGER)
            with self.assertRaises(PrivateAssignmentError):
                self._generator(ledger).validate(path)

    def test_cli_is_private_read_write_only_and_release_gate_remains_rc9(self) -> None:
        source = (ROOT / "tools" / "v1_private_assignment_packets.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn('add_parser("validate"', source)
        self.assertIn('add_parser("write"', source)
        for forbidden in ("start-control", "link-evidence", "approve", "ratify", "authorize"):
            self.assertNotIn(f'add_parser("{forbidden}"', source)
        self.assertIn("release_readiness_v1_rc9", release_cli)
        self.assertNotIn("private_assignment_packets_v1", release_cli)

    def test_ops3_has_no_runtime_endpoint_and_uses_existing_private_ignore_roots(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("private_assignment_packets_v1", run_source)
        self.assertNotIn("v1_private_assignment_packets", run_source)
        for marker in ("runtime/*", "secrets/", "output/"):
            self.assertIn(marker, ignore)


if __name__ == "__main__":
    unittest.main()
