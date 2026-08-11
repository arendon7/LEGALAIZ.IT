from __future__ import annotations

"""Ajuste de paginación contractual específico para CO-LA-002.

Se aplica después del estilo contractual M33.2 y únicamente al contrato laboral.
No modifica texto, fuente, márgenes, tablas, reglas ni conclusiones jurídicas: reduce
la respiración vertical de 6 a 4 pt y compacta el encabezado de firmas para evitar
una cola de firma escasa provocada por cláusulas sustantivas más extensas.

El preflight técnico final permanece a cargo de ``build_m33_presentation``, que conoce
si el archivo es borrador o ``approval_candidate`` y aplica el perfil correcto.
"""

from pathlib import Path

from docx import Document
from docx.shared import Pt

from m33_2_contract_style_finalize import CLAUSE_BEFORE_PT, PARAGRAPH_AFTER_PT

EMPLOYMENT_PRODUCT = "CO-LA-002"
EMPLOYMENT_PARAGRAPH_AFTER_PT = 4
EMPLOYMENT_CLAUSE_BEFORE_PT = 4
EMPLOYMENT_SIGNATURE_BEFORE_PT = 4


def _points(value) -> float | None:
    return None if value is None else float(value.pt)


def finalize_contract_pagination(path: str | Path, *, product_code: str) -> dict:
    """Compacta solo CO-LA-002 preservando íntegro el contenido y Book Antiqua 11 pt."""
    if str(product_code or "").strip().upper() != EMPLOYMENT_PRODUCT:
        return {
            "applied": False,
            "profile": "M33.2-contract-pagination",
            "reason": "non_employment_contract",
        }

    target = Path(path)
    document = Document(target)
    paragraphs_compacted = 0
    clauses_compacted = 0
    signature_headings = 0

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = str(getattr(getattr(paragraph, "style", None), "name", "") or "").casefold()
        if style_name == "title":
            continue

        if text.upper() == "FIRMAS":
            paragraph.paragraph_format.space_before = Pt(EMPLOYMENT_SIGNATURE_BEFORE_PT)
            paragraph.paragraph_format.space_after = Pt(EMPLOYMENT_PARAGRAPH_AFTER_PT)
            signature_headings += 1
            continue

        after = _points(paragraph.paragraph_format.space_after)
        if after is not None and abs(after - PARAGRAPH_AFTER_PT) < 0.01:
            paragraph.paragraph_format.space_after = Pt(EMPLOYMENT_PARAGRAPH_AFTER_PT)
            paragraphs_compacted += 1

        before = _points(paragraph.paragraph_format.space_before)
        if before is not None and abs(before - CLAUSE_BEFORE_PT) < 0.01:
            paragraph.paragraph_format.space_before = Pt(EMPLOYMENT_CLAUSE_BEFORE_PT)
            clauses_compacted += 1

    document.save(target)
    return {
        "applied": True,
        "profile": "M33.2-employment-pagination",
        "font_size_preserved_pt": 11,
        "paragraph_spacing_after_pt": EMPLOYMENT_PARAGRAPH_AFTER_PT,
        "clause_spacing_before_pt": EMPLOYMENT_CLAUSE_BEFORE_PT,
        "signature_spacing_before_pt": EMPLOYMENT_SIGNATURE_BEFORE_PT,
        "paragraphs_compacted": paragraphs_compacted,
        "clauses_compacted": clauses_compacted,
        "signature_headings": signature_headings,
    }


__all__ = [
    "EMPLOYMENT_CLAUSE_BEFORE_PT",
    "EMPLOYMENT_PARAGRAPH_AFTER_PT",
    "EMPLOYMENT_SIGNATURE_BEFORE_PT",
    "finalize_contract_pagination",
]
