import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from docx_builder import build_docx


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class M330DocxPaginationTests(unittest.TestCase):
    def test_final_signature_table_is_not_followed_by_empty_body_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "firma-final.docx"
            build_docx(
                target,
                "Documento de prueba",
                "",
                [],
                [
                    {
                        "heading": "I. CONTENIDO",
                        "paragraphs": ["Contenido sustantivo suficiente para la prueba estructural."],
                    },
                    {
                        "heading": "FIRMA",
                        "_type": "signature",
                        "parties": [
                            {"label": "PERSONA FIRMANTE", "name": "Nombre de prueba", "id": "1.000.000"}
                        ],
                    },
                ],
                append_default_control=False,
            )
            with ZipFile(target) as archive:
                root = ET.fromstring(archive.read("word/document.xml"))
            body = root.find(f"{W}body")
            children = list(body)
            self.assertEqual(children[-1].tag, f"{W}sectPr")
            self.assertEqual(children[-2].tag, f"{W}tbl")


if __name__ == "__main__":
    unittest.main()
