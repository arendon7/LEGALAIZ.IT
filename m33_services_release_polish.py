from __future__ import annotations

"""Pulido final del instrumento CO-EM-003 M33.0.

Conserva intactos los módulos internos de fuentes y gobierno para que la evidencia
jurídica siga disponible en el manifiesto, pero corrige lenguaje y gramática del
instrumento que posteriormente separa `build_m33_presentation`.
"""

from copy import deepcopy
from typing import Any

from m33_services_instrument_finalize import compose_services_m33_instrument


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _polish_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value
    replacements = (
        ("millones pesos moneda corriente", "millones de pesos moneda corriente"),
        ("millón pesos moneda corriente", "millón de pesos moneda corriente"),
        ("Bogotá D.C..", "Bogotá D.C."),
        ("Medellín, Antioquia..", "Medellín, Antioquia."),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _polish_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _polish_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_polish_text(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_polish_text(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        polished = []
        for party in result["parties"]:
            if isinstance(party, dict):
                polished.append({key: _polish_text(value) for key, value in party.items()})
            else:
                polished.append(party)
        result["parties"] = polished
    return result


def _scope_phrase(value: str) -> str:
    text = str(value or "").strip().rstrip(".")
    lowered = text.casefold()
    prefixes = (
        "prestar servicios independientes de ",
        "prestar servicios profesionales independientes de ",
        "prestar servicios profesionales de ",
        "prestar servicios de ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return "actividades de " + text[len(prefix):]
    return text or "las actividades especializadas definidas en el contrato"


def _result_phrase(value: str) -> str:
    text = str(value or "").strip().rstrip(".")
    if not text:
        return "los resultados verificables definidos en la matriz de entregables"
    lowered = text.casefold()
    if lowered.startswith("entregar "):
        return "la entrega de " + text[len("entregar "):]
    return text


def compose_services_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_services_m33_instrument(answers))
    scope = _scope_phrase(_read(answers, "service.object", ""))
    result = _result_phrase(_read(answers, "service.expected_result", ""))

    sections: list[dict] = []
    for original in composition.get("sections") or []:
        section = _polish_section(original)
        heading_cf = str(section.get("heading") or "").strip().casefold()

        if heading_cf == "consideraciones":
            paragraphs = list(section.get("paragraphs") or [])
            if paragraphs:
                paragraphs[0] = (
                    f"PRIMERA: EL CONTRATANTE ha identificado una necesidad especializada relacionada con {scope}, "
                    "cuya atención se pretende estructurar por resultados verificables y no mediante la provisión "
                    "permanente de un cargo sometido a subordinación laboral."
                )
            section["paragraphs"] = paragraphs

        elif heading_cf == "1. objetivo operativo":
            section.pop("text", None)
            section["paragraphs"] = [
                f"El objetivo operativo del encargo consiste en ejecutar {scope}. El resultado verificable esperado "
                f"corresponde a {result}. Las actividades del anexo constituyen medios para alcanzar ese resultado y "
                "no una autorización abierta para incorporar trabajos ajenos al objeto, exigir disponibilidad permanente "
                "o modificar informalmente el alcance, el precio, el plazo o la distribución de riesgos."
            ]

        sections.append(section)

    composition["sections"] = sections
    composition.setdefault("maturity_answers", {})["services_release_polished"] = True
    return composition


__all__ = ["compose_services_m33_release"]
