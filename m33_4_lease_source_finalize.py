from __future__ import annotations

"""Trazabilidad normativa M33.4 para CO-AR-001.

La capa se ejecuta después del pulido visible M33.0. Añade metadatos auditables y
actualiza exclusivamente la sección interna de control. La guardia sustantiva de
terminación corrige únicamente las rutas imperativas verificadas de los artículos
22 a 26 antes de construir el manifiesto de fuentes.
"""

from copy import deepcopy
from typing import Any

from legalai_platform.lease_legal_source_pack import LEASE_SOURCE_IDS
from legalai_platform.legal_source_registry import (
    build_legal_source_manifest,
    source_control_lines,
)
from m33_4_lease_termination_guard import finalize_lease_termination_routes
from m33_lease_release_polish import compose_lease_m33_release as compose_lease_m33_release_base


def compose_lease_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_lease_m33_release_base(answers))
    composition = finalize_lease_termination_routes(composition)
    manifest = build_legal_source_manifest(LEASE_SOURCE_IDS)

    controls = 0
    for section in composition.get("sections") or []:
        if section.get("_type") != "control":
            continue
        controls += 1
        section["source_ids"] = list(LEASE_SOURCE_IDS)
        section["source_manifest_status"] = manifest["status"]
        section["bullets"] = source_control_lines(LEASE_SOURCE_IDS)
        section["text"] = (
            "Documento candidato interno CO-AR-001 M33.4. Antes de liberar deben verificarse identidad y capacidad, "
            "titularidad o facultad para arrendar, clasificación real, inmueble, canon y soportes de valor, servicios, "
            "administración, garantías, inventario, comunicaciones, módulos condicionales y rutas de terminación, "
            "incluidos preavisos, indemnizaciones, consignaciones, cauciones y el derecho de retención cuando aplique. "
            "Las fuentes jurídicas se encuentran estructuradas en un manifiesto de trazabilidad; si su estado es "
            "needs_reverification, la liberación debe bloquearse hasta una nueva verificación oficial. La aprobación "
            "jurídica y QA deben recaer sobre la misma revisión y hash."
        )

    if controls != 1:
        raise ValueError(f"M33.4 CO-AR-001: se esperaba exactamente un control interno y se encontraron {controls}")

    composition["legal_source_manifest"] = manifest
    maturity = composition.setdefault("maturity_answers", {})
    maturity["legal_source_standard"] = "M33.4"
    maturity["legal_source_gate_m334"] = manifest["status"]
    maturity["legal_source_ids_m334"] = list(LEASE_SOURCE_IDS)
    return composition


__all__ = ["compose_lease_m33_release"]
