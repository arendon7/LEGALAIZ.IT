from __future__ import annotations

"""Higiene editorial de la copia pública M33.

La metadata técnica y de auditoría puede conservar nombres de estándares internos,
pero el instrumento que recibe el usuario no debe exponer nomenclatura de ingeniería
como ``M33.x`` o ``ruleset``. Esta capa solo transforma texto de ``sections`` y no
modifica controles internos, manifiestos, compuertas, hechos, fechas ni resultados.

Las sustituciones son deliberadamente exactas. Una nueva fuga desconocida debe ser
detectada por CI en vez de ser ocultada mediante una limpieza genérica.
"""

from copy import deepcopy
from typing import Any


_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (
        "M33.3 separa la permanencia del dato de la existencia de la obligación.",
        "El control temporal separa la permanencia del dato de la existencia de la obligación.",
    ),
    ("Control M33.3 de comunicación previa:", "Control de comunicación previa:"),
    ("Fecha aplicable / corte M33.3", "Fecha aplicable / fecha de corte"),
    ("Trazabilidad M33.3:", "Trazabilidad del cómputo:"),
    ("corte regulatorio M33.3", "corte regulatorio del expediente"),
    ("Calendario nacional M33.3 · verificado", "Calendario nacional verificado"),
    ("Referencia subsidiaria M33.3 (", "Referencia subsidiaria ("),
    ("ruleset colombiano verificado", "calendario normativo colombiano verificado"),
    ("ruleset verificado", "calendario normativo verificado"),
    ("; ruleset ", "; calendario normativo verificado: "),
    ("Ruleset", "Conjunto de reglas"),
    (
        "evidencia estructurada conservada por el motor",
        "evidencia estructurada conservada en el expediente",
    ),
    ("modelo determinístico de cálculo vigente", "método determinístico de cálculo vigente"),
    ("4. RESULTADO PRELIMINAR DEL MOTOR", "4. RESULTADO PRELIMINAR DEL CÁLCULO"),
    ("5. BASES, PERÍODOS Y CONTROLES DEL MOTOR", "5. BASES, PERÍODOS Y CONTROLES DEL CÁLCULO"),
    ("ANEXO No. 1 — MATRICES DEL MOTOR DE LIQUIDACIÓN", "ANEXO No. 1 — MATRICES DE LIQUIDACIÓN"),
    ("motor determinístico vigente", "método de cálculo determinístico vigente"),
    ("Según motor", "Según cálculo"),
)

_LABOR_ENGINE_KINDS = {"labor_diagnostic", "calculation"}
_LABOR_ENGINE_ROW_LABELS = {"motor", "versión del motor"}
_LABOR_METHOD_LABEL = "Método de cálculo"
_LABOR_METHOD_VALUE = "Liquidación determinística reproducible con trazabilidad por concepto"


def _sanitize(value: Any, *, document_kind: str = "") -> Any:
    if isinstance(value, str):
        result = value
        for old, new in _REPLACEMENTS:
            result = result.replace(old, new)
        return result
    if isinstance(value, list):
        if (
            document_kind in _LABOR_ENGINE_KINDS
            and len(value) >= 2
            and isinstance(value[0], str)
            and value[0].strip().casefold() in _LABOR_ENGINE_ROW_LABELS
        ):
            row = list(value)
            row[0] = _LABOR_METHOD_LABEL
            row[1] = _LABOR_METHOD_VALUE
            return [_sanitize(item, document_kind=document_kind) for item in row]
        return [_sanitize(item, document_kind=document_kind) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item, document_kind=document_kind) for item in value)
    if isinstance(value, dict):
        return {key: _sanitize(item, document_kind=document_kind) for key, item in value.items()}
    return value


def finalize_public_presentation_hygiene(specs: list[dict]) -> list[dict]:
    """Devuelve specs equivalentes con higiene aplicada solo a secciones públicas."""
    finalized: list[dict] = []
    for original in specs:
        spec = deepcopy(original)
        document_kind = str(spec.get("kind") or "")
        spec["sections"] = _sanitize(spec.get("sections") or [], document_kind=document_kind)
        finalized.append(spec)
    return finalized


__all__ = ["finalize_public_presentation_hygiene"]
