from __future__ import annotations

"""Overlay de entrevista para la transición de la Ley 2573 de 2026 en CO-CD-001.

El artículo 13 difiere la vigencia general hasta el 20 de noviembre de 2026, pero
exceptúa expresamente los parágrafos 1 y 2 del artículo 5. Este overlay recopila los
hechos mínimos para analizar el parágrafo 2 sin presumir incumplimientos ni activar
anticipadamente los artículos 6 a 10.

El parágrafo 2 no se limita al futuro protocolo del parágrafo 1: se refiere a
lineamientos, recomendaciones y protocolos de seguridad expedidos por autoridades
competentes. Por ello, cuando se afirma un incumplimiento verificado, el expediente
debe individualizar el instrumento oficial, la autoridad, el requisito cotejado y su
aplicabilidad temporal/material.

Ruleset verificado: 2026-08-10.
"""

from copy import deepcopy
from types import ModuleType
from typing import Any

PRODUCT_CODE = "CO-CD-001"
OVERLAY_STANDARD = "M33.3-law2573-transition-interview-v2"
CORRECTION_ID = "identity_theft_correction_requested"
SECURITY_BREACH_ID = "identity_theft_security_noncompliance_verified"
SECURITY_SUPPORT_ID = "identity_theft_security_noncompliance_support"
SECURITY_AUTHORITY_ID = "identity_theft_security_instrument_authority"
SECURITY_INSTRUMENT_ID = "identity_theft_security_instrument_reference"
SECURITY_REQUIREMENT_ID = "identity_theft_security_requirement_tested"
SECURITY_APPLICABLE_ID = "identity_theft_security_instrument_applicable"

_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": CORRECTION_ID,
        "label": "¿Se presentó una solicitud de corrección a la fuente manifestando posible suplantación?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": "identity_theft", "equals": "Sí"},
        "help": {
            "why_asked": "El parágrafo 2 del artículo 5 de la Ley 2573 de 2026 exige una solicitud de corrección del titular que manifieste ser víctima de suplantación.",
            "warning": "Una consulta genérica o una reclamación sobre una obligación distinta no debe tratarse automáticamente como esta solicitud.",
        },
    },
    {
        "id": SECURITY_BREACH_ID,
        "label": "¿Existe verificación documentada de incumplimiento de lineamientos, recomendaciones o protocolos de seguridad aplicables?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": "identity_theft", "equals": "Sí"},
        "help": {
            "why_asked": "La consecuencia inmediata del parágrafo 2 no nace de la sola alegación de suplantación; exige incumplimiento verificado de controles de seguridad expedidos por autoridad competente.",
            "warning": "No marques Sí solo porque ocurrió un fraude: debe existir un cotejo documentado contra un instrumento oficial aplicable al caso.",
        },
    },
    {
        "id": SECURITY_SUPPORT_ID,
        "label": "Nivel de soporte de la verificación del incumplimiento de seguridad",
        "type": "select",
        "options": ["Completo", "Parcial", "No", "No sé"],
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": SECURITY_BREACH_ID, "equals": "Sí"},
        "help": {
            "why_asked": "Permite distinguir una conclusión técnica respaldada de una mera afirmación del expediente.",
            "warning": "La aplicación de consecuencias patrimoniales o de reporte requiere revisión jurídica humana sobre el soporte exacto.",
        },
    },
    {
        "id": SECURITY_AUTHORITY_ID,
        "label": "Autoridad que expidió el lineamiento, recomendación o protocolo de seguridad cotejado",
        "type": "select",
        "options": [
            "Superintendencia Financiera de Colombia",
            "Superintendencia de Industria y Comercio",
            "Ministerio de Tecnologías de la Información y las Comunicaciones",
            "Otra autoridad competente",
            "No sé",
        ],
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": SECURITY_BREACH_ID, "equals": "Sí"},
        "help": {
            "why_asked": "El parágrafo 2 exige que el estándar de seguridad provenga de una autoridad competente; no basta una política interna o una buena práctica sin identificar su fuente jurídica.",
            "warning": "Si seleccionas Otra autoridad competente, la referencia del instrumento debe permitir verificar la competencia y el alcance material.",
        },
    },
    {
        "id": SECURITY_INSTRUMENT_ID,
        "label": "Referencia exacta del instrumento oficial de seguridad cotejado",
        "type": "text",
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": SECURITY_BREACH_ID, "equals": "Sí"},
        "min_length": 4,
        "help": {
            "why_asked": "Identifica la circular, resolución, instrucción, protocolo, capítulo o lineamiento oficial que se afirma incumplido.",
            "example": "Circular Básica Jurídica SFC, Parte I, Título II, Capítulo I, numeral aplicable.",
            "warning": "No uses una descripción genérica como 'norma de seguridad'.",
        },
    },
    {
        "id": SECURITY_REQUIREMENT_ID,
        "label": "Requisito concreto de seguridad que fue cotejado y se considera incumplido",
        "type": "textarea",
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": SECURITY_BREACH_ID, "equals": "Sí"},
        "min_length": 10,
        "help": {
            "why_asked": "Permite vincular la evidencia del caso con una obligación de seguridad específica, en vez de deducir incumplimiento por el mero resultado fraudulento.",
            "warning": "Debe describirse el requisito y el hecho/evidencia que se cotejó; la conclusión final sigue sujeta a revisión profesional.",
        },
    },
    {
        "id": SECURITY_APPLICABLE_ID,
        "label": "¿El instrumento estaba vigente y era materialmente aplicable a la entidad, canal y operación del caso?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Riesgo y escalamiento",
        "show_if": {"field": SECURITY_BREACH_ID, "equals": "Sí"},
        "help": {
            "why_asked": "Evita aplicar retroactivamente o fuera de competencia una instrucción de seguridad.",
            "warning": "Un instrumento posterior al hecho o dirigido a otro tipo de entidad no debe usarse como presupuesto automático del parágrafo 2.",
        },
    },
)


