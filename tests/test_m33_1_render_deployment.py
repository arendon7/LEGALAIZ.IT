from __future__ import annotations

from pathlib import Path
from unittest import TestCase
import re


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
        self.assertRegex(
            self.blueprint,
            r"- key: LEGAL_DEMO_PASSWORD\s+sync: false",
        )
        self.assertNotIn("LegalAIZDemo2026!", self.blueprint)

    def test_master_key_is_generated_by_render(self) -> None:
        self.assertRegex(
            self.blueprint,
            r"- key: LEGAL_MASTER_KEY\s+generateValue: true",
        )

    def test_origin_check_uses_render_external_url(self) -> None:
        self.assertRegex(
            self.blueprint,
            r"- key: LEGAL_PUBLIC_BASE_URL\s+fromService:\s+type: web\s+name: legalaiz-it-demo\s+envVarKey: RENDER_EXTERNAL_URL",
        )
        self.assertRegex(
            self.blueprint,
            r"- key: LEGAL_REQUIRE_ORIGIN_CHECK\s+value: \"true\"",
        )
        self.assertRegex(
            self.blueprint,
            r"- key: LEGAL_SECURE_COOKIES\s+value: \"true\"",
        )

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
