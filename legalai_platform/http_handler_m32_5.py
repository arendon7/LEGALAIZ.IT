from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler import Handler as BaseHandler
from legalai_platform.routes.m32_5_approval_desk_routes import (
    PREFIX,
    handle_m32_5_approval_desk_get,
    handle_m32_5_approval_desk_post,
)


class Handler(BaseHandler):
    """Extensión aislada que conserva todas las rutas y controles anteriores."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m32_5_approval_desk_get(self, path, user)

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
            return handle_m32_5_approval_desk_post(self, path, user)
        except Exception:
            # Los errores esperados se traducen en el módulo de rutas. Un fallo no
            # controlado nunca expone rutas, clases, SQL ni mensajes internos.
            return self.send_json({"error": "Error interno de la Mesa Jurídica"}, 500)


__all__ = ["Handler"]
