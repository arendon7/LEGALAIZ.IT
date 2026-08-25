#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.private_assignment_packets_v1 import (
    PrivateAssignmentError,
    PrivateAssignmentPacketGenerator,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida asignaciones humanas y genera paquetes locales privados OPS3. "
            "No registra evidencia, no modifica campañas y no autoriza release."
        )
    )
    parser.add_argument(
        "--ledger-path",
        default=None,
        help="Ruta local opcional al ledger RC8.1. No se imprime ni modifica.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validar archivo privado sin escribir paquetes.")
    validate.add_argument("--assignments", required=True)

    write = sub.add_parser("write", help="Generar paquetes privados con permisos restrictivos.")
    write.add_argument("--assignments", required=True)
    write.add_argument("--output-dir", required=True)

    args = parser.parse_args()
    generator = PrivateAssignmentPacketGenerator(ROOT, ledger_path=args.ledger_path)
    try:
        if args.command == "validate":
            validated = generator.validate(args.assignments)
            print(json.dumps(
                generator.public_validation_summary(validated),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ))
            return 0

        result = generator.write(args.assignments, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except PrivateAssignmentError as exc:
        # El error puede referir controles/roles, pero nunca se imprime el payload privado.
        print(f"OPS3 ASSIGNMENT ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
