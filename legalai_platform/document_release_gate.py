from __future__ import annotations

"""Compuerta transversal de calidad para todos los DOCX de LegalAIZ.it.

La compuerta valida integridad OOXML, apertura con python-docx y estructura visual
antes de devolver un archivo al flujo de generación. También conserva un manifiesto
lateral auditable. El preflight no constituye aprobación jurídica ni QA humana.
"""

from copy import deepcopy
from datetime import datetime
from functools import wraps
import json
import os
from pathlib import Path
import re
from threading import RLock
from zoneinfo import ZoneInfo

from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure


CANONICAL_PRODUCTS = frozenset({
    "CO-TR-001",
    "CO-TR-002",
    "CO-LA-001",
    "CO-LA-002",
    "CO-AR-001",
    "CO-EM-003",
    "CO-EM-004",
    "CO-SA-001",
    "CO-CD-001",
    "CO-CD-003",
    "CO-CD-004",
})
M32_2_PRODUCTS = frozenset({
    "CO-TR-001",
    "CO-TR-002",
    "CO-SA-001",
    "CO-CD-001",
    "CO-CD-003",
    "CO-CD-004",
})
PRODUCT_PATTERN = re.compile(r"CO-(?:TR|LA|AR|EM|SA|CD)-\d{3}", re.I)
_GATE_LOCK = RLock()


def _now_bogota() -> str:
    return datetime.now(ZoneInfo("America/Bogota")).isoformat(timespec="seconds")


def _metadata_text(metadata) -> str:
    values: list[str] = []
    for row in metadata or []:
        if isinstance(row, (list, tuple)):
            values.extend(str(value or "") for value in row)
        else:
            values.append(str(row or ""))
    return " ".join(values)


def infer_product_code(path: str | Path, metadata=None) -> str | None:
    haystack = f"{Path(path).name} {_metadata_text(metadata)}"
    match = PRODUCT_PATTERN.search(haystack)
    if not match:
        return None
    code = match.group(0).upper()
    return code if code in CANONICAL_PRODUCTS else None


def manifest_path_for(path: str | Path) -> Path:
    file_path = Path(path)
    return file_path.with_suffix(file_path.suffix + ".quality.json")


