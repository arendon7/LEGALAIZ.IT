#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


PAGE_PATTERN = "page-*.png"


def _font(size: int):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _pages(rendered: Path, stem: str) -> list[Path]:
    folder = rendered / stem
    pages = sorted(folder.glob(PAGE_PATTERN))
    if not pages:
        raise RuntimeError(f"No existen páginas rasterizadas para {stem}.")
    return pages


def _contact_sheet(product_code: str, pages: Iterable[Path], target: Path) -> None:
    pages = list(pages)
    thumb_width = 420
    margin = 24
    header_height = 72
    captions = 34
    opened: list[Image.Image] = []
    try:
        for page in pages:
            image = Image.open(page).convert("RGB")
            ratio = thumb_width / image.width
            image = image.resize((thumb_width, max(1, int(image.height * ratio))))
            opened.append(image)
        columns = 2 if len(opened) > 1 else 1
        rows = (len(opened) + columns - 1) // columns
        row_height = max(image.height for image in opened) + captions + margin
        canvas_width = columns * thumb_width + (columns + 1) * margin
        canvas_height = header_height + rows * row_height + margin
        canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text((margin, 18), f"{product_code} · Contact sheet M32.3", font=_font(26), fill="black")
        for index, image in enumerate(opened):
            row, column = divmod(index, columns)
            x = margin + column * (thumb_width + margin)
            y = header_height + row * row_height
            canvas.paste(image, (x, y))
            draw.text((x, y + image.height + 4), f"Página {index + 1}", font=_font(18), fill="black")
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, format="PNG", optimize=True)
    finally:
        for image in opened:
            image.close()


def _markdown(packet: dict) -> str:
    lines = [
        "# Expediente de revisión M32.3 — Portafolio de 11 productos",
        "",
        "> **Estado:** preflight técnico aprobado. Revisión visual humana y revisión jurídica sustantiva pendientes. Ningún documento es candidato de liberación.",
        "",
        "## Matriz de revisión",
        "",
        "| Producto | Documento | Páginas | Preflight | Revisión visual | Revisión jurídica | Liberable |",
        "|---|---|---:|---|---|---|---|",
    ]
    for item in packet["products"]:
        lines.append(
            f"| `{item['product_code']}` | `{item['sample_name']}` | {item['page_count']} | "
            f"{item['technical_preflight']} | {item['human_visual_review']} | "
            f"{item['legal_substantive_review']} | No |"
        )
    lines.extend(
        [
            "",
            "## Instrucciones de revisión humana",
            "",
            "Cada página debe inspeccionarse en el PNG individual y en la hoja de contacto. La persona revisora debe registrar, como mínimo:",
            "",
            "1. cortes, desbordamientos, páginas en blanco o tablas fracturadas;",
            "2. encabezados huérfanos, firmas separadas o saltos de página impropios;",
            "3. legibilidad, jerarquía, numeración, consistencia tipográfica y márgenes;",
            "4. nombres, identificaciones, fechas, valores, sujetos, obligaciones y anexos;",
            "5. variables sin resolver, valores sentinela, duplicaciones o contradicciones;",
            "6. correspondencia entre el documento, su producto y el expediente sintético;",
            "7. cláusulas o conclusiones que exijan corrección jurídica antes de liberación.",
            "",
            "## Regla de cierre",
            "",
            "La inspección automatizada y el renderizado acreditan únicamente que el documento pudo generarse y representarse. La liberación requiere aprobación expresa e independiente del especialista jurídico y de QA, vinculada al hash exacto de cada archivo.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el expediente de revisión humana M32.3.")
    parser.add_argument("--portfolio", required=True, type=Path)
    parser.add_argument("--rendered", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    portfolio = json.loads(args.portfolio.read_text(encoding="utf-8"))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    products = []
    total_pages = 0

    for item in portfolio.get("products", []):
        stem = Path(item["sample_name"]).stem
        pages = _pages(args.rendered.resolve(), stem)
        page_count = len(pages)
        total_pages += page_count
        contact_name = f"{item['product_code']}_contact_sheet.png"
        _contact_sheet(item["product_code"], pages, output / "contact-sheets" / contact_name)
        products.append(
            {
                **item,
                "page_count": page_count,
                "rendered_folder": stem,
                "contact_sheet": f"contact-sheets/{contact_name}",
                "technical_preflight": "passed",
                "human_visual_review": "pending",
                "legal_substantive_review": "pending",
                "release_candidate": False,
                "legal_approval": "pending",
                "qa_approval": "pending",
            }
        )

    if len(products) != 11 or len({item["product_code"] for item in products}) != 11:
        raise RuntimeError("El expediente de revisión no contiene exactamente once productos.")
    if total_pages < 11:
        raise RuntimeError("El portafolio no produjo al menos una página por producto.")

    packet = {
        "iteration": "M32.3",
        "product_count": len(products),
        "page_count": total_pages,
        "products": products,
        "technical_preflight": "passed",
        "human_visual_review": "pending",
        "legal_substantive_review": "pending",
        "dual_approval": {"legal": "pending", "qa": "pending"},
        "release_candidate": False,
        "review_declaration": "Las hojas de contacto facilitan la inspección, pero no constituyen revisión visual humana ni aprobación jurídica.",
    }
    (output / "m32-3-review-packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "M32_3_REVIEW_PACKET.md").write_text(_markdown(packet), encoding="utf-8")
    print(json.dumps({"products": len(products), "pages": total_pages, "release_candidate": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
