#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.private_execution_dispatch_guard_v1 import (
    PrivateDispatchGuardError,
    PrivateExecutionDispatchGuard,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight y materialización privada de paquetes OPS3 listos para ejecución. "
            "No envía archivos, no ejecuta controles y no muta campañas/evidencia/autorización."
        )
    )
    parser.add_argument(
        "--ledger-path",
        default=None,
        help="Ruta local opcional al ledger RC8.1; se lee pero nunca se modifica.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Validar vigencia y calcular controles despachables.")
    preflight.add_argument("--pack-dir", required=True)

    write = sub.add_parser("write", help="Copiar sólo paquetes READY_TO_EXECUTE a un despacho privado.")
    write.add_argument("--pack-dir", required=True)
    write.add_argument("--output-dir", required=True)

    args = parser.parse_args()
    guard = PrivateExecutionDispatchGuard(ROOT, ledger_path=args.ledger_path)
    try:
        if args.command == "preflight":
            result = guard.preflight(args.pack_dir)
        else:
            result = guard.write(args.pack_dir, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except PrivateDispatchGuardError as exc:
        print(f"OPS4 DISPATCH ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
