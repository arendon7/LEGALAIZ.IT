from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from co_tr_001_v257 import CoTr001CanonicalV257


class CoTr001ServiceV257:
    def __init__(self, root: Optional[Union[Path, str]] = None):
        self.engine = CoTr001CanonicalV257(root)

    def check(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.engine.evaluate(payload, mode="precheck")

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.engine.evaluate(payload, mode="registration")

    def authority_candidates(self, text: str) -> dict[str, Any]:
        return self.engine.normalize_authority(text)

    def health(self) -> dict[str, Any]:
        manifest = self.engine.summary()["manifest"]
        return {"ok": True, **manifest}
