from __future__ import annotations

"""Fuentes jurídicas M33.4 para CO-TR-001 — verificación SAST."""

from datetime import date
from typing import Any

from legalai_platform import sast_official_domains as _sast_official_domains  # noqa: F401
from legalai_platform.legal_source_registry import LEGAL_SOURCE_REGISTRY, REVIEW_DUE_ON, VERIFIED_ON, validate_registry


SAST_SOURCE_RECORDS = {
    "CO-LEY1843-SAST": {
        "title": "Ley 1843 de 2017", "locator": "Artículos 1, 2, 3, 10, 13 y 14 — instalación, operación, señalización, control y metrología SAST",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30032605",
        "observed_status": "vigente con modificaciones; regula SAST, señalización y trazabilidad de equipos medidores de velocidad",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["SAST", "señalización", "autorización", "metrología"], "source_kind": "statute",
        "applicability": "base transversal; debe leerse con modificaciones posteriores y según fecha del hecho",
    },
    "CO-D2106-ART109-SAST": {
        "title": "Decreto Ley 2106 de 2019", "locator": "Artículo 109 — autorización ANSV y vigencia de cinco años",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30038501",
        "observed_status": "vigente; modificó el artículo 2 de la Ley 1843 y asignó autorización a ANSV por cinco años",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["SAST", "ANSV", "autorización", "vigencia"], "source_kind": "decree_law",
        "applicability": "régimen general de autorización; no desplaza excepciones legales específicas",
    },
    "CO-LEY2294-ART181-SAST": {
        "title": "Ley 2294 de 2023", "locator": "Artículo 181 — parágrafo 2 del artículo 2 de la Ley 1843",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes/30046580",
        "observed_status": "vigente; excepción específica de autorización nacional para ciertos sistemas en infraestructura de transporte público, conservando señalización",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["SAST", "transporte público", "excepción", "carril exclusivo"], "source_kind": "statute_exception",
        "applicability": "solo si hechos e infraestructura encajan materialmente en el supuesto legal",
    },
    "CO-R11245-2020-SAST": {
        "title": "Resolución 20203040011245 de 2020", "locator": "Criterios técnicos para instalación y operación de SAST",
        "authority": "Ministerio de Transporte y Agencia Nacional de Seguridad Vial", "official_url": "https://mintransporte.gov.co/publicaciones/9590/normatividad-racionalizacion/",
        "observed_status": "vigente y compilada en la Resolución Única de Tránsito; sustituyó la Resolución 718 de 2018",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["SAST", "criterios técnicos", "operación", "registro"], "source_kind": "technical_regulation",
        "applicability": "condiciones técnicas actuales; no confundir autorización de instalación con cumplimiento operativo en una fecha concreta",
    },
    "CO-R45005-2024-SENAL": {
        "title": "Resolución 20243040045005 de 2024", "locator": "Manual de Señalización Vial de Colombia y artículo 3 de transición",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Resolucion%2F30054056",
        "observed_status": "vigente desde 02/10/2024; sustituyó el manual anterior y contiene transición para señalización y diseños preexistentes",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["señalización", "manual 2024", "transición"], "source_kind": "signage_regulation",
        "applicability": "según fecha relevante; no debe aplicarse retrospectivamente a evidencia histórica sin análisis de transición",
    },
    "CO-INM-2026-DESEMPENO": {
        "title": "Aclaración oficial INM 2026 sobre Concepto de Desempeño", "locator": "Vigencia histórica 22/03/2018–19/08/2020 y alcance exclusivamente metrológico",
        "authority": "Instituto Nacional de Metrología de Colombia", "official_url": "https://inm.gov.co/informacion-fotomultas-concepto-de-desempeno/",
        "observed_status": "aclaración oficial vigente; el antiguo requisito no es actual y nunca equivalió a autorización integral de funcionamiento",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["metrología", "concepto de desempeño", "temporalidad"], "source_kind": "official_technical_clarification",
        "applicability": "solo para clasificar el antiguo requisito y evitar su aplicación fuera de 2018–2020",
    },
    "CO-INM-R352-2020-VELOCIDAD": {
        "title": "Resolución 352 de 2020", "locator": "Alternativas para obtener trazabilidad metrológica en mediciones de velocidad",
        "authority": "Instituto Nacional de Metrología de Colombia", "official_url": "https://inm.gov.co/normatividad/resoluciones/",
        "observed_status": "publicada por el INM; establece alternativas de trazabilidad metrológica para mediciones de velocidad",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["velocidad", "trazabilidad metrológica", "calibración"], "source_kind": "metrology_regulation",
        "applicability": "solo cuando el equipo efectivamente mide velocidad",
    },
    "CO-LEY1755-PETICION-SAST": {
        "title": "Ley 1755 de 2015", "locator": "Artículos 14 y 21 — términos de petición y traslado por falta de competencia",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30043679",
        "observed_status": "vigente", "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["petición", "información", "documentos", "traslado"], "source_kind": "petition_statute",
        "applicability": "petición de expediente, inspección, reiteración y seguimiento según naturaleza de cada solicitud",
    },
    "CO-LEY1712-TRANSPARENCIA-SAST": {
        "title": "Ley 1712 de 2014", "locator": "Artículos 2, 18 a 21 — máxima publicidad, reservas y versión pública",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho", "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1687091",
        "observed_status": "vigente; la reserva debe tener fundamento legal y, cuando sea posible, entregarse versión pública",
        "verified_on": VERIFIED_ON.isoformat(), "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["transparencia", "documentos públicos", "reserva", "versión pública"], "source_kind": "transparency_statute",
        "applicability": "solicitudes de expediente y documentos oficiales",
    },
}

