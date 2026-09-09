#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legalai_platform.evidence_execution_board_v1 import (
    EvidenceOperationsBoard,
    EvidenceOperationsBoardError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compone una mesa operativa read-only desde OPS1 + RC8.1. "
            "No ejecuta, no registra evidencia y no autoriza release."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Mostrar el tablero derivado por stdout.")
    show.add_argument("--campaign", default=None)
    show.add_argument("--format", choices=("json", "markdown"), default="markdown")

    write = sub.add_parser("write", help="Escribir JSON y Markdown derivados en un directorio de trabajo.")
    write.add_argument("--campaign", default=None)
    write.add_argument("--output-dir", required=True)

    args = parser.parse_args()
    try:
        board = EvidenceOperationsBoard(ROOT, campaign_id=args.campaign)
        payload = board.build()
        markdown = board.to_markdown(payload)
        if args.command == "show":
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(markdown)
            return 0

        output_dir = Path(args.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "v1-evidence-operations-board.json"
        md_path = output_dir / "v1-evidence-operations-board.md"
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        print(json.dumps({
            "schema": "legalaiz-v1-ops2-board-export-v1",
            "json": str(json_path),
            "markdown": str(md_path),
            "mode": payload["mode"],
            "controls": payload["summary"]["total_controls"],
            "verified": payload["summary"]["verified_controls"],
            "board_sha256": payload["board_sha256"],
            "campaign_changed": False,
            "evidence_changed": False,
            "authorization_changed": False,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except EvidenceOperationsBoardError as exc:
        print(f"OPS2 BOARD ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
