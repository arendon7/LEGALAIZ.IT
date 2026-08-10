from __future__ import annotations

"""Cierre estilístico del instrumento laboral CO-LA-002 M33.0/M33.4.

No altera reglas ni módulos sustantivos. Corrige únicamente concordancia,
contracciones y consistencia de términos definidos visibles. M33.4 incorpora antes
de esta capa el manifiesto normativo auditable y mantiene su control fuera del
instrumento firmable.
"""

from copy import deepcopy
from typing import Any

from m33_4_employment_source_finalize import compose_employment_m33_release


def _polish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    replacements = (
        (
            "La entrega de un equipo empresarial o el uso de una red corporativa no elimina por sí solos toda expectativa legítima de privacidad.",
            "Ni la entrega de un equipo empresarial ni el uso de una red corporativa eliminan por sí solos toda expectativa legítima de privacidad.",
        ),
        ("al trabajador", "a LA PERSONA TRABAJADORA"),
        ("del trabajador", "de LA PERSONA TRABAJADORA"),
        ("El trabajador", "LA PERSONA TRABAJADORA"),
        ("el trabajador", "LA PERSONA TRABAJADORA"),
        ("al empleador", "al EMPLEADOR"),
        ("del empleador", "del EMPLEADOR"),
        ("El empleador", "EL EMPLEADOR"),
        ("el empleador", "EL EMPLEADOR"),
        ("a EL EMPLEADOR", "al EMPLEADOR"),
        ("de EL EMPLEADOR", "del EMPLEADOR"),
    )
    text = value
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _section(section: dict) -> dict:
    result = deepcopy(section)
    if result.get("_type") == "control":
        return result
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _polish(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_polish(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_polish(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        result["parties"] = [
            {key: _polish(value) for key, value in party.items()} if isinstance(party, dict) else party
            for party in result["parties"]
        ]
    return result


def compose_employment_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_employment_m33_release(answers))
    composition["sections"] = [_section(item) for item in composition.get("sections") or []]
    composition.setdefault("maturity_answers", {})["employment_instrument_finalized"] = True
    return composition


__all__ = ["compose_employment_m33_instrument"]
