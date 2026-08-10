from __future__ import annotations

"""Presentaciones documentales M33.x sin alterar el contenido jurídico aprobado.

La copia de revisión y el instrumento sometido a aprobación son artefactos distintos.
El instrumento `approval_candidate` nace limpio ANTES de las aprobaciones; por tanto,
el SHA-256 que revisan Jurídico y QA es el mismo que posteriormente puede liberarse.
Nunca se elimina una marca ni una página después de aprobar, porque eso cambiaría el
hash y rompería la trazabilidad.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

from docx import Document

from document_standard_v33 import STANDARD_VERSION, audit_docx_legal_standard
from docx_builder import build_docx
from m33_2_contract_style_finalize import finalize_contract_style
from m33_2_reference_format import apply_m33_2_reference_format


REVIEW_MODE = "review"
APPROVAL_CANDIDATE_MODE = "approval_candidate"
VALID_PRESENTATIONS = frozenset({REVIEW_MODE, APPROVAL_CANDIDATE_MODE})


def _is_control(section: dict[str, Any]) -> bool:
    heading = str(section.get("heading") or "")
    return (section.get("_type") or section.get("type")) == "control" or "control de uso" in heading.casefold()


def split_internal_review_sections(sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    for section in deepcopy(list(sections or [])):
        (internal if _is_control(section) else public).append(section)
    return public, internal


def review_evidence_from_sections(sections: list[dict[str, Any]]) -> dict[str, Any]:
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
        "presentation_standard": STANDARD_VERSION,
        "presentation_mode": APPROVAL_CANDIDATE_MODE,
        "controls_externalized": len(controls),
        "legal_sources": list(dict.fromkeys(sources)),
        "review_notes": notes,
        "release_rule": (
            "El DOCX approval_candidate debe aprobarse y liberarse sin transformación posterior; "
            "el SHA-256 aprobado es el mismo que posteriormente puede liberarse y Jurídico y QA "
            "deben decidir sobre ese archivo limpio exacto."
        ),
    }


def audit_m33_presentation(path: str | Path, presentation_mode: str) -> dict[str, Any]:
    mode = str(presentation_mode or REVIEW_MODE).strip().casefold()
    if mode not in VALID_PRESENTATIONS:
        raise ValueError(f"Modo de presentación M33 inválido: {presentation_mode}.")
    base = deepcopy(audit_docx_legal_standard(Path(path)))
    base["presentation_mode"] = mode
    if mode == APPROVAL_CANDIDATE_MODE:
        base["findings"] = [
            item for item in base.get("findings") or []
            if item.get("code") != "DRAFT-BANNER-MISSING"
        ]
        base["valid"] = not any(item.get("severity") == "error" for item in base["findings"])
    return base


def _stamp_internal_identity(path: Path, product_code: str, presentation_mode: str) -> None:
    document = Document(path)
    document.core_properties.subject = str(product_code or "").strip()
    document.core_properties.comments = f"LegalAIZ.it · {STANDARD_VERSION} · {presentation_mode}"
    document.save(path)


def build_m33_presentation(
    *,
    path: str | Path,
    title: str,
    subtitle: str,
    metadata: list[tuple[str, str]],
    sections: list[dict[str, Any]],
    product_code: str,
    presentation_mode: str = REVIEW_MODE,
    approval_subtitle: str = "",
    approval_metadata: list[tuple[str, str]] | None = None,
    footer: str = "LegalAIZ.it · Más que respuestas, soluciones.",
) -> dict[str, Any]:
    """Construye una copia de revisión o el instrumento exacto de aprobación.

    `approval_metadata` contiene exclusivamente datos jurídicamente útiles del
    instrumento. Los datos operativos de LegalAIZ.it permanecen fuera de la
    versión destinada a firma.
    """
    mode = str(presentation_mode or REVIEW_MODE).strip().casefold()
    if mode not in VALID_PRESENTATIONS:
        raise ValueError(f"Modo de presentación M33 inválido: {presentation_mode}.")

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
        rendered_metadata = list(approval_metadata or [])
        rendered_subtitle = str(approval_subtitle or "").strip()
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
        enforce_legal_standard=(mode == REVIEW_MODE),
        product_code=product_code,
    )

    if mode == APPROVAL_CANDIDATE_MODE:
        reference_format = apply_m33_2_reference_format(
            target,
            product_code=product_code,
            title=title,
            approval_subtitle=rendered_subtitle,
        )
        evidence["reference_format"] = reference_format
        if reference_format.get("applied"):
            evidence["reference_format_finalize"] = finalize_contract_style(target)

    _stamp_internal_identity(target, product_code, mode)
    technical = audit_m33_presentation(target, mode)
    if not technical["valid"]:
        try:
            target.unlink()
        except OSError:
            pass
        raise ValueError(
            f"DOCX bloqueado por estándar jurídico {technical['standard']} "
            f"({mode}): {technical['findings']}"
        )
    evidence["technical_preflight"] = technical
    return evidence


__all__ = [
    "APPROVAL_CANDIDATE_MODE",
    "REVIEW_MODE",
    "VALID_PRESENTATIONS",
    "audit_m33_presentation",
    "build_m33_presentation",
    "review_evidence_from_sections",
    "split_internal_review_sections",
]
