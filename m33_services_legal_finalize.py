from __future__ import annotations

"""Cierre de QA jurídico para el contrato patrón CO-EM-003 M33.0.

Esta capa finaliza la segunda pasada de revisión: aplica encabezados reales de la
biblioteca, elimina módulos inactivos, corrige prosa residual y renumera las
cláusulas después de la composición condicional. No altera versiones históricas.
"""

from copy import deepcopy
import re
from typing import Any

from legalai_platform.contractual_maturity import ORDINALS
from m33_services_legal_review import compose_services_m33_reviewed


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"sí", "si", "true", "1", "yes"}


def _nature(answers: dict) -> str:
    raw = str(_read(answers, "contractor.identification.type", "") or "").strip().casefold()
    if raw in {"natural_person", "persona natural", "persona_natural", "natural", "individual"}:
        return "natural_person"
    if raw in {"legal_person", "persona jurídica", "persona juridica", "persona_juridica", "company", "corporation", "sas", "s.a.s."}:
        return "legal_person"
    return "unconfirmed"


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


def _clean_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = value.replace("los actividades de ", "las actividades de ")
    value = value.replace("los actividades consistentes en ", "las actividades consistentes en ")
    return value


def _clean_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _clean_value(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_clean_value(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_clean_value(cell) for cell in row] for row in result["table"]]
    return result


def _clean_considerations(section: dict) -> None:
    if str(section.get("heading") or "").strip().casefold() != "consideraciones":
        return
    cleaned = []
    for paragraph in section.get("paragraphs") or []:
        text = str(paragraph)
        text = re.sub(r"^([^:]+):\s+Que\s+", r"\1: ", text, flags=re.IGNORECASE)
        cleaned.append(text)
    section["paragraphs"] = cleaned


def _renumber_clauses(sections: list[dict]) -> list[dict]:
    number = 0
    for section in sections:
        if section.get("_type") != "clause":
            continue
        number += 1
        heading = str(section.get("heading") or "").strip()
        title = heading.split(":", 1)[1].strip() if ":" in heading else heading
        ordinal = ORDINALS[number - 1] if number <= len(ORDINALS) else str(number)
        section["heading"] = f"{ordinal}: {title.upper()}"
        section["clause_number"] = number
    return sections


def compose_services_m33_final(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_services_m33_reviewed(answers))
    nature = _nature(answers)
    ai_used = _bool(_read(answers, "ai.used", False))
    liability_cap = _read(answers, "risk.liability_cap", _read(answers, "risk.cap", None))
    final: list[dict] = []

    for original in composition.get("sections") or []:
        section = _clean_section(original)
        _clean_considerations(section)

        if _has(section, "INTELIGENCIA ARTIFICIAL"):
            if not ai_used:
                continue
            _paragraph(section, "El uso de inteligencia artificial o servicios en nube solo se autoriza para finalidades documentadas y mediante herramientas aprobadas. Antes de cargar información se verificará proveedor, ubicación y retención de datos, uso para entrenamiento, subprocesadores, transferencias internacionales, controles de acceso y eliminación. No se introducirán secretos, datos personales o información reservada en servicios públicos o no aprobados. Los resultados automatizados deberán ser revisados por una persona competente antes de incorporarse a entregables o decisiones de impacto jurídico, técnico, financiero o de seguridad.")

        elif _has(section, "DATOS PERSONALES") and section.get("_type") == "clause":
            _paragraph(section, "Cuando la ejecución implique datos personales, cada actividad deberá identificar finalidad, categorías de datos y titulares, calidad de responsable o encargado, instrucciones documentadas, base jurídica, medidas de seguridad, plazo de conservación y destinatarios. Si EL CONTRATISTA actúa como encargado, el anexo de tratamiento deberá regular confidencialidad, personal autorizado, subencargados, transmisión o transferencia internacional, atención de derechos, incidentes, auditoría razonable y devolución o eliminación al cierre. La confidencialidad contractual no sustituye las obligaciones de la Ley 1581 de 2012 y su reglamentación.")

        elif _has(section, "RESPONSABILIDAD") and section.get("_type") == "clause":
            if liability_cap not in (None, "", 0, "0"):
                _paragraph(section, f"Cada parte responderá por daños directos, ciertos, demostrables y causalmente atribuibles a su incumplimiento. El límite cuantitativo pactado para los eventos jurídicamente limitables es {liability_cap}; no cubrirá dolo, culpa grave ni responsabilidades que por norma imperativa no puedan limitarse. Datos, confidencialidad, propiedad intelectual, personal, seguridad e indemnidad frente a terceros se regirán además por sus cláusulas específicas.")
            else:
                _paragraph(section, "Cada parte responderá por daños directos, ciertos, demostrables y causalmente atribuibles a su incumplimiento conforme al régimen legal y a las asignaciones específicas del contrato. En esta versión no se pacta un límite cuantitativo general de responsabilidad; ninguna referencia a límites contractuales podrá interpretarse como un tope inexistente. No se excluyen dolo, culpa grave ni responsabilidades que por norma imperativa no puedan limitarse.")

        elif nature == "legal_person" and _has(section, "SEGURIDAD SOCIAL DEL CONTRATISTA"):
            _paragraph(section, "EL CONTRATISTA es una persona jurídica. El valor de este contrato no constituye por sí mismo un ingreso base de cotización personal ni se le aplica una regla de cotización diseñada para determinadas personas naturales independientes. EL CONTRATISTA responderá, según cada relación jurídica real, por la afiliación, cotización, nómina, riesgos laborales y demás obligaciones respecto de sus trabajadores, contratistas y subcontratistas; EL CONTRATANTE conservará los deberes de verificación y coordinación que legalmente le correspondan frente al personal que participe en la ejecución.")

        final.append(section)

    composition["sections"] = _renumber_clauses(final)
    composition.setdefault("maturity_answers", {})["legal_review_finalized"] = True
    return composition
