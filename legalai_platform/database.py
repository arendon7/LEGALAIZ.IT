from __future__ import annotations

"""Adaptador de persistencia dual para LegalAIZ.it.

M31.5 mantiene SQLite como perfil local certificado y añade un contrato ejecutable
para PostgreSQL. El adaptador traduce únicamente el subconjunto SQL utilizado por
la aplicación; la certificación externa exige ejecutar la suite contra un servidor
PostgreSQL real y conservar la evidencia generada por ``tools/postgres_certify.py``.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import re
import sqlite3


SUPPORTED_BACKENDS = {"sqlite", "postgresql"}


class DatabaseConfigurationError(RuntimeError):
    pass


class PostgresDriverUnavailable(DatabaseConfigurationError):
    pass


class ManagedSQLiteConnection(sqlite3.Connection):
    """Cierra defensivamente el descriptor en rutas excepcionales."""

    backend = "sqlite"

    def __del__(self) -> None:  # pragma: no cover - defensa de último recurso
        try:
            self.close()
        except Exception:
            pass


class HybridRow(Mapping[str, Any]):
    """Fila compatible con ``sqlite3.Row``: acepta índices y nombres."""

    __slots__ = ("_columns", "_values", "_index")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._index = {name: idx for idx, name in enumerate(self._columns)}

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return zip(self._columns, self._values)

    def __repr__(self) -> str:  # pragma: no cover - diagnóstico
        return f"HybridRow({dict(self)!r})"


@dataclass(frozen=True)
class DatabaseRuntime:
    backend: str
    database_url_configured: bool
    driver_available: bool
    compatibility_layer: str = "m31.6"

    def public(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "database_url_configured": self.database_url_configured,
            "driver_available": self.driver_available,
            "compatibility_layer": self.compatibility_layer,
        }


def selected_backend(env: Mapping[str, str] | None = None) -> str:
    values = env or os.environ
    backend = str(values.get("LEGAL_DATABASE_BACKEND", "sqlite")).strip().lower()
    aliases = {"postgres": "postgresql", "pg": "postgresql"}
    backend = aliases.get(backend, backend)
    if backend not in SUPPORTED_BACKENDS:
        raise DatabaseConfigurationError(
            f"LEGAL_DATABASE_BACKEND inválido: {backend!r}. Use sqlite o postgresql."
        )
    return backend


def _psycopg_module():
    try:
        import psycopg  # type: ignore
    except Exception as exc:  # pragma: no cover - depende del entorno
        raise PostgresDriverUnavailable(
            "PostgreSQL requiere psycopg 3. Instale requirements-postgres.txt."
        ) from exc
    return psycopg


def postgres_driver_available() -> bool:
    try:
        _psycopg_module()
        return True
    except PostgresDriverUnavailable:
        return False


def runtime_status(env: Mapping[str, str] | None = None) -> DatabaseRuntime:
    values = env or os.environ
    backend = selected_backend(values)
    return DatabaseRuntime(
        backend=backend,
        database_url_configured=bool(
            str(values.get("DATABASE_URL", "")).strip()
            or str(values.get("DATABASE_URL_FILE", "")).strip()
            or str(values.get("PGHOST", "")).strip()
        ),
        driver_available=backend == "sqlite" or postgres_driver_available(),
    )




def _postgres_connect_arguments(values: Mapping[str, str]) -> tuple[tuple[Any, ...], dict[str, Any]]:
    direct = str(values.get("DATABASE_URL", "")).strip()
    url_file = str(values.get("DATABASE_URL_FILE", "")).strip()
    if not direct and url_file:
        path = Path(url_file).expanduser()
        if not path.is_file():
            raise DatabaseConfigurationError(f"DATABASE_URL_FILE no existe: {path}")
        direct = path.read_text(encoding="utf-8").strip()
    if direct:
        return (direct,), {"autocommit": False}

    host = str(values.get("PGHOST", "")).strip()
    database = str(values.get("PGDATABASE", "legalaiz")).strip()
    user = str(values.get("PGUSER", "legalaiz")).strip()
    port = str(values.get("PGPORT", "5432")).strip()
    password = str(values.get("PGPASSWORD", "")).strip()
    password_file = str(values.get("LEGAL_POSTGRES_PASSWORD_FILE", "")).strip()
    if not password and password_file:
        path = Path(password_file).expanduser()
        if not path.is_file():
            raise DatabaseConfigurationError(f"LEGAL_POSTGRES_PASSWORD_FILE no existe: {path}")
        password = path.read_text(encoding="utf-8").strip()
    if not host or not password:
        raise DatabaseConfigurationError(
            "Configure DATABASE_URL/DATABASE_URL_FILE o PGHOST con LEGAL_POSTGRES_PASSWORD_FILE."
        )
    kwargs = {
        "host": host, "dbname": database, "user": user, "port": int(port),
        "password": password, "autocommit": False,
    }
    sslmode = str(values.get("PGSSLMODE", "")).strip()
    if sslmode:
        kwargs["sslmode"] = sslmode
    return (), kwargs

def connect_database(
    sqlite_path: Path,
    *,
    env: Mapping[str, str] | None = None,
    timeout: int = 30,
):
    values = env or os.environ
    backend = selected_backend(values)
    if backend == "sqlite":
        con = sqlite3.connect(
            Path(sqlite_path), timeout=timeout, factory=ManagedSQLiteConnection
        )
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    args, kwargs = _postgres_connect_arguments(values)
    psycopg = _psycopg_module()
    kwargs.setdefault("connect_timeout", int(values.get("LEGAL_POSTGRES_CONNECT_TIMEOUT", timeout)))
    kwargs.setdefault("application_name", str(values.get("LEGAL_POSTGRES_APPLICATION_NAME", "legalaizit-m31.6")))
    raw = psycopg.connect(*args, **kwargs)
    adapter = PostgresConnectionAdapter(raw)
    schema = str(values.get("LEGAL_POSTGRES_SCHEMA", "public")).strip() or "public"
    create_schema = str(values.get("LEGAL_POSTGRES_CREATE_SCHEMA", "false")).strip().lower() in {"1", "true", "yes", "on"}
    adapter.configure_session(schema=schema, create_schema=create_schema)
    return adapter


def _replace_qmark(sql: str) -> str:
    """Convierte marcadores DB-API ``?`` a ``%s`` fuera de literales SQL."""

    output: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(sql):
        ch = sql[i]
        if quote:
            output.append(ch)
            if ch == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    output.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            output.append(ch)
        elif ch == "?":
            output.append("%s")
        else:
            output.append(ch)
        i += 1
    return "".join(output)


def _split_script(script: str) -> list[str]:
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


def _translate_insert_or_ignore(sql: str) -> str:
    match = re.match(r"(?is)^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", sql)
    if not match:
        return sql
    translated = re.sub(
        r"(?is)^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", "INSERT INTO ", sql, count=1
    )
    if re.search(r"(?is)\bON\s+CONFLICT\b", translated):
        return translated
    return translated.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"


def _translate_insert_or_replace(sql: str) -> str:
    match = re.match(
        r"(?is)^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+([A-Za-z_][\w]*)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)\s*$",
        sql.strip().rstrip(";"),
    )
    if not match:
        return sql
    table, raw_columns, raw_values = match.groups()
    columns = [item.strip() for item in raw_columns.split(",")]
    if not columns:
        return sql
    conflict = columns[0]
    updates = ",".join(
        f"{column}=EXCLUDED.{column}" for column in columns[1:]
    )
    suffix = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
    return (
        f"INSERT INTO {table}({','.join(columns)}) VALUES({raw_values}) "
        f"ON CONFLICT({conflict}) {suffix}"
    )


def translate_sqlite_sql(sql: str) -> str:
    """Traduce el subconjunto de SQLite usado por LegalAIZ.it a PostgreSQL."""

    translated = sql.strip()
    translated = re.sub(
        r"(?i)\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        translated,
    )
    translated = re.sub(r"(?i)\bAUTOINCREMENT\b", "", translated)
    translated = re.sub(r"(?i)\bBLOB\b", "BYTEA", translated)
    translated = _translate_insert_or_ignore(translated)
    translated = _translate_insert_or_replace(translated)
    translated = _replace_qmark(translated)
    return translated


class PostgresCursorAdapter:
    def __init__(self, raw_cursor, *, lastrowid: int | None = None):
        self._raw = raw_cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self) -> int:
        return int(self._raw.rowcount or 0)

    @property
    def description(self):
        return self._raw.description

    def _columns(self) -> tuple[str, ...]:
        if not self._raw.description:
            return ()
        return tuple(str(item.name if hasattr(item, "name") else item[0]) for item in self._raw.description)

    def fetchone(self):
        row = self._raw.fetchone()
        if row is None:
            return None
        return HybridRow(self._columns(), row)

    def fetchall(self):
        columns = self._columns()
        return [HybridRow(columns, row) for row in self._raw.fetchall()]

    def __iter__(self):
        columns = self._columns()
        for row in self._raw:
            yield HybridRow(columns, row)


class PostgresConnectionAdapter:
    backend = "postgresql"

    def __init__(self, raw_connection):
        self._raw = raw_connection
        self._serial_tables: set[str] = set()
        self._non_serial_tables: set[str] = set()
        self.schema = "public"

    @staticmethod
    def _validated_identifier(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise DatabaseConfigurationError(
                f"Identificador PostgreSQL inválido: {value!r}"
            )
        return value

    def configure_session(self, *, schema: str, create_schema: bool = False) -> None:
        schema = self._validated_identifier(schema)
        quoted = '"' + schema.replace('"', '""') + '"'
        if create_schema:
            cursor = self._raw.cursor()
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted}")
            self._raw.commit()
        cursor = self._raw.cursor()
        cursor.execute(f"SET search_path TO {quoted}")
        self.schema = schema

    def _raw_execute(self, sql: str, params: Sequence[Any] | None = None):
        cursor = self._raw.cursor()
        cursor.execute(sql, tuple(params or ()))
        return cursor

    def _compatibility_query(self, sql: str, params: Sequence[Any] | None):
        normalized = " ".join(sql.strip().split())
        lower = normalized.lower()
        if lower == "pragma foreign_keys=on":
            return self._raw_execute("SELECT 1 AS foreign_keys_enabled")
        if lower == "pragma integrity_check":
            return self._raw_execute("SELECT 'ok' AS integrity_check")
        table_info = re.match(r"(?i)^pragma\s+table_info\(([^)]+)\)$", normalized)
        if table_info:
            table = table_info.group(1).strip().strip('"')
            return self._raw_execute(
                """
                SELECT ordinal_position - 1 AS cid,
                       column_name AS name,
                       data_type AS type,
                       CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS notnull,
                       column_default AS dflt_value,
                       CASE WHEN column_name IN (
                           SELECT kcu.column_name
                           FROM information_schema.table_constraints tc
                           JOIN information_schema.key_column_usage kcu
                             ON tc.constraint_name=kcu.constraint_name
                            AND tc.table_schema=kcu.table_schema
                           WHERE tc.constraint_type='PRIMARY KEY'
                             AND tc.table_schema=current_schema()
                             AND tc.table_name=%s
                       ) THEN 1 ELSE 0 END AS pk
                FROM information_schema.columns
                WHERE table_schema=current_schema() AND table_name=%s
                ORDER BY ordinal_position
                """,
                (table, table),
            )
        if "from sqlite_master" in lower:
            if "name=" in lower:
                table = params[0] if params else re.search(r"(?i)name\s*=\s*'([^']+)'", normalized).group(1)
                return self._raw_execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=%s",
                    (table,),
                )
            return self._raw_execute(
                "SELECT tablename AS name FROM pg_catalog.pg_tables WHERE schemaname=current_schema()"
            )
        return None

    def _remember_serial_table(self, sql: str) -> None:
        match = re.search(
            r'(?is)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"?([A-Za-z_][\w]*)"?\s*\((.*?)\)',
            sql,
        )
        if match and re.search(r"(?i)\bid\s+BIGSERIAL\s+PRIMARY\s+KEY\b", match.group(2)):
            table = match.group(1)
            self._serial_tables.add(table)
            self._non_serial_tables.discard(table)

    def _is_serial_table(self, table: str) -> bool:
        if table in self._serial_tables:
            return True
        if table in self._non_serial_tables:
            return False
        cursor = self._raw_execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=current_schema()
              AND table_name=%s
              AND column_name='id'
              AND column_default LIKE 'nextval(%'
            LIMIT 1
            """,
            (table,),
        )
        if cursor.fetchone() is not None:
            self._serial_tables.add(table)
            return True
        self._non_serial_tables.add(table)
        return False

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        special = self._compatibility_query(sql, params)
        if special is not None:
            return PostgresCursorAdapter(special)
        translated = translate_sqlite_sql(sql)
        self._remember_serial_table(translated)
        insert = re.match(
            r'(?is)^\s*INSERT\s+INTO\s+"?([A-Za-z_][\w]*)"?\s*(?:\(([^)]*)\))?',
            translated,
        )
        wants_id = False
        if insert and not re.search(r"(?i)\bRETURNING\b", translated):
            table = insert.group(1)
            raw_columns = insert.group(2) or ""
            columns = {item.strip().strip('"').lower() for item in raw_columns.split(",") if item.strip()}
            wants_id = "id" not in columns and self._is_serial_table(table)
        if wants_id:
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        cursor = self._raw_execute(translated, params)
        lastrowid = None
        if wants_id:
            row = cursor.fetchone()
            if row:
                lastrowid = int(row[0])
        return PostgresCursorAdapter(cursor, lastrowid=lastrowid)

    def executemany(self, sql: str, parameters: Sequence[Sequence[Any]]):
        translated = translate_sqlite_sql(sql)
        cursor = self._raw.cursor()
        cursor.executemany(translated, parameters)
        return PostgresCursorAdapter(cursor)

    def executescript(self, script: str):
        cursor = None
        for statement in _split_script(script):
            cursor = self.execute(statement)
        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def cursor(self):
        return PostgresCursorAdapter(self._raw.cursor())

    @property
    def raw_connection(self):
        """Acceso explícito solo para herramientas de infraestructura."""
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False
