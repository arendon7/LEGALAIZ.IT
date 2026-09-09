from __future__ import annotations

from pathlib import Path
from typing import Mapping

from legalai_platform.external_evidence_dossier_v1_rc2 import (
    ASSURANCE,
    ExternalEvidenceDossier,
    ExternalEvidenceIntegrityError,
)
from legalai_platform.operational_security import ExternalAttestationRegistry
from legalai_platform.v1_rc1_production_readiness import (
    V1RC1ProductionReadinessGate,
    V1RC1ReadinessError,
)


class V1RC2ReleaseAssuranceError(RuntimeError):
    pass


class V1RC2ReleaseAssuranceGate:
    """Compone V1-RC1 con el dossier reforzado de evidencia externa V1-RC2.

    RC2 no habilita producción, pagos ni comunicaciones. Su única función es
    sustituir, para esta fase de release, la atestación legacy M7 por un dossier
    append-only con evidencia hasheada, vigencia, aprobación de dominio y
    ratificación de release separada. La decisión comercial continúa perteneciendo
    al gate RC1 y a la metadata de release.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        dossier: ExternalEvidenceDossier | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.rc1 = V1RC1ProductionReadinessGate(self.root)
        self.dossier = dossier or ExternalEvidenceDossier(self.root)
        self._validate_contract_alignment()

    def _validate_contract_alignment(self) -> None:
        rc1_controls = tuple(self.rc1.policy.get("external_attestations") or [])
        rc2_controls = tuple(self.dossier.controls)
        canonical = tuple(ExternalAttestationRegistry.REQUIRED)
        if set(rc1_controls) != set(canonical):
            raise V1RC2ReleaseAssuranceError("RC1 ya no coincide con el inventario canónico de atestaciones externas.")
        if set(rc2_controls) != set(canonical):
            raise V1RC2ReleaseAssuranceError("RC2 debe gobernar exactamente las diez atestaciones externas canónicas.")

    def external_summary_for_rc1(self) -> dict:
        summary = self.dossier.summary()
        checks = list(summary.get("checks") or [])
        missing = [
            str(row.get("key") or "")
            for row in checks
            if not bool(row.get("passed"))
        ]
        return {
            "ready": bool(summary.get("ready")),
            "passed": int(summary.get("passed") or 0),
            "total": int(summary.get("total") or 0),
            "missing": missing,
        }

    def evaluate(self, environ: Mapping[str, str] | None = None) -> dict:
        dossier_summary = self.dossier.summary()
        rc1_report = self.rc1.evaluate(
            environ,
            external_summary=self.external_summary_for_rc1(),
        )
        dossier_integrity_valid = dossier_summary.get("integrity") == "valid"
        dossier_ready = bool(dossier_summary.get("ready"))
        controlled_ready = bool((rc1_report.get("commercial") or {}).get("controlled_validation_ready"))

        if not dossier_integrity_valid:
            state = "BLOCKED_EVIDENCE_DOSSIER_INTEGRITY"
        elif not dossier_ready:
            state = "BLOCKED_EVIDENCE_DOSSIER"
        else:
            state = str(rc1_report.get("state") or "UNKNOWN")

        return {
            "schema": "legalaizit-v1-rc2-release-assurance-report-v1",
            "candidate": "V1-RC2",
            "assurance": ASSURANCE,
            "state": state,
            "external_evidence": dossier_summary,
            "rc1_state": str(rc1_report.get("state") or "UNKNOWN"),
            "startup": rc1_report.get("startup") or {},
            "release_metadata": rc1_report.get("release_metadata") or {},
            "commercial": rc1_report.get("commercial") or {},
            "ready_for_controlled_production_validation": bool(dossier_ready and controlled_ready),
            "notices": [
                "V1-RC2 no autoriza producción, pagos reales ni comunicaciones externas.",
                "La evidencia RC2 debe existir fuera de respuestas públicas y conservar coincidencia SHA-256.",
                "Aprobación de dominio y ratificación de release requieren actores distintos.",
                "La cadena JSONL es append-only y detecta alteraciones bajo el modelo de control de la aplicación; no equivale por sí sola a almacenamiento WORM ni a una firma externa independiente.",
            ],
        }

    def assert_controlled_validation_ready(self, environ: Mapping[str, str] | None = None) -> dict:
        report = self.evaluate(environ)
        if not report.get("ready_for_controlled_production_validation"):
            external = report.get("external_evidence") or {}
            blockers = [
                str(row.get("key") or "")
                for row in external.get("checks") or []
                if not bool(row.get("passed"))
            ]
            suffix = ", ".join(blockers) if blockers else str(report.get("state") or "UNKNOWN")
            raise V1RC2ReleaseAssuranceError(f"Validación productiva controlada V1-RC2 bloqueada: {suffix}")
        return report

    def assert_safe_launch_claim(self, environ: Mapping[str, str] | None = None) -> dict:
        """Delega la afirmación de lanzamiento a RC1 usando exclusivamente evidencia RC2."""
        try:
            return self.rc1.assert_safe_launch_claim(
                environ,
                external_summary=self.external_summary_for_rc1(),
            )
        except V1RC1ReadinessError as exc:
            raise V1RC2ReleaseAssuranceError(str(exc)) from exc
        except ExternalEvidenceIntegrityError as exc:
            raise V1RC2ReleaseAssuranceError("El dossier RC2 no supera la verificación de integridad.") from exc


__all__ = [
    "V1RC2ReleaseAssuranceError",
    "V1RC2ReleaseAssuranceGate",
]
