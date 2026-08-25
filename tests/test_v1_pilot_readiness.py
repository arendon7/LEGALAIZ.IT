from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from legalai_platform import release_metadata
from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier
from legalai_platform.pilot_readiness_v1 import (
    PilotAuthorizationDossier,
    PilotReadinessError,
    PilotReadinessIntegrityError,
    PilotReadinessPermissionError,
    V1PilotReadinessGate,
)
from legalai_platform.v1_rc2_release_assurance import V1RC2ReleaseAssuranceGate


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def production_env() -> dict[str, str]:
    return {
        "LEGAL_PROFILE": "production",
        "LEGAL_APP_ENV": "production",
        "LEGAL_PUBLIC_BASE_URL": "https://pilot.legalaiz.test",
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
        "LEGAL_MASTER_KEY_SEED": "managed-pilot-secret-material",
        "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "false",
        "LEGAL_REAL_PAYMENTS_AUTHORIZED": "false",
        "LEGAL_PAYMENT_PROVIDER": "sandbox",
        "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "false",
        "LEGAL_COMMUNICATION_PROVIDER": "disabled",
        "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_PRIVACY_FINAL_APPROVED": "false",
        "LEGAL_PILOT_EXECUTION_REQUESTED": "false",
    }


class V1PilotReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.clock = [datetime(2026, 8, 25, 12, 0, tzinfo=UTC)]
        self.pilot = PilotAuthorizationDossier(
            ROOT,
            dossier_path=base / "pilot.jsonl",
            now_factory=lambda: self.clock[0],
        )
        self.evidence_root = base / "evidence"
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.external = ExternalEvidenceDossier(
            ROOT,
            dossier_path=base / "external.jsonl",
            evidence_root=self.evidence_root,
            now_factory=lambda: self.clock[0],
        )
        self.rc2 = V1RC2ReleaseAssuranceGate(ROOT, dossier=self.external)
        self.gate = V1PilotReadinessGate(ROOT, dossier=self.pilot, rc2_gate=self.rc2)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _plan(self, **overrides):
        payload = {
            "pilot_id": "PILOT-LEGALAI-01",
            "mode": "SYNTHETIC_CONTROLLED",
            "starts_on": "2026-08-26",
            "ends_on": "2026-09-15",
            "max_users": 12,
            "max_tenants": 3,
            "product_codes": ["CO-CD-003", "CO-EM-003", "CO-AR-001"],
            "data_scope": "SYNTHETIC_ONLY",
            "payment_mode": "SANDBOX_ONLY",
            "external_communications": "DISABLED",
            "purpose": "Validar de punta a punta el journey jurídico, documental y operativo con datos sintéticos controlados.",
        }
        payload.update(overrides)
        return payload

    def _register_plan(self, **overrides):
        return self.pilot.register_plan(self._plan(**overrides), actor={"id": "USR-RELEASE", "role": "admin"})

    def _approve_all(self):
        self.pilot.record_approval("legal", actor={"id": "USR-LEGAL", "role": "specialist"})
        self.pilot.record_approval("qa", actor={"id": "USR-QA", "role": "qa"})
        self.pilot.record_approval("privacy", actor={"id": "USR-PRIV", "role": "specialist"})
        self.pilot.record_approval("security_operations", actor={"id": "USR-SEC", "role": "admin"})
        self.pilot.ratify(actor={"id": "USR-RATIFIER", "role": "admin"})

    def _complete_external(self):
        for control in self.external.controls:
            evidence = self.evidence_root / f"{control}.txt"
            evidence.write_text(f"external evidence for {control}\n", encoding="utf-8")
            registered = self.external.register_evidence(
                control,
                evidence.name,
                observed_at=(self.clock[0] - timedelta(hours=1)).isoformat(),
                valid_until=(self.clock[0] + timedelta(days=20)).isoformat(),
                actor={"id": f"USR-OPS-{control}", "role": "admin"},
            )
            domain_role = "specialist" if control == "privacy_approval" else "admin"
            self.external.approve_domain(
                control,
                registered["event_id"],
                actor={"id": f"USR-DOMAIN-{control}", "role": domain_role},
            )
            self.external.ratify_release(
                control,
                registered["event_id"],
                actor={"id": f"USR-RATIFY-{control}", "role": "qa"},
            )

    def test_policy_is_bound_to_exact_current_11_product_contracts(self):
        self.assertEqual(len(self.pilot.product_codes), 11)
        self.assertEqual(len(set(self.pilot.product_codes)), 11)
        self.assertIn("CO-EM-003", self.pilot.product_codes)
        self.assertIn("CO-SA-001", self.pilot.product_codes)

    def test_only_admin_can_register_and_plan_scope_is_bounded(self):
        with self.assertRaises(PilotReadinessPermissionError):
            self.pilot.register_plan(self._plan(), actor={"id": "USR-LEGAL", "role": "specialist"})
        with self.assertRaises(PilotReadinessError):
            self._register_plan(max_users=26)
        with self.assertRaises(PilotReadinessError):
            self._register_plan(max_tenants=6)
        with self.assertRaises(PilotReadinessError):
            self._register_plan(product_codes=["CO-NOT-REAL"])
        with self.assertRaises(PilotReadinessError):
            self._register_plan(ends_on="2026-12-31")

    def test_synthetic_mode_cannot_request_real_payment_or_external_communications(self):
        with self.assertRaises(PilotReadinessError):
            self._register_plan(payment_mode="REAL_PROVIDER")
        with self.assertRaises(PilotReadinessError):
            self._register_plan(external_communications="REAL_PROVIDER")
        with self.assertRaises(PilotReadinessError):
            self._register_plan(data_scope="REAL_CLIENT_DATA")

    def test_active_plan_cannot_be_overwritten_and_revocation_allows_replacement(self):
        first = self._register_plan()
        with self.assertRaises(PilotReadinessError):
            self.pilot.register_plan(self._plan(pilot_id="PILOT-LEGALAI-02"), actor={"id": "USR-RELEASE", "role": "admin"})
        revoked = self.pilot.revoke(reason_code="SCOPE_CHANGED", actor={"id": "USR-RATIFIER", "role": "qa"})
        self.assertEqual(revoked["pilot_id"], first["pilot_id"])
        second = self.pilot.register_plan(self._plan(pilot_id="PILOT-LEGALAI-02"), actor={"id": "USR-RELEASE", "role": "admin"})
        self.assertEqual(second["pilot_id"], "PILOT-LEGALAI-02")
        self.assertGreater(self.pilot.verify_chain()["events"], 2)

    def test_legal_and_qa_approvals_enforce_roles_and_distinct_actors(self):
        self._register_plan()
        with self.assertRaises(PilotReadinessPermissionError):
            self.pilot.record_approval("legal", actor={"id": "USR-ADMIN", "role": "admin"})
        self.pilot.record_approval("legal", actor={"id": "USR-HUMAN", "role": "specialist"})
        with self.assertRaises(PilotReadinessPermissionError):
            self.pilot.record_approval("qa", actor={"id": "USR-HUMAN", "role": "qa"})
        qa = self.pilot.record_approval("qa", actor={"id": "USR-QA", "role": "qa"})
        self.assertFalse(qa["idempotent"])

    def test_domain_approval_is_idempotent_only_for_exact_same_actor(self):
        self._register_plan()
        first = self.pilot.record_approval("privacy", actor={"id": "USR-PRIV", "role": "specialist"})
        self.assertFalse(first["idempotent"])
        retry = self.pilot.record_approval("privacy", actor={"id": "USR-PRIV", "role": "specialist"})
        self.assertTrue(retry["idempotent"])
        with self.assertRaises(PilotReadinessError):
            self.pilot.record_approval("privacy", actor={"id": "USR-OTHER", "role": "admin"})

    def test_ratification_requires_all_domains_and_distinct_release_actor(self):
        self._register_plan()
        self.pilot.record_approval("legal", actor={"id": "USR-LEGAL", "role": "specialist"})
        self.pilot.record_approval("qa", actor={"id": "USR-QA", "role": "qa"})
        with self.assertRaises(PilotReadinessError):
            self.pilot.ratify(actor={"id": "USR-RATIFIER", "role": "admin"})
        self.pilot.record_approval("privacy", actor={"id": "USR-PRIV", "role": "specialist"})
        self.pilot.record_approval("security_operations", actor={"id": "USR-SEC", "role": "admin"})
        with self.assertRaises(PilotReadinessPermissionError):
            self.pilot.ratify(actor={"id": "USR-LEGAL", "role": "admin"})
        result = self.pilot.ratify(actor={"id": "USR-RATIFIER", "role": "admin"})
        self.assertTrue(result["ratified"])
        retry = self.pilot.ratify(actor={"id": "USR-RATIFIER", "role": "admin"})
        self.assertTrue(retry["idempotent"])

    def test_ledger_tampering_fails_closed(self):
        self._register_plan()
        rows = self.pilot.dossier_path.read_text(encoding="utf-8").splitlines()
        row = json.loads(rows[0])
        row["payload"]["plan"]["max_users"] = 25
        self.pilot.dossier_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = self.pilot.summary()
        self.assertEqual(summary["integrity"], "invalid")
        self.assertFalse(summary["ready"])
        with self.assertRaises(PilotReadinessIntegrityError):
            self.pilot.record_approval("legal", actor={"id": "USR-LEGAL", "role": "specialist"})

    def test_public_summary_minimizes_internal_actors_hashes_events_and_purpose(self):
        self._register_plan()
        self._approve_all()
        raw = json.dumps(self.pilot.summary(), ensure_ascii=False).lower()
        for forbidden in ("actor_id", "plan_hash", "event_id", "previous_hash", "event_hash", "validar de punta"):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(self.pilot.summary()["active_plan"]["product_count"], 3)

    def test_gate_blocks_before_rc2_even_when_pilot_governance_is_complete(self):
        self._register_plan()
        self._approve_all()
        report = self.gate.evaluate(production_env())
        self.assertEqual(report["state"], "BLOCKED_RC2_ASSURANCE")
        self.assertFalse(report["readiness"]["technical_preparation_ready"])

    def test_full_rc2_and_approved_synthetic_plan_is_ready_without_real_launch_claim(self):
        self._complete_external()
        self._register_plan()
        self._approve_all()
        report = self.gate.evaluate(production_env())
        self.assertEqual(report["state"], "READY_FOR_SYNTHETIC_CONTROLLED_PILOT")
        self.assertTrue(report["readiness"]["technical_preparation_ready"])
        self.assertTrue(report["readiness"]["pilot_mode_ready"])
        self.assertFalse(report["readiness"]["execution_requested"])
        self.assertTrue(report["readiness"]["safe_execution_claim"])
        self.assertTrue(report["release_metadata"]["SYNTHETIC_DATA_ONLY"])
        self.assertFalse(report["release_metadata"]["REAL_PRODUCTION_AUTHORIZED"])

    def test_execution_request_before_readiness_is_explicitly_blocked(self):
        env = production_env()
        env["LEGAL_PILOT_EXECUTION_REQUESTED"] = "true"
        report = self.gate.evaluate(env)
        self.assertEqual(report["state"], "BLOCKED_UNSAFE_PILOT_EXECUTION_CLAIM")
        self.assertFalse(report["readiness"]["safe_execution_claim"])
        with self.assertRaises(PilotReadinessError):
            self.gate.assert_safe_execution_claim(env)

    def test_real_client_pilot_cannot_be_unlocked_by_environment_while_release_metadata_blocks_it(self):
        self._complete_external()
        self._register_plan(
            mode="REAL_CLIENT_CONTROLLED",
            data_scope="REAL_CLIENT_DATA",
            payment_mode="REAL_PROVIDER",
            external_communications="REAL_PROVIDER",
        )
        self._approve_all()
        env = production_env()
        env.update({
            "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "true",
            "LEGAL_REAL_PAYMENTS_AUTHORIZED": "true",
            "LEGAL_PAYMENT_PROVIDER": "stripe",
            "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "true",
            "LEGAL_COMMUNICATION_PROVIDER": "postmark",
        })
        report = self.gate.evaluate(env)
        self.assertEqual(report["state"], "BLOCKED_REAL_CLIENT_AUTHORIZATION")
        self.assertIn("REAL_PRODUCTION_AUTHORIZED", report["readiness"]["real_client_blockers"])
        self.assertIn("SYNTHETIC_DATA_ONLY", report["readiness"]["real_client_blockers"])
        self.assertIn("REAL_PAYMENTS_AUTHORIZED", report["readiness"]["real_client_blockers"])
        self.assertFalse(report["readiness"]["pilot_mode_ready"])
        self.assertFalse(release_metadata.REAL_PRODUCTION_AUTHORIZED)
        self.assertFalse(release_metadata.REAL_PAYMENTS_AUTHORIZED)
        self.assertTrue(release_metadata.SYNTHETIC_DATA_ONLY)

    def test_hypothetical_real_client_path_still_requires_real_payment_and_communications_providers(self):
        self._complete_external()
        self._register_plan(
            mode="REAL_CLIENT_CONTROLLED",
            data_scope="REAL_CLIENT_DATA",
            payment_mode="REAL_PROVIDER",
            external_communications="REAL_PROVIDER",
        )
        self._approve_all()
        original = (
            release_metadata.REAL_PRODUCTION_AUTHORIZED,
            release_metadata.REAL_PAYMENTS_AUTHORIZED,
            release_metadata.SYNTHETIC_DATA_ONLY,
        )
        try:
            release_metadata.REAL_PRODUCTION_AUTHORIZED = True
            release_metadata.REAL_PAYMENTS_AUTHORIZED = True
            release_metadata.SYNTHETIC_DATA_ONLY = False
            env = production_env()
            env["LEGAL_REAL_PAYMENTS_AUTHORIZED"] = "true"
            env["LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED"] = "true"
            blocked = self.gate.evaluate(env)
            self.assertIn("payment_provider_real", blocked["readiness"]["real_client_blockers"])
            self.assertIn("communications_provider_real", blocked["readiness"]["real_client_blockers"])
            env["LEGAL_PAYMENT_PROVIDER"] = "stripe"
            env["LEGAL_COMMUNICATION_PROVIDER"] = "postmark"
            ready = self.gate.evaluate(env)
            self.assertEqual(ready["state"], "REAL_CLIENT_PILOT_READY")
            self.assertTrue(ready["readiness"]["pilot_mode_ready"])
        finally:
            (
                release_metadata.REAL_PRODUCTION_AUTHORIZED,
                release_metadata.REAL_PAYMENTS_AUTHORIZED,
                release_metadata.SYNTHETIC_DATA_ONLY,
            ) = original


if __name__ == "__main__":
    unittest.main()
