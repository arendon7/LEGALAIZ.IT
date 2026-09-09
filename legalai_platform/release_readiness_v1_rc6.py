from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.release_readiness_v1_rc5 import assess_release_readiness as assess_rc5_release_readiness


ROOT = Path(__file__).resolve().parents[1]


def assess_release_readiness(root: Path | None = None) -> dict[str, Any]:
    """Añade a RC5 un gate estructural para ejecutar evidencia externa.

    RC6 certifica solamente que existe un runbook completo, segregado y fail-closed.
    El estado de ejecución permanece externo y pendiente; este módulo no puede crear
    evidencia, cambiar attestations, modificar release_metadata ni autorizar go-live.
    """

    root = Path(root or ROOT)
    report = deepcopy(assess_rc5_release_readiness(root))
    execution_pack = EvidenceExecutionPlan(root).summary()

    candidate = report["code_release_candidate"]
    checks = list(candidate.get("checks") or [])
    checks.extend(
        [
            {
                "key": "evidence_execution_pack_structurally_ready",
                "passed": bool(execution_pack["structurally_ready"]),
                "detail": (
                    f"controls={execution_pack['controls']} rc2={execution_pack['rc2_controls']} "
                    f"rc4={execution_pack['rc4_attestations']} errors={len(execution_pack['errors'])}"
                ),
            },
            {
                "key": "evidence_execution_pack_has_no_embedded_evidence",
                "passed": execution_pack["evidence_refs_present"] == 0 and execution_pack["executed"] == 0,
                "detail": "el plan define ejecución; no contiene evidencia ni afirma controles ejecutados",
            },
            {
                "key": "evidence_execution_pack_starts_fail_closed",
                "passed": execution_pack["pending"] == 22 and execution_pack["execution_ready"] is False,
                "detail": f"pending={execution_pack['pending']}/22 execution_ready=false",
            },
        ]
    )
    candidate["checks"] = checks
    candidate["ready"] = all(bool(item.get("passed")) for item in checks)
    candidate["status"] = "RC_CODE_READY" if candidate["ready"] else "RC_CODE_BLOCKED"

    real = report["real_legal_production"]
    real["ready"] = bool(real.get("ready") and candidate["ready"])
    real["status"] = "REAL_PRODUCTION_READY" if real["ready"] else "REAL_PRODUCTION_BLOCKED"

    commercial = report["commercial_v1"]
    commercial["ready"] = bool(commercial.get("ready") and real["ready"] and candidate["ready"])
    commercial["status"] = "COMMERCIAL_V1_READY" if commercial["ready"] else "COMMERCIAL_V1_BLOCKED"
    blockers = [item for item in list(commercial.get("blockers") or []) if item != "REAL_LEGAL_PRODUCTION_NOT_READY"]
    if not real["ready"]:
        blockers.insert(0, "REAL_LEGAL_PRODUCTION_NOT_READY")
    commercial["blockers"] = list(dict.fromkeys(blockers))

    report["schema"] = "legalaiz-v1-release-readiness-report-v4"
    report["evidence_execution_pack"] = execution_pack
    governance = report["governance"]
    governance["execution_plan_completeness_is_not_external_evidence"] = True
    governance["ci_can_validate_execution_plan_structure_only"] = True
    governance["ci_can_mark_external_execution_complete"] = False
    governance["external_execution_pack_required_before_evidence_collection"] = True

    return report


__all__ = ["assess_release_readiness"]
