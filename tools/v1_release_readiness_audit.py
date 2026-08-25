#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.release_readiness_v1_rc7 import assess_release_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit V1 release readiness without authorizing production.")
    parser.add_argument(
        "--require-real-production",
        action="store_true",
        help="Return non-zero unless real legal production is fully evidenced and human-authorized.",
    )
    parser.add_argument(
        "--require-commercial-v1",
        action="store_true",
        help="Return non-zero unless real legal production and real payments are fully evidenced and human-authorized.",
    )
    args = parser.parse_args()

    report = assess_release_readiness(ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    candidate = report["code_release_candidate"]
    real = report["real_legal_production"]
    commercial = report["commercial_v1"]
    governance = report["governance"]

    if not candidate["ready"]:
        print("V1 READINESS FAIL: el stack no cumple los gates de release candidate de código.", file=sys.stderr)
        return 2
    if governance["authorization_state_inconsistent"]:
        print(
            "V1 READINESS FAIL: el estado de autorización y su decisión versionada son inconsistentes.",
            file=sys.stderr,
        )
        return 3
    if governance["unauthorized_promotion_detected"]:
        print(
            "V1 READINESS FAIL: se detectó una autorización activa sin procedencia humana versionada válida.",
            file=sys.stderr,
        )
        return 3
    if args.require_real_production and not real["ready"]:
        print(
            "V1 READINESS BLOCKED: producción jurídica real carece de evidencia/autorización completa: "
            + ", ".join(real["blockers"]),
            file=sys.stderr,
        )
        return 4
    if args.require_commercial_v1 and not commercial["ready"]:
        print(
            "V1 READINESS BLOCKED: V1 comercial carece de producción real y/o pagos certificados: "
            + ", ".join(commercial["blockers"]),
            file=sys.stderr,
        )
        return 5

    superset = report["assurance_superset"]
    execution = report["evidence_execution_pack"]
    runtime = report["runtime_external_evidence"]
    rc2_bundle = runtime["rc2_bundle_gate"]
    rc4_ledger = runtime["rc4_attestation_ledger"]
    print(
        "V1 READINESS PASS · "
        f"candidate={candidate['status']} real={real['status']} commercial={commercial['status']} "
        f"rc2={superset['rc2_control_count']} rc4={superset['rc4_attestation_count']} "
        f"execution_plan={execution['controls']} pending={execution['pending']} "
        f"rc2_bundles={rc2_bundle['bundle_validated']}/{rc2_bundle['total']} "
        f"rc4_runtime_verified={rc4_ledger['passed']}/{rc4_ledger['total']} "
        "production_auto_authorized=false payments_auto_authorized=false "
        "runtime_registry_mutation=false authorization_provenance=versioned-human-decision"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
