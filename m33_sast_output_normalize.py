from __future__ import annotations

"""Normaliza la salida viva de CO-TR-001 a siete piezas canónicas M33.

La composición histórica SAST conserva varios `kind` heredados que son absorbidos
por las siete piezas M33.0. Tras la reclasificación jurídica algunos de esos
heredados pueden converger sobre el mismo `kind` canónico. Esta capa elimina solo
esas duplicidades de salida; no elimina generadores históricos ni evidencia interna.
"""

from copy import deepcopy
from typing import Any


SAST_CANONICAL_ORDER = (
    "sast_report",
    "sast_traceability",
    "sast_registration",
    "sast_record_request",
    "sast_inspection",
    "sast_followup",
    "sast_package",
)

SAST_CANONICAL_SUFFIXES = {
    "sast_report": "informe_sast",
    "sast_traceability": "trazabilidad_sast",
    "sast_registration": "inscripcion_sast",
    "sast_record_request": "expediente_sast",
    "sast_inspection": "revision_sast",
    "sast_followup": "seguimiento_sast",
    "sast_package": "paquete_sast",
}

SAST_LEGACY_ABSORBED_KINDS = {
    "sast_verification_matrix",
    "sast_supertransport_request",
    "sast_conditional_review",
    "sast_alert_registry",
    "sast_route_guide",
}


def _stable_key(value: Any) -> str:
    return repr(value)


def _merge_internal_sections(primary: dict, duplicate: dict) -> None:
    merged = deepcopy(primary.get("internal_review_sections") or [])
    seen = {_stable_key(section) for section in merged}
    for section in duplicate.get("internal_review_sections") or []:
        key = _stable_key(section)
        if key in seen:
            continue
        merged.append(deepcopy(section))
        seen.add(key)
    if merged:
        primary["internal_review_sections"] = merged


def normalize_sast_outputs(specs: list[dict]) -> list[dict]:
    """Devuelve exactamente una salida por cada pieza SAST canónica.

    Falla cerrado si falta una pieza canónica. Los `kind` históricos absorbidos se
    retiran únicamente de la salida viva porque su contenido ya fue recompuesto por
    `finalize_sast_specs`; sus generadores históricos permanecen intactos en código.
    """
    selected: dict[str, dict] = {}
    passthrough: list[dict] = []

    for original in deepcopy(specs):
        kind = str(original.get("kind") or "")
        if kind in SAST_CANONICAL_ORDER:
            original["filename_suffix"] = SAST_CANONICAL_SUFFIXES[kind]
            if kind not in selected:
                selected[kind] = original
            else:
                _merge_internal_sections(selected[kind], original)
            continue
        if kind in SAST_LEGACY_ABSORBED_KINDS:
            continue
        passthrough.append(original)

    missing = [kind for kind in SAST_CANONICAL_ORDER if kind not in selected]
    if missing:
        raise ValueError(f"M33 SAST: faltan piezas canónicas después de normalizar: {missing}")

    canonical = [selected[kind] for kind in SAST_CANONICAL_ORDER]
    return passthrough + canonical


__all__ = [
    "SAST_CANONICAL_ORDER",
    "SAST_CANONICAL_SUFFIXES",
    "SAST_LEGACY_ABSORBED_KINDS",
    "normalize_sast_outputs",
]
