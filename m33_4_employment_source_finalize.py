from __future__ import annotations

"""Trazabilidad normativa M33.4 para CO-LA-002."""

from copy import deepcopy
from typing import Any

from legalai_platform.employment_legal_source_pack import EMPLOYMENT_SOURCE_IDS
from legalai_platform.legal_source_registry import (
    build_legal_source_manifest,
    source_control_lines,
)
from m33_employment_release_polish import compose_employment_m33_release as compose_employment_m33_release_base


def compose_employment_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_employment_m33_release_base(answers))
    manifest = build_legal_source_manifest(EMPLOYMENT_SOURCE_IDS)

    controls = 0
    for section in composition.get("sections") or []:
        if section.get("_type") != "control":
            continue
        controls += 1
        section["source_ids"] = list(EMPLOYMENT_SOURCE_IDS)
        section["source_manifest_status"] = manifest["status"]
        section["bullets"] = source_control_lines(EMPLOYMENT_SOURCE_IDS)
        section["text"] = (
            "Documento candidato interno CO-LA-002 M33.4. Antes de liberar deben verificarse modalidad contractual, "
            "fecha efectiva de inicio, jornada, distribución, salario, recargos, funciones, lugar y modalidad de trabajo, "
            "seguridad social, SG-SST, debido proceso, desconexión, datos personales y módulos condicionales. Las fuentes "
            "jurídicas están estructuradas en un manifiesto temporal; needs_reverification bloquea la liberación hasta "
            "una nueva verificación oficial. La aprobación jurídica y QA deben recaer sobre la misma revisión y hash."
        )

    if controls != 1:
        raise ValueError(f"M33.4 CO-LA-002: se esperaba exactamente un control interno y se encontraron {controls}")

    composition["legal_source_manifest"] = manifest
    maturity = composition.setdefault("maturity_answers", {})
    maturity["legal_source_standard"] = "M33.4"
    maturity["legal_source_gate_m334"] = manifest["status"]
    maturity["legal_source_ids_m334"] = list(EMPLOYMENT_SOURCE_IDS)
    return composition


__all__ = ["compose_employment_m33_release"]
