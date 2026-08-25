#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.evidence_audit_pack_v1_rc9 import EvidenceAuditPack, EvidenceAuditPackError


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Genera un snapshot V1 read-only de evidencia, campaña y procedencia de autorización. "
            "No ejecuta controles, no registra evidencia y no autoriza producción ni pagos."
        )
    )
    parser.add_argument("--campaign", help="Campaign ID RC8/RC8.1 a vincular al snapshot.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Formato de salida por stdout.",
    )
    args = parser.parse_args()

    try:
        audit = EvidenceAuditPack(ROOT)
        pack = audit.build(campaign_id=args.campaign)
        if args.format == "markdown":
            print(audit.to_markdown(pack))
        else:
            print(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True))
    except EvidenceAuditPackError as exc:
        print(f"RC9 AUDIT PACK ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
