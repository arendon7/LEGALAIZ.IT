from __future__ import annotations

import json
from pathlib import Path


class ProductQualityCenter:
    """Read-only register of substantive product reviews.

    It separates a product's historical approval from the date and scope of the
    latest legal verification. This prevents a mature document package from
    being presented as if every dynamic rule had been revalidated indefinitely.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "governance" / "m20" / "M20_PRODUCT_QUALITY_REGISTRY.json"

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def summary(self):
        data = self._load(); products = data.get("products", [])
        counts = {"reviewed": 0, "in_review": 0, "pending": 0}
        for product in products:
            status = product.get("status", "pending")
            counts[status if status in counts else "pending"] += 1
        return {
            "version": data.get("version"),
            "verified_at": data.get("verified_at"),
            "counts": counts,
            "products": [{k: row.get(k) for k in ("product_code", "title", "status", "verified_at", "next_action")} for row in products],
            "notice": data.get("notice"),
        }

    def detail(self, product_code: str):
        data = self._load()
        return next((row for row in data.get("products", []) if row.get("product_code") == product_code), None)
