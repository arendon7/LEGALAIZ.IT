from __future__ import annotations

"""Ajuste final M33.2 para evitar colas editoriales huérfanas en guías especiales.

Esta capa no modifica texto, hechos, reglas, conclusiones, fuentes ni efectos jurídicos.
Únicamente reduce espacios verticales —sin bajar Book Antiqua 11 pt— en documentos
clasificados como ``guide`` por la familia especial M33.2. El objetivo es impedir que
un último encabezado y un párrafo breve queden aislados en una página adicional cuando
pueden convivir de forma legible con el contenido precedente.
"""

from functools import wraps
from pathlib import Path

from docx import Document
from docx.shared import Pt

from document_standard_v33 import audit_docx_legal_standard
from m33_2_special_reference_format import classify_m33_2_special_document

GUIDE_TITLE_AFTER_PT = 6
GUIDE_SUBTITLE_AFTER_PT = 7
GUIDE_SECTION_BEFORE_PT = 5
GUIDE_SECTION_AFTER_PT = 3
GUIDE_BODY_AFTER_PT = 3


def _title_paragraph(document: Document, title: str):
    wanted = str(title or "").strip()
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == wanted:
            return paragraph
    return next((p for p in document.paragraphs if p.style and p.style.name == "Title"), None)


def _paragraph_after(document: Document, paragraph):
    if paragraph is None:
        return None
    sibling = paragraph._p.getnext()
    while sibling is not None:
        if sibling.tag.endswith("}p"):
            return next((p for p in document.paragraphs if p._p is sibling), None)
        sibling = sibling.getnext()
    return None


def apply_m33_2_special_pagination_finalize(
    path: str | Path,
    *,
    product_code: str,
    title: str,
) -> dict:
    """Compacta solo las guías especiales, conservando tipografía y contenido."""
    if classify_m33_2_special_document(product_code, title) != "guide":
        return {
            "applied": False,
            "profile": "M33.2-special-guide-pagination",
            "reason": "non_guide_document",
        }

    target = Path(path)
    document = Document(target)
    title_p = _title_paragraph(document, title)
    subtitle = _paragraph_after(document, title_p)

    if title_p is not None:
        title_p.paragraph_format.space_after = Pt(GUIDE_TITLE_AFTER_PT)
    if subtitle is not None and subtitle.text.strip():
        style_name = subtitle.style.name if subtitle.style else ""
        if not style_name.lower().startswith("heading"):
            subtitle.paragraph_format.space_after = Pt(GUIDE_SUBTITLE_AFTER_PT)

    headings = 0
    body_paragraphs = 0
    for paragraph in document.paragraphs:
        if not paragraph.text.strip():
            continue
        if title_p is not None and paragraph._p is title_p._p:
            continue
        if subtitle is not None and paragraph._p is subtitle._p:
            continue
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.lower().startswith("heading"):
            paragraph.paragraph_format.space_before = Pt(GUIDE_SECTION_BEFORE_PT)
            paragraph.paragraph_format.space_after = Pt(GUIDE_SECTION_AFTER_PT)
            paragraph.paragraph_format.keep_with_next = True
            headings += 1
        else:
            paragraph.paragraph_format.space_after = Pt(GUIDE_BODY_AFTER_PT)
            body_paragraphs += 1

    document.save(target)
    report = audit_docx_legal_standard(target)
    if not report.get("valid"):
        raise ValueError(
            f"Guía especial M33.2 no supera auditoría tras ajuste de paginación: {report.get('findings')}"
        )

    return {
        "applied": True,
        "profile": "M33.2-special-guide-pagination",
        "formatted_headings": headings,
        "formatted_body_paragraphs": body_paragraphs,
        "font_size_preserved_pt": 11,
    }


def install_m33_2_special_pagination_gate() -> bool:
    """Envuelve el constructor final y vuelve a gobernar el hash exacto resultante."""
    import docx_builder
    from legalai_platform.document_release_gate import enforce_document_release_gate, infer_product_code

    current = docx_builder.build_docx
    if getattr(current, "_legalaiz_m33_2_special_pagination", False):
        return True

    @wraps(current)
    def guarded_build_docx(*args, **kwargs):
        call_args = list(args)
        path = kwargs.get("path") or (call_args[0] if call_args else None)
        title = kwargs.get("title") or (call_args[1] if len(call_args) >= 2 else "")
        metadata = kwargs.get("metadata")
        if metadata is None and len(call_args) >= 4:
            metadata = call_args[3]
        product_code = str(
            kwargs.get("product_code")
            or infer_product_code(path or "document.docx", metadata)
            or ""
        ).upper()

        result = current(*args, **kwargs)
        final_path = Path(path or result)
        presentation = apply_m33_2_special_pagination_finalize(
            final_path,
            product_code=product_code,
            title=str(title or ""),
        )
        if presentation.get("applied"):
            enforce_document_release_gate(
                final_path,
                expected_product=product_code or None,
                metadata=metadata,
            )
        return result

    guarded_build_docx._legalaiz_m33_2_special_pagination = True
    guarded_build_docx._legalaiz_original = current
    docx_builder.build_docx = guarded_build_docx
    return True


__all__ = [
    "apply_m33_2_special_pagination_finalize",
    "install_m33_2_special_pagination_gate",
]
