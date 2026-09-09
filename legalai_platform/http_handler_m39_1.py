from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m37_3 import Handler as BaseHandler
from legalai_platform.routes.m39_1_enterprise_routes import (
    PREFIX,
    handle_m39_1_enterprise_get,
    handle_m39_1_enterprise_post,
)


class Handler(BaseHandler):
    """M39.1 incremental handler; tenancy routes are isolated from M37.x."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m39_1_enterprise_get(self, path, user)

    def do_POST(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_POST()
        if not self.require_origin():
            return
        user = self.require_user()
        if not user:
            return
        if not self.require_csrf():
            return
        return handle_m39_1_enterprise_post(self, path, user)


__all__ = ["Handler"]
