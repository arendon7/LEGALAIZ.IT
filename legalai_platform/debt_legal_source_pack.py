from __future__ import annotations

"""Paquete normativo y control paramétrico M33.4 para CO-CD-004.

Las fuentes jurídicas estables se registran en el registro normativo M33.4. La
certificación periódica del interés bancario corriente no se trata como una norma:
se evalúa en una compuerta financiera independiente que exige fuente oficial,
modalidad y período exactos antes de permitir reutilizar una tasa o límite.
"""

from datetime import date
from urllib.parse import urlparse
from typing import Any

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


DEBT_SOURCE_RECORDS = {
    "CO-COM-TITULOS-PAGARE": {
        "title": "Código de Comercio — títulos valores y pagaré",
        "locator": "Decreto 410 de 1971, artículos 621, 622 y 709 a 711",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F1833376",
        "observed_status": "Código de Comercio consultado como vigente; comprende requisitos generales de títulos valores, diligenciamiento de espacios en blanco y reglas del pagaré",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["títulos valores", "pagaré", "espacios en blanco", "vencimiento", "firma"],
        "source_kind": "commercial_code",
        "applicability": "cuando el expediente genera o controla un pagaré u otro título valor",
    },
    "CO-COM-INTERESES-884-886": {
        "title": "Código de Comercio — intereses mercantiles",
        "locator": "Decreto 410 de 1971, artículos 884 y 886",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1833376",
        "observed_status": "Código de Comercio vigente; artículo 884 modificado por la Ley 510 de 1999 y artículo 886 vigente sobre intereses pendientes",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["interés bancario corriente", "interés moratorio", "límite de intereses", "anatocismo"],
        "source_kind": "commercial_code",
        "applicability": "cuando existen intereses mercantiles pactados, legales o moratorios",
    },
    "CO-D1454-1989-INTERESES": {
        "title": "Decreto 1454 de 1989",
        "locator": "Artículo 1; reglamentación de intereses pendientes o atrasados y capitalización",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1289765",
        "observed_status": "vigente; reglamenta los artículos 886 del Código de Comercio y 2235 del Código Civil en materia de intereses",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["intereses pendientes", "capitalización", "anatocismo", "exigibilidad"],
        "source_kind": "regulation",
        "applicability": "control de capitalización e intereses pendientes según la naturaleza de la obligación",
    },
    "CO-CC-NOVACION-1687-1693-1708": {
        "title": "Código Civil — novación y garantías",
        "locator": "Ley 84 de 1873, artículos 1687, 1693 y 1708",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1827111",
        "observed_status": "Código Civil consultado en el Título XV sobre novación; fuente oficial identifica los artículos 1687 a 1710 dentro del régimen vigente consultado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["novación", "ampliación de plazo", "garantías de terceros", "obligación anterior"],
        "source_kind": "civil_code",
        "applicability": "acuerdos que modifican plazo u obligación y requieren controlar efectos sobre garantías",
    },
    "CO-CGP-ART422": {
        "title": "Código General del Proceso, artículo 422",
        "locator": "Ley 1564 de 2012, artículo 422 — título ejecutivo",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1683572",
        "observed_status": "texto vigente consultado: exige obligaciones expresas, claras y exigibles que consten en documentos con fuerza ejecutiva conforme a la ley",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["título ejecutivo", "obligación expresa", "obligación clara", "exigibilidad"],
        "source_kind": "procedural_code",
        "applicability": "diagnóstico de mérito ejecutivo y documentos destinados a soportar eventual ejecución",
    },
    "CO-LEY2300-COBRANZA": {
        "title": "Ley 2300 de 2023",
        "locator": "Artículos 1 a 7 y 10 — canales, horarios, periodicidad y límites de contacto en cobranza",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30046853",
        "observed_status": "vigente desde el 10/10/2023; regula gestiones de cobranza dentro de su ámbito y no debe presumirse aplicable a toda relación empresarial sin verificar destinatario, obligación y gestión",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["cobranza", "intimidad", "canales autorizados", "horarios", "periodicidad"],
        "source_kind": "statute",
        "applicability": "conditional_scope_human_review_required",
    },
    "CO-LEY1266-REPORTING": {
        "title": "Ley Estatutaria 1266 de 2008 — reporte crediticio",
        "locator": "Régimen de información financiera, crediticia, comercial y de servicios; artículo 12 y reglas concordantes",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1676616",
        "observed_status": "vigente con modificaciones incorporadas; el reporte negativo exige control de fuente, comunicación previa, exactitud y demás presupuestos del régimen especial",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["reporte crediticio", "hábeas data", "comunicación previa", "fuente de información"],
        "source_kind": "statutory_data_regime",
        "applicability": "solo cuando el expediente pretende realizar, actualizar o controlar reporte crediticio",
    },
}


