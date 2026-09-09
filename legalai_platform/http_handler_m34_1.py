from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m33_0 import Handler as BaseHandler
from legalai_platform.routes.m34_1_intake_routes import PREFIX, handle_m34_1_intake_post


class Handler(BaseHandler):
    """M34.1 public intake extension.

    Anonymous intake routes require a same-origin POST but deliberately do not require
    login or CSRF because there is no authenticated browser session yet. The recovery
    code is the scoped bearer secret and is never placed in a URL.
    """

    def do_POST(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            return handle_m34_1_intake_post(self, path)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible procesar el diagnóstico.",
                    "code": "INTAKE_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
