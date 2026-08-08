from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "si", "sí", "on"}


PROJECT_NAME = "LegalAIZ.it"
MILESTONE = "M33.1"
VERSION = "5.1.2"
BUILD_ID = "M33-1-DESPLIEGUE-RENDER-ENDURECIDO-2026-08-08"
RELEASE_ID = "M33-1-RENDER-HARDENING-5.1.2-2026-08-08"
RELEASE_NAME = "M33.1 — despliegue público demostrativo endurecido"
RELEASE_DATE = "2026-08-08"
BASE_RELEASE = "M33.0 v5.1.1"
PUBLIC_DEMO_AVAILABLE = True
PUBLIC_DEMO_MODE = _flag("LEGAL_PUBLIC_DEMO_MODE", False)
RELEASE_CHANNEL = "public_demo_hardened" if PUBLIC_DEMO_MODE else "controlled_demo_case_workflows"
PRODUCTION_AUTHORIZED = PUBLIC_DEMO_MODE
PUBLIC_PRODUCTION_READY = PUBLIC_DEMO_MODE
REAL_PRODUCTION_AUTHORIZED = False
REAL_PAYMENTS_AUTHORIZED = False
SYNTHETIC_DATA_ONLY = True
POSTGRES_ADAPTER_IMPLEMENTED = True
POSTGRES_EXTERNAL_CERTIFIED = False
POSTGRES_BACKUP_RESTORE_CERTIFIED = False
POSTGRES_MIGRATION_CERTIFIED = False
CATALOG_RATIFICATION_MODEL = "historical_multi_stage_single_responsible"
DOCUMENT_RELEASE_APPROVAL_MODEL = "distinct_legal_and_qa_same_revision"
