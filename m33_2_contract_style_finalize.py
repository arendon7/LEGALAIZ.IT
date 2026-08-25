from __future__ import annotations

"""Cierre editorial del formato contractual M33.2.

Opera después de `m33_2_reference_format` y corrige únicamente detalles de
presentación del DOCX: ordinal con punto, título de cláusula con dos puntos,
alineación del rótulo de firmas y respiración visual entre párrafos. No modifica
el contenido jurídico.
"""

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

FONT_NAME = "Book Antiqua"
BODY_PT = 11
PARAGRAPH_AFTER_PT = 6
CLAUSE_BEFORE_PT = 6

_ORDINAL = (
    r"PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|OCTAVA|NOVENA|D[ÉE]CIMA|"
    r"D[ÉE]CIMA\s+PRIMERA|D[ÉE]CIMA\s+SEGUNDA|D[ÉE]CIMA\s+TERCERA|D[ÉE]CIMA\s+CUARTA|"
    r"D[ÉE]CIMA\s+QUINTA|D[ÉE]CIMA\s+SEXTA|D[ÉE]CIMA\s+S[ÉE]PTIMA|D[ÉE]CIMA\s+OCTAVA|"
    r"D[ÉE]CIMA\s+NOVENA|VIG[ÉE]SIMA|VIG[ÉE]SIMA\s+PRIMERA|VIG[ÉE]SIMA\s+SEGUNDA|"
    r"VIG[ÉE]SIMA\s+TERCERA|VIG[ÉE]SIMA\s+CUARTA|VIG[ÉE]SIMA\s+QUINTA|"
    r"VIG[ÉE]SIMA\s+SEXTA|VIG[ÉE]SIMA\s+S[ÉE]PTIMA|VIG[ÉE]SIMA\s+OCTAVA|"
    r"VIG[ÉE]SIMA\s+NOVENA|TRIG[ÉE]SIMA|CUADRAG[ÉE]SIMA|QUINCUAG[ÉE]SIMA"
)
_INLINE_LABEL_RE = re.compile(rf"^({_ORDINAL})\s*[:.]\s*([^:]+):\s*$", re.IGNORECASE)


def _font(run, *, bold: bool | None = None) -> None:
    run.font.name = FONT_NAME
    rfonts = run._element.get_or_add_rPr().rFonts
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), FONT_NAME)
    run.font.size = Pt(BODY_PT)
    if bold is not None:
        run.bold = bold


def _canonical_label(text: str) -> str | None:
    match = _INLINE_LABEL_RE.match(str(text or "").strip())
    if not match:
        return None
    ordinal, subject = match.groups()
    return f"{ordinal.upper()}. {subject.strip().upper()}: "


def _is_title(paragraph) -> bool:
    style_name = str(getattr(getattr(paragraph, "style", None), "name", "") or "").casefold()
    return style_name == "title"


def finalize_contract_style(path: str | Path) -> dict:
    target = Path(path)
    document = Document(target)
    changed = 0
    spaced = 0
    clauses_spaced = 0

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if _is_title(paragraph):
            # El título conserva el espacio propio definido por M33.2 entre título y tabla.
            continue
        if text.upper() == "CONSIDERACIONES":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(CLAUSE_BEFORE_PT)
            paragraph.paragraph_format.space_after = Pt(PARAGRAPH_AFTER_PT)
            for run in paragraph.runs:
                _font(run, bold=True)
            spaced += 1
            continue
        if text.upper() == "FIRMAS":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(8)
            paragraph.paragraph_format.space_after = Pt(PARAGRAPH_AFTER_PT)
            for run in paragraph.runs:
                _font(run, bold=True)
            continue

        # Equivalente visual a un Enter entre párrafos, sin insertar párrafos vacíos.
        # Así se preservan paginación, tablas, hashes y estabilidad Word/LibreOffice.
        paragraph.paragraph_format.space_after = Pt(PARAGRAPH_AFTER_PT)
        spaced += 1

        if not paragraph.runs:
            continue
        first = paragraph.runs[0]
        if first.bold is not True:
            continue
        canonical = _canonical_label(first.text)
        if canonical is None:
            continue
        paragraph.paragraph_format.space_before = Pt(CLAUSE_BEFORE_PT)
        clauses_spaced += 1
        if first.text != canonical:
            first.text = canonical
            _font(first, bold=True)
            changed += 1

    document.save(target)
    return {
        "profile": "M33.2",
        "canonical_clause_labels": changed,
        "paragraph_spacing_after_pt": PARAGRAPH_AFTER_PT,
        "clause_spacing_before_pt": CLAUSE_BEFORE_PT,
        "spaced_paragraphs": spaced,
        "spaced_clauses": clauses_spaced,
    }


__all__ = [
    "CLAUSE_BEFORE_PT",
    "PARAGRAPH_AFTER_PT",
    "finalize_contract_style",
]
