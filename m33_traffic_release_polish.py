from __future__ import annotations

"""Pulido de radicabilidad y presentación para CO-TR-002.

Evita que una pieza condicionada muestre bloque de firma cuando todavía falta el
acto mínimo que permitiría individualizar jurídicamente la actuación.
"""

from copy import deepcopy
from datetime import date


def _parsed_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _is_verified_act(value) -> bool:
    text = str(value or "").strip().casefold()
    if not text:
        return False
    return not any(token in text for token in ("por obtener", "por verificar", "pendiente", "no confirmado", "aparentemente"))


def _remove_signature(spec: dict) -> None:
    spec["sections"] = [
        section for section in (spec.get("sections") or [])
        if not (
            isinstance(section, dict)
            and str(section.get("_type") or section.get("type") or "").casefold() == "signature"
        )
    ]


def _prepend_blocking_status(spec: dict, message: str) -> None:
    sections = list(spec.get("sections") or [])
    if sections and isinstance(sections[0], dict):
        paragraphs = list(sections[0].get("paragraphs") or [])
        if not any("NO RADICABLE TODAVÍA" in str(item) for item in paragraphs):
            paragraphs.insert(0, message)
            sections[0]["paragraphs"] = paragraphs
    spec["sections"] = sections


def finalize_traffic_release_polish(specs: list[dict], answers: dict) -> list[dict]:
    polished = deepcopy(specs)
    sanction_act = answers.get("sanction_resolution")
    sanction_date = _parsed_date(answers.get("sanction_date"))
    revocation_ready = _is_verified_act(sanction_act) and sanction_date is not None

    registry_act = answers.get("registry_source_act")
    registry_ready = _is_verified_act(registry_act)

    for spec in polished:
        kind = str(spec.get("kind") or "")
        if kind == "traffic_revocation_request" and not revocation_ready:
            _remove_signature(spec)
        elif kind == "traffic_registry_correction" and not registry_ready:
            _prepend_blocking_status(
                spec,
                "NO RADICABLE TODAVÍA — falta individualizar y acreditar el acto fuente que ordena o soporta la corrección registral.",
            )
            _remove_signature(spec)
    return polished
