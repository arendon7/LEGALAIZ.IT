from __future__ import annotations

from datetime import date
from types import ModuleType
import unittest

from legalai_platform.colombian_business_calendar import (
    CALENDAR_SCOPE,
    RULESET_VERIFIED_AT,
    add_colombian_business_days,
    calculate_colombian_business_days,
    colombian_national_holidays,
)
from m33_3_business_day_overrides import install_m33_3_business_day_overrides
from m33_3_consumer_calendar_finalize import finalize_consumer_calendar_m33_3
from m33_3_cross_calendar_finalize import (
    finalize_habeas_calendar_m33_3,
    finalize_health_calendar_m33_3,
)


def audited_calculation(start: date = date(2026, 8, 7), days: int = 15) -> dict:
    audit = calculate_colombian_business_days(start, days).to_dict()
    audit["sequence"] = 1
    return {
        "holiday_calendar_applied": True,
        "deadline_is_preliminary": True,
        "business_day_calendar_scope": CALENDAR_SCOPE,
        "business_day_calendar_engine": "M33.3-test",
        "business_day_calendar_verified_at": RULESET_VERIFIED_AT,
        "business_day_calendar_basis": ["Ley 51 de 1983", "Ley 2578 de 2026, artículo 6"],
        "business_day_calendar_limitations": ["No se incluyen vacaciones judiciales."],
        "business_day_calculations": [audit],
        "preliminary_due_date": audit["due_date"],
        "preliminary_business_days": days,
        "term_category": "petición general subsidiaria",
    }


