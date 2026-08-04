from __future__ import annotations

import json
from pathlib import Path


class CompleteLegalModelsV215:
    """Read-only registry for complete master legal models."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "app" / "assets" / "master-legal-models" / "manifest.json"

    def summary(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            "version": data.get("version"),
            "title": data.get("title"),
            "notice": data.get("notice"),
            "metrics": data.get("metrics", {}),
            "products": [
                {
                    "product_code": p.get("product_code"),
                    "title": p.get("title"),
                    "source_package": p.get("source_package"),
                    "source_status": p.get("source_status"),
                    "metrics": p.get("metrics", {}),
                    "documents": p.get("documents", []),
                }
                for p in data.get("products", [])
            ],
        }
