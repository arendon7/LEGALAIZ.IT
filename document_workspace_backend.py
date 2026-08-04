from __future__ import annotations

from datetime import datetime, timedelta
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import uuid

from docx_builder import build_docx
from source_extractors import extract_source


def utc_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class DocumentWorkspace:
    """Workspace documental v2.3.

    Proporciona comparación de versiones, borradores de trabajo no publicados y una
    actividad transversal. No cambia el estado jurídico ni publica documentos.
    """

    def __init__(self, root: Path, generated: Path):
        self.root = Path(root)
        self.generated = Path(generated)

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS document_compare_runs(
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              from_ref TEXT NOT NULL,
              to_ref TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              summary_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(document_id) REFERENCES documents(id),
              FOREIGN KEY(actor_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_compare_document ON document_compare_runs(document_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS factory_working_drafts(
              template_id TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              base_revision_id INTEGER NOT NULL,
              content_json TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              note TEXT,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(template_id,actor_id),
              FOREIGN KEY(actor_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS activity_reads(
              user_id TEXT PRIMARY KEY,
              last_seen_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )

    def init_demo_versions(self, con) -> int:
        """Crea una revisión histórica explícitamente demostrativa para tres documentos.

        La revisión se etiqueta como demostrativa y nunca se considera canónica ni aprobada.
        """
        created = 0
        rows = con.execute(
            """SELECT d.* FROM documents d
               WHERE lower(d.name) LIKE '%.docx' ORDER BY d.created_at"""
        ).fetchall()
        for row in rows:
            exists = con.execute(
                "SELECT 1 FROM document_versions WHERE document_id=? AND note LIKE 'Versión demostrativa anterior v2.3%'",
                (row["id"],),
            ).fetchone()
            if exists:
                continue
            current = Path(row["file_path"] or "")
            if not current.exists():
                continue
            target = self.generated / f"{current.stem}_version_anterior_demo_v23.docx"
            try:
                extracted = extract_source(current)
                paragraphs = extracted.get("paragraphs", [])
            except Exception:
                paragraphs = []
            sections = [
                {
                    "heading": "Versión anterior demostrativa",
                    "text": "Este archivo existe únicamente para probar la comparación lado a lado. No constituye una fuente canónica ni una versión aprobada.",
                    "_type": "control",
                }
            ]
            for i, text in enumerate(paragraphs[:8], 1):
                sections.append({"heading": f"Bloque {i}", "text": text, "_type": "section"})
            sections.append(
                {
                    "heading": "Pendientes de esta versión",
                    "bullets": [
                        "Verificar datos completos de las partes.",
                        "Revisar coherencia de fechas, valores y anexos.",
                        "Someter el documento a revisión jurídica y QA.",
                    ],
                    "_type": "notice",
                }
            )
            build_docx(
                target,
                f"{row['name']} · versión anterior",
                "Material demostrativo para control de cambios",
                [("Documento", row["id"]), ("Expediente", row["case_id"]), ("Estado", "No aprobado")],
                sections,
            )
            earlier = (datetime.fromisoformat(row["created_at"]) - timedelta(days=1)).isoformat(timespec="seconds")
            con.execute(
                "INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",
                (row["id"], "demo-anterior-v2.3", earlier, "Versión demostrativa anterior v2.3; no canónica ni aprobada.", str(target)),
            )
            created += 1
        return created

    @staticmethod
    def _flatten(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            data = extract_source(path)
        except Exception:
            return []
        out: list[dict[str, Any]] = []
        fmt = data.get("format")
        if fmt == "docx":
            for i, text in enumerate(data.get("paragraphs", []), 1):
                out.append({"key": f"p-{i}", "kind": "paragraph", "text": _clean(text)})
            for ti, table in enumerate(data.get("tables", []), 1):
                for ri, row in enumerate(table, 1):
                    out.append({"key": f"t-{ti}-r-{ri}", "kind": "table", "text": " | ".join(_clean(x) for x in row), "cells": row})
        elif fmt in ("txt", "md"):
            for i, line in enumerate(str(data.get("text", "")).splitlines(), 1):
                if _clean(line):
                    out.append({"key": f"l-{i}", "kind": "paragraph", "text": _clean(line)})
        elif fmt == "pdf":
            for page in data.get("pages", []):
                for i, line in enumerate(str(page.get("text", "")).splitlines(), 1):
                    if _clean(line):
                        out.append({"key": f"p-{page.get('page')}-l-{i}", "kind": "paragraph", "text": _clean(line)})
        return out

    def version_catalog(self, con, document_id: str) -> list[dict[str, Any]]:
        doc = con.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not doc:
            return []
        rows = [
            {
                "ref": "current",
                "label": f"Actual · {doc['version']}",
                "version": doc["version"],
                "created_at": doc["updated_at"],
                "note": "Archivo actual del expediente.",
                "file_path": doc["file_path"],
                "current": True,
            }
        ]
        seen = {str(doc["file_path"] or "")}
        for row in con.execute(
            "SELECT * FROM document_versions WHERE document_id=? ORDER BY created_at DESC,id DESC", (document_id,)
        ).fetchall():
            path = str(row["file_path"] or "")
            if not path or path in seen:
                continue
            seen.add(path)
            rows.append(
                {
                    "ref": str(row["id"]),
                    "label": f"{row['version']} · #{row['id']}",
                    "version": row["version"],
                    "created_at": row["created_at"],
                    "note": row["note"],
                    "file_path": path,
                    "current": False,
                }
            )
        for item in rows:
            p = Path(item["file_path"] or "")
            item["available"] = p.exists()
            item["sha256"] = sha256(p.read_bytes()).hexdigest() if p.exists() else None
            item.pop("file_path", None)
        return rows

    @staticmethod
    def _resolve_version(con, document_id: str, ref: str) -> tuple[dict[str, Any], Path] | None:
        if ref == "current":
            row = con.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row:
                return None
            return ({"ref": "current", "version": row["version"], "created_at": row["updated_at"], "note": "Archivo actual"}, Path(row["file_path"] or ""))
        try:
            rid = int(ref)
        except (TypeError, ValueError):
            return None
        row = con.execute("SELECT * FROM document_versions WHERE document_id=? AND id=?", (document_id, rid)).fetchone()
        if not row:
            return None
        return ({"ref": str(rid), "version": row["version"], "created_at": row["created_at"], "note": row["note"]}, Path(row["file_path"] or ""))

    def compare(self, con, document_id: str, from_ref: str, to_ref: str, actor_id: str) -> dict[str, Any]:
        left_res = self._resolve_version(con, document_id, from_ref)
        right_res = self._resolve_version(con, document_id, to_ref)
        if not left_res or not right_res:
            raise ValueError("Una de las versiones no existe.")
        left_meta, left_path = left_res
        right_meta, right_path = right_res
        if not left_path.exists() or not right_path.exists():
            raise ValueError("El archivo físico de una versión no está disponible.")
        left = self._flatten(left_path)
        right = self._flatten(right_path)
        a = [x.get("text", "") for x in left]
        b = [x.get("text", "") for x in right]
        matcher = SequenceMatcher(None, a, b, autojunk=False)
        rows: list[dict[str, Any]] = []
        metrics = {"unchanged": 0, "changed": 0, "added": 0, "removed": 0}
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for l, r in zip(left[i1:i2], right[j1:j2]):
                    rows.append({"status": "unchanged", "left": l, "right": r})
                    metrics["unchanged"] += 1
            elif tag == "replace":
                size = max(i2 - i1, j2 - j1)
                for k in range(size):
                    l = left[i1 + k] if i1 + k < i2 else None
                    r = right[j1 + k] if j1 + k < j2 else None
                    status = "changed" if l and r else ("removed" if l else "added")
                    rows.append({"status": status, "left": l, "right": r})
                    metrics[status] += 1
            elif tag == "delete":
                for l in left[i1:i2]:
                    rows.append({"status": "removed", "left": l, "right": None})
                    metrics["removed"] += 1
            elif tag == "insert":
                for r in right[j1:j2]:
                    rows.append({"status": "added", "left": None, "right": r})
                    metrics["added"] += 1
        summary = {
            **metrics,
            "total_rows": len(rows),
            "similarity": round(matcher.ratio() * 100, 1),
            "left_blocks": len(left),
            "right_blocks": len(right),
        }
        compare_id = "CMP-" + uuid.uuid4().hex[:12].upper()
        con.execute(
            "INSERT INTO document_compare_runs(id,document_id,from_ref,to_ref,actor_id,summary_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (compare_id, document_id, from_ref, to_ref, actor_id, json.dumps(summary, ensure_ascii=False), utc_now()),
        )
        return {
            "compare_id": compare_id,
            "document_id": document_id,
            "from": left_meta,
            "to": right_meta,
            "metrics": summary,
            "rows": rows[:800],
            "notice": "La comparación es textual y orientativa. La equivalencia jurídica exige revisión profesional y cotejo con fuentes canónicas.",
        }

    def save_working_draft(self, con, template_id: str, actor_id: str, base_revision_id: int, content: dict, note: str = "") -> dict[str, Any]:
        raw = json.dumps(content, ensure_ascii=False, sort_keys=True)
        digest = sha256(raw.encode("utf-8")).hexdigest()
        now = utc_now()
        con.execute(
            """INSERT INTO factory_working_drafts(template_id,actor_id,base_revision_id,content_json,content_hash,note,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(template_id,actor_id) DO UPDATE SET base_revision_id=excluded.base_revision_id,
               content_json=excluded.content_json,content_hash=excluded.content_hash,note=excluded.note,updated_at=excluded.updated_at""",
            (template_id, actor_id, int(base_revision_id), raw, digest, _clean(note)[:1000], now),
        )
        return {"ok": True, "template_id": template_id, "base_revision_id": int(base_revision_id), "content_hash": digest, "updated_at": now}

    def working_draft(self, con, template_id: str, actor_id: str) -> dict[str, Any] | None:
        row = con.execute(
            "SELECT * FROM factory_working_drafts WHERE template_id=? AND actor_id=?", (template_id, actor_id)
        ).fetchone()
        if not row:
            return None
        obj = dict(row)
        obj["content"] = json.loads(obj.pop("content_json"))
        return obj

    def activity_feed(self, con, scope_sql: str, params: list[Any], user: dict[str, Any], limit: int = 120) -> dict[str, Any]:
        cases = [dict(x) for x in con.execute(
            f"SELECT c.id,c.product_code,c.title,c.status,c.risk,c.updated_at FROM cases c WHERE {scope_sql}", params
        ).fetchall()]
        if not cases:
            return {"events": [], "metrics": {"events": 0, "unread": 0, "cases": 0}, "last_seen_at": None}
        ids = [x["id"] for x in cases]
        marks = ",".join("?" for _ in ids)
        event_rows: list[dict[str, Any]] = []
        for row in con.execute(
            f"""SELECT a.id,a.case_id,a.kind,a.text,a.created_at,c.title case_title,c.product_code
                FROM activity a JOIN cases c ON c.id=a.case_id
                WHERE a.case_id IN ({marks}) ORDER BY a.created_at DESC LIMIT ?""", [*ids, limit]
        ).fetchall():
            event_rows.append({**dict(row), "event_id": f"activity-{row['id']}", "event_type": "activity", "visibility": "shared"})
        visibility = "" if user["role"] in ("specialist", "admin") else " AND m.visibility='shared'"
        for row in con.execute(
            f"""SELECT m.id,m.case_id,m.body text,m.created_at,m.visibility,c.title case_title,c.product_code,
                       u.name actor_name,u.role actor_role
                FROM case_messages m JOIN cases c ON c.id=m.case_id JOIN users u ON u.id=m.author_id
                WHERE m.case_id IN ({marks}) {visibility} ORDER BY m.created_at DESC LIMIT ?""", [*ids, limit]
        ).fetchall():
            event_rows.append({**dict(row), "event_id": f"message-{row['id']}", "event_type": "message", "kind": "message"})
        for row in con.execute(
            f"""SELECT t.id,t.case_id,('Tarea: '||t.label||' · '||t.status) text,t.updated_at created_at,
                       c.title case_title,c.product_code,d.priority,u.name actor_name
                FROM case_tasks t JOIN cases c ON c.id=t.case_id
                LEFT JOIN case_task_details d ON d.task_id=t.id LEFT JOIN users u ON u.id=d.created_by
                WHERE t.case_id IN ({marks}) ORDER BY t.updated_at DESC LIMIT ?""", [*ids, limit]
        ).fetchall():
            event_rows.append({**dict(row), "event_id": f"task-{row['id']}", "event_type": "task", "kind": "task", "visibility": "shared"})
        comment_visibility = "" if user["role"] in ("specialist", "admin") else " AND dc.visibility='shared'"
        for row in con.execute(
            f"""SELECT dc.id,dc.case_id,('Comentario documental: '||dc.comment) text,dc.created_at,dc.visibility,
                       c.title case_title,c.product_code,u.name actor_name,u.role actor_role,d.name document_name
                FROM document_comments dc JOIN cases c ON c.id=dc.case_id JOIN users u ON u.id=dc.author_id
                JOIN documents d ON d.id=dc.document_id
                WHERE dc.case_id IN ({marks}) {comment_visibility} ORDER BY dc.created_at DESC LIMIT ?""", [*ids, limit]
        ).fetchall():
            event_rows.append({**dict(row), "event_id": f"comment-{row['id']}", "event_type": "comment", "kind": "comment"})
        events = sorted(event_rows, key=lambda x: x.get("created_at") or "", reverse=True)[:limit]
        read = con.execute("SELECT last_seen_at FROM activity_reads WHERE user_id=?", (user["id"],)).fetchone()
        last_seen = read["last_seen_at"] if read else None
        unread = sum(not last_seen or (x.get("created_at") or "") > last_seen for x in events)
        return {
            "events": events,
            "last_seen_at": last_seen,
            "metrics": {
                "events": len(events),
                "unread": unread,
                "cases": len(cases),
                "messages": sum(x.get("event_type") == "message" for x in events),
                "tasks": sum(x.get("event_type") == "task" for x in events),
                "comments": sum(x.get("event_type") == "comment" for x in events),
            },
        }

    @staticmethod
    def mark_activity_read(con, user_id: str) -> dict[str, Any]:
        now = utc_now()
        con.execute(
            "INSERT INTO activity_reads(user_id,last_seen_at) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET last_seen_at=excluded.last_seen_at",
            (user_id, now),
        )
        return {"ok": True, "last_seen_at": now}
