from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m34_1 import Handler as BaseHandler
from legalai_platform.routes.m34_2_fact_routes import (
    ANALYZE_PATH,
    FACT_DECISIONS_PATH,
    handle_m34_2_fact_post,
)


class Handler(BaseHandler):
    """M34.2 structured fact extraction and confirmation extension.

    Only the two new M34.2 POST routes are intercepted here. Existing M34.1
    start/recover/problem routes continue through the inherited handler.
    """

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in {ANALYZE_PATH, FACT_DECISIONS_PATH}:
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            handled = handle_m34_2_fact_post(self, path)
            if not handled:
                return self.send_json({"error": "Ruta M34.2 no encontrada."}, 404)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible procesar la revisión de datos.",
                    "code": "FACT_REVIEW_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
