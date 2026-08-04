from __future__ import annotations

from pathlib import Path
from typing import Any
import json


class ExperienceCenter:
    """Read model for the v2.1 navigation, file center and global search.

    The center does not bypass case-level RBAC. The caller provides the SQL case scope
    already used by the runtime, so every aggregation is filtered by the authenticated role.
    """

    def __init__(self, root: Path, products: list[dict[str, Any]]):
        self.root = Path(root)
        self.products = products
        self.product_map = {item["code"]: item for item in products}
        path = self.root / "data" / "file_requirements.json"
        self.requirements = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    @staticmethod
    def create_schema(con) -> None:
        columns = {row[1] for row in con.execute("PRAGMA table_info(attachments)")}
        if "requirement_key" not in columns:
            con.execute("ALTER TABLE attachments ADD COLUMN requirement_key TEXT")
        if "description" not in columns:
            con.execute("ALTER TABLE attachments ADD COLUMN description TEXT")
        if "updated_at" not in columns:
            con.execute("ALTER TABLE attachments ADD COLUMN updated_at TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS idx_attachments_case_requirement ON attachments(case_id,requirement_key)")

    def product_requirements(self, code: str) -> dict[str, Any]:
        spec = self.requirements.get(code, {"title": code, "required": [], "optional": []})
        return {
            "product_code": code,
            "product_title": self.product_map.get(code, {}).get("title", spec.get("title", code)),
            "required": spec.get("required", []),
            "optional": spec.get("optional", []),
        }

    def _coverage(self, code: str, attachments: list[dict[str, Any]]) -> dict[str, Any]:
        spec = self.product_requirements(code)
        exact = {item.get("requirement_key") for item in attachments if item.get("requirement_key")}
        categories = {item.get("category") for item in attachments if item.get("category")}
        required = []
        for item in spec["required"]:
            satisfied = item.get("key") in exact
            # Backward-compatible inference for demo attachments created before v2.1.
            if not satisfied and not exact:
                same_category = [x for x in spec["required"] if x.get("category") == item.get("category")]
                satisfied = len(same_category) == 1 and item.get("category") in categories
            required.append({**item, "satisfied": bool(satisfied)})
        optional = [{**item, "satisfied": item.get("key") in exact} for item in spec["optional"]]
        completed = sum(bool(x["satisfied"]) for x in required)
        total = len(required)
        return {
            "required": required,
            "optional": optional,
            "completed": completed,
            "total": total,
            "percent": round(completed * 100 / total) if total else 100,
            "ready": completed == total,
        }

    def file_center(self, con, scope_sql: str, params: list[Any]) -> dict[str, Any]:
        cases = [dict(row) for row in con.execute(
            f"""SELECT c.id,c.product_code,c.title,c.risk,c.status,c.review_status,c.updated_at,
                       u.name specialist_name
                FROM cases c LEFT JOIN users u ON u.id=c.specialist_id
                WHERE {scope_sql} ORDER BY c.updated_at DESC""",
            params,
        ).fetchall()]
        documents = [dict(row) for row in con.execute(
            f"""SELECT d.id,d.case_id,d.product_code,d.kind,d.name,d.mime_type,d.created_at,d.updated_at,
                       d.version,d.status,c.title case_title,c.risk
                FROM documents d JOIN cases c ON c.id=d.case_id
                WHERE {scope_sql} ORDER BY d.updated_at DESC""",
            params,
        ).fetchall()]
        attachments = [dict(row) for row in con.execute(
            f"""SELECT a.id,a.case_id,a.name,a.mime_type,a.size_bytes,a.category,a.created_at,a.updated_at,
                       a.sha256,a.detected_type,a.security_status,a.uploaded_by,a.requirement_key,a.description,
                       c.product_code,c.title case_title,c.risk
                FROM attachments a JOIN cases c ON c.id=a.case_id
                WHERE {scope_sql} ORDER BY COALESCE(a.updated_at,a.created_at) DESC""",
            params,
        ).fetchall()]
        by_case: dict[str, list[dict[str, Any]]] = {}
        for item in attachments:
            by_case.setdefault(item["case_id"], []).append(item)
        coverage = []
        for case in cases:
            cov = self._coverage(case["product_code"], by_case.get(case["id"], []))
            coverage.append({
                "case_id": case["id"],
                "case_title": case["title"],
                "product_code": case["product_code"],
                "product_title": self.product_map.get(case["product_code"], {}).get("title", case["product_code"]),
                "risk": case["risk"],
                **cov,
            })
        total_bytes = sum(int(item.get("size_bytes") or 0) for item in attachments)
        return {
            "metrics": {
                "cases": len(cases),
                "documents": len(documents),
                "attachments": len(attachments),
                "total_bytes": total_bytes,
                "complete_cases": sum(bool(x["ready"]) for x in coverage),
                "pending_required": sum(max(0, x["total"] - x["completed"]) for x in coverage),
            },
            "cases": cases,
            "documents": documents,
            "attachments": attachments,
            "coverage": coverage,
            "requirements": self.requirements,
            "notice": "La cobertura documental se calcula con la relación explícita del soporte a un requisito. Los archivos antiguos pueden inferirse por categoría únicamente cuando la correspondencia es inequívoca.",
        }

    def global_search(self, con, scope_sql: str, params: list[Any], query: str, limit: int = 30) -> dict[str, Any]:
        term = (query or "").strip()
        if len(term) < 2:
            return {"query": term, "results": [], "count": 0}
        like = f"%{term}%"
        results: list[dict[str, Any]] = []
        for product in self.products:
            haystack = " ".join(str(product.get(key, "")) for key in ("code", "title", "summary", "vertical"))
            if term.casefold() in haystack.casefold():
                results.append({
                    "type": "product", "id": product["code"], "title": product["title"],
                    "subtitle": f"{product.get('vertical','')} · {product['code']}", "route": f"/producto/{product['code']}"
                })
        rows = con.execute(
            f"""SELECT c.id,c.title,c.product_code,c.status,c.risk,c.updated_at
                FROM cases c WHERE {scope_sql} AND (c.id LIKE ? OR c.title LIKE ? OR c.product_code LIKE ?)
                ORDER BY c.updated_at DESC LIMIT ?""",
            [*params, like, like, like, limit],
        ).fetchall()
        results.extend({
            "type": "case", "id": row["id"], "title": row["title"],
            "subtitle": f"{row['product_code']} · {row['status']}", "risk": row["risk"], "route": f"/caso/{row['id']}"
        } for row in rows)
        rows = con.execute(
            f"""SELECT d.id,d.name,d.case_id,d.kind,d.status,d.updated_at
                FROM documents d JOIN cases c ON c.id=d.case_id
                WHERE {scope_sql} AND (d.name LIKE ? OR d.kind LIKE ? OR d.case_id LIKE ?)
                ORDER BY d.updated_at DESC LIMIT ?""",
            [*params, like, like, like, limit],
        ).fetchall()
        results.extend({
            "type": "document", "id": row["id"], "title": row["name"],
            "subtitle": f"{row['kind']} · {row['case_id']} · {row['status']}", "route": f"/documento/{row['id']}"
        } for row in rows)
        rows = con.execute(
            f"""SELECT a.id,a.name,a.case_id,a.category,a.created_at
                FROM attachments a JOIN cases c ON c.id=a.case_id
                WHERE {scope_sql} AND (a.name LIKE ? OR a.category LIKE ? OR a.case_id LIKE ?)
                ORDER BY a.created_at DESC LIMIT ?""",
            [*params, like, like, like, limit],
        ).fetchall()
        results.extend({
            "type": "attachment", "id": row["id"], "title": row["name"],
            "subtitle": f"{row['category']} · {row['case_id']}", "route": "/archivos"
        } for row in rows)
        return {"query": term, "results": results[:limit], "count": min(len(results), limit)}