def _index(questions: list[dict], question_id: str) -> int | None:
    for index, question in enumerate(questions):
        if str(question.get("id") or "") == question_id:
            return index
    return None


def _insert_after(questions: list[dict], anchor_id: str, question: dict) -> bool:
    if _index(questions, str(question.get("id"))) is not None:
        return False
    anchor = _index(questions, anchor_id)
    if anchor is None:
        raise RuntimeError(f"No se encontró {anchor_id}; no es seguro aplicar el overlay Ley 2573 M33.3.")
    questions.insert(anchor + 1, deepcopy(question))
    return True


def install_m33_3_habeas_law2573_interview(core_module: ModuleType) -> dict:
    interviews = getattr(core_module, "INTERVIEWS", None)
    if not isinstance(interviews, dict):
        raise RuntimeError("El runtime no expone INTERVIEWS como diccionario.")
    spec = interviews.get(PRODUCT_CODE)
    if not isinstance(spec, dict):
        raise RuntimeError(f"No existe entrevista activa para {PRODUCT_CODE}.")
    questions = spec.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError(f"La entrevista {PRODUCT_CODE} no contiene una lista de preguntas.")
    if _index(questions, "identity_theft") is None:
        raise RuntimeError("La entrevista histórica cambió y no conserva identity_theft.")

    inserted: list[str] = []
    anchor = "identity_theft"
    for question in _QUESTIONS:
        if _insert_after(questions, anchor, question):
            inserted.append(str(question["id"]))
        anchor = str(question["id"])

    spec["interview_standard"] = "M33.3"
    spec["m33_3_law2573_transition_overlay"] = OVERLAY_STANDARD
    return {
        "installed": True,
        "inserted_question_ids": inserted,
        "question_count": len(questions),
        "overlay_standard": OVERLAY_STANDARD,
        "source_version": spec.get("version"),
    }


__all__ = [
    "CORRECTION_ID",
    "OVERLAY_STANDARD",
    "PRODUCT_CODE",
    "SECURITY_APPLICABLE_ID",
    "SECURITY_AUTHORITY_ID",
    "SECURITY_BREACH_ID",
    "SECURITY_INSTRUMENT_ID",
    "SECURITY_REQUIREMENT_ID",
    "SECURITY_SUPPORT_ID",
    "install_m33_3_habeas_law2573_interview",
]
