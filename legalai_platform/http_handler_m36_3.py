from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m36_2 import Handler as BaseHandler
from legalai_platform.routes.m36_3_controlled_delivery_routes import (
    PREFIX,
    handle_m36_3_delivery_get,
    handle_m36_3_delivery_post,
)


class Handler(BaseHandler):
    """M36.3 incremental handler; all prior routes remain delegated unchanged."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m36_3_delivery_get(self, path, user)

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
            return handle_m36_3_delivery_post(self, path, user)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible completar la operación de entrega.",
                    "code": "DELIVERY_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
