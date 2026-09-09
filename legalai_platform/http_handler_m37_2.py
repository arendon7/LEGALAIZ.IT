from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m37_1 import Handler as BaseHandler
from legalai_platform.routes.m37_2_timing_reminder_routes import (
    PREFIX,
    handle_m37_2_timing_get,
    handle_m37_2_timing_post,
)


class Handler(BaseHandler):
    """M37.2 incremental handler; every non-M37.2 route delegates unchanged."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m37_2_timing_get(self, path, user)

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
        return handle_m37_2_timing_post(self, path, user)


__all__ = ["Handler"]
