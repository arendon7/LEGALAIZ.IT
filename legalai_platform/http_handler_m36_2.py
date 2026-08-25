from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m36_1 import Handler as BaseHandler
from legalai_platform.routes.m36_2_review_reconciliation_routes import (
    PREFIX,
    handle_m36_2_review_get,
    handle_m36_2_review_post,
)


class Handler(BaseHandler):
    """M36.2 incremental handler; all prior routes remain delegated unchanged."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user()
        if not user:
            return
        return handle_m36_2_review_get(self, path, user)

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
            return handle_m36_2_review_post(self, path, user)
        except Exception:
            return self.send_json({"error": "No fue posible reconciliar el ciclo de revisión.", "code": "RECONCILIATION_INTERNAL_ERROR"}, 500)


__all__ = ["Handler"]
