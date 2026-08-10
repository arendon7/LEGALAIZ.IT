from __future__ import annotations

"""Presentación M33.3 de calendarios de hábeas data y salud.

No cambia los términos sustantivos configurados. Solo hace visible la procedencia de
las fechas ya calculadas por el motor M33.3 y evita exhibir fechas heredadas como si
fueran exactas cuando no existe evidencia del calendario nacional aplicado.
"""

from copy import deepcopy
from typing import Any

from premium_document_engine import format_date_es


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _date_es(value: Any) -> str:
    if not value:
        return "Por verificar"
    try:
        return format_date_es(str(value))
    except Exception:
        return str(value)


def _active(calculation: dict) -> bool:
    return bool(
        calculation.get("holiday_calendar_applied")
        and calculation.get("business_day_calendar_scope") == "colombia_national_holidays"
    )


def _unique_skipped_holidays(calculation: dict) -> list[str]:
    seen: set[tuple[str, str]] = set()
    values: list[str] = []
    for entry in calculation.get("business_day_calculations") or []:
        if not isinstance(entry, dict):
            continue
        for holiday in entry.get("skipped_holidays") or []:
            if not isinstance(holiday, dict):
                continue
            key = (str(holiday.get("date") or ""), str(holiday.get("name") or "Festivo nacional"))
            if key in seen:
                continue
            seen.add(key)
            values.append(
                f"{_date_es(holiday.get('date'))}: {holiday.get('name') or 'Festivo nacional'}"
            )
    return values


def _trace_summary(calculation: dict) -> str:
    holidays = _unique_skipped_holidays(calculation)
    holiday_text = "; ".join(holidays) if holidays else "ningún festivo nacional dentro de los tramos registrados"
    verified = _date_es(calculation.get("business_day_calendar_verified_at"))
    return (
        "Trazabilidad M33.3: las fechas automáticas expresadas en días hábiles fueron calculadas "
        f"con calendario nacional colombiano, fecha inicial excluida y ruleset verificado al {verified}. "
        f"Festivos nacionales efectivamente omitidos en los tramos registrados: {holiday_text}. "
        "Este control no sustituye la prueba de recepción ni incorpora vacaciones judiciales, cierres "
        "extraordinarios, suspensiones, reglas sectoriales especiales o festivos territoriales."
    )


def finalize_habeas_calendar_m33_3(specs: list[dict], result: dict) -> list[dict]:
    calculation = _calc(result)
    if not _active(calculation):
        return specs

    finalized: list[dict] = []
    for original in specs:
        if original.get("kind") != "habeas_deadline_calendar":
            finalized.append(original)
            continue
        spec = deepcopy(original)
        spec["subtitle"] = "Hábeas data financiero · calendario nacional auditable · recepción por verificar"
        sections = deepcopy(spec.get("sections") or [])
        for section in sections:
            if str(section.get("heading") or "") == "1. REGLAS LEGALES DE CÓMPUTO":
                paragraphs = list(section.get("paragraphs") or [])
                note = _trace_summary(calculation)
                if note not in paragraphs:
                    paragraphs.append(note)
                section["paragraphs"] = paragraphs
        spec["sections"] = sections
        spec["calendar_standard"] = "M33.3"
        spec["calendar_scope"] = calculation.get("business_day_calendar_scope")
        spec["calendar_ruleset_verified_at"] = calculation.get("business_day_calendar_verified_at")
        finalized.append(spec)
    return finalized


def finalize_health_calendar_m33_3(specs: list[dict], result: dict) -> list[dict]:
    calculation = _calc(result)
    audited = _active(calculation)

    finalized: list[dict] = []
    for original in specs:
        if original.get("kind") != "health_calendar":
            finalized.append(original)
            continue
        spec = deepcopy(original)
        sections = deepcopy(spec.get("sections") or [])
        for section in sections:
            heading = str(section.get("heading") or "")
            if heading == "REGLA DE CÓMPUTO":
                paragraphs = list(section.get("paragraphs") or [])
                if audited:
                    note = _trace_summary(calculation)
                else:
                    note = (
                        "No se presenta una fecha genérica heredada como vencimiento cierto cuando el "
                        "resultado no acredita un cálculo con calendario nacional. El término sectorial de "
                        "salud conserva prioridad y cualquier control general de petición debe reconstruirse "
                        "desde la recepción efectiva y la modalidad exacta de la solicitud."
                    )
                if note not in paragraphs:
                    paragraphs.append(note)
                section["paragraphs"] = paragraphs
            if heading == "I. HITOS" and isinstance(section.get("table"), list):
                table = deepcopy(section["table"])
                for row in table[1:]:
                    if not row or str(row[0]) != "Vencimiento genérico heredado":
                        continue
                    row[0] = "Control general de petición"
                    due = calculation.get("preliminary_due_date") if audited else None
                    row[1] = _date_es(due) if due else "Sin fecha nacional auditada"
                    if audited:
                        days = calculation.get("preliminary_business_days")
                        category = str(calculation.get("term_category") or "modalidad por verificar")
                        detail = f"{days} días hábiles · {category}" if days else category
                        row[2] = (
                            f"Referencia subsidiaria M33.3 ({detail}); no sustituye el término sectorial "
                            "de riesgo ni autoriza esperar su vencimiento."
                        )
                    else:
                        row[2] = "No usar una fecha heredada sin reconstruir modalidad, recepción y calendario aplicable."
                section["table"] = table
        spec["sections"] = sections
        if audited:
            spec["calendar_standard"] = "M33.3"
            spec["calendar_scope"] = calculation.get("business_day_calendar_scope")
            spec["calendar_ruleset_verified_at"] = calculation.get("business_day_calendar_verified_at")
        finalized.append(spec)
    return finalized


__all__ = [
    "finalize_habeas_calendar_m33_3",
    "finalize_health_calendar_m33_3",
]