class ColombianBusinessCalendarM333Tests(unittest.TestCase):
    def test_2026_holiday_rules_include_easter_monday_shifts_and_new_chiquinquira_holiday(self):
        holidays = colombian_national_holidays(2026)
        expected = {
            date(2026, 3, 23): "San José",
            date(2026, 4, 2): "Jueves Santo",
            date(2026, 4, 3): "Viernes Santo",
            date(2026, 5, 18): "Ascensión",
            date(2026, 6, 8): "Corpus Christi",
            date(2026, 6, 15): "Sagrado Corazón",
            date(2026, 6, 29): "San Pedro",
            date(2026, 7, 13): "Chiquinquirá",
            date(2026, 7, 20): "Independencia",
            date(2026, 8, 7): "Boyacá",
            date(2026, 8, 17): "Asunción",
        }
        for holiday_date, token in expected.items():
            with self.subTest(holiday_date=holiday_date):
                self.assertIn(holiday_date, holidays)
                self.assertIn(token, holidays[holiday_date].name)

    def test_chiquinquira_rule_respects_effective_date_and_monday_observance(self):
        self.assertFalse(any("Chiquinquirá" in holiday.name for holiday in colombian_national_holidays(2025).values()))
        holidays_2026 = colombian_national_holidays(2026)
        self.assertNotIn(date(2026, 7, 9), holidays_2026)
        observed = holidays_2026[date(2026, 7, 13)]
        self.assertEqual(observed.nominal_date, date(2026, 7, 9))
        self.assertTrue(observed.shifted_to_monday)
        self.assertIn("Ley 2578", observed.basis)

    def test_august_2026_direct_claim_skips_assumption_holiday(self):
        result = calculate_colombian_business_days(date(2026, 8, 7), 15)
        self.assertEqual(result.due_date, date(2026, 8, 31))
        self.assertEqual(result.calendar_scope, CALENDAR_SCOPE)
        self.assertEqual(result.calendar_ruleset_verified_at, RULESET_VERIFIED_AT)
        self.assertEqual(result.counting_rule, "start_exclusive")
        skipped_dates = {holiday.date for holiday in result.skipped_holidays}
        self.assertIn(date(2026, 8, 17), skipped_dates)
        self.assertIn("Asunción", next(holiday.name for holiday in result.skipped_holidays if holiday.date == date(2026, 8, 17)))

    def test_zero_days_preserves_start_and_negative_days_fail_closed(self):
        start = date(2026, 8, 7)
        result = calculate_colombian_business_days(start, 0)
        self.assertEqual(result.due_date, start)
        self.assertEqual(result.skipped_holidays, ())
        with self.assertRaises(ValueError):
            calculate_colombian_business_days(start, -1)

    def test_cross_year_calculation_respects_christmas_and_weekend(self):
        self.assertEqual(add_colombian_business_days(date(2026, 12, 24), 3), date(2026, 12, 30))

    def test_audit_declares_non_universal_calendar_limitations(self):
        payload = calculate_colombian_business_days(date(2026, 8, 7), 15).to_dict()
        limitations = " ".join(payload["limitations"]).casefold()
        self.assertIn("vacaciones judiciales", limitations)
        self.assertIn("cierres extraordinarios", limitations)
        self.assertIn("festivos territoriales", limitations)
        self.assertTrue(payload["holiday_calendar_applied"])

    def test_runtime_override_records_each_business_day_sum_and_removes_stale_assumption(self):
        module = ModuleType("fake_core_m33_3")
        module.__dict__["date"] = date
        exec(
            """
def _business_day_add(start, days):
    cursor = start
    added = 0
    while added < days:
        cursor = cursor.fromordinal(cursor.toordinal() + 1)
        if cursor.weekday() < 5:
            added += 1
    return cursor

def consumer_protection_calc(a):
    start = date.fromisoformat(a['start'])
    due = _business_day_add(start, 15)
    return {
        'engine_version': 'test',
        'direct_claim_due_date': due.isoformat(),
        'holiday_calendar_applied': False,
        'deadline_is_preliminary': True,
        'assumptions': ['Los días hábiles excluyen sábados y domingos, pero no descuentan festivos nacionales o territoriales.'],
    }
def health_petition_calc(a):
    return consumer_protection_calc(a)
def habeas_data_calc(a):
    return consumer_protection_calc(a)
""",
            module.__dict__,
        )
        status = install_m33_3_business_day_overrides(module)
        self.assertTrue(status["installed"])
        calc = module.consumer_protection_calc({"start": "2026-08-07"})
        self.assertEqual(calc["direct_claim_due_date"], "2026-08-31")
        self.assertTrue(calc["holiday_calendar_applied"])
        self.assertEqual(calc["business_day_calendar_scope"], CALENDAR_SCOPE)
        self.assertEqual(len(calc["business_day_calculations"]), 1)
        self.assertEqual(calc["business_day_calculations"][0]["due_date"], "2026-08-31")
        self.assertNotIn("no descuentan festivos", " ".join(calc["assumptions"]).casefold())

    def test_consumer_calendar_uses_compact_traceability_without_separate_sparse_audit_section(self):
        specs = [{
            "kind": "consumer_deadline_calendar",
            "title": "Calendario jurídico de protección al consumidor",
            "subtitle": "Términos legales y fechas preliminares sujetas a verificación",
            "sections": [
                {
                    "heading": "OBJETO Y NATURALEZA DEL CALENDARIO",
                    "paragraphs": ["Los días hábiles calculados excluyen sábados y domingos, pero el cómputo preliminar no descuenta festivos nacionales o territoriales."],
                },
                {
                    "heading": "I. HITOS Y TÉRMINOS",
                    "table": [["Hito", "Regla", "Fecha preliminar", "Control"], ["Reclamación directa", "15 días hábiles", "31 de agosto de 2026", "Fecha preliminar: el cómputo preliminar no descuenta festivos."]],
                },
                {
                    "heading": "II. REGLAS DE USO",
                    "numbered": ["Comprobar festivos y reglas especiales antes de afirmar vencimiento o incumplimiento."],
                },
            ],
        }]
        result = {"calculation": audited_calculation()}
        finalized = finalize_consumer_calendar_m33_3(specs, result)
        calendar = finalized[0]
        visible = " ".join(str(section) for section in calendar["sections"]).casefold()
        headings = [section.get("heading") for section in calendar["sections"]]
        self.assertIn("calendario nacional aplicado", visible)
        self.assertIn("trazabilidad del cómputo nacional", visible)
        self.assertIn("31 de agosto de 2026", visible)
        self.assertIn("17 de agosto de 2026: asunción", visible)
        self.assertNotIn("no descuenta festivos", visible)
        self.assertNotIn("V. REGISTRO DE SUMAS HÁBILES", headings)
        self.assertEqual(calendar["calendar_standard"], "M33.3")

        unchanged = finalize_consumer_calendar_m33_3(specs, {"calculation": {}})
        self.assertIs(unchanged, specs)

    def test_habeas_calendar_declares_audited_national_calendar_without_changing_terms(self):
        specs = [{
            "kind": "habeas_deadline_calendar",
            "subtitle": "original",
            "sections": [{
                "heading": "1. REGLAS LEGALES DE CÓMPUTO",
                "table": [["Actuación", "Término", "Control"], ["Reclamo", "15 días hábiles", "Artículo 16"]],
            }],
        }]
        finalized = finalize_habeas_calendar_m33_3(specs, {"calculation": audited_calculation()})
        calendar = finalized[0]
        visible = " ".join(str(section) for section in calendar["sections"]).casefold()
        self.assertIn("trazabilidad m33.3", visible)
        self.assertIn("17 de agosto de 2026: asunción", visible)
        self.assertIn("15 días hábiles", visible)
        self.assertEqual(calendar["calendar_standard"], "M33.3")
        self.assertIn("calendario nacional auditable", calendar["subtitle"].casefold())

    def test_health_calendar_replaces_unaudited_inherited_date_and_keeps_sector_rule_primary(self):
        specs = [{
            "kind": "health_calendar",
            "sections": [
                {"heading": "REGLA DE CÓMPUTO", "paragraphs": ["Máximo 48 horas corridas."]},
                {"heading": "I. HITOS", "table": [
                    ["Actuación", "Fecha / regla", "Estado"],
                    ["Vencimiento genérico heredado", "21 de agosto de 2026", "No usar como término rector del reclamo sectorial"],
                ]},
            ],
        }]
        audited = finalize_health_calendar_m33_3(specs, {"calculation": audited_calculation()})[0]
        visible = " ".join(str(section) for section in audited["sections"]).casefold()
        self.assertIn("máximo 48 horas corridas", visible)
        self.assertIn("control general de petición", visible)
        self.assertIn("31 de agosto de 2026", visible)
        self.assertNotIn("vencimiento genérico heredado", visible)
        self.assertIn("no sustituye el término sectorial", visible)
        self.assertEqual(audited["calendar_standard"], "M33.3")

        conservative = finalize_health_calendar_m33_3(specs, {"calculation": {}})[0]
        conservative_text = " ".join(str(section) for section in conservative["sections"]).casefold()
        self.assertIn("sin fecha nacional auditada", conservative_text)
        self.assertNotIn("21 de agosto de 2026", conservative_text)
        self.assertIn("no se presenta una fecha genérica heredada", conservative_text)


if __name__ == "__main__":
    unittest.main()
