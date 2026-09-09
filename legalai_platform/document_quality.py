from __future__ import annotations

import hashlib
import posixpath
import re
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from docx import Document


REQUIRED_OOXML_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/styles.xml",
}
RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DOCX_MAIN_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
UNRESOLVED_PATTERNS = (
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"\$\{[^{}]+\}"),
    re.compile(r"\[\[[^\[\]]+\]\]"),
    re.compile(r"<<[^<>]+>>"),
    re.compile(r"\b(?:NULL|undefined|NaN)\b", re.I),
)
SOFT_SENTINELS = (
    re.compile(r"\bN/?A\b", re.I),
    re.compile(r"_{5,}"),
)


def _relationship_target(rels_path: str, target: str) -> str:
    """Resolve an internal OOXML relationship target to a package part.

    ``lstrip('./')`` must not be used here: it can erase the leading ``../`` of
    a path that escaped the package root. We normalize first and remove only the
    single OPC root slash when the relationship target is package-absolute.
    """
    target = str(target or "").split("#", 1)[0]
    if target.startswith("/"):
        return posixpath.normpath(target)[1:]
    if rels_path == "_rels/.rels":
        base = ""
    else:
        owner = rels_path.replace("/_rels/", "/")
        if owner.endswith(".rels"):
            owner = owner[:-5]
        base = posixpath.dirname(owner)
    return posixpath.normpath(posixpath.join(base, target))


def _unsafe_package_name(name: str) -> str | None:
    """Return a reason when a ZIP entry is ambiguous or unsafe as an OPC part."""
    if not name:
        return "nombre vacío"
    if name.startswith("/"):
        return "ruta absoluta"
    if "\\" in name:
        return "separador inverso no permitido en OPC"
    candidate = name[:-1] if name.endswith("/") else name
    if not candidate:
        return "entrada de directorio raíz inválida"
    segments = candidate.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return "segmento de ruta vacío, '.' o '..'"
    return None


def _validate_content_types(package: ZipFile, names: set[str], errors: list[str]) -> None:
    """Validate OPC content-type declarations required for an ordinary DOCX."""
    part = "[Content_Types].xml"
    if part not in names:
        return
    try:
        root = ET.fromstring(package.read(part))
    except ET.ParseError:
        return

    expected_root = f"{{{CONTENT_TYPES_NS}}}Types"
    if root.tag != expected_root:
        errors.append("[Content_Types].xml no usa el elemento raíz Types del espacio de nombres OPC esperado.")
        return

    defaults: set[str] = set()
    overrides: set[str] = set()
    main_content_type: str | None = None
    for child in root:
        if child.tag == f"{{{CONTENT_TYPES_NS}}}Default":
            extension = str(child.attrib.get("Extension") or "").strip()
            content_type = str(child.attrib.get("ContentType") or "").strip()
            key = extension.casefold()
            if not extension or not content_type:
                errors.append("[Content_Types].xml contiene un Default sin Extension o ContentType.")
                continue
            if key in defaults:
                errors.append(f"[Content_Types].xml contiene un Default duplicado para la extensión {extension}.")
            defaults.add(key)
        elif child.tag == f"{{{CONTENT_TYPES_NS}}}Override":
            part_name = str(child.attrib.get("PartName") or "").strip()
            content_type = str(child.attrib.get("ContentType") or "").strip()
            if not part_name or not content_type:
                errors.append("[Content_Types].xml contiene un Override sin PartName o ContentType.")
                continue
            if not part_name.startswith("/"):
                errors.append(f"[Content_Types].xml contiene un PartName no absoluto: {part_name}.")
                continue
            normalized_part = posixpath.normpath(part_name)
            if normalized_part != part_name or normalized_part.startswith("/../") or "\\" in part_name:
                errors.append(f"[Content_Types].xml contiene un PartName inseguro o ambiguo: {part_name}.")
                continue
            key = part_name.casefold()
            if key in overrides:
                errors.append(f"[Content_Types].xml contiene un Override duplicado o con colisión de mayúsculas: {part_name}.")
            overrides.add(key)
            package_name = part_name[1:]
            if package_name not in names:
                errors.append(f"[Content_Types].xml declara una parte inexistente: {part_name}.")
            if key == "/word/document.xml":
                main_content_type = content_type

    if main_content_type is None:
        errors.append("[Content_Types].xml no declara /word/document.xml mediante Override.")
    elif main_content_type != DOCX_MAIN_CONTENT_TYPE:
        errors.append(
            "[Content_Types].xml declara un ContentType no válido para el documento principal DOCX: "
            + main_content_type
            + "."
        )


