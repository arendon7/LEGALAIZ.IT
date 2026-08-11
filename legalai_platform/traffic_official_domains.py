from __future__ import annotations

"""Allowlist sectorial M33.4 para fuentes primarias de tránsito.

La ampliación es deliberadamente estrecha: Corte Constitucional y Ministerio de
Transporte. SUIN-Juriscol ya pertenece al registro central. No se habilitan blogs,
portales comerciales ni agregadores jurídicos.
"""

from legalai_platform.legal_source_registry import OFFICIAL_DOMAINS


TRAFFIC_OFFICIAL_DOMAINS = {
    "www.corteconstitucional.gov.co",
    "corteconstitucional.gov.co",
    "www.mintransporte.gov.co",
    "mintransporte.gov.co",
}

OFFICIAL_DOMAINS.update(TRAFFIC_OFFICIAL_DOMAINS)


__all__ = ["TRAFFIC_OFFICIAL_DOMAINS"]
