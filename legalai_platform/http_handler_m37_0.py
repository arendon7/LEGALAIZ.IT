from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m36_3 import Handler as BaseHandler
from legalai_platform.routes.m37_0_post_delivery_followup_routes import (
    PREFIX,
    handle_m37_0_followup_get,
    handle_m37_0_followup_post,
)


class Handler(BaseHandler):
    """M37.0 incremental handler; every non-M37 route delegates unchanged."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m37_0_followup_get(self, path, user)

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
            return handle_m37_0_followup_post(self, path, user)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible completar la operación de seguimiento.",
                    "code": "FOLLOWUP_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
