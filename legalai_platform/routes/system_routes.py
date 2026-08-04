from __future__ import annotations

import core_v11 as core
from legalai_platform.application_services import security_overview
from legalai_platform.runtime_registry import BUILD_ID, EXTERNAL_ATTESTATIONS, INFRA, OBSERVABILITY, PRIVACY, SETTINGS


def handle_admin_system_get(handler, path, user):
    if path == "/api/observability":
        if user["role"] != "admin": handler.send_json({"error": "Sin permisos."}, 403); return True
        handler.send_json({"events": OBSERVABILITY.tail(100), "request_id": handler.request_id}); return True
    if path == "/api/privacy":
        if user["role"] != "admin": handler.send_json({"error": "Sin permisos."}, 403); return True
        con = core.db(); obj = {"policy": PRIVACY.policy(), "inventory": PRIVACY.inventory(con), "dry_run": PRIVACY.dry_run(con)}; con.close(); handler.send_json(obj); return True
    if path == "/api/m7/readiness":
        if user["role"] != "admin": handler.send_json({"error": "Sin permisos."}, 403); return True
        con = core.db(); doctor = INFRA.doctor(con); con.close(); external = EXTERNAL_ATTESTATIONS.summary()
        handler.send_json({"phase": "M7", "build_id": BUILD_ID, "application_controls": doctor, "external_attestations": external, "production_ready": bool(doctor.get("ready") and external.get("ready") and SETTINGS.profile == "production"), "notice": "La preparación técnica no sustituye la evidencia del entorno, pentest, carga, privacidad, restauración y rollback."}); return True
    if path == "/api/security":
        if user["role"] != "admin": handler.send_json({"error": "Sin permisos."}, 403); return True
        handler.send_json(security_overview()); return True
    return False
