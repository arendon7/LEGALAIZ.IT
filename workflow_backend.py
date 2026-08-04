from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile
import json
import re
import uuid

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


class WorkflowExperience:
    """Collaboration, product journeys and document preview for v2.2.

    This layer deliberately keeps the existing case/document engine intact. It adds read models
    and auditable collaboration records without weakening the canonical-source or publication gates.
    """

    def __init__(self, root: Path, products: list[dict[str, Any]], requirements: dict[str, Any]):
        self.root = Path(root)
        self.products = products
        self.product_map = {p["code"]: p for p in products}
        self.requirements = requirements
        path = self.root / "data" / "product_experience.json"
        self.experience = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    @staticmethod
    def create_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS case_messages(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              author_id TEXT NOT NULL,
              message_type TEXT NOT NULL DEFAULT 'message',
              visibility TEXT NOT NULL DEFAULT 'shared',
              body TEXT NOT NULL,
              parent_id TEXT,
              created_at TEXT NOT NULL,
              edited_at TEXT,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(author_id) REFERENCES users(id),
              FOREIGN KEY(parent_id) REFERENCES case_messages(id)
            );
            CREATE INDEX IF NOT EXISTS idx_case_messages_case ON case_messages(case_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_case_messages_visibility ON case_messages(case_id,visibility,created_at);

            CREATE TABLE IF NOT EXISTS case_task_details(
              task_id TEXT PRIMARY KEY,
              description TEXT,
              assigned_to TEXT,
              due_at TEXT,
              priority INTEGER NOT NULL DEFAULT 2,
              created_by TEXT,
              source TEXT NOT NULL DEFAULT 'workflow',
              FOREIGN KEY(task_id) REFERENCES case_tasks(id),
              FOREIGN KEY(assigned_to) REFERENCES users(id),
              FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS document_comments(
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              author_id TEXT NOT NULL,
              section_key TEXT,
              quote TEXT,
              comment TEXT NOT NULL,
              visibility TEXT NOT NULL DEFAULT 'shared',
              status TEXT NOT NULL DEFAULT 'Abierto',
              created_at TEXT NOT NULL,
              resolved_at TEXT,
              resolved_by TEXT,
              FOREIGN KEY(document_id) REFERENCES documents(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(author_id) REFERENCES users(id),
              FOREIGN KEY(resolved_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_document_comments_document ON document_comments(document_id,status,created_at);
            """
        )

    def init_demo(self, con) -> None:
        if con.execute("SELECT COUNT(*) FROM case_messages").fetchone()[0]:
            return
        assignments = {
            "CO-EM-003": ("USR-COMM", "Carlos López"),
            "CO-LA-001": ("USR-LAB", "María Fernández"),
            "CO-TR-001": ("USR-TRANSIT", "Laura Gómez"),
        }
        cases = con.execute("SELECT id,product_code,title FROM cases ORDER BY created_at").fetchall()
        now = utc_now()
        for row in cases:
            specialist_id, specialist_name = assignments.get(row["product_code"], (None, None))
            if specialist_id:
                con.execute(
                    "UPDATE cases SET specialist_id=?,review_status='En revisión',status='En revisión profesional',updated_at=? WHERE id=?",
                    (specialist_id, now, row["id"]),
                )
            client_body = {
                "CO-EM-003": "Ya confirmé las partes, el objeto y el esquema de pago. Quiero revisar que el alcance quede suficientemente claro.",
                "CO-LA-001": "Cargué los datos principales. Me falta confirmar si el último pago incluyó una parte de la prima.",
                "CO-TR-001": "La consulta aparece en SIMIT, pero no tengo todavía copia del acto individual ni de la notificación.",
            }.get(row["product_code"], "He completado la información inicial del expediente.")
            specialist_body = {
                "CO-EM-003": "Revisaré la independencia de la relación, los criterios de aceptación y la propiedad intelectual antes de aprobar una nueva versión.",
                "CO-LA-001": "El cálculo es preliminar. Necesito el último desprendible o comprobante para validar pagos previos y la base utilizada.",
                "CO-TR-001": "La coincidencia SAST es únicamente preliminar. Debemos verificar dispositivo, acto, expediente y etapa procesal.",
            }.get(row["product_code"], "Revisaré los soportes y la salida documental.")
            self._insert_message(con, row["id"], "USR-CLIENT", client_body, "shared", "message", now)
            if specialist_id:
                self._insert_message(con, row["id"], specialist_id, specialist_body, "shared", "message", now)
                self._insert_message(con, row["id"], specialist_id, "Nota interna: comprobar coherencia entre respuestas, documentos y reglas ejecutadas.", "internal", "note", now)
            document = con.execute(
                "SELECT id,name FROM documents WHERE case_id=? AND kind!='audit' ORDER BY created_at LIMIT 1", (row["id"],)
            ).fetchone()
            if document and specialist_id:
                con.execute(
                    """INSERT INTO document_comments(id,document_id,case_id,author_id,section_key,quote,comment,visibility,status,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "DCO-" + uuid.uuid4().hex[:10].upper(), document["id"], row["id"], specialist_id,
                        "preview:1", "Primera sección del documento",
                        "Comentario demostrativo: validar este apartado contra las respuestas confirmadas y el paquete jurídico antes de aprobación.",
                        "shared", "Abierto", now,
                    ),
                )
        con.commit()

    @staticmethod
    def _insert_message(con, case_id: str, author_id: str, body: str, visibility: str, message_type: str, created_at: str | None = None) -> str:
        mid = "MSG-" + uuid.uuid4().hex[:12].upper()
        con.execute(
            "INSERT INTO case_messages(id,case_id,author_id,message_type,visibility,body,created_at) VALUES(?,?,?,?,?,?,?)",
            (mid, case_id, author_id, message_type, visibility, body, created_at or utc_now()),
        )
        return mid

    def product_experience(self, code: str) -> dict[str, Any] | None:
        item = self.experience.get(code)
        if not item:
            return None
        p = self.product_map.get(code, {})
        return {
            **item,
            "product": {
                "code": code,
                "title": p.get("title", code),
                "vertical": p.get("vertical"),
                "risk": p.get("base_risk"),
                "version": p.get("version"),
                "price_auto": p.get("price_auto"),
                "price_review": p.get("price_review"),
                "publication_status": p.get("publication_status"),
            },
        }

    def experience_summary(self) -> dict[str, Any]:
        rows = [self.product_experience(code) for code in self.experience]
        rows = [x for x in rows if x]
        return {
            "products": rows,
            "metrics": {
                "products": len(rows),
                "steps": sum(len(x.get("steps", [])) for x in rows),
                "deliverables": sum(len(x.get("deliverables", [])) for x in rows),
                "faqs": sum(len(x.get("faqs", [])) for x in rows),
            },
            "notice": "Los recorridos describen el piloto y no sustituyen la aprobación jurídica de las fuentes y documentos canónicos.",
        }

    @staticmethod
    def _visibility_sql(user: dict[str, Any]) -> tuple[str, list[Any]]:
        if user["role"] in ("specialist", "admin"):
            return "1=1", []
        return "m.visibility='shared'", []

    def case_collaboration(self, con, case_id: str, user: dict[str, Any]) -> dict[str, Any]:
        vis_sql, vis_params = self._visibility_sql(user)
        messages = [dict(row) for row in con.execute(
            f"""SELECT m.*,u.name author_name,u.role author_role,u.specialty author_specialty
                FROM case_messages m JOIN users u ON u.id=m.author_id
                WHERE m.case_id=? AND {vis_sql} ORDER BY m.created_at ASC,m.id ASC""",
            [case_id, *vis_params],
        ).fetchall()]
        tasks = [dict(row) for row in con.execute(
            """SELECT t.*,d.description,d.assigned_to,d.due_at,d.priority,d.created_by,d.source,
                      u.name assigned_name
               FROM case_tasks t LEFT JOIN case_task_details d ON d.task_id=t.id
               LEFT JOIN users u ON u.id=d.assigned_to
               WHERE t.case_id=? ORDER BY t.position,t.created_at""",
            (case_id,),
        ).fetchall()]
        comments = [dict(row) for row in con.execute(
            """SELECT dc.*,u.name author_name,u.role author_role,r.name resolved_by_name,d.name document_name
               FROM document_comments dc JOIN users u ON u.id=dc.author_id
               JOIN documents d ON d.id=dc.document_id
               LEFT JOIN users r ON r.id=dc.resolved_by
               WHERE dc.case_id=? AND (dc.visibility='shared' OR ? IN ('specialist','admin'))
               ORDER BY CASE dc.status WHEN 'Abierto' THEN 0 ELSE 1 END,dc.created_at DESC""",
            (case_id, user["role"]),
        ).fetchall()]
        return {
            "case_id": case_id,
            "messages": messages,
            "tasks": tasks,
            "document_comments": comments,
            "metrics": {
                "messages": len(messages),
                "open_tasks": sum(x.get("status") in ("Pendiente", "Bloqueada") for x in tasks),
                "open_comments": sum(x.get("status") == "Abierto" for x in comments),
            },
        }

    def collaboration_overview(self, con, scope_sql: str, params: list[Any], user: dict[str, Any]) -> dict[str, Any]:
        cases = [dict(row) for row in con.execute(
            f"""SELECT c.id,c.product_code,c.title,c.risk,c.status,c.updated_at,u.name specialist_name
                FROM cases c LEFT JOIN users u ON u.id=c.specialist_id WHERE {scope_sql}
                ORDER BY c.updated_at DESC""", params
        ).fetchall()]
        if not cases:
            return {"cases": [], "messages": [], "tasks": [], "metrics": {"cases": 0, "messages": 0, "open_tasks": 0}}
        ids = [x["id"] for x in cases]
        placeholders = ",".join("?" for _ in ids)
        vis = "" if user["role"] in ("specialist", "admin") else " AND m.visibility='shared'"
        messages = [dict(row) for row in con.execute(
            f"""SELECT m.*,u.name author_name,u.role author_role,c.title case_title,c.product_code
                 FROM case_messages m JOIN users u ON u.id=m.author_id JOIN cases c ON c.id=m.case_id
                 WHERE m.case_id IN ({placeholders}) {vis}
                 ORDER BY m.created_at DESC LIMIT 80""", ids
        ).fetchall()]
        tasks = [dict(row) for row in con.execute(
            f"""SELECT t.*,d.description,d.assigned_to,d.due_at,d.priority,d.created_by,d.source,
                       u.name assigned_name,c.title case_title,c.product_code
                 FROM case_tasks t JOIN cases c ON c.id=t.case_id
                 LEFT JOIN case_task_details d ON d.task_id=t.id LEFT JOIN users u ON u.id=d.assigned_to
                 WHERE t.case_id IN ({placeholders}) ORDER BY CASE t.status WHEN 'Bloqueada' THEN 0 WHEN 'Pendiente' THEN 1 ELSE 2 END,t.updated_at DESC""", ids
        ).fetchall()]
        return {
            "cases": cases,
            "messages": messages,
            "tasks": tasks,
            "metrics": {
                "cases": len(cases),
                "messages": len(messages),
                "open_tasks": sum(x.get("status") in ("Pendiente", "Bloqueada") for x in tasks),
                "internal_messages": sum(x.get("visibility") == "internal" for x in messages),
            },
        }

    def post_message(self, con, case_id: str, user: dict[str, Any], body: str, visibility: str = "shared", message_type: str = "message") -> dict[str, Any]:
        body = _clean_text(body)
        if len(body) < 3:
            raise ValueError("El mensaje debe tener al menos 3 caracteres.")
        if len(body) > 4000:
            raise ValueError("El mensaje excede 4.000 caracteres.")
        visibility = visibility if visibility in ("shared", "internal") else "shared"
        if visibility == "internal" and user["role"] == "client":
            raise PermissionError("El cliente no puede crear notas internas.")
        message_type = message_type if message_type in ("message", "note", "system") else "message"
        mid = self._insert_message(con, case_id, user["id"], body, visibility, message_type)
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "message", "Se agregó un mensaje compartido." if visibility == "shared" else "Se agregó una nota interna.", utc_now()),
        )
        row = con.execute(
            """SELECT m.*,u.name author_name,u.role author_role,u.specialty author_specialty
               FROM case_messages m JOIN users u ON u.id=m.author_id WHERE m.id=?""", (mid,)
        ).fetchone()
        return dict(row)

    def create_task(self, con, case_id: str, user: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        if user["role"] not in ("specialist", "admin"):
            raise PermissionError("Solo especialista o administración puede crear tareas.")
        label = _clean_text(data.get("label"))
        if len(label) < 4:
            raise ValueError("La tarea requiere un título de al menos 4 caracteres.")
        owner_role = data.get("owner_role") if data.get("owner_role") in ("client", "specialist", "admin", "system") else "client"
        status = data.get("status") if data.get("status") in ("Pendiente", "Bloqueada", "Opcional", "Completada") else "Pendiente"
        priority = int(data.get("priority") or 2)
        if priority not in (1, 2, 3):
            raise ValueError("La prioridad debe ser 1, 2 o 3.")
        assigned_to = data.get("assigned_to") or None
        if assigned_to and not con.execute("SELECT 1 FROM users WHERE id=?", (assigned_to,)).fetchone():
            raise ValueError("El usuario asignado no existe.")
        position = con.execute("SELECT COALESCE(MAX(position),0)+1 FROM case_tasks WHERE case_id=?", (case_id,)).fetchone()[0]
        tid = "TSK-" + uuid.uuid4().hex[:10].upper()
        now = utc_now()
        con.execute(
            "INSERT INTO case_tasks(id,case_id,label,status,owner_role,position,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (tid, case_id, label, status, owner_role, position, now, now),
        )
        con.execute(
            """INSERT INTO case_task_details(task_id,description,assigned_to,due_at,priority,created_by,source)
               VALUES(?,?,?,?,?,?,?)""",
            (tid, _clean_text(data.get("description")), assigned_to, data.get("due_at") or None, priority, user["id"], "manual"),
        )
        con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (case_id, "task", f"Nueva tarea: {label}.", now))
        row = con.execute(
            """SELECT t.*,d.description,d.assigned_to,d.due_at,d.priority,d.created_by,d.source,u.name assigned_name
               FROM case_tasks t LEFT JOIN case_task_details d ON d.task_id=t.id
               LEFT JOIN users u ON u.id=d.assigned_to WHERE t.id=?""", (tid,)
        ).fetchone()
        return dict(row)

    def add_document_comment(self, con, document_id: str, case_id: str, user: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        comment = _clean_text(data.get("comment"))
        if len(comment) < 5:
            raise ValueError("El comentario debe tener al menos 5 caracteres.")
        visibility = data.get("visibility") if data.get("visibility") in ("shared", "internal") else "shared"
        if visibility == "internal" and user["role"] == "client":
            raise PermissionError("El cliente no puede crear comentarios internos.")
        cid = "DCO-" + uuid.uuid4().hex[:12].upper()
        now = utc_now()
        con.execute(
            """INSERT INTO document_comments(id,document_id,case_id,author_id,section_key,quote,comment,visibility,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                cid, document_id, case_id, user["id"], _clean_text(data.get("section_key")),
                _clean_text(data.get("quote"))[:1000], comment, visibility, "Abierto", now,
            ),
        )
        con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (case_id, "document_comment", "Se añadió un comentario al documento.", now))
        row = con.execute(
            """SELECT dc.*,u.name author_name,u.role author_role,d.name document_name
               FROM document_comments dc JOIN users u ON u.id=dc.author_id JOIN documents d ON d.id=dc.document_id
               WHERE dc.id=?""", (cid,)
        ).fetchone()
        return dict(row)

    def resolve_comment(self, con, comment_id: str, user: dict[str, Any], status: str = "Resuelto") -> dict[str, Any]:
        if user["role"] not in ("specialist", "admin"):
            raise PermissionError("Solo especialista o administración puede resolver comentarios.")
        row = con.execute("SELECT * FROM document_comments WHERE id=?", (comment_id,)).fetchone()
        if not row:
            raise ValueError("Comentario no encontrado.")
        status = "Resuelto" if status == "Resuelto" else "Abierto"
        now = utc_now()
        if status == "Resuelto":
            con.execute("UPDATE document_comments SET status=?,resolved_at=?,resolved_by=? WHERE id=?", (status, now, user["id"], comment_id))
        else:
            con.execute("UPDATE document_comments SET status='Abierto',resolved_at=NULL,resolved_by=NULL WHERE id=?", (comment_id,))
        updated = con.execute(
            """SELECT dc.*,u.name author_name,r.name resolved_by_name,d.name document_name
               FROM document_comments dc JOIN users u ON u.id=dc.author_id JOIN documents d ON d.id=dc.document_id
               LEFT JOIN users r ON r.id=dc.resolved_by WHERE dc.id=?""", (comment_id,)
        ).fetchone()
        return dict(updated)

    @staticmethod
    def _paragraph_text(node: ET.Element) -> str:
        return _clean_text("".join(t.text or "" for t in node.findall(".//w:t", NS)))

    @classmethod
    def _docx_preview(cls, path: Path) -> dict[str, Any]:
        try:
            with ZipFile(path) as z:
                raw = z.read("word/document.xml")
        except (BadZipFile, KeyError, OSError) as exc:
            raise ValueError("No fue posible leer la estructura del DOCX.") from exc
        root = ET.fromstring(raw)
        body = root.find("w:body", NS)
        blocks: list[dict[str, Any]] = []
        tables: list[dict[str, Any]] = []
        placeholder_count = 0
        if body is not None:
            index = 0
            for child in list(body):
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "p":
                    text = cls._paragraph_text(child)
                    if not text:
                        continue
                    index += 1
                    style_node = child.find("w:pPr/w:pStyle", NS)
                    style = style_node.get(f"{{{W_NS}}}val") if style_node is not None else ""
                    kind = "heading" if style and style.lower() in ("title", "heading1", "heading2", "heading3") else "paragraph"
                    if kind == "paragraph" and (text.isupper() and len(text) < 140):
                        kind = "heading"
                    placeholders = re.findall(r"\{\{[^{}]+\}\}|\[[A-ZÁÉÍÓÚÑ0-9_ .-]{3,}\]", text)
                    placeholder_count += len(placeholders)
                    blocks.append({"key": f"preview:{index}", "kind": kind, "style": style, "text": text, "placeholders": placeholders})
                elif tag == "tbl":
                    rows = []
                    for tr in child.findall("w:tr", NS):
                        cells = [cls._paragraph_text(tc) for tc in tr.findall("w:tc", NS)]
                        if any(cells):
                            rows.append(cells)
                    if rows:
                        index += 1
                        tables.append({"key": f"preview:{index}", "rows": rows})
                        blocks.append({"key": f"preview:{index}", "kind": "table", "rows": rows})
        full_text = "\n".join(x.get("text", "") for x in blocks if x.get("text"))
        return {
            "format": "docx",
            "blocks": blocks,
            "tables": tables,
            "text": full_text,
            "metrics": {
                "blocks": len(blocks),
                "paragraphs": sum(x["kind"] in ("paragraph", "heading") for x in blocks),
                "headings": sum(x["kind"] == "heading" for x in blocks),
                "tables": len(tables),
                "characters": len(full_text),
                "unresolved_placeholders": placeholder_count,
            },
        }

    @staticmethod
    def _json_preview(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError("No fue posible leer el JSON.") from exc
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return {
            "format": "json",
            "blocks": [{"key": "preview:1", "kind": "code", "text": text}],
            "tables": [],
            "text": text,
            "metrics": {"blocks": 1, "paragraphs": 0, "headings": 0, "tables": 0, "characters": len(text), "unresolved_placeholders": 0},
        }

    def document_preview(self, con, document: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        path = Path(document.get("file_path") or "")
        if not path.exists():
            raise ValueError("El archivo físico del documento no está disponible.")
        mime = document.get("mime_type") or ""
        if path.suffix.lower() == ".docx" or "wordprocessingml" in mime:
            preview = self._docx_preview(path)
        elif path.suffix.lower() == ".json" or mime == "application/json":
            preview = self._json_preview(path)
        elif path.suffix.lower() == ".txt" or mime.startswith("text/"):
            text = path.read_text(encoding="utf-8")
            preview = {"format": "text", "blocks": [{"key": "preview:1", "kind": "paragraph", "text": text}], "tables": [], "text": text,
                       "metrics": {"blocks": 1, "paragraphs": 1, "headings": 0, "tables": 0, "characters": len(text), "unresolved_placeholders": 0}}
        else:
            preview = {"format": "binary", "blocks": [], "tables": [], "text": "", "metrics": {"blocks": 0, "paragraphs": 0, "headings": 0, "tables": 0, "characters": 0, "unresolved_placeholders": 0}}
        comments = [dict(row) for row in con.execute(
            """SELECT dc.*,u.name author_name,u.role author_role,r.name resolved_by_name
               FROM document_comments dc JOIN users u ON u.id=dc.author_id
               LEFT JOIN users r ON r.id=dc.resolved_by
               WHERE dc.document_id=? AND (dc.visibility='shared' OR ? IN ('specialist','admin'))
               ORDER BY CASE dc.status WHEN 'Abierto' THEN 0 ELSE 1 END,dc.created_at DESC""",
            (document["id"], user["role"]),
        ).fetchall()]
        return {
            "document": {k: document.get(k) for k in ("id", "case_id", "product_code", "kind", "name", "mime_type", "created_at", "updated_at", "version", "status")},
            "preview": preview,
            "comments": comments,
            "notice": "La vista previa facilita revisión y comentarios. El archivo descargable y su historial siguen siendo la evidencia documental primaria del piloto.",
        }
