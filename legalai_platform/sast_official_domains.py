from __future__ import annotations

"""Allowlist sectorial M33.4 para fuentes oficiales SAST."""

from legalai_platform.legal_source_registry import OFFICIAL_DOMAINS


SAST_OFFICIAL_DOMAINS = {
    "inm.gov.co",
    "www.inm.gov.co",
    "mintransporte.gov.co",
    "www.mintransporte.gov.co",
    "ansv.gov.co",
    "www.ansv.gov.co",
}

OFFICIAL_DOMAINS.update(SAST_OFFICIAL_DOMAINS)


__all__ = ["SAST_OFFICIAL_DOMAINS"]
