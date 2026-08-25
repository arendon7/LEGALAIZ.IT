from __future__ import annotations

"""Capa M33.4 posterior al instrumento visible CO-EM-004.

No reescribe cláusulas públicas. Añade únicamente manifiesto normativo, metadatos de
madurez y control interno externalizable después de que M33.0 haya cerrado el texto
que revisan y firman las partes.
"""

from copy import deepcopy
from typing import Any

from legalai_platform.nda_legal_source_pack import nda_source_ids
from legalai_platform.legal_source_registry import (
    build_legal_source_manifest,
    source_control_lines,
)
from m33_nda_instrument_finalize import compose_nda_m33_instrument as compose_nda_m33_instrument_base


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def compose_nda_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_nda_m33_instrument_base(answers))
    personal_data = bool(_read(answers, "data.personal", False))
    ai_used = bool(_read(answers, "ai.used", False))
    source_ids = nda_source_ids(personal_data=personal_data)
    manifest = build_legal_source_manifest(source_ids)

    controls = 0
    for section in composition.get("sections") or []:
        if section.get("_type") != "control":
            continue
        controls += 1
        section["source_ids"] = list(source_ids)
        section["source_manifest_status"] = manifest["status"]
        section["bullets"] = source_control_lines(source_ids)
        section["text"] = (
            "Documento candidato interno CO-EM-004 M33.4. Antes de liberar deben verificarse identidad y facultades, "
            "finalidad, información protegida, calidad real de secreto empresarial, medidas razonables, accesos, "
            "terceros, seguridad, incidentes, PI preexistente, resultados, licencias, duración y cierre. "
            + (
                "El módulo de datos personales está activo y exige revisar roles, finalidades, instrucciones, terceros, "
                "transferencias o transmisiones, conservación y atención de derechos. "
                if personal_data else
                "El módulo de datos personales no está activo con los hechos suministrados y no se presume. "
            )
            + (
                "El módulo de IA está activo como control contractual y de riesgo; no se infiere una ley general autónoma de IA y su análisis debe anclarse a las normas realmente aplicables a la operación. "
                if ai_used else
                "No se ha activado un módulo de IA con los hechos suministrados. "
            )
            + "Las fuentes jurídicas están estructuradas en un manifiesto temporal; needs_reverification bloquea la liberación hasta nueva verificación oficial. La aprobación jurídica y QA deben recaer sobre la misma revisión y hash."
        )

    if controls != 1:
        raise ValueError(f"M33.4 CO-EM-004: se esperaba exactamente un control interno y se encontraron {controls}")

    composition["legal_source_manifest"] = manifest
    maturity = composition.setdefault("maturity_answers", {})
    maturity["legal_source_standard"] = "M33.4"
    maturity["legal_source_gate_m334"] = manifest["status"]
    maturity["legal_source_ids_m334"] = list(source_ids)
    maturity["ai_legal_source_model_m334"] = "applicable-law-only; no_general_ai_law_inferred"
    return composition


__all__ = ["compose_nda_m33_instrument"]
