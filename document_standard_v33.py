from __future__ import annotations

"""Estándar documental jurídico transversal M33.2 de LegalAIZ.it.

Este módulo no contiene reglas sustantivas de un producto concreto. Define las
invariantes de presentación y QA que todas las salidas profesionales deben
cumplir antes de entrar a revisión jurídica y QA humano.
"""

from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

STANDARD_VERSION = "M33.2"
FONT_NAME = "Book Antiqua"
BODY_SIZE_HALF_POINTS = 22  # 11 pt
TABLE_SIZE_HALF_POINTS = 20  # 10 pt, para matrices densas
TITLE_SIZE_HALF_POINTS = 24  # 12 pt
HEADING_SIZE_HALF_POINTS = 22  # 11 pt
MARGIN_TWIPS = 1417  # 2,5 cm
HEADER_FOOTER_TWIPS = 567  # ~1 cm
LINE_SPACING_TWIPS = 240  # sencillo/compacto jurídico
PARAGRAPH_AFTER_TWIPS = 80  # 4 pt

SENTINEL_PATTERNS = (
    r"\{\{",
    r"\bundefined\b",
    r"\bnull\b",
    r"\bnone\b",
    r"\bn/?a\b",
    r"\[objeto pendiente\]",
    r"\[contratante\]",
    r"\[contratista\]",
    r"\[trabajador(?:a)?\]",
    r"\[empleador\]",
    r"\[arrendador(?:a)?\]",
    r"\[arrendatario\]",
    r"\[fecha\]",
    r"\[valor\]",
    r"\[nombre\]",
    r"\[documento\]",
    r"\[por diligenciar\]",
)

DECORATIVE_SEPARATOR_RE = re.compile(r"(?:_{4,}|={5,}|-{6,})")
ORDINAL_RE = re.compile(
    r"^(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|OCTAVA|NOVENA|D[ÉE]CIMA|"
    r"D[ÉE]CIMA\s+PRIMERA|D[ÉE]CIMA\s+SEGUNDA|D[ÉE]CIMA\s+TERCERA|D[ÉE]CIMA\s+CUARTA|"
    r"D[ÉE]CIMA\s+QUINTA|D[ÉE]CIMA\s+SEXTA|D[ÉE]CIMA\s+S[ÉE]PTIMA|D[ÉE]CIMA\s+OCTAVA|"
    r"D[ÉE]CIMA\s+NOVENA|VIG[ÉE]SIMA|TRIG[ÉE]SIMA|CUADRAG[ÉE]SIMA|QUINCUAG[ÉE]SIMA)\b",
    re.IGNORECASE,
)


def _plain_section_text(section: dict) -> str:
    chunks: list[str] = [str(section.get("heading") or "")]
    if section.get("text"):
        chunks.append(str(section["text"]))
    chunks.extend(str(x) for x in section.get("paragraphs") or [])
    chunks.extend(str(x) for x in section.get("bullets") or [])
    for row in section.get("table") or []:
        chunks.extend(str(x) for x in row)
    for party in section.get("parties") or []:
        if isinstance(party, dict):
            chunks.extend(str(party.get(k) or "") for k in ("label", "name", "id", "role", "email"))
    return "\n".join(chunks)


def find_sentinels(text: str) -> list[str]:
    found: list[str] = []
    lowered = str(text or "").casefold()
    for pattern in SENTINEL_PATTERNS:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return sorted(set(found))


def validate_rendered_sections(sections: list[dict], *, product_code: str | None = None) -> dict:
    """QA semántico mínimo previo a empaquetar el DOCX."""
    errors: list[dict] = []
    warnings: list[dict] = []
    headings: set[str] = set()
    word_count = 0
    clause_count = 0
    annex_count = 0
    signature_count = 0

    for index, section in enumerate(sections or [], 1):
        heading = str(section.get("heading") or "").strip()
        section_type = str(section.get("_type") or section.get("type") or "section")
        plain = _plain_section_text(section)
        word_count += len(re.findall(r"\b\w+\b", plain, re.UNICODE))

        if not heading and section_type != "signature":
            errors.append({"code": "SECTION-WITHOUT-HEADING", "section": index})
        normalized_heading = re.sub(r"\s+", " ", heading).casefold()
        if heading and normalized_heading in headings:
            warnings.append({"code": "DUPLICATE-HEADING", "section": index, "detail": heading})
        headings.add(normalized_heading)

        sentinels = find_sentinels(plain)
        if sentinels:
            errors.append({"code": "UNRESOLVED-SENTINEL", "section": index, "detail": sentinels})
        if DECORATIVE_SEPARATOR_RE.search(plain):
            errors.append({"code": "DECORATIVE-SEPARATOR", "section": index})

        is_clause = section_type == "clause" or bool(ORDINAL_RE.match(heading))
        if is_clause:
            clause_count += 1
            substantive = " ".join(
                [str(section.get("text") or "")] +
                [str(x) for x in section.get("paragraphs") or []] +
                [str(x) for x in section.get("bullets") or []]
            ).strip()
            if len(substantive) < 160:
                warnings.append({"code": "THIN-CLAUSE", "section": index, "detail": f"{len(substantive)} caracteres sustantivos"})

        if section_type == "annex" or heading.upper().startswith("ANEXO"):
            annex_count += 1
            if index > 1 and not section.get("page_break_before"):
                warnings.append({"code": "ANNEX-WITHOUT-PAGE-BREAK", "section": index, "detail": heading})

        if section_type == "signature":
            signature_count += 1
            parties = list(section.get("parties") or [])
            if not parties:
                errors.append({"code": "SIGNATURE-WITHOUT-PARTIES", "section": index})
            if DECORATIVE_SEPARATOR_RE.search(plain):
                errors.append({"code": "MANUAL-SIGNATURE-LINE", "section": index})

    if not sections:
        errors.append({"code": "EMPTY-DOCUMENT"})

    return {
        "standard": STANDARD_VERSION,
        "product_code": product_code,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "sections": len(sections or []),
            "clauses": clause_count,
            "annexes": annex_count,
            "signature_sections": signature_count,
            "words": word_count,
        },
    }


