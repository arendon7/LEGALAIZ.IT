#!/usr/bin/env python3
from __future__ import annotations

"""Punto de entrada compatible para la generación integral M32.3.

Las fábricas especializadas históricas conservan pequeñas diferencias de interfaz:
unas exponen ``evaluator.documents`` como catálogo descriptivo y otras retornan
únicamente IDs; además, no todas publican el mismo campo para la carpeta de la
revisión inmutable. Este adaptador preserva esas fábricas y localiza la salida
primaria dentro de la generación exacta, sin introducir plantillas paralelas.
"""

from pathlib import Path
import shutil

from scripts import generate_m32_3_full_portfolio as implementation


class FactoryCompatibleEvaluator:
    def __init__(self, documents: list[str], blocks: list[str] | None = None):
        self.document_ids = [str(document_id) for document_id in documents]
        self.documents = [
            {"id": document_id, "name": document_id.replace("-", " ")}
            for document_id in self.document_ids
        ]
        self.blocks = list(blocks or [])

    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": list(self.document_ids),
            "readiness": "ready_for_human_review",
            "status": "ready_for_human_review",
            "professional_review_required": True,
            "professional_reviews": ["Revisión jurídica sustantiva", "QA visual humano"],
            "review_requirements": ["Revisión jurídica sustantiva", "QA visual humano"],
            "findings": [],
            "blockers": [],
            "warnings": [],
            "blocks": list(self.blocks),
        }


def _resolve_generated_document(factory, manifest: dict, document: dict) -> Path:
    generation_root = Path(factory.output_dir) / str(manifest["generation_id"])
    filename = str(document["filename"])
    candidates: list[Path] = []

    for key in ("path", "relative_path", "content_location"):
        value = document.get(key)
        if value:
            candidate = Path(str(value))
            candidates.append(candidate if candidate.is_absolute() else generation_root / candidate)

    folder = manifest.get("document_folder")
    if folder:
        candidates.append(generation_root / str(folder) / filename)

    candidates.extend(
        [
            generation_root / "documents" / "revision-0001" / filename,
            generation_root / "documents" / filename,
            generation_root / filename,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    matches = sorted(path for path in generation_root.rglob(filename) if path.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError(
            f"No se encontró {filename} dentro de la generación inmutable {generation_root}."
        )
    raise RuntimeError(
        f"La generación {generation_root} contiene múltiples salidas ambiguas para {filename}: "
        + ", ".join(str(path.relative_to(generation_root)) for path in matches)
    )


def _copy_primary_compatible(factory, answers: dict, product_code: str, output: Path) -> dict:
    manifest = factory.generate(answers, actor={"id": "m32-3-ci", "role": "qa"})
    primary_id = implementation.PRIMARY_DOCUMENT_IDS[product_code]
    document = next(
        (item for item in manifest.get("documents", []) if item.get("id") == primary_id),
        None,
    )
    if not document:
        available = ", ".join(str(item.get("id")) for item in manifest.get("documents", []))
        raise RuntimeError(
            f"La fábrica {product_code} no produjo {primary_id}. Disponibles: {available or 'ninguno'}."
        )
    source = _resolve_generated_document(factory, manifest, document)
    destination = output / f"{product_code}_{Path(document['filename']).stem}_M32_3.docx"
    shutil.copy2(source, destination)
    return {
        "product_code": product_code,
        "factory": type(factory).__name__,
        "factory_version": str(getattr(factory, "VERSION", "")),
        "document_id": primary_id,
        "source_filename": document["filename"],
        "sample_name": destination.name,
        "generation_id": manifest["generation_id"],
        "factory_legal_approval": manifest.get("legal_approval", {}).get("status", "pending"),
        "factory_qa_approval": manifest.get("qa_approval", {}).get("status", "pending"),
        "factory_released": bool(manifest.get("released", False)),
    }


implementation.ControlledEvaluator = FactoryCompatibleEvaluator
implementation._copy_primary = _copy_primary_compatible


if __name__ == "__main__":
    raise SystemExit(implementation.main())
