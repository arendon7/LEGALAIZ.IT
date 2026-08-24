from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m35_0 import Handler as BaseHandler
from legalai_platform.routes.m35_1_fulfillment_routes import PREPARE_PATH, handle_m35_1_fulfillment_post


class Handler(BaseHandler):
    """M35.1 fulfillment bridge on top of the certified M35.0 ownership handoff."""

    def do_POST(self):
        path = urlparse(self.path).path
        if path != PREPARE_PATH:
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            user = self.require_user(roles={"client"})
            if not user:
                return
            if not self.require_csrf():
                return
            if not handle_m35_1_fulfillment_post(self, path, user):
                return self.send_json({"error": "Ruta M35.1 no encontrada."}, 404)
        except Exception:
            return self.send_json(
                {"error": "No fue posible preparar fulfillment.", "code": "FULFILLMENT_INTERNAL_ERROR"},
                500,
            )


__all__ = ["Handler"]
