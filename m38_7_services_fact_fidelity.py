from __future__ import annotations

"""M38.7 · Fidelidad factual del instrumento visible CO-EM-003.

Esta capa es deliberadamente posterior a la composición jurídica M33. No crea reglas
jurídicas nuevas ni sustituye la biblioteca contractual: incorpora, en las cláusulas ya
existentes, hechos materiales que el usuario confirmó en la entrevista y que de otro
modo quedarían expresados solo de forma genérica.

La función es pura respecto de sus entradas: devuelve una copia, no persiste respuestas,
no cambia aprobaciones y omite valores vacíos o sentinelas.
"""

from copy import deepcopy
import re
from typing import Any


_SENTINELS = {"null", "none", "n/a", "na", "undefined", "nan", "pendiente", "por definir"}
_SPACE = re.compile(r"\s+")


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _fact(data: dict, path: str) -> str:
    value = _read(data, path)
    if value is None or isinstance(value, (dict, list, tuple, set, bool)):
        return ""
    text = _SPACE.sub(" ", str(value)).strip().strip(".;")
    if not text or text.casefold() in _SENTINELS:
        return ""
    return text


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _append(section: dict, *values: str) -> None:
    additions = [str(value).strip() for value in values if str(value or "").strip()]
    if not additions:
        return
    existing = list(section.get("paragraphs") or [])
    text = str(section.pop("text", "") or "").strip()
    if text and not existing:
        existing.append(text)
    for value in additions:
        if value not in existing:
            existing.append(value)
    section["paragraphs"] = existing


def _dispute_rule(value: str) -> str:
    normalized = value.casefold().strip()
    mapping = {
        "negotiation_conciliation_courts": (
            "negociación directa, posterior conciliación cuando resulte procedente y, "
            "si no existe acuerdo, acceso a la jurisdicción competente"
        ),
        "negotiation_and_courts": "negociación directa y, si no existe acuerdo, acceso a la jurisdicción competente",
        "conciliation_courts": "conciliación cuando resulte procedente y, si no existe acuerdo, acceso a la jurisdicción competente",
    }
    return mapping.get(normalized, value.replace("_", " "))


