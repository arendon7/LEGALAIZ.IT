from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from unittest import TestCase
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
LIVE_URL = "http://127.0.0.1:8765/api/live"


class V1R0HttpRuntimeTests(TestCase):
    def test_real_http_readiness_smoke_runs_against_isolated_server(self):
        with tempfile.TemporaryDirectory(prefix="legalaiz-v1-r0-http-") as temp_dir:
            env = os.environ.copy()
            env.update(
                {
                    "LEGAL_PROFILE": "local",
                    "LEGAL_APP_ENV": "demo",
                    "LEGAL_RUNTIME_DIR": temp_dir,
                    "LEGAL_ALLOW_DEMO_ACCOUNTS": "true",
                    "LEGAL_REQUIRE_MFA_ROLES": "",
                    "LEGAL_GITHUB_LITE_ASSETS": "true",
                    "LEGAL_DEMO_PASSWORD": secrets.token_urlsafe(32),
                    "LEGAL_HOST": "127.0.0.1",
                    "LEGAL_PORT": "8765",
                }
            )
            log_path = Path(temp_dir) / "server.log"
            with log_path.open("w+", encoding="utf-8") as server_log:
                process = subprocess.Popen(
                    [sys.executable, "run.py", "--no-browser"],
                    cwd=ROOT,
                    env=env,
                    stdout=server_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                try:
                    self._wait_until_live(process, server_log)
                    smoke = subprocess.run(
                        [sys.executable, "tools/v1_r0_http_smoke.py"],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                    )
                    output = (smoke.stdout or "") + (smoke.stderr or "")
                    self.assertEqual(
                        smoke.returncode,
                        0,
                        "V1-R0 HTTP smoke falló:\n" + output[-6000:] + "\nServidor:\n" + self._tail(server_log),
                    )
                    self.assertIn("V1-R0 HTTP smoke PASS", output)
                    self.assertIn("activation=BLOCKED", output)
                    self.assertIn("admin_only=true", output)
                    self.assertIn("read_only=true", output)
                    self.assertIn("self_authorization=false", output)
                finally:
                    self._stop(process)

    def _wait_until_live(self, process: subprocess.Popen, server_log) -> None:
        deadline = time.monotonic() + 30
        last_error = ""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(
                    f"Servidor V1-R0 terminó antes de quedar live (rc={process.returncode}).\n"
                    + self._tail(server_log)
                )
            try:
                with urlopen(LIVE_URL, timeout=2) as response:
                    if response.status == 200:
                        return
            except (URLError, OSError) as exc:
                last_error = type(exc).__name__
            time.sleep(0.25)
        self.fail(f"Servidor V1-R0 no quedó live ({last_error}).\n" + self._tail(server_log))

    @staticmethod
    def _tail(server_log) -> str:
        try:
            server_log.flush()
            server_log.seek(0)
            return server_log.read()[-6000:]
        except Exception:
            return "<server log unavailable>"

    @staticmethod
    def _stop(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
