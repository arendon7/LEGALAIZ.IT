from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m32_5 import Handler as BaseHandler
from legalai_platform.routes.m32_6_approval_operations_routes import (
    PREFIX,
    handle_m32_6_operations_get,
    handle_m32_6_operations_post,
)


class Handler(BaseHandler):
    """Extensión M32.6 aislada; las rutas previas continúan delegadas sin cambios."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m32_6_operations_get(self, path, user)

    def do_POST(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            user = self.require_user()
            if not user:
                return
            if not self.require_csrf():
                return
            return handle_m32_6_operations_post(self, path, user)
        except Exception:
            return self.send_json({"error": "Error interno de la operación documental"}, 500)


__all__ = ["Handler"]
