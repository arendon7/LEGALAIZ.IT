from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from scripts.generate_m33_0_procedural_samples import _visible_metadata
from tests.test_m33_0_procedural_wave import PRODUCTS, habeas_fixture


class HabeasClientPresentationM330Tests(unittest.TestCase):
    def _specs(self) -> list[dict]:
        answers, result = habeas_fixture()
        return document_specs_m33_all(
            "CASE-M33-HABEAS-CLIENT",
            "CO-CD-001",
            answers,
            result,
            PRODUCTS["CO-CD-001"],
            "2026-08-08T09:00:00-05:00",
            [],
        )

    def test_client_subtitle_contains_no_internal_product_or_release_jargon(self):
        specs = [spec for spec in self._specs() if spec.get("internal_controls_externalized")]
        self.assertEqual(len(specs), 7)
        for spec in specs:
            subtitle = spec.get("subtitle", "")
            self.assertEqual(
                subtitle,
                "Hábeas data financiero · documento sujeto a verificación de hechos y soportes",
            )
            lowered = subtitle.casefold()
            self.assertNotIn("co-cd-001", lowered)
            self.assertNotIn("m33", lowered)
            self.assertNotIn("candidato", lowered)
            self.assertNotIn("qa", lowered)

    def test_externalized_habeas_sample_does_not_print_internal_metadata_table(self):
        spec = next(item for item in self._specs() if item.get("kind") == "habeas_consultation")
        self.assertEqual(_visible_metadata("CO-CD-001", spec), [])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "consulta.docx"
            build_docx(
                target,
                spec["title"],
                spec.get("subtitle", ""),
                _visible_metadata("CO-CD-001", spec),
                spec["sections"],
                product_code="CO-CD-001",
                enforce_legal_standard=True,
                append_default_control=False,
            )
            with ZipFile(target) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertNotIn("Estándar documental", xml)
            self.assertNotIn("Candidato sujeto a revisión jurídica y QA", xml)
            self.assertNotIn("Instrumento jurídico CO-CD-001", xml)


if __name__ == "__main__":
    unittest.main()
