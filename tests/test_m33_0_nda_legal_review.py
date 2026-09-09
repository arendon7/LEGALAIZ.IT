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

from m33_nda_legal_finalize import compose_nda_m33_final


def nda_answers() -> dict:
    return {
        "party_a": {
            "identification": {
                "type": "legal_person",
                "name": "Soluciones Andinas S.A.S.",
                "id_number": "901234567-8",
                "address": "Medellín, Antioquia",
                "email": "juridica@demo.legalaiz.it",
            },
            "signatory": {
                "name": "María Fernanda Gómez Ruiz",
                "id_number": "43678901",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "party_b": {
            "identification": {
                "type": "legal_person",
                "name": "Tecnología Segura S.A.S.",
                "id_number": "900765432-1",
                "address": "Bogotá D.C.",
                "email": "contratos@demo.legalaiz.it",
            },
            "signatory": {
                "name": "Juan David Torres",
                "id_number": "79543210",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "agreement": {
            "type": "mutual",
            "reciprocal": True,
            "purpose": "evaluar y ejecutar una integración tecnológica y documental entre las partes",
            "reference": "Proyecto Integración Segura 2026",
        },
        "information": {
            "categories": "arquitectura, código, documentación técnica, modelos jurídicos, precios, estrategias y datos operativos",
            "formats_sources": "documentos, reuniones, repositorios autorizados, demostraciones y accesos controlados",
            "exclusions": "información pública, conocida legítimamente o desarrollada de forma independiente",
        },
        "access": {
            "authorized_recipients": "personal directivo, jurídico y técnico expresamente asignado",
            "representatives": "asesores y subcontratistas autorizados y sometidos a obligaciones equivalentes",
            "need_to_know": "mínimo privilegio",
            "permitted_use": "evaluación, integración, pruebas y ejecución del proyecto",
            "compelled_disclosure": "notificación previa cuando sea posible y revelación mínima",
        },
        "security": {
            "controls": {
                "level": "enhanced",
                "technical": "cifrado, MFA, registro de accesos, segregación y copias de seguridad",
                "organizational": "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes",
                "physical": "control de ingreso y custodia de soportes",
            },
            "incident_protocol": "notificación, contención, investigación y preservación de evidencia",
        },
        "data": {
            "personal": False,
            "roles": {},
            "lifecycle": "conservación durante la finalidad y eliminación al cierre",
            "crossborder": False,
        },
        "ip": {
            "results_allocation": "case_by_case",
            "preexisting_materials": "herramientas, bibliotecas, plantillas y conocimientos identificados por cada parte",
            "source_code_reverse_engineering": "prohibición salvo autorización o excepción legal",
        },
        "ai": {
            "used": True,
            "training_outputs": "uso controlado sin entrenamiento ni retención con información protegida",
        },
        "term_remedies": {
            "agreement_years": 2,
            "ordinary_confidentiality_years": 5,
            "trade_secret_rule": "while_secret",
            "penalty_or_liability": "responsabilidad por daños directos, probados y causalmente vinculados",
        },
        "closure_confirmation": {
            "return_destroy": "devolución o eliminación segura",
            "retained_copies": "conservación limitada por obligación legal o defensa de derechos",
            "dispute_mechanism": "negotiation_conciliation",
        },
    }


def section(composition: dict, phrase: str) -> dict | None:
    matches = [
        item for item in composition.get("sections") or []
        if phrase.casefold() in str(item.get("heading") or "").casefold()
    ]
    if not matches:
        return None
    # Los títulos de portada pueden contener nombres de módulos (PI, datos, IA,
    # secretos). Para una consulta temática se prefiere siempre la cláusula real;
    # la portada se usa solo cuando no existe una cláusula coincidente.
    return next((item for item in matches if item.get("_type") == "clause"), matches[0])


def section_text(composition: dict, phrase: str) -> str:
    item = section(composition, phrase)
    if not item:
        return ""
    values = [str(item.get("text") or "")]
    values.extend(str(value) for value in item.get("paragraphs") or [])
    values.extend(str(value) for value in item.get("bullets") or [])
    return "\n".join(values)


def visible_text(composition: dict, *, include_control: bool = False) -> str:
    values = []
    for item in composition.get("sections") or []:
        if not include_control and item.get("_type") == "control":
            continue
        values.append(str(item.get("heading") or ""))
        values.append(str(item.get("text") or ""))
        values.extend(str(value) for value in item.get("paragraphs") or [])
        values.extend(str(value) for value in item.get("bullets") or [])
    return "\n".join(values)


class NdaLegalReviewM330Tests(unittest.TestCase):
    def test_mutual_appearance_identifies_both_legal_entities_and_representatives(self):
        composition = compose_nda_m33_final(nda_answers())
        appearance = section_text(composition, "ACUERDO DE CONFIDENCIALIDAD")
        self.assertIn("Soluciones Andinas S.A.S., NIT 901.234.567-8, con domicilio en Medellín, Antioquia", appearance)
        self.assertIn("María Fernanda Gómez Ruiz", appearance)
        self.assertIn("documento No. 43.678.901", appearance)
        self.assertIn("Tecnología Segura S.A.S., NIT 900.765.432-1, con domicilio en Bogotá D.C.", appearance)
        self.assertIn("Juan David Torres", appearance)
        self.assertIn("documento No. 79.543.210", appearance)
        self.assertIn("Proyecto Integración Segura 2026", appearance)
        self.assertIn("Cada parte tendrá la calidad de PARTE REVELADORA", appearance)

    def test_object_is_deep_and_has_no_historical_duplicate_phrase(self):
        composition = compose_nda_m33_final(nda_answers())
        text = section_text(composition, "OBJETO")
        self.assertIn("evaluación, integración, pruebas y ejecución del proyecto", text)
        self.assertIn("entrenar modelos", text)
        self.assertNotIn("cada parte cuando revele", text.casefold())
        self.assertNotIn("cada parte cuando reciba", text.casefold())

    def test_trade_secret_is_not_created_by_confidential_label(self):
        composition = compose_nda_m33_final(nda_answers())
        text = section_text(composition, "SECRETOS EMPRESARIALES")
        self.assertIn("no ser generalmente conocida ni fácilmente accesible", text)
        self.assertIn("valor comercial precisamente por ser secreta", text)
        self.assertIn("medidas razonables", text)
        self.assertIn("La etiqueta contractual 'confidencial' no crea por sí sola", text)

    def test_personal_data_module_is_absent_when_case_declares_no_personal_data(self):
        composition = compose_nda_m33_final(nda_answers())
        headings = [str(item.get("heading") or "").casefold() for item in composition["sections"]]
        self.assertFalse(any("datos personales" in heading for heading in headings))
        self.assertFalse(any("datos sensibles" in heading for heading in headings))
        self.assertFalse(any("reporte regulatorio" in heading for heading in headings))
        provider = section_text(composition, "PROVEEDORES, NUBE Y TERCEROS")
        self.assertIn("no se activa un régimen contractual de encargado/subencargado", provider)
        sources = composition["maturity_answers"]["legal_sources"]
        self.assertFalse(any("Ley 1581" in item for item in sources))
        self.assertFalse(any("Decreto 1074" in item for item in sources))

    def test_personal_data_module_and_sources_activate_only_when_declared(self):
        answers = nda_answers()
        answers["data"]["personal"] = True
        answers["data"]["crossborder"] = True
        composition = compose_nda_m33_final(answers)
        data_clause = section_text(composition, "DATOS PERSONALES")
        self.assertIn("Ley 1581 de 2012", data_clause)
        self.assertIn("flujo transfronterizo", data_clause)
        sources = composition["maturity_answers"]["legal_sources"]
        self.assertTrue(any("Ley 1581" in item for item in sources))
        self.assertTrue(any("Decreto 1074" in item for item in sources))

    def test_ai_module_is_conditional_and_preserves_no_training_rule(self):
        composition = compose_nda_m33_final(nda_answers())
        ai = section_text(composition, "INTELIGENCIA ARTIFICIAL")
        self.assertIn("sin entrenamiento ni retención con información protegida", ai)
        self.assertIn("revisión humana", ai)
        self.assertNotIn("Ley 2502", ai)

        answers = nda_answers()
        answers["ai"]["used"] = False
        disabled = compose_nda_m33_final(answers)
        headings = [str(item.get("heading") or "").casefold() for item in disabled["sections"]]
        self.assertFalse(any("inteligencia artificial" in heading for heading in headings))
        self.assertNotIn("INTELIGENCIA ARTIFICIAL", disabled["title"])

    def test_incident_timing_is_not_invented_but_can_be_configured(self):
        composition = compose_nda_m33_final(nda_answers())
        incident = section_text(composition, "INCIDENTES Y NOTIFICACIÓN")
        self.assertIn("tan pronto como razonablemente sea posible", incident)
        self.assertNotIn("24 horas", incident)
        self.assertNotIn("veinticuatro", incident.casefold())

        answers = nda_answers()
        answers["security"]["notification_hours"] = 12
        configured = compose_nda_m33_final(answers)
        self.assertIn("primeras 12 horas", section_text(configured, "INCIDENTES Y NOTIFICACIÓN"))

    def test_ip_results_are_case_by_case_and_legally_delimited(self):
        composition = compose_nda_m33_final(nda_answers())
        text = section_text(composition, "RESULTADOS Y CADENA DE TITULARIDAD")
        self.assertIn("caso por caso", text)
        self.assertIn("modalidades de explotación", text)
        self.assertIn("tiempo", text)
        self.assertIn("ámbito territorial", text)
        self.assertIn("deberán constar por escrito", text)
        self.assertIn("producción futura", text)
        self.assertIn("derechos morales", text)

    def test_term_has_three_distinct_survival_rules(self):
        composition = compose_nda_m33_final(nda_answers())
        text = section_text(composition, "DURACIÓN Y SUPERVIVENCIA")
        self.assertIn("vigencia operativa de 2 años", text)
        self.assertIn("durante 5 años", text)
        self.assertIn("mientras reúnan los requisitos jurídicos", text)

    def test_return_retention_liability_and_commercial_restrictions_are_precise(self):
        composition = compose_nda_m33_final(nda_answers())
        closing = section_text(composition, "DEVOLUCIÓN, ELIMINACIÓN Y CERTIFICACIÓN")
        liability = section_text(composition, "RESPONSABILIDAD Y MITIGACIÓN")
        commercial = section_text(composition, "RESTRICCIONES COMERCIALES")
        self.assertIn("devolución o eliminación segura", closing)
        self.assertIn("conservación limitada por obligación legal o defensa de derechos", closing)
        self.assertIn("daños directos, probados y causalmente vinculados", liability)
        self.assertIn("no constituye por sí sola cláusula penal", liability)
        self.assertIn("no crea no competencia", commercial)
        self.assertIn("competencia por méritos", commercial)

    def test_signatures_identify_representatives_entities_and_nits(self):
        composition = compose_nda_m33_final(nda_answers())
        signature = next(item for item in composition["sections"] if item.get("_type") == "signature")
        parties = signature.get("parties") or []
        self.assertEqual(len(parties), 2)
        first, second = parties
        self.assertEqual(first["name"], "María Fernanda Gómez Ruiz")
        self.assertIn("Soluciones Andinas S.A.S.", first.get("role") or "")
        self.assertIn("Documento 43.678.901", first.get("id") or "")
        self.assertIn("NIT 901.234.567-8", first.get("id") or "")
        self.assertEqual(second["name"], "Juan David Torres")
        self.assertIn("Tecnología Segura S.A.S.", second.get("role") or "")
        self.assertIn("Documento 79.543.210", second.get("id") or "")
        self.assertIn("NIT 900.765.432-1", second.get("id") or "")

    def test_considerations_and_visible_text_have_no_known_editorial_defects(self):
        composition = compose_nda_m33_final(nda_answers())
        text = visible_text(composition)
        self.assertNotIn("Que La", text)
        self.assertNotIn("Que El", text)
        self.assertNotIn("CONTROL DE USO", text)
        self.assertNotIn("24 horas", text)

    def test_clause_numbers_are_continuous_after_conditional_modules(self):
        composition = compose_nda_m33_final(nda_answers())
        numbers = [item.get("clause_number") for item in composition["sections"] if item.get("_type") == "clause"]
        self.assertGreaterEqual(len(numbers), 20)
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        control = next(item for item in composition["sections"] if item.get("_type") == "control")
        self.assertGreaterEqual(len(control.get("bullets") or []), 5)
        self.assertTrue(all("Fuente jurídica de control:" in item for item in control.get("bullets") or []))


if __name__ == "__main__":
    unittest.main()
