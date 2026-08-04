from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from legalai_platform import release_metadata as release


@dataclass(frozen=True)
class AuditCheck:
    key: str
    passed: bool
    detail: object


FORBIDDEN_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".db-journal", ".pyc", ".pyo", ".lzbackup", ".dump", ".pgdump",
    ".pem", ".key", ".p12", ".pfx",
}
FORBIDDEN_NAMES = {".env", "master.key", "secret.key", "secrets.json"}
FORBIDDEN_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", ".idea", ".vscode"}
ACTIVE_DOCS = (
    "README.md", "00_LEEME_PRIMERO.txt", "ALCANCE_Y_LIMITES_FINAL.md",
    "FINAL_RELEASE_NOTES.md", "FINAL_QA_REPORT.md",
    "GUIA_DEMO_INVERSORES_Y_CLIENTES.md", "GUIA_PILOTO_CONTROLADO.md",
    "M31_8_RELEASE_NOTES.md", "M31_8_QA_REPORT.md",
)
REQUIRED_FILES = (
    "legalai_platform/release_metadata.py", "legalai_platform/release_integrity.py",
    "legalai_platform/database.py", "legalai_platform/postgres_evidence.py",
    "legalai_platform/environment_attestation.py", "legalai_platform/evidence_bundle.py",
    "legalai_platform/postgres_schema_bootstrap.py",
    "tools/release_audit.py", "tools/http_smoke.py", "tools/demo_document_smoke.py", "tools/build_release.py",
    "tools/export_postgres_schema.py", "tools/migrate_sqlite_to_postgres.py",
    "tools/postgres_certify.py", "tools/postgres_backup_restore_drill.py",
    "tools/postgres_release_gate.py", "tools/postgres_readiness.py",
    "tools/postgres_certification_pipeline.py", "tools/verify_external_evidence_bundle.py",
    "requirements-postgres.txt", "config/m31_6_release_policy.json",
    "config/m31_7_release_policy.json", "config/m31_8_release_policy.json",
    "M31_8_RELEASE_NOTES.md", "M31_8_QA_REPORT.md", "M31_8_RELEASE_MANIFEST.json",
    "legalai_platform/m31_case_demo.py", "legalai_platform/routes/m31_case_demo_routes.py",
    "app/modules/case_demo_m31_8.js", "tools/case_demo_smoke.py",
    "legalai_platform/m31_demo_reality.py",
    "legalai_platform/routes/m31_demo_reality_routes.py", "app/modules/demo_reality_m31_7.js",
    "deploy/postgres_schema_candidate.sql",
    "deploy/postgres_readiness_m31_6.json", "deploy/postgres_gate_pending_m31_6.json",
    "deploy/docker-compose.postgres-preproduction.yml",
    "deploy/PREPRODUCTION_RUNBOOK_M31_6.md",
    "deploy/POSTGRES_CERTIFICATION_RUNBOOK_M31_6.md",
    "03_CERTIFICAR_POSTGRES_PREPRODUCCION_MAC.command",
    "03_CERTIFICAR_POSTGRES_PREPRODUCCION_LINUX.sh",
    "03_CERTIFICAR_POSTGRES_PREPRODUCCION_WINDOWS.ps1",
)



