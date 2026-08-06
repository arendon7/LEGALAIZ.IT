from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from legalai_platform.document_release_gate import normalize_semantic_sections
from scripts.build_m32_3_review_packet import _contact_sheet, _markdown
from scripts.generate_m32_3_full_portfolio import CANONICAL_PRODUCTS, PRIMARY_DOCUMENT_IDS, TRANSVERSAL_KINDS
from scripts.generate_m32_3_full_portfolio import _services_answers
from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244


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

    def test_tasas_cero_no_se_presentan_como_conclusion_si_no_fueron_calculadas(self):
        sections = [
            {
                "heading": "5. Saldo e intereses",
                "table": [
                    ("Concepto", "Valor"),
                    ("Modalidad", "Intereses no calculados: tasa y período sujetos a validación"),
                    ("Tasa equivalente E.A.", "0.0000%"),
                    ("IBC vigente", "0.00% E.A."),
                    ("Límite de referencia", "0.00% E.A."),
                ],
            }
        ]
        normalized, adjustments = normalize_semantic_sections("CO-CD-004", sections)
        values = {row[0]: row[1] for row in normalized[0]["table"]}
        self.assertEqual(values["Tasa equivalente E.A."], "Pendiente de verificación")
        self.assertEqual(values["IBC vigente"], "Pendiente de verificación")
        self.assertEqual(values["Límite de referencia"], "Pendiente de verificación")
        self.assertEqual(len(adjustments), 3)
        self.assertEqual(sections[0]["table"][2][1], "0.0000%")  # no muta la entrada

    def test_tasa_validada_distinta_de_cero_no_se_reescribe(self):
        sections = [
            {
                "heading": "5. Saldo e intereses",
                "table": [
                    ("Modalidad", "Interés remuneratorio validado"),
                    ("Tasa equivalente E.A.", "18.50%"),
                    ("IBC vigente", "17.20% E.A."),
                    ("Límite de referencia", "25.80% E.A."),
                ],
            }
        ]
        normalized, adjustments = normalize_semantic_sections("CO-CD-004", sections)
        self.assertEqual(normalized, sections)
        self.assertEqual(adjustments, [])

    def test_normalizacion_servicios_no_filtra_diccionarios_ni_infinitivos_duplicados(self):
        normalized = CoEm003DocumentFactoryV244._normalize_answers(_services_answers())
        self.assertEqual(
            normalized["service"]["object"],
            "servicios independientes de diagnóstico, diseño y mejora de procesos documentales y tecnológicos",
        )
        self.assertEqual(
            normalized["service"]["expected_result"],
            "una arquitectura documentada, matrices de control, configuración funcional y evidencia de pruebas",
        )
        self.assertIsInstance(normalized["schedule"], str)
        self.assertIsInstance(normalized["termination"], str)
        self.assertIsInstance(normalized["closure"], str)
        self.assertEqual(normalized["fees"]["financial_terms"]["amount"], 48000000)
        self.assertEqual(normalized["term"]["start_date"], "2026-08-15")
        self.assertNotIn("Rules:", normalized["termination"])
        self.assertNotIn("Transición:", normalized["closure"])


if __name__ == "__main__":
    unittest.main()