def _zero_rate(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return float(value) == 0.0
    text = str(value or "").strip().casefold()
    text = text.replace("e.a.", "").replace("e.a", "").replace("%", "").replace(",", ".").strip()
    try:
        return float(text) == 0.0
    except ValueError:
        return False


def normalize_semantic_sections(product_code: str | None, sections) -> tuple[list[dict], list[dict]]:
    """Evita que valores técnicos por defecto se lean como conclusiones jurídicas.

    En CO-CD-004, tres tasas en cero junto con una modalidad que declara que los
    intereses no fueron calculados significan ausencia de parámetro, no una tasa
    sustantiva de 0 %. La tabla se corrige antes de construir el DOCX y la decisión
    queda registrada en el manifiesto de calidad.
    """
    normalized = deepcopy(list(sections or []))
    adjustments: list[dict] = []
    if product_code != "CO-CD-004":
        return normalized, adjustments

    rate_labels = {"tasa equivalente e.a.", "ibc vigente", "límite de referencia"}
    for section in normalized:
        heading = str(section.get("heading") or "").casefold()
        table = section.get("table")
        if "saldo e intereses" not in heading or not isinstance(table, list):
            continue
        modality = ""
        rates: list[tuple[int, str, object]] = []
        for index, row in enumerate(table):
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            label = str(row[0]).strip()
            key = label.casefold()
            if key == "modalidad":
                modality = str(row[1] or "").casefold()
            elif key in rate_labels:
                rates.append((index, label, row[1]))
        if not rates:
            continue
        unavailable = "no calculad" in modality or "pendiente" in modality
        all_zero = len(rates) == len(rate_labels) and all(_zero_rate(value) for _, _, value in rates)
        if not (unavailable and all_zero):
            continue
        for index, label, original in rates:
            row = list(table[index])
            row[1] = "Pendiente de verificación"
            table[index] = tuple(row)
            adjustments.append({
                "product_code": product_code,
                "section": section.get("heading"),
                "field": label,
                "original_value": str(original),
                "normalized_value": "Pendiente de verificación",
                "reason": "La modalidad declara que los intereses no fueron calculados; cero era un valor técnico por defecto.",
            })
        break
    return normalized, adjustments


def _existing_semantic_adjustments(path: Path) -> list[dict]:
    target = manifest_path_for(path)
    if not target.is_file():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    value = payload.get("semantic_adjustments")
    return list(value) if isinstance(value, list) else []


def enforce_document_release_gate(
    path: str | Path,
    *,
    expected_product: str | None = None,
    metadata=None,
    write_manifest: bool = True,
    semantic_adjustments: list[dict] | None = None,
) -> dict:
    """Valida un DOCX y registra una evidencia inmutable de preflight.

    Los errores técnicos bloquean la generación. Las advertencias permanecen en el
    manifiesto para revisión jurídica y QA. La aprobación dual siempre queda pendiente.
    """
    file_path = Path(path)
    inferred = expected_product or infer_product_code(file_path, metadata)
    product_code = inferred.upper() if inferred else None
    if product_code and product_code not in CANONICAL_PRODUCTS:
        raise ValueError(f"Código de producto no canónico para la compuerta documental: {product_code}.")

    quality_report = assert_docx_quality(file_path, expected_product=product_code)
    visual_report = assert_visual_structure(file_path, expected_product=product_code)
    warnings = list(dict.fromkeys(
        list(quality_report.get("warnings") or []) + list(visual_report.get("warnings") or [])
    ))
    adjustments = list(semantic_adjustments or _existing_semantic_adjustments(file_path))
    manifest = {
        "manifest_version": "M32.3",
        "generated_at": _now_bogota(),
        "document": file_path.name,
        "product_code": product_code,
        "sha256": quality_report.get("sha256"),
        "release_status": "preflight_passed_pending_dual_approval",
        "quality": quality_report,
        "visual_preflight": visual_report,
        "semantic_adjustments": adjustments,
        "warnings": warnings,
        "approval_state": {
            "legal": "pending",
            "qa": "pending",
        },
        "requires_human_visual_review": True,
        "review_statement": (
            "La integridad técnica y el preflight estructural no sustituyen la revisión "
            "jurídica del caso ni la inspección humana página por página."
        ),
    }
    if write_manifest:
        target = manifest_path_for(file_path)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
    return manifest


def install_docx_release_gate() -> bool:
    """Instala una envoltura idempotente sobre docx_builder.build_docx."""
    if str(os.environ.get("LEGAL_DISABLE_DOCX_RELEASE_GATE", "")).strip().lower() in {"1", "true", "yes"}:
        return False

    import docx_builder

    with _GATE_LOCK:
        current = docx_builder.build_docx
        if getattr(current, "_legalaiz_release_gate", False):
            return True

        @wraps(current)
        def guarded_build_docx(*args, **kwargs):
            call_args = list(args)
            call_kwargs = dict(kwargs)
            path = call_kwargs.get("path") or (call_args[0] if call_args else None)
            metadata = call_kwargs.get("metadata")
            if metadata is None and len(call_args) >= 4:
                metadata = call_args[3]
            product_code = infer_product_code(path or "document.docx", metadata)
            sections = call_kwargs.get("sections")
            if sections is None and len(call_args) >= 5:
                sections = call_args[4]
            normalized_sections, adjustments = normalize_semantic_sections(product_code, sections)
            if sections is not None:
                if "sections" in call_kwargs:
                    call_kwargs["sections"] = normalized_sections
                elif len(call_args) >= 5:
                    call_args[4] = normalized_sections
            result = current(*call_args, **call_kwargs)
            final_path = path or result
            enforce_document_release_gate(
                final_path,
                metadata=metadata,
                semantic_adjustments=adjustments,
            )
            return result

        guarded_build_docx._legalaiz_release_gate = True
        guarded_build_docx._legalaiz_original = current
        docx_builder.build_docx = guarded_build_docx
        return True
