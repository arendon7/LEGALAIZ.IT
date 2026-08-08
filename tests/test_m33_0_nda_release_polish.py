from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from m33_nda_release_polish import compose_nda_m33_release
from test_m33_0_nda_legal_review import nda_answers, section_text, visible_text


class NdaReleasePolishM330Tests(unittest.TestCase):
    def test_notifications_use_real_case_contacts_not_internal_ficha(self):
        composition = compose_nda_m33_release(nda_answers())
        notifications = section_text(composition, "NOTIFICACIONES")
        self.assertIn("juridica@demo.legalaiz.it", notifications)
        self.assertIn("contratos@demo.legalaiz.it", notifications)
        self.assertIn("Medellín, Antioquia", notifications)
        self.assertIn("Bogotá D.C.", notifications)
        self.assertNotIn("contactos de la ficha", notifications.casefold())

    def test_integrity_has_no_internal_platform_ficha_reference(self):
        composition = compose_nda_m33_release(nda_answers())
        integrity = section_text(composition, "INTEGRIDAD, PRELACIÓN Y MODIFICACIONES")
        self.assertIn("sus anexos expresamente incorporados", integrity)
        self.assertIn("instrumentos específicos", integrity)
        self.assertNotIn("La ficha", integrity)
        self.assertNotIn("la ficha", integrity)

    def test_signature_clause_defines_execution_date_and_same_hash_governance(self):
        composition = compose_nda_m33_release(nda_answers())
        signature = section_text(composition, "FIRMA Y EVIDENCIA ELECTRÓNICA")
        self.assertIn("última firma necesaria", signature)
        self.assertIn("Jurídico y QA aprueben su hash", signature)
        self.assertIn("copia íntegra", signature)

    def test_residual_clauses_are_substantive_not_one_line_placeholders(self):
        composition = compose_nda_m33_release(nda_answers())
        for heading, token in (
            ("GARANTÍAS SOBRE TERCEROS", "derechos de terceros"),
            ("AUDITORÍA PROPORCIONADA", "evidencia documental"),
            ("MEDIDAS URGENTES", "medidas cautelares"),
            ("RECLAMOS DE TERCEROS", "control de su propia defensa"),
            ("CESIÓN Y CAMBIO DE CONTROL", "reorganización societaria"),
        ):
            text = section_text(composition, heading)
            self.assertGreater(len(text.split()), 70, heading)
            self.assertIn(token, text, heading)

    def test_defined_terms_are_consistent_and_gender_placeholder_is_removed(self):
        composition = compose_nda_m33_release(nda_answers())
        text = visible_text(composition)
        self.assertNotIn("identificado(a)", text)
        self.assertNotIn("La Parte Reveladora", text)
        self.assertNotIn("la Parte Reveladora", text)
        self.assertNotIn("La Parte Receptora", text)
        self.assertNotIn("la Parte Receptora", text)
        self.assertIn("LA PARTE REVELADORA", text)
        self.assertIn("LA PARTE RECEPTORA", text)

    def test_no_personal_data_case_does_not_add_data_transfer_language_in_assignment(self):
        composition = compose_nda_m33_release(nda_answers())
        assignment = section_text(composition, "CESIÓN Y CAMBIO DE CONTROL")
        self.assertNotIn("datos personales", assignment.casefold())


if __name__ == "__main__":
    unittest.main()
