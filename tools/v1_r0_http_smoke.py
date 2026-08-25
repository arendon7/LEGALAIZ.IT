#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.m35_0_http_smoke import Client, register_client, require
from tools.m36_0_http_smoke import login_admin


PATH = "/api/release/v1/readiness"


def main() -> int:
    anonymous = Client()
    anonymous.get(PATH, expected=401)

    client = Client()
    register_client(client, "V1R0Client")
    denied = client.get(PATH, expected=403)
    require(
        denied.get("code") in {"ROLE_FORBIDDEN", "FORBIDDEN", "AUTH_FORBIDDEN"}
        or "rol" in str(denied.get("error") or "").lower(),
        "V1-R0 expuso readiness de infraestructura a cliente",
    )

    admin = login_admin()
    payload = admin.get(PATH, expected=200)
    require(payload.get("schema") == "legalai_v1_release_readiness_v1", "Schema V1-R0 inesperado")
    readiness = payload.get("readiness") or {}
    require(readiness.get("platform_ready") is False, "Demo fue presentada como platform-ready real")
    require(readiness.get("payments_ready") is False, "Demo fue presentada como payments-ready real")
    require(readiness.get("commercial_ready") is False, "Demo fue presentada como commercial-ready real")
    require(readiness.get("real_production_authorized") is False, "V1-R0 cambió autorización real")
    require(readiness.get("activation_authorized") is False, "V1-R0 se autoautorizó")
    require(readiness.get("activation_state") == "BLOCKED", "V1-R0 no bloqueó activación real")

    blockers = set(payload.get("blocking") or [])
    for expected in (
        "production_profile",
        "synthetic_data_boundary_removed",
        "postgres_backend",
        "postgres_repository_evidence",
        "durable_object_storage",
        "monitoring_certified",
        "incident_response_certified",
        "independent_security_review",
        "privacy_governance_approved",
        "legal_operations_approved",
        "qa_operations_approved",
    ):
        require(expected in blockers, f"V1-R0 perdió blocker esperado: {expected}")

    evidence = payload.get("evidence_summary") or {}
    require(evidence.get("repository_evidence_complete") is False, "V1-R0 ignoró evidencia PostgreSQL ausente")
    require(
        "postgres_certification_tool" in (evidence.get("repository_evidence_missing") or []),
        "V1-R0 no detectó tools/postgres_certify.py ausente",
    )
    governance = payload.get("governance") or {}
    require(governance.get("read_only") is True, "V1-R0 no declaró naturaleza read-only")
    require(governance.get("self_authorization") is False, "V1-R0 permite autoautorización")
    require(governance.get("technical_readiness_is_legal_approval") is False, "V1-R0 confundió readiness con aprobación legal")
    require(governance.get("technical_readiness_is_qa_approval") is False, "V1-R0 confundió readiness con QA")
    require(governance.get("real_payments_are_separate") is True, "V1-R0 mezcló pagos con readiness de plataforma")

    raw = json.dumps(payload, ensure_ascii=False).lower()
    for forbidden in (
        "database_url",
        "master_key_seed",
        "legal_master_key",
        "password",
        "recovery_codes",
        "actor_id",
        "problem_statement",
        "answers",
        "@demo.legalaiz.it",
    ):
        require(forbidden not in raw, f"V1-R0 filtró dato sensible: {forbidden}")

    repeated = admin.get(PATH, expected=200)
    require(repeated.get("readiness") == payload.get("readiness"), "Readiness V1-R0 cambió tras lectura")
    require(repeated.get("blocking") == payload.get("blocking"), "Blockers V1-R0 cambiaron tras lectura")
    require(repeated.get("evidence_summary") == payload.get("evidence_summary"), "Evidencia V1-R0 cambió tras lectura")

    print(
        "V1-R0 HTTP smoke PASS · "
        f"profile={payload.get('profile')} platform_ready=false commercial_ready=false activation=BLOCKED "
        f"blockers={len(blockers)} postgres_evidence=missing admin_only=true read_only=true self_authorization=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"V1-R0 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
