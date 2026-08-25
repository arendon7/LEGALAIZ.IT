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
    def test_comparecencia_survives_title_keywords_and_ai_stays_in_its_clause(self):
        composition = compose_nda_m33_instrument(nda_answers())
        title_section = next(
            item for item in composition["sections"]
            if item.get("_type") != "clause"
            and str(item.get("heading") or "").upper().startswith("ACUERDO DE CONFIDENCIALIDAD")
        )
        appearance = "\n".join(str(value) for value in title_section.get("paragraphs") or [])
        self.assertIn("Soluciones Andinas S.A.S., NIT 901.234.567-8", appearance)
        self.assertIn("María Fernanda Gómez Ruiz", appearance)
        self.assertIn("Tecnología Segura S.A.S., NIT 900.765.432-1", appearance)
        self.assertIn("Juan David Torres", appearance)
        self.assertIn("Cada parte tendrá la calidad de PARTE REVELADORA", appearance)
        self.assertNotIn("condición contractual: uso controlado sin entrenamiento", appearance)

        ai = section_text(composition, "INTELIGENCIA ARTIFICIAL")
        self.assertIn("condición contractual: uso controlado sin entrenamiento", ai)

    def test_considerations_are_substantive_and_client_facing(self):
        composition = compose_nda_m33_instrument(nda_answers())
        considerations = next(
            item for item in composition["sections"]
            if str(item.get("heading") or "").strip().casefold() == "consideraciones"
        )
        paragraphs = considerations.get("paragraphs") or []
        self.assertEqual(6, len(paragraphs))
        text = "\n".join(str(value) for value in paragraphs)
        self.assertIn("confidencialidad contractual y el secreto empresarial", text)
        self.assertIn("principio de necesidad de conocer", text)
        self.assertIn("instrumento operativo y probatorio de prevención", text)
        self.assertNotIn("expediente", text.casefold())
        self.assertNotIn("plataforma", text.casefold())

    def test_clean_instrument_contains_no_internal_workspace_language(self):
        composition = compose_nda_m33_instrument(nda_answers())
        text = visible_text(composition)
        self.assertNotIn("expediente", text.casefold())
        self.assertNotIn("plataforma", text.casefold())
        self.assertNotIn("jurídico y qa", text.casefold())
        self.assertNotIn("aprobación jurídica", text.casefold())

    def test_no_personal_data_case_omits_data_module_vocabulary_from_visible_instrument(self):
        composition = compose_nda_m33_instrument(nda_answers())
        text = visible_text(composition).casefold()
        self.assertNotIn("datos personales", text)
        self.assertNotIn("encargado/subencargado", text)
        self.assertNotIn("responsable/encargado", text)
        self.assertNotIn("protección de datos", text)
        definitions = section_text(composition, "DEFINICIONES OPERATIVAS")
        self.assertIn("titularidad, autoría, representación, relación laboral, licenciamiento", definitions)

    def test_security_provider_ai_and_liability_are_contract_language_not_case_metadata(self):
        composition = compose_nda_m33_instrument(nda_answers())
        security = section_text(composition, "SEGURIDAD DE LA INFORMACIÓN")
        provider = section_text(composition, "PROVEEDORES, NUBE Y TERCEROS")
        ai = section_text(composition, "INTELIGENCIA ARTIFICIAL")
        liability = section_text(composition, "RESPONSABILIDAD Y MITIGACIÓN")
        self.assertIn("controles técnicos de cifrado, autenticación multifactor (MFA)", security)
        self.assertIn("finalidad del acuerdo", provider)
        self.assertIn("condición contractual", ai)
        self.assertIn("Las partes acuerdan como regla de responsabilidad", liability)
        for text in (security, provider, ai, liability):
            self.assertNotIn("expediente", text.casefold())

    def test_visible_wording_avoids_avoidable_anglicisms(self):
        composition = compose_nda_m33_instrument(nda_answers())
        text = visible_text(composition)
        headings = "\n".join(str(item.get("heading") or "") for item in composition["sections"])
        restrictions = section_text(composition, "RESTRICCIONES COMERCIALES")
        purpose = section_text(composition, "FINALIDAD AUTORIZADA")
        self.assertNotIn("Este NDA", text)
        self.assertNotIn("LEGAL HOLD", headings.upper())
        self.assertNotIn("benchmarking", purpose.casefold())
        self.assertIn("El presente acuerdo no crea obligaciones de no competencia", restrictions)
        self.assertIn("CONSERVACIÓN PROBATORIA Y RETENCIÓN LEGAL", headings)

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
        self.assertIn("protección de datos", section_text(composition, "SOLUCIÓN DE CONTROVERSIAS"))


if __name__ == "__main__":
    unittest.main()
