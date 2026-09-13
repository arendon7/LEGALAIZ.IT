from __future__ import annotations

from urllib.parse import urlparse

from legalai_platform.http_handler_m34_2 import Handler as BaseHandler
from legalai_platform.routes.m34_3_question_routes import (
    ANSWER_PATH,
    NEXT_STEP_PATH,
    handle_m34_3_question_post,
)


class Handler(BaseHandler):
    """M34.3 adaptive question extension over the certified M34.2 handler."""

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in {NEXT_STEP_PATH, ANSWER_PATH}:
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            handled = handle_m34_3_question_post(self, path)
            if not handled:
                return self.send_json({"error": "Ruta M34.3 no encontrada."}, 404)
        except Exception:
            return self.send_json(
                {
                    "error": "No fue posible procesar la siguiente etapa del diagnóstico.",
                    "code": "M34_3_INTERNAL_ERROR",
                },
                500,
            )


__all__ = ["Handler"]
