from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m37_3 import Handler as BaseHandler
from legalai_platform.routes.release_readiness_v1_routes import PREFIX, handle_release_readiness_get


class Handler(BaseHandler):
    """V1-R0 read-only readiness endpoint on top of certified M37.3."""

    def do_GET(self):
        path = urlparse(self.path).path
        if path != PREFIX:
            return super().do_GET()
        user = self.require_user(roles={"admin"})
        if not user:
            return
        return handle_release_readiness_get(self, path, user)


__all__ = ["Handler"]
