from __future__ import annotations

"""Pulido final de presentación de CO-TR-001 sin alterar su lógica jurídica."""

from copy import deepcopy


_UNVERIFIED_ROLES = {
    "calidad por acreditar",
    "calidad por verificar",
    "por verificar",
}


def _polish_report_paragraphs(spec: dict) -> None:
    if str(spec.get("kind") or "") != "sast_report":
        return
    for section in spec.get("sections") or []:
        if not isinstance(section, dict):
            continue
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list):
            continue
        section["paragraphs"] = [
            str(paragraph).replace(
                "la evidencia de señalización, Cuando el equipo",
                "la evidencia de señalización. Cuando el equipo",
            )
            for paragraph in paragraphs
        ]


def _omit_unverified_signature_role(spec: dict) -> None:
    """No imprime una calidad no acreditada dentro del bloque de suscripción.

    La calidad permanece visible como dato pendiente en la identificación del caso.
    Además de mejorar la precisión jurídica, evita que el párrafo terminal del
    builder se desplace por sí solo a una página adicional en la inspección SAST.
    """
    for section in spec.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_type = str(section.get("_type") or section.get("type") or "")
        if section_type != "signature":
            continue
        for party in section.get("parties") or []:
            if not isinstance(party, dict):
                continue
            role = str(party.get("role") or "").strip()
            if role.casefold() in _UNVERIFIED_ROLES:
                party["role"] = ""


def finalize_sast_release_polish(specs: list[dict]) -> list[dict]:
    polished = deepcopy(specs)
    for spec in polished:
        _polish_report_paragraphs(spec)
        _omit_unverified_signature_role(spec)
    return polished
