from __future__ import annotations

"""Overlay M33.3 de entrevista y reglas para comunicación previa CO-CD-001.

La fuente histórica 2.32 conserva por trazabilidad la pregunta sobre recepción de la
comunicación. El artículo 12 de la Ley 1266 de 2008, sin embargo, cuenta la antelación
desde el envío. Este overlay no borra el dato histórico: añade las variables necesarias
para separar envío, recepción, canal, destino, contenido y la regla especial de
obligaciones de pequeña cuantía.

Ruleset verificado: 2026-08-10.
"""

from copy import deepcopy
from types import ModuleType
from typing import Any

PRODUCT_CODE = "CO-CD-001"
INTERVIEW_STANDARD = "M33.3"
OVERLAY_STANDARD = "M33.3-habeas-prior-communication-interview-v1"

SENT_ID = "prior_communication_sent"
CHANNEL_ID = "prior_communication_channel"
DESTINATION_ID = "prior_communication_destination_verified"
ALT_AGREED_ID = "prior_communication_alternative_channel_agreed"
CONSULTABLE_ID = "prior_communication_message_consultable"
CONTENT_ID = "prior_communication_content_sufficient"
FIRST_DATE_ID = "prior_communication_first_date"

_NEW_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": SENT_ID,
        "label": "¿La fuente acredita el envío de la comunicación previa al reporte negativo?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Comunicación previa",
        "help": {
            "why_asked": "El término previo al reporte se controla desde el envío, no desde un acuse de recibo.",
            "example": "Responde Sí solo si existe soporte individualizable de envío; No sé si solo conoces que el reporte existe.",
            "warning": "La recepción declarada por el titular se conserva como un hecho distinto y no sustituye la prueba de envío.",
        },
    },
    {
        "id": CHANNEL_ID,
        "label": "Canal usado para enviar la última comunicación previa",
        "type": "select",
        "options": [
            "Dirección física registrada",
            "Extracto periódico físico",
            "Extracto periódico electrónico",
            "Correo electrónico",
            "SMS u otro mensaje de datos",
            "Otro mecanismo pactado",
            "No sé",
        ],
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": SENT_ID, "equals": "Sí"},
    },
    {
        "id": DESTINATION_ID,
        "label": "¿El soporte identifica el destino usado y coincide con la última dirección o canal registrado o pactado?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": SENT_ID, "equals": "Sí"},
    },
    {
        "id": ALT_AGREED_ID,
        "label": "Si se usó un canal alterno o electrónico, ¿existe soporte de que ese mecanismo fue pactado o autorizado?",
        "type": "select",
        "options": ["Sí", "No", "No sé", "No aplica"],
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": SENT_ID, "equals": "Sí"},
    },
    {
        "id": CONSULTABLE_ID,
        "label": "Si se usó un mensaje de datos o canal alterno, ¿la comunicación puede consultarse posteriormente?",
        "type": "select",
        "options": ["Sí", "No", "No sé", "No aplica"],
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": SENT_ID, "equals": "Sí"},
    },
    {
        "id": CONTENT_ID,
        "label": "¿La comunicación permite identificar la obligación o reporte negativo y controvertirlo antes del reporte?",
        "type": "select",
        "options": ["Sí", "No", "No sé"],
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": SENT_ID, "equals": "Sí"},
    },
    {
        "id": FIRST_DATE_ID,
        "label": "Fecha de envío de la primera comunicación para la regla especial de dos avisos",
        "type": "date",
        "required": True,
        "section": "Comunicación previa",
        "show_if": {"field": "small_obligation_two_notices", "equals": "Sí"},
        "help": {
            "why_asked": "Para obligaciones iguales o inferiores al 15 % de un SMLMV deben verificarse al menos dos comunicaciones en días diferentes.",
            "warning": "La fecha no sustituye el soporte de envío de cada comunicación.",
        },
    },
)


def _question_index(questions: list[dict], question_id: str) -> int | None:
    for index, question in enumerate(questions):
        if str(question.get("id") or "") == question_id:
            return index
    return None


def _insert_after(questions: list[dict], anchor_id: str, question: dict) -> bool:
    if _question_index(questions, str(question.get("id"))) is not None:
        return False
    anchor = _question_index(questions, anchor_id)
    if anchor is None:
        raise RuntimeError(f"No se encontró {anchor_id}; no es seguro aplicar el overlay de comunicación M33.3.")
    questions.insert(anchor + 1, deepcopy(question))
    return True


