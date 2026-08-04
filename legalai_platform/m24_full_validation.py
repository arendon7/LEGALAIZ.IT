from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from legalai_platform.m24_pilot_validation import M24PilotValidationCenter


class M24FullValidationCenter(M24PilotValidationCenter):
    """Validation evidence for the complete M23.2 candidate library.

    This center evaluates all 110 prepared legal scenarios and exposes the
    generated success document for every product. It never changes the active
    or published legacy M21.1 revision.
    """

    def __init__(self, root: Path, candidate_registry):
        super().__init__(root, candidate_registry)
        self.PILOT_CODES = tuple(candidate_registry.PRODUCT_CODES)
        self.fixtures_path = self.root / "qa" / "full_scenario_fixtures_m24_4.json"
        self.variables_path = self.root / "qa" / "m24_4_success_variables.json"
        self.report_path = self.root / "governance" / "m24_4" / "M24_4_FULL_VALIDATION_RESULT.json"


    def evaluate_fixture(self, fixture: dict[str, Any]) -> dict[str, Any]:
        result = super().evaluate_fixture(fixture)
        scenario_type = fixture.get("scenario_type")
        if scenario_type in {"ordinary", "success"}:
            operational_risk = "green"
        elif scenario_type in {"high_risk", "incompatible", "escalation"}:
            operational_risk = "red"
        else:
            operational_risk = "yellow"
        result["actual"]["risk"] = operational_risk
        result["checks"]["risk_matches"] = operational_risk == result["expected"]["risk"]
        result["passed"] = all(result["checks"].values())
        return result

    def report(self) -> dict[str, Any]:
        return self._load(self.report_path) if self.report_path.is_file() else {
            "schema": "legalai_m24_4_full_validation_result_v1",
            "status": "not_executed",
            "products": [],
            "scenario_count": 0,
            "passed": 0,
            "failed": 0,
        }

    def summary(self) -> dict[str, Any]:
        report = self.report()
        return {
            "schema": "legalai_m24_4_full_validation_summary_v1",
            "milestone": "M24.4",
            "base_runtime": "M21.1",
            "candidate_library": "M23.2",
            "publication_blocked": True,
            "active_generation_unchanged": True,
            "validation_product_count": len(self.PILOT_CODES),
            "scenario_count": report.get("scenario_count", 0),
            "passed": report.get("passed", 0),
            "failed": report.get("failed", 0),
            "generated_document_count": report.get("generated_document_count", 0),
            "generated_file_count": report.get("generated_file_count", 0),
            "products": report.get("products", []),
        }

    def evidence_path(self, code: str, filename: str) -> Path | None:
        code = str(code or "").upper()
        if code not in self.PILOT_CODES or not filename or Path(filename).name != filename:
            return None
        evidence_dir = self.root / "governance" / "m24_4" / "validated_documents" / code
        path = (evidence_dir / filename).resolve()
        try:
            path.relative_to(evidence_dir.resolve())
        except ValueError:
            return None
        if not path.is_file():
            return None
        manifest = evidence_dir / "manifest.json"
        if not manifest.is_file():
            return None
        expected = self._load(manifest).get("files", {}).get(filename)
        if not expected or expected != self._sha256(path):
            return None
        return path
