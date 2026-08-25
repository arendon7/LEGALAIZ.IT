from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = Path("config/v1/evidence_execution_plan.json")
RC2_POLICY_PATH = Path("config/v1_rc2_external_evidence_policy.json")
RC4_ATTESTATIONS_PATH = Path("config/v1/production_attestations.json")
EXPECTED_SCHEMA = "legalaiz-v1-evidence-execution-plan-v1"
EXPECTED_PENDING_STATUS = "PENDING_EXTERNAL_EXECUTION"
FORBIDDEN_SECRET_KEYS = {
    "password",
    "passwords",
    "token",
    "tokens",
    "api_key",
    "api_keys",
    "secret_value",
    "secret_values",
    "credential",
    "credentials",
    "private_key",
    "private_keys",
}


@dataclass(frozen=True)
class ExecutionPlanValidation:
    valid: bool
    errors: tuple[str, ...]
    rc2_count: int
    rc4_count: int
    total_count: int
    pending_count: int
    evidence_refs_present: int

    def public(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "rc2_count": self.rc2_count,
            "rc4_count": self.rc4_count,
            "total_count": self.total_count,
            "pending_count": self.pending_count,
            "evidence_refs_present": self.evidence_refs_present,
        }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _index_rc4_attestations(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("attestations"), list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for row in payload["attestations"]:
        if not isinstance(row, dict):
            continue
        key = str(row.get("id") or "").strip()
        if key and key not in indexed:
            indexed[key] = row
    return indexed


def _forbidden_keys(payload: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).strip().lower()
            child = f"{path}.{key}"
            if lowered in FORBIDDEN_SECRET_KEYS:
                findings.append(child)
            findings.extend(_forbidden_keys(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(_forbidden_keys(value, f"{path}[{index}]"))
    return findings


def _dependency_cycle(indexed: dict[str, dict[str, Any]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        if node in visiting:
            try:
                start = stack.index(node)
            except ValueError:
                start = 0
            return stack[start:] + [node]
        if node in visited:
            return []
        visiting.add(node)
        stack.append(node)
        for dependency in indexed[node].get("prerequisites") or []:
            dep = str(dependency)
            if dep in indexed:
                cycle = visit(dep)
                if cycle:
                    return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return []

    for ref in indexed:
        cycle = visit(ref)
        if cycle:
            return cycle
    return []


def validate_plan_payload(plan: Any, rc2_policy: Any, rc4_attestations: Any) -> ExecutionPlanValidation:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ExecutionPlanValidation(False, ("plan_not_object",), 0, 0, 0, 0, 0)

    if str(plan.get("schema") or "") != EXPECTED_SCHEMA:
        errors.append("invalid_schema")
    if str(plan.get("status") or "") != "PLANNED_NOT_EXECUTED":
        errors.append("invalid_plan_status")

    governance = plan.get("governance")
    required_false = (
        "ci_can_mark_external_execution_complete",
        "ci_can_authorize_real_production",
        "ci_can_authorize_real_payments",
    )
    required_true = (
        "plan_completeness_is_not_evidence",
        "ci_can_validate_structure_only",
        "executor_and_reviewer_must_be_distinct_roles",
        "evidence_must_remain_outside_public_outputs",
        "secrets_must_not_be_stored_in_plan",
        "control_equivalence_requires_versioned_policy_migration",
    )
    if not isinstance(governance, dict):
        errors.append("missing_governance")
        governance = {}
    for key in required_false:
        if governance.get(key) is not False:
            errors.append(f"governance_must_be_false:{key}")
    for key in required_true:
        if governance.get(key) is not True:
            errors.append(f"governance_must_be_true:{key}")

    forbidden = _forbidden_keys(plan)
    errors.extend(f"secret_bearing_key_forbidden:{path}" for path in forbidden)

    rc2_controls = {}
    if isinstance(rc2_policy, dict) and isinstance(rc2_policy.get("controls"), dict):
        rc2_controls = rc2_policy["controls"]
    rc4_index = _index_rc4_attestations(rc4_attestations)
    if len(rc2_controls) != 10:
        errors.append(f"rc2_source_inventory_invalid:{len(rc2_controls)}")
    if len(rc4_index) != 12:
        errors.append(f"rc4_source_inventory_invalid:{len(rc4_index)}")

    controls = plan.get("controls")
    if not isinstance(controls, list):
        controls = []
        errors.append("controls_not_list")

    allowed_environments = set(plan.get("allowed_environments") or [])
    allowed_scopes = set(plan.get("allowed_release_scopes") or [])
    indexed: dict[str, dict[str, Any]] = {}
    source_seen: set[tuple[str, str]] = set()
    rc2_seen: set[str] = set()
    rc4_seen: set[str] = set()
    pending_count = 0
    evidence_refs_present = 0

    for position, row in enumerate(controls):
        prefix = f"control[{position}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}:not_object")
            continue
        framework = str(row.get("source_framework") or "")
        source_id = str(row.get("source_id") or "")
        ref = str(row.get("ref") or "")
        expected_ref = f"{framework}:{source_id}"
        if not framework or not source_id or ref != expected_ref:
            errors.append(f"{prefix}:invalid_ref")
        if ref in indexed:
            errors.append(f"duplicate_ref:{ref}")
        elif ref:
            indexed[ref] = row
        source_key = (framework, source_id)
        if source_key in source_seen:
            errors.append(f"duplicate_source_control:{framework}:{source_id}")
        source_seen.add(source_key)

        if framework == "RC2":
            rc2_seen.add(source_id)
            source = rc2_controls.get(source_id)
            if not isinstance(source, dict):
                errors.append(f"{ref}:unknown_rc2_source")
            else:
                if str(row.get("domain") or "") != str(source.get("domain") or ""):
                    errors.append(f"{ref}:rc2_domain_mismatch")
                if row.get("max_validity_days") != source.get("max_validity_days"):
                    errors.append(f"{ref}:rc2_validity_mismatch")
        elif framework == "RC4":
            rc4_seen.add(source_id)
            source = rc4_index.get(source_id)
            if not isinstance(source, dict):
                errors.append(f"{ref}:unknown_rc4_source")
            elif str(row.get("executor_role") or "") != str(source.get("owner_role") or ""):
                errors.append(f"{ref}:rc4_owner_executor_mismatch")
        else:
            errors.append(f"{ref or prefix}:unknown_framework")

        executor = str(row.get("executor_role") or "").strip()
        reviewer = str(row.get("reviewer_role") or "").strip()
        if not executor:
            errors.append(f"{ref}:missing_executor_role")
        if not reviewer:
            errors.append(f"{ref}:missing_reviewer_role")
        if executor and reviewer and executor == reviewer:
            errors.append(f"{ref}:executor_reviewer_not_separated")

        environment = str(row.get("environment") or "")
        if environment not in allowed_environments:
            errors.append(f"{ref}:invalid_environment")
        scope = str(row.get("release_scope") or "")
        if scope not in allowed_scopes:
            errors.append(f"{ref}:invalid_release_scope")
        expected_scope = "commercial_only" if source_id == "real_payment_provider_certification" else "real_production"
        if scope != expected_scope:
            errors.append(f"{ref}:release_scope_mismatch")

        if not str(row.get("artifact_type") or "").strip():
            errors.append(f"{ref}:missing_artifact_type")
        artifacts = row.get("required_artifacts")
        if not isinstance(artifacts, list) or not artifacts or "sha256_manifest" not in artifacts:
            errors.append(f"{ref}:invalid_required_artifacts")
        validity = row.get("max_validity_days")
        if not isinstance(validity, int) or isinstance(validity, bool) or validity <= 0:
            errors.append(f"{ref}:invalid_max_validity_days")
        if row.get("evidence_ref") not in (None, ""):
            evidence_refs_present += 1
            errors.append(f"{ref}:plan_must_not_embed_evidence_ref")
        if str(row.get("status") or "") == EXPECTED_PENDING_STATUS:
            pending_count += 1
        else:
            errors.append(f"{ref}:invalid_execution_status")
        if not str(row.get("redaction_policy") or "").strip():
            errors.append(f"{ref}:missing_redaction_policy")
        prerequisites = row.get("prerequisites")
        if not isinstance(prerequisites, list):
            errors.append(f"{ref}:prerequisites_not_list")

    expected_rc2 = set(rc2_controls)
    expected_rc4 = set(rc4_index)
    if rc2_seen != expected_rc2:
        errors.append(f"rc2_inventory_mismatch:missing={sorted(expected_rc2 - rc2_seen)}:extra={sorted(rc2_seen - expected_rc2)}")
    if rc4_seen != expected_rc4:
        errors.append(f"rc4_inventory_mismatch:missing={sorted(expected_rc4 - rc4_seen)}:extra={sorted(rc4_seen - expected_rc4)}")

    for ref, row in indexed.items():
        for dependency in row.get("prerequisites") or []:
            dep = str(dependency)
            if dep == ref:
                errors.append(f"{ref}:self_dependency")
            elif dep not in indexed:
                errors.append(f"{ref}:unknown_dependency:{dep}")
    cycle = _dependency_cycle(indexed) if indexed else []
    if cycle:
        errors.append("dependency_cycle:" + "->".join(cycle))

    rc2_count = sum(1 for row in controls if isinstance(row, dict) and row.get("source_framework") == "RC2")
    rc4_count = sum(1 for row in controls if isinstance(row, dict) and row.get("source_framework") == "RC4")
    total_count = len(controls)
    if total_count != 22:
        errors.append(f"execution_inventory_count:{total_count}:expected=22")
    if pending_count != total_count:
        errors.append(f"all_controls_must_start_pending:{pending_count}/{total_count}")

    errors = list(dict.fromkeys(errors))
    return ExecutionPlanValidation(
        valid=not errors,
        errors=tuple(errors),
        rc2_count=rc2_count,
        rc4_count=rc4_count,
        total_count=total_count,
        pending_count=pending_count,
        evidence_refs_present=evidence_refs_present,
    )


class EvidenceExecutionPlan:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or ROOT)
        self.plan = _load_json(self.root / PLAN_PATH)
        self.rc2_policy = _load_json(self.root / RC2_POLICY_PATH)
        self.rc4_attestations = _load_json(self.root / RC4_ATTESTATIONS_PATH)

    def validate(self) -> ExecutionPlanValidation:
        return validate_plan_payload(self.plan, self.rc2_policy, self.rc4_attestations)

    def summary(self) -> dict[str, Any]:
        validation = self.validate()
        return {
            "schema": "legalaiz-v1-evidence-execution-plan-summary-v1",
            "structurally_ready": validation.valid,
            "execution_ready": False,
            "execution_status": "PENDING_EXTERNAL_EXECUTION",
            "controls": validation.total_count,
            "pending": validation.pending_count,
            "executed": 0,
            "evidence_refs_present": validation.evidence_refs_present,
            "rc2_controls": validation.rc2_count,
            "rc4_attestations": validation.rc4_count,
            "errors": list(validation.errors),
            "statement": "Plan completo no equivale a evidencia ejecutada ni a autorización de producción.",
        }


__all__ = [
    "EvidenceExecutionPlan",
    "ExecutionPlanValidation",
    "EXPECTED_PENDING_STATUS",
    "validate_plan_payload",
]
