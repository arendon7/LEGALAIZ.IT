from __future__ import annotations

"""Compatibilidad final de CO-TR-001 después de la profundización M33.0."""

from copy import deepcopy


def finalize_sast_compat_polish(specs: list[dict]) -> list[dict]:
    """Retira la guía histórica redundante sin alterar las siete piezas M33.0.

    `sast_route_guide` duplicaba seguimiento, escalamiento y cierre y conservaba
    lenguaje interno de plataforma. Su contenido sustantivo ya está absorbido por
    `sast_followup` y `sast_package`.
    """
    polished: list[dict] = []
    for spec in deepcopy(specs):
        kind = str(spec.get("kind") or "")
        title = str(spec.get("title") or "").casefold()
        if kind == "sast_route_guide" or (
            "guía de verificación" in title and "escalamiento" in title
        ):
            continue
        polished.append(spec)
    return polished
