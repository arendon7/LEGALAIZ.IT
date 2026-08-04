from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class CoTr001ValidationV258:
    VERSION = "2.58"

    def __init__(self, root: Path, evaluator):
        self.root = Path(root)
        self.evaluator = evaluator
        self.product_dir = self.root / "app" / "assets" / "advanced-legal-library" / "CO-TR-001"
        self.canonical = self._load("ESCENARIOS_CANONICOS_V258.json")
        self.negative = self._load("ESCENARIOS_NEGATIVOS_V258.json")
        self.visual = self._load("QA_VISUAL_V258.json")

    def _load(self, name: str) -> dict[str, Any]:
        return json.loads((self.product_dir / name).read_text(encoding="utf-8"))

    @staticmethod
    def _set(obj: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split(".")
        current = obj
        for key in parts[:-1]:
            current = current.setdefault(key, {})
        current[parts[-1]] = copy.deepcopy(value)

    @staticmethod
    def _remove(obj: dict[str, Any], path: str) -> None:
        parts = path.split(".")
        current: Any = obj
        for key in parts[:-1]:
            if not isinstance(current, dict) or key not in current:
                return
            current = current[key]
        if isinstance(current, dict):
            current.pop(parts[-1], None)

    def materialize(self, catalog: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
        answers = copy.deepcopy(catalog["base_case"])
        for path, value in scenario.get("overrides", {}).items():
            self._set(answers, path, value)
        for path in scenario.get("remove", []):
            self._remove(answers, path)
        return answers

    def scenario(self, scenario_id: str):
        for catalog in (self.canonical, self.negative):
            for item in catalog["scenarios"]:
                if item["id"] == scenario_id:
                    return item, self.materialize(catalog, item)
        raise KeyError(scenario_id)

    def validate_catalogs(self) -> dict[str, Any]:
        issues = []
        ids = []
        for catalog in (self.canonical, self.negative):
            for scenario in catalog["scenarios"]:
                ids.append(scenario["id"])
                answers = self.materialize(catalog, scenario)
                mode = scenario.get("mode", "precheck")
                result = self.evaluator.evaluate(answers, mode=mode)
                expected = scenario.get("expected", {})
                if "blocked" in expected and result.get("blocked") != expected["blocked"]:
                    issues.append("%s: blocked=%s" % (scenario["id"], result.get("blocked")))
                if expected.get("status") and result.get("status") != expected["status"]:
                    issues.append("%s: status=%s" % (scenario["id"], result.get("status")))
                if "match_count" in expected and result.get("match_count") != expected["match_count"]:
                    issues.append("%s: match_count=%s" % (scenario["id"], result.get("match_count")))
                finding_ids = {item["id"] for item in result.get("findings", [])}
                for finding_id in expected.get("required_findings", []):
                    if finding_id not in finding_ids:
                        issues.append("%s: falta %s" % (scenario["id"], finding_id))
                if expected.get("missing") and expected["missing"] not in {item["path"] for item in result.get("missing_fields", [])}:
                    issues.append("%s: falta campo %s" % (scenario["id"], expected["missing"]))
                for document in expected.get("documents", []):
                    if document not in result.get("documents", []):
                        issues.append("%s: falta documento %s" % (scenario["id"], document))
        if len(ids) != len(set(ids)):
            issues.append("Identificadores de escenarios duplicados.")
        known = set(ids)
        for visual in self.visual["scenarios"]:
            if visual["id"] not in known:
                issues.append("Escenario visual inexistente: %s" % visual["id"])
        return {
            "version": self.VERSION,
            "canonical": len(self.canonical["scenarios"]),
            "negative": len(self.negative["scenarios"]),
            "visual": len(self.visual["scenarios"]),
            "issues": issues,
            "valid": not issues,
        }

    def summary(self) -> dict[str, Any]:
        result = self.validate_catalogs()
        result.update({"status": "ready" if result["valid"] else "issues_detected", "visual_scenarios": self.visual["scenarios"]})
        return result
