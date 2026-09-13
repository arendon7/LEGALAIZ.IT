from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from legalai_platform import release_metadata
from legalai_platform.external_evidence_dossier_v1_rc2 import (
    ExternalEvidenceDossier,
    ExternalEvidenceError,
    ExternalEvidenceIntegrityError,
    ExternalEvidencePermissionError,
)
from legalai_platform.operational_security import ExternalAttestationRegistry
from legalai_platform.v1_rc2_release_assurance import (
    V1RC2ReleaseAssuranceError,
    V1RC2ReleaseAssuranceGate,
)


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def good_production_env() -> dict[str, str]:
    return {
        "LEGAL_PROFILE": "production",
        "LEGAL_APP_ENV": "production",
        "LEGAL_PUBLIC_BASE_URL": "https://app.legalaiz.test",
        "LEGAL_SECURE_COOKIES": "true",
        "LEGAL_REQUIRE_ORIGIN_CHECK": "true",
        "LEGAL_TRUST_PROXY": "true",
        "LEGAL_TRUSTED_PROXY_IPS": "10.20.0.10,10.20.0.11",
        "LEGAL_ALLOW_DEMO_ACCOUNTS": "false",
        "LEGAL_PUBLIC_DEMO_MODE": "false",
        "LEGAL_DATABASE_BACKEND": "postgresql",
        "DATABASE_URL": "postgresql://runtime-user@db.internal/legalaiz",
        "LEGAL_POSTGRES_EXTERNAL_CERTIFIED": "true",
        "LEGAL_OBJECT_ENCRYPTION": "true",
        "LEGAL_VOLUME_ENCRYPTION_CONFIRMED": "true",
        "LEGAL_MALWARE_SCANNER": "clamav",
        "LEGAL_REQUIRE_MFA_ROLES": "admin,specialist",
        "LEGAL_MASTER_KEY_SEED": "managed-rc2-secret-material",
        "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "false",
        "LEGAL_REAL_PAYMENTS_AUTHORIZED": "false",
        "LEGAL_PAYMENT_PROVIDER": "sandbox",
        "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "false",
        "LEGAL_COMMUNICATION_PROVIDER": "disabled",
        "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_PRIVACY_FINAL_APPROVED": "false",
    }


