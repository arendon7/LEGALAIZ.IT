#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")
SIGNATURE_RE = re.compile(r"\bFIRMAS?\b", re.IGNORECASE)
DEFAULT_MAX_WORDS = 42


def _pdf_pages(path: Path) -> int:
    process = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    match = re.search(r"^Pages:\s+(\d+)\s*$", process.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError(f"No fue posible determinar el número de páginas de {path}")
    return int(match.group(1))


def _last_page_text(path: Path, page: int) -> str:
    process = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    return process.stdout


def audit_sparse_signature_tails(rendered: Path, *, max_words: int = DEFAULT_MAX_WORDS) -> dict:
    rendered = rendered.resolve()
    findings: list[dict] = []
    checked = 0
    multi_page = 0
    signature_tails = 0

    pdfs = sorted(rendered.rglob("*_M33_0.pdf"))
    for pdf in pdfs:
        checked += 1
        pages = _pdf_pages(pdf)
        if pages <= 1:
            continue
        multi_page += 1
        text = _last_page_text(pdf, pages)
        if not SIGNATURE_RE.search(text):
            continue
        signature_tails += 1
        words = WORD_RE.findall(text)
        word_count = len(words)
        if word_count <= max_words:
            findings.append({
                "document": pdf.relative_to(rendered).as_posix(),
                "page": pages,
                "word_count": word_count,
                "threshold": max_words,
                "excerpt": " ".join(words[:28]),
            })

    return {
        "schema": "legalaizit-m33-2-sparse-signature-tail-audit-v1",
        "checked_documents": checked,
        "multi_page_documents": multi_page,
        "signature_last_pages": signature_tails,
        "max_words": max_words,
        "findings": findings,
        "ok": not findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detecta páginas finales M33.2 dedicadas casi exclusivamente a firma."
    )
    parser.add_argument("rendered", type=Path)
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit_sparse_signature_tails(args.rendered, max_words=args.max_words)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "checked_documents": report["checked_documents"],
        "multi_page_documents": report["multi_page_documents"],
        "signature_last_pages": report["signature_last_pages"],
        "max_words": report["max_words"],
        "findings": len(report["findings"]),
        "ok": report["ok"],
    }, ensure_ascii=False))
    if report["findings"]:
        for finding in report["findings"]:
            print(
                f"ERROR: {finding['document']} página {finding['page']} "
                f"tiene solo {finding['word_count']} palabras visibles con firma",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
