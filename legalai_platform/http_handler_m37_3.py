from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m37_2 import Handler as BaseHandler
from legalai_platform.routes.m37_3_disposition_routes import (
    PREFIX,
    handle_m37_3_disposition_get,
    handle_m37_3_disposition_post,
)


class Handler(BaseHandler):
    """M37.3 incremental handler; all earlier routes delegate unchanged."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m37_3_disposition_get(self, path, user)

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
        return handle_m37_3_disposition_post(self, path, user)


__all__ = ["Handler"]
