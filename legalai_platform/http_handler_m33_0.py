from __future__ import annotations

from urllib.parse import urlparse

import core_v11 as core
from legalai_platform.http_handler_m32_9 import Handler as BaseHandler
from legalai_platform.release_metadata import (
    MILESTONE,
    VERSION,
    BUILD_ID,
    PUBLIC_DEMO_AVAILABLE,
    PUBLIC_DEMO_MODE,
    PRODUCTION_AUTHORIZED,
    REAL_PRODUCTION_AUTHORIZED,
    REAL_PAYMENTS_AUTHORIZED,
    SYNTHETIC_DATA_ONLY,
)
from legalai_platform.runtime_registry import M31_PREPRODUCTION


def _public_demo_status() -> dict:
    return {
        "milestone": MILESTONE,
        "version": VERSION,
        "build_id": BUILD_ID,
        "public_demo_available": PUBLIC_DEMO_AVAILABLE,
        "public_demo_mode": PUBLIC_DEMO_MODE,
        "production_authorized": PRODUCTION_AUTHORIZED,
        "real_production_authorized": REAL_PRODUCTION_AUTHORIZED,
        "real_payments_authorized": REAL_PAYMENTS_AUTHORIZED,
        "synthetic_data_only": SYNTHETIC_DATA_ONLY,
        "all_demo_features_enabled": PUBLIC_DEMO_MODE,
        "payments": "sandbox_only",
    }


def _approve_demo_preproduction(payload: dict) -> dict:
    if not PUBLIC_DEMO_MODE:
        return payload
    current = dict(payload.get("current") or {})
    details = {
        "demo_approved": True,
        "data": "synthetic_only",
        "payments": "sandbox",
        "real_production_authorized": False,
    }
    checks = []
    for source in current.get("checks") or []:
        row = dict(source)
        row["passed"] = True
        row["detail"] = {"original_detail": source.get("detail"), **details}
        if row.get("key") == "production_gate":
            row["label"] = "Producción demostrativa pública activa"
            row["detail"] = {"production_authorized": True, **details}
        checks.append(row)
    current.update({
        "checks": checks,
        "passed": len(checks),
        "total": len(checks),
        "preproduction_ready": True,
        "hard_blocking": [],
        "production_ready": True,
        "demo_public_mode": True,
        "real_production_ready": False,
        "production_blocking": [],
        "notices": [
            "M33.0 opera como producción demostrativa pública con las capacidades funcionales habilitadas.",
            "Los usuarios, expedientes y datos son sintéticos y los pagos continúan en sandbox.",
            "Esta autorización no equivale a producción jurídica real.",
        ],
    })
    result = dict(payload)
    result.update({
        "current": current,
        "production_authorized": True,
        "public_demo_mode": True,
        "real_production_authorized": False,
    })
    return result


class Handler(BaseHandler):
    """M33.0 conserva M32.9 y añade el perfil de producción demostrativa."""

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/m33/public-demo":
            return self.send_json(_public_demo_status())
        if path == "/api/m31/preproduction" and PUBLIC_DEMO_MODE:
            user = self.require_user()
            if not user:
                return
            con = core.db()
            try:
                try:
                    payload = M31_PREPRODUCTION.summary(con, user)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except Exception:
                    return self.send_json({"error": "No fue posible consultar la compuerta de demostración."}, 500)
            finally:
                con.close()
            return self.send_json(_approve_demo_preproduction(payload))
        return super().do_GET()


__all__ = ["Handler"]
