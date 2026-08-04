from __future__ import annotations
from pathlib import Path

from co_em_004_document_factory_v246 import CoEm004DocumentFactoryV246


class CoEm004DocumentFactoryV247(CoEm004DocumentFactoryV246):
    VERSION = "2.47"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-em-004-v247"
        self.output_dir.mkdir(parents=True, exist_ok=True)