def apply_services_fact_fidelity(composition: dict, answers: dict) -> dict:
    """Incorpora hechos confirmados en las cláusulas sustantivamente pertinentes."""
    result = deepcopy(composition or {})
    source = answers if isinstance(answers, dict) else {}

    acceptance = _fact(source, "scope.acceptance_criteria")
    duration = _fact(source, "schedule.duration")
    milestones = _fact(source, "schedule.milestones")
    execution_arrangement = _fact(source, "execution.arrangement")
    execution_place = _fact(source, "execution.place")
    execution_team = _fact(source, "execution.team")
    subcontracting = _fact(source, "execution.subcontracting")
    dependencies = _fact(source, "execution.dependencies")

    invoice = _fact(source, "fees.invoice")
    expenses = _fact(source, "fees.expenses")
    retentions = _fact(source, "fees.retentions")

    independence_direction = _fact(source, "independence.direction")
    independence_personnel = _fact(source, "independence.personnel")
    independence_social_security = _fact(source, "independence.social_security")

    confidentiality_categories = _fact(source, "confidentiality.categories")
    confidentiality_term = _fact(source, "confidentiality.term")
    data_roles = _fact(source, "data.roles")
    data_security = _fact(source, "data.security")

    ip_preexisting = _fact(source, "ip.preexisting")
    ip_results = _fact(source, "ip.results")
    ip_third_party = _fact(source, "ip.third_party")
    ai_rules = _fact(source, "ai.rules")

    risk_allocation = _fact(source, "risk.allocation")
    risk_liability = _fact(source, "risk.liability")
    risk_insurance = _fact(source, "risk.insurance")

    closure_transition = _fact(source, "closure.transition")
    closure_return_destroy = _fact(source, "closure.return_destroy")
    dispute = _fact(source, "dispute.mechanism") or _fact(source, "disputes.mechanism")

    for section in result.get("sections") or []:
        if not isinstance(section, dict):
            continue

        if _has(section, "ENTREGABLES Y TRAZABILIDAD"):
            _append(
                section,
                f"PARÁGRAFO. Como criterio general de aceptación confirmado para este encargo se aplicará {acceptance}." if acceptance else "",
            )

        elif _has(section, "AUTONOMÍA E INDEPENDENCIA"):
            _append(
                section,
                f"PARÁGRAFO PRIMERO. La forma de dirección pactada para la ejecución es la siguiente: {independence_direction}." if independence_direction else "",
                f"PARÁGRAFO SEGUNDO. Respecto del personal asignado, LAS PARTES han confirmado que {independence_personnel}." if independence_personnel else "",
                f"PARÁGRAFO TERCERO. En materia de seguridad social se registró como condición particular que {independence_social_security}." if independence_social_security else "",
            )

        elif _has(section, "EQUIPO Y PERSONAL"):
            _append(
                section,
                f"PARÁGRAFO. Para este contrato, la estructura de equipo confirmada es: {execution_team}." if execution_team else "",
            )

        elif _has(section, "SUBCONTRATACIÓN"):
            _append(
                section,
                f"PARÁGRAFO. La condición particular informada para subcontratación es: {subcontracting}. Esta precisión se interpreta conjuntamente con las autorizaciones y responsabilidades previstas en la presente cláusula." if subcontracting else "",
            )

        elif _has(section, "LUGAR, DISPONIBILIDAD Y COORDINACIÓN"):
            _append(
                section,
                f"PARÁGRAFO PRIMERO. LAS PARTES han definido como modalidad material de ejecución: {execution_arrangement}." if execution_arrangement else "",
                f"PARÁGRAFO SEGUNDO. El lugar o esquema territorial confirmado para la prestación es: {execution_place}." if execution_place else "",
            )

        elif _has(section, "CRONOGRAMA Y DEPENDENCIAS"):
            _append(
                section,
                f"PARÁGRAFO PRIMERO. La duración operativa informada para el encargo es {duration}." if duration else "",
                f"PARÁGRAFO SEGUNDO. Los hitos confirmados comprenden {milestones}." if milestones else "",
                f"PARÁGRAFO TERCERO. Se reconocen como dependencias específicas del proyecto: {dependencies}. Su impacto deberá acreditarse y gestionarse conforme a esta cláusula." if dependencies else "",
            )

        elif _has(section, "FACTURACIÓN, SOPORTES Y PAGO"):
            _append(
                section,
                f"PARÁGRAFO. El soporte de cobro pactado para esta operación es: {invoice}." if invoice else "",
            )

        elif _has(section, "GASTOS Y REEMBOLSOS"):
            _append(
                section,
                f"PARÁGRAFO. En este contrato LAS PARTES han definido respecto de gastos que {expenses}." if expenses else "",
            )

        elif _has(section, "TRIBUTOS, RETENCIONES"):
            _append(
                section,
                f"PARÁGRAFO. La condición particular registrada sobre retenciones y descuentos es: {retentions}." if retentions else "",
            )

        elif _has(section, "CONFIDENCIALIDAD") and not _has(section, "CONTROL"):
            _append(
                section,
                f"PARÁGRAFO PRIMERO. Para este encargo se han identificado expresamente como categorías de información protegida: {confidentiality_categories}." if confidentiality_categories else "",
                f"PARÁGRAFO SEGUNDO. La regla temporal particular informada para la confidencialidad es: {confidentiality_term}. Esta regla se aplicará sin reducir la protección que deba subsistir por mandato legal o por la naturaleza de un secreto empresarial." if confidentiality_term else "",
            )

        elif _has(section, "DATOS PERSONALES"):
            _append(
                section,
                f"PARÁGRAFO. Para las actividades de este contrato LAS PARTES han descrito los roles de tratamiento así: {data_roles}. La calificación jurídica definitiva de cada rol dependerá de la actividad efectivamente realizada y de quién determine sus finalidades y medios esenciales." if data_roles else "",
            )

        elif _has(section, "SEGURIDAD DE LA INFORMACIÓN"):
            _append(
                section,
                f"PARÁGRAFO. Como medidas de seguridad específicamente confirmadas para la ejecución se aplicarán: {data_security}." if data_security else "",
            )

        elif _has(section, "PROPIEDAD INTELECTUAL PREEXISTENTE"):
            _append(
                section,
                f"PARÁGRAFO. LAS PARTES han identificado la siguiente regla particular sobre activos preexistentes: {ip_preexisting}." if ip_preexisting else "",
            )

        elif _has(section, "RESULTADOS Y DERECHOS PATRIMONIALES"):
            _append(
                section,
                f"PARÁGRAFO. Respecto de los resultados específicamente producidos en ejecución del contrato se registró la siguiente asignación: {ip_results}. Esta descripción deberá interpretarse con los requisitos legales de determinación, alcance y forma previstos en esta cláusula." if ip_results else "",
            )

        elif _has(section, "SOFTWARE, COMPONENTES DE TERCEROS"):
            _append(
                section,
                f"PARÁGRAFO. Los componentes o materiales de terceros conservarán el siguiente tratamiento confirmado: {ip_third_party}." if ip_third_party else "",
            )

        elif _has(section, "INTELIGENCIA ARTIFICIAL"):
            _append(
                section,
                f"PARÁGRAFO. Para este encargo LAS PARTES han establecido adicionalmente la siguiente regla operativa sobre inteligencia artificial: {ai_rules}." if ai_rules else "",
            )

        elif _has(section, "RESPONSABILIDAD"):
            _append(
                section,
                f"PARÁGRAFO PRIMERO. La asignación particular de riesgos confirmada para este contrato es: {risk_allocation}." if risk_allocation else "",
                f"PARÁGRAFO SEGUNDO. LAS PARTES han descrito la regla de responsabilidad del caso así: {risk_liability}. Esta descripción se aplicará únicamente en cuanto sea compatible con las normas imperativas y con las exclusiones o límites válidamente pactados." if risk_liability else "",
                f"PARÁGRAFO TERCERO. En materia de aseguramiento se registró como condición de gestión: {risk_insurance}. Su suficiencia, obligatoriedad, límites y vigencia deberán verificarse conforme al riesgo real y a cualquier exigencia legal o contractual aplicable." if risk_insurance else "",
            )

        elif _has(section, "TRANSICIÓN Y ENTREGA"):
            _append(
                section,
                f"PARÁGRAFO. Como contenido particular de la transición se ha confirmado: {closure_transition}." if closure_transition else "",
            )

        elif _has(section, "LIQUIDACIÓN Y ACTA DE CIERRE"):
            _append(
                section,
                f"PARÁGRAFO. Respecto de información, soportes y credenciales al cierre se aplicará la siguiente condición confirmada: {closure_return_destroy}." if closure_return_destroy else "",
            )

        elif _has(section, "SOLUCIÓN ESCALONADA DE CONTROVERSIAS") and dispute:
            visible = _dispute_rule(dispute)
            _append(
                section,
                f"PARÁGRAFO. El mecanismo particular seleccionado por LAS PARTES corresponde a {visible}; esta selección no excluye requisitos de procedibilidad ni competencias imperativas que resulten aplicables." if visible else "",
            )

    result.setdefault("maturity_answers", {})["m38_7_contractual_fact_fidelity"] = True
    return result


__all__ = ["apply_services_fact_fidelity"]
