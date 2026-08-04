from __future__ import annotations

from legalai_platform.runtime_registry import PRODUCT_QUALITY


def handle_product_quality_get(handler, path, user):
    if path == "/api/product-quality":
        handler.send_json(PRODUCT_QUALITY.summary()); return True
    if path.startswith("/api/product-quality/"):
        code = path.split("/")[-1]; detail = PRODUCT_QUALITY.detail(code)
        handler.send_json(detail or {}, 200 if detail else 404); return True
    return False