for source_id, record in DEBT_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


DEBT_KINDS = {
    "debt_diagnostic",
    "account_statement",
    "collection_evidence_matrix",
    "collection_letter",
    "payment_agreement",
    "payment_schedule",
    "promissory_note",
    "instruction_letter",
    "payment_receipt",
    "settlement_certificate",
}

DEBT_INTEREST_PARAMETER_KINDS = {
    "debt_diagnostic",
    "account_statement",
    "collection_letter",
    "payment_agreement",
    "payment_schedule",
    "promissory_note",
    "instruction_letter",
    "payment_receipt",
}

_EXECUTIVE_KINDS = {
    "debt_diagnostic",
    "collection_evidence_matrix",
    "collection_letter",
    "payment_agreement",
    "promissory_note",
    "instruction_letter",
    "settlement_certificate",
}

_INTEREST_SOURCE_KINDS = DEBT_INTEREST_PARAMETER_KINDS
_NOVATION_KINDS = {"debt_diagnostic", "payment_agreement", "payment_schedule"}
_TITLE_KINDS = {
    "debt_diagnostic",
    "collection_evidence_matrix",
    "payment_agreement",
    "promissory_note",
    "instruction_letter",
    "settlement_certificate",
}


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def debt_source_ids(kind: str, answers: dict) -> list[str]:
    """Selecciona fuentes por función y por hechos jurídicamente relevantes."""
    if kind not in DEBT_KINDS:
        return []

    values: list[str] = []
    if kind in _EXECUTIVE_KINDS:
        values.append("CO-CGP-ART422")

    if kind in _INTEREST_SOURCE_KINDS and _yes(answers.get("interest_agreed")):
        values.extend(["CO-COM-INTERESES-884-886", "CO-D1454-1989-INTERESES"])

    note_relevant = kind in {"promissory_note", "instruction_letter"} or _yes(answers.get("promissory_note_required"))
    if kind in _TITLE_KINDS and note_relevant:
        values.append("CO-COM-TITULOS-PAGARE")

    if kind in _NOVATION_KINDS:
        values.append("CO-CC-NOVACION-1687-1693-1708")

    # La carta visible explica la Ley 2300 de forma condicional; registrar la
    # fuente no equivale a afirmar que el caso concreto esté dentro de su ámbito.
    if kind == "collection_letter":
        values.append("CO-LEY2300-COBRANZA")

    if _yes(answers.get("credit_reporting")) and kind in {
        "debt_diagnostic",
        "collection_evidence_matrix",
        "collection_letter",
        "payment_agreement",
        "settlement_certificate",
    }:
        values.append("CO-LEY1266-REPORTING")

    if kind == "collection_evidence_matrix":
        values.extend(["CO-LEY1581-2012", "CO-LEY527-ARTS6-7-14"])
    elif kind in {"payment_receipt", "settlement_certificate"}:
        values.append("CO-LEY527-ARTS6-7-14")

    return _dedupe(values)


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _is_demo_parameter(value: Any) -> bool:
    text = str(value or "").casefold()
    return any(token in text for token in ("demostr", "prueba", "test", "revalidar en producción"))


