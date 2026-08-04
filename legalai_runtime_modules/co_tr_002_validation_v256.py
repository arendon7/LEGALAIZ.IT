from __future__ import annotations

import copy
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class CoTr002ValidationV256:
    VERSION = "2.56"
    OFFICIAL_DOMAINS = {
        "suin-juriscol.gov.co",
        "www.suin-juriscol.gov.co",
        "corteconstitucional.gov.co",
        "www.corteconstitucional.gov.co",
        "mintransporte.gov.co",
        "www.mintransporte.gov.co",
    }

    def __init__(self, root: Path, evaluator, reference_date: date | None = None):
        self.root = Path(root)
        self.evaluator = evaluator
        self.reference_date = reference_date or date.today()
        self.product_dir = self.root / "app" / "assets" / "advanced-legal-library" / "CO-TR-002"
        self.canonical = self._load("ESCENARIOS_CANONICOS_V256.json")
        self.negative = self._load("ESCENARIOS_NEGATIVOS_V256.json")
        self.visual = self._load("QA_VISUAL_V256.json")
        self.sources = self._load("FUENTES_V256.json")
        self.source_verification = self._load("SOURCE_VERIFICATION_V256.json")
        self.documents = self._load("DOCUMENTOS_V256.json")
        self.blocks = self._load("BLOQUES_V256.json")
        self.governance = self._load("GOBIERNO_V256.json")
        self.regression = self._load("REGRESSION_MATRIX_V256.json")

    def _load(self, name: str) -> dict[str, Any]:
        path = self.product_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Activo de validación ausente: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

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

    def scenario(self, scenario_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for catalog in (self.canonical, self.negative):
            for item in catalog["scenarios"]:
                if item["id"] == scenario_id:
                    return item, self.materialize(catalog, item)
        raise KeyError(scenario_id)

    @staticmethod
    def _ids(items: list[dict[str, Any]], key: str = "id") -> set[str]:
        return {str(item.get(key)) for item in items if item.get(key)}

    def _validate_scenario_result(self, scenario: dict[str, Any], result: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        sid = scenario["id"]
        expected = scenario.get("expected", {})
        for scalar in ("blocked", "status", "risk", "release_blocked", "professional_review_required"):
            if scalar in expected and result.get(scalar) != expected[scalar]:
                issues.append(f"{sid}: {scalar}={result.get(scalar)!r}, esperado={expected[scalar]!r}")

        finding_ids = self._ids(result.get("findings", []))
        for finding_id in expected.get("required_findings", []):
            if finding_id not in finding_ids:
                issues.append(f"{sid}: falta hallazgo {finding_id}")
        for finding_id in expected.get("forbidden_findings", []):
            if finding_id in finding_ids:
                issues.append(f"{sid}: hallazgo prohibido {finding_id}")

        missing_paths = {item.get("path") for item in result.get("missing_fields", [])}
        if expected.get("missing") and expected["missing"] not in missing_paths:
            issues.append(f"{sid}: falta campo esperado {expected['missing']}")

        documents = set(result.get("documents", []))
        for document in expected.get("documents", []):
            if document not in documents:
                issues.append(f"{sid}: falta documento {document}")
        for document in expected.get("forbidden_documents", []):
            if document in documents:
                issues.append(f"{sid}: documento prohibido {document}")
        if expected.get("document_count") is not None and len(documents) != int(expected["document_count"]):
            issues.append(f"{sid}: documentos={len(documents)}, esperado={expected['document_count']}")

        blocks = set(result.get("blocks", []))
        for block in expected.get("blocks", []):
            if block not in blocks:
                issues.append(f"{sid}: falta bloque {block}")
        for block in expected.get("forbidden_blocks", []):
            if block in blocks:
                issues.append(f"{sid}: bloque prohibido {block}")
        return issues

    def validate_catalogs(self) -> dict[str, Any]:
        issues: list[str] = []
        ids: list[str] = []
        passed = 0
        for catalog in (self.canonical, self.negative):
            if catalog.get("version") != self.VERSION:
                issues.append("Un catálogo de escenarios tiene versión incorrecta.")
            for scenario in catalog.get("scenarios", []):
                ids.append(scenario["id"])
                answers = self.materialize(catalog, scenario)
                result = self.evaluator.evaluate(answers)
                scenario_issues = self._validate_scenario_result(scenario, result)
                if scenario_issues:
                    issues.extend(scenario_issues)
                else:
                    passed += 1
        if len(ids) != len(set(ids)):
            issues.append("Identificadores de escenarios duplicados.")

        canonical_ids = {item["id"] for item in self.canonical.get("scenarios", [])}
        for visual in self.visual.get("scenarios", []):
            if visual.get("id") not in canonical_ids:
                issues.append(f"Escenario visual inexistente: {visual.get('id')}")
            else:
                _, answers = self.scenario(visual["id"])
                result = self.evaluator.evaluate(answers)
                if result.get("blocked"):
                    issues.append(f"Escenario visual bloqueado: {visual['id']}")
            if not visual.get("documents") or not visual.get("checks"):
                issues.append(f"Escenario visual incompleto: {visual.get('id')}")

        return {
            "valid": not issues,
            "issues": issues,
            "canonical": len(self.canonical.get("scenarios", [])),
            "negative": len(self.negative.get("scenarios", [])),
            "visual": len(self.visual.get("scenarios", [])),
            "scenarios_passed": passed,
            "scenarios_total": len(ids),
        }

    def validate_assets(self) -> dict[str, Any]:
        issues: list[str] = []
        document_items = self.documents.get("documents", [])
        document_ids = [item.get("id") for item in document_items]
        if len(document_ids) != len(set(document_ids)):
            issues.append("Hay identificadores de documentos duplicados.")
        required_document_fields = {"id", "filename", "title", "subject", "kind", "required"}
        for item in document_items:
            missing = required_document_fields - set(item)
            if missing:
                issues.append(f"Documento {item.get('id')}: faltan {sorted(missing)}")
            if not isinstance(item.get("required"), list):
                issues.append(f"Documento {item.get('id')}: required no es lista.")

        block_items = self.blocks.get("blocks", [])
        block_ids = [item.get("id") for item in block_items]
        if len(block_ids) != len(set(block_ids)):
            issues.append("Hay identificadores de bloques duplicados.")
        if any(not str(block_id or "").startswith("B256-") for block_id in block_ids):
            issues.append("Existen bloques que no pertenecen a la versión B256.")

        controls = self.governance.get("controls", {})
        mandatory_controls = (
            "immutable_revisions",
            "audit_chain",
            "dual_approval",
            "same_actor_dual_approval",
            "release_gate_required",
            "safe_api_errors",
        )
        for control in mandatory_controls:
            if control not in controls:
                issues.append(f"Falta control de gobierno: {control}")
        if controls.get("same_actor_dual_approval") is not False:
            issues.append("El control de independencia de aprobación no está configurado correctamente.")

        matrix = self.regression.get("matrix", [])
        covered = {item.get("area") for item in matrix}
        for area in {"evaluación", "documentos", "gobierno", "API", "instalación"}:
            if area not in covered:
                issues.append(f"La matriz de regresión no cubre {area}.")

        return {
            "valid": not issues,
            "issues": issues,
            "documents": len(document_items),
            "blocks": len(block_items),
            "regression_areas": len(matrix),
        }

    def validate_sources(self) -> dict[str, Any]:
        issues: list[str] = []
        source_items = self.sources.get("sources", [])
        source_ids = [item.get("id") for item in source_items]
        if len(source_ids) != len(set(source_ids)):
            issues.append("Hay fuentes duplicadas.")
        verification_checks = {item.get("source_id"): item for item in self.source_verification.get("checks", [])}
        for item in source_items:
            source_id = item.get("id")
            parsed = urlparse(str(item.get("url") or ""))
            if parsed.scheme != "https":
                issues.append(f"{source_id}: URL no usa HTTPS.")
            if parsed.netloc not in self.OFFICIAL_DOMAINS:
                issues.append(f"{source_id}: dominio no oficial {parsed.netloc}.")
            if source_id not in verification_checks:
                issues.append(f"{source_id}: falta evidencia de verificación.")
            if not item.get("binding_level"):
                issues.append(f"{source_id}: falta nivel de fuerza jurídica.")
            if item.get("requires_pre_filing_recheck") is not True:
                issues.append(f"{source_id}: falta revalidación previa a radicación.")

        try:
            verified_at = datetime.fromisoformat(str(self.source_verification.get("verified_at"))).date()
        except ValueError:
            verified_at = None
            issues.append("Fecha de verificación normativa inválida.")
        max_age = int(self.source_verification.get("max_age_days") or 0)
        age_days = (self.reference_date - verified_at).days if verified_at else None
        stale = age_days is None or age_days < 0 or age_days > max_age
        if stale:
            issues.append("La verificación normativa está vencida o tiene fecha inconsistente.")

        return {
            "valid": not issues,
            "issues": issues,
            "sources": len(source_items),
            "verified_at": str(verified_at) if verified_at else None,
            "age_days": age_days,
            "max_age_days": max_age,
            "stale": stale,
        }

    def summary(self) -> dict[str, Any]:
        catalogs = self.validate_catalogs()
        assets = self.validate_assets()
        sources = self.validate_sources()
        issues = catalogs["issues"] + assets["issues"] + sources["issues"]
        valid = not issues
        return {
            "version": self.VERSION,
            "product_id": "CO-TR-002",
            "status": "closed" if valid else "issues_detected",
            "valid": valid,
            "issues": issues,
            "catalogs": catalogs,
            "assets": assets,
            "sources": sources,
            "visual_scenarios": self.visual.get("scenarios", []),
            "closure_controls": [
                "scenario_matrix",
                "negative_matrix",
                "visual_qa",
                "official_source_control",
                "release_gate",
                "cryptographic_integrity",
                "dual_approval",
                "safe_api_errors",
            ],
        }
