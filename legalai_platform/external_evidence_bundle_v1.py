from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.external_evidence_dossier_v1_rc2 import ExternalEvidenceDossier


BUNDLE_SCHEMA = "legalaiz-v1-external-evidence-bundle-v1"
MANIFEST_NAME = "manifest.json"
FORBIDDEN_SECRET_KEYS = {
    "password",
    "passwords",
    "token",
    "tokens",
    "api_key",
    "api_keys",
    "secret",
    "secrets",
    "secret_value",
    "secret_values",
    "credential",
    "credentials",
    "private_key",
    "private_keys",
    "recovery_code",
    "recovery_codes",
}


class EvidenceBundleError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise EvidenceBundleError(f"{field} es obligatorio.")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceBundleError(f"{field} debe usar ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise EvidenceBundleError(f"{field} debe incluir zona horaria.")
    return parsed.astimezone(timezone.utc)


def _resolve_under(base: Path, relative: str, field: str) -> tuple[Path, str]:
    raw = str(relative or "").strip().replace("\\", "/")
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or ".." in candidate.parts:
        raise EvidenceBundleError(f"{field} debe ser una ruta relativa segura.")
    base_resolved = base.resolve()
    resolved = (base_resolved / candidate).resolve()
    try:
        normalized = resolved.relative_to(base_resolved).as_posix()
    except ValueError as exc:
        raise EvidenceBundleError(f"{field} sale del repositorio de evidencia.") from exc
    return resolved, normalized


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _forbidden_key_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().casefold() in FORBIDDEN_SECRET_KEYS:
                findings.append(child_path)
            findings.extend(_forbidden_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_forbidden_key_paths(child, f"{path}[{index}]"))
    return findings


def _safe_identity(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise EvidenceBundleError(f"{field} debe identificar actor y rol.")
    actor_id = str(value.get("id") or "").strip()
    role = str(value.get("role") or "").strip().casefold()
    if not re.fullmatch(r"[A-Za-z0-9._@-]{2,160}", actor_id):
        raise EvidenceBundleError(f"{field}.id inválido.")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,80}", role):
        raise EvidenceBundleError(f"{field}.role inválido.")
    return {"id": actor_id, "role": role}


@dataclass(frozen=True)
class ValidatedEvidenceBundle:
    control_ref: str
    source_framework: str
    source_id: str
    bundle_path: str
    manifest_path: str
    manifest_sha256: str
    observed_at: str
    valid_until: str
    environment: str
    executor: dict[str, str]
    artifact_count: int

    def public(self) -> dict[str, Any]:
        return {
            "control_ref": self.control_ref,
            "source_framework": self.source_framework,
            "source_id": self.source_id,
            "bundle_path": self.bundle_path,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "observed_at": self.observed_at,
            "valid_until": self.valid_until,
            "environment": self.environment,
            "executor": dict(self.executor),
            "artifact_count": self.artifact_count,
        }


class EvidenceBundleValidator:
    def __init__(
        self,
        root: str | Path,
        evidence_root: str | Path,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.evidence_root = Path(evidence_root).expanduser().resolve()
        self.now_factory = now_factory or _now
        plan = EvidenceExecutionPlan(self.root)
        validation = plan.validate()
        if not validation.valid:
            raise EvidenceBundleError("El execution pack RC6 no es estructuralmente válido.")
        self.plan = plan.plan
        self.controls = {str(row["ref"]): row for row in self.plan["controls"]}

    def validate(self, bundle_path: str, *, expected_control_ref: str | None = None) -> ValidatedEvidenceBundle:
        bundle_dir, normalized_bundle = _resolve_under(self.evidence_root, bundle_path, "bundle_path")
        if not bundle_dir.is_dir():
            raise EvidenceBundleError("El bundle de evidencia no existe o no es directorio.")
        manifest_path = bundle_dir / MANIFEST_NAME
        if not manifest_path.is_file():
            raise EvidenceBundleError("Falta manifest.json en el bundle de evidencia.")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceBundleError("manifest.json no puede leerse íntegramente.") from exc
        if not isinstance(manifest, dict) or manifest.get("schema") != BUNDLE_SCHEMA:
            raise EvidenceBundleError("Schema de bundle externo inválido.")
        forbidden = _forbidden_key_paths(manifest)
        if forbidden:
            raise EvidenceBundleError("El manifiesto contiene claves capaces de almacenar secretos: " + ", ".join(forbidden))

        control_ref = str(manifest.get("control_ref") or "").strip()
        if expected_control_ref and control_ref != expected_control_ref:
            raise EvidenceBundleError("El bundle no corresponde al control esperado.")
        control = self.controls.get(control_ref)
        if not control:
            raise EvidenceBundleError("El bundle referencia un control RC6 desconocido.")
        framework = str(control.get("source_framework") or "")
        source_id = str(control.get("source_id") or "")
        if str(manifest.get("source_framework") or "") != framework or str(manifest.get("source_id") or "") != source_id:
            raise EvidenceBundleError("La identidad fuente del bundle no coincide con RC6.")

        environment = str(manifest.get("environment") or "").strip()
        if environment != str(control.get("environment") or ""):
            raise EvidenceBundleError("El entorno del bundle no coincide con el execution pack.")
        executor = _safe_identity(manifest.get("executor"), "executor")
        if executor["role"] != str(control.get("executor_role") or ""):
            raise EvidenceBundleError("El rol ejecutor del bundle no coincide con RC6.")

        redaction = manifest.get("redaction")
        if not isinstance(redaction, dict) or redaction.get("performed") is not True:
            raise EvidenceBundleError("El bundle debe declarar redacción de información sensible.")
        declaration = str(redaction.get("declaration") or "").strip()
        if len(declaration) < 20:
            raise EvidenceBundleError("La declaración de redacción es insuficiente.")

        observed = _parse_dt(manifest.get("observed_at"), "observed_at")
        valid = _parse_dt(manifest.get("valid_until"), "valid_until")
        now = self.now_factory().astimezone(timezone.utc)
        max_days = int(control.get("max_validity_days") or 0)
        if observed > now + timedelta(minutes=5):
            raise EvidenceBundleError("observed_at no puede estar en el futuro.")
        if valid <= observed or valid > observed + timedelta(days=max_days):
            raise EvidenceBundleError("valid_until excede la vigencia máxima RC6.")
        if valid <= now:
            raise EvidenceBundleError("El bundle de evidencia está vencido.")

        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise EvidenceBundleError("El bundle debe contener un inventario de artefactos.")
        required = {str(name) for name in (control.get("required_artifacts") or []) if str(name) != "sha256_manifest"}
        names: set[str] = set()
        paths: set[str] = set()
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                raise EvidenceBundleError(f"artifacts[{index}] inválido.")
            name = str(artifact.get("name") or "").strip()
            if not re.fullmatch(r"[a-z][a-z0-9_]{2,100}", name):
                raise EvidenceBundleError(f"artifacts[{index}].name inválido.")
            if name in names:
                raise EvidenceBundleError("El bundle repite nombres de artefacto.")
            names.add(name)
            file_path, normalized_path = _resolve_under(bundle_dir, str(artifact.get("path") or ""), f"artifacts[{index}].path")
            if normalized_path == MANIFEST_NAME:
                raise EvidenceBundleError("manifest.json no puede declararse como artefacto ordinario.")
            if normalized_path in paths:
                raise EvidenceBundleError("El bundle repite rutas de artefacto.")
            paths.add(normalized_path)
            if not file_path.is_file():
                raise EvidenceBundleError(f"Falta el artefacto {name}.")
            declared_sha = str(artifact.get("sha256") or "").strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", declared_sha):
                raise EvidenceBundleError(f"Hash SHA-256 inválido para {name}.")
            declared_size = artifact.get("size")
            if not isinstance(declared_size, int) or isinstance(declared_size, bool) or declared_size < 0:
                raise EvidenceBundleError(f"Tamaño inválido para {name}.")
            if _sha256_file(file_path) != declared_sha or int(file_path.stat().st_size) != declared_size:
                raise EvidenceBundleError(f"Integridad de artefacto inválida para {name}.")
        missing = sorted(required - names)
        if missing:
            raise EvidenceBundleError("Faltan artefactos obligatorios: " + ", ".join(missing))

        normalized_manifest = f"{normalized_bundle}/{MANIFEST_NAME}" if normalized_bundle else MANIFEST_NAME
        return ValidatedEvidenceBundle(
            control_ref=control_ref,
            source_framework=framework,
            source_id=source_id,
            bundle_path=normalized_bundle,
            manifest_path=normalized_manifest,
            manifest_sha256=_sha256_file(manifest_path),
            observed_at=observed.isoformat(timespec="seconds"),
            valid_until=valid.isoformat(timespec="seconds"),
            environment=environment,
            executor=executor,
            artifact_count=len(artifacts),
        )


def register_rc2_bundle(
    dossier: ExternalEvidenceDossier,
    bundle_path: str,
    *,
    actor: Mapping[str, Any],
) -> dict[str, Any]:
    validator = EvidenceBundleValidator(dossier.root, dossier.evidence_root, now_factory=dossier.now_factory)
    validated = validator.validate(bundle_path)
    if validated.source_framework != "RC2":
        raise EvidenceBundleError("El bridge RC2 sólo admite controles RC2.")
    return dossier.register_evidence(
        validated.source_id,
        validated.manifest_path,
        observed_at=validated.observed_at,
        valid_until=validated.valid_until,
        actor=actor,
    )


__all__ = [
    "BUNDLE_SCHEMA",
    "EvidenceBundleError",
    "EvidenceBundleValidator",
    "ValidatedEvidenceBundle",
    "register_rc2_bundle",
]
