from __future__ import annotations

import copy
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse


class CoTr001ValidationV259:
    VERSION = "2.59"
    PRODUCT_ID = "CO-TR-001"
    OFFICIAL_DOMAINS = {
        "supertransporte.gov.co",
        "www.supertransporte.gov.co",
        "mintransporte.gov.co",
        "www.mintransporte.gov.co",
        "funcionpublica.gov.co",
        "www.funcionpublica.gov.co",
        "www1.funcionpublica.gov.co",
        "suin-juriscol.gov.co",
        "www.suin-juriscol.gov.co",
    }

    def __init__(self, root: Path, evaluator, reference_date: Optional[date] = None):
        self.root = Path(root)
        self.evaluator = evaluator
        self.reference_date = reference_date or date.today()
        self.product_dir = self.root / "app" / "assets" / "advanced-legal-library" / self.PRODUCT_ID
        self.canonical = self._load("ESCENARIOS_CANONICOS_V259.json")
        self.negative = self._load("ESCENARIOS_NEGATIVOS_V259.json")
        self.visual = self._load("QA_VISUAL_V259.json")
        self.sources = self._load("FUENTES_V259.json")
        self.source_verification = self._load("SOURCE_VERIFICATION_V259.json")
        self.documents = self._load("DOCUMENTOS_V259.json")
        self.blocks = self._load("BLOQUES_V259.json")
        self.governance = self._load("GOBIERNO_V259.json")
        self.regression = self._load("REGRESSION_MATRIX_V259.json")
        self.matrix = self._load("INVESTIGACIONES_SAST_V259.json")
        self.aliases = self._load("AUTORIDADES_ALIAS_V259.json")

    def _load(self, name: str) -> dict[str, Any]:
        path = self.product_dir / name
        if not path.is_file():
            raise FileNotFoundError("Activo de validación ausente: %s" % path)
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
            for item in catalog.get("scenarios", []):
                if item.get("id") == scenario_id:
                    return item, self.materialize(catalog, item)
        raise KeyError(scenario_id)

    @staticmethod
    def _ids(items: list[dict[str, Any]], key: str = "id") -> set[str]:
        return {str(item.get(key)) for item in items if item.get(key)}

    def _validate_scenario_result(self, scenario: dict[str, Any], result: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        sid = str(scenario.get("id"))
        expected = scenario.get("expected", {})
        for scalar in (
            "blocked",
            "status",
            "risk",
            "release_blocked",
            "professional_review_required",
            "decision_firmness_required",
            "match_count",
        ):
            if scalar in expected and result.get(scalar) != expected[scalar]:
                issues.append("%s: %s=%r, esperado=%r" % (sid, scalar, result.get(scalar), expected[scalar]))

        finding_ids = self._ids(result.get("findings", []))
        for finding_id in expected.get("required_findings", []):
            if finding_id not in finding_ids:
                issues.append("%s: falta hallazgo %s" % (sid, finding_id))
        for finding_id in expected.get("forbidden_findings", []):
            if finding_id in finding_ids:
                issues.append("%s: hallazgo prohibido %s" % (sid, finding_id))

        missing_paths = {item.get("path") for item in result.get("missing_fields", [])}
        for path in expected.get("missing", [] if isinstance(expected.get("missing"), list) else [expected.get("missing")]):
            if path and path not in missing_paths:
                issues.append("%s: falta campo esperado %s" % (sid, path))
        for path in expected.get("forbidden_missing", []):
            if path in missing_paths:
                issues.append("%s: campo no debía estar pendiente %s" % (sid, path))

        documents = set(result.get("documents", []))
        for document in expected.get("documents", []):
            if document not in documents:
                issues.append("%s: falta documento %s" % (sid, document))
        for document in expected.get("forbidden_documents", []):
            if document in documents:
                issues.append("%s: documento prohibido %s" % (sid, document))
        if expected.get("document_count") is not None and len(documents) != int(expected["document_count"]):
            issues.append("%s: documentos=%d, esperado=%s" % (sid, len(documents), expected["document_count"]))

        blocks = set(result.get("blocks", []))
        for block in expected.get("blocks", []):
            if block not in blocks:
                issues.append("%s: falta bloque %s" % (sid, block))
        for block in expected.get("forbidden_blocks", []):
            if block in blocks:
                issues.append("%s: bloque prohibido %s" % (sid, block))

        match_ids = {str(item.get("id")) for item in result.get("matches", []) if item.get("id")}
        for match_id in expected.get("match_ids", []):
            if match_id not in match_ids:
                issues.append("%s: falta coincidencia %s" % (sid, match_id))
        if "exact_match_ids" in expected and match_ids != set(expected.get("exact_match_ids", [])):
            issues.append("%s: coincidencias=%s, esperado=%s" % (sid, sorted(match_ids), sorted(expected.get("exact_match_ids", []))))
        return issues

    def validate_catalogs(self) -> dict[str, Any]:
        issues: list[str] = []
        ids: list[str] = []
        passed = 0
        for catalog in (self.canonical, self.negative):
            if catalog.get("version") != self.VERSION:
                issues.append("Un catálogo de escenarios tiene versión incorrecta.")
            for scenario in catalog.get("scenarios", []):
                ids.append(str(scenario.get("id")))
                answers = self.materialize(catalog, scenario)
                result = self.evaluator.evaluate(answers, mode=scenario.get("mode", "precheck"))
                scenario_issues = self._validate_scenario_result(scenario, result)
                if scenario_issues:
                    issues.extend(scenario_issues)
                else:
                    passed += 1
        if len(ids) != len(set(ids)):
            issues.append("Identificadores de escenarios duplicados.")

        canonical_ids = {item.get("id") for item in self.canonical.get("scenarios", [])}
        for visual in self.visual.get("scenarios", []):
            if visual.get("id") not in canonical_ids:
                issues.append("Escenario visual inexistente: %s" % visual.get("id"))
                continue
            _, answers = self.scenario(str(visual["id"]))
            result = self.evaluator.evaluate(answers, mode=visual.get("mode", "precheck"))
            if result.get("blocked"):
                issues.append("Escenario visual bloqueado: %s" % visual["id"])
            docs = visual.get("documents") or ([visual.get("document")] if visual.get("document") else [])
            if not docs or not visual.get("checks"):
                issues.append("Escenario visual incompleto: %s" % visual.get("id"))

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
        required_document_fields = {"id", "filename", "title", "subject", "kind", "modes", "required"}
        for item in document_items:
            missing = required_document_fields - set(item)
            if missing:
                issues.append("Documento %s: faltan %s" % (item.get("id"), sorted(missing)))
            if not isinstance(item.get("required"), list):
                issues.append("Documento %s: required no es lista." % item.get("id"))

        block_items = self.blocks.get("blocks", [])
        block_ids = [item.get("id") for item in block_items]
        if len(block_ids) != len(set(block_ids)):
            issues.append("Hay identificadores de bloques duplicados.")
        if any(not str(block_id or "").startswith("B259-") for block_id in block_ids):
            issues.append("Existen bloques que no pertenecen a la versión B259.")

        controls = self.governance.get("controls", {})
        mandatory_controls = (
            "immutable_revisions",
            "audit_chain",
            "dual_approval",
            "same_actor_dual_approval",
            "release_gate_required",
            "source_revalidation_required",
            "safe_api_errors",
            "approved_package_integrity",
        )
        for control in mandatory_controls:
            if control not in controls:
                issues.append("Falta control de gobierno: %s" % control)
        if controls.get("same_actor_dual_approval") is not False:
            issues.append("El control de independencia de aprobación no está configurado correctamente.")

        matrix = self.regression.get("matrix", [])
        covered = {item.get("area") for item in matrix}
        for area in {"evaluación", "documentos", "gobierno", "API", "instalación", "fuentes", "QA visual"}:
            if area not in covered:
                issues.append("La matriz de regresión no cubre %s." % area)

        records = list(self.matrix.get("records", []))
        record_ids = [item.get("id") for item in records]
        if len(records) != 49:
            issues.append("La instantánea SAST no contiene 49 rangos.")
        if sum(1 for item in records if item.get("group") == "A") != 37:
            issues.append("El Grupo A no contiene 37 rangos.")
        if sum(1 for item in records if item.get("group") == "B") != 12:
            issues.append("El Grupo B no contiene 12 rangos.")
        if len(record_ids) != len(set(record_ids)):
            issues.append("Hay rangos SAST duplicados.")
        alias_map = self.aliases.get("aliases", {})
        if len(alias_map) < 39:
            issues.append("El catálogo de alias no conserva las 39 autoridades esperadas.")

        return {
            "valid": not issues,
            "issues": issues,
            "documents": len(document_items),
            "blocks": len(block_items),
            "regression_areas": len(matrix),
            "matrix_records": len(records),
            "authority_alias_groups": len(alias_map),
        }

    def validate_sources(self) -> dict[str, Any]:
        issues: list[str] = []
        source_items = self.sources.get("sources", [])
        source_ids = [item.get("id") for item in source_items]
        if len(source_ids) != len(set(source_ids)):
            issues.append("Hay fuentes duplicadas.")
        checks = {item.get("source_id"): item for item in self.source_verification.get("checks", [])}
        for item in source_items:
            source_id = item.get("id")
            parsed = urlparse(str(item.get("url") or ""))
            if parsed.scheme != "https":
                issues.append("%s: URL no usa HTTPS." % source_id)
            if parsed.netloc not in self.OFFICIAL_DOMAINS:
                issues.append("%s: dominio no oficial %s." % (source_id, parsed.netloc))
            if source_id not in checks:
                issues.append("%s: falta evidencia de verificación." % source_id)
            if not item.get("binding_level"):
                issues.append("%s: falta nivel de fuerza jurídica." % source_id)
            if item.get("requires_pre_release_recheck") is not True:
                issues.append("%s: falta revalidación previa a liberación." % source_id)
            if not item.get("legal_use"):
                issues.append("%s: falta delimitación de uso jurídico." % source_id)

        for source_id, check in checks.items():
            if source_id not in set(source_ids):
                issues.append("Evidencia de verificación huérfana: %s." % source_id)
            if check.get("status") != "verified":
                issues.append("%s: verificación no aprobada." % source_id)
            if source_id in {"ST-2026-37-WEB", "ST-2026-12-WEB", "ST-2026-37-PDF"}:
                if check.get("firm_decision_found") is True:
                    issues.append("%s: se encontró decisión firme; la matriz y el alcance jurídico deben versionarse antes de liberar." % source_id)
                if check.get("procedural_status") not in {"investigation_published", "official_matrix_published"}:
                    issues.append("%s: estado procesal de la fuente SAST no está controlado." % source_id)

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
            "firm_decision_found": any(bool(item.get("firm_decision_found")) for item in checks.values()),
        }

    def summary(self) -> dict[str, Any]:
        catalogs = self.validate_catalogs()
        assets = self.validate_assets()
        sources = self.validate_sources()
        issues = catalogs["issues"] + assets["issues"] + sources["issues"]
        valid = not issues
        return {
            "version": self.VERSION,
            "product_id": self.PRODUCT_ID,
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
                "firm_decision_control",
                "release_gate",
                "cryptographic_integrity",
                "dual_approval",
                "safe_api_errors",
                "installer_integrity",
            ],
        }