def _is_official_sfc_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    host = parsed.netloc.casefold()
    return parsed.scheme == "https" and (host == "superfinanciera.gov.co" or host.endswith(".superfinanciera.gov.co"))


def evaluate_interest_parameter_m334(answers: dict, result: dict) -> dict:
    """Valida la reutilización temporal de la tasa/límite sin declarar la SFC norma.

    ``verified_exact_period`` solo es posible si el expediente conserva una fuente
    oficial de la SFC, resolución identificable, modalidad, período y fecha de
    documento compatibles. Un número aislado nunca supera esta compuerta.
    """
    if not _yes(answers.get("interest_agreed")):
        return {
            "standard": "M33.4",
            "status": "not_applicable",
            "gate": "not_applicable",
            "legal_effect": "no_interest_parameter_reuse",
            "verified_on": VERIFIED_ON.isoformat(),
            "reasons": [],
        }

    calculation = (result or {}).get("calculation")
    c = calculation if isinstance(calculation, dict) else {}
    resolution = c.get("interest_resolution")
    official_url = c.get("interest_official_url") or c.get("interest_source_url")
    valid_from = _parse_date(c.get("interest_valid_from"))
    valid_to = _parse_date(c.get("interest_valid_to"))
    document_date = _parse_date(answers.get("document_date"))
    modality = c.get("interest_modality") or answers.get("interest_type")
    maximum_reference = c.get("maximum_reference_ea")

    reasons: list[str] = []
    if _is_demo_parameter(resolution):
        reasons.append("La referencia de interés está marcada como demostrativa o pendiente de revalidación.")
    if not resolution or "resol" not in str(resolution).casefold():
        reasons.append("Falta identificar la resolución oficial exacta que soporta el período.")
    if not _is_official_sfc_url(official_url):
        reasons.append("Falta URL oficial de la Superintendencia Financiera para la certificación exacta.")
    if not modality:
        reasons.append("Falta la modalidad de crédito/interés que determina la certificación aplicable.")
    if valid_from is None or valid_to is None:
        reasons.append("Falta el período exacto de vigencia del parámetro financiero.")
    if document_date is None:
        reasons.append("Falta fecha del documento para cotejar la vigencia del parámetro.")
    elif valid_from is not None and valid_to is not None and not (valid_from <= document_date <= valid_to):
        reasons.append("La fecha del documento está fuera del período declarado para la certificación.")
    if maximum_reference in (None, "", 0, 0.0):
        reasons.append("Falta el límite o referencia numérica que se pretende controlar.")

    status = "verified_exact_period" if not reasons else "needs_exact_period_reverification"
    gate = (
        "current_exact_period"
        if status == "verified_exact_period"
        else "release_block_interest_parameter_reverification_required"
    )
    return {
        "standard": "M33.4",
        "status": status,
        "gate": gate,
        "legal_effect": (
            "parameter_traceability_only; human_legal_review_required"
            if status == "verified_exact_period"
            else "do_not_rely_on_numeric_interest_limit_until_exact_period_source_is_verified"
        ),
        "verified_on": VERIFIED_ON.isoformat(),
        "authority": "Superintendencia Financiera de Colombia",
        "authority_domain": "superfinanciera.gov.co",
        "resolution": str(resolution or ""),
        "official_url": str(official_url or ""),
        "modality": str(modality or ""),
        "valid_from": valid_from.isoformat() if valid_from else None,
        "valid_to": valid_to.isoformat() if valid_to else None,
        "document_date": document_date.isoformat() if document_date else None,
        "maximum_reference_ea": maximum_reference,
        "parameter_nature": "volatile_period_specific_financial_reference",
        "reasons": reasons,
    }


__all__ = [
    "DEBT_INTEREST_PARAMETER_KINDS",
    "DEBT_KINDS",
    "DEBT_SOURCE_RECORDS",
    "debt_source_ids",
    "evaluate_interest_parameter_m334",
]
