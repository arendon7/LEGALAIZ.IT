from __future__ import annotations

"""Extensión sectorial explícita del allowlist M33.4 para fuentes primarias de salud.

Se carga antes de ``health_legal_source_pack``. No autoriza dominios genéricos ni
fuentes secundarias: únicamente autoridades colombianas competentes utilizadas por
CO-SA-001.
"""

from legalai_platform.legal_source_registry import OFFICIAL_DOMAINS


HEALTH_OFFICIAL_DOMAINS = {
    "www.supersalud.gov.co",
    "supersalud.gov.co",
    "normograma.supersalud.gov.co",
    "www.corteconstitucional.gov.co",
    "corteconstitucional.gov.co",
    "www.minsalud.gov.co",
    "minsalud.gov.co",
    "www2.minsalud.gov.co",
}

OFFICIAL_DOMAINS.update(HEALTH_OFFICIAL_DOMAINS)


__all__ = ["HEALTH_OFFICIAL_DOMAINS"]
