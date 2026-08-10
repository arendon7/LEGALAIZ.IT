from __future__ import annotations

"""Paquete normativo M33.4 para CO-LA-002."""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


EMPLOYMENT_SOURCE_RECORDS = {
    "CO-CST-EMPLOYMENT-2026": {
        "title": "Código Sustantivo del Trabajo vigente",
        "locator": "Artículos 46, 47, 115, 160, 161, 162 y 168, entre otros aplicables, con modificaciones incorporadas",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo%2F30019323",
        "observed_status": "texto oficial consultado con modificaciones vigentes incorporadas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["contrato de trabajo", "duración", "jornada", "trabajo nocturno", "recargos", "debido proceso disciplinario"],
    },
    "CO-LEY2466-2025": {
        "title": "Ley 2466 de 2025",
        "locator": "Reforma laboral; disposiciones sobre modalidades contractuales, jornada, trabajo nocturno, descanso obligatorio y demás materias aplicables",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes/30055086",
        "observed_status": "vigente; modificaciones relevantes incorporadas o aplicables según su régimen temporal",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["reforma laboral", "término indefinido", "término fijo", "obra o labor", "jornada", "recargos"],
    },
    "CO-LEY2101-2021": {
        "title": "Ley 2101 de 2021",
        "locator": "Reducción gradual de la jornada laboral semanal hasta cuarenta y dos (42) horas",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F30042017",
        "observed_status": "vigente; reducción gradual y protección de remuneración y derechos adquiridos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["jornada máxima", "42 horas", "reducción gradual"],
    },
    "CO-LEY2191-2022": {
        "title": "Ley 2191 de 2022",
        "locator": "Derecho a la desconexión laboral",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30043769",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["desconexión laboral", "descanso", "tiempo libre"],
    },
    "CO-LEY1010-2006": {
        "title": "Ley 1010 de 2006",
        "locator": "Prevención, corrección y sanción del acoso laboral; texto vigente y modificaciones incorporadas",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F30044240",
        "observed_status": "vigente; la fuente oficial expone evolución normativa y jurisprudencial de sus disposiciones",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["acoso laboral", "prevención", "procedimiento interno", "protección laboral"],
    },
}


for source_id, record in EMPLOYMENT_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


EMPLOYMENT_SOURCE_IDS = [
    "CO-CST-EMPLOYMENT-2026",
    "CO-LEY2466-2025",
    "CO-LEY2101-2021",
    "CO-LEY2191-2022",
    "CO-D1072-SGRL-SGSST",
    "CO-LEY1010-2006",
    "CO-LEY1581-2012",
    "CO-D1074-DATOS",
    "CO-LEY527-ARTS6-7-14",
]


__all__ = ["EMPLOYMENT_SOURCE_IDS", "EMPLOYMENT_SOURCE_RECORDS"]
