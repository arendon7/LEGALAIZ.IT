from __future__ import annotations

"""Pulido final y guardia sustantiva del instrumento CO-EM-003.

Conserva intactos los módulos internos de fuentes y gobierno para que la evidencia
jurídica siga disponible en el manifiesto. Para contratistas persona jurídica, además
separa expresamente el vínculo comercial entre las sociedades de cualquier eventual
relación laboral real de las personas naturales que intervengan en la ejecución y
preserva las responsabilidades imperativas frente al personal del contratista.
"""

from copy import deepcopy
from typing import Any

from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines
from legalai_platform.services_substantive_source_pack import SERVICES_SUBSTANTIVE_SOURCE_IDS
from m33_services_instrument_finalize import compose_services_m33_instrument
from m38_8_services_fact_fidelity import apply_services_fact_fidelity


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _nature(answers: dict) -> str:
    raw = str(_read(answers, "contractor.identification.type", "") or "").strip().casefold()
    if raw in {"legal_person", "persona jurídica", "persona juridica", "persona_juridica", "company", "corporation", "sas", "s.a.s."}:
        return "legal_person"
    if raw in {"natural_person", "persona natural", "persona_natural", "natural", "individual"}:
        return "natural_person"
    return "unconfirmed"


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


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraphs(section: dict, *values: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [value for value in values if str(value or "").strip()]


def _legal_person_guard(section: dict) -> None:
    heading = str(section.get("heading") or "").strip()
    heading_cf = heading.casefold()

    if heading_cf.startswith("contrato de prestación de servicios"):
        paragraphs = list(section.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = paragraphs[0].replace(
                "y que la naturaleza jurídica del vínculo será determinada por la realidad de su ejecución.",
                "y que este instrumento regula un vínculo comercial entre las personas jurídicas comparecientes, sin perjuicio de que las relaciones reales de las personas naturales que intervengan en la ejecución se califiquen conforme a las normas laborales imperativas.",
            )
        section["paragraphs"] = paragraphs

    elif _has(section, "PREVENCIÓN DEL RIESGO DE LABORALIDAD"):
        _paragraphs(
            section,
            "EL CONTRATISTA es una persona jurídica y, por tanto, no ostenta la condición de trabajador prevista para la persona natural que presta personalmente un servicio bajo los presupuestos de los artículos 22 y 23 del Código Sustantivo del Trabajo. El presente contrato regula una relación comercial entre las partes y su autonomía se ejecutará con los medios, organización, riesgos y libertad técnica y directiva que correspondan al contratista conforme a la ley.",
            "Lo anterior no autoriza utilizar la estructura contractual para encubrir relaciones laborales reales de las personas naturales que participen en la ejecución. Respecto de cada una de ellas deberán examinarse los hechos concretos y, si concurren prestación personal, subordinación continuada y remuneración en los términos legales, la denominación comercial del contrato no desplazará las normas laborales imperativas. La coordinación por resultados, seguridad, acceso, calidad o cronograma no equivale por sí sola a subordinación, pero tampoco podrá usarse para justificar potestad disciplinaria, disponibilidad personal permanente u órdenes continuas sobre modo, tiempo o cantidad de trabajo de personal ajeno.",
            "La autonomía contractual tampoco excluye la solidaridad o las demás responsabilidades que imperativamente puedan corresponder a quien contrata o subcontrata obras o servicios respecto de los trabajadores del contratista o subcontratista. Su procedencia deberá determinarse según el artículo 34 del Código Sustantivo del Trabajo vigente, la relación entre las labores ejecutadas y las actividades normales de la empresa o negocio y los hechos probados del caso.",
        )

    elif _has(section, "SEGURIDAD SOCIAL DEL CONTRATISTA"):
        _paragraphs(
            section,
            "EL CONTRATISTA es una persona jurídica. El valor de este contrato no constituye por sí mismo un ingreso base de cotización personal ni se le aplica una regla de cotización diseñada para determinadas personas naturales independientes. EL CONTRATISTA responderá, según cada relación jurídica real, por la afiliación, cotización, nómina, riesgos laborales y demás obligaciones respecto de sus trabajadores, contratistas y subcontratistas; EL CONTRATANTE conservará los deberes de verificación y coordinación que legalmente le correspondan frente al personal que participe en la ejecución.",
            "La asignación contractual anterior no constituye renuncia, exclusión ni limitación de la solidaridad o de otras responsabilidades imperativas que puedan resultar aplicables al CONTRATANTE frente a trabajadores del contratista o subcontratista. Tampoco convierte por sí sola a EL CONTRATANTE en empleador directo: cada consecuencia dependerá de la norma aplicable y de los hechos reales de ejecución.",
        )

    elif _has(section, "VERIFICACIÓN DE APORTES"):
        _paragraphs(
            section,
            "Cuando sea jurídicamente procedente, EL CONTRATANTE podrá solicitar soportes razonables y minimizados sobre el cumplimiento laboral, de seguridad social y de riesgos del personal efectivamente destinado a la ejecución, sin asumir por ese solo hecho dirección del personal ajeno. La revisión se limitará a personas y periodos pertinentes, protegerá los datos personales y permitirá documentar alertas, subsanaciones y medidas de control.",
            "La verificación no desplaza las obligaciones primarias de EL CONTRATISTA como empleador o contratante ni crea por sí sola una relación laboral directa con EL CONTRATANTE. Sin embargo, ninguna estipulación de este contrato podrá interpretarse como exclusión de la solidaridad prevista en el artículo 34 del Código Sustantivo del Trabajo o de otra responsabilidad imperativa que resulte aplicable conforme a los hechos.",
        )


def compose_services_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_services_m33_instrument(answers))
    scope = _scope_phrase(_read(answers, "service.object", ""))
    result = _result_phrase(_read(answers, "service.expected_result", ""))
    nature = _nature(answers)

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

        if nature == "legal_person":
            _legal_person_guard(section)

        sections.append(section)

    source_ids = list((composition.get("legal_source_manifest") or {}).get("source_ids") or [])
    source_ids.extend(SERVICES_SUBSTANTIVE_SOURCE_IDS)
    source_ids = list(dict.fromkeys(source_ids))
    manifest = build_legal_source_manifest(source_ids)
    for section in sections:
        if section.get("_type") == "control":
            section["source_ids"] = list(source_ids)
            section["source_manifest_status"] = manifest["status"]
            section["bullets"] = source_control_lines(source_ids)

    composition["sections"] = sections
    composition["legal_source_manifest"] = manifest
    maturity = composition.setdefault("maturity_answers", {})
    maturity["services_release_polished"] = True
    maturity["services_substantive_review"] = "2026-08-11"
    maturity["services_substantive_source_ids"] = list(SERVICES_SUBSTANTIVE_SOURCE_IDS)
    if nature == "legal_person":
        maturity["contractor_legal_person_framework"] = "commercial_contract_with_personnel_labor_safeguards"
    return apply_services_fact_fidelity(composition, answers)


__all__ = ["compose_services_m33_release"]
