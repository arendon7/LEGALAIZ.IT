from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def substantive_pixels(path: Path) -> int:
    """Cuenta píxeles no blancos en el cuerpo, excluyendo cabecera y pie."""
    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        body = gray.crop(
            (
                int(width * 0.08),
                int(height * 0.14),
                int(width * 0.92),
                int(height * 0.86),
            )
        )
        histogram = body.histogram()
        return sum(histogram[:250])


def main(root: str) -> int:
    rendered = Path(root)
    pages = sorted(rendered.rglob("page-*.png"))
    if not pages:
        raise SystemExit("No se encontraron páginas rasterizadas para inspección.")

    blank = []
    for page in pages:
        if substantive_pixels(page) < 20:
            blank.append(page.relative_to(rendered).as_posix())

    if blank:
        print("Páginas sin contenido sustantivo detectadas:", file=sys.stderr)
        for page in blank:
            print(f"- {page}", file=sys.stderr)
        return 1

    print(f"QA visual de páginas: {len(pages)} páginas con contenido corporal detectable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