def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _release_contract(root: Path) -> list[AuditCheck]:
    manifest = _json(root / "MANIFEST.json")
    runtime = _json(root / "config/runtime_manifest.json")
    policy = _json(root / "config/m31_8_release_policy.json")
    expected = {
        "version": release.VERSION,
        "build_id": release.BUILD_ID,
        "release_id": release.RELEASE_ID,
        "release_name": release.RELEASE_NAME,
        "production_authorized": False,
    }
    actual = {key: manifest.get(key) for key in expected}
    runtime_actual = {
        "runtime_version": runtime.get("runtime_version"),
        "build": runtime.get("build"),
        "release_iteration": runtime.get("release_iteration"),
        "production_authorized": runtime.get("m31_8", {}).get("production_authorized"),
    }
    runtime_expected = {
        "runtime_version": release.VERSION,
        "build": release.BUILD_ID,
        "release_iteration": release.MILESTONE,
        "production_authorized": False,
    }
    policy_actual = {
        "phase": policy.get("phase"),
        "version": policy.get("version"),
        "release_id": policy.get("release_id"),
        "production_authorized": policy.get("production_authorized"),
    }
    policy_expected = {
        "phase": release.MILESTONE,
        "version": release.VERSION,
        "release_id": release.RELEASE_ID,
        "production_authorized": False,
    }
    return [
        AuditCheck("manifest_identity", actual == expected, {"expected": expected, "actual": actual}),
        AuditCheck("runtime_manifest_identity", runtime_actual == runtime_expected, {"expected": runtime_expected, "actual": runtime_actual}),
        AuditCheck("release_policy_identity", policy_actual == policy_expected, {"expected": policy_expected, "actual": policy_actual}),
    ]


