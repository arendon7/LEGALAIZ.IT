from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from hmac import new as hmac_new
from pathlib import Path
from typing import Any
import os
import html
import json
import re
import uuid

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from source_extractors import extract_source


NAVY = colors.HexColor("#0D1324")
BLUE = colors.HexColor("#2563EB")
GOLD = colors.HexColor("#C9A96E")
IVORY = colors.HexColor("#F7F5F1")
CHARCOAL = colors.HexColor("#1F1F1F")
GRAY = colors.HexColor("#A8AEB8")
SOFT_GRAY = colors.HexColor("#F1F1F1")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "archivo")).strip("._") or "archivo"


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=False).replace("\n", "<br/>")


class NumberedDocTemplate(BaseDocTemplate):
    def __init__(self, filename, *, legal_title: str, legal_subtitle: str = "", **kwargs):
        super().__init__(filename, **kwargs)
        self.legal_title = legal_title
        self.legal_subtitle = legal_subtitle
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="LegalAIZ", frames=[frame], onPage=self._header_footer))

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.7)
        canvas.line(self.leftMargin, height - 22 * mm, width - self.rightMargin, height - 22 * mm)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(self.leftMargin, height - 17 * mm, "LegalAIZ.it")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(width - self.rightMargin, height - 17 * mm, "Más que respuestas, soluciones.")
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(self.leftMargin, 13 * mm, "Vista PDF generada por LegalAIZ.it · Control de integridad y trazabilidad")
        canvas.drawRightString(width - self.rightMargin, 13 * mm, f"Página {doc.page}")
        canvas.restoreState()


