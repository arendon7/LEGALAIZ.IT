from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _image_paragraph(rel_id="rId2", cx=3657600, cy=1159200):
    return f'''<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="100"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="1" name="LegalAIZ.it"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="logo-legalaizit-docx.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''


def _run(text: str, bold=False, italic=False, size=22, color=None):
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if size:
        props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    run_props = f'<w:rPr>{"".join(props)}</w:rPr>' if props else ""
    return f'<w:r>{run_props}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _paragraph(
    text="",
    style=None,
    bold=False,
    italic=False,
    size=22,
    color=None,
    align=None,
    spacing_after=120,
    keep_next=False,
    page_break_before=False,
):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    if page_break_before:
        ppr.append("<w:pageBreakBefore/>")
    ppr.append('<w:widowControl/><w:keepLines/>')
    ppr.append(f'<w:spacing w:after="{spacing_after}"/>')
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{_run(text, bold, italic, size, color)}</w:p>'


def _table(rows):
    """Renderiza matrices de dos o más columnas sin romper documentos históricos."""
    normalized = [tuple(row) for row in rows]
    column_count = max((len(row) for row in normalized), default=0)
    if column_count == 0:
        return ""
    if column_count == 2:
        widths = [3100, 6100]
    else:
        first = min(2200, max(1500, 9200 // column_count))
        remaining = 9200 - first
        base = remaining // (column_count - 1)
        widths = [first] + [base] * (column_count - 1)
        widths[-1] += 9200 - sum(widths)
    rendered_rows = []
    for i, row in enumerate(normalized):
        values = list(row) + [""] * (column_count - len(row))
        cells = []
        for j, value in enumerate(values):
            shade = '<w:shd w:fill="F7F5F1"/>' if i == 0 else ""
            bold = i == 0 or j == 0
            cells.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>{shade}</w:tcPr>'
                f'{_paragraph(str(value), bold=bold, size=19, spacing_after=40)}</w:tc>'
            )
        row_props = '<w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if i == 0 else '') + '</w:trPr>'
        rendered_rows.append('<w:tr>' + row_props + ''.join(cells) + '</w:tr>')
    borders = '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="E6E6E1"/><w:left w:val="single" w:sz="4" w:color="E6E6E1"/><w:bottom w:val="single" w:sz="4" w:color="E6E6E1"/><w:right w:val="single" w:sz="4" w:color="E6E6E1"/><w:insideH w:val="single" w:sz="4" w:color="E6E6E1"/><w:insideV w:val="single" w:sz="4" w:color="E6E6E1"/></w:tblBorders>'
    return f'<w:tbl><w:tblPr><w:tblW w:w="9200" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar>{borders}</w:tblPr>{"".join(rendered_rows)}</w:tbl>'


def _signature_table(parties):
    parties = list(parties or [])[:2]
    while len(parties) < 2:
        parties.append({"label": "Firma", "name": ""})
    rows = []
    cells = []
    for party in parties:
        label = escape(str(party.get("label") or "Firma"))
        name = escape(str(party.get("name") or ""))
        content = (
            '<w:p><w:pPr><w:spacing w:before="480" w:after="60"/></w:pPr>'
            '<w:r><w:t>________________________________</w:t></w:r></w:p>'
            f'<w:p><w:pPr><w:spacing w:after="30"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{name or label}</w:t></w:r></w:p>'
            f'<w:p><w:pPr><w:spacing w:after="30"/></w:pPr><w:r><w:t>{label if name else ""}</w:t></w:r></w:p>'
        )
        cells.append(f'<w:tc><w:tcPr><w:tcW w:w="4600" w:type="dxa"/></w:tcPr>{content}</w:tc>')
    rows.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + ''.join(cells) + '</w:tr>')
    return '<w:tbl><w:tblPr><w:tblW w:w="9200" w:type="dxa"/></w:tblPr>' + ''.join(rows) + '</w:tbl>'


def _header_xml(status_banner: str):
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:hdr xmlns:w="{NS}"><w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs>'
        '<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="5" w:color="C9A96E"/></w:pBdr>'
        '<w:spacing w:after="60"/></w:pPr>'
        f'{_run("LegalAIZ.it", bold=True, size=20, color="0D1324")}<w:r><w:tab/></w:r>'
        f'{_run(status_banner, bold=True, size=15, color="C94040")}</w:p></w:hdr>'
    )


def _page_field(instruction: str):
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> {escape(instruction)} </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>1</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def _footer_xml(text: str):
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{NS}"><w:p><w:pPr><w:jc w:val="center"/>'
        '<w:pBdr><w:top w:val="single" w:sz="4" w:space="5" w:color="E6E6E1"/></w:pBdr>'
        '<w:spacing w:before="80"/></w:pPr>'
        f'{_run(text + " · Página ", size=16, color="666666")}{_page_field("PAGE")}'
        f'{_run(" de ", size=16, color="666666")}{_page_field("NUMPAGES")}</w:p></w:ftr>'
    )


def build_docx(
    path: Path,
    title: str,
    subtitle: str,
    metadata: list[tuple[str, str]],
    sections: list[dict],
    footer="LegalAIZ.it · Más que respuestas, soluciones.",
    append_default_control=True,
    document_status="BORRADOR CONTROLADO · NO FIRMAR",
):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = []
    logo_path = Path(__file__).resolve().parent / "app" / "assets" / "logo-legalaizit-docx.png"
    has_logo = logo_path.is_file()
    if has_logo:
        body.append(_image_paragraph())
        body.append(_paragraph("", spacing_after=90))
    else:
        body.append(_paragraph("LegalAIZ.it", bold=True, size=34, color="0D1324", align="center", spacing_after=40))
        body.append(_paragraph("Más que respuestas, soluciones.", italic=True, size=20, color="C9A96E", align="center", spacing_after=150))
    body.append(_paragraph(title, style="Title", bold=True, size=36, color="0D1324", align="center", spacing_after=120))
    body.append(_paragraph(subtitle, italic=True, size=21, color="555555", align="center", spacing_after=260))
    if metadata:
        body.append(_table([("Campo", "Información")] + [(str(a), str(b)) for a, b in metadata]))
        body.append(_paragraph("", spacing_after=80))
    has_control = False
    for sec_index, sec in enumerate(sections):
        heading = str(sec.get("heading", ""))
        section_type = sec.get("_type") or sec.get("type") or "section"
        is_control = section_type == "control" or "control de uso" in heading.casefold()
        if is_control:
            has_control = True
        if section_type == "signature":
            body.append(_paragraph(heading or "Firmas", style="Heading1", bold=True, size=26, color="0D1324", spacing_after=80, keep_next=True))
            body.append(_signature_table(sec.get("parties") or []))
            body.append(_paragraph("", spacing_after=60))
            continue
        keep = True  # Evita encabezados huérfanos y mejora la paginación contractual.
        heading_color = "C94040" if is_control else "0D1324"
        text_color = "7A2D2D" if is_control else "1F1F1F"
        body.append(
            _paragraph(
                heading,
                style="Heading1",
                bold=True,
                size=26,
                color=heading_color,
                spacing_after=80,
                keep_next=keep,
                page_break_before=bool(sec.get("page_break_before")),
            )
        )
        if sec.get("text"):
            for part in str(sec["text"]).split("\n"):
                body.append(_paragraph(part, size=19 if is_control else 21, color=text_color, italic=is_control, spacing_after=90, keep_next=keep))
        if sec.get("bullets"):
            for item in sec["bullets"]:
                body.append(_paragraph("• " + str(item), size=19 if is_control else 20, color=text_color, italic=is_control, spacing_after=55, keep_next=keep))
        if sec.get("table"):
            body.append(_table(sec["table"]))
        if sec_index < len(sections) - 1:
            body.append(_paragraph("", spacing_after=30))
    if append_default_control and not has_control:
        body.append(_paragraph("CONTROL DE USO", bold=True, size=22, color="C94040", spacing_after=70))
        body.append(
            _paragraph(
                "Documento candidato interno. Su liberación depende del cierre del abogado responsable del alcance y del QA aplicable según impacto; no está autorizado para firma o publicación mientras el ciclo permanezca abierto.",
                italic=True,
                size=18,
                color="7A2D2D",
                spacing_after=180,
            )
        )
    sect = '''<w:sectPr><w:headerReference w:type="default" r:id="rId3"/><w:footerReference w:type="default" r:id="rId4"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="540" w:footer="540" w:gutter="0"/></w:sectPr>'''
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<w:body>{"".join(body)}{sect}</w:body></w:document>'
    )
    styles = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{NS}">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
        '<w:next w:val="Normal"/><w:qFormat/></w:style></w:styles>'
    )
    now = datetime.now(timezone.utc).isoformat()
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>{escape(title)}</dc:title><dc:creator>LegalAIZ.it</dc:creator><cp:lastModifiedBy>LegalAIZ.it</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        '</cp:coreProperties>'
    )
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    image_relationship = (
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo-legalaizit-docx.png"/>'
        if has_logo
        else ""
    )
    docrels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        f'{image_relationship}'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
        '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
        '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
        '</Relationships>'
    )
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>LegalAIZ.it</Application></Properties>'''
    settings = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{NS}"><w:updateFields w:val="true"/><w:doNotTrackMoves/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>'''
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/settings.xml", settings)
        z.writestr("word/header1.xml", _header_xml(document_status))
        z.writestr("word/footer1.xml", _footer_xml(footer))
        z.writestr("word/_rels/document.xml.rels", docrels)
        if has_logo:
            z.writestr("word/media/logo-legalaizit-docx.png", logo_path.read_bytes())
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    return path
