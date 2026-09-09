from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from legalai_platform.deployment_environment import (
    ProductionConfigurationError,
    prepare_deployment_environment,
)


ROOT = Path(__file__).resolve().parents[1]


class V1RC1StartupEnforcementTests(unittest.TestCase):
    def test_prepare_deployment_environment_blocks_unsafe_production_before_runtime(self):
        with patch.dict(
            os.environ,
            {
                "LEGAL_PROFILE": "production",
                "LEGAL_APP_ENV": "production",
                "LEGAL_PUBLIC_BASE_URL": "http://unsafe.example.test",
                "LEGAL_ALLOW_DEMO_ACCOUNTS": "true",
            },
            clear=True,
        ):
            with self.assertRaises(ProductionConfigurationError) as ctx:
                prepare_deployment_environment()
        self.assertIn("public_https", str(ctx.exception))
        self.assertIn("demo_accounts_disabled", str(ctx.exception))

    def test_prepare_deployment_environment_keeps_public_demo_local_profile_compatible(self):
        with patch.dict(
            os.environ,
            {
                "LEGAL_PROFILE": "local",
                "LEGAL_APP_ENV": "demo_public",
                "LEGAL_PUBLIC_DEMO_MODE": "true",
                "LEGAL_ALLOW_DEMO_ACCOUNTS": "true",
                "RENDER_EXTERNAL_URL": "https://legalaiz-it-demo.onrender.com",
                "LEGAL_MASTER_KEY_SEED": "synthetic-render-seed",
            },
            clear=True,
        ):
            prepare_deployment_environment()
            self.assertEqual(os.environ["LEGAL_PUBLIC_BASE_URL"], "https://legalaiz-it-demo.onrender.com")
            self.assertTrue(os.environ.get("LEGAL_MASTER_KEY"))

    def test_cli_readiness_gate_is_part_of_the_unittest_certification_surface(self):
        result = subprocess.run(
            [sys.executable, "tools/v1_rc1_readiness_gate.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        self.assertIn("V1-RC1 readiness gate PASS", result.stdout)
        self.assertIn("commercial_launch=blocked_by_release_metadata", result.stdout)


if __name__ == "__main__":
    unittest.main()
