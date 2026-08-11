from __future__ import annotations

"""Trazabilidad normativa interna M33.4 para CO-CD-001.

Se ejecuta después de las compuertas M33.3. No modifica secciones públicas: adjunta
manifiestos por pieza y un control exclusivamente interno para revisión jurídica/QA.
"""

from copy import deepcopy

from legalai_platform.habeas_data_legal_source_pack import HABEAS_KINDS, habeas_source_ids
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_habeas_source_control"


def _calculation(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def finalize_habeas_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Añade trazabilidad M33.4 sin cambiar el instrumento que recibe el cliente."""
    if (result or {}).get("risk") == "red":
        return specs

    calculation = _calculation(result)
    transition_phase = str(calculation.get("law2573_transition_phase") or "not_calculated")
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in HABEAS_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        source_ids = habeas_source_ids(kind)
        manifest = build_legal_source_manifest(source_ids)
        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS M33.4 — CO-CD-001",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "bullets": source_control_lines(source_ids),
            "text": (
                "Control interno de trazabilidad normativa. Las fuentes se verificaron contra repositorios oficiales y "
                "su vigencia/aplicabilidad debe revalidarse antes de liberar. La Ley 2573 de 2026 se trata con control "
                "temporal: su régimen general no se anticipa antes del 20 de noviembre de 2026; durante la ventana "
                "transitoria solo se modelan como inmediatamente vigentes los parágrafos 1 y 2 del artículo 5. "
                "Las decisiones administrativas SIC se registran con su alcance propio y no se convierten en precedente "
                "judicial ni en regla general autónoma. Aprobación jurídica y QA permanecen pendientes sobre la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["legal_source_temporal_context_m334"] = {
            "law2573_transition_phase": transition_phase,
            "law2573_general_effective_date": "2026-11-20",
            "law2573_pre_general_rule": "article5_paragraphs_1_and_2_only",
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_habeas_sources_m33_4"]