def _active_docs(root: Path) -> AuditCheck:
    failures = []
    for relative in ACTIVE_DOCS:
        path = root / relative
        if not path.is_file():
            failures.append({"file": relative, "error": "missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if release.MILESTONE not in text or release.VERSION not in text:
            failures.append({
                "file": relative,
                "milestone": release.MILESTONE in text,
                "version": release.VERSION in text,
            })
    return AuditCheck("active_documentation", not failures, failures or {"files": len(ACTIVE_DOCS)})


def _required_files(root: Path) -> AuditCheck:
    missing = [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]
    return AuditCheck("required_release_artifacts", not missing, missing or {"files": len(REQUIRED_FILES)})


def _distribution_state(root: Path) -> AuditCheck:
    violations: list[str] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_dir() and path.name in FORBIDDEN_DIR_NAMES:
            violations.append(rel + "/")
            continue
        if not path.is_file():
            continue
        lower = path.name.lower()
        if lower in FORBIDDEN_NAMES or any(lower.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            violations.append(rel)
            continue
        if rel.startswith("runtime/") and path.name != ".gitkeep":
            violations.append(rel)
            continue
        if rel.startswith("deploy/secrets/") and path.name != "README.md":
            violations.append(rel)
    return AuditCheck("sanitized_distribution", not violations, violations[:200] if violations else {"status": "clean"})


def _docker_contract(root: Path) -> AuditCheck:
    files = [
        root / "deploy/docker-compose.preproduction.yml",
        root / "deploy/docker-compose.yml",
        root / "deploy/docker-compose.postgres-lab.yml",
        root / "deploy/docker-compose.postgres-preproduction.yml",
    ]
    failures = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        if not path.is_file():
            failures.append({"file": relative, "error": "missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "CHANGE_ME_BEFORE_USE" in text:
            failures.append({"file": relative, "error": "inline placeholder secret"})
    pre = (root / "deploy/docker-compose.preproduction.yml").read_text(encoding="utf-8", errors="ignore")
    for token in ("read_only: true", "no-new-privileges:true", "cap_drop: [ALL]", 'LEGAL_ALLOW_DEMO_ACCOUNTS: "false"'):
        if token not in pre:
            failures.append({"file": "deploy/docker-compose.preproduction.yml", "missing": token})
    pg = (root / "deploy/docker-compose.postgres-preproduction.yml").read_text(encoding="utf-8", errors="ignore")
    for token in (
        "LEGAL_DATABASE_BACKEND: postgresql", "POSTGRES_PASSWORD_FILE",
        "LEGAL_POSTGRES_PASSWORD_FILE", "postgres-backup-restore:",
        "database-restore:", "LEGAL_CONFIRM_DESTRUCTIVE_RESTORE: RESTORE_TEST_DATABASE",
        "read_only: true", "cap_drop: [ALL]",
    ):
        if token not in pg:
            failures.append({"file": "deploy/docker-compose.postgres-preproduction.yml", "missing": token})
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8", errors="ignore")
    if "postgresql-client" not in dockerfile:
        failures.append({"file": "Dockerfile", "missing": "postgresql-client"})
    return AuditCheck("deployment_security_contract", not failures, failures or {"status": "hardened"})


def _postgres_foundation(root: Path) -> AuditCheck:
    failures = []
    readiness = _json(root / "deploy/postgres_readiness_m31_6.json")
    if readiness.get("ready_for_external_certification") is not True:
        failures.append("readiness_not_ready")
    for key in ("external_certified", "migration_certified", "backup_restore_certified"):
        if readiness.get(key) is not False:
            failures.append(f"{key}_must_remain_false")
    gate = _json(root / "deploy/postgres_gate_pending_m31_6.json")
    if gate.get("ok") is not False or gate.get("postgres_preproduction_certified") is not False:
        failures.append("pending_gate_must_remain_closed")
    if gate.get("production_authorized") is not False:
        failures.append("pending_gate_must_not_authorize_production")
    schema = (root / "deploy/postgres_schema_candidate.sql").read_text(encoding="utf-8", errors="ignore")
    tables = len(re.findall(r"(?im)^CREATE TABLE(?: IF NOT EXISTS)?", schema))
    indexes = len(re.findall(r"(?im)^CREATE (?:UNIQUE )?INDEX(?: IF NOT EXISTS)?", schema))
    if tables < 100:
        failures.append({"schema_tables": tables,
            "schema_indexes": indexes,
            "lightweight_schema_bootstrap": True, "minimum": 100})
    if indexes < 60:
        failures.append({"schema_indexes": indexes, "minimum": 60})
    if f"-- milestone={release.MILESTONE}" not in schema or f"-- version={release.VERSION}" not in schema:
        failures.append("schema_release_identity_stale")
    if "CREATE TABLE IF NOT EXISTS" not in schema or "CREATE INDEX IF NOT EXISTS" not in schema:
        failures.append("schema_not_idempotent")
    try:
        from legalai_platform.postgres_schema_bootstrap import schema_contract
        contract = schema_contract(root / "deploy/postgres_schema_candidate.sql")
        if not contract.get("ok") or not contract.get("release_identity_valid"):
            failures.append({"schema_contract": contract})
    except Exception as exc:
        failures.append({"schema_contract_error": f"{type(exc).__name__}: {exc}"})
    for relative in ("tools/postgres_certify.py", "tools/migrate_sqlite_to_postgres.py"):
        source = (root / relative).read_text(encoding="utf-8", errors="ignore")
        if "application_services" in source:
            failures.append({"heavy_runtime_dependency": relative})
    requirements = (root / "requirements-postgres.txt").read_text(encoding="utf-8", errors="ignore")
    if "psycopg" not in requirements:
        failures.append("psycopg_requirement_missing")
    return AuditCheck(
        "postgres_certification_foundation",
        not failures,
        failures or {
            "code_ready_for_external_certification": True,
            "external_certified": False,
            "migration_certified": False,
            "backup_restore_certified": False,
            "gate_closed": True,
            "schema_tables": tables,
            "schema_indexes": indexes,
            "lightweight_schema_bootstrap": True,
        },
    )



def _pipeline_contract(root: Path) -> AuditCheck:
    failures = []
    policy = _json(root / "config/m31_6_release_policy.json")
    for key in (
        "single_pipeline_required",
        "environment_attestation_required",
        "evidence_hash_manifest_required",
        "evidence_tamper_verification_required",
        "evidence_may_not_contain_secret_keys",
    ):
        if policy.get(key) is not True:
            failures.append({"policy": key})
    pipeline_path = root / "tools/postgres_certification_pipeline.py"
    verifier_path = root / "tools/verify_external_evidence_bundle.py"
    if pipeline_path.is_file():
        source = pipeline_path.read_text(encoding="utf-8", errors="ignore")
        for token in (
            "M31_6_ENVIRONMENT_ATTESTATION.json",
            "M31_6_EVIDENCE_MANIFEST.json",
            "M31_6_EVIDENCE_VERIFICATION.json",
            "production_authorized",
        ):
            if token not in source:
                failures.append({"pipeline_missing": token})
    else:
        failures.append({"missing": "tools/postgres_certification_pipeline.py"})
    if not verifier_path.is_file():
        failures.append({"missing": "tools/verify_external_evidence_bundle.py"})
    compose = (root / "deploy/docker-compose.postgres-preproduction.yml").read_text(
        encoding="utf-8", errors="ignore"
    )
    for token in (
        "postgres-certification-pipeline:",
        "profiles: [certification-pipeline]",
        "MIGRATION_SOURCE_HOST",
        "database-restore: {condition: service_healthy}",
    ):
        if token not in compose:
            failures.append({"compose_missing": token})
    return AuditCheck(
        "external_certification_pipeline",
        not failures,
        failures or {
            "single_pipeline": True,
            "environment_attestation": True,
            "evidence_hashes": True,
            "tamper_verification": True,
            "production_authorized": False,
        },
    )



def _demo_documental_contract(root: Path) -> AuditCheck:
    failures = []
    policy = _json(root / "config/m31_7_release_policy.json")
    expected = {
        "products_required": 11,
        "templates_required": 76,
        "docx_generation_required": 76,
        "validated_reference_docx_required": 11,
        "validated_reference_pdf_required": 11,
        "per_product_packages_required": 11,
        "global_package_required": True,
        "sha256_verification_required": True,
        "unresolved_variables_allowed": 0,
        "synthetic_data_only": True,
        "production_authorized": False,
    }
    actual = {key: policy.get(key) for key in expected}
    if actual != expected:
        failures.append({"policy": {"expected": expected, "actual": actual}})
    templates = _json(root / "data/document_templates.json")
    products = _json(root / "data/products.json")
    if len(templates) != 76:
        failures.append({"templates": len(templates), "expected": 76})
    if len(products) != 11:
        failures.append({"products": len(products), "expected": 11})
    by_product = {row.get("product_code") for row in templates}
    product_codes = {row.get("code") for row in products}
    if by_product != product_codes:
        failures.append({"template_product_coverage": sorted(by_product), "catalog": sorted(product_codes)})
    backend = (root / "legalai_platform/m31_demo_reality.py").read_text(encoding="utf-8", errors="ignore")
    routes = (root / "legalai_platform/routes/m31_demo_reality_routes.py").read_text(encoding="utf-8", errors="ignore")
    frontend = (root / "app/modules/demo_reality_m31_7.js").read_text(encoding="utf-8", errors="ignore")
    for token in (
        "synthetic_no_real_personal_data", "unresolved_files", "SHA256SUMS.txt", "_generation_lock",
        "Pendiente de diligenciar", "_sanitize_demo_sections",
    ):
        if token not in backend:
            failures.append({"backend_missing": token})
    for token in ("specialist", "admin", "pilot-local", "/generate"):
        if token not in routes:
            failures.append({"routes_missing": token})
    for token in ("Generar los documentos finales", "Descargar ZIP completo", "Variables sin resolver"):
        if token not in frontend:
            failures.append({"frontend_missing": token})
    return AuditCheck(
        "demo_documental_integral",
        not failures,
        failures or {
            "products": 11,
            "templates": 76,
            "synthetic_data_only": True,
            "hash_verification": True,
            "runtime_output_excluded_from_release": True,
            "production_authorized": False,
        },
    )


def _case_demo_contract(root: Path) -> AuditCheck:
    failures = []
    policy = _json(root / "config/m31_8_release_policy.json")
    expected = {
        "demo_cases_required": 11,
        "products_required": 11,
        "active_documents_required": 76,
        "released_packages_required": 11,
        "dual_approvals_required_per_case": 2,
        "distinct_legal_and_qa_people_required": True,
        "same_revision_hash_required": True,
        "immutable_revisions_required": True,
        "new_revision_invalidates_release": True,
        "synthetic_data_only": True,
        "unresolved_variables_allowed": 0,
        "production_authorized": False,
    }
    actual = {key: policy.get(key) for key in expected}
    if actual != expected:
        failures.append({"policy": {"expected": expected, "actual": actual}})
    backend = (root / "legalai_platform/m31_case_demo.py").read_text(encoding="utf-8", errors="ignore")
    routes = (root / "legalai_platform/routes/m31_case_demo_routes.py").read_text(encoding="utf-8", errors="ignore")
    frontend = (root / "app/modules/case_demo_m31_8.js").read_text(encoding="utf-8", errors="ignore")
    for token in (
        "m31_8_demo_revisions", "m31_8_demo_approvals", "revision_sha256",
        "distinct_people", "_invalidate_cohort_package", "build_cohort_package",
        "synthetic_no_real_personal_data",
    ):
        if token not in backend:
            failures.append({"backend_missing": token})
    for token in ("legal-approve", "qa-approve", 'action == "release"', "specialist", "admin"):
        if token not in routes:
            failures.append({"routes_missing": token})
    for token in ("Demo integral por expediente", "Descargar cohorte completa", "Crear nueva revisión"):
        if token not in frontend:
            failures.append({"frontend_missing": token})
    return AuditCheck(
        "case_demo_integral",
        not failures,
        failures or {
            "cases": 11, "documents": 76, "case_packages": 11,
            "immutable_revisions": True, "distinct_dual_approval": True,
            "global_cohort_package": True, "production_authorized": False,
        },
    )


def _security_report(root: Path) -> AuditCheck:
    report = _json(root / "FINAL_SECURITY_SCAN.json")
    actual = {
        "version": report.get("version"),
        "milestone": report.get("milestone"),
        "critical_findings": report.get("critical_findings"),
        "high_findings": report.get("high_findings"),
        "production_blocked": report.get("controls", {}).get("production_blocked"),
    }
    expected = {
        "version": release.VERSION,
        "milestone": release.MILESTONE,
        "critical_findings": 0,
        "high_findings": 0,
        "production_blocked": True,
    }
    return AuditCheck("security_report_current", actual == expected, {"expected": expected, "actual": actual})


def audit_release(root: Path, *, strict_distribution: bool = True) -> dict:
    root = root.resolve()
    checks: list[AuditCheck] = []
    checks.extend(_release_contract(root))
    checks.append(_active_docs(root))
    checks.append(_required_files(root))
    checks.append(_docker_contract(root))
    checks.append(_postgres_foundation(root))
    checks.append(_pipeline_contract(root))
    checks.append(_demo_documental_contract(root))
    checks.append(_case_demo_contract(root))
    checks.append(_security_report(root))
    if strict_distribution:
        checks.append(_distribution_state(root))
    payload = {
        "schema": "legalaizit-release-audit-v1",
        "milestone": release.MILESTONE,
        "version": release.VERSION,
        "build_id": release.BUILD_ID,
        "root": str(root),
        "strict_distribution": strict_distribution,
        "checks": [asdict(check) for check in checks],
    }
    payload["passed"] = sum(1 for check in checks if check.passed)
    payload["total"] = len(checks)
    payload["ok"] = payload["passed"] == payload["total"]
    payload["failures"] = [check.key for check in checks if not check.passed]
    return payload


def write_hash_manifest(root: Path, output: Path, *, exclude: set[str] | None = None) -> int:
    excluded = exclude or set()
    rows = []
    for path in sorted(iter_files(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append(f"{sha256(path)}  {relative}")
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows)
