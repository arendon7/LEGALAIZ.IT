from __future__ import annotations

"""Ajuste de paginación final CO-CD-004 validado contra render LibreOffice.

No modifica contenido jurídico ni cálculos. El anexo económico del acuerdo ya
queda naturalmente separado por el flujo del contenido; conservar un salto
forzado después de la ampliación de cláusulas produce una página completamente
vacía en el renderer final.
"""

from copy import deepcopy


def finalize_debt_layout_polish(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    if (result or {}).get("risk") == "red":
        return specs

    polished = deepcopy(specs)
    for spec in polished:
        if spec.get("kind") != "payment_agreement" or not spec.get("internal_controls_externalized"):
            continue
        for section in spec.get("sections") or []:
            if str(section.get("heading") or "").startswith("ANEXO ECONÓMICO"):
                section["page_break_before"] = False
    return polished
