from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from scripts.build_m32_3_review_packet import _contact_sheet, _markdown
from scripts.generate_m32_3_full_portfolio import CANONICAL_PRODUCTS, PRIMARY_DOCUMENT_IDS, TRANSVERSAL_KINDS


class M323FullPortfolioTests(unittest.TestCase):
    def test_catalogo_contiene_once_productos_sin_duplicados(self):
        self.assertEqual(len(CANONICAL_PRODUCTS), 11)
        self.assertEqual(len(set(CANONICAL_PRODUCTS)), 11)
        self.assertEqual(set(TRANSVERSAL_KINDS) | set(PRIMARY_DOCUMENT_IDS), set(CANONICAL_PRODUCTS))
        self.assertFalse(set(TRANSVERSAL_KINDS) & set(PRIMARY_DOCUMENT_IDS))

    def test_matriz_de_revision_nunca_presenta_liberacion_automatica(self):
        packet = {
            "products": [
                {
                    "product_code": code,
                    "sample_name": f"{code}_M32_3.docx",
                    "page_count": 1,
                    "technical_preflight": "passed",
                    "human_visual_review": "pending",
                    "legal_substantive_review": "pending",
                }
                for code in CANONICAL_PRODUCTS
            ]
        }
        markdown = _markdown(packet)
        self.assertIn("Ningún documento es candidato de liberación", markdown)
        self.assertEqual(markdown.count("| No |"), 11)
        self.assertNotIn("aprobación automática", markdown.casefold())

    def test_hoja_de_contacto_se_construye_sin_alterar_paginas_fuente(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            pages = []
            for index in range(3):
                path = root / f"page-{index + 1}.png"
                Image.new("RGB", (600, 900), "white").save(path)
                pages.append(path)
            target = root / "contact.png"
            _contact_sheet("CO-TR-001", pages, target)
            self.assertTrue(target.is_file())
            with Image.open(target) as image:
                self.assertGreater(image.width, 420)
                self.assertGreater(image.height, 900)
            self.assertTrue(all(path.is_file() for path in pages))


if __name__ == "__main__":
    unittest.main()
