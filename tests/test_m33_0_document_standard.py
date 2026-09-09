from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx import Document

from document_standard_v33 import STANDARD_VERSION, audit_docx_legal_standard, validate_rendered_sections
from docx_builder import build_docx
from factory_backend import DocumentFactory


class DocumentStandardM33Tests(unittest.TestCase):
    def _sections(self):
        return [
            {
                "heading": "PRIMERA: OBJETO Y ALCANCE",
                "_type": "clause",
                "paragraphs": [
                    "La parte obligada ejecutará las prestaciones definidas en este documento con la diligencia profesional exigible, dentro del alcance material acordado y atendiendo las dependencias identificadas por las partes.",
                    "La obligación comprende la entrega de resultados, la conservación de soportes suficientes y la advertencia oportuna de circunstancias que puedan afectar el cumplimiento, sin extender el alcance a actividades no incorporadas mediante el mecanismo de cambios aplicable.",
                ],
            },
            {
                "heading": "ANEXO No. 1 — MATRIZ DE RESPONSABILIDADES",
                "_type": "annex",
                "page_break_before": True,
                "table": [["Actividad", "Responsable"], ["Entrega", "Parte contratante"]],
            },
            {
                "heading": "FIRMAS",
                "_type": "signature",
                "parties": [
                    {"label": "LA CONTRATANTE", "name": "EMPRESA DEMOSTRATIVA S.A.S."},
                    {"label": "EL CONTRATISTA", "name": "JUAN DEMOSTRATIVO"},
                ],
            },
            {"heading": "CONTROL DE USO", "_type": "control", "text": "Documento sujeto a revisión jurídica y QA."},
        ]

    def test_semantic_gate_accepts_deep_clause_annex_and_signature(self):
        report = validate_rendered_sections(self._sections(), product_code="CO-EM-003")
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["standard"], STANDARD_VERSION)
        self.assertEqual(report["metrics"]["clauses"], 1)
        self.assertEqual(report["metrics"]["annexes"], 1)
        self.assertEqual(report["metrics"]["signature_sections"], 1)

    def test_semantic_gate_blocks_sentinels_and_manual_lines(self):
        report = validate_rendered_sections([
            {"heading": "PRIMERA: OBJETO", "_type": "clause", "text": "Objeto [OBJETO PENDIENTE]. ________"},
            {"heading": "CONTROL DE USO", "_type": "control", "text": "Borrador."},
        ])
        self.assertFalse(report["valid"])
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("UNRESOLVED-SENTINEL", codes)
        self.assertIn("DECORATIVE-SEPARATOR", codes)

    def test_thin_clause_is_warning_not_error(self):
        report = validate_rendered_sections([
            {"heading": "PRIMERA: PLAZO", "_type": "clause", "text": "El plazo será el acordado."},
            {"heading": "CONTROL DE USO", "_type": "control", "text": "Borrador."},
        ])
        self.assertTrue(report["valid"])
        self.assertIn("THIN-CLAUSE", {item["code"] for item in report["warnings"]})

    def test_strict_docx_uses_book_antiqua_and_compact_legal_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contrato_m33_2.docx"
            build_docx(
                path,
                "CONTRATO DE PRESTACIÓN DE SERVICIOS",
                "Documento demostrativo controlado",
                [("Expediente", "DEMO-M33")],
                self._sections(),
                enforce_legal_standard=True,
                product_code="CO-EM-003",
            )
            self.assertTrue(path.is_file())
            self.assertGreater(len(Document(path).paragraphs), 1)
            report = audit_docx_legal_standard(path)
            self.assertTrue(report["valid"], report["findings"])
            with ZipFile(path) as archive:
                styles = archive.read("word/styles.xml").decode("utf-8")
                body = archive.read("word/document.xml").decode("utf-8")
                footer = archive.read("word/footer1.xml").decode("utf-8")
            self.assertIn("Book Antiqua", styles)
            self.assertNotIn("Times New Roman", styles)
            self.assertNotIn("Arial", styles)
            self.assertIn('w:sz w:val="22"', styles)
            self.assertIn('w:top="1417" w:right="1417" w:bottom="1417" w:left="1417"', body)
            self.assertIn('w:line="240"', body)
            self.assertIn('w:jc w:val="both"', body)
            self.assertIn('w:tblDescription w:val="LegalAIZ-SignatureTable"', body)
            self.assertNotIn("________", body)
            self.assertIn("PAGE", footer)
            self.assertIn("NUMPAGES", footer)

    def test_strict_builder_refuses_unresolved_final_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blocked.docx"
            with self.assertRaises(ValueError):
                build_docx(
                    path,
                    "CONTRATO",
                    "",
                    [],
                    [
                        {"heading": "PRIMERA: OBJETO", "_type": "clause", "text": "Objeto: [OBJETO PENDIENTE]."},
                        {"heading": "CONTROL DE USO", "_type": "control", "text": "Borrador."},
                    ],
                    enforce_legal_standard=True,
                    product_code="CO-EM-003",
                )
            self.assertFalse(path.exists())

    def test_factory_renders_rich_blocks_without_breaking_legacy_schema(self):
        factory = DocumentFactory(
            templates=[],
            products=[{"code": "CO-EM-003"}],
            interviews=[],
            sources={"CO-EM-003": []},
            eval_conditions=lambda condition, answers: True,
        )
        content = {
            "template_id": "TPL-M33-DEMO",
            "product_code": "CO-EM-003",
            "kind": "contract",
            "title": "CONTRATO {{client}}",
            "version_label": "M33.2",
            "variables": [{"id": "client", "type": "text"}, {"id": "contractor", "type": "text"}],
            "blocks": [
                {
                    "id": "clause-object",
                    "type": "clause",
                    "heading": "PRIMERA: OBJETO",
                    "paragraphs": [
                        "{{client}} contrata a {{contractor}} para ejecutar el objeto acordado con diligencia profesional.",
                        "La ejecución conservará evidencia suficiente de entregas y aceptaciones.",
                    ],
                    "numbered": ["Entregar el resultado.", "Atender observaciones procedentes."],
                },
                {
                    "id": "signature",
                    "type": "signature",
                    "heading": "FIRMAS",
                    "parties": [
                        {"label": "LA CONTRATANTE", "name": "{{client}}"},
                        {"label": "EL CONTRATISTA", "name": "{{contractor}}"},
                    ],
                },
                {"id": "control", "type": "control", "heading": "CONTROL DE USO", "text": "Sujeto a revisión humana."},
            ],
        }
        validation = factory.validate("TPL-M33-DEMO", content)
        self.assertTrue(validation["valid"], validation["errors"])
        rendered = factory.render(content, {"client": "Cliente Demo S.A.S.", "contractor": "Contratista Demo"})
        self.assertEqual(rendered["sections"][0]["paragraphs"][0].split()[0], "Cliente")
        self.assertEqual(rendered["sections"][1]["parties"][1]["name"], "Contratista Demo")


if __name__ == "__main__":
    unittest.main()
