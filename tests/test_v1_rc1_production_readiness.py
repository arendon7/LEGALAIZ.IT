from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from legalai_platform import release_metadata
from legalai_platform.deployment_environment import (
    ProductionConfigurationError,
    assert_production_startup_environment,
    production_startup_report,
)
from legalai_platform.operational_security import ExternalAttestationRegistry
from legalai_platform.v1_rc1_production_readiness import (
    V1RC1ProductionReadinessGate,
    V1RC1ReadinessError,
)


ROOT = Path(__file__).resolve().parents[1]


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
        "LEGAL_MASTER_KEY_SEED": "managed-ci-secret-material",
        "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "false",
        "LEGAL_REAL_PAYMENTS_AUTHORIZED": "false",
        "LEGAL_PAYMENT_PROVIDER": "sandbox",
        "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "false",
        "LEGAL_COMMUNICATION_PROVIDER": "disabled",
        "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "false",
        "LEGAL_PRIVACY_FINAL_APPROVED": "false",
    }


def external_ready() -> dict:
    total = len(ExternalAttestationRegistry.REQUIRED)
    return {"ready": True, "passed": total, "total": total, "missing": []}


class V1RC1ProductionStartupTests(unittest.TestCase):
    def test_non_production_profiles_are_not_changed_by_rc1_startup_gate(self):
        report = production_startup_report({"LEGAL_PROFILE": "local"})
        self.assertFalse(report["applies"])
        self.assertTrue(report["safe"])
        self.assertEqual(report["blockers"], [])

    def test_complete_production_shape_passes_startup_configuration_gate(self):
        report = production_startup_report(good_production_env())
        self.assertTrue(report["applies"])
        self.assertTrue(report["safe"])
        self.assertEqual(report["blockers"], [])
        self.assertGreaterEqual(len(report["checks"]), 17)

    def test_each_critical_production_boundary_fails_closed(self):
        mutations = {
            "public_https": ("LEGAL_PUBLIC_BASE_URL", "http://app.legalaiz.test"),
            "secure_cookies": ("LEGAL_SECURE_COOKIES", "false"),
            "origin_check": ("LEGAL_REQUIRE_ORIGIN_CHECK", "false"),
            "trust_proxy": ("LEGAL_TRUST_PROXY", "false"),
            "trusted_proxy_ips": ("LEGAL_TRUSTED_PROXY_IPS", "0.0.0.0/0"),
            "demo_accounts_disabled": ("LEGAL_ALLOW_DEMO_ACCOUNTS", "true"),
            "public_demo_disabled": ("LEGAL_PUBLIC_DEMO_MODE", "true"),
            "database_postgresql": ("LEGAL_DATABASE_BACKEND", "sqlite"),
            "database_url_managed": ("DATABASE_URL", "SET_IN_SECRET_MANAGER"),
            "postgres_external_certified": ("LEGAL_POSTGRES_EXTERNAL_CERTIFIED", "false"),
            "volume_encryption_confirmed": ("LEGAL_VOLUME_ENCRYPTION_CONFIRMED", "false"),
            "malware_scanner_clamav": ("LEGAL_MALWARE_SCANNER", "none"),
            "mfa_admin_specialist": ("LEGAL_REQUIRE_MFA_ROLES", "admin"),
            "managed_master_key": ("LEGAL_MASTER_KEY_SEED", ""),
        }
        for expected_blocker, (key, value) in mutations.items():
            with self.subTest(expected_blocker=expected_blocker):
                env = good_production_env()
                env[key] = value
                report = production_startup_report(env)
                self.assertFalse(report["safe"])
                self.assertIn(expected_blocker, report["blockers"])

    def test_bootstrap_admin_is_optional_but_if_present_must_be_non_demo_and_non_placeholder(self):
        env = good_production_env()
        self.assertTrue(production_startup_report(env)["safe"])
        env["LEGAL_BOOTSTRAP_ADMIN_EMAIL"] = "admin@demo.legalaiz.it"
        env["LEGAL_BOOTSTRAP_ADMIN_PASSWORD"] = "CHANGE_ME"
        report = production_startup_report(env)
        self.assertFalse(report["safe"])
        self.assertIn("bootstrap_admin_safe", report["blockers"])

    def test_startup_exception_lists_only_control_keys_never_secret_values(self):
        env = good_production_env()
        secret = "SUPER-PRIVATE-RC1-SEED"
        env["LEGAL_MASTER_KEY_SEED"] = secret
        env["DATABASE_URL"] = "SET_IN_SECRET_MANAGER"
        with self.assertRaises(ProductionConfigurationError) as ctx:
            assert_production_startup_environment(env)
        self.assertIn("database_url_managed", str(ctx.exception))
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn("SET_IN_SECRET_MANAGER", str(ctx.exception))


