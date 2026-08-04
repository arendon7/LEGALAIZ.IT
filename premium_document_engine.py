from __future__ import annotations

"""Motor transversal de presentación y QA documental de LegalAIZ.it.

Centraliza formatos jurídicos colombianos para impedir que cada producto
implemente cifras, fechas y controles de salida de manera diferente.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

MONEY_FIELD_IDS = {
    "fees", "monthly_salary", "rent", "amount", "principal",
    "confirmed_prior_payments", "variable_average", "administration_charge",
    "commercial_value", "cadastral_value", "prior_salary_paid",
    "prior_cesantias_paid", "prior_interest_paid", "prior_prima_paid",
    "prior_vacation_paid", "prior_indemnity_paid", "obligation_amount",
    "reported_balance", "partial_payments_total", "other_charges",
    "agreement_total", "purchase_value", "reversal_amount",
}

MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
    "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
    "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte",
    "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
    "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos", 500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"}


def parse_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise InvalidOperation("boolean is not a monetary value")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raw = str(value or "").strip()
    if not raw:
        raise InvalidOperation("empty value")
    raw = re.sub(r"(?i)\b(COP|PESOS?|M/?CTE)\b", "", raw)
    raw = raw.replace("$", "").replace("\u00a0", "").replace(" ", "")
    if "," in raw and "." in raw:
        # Convención colombiana: 1.234.567,89
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        tail = raw.rsplit(",", 1)[1]
        raw = raw.replace(".", "")
        raw = raw.replace(",", "." if len(tail) <= 2 else "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif raw.count(".") == 1:
        head, tail = raw.split(".")
        if len(tail) == 3 and head not in ("0", "-0"):
            raw = head + tail
    return Decimal(raw)


def _under_thousand(n: int) -> str:
    if n < 30:
        return _UNITS[n]
    if n < 100:
        tens = (n // 10) * 10
        rest = n % 10
        return _TENS[tens] if not rest else f"{_TENS[tens]} y {_UNITS[rest]}"
    if n == 100:
        return "cien"
    hundreds = (n // 100) * 100
    rest = n % 100
    prefix = "ciento" if hundreds == 100 else _HUNDREDS[hundreds]
    return prefix if not rest else f"{prefix} {_under_thousand(rest)}"


def number_to_words_es(value: int) -> str:
    n = int(value)
    if n < 0:
        return "menos " + number_to_words_es(abs(n))
    if n < 1000:
        return _under_thousand(n)
    if n < 1_000_000:
        thousands, rest = divmod(n, 1000)
        prefix = "mil" if thousands == 1 else f"{number_to_words_es(thousands)} mil"
        return prefix if not rest else f"{prefix} {number_to_words_es(rest)}"
    if n < 1_000_000_000_000:
        millions, rest = divmod(n, 1_000_000)
        prefix = "un millón" if millions == 1 else f"{number_to_words_es(millions)} millones"
        return prefix if not rest else f"{prefix} {number_to_words_es(rest)}"
    billions, rest = divmod(n, 1_000_000_000_000)
    prefix = "un billón" if billions == 1 else f"{number_to_words_es(billions)} billones"
    return prefix if not rest else f"{prefix} {number_to_words_es(rest)}"


def _apocopate_un(text: str) -> str:
    return re.sub(r"\bveintiuno$", "veintiún", re.sub(r"\buno$", "un", text))


def format_cop(value, *, include_words: bool = True, empty: str = "No informado") -> str:
    try:
        amount = parse_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return empty if value in (None, "") else str(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    integer = int(amount)
    cents = int((amount - Decimal(integer)) * 100)
    numeric = f"{integer:,}".replace(",", ".")
    if cents:
        numeric += f",{cents:02d}"
    numeric_label = f"COP ${sign}{numeric}"
    if not include_words:
        return numeric_label
    words = _apocopate_un(number_to_words_es(integer)).upper()
    if cents:
        words += f" CON {cents:02d}/100"
    return f"{sign}{words} PESOS M/CTE ({numeric_label})"


def format_number_es(value, *, empty: str = "No informado") -> str:
    try:
        number = parse_decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return empty if value in (None, "") else str(value)
    if number == number.to_integral():
        return f"{int(number):,}".replace(",", ".")
    rendered = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return rendered.rstrip("0").rstrip(",")


def format_date_es(value, *, empty: str = "No informado") -> str:
    if value in (None, ""):
        return empty
    parsed = None
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        raw = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                parsed = date.fromisoformat(raw)
            except ValueError:
                return raw
    return f"{parsed.day} de {MONTHS_ES[parsed.month - 1]} de {parsed.year}"


def format_display_value(key: str, value, spec: dict | None = None, override: str | None = None) -> str:
    if value in (None, "", []):
        return "No informado"
    spec = spec or {}
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) if value else "No informado"
    display_format = override or spec.get("display_format")
    if display_format == "cop_words":
        return format_cop(value, include_words=True)
    if display_format == "cop_numeric" or (key in MONEY_FIELD_IDS and not display_format):
        return format_cop(value, include_words=False)
    if display_format == "date_es" or spec.get("type") == "date":
        return format_date_es(value)
    if display_format == "decimal_es" or spec.get("type") == "number":
        return format_number_es(value)
    return str(value)


def audit_docx(path: Path) -> dict:
    """Auditoría estructural rápida; complementa, no sustituye, el QA visual."""
    path = Path(path)
    findings: list[dict] = []
    try:
        with ZipFile(path) as zf:
            names = set(zf.namelist())
            required = {"[Content_Types].xml", "word/document.xml", "word/header1.xml", "word/footer1.xml", "docProps/core.xml"}
            for missing in sorted(required - names):
                findings.append({"severity": "error", "code": "DOCX-MISSING-PART", "detail": missing})
            document = zf.read("word/document.xml").decode("utf-8", "replace") if "word/document.xml" in names else ""
            header = zf.read("word/header1.xml").decode("utf-8", "replace") if "word/header1.xml" in names else ""
            footer = zf.read("word/footer1.xml").decode("utf-8", "replace") if "word/footer1.xml" in names else ""
            plain = re.sub(r"<[^>]+>", " ", document)
            for token in ("{{", "undefined", " NULL ", "[OBJETO PENDIENTE]", "[CONTRATANTE]", "[TRABAJADOR]"):
                if token.casefold() in plain.casefold():
                    findings.append({"severity": "error", "code": "UNRESOLVED-SENTINEL", "detail": token})
            table_count = document.count("<w:tbl>")
            header_rows = document.count("<w:tblHeader")
            if table_count and header_rows < table_count:
                findings.append({"severity": "warning", "code": "TABLE-HEADER-NOT-REPEATED", "detail": f"{header_rows}/{table_count}"})
            if "BORRADOR CONTROLADO" not in header:
                findings.append({"severity": "error", "code": "DRAFT-BANNER-MISSING", "detail": "Encabezado sin control de borrador"})
            if "PAGE" not in footer or "NUMPAGES" not in footer:
                findings.append({"severity": "error", "code": "PAGE-FIELDS-MISSING", "detail": "Pie sin campos PAGE/NUMPAGES"})
    except (BadZipFile, KeyError, OSError) as exc:
        findings.append({"severity": "error", "code": "INVALID-DOCX", "detail": str(exc)})
    return {
        "path": str(path),
        "valid": not any(f["severity"] == "error" for f in findings),
        "findings": findings,
    }
