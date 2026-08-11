from __future__ import annotations

"""Registro normativo estructurado para trazabilidad jurídica LegalAIZ.it.

M33.4 separa tres conceptos que antes aparecían mezclados en texto libre:

* la norma o fuente jurídica invocada;
* la evidencia oficial usada para verificarla;
* la fecha hasta la cual esa verificación puede reutilizarse sin revisión.

El registro NO declara vigencia con fuerza certificante. ``observed_status`` refleja lo
consultado en la fuente oficial indicada y ``review_due_on`` obliga a revalidar cuando
la evidencia envejece. Los documentos siguen sujetos a revisión jurídica humana.
"""

from copy import deepcopy
from datetime import date
from urllib.parse import urlparse
from typing import Iterable


VERIFIED_ON = date(2026, 8, 10)
REVIEW_DUE_ON = date(2026, 11, 8)
OFFICIAL_DOMAINS = {
    "www.suin-juriscol.gov.co",
    "suin-juriscol.gov.co",
    "www.comunidadandina.org",
    "comunidadandina.org",
}


LEGAL_SOURCE_REGISTRY: dict[str, dict] = {
    "CO-CST-ART23-2025": {
        "title": "Código Sustantivo del Trabajo, artículo 23",
        "locator": "Artículo 23; literal b modificado por el artículo 16 de la Ley 2466 de 2025",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo%2F30019323",
        "observed_status": "vigente; modificación de 2025 incorporada en el texto consultado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["laboralidad", "subordinación", "primacía de la realidad"],
    },
    "CO-COM-ART871": {
        "title": "Código de Comercio, artículo 871",
        "locator": "Decreto 410 de 1971, artículo 871",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F1833376",
        "observed_status": "Código de Comercio consultado como vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["buena fe", "contratos mercantiles"],
    },
    "CO-LEY2024-ART3": {
        "title": "Ley 2024 de 2020, artículo 3",
        "locator": "Pago en plazos justos; artículo 3 y excepciones/jurisprudencia asociada",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30039609",
        "observed_status": "vigente; plazo general de 45 días desde el segundo año, sujeto a ámbito y excepciones",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["pago", "facturación", "plazos justos"],
    },
    "CO-LEY2277-ART89": {
        "title": "Ley 2277 de 2022, artículo 89",
        "locator": "Ingreso base de cotización de independientes",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://suin-juriscol.gov.co/viewDocument.asp?id=30045028",
        "observed_status": "texto consultado aplicable al IBC de independientes según sus presupuestos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["seguridad social", "IBC", "independientes"],
    },
    "CO-D1072-SGRL-SGSST": {
        "title": "Decreto 1072 de 2015",
        "locator": "Sección 2.2.4.2.2 y Capítulo 2.2.4.6, entre otras disposiciones aplicables",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://suin-juriscol.gov.co/viewDocument.asp?id=30019522",
        "observed_status": "vigente; contiene reglas de riesgos laborales y SG-SST para contratantes/contratistas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["ARL", "riesgos laborales", "SG-SST", "contratistas"],
    },
    "CO-LEY23-ART183": {
        "title": "Ley 23 de 1982, artículo 183",
        "locator": "Acuerdos sobre derechos patrimoniales de autor o conexos",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes/30035790",
        "observed_status": "texto vigente consultado con modificaciones incorporadas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["derecho de autor", "transferencia", "licencia"],
    },
    "CO-LEY1955-ART181": {
        "title": "Ley 1955 de 2019, artículo 181",
        "locator": "Modificación del artículo 183 de la Ley 23 de 1982",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes/30036488",
        "observed_status": "modificación incorporada en el artículo 183 consultado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["derecho de autor", "transferencia", "forma escrita"],
    },
    "CAN-DEC351-DA": {
        "title": "Decisión Andina 351 de 1993",
        "locator": "Régimen Común sobre Derecho de Autor y Derechos Conexos",
        "authority": "Secretaría General de la Comunidad Andina",
        "official_url": "https://www.comunidadandina.org/temas/dg-dec/propiedad-intelectual/",
        "observed_status": "referenciada por la CAN como régimen común vigente de derecho de autor y derechos conexos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["derecho de autor", "derechos conexos", "régimen andino"],
    },
    "CO-LEY1581-2012": {
        "title": "Ley Estatutaria 1581 de 2012",
        "locator": "Régimen general de protección de datos personales",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1684507",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["datos personales", "responsable", "encargado", "transferencia"],
    },
    "CO-D1074-DATOS": {
        "title": "Decreto 1074 de 2015",
        "locator": "Capítulo 25 del Título 2 de la Parte 2 del Libro 2 y reglas concordantes de protección de datos",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Decretos/30019935",
        "observed_status": "vigente; decreto único con reglamentación compilada del sector Comercio, Industria y Turismo",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["datos personales", "reglamentación", "encargado", "responsable"],
    },
    "CO-LEY527-ARTS6-7-14": {
        "title": "Ley 527 de 1999",
        "locator": "Artículos 6, 7 y 14 y disposiciones concordantes sobre mensajes de datos y firma",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1662013",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["mensajes de datos", "firma", "contratación electrónica"],
    },
}