class V1RC2ExternalEvidenceAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.dossier_path = base / "dossier.jsonl"
        self.evidence_root = base / "evidence"
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.clock = [datetime(2026, 8, 25, 1, 0, tzinfo=UTC)]
        self.dossier = ExternalEvidenceDossier(
            ROOT,
            dossier_path=self.dossier_path,
            evidence_root=self.evidence_root,
            now_factory=lambda: self.clock[0],
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_evidence(self, control: str, content: str | None = None) -> str:
        name = f"{control}.txt"
        (self.evidence_root / name).write_text(content or f"external evidence for {control}\n", encoding="utf-8")
        return name

    def _register(self, control: str):
        return self.dossier.register_evidence(
            control,
            self._write_evidence(control),
            observed_at=(self.clock[0] - timedelta(hours=1)).isoformat(),
            valid_until=(self.clock[0] + timedelta(days=30)).isoformat(),
            actor={"id": "USR-OPS", "role": "admin"},
        )

    def _complete_control(self, control: str) -> None:
        registered = self._register(control)
        self.dossier.approve_domain(
            control,
            registered["event_id"],
            actor={"id": "USR-DOMAIN", "role": "admin"},
        )
        self.dossier.ratify_release(
            control,
            registered["event_id"],
            actor={"id": "USR-RATIFIER", "role": "qa"},
        )

    def test_policy_matches_exactly_the_ten_canonical_rc1_attestations(self):
        self.assertEqual(set(self.dossier.controls), set(ExternalAttestationRegistry.REQUIRED))
        self.assertEqual(len(self.dossier.controls), 10)

    def test_empty_dossier_is_valid_but_fails_closed_as_missing_evidence(self):
        summary = self.dossier.summary()
        self.assertEqual(summary["integrity"], "valid")
        self.assertFalse(summary["ready"])
        self.assertEqual(summary["passed"], 0)
        self.assertTrue(all(row["status"] == "MISSING_EVIDENCE" for row in summary["checks"]))

    def test_registration_requires_safe_relative_path_existing_file_and_bounded_validity(self):
        with self.assertRaises(ExternalEvidenceError):
            self.dossier.register_evidence(
                "pentest",
                "../escape.txt",
                observed_at=self.clock[0].isoformat(),
                valid_until=(self.clock[0] + timedelta(days=10)).isoformat(),
                actor={"id": "USR-OPS", "role": "admin"},
            )
        with self.assertRaises(ExternalEvidenceError):
            self.dossier.register_evidence(
                "pentest",
                "missing.pdf",
                observed_at=self.clock[0].isoformat(),
                valid_until=(self.clock[0] + timedelta(days=10)).isoformat(),
                actor={"id": "USR-OPS", "role": "admin"},
            )
        path = self._write_evidence("pentest")
        with self.assertRaises(ExternalEvidenceError):
            self.dossier.register_evidence(
                "pentest",
                path,
                observed_at=self.clock[0].isoformat(),
                valid_until=(self.clock[0] + timedelta(days=181)).isoformat(),
                actor={"id": "USR-OPS", "role": "admin"},
            )

    def test_evidence_alone_never_passes_without_domain_approval_and_release_ratification(self):
        registered = self._register("pentest")
        self.assertEqual(self.dossier.summary()["checks"][5]["status"], "DOMAIN_APPROVAL_REQUIRED")
        self.dossier.approve_domain(
            "pentest",
            registered["event_id"],
            actor={"id": "USR-DOMAIN", "role": "admin"},
        )
        pentest = next(row for row in self.dossier.summary()["checks"] if row["key"] == "pentest")
        self.assertEqual(pentest["status"], "RELEASE_RATIFICATION_REQUIRED")

    def test_domain_approval_and_release_ratification_require_distinct_actors(self):
        registered = self._register("privacy_approval")
        self.dossier.approve_domain(
            "privacy_approval",
            registered["event_id"],
            actor={"id": "USR-LEGAL", "role": "specialist"},
        )
        with self.assertRaises(ExternalEvidencePermissionError):
            self.dossier.ratify_release(
                "privacy_approval",
                registered["event_id"],
                actor={"id": "USR-LEGAL", "role": "admin"},
            )
        ratified = self.dossier.ratify_release(
            "privacy_approval",
            registered["event_id"],
            actor={"id": "USR-QA", "role": "qa"},
        )
        self.assertEqual(ratified["event_type"], "RELEASE_RATIFIED")

    def test_role_policy_blocks_specialist_from_security_domain_approval(self):
        registered = self._register("pentest")
        with self.assertRaises(ExternalEvidencePermissionError):
            self.dossier.approve_domain(
                "pentest",
                registered["event_id"],
                actor={"id": "USR-LEGAL", "role": "specialist"},
            )

    def test_evidence_file_mutation_and_expiry_fail_closed(self):
        registered = self._register("load_test")
        self.dossier.approve_domain("load_test", registered["event_id"], actor={"id": "USR-A", "role": "admin"})
        self.dossier.ratify_release("load_test", registered["event_id"], actor={"id": "USR-B", "role": "qa"})
        path = self.evidence_root / "load_test.txt"
        path.write_text("mutated evidence\n", encoding="utf-8")
        check = next(row for row in self.dossier.summary()["checks"] if row["key"] == "load_test")
        self.assertEqual(check["status"], "EVIDENCE_INTEGRITY_MISMATCH")

        second = self._register("monitoring_alerts")
        self.dossier.approve_domain("monitoring_alerts", second["event_id"], actor={"id": "USR-A", "role": "admin"})
        self.dossier.ratify_release("monitoring_alerts", second["event_id"], actor={"id": "USR-B", "role": "qa"})
        self.clock[0] += timedelta(days=31)
        expired = next(row for row in self.dossier.summary()["checks"] if row["key"] == "monitoring_alerts")
        self.assertEqual(expired["status"], "EVIDENCE_EXPIRED")

    def test_dossier_chain_tampering_blocks_readiness_and_new_events(self):
        self._register("tls_certificate")
        row = json.loads(self.dossier_path.read_text(encoding="utf-8").splitlines()[0])
        row["payload"]["evidence_size"] = int(row["payload"]["evidence_size"]) + 1
        self.dossier_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = self.dossier.summary()
        self.assertEqual(summary["integrity"], "invalid")
        self.assertFalse(summary["ready"])
        with self.assertRaises(ExternalEvidenceIntegrityError):
            self.dossier.register_evidence(
                "pentest",
                self._write_evidence("pentest"),
                observed_at=self.clock[0].isoformat(),
                valid_until=(self.clock[0] + timedelta(days=10)).isoformat(),
                actor={"id": "USR-OPS", "role": "admin"},
            )

    def test_revocation_is_append_only_and_requires_replacement_before_control_passes_again(self):
        registered = self._register("rollback_drill")
        self.dossier.approve_domain("rollback_drill", registered["event_id"], actor={"id": "USR-A", "role": "admin"})
        self.dossier.ratify_release("rollback_drill", registered["event_id"], actor={"id": "USR-B", "role": "qa"})
        self.assertTrue(next(row for row in self.dossier.summary()["checks"] if row["key"] == "rollback_drill")["passed"])
        self.dossier.revoke(
            "rollback_drill",
            registered["event_id"],
            reason_code="SUPERSEDED_BY_NEW_DRILL",
            actor={"id": "USR-B", "role": "qa"},
        )
        check = next(row for row in self.dossier.summary()["checks"] if row["key"] == "rollback_drill")
        self.assertFalse(check["passed"])
        self.assertEqual(check["status"], "MISSING_EVIDENCE")
        replacement = self.dossier.register_evidence(
            "rollback_drill",
            self._write_evidence("rollback_drill", "replacement rollback evidence\n"),
            observed_at=self.clock[0].isoformat(),
            valid_until=(self.clock[0] + timedelta(days=30)).isoformat(),
            actor={"id": "USR-OPS", "role": "admin"},
        )
        self.assertNotEqual(replacement["event_id"], registered["event_id"])
        self.assertGreater(self.dossier.verify_chain()["events"], 4)

    def test_public_summary_excludes_paths_hashes_actor_ids_and_event_ids(self):
        self._complete_control("postgres_runtime")
        raw = json.dumps(self.dossier.summary(), ensure_ascii=False)
        for forbidden in ("evidence_path", "evidence_sha256", "actor_id", "domain_actor_id", "event_id"):
            self.assertNotIn(forbidden, raw)

    def test_rc2_gate_rejects_legacy_only_evidence_and_uses_dossier_as_rc1_input(self):
        gate = V1RC2ReleaseAssuranceGate(ROOT, dossier=self.dossier)
        report = gate.evaluate(good_production_env())
        self.assertEqual(report["state"], "BLOCKED_EVIDENCE_DOSSIER")
        self.assertFalse(report["ready_for_controlled_production_validation"])
        self.assertEqual(report["rc1_state"], "BLOCKED_EXTERNAL_EVIDENCE")
        with self.assertRaises(V1RC2ReleaseAssuranceError):
            gate.assert_controlled_validation_ready(good_production_env())

    def test_ten_of_ten_rc2_evidence_enables_controlled_validation_but_not_commercial_launch(self):
        for control in self.dossier.controls:
            self._complete_control(control)
        gate = V1RC2ReleaseAssuranceGate(ROOT, dossier=self.dossier)
        report = gate.evaluate(good_production_env())
        self.assertTrue(report["external_evidence"]["ready"])
        self.assertEqual(report["external_evidence"]["passed"], 10)
        self.assertTrue(report["ready_for_controlled_production_validation"])
        self.assertEqual(report["state"], "READY_FOR_CONTROLLED_PRODUCTION_VALIDATION")
        self.assertFalse(report["commercial"]["commercial_launch_ready"])
        self.assertFalse(release_metadata.REAL_PRODUCTION_AUTHORIZED)
        self.assertFalse(release_metadata.REAL_PAYMENTS_AUTHORIZED)
        self.assertTrue(release_metadata.SYNTHETIC_DATA_ONLY)


if __name__ == "__main__":
    unittest.main()
