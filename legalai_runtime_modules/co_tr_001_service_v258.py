from __future__ import annotations

from pathlib import Path
from typing import Any

from co_tr_001_document_factory_v258 import CoTr001DocumentFactoryV258
from co_tr_001_governance_v258 import CoTr001GovernanceV258
from co_tr_001_v258 import CoTr001CanonicalV258
from co_tr_001_validation_v258 import CoTr001ValidationV258


class CoTr001ServiceV258:
    VERSION = "2.58"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.evaluator = CoTr001CanonicalV258(self.root)
        self.factory = CoTr001DocumentFactoryV258(self.root, self.evaluator)
        self.governance = CoTr001GovernanceV258(self.root, self.factory)
        self.validation = CoTr001ValidationV258(self.root, self.evaluator)

    def capabilities(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "product": "CO-TR-001",
            "summary": self.evaluator.summary(),
            "validation": self.validation.summary(),
            "actions": [
                "evaluate",
                "generate",
                "register_generation",
                "create_revision",
                "compare",
                "approve",
                "verify_integrity",
            ],
        }

    def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        return self.evaluator.evaluate(answers, mode=mode)

    def generate(self, answers: dict[str, Any], actor: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        result = self.factory.generate(answers, actor, mode=mode)
        result["governance"] = self.governance.register_generation(result, answers, actor)
        return result
