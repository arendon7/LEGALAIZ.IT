from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def clean_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def extract_docx(path: Path) -> dict:
    paragraphs, tables = [], []
    with ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
        body = root.find(f'{W}body')
        if body is None:
            return {'format': 'docx', 'paragraphs': [], 'tables': [], 'paragraph_count': 0, 'table_count': 0}
        for node in list(body):
            if node.tag == f'{W}p':
                text = clean_text(''.join(t.text or '' for t in node.iter(f'{W}t')))
                if text:
                    paragraphs.append(text)
            elif node.tag == f'{W}tbl':
                rows = []
                for tr in node.findall(f'.//{W}tr'):
                    row = []
                    for tc in tr.findall(f'./{W}tc'):
                        row.append(clean_text(' '.join(t.text or '' for t in tc.iter(f'{W}t'))))
                    if any(row):
                        rows.append(row)
                if rows:
                    tables.append(rows)
    return {
        'format': 'docx',
        'paragraph_count': len(paragraphs),
        'table_count': len(tables),
        'paragraphs': paragraphs,
        'tables': tables,
    }


def _xlsx_shared_strings(z: ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    return [clean_text(''.join(t.text or '' for t in si.iter(f'{S}t'))) for si in root.findall(f'{S}si')]


def extract_xlsx(path: Path) -> dict:
    sheets = []
    with ZipFile(path) as z:
        shared = _xlsx_shared_strings(z)
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        for sh in workbook.findall(f'.//{S}sheet'):
            name = sh.attrib.get('name', 'Hoja')
            target = targets.get(sh.attrib.get(f'{R}id'))
            if not target:
                continue
            xml_path = 'xl/' + target.lstrip('/') if not target.startswith('xl/') else target
            sheet = ET.fromstring(z.read(xml_path))
            rows = []
            for row in sheet.findall(f'.//{S}row'):
                values = []
                for cell in row.findall(f'{S}c'):
                    ctype = cell.attrib.get('t')
                    value = cell.find(f'{S}v')
                    raw = value.text if value is not None else ''
                    if ctype == 's' and raw.isdigit() and int(raw) < len(shared):
                        raw = shared[int(raw)]
                    elif ctype == 'inlineStr':
                        raw = ''.join(t.text or '' for t in cell.iter(f'{S}t'))
                    values.append(clean_text(raw))
                if any(values):
                    rows.append(values)
            sheets.append({'name': name, 'row_count': len(rows), 'rows': rows})
    return {'format': 'xlsx', 'sheet_count': len(sheets), 'sheets': sheets}


def extract_pdf(path: Path) -> dict:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError('Para extraer PDF instale opcionalmente pypdf: python3 -m pip install pypdf') from exc
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ''
        pages.append({'page': index, 'text': text.strip()})
    return {'format': 'pdf', 'page_count': len(pages), 'pages': pages}


def extract_source(path: Path) -> dict:
    ext = path.suffix.lower()
    if ext == '.docx':
        return extract_docx(path)
    if ext == '.xlsx':
        return extract_xlsx(path)
    if ext == '.pdf':
        return extract_pdf(path)
    if ext in {'.txt', '.md'}:
        text = path.read_text(encoding='utf-8', errors='replace')
        return {'format': ext[1:], 'character_count': len(text), 'text': text}
    raise ValueError('Formato no soportado. Use DOCX, XLSX, PDF, TXT o MD.')
