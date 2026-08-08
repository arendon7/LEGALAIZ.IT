from __future__ import annotations

from copy import deepcopy
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


class LeaseLegalReviewM330Tests(unittest.TestCase):
    def test_joint_lease_uses_legal_classification_and_all_signatories(self):
        composition = compose_lease_m33_final(complete_answers())
        modality = section_text(composition, "MODALIDAD")
        self.assertIn("arrendamiento mancomunado", modality)
        self.assertIn("solidarias", modality)
        signature = next(section for section in composition["sections"] if section.get("_type") == "signature")
        names = [party.get("name") for party in signature.get("parties") or []]
        self.assertIn("Ana Representante", names)
        self.assertIn("Carlos Arrendatario", names)
        self.assertIn("María Arrendataria", names)
        self.assertEqual(len(names), 3)

    def test_property_and_delivery_are_complete_and_dates_are_human_readable(self):
        composition = compose_lease_m33_final(complete_answers())
        property_text = section_text(composition, "IDENTIFICACIÓN DEL INMUEBLE")
        delivery = section_text(composition, "ENTREGA")
        self.assertIn("matrícula inmobiliaria 001-123456", property_text)
        self.assertIn("identificación catastral 05001-01-0001", property_text)
        self.assertIn("Parqueadero 18", property_text)
        self.assertIn("Cuarto útil 7", property_text)
        self.assertIn("1 de agosto de 2026", delivery)
        self.assertNotIn("2026-08-01", delivery)

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
        self.assertIn("artículo 16", deposits)
        self.assertIn("empresa prestadora", deposits)
        self.assertIn("Decreto 3130 de 2003", deposits)

    def test_landlord_and_tenant_termination_paths_are_not_collapsed(self):
        composition = compose_lease_m33_final(complete_answers())
        landlord = section_text(composition, "TERMINACIÓN POR EL ARRENDADOR")
        tenant = section_text(composition, "TERMINACIÓN POR EL ARRENDATARIO")
        self.assertIn("seis (6) cánones", landlord)
        self.assertIn("cuatro (4) años", landlord)
        self.assertIn("uno punto cinco (1,5) cánones", landlord)
        self.assertIn("tres (3) cánones", tenant)
        self.assertIn("sin indemnización", tenant)

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
