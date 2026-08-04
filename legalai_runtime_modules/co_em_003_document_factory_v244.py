from __future__ import annotations
from co_em_003_document_factory_v243 import CoEm003DocumentFactoryV243


class CoEm003DocumentFactoryV244(CoEm003DocumentFactoryV243):
    VERSION = "2.44"

    def __init__(self, root, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = self.root / "data" / "generated" / "co-em-003-v244"
        self.output_dir.mkdir(parents=True, exist_ok=True)
