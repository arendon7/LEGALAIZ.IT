from __future__ import annotations

import unittest

from co_ar_001_test_fixtures_v249 import complete_answers
from legalai_platform.legal_source_registry import get_legal_source
from m33_lease_instrument_finalize import compose_lease_m33_instrument
from m33_lease_release_polish import compose_lease_m33_release as compose_lease_before_m334


def section_text(composition: dict, phrase: str) -> str:
    for section in composition.get("sections") or []:
        if phrase.casefold() in str(section.get("heading") or "").casefold():
            values = [str(section.get("text") or "")]
            values.extend(str(item) for item in section.get("paragraphs") or [])
            return "\n".join(value for value in values if value)
    return ""


class LeaseTerminationSubstantiveReviewTests(unittest.TestCase):
    def test_landlord_special_causes_match_articles_22_and_26(self):
        composition = compose_lease_m33_instrument(complete_answers())
        text = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDADORA")
        self.assertIn("término no menor de un (1) año", text)
        self.assertIn("obras independientes de reparación", text)
        self.assertNotIn("reparación indispensable", text)
        self.assertIn("seis (6) cánones de arrendamiento", text)
        self.assertIn("uno punto cinco (1,5) cánones de arrendamiento", text)
        self.assertIn("artículo 26", text)
        self.assertIn("no ser privada del inmueble", text)

    def test_landlord_indemnity_route_exposes_article_23_consignation(self):
        composition = compose_lease_m33_instrument(complete_answers())
        text = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDADORA")
        self.assertIn("artículo 23", text)
        self.assertIn("consignarse a favor de LA PARTE ARRENDATARIA", text)
        self.assertIn("a órdenes de la autoridad competente", text)
        self.assertIn("dentro de los tres (3) meses anteriores", text)

    def test_tenant_route_exposes_article_25_and_provisional_delivery(self):
        composition = compose_lease_m33_instrument(complete_answers())
        text = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDATARIA")
        self.assertIn("artículo 25", text)
        self.assertIn("consignarse a favor de LA PARTE ARRENDADORA", text)
        self.assertIn("renta vigente a la fecha del preaviso", text)
        self.assertIn("sin indemnización", text)
        self.assertIn("entrega provisional ante la autoridad competente", text)
        self.assertIn("renovación automática", text)

    def test_review_is_surgical_outside_termination(self):
        before = compose_lease_before_m334(complete_answers())
        after = compose_lease_m33_instrument(complete_answers())
        invariant_rules = {
            "CANON": ("uno por ciento (1 %)", "dos (2) veces el avalúo catastral"),
            "REAJUSTE": ("doce (12) meses", "publicación oficial del DANE"),
            "DEPÓSITOS Y GARANTÍAS": ("artículo 16", "Decreto 3130 de 2003"),
            "SERVICIOS PÚBLICOS": ("artículo 15", "medidores individuales y facturas"),
        }
        for heading, rules in invariant_rules.items():
            before_text = section_text(before, heading)
            after_text = section_text(after, heading)
            for rule in rules:
                self.assertIn(rule, before_text)
                self.assertIn(rule, after_text)
        maturity = after.get("maturity_answers") or {}
        self.assertEqual("2026-08-11", maturity.get("lease_termination_substantive_review"))
        self.assertEqual("22-26", maturity.get("lease_termination_articles_reviewed"))
        self.assertTrue(maturity.get("lease_termination_route_guard"))

    def test_source_registry_covers_articles_25_and_26(self):
        source = get_legal_source("CO-LEY820-2003")
        self.assertIn("artículos 2 a 26", source["locator"])
        topics = " ".join(source.get("topics") or [])
        self.assertIn("consignación", topics)
        self.assertIn("derecho de retención", topics)


if __name__ == "__main__":
    unittest.main()
