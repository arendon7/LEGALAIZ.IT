from __future__ import annotations

from pathlib import Path

from co_ar_001_document_factory_v249 import CoAr001DocumentFactoryV249


class CoAr001DocumentFactoryV250(CoAr001DocumentFactoryV249):
    VERSION = "2.50"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-ar-001-v250"
        self.output_dir.mkdir(parents=True, exist_ok=True)
