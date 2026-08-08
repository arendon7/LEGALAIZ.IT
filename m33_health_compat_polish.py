from __future__ import annotations

"""Pulido de compatibilidad para CO-SA-001 después de la finalización jurídica."""

from copy import deepcopy


def finalize_health_compat_polish(specs: list[dict]) -> list[dict]:
    polished: list[dict] = []
    for spec in deepcopy(specs):
        title = str(spec.get("title") or "")
        kind = str(spec.get("kind") or "")

        # El compositor histórico agrega una pieza redundante de bloqueo en casos
        # rojos. La criticidad ya queda preservada como gobierno interno en cada
        # una de las siete piezas finales, por lo que no se imprime un octavo
        # documento con lenguaje de plataforma.
        if "bloqueo y escalamiento profesional" in title.casefold() and kind not in {
            "health_diagnostic", "health_petition", "health_reiteration",
            "health_supersalud", "health_history_request", "health_evidence",
            "health_calendar",
        }:
            continue

        if kind == "health_supersalud":
            spec["title"] = "PQRD y solicitud de intervención ante Supersalud"
        polished.append(spec)
    return polished
