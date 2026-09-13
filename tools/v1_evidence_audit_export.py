#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.audit_custody_export_v1_rc10 import (
    AuditCustodyExport,
    AuditCustodyExportError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta o verifica un bundle RC10 de custodia del audit pack redactado. "
            "No ejecuta controles, no registra evidencia, no aprueba, no ratifica y no autoriza release."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="Crear un bundle canónico inmutable.")
    export.add_argument("--output-root", required=True, help="Directorio padre para bundles RC10.")
    export.add_argument("--campaign", help="Campaign ID RC8/RC8.1 opcional.")

    verify = sub.add_parser("verify", help="Verificar integridad de un bundle RC10 existente.")
    verify.add_argument("--bundle", required=True, help="Directorio del bundle RC10.")
    verify.add_argument(
        "--expected-envelope-sha256",
        help="Digest previamente anclado fuera del bundle para comprobar correspondencia.",
    )

    args = parser.parse_args()
    try:
        custody = AuditCustodyExport(ROOT)
        if args.command == "export":
            result = custody.export(args.output_root, campaign_id=args.campaign)
        else:
            result = custody.verify(
                args.bundle,
                expected_envelope_sha256=args.expected_envelope_sha256,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except AuditCustodyExportError as exc:
        print(f"RC10 CUSTODY ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
