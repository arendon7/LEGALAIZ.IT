from __future__ import annotations

"""Finalizador runtime de la segunda oleada M33.0.

La composición profunda reemplaza los documentos sustantivos principales. Algunas
matrices/calendarios históricos se conservan porque ya contienen cálculos maduros.
Este finalizador elimina artefactos de presentación incompatibles con M33.0, agrega
control de uso donde falte y estructura la firma de comunicaciones históricas sin
alterar el resultado sustantivo del motor.
"""

from copy import deepcopy
import re
from typing import Any

from m33_procedural_composition import M33_PROCEDURAL_CODES, document_specs_m33

_SEPARATOR_RE = re.compile(r"(?:_{4,}|={5,}|-{6,})")
_PLACEHOLDER_RE = re.compile(r"\[[A-ZÁÉÍÓÚÜÑ0-9][A-ZÁÉÍÓÚÜÑ0-9 _./:-]{1,80}\]")
_SENTINELS = {"none", "null", "undefined", "n/a", "na", "nan"}

_SIGNATURE_KINDS = {
    "habeas_authority_escalation",
    "collection_letter",
    "payment_agreement",
    "promissory_note",
    "instruction_letter",
    "payment_receipt",
    "settlement_certificate",
    "warranty_claim",
    "withdrawal_notice",
    "payment_reversal_request",
    "recurring_debit_revocation",
    "ecommerce_non_delivery_termination",
    "claim",
    "labor_support_request",
}