def audit_docx_legal_standard(path: Path) -> dict:
    """Verifica en OOXML las invariantes formales aprobadas para M33.2."""
    path = Path(path)
    findings: list[dict] = []
    try:
        with ZipFile(path) as zf:
            names = set(zf.namelist())
            required = {
                "[Content_Types].xml",
                "word/document.xml",
                "word/styles.xml",
                "word/header1.xml",
                "word/footer1.xml",
                "docProps/core.xml",
            }
            for missing in sorted(required - names):
                findings.append({"severity": "error", "code": "DOCX-MISSING-PART", "detail": missing})

            document = zf.read("word/document.xml").decode("utf-8", "replace") if "word/document.xml" in names else ""
            styles = zf.read("word/styles.xml").decode("utf-8", "replace") if "word/styles.xml" in names else ""
            header = zf.read("word/header1.xml").decode("utf-8", "replace") if "word/header1.xml" in names else ""
            footer = zf.read("word/footer1.xml").decode("utf-8", "replace") if "word/footer1.xml" in names else ""
            plain = re.sub(r"<[^>]+>", " ", document)

            sentinels = find_sentinels(plain)
            if sentinels:
                findings.append({"severity": "error", "code": "UNRESOLVED-SENTINEL", "detail": sentinels})
            if DECORATIVE_SEPARATOR_RE.search(plain):
                findings.append({"severity": "error", "code": "DECORATIVE-SEPARATOR", "detail": "Se detectaron líneas manuales o separadores decorativos."})

            if FONT_NAME not in styles or 'w:sz w:val="22"' not in styles:
                findings.append({"severity": "error", "code": "LEGAL-FONT-STYLE", "detail": "Normal debe usar Book Antiqua 11 pt."})
            if "Arial" in styles or "Times New Roman" in styles:
                findings.append({"severity": "error", "code": "LEGACY-FONT-STYLE", "detail": "El estilo base conserva una tipografía anterior."})

            margin_fragment = f'w:top="{MARGIN_TWIPS}" w:right="{MARGIN_TWIPS}" w:bottom="{MARGIN_TWIPS}" w:left="{MARGIN_TWIPS}"'
            if margin_fragment not in document:
                findings.append({"severity": "error", "code": "LEGAL-MARGINS", "detail": "Márgenes principales deben ser 2,5 cm."})

            if f'w:line="{LINE_SPACING_TWIPS}"' not in document and f'w:line="{LINE_SPACING_TWIPS}"' not in styles:
                findings.append({"severity": "error", "code": "LEGAL-LINE-SPACING", "detail": "Interlineado compacto jurídico no acreditado."})

            justified = document.count('<w:jc w:val="both"/>')
            body_paragraphs = max(1, document.count("<w:p>"))
            if justified < max(1, body_paragraphs // 5):
                findings.append({"severity": "warning", "code": "LOW-JUSTIFICATION-COVERAGE", "detail": f"{justified}/{body_paragraphs}"})

            table_count = document.count("<w:tbl>")
            header_rows = document.count("<w:tblHeader")
            if table_count and header_rows < max(0, table_count - signature_count_from_xml(document)):
                findings.append({"severity": "warning", "code": "TABLE-HEADER-NOT-REPEATED", "detail": f"{header_rows}/{table_count}"})

            if "BORRADOR CONTROLADO" not in header:
                findings.append({"severity": "error", "code": "DRAFT-BANNER-MISSING", "detail": "Encabezado sin control de borrador."})
            if "PAGE" not in footer or "NUMPAGES" not in footer:
                findings.append({"severity": "error", "code": "PAGE-FIELDS-MISSING", "detail": "Pie sin PAGE/NUMPAGES."})
    except (BadZipFile, KeyError, OSError) as exc:
        findings.append({"severity": "error", "code": "INVALID-DOCX", "detail": str(exc)})

    return {
        "standard": STANDARD_VERSION,
        "path": str(path),
        "valid": not any(item["severity"] == "error" for item in findings),
        "findings": findings,
    }


def signature_count_from_xml(document_xml: str) -> int:
    return document_xml.count('w:tblDescription w:val="LegalAIZ-SignatureTable"')
