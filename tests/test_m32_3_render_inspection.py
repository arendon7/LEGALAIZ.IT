from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image, ImageDraw

from scripts.inspect_m32_3_rendered_pages import inspect_page, inspect_rendered_root


class M323RenderInspectionTests(unittest.TestCase):
    def test_pagina_sin_contenido_sustantivo_es_bloqueante(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "page-1.png"
            Image.new("RGB", (1200, 1600), "white").save(path)
            report = inspect_page(path)
            self.assertTrue(report["blank"])
            self.assertFalse(report["sparse"])

    def test_pagina_con_texto_no_es_vacia(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "page-1.png"
            image = Image.new("RGB", (1200, 1600), "white")
            draw = ImageDraw.Draw(image)
            for row in range(20):
                y = 180 + row * 45
                draw.rectangle((120, y, 1040, y + 12), fill="black")
            image.save(path)
            report = inspect_page(path)
            self.assertFalse(report["blank"])

    def test_raiz_invalida_si_contiene_una_pagina_vacia(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "documento"
            folder.mkdir()
            Image.new("RGB", (1200, 1600), "white").save(folder / "page-1.png")
            image = Image.new("RGB", (1200, 1600), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((120, 200, 1040, 1200), fill="black")
            image.save(folder / "page-2.png")
            report = inspect_rendered_root(root)
            self.assertFalse(report["valid"])
            self.assertEqual(len(report["blank_pages"]), 1)
            self.assertEqual(report["page_count"], 2)


if __name__ == "__main__":
    unittest.main()
