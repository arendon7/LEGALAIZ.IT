from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MODULE = ROOT / "app" / "modules" / "public_m29_1.js"


class PublicProductExperienceM380Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PUBLIC_MODULE.read_text(encoding="utf-8")
        cls.folded = cls.source.casefold()

    def test_canonical_brand_promise_remains_public(self):
        self.assertIn("Más que respuestas, soluciones.", self.source)
        self.assertIn("Tu solución legal, impulsada por IA y expertos.", self.source)

    def test_public_copy_does_not_expose_release_or_deployment_state(self):
        forbidden = (
            "antes de un despliegue productivo",
            "antes de producción",
            "antes de produccion",
            "preproducción",
            "preproduccion",
            "release gate",
            "real_production_blocked",
            "commercial_v1_blocked",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, self.folded, phrase)

    def test_data_protection_copy_is_client_facing_and_specific(self):
        self.assertIn("controles de acceso por rol", self.folded)
        self.assertIn("separación entre usuarios y expedientes", self.folded)
        self.assertIn("trazabilidad de acciones", self.folded)
        self.assertIn("minimizan la exposición de información sensible", self.folded)

    def test_enterprise_value_proposition_is_recurring_platform_not_one_off_document(self):
        required = (
            "genera nuevos contratos y documentos desde la plataforma",
            "una plataforma jurídica para generar, revisar y mantener documentos recurrentes",
            "reutiliza información validada",
            "cada nuevo documento parta de un contexto controlado",
            "genera de nuevo sin empezar desde cero",
            "mantén historial y contexto",
            "actualiza con control",
        )
        for phrase in required:
            self.assertIn(phrase, self.folded, phrase)

    def test_enterprise_updates_do_not_claim_automatic_legal_currency(self):
        forbidden_patterns = (
            r"actualizad[oa]s? autom[aá]ticamente",
            r"siempre (?:estar[aá]n |se mantendr[aá]n )?vigentes",
            r"garantiza(?:mos)? (?:la )?vigencia",
            r"vigencia jur[ií]dica autom[aá]tica",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, self.source, re.IGNORECASE), pattern)
        self.assertIn(
            "Los cambios jurídicos y de plantilla se incorporan mediante revisión, aprobación y trazabilidad antes de su uso.",
            self.source,
        )

    def test_enterprise_demo_cta_is_explicit_and_non_transactional(self):
        self.assertIn("Solicitar demo empresarial", self.source)
        self.assertIn("'/agenda-demo'", self.source)
        self.assertNotIn("Comprar ahora", self.source)
        self.assertNotIn("Activar producción", self.source)

    def test_responsible_use_disclaimer_remains_visible(self):
        self.assertIn("No garantiza resultados ni sustituye representación judicial.", self.source)
        self.assertIn("Cada documento se genera como borrador controlado.", self.source)


if __name__ == "__main__":
    unittest.main()
