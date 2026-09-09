from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from legalai_platform.evidence_audit_pack_v1_rc9 import (
    PACK_SCHEMA,
    EvidenceAuditPack,
    EvidenceAuditPackError,
)
from legalai_platform.release_readiness_v1_rc9 import (
    RC9_AUDIT_PACK_RUNTIME,
    RC9_AUDIT_PACK_STRUCTURE,
    assess_release_readiness,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "24e9dafdd1508189192daa17db957906119c6ae9"
ENV_FINGERPRINT = "c" * 64
MANAGER = {"id": "audit.manager", "role": "admin"}


class V1RC9EvidenceAuditPackTests(unittest.TestCase):
    def test_clean_pack_is_deterministic_redacted_and_covers_exact_22_controls(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                first = packer.build()
                second = packer.build()
        self.assertEqual(first["schema"], PACK_SCHEMA)
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertEqual(len(first["controls"]), 22)
        self.assertEqual(sum(row["source_framework"] == "RC2" for row in first["controls"]), 10)
        self.assertEqual(sum(row["source_framework"] == "RC4" for row in first["controls"]), 12)
        self.assertEqual(first["evidence"]["verified"], 0)
        self.assertFalse(first["evidence"]["real_production_evidence_complete"])
        self.assertFalse(first["evidence"]["commercial_evidence_complete"])
        self.assertFalse(first["release"]["real_legal_production"]["ready"])
        self.assertFalse(first["release"]["commercial_v1"]["ready"])
        self.assertTrue(first["boundaries"]["read_only"])
        self.assertFalse(first["boundaries"]["contains_evidence_payloads"])
        self.assertFalse(first["boundaries"]["contains_actor_identifiers"])
        self.assertFalse(first["boundaries"]["contains_environment_fingerprint"])
        self.assertFalse(first["boundaries"]["authorizes_real_production"])
        self.assertFalse(first["boundaries"]["authorizes_real_payments"])

    def test_pack_contains_no_forbidden_internal_keys_anywhere(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                pack = packer.build()
        forbidden = packer.forbidden_output_keys

        def walk(value: object) -> list[str]:
            hits: list[str] = []
            if isinstance(value, dict):
                for key, child in value.items():
                    if str(key).casefold() in forbidden:
                        hits.append(str(key))
                    hits.extend(walk(child))
            elif isinstance(value, list):
                for child in value:
                    hits.extend(walk(child))
            return hits

        self.assertEqual(walk(pack), [])

    def test_markdown_is_human_readable_and_does_not_leak_internal_evidence_plumbing(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                markdown = packer.to_markdown(packer.build())
        self.assertIn("# LegalAIZ.it — V1 Evidence Audit Pack", markdown)
        self.assertIn("## Controles de evidencia", markdown)
        self.assertIn("## Procedencia de autorización", markdown)
        self.assertIn("22", markdown)
        for forbidden in (
            "evidence_event_id", "evidence_path", "bundle_path", "manifest_path",
            "environment_fingerprint", "connection_string",
        ):
            self.assertNotIn(forbidden, markdown)

    def test_campaign_bound_pack_uses_rc8_1_semantics_without_exposing_environment_fingerprint(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                created = packer.ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                pack = packer.build(campaign_id=created["campaign_id"])
        campaign = pack["campaign"]
        self.assertEqual(campaign["status"], "CREATED")
        self.assertTrue(campaign["dependency_constraints_active"])
        self.assertGreater(campaign["dependency_blocked_controls"], 0)
        self.assertEqual(campaign["global_blockers"], [])
        self.assertNotIn("environment_fingerprint", campaign)
        self.assertNotIn(ENV_FINGERPRINT, json.dumps(pack, sort_keys=True))
        self.assertEqual(campaign["source_revision"], SOURCE_REVISION)

    def test_campaign_activity_changes_snapshot_without_mutating_evidence_or_authorization(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                created = packer.ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                before = packer.build(campaign_id=created["campaign_id"])
                independent = next(row for row in packer.audit.controls.values() if not row.get("prerequisites"))
                packer.ledger.start_control(
                    created["campaign_id"],
                    independent["ref"],
                    actor={"id": "executor.audit", "role": independent["executor_role"]},
                )
                after = packer.build(campaign_id=created["campaign_id"])
        self.assertNotEqual(before["snapshot_sha256"], after["snapshot_sha256"])
        self.assertEqual(after["campaign"]["status"], "IN_PROGRESS")
        self.assertEqual(after["evidence"]["verified"], 0)
        self.assertFalse(after["release"]["real_legal_production"]["ready"])
        self.assertFalse(after["release"]["commercial_v1"]["ready"])

    def test_evidence_complete_snapshot_still_does_not_become_human_authorization(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                base = packer.audit.build()
                fake_controls = []
                for row in base["controls"]:
                    item = dict(row)
                    item["status"] = "VERIFIED"
                    item["passed"] = True
                    item["dependency_blockers"] = []
                    fake_controls.append(item)
                fake = dict(base)
                fake["controls"] = fake_controls
                fake["summary"] = {
                    "verified": 22,
                    "total": 22,
                    "dependency_blocked": 0,
                    "status_counts": {"VERIFIED": 22},
                    "real_production_evidence_complete": True,
                    "commercial_evidence_complete": True,
                    "release_authorized": False,
                    "commercial_authorized": False,
                }
                with patch.object(packer.audit, "build", return_value=fake):
                    pack = packer.build()
        self.assertTrue(pack["evidence"]["real_production_evidence_complete"])
        self.assertTrue(pack["evidence"]["commercial_evidence_complete"])
        self.assertFalse(pack["release"]["real_legal_production"]["provenance_valid"])
        self.assertFalse(pack["release"]["commercial_v1"]["provenance_valid"])
        self.assertIn("OBTAIN_VERSIONED_HUMAN_PRODUCTION_AUTHORIZATION", pack["next_actions"])
        self.assertIn("OBTAIN_VERSIONED_HUMAN_COMMERCIAL_AUTHORIZATION", pack["next_actions"])
        self.assertFalse(pack["boundaries"]["evidence_complete_is_release_authorization"])

    def test_tampered_runtime_ledger_fails_pack_closed_but_does_not_block_code_candidate(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                packer = EvidenceAuditPack(ROOT)
                packer.ledger.create_campaign(
                    environment_fingerprint=ENV_FINGERPRINT,
                    source_revision=SOURCE_REVISION,
                    actor=MANAGER,
                )
                row = json.loads(packer.ledger.path.read_text(encoding="utf-8").strip())
                row["actor"]["id"] = "tampered.audit.actor"
                packer.ledger.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
                with self.assertRaises(EvidenceAuditPackError):
                    packer.build()
                report = assess_release_readiness(ROOT)
        self.assertTrue(report["code_release_candidate"]["ready"], report["code_release_candidate"])
        self.assertEqual(report["code_release_candidate"]["status"], "RC_CODE_READY")
        self.assertFalse(report["evidence_audit_pack"]["runtime_snapshot"]["valid"])
        self.assertIn(RC9_AUDIT_PACK_RUNTIME, report["real_legal_production"]["blockers"])
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertFalse(report["commercial_v1"]["ready"])
        self.assertTrue(report["governance"]["audit_pack_runtime_health_is_not_code_readiness"])

    def test_structural_rc9_failure_blocks_code_candidate(self) -> None:
        with patch(
            "legalai_platform.release_readiness_v1_rc9.EvidenceAuditPack",
            side_effect=EvidenceAuditPackError("invalid-policy"),
        ):
            report = assess_release_readiness(ROOT)
        self.assertFalse(report["code_release_candidate"]["ready"])
        self.assertEqual(report["code_release_candidate"]["status"], "RC_CODE_BLOCKED")
        self.assertIn(RC9_AUDIT_PACK_STRUCTURE, report["real_legal_production"]["blockers"])
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertFalse(report["commercial_v1"]["ready"])

    def test_clean_release_readiness_exposes_rc9_without_authorizing_real_use(self) -> None:
        with TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"LEGAL_RUNTIME_DIR": temp}, clear=False):
                report = assess_release_readiness(ROOT)
        self.assertTrue(report["code_release_candidate"]["ready"], report["code_release_candidate"])
        audit_pack = report["evidence_audit_pack"]
        self.assertTrue(audit_pack["structure"]["valid"])
        self.assertTrue(audit_pack["runtime_snapshot"]["valid"])
        self.assertTrue(audit_pack["runtime_snapshot"]["deterministic"])
        self.assertEqual(audit_pack["runtime_snapshot"]["total"], 22)
        self.assertEqual(audit_pack["runtime_snapshot"]["verified"], 0)
        self.assertFalse(report["real_legal_production"]["ready"])
        self.assertFalse(report["commercial_v1"]["ready"])
        self.assertTrue(report["governance"]["audit_pack_is_read_only"])
        self.assertFalse(report["governance"]["audit_pack_contains_actor_identifiers"])

    def test_audit_cli_is_read_only_and_release_chain_is_rc9_to_rc8(self) -> None:
        cli = (ROOT / "tools" / "v1_evidence_audit_pack.py").read_text(encoding="utf-8")
        release_cli = (ROOT / "tools" / "v1_release_readiness_audit.py").read_text(encoding="utf-8")
        rc9 = (ROOT / "legalai_platform" / "release_readiness_v1_rc9.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.evidence_audit_pack_v1_rc9 import EvidenceAuditPack", cli)
        self.assertIn("from legalai_platform.release_readiness_v1_rc9 import assess_release_readiness", release_cli)
        self.assertIn(
            "from legalai_platform.release_readiness_v1_rc8 import assess_release_readiness as assess_rc8_release_readiness",
            rc9,
        )
        for mutator in ("start_control(", "link_evidence(", "register_bundle(", "approve_review(", "ratify_release("):
            self.assertNotIn(mutator, cli)

    def test_rc9_does_not_expose_runtime_endpoint(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("evidence_audit_pack_v1_rc9", run_source)
        self.assertNotIn("release_readiness_v1_rc9", run_source)
        self.assertNotIn("/api/release", run_source)


if __name__ == "__main__":
    unittest.main()
