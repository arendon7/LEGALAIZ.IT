#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.evidence_orchestration_v1_rc8_1 import (
    EvidenceAuditDossier,
    EvidenceCampaignError,
    EvidenceCampaignLedger,
)


def _actor(args: argparse.Namespace) -> dict[str, str]:
    return {"id": args.actor_id, "role": args.actor_role}


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Coordina campañas V1 de evidencia externa. No ejecuta controles, no aprueba evidencia y no autoriza producción."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Crear campaña fijando plan, revisión fuente y fingerprint opaco del entorno.")
    create.add_argument("--environment-fingerprint", required=True)
    create.add_argument("--source-revision", required=True)
    create.add_argument("--actor-id", required=True)
    create.add_argument("--actor-role", required=True)

    status = sub.add_parser("status", help="Mostrar estado derivado de una campaña.")
    status.add_argument("--campaign", required=True)

    packet = sub.add_parser("packet", help="Generar task packet seguro de un control canónico.")
    packet.add_argument("--control", required=True)

    audit = sub.add_parser("audit", help="Componer dossier de auditoría de los 22 controles.")
    audit.add_argument("--campaign")

    start = sub.add_parser("start-control", help="Registrar inicio de coordinación; no ejecuta el control.")
    start.add_argument("--campaign", required=True)
    start.add_argument("--control", required=True)
    start.add_argument("--actor-id", required=True)
    start.add_argument("--actor-role", required=True)

    link = sub.add_parser("link-evidence", help="Vincular una evidencia ya registrada en el dossier canónico.")
    link.add_argument("--campaign", required=True)
    link.add_argument("--control", required=True)
    link.add_argument("--evidence-event-id", required=True)
    link.add_argument("--actor-id", required=True)
    link.add_argument("--actor-role", required=True)

    review = sub.add_parser("review-ready", help="Registrar que coordinación entregó evidencia a revisión; no aprueba.")
    review.add_argument("--campaign", required=True)
    review.add_argument("--control", required=True)
    review.add_argument("--actor-id", required=True)
    review.add_argument("--actor-role", required=True)

    block = sub.add_parser("block-control", help="Registrar bloqueo operativo de un control.")
    block.add_argument("--campaign", required=True)
    block.add_argument("--control", required=True)
    block.add_argument("--reason-code", required=True)
    block.add_argument("--actor-id", required=True)
    block.add_argument("--actor-role", required=True)

    abort = sub.add_parser("abort", help="Abortar campaña sin modificar evidencia ni autorización.")
    abort.add_argument("--campaign", required=True)
    abort.add_argument("--reason-code", required=True)
    abort.add_argument("--actor-id", required=True)
    abort.add_argument("--actor-role", required=True)

    args = parser.parse_args()
    try:
        ledger = EvidenceCampaignLedger(ROOT)
        if args.command == "create":
            event = ledger.create_campaign(
                environment_fingerprint=args.environment_fingerprint,
                source_revision=args.source_revision,
                actor=_actor(args),
            )
            _print(event)
        elif args.command == "status":
            _print(ledger.campaign_state(args.campaign))
        elif args.command == "packet":
            _print(ledger.task_packet(args.control))
        elif args.command == "audit":
            _print(EvidenceAuditDossier(ROOT, campaign_ledger=ledger).build(campaign_id=args.campaign))
        elif args.command == "start-control":
            _print(ledger.start_control(args.campaign, args.control, actor=_actor(args)))
        elif args.command == "link-evidence":
            _print(ledger.link_evidence(
                args.campaign,
                args.control,
                args.evidence_event_id,
                actor=_actor(args),
            ))
        elif args.command == "review-ready":
            _print(ledger.mark_review_ready(args.campaign, args.control, actor=_actor(args)))
        elif args.command == "block-control":
            _print(ledger.block_control(
                args.campaign,
                args.control,
                reason_code=args.reason_code,
                actor=_actor(args),
            ))
        elif args.command == "abort":
            _print(ledger.abort_campaign(args.campaign, reason_code=args.reason_code, actor=_actor(args)))
        else:
            parser.error("Comando RC8.1 desconocido.")
    except EvidenceCampaignError as exc:
        print(f"RC8.1 CAMPAIGN ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
