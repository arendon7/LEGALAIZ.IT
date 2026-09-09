from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any, Mapping

from legalai_platform.evidence_audit_pack_v1_rc9 import (
    PACK_SCHEMA,
    EvidenceAuditPack,
    EvidenceAuditPackError,
)


POLICY_SCHEMA = "legalaiz-v1-rc10-audit-custody-export-policy-v1"
ENVELOPE_SCHEMA = "legalaiz-v1-rc10-audit-custody-envelope-v1"
VERIFY_SCHEMA = "legalaiz-v1-rc10-audit-custody-verification-v1"
CANONICAL_FILES = ("audit-pack.json", "audit-pack.md", "custody-manifest.json")
PAYLOAD_FILES = ("audit-pack.json", "audit-pack.md")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AuditCustodyExportError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _markdown_bytes(value: str) -> bytes:
    return (value.rstrip() + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with NamedTemporaryFile("wb", dir=path.parent, delete=False, prefix=f".{path.name}.") as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _validate_sha256(value: str, *, label: str) -> str:
    text = str(value or "").strip().lower()
    if not SHA256_RE.fullmatch(text):
        raise AuditCustodyExportError(f"{label} debe ser un SHA-256 hexadecimal de 64 caracteres.")
    return text


def _recompute_rc9_snapshot(pack: Mapping[str, Any]) -> str:
    if pack.get("schema") != PACK_SCHEMA or int(pack.get("schema_version") or 0) != 1:
        raise AuditCustodyExportError("audit-pack.json no contiene un snapshot RC9 válido.")
    expected = _validate_sha256(str(pack.get("snapshot_sha256") or ""), label="snapshot_sha256")
    core = dict(pack)
    core.pop("schema", None)
    core.pop("schema_version", None)
    core.pop("snapshot_sha256", None)
    actual = sha256(_canonical_json(core).encode("utf-8")).hexdigest()
    if actual != expected:
        raise AuditCustodyExportError("El snapshot RC9 no supera su digest canónico.")
    return expected


class AuditCustodyExport:
    """Exporta y verifica un bundle de custodia derivado del audit pack RC9.

    El bundle sólo contiene el snapshot redactado y un manifest de integridad de
    esos archivos redactados. No contiene evidencia fuente ni reemplaza los
    ledgers, decisiones o gates que originan el snapshot.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        policy_path = self.root / "config" / "v1" / "rc10_audit_custody_export_policy.json"
        if not policy_path.is_file():
            raise AuditCustodyExportError("Falta la política RC10 de custodia.")
        try:
            self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditCustodyExportError("No fue posible leer la política RC10.") from exc
        self._validate_policy()

    def _validate_policy(self) -> None:
        policy = self.policy
        if policy.get("schema") != POLICY_SCHEMA or int(policy.get("schema_version") or 0) != 1:
            raise AuditCustodyExportError("Política RC10 inválida.")
        if tuple(policy.get("canonical_files") or ()) != CANONICAL_FILES:
            raise AuditCustodyExportError("RC10 perdió el inventario canónico de archivos.")
        if tuple(policy.get("payload_files") or ()) != PAYLOAD_FILES:
            raise AuditCustodyExportError("RC10 perdió el inventario de payload redactado.")

        governance = policy.get("governance") or {}
        required_true = {
            "export_is_derived_not_source_of_truth",
            "export_does_not_mutate_runtime_ledgers",
            "export_does_not_mutate_release_metadata",
            "export_does_not_register_evidence",
            "export_does_not_approve_or_ratify_evidence",
            "export_does_not_authorize_real_production",
            "export_does_not_authorize_real_payments",
            "only_redacted_audit_pack_files_are_hashed",
            "evidence_artifact_hashes_remain_forbidden",
            "actor_identifiers_remain_forbidden",
            "environment_fingerprint_remains_forbidden",
            "authorization_evidence_reference_remains_forbidden",
            "canonical_bundle_is_immutable",
            "existing_invalid_bundle_is_never_overwritten",
            "envelope_digest_is_not_a_digital_signature",
            "external_anchor_required_for_non_repudiation",
            "retention_period_is_organization_defined",
            "retention_period_is_not_a_legal_conclusion",
        }
        missing = sorted(key for key in required_true if governance.get(key) is not True)
        if missing:
            raise AuditCustodyExportError("Gobierno RC10 incompleto: " + ", ".join(missing))

    def _manifest(self, *, pack: Mapping[str, Any], payloads: Mapping[str, bytes]) -> dict[str, Any]:
        snapshot_sha256 = _validate_sha256(str(pack.get("snapshot_sha256") or ""), label="snapshot_sha256")
        campaign = pack.get("campaign") or {}
        files = []
        for name in PAYLOAD_FILES:
            payload = payloads[name]
            files.append({
                "name": name,
                "sha256": _sha256_bytes(payload),
                "size_bytes": len(payload),
                "media_type": "application/json" if name.endswith(".json") else "text/markdown; charset=utf-8",
            })
        core = {
            "schema": ENVELOPE_SCHEMA,
            "schema_version": 1,
            "snapshot_sha256": snapshot_sha256,
            "campaign_bound": bool((pack.get("scope") or {}).get("campaign_bound")),
            "campaign_id": str(campaign.get("campaign_id") or "") or None,
            "source_revision": str(campaign.get("source_revision") or "") or None,
            "files": files,
            "governance": {
                "derived_export_only": True,
                "contains_evidence_payloads": False,
                "contains_evidence_artifact_hashes": False,
                "contains_actor_identifiers": False,
                "contains_environment_fingerprint": False,
                "contains_authorization_evidence_reference": False,
                "mutates_runtime_ledgers": False,
                "mutates_release_metadata": False,
                "registers_evidence": False,
                "approves_or_ratifies_evidence": False,
                "authorizes_real_production": False,
                "authorizes_real_payments": False,
                "digest_is_digital_signature": False,
                "external_anchor_required_for_non_repudiation": True,
                "retention_period_defined_by_organization": True,
                "retention_period_is_legal_conclusion": False,
            },
        }
        return {**core, "envelope_sha256": sha256(_canonical_json(core).encode("utf-8")).hexdigest()}

    def export(self, output_root: str | Path, *, campaign_id: str | None = None) -> dict[str, Any]:
        output_root = Path(output_root).expanduser()
        if output_root.exists() and not output_root.is_dir():
            raise AuditCustodyExportError("El destino RC10 debe ser un directorio.")
        output_root.mkdir(parents=True, exist_ok=True)

        try:
            packer = EvidenceAuditPack(self.root)
            pack = packer.build(campaign_id=campaign_id)
            _recompute_rc9_snapshot(pack)
            payloads = {
                "audit-pack.json": _json_bytes(pack),
                "audit-pack.md": _markdown_bytes(packer.to_markdown(pack)),
            }
        except EvidenceAuditPackError as exc:
            raise AuditCustodyExportError(str(exc)) from exc

        manifest = self._manifest(pack=pack, payloads=payloads)
        envelope_sha256 = _validate_sha256(manifest["envelope_sha256"], label="envelope_sha256")
        bundle_dir = output_root / envelope_sha256

        if bundle_dir.exists():
            verification = self.verify(bundle_dir, expected_envelope_sha256=envelope_sha256)
            if verification["valid"] and verification["snapshot_sha256"] == pack["snapshot_sha256"]:
                return {
                    "schema": ENVELOPE_SCHEMA,
                    "bundle_dir": str(bundle_dir),
                    "envelope_sha256": envelope_sha256,
                    "snapshot_sha256": pack["snapshot_sha256"],
                    "campaign_bound": bool((pack.get("scope") or {}).get("campaign_bound")),
                    "created": False,
                    "idempotent": True,
                    "authorization_changed": False,
                }
            raise AuditCustodyExportError(
                "Ya existe un bundle RC10 inválido o distinto; no se sobrescribe. Debe aislarse manualmente."
            )

        bundle_dir.mkdir(mode=0o700)
        _atomic_write(bundle_dir / "audit-pack.json", payloads["audit-pack.json"])
        _atomic_write(bundle_dir / "audit-pack.md", payloads["audit-pack.md"])
        _atomic_write(bundle_dir / "custody-manifest.json", _json_bytes(manifest))
        verification = self.verify(bundle_dir, expected_envelope_sha256=envelope_sha256)

        return {
            "schema": ENVELOPE_SCHEMA,
            "bundle_dir": str(bundle_dir),
            "envelope_sha256": envelope_sha256,
            "snapshot_sha256": pack["snapshot_sha256"],
            "campaign_bound": bool((pack.get("scope") or {}).get("campaign_bound")),
            "created": True,
            "idempotent": False,
            "authorization_changed": False,
            "verification": verification,
        }

    def verify(
        self,
        bundle_dir: str | Path,
        *,
        expected_envelope_sha256: str | None = None,
    ) -> dict[str, Any]:
        bundle_dir = Path(bundle_dir)
        if bundle_dir.is_symlink() or not bundle_dir.is_dir():
            raise AuditCustodyExportError("El bundle RC10 debe ser un directorio real, no un symlink.")

        names = sorted(path.name for path in bundle_dir.iterdir())
        if names != sorted(CANONICAL_FILES):
            raise AuditCustodyExportError("El bundle RC10 no contiene exactamente los tres archivos canónicos.")

        paths = {name: bundle_dir / name for name in CANONICAL_FILES}
        for name, path in paths.items():
            if path.is_symlink() or not path.is_file():
                raise AuditCustodyExportError(f"{name} debe ser un archivo regular.")

        try:
            manifest = json.loads(paths["custody-manifest.json"].read_text(encoding="utf-8"))
            pack = json.loads(paths["audit-pack.json"].read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditCustodyExportError("El bundle RC10 contiene JSON ilegible o inválido.") from exc

        if manifest.get("schema") != ENVELOPE_SCHEMA or int(manifest.get("schema_version") or 0) != 1:
            raise AuditCustodyExportError("Manifest RC10 inválido.")
        envelope_sha256 = _validate_sha256(str(manifest.get("envelope_sha256") or ""), label="envelope_sha256")

        core = dict(manifest)
        core.pop("envelope_sha256", None)
        recomputed_envelope = sha256(_canonical_json(core).encode("utf-8")).hexdigest()
        if recomputed_envelope != envelope_sha256:
            raise AuditCustodyExportError("El manifest RC10 no supera su digest canónico.")

        if bundle_dir.name != envelope_sha256:
            raise AuditCustodyExportError("El nombre del bundle no coincide con envelope_sha256.")

        if expected_envelope_sha256 is not None:
            expected = _validate_sha256(expected_envelope_sha256, label="expected_envelope_sha256")
            if expected != envelope_sha256:
                raise AuditCustodyExportError("El bundle no coincide con el digest anclado externamente.")

        snapshot_sha256 = _recompute_rc9_snapshot(pack)
        if snapshot_sha256 != str(manifest.get("snapshot_sha256") or ""):
            raise AuditCustodyExportError("El manifest no está vinculado al snapshot RC9 exportado.")

        listed_files = manifest.get("files") or []
        if [row.get("name") for row in listed_files] != list(PAYLOAD_FILES):
            raise AuditCustodyExportError("El manifest RC10 perdió el orden/inventario de payloads.")

        for row in listed_files:
            name = str(row.get("name") or "")
            if name not in PAYLOAD_FILES:
                raise AuditCustodyExportError("El manifest RC10 contiene un payload no permitido.")
            payload = paths[name].read_bytes()
            expected_hash = _validate_sha256(str(row.get("sha256") or ""), label=f"{name}.sha256")
            if _sha256_bytes(payload) != expected_hash:
                raise AuditCustodyExportError(f"{name} no supera integridad SHA-256.")
            if len(payload) != int(row.get("size_bytes") or -1):
                raise AuditCustodyExportError(f"{name} no coincide con el tamaño registrado.")

        markdown = paths["audit-pack.md"].read_text(encoding="utf-8")
        if snapshot_sha256 not in markdown:
            raise AuditCustodyExportError("audit-pack.md no referencia el snapshot RC9 exportado.")

        governance = manifest.get("governance") or {}
        if governance.get("digest_is_digital_signature") is not False:
            raise AuditCustodyExportError("RC10 no puede presentar el digest como firma digital.")
        if governance.get("external_anchor_required_for_non_repudiation") is not True:
            raise AuditCustodyExportError("RC10 debe conservar el requisito de anclaje externo.")

        return {
            "schema": VERIFY_SCHEMA,
            "valid": True,
            "envelope_sha256": envelope_sha256,
            "snapshot_sha256": snapshot_sha256,
            "campaign_bound": bool(manifest.get("campaign_bound")),
            "external_anchor_checked": expected_envelope_sha256 is not None,
            "authorization_changed": False,
        }


__all__ = [
    "AuditCustodyExport",
    "AuditCustodyExportError",
    "CANONICAL_FILES",
    "ENVELOPE_SCHEMA",
    "POLICY_SCHEMA",
    "VERIFY_SCHEMA",
]
