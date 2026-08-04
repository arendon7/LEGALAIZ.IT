from __future__ import annotations

"""Bootstrap liviano y verificable del esquema PostgreSQL de LegalAIZ.it.

Este módulo no importa ``application_services`` ni el registro jurídico completo.
Permite que el kit de certificación cree y valide el esquema sin transportar las
bibliotecas documentales utilizadas por el runtime de la aplicación.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

from legalai_platform import release_metadata as release
from legalai_platform.database import connect_database

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = ROOT / "deploy" / "postgres_schema_candidate.sql"


def _split_sql(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(script):
        ch = script[i]
        current.append(ch)
        if quote:
            if ch == quote:
                if i + 1 < len(script) and script[i + 1] == quote:
                    current.append(script[i + 1])
                    i += 1
                else:
                    quote = None
        elif ch in {"'", '"'}:
            quote = ch
        elif ch == ";":
            statement = "".join(current[:-1]).strip()
            if statement:
                statements.append(statement)
            current = []
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def schema_statements(path: Path = DEFAULT_SCHEMA_PATH) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    script = path.read_text(encoding="utf-8")
    script = "\n".join(
        line for line in script.splitlines() if not line.lstrip().startswith("--")
    )
    statements: list[str] = []
    for raw in _split_sql(script):
        cleaned = raw.strip()
        if not cleaned or cleaned.upper() in {"BEGIN", "COMMIT"}:
            continue
        statements.append(cleaned)
    return statements


def schema_contract(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    statements = schema_statements(path)
    tables = sum(bool(re.match(r"(?is)^CREATE\s+TABLE\b", item)) for item in statements)
    indexes = sum(bool(re.match(r"(?is)^CREATE\s+(?:UNIQUE\s+)?INDEX\b", item)) for item in statements)
    milestone = re.search(r"(?m)^--\s*milestone=(.+?)\s*$", text)
    version = re.search(r"(?m)^--\s*version=(.+?)\s*$", text)
    ordered = _foreign_key_order_is_valid(statements)
    return {
        "schema": "legalaizit-postgres-schema-contract-v1",
        "path": str(path),
        "milestone": milestone.group(1).strip() if milestone else None,
        "version": version.group(1).strip() if version else None,
        "statements": len(statements),
        "tables": tables,
        "indexes": indexes,
        "foreign_key_order_valid": ordered,
        "release_identity_valid": bool(
            milestone
            and version
            and milestone.group(1).strip() == release.MILESTONE
            and version.group(1).strip() == release.VERSION
        ),
        "ok": tables >= 100 and indexes >= 60 and ordered,
        "production_authorized": False,
    }


def _foreign_key_order_is_valid(statements: list[str]) -> bool:
    created: set[str] = set()
    for statement in statements:
        match = re.match(
            r'(?is)^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"?([A-Za-z_][A-Za-z0-9_]*)"?',
            statement,
        )
        if not match:
            continue
        table = match.group(1)
        dependencies = {
            item
            for item in re.findall(
                r'(?is)REFERENCES\s+"?([A-Za-z_][A-Za-z0-9_]*)"?', statement
            )
            if item != table
        }
        if not dependencies.issubset(created):
            return False
        created.add(table)
    return True


def bootstrap_postgres_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    contract = schema_contract(path)
    if not contract["ok"] or not contract["release_identity_valid"]:
        raise RuntimeError(f"Contrato de esquema inválido: {contract}")

    con = connect_database(Path("unused.db"))
    if getattr(con, "backend", None) != "postgresql":
        con.close()
        raise RuntimeError("El bootstrap externo exige LEGAL_DATABASE_BACKEND=postgresql")
    executed = 0
    try:
        for statement in schema_statements(path):
            con.execute(statement)
            executed += 1
        con.commit()
        row = con.execute(
            "SELECT current_schema() AS schema," 
            "(SELECT COUNT(*) FROM information_schema.tables "
            " WHERE table_schema=current_schema()) AS tables," 
            "(SELECT COUNT(*) FROM pg_indexes "
            " WHERE schemaname=current_schema()) AS indexes"
        ).fetchone()
        actual_tables = int(row["tables"])
        actual_indexes = int(row["indexes"])
        if actual_tables < contract["tables"]:
            raise AssertionError(
                f"Esquema incompleto: {actual_tables}/{contract['tables']} tablas"
            )
        return {
            "schema": "legalaizit-postgres-schema-bootstrap-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "milestone": release.MILESTONE,
            "version": release.VERSION,
            "database_schema": row["schema"],
            "executed_statements": executed,
            "expected_tables": contract["tables"],
            "actual_tables": actual_tables,
            "expected_indexes": contract["indexes"],
            "actual_indexes": actual_indexes,
            "ok": True,
            "production_authorized": False,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
