from __future__ import annotations

"""Perfiles de paginación contractual M33.2 por producto.

Se ejecutan después del estilo contractual de referencia y antes del preflight final.
Los perfiles solo reducen respiración vertical cuando un contrato jurídicamente más
profundo genera una cola de firma escasa. No modifican texto, fuente, márgenes, tablas,
reglas, conclusiones jurídicas ni el contenido de las firmas.
"""

from pathlib import Path

from docx import Document
from docx.shared import Pt

from m33_2_contract_style_finalize import CLAUSE_BEFORE_PT, PARAGRAPH_AFTER_PT

EMPLOYMENT_PRODUCT = "CO-LA-002"
LEASE_PRODUCT = "CO-AR-001"

EMPLOYMENT_PARAGRAPH_AFTER_PT = 4
EMPLOYMENT_CLAUSE_BEFORE_PT = 4
EMPLOYMENT_SIGNATURE_BEFORE_PT = 4

LEASE_PARAGRAPH_AFTER_PT = 4
LEASE_CLAUSE_BEFORE_PT = 4
LEASE_SIGNATURE_BEFORE_PT = 4

_PRODUCT_PROFILES = {
    EMPLOYMENT_PRODUCT: {
        "profile": "M33.2-employment-pagination",
        "paragraph_after_pt": EMPLOYMENT_PARAGRAPH_AFTER_PT,
        "clause_before_pt": EMPLOYMENT_CLAUSE_BEFORE_PT,
        "signature_before_pt": EMPLOYMENT_SIGNATURE_BEFORE_PT,
    },
    LEASE_PRODUCT: {
        "profile": "M33.2-lease-pagination",
        "paragraph_after_pt": LEASE_PARAGRAPH_AFTER_PT,
        "clause_before_pt": LEASE_CLAUSE_BEFORE_PT,
        "signature_before_pt": LEASE_SIGNATURE_BEFORE_PT,
    },
}


def _points(value) -> float | None:
    return None if value is None else float(value.pt)


def finalize_contract_pagination(path: str | Path, *, product_code: str) -> dict:
    """Aplica un perfil de compactación permitido, preservando contenido y 11 pt."""
    code = str(product_code or "").strip().upper()
    profile = _PRODUCT_PROFILES.get(code)
    if profile is None:
        return {
            "applied": False,
            "profile": "M33.2-contract-pagination",
            "reason": "product_without_pagination_profile",
        }

    paragraph_after_pt = profile["paragraph_after_pt"]
    clause_before_pt = profile["clause_before_pt"]
    signature_before_pt = profile["signature_before_pt"]

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
            paragraph.paragraph_format.space_before = Pt(signature_before_pt)
            paragraph.paragraph_format.space_after = Pt(paragraph_after_pt)
            signature_headings += 1
            continue

        after = _points(paragraph.paragraph_format.space_after)
        if after is not None and abs(after - PARAGRAPH_AFTER_PT) < 0.01:
            paragraph.paragraph_format.space_after = Pt(paragraph_after_pt)
            paragraphs_compacted += 1

        before = _points(paragraph.paragraph_format.space_before)
        if before is not None and abs(before - CLAUSE_BEFORE_PT) < 0.01:
            paragraph.paragraph_format.space_before = Pt(clause_before_pt)
            clauses_compacted += 1

    document.save(target)
    return {
        "applied": True,
        "profile": profile["profile"],
        "product_code": code,
        "font_size_preserved_pt": 11,
        "paragraph_spacing_after_pt": paragraph_after_pt,
        "clause_spacing_before_pt": clause_before_pt,
        "signature_spacing_before_pt": signature_before_pt,
        "paragraphs_compacted": paragraphs_compacted,
        "clauses_compacted": clauses_compacted,
        "signature_headings": signature_headings,
    }


__all__ = [
    "EMPLOYMENT_CLAUSE_BEFORE_PT",
    "EMPLOYMENT_PARAGRAPH_AFTER_PT",
    "EMPLOYMENT_SIGNATURE_BEFORE_PT",
    "LEASE_CLAUSE_BEFORE_PT",
    "LEASE_PARAGRAPH_AFTER_PT",
    "LEASE_SIGNATURE_BEFORE_PT",
    "finalize_contract_pagination",
]
