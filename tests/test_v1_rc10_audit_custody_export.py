from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.audit_custody_export_v1_rc10 import (
    AuditCustodyExport,
    AuditCustodyExportError,
    CANONICAL_FILES,
    ENVELOPE_SCHEMA,
    VERIFY_SCHEMA,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "24e9dafdd1508189192daa17db957906119c6ae9"
ENV_FINGERPRINT = "d" * 64
MANAGER = {"id": "custody.manager", "role": "admin"}


class V1RC10AuditCustodyExportTests(unittest.TestCase):
    def test_clean_export_creates_exact_immutable_bundle_and_verifies(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                result = custody.export(base / "exports")
                bundle = Path(result["bundle_dir"])
                verification = custody.verify(
                    bundle,
                    expected_envelope_sha256=result["envelope_sha256"],
                )
                bundle_names = sorted(path.name for path in bundle.iterdir())

        self.assertTrue(result["created"])
        self.assertFalse(result["idempotent"])
        self.assertFalse(result["authorization_changed"])
        self.assertEqual(bundle_names, sorted(CANONICAL_FILES))
        self.assertEqual(bundle.name, result["envelope_sha256"])
        self.assertEqual(verification["schema"], VERIFY_SCHEMA)
        self.assertTrue(verification["valid"])
        self.assertTrue(verification["external_anchor_checked"])
        self.assertFalse(verification["authorization_changed"])

    def test_same_snapshot_export_is_idempotent_and_does_not_create_second_bundle(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                first = custody.export(base / "exports")
                second = custody.export(base / "exports")
                bundles = [path for path in (base / "exports").iterdir() if path.is_dir()]

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["bundle_dir"], second["bundle_dir"])
        self.assertEqual(first["envelope_sha256"], second["envelope_sha256"])
        self.assertEqual(len(bundles), 1)

    def test_tampered_json_or_markdown_fails_closed(self) -> None:
        for filename in ("audit-pack.json", "audit-pack.md"):
            with self.subTest(filename=filename):
                with TemporaryDirectory() as temp:
                    base = Path(temp)
                    with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                        custody = AuditCustodyExport(ROOT)
                        result = custody.export(base / "exports")
                        path = Path(result["bundle_dir"]) / filename
                        path.write_bytes(path.read_bytes() + b"\nTAMPERED\n")
                        with self.assertRaises(AuditCustodyExportError):
                            custody.verify(result["bundle_dir"])

    def test_manifest_tampering_fails_its_own_envelope_digest(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                result = custody.export(base / "exports")
                manifest_path = Path(result["bundle_dir"]) / "custody-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["campaign_bound"] = not manifest["campaign_bound"]
                manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
                with self.assertRaises(AuditCustodyExportError):
                    custody.verify(result["bundle_dir"])

    def test_external_anchor_mismatch_fails_closed(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                result = custody.export(base / "exports")
                wrong = "f" * 64
                self.assertNotEqual(wrong, result["envelope_sha256"])
                with self.assertRaises(AuditCustodyExportError):
                    custody.verify(result["bundle_dir"], expected_envelope_sha256=wrong)

    def test_existing_invalid_bundle_is_never_overwritten(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                result = custody.export(base / "exports")
                markdown = Path(result["bundle_dir"]) / "audit-pack.md"
                markdown.write_text("quarantined-tampered-copy\n", encoding="utf-8")
                before = markdown.read_bytes()
                with self.assertRaises(AuditCustodyExportError):
                    custody.export(base / "exports")
                after = markdown.read_bytes()

        self.assertEqual(before, after)

    def test_campaign_export_redacts_actor_and_environment_and_does_not_mutate_ledger(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                from legalai_platform.evidence_audit_pack_v1_rc9 import EvidenceAuditPack
                audit = EvidenceAuditPack(ROOT)
                created = audit.ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                ledger_before = audit.ledger.path.read_bytes()
                result = custody.export(base / "exports", campaign_id=created["campaign_id"])
                ledger_after = audit.ledger.path.read_bytes()
                bundle = Path(result["bundle_dir"])
                exported = "\n".join(
                    (bundle / name).read_text(encoding="utf-8")
                    for name in CANONICAL_FILES
                )
                json_text = (bundle / "audit-pack.json").read_text(encoding="utf-8")
                markdown_text = (bundle / "audit-pack.md").read_text(encoding="utf-8")

        self.assertEqual(ledger_before, ledger_after)
        self.assertNotIn(ENV_FINGERPRINT, exported)
        self.assertNotIn(MANAGER["id"], exported)
        self.assertNotIn("evidence_event_id", json_text)
        self.assertNotIn("evidence_event_id", markdown_text)

    def test_manifest_hashes_only_two_redacted_payload_files_and_digest_is_not_signature(self) -> None:
        with TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": str(base / "runtime")}, clear=False):
                custody = AuditCustodyExport(ROOT)
                result = custody.export(base / "exports")
                bundle = Path(result["bundle_dir"])
                manifest = json.loads((bundle / "custody-manifest.json").read_text(encoding="utf-8"))
                payload_checks = {
                    row["name"]: (
                        sha256((bundle / row["name"]).read_bytes()).hexdigest(),
                        len((bundle / row["name"]).read_bytes()),
                    )
                    for row in manifest["files"]
                }

        self.assertEqual(manifest["schema"], ENVELOPE_SCHEMA)
        self.assertEqual([row["name"] for row in manifest["files"]], ["audit-pack.json", "audit-pack.md"])
        for row in manifest["files"]:
            payload_hash, payload_size = payload_checks[row["name"]]
            self.assertEqual(row["sha256"], payload_hash)
            self.assertEqual(row["size_bytes"], payload_size)
        self.assertFalse(manifest["governance"]["contains_evidence_artifact_hashes"])
        self.assertFalse(manifest["governance"]["digest_is_digital_signature"])
        self.assertTrue(manifest["governance"]["external_anchor_required_for_non_repudiation"])
        self.assertFalse(manifest["governance"]["authorizes_real_production"])
        self.assertFalse(manifest["governance"]["authorizes_real_payments"])

    def test_policy_keeps_retention_as_organizational_not_legal_conclusion(self) -> None:
        custody = AuditCustodyExport(ROOT)
        governance = custody.policy["governance"]
        self.assertTrue(governance["retention_period_is_organization_defined"])
        self.assertTrue(governance["retention_period_is_not_a_legal_conclusion"])
        self.assertTrue(governance["external_anchor_required_for_non_repudiation"])
        self.assertTrue(governance["existing_invalid_bundle_is_never_overwritten"])

    def test_cli_is_operational_export_verify_only_and_does_not_mutate_release_gate(self) -> None:
        cli = (ROOT / "tools" / "v1_evidence_audit_export.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("export"', cli)
        self.assertIn('sub.add_parser("verify"', cli)
        self.assertIn("release_readiness_v1_rc9", release_cli)
        self.assertNotIn("release_readiness_v1_rc10", release_cli)
        for mutator in (
            "start_control(",
            "link_evidence(",
            "register_bundle(",
            "approve_review(",
            "ratify_release(",
            "set_authorization(",
        ):
            self.assertNotIn(mutator, cli)

    def test_rc10_does_not_expose_runtime_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("audit_custody_export_v1_rc10", run_source)
        self.assertNotIn("v1_evidence_audit_export", run_source)
        self.assertNotIn("/api/release", run_source)


if __name__ == "__main__":
    unittest.main()