def _clean_text(value: Any) -> Any:
    """Normaliza valores heredados sin alterar valores jurídicamente significativos.

    M33.0 no debe exponer representaciones de Python ni marcadores de plantilla. Los
    nulos y centinelas se convierten en un estado explícito de verificación; cero,
    ``False`` y demás valores reales se conservan. La obligatoriedad material de un
    dato sigue controlada por las reglas y compuertas del producto.
    """
    if value is None:
        return "Dato pendiente de verificación"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return value

    cleaned = value.strip()
    if cleaned.casefold() in _SENTINELS:
        return "Dato pendiente de verificación"
    cleaned = _SEPARATOR_RE.sub("", cleaned)
    cleaned = _PLACEHOLDER_RE.sub("Dato pendiente de verificación", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _sanitize_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _clean_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if key in result and isinstance(result[key], list):
            result[key] = [cleaned for item in result[key] if (cleaned := _clean_text(item))]
    if isinstance(result.get("table"), list):
        result["table"] = [[_clean_text(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        parties = []
        for party in result["parties"]:
            if isinstance(party, dict):
                parties.append({key: _clean_text(value) for key, value in party.items()})
        result["parties"] = parties
    return result


def _control(code: str) -> dict:
    return {
        "heading": "CONTROL DE USO, FUENTES Y REVISIÓN",
        "_type": "control",
        "text": (
            f"Documento candidato interno {code} bajo estándar M33.0. La generación conserva las reglas, cálculos, condiciones y bloqueos del motor vigente. "
            "La liberación exige verificar hechos, identidad, legitimación, fechas, valores, anexos, fuentes, vigencia normativa y coherencia completa, además de aprobación jurídica y QA sobre la misma revisión y hash."
        ),
    }


def _signature_identity(code: str, answers: dict) -> tuple[str, str, str]:
    if code == "CO-LA-001":
        return (
            "PERSONA TRABAJADORA",
            str(answers.get("employee_name") or answers.get("worker_name") or answers.get("name") or "Persona trabajadora por identificar"),
            str(answers.get("employee_id") or answers.get("worker_id") or ""),
        )
    if code == "CO-CD-001":
        return (
            "TITULAR DE LA INFORMACIÓN",
            str(answers.get("data_subject_name") or "Titular por identificar"),
            str(answers.get("data_subject_id") or ""),
        )
    if code == "CO-CD-003":
        return (
            "PERSONA CONSUMIDORA",
            str(answers.get("consumer_name") or "Persona consumidora por identificar"),
            str(answers.get("consumer_id") or ""),
        )
    return (
        "PARTE QUE SUSCRIBE",
        str(answers.get("creditor_name") or answers.get("creditor") or answers.get("debtor_name") or answers.get("debtor") or "Parte por identificar"),
        str(answers.get("creditor_id") or answers.get("debtor_id") or ""),
    )


def _structured_signature(code: str, answers: dict) -> dict:
    label, name, identity = _signature_identity(code, answers)
    return {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [{"label": label, "name": name, "id": identity}],
    }


def _labor_evidence_spec(specs: list[dict], answers: dict) -> dict:
    metadata = specs[0].get("metadata") if specs else []
    return {
        "kind": "labor_evidence_index",
        "title": "Índice probatorio y matriz de trazabilidad laboral",
        "filename_suffix": "indice_probatorio_laboral",
        "subtitle": "Expediente probatorio M33.0",
        "metadata": metadata,
        "document_standard": "M33.0",
        "sections": [
            {
                "heading": "1. FINALIDAD DEL ÍNDICE",
                "paragraphs": [
                    "El índice identifica los documentos que permiten acreditar cada hecho utilizado por el diagnóstico, la liquidación y la reclamación. Un dato extraído de un archivo o informado en el formulario no se considera definitivamente confirmado hasta que pueda vincularse con un soporte suficientemente confiable o sea ratificado por la persona usuaria.",
                    "La ausencia de un documento no se interpreta automáticamente contra ninguna de las partes. Se registra como vacío probatorio para solicitarlo, sustituirlo mediante otra evidencia admisible o ajustar el nivel de certeza de la afirmación correspondiente.",
                ],
            },
            {
                "heading": "2. MATRIZ DE EVIDENCIAS",
                "table": [
                    ["ID", "Documento o evidencia", "Hecho que acredita", "Estado", "Observación"],
                    ["LAB-EV-001", "Contrato de trabajo y anexos", "Modalidad, cargo, salario y condiciones", "Por verificar", "Conservar versión íntegra"],
                    ["LAB-EV-002", "Desprendibles de nómina", "Devengos, deducciones y pagos", "Por verificar", "Cotejar con banco"],
                    ["LAB-EV-003", "Comprobantes bancarios", "Pago efectivo", "Por verificar", "Identificar concepto y período"],
                    ["LAB-EV-004", "Soportes de prima y cesantías", "Pagos prestacionales previos", "Por verificar", "Evitar doble cobro"],
                    ["LAB-EV-005", "Registro de vacaciones", "Días disfrutados o pendientes", "Por verificar", "Cotejar fechas"],
                    ["LAB-EV-006", "Comunicación de terminación", "Fecha, autor y causa informada", "Por verificar", "Revisar anexos"],
                    ["LAB-EV-007", "PILA / seguridad social", "Aportes durante la relación", "Condicional", "Solo períodos pertinentes"],
                    ["LAB-EV-008", "Liquidación del empleador", "Posición económica de la contraparte", "Pendiente", "Comparar por concepto"],
                    ["LAB-EV-009", "Reclamación y acuse", "Contenido y fecha de recepción", "Por generar", "Conservar versión exacta"],
                ],
            },
            {
                "heading": "3. REGLAS DE TRAZABILIDAD",
                "numbered": [
                    "Conservar el archivo original y trabajar sobre copias identificadas.",
                    "Registrar fecha, fuente, nombre de archivo y versión.",
                    "Vincular cada documento con el hecho o cálculo que soporta.",
                    "No eliminar evidencia desfavorable ni sobrescribir una versión anterior.",
                    "Distinguir hechos confirmados, manifestaciones del usuario, inferencias y supuestos de cálculo.",
                    "Actualizar el índice cuando llegue una respuesta o un documento adicional.",
                ],
            },
            _control("CO-LA-001"),
        ],
    }


def _finalize_spec(code: str, answers: dict, spec: dict) -> dict:
    result = deepcopy(spec)
    result["document_standard"] = "M33.0"
    sections = [_sanitize_section(section) for section in result.get("sections") or []]

    if result.get("kind") in _SIGNATURE_KINDS and not any(section.get("_type") == "signature" for section in sections):
        sections.append(_structured_signature(code, answers))

    controls = [section for section in sections if section.get("_type") == "control" or "control de uso" in str(section.get("heading") or "").casefold()]
    sections = [section for section in sections if section not in controls]
    sections.append(controls[0] if controls else _control(code))
    result["sections"] = sections
    return result


def document_specs_m33_runtime(case_id, code, answers, result, product, generated_at, question_rows):
    specs = document_specs_m33(case_id, code, answers, result, product, generated_at, question_rows)
    if code not in M33_PROCEDURAL_CODES or result.get("risk") == "red":
        return specs
    if code == "CO-LA-001" and not any(spec.get("kind") == "labor_evidence_index" for spec in specs):
        specs.append(_labor_evidence_spec(specs, answers))
    return [_finalize_spec(code, answers, spec) for spec in specs]