def _as_date(value: str) -> date:
    return date.fromisoformat(value)


def validate_registry() -> None:
    """Falla cerrado si una fuente registrada carece de trazabilidad mínima."""
    errors: list[str] = []
    for source_id, record in LEGAL_SOURCE_REGISTRY.items():
        if not source_id or source_id.strip() != source_id:
            errors.append(f"ID inválido: {source_id!r}")
        for key in (
            "title",
            "locator",
            "authority",
            "official_url",
            "observed_status",
            "verified_on",
            "review_due_on",
            "topics",
        ):
            if record.get(key) in (None, "", []):
                errors.append(f"{source_id}: falta {key}")
        try:
            verified_on = _as_date(str(record.get("verified_on")))
            review_due_on = _as_date(str(record.get("review_due_on")))
            if review_due_on < verified_on:
                errors.append(f"{source_id}: review_due_on anterior a verified_on")
        except ValueError:
            errors.append(f"{source_id}: fecha de verificación/revisión inválida")

        parsed = urlparse(str(record.get("official_url") or ""))
        if parsed.scheme != "https" or parsed.netloc not in OFFICIAL_DOMAINS:
            errors.append(f"{source_id}: fuente no pertenece al allowlist oficial ({parsed.netloc})")

    if errors:
        raise ValueError("Registro normativo inválido: " + "; ".join(errors))


def get_legal_source(source_id: str, *, as_of: date | None = None) -> dict:
    if source_id not in LEGAL_SOURCE_REGISTRY:
        raise KeyError(f"Fuente jurídica no registrada: {source_id}")
    record = deepcopy(LEGAL_SOURCE_REGISTRY[source_id])
    record["id"] = source_id
    effective_date = as_of or date.today()
    record["freshness_status"] = (
        "current"
        if effective_date <= _as_date(record["review_due_on"])
        else "needs_reverification"
    )
    return record


def build_legal_source_manifest(
    source_ids: Iterable[str],
    *,
    as_of: date | None = None,
) -> dict:
    effective_date = as_of or date.today()
    ordered_ids = list(dict.fromkeys(str(item) for item in source_ids))
    sources = [get_legal_source(source_id, as_of=effective_date) for source_id in ordered_ids]
    stale = [item["id"] for item in sources if item["freshness_status"] != "current"]
    return {
        "standard": "M33.4",
        "as_of": effective_date.isoformat(),
        "status": "current" if not stale else "needs_reverification",
        "source_ids": ordered_ids,
        "stale_source_ids": stale,
        "sources": sources,
        "legal_effect": (
            "traceability_only; human_legal_review_required"
            if not stale
            else "release_block_reverification_required"
        ),
    }


def source_control_lines(source_ids: Iterable[str], *, as_of: date | None = None) -> list[str]:
    manifest = build_legal_source_manifest(source_ids, as_of=as_of)
    return [
        (
            f"Fuente jurídica de control [{record['id']}]: {record['title']} · {record['locator']} · "
            f"{record['authority']} · verificada {record['verified_on']} · "
            f"estado {record['freshness_status']}."
        )
        for record in manifest["sources"]
    ]


validate_registry()
