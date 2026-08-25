from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M362CIAuthIsolationTests(unittest.TestCase):
    def test_m362_gets_fresh_process_without_weakening_login_policy(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        auth = (ROOT / "legalai_platform/application_services.py").read_text(encoding="utf-8")
        self.assertIn('RATE_LIMITER.allow(f"login-ip:{ip}", 12, 300)', auth)
        self.assertNotIn("LEGAL_DISABLE_RATE_LIMIT", ci)
        self.assertNotIn("LEGAL_LOGIN_RATE_LIMIT", ci)
        self.assertIn("stop_server", ci)
        self.assertIn("start_server /tmp/legalaiz-m36-2.log", ci)
        self.assertIn("python tools/m36_1_http_smoke.py", ci)
        self.assertIn("python tools/m36_2_http_smoke.py", ci)
        first = ci.index("python tools/m36_1_http_smoke.py")
        restart = ci.index("start_server /tmp/legalaiz-m36-2.log")
        second = ci.index("python tools/m36_2_http_smoke.py")
        self.assertLess(first, restart)
        self.assertLess(restart, second)
        self.assertIn("LEGAL_RUNTIME_DIR: ${{ runner.temp }}/legalaiz-runtime", ci)


if __name__ == "__main__":
    unittest.main()
