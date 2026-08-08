from __future__ import annotations

"""Pulido de compatibilidad para CO-SA-001 después de la finalización jurídica."""

from copy import deepcopy


HEALTH_KINDS = {
    "health_diagnostic", "health_petition", "health_reiteration",
    "health_supersalud", "health_history_request", "health_evidence",
    "health_calendar",
}


def _explicit_history_custodian(answers: dict) -> str:
    """No presume que un dispensador o gestor sea custodio de la historia clínica."""
    for key in (
        "history_custodian",
        "clinical_history_custodian",
        "ips_name",
        "treating_ips_name",
        "treating_provider_name",
    ):
        value = str((answers or {}).get(key) or "").strip()
        if value:
            return value
    return "Prestador/custodio por verificar"


def _polish_petition_language(spec: dict) -> None:
    for section in spec.get("sections") or []:
        if not isinstance(section, dict) or section.get("heading") != "ASUNTO Y PRIORIDAD":
            continue
        paragraphs = list(section.get("paragraphs") or [])
        if paragraphs:
            paragraphs[0] = str(paragraphs[0]).replace(
                "debe validarla y aplicar ",
                "debe validarla y aplicar la regla sectorial correspondiente: ",
                1,
            )
            section["paragraphs"] = paragraphs
        return


def _polish_history_custodian(spec: dict, answers: dict) -> None:
    custodian = _explicit_history_custodian(answers)
    for section in spec.get("sections") or []:
        if not isinstance(section, dict) or section.get("heading") != "I. LEGITIMACIÓN":
            continue
        table = section.get("table")
        if not isinstance(table, list):
            return
        for index, row in enumerate(table):
            if not isinstance(row, list) or len(row) < 2:
                continue
            if str(row[0] or "").strip().casefold() == "prestador/custodio":
                updated = list(row)
                updated[1] = custodian
                table[index] = updated
                return


def finalize_health_compat_polish(specs: list[dict], answers: dict | None = None) -> list[dict]:
    polished: list[dict] = []
    for spec in deepcopy(specs):
        title = str(spec.get("title") or "")
        kind = str(spec.get("kind") or "")

        # El compositor histórico agrega una pieza redundante de bloqueo en casos
        # rojos. La criticidad ya queda preservada como gobierno interno en cada
        # una de las siete piezas finales, por lo que no se imprime un octavo
        # documento con lenguaje de plataforma.
        if "bloqueo y escalamiento profesional" in title.casefold() and kind not in HEALTH_KINDS:
            continue

        if kind == "health_supersalud":
            spec["title"] = "PQRD y solicitud de intervención ante Supersalud"
        elif kind == "health_petition":
            _polish_petition_language(spec)
        elif kind == "health_history_request":
            _polish_history_custodian(spec, answers or {})
        polished.append(spec)
    return polished
