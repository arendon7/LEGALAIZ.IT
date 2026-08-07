from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "si", "sí", "on"}


PROJECT_NAME = "LegalAIZ.it"
MILESTONE = "M33.0"
VERSION = "5.1.1"
BUILD_ID = "M33-0-INTEGRACION-DEMO-PUBLICA-M32-9-2026-08-07"
RELEASE_ID = "M33-0-DEMO-PUBLICA-INTEGRADA-5.1.1-2026-08-07"
RELEASE_NAME = "M33.0 — M32.9 con producción demostrativa pública integral"
RELEASE_DATE = "2026-08-07"
BASE_RELEASE = "M32.9 + M31.9 v5.1.0 aprobada"
PUBLIC_DEMO_AVAILABLE = True
PUBLIC_DEMO_MODE = _flag("LEGAL_PUBLIC_DEMO_MODE", False)
RELEASE_CHANNEL = "public_demo_final" if PUBLIC_DEMO_MODE else "controlled_demo_case_workflows"
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
