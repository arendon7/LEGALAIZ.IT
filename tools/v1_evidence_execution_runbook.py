#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.evidence_execution_runbook_v1 import (
    EvidenceExecutionRunbook,
    EvidenceExecutionRunbookError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compone el runbook humano de ejecución de los 22 controles V1 desde RC6/RC8.1. "
            "No ejecuta controles, no registra evidencia y no autoriza release."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Mostrar el runbook derivado por stdout.")
    show.add_argument("--format", choices=("json", "markdown"), default="markdown")

    write = sub.add_parser("write", help="Escribir JSON y Markdown derivados en un directorio de trabajo.")
    write.add_argument("--output-dir", required=True)

    args = parser.parse_args()
    try:
        runbook = EvidenceExecutionRunbook(ROOT)
        payload = runbook.build()
        markdown = runbook.to_markdown(payload)
        if args.command == "show":
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(markdown)
            return 0

        output_dir = Path(args.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "v1-real-evidence-runbook.json"
        md_path = output_dir / "v1-real-evidence-runbook.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        print(json.dumps({
            "schema": "legalaiz-v1-ops1-runbook-export-v1",
            "json": str(json_path),
            "markdown": str(md_path),
            "controls": payload["controls"],
            "waves": len(payload["waves"]),
            "runbook_sha256": payload["runbook_sha256"],
            "execution_changed": False,
            "authorization_changed": False,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except EvidenceExecutionRunbookError as exc:
        print(f"OPS1 RUNBOOK ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
