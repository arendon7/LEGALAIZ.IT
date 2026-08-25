from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m35_2 import Handler as BaseHandler
from legalai_platform.routes.m35_3_activation_routes import PREFIX, handle_m35_3_activation_get


class Handler(BaseHandler):
    """M35.3 verified post-purchase activation on top of certified M35.2."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not path.startswith(PREFIX):
            return super().do_GET()
        user = self.require_user(roles={"client"})
        if not user:
            return
        if not handle_m35_3_activation_get(self, path, user):
            return self.send_json({"error": "Ruta M35.3 no encontrada.", "code": "M35_3_NOT_FOUND"}, 404)


__all__ = ["Handler"]
