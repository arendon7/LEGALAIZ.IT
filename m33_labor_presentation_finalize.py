from __future__ import annotations

"""Pulido visual del informe CO-LA-001 después del cierre jurídico/probatorio.

No recalcula valores ni altera solicitudes. Se limita a presentar las mismas variables
en tablas de ancho razonable, evitar saltos de página forzados y compactar el control
interno sin perder sus fuentes ni alertas jurídicas.
"""

from copy import deepcopy
from typing import Any

from premium_document_engine import format_cop


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _value(value: Any, fallback: str = "No confirmado en esta revisión") -> str:
    if value in (None, "", [], {}):
        return fallback
    return str(value)


def _money(value: Any) -> str:
    try:
        return format_cop(float(value or 0), include_words=False)
    except Exception:
        return "Valor no determinado"


def _line_context(item: dict, calculation: dict) -> tuple[str, str]:
    key = str(item.get("key") or "").strip().casefold()
    if key == "cesantias":
        return _value(calculation.get("cesantias_days")), _money(calculation.get("cesantias_base"))
    if key == "intereses_cesantias":
        return _value(calculation.get("cesantias_days")), "Cesantías causadas en esta revisión"
    if key == "prima":
        return _value(calculation.get("prima_days")), _money(calculation.get("prima_base"))
    if key == "vacaciones":
        return _value(calculation.get("vacation_pending_days")), _money(calculation.get("vacation_base"))
    if key == "indemnizacion":
        return _value(calculation.get("indemnity_days")), _money(calculation.get("indemnity_base"))
    return "Según motor", "Según motor"


def _is_heading(section: dict, fragment: str) -> bool:
    return fragment.casefold() in str(section.get("heading") or "").casefold()


def _polish_calculation(spec: dict, answers: dict, result: dict) -> dict:
    c = _calc(result)
    line_items = list(c.get("line_items") or [])
    sections: list[dict] = []

    money_rows = [["Concepto", "Bruto", "Pagado", "Saldo"]]
    formula_rows = [["Concepto", "Días / parámetro", "Base", "Fórmula o criterio"]]
    for item in line_items:
        concept = _value(item.get("label") or item.get("key"))
        days, base = _line_context(item, c)
        money_rows.append([
            concept,
            _money(item.get("gross")),
            _money(item.get("prior_paid")),
            _money(item.get("net")),
        ])
        formula_rows.append([
            concept,
            days,
            base,
            _value(item.get("formula")),
        ])

    for source in spec.get("sections") or []:
        section = deepcopy(source)

        if _is_heading(section, "2. DATOS UTILIZADOS EN ESTA REVISIÓN"):
            old = section.get("table") or []
            compact = [["Variable", "Dato utilizado"]]
            for row in old[1:]:
                if isinstance(row, list) and len(row) >= 2:
                    compact.append([str(row[0]), str(row[1])])
            section["table"] = compact
            section["bullets"] = [
                "Identidad, denominación del empleador y fechas: cotejar contra documentos fuente y la ejecución real de la relación.",
                "Modalidad y causa de terminación: verificar el instrumento contractual, las comunicaciones y los hechos efectivamente acreditados.",
                "Salario y auxilio de transporte: cotejar contra nómina, comprobantes y reglas de incidencia aplicables a cada concepto.",
            ]

        elif _is_heading(section, "3. LIQUIDACIÓN REPRODUCIBLE POR CONCEPTO"):
            section["table"] = money_rows if len(money_rows) > 1 else [["Concepto", "Estado"], ["Liquidación", "Sin líneas suficientes"]]
            sections.append(section)
            sections.append({
                "heading": "3.1 BASES, DÍAS Y FÓRMULAS DE CADA CONCEPTO",
                "paragraphs": [
                    "La siguiente tabla separa la explicación matemática de la tabla de saldos para que cada línea pueda revisarse sin comprimir valores monetarios, bases y fórmulas en una sola fila de siete columnas."
                ],
                "table": formula_rows if len(formula_rows) > 1 else [["Concepto", "Estado"], ["Liquidación", "Sin líneas suficientes"]],
            })
            continue

        elif _is_heading(section, "ANEXO No. 1 — TRAZA REPRODUCIBLE"):
            section.pop("page_break_before", None)
            section["paragraphs"] = [
                "Este anexo reproduce exclusivamente las variables y resultados de la misma revisión que sustenta el cuerpo del informe. No incorpora matrices históricas vacías ni una segunda capa de datos que pueda contradecir el cálculo vigente."
            ]

        elif section.get("_type") == "control":
            section["text"] = (
                "Control interno: antes de liberar esta revisión deben cotejarse los soportes de la relación, la vigencia normativa y la aprobación jurídica y QA sobre el mismo hash."
            )
            section["bullets"] = [
                "Fuentes de control: Código Sustantivo del Trabajo, artículos 64, 186, 249, 306, 488 y 489; Ley 52 de 1975, artículo 1; y Ley 2466 de 2025, artículo 62.",
                "No automatizar sin análisis individual: indemnización moratoria, estabilidad laboral reforzada, fueros, contrato realidad, sanciones, perjuicios o indexaciones.",
            ]

        sections.append(section)

    spec["sections"] = sections
    return spec


def finalize_labor_presentation(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    if str((result or {}).get("risk") or "").casefold() == "red":
        return specs
    output = deepcopy(specs)
    for index, spec in enumerate(output):
        if spec.get("kind") == "calculation":
            output[index] = _polish_calculation(spec, answers, result)
    return output


__all__ = ["finalize_labor_presentation"]
