#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


BLANK_DARK_RATIO = 0.002
SPARSE_DARK_RATIO = 0.020


def inspect_page(path: Path) -> dict:
    """Mide tinta sustantiva ignorando encabezado, pie y márgenes exteriores."""
    with Image.open(path) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        crop = grayscale.crop(
            (
                int(width * 0.05),
                int(height * 0.06),
                int(width * 0.95),
                int(height * 0.90),
            )
        )
        histogram = crop.histogram()
        total = max(1, crop.width * crop.height)
        dark_pixels = sum(histogram[:220])
        dark_ratio = dark_pixels / total
    return {
        "file": str(path),
        "dark_ratio": round(dark_ratio, 8),
        "blank": dark_ratio < BLANK_DARK_RATIO,
        "sparse": BLANK_DARK_RATIO <= dark_ratio < SPARSE_DARK_RATIO,
    }


def inspect_rendered_root(root: Path) -> dict:
    pages = sorted(root.glob("*/page-*.png"))
    if not pages:
        raise RuntimeError(f"No se encontraron páginas PNG en {root}.")
    reports = [inspect_page(path) for path in pages]
    return {
        "page_count": len(reports),
        "blank_pages": [item for item in reports if item["blank"]],
        "sparse_pages": [item for item in reports if item["sparse"]],
        "pages": reports,
        "valid": not any(item["blank"] for item in reports),
        "thresholds": {
            "blank_dark_ratio": BLANK_DARK_RATIO,
            "sparse_dark_ratio": SPARSE_DARK_RATIO,
        },
        "declaration": (
            "La medición automática bloquea páginas sin contenido sustantivo; "
            "las páginas dispersas siguen requiriendo inspección visual humana."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detecta páginas vacías y dispersas en el render M32.3.")
    parser.add_argument("--rendered", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = inspect_rendered_root(args.rendered.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "page_count": report["page_count"],
        "blank_pages": len(report["blank_pages"]),
        "sparse_pages": len(report["sparse_pages"]),
        "valid": report["valid"],
    }, ensure_ascii=False))
    if not report["valid"]:
        names = ", ".join(Path(item["file"]).name for item in report["blank_pages"])
        raise SystemExit(f"Render M32.3 bloqueado por páginas vacías: {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
