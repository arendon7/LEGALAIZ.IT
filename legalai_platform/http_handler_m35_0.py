from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m34_4 import Handler as BaseHandler
from legalai_platform.routes.m35_0_handoff_routes import CLAIM_PATH, handle_m35_0_handoff_post


class Handler(BaseHandler):
    """M35.0 authenticated ownership transfer on top of public M34.4."""

    def do_POST(self):
        path = urlparse(self.path).path
        if path != CLAIM_PATH:
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            user = self.require_user(roles={"client"})
            if not user:
                return
            if not self.require_csrf():
                return
            handled = handle_m35_0_handoff_post(self, path, user)
            if not handled:
                return self.send_json({"error": "Ruta M35.0 no encontrada."}, 404)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible transferir el diagnóstico.",
                    "code": "HANDOFF_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
