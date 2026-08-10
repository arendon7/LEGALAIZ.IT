from __future__ import annotations

"""Overlay de entrevista para la transición de la Ley 2573 de 2026 en CO-CD-001.

El artículo 13 difiere la vigencia general hasta el 20 de noviembre de 2026, pero
exceptúa expresamente los parágrafos 1 y 2 del artículo 5. Este overlay recopila los
hechos mínimos para analizar el parágrafo 2 sin presumir incumplimientos ni activar
anticipadamente los artículos 6 a 10.

Ruleset verificado: 2026-08-10.
"""

from copy import deepcopy
from types import ModuleType
from typing import Any

PRODUCT_CODE = "CO-CD-001"
OVERLAY_STANDARD = "M33.3-law2573-transition-interview-v1"
CORRECTION_ID = "identity_theft_correction_requested"
SECURITY_BREACH_ID = "identity_theft_security_noncompliance_verified"
SECURITY_SUPPORT_ID = "identity_theft_security_noncompliance_support"

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
            "why_asked": "La consecuencia inmediata del parágrafo 2 no nace de la sola alegación de suplantación; exige incumplimiento verificado de controles de seguridad aplicables.",
            "warning": "No marques Sí solo porque ocurrió un fraude: debe existir un cotejo documentado contra un lineamiento, recomendación o protocolo aplicable al caso.",
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
    "SECURITY_BREACH_ID",
    "SECURITY_SUPPORT_ID",
    "install_m33_3_habeas_law2573_interview",
]