class V1RC1ProductionReadinessGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = V1RC1ProductionReadinessGate(ROOT)

    def test_policy_uses_the_exact_canonical_external_attestation_set(self):
        self.assertEqual(
            set(self.gate.policy["external_attestations"]),
            set(ExternalAttestationRegistry.REQUIRED),
        )

    def test_current_release_metadata_keeps_real_launch_and_payments_blocked(self):
        self.assertFalse(release_metadata.REAL_PRODUCTION_AUTHORIZED)
        self.assertFalse(release_metadata.REAL_PAYMENTS_AUTHORIZED)
        self.assertTrue(release_metadata.SYNTHETIC_DATA_ONLY)
        report = self.gate.evaluate(good_production_env(), external_summary=external_ready())
        self.assertTrue(report["commercial"]["controlled_validation_ready"])
        self.assertFalse(report["commercial"]["commercial_launch_ready"])
        self.assertEqual(report["state"], "READY_FOR_CONTROLLED_PRODUCTION_VALIDATION")

    def test_environment_flags_cannot_override_release_metadata_prohibition(self):
        env = good_production_env()
        env.update({
            "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "true",
            "LEGAL_REAL_PAYMENTS_AUTHORIZED": "true",
            "LEGAL_PAYMENT_PROVIDER": "real-provider",
            "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "true",
            "LEGAL_COMMUNICATION_PROVIDER": "real-provider",
            "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_PRIVACY_FINAL_APPROVED": "true",
        })
        report = self.gate.evaluate(env, external_summary=external_ready())
        self.assertFalse(report["commercial"]["commercial_launch_ready"])
        self.assertFalse(report["commercial"]["safe_launch_claim"])
        self.assertEqual(report["state"], "BLOCKED_UNSAFE_LAUNCH_CLAIM")
        with self.assertRaises(V1RC1ReadinessError):
            self.gate.assert_safe_launch_claim(env, external_summary=external_ready())

    def test_sandbox_or_disabled_providers_never_satisfy_commercial_gate(self):
        env = good_production_env()
        env.update({
            "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "true",
            "LEGAL_REAL_PAYMENTS_AUTHORIZED": "true",
            "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "true",
            "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_PRIVACY_FINAL_APPROVED": "true",
        })
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", True), \
             patch.object(release_metadata, "REAL_PAYMENTS_AUTHORIZED", True), \
             patch.object(release_metadata, "SYNTHETIC_DATA_ONLY", False):
            report = self.gate.evaluate(env, external_summary=external_ready())
        self.assertIn("payment_provider_real", report["commercial"]["blockers"])
        self.assertIn("communications_provider_real", report["commercial"]["blockers"])

    def test_all_layers_must_be_green_before_hypothetical_commercial_ready_state(self):
        env = good_production_env()
        env.update({
            "LEGAL_PRODUCTION_LAUNCH_AUTHORIZED": "true",
            "LEGAL_REAL_PAYMENTS_AUTHORIZED": "true",
            "LEGAL_PAYMENT_PROVIDER": "verified-payment-adapter",
            "LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED": "true",
            "LEGAL_COMMUNICATION_PROVIDER": "verified-transactional-adapter",
            "LEGAL_LEGAL_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_QA_PORTFOLIO_FINAL_APPROVED": "true",
            "LEGAL_PRIVACY_FINAL_APPROVED": "true",
        })
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", True), \
             patch.object(release_metadata, "REAL_PAYMENTS_AUTHORIZED", True), \
             patch.object(release_metadata, "SYNTHETIC_DATA_ONLY", False):
            report = self.gate.evaluate(env, external_summary=external_ready())
        self.assertTrue(report["commercial"]["commercial_launch_ready"])
        self.assertTrue(report["commercial"]["safe_launch_claim"])
        self.assertEqual(report["state"], "COMMERCIAL_LAUNCH_READY")

    def test_missing_external_evidence_blocks_even_with_safe_startup_shape(self):
        report = self.gate.evaluate(
            good_production_env(),
            external_summary={"ready": False, "passed": 7, "total": 10, "missing": ["pentest", "load_test", "rollback_drill"]},
        )
        self.assertEqual(report["state"], "BLOCKED_EXTERNAL_EVIDENCE")
        self.assertFalse(report["commercial"]["controlled_validation_ready"])

    def test_public_report_contains_no_database_url_master_key_or_bootstrap_password(self):
        env = good_production_env()
        env["LEGAL_BOOTSTRAP_ADMIN_EMAIL"] = "admin@legalaiz.test"
        env["LEGAL_BOOTSTRAP_ADMIN_PASSWORD"] = "PRIVATE-BOOTSTRAP-RC1"
        report = self.gate.evaluate(env, external_summary=external_ready())
        raw = json.dumps(report, ensure_ascii=False)
        for secret in (
            env["DATABASE_URL"],
            env["LEGAL_MASTER_KEY_SEED"],
            env["LEGAL_BOOTSTRAP_ADMIN_PASSWORD"],
        ):
            self.assertNotIn(secret, raw)

    def test_production_template_is_fail_closed_and_commercially_disabled_by_default(self):
        path = ROOT / ".env.production.example"
        self.assertTrue(path.is_file())
        values = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        self.assertEqual(values["LEGAL_PROFILE"], "production")
        self.assertEqual(values["LEGAL_PRODUCTION_LAUNCH_AUTHORIZED"], "false")
        self.assertEqual(values["LEGAL_REAL_PAYMENTS_AUTHORIZED"], "false")
        self.assertEqual(values["LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED"], "false")
        self.assertEqual(values["LEGAL_PAYMENT_PROVIDER"], "sandbox")
        self.assertEqual(values["LEGAL_COMMUNICATION_PROVIDER"], "disabled")
        self.assertFalse(production_startup_report(values)["safe"], "La plantilla no debe ser desplegable sin sustituir placeholders/evidencia")


if __name__ == "__main__":
    unittest.main()
