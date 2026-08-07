from __future__ import annotations

"""Runtime M33.0 completo hasta la tercera oleada."""

from m33_procedural_runtime import _finalize_spec
from m33_wave3_composition import WAVE3_CODES, document_specs_m33_wave3


def document_specs_m33_all(case_id, code, answers, result, product, generated_at, question_rows):
    specs = document_specs_m33_wave3(case_id, code, answers, result, product, generated_at, question_rows)
    if code not in WAVE3_CODES:
        return specs
    return [_finalize_spec(code, answers, spec) for spec in specs]