class PdfAcceptanceCenter:
    """Vista PDF y aceptación electrónica simple de documentos del expediente.

    La aceptación registra voluntad, versión y hash del archivo. No pretende sustituir
    una firma digital o electrónica avanzada cuando la ley o el negocio la requieran.
    """

    ACCEPTANCE_TEXT = (
        "Confirmo que revisé el documento identificado por su versión y hash SHA-256, "
        "que los datos suministrados reflejan la información que proporcioné y que entiendo "
        "su estado jurídico y las advertencias de uso indicadas por LegalAIZ.it."
    )

    def __init__(self, root: Path, hmac_key: bytes):
        self.root = Path(root)
        self.generated = Path(os.environ.get("LEGAL_RUNTIME_DIR", "")).expanduser() / "generated" if os.environ.get("LEGAL_RUNTIME_DIR") else self.root / "runtime" / "generated"
        self.preview_dir = self.generated / "pdf_previews"
        self.receipt_dir = self.generated / "acceptance_receipts"
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        self.hmac_key = bytes(hmac_key)

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS document_pdf_previews(
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              document_sha256 TEXT NOT NULL,
              source_version TEXT,
              file_path TEXT NOT NULL,
              pdf_sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              page_count INTEGER,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(document_id,document_sha256),
              FOREIGN KEY(document_id) REFERENCES documents(id),
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_pdf_preview_document ON document_pdf_previews(document_id,created_at DESC);

            CREATE TABLE IF NOT EXISTS document_acceptances(
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              signer_name TEXT NOT NULL,
              signer_email TEXT NOT NULL,
              acceptance_type TEXT NOT NULL,
              acceptance_text TEXT NOT NULL,
              document_sha256 TEXT NOT NULL,
              document_version TEXT,
              preview_id TEXT,
              preview_sha256 TEXT,
              receipt_json TEXT NOT NULL,
              receipt_sha256 TEXT NOT NULL,
              receipt_hmac TEXT NOT NULL,
              receipt_path TEXT NOT NULL,
              ip_address TEXT,
              user_agent TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              revoked_at TEXT,
              revoked_by TEXT,
              revocation_reason TEXT,
              FOREIGN KEY(document_id) REFERENCES documents(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(preview_id) REFERENCES document_pdf_previews(id)
            );
            CREATE INDEX IF NOT EXISTS idx_acceptance_document ON document_acceptances(document_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_acceptance_case ON document_acceptances(case_id,created_at DESC);

            CREATE TABLE IF NOT EXISTS document_acceptance_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              acceptance_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              previous_hash TEXT,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(acceptance_id) REFERENCES document_acceptances(id)
            );
            CREATE INDEX IF NOT EXISTS idx_acceptance_events ON document_acceptance_events(acceptance_id,id);
            """
        )

    @staticmethod
    def _document(con, document_id: str):
        return con.execute(
            """SELECT d.*,c.title case_title,c.owner_id,c.specialist_id,c.risk,c.status case_status,
                      u.email owner_email,u.name owner_name
               FROM documents d JOIN cases c ON c.id=d.case_id
               LEFT JOIN users u ON u.id=c.owner_id WHERE d.id=?""",
            (document_id,),
        ).fetchone()

    @staticmethod
    def _source_sha(row) -> str:
        path = Path(row["file_path"] or "")
        if not path.is_file():
            raise ValueError("El archivo físico del documento no está disponible.")
        return sha256(path.read_bytes()).hexdigest()

    def _styles(self):
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "LegalTitle",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=25,
                textColor=NAVY,
                alignment=TA_LEFT,
                spaceAfter=7 * mm,
            ),
            "subtitle": ParagraphStyle(
                "LegalSubtitle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#4B5563"),
                spaceAfter=4 * mm,
            ),
            "h1": ParagraphStyle(
                "LegalH1",
                parent=base["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=17,
                textColor=NAVY,
                spaceBefore=5 * mm,
                spaceAfter=2.5 * mm,
                keepWithNext=True,
            ),
            "body": ParagraphStyle(
                "LegalBody",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=9.2,
                leading=14,
                textColor=CHARCOAL,
                alignment=TA_LEFT,
                spaceAfter=2.5 * mm,
            ),
            "small": ParagraphStyle(
                "LegalSmall",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=7.8,
                leading=11,
                textColor=colors.HexColor("#4B5563"),
            ),
            "center": ParagraphStyle(
                "LegalCenter",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=CHARCOAL,
                alignment=TA_CENTER,
            ),
        }

    def _metadata_table(self, row, digest: str, styles):
        data = [
            [Paragraph("<b>Expediente</b>", styles["small"]), Paragraph(_escape(row["case_id"]), styles["small"])],
            [Paragraph("<b>Documento</b>", styles["small"]), Paragraph(_escape(row["name"]), styles["small"])],
            [Paragraph("<b>Versión</b>", styles["small"]), Paragraph(_escape(row["version"] or "—"), styles["small"])],
            [Paragraph("<b>Estado</b>", styles["small"]), Paragraph(_escape(row["status"] or "—"), styles["small"])],
            [Paragraph("<b>SHA-256</b>", styles["small"]), Paragraph(_escape(digest), styles["small"])],
        ]
        table = Table(data, colWidths=[34 * mm, 130 * mm], repeatRows=0)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), IVORY),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8D8D2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def _document_story(self, row, digest: str) -> list[Any]:
        styles = self._styles()
        path = Path(row["file_path"] or "")
        story: list[Any] = [
            Paragraph(_escape(row["name"] or "Documento"), styles["title"]),
            Paragraph(
                "Vista PDF de lectura. La versión controlada permanece identificada por su archivo original, versión y hash.",
                styles["subtitle"],
            ),
            self._metadata_table(row, digest, styles),
            Spacer(1, 5 * mm),
        ]
        try:
            extraction = extract_source(path)
        except Exception as exc:
            extraction = {"format": "unknown", "error": str(exc)}
        fmt = extraction.get("format")
        if fmt == "docx":
            paragraphs = extraction.get("paragraphs", [])
            tables = extraction.get("tables", [])
            for text in paragraphs:
                cleaned = " ".join(str(text or "").split())
                if not cleaned:
                    continue
                is_heading = len(cleaned) < 110 and (cleaned.isupper() or re.match(r"^(CLÁUSULA|ARTÍCULO|CAPÍTULO|SECCIÓN|ANEXO|ACTA|INFORME|CONTRATO)\b", cleaned, re.I))
                story.append(Paragraph(_escape(cleaned), styles["h1"] if is_heading else styles["body"]))
            for table_index, rows in enumerate(tables, 1):
                if not rows:
                    continue
                table_data = [[Paragraph(_escape(cell), styles["small"]) for cell in r] for r in rows]
                widths = [max(28 * mm, 164 * mm / max(1, len(table_data[0])))] * len(table_data[0])
                t = Table(table_data, colWidths=widths, repeatRows=1)
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8D8D2")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.extend([Paragraph(f"Tabla {table_index}", styles["h1"]), t, Spacer(1, 3 * mm)])
        elif fmt in {"txt", "md"}:
            for chunk in re.split(r"\n\s*\n", extraction.get("text", "")):
                if chunk.strip():
                    story.append(Paragraph(_escape(chunk.strip()), styles["body"]))
        elif fmt == "pdf":
            for page in extraction.get("pages", []):
                story.append(Paragraph(f"Contenido extraído de la página {page.get('page')}", styles["h1"]))
                story.append(Paragraph(_escape(page.get("text", "")), styles["body"]))
        else:
            story.append(
                Paragraph(
                    "No fue posible producir una vista semántica completa. Descargue el archivo original para su revisión.",
                    styles["body"],
                )
            )
        control = Table(
            [[Paragraph("<b>Control de uso</b>", styles["small"]), Paragraph(
                "Esta vista PDF facilita la lectura y no sustituye el archivo original. La aceptación electrónica simple no equivale a firma digital ni elimina la necesidad de revisión profesional cuando el producto o el caso la exijan.",
                styles["small"],
            )]],
            colWidths=[35 * mm, 129 * mm],
        )
        control.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E8")),
            ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([Spacer(1, 6 * mm), KeepTogether(control)])
        return story

    def ensure_preview(self, con, document_id: str, actor_id: str) -> dict:
        row = self._document(con, document_id)
        if not row:
            raise ValueError("Documento no encontrado.")
        digest = self._source_sha(row)
        existing = con.execute(
            "SELECT * FROM document_pdf_previews WHERE document_id=? AND document_sha256=? ORDER BY created_at DESC LIMIT 1",
            (document_id, digest),
        ).fetchone()
        if existing and Path(existing["file_path"]).is_file():
            return self.public_preview(existing)
        preview_id = "PDF-" + uuid.uuid4().hex[:14].upper()
        filename = safe_name(f"{row['name']}_{row['version'] or 'actual'}_{digest[:10]}_vista.pdf")
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        target = self.preview_dir / filename
        doc = NumberedDocTemplate(
            str(target),
            legal_title=row["name"] or "Documento",
            legal_subtitle="LegalAIZ.it",
            pagesize=A4,
            rightMargin=23 * mm,
            leftMargin=23 * mm,
            topMargin=30 * mm,
            bottomMargin=22 * mm,
            title=str(row["name"] or "Documento"),
            author="LegalAIZ.it",
            subject="Vista PDF verificable",
            creator="LegalAIZ.it v2.7",
        )
        doc.build(self._document_story(row, digest))
        pdf_raw = target.read_bytes()
        pdf_hash = sha256(pdf_raw).hexdigest()
        # ReportLab no expone el total de páginas sin segunda pasada; se conserva como dato opcional.
        con.execute(
            """INSERT INTO document_pdf_previews(id,document_id,document_sha256,source_version,file_path,pdf_sha256,
               size_bytes,page_count,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (preview_id, document_id, digest, row["version"], str(target), pdf_hash, len(pdf_raw), None, actor_id, utc_iso()),
        )
        return self.public_preview(con.execute("SELECT * FROM document_pdf_previews WHERE id=?", (preview_id,)).fetchone())

    @staticmethod
    def public_preview(row) -> dict:
        if not row:
            return {}
        obj = dict(row)
        obj.pop("file_path", None)
        obj["download_url"] = f"/api/pdf-previews/{obj['id']}/download"
        obj["inline_url"] = f"/api/pdf-previews/{obj['id']}/view"
        return obj

    def preview_path(self, con, preview_id: str) -> Path | None:
        row = con.execute("SELECT file_path FROM document_pdf_previews WHERE id=?", (preview_id,)).fetchone()
        if not row:
            return None
        path = Path(row["file_path"])
        return path if path.is_file() else None

    def _event(self, con, acceptance_id: str, event_type: str, actor_id: str, detail: dict) -> str:
        prev = con.execute(
            "SELECT event_hash FROM document_acceptance_events WHERE acceptance_id=? ORDER BY id DESC LIMIT 1",
            (acceptance_id,),
        ).fetchone()
        previous = prev["event_hash"] if prev else ""
        created = utc_iso()
        raw = json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload = "|".join((acceptance_id, event_type, actor_id, created, previous, raw))
        digest = sha256(payload.encode("utf-8")).hexdigest()
        con.execute(
            """INSERT INTO document_acceptance_events(acceptance_id,event_type,actor_id,detail_json,previous_hash,event_hash,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (acceptance_id, event_type, actor_id, raw, previous or None, digest, created),
        )
        return digest

    def _receipt_pdf(self, acceptance: dict, target: Path) -> None:
        styles = self._styles()
        doc = NumberedDocTemplate(
            str(target),
            legal_title="Constancia de aceptación electrónica simple",
            legal_subtitle="LegalAIZ.it",
            pagesize=A4,
            rightMargin=23 * mm,
            leftMargin=23 * mm,
            topMargin=30 * mm,
            bottomMargin=22 * mm,
            author="LegalAIZ.it",
            subject="Constancia de aceptación electrónica simple",
            creator="LegalAIZ.it v2.7",
        )
        receipt = acceptance["receipt"]
        rows = [
            ("Constancia", acceptance["id"]),
            ("Expediente", receipt["case_id"]),
            ("Documento", receipt["document_name"]),
            ("Versión", receipt.get("document_version") or "—"),
            ("Firmante", receipt["signer_name"]),
            ("Correo", receipt["signer_email"]),
            ("Fecha UTC", receipt["created_at"]),
            ("SHA-256 documento", receipt["document_sha256"]),
            ("SHA-256 vista PDF", receipt.get("preview_sha256") or "—"),
            ("SHA-256 constancia", acceptance["receipt_sha256"]),
            ("Sello HMAC", acceptance["receipt_hmac"]),
        ]
        table = Table(
            [[Paragraph(f"<b>{_escape(k)}</b>", styles["small"]), Paragraph(_escape(v), styles["small"])] for k, v in rows],
            colWidths=[43 * mm, 121 * mm],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), IVORY),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8D8D2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story = [
            Paragraph("Constancia de aceptación electrónica simple", styles["title"]),
            Paragraph(
                "Registro verificable de la manifestación realizada dentro del prototipo LegalAIZ.it.",
                styles["subtitle"],
            ),
            table,
            Spacer(1, 6 * mm),
            Paragraph("Declaración aceptada", styles["h1"]),
            Paragraph(_escape(receipt["acceptance_text"]), styles["body"]),
            Spacer(1, 5 * mm),
            Paragraph("Alcance jurídico", styles["h1"]),
            Paragraph(
                "Esta constancia conserva evidencia técnica de usuario, fecha, versión y hash. No se presenta como firma digital, firma electrónica avanzada, autenticación notarial ni certificación de identidad. La suficiencia jurídica depende del negocio, las partes, la evidencia disponible y la normativa aplicable.",
                styles["body"],
            ),
        ]
        doc.build(story)

    def accept(
        self,
        con,
        document_id: str,
        user: dict,
        signer_name: str,
        accepted: bool,
        expected_sha256: str,
        ip_address: str,
        user_agent: str,
        acceptance_type: str = "Aceptación de borrador personalizado",
    ) -> dict:
        if not accepted:
            raise ValueError("Debe confirmar expresamente la declaración de aceptación.")
        signer_name = " ".join(str(signer_name or "").split()).strip()
        if len(signer_name) < 3:
            raise ValueError("Escriba el nombre completo de la persona que acepta.")
        row = self._document(con, document_id)
        if not row:
            raise ValueError("Documento no encontrado.")
        digest = self._source_sha(row)
        if not expected_sha256 or expected_sha256 != digest:
            raise ValueError("El documento cambió desde que se abrió. Revise nuevamente la versión actual.")
        preview = self.ensure_preview(con, document_id, user["id"])
        acceptance_id = "ACC-" + uuid.uuid4().hex[:14].upper()
        created = utc_iso()
        receipt = {
            "schema": "legalaizit-simple-acceptance-v2.7",
            "acceptance_id": acceptance_id,
            "document_id": document_id,
            "case_id": row["case_id"],
            "document_name": row["name"],
            "document_version": row["version"],
            "document_status": row["status"],
            "document_sha256": digest,
            "preview_id": preview.get("id"),
            "preview_sha256": preview.get("pdf_sha256"),
            "signer_name": signer_name,
            "signer_email": user.get("email") or "",
            "user_id": user["id"],
            "acceptance_type": acceptance_type,
            "acceptance_text": self.ACCEPTANCE_TEXT,
            "created_at": created,
            "professional_use_authorized": False,
            "signature_level": "Aceptación electrónica simple dentro del prototipo",
        }
        raw = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        receipt_hash = sha256(raw).hexdigest()
        receipt_hmac = hmac_new(self.hmac_key, raw, "sha256").hexdigest()
        filename = safe_name(f"LegalAIZit_{acceptance_id}_constancia_aceptacion.pdf")
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        target = self.receipt_dir / filename
        acceptance_obj = {
            "id": acceptance_id,
            "receipt": receipt,
            "receipt_sha256": receipt_hash,
            "receipt_hmac": receipt_hmac,
        }
        self._receipt_pdf(acceptance_obj, target)
        con.execute(
            """INSERT INTO document_acceptances(id,document_id,case_id,user_id,signer_name,signer_email,
               acceptance_type,acceptance_text,document_sha256,document_version,preview_id,preview_sha256,
               receipt_json,receipt_sha256,receipt_hmac,receipt_path,ip_address,user_agent,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                acceptance_id,
                document_id,
                row["case_id"],
                user["id"],
                signer_name,
                user.get("email") or "",
                acceptance_type,
                self.ACCEPTANCE_TEXT,
                digest,
                row["version"],
                preview.get("id"),
                preview.get("pdf_sha256"),
                raw.decode("utf-8"),
                receipt_hash,
                receipt_hmac,
                str(target),
                ip_address,
                (user_agent or "")[:1000],
                "Vigente",
                created,
            ),
        )
        self._event(
            con,
            acceptance_id,
            "accepted",
            user["id"],
            {"document_id": document_id, "document_sha256": digest, "receipt_sha256": receipt_hash},
        )
        return self.detail(con, acceptance_id)

    def list_for_document(self, con, document_id: str) -> list[dict]:
        rows = con.execute(
            "SELECT * FROM document_acceptances WHERE document_id=? ORDER BY created_at DESC",
            (document_id,),
        ).fetchall()
        return [self.public_acceptance(row) for row in rows]

    @staticmethod
    def public_acceptance(row) -> dict:
        if not row:
            return {}
        obj = dict(row)
        obj.pop("receipt_path", None)
        obj.pop("ip_address", None)
        obj.pop("user_agent", None)
        try:
            obj["receipt"] = json.loads(obj.pop("receipt_json"))
        except Exception:
            obj.pop("receipt_json", None)
        obj["receipt_url"] = f"/api/document-acceptances/{obj['id']}/receipt"
        return obj

    def detail(self, con, acceptance_id: str) -> dict | None:
        row = con.execute("SELECT * FROM document_acceptances WHERE id=?", (acceptance_id,)).fetchone()
        return self.public_acceptance(row) if row else None

    def receipt_path(self, con, acceptance_id: str) -> Path | None:
        row = con.execute("SELECT receipt_path FROM document_acceptances WHERE id=?", (acceptance_id,)).fetchone()
        if not row:
            return None
        path = Path(row["receipt_path"])
        return path if path.is_file() else None

    def verify(self, con, acceptance_id: str) -> dict:
        row = con.execute("SELECT * FROM document_acceptances WHERE id=?", (acceptance_id,)).fetchone()
        if not row:
            raise ValueError("Constancia no encontrada.")
        raw = row["receipt_json"].encode("utf-8")
        receipt_hash = sha256(raw).hexdigest()
        receipt_hmac = hmac_new(self.hmac_key, raw, "sha256").hexdigest()
        doc = self._document(con, row["document_id"])
        current_hash = self._source_sha(doc) if doc else None
        receipt_file = Path(row["receipt_path"])
        events = [dict(x) for x in con.execute(
            "SELECT * FROM document_acceptance_events WHERE acceptance_id=? ORDER BY id", (acceptance_id,)
        ).fetchall()]
        previous = ""
        chain_ok = True
        for event in events:
            payload = "|".join((
                acceptance_id,
                event["event_type"],
                event["actor_id"],
                event["created_at"],
                previous,
                event["detail_json"],
            ))
            digest = sha256(payload.encode("utf-8")).hexdigest()
            if (event.get("previous_hash") or "") != previous or event.get("event_hash") != digest:
                chain_ok = False
                break
            previous = digest
        return {
            "acceptance_id": acceptance_id,
            "receipt_hash_valid": receipt_hash == row["receipt_sha256"],
            "receipt_hmac_valid": receipt_hmac == row["receipt_hmac"],
            "document_unchanged": current_hash == row["document_sha256"],
            "receipt_file_available": receipt_file.is_file(),
            "event_chain_valid": chain_ok,
            "valid": bool(
                receipt_hash == row["receipt_sha256"]
                and receipt_hmac == row["receipt_hmac"]
                and chain_ok
                and row["status"] == "Vigente"
            ),
            "notice": "La verificación acredita integridad técnica de la constancia; no certifica identidad ni equivalencia con firma digital.",
        }
