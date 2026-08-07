from __future__ import annotations

"""Shim de compatibilidad para los modelos jurídicos v2.15.

La aplicación histórica añade ``legalai_runtime_modules`` al ``sys.path`` desde
``run.py``. Algunas herramientas de QA, scripts y pruebas importan
``expanded_documents`` directamente y, por tanto, no ejecutan ese bootstrap.

Este módulo mantiene el contrato de importación histórico
``import complete_legal_models_v215 as v215`` sin duplicar implementación: toda la
lógica permanece en ``legalai_runtime_modules.complete_legal_models_v215``.
"""

from legalai_runtime_modules.complete_legal_models_v215 import *  # noqa: F401,F403
from legalai_runtime_modules.complete_legal_models_v215 import VERSION
