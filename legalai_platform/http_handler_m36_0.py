from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m35_3 import Handler as BaseHandler
from legalai_platform.routes.m36_0_fulfillment_routes import (
    PREFIX,
    handle_m36_0_fulfillment_get,
    handle_m36_0_fulfillment_post,
)


class Handler(BaseHandler):
    """M36.0 exact fulfillment intake on top of certified M35.3."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user(roles={"admin"})
        if not user:
            return
        return handle_m36_0_fulfillment_get(self, path, user)

    def do_POST(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_POST()
        if not self.require_origin():
            return
        user = self.require_user(roles={"admin"})
        if not user:
            return
        if not self.require_csrf():
            return
        return handle_m36_0_fulfillment_post(self, path, user)


__all__ = ["Handler"]