def _patch_rules(core_module: ModuleType) -> dict:
    rules_by_product = getattr(core_module, "RULES", None)
    if not isinstance(rules_by_product, dict):
        raise RuntimeError("El runtime no expone RULES como diccionario.")
    rules = rules_by_product.get(PRODUCT_CODE)
    if not isinstance(rules, list):
        raise RuntimeError(f"No existe ruleset activo para {PRODUCT_CODE}.")

    r13_patched = False
    evidence_patched = False
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("id") == "CD1-R13":
            rule["message"] = "No está acreditado el envío de la comunicación previa al reporte."
            rule["action"] = (
                "Solicitar soporte individualizable del envío, fecha, canal, destino y contenido; "
                "la falta de acuse de recibo no equivale por sí sola a falta de envío."
            )
            rule["conditions"] = {
                "any": [
                    {"field": SENT_ID, "op": "equals", "value": "No"},
                    {"field": SENT_ID, "op": "equals", "value": "No sé"},
                ]
            }
            rule["m33_3_supersedes_receipt_pivot"] = True
            r13_patched = True
        if "prueba de comunicación previa" in str(rule.get("message") or "").casefold():
            rule["message"] = "La prueba del envío de la comunicación previa es incompleta o no ha sido solicitada."
            rule["action"] = (
                "No concluir cumplimiento con afirmaciones genéricas; exigir soporte verificable de envío, "
                "fecha, destino, canal y contenido suficiente."
            )
            evidence_patched = True
    return {"r13_patched": r13_patched, "evidence_rule_patched": evidence_patched}


def install_m33_3_habeas_communication_interview(core_module: ModuleType) -> dict:
    interviews = getattr(core_module, "INTERVIEWS", None)
    if not isinstance(interviews, dict):
        raise RuntimeError("El runtime no expone INTERVIEWS como diccionario.")
    spec = interviews.get(PRODUCT_CODE)
    if not isinstance(spec, dict):
        raise RuntimeError(f"No existe entrevista activa para {PRODUCT_CODE}.")
    questions = spec.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError(f"La entrevista {PRODUCT_CODE} no contiene una lista de preguntas.")

    date_question_index = _question_index(questions, "prior_communication_date")
    evidence_question_index = _question_index(questions, "prior_communication_evidence")
    received_index = _question_index(questions, "prior_communication_received")
    small_index = _question_index(questions, "small_obligation_two_notices")
    if None in {date_question_index, evidence_question_index, received_index, small_index}:
        raise RuntimeError("La entrevista histórica cambió y no conserva los anclajes de comunicación previa esperados.")

    questions[date_question_index]["label"] = "Fecha de envío de la última comunicación previa"
    questions[date_question_index]["required"] = True
    questions[date_question_index]["show_if"] = {"field": SENT_ID, "equals": "Sí"}
    questions[evidence_question_index]["label"] = "Prueba del envío de la comunicación previa"

    inserted: list[str] = []
    if _insert_after(questions, "prior_communication_received", _NEW_QUESTIONS[0]):
        inserted.append(SENT_ID)
    if _insert_after(questions, "prior_communication_date", _NEW_QUESTIONS[1]):
        inserted.append(CHANNEL_ID)
    if _insert_after(questions, CHANNEL_ID, _NEW_QUESTIONS[2]):
        inserted.append(DESTINATION_ID)
    if _insert_after(questions, DESTINATION_ID, _NEW_QUESTIONS[3]):
        inserted.append(ALT_AGREED_ID)
    if _insert_after(questions, ALT_AGREED_ID, _NEW_QUESTIONS[4]):
        inserted.append(CONSULTABLE_ID)
    if _insert_after(questions, CONSULTABLE_ID, _NEW_QUESTIONS[5]):
        inserted.append(CONTENT_ID)
    if _insert_after(questions, "small_obligation_two_notices", _NEW_QUESTIONS[6]):
        inserted.append(FIRST_DATE_ID)

    spec["interview_standard"] = INTERVIEW_STANDARD
    spec["m33_3_habeas_communication_overlay"] = OVERLAY_STANDARD
    rule_status = _patch_rules(core_module)
    return {
        "installed": True,
        "inserted_question_ids": inserted,
        "question_count": len(questions),
        "interview_standard": INTERVIEW_STANDARD,
        "overlay_standard": OVERLAY_STANDARD,
        "source_version": spec.get("version"),
        **rule_status,
    }


__all__ = [
    "ALT_AGREED_ID",
    "CHANNEL_ID",
    "CONSULTABLE_ID",
    "CONTENT_ID",
    "DESTINATION_ID",
    "FIRST_DATE_ID",
    "INTERVIEW_STANDARD",
    "OVERLAY_STANDARD",
    "PRODUCT_CODE",
    "SENT_ID",
    "install_m33_3_habeas_communication_interview",
]