def _document_text(document: Document) -> str:
    parts: list[str] = []
    parts.extend(paragraph.text for paragraph in document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    for section in document.sections:
        for container in (section.header, section.footer):
            parts.extend(paragraph.text for paragraph in container.paragraphs)
            for table in container.tables:
                for row in table.rows:
                    parts.extend(cell.text for cell in row.cells)
    return "\n".join(part for part in parts if part is not None)


def _duplicate_paragraphs(document: Document) -> list[str]:
    normalized: list[str] = []
    for paragraph in document.paragraphs:
        text = re.sub(r"\s+", " ", paragraph.text or "").strip().casefold()
        if len(text) >= 80:
            normalized.append(text)
    return [text[:160] for text, count in Counter(normalized).items() if count > 1]


def validate_docx(path: str | Path, expected_product: str | None = None) -> dict:
    """Validate a DOCX as an OOXML package and as an editable Word document.

    Errors block delivery. Warnings identify issues that require human review but
    may be legitimate in an editable draft, such as signature lines or N/A.
    """
    file_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {
        "bytes": file_path.stat().st_size if file_path.is_file() else 0,
        "package_parts": 0,
        "package_entries": 0,
        "paragraphs": 0,
        "tables": 0,
        "characters": 0,
    }

    if not file_path.is_file():
        errors.append("El archivo DOCX no existe.")
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics, "sha256": None}
    if file_path.stat().st_size < 1_000:
        errors.append("El archivo DOCX está vacío o es anormalmente pequeño.")

    names: set[str] = set()
    try:
        with ZipFile(file_path) as package:
            corrupt_part = package.testzip()
            if corrupt_part:
                errors.append(f"La parte OOXML {corrupt_part} no supera la comprobación CRC.")

            entries = [info.filename for info in package.infolist()]
            metrics["package_entries"] = len(entries)
            exact_counts = Counter(entries)
            exact_duplicates = sorted(name for name, count in exact_counts.items() if count > 1)
            if exact_duplicates:
                errors.append("El paquete OOXML contiene entradas ZIP duplicadas: " + ", ".join(exact_duplicates[:10]))

            case_groups: dict[str, set[str]] = {}
            for name in entries:
                case_groups.setdefault(name.casefold(), set()).add(name)
                unsafe_reason = _unsafe_package_name(name)
                if unsafe_reason:
                    errors.append(f"Entrada OOXML insegura o ambigua {name!r}: {unsafe_reason}.")
            case_collisions = [sorted(values) for values in case_groups.values() if len(values) > 1]
            if case_collisions:
                rendered = "; ".join(" / ".join(values) for values in case_collisions[:10])
                errors.append("El paquete OOXML contiene colisiones de nombres por mayúsculas/minúsculas: " + rendered)

            names = set(entries)
            metrics["package_parts"] = len(names)
            missing = sorted(REQUIRED_OOXML_PARTS - names)
            if missing:
                errors.append("Faltan partes OOXML obligatorias: " + ", ".join(missing))

            _validate_content_types(package, names, errors)

            for name in sorted(names):
                if name.endswith("/") or not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                try:
                    root = ET.fromstring(package.read(name))
                except ET.ParseError as exc:
                    errors.append(f"XML inválido en {name}: {exc}.")
                    continue
                if not name.endswith(".rels"):
                    continue

                relationships = root.findall(f"{{{RELATIONSHIP_NS}}}Relationship")
                relationship_ids = [str(rel.attrib.get("Id") or "").strip() for rel in relationships]
                duplicate_ids = sorted(rel_id for rel_id, count in Counter(relationship_ids).items() if rel_id and count > 1)
                if duplicate_ids:
                    errors.append(f"IDs de relación OOXML duplicados en {name}: " + ", ".join(duplicate_ids[:10]) + ".")

                for rel in relationships:
                    if str(rel.attrib.get("TargetMode", "")).casefold() == "external":
                        continue
                    target = str(rel.attrib.get("Target") or "")
                    if "\\" in target:
                        errors.append(f"Relación interna insegura o inválida en {name}: {target}.")
                        continue
                    resolved = _relationship_target(name, target)
                    if not target or not resolved or resolved == ".." or resolved.startswith("../") or resolved.startswith("/"):
                        errors.append(f"Relación interna insegura o inválida en {name}: {target}.")
                    elif resolved not in names:
                        errors.append(f"Relación rota en {name}: no existe {resolved}.")
    except BadZipFile:
        errors.append("El archivo no es un paquete DOCX/ZIP válido.")
    except OSError as exc:
        errors.append(f"No fue posible leer el archivo DOCX: {exc}.")

    document = None
    text = ""
    if not errors or names:
        try:
            document = Document(file_path)
            text = _document_text(document)
            metrics["paragraphs"] = len(document.paragraphs)
            metrics["tables"] = len(document.tables)
            metrics["characters"] = len(text.strip())
        except Exception as exc:  # python-docx exposes several package exceptions
            errors.append(f"python-docx no pudo abrir el documento: {type(exc).__name__}: {exc}.")

    if document is not None:
        if len(text.strip()) < 80:
            errors.append("El documento no contiene texto jurídico suficiente.")
        for pattern in UNRESOLVED_PATTERNS:
            matches = sorted(set(pattern.findall(text)))
            if matches:
                errors.append("Se detectaron variables o valores centinela sin resolver: " + ", ".join(map(str, matches[:10])))
        for pattern in SOFT_SENTINELS:
            if pattern.search(text):
                warnings.append(f"Se detectó un marcador editable que requiere revisión humana: {pattern.pattern}.")
        if expected_product:
            metadata = " ".join(
                str(value or "")
                for value in (
                    document.core_properties.title,
                    document.core_properties.subject,
                    document.core_properties.comments,
                )
            )
            if expected_product.casefold() not in (text + "\n" + metadata).casefold():
                errors.append(f"El documento no conserva el identificador esperado {expected_product}.")
        duplicates = _duplicate_paragraphs(document)
        if duplicates:
            warnings.append(f"Se detectaron {len(duplicates)} párrafos extensos duplicados; deben revisarse antes de aprobar.")

    sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest() if file_path.is_file() else None
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "sha256": sha256,
    }


def assert_docx_quality(path: str | Path, expected_product: str | None = None) -> dict:
    report = validate_docx(path, expected_product=expected_product)
    if not report["valid"]:
        raise ValueError("Control de calidad DOCX fallido: " + " | ".join(report["errors"]))
    return report
