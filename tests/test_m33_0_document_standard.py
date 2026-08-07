from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx import Document

from document_standard_v33 import (
    STANDARD_VERSION,
    audit_docx_legal_standard,
    validate_rendered_sections,
)
from docx_builder import build_docx
from factory_backend import DocumentFactory


class DocumentStandardM330Tests(unittest.TestCase):
    def _sections(self):
        return [
            {
                "heading": "PRIMERA: OBJETO Y ALCANCE",
                "_type": "clause",
                "paragraphs": [
                    "La parte obligada ejecutará las prestaciones expresamente definidas en este documento, con la diligencia profesional exigible, dentro del alcance material acordado y atendiendo las dependencias que hayan sido identificadas por las partes.",
                    "La obligación comprende la entrega de los resultados descritos, la conservación de soportes suficientes y la advertencia oportuna de circunstancias que puedan afectar el cumplimiento, sin extender el alcance a actividades que no hayan sido incorporadas mediante el mecanismo de cambios aplicable.",
                ],
            },
            {
                "heading": "ANEXO No. 1 — MATRIZ DE RESPONSABILIDADES",
                "_type": "annex",
                "page_break_before": True,
                "table": [
                    ["Actividad", "Responsable"],
                    ["Entrega de información", "Parte contratante"],
                    ["Preparación del resultado", "Parte contratista"],
                ],
            },
            {
                "heading": "FIRMAS",
                "_type": "signature",
                "parties": [
                    {
                        "label": "LA CONTRATANTE",
                        "name": "EMPRESA DEMOSTRATIVA S.A.S.",
                        "role": "Representante legal",
                        "id": "NIT 900.000.001-1",
                        "email": "contratos@example.test",
                    },
                    {
                        "label": "EL CONTRATISTA",
                        "name": "JUAN DEMOSTRATIVO",
                        "id": "C.C. 1.000.000.001",
                        "email": "contratista@example.test",
                    },
                ],
            },
            {
                "heading": "CONTROL DE USO",
                "_type": "control",
                "text": "Documento candidato sujeto a aprobación jurídica y QA sobre la revisión exacta antes de su firma o publicación.",
            },
        ]

    def test_semantic_gate_accepts_deep_clause_annex_and_signature(self):
        report = validate_rendered_sections(self._sections(), product_code="CO-EM-003")
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["standard"], STANDARD_VERSION)
        self.assertEqual(report["metrics"]["clauses"], 1)
        self.assertEqual(report["metrics"]["annexes"], 1)
        self.assertEqual(report["metrics"]["signature_sections"], 1)
        self.assertGreater(report["metrics"]["words"], 70)

    def test_semantic_gate_blocks_unresolved_sentinels_and_manual_lines(self):
        sections = [
            {
                "heading": "PRIMERA: OBJETO",
                "_type": "clause",
                "text": "El objeto será [OBJETO PENDIENTE] y deberá verificarse antes de firma. ________",
            },
            {"heading": "CONTROL DE USO", "_type": "control", "text": "Borrador."},
        ]
        report = validate_rendered_sections(sections, product_code="CO-EM-003")
        self.assertFalse(report["valid"])
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("UNRESOLVED-SENTINEL", codes)
        self.assertIn("DECORATIVE-SEPARATOR", codes)

    def test_thin_clause_is_warning_not_error(self):
        sections = [
            {"heading": "PRIMERA: PLAZO", "_type": "clause", "text": "El plazo será el acordado por las partes."},
            {"heading": "CONTROL DE USO", "_type": "control", "text": "Borrador sujeto a revisión."},
        ]
        report = validate_rendered_sections(sections)
        self.assertTrue(report["valid"])
        self.assertIn("THIN-CLAUSE", {item["code"] for item in report["warnings"]})

    def test_strict_docx_uses_approved_legal_format_without_signature_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contrato_m33.docx"
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
            # Debe ser abrible por python-docx como control adicional de compatibilidad Word.
            document = Document(path)
            self.assertGreater(len(document.paragraphs), 1)

            report = audit_docx_legal_standard(path)
            self.assertTrue(report["valid"], report["findings"])
            with ZipFile(path) as archive:
                styles = archive.read("word/styles.xml").decode("utf-8")
                body = archive.read("word/document.xml").decode("utf-8")
                footer = archive.read("word/footer1.xml").decode("utf-8")
            self.assertIn("Times New Roman", styles)
            self.assertNotIn("Arial", styles)
            self.assertIn('w:top="1417" w:right="1417" w:bottom="1417" w:left="1417"', body)
            self.assertIn('w:line="276"', body)
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
            "subtitle": "M33.0",
            "version_label": "M33.0",
            "variables": [
                {"id": "client", "type": "text"},
                {"id": "contractor", "type": "text"},
            ],
            "blocks": [
                {
                    "id": "clause-object",
                    "type": "clause",
                    "heading": "PRIMERA: OBJETO",
                    "paragraphs": [
                        "{{client}} contrata a {{contractor}} para ejecutar el objeto acordado con la diligencia profesional exigible y conforme al alcance documentado por las partes.",
                        "La ejecución deberá conservar evidencia suficiente de entregas, observaciones, correcciones y aceptaciones, sin extender el alcance a actividades no acordadas.",
                    ],
                    "numbered": ["Entregar el resultado.", "Atender observaciones procedentes."],
                },
                {
                    "id": "annex-one",
                    "type": "annex",
                    "heading": "ANEXO No. 1 — ALCANCE",
                    "page_break_before": True,
                    "table": [["Parte", "Nombre"], ["Cliente", "{{client}}"], ["Contratista", "{{contractor}}"]],
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
        clause = rendered["sections"][0]
        annex = rendered["sections"][1]
        signature = rendered["sections"][2]
        self.assertEqual(clause["paragraphs"][0].split()[0], "Cliente")
        self.assertEqual(len(clause["numbered"]), 2)
        self.assertTrue(annex["page_break_before"])
        self.assertEqual(signature["parties"][0]["name"], "Cliente Demo S.A.S.")
        self.assertEqual(signature["parties"][1]["name"], "Contratista Demo")


if __name__ == "__main__":
    unittest.main()
