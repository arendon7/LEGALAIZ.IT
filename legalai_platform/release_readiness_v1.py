from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from legalai_platform import release_metadata


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "v1" / "release_readiness_contract.json"


@dataclass(frozen=True)
class ReadinessCheck:
    key: str
    passed: bool
    detail: str

    def public(self) -> dict[str, Any]:
        return {"key": self.key, "passed": self.passed, "detail": self.detail}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _count_collection_items(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    return sum(len(value) for value in payload.values() if isinstance(value, list))


def _count_questions(interviews: Any) -> int:
    if not isinstance(interviews, dict):
        return 0
    total = 0
    for interview in interviews.values():
        if not isinstance(interview, dict):
            continue
        questions = interview.get("questions")
        if isinstance(questions, list):
            total += len(questions)
    return total


def _check(key: str, passed: bool, detail: str) -> ReadinessCheck:
    return ReadinessCheck(key=key, passed=bool(passed), detail=detail)


def _attestation_index(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("attestations")
    if not isinstance(rows, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        attestation_id = str(row.get("id") or "").strip()
        if not attestation_id or attestation_id in indexed:
            continue
        indexed[attestation_id] = row
    return indexed


def _verified_attestation(
    indexed: dict[str, dict[str, Any]],
    attestation_id: str,
    verified_status: str,
) -> bool:
    row = indexed.get(attestation_id)
    if not row:
        return False
    if str(row.get("status") or "") != verified_status:
        return False
    return bool(str(row.get("evidence_ref") or "").strip())


def _metadata_gate(name: str) -> bool:
    return bool(getattr(release_metadata, name, False))


def _metadata_snapshot(names: Iterable[str]) -> dict[str, bool]:
    return {name: _metadata_gate(name) for name in names}


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """Evalúa readiness sin activar producción ni confiar en variables de entorno para promoverla.

    La evaluación distingue tres estados:
    1. código acumulado apto como release candidate;
    2. producción jurídica real;
    3. V1 comercial con pagos reales.

    La CI puede acreditar únicamente el primero. Los otros dos exigen metadata explícita
    y evidencia externa trazable en el registro de attestations.
    """

    root = Path(root or ROOT)
    contract = _load_json(root / "config" / "v1" / "release_readiness_contract.json")
    attestation_path = root / str(contract["attestation_registry"])
    attestations = _load_json(attestation_path) if attestation_path.exists() else {}
    indexed_attestations = _attestation_index(attestations)
    verified_status = str(contract["verified_attestation_status"])

    interviews = _load_json(root / "data" / "interviews.json")
    rules = _load_json(root / "data" / "rules.json")
    run_source = _read_text(root / "run.py")
    production_example = _read_text(root / "config" / ".env.production.example")

    product_count = len(interviews) if isinstance(interviews, dict) else 0
    question_count = _count_questions(interviews)
    rule_count = _count_collection_items(rules)
    floors = contract["portfolio_floor"]

    code_checks: list[ReadinessCheck] = [
        _check(
            "canonical_baseline_preserved",
            str(release_metadata.MILESTONE) == str(contract["candidate_lineage"]["canonical_baseline"]),
            f"release_metadata={release_metadata.MILESTONE}; el gate no promueve VERSION ni main",
        ),
        _check(
            "portfolio_products_floor",
            product_count == int(floors["products"]),
            f"products={product_count} expected={int(floors['products'])}",
        ),
        _check(
            "portfolio_questions_floor",
            question_count >= int(floors["questions"]),
            f"questions={question_count} floor={int(floors['questions'])}",
        ),
        _check(
            "portfolio_rules_floor",
            rule_count >= int(floors["rules"]),
            f"rules={rule_count} floor={int(floors['rules'])}",
        ),
        _check(
            "active_runtime_handler_m37_3",
            str(contract["candidate_lineage"]["required_runtime_handler"]) in run_source,
            "runtime incremental activo en M37.3",
        ),
    ]

    for marker in contract["candidate_lineage"]["required_runtime_markers"]:
        code_checks.append(
            _check(
                f"runtime_marker:{marker}",
                str(marker) in run_source,
                "marker de linaje acumulado presente" if str(marker) in run_source else "marker faltante",
            )
        )

    for literal in contract["production_profile_code_controls"]:
        code_checks.append(
            _check(
                f"production_profile_control:{literal.split('=', 1)[0]}",
                str(literal) in production_example,
                "control declarado en perfil de producción" if str(literal) in production_example else "control ausente",
            )
        )

    code_checks.extend(
        [
            _check(
                "dual_approval_model_preserved",
                str(release_metadata.DOCUMENT_RELEASE_APPROVAL_MODEL) == "distinct_legal_and_qa_same_revision",
                str(release_metadata.DOCUMENT_RELEASE_APPROVAL_MODEL),
            ),
            _check(
                "synthetic_data_boundary_preserved",
                bool(release_metadata.SYNTHETIC_DATA_ONLY) is True,
                "la línea canónica sigue limitada a datos sintéticos",
            ),
        ]
    )

    code_candidate_ready = all(item.passed for item in code_checks)

    real_metadata_names = list(contract["real_production_metadata_gates"])
    commercial_metadata_names = list(contract["commercial_v1_metadata_gates"])
    real_metadata = _metadata_snapshot(real_metadata_names)
    commercial_metadata = _metadata_snapshot(commercial_metadata_names)

    real_attestation_ids = list(contract["real_production_attestations"])
    commercial_attestation_ids = list(contract["commercial_v1_attestations"])
    real_attestation_state = {
        attestation_id: _verified_attestation(indexed_attestations, attestation_id, verified_status)
        for attestation_id in real_attestation_ids
    }
    commercial_attestation_state = {
        attestation_id: _verified_attestation(indexed_attestations, attestation_id, verified_status)
        for attestation_id in commercial_attestation_ids
    }

    real_blockers = [name for name, value in real_metadata.items() if not value]
    real_blockers.extend(attestation_id for attestation_id, value in real_attestation_state.items() if not value)
    commercial_blockers = [name for name, value in commercial_metadata.items() if not value]
    commercial_blockers.extend(
        attestation_id for attestation_id, value in commercial_attestation_state.items() if not value
    )

    real_ready = code_candidate_ready and not real_blockers
    commercial_ready = real_ready and not commercial_blockers

    governance = contract["governance"]
    unauthorized_promotion_detected = bool(
        (real_ready and not bool(governance["code_ci_can_authorize_real_production"]))
        or (commercial_ready and not bool(governance["code_ci_can_authorize_real_payments"]))
    )

    return {
        "schema": "legalaiz-v1-release-readiness-report-v1",
        "canonical_release": {
            "milestone": str(release_metadata.MILESTONE),
            "version": str(release_metadata.VERSION),
            "release_name": str(release_metadata.RELEASE_NAME),
        },
        "candidate_lineage": str(contract["candidate_lineage"]["integrated_head"]),
        "code_release_candidate": {
            "ready": code_candidate_ready,
            "status": "RC_CODE_READY" if code_candidate_ready else "RC_CODE_BLOCKED",
            "checks": [item.public() for item in code_checks],
            "portfolio": {
                "products": product_count,
                "questions": question_count,
                "rules": rule_count,
            },
        },
        "real_legal_production": {
            "ready": real_ready,
            "status": "REAL_PRODUCTION_READY" if real_ready else "REAL_PRODUCTION_BLOCKED",
            "metadata_gates": real_metadata,
            "attestations_verified": real_attestation_state,
            "blockers": real_blockers,
        },
        "commercial_v1": {
            "ready": commercial_ready,
            "status": "COMMERCIAL_V1_READY" if commercial_ready else "COMMERCIAL_V1_BLOCKED",
            "metadata_gates": commercial_metadata,
            "attestations_verified": commercial_attestation_state,
            "blockers": ([] if real_ready else ["REAL_LEGAL_PRODUCTION_NOT_READY"]) + commercial_blockers,
        },
        "governance": {
            "release_candidate_is_not_production_authorization": bool(
                governance["release_candidate_is_not_production_authorization"]
            ),
            "human_legal_and_qa_approval_remain_required": bool(
                governance["human_legal_and_qa_approval_remain_required"]
            ),
            "missing_attestation_fails_closed": bool(governance["missing_attestation_fails_closed"]),
            "unauthorized_promotion_detected": unauthorized_promotion_detected,
        },
    }


__all__ = ["ReadinessCheck", "assess_release_readiness"]
