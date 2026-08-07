#!/usr/bin/env python3
from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def req(opener, url, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with opener.open(request, timeout=180) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode())
        except Exception:
            payload = {}
        return exc.code, payload


def main():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    password = "LegalAIZDemo2026!"
    checks = []
    with tempfile.TemporaryDirectory(prefix="legalaiz-m330-") as runtime:
        env = {**os.environ,
            "LEGAL_RUNTIME_DIR": runtime, "LEGAL_PORT": str(port), "LEGAL_HOST": "127.0.0.1",
            "LEGAL_PROFILE": "local", "LEGAL_APP_ENV": "demo_public", "LEGAL_PUBLIC_DEMO_MODE": "true",
            "LEGAL_ALLOW_DEMO_ACCOUNTS": "true", "LEGAL_DEMO_PASSWORD": password,
            "LEGAL_REQUIRE_MFA_ROLES": "", "LEGAL_REQUIRE_ORIGIN_CHECK": "false",
            "LEGAL_SECURE_COOKIES": "false", "LEGAL_DATABASE_BACKEND": "sqlite",
            "PYTHONDONTWRITEBYTECODE": "1"}
        process = subprocess.Popen([sys.executable, "run.py", "--no-browser"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            live = None
            for _ in range(240):
                if process.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(f"{base}/api/live", timeout=1) as response:
                        live = json.loads(response.read().decode())
                    break
                except Exception:
                    time.sleep(.25)
            checks.append(("startup", bool(live and live.get("version") == "5.1.1")))
            plain = urllib.request.build_opener()
            status, demo = req(plain, f"{base}/api/m33/public-demo")
            checks.append(("public_demo_status", status == 200 and demo.get("public_demo_mode") is True and demo.get("production_authorized") is True and demo.get("real_production_authorized") is False))
            jar = http.cookiejar.CookieJar(); admin = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            status, auth = req(admin, f"{base}/api/auth/login", "POST", {"email":"ana@demo.legalaiz.it","password":password}, {"Origin":base})
            checks.append(("admin_login", status == 200 and auth.get("user",{}).get("role") == "admin"))
            status, cohort = req(admin, f"{base}/api/m31/case-demo")
            metrics = cohort.get("metrics", {}) if isinstance(cohort, dict) else {}
            checks.append(("cohort", status == 200 and metrics.get("cases") == 11 and metrics.get("documents") == 76 and metrics.get("released_cases") == 11))
            status, verified = req(admin, f"{base}/api/m31/case-demo/verify")
            checks.append(("integrity", status == 200 and verified.get("ok") is True and verified.get("checked") == 88))
            status, pre = req(admin, f"{base}/api/m31/preproduction")
            current = pre.get("current", {}) if isinstance(pre, dict) else {}
            checks.append(("demo_gate", status == 200 and pre.get("production_authorized") is True and current.get("production_ready") is True and current.get("passed") == current.get("total")))
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill()
            output = process.stdout.read() if process.stdout else ""
    report = {"schema":"legalaizit-m33-public-demo-smoke-v1","checks":[{"key":k,"passed":v} for k,v in checks],"passed":sum(v for _,v in checks),"total":len(checks),"ok":all(v for _,v in checks),"server_output_tail":output[-3000:]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
