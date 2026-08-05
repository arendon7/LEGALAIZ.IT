from __future__ import annotations

"""Compuerta transversal de calidad para todos los DOCX de LegalAIZ.it.

La compuerta valida integridad OOXML, apertura con python-docx y estructura visual
antes de devolver un archivo al flujo de generación. También conserva un manifiesto
lateral auditable. El preflight no constituye aprobación jurídica ni QA humana.
"""

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


def enforce_document_release_gate(
    path: str | Path,
    *,
    expected_product: str | None = None,
    metadata=None,
    write_manifest: bool = True,
) -> dict:
    """Valida un DOCX y registra una evidencia inmutable de preflight.

    Los errores técnicos bloquean la generación. Las advertencias permanecen en el
    manifiesto para revisión jurídica y QA. La aprobación dual siempre queda pendiente.
    """
    file_path = Path(path)
    product_code = (expected_product or infer_product_code(file_path, metadata)).upper() if (expected_product or infer_product_code(file_path, metadata)) else None
    if product_code and product_code not in CANONICAL_PRODUCTS:
        raise ValueError(f"Código de producto no canónico para la compuerta documental: {product_code}.")

    quality_report = assert_docx_quality(file_path, expected_product=product_code)
    visual_report = assert_visual_structure(file_path, expected_product=product_code)
    warnings = list(dict.fromkeys(
        list(quality_report.get("warnings") or []) + list(visual_report.get("warnings") or [])
    ))
    manifest = {
        "manifest_version": "M32.2",
        "generated_at": _now_bogota(),
        "document": file_path.name,
        "product_code": product_code,
        "sha256": quality_report.get("sha256"),
        "release_status": "preflight_passed_pending_dual_approval",
        "quality": quality_report,
        "visual_preflight": visual_report,
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
            result = current(*args, **kwargs)
            path = kwargs.get("path") or (args[0] if args else result)
            metadata = kwargs.get("metadata")
            if metadata is None and len(args) >= 4:
                metadata = args[3]
            enforce_document_release_gate(path, metadata=metadata)
            return result

        guarded_build_docx._legalaiz_release_gate = True
        guarded_build_docx._legalaiz_original = current
        docx_builder.build_docx = guarded_build_docx
        return True
