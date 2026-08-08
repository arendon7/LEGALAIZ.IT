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

from m33_nda_instrument_finalize import compose_nda_m33_instrument
from test_m33_0_nda_legal_review import nda_answers, section_text, visible_text


class NdaInstrumentFinalM330Tests(unittest.TestCase):
    def test_clean_instrument_contains_no_internal_workspace_language(self):
        composition = compose_nda_m33_instrument(nda_answers())
        text = visible_text(composition)
        self.assertNotIn("expediente", text.casefold())
        self.assertNotIn("plataforma", text.casefold())
        self.assertNotIn("jurídico y qa", text.casefold())
        self.assertNotIn("aprobación jurídica", text.casefold())

    def test_no_personal_data_case_omits_personal_data_references_from_visible_instrument(self):
        composition = compose_nda_m33_instrument(nda_answers())
        text = visible_text(composition)
        self.assertNotIn("datos personales", text.casefold())
        self.assertNotIn("encargado/subencargado", text.casefold())

    def test_security_provider_ai_and_liability_are_contract_language_not_case_metadata(self):
        composition = compose_nda_m33_instrument(nda_answers())
        security = section_text(composition, "SEGURIDAD DE LA INFORMACIÓN")
        provider = section_text(composition, "PROVEEDORES, NUBE Y TERCEROS")
        ai = section_text(composition, "INTELIGENCIA ARTIFICIAL")
        liability = section_text(composition, "RESPONSABILIDAD Y MITIGACIÓN")
        self.assertIn("controles técnicos de cifrado, MFA", security)
        self.assertIn("finalidad del acuerdo", provider)
        self.assertIn("condición contractual", ai)
        self.assertIn("Las partes acuerdan como regla de responsabilidad", liability)
        for text in (security, provider, ai, liability):
            self.assertNotIn("expediente", text.casefold())

    def test_signature_clause_preserves_integrity_without_printing_internal_approval_process(self):
        composition = compose_nda_m33_instrument(nda_answers())
        signature = section_text(composition, "FIRMA Y EVIDENCIA ELECTRÓNICA")
        self.assertIn("última firma necesaria", signature)
        self.assertIn("preservarse sin modificaciones posteriores", signature)
        self.assertIn("nueva versión", signature)
        self.assertNotIn("plataforma", signature.casefold())
        self.assertNotIn("jurídico", signature.casefold())
        self.assertNotIn("qa", signature.casefold())
        self.assertNotIn("hash", signature.casefold())

    def test_personal_data_language_reappears_only_when_module_is_activated(self):
        answers = nda_answers()
        answers["data"]["personal"] = True
        composition = compose_nda_m33_instrument(answers)
        text = visible_text(composition)
        self.assertIn("datos personales", text.casefold())
        self.assertIn("tratamiento de datos personales", section_text(composition, "DURACIÓN Y SUPERVIVENCIA"))


if __name__ == "__main__":
    unittest.main()
