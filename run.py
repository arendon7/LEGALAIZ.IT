#!/usr/bin/env python3
from __future__ import annotations

import os

from legalai_platform.deployment_environment import prepare_deployment_environment

prepare_deployment_environment()

from legalai_platform.document_release_gate import install_docx_release_gate

install_docx_release_gate()

from core_v11 import *  # noqa: F401,F403,E402
import core_v11 as core  # noqa: E402
from http.server import ThreadingHTTPServer
import sys
import threading
import webbrowser
import signal
from legalai_platform.runtime_registry import *  # noqa: F401,F403,E402
from legalai_platform.release_metadata import RELEASE_NAME, PUBLIC_DEMO_MODE, MILESTONE  # noqa: E402
from legalai_platform.application_services import *  # noqa: F401,F403,E402
import legalai_platform.application_services as _application_services  # noqa: E402
from legalai_platform.http_handler_m34_3 import Handler  # noqa: E402
# from legalai_platform.http_handler_m34_2 import Handler  # compatibility marker
# from legalai_platform.http_handler_m34_1 import Handler  # compatibility marker
# from legalai_platform.http_handler_m33_0 import Handler  # compatibility marker
# from legalai_platform.http_handler_m32_9 import Handler  # compatibility marker
# from legalai_platform.http_handler_m32_8 import Handler  # compatibility marker
# from legalai_platform.http_handler_m32_7 import Handler  # compatibility marker
# from legalai_platform.http_handler_m32_6 import Handler  # compatibility marker
# from legalai_platform.http_handler_m32_5 import Handler  # compatibility marker
# VERSION = "3.8.0"
# co-ar-001-closed-v250
# co-la-001-closed-v253
# m32-2-document-release-gate
# m32-6-portfolio-operations
# m32-7-notification-center
# m32-8-transactional-communications
# m32-9-contact-governance
# m33-0-public-demo-integration
# m33-1-render-deployment-hardening
# m34-1-intelligent-intake-ux
# m34-2-structured-fact-extraction-confirmation
# m34-3-adaptive-question-sufficiency
# LEGAL_ALLOW_DEMO_ACCOUNTS
# LEGAL_BOOTSTRAP_ADMIN_EMAIL
# UPDATE users SET active=0 WHERE lower(email) LIKE '%@demo.legalaiz.it'
# "code": "internal_error"


_original_m31_case_demo_summary = M31_CASE_DEMO.summary


def _safe_m31_case_demo_summary(con):
    """Neutraliza credenciales heredadas del snapshot M31.8 antes de cualquier salida M33."""
    payload = _original_m31_case_demo_summary(con)
    credentials = payload.get("credentials") if isinstance(payload, dict) else None
    if isinstance(credentials, dict):
        credentials.pop("password", None)
        credentials["password_source"] = "LEGAL_DEMO_PASSWORD"
    return payload


M31_CASE_DEMO.summary = _safe_m31_case_demo_summary


def authenticate(*args, **kwargs):
    """Compatibility wrapper for callers that temporarily replace run.SETTINGS."""
    previous = _application_services.SETTINGS
    _application_services.SETTINGS = SETTINGS
    try:
        return _application_services.authenticate(*args, **kwargs)
    finally:
        _application_services.SETTINGS = previous


def _bootstrap_public_demo() -> None:
    if not PUBLIC_DEMO_MODE:
        return
    con = core.db()
    try:
        M31_CASE_DEMO.bootstrap(con, "USR-ADMIN", reset=False, auto_release=True)
    finally:
        con.close()


def main():
    init_db()
    _bootstrap_public_demo()
    port = int(os.environ.get("LEGAL_PORT") or os.environ.get("PORT") or PORT)
    host = os.environ.get("LEGAL_HOST", HOST).strip() or HOST
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
        if arg == "--lan":
            host = "0.0.0.0"
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), Handler)
    browser_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{browser_host}:{port}"
    print(f"LegalAIZ.it v{VERSION} · {RELEASE_NAME} · {BUILD_ID} disponible en {url}")
    print("Expedientes · documentos · revisión controlada · trazabilidad · seguridad por rol")
    allow_demo = str(os.environ.get("LEGAL_ALLOW_DEMO_ACCOUNTS", "")).strip().lower() in {"1", "true", "yes", "si", "sí"}
    if SETTINGS.profile == "local" and allow_demo:
        print("Acceso demo habilitado para cuentas @demo.legalaiz.it.")
        print("La contraseña se obtiene de LEGAL_DEMO_PASSWORD y no se imprime en logs.")
    if PUBLIC_DEMO_MODE:
        print(f"MODO {MILESTONE}: producción demostrativa pública activa; datos sintéticos y pagos sandbox.")
    if host == "0.0.0.0":
        print("ADVERTENCIA: servicio expuesto en red. Use un proxy TLS administrado para acceso público.")
    if "--no-browser" not in sys.argv and SETTINGS.profile == "local":
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()

    def stop_server(signum, frame):
        OBSERVABILITY.write("server_shutdown_requested", signal=signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stop_server)
    try:
        OBSERVABILITY.write("server_started", host=host, port=port, profile=SETTINGS.profile, version=VERSION)
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        OBSERVABILITY.write("server_stopped", host=host, port=port, profile=SETTINGS.profile, version=VERSION)
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
