from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from legalai_platform.document_release_gate import (
    CANONICAL_PRODUCTS,
    M32_2_PRODUCTS,
    enforce_document_release_gate,
    install_docx_release_gate,
    manifest_path_for,
)


def _sections(product_code: str) -> list[dict]:
    return [
        {
            "heading": "1. Identificación y alcance",
            "text": (
                f"Documento demostrativo controlado del producto {product_code}. "
                "La información debe cotejarse con el expediente y los soportes aportados."
            ),
        },
        {
            "heading": "2. Solicitudes y evidencia",
            "bullets": [
                "Verificar identidad, competencia, fechas y destinatario.",
                "Conservar los soportes y la constancia de radicación.",
                "No afirmar consecuencias automáticas sin revisión del caso.",
            ],
        },
        {
            "heading": "CONTROL DE USO",
            "_type": "control",
            "text": "Borrador sujeto a revisión jurídica, QA y aprobación dual antes de liberación.",
        },
    ]


class M322DocumentReleaseGateTests(unittest.TestCase):
    def test_catalogo_canonico_y_ola_m32_2_completos(self):
        self.assertEqual(len(CANONICAL_PRODUCTS), 11)
        self.assertEqual(
            M32_2_PRODUCTS,
            {
                "CO-TR-001",
                "CO-TR-002",
                "CO-SA-001",
                "CO-CD-001",
                "CO-CD-003",
                "CO-CD-004",
            },
        )
        self.assertLess(M32_2_PRODUCTS, CANONICAL_PRODUCTS)

    def test_builder_instalado_genera_manifiesto_pendiente_de_aprobacion(self):
        install_docx_release_gate()
        from docx_builder import build_docx

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for product_code in sorted(M32_2_PRODUCTS):
                with self.subTest(product_code=product_code):
                    target = root / f"{product_code}_M32_2_muestra.docx"
                    build_docx(
                        target,
                        f"Muestra controlada {product_code}",
                        "Preflight transversal M32.2",
                        [("Producto", product_code), ("Estado", "Borrador controlado")],
                        _sections(product_code),
                    )

                    sidecar = manifest_path_for(target)
                    self.assertTrue(target.is_file())
                    self.assertTrue(sidecar.is_file())
                    payload = json.loads(sidecar.read_text(encoding="utf-8"))
                    self.assertEqual(payload["product_code"], product_code)
                    self.assertTrue(payload["quality"]["valid"])
                    self.assertTrue(payload["visual_preflight"]["valid"])
                    self.assertEqual(payload["approval_state"], {"legal": "pending", "qa": "pending"})
                    self.assertTrue(payload["requires_human_visual_review"])
                    self.assertEqual(payload["release_status"], "preflight_passed_pending_dual_approval")
                    self.assertEqual(len(payload["sha256"]), 64)

    def test_compuerta_bloquea_un_archivo_que_no_es_docx(self):
        with TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "CO-TR-001_archivo_invalido.docx"
            invalid.write_text("esto no es un paquete OOXML", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Control de calidad DOCX fallido"):
                enforce_document_release_gate(invalid, expected_product="CO-TR-001")


if __name__ == "__main__":
    unittest.main()
