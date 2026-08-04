from __future__ import annotations

from pathlib import Path
from typing import Any

from co_tr_001_document_factory_v259 import CoTr001DocumentFactoryV259
from co_tr_001_governance_v259 import CoTr001GovernanceV259
from co_tr_001_release_gate_v259 import CoTr001ReleaseGateV259
from co_tr_001_v259 import CoTr001CanonicalV259
from co_tr_001_validation_v259 import CoTr001ValidationV259


class CoTr001ServiceV259:
    """Fachada estable de CO-TR-001 v2.59, desacoplada del framework HTTP."""

    VERSION = "2.59"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.evaluator = CoTr001CanonicalV259(self.root)
        self.factory = CoTr001DocumentFactoryV259(self.root, self.evaluator)
        self.governance = CoTr001GovernanceV259(self.root, self.factory)
        self.validation = CoTr001ValidationV259(self.root, self.evaluator)
        self.release_gate = CoTr001ReleaseGateV259(
            self.root,
            self.evaluator,
            self.validation,
            self.governance,
        )
        self.governance.bind_release_gate(self.release_gate)

    def capabilities(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "product": "CO-TR-001",
            "summary": self.evaluator.summary(),
            "validation": self.validation.summary(),
            "release_gate": self.release_gate.static(),
            "actions": [
                "evaluate",
                "generate",
                "summary",
                "create_revision",
                "compare",
                "approve",
                "verify_integrity",
                "release_gate",
                "source_control",
                "closure",
            ],
        }

    def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        return self.evaluator.evaluate(answers, mode=mode)

    def generate(self, answers: dict[str, Any], actor: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        result = self.factory.generate(answers, actor, mode=mode)
        result["governance"] = self.governance.register_generation(result, answers, actor)
        return result

    def closure(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "validation": self.validation.summary(),
            "release_gate": self.release_gate.static(),
        }

    def source_control(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "validation": self.validation.validate_sources(),
            "verification": self.factory.source_verification,
            "sources": self.factory.sources,
        }
