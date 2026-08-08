import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class M331PublicDemoTests(unittest.TestCase):
    def test_release_flags_are_demo_only(self):
        with patch.dict(os.environ, {"LEGAL_PUBLIC_DEMO_MODE": "true"}, clear=False):
            import legalai_platform.release_metadata as release
            release = importlib.reload(release)
            self.assertEqual((release.MILESTONE, release.VERSION), ("M33.1", "5.1.2"))
            self.assertTrue(release.PRODUCTION_AUTHORIZED)
            self.assertTrue(release.PUBLIC_PRODUCTION_READY)
            self.assertFalse(release.REAL_PRODUCTION_AUTHORIZED)
            self.assertFalse(release.REAL_PAYMENTS_AUTHORIZED)
        os.environ.pop("LEGAL_PUBLIC_DEMO_MODE", None)
        importlib.reload(release)

    def test_artifacts_are_present(self):
        root = Path(__file__).resolve().parents[1]
        required = [
            "render.yaml", "deploy/docker-compose.public-demo.yml",
            "config/.env.public-demo.example", "config/m33_0_public_demo_policy.json",
            "01_INICIAR_DEMO_PUBLICA_MAC.command", "01_INICIAR_DEMO_PUBLICA_LINUX.sh",
            "01_INICIAR_DEMO_PUBLICA_WINDOWS.bat", "app/modules/public_demo_m33.js",
            "app/modules/public_demo_m33.css", "legalai_platform/http_handler_m33_0.py",
        ]
        self.assertTrue(all((root / item).is_file() for item in required))

    def test_version_file(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "VERSION").read_text(encoding="utf-8").strip(), "M33.1")


if __name__ == "__main__":
    unittest.main()
