from __future__ import annotations

"""Cierre editorial del formato contractual M33.2.

Opera después de `m33_2_reference_format` y corrige únicamente detalles de
presentación del DOCX: ordinal con punto, título de cláusula con dos puntos,
y alineación del rótulo de firmas. No modifica el contenido jurídico.
"""

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

FONT_NAME = "Book Antiqua"
BODY_PT = 11

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


def finalize_contract_style(path: str | Path) -> dict:
    target = Path(path)
    document = Document(target)
    changed = 0
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text.upper() == "FIRMAS":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(8)
            paragraph.paragraph_format.space_after = Pt(6)
            for run in paragraph.runs:
                _font(run, bold=True)
            continue
        if not paragraph.runs:
            continue
        first = paragraph.runs[0]
        if first.bold is not True:
            continue
        canonical = _canonical_label(first.text)
        if canonical is None:
            continue
        if first.text != canonical:
            first.text = canonical
            _font(first, bold=True)
            changed += 1
    document.save(target)
    return {"profile": "M33.2", "canonical_clause_labels": changed}


__all__ = ["finalize_contract_style"]
