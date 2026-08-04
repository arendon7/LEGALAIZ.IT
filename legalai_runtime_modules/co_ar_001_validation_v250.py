from __future__ import annotations

import copy
import json
from pathlib import Path


class CoAr001ValidationV250:
    VERSION = "2.50"

    def __init__(self, root: Path, evaluator):
        self.root = Path(root)
        self.evaluator = evaluator
        self.product_dir = self.root / "app" / "assets" / "advanced-legal-library" / "CO-AR-001"
        self.canonical = self._load("ESCENARIOS_CANONICOS_V250.json")
        self.negative = self._load("ESCENARIOS_NEGATIVOS_V250.json")
        self.visual = self._load("QA_VISUAL_V250.json")

    def _load(self, name):
        return json.loads((self.product_dir / name).read_text(encoding="utf-8"))

    @staticmethod
    def _set(obj, path, value):
        parts = path.split(".")
        current = obj
        for key in parts[:-1]:
            current = current.setdefault(key, {})
        current[parts[-1]] = copy.deepcopy(value)

    @staticmethod
    def _remove(obj, path):
        parts = path.split(".")
        current = obj
        for key in parts[:-1]:
            if not isinstance(current, dict) or key not in current:
                return
            current = current[key]
        if isinstance(current, dict):
            current.pop(parts[-1], None)

    def materialize(self, catalog, scenario):
        answers = copy.deepcopy(catalog["base_case"])
        for path, value in scenario.get("overrides", {}).items():
            self._set(answers, path, value)
        for path in scenario.get("remove", []):
            self._remove(answers, path)
        return answers

    def scenario(self, scenario_id):
        for catalog in (self.canonical, self.negative):
            for item in catalog["scenarios"]:
                if item["id"] == scenario_id:
                    return item, self.materialize(catalog, item)
        raise KeyError(scenario_id)

    def validate_catalogs(self):
        issues = []
        ids = []
        for catalog in (self.canonical, self.negative):
            for scenario in catalog["scenarios"]:
                ids.append(scenario["id"])
                answers = self.materialize(catalog, scenario)
                result = self.evaluator.evaluate(answers)
                expected = scenario.get("expected", {})
                if "blocked" in expected and result.get("blocked") != expected["blocked"]:
                    issues.append(f"{scenario['id']}: blocked={result.get('blocked')}")
                if expected.get("readiness") and result.get("readiness") != expected["readiness"]:
                    issues.append(f"{scenario['id']}: readiness={result.get('readiness')}")
                finding_ids = {item["id"] for item in result.get("findings", [])}
                for finding_id in expected.get("required_findings", []):
                    if finding_id not in finding_ids:
                        issues.append(f"{scenario['id']}: falta {finding_id}")
                if expected.get("missing") and expected["missing"] not in {item["path"] for item in result.get("missing_fields", [])}:
                    issues.append(f"{scenario['id']}: falta campo {expected['missing']}")
                for document in expected.get("documents", []):
                    if document not in result.get("documents", []):
                        issues.append(f"{scenario['id']}: falta documento {document}")
                if expected.get("document_count") is not None and len(result.get("documents", [])) != expected["document_count"]:
                    issues.append(f"{scenario['id']}: documentos={len(result.get('documents', []))}")
                for block in expected.get("blocks", []):
                    if block not in result.get("blocks", []):
                        issues.append(f"{scenario['id']}: falta bloque {block}")
        if len(ids) != len(set(ids)):
            issues.append("Identificadores de escenarios duplicados.")
        canonical_ids = {item["id"] for item in self.canonical["scenarios"]}
        for visual in self.visual["scenarios"]:
            if visual["id"] not in canonical_ids:
                issues.append(f"Escenario visual inexistente: {visual['id']}")
        return {
            "version": self.VERSION,
            "canonical": len(self.canonical["scenarios"]),
            "negative": len(self.negative["scenarios"]),
            "visual": len(self.visual["scenarios"]),
            "issues": issues,
            "valid": not issues,
        }

    def summary(self):
        result = self.validate_catalogs()
        result.update({
            "status": "closed" if result["valid"] else "issues_detected",
            "visual_scenarios": self.visual["scenarios"],
        })
        return result
