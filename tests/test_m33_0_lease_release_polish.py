from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
for candidate in (ROOT, RUNTIME_MODULES):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from co_ar_001_test_fixtures_v249 import complete_answers
from m33_document_presentation import split_internal_review_sections
from m33_lease_instrument_finalize import compose_lease_m33_instrument


def section_text(composition: dict, phrase: str) -> str:
    for section in composition.get("sections") or []:
        if phrase.casefold() in str(section.get("heading") or "").casefold():
            values = []
            if section.get("text"):
                values.append(str(section["text"]))
            values.extend(str(item) for item in section.get("paragraphs") or [])
            values.extend(str(item) for item in section.get("bullets") or [])
            return "\n".join(values)
    return ""


def public_text(composition: dict) -> str:
    public, _ = split_internal_review_sections(composition.get("sections") or [])
    return json.dumps(public, ensure_ascii=False)


class LeaseReleasePolishM330Tests(unittest.TestCase):
    def test_considerations_are_substantive_and_client_facing(self):
        composition = compose_lease_m33_instrument(complete_answers())
        considerations = next(
            section for section in composition["sections"]
            if str(section.get("heading") or "").strip().casefold() == "consideraciones"
        )
        paragraphs = considerations.get("paragraphs") or []
        self.assertEqual(6, len(paragraphs))
        text = "\n".join(paragraphs)
        self.assertIn("régimen especial de la Ley 820 de 2003", text)
        self.assertIn("desgaste normal, daños imputables, reparaciones necesarias", text)
        self.assertIn("buena fe y por la realidad acreditada", text)

    def test_signed_instrument_has_no_workspace_language(self):
        composition = compose_lease_m33_instrument(complete_answers())
        text = public_text(composition).casefold()
        for forbidden in ("ficha", "expediente", "la plataforma", "aprobación jurídica", "jurídico y qa", "hash"):
            self.assertNotIn(forbidden, text)
        internal = split_internal_review_sections(composition.get("sections") or [])[1]
        internal_text = json.dumps(internal, ensure_ascii=False)
        self.assertIn("Fuente jurídica de control", internal_text)
        self.assertIn("Ley 820 de 2003", internal_text)

    def test_rent_is_in_cop_and_words_and_preserves_article_18_control(self):
        composition = compose_lease_m33_instrument(complete_answers())
        rent = section_text(composition, "CANON")
        self.assertIn("COP $2.500.000", rent)
        self.assertIn("dos millones quinientos mil pesos moneda corriente", rent)
        self.assertIn("uno por ciento (1 %)", rent)
        self.assertIn("COP $350.000.000", rent)
        self.assertIn("COP $3.500.000", rent)
        self.assertIn("COP $200.000.000", rent)
        self.assertNotIn("Cuenta informada por el arrendador", rent)

    def test_deposit_clause_distinguishes_prohibited_deposit_and_utility_guarantee(self):
        composition = compose_lease_m33_instrument(complete_answers())
        deposits = section_text(composition, "DEPÓSITOS Y GARANTÍAS")
        self.assertIn("artículo 16 de la Ley 820 de 2003", deposits)
        self.assertIn("artículo 15 de la Ley 820 de 2003", deposits)
        self.assertIn("Decreto 3130 de 2003", deposits)
        self.assertIn("compilada en el Decreto 1077 de 2015", deposits)
        self.assertIn("no convierte una estimación unilateral en deuda cierta", deposits)

    def test_repair_inventory_and_closeout_are_evidence_driven(self):
        composition = compose_lease_m33_instrument(complete_answers())
        repairs = section_text(composition, "REPARACIONES NECESARIAS")
        inventory = section_text(composition, "INVENTARIO Y EVIDENCIA")
        restitution = section_text(composition, "RESTITUCIÓN")
        liquidation = section_text(composition, "LIQUIDACIÓN DE SALDOS")
        self.assertIn("habitabilidad, la seguridad", repairs)
        self.assertIn("desgaste normal, envejecimiento", inventory)
        self.assertIn("no podrá condicionarse a la aceptación inmediata de cargos controvertidos", restitution)
        self.assertIn("Las cotizaciones constituyen elementos de estimación", liquidation)

    def test_notices_preserve_statutory_formality_and_real_channels(self):
        composition = compose_lease_m33_instrument(complete_answers())
        communications = section_text(composition, "COMUNICACIONES")
        self.assertIn("arrendador@example.com", communications)
        self.assertIn("tenant@example.com", communications)
        self.assertIn("servicio postal autorizado", communications)
        self.assertIn("correo electrónico o mensaje informal no sustituirá", communications)

    def test_signature_integrity_has_no_platform_language(self):
        composition = compose_lease_m33_instrument(complete_answers())
        signature = section_text(composition, "FIRMA Y COPIA")
        self.assertIn("copia íntegra del contrato", signature)
        self.assertIn("preservarse sin modificaciones posteriores", signature)
        self.assertIn("nueva versión, otrosí o instrumento válido", signature)
        self.assertNotIn("plataforma", signature.casefold())

    def test_residual_risk_clauses_are_substantive(self):
        composition = compose_lease_m33_instrument(complete_answers())
        insurance = section_text(composition, "SEGUROS")
        data = section_text(composition, "DATOS PERSONALES")
        breach = section_text(composition, "INCUMPLIMIENTO Y SUBSANACIÓN")
        abandonment = section_text(composition, "ABANDONO Y BIENES")
        disputes = section_text(composition, "SOLUCIÓN DE CONTROVERSIAS")
        self.assertIn("Aseguradora Ejemplo S.A.", insurance)
        self.assertIn("doble recuperación", insurance)
        self.assertIn("acceso restringido", data)
        self.assertIn("no convierte por sí sola la afirmación de una parte en hecho probado", breach)
        self.assertIn("La mera ausencia temporal", abandonment)
        self.assertIn("conciliación ante un centro o conciliador competente", disputes)

    def test_landlord_and_tenant_termination_rules_survive_release_polish(self):
        composition = compose_lease_m33_instrument(complete_answers())
        landlord = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDADORA")
        tenant = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDATARIA")
        self.assertIn("seis (6) cánones", landlord)
        self.assertIn("cuatro (4) años", landlord)
        self.assertIn("uno punto cinco (1,5) cánones", landlord)
        self.assertIn("tres (3) cánones", tenant)
        self.assertIn("sin indemnización", tenant)


if __name__ == "__main__":
    unittest.main()
