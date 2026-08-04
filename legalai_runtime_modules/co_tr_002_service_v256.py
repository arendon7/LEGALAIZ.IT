from __future__ import annotations

from pathlib import Path
from typing import Any

from co_tr_002_document_factory_v256 import CoTr002DocumentFactoryV256
from co_tr_002_governance_v256 import CoTr002GovernanceV256
from co_tr_002_release_gate_v256 import CoTr002ReleaseGateV256
from co_tr_002_v256 import CoTr002CanonicalV256
from co_tr_002_validation_v256 import CoTr002ValidationV256


class CoTr002ServiceV256:
    """Fachada de CO-TR-002 para integrar la Macrofase C sin acoplarla al framework HTTP."""

    VERSION = "2.56"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.evaluator = CoTr002CanonicalV256(self.root)
        self.factory = CoTr002DocumentFactoryV256(self.root, self.evaluator)
        self.governance = CoTr002GovernanceV256(self.root, self.factory)
        self.validation = CoTr002ValidationV256(self.root, self.evaluator)
        self.release_gate = CoTr002ReleaseGateV256(
            self.root,
            self.evaluator,
            self.validation,
            self.governance,
        )
        self.governance.release_gate = self.release_gate

    def capabilities(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "product": "CO-TR-002",
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
            ],
        }

    def evaluate(self, answers: dict[str, Any]) -> dict[str, Any]:
        return self.evaluator.evaluate(answers)

    def generate(self, answers: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        result = self.factory.generate(answers, actor)
        result["governance"] = self.governance.register_generation(result, answers, actor)
        return result

    def closure(self) -> dict[str, Any]:
        return {
            "validation": self.validation.summary(),
            "release_gate": self.release_gate.static(),
        }

    def source_control(self) -> dict[str, Any]:
        return {
            "validation": self.validation.validate_sources(),
            "verification": self.factory.source_verification,
            "sources": self.factory.sources,
        }
