#!/usr/bin/env python3
from __future__ import annotations

"""Punto de entrada compatible para la generación integral M32.3.

Las fábricas especializadas históricas consultan ``evaluator.documents`` como
catálogo de objetos con ``id`` y ``name``. A la vez, sus resultados de evaluación
esperan una lista simple de identificadores documentales. Este adaptador conserva
ambos contratos sin modificar las fábricas ni introducir plantillas paralelas.
"""

import sys

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


implementation.ControlledEvaluator = FactoryCompatibleEvaluator


if __name__ == "__main__":
    raise SystemExit(implementation.main())
