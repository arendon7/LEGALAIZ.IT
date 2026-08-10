from __future__ import annotations

"""Presentación sustantiva M33.3 del calendario CO-CD-003.

La capa no recalcula términos ni cambia la selección del mecanismo. Únicamente
presenta como calendario nacional auditado una fecha que ya fue producida por el
motor M33.3. Si esa evidencia no existe, mantiene intacta la salida conservadora
anterior y no afirma que los festivos hayan sido considerados.
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


def _holiday_summary(entry: dict) -> str:
    skipped = entry.get("skipped_holidays") if isinstance(entry, dict) else []
    if not skipped:
        return "Sin festivos nacionales omitidos en este tramo"
    values: list[str] = []
    for item in skipped:
        if not isinstance(item, dict):
            continue
        when = _date_es(item.get("date"))
        name = str(item.get("name") or "Festivo nacional")
        basis = str(item.get("basis") or "Base jurídica registrada")
        values.append(f"{when}: {name} ({basis})")
    return "; ".join(values) if values else "Festivo nacional omitido; ver trazabilidad interna"


def _audit_table(calculation: dict) -> list[list[str]]:
    rows = [["Cómputo", "Fecha inicial", "Días hábiles", "Resultado y festivos omitidos"]]
    for index, entry in enumerate(calculation.get("business_day_calculations") or [], start=1):
        if not isinstance(entry, dict):
            continue
        rows.append([
            f"#{entry.get('sequence') or index}",
            _date_es(entry.get("start_date")),
            str(entry.get("business_days") if entry.get("business_days") is not None else "Por verificar"),
            f"Vence {_date_es(entry.get('due_date'))}. {_holiday_summary(entry)}.",
        ])
    if len(rows) == 1:
        rows.append(["Sin suma hábil registrada", "—", "—", "La salida no debe presentarse como fecha nacional auditada."])
    return rows


def _replace_stale_calendar_phrases(value: Any) -> Any:
    if isinstance(value, str):
        replacements = (
            (
                "Fecha preliminar: el cómputo preliminar no descuenta festivos.",
                "Calendario nacional aplicado; validar recepción efectiva y cierres específicos.",
            ),
            (
                "Fecha preliminar: el motor no descuenta festivos.",
                "Calendario nacional aplicado; validar recepción efectiva y cierres específicos.",
            ),
            (
                "Comprobar festivos y reglas especiales antes de afirmar vencimiento o incumplimiento.",
                "Verificar cierres específicos, suspensiones, reglas sectoriales y, cuando corresponda, calendario judicial antes de afirmar vencimiento o incumplimiento.",
            ),
        )
        result = value
        for old, new in replacements:
            result = result.replace(old, new)
        return result
    if isinstance(value, list):
        return [_replace_stale_calendar_phrases(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_stale_calendar_phrases(item) for item in value)
    if isinstance(value, dict):
        return {key: _replace_stale_calendar_phrases(item) for key, item in value.items()}
    return value


def _traceability_section(calculation: dict) -> dict:
    basis = calculation.get("business_day_calendar_basis") or []
    limitations = calculation.get("business_day_calendar_limitations") or []
    return {
        "heading": "IV. TRAZABILIDAD DEL CÓMPUTO NACIONAL",
        "table": [
            ["Control", "Valor"],
            ["Motor de calendario", str(calculation.get("business_day_calendar_engine") or "M33.3")],
            ["Alcance", str(calculation.get("business_day_calendar_scope") or "calendario nacional colombiano")],
            ["Ruleset verificado", _date_es(calculation.get("business_day_calendar_verified_at"))],
            ["Regla de conteo", "Fecha inicial excluida; se cuentan días hábiles posteriores"],
            ["Base jurídica", "; ".join(str(item) for item in basis) or "Requiere verificación"],
        ],
        "paragraphs": [
            "La tabla siguiente permite reconstruir las sumas de días hábiles efectivamente ejecutadas por el motor. La fecha sigue siendo un control jurídico sujeto a las limitaciones expresas del calendario."
        ],
        "tables": [],
        "numbered": [str(item) for item in limitations],
        "audit_table": _audit_table(calculation),
    }


def _materialize_traceability(section: dict) -> list[dict]:
    """Divide la trazabilidad en bloques soportados por el esquema documental."""
    audit_table = section.pop("audit_table", None)
    sections = [section]
    if audit_table:
        sections.append({
            "heading": "V. REGISTRO DE SUMAS HÁBILES",
            "table": audit_table,
        })
    return sections


def finalize_consumer_calendar_m33_3(specs: list[dict], result: dict) -> list[dict]:
    calculation = _calc(result)
    if not calculation.get("holiday_calendar_applied"):
        return specs
    if calculation.get("business_day_calendar_scope") != "colombia_national_holidays":
        return specs

    finalized: list[dict] = []
    for original in specs:
        if original.get("kind") != "consumer_deadline_calendar":
            finalized.append(original)
            continue
        spec = deepcopy(original)
        spec["subtitle"] = "Términos legales · calendario nacional auditado · revisión requerida"
        sections = _replace_stale_calendar_phrases(list(spec.get("sections") or []))
        for section in sections:
            if str(section.get("heading") or "") == "OBJETO Y NATURALEZA DEL CALENDARIO":
                section["paragraphs"] = [
                    "Este calendario reúne los términos asociados con la ruta seleccionada. Los cómputos expresados en días hábiles incorporan fines de semana y festivos nacionales del ruleset colombiano verificado al 10 de agosto de 2026. La fecha continúa siendo preliminar para efectos profesionales: antes de afirmar vencimiento deben verificarse la recepción efectiva, la completitud, cualquier suspensión o cierre específico, el régimen sectorial aplicable y, cuando corresponda, el calendario judicial."
                ]
        headings = {str(section.get("heading") or "") for section in sections if isinstance(section, dict)}
        if "IV. TRAZABILIDAD DEL CÓMPUTO NACIONAL" not in headings:
            sections.extend(_materialize_traceability(_traceability_section(calculation)))
        spec["sections"] = sections
        spec["calendar_standard"] = "M33.3"
        spec["calendar_scope"] = calculation.get("business_day_calendar_scope")
        spec["calendar_ruleset_verified_at"] = calculation.get("business_day_calendar_verified_at")
        finalized.append(spec)
    return finalized


__all__ = ["finalize_consumer_calendar_m33_3"]
