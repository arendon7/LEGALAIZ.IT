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

from co_ar_001_test_fixtures_v249 import complete_answers
from m33_lease_legal_finalize import compose_lease_m33_final


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


def all_visible_text(composition: dict) -> str:
    chunks = []
    for section in composition.get("sections") or []:
        chunks.append(str(section.get("heading") or ""))
        chunks.append(str(section.get("text") or ""))
        chunks.extend(str(item) for item in section.get("paragraphs") or [])
        chunks.extend(str(item) for item in section.get("bullets") or [])
    return "\n".join(chunks)


class LeaseLegalReviewM330Tests(unittest.TestCase):
    def test_joint_lease_uses_legal_classification_and_all_signatories(self):
        composition = compose_lease_m33_final(complete_answers())
        modality = section_text(composition, "MODALIDAD")
        self.assertIn("arrendamiento mancomunado", modality)
        self.assertIn("solidarias", modality)
        signature = next(section for section in composition["sections"] if section.get("_type") == "signature")
        parties = signature.get("parties") or []
        names = [party.get("name") for party in parties]
        self.assertIn("Ana Representante", names)
        self.assertIn("Carlos Arrendatario", names)
        self.assertIn("María Arrendataria", names)
        self.assertEqual(len(names), 3)
        landlord = next(party for party in parties if party.get("name") == "Ana Representante")
        self.assertIn("Arrendamientos Ejemplo S.A.S.", landlord.get("role") or "")
        self.assertIn("NIT 901.000.001-1", landlord.get("role") or "")

    def test_appearance_uses_complete_parties_without_gender_or_role_crossing(self):
        composition = compose_lease_m33_final(complete_answers())
        appearance = section_text(composition, "CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA")
        self.assertIn("Arrendamientos Ejemplo S.A.S., NIT 901.000.001-1, con domicilio en Medellín", appearance)
        self.assertIn("Ana Representante", appearance)
        self.assertIn("Carlos Arrendatario, documento No. 71.000.001, con domicilio en Medellín", appearance)
        self.assertIn("María Arrendataria, documento No. 43.000.002", appearance)
        self.assertNotIn("Carlos Arrendatario, documento No. 71.000.001, domiciliada", appearance)

    def test_property_delivery_and_term_are_complete_and_human_readable(self):
        composition = compose_lease_m33_final(complete_answers())
        property_text = section_text(composition, "IDENTIFICACIÓN DEL INMUEBLE")
        delivery = section_text(composition, "ENTREGA")
        term = section_text(composition, "TÉRMINO")
        self.assertIn("matrícula inmobiliaria 001-123456", property_text)
        self.assertIn("identificación catastral 05001-01-0001", property_text)
        self.assertIn("Parqueadero 18", property_text)
        self.assertIn("Cuarto útil 7", property_text)
        self.assertIn("1 de agosto de 2026", delivery)
        self.assertIn("Ajuste de una bisagra.", delivery)
        self.assertIn("Arrendador dentro de los cinco días siguientes.", delivery)
        self.assertNotIn("2026-08-01", delivery)
        self.assertIn("desde el 1 de agosto de 2026 hasta el 31 de julio de 2027", term)
        self.assertIn("mismo término inicial", term)

    def test_rent_adjustment_is_rule_driven_and_not_frozen_to_a_past_ipc(self):
        composition = compose_lease_m33_final(complete_answers())
        adjustment = section_text(composition, "REAJUSTE")
        self.assertIn("publicación oficial del DANE", adjustment)
        self.assertIn("doce (12) meses", adjustment)
        self.assertNotIn("5,10", adjustment)
        self.assertNotIn("IPC anual de 2025", adjustment)

    def test_rent_above_article_18_limit_is_blocked(self):
        answers = complete_answers()
        answers["rent"]["amount"] = 4_000_000
        with self.assertRaisesRegex(ValueError, "uno por ciento"):
            compose_lease_m33_final(answers)

    def test_commercial_value_above_two_times_cadastral_is_blocked(self):
        answers = complete_answers()
        answers["rent"]["values"]["commercial_value"] = 500_000_000
        with self.assertRaisesRegex(ValueError, "dos veces el avalúo catastral"):
            compose_lease_m33_final(answers)

    def test_additional_services_above_fifty_percent_are_blocked(self):
        answers = complete_answers()
        answers["charges"]["additional_services"]["value"] = 1_300_000
        with self.assertRaisesRegex(ValueError, "50 %"):
            compose_lease_m33_final(answers)

    def test_cash_deposit_prohibition_is_separated_from_utility_guarantees(self):
        composition = compose_lease_m33_final(complete_answers())
        deposits = section_text(composition, "DEPÓSITOS Y GARANTÍAS")
        utilities = section_text(composition, "SERVICIOS PÚBLICOS")
        self.assertIn("artículo 16", deposits)
        self.assertIn("empresa prestadora", deposits)
        self.assertIn("Decreto 3130 de 2003", deposits)
        self.assertIn("medidores individuales y facturas", utilities)
        self.assertIn("artículo 15", utilities)

    def test_landlord_and_tenant_termination_paths_are_not_collapsed(self):
        composition = compose_lease_m33_final(complete_answers())
        landlord = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDADORA")
        tenant = section_text(composition, "TERMINACIÓN POR LA PARTE ARRENDATARIA")
        self.assertIn("seis (6) cánones", landlord)
        self.assertIn("cuatro (4) años", landlord)
        self.assertIn("uno punto cinco (1,5) cánones", landlord)
        self.assertIn("tres (3) cánones", tenant)
        self.assertIn("sin indemnización", tenant)

    def test_party_terms_are_consistent_across_body(self):
        composition = compose_lease_m33_final(complete_answers())
        text = all_visible_text(composition)
        self.assertNotIn("EL ARRENDADOR", text)
        self.assertNotIn("EL ARRENDATARIO", text)
        self.assertNotIn("El arrendador", text)
        self.assertNotIn("El arrendatario", text)

    def test_pet_clause_is_conditional_and_sources_remain_externalizable(self):
        answers = complete_answers()
        answers["pets"]["exists"] = False
        composition = compose_lease_m33_final(answers)
        headings = [str(section.get("heading") or "") for section in composition["sections"]]
        self.assertFalse(any("MASCOTAS" in heading for heading in headings))
        control = next(section for section in composition["sections"] if section.get("_type") == "control")
        self.assertGreaterEqual(len(control.get("bullets") or []), 7)
        self.assertTrue(all("Fuente jurídica de control:" in item for item in control.get("bullets") or []))


if __name__ == "__main__":
    unittest.main()
