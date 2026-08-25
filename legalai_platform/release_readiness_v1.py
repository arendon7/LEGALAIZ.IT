from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping

from legalai_platform import release_metadata
from legalai_platform.database import runtime_status


SCHEMA = "legalai_v1_release_readiness_v1"
SCHEMA_VERSION = 1


def _flag(values: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = str(values.get(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "si", "sí", "on"}


@dataclass(frozen=True)
class ReadinessCheck:
    key: str
    category: str
    passed: bool
    blocking: bool = True
    evidence: str = "runtime"

    def public(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "passed": bool(self.passed),
            "blocking": bool(self.blocking),
            "evidence": self.evidence,
        }


class ReleaseReadinessContractError(RuntimeError):
    pass


class ReleaseReadinessV1:
    """Fail-closed evidence gate for a future real-production release.

    This center is deliberately read-only. It evaluates repository/runtime evidence,
    but it never flips release flags, creates attestations or authorizes payments.
    """

    def __init__(
        self,
        root: Path,
        settings,
        infra,
        products: Mapping[str, Any],
        interviews: Mapping[str, Any],
        *,
        env: Mapping[str, str] | None = None,
        release_flags: Mapping[str, bool] | None = None,
        contract_path: Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.settings = settings
        self.infra = infra
        self.products = products
        self.interviews = interviews
        self.env = env if env is not None else os.environ
        self.release_flags = dict(release_flags or {
            "public_demo_mode": bool(release_metadata.PUBLIC_DEMO_MODE),
            "real_production_authorized": bool(release_metadata.REAL_PRODUCTION_AUTHORIZED),
            "real_payments_authorized": bool(release_metadata.REAL_PAYMENTS_AUTHORIZED),
            "synthetic_data_only": bool(release_metadata.SYNTHETIC_DATA_ONLY),
        })
        self.contract_path = contract_path or self.root / "config" / "release" / "v1_readiness_contract.json"
        self.contract = self._load_contract()

    def _load_contract(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.contract_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReleaseReadinessContractError("No fue posible cargar el contrato V1 de readiness.") from exc
        if payload.get("schema") != "legalai_v1_release_readiness_contract_v1":
            raise ReleaseReadinessContractError("Schema de readiness V1 inválido.")
        if int(payload.get("schema_version") or 0) != SCHEMA_VERSION:
            raise ReleaseReadinessContractError("Versión de contrato V1 no soportada.")
        required = payload.get("required_runtime_markers")
        if not isinstance(required, list) or not required or len(required) != len(set(required)):
            raise ReleaseReadinessContractError("Los marcadores de runtime V1 son inválidos o duplicados.")
        artifacts = payload.get("required_repository_evidence")
        if not isinstance(artifacts, dict) or not artifacts:
            raise ReleaseReadinessContractError("La evidencia de repositorio V1 no puede estar vacía.")
        attestations = payload.get("external_attestations")
        if not isinstance(attestations, dict) or not attestations:
            raise ReleaseReadinessContractError("Las atestaciones externas V1 no pueden estar vacías.")
        return payload

    def _runtime_markers_ok(self) -> bool:
        run_path = self.root / "run.py"
        if not run_path.is_file():
            return False
        source = run_path.read_text(encoding="utf-8")
        required = [str(item) for item in self.contract["required_runtime_markers"]]
        return all(marker in source for marker in required) and "http_handler_m37_3 import Handler" in source

    def _portfolio_ok(self) -> bool:
        floor = self.contract["portfolio_floor"]
        product_count = len(self.products)
        question_count = sum(len((item or {}).get("questions") or []) for item in self.interviews.values())
        return product_count >= int(floor["products"]) and question_count >= int(floor["questions"])

    def _repository_evidence(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        for key, rel in self.contract["required_repository_evidence"].items():
            path = self.root / str(rel)
            if not path.is_file():
                missing.append(str(key))
        return not missing, missing

    def _attested(self, key: str) -> bool:
        env_name = str(self.contract["external_attestations"].get(key) or "")
        return bool(env_name and _flag(self.env, env_name, False))

    @staticmethod
    def _doctor_map(doctor: Mapping[str, Any]) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for item in doctor.get("checks") or []:
            if isinstance(item, Mapping) and item.get("key"):
                result[str(item["key"])] = bool(item.get("passed"))
        return result

    def _checks(self, con) -> tuple[list[ReadinessCheck], dict[str, Any]]:
        doctor = self.infra.doctor(con)
        doctor_map = self._doctor_map(doctor)
        db = runtime_status(self.env)
        repo_ok, repo_missing = self._repository_evidence()
        durable_backends = {str(x) for x in self.contract.get("durable_object_storage_backends") or []}
        storage_backend = str(getattr(self.settings, "object_storage_backend", "") or "")

        checks = [
            ReadinessCheck("stack_m34_m37_complete", "application", self._runtime_markers_ok(), evidence="repository"),
            ReadinessCheck("portfolio_floor_preserved", "application", self._portfolio_ok(), evidence="repository"),
            ReadinessCheck("production_profile", "environment", str(getattr(self.settings, "profile", "")) == "production"),
            ReadinessCheck("public_demo_disabled", "environment", not bool(self.release_flags.get("public_demo_mode"))),
            ReadinessCheck("synthetic_data_boundary_removed", "governance", not bool(self.release_flags.get("synthetic_data_only")), evidence="release_metadata"),
            ReadinessCheck("managed_master_key", "security", doctor_map.get("master_key", False)),
            ReadinessCheck("secure_cookies", "security", doctor_map.get("secure_cookies", False)),
            ReadinessCheck("public_https", "security", doctor_map.get("public_https", False)),
            ReadinessCheck("origin_check", "security", bool(getattr(self.settings, "require_origin_check", False))),
            ReadinessCheck("privileged_mfa", "security", doctor_map.get("mfa", False)),
            ReadinessCheck("volume_encryption", "security", doctor_map.get("volume_encryption", False)),
            ReadinessCheck("malware_scanner", "security", doctor_map.get("malware_scanner", False)),
            ReadinessCheck("postgres_backend", "persistence", db.backend == "postgresql"),
            ReadinessCheck("postgres_driver", "persistence", db.backend == "postgresql" and bool(db.driver_available)),
            ReadinessCheck("postgres_repository_evidence", "persistence", repo_ok, evidence="repository"),
            ReadinessCheck("postgres_external_certified", "persistence", self._attested("postgres_external_certified"), evidence="external_attestation"),
            ReadinessCheck("postgres_migration_certified", "persistence", repo_ok and self._attested("postgres_migration_certified"), evidence="external_attestation+repository"),
            ReadinessCheck("postgres_backup_restore_certified", "resilience", self._attested("postgres_backup_restore_certified"), evidence="external_attestation"),
            ReadinessCheck(
                "durable_object_storage",
                "resilience",
                storage_backend in durable_backends and self._attested("durable_object_storage_certified"),
                evidence="external_attestation+runtime",
            ),
            ReadinessCheck("monitoring_certified", "operations", self._attested("monitoring_certified"), evidence="external_attestation"),
            ReadinessCheck("incident_response_certified", "operations", self._attested("incident_response_certified"), evidence="external_attestation"),
            ReadinessCheck("independent_security_review", "security", self._attested("security_review_certified"), evidence="external_attestation"),
            ReadinessCheck("canonical_sources_verified", "legal_governance", doctor_map.get("canonical_sources", False)),
            ReadinessCheck("privacy_governance_approved", "legal_governance", self._attested("privacy_governance_approved"), evidence="human_attestation"),
            ReadinessCheck("legal_operations_approved", "legal_governance", self._attested("legal_operations_approved"), evidence="human_attestation"),
            ReadinessCheck("qa_operations_approved", "legal_governance", self._attested("qa_operations_approved"), evidence="human_attestation"),
        ]
        context = {
            "doctor_passed": int(doctor.get("passed") or 0),
            "doctor_total": int(doctor.get("total") or 0),
            "repository_evidence_missing": repo_missing,
            "database_backend": db.backend,
            "database_driver_available": bool(db.driver_available),
            "object_storage_backend": storage_backend,
        }
        return checks, context

    @staticmethod
    def _next_action(key: str) -> str:
        actions = {
            "production_profile": "Ejecutar la certificación en un entorno aislado con LEGAL_PROFILE=production.",
            "synthetic_data_boundary_removed": "Crear una release posterior que retire explícitamente SYNTHETIC_DATA_ONLY sólo después de aprobar infraestructura y privacidad.",
            "postgres_repository_evidence": "Restaurar o reconstruir los artefactos de certificación PostgreSQL citados por el runtime y someterlos a CI.",
            "postgres_backend": "Ejecutar la aplicación contra PostgreSQL administrado; SQLite no es aceptable para producción jurídica real.",
            "postgres_driver": "Instalar y fijar psycopg 3 en el entorno objetivo de certificación.",
            "postgres_external_certified": "Ejecutar y conservar evidencia de la suite completa contra PostgreSQL real.",
            "postgres_migration_certified": "Probar una migración real desde snapshot controlado y verificar conteos, hashes e integridad funcional.",
            "postgres_backup_restore_certified": "Ejecutar backup y restore reales de PostgreSQL con evidencia de RPO/RTO y recuperación.",
            "durable_object_storage": "Implementar almacenamiento de objetos durable, cifrado y aislado por tenant; el store local no basta.",
            "monitoring_certified": "Configurar health, métricas, logs, alertas y escalamiento operativo en la infraestructura objetivo.",
            "incident_response_certified": "Aprobar y probar runbook de incidentes, responsables, severidades y recuperación.",
            "independent_security_review": "Completar revisión de seguridad independiente sobre el release candidate y cerrar hallazgos bloqueantes.",
            "privacy_governance_approved": "Aprobar tratamiento de datos, retención, encargados, privacidad y respuesta a titulares para operación real.",
            "legal_operations_approved": "Aprobar el modelo operativo de especialistas, límites del servicio, escalamiento y revisión jurídica humana.",
            "qa_operations_approved": "Aprobar el modelo QA humano y evidencia de liberación para documentos y expedientes reales.",
            "privileged_mfa": "Activar MFA para todos los usuarios activos de roles obligatorios.",
            "malware_scanner": "Configurar un escáner antimalware operativo y fail-closed para cargas reales.",
            "origin_check": "Mantener verificación estricta de origen en producción.",
            "public_https": "Configurar URL pública HTTPS válida en el entorno objetivo.",
            "secure_cookies": "Forzar cookies Secure en el entorno objetivo.",
            "volume_encryption": "Conservar evidencia verificable de cifrado del volumen/base administrada.",
            "managed_master_key": "Usar una llave maestra administrada fuera del filesystem efímero y fuera de Git.",
            "canonical_sources_verified": "Verificar al menos una fuente jurídica canónica dentro de la base productiva de certificación.",
            "stack_m34_m37_complete": "Restaurar la cadena incremental M34-M37 completa antes de certificar V1.",
            "portfolio_floor_preserved": "Restaurar el piso canónico de 11 productos y 473 preguntas.",
            "public_demo_disabled": "Separar completamente el perfil de producción real del modo de demostración pública.",
        }
        return actions.get(key, "Cerrar la evidencia bloqueante y volver a ejecutar el gate V1.")

    def assess(self, con) -> dict[str, Any]:
        checks, context = self._checks(con)
        blocking = [item.key for item in checks if item.blocking and not item.passed]
        platform_ready = not blocking

        payment_checks = [
            ReadinessCheck(
                "real_payments_authorized",
                "payments",
                bool(self.release_flags.get("real_payments_authorized")),
                evidence="release_metadata",
            ),
            ReadinessCheck(
                "real_payment_provider_certified",
                "payments",
                self._attested("real_payment_provider_certified"),
                evidence="external_attestation",
            ),
        ]
        payment_blocking = [item.key for item in payment_checks if not item.passed]
        payments_ready = not payment_blocking
        real_production_flag = bool(self.release_flags.get("real_production_authorized"))
        activation_authorized = bool(platform_ready and real_production_flag)

        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile": str(getattr(self.settings, "profile", "")),
            "readiness": {
                "platform_ready": platform_ready,
                "payments_ready": payments_ready,
                "commercial_ready": bool(platform_ready and payments_ready),
                "real_production_authorized": real_production_flag,
                "activation_authorized": activation_authorized,
                "activation_state": "AUTHORIZED" if activation_authorized else "BLOCKED",
            },
            "checks": [item.public() for item in checks],
            "blocking": blocking,
            "payment_checks": [item.public() for item in payment_checks],
            "payment_blocking": payment_blocking,
            "next_actions": [self._next_action(key) for key in blocking],
            "evidence_summary": {
                "doctor_passed": context["doctor_passed"],
                "doctor_total": context["doctor_total"],
                "repository_evidence_complete": not bool(context["repository_evidence_missing"]),
                "repository_evidence_missing": context["repository_evidence_missing"],
                "database_backend": context["database_backend"],
                "database_driver_available": context["database_driver_available"],
                "object_storage_backend": context["object_storage_backend"],
            },
            "governance": {
                "read_only": True,
                "self_authorization": False,
                "technical_readiness_is_legal_approval": False,
                "technical_readiness_is_qa_approval": False,
                "technical_readiness_is_security_approval": False,
                "technical_readiness_is_privacy_approval": False,
                "real_payments_are_separate": True,
            },
            "notice": str((self.contract.get("notices") or {}).get("assessment") or ""),
        }


__all__ = [
    "ReadinessCheck",
    "ReleaseReadinessContractError",
    "ReleaseReadinessV1",
    "SCHEMA",
    "SCHEMA_VERSION",
]
