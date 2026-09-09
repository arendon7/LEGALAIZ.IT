from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m34_3 import Handler as BaseHandler
from legalai_platform.routes.m34_4_recommendation_routes import (
    RECOMMENDATION_PATH,
    handle_m34_4_recommendation_post,
)


class Handler(BaseHandler):
    """M34.4 recommendation extension over the certified M34.3 handler."""

    def do_POST(self):
        path = urlparse(self.path).path
        if path != RECOMMENDATION_PATH:
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            handled = handle_m34_4_recommendation_post(self, path)
            if not handled:
                return self.send_json({"error": "Ruta M34.4 no encontrada."}, 404)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible procesar la recomendación.",
                    "code": "M34_4_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
