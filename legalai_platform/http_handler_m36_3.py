from __future__ import annotations

from legalai_platform.http_handler_m36_2 import Handler as BaseHandler
from legalai_platform.routes.m36_3_controlled_delivery_routes import (
    PREFIX,
    handle_m36_3_delivery_get,
    handle_m36_3_delivery_post,
)


class Handler(BaseHandler):
    def do_GET(self):
        path = self._path()
        if path == PREFIX or path.startswith(PREFIX + "/"):
            user = self.require_user()
            if not user:
                return
            if handle_m36_3_delivery_get(self, path, user):
                return
        return super().do_GET()

    def do_POST(self):
        path = self._path()
        if path == PREFIX or path.startswith(PREFIX + "/"):
            if not self.require_origin():
                return
            user = self.require_user()
            if not user:
                return
            if not self.require_csrf(user):
                return
            if handle_m36_3_delivery_post(self, path, user):
                return
        return super().do_POST()


__all__ = ["Handler"]