for source_id, record in SAST_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record
validate_registry()

SAST_KINDS = {"sast_report", "sast_traceability", "sast_registration", "sast_record_request", "sast_inspection", "sast_followup", "sast_package"}


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except Exception:
        return None


def _speed(answers: dict) -> bool:
    text = " ".join(str(answers.get(key) or "") for key in ("device_type", "conduct_code", "request_mode")).casefold()
    return "velocidad" in text or "radar" in text


def _public_request_kind(kind: str) -> bool:
    return kind in {"sast_record_request", "sast_inspection", "sast_followup", "sast_package"}


def sast_source_ids(kind: str, answers: dict, result: dict) -> list[str]:
    if kind not in SAST_KINDS:
        return []
    ids = ["CO-LEY1843-SAST", "CO-D2106-ART109-SAST", "CO-R11245-2020-SAST"]
    if kind in {"sast_report", "sast_traceability", "sast_record_request", "sast_inspection", "sast_package"}:
        ids.extend(["CO-LEY2294-ART181-SAST", "CO-R45005-2024-SENAL", "CO-INM-2026-DESEMPENO"])
    if _speed(answers) and kind in {"sast_report", "sast_traceability", "sast_record_request", "sast_inspection", "sast_package"}:
        ids.append("CO-INM-R352-2020-VELOCIDAD")
    if _public_request_kind(kind):
        ids.extend(["CO-LEY1755-PETICION-SAST", "CO-LEY1712-TRANSPARENCIA-SAST"])
    return list(dict.fromkeys(ids))


def sast_temporal_control(answers: dict) -> dict:
    observed = _date(answers.get("observation_date") or answers.get("event_date") or answers.get("reference_date"))
    if observed is None:
        return {"reference_date": None, "performance_concept": "date_required", "signage_regime": "date_required"}
    performance = "historical_window" if date(2018, 3, 22) <= observed <= date(2020, 8, 19) else "not_current_requirement"
    signage = "manual_2024_with_transition" if observed >= date(2024, 10, 2) else "historical_signage_regime_required"
    return {"reference_date": observed.isoformat(), "performance_concept": performance, "signage_regime": signage}


__all__ = ["SAST_KINDS", "SAST_SOURCE_RECORDS", "sast_source_ids", "sast_temporal_control"]
