from __future__ import annotations
import copy
import json
from pathlib import Path


class CoEm003ValidationV244:
    VERSION = "2.44"

    def __init__(self, root: Path, evaluator):
        self.root = Path(root)
        self.evaluator = evaluator
        self.product_dir = self.root / "app" / "assets" / "advanced-legal-library" / "CO-EM-003"
        self.canonical = self._load("ESCENARIOS_CANONICOS_V244.json")
        self.negative = self._load("ESCENARIOS_NEGATIVOS_V244.json")
        self.visual = self._load("QA_VISUAL_V244.json")

    def _load(self, name):
        return json.loads((self.product_dir / name).read_text(encoding="utf-8"))

    @staticmethod
    def _set(obj, path, value):
        parts = path.split(".")
        cur = obj
        for key in parts[:-1]:
            cur = cur.setdefault(key, {})
        cur[parts[-1]] = copy.deepcopy(value)

    @staticmethod
    def _remove(obj, path):
        parts = path.split(".")
        cur = obj
        for key in parts[:-1]:
            if not isinstance(cur, dict) or key not in cur:
                return
            cur = cur[key]
        if isinstance(cur, dict):
            cur.pop(parts[-1], None)

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
        for kind, catalog in (("canonical", self.canonical), ("negative", self.negative)):
            for scenario in catalog["scenarios"]:
                ids.append(scenario["id"])
                answers = self.materialize(catalog, scenario)
                result = self.evaluator.evaluate(answers)
                exp = scenario.get("expected", {})
                if "blocked" in exp and result["blocked"] != exp["blocked"]:
                    issues.append(f"{scenario['id']}: blocked={result['blocked']}")
                if exp.get("risk_level") and result["risk_level"] != exp["risk_level"]:
                    issues.append(f"{scenario['id']}: risk={result['risk_level']}")
                if exp.get("readiness") and result["readiness"] != exp["readiness"]:
                    issues.append(f"{scenario['id']}: readiness={result['readiness']}")
                finding_ids = {x["id"] for x in result["findings"]}
                required = exp.get("required_findings") or exp.get("findings") or []
                if exp.get("finding"):
                    required = list(required) + [exp["finding"]]
                for fid in required:
                    if fid not in finding_ids:
                        issues.append(f"{scenario['id']}: falta {fid}")
                if exp.get("missing") and exp["missing"] not in {x["path"] for x in result["missing_fields"]}:
                    issues.append(f"{scenario['id']}: falta campo {exp['missing']}")
                for doc in exp.get("documents", []):
                    if doc not in result["documents"]:
                        issues.append(f"{scenario['id']}: falta documento {doc}")
                if exp.get("document_count") is not None and len(result["documents"]) != exp["document_count"]:
                    issues.append(f"{scenario['id']}: documentos={len(result['documents'])}")
                for block in exp.get("blocks", []):
                    if block not in result["blocks"]:
                        issues.append(f"{scenario['id']}: falta bloque {block}")
        if len(ids) != len(set(ids)):
            issues.append("Identificadores de escenarios duplicados.")
        return {"version": self.VERSION, "canonical": len(self.canonical["scenarios"]), "negative": len(self.negative["scenarios"]), "visual": len(self.visual["scenarios"]), "issues": issues, "valid": not issues}

    def summary(self):
        out = self.validate_catalogs()
        out.update({"status": "closed" if out["valid"] else "issues_detected", "visual_scenarios": self.visual["scenarios"]})
        return out
