from __future__ import annotations

import base64
import os
from hashlib import sha256
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from legalai_platform.deployment_environment import prepare_deployment_environment


ROOT = Path(__file__).resolve().parents[1]


class M331RenderDeploymentTests(TestCase):
    def setUp(self) -> None:
        self.blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    def test_blueprint_has_explicit_free_plan_and_ci_gate(self) -> None:
        self.assertIn("plan: free", self.blueprint)
        self.assertIn("autoDeployTrigger: checksPass", self.blueprint)
        self.assertIn("healthCheckPath: /api/live", self.blueprint)
        self.assertIn("maxShutdownDelaySeconds: 30", self.blueprint)

    def test_demo_password_is_prompted_and_not_committed(self) -> None:
        self.assertRegex(self.blueprint, r"- key: LEGAL_DEMO_PASSWORD\s+sync: false")
        self.assertNotIn("LegalAIZDemo2026!", self.blueprint)

    def test_master_key_seed_is_generated_by_render(self) -> None:
        self.assertRegex(self.blueprint, r"- key: LEGAL_MASTER_KEY_SEED\s+generateValue: true")
        self.assertNotRegex(self.blueprint, r"- key: LEGAL_MASTER_KEY\s+generateValue: true")

    def test_origin_and_secure_cookie_controls_are_enabled(self) -> None:
        self.assertRegex(self.blueprint, r"- key: LEGAL_REQUIRE_ORIGIN_CHECK\s+value: \"true\"")
        self.assertRegex(self.blueprint, r"- key: LEGAL_SECURE_COOKIES\s+value: \"true\"")

    def test_render_external_url_becomes_public_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {"RENDER_EXTERNAL_URL": "https://legalaiz-it-demo.onrender.com"},
            clear=True,
        ):
            prepare_deployment_environment()
            self.assertEqual(
                os.environ.get("LEGAL_PUBLIC_BASE_URL"),
                "https://legalaiz-it-demo.onrender.com",
            )

    def test_explicit_public_base_url_wins_over_render_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RENDER_EXTERNAL_URL": "https://automatico.onrender.com",
                "LEGAL_PUBLIC_BASE_URL": "https://demo.legalaiz.it",
            },
            clear=True,
        ):
            prepare_deployment_environment()
            self.assertEqual(os.environ.get("LEGAL_PUBLIC_BASE_URL"), "https://demo.legalaiz.it")

    def test_render_seed_derives_valid_32_byte_master_key(self) -> None:
        seed = "render-secret-seed-for-test"
        with patch.dict(os.environ, {"LEGAL_MASTER_KEY_SEED": seed}, clear=True):
            prepare_deployment_environment()
            encoded = os.environ.get("LEGAL_MASTER_KEY", "")
            decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            self.assertEqual(len(decoded), 32)
            self.assertEqual(decoded, sha256(seed.encode("utf-8")).digest())

    def test_explicit_master_key_is_not_overwritten(self) -> None:
        explicit = base64.urlsafe_b64encode(b"x" * 32).decode("ascii").rstrip("=")
        with patch.dict(
            os.environ,
            {"LEGAL_MASTER_KEY_SEED": "seed", "LEGAL_MASTER_KEY": explicit},
            clear=True,
        ):
            prepare_deployment_environment()
            self.assertEqual(os.environ.get("LEGAL_MASTER_KEY"), explicit)

    def test_free_demo_is_explicitly_ephemeral(self) -> None:
        self.assertIn("value: /tmp/legalaiz-runtime", self.blueprint)
        self.assertNotRegex(self.blueprint, r"(?m)^\s+disk:")

    def test_runtime_logs_do_not_echo_demo_password(self) -> None:
        run_source = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("clave: {DEMO_PASSWORD}", run_source)
        self.assertNotIn("print(DEMO_PASSWORD", run_source)
        self.assertIn("no se imprime en logs", run_source)


if __name__ == "__main__":
    import unittest

    unittest.main()
