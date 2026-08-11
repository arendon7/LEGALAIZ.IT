from __future__ import annotations

"""Overlay de entrevista M33.3 para CO-CD-001.

La entrevista histórica 2.32 pregunta si existe reclamo previo y si existe una ruta de
posible suplantación, pero no individualiza si ese reclamo previo se refería
precisamente a la obligación o producto desconocido. Esa distinción es necesaria
para la compuerta M33.3 del silencio favorable.

El overlay muta la estructura compartida ``INTERVIEWS`` en memoria, de manera
idempotente y compatible con la API existente. No elimina ni reordena preguntas
históricas salvo por insertar la nueva pregunta inmediatamente después del control
de completitud del reclamo previo.
"""

from copy import deepcopy
from types import ModuleType
from typing import Any

PRODUCT_CODE = "CO-CD-001"
INTERVIEW_STANDARD = "M33.3"
QUESTION_ID = "prior_claim_identity_theft"

QUESTION: dict[str, Any] = {
    "id": QUESTION_ID,
    "label": (
        "¿El reclamo previo estaba dirigido específicamente a la obligación o producto "
        "que desconoce por posible suplantación?"
    ),
    "type": "select",
    "options": ["Sí", "No", "No sé"],
    "required": True,
    "section": "Gestiones previas",
    "show_if": {
        "field": "prior_claim",
        "equals": "Sí",
    },
    "help": {
        "why_asked": (
            "Permite distinguir un reclamo ordinario vencido del supuesto específico de "
            "posible suplantación. Esa diferencia condiciona si el sistema puede siquiera "
            "modelar un eventual efecto favorable del silencio."
        ),
        "example": (
            "Responde “Sí” solo si el reclamo previo identificaba esa obligación o producto "
            "desconocido y planteaba expresamente que no fue adquirido por ti o que podía "
            "existir una suplantación. Si el reclamo trataba otro reporte, responde “No”."
        ),
        "warning": (
            "La respuesta no sustituye la revisión del radicado, la prueba de recepción, la "
            "completitud, la prórroga ni la respuesta de fondo."
        ),
    },
}


def _question_index(questions: list[dict], question_id: str) -> int | None:
    for index, question in enumerate(questions):
        if str(question.get("id") or "") == question_id:
            return index
    return None


def install_m33_3_interview_overrides(core_module: ModuleType) -> dict:
    interviews = getattr(core_module, "INTERVIEWS", None)
    if not isinstance(interviews, dict):
        raise RuntimeError("El runtime no expone INTERVIEWS como diccionario.")
    spec = interviews.get(PRODUCT_CODE)
    if not isinstance(spec, dict):
        raise RuntimeError(f"No existe entrevista activa para {PRODUCT_CODE}.")
    questions = spec.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError(f"La entrevista {PRODUCT_CODE} no contiene una lista de preguntas.")

    existing = _question_index(questions, QUESTION_ID)
    inserted = False
    if existing is None:
        anchor = _question_index(questions, "prior_claim_complete")
        if anchor is None:
            raise RuntimeError(
                "No se encontró prior_claim_complete; no es seguro insertar la pregunta M33.3."
            )
        questions.insert(anchor + 1, deepcopy(QUESTION))
        inserted = True
        existing = anchor + 1

    spec["interview_standard"] = INTERVIEW_STANDARD
    spec["m33_3_interview_overlay"] = True
    # La versión del JSON histórico se preserva para trazabilidad. El overlay se
    # identifica por un campo separado y no finge haber reescrito la fuente 2.32.
    return {
        "installed": True,
        "inserted": inserted,
        "product_code": PRODUCT_CODE,
        "question_id": QUESTION_ID,
        "question_index": existing,
        "question_count": len(questions),
        "interview_standard": INTERVIEW_STANDARD,
        "source_version": spec.get("version"),
    }


__all__ = [
    "INTERVIEW_STANDARD",
    "PRODUCT_CODE",
    "QUESTION",
    "QUESTION_ID",
    "install_m33_3_interview_overrides",
]
