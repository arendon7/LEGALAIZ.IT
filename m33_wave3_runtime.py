from __future__ import annotations

"""Runtime M33.0 completo hasta la tercera oleada."""

from m33_consumer_legal_finalize import finalize_consumer_specs
from m33_consumer_release_polish import finalize_consumer_release_polish
from m33_debt_layout_polish import finalize_debt_layout_polish
from m33_debt_legal_finalize import finalize_debt_specs
from m33_debt_release_polish import finalize_debt_release_polish
from m33_depth_polish import finalize_depth_polish
from m33_habeas_legal_finalize import finalize_habeas_specs
from m33_health_compat_polish import finalize_health_compat_polish
from m33_health_legal_finalize import finalize_health_specs
from m33_labor_presentation_finalize import finalize_labor_presentation
from m33_labor_procedural_finalize import finalize_labor_specs
from m33_procedural_runtime import _finalize_spec
from m33_sast_compat_polish import finalize_sast_compat_polish
from m33_sast_legal_finalize import finalize_sast_specs
from m33_sast_release_polish import finalize_sast_release_polish
from m33_traffic_legal_finalize import finalize_traffic_specs
from m33_traffic_release_polish import finalize_traffic_release_polish
from m33_wave3_composition import WAVE3_CODES, document_specs_m33_wave3


_HABEAS_CLIENT_SUBTITLE = (
    "Hábeas data financiero · documento sujeto a verificación de hechos y soportes"
)


def _polish_habeas_client_presentation(specs: list[dict]) -> list[dict]:
    """Retira metadatos editoriales del subtítulo sin tocar la gobernanza interna."""
    for spec in specs:
        if spec.get("internal_controls_externalized"):
            spec["subtitle"] = _HABEAS_CLIENT_SUBTITLE
    return specs


def document_specs_m33_all(case_id, code, answers, result, product, generated_at, question_rows):
    specs = document_specs_m33_wave3(case_id, code, answers, result, product, generated_at, question_rows)
    if code == "CO-LA-001":
        labor_specs = finalize_labor_specs(specs, answers, result)
        return finalize_labor_presentation(labor_specs, answers, result)
    if code == "CO-CD-001":
        habeas_specs = finalize_habeas_specs(specs, answers, result)
        return _polish_habeas_client_presentation(habeas_specs)
    if code == "CO-CD-003":
        consumer_specs = finalize_consumer_specs(specs, answers, result)
        consumer_specs = finalize_consumer_release_polish(consumer_specs)
        return finalize_depth_polish(code, consumer_specs, answers, result)
    if code == "CO-CD-004":
        debt_specs = finalize_debt_specs(specs, answers, result)
        debt_specs = finalize_debt_release_polish(debt_specs, answers, result)
        return finalize_debt_layout_polish(debt_specs, answers, result)
    if code == "CO-SA-001":
        health_specs = finalize_health_specs(specs, answers, result)
        health_specs = finalize_health_compat_polish(health_specs, answers)
        return finalize_depth_polish(code, health_specs, answers, result)
    if code == "CO-TR-001":
        sast_specs = finalize_sast_specs(specs, answers, result)
        sast_specs = finalize_sast_compat_polish(sast_specs)
        return finalize_sast_release_polish(sast_specs)
    if code == "CO-TR-002":
        traffic_specs = finalize_traffic_specs(specs, answers, result)
        traffic_specs = finalize_traffic_release_polish(traffic_specs, answers)
        return finalize_depth_polish(code, traffic_specs, answers, result)
    if code not in WAVE3_CODES:
        return specs
    return [_finalize_spec(code, answers, spec) for spec in specs]
