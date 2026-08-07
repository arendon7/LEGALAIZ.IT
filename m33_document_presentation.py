from __future__ import annotations

"""Presentaciones documentales M33.0 sin alterar el contenido jurídico aprobado.

La copia de revisión y el instrumento sometido a aprobación son artefactos distintos.
El instrumento `approval_candidate` nace limpio ANTES de las aprobaciones; por tanto,
el SHA-256 que revisan Jurídico y QA es el mismo que posteriormente puede liberarse.
Nunca se elimina una marca ni una página después de aprobar, porque eso cambiaría el
hash y rompería la trazabilidad.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

from docx_builder import build_docx


REVIEW_MODE = "review"
APPROVAL_CANDIDATE_MODE = "approval_candidate"
VALID_PRESENTATIONS = frozenset({REVIEW_MODE, APPROVAL_CANDIDATE_MODE})


def _is_control(section: dict[str, Any]) -> bool:
    heading = str(section.get("heading") or "")
    return (section.get("_type") or section.get("type")) == "control" or "control de uso" in heading.casefold()


def split_internal_review_sections(sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa contenido contractual de evidencias internas sin perder trazabilidad."""
    public: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    for section in deepcopy(list(sections or [])):
        (internal if _is_control(section) else public).append(section)
    return public, internal


def review_evidence_from_sections(sections: list[dict[str, Any]]) -> dict[str, Any]:
    """Extrae controles/fuentes para persistirlos en el manifiesto, no en el contrato."""
    _, controls = split_internal_review_sections(sections)
    sources: list[str] = []
    notes: list[str] = []
    for section in controls:
        text = str(section.get("text") or "").strip()
        if text:
            notes.append(text)
        for item in section.get("bullets") or []:
            value = str(item).strip()
            if not value:
                continue
            prefix = "Fuente jurídica de control:"
            if value.casefold().startswith(prefix.casefold()):
                value = value[len(prefix):].strip()
            sources.append(value)
    return {
        "document_standard": "M33.0",
        "presentation_mode": APPROVAL_CANDIDATE_MODE,
        "controls_externalized": len(controls),
        "legal_sources": list(dict.fromkeys(sources)),
        "review_notes": notes,
        "release_rule": (
            "El DOCX approval_candidate debe aprobarse y liberarse sin transformación posterior; "
            "Jurídico y QA deben aprobar el SHA-256 exacto del archivo limpio."
        ),
    }


def build_m33_presentation(
    *,
    path: str | Path,
    title: str,
    subtitle: str,
    metadata: list[tuple[str, str]],
    sections: list[dict[str, Any]],
    product_code: str,
    presentation_mode: str = REVIEW_MODE,
    footer: str = "LegalAIZ.it · Más que respuestas, soluciones.",
) -> dict[str, Any]:
    """Construye una copia de revisión o el instrumento exacto de aprobación."""
    mode = str(presentation_mode or REVIEW_MODE).strip().casefold()
    if mode not in VALID_PRESENTATIONS:
        raise ValueError(f"Modo de presentación M33.0 inválido: {presentation_mode}.")

    target = Path(path)
    if mode == REVIEW_MODE:
        rendered_sections = deepcopy(list(sections or []))
        rendered_metadata = list(metadata or [])
        rendered_subtitle = subtitle
        status = "BORRADOR CONTROLADO · NO FIRMAR"
        append_control = True
        evidence = review_evidence_from_sections(sections)
        evidence["presentation_mode"] = REVIEW_MODE
    else:
        rendered_sections, _ = split_internal_review_sections(sections)
        # Los datos operativos (producto, estándar, estado interno) viven en el
        # expediente y no forman parte del instrumento jurídico que se firma.
        rendered_metadata = []
        rendered_subtitle = ""
        status = ""
        append_control = False
        evidence = review_evidence_from_sections(sections)

    build_docx(
        target,
        title,
        rendered_subtitle,
        rendered_metadata,
        rendered_sections,
        footer=footer,
        append_default_control=append_control,
        document_status=status,
        enforce_legal_standard=True,
        product_code=product_code,
    )
    return evidence


__all__ = [
    "APPROVAL_CANDIDATE_MODE",
    "REVIEW_MODE",
    "VALID_PRESENTATIONS",
    "build_m33_presentation",
    "review_evidence_from_sections",
    "split_internal_review_sections",
]
