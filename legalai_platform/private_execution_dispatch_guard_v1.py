from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Any

from legalai_platform.evidence_execution_board_v1 import (
    EvidenceOperationsBoard,
    EvidenceOperationsBoardError,
)
from legalai_platform.private_assignment_packets_v1 import (
    ASSIGNMENT_MANIFEST_SCHEMA,
    PRIVATE_TOP_LEVEL_DIRS,
)


PREFLIGHT_SCHEMA = "legalaiz-v1-ops4-private-execution-preflight-v1"
DISPATCH_MANIFEST_SCHEMA = "legalaiz-v1-ops4-private-dispatch-manifest-v1"
DISPATCHABLE_STATUSES = frozenset({"READY_TO_EXECUTE"})
PII_KEYS = frozenset({"display_name", "contact", "actor_id", "person_ref"})
EXPECTED_MANIFEST_KEYS = frozenset({
    "schema", "campaign_id", "source_board_sha256", "controls", "waves", "packets",
    "manifest_contains_personal_data", "packet_files_contain_personal_data", "input_copied",
    "packet_hashes_persisted", "repository_persistence_allowed", "campaign_mutated",
    "evidence_mutated", "release_authorization_changed",
})
EXPECTED_PACKET_KEYS = frozenset({
    "sequence", "wave", "control_ref", "work_status", "executor_role", "reviewer_role",
    "packet_file", "contains_personal_data",
})


class PrivateDispatchGuardError(RuntimeError):
    pass


def _pii_key_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().casefold() in PII_KEYS:
                findings.append(child_path)
            findings.extend(_pii_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_pii_key_paths(child, f"{path}[{index}]"))
    return findings


def _exact_keys(row: dict[str, Any], expected: frozenset[str], label: str) -> None:
    actual = set(row)
    extra = sorted(actual - set(expected))
    missing = sorted(set(expected) - actual)
    if extra or missing:
        details: list[str] = []
        if extra:
            details.append("sobran=" + ",".join(extra))
        if missing:
            details.append("faltan=" + ",".join(missing))
        raise PrivateDispatchGuardError(f"{label} no conserva el schema OPS3 exacto: " + "; ".join(details))


class PrivateExecutionDispatchGuard:
    """Preflight read-only y despacho privado; nunca ejecuta controles ni muta campañas."""

    def __init__(self, root: str | Path, *, ledger_path: str | Path | None = None) -> None:
        self.root = Path(root).resolve()
        self.ledger_path = Path(ledger_path).expanduser() if ledger_path is not None else None

    def _private_path(self, path: str | Path, *, label: str, must_exist: bool, expect_dir: bool) -> Path:
        raw = Path(path).expanduser().absolute()
        try:
            relative = raw.relative_to(self.root)
        except ValueError:
            relative = None
        if relative is not None:
            top = relative.parts[0] if relative.parts else ""
            if top not in PRIVATE_TOP_LEVEL_DIRS:
                raise PrivateDispatchGuardError(
                    f"{label} no puede vivir en una ruta versionable del repositorio."
                )
        if raw.exists() and raw.is_symlink():
            raise PrivateDispatchGuardError(f"{label} no puede ser un enlace simbólico.")
        if must_exist:
            if not raw.exists():
                raise PrivateDispatchGuardError(f"{label} no existe.")
            if expect_dir and not raw.is_dir():
                raise PrivateDispatchGuardError(f"{label} debe ser un directorio.")
            if not expect_dir and not raw.is_file():
                raise PrivateDispatchGuardError(f"{label} debe ser un archivo regular.")
            return raw.resolve(strict=True)
        return raw

    @staticmethod
    def _safe_packet_relative_path(value: Any) -> PurePosixPath:
        text = str(value or "").strip().replace("\\", "/")
        candidate = PurePosixPath(text)
        if (
            not text
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) != 2
            or candidate.parts[0] != "controls"
            or candidate.suffix.lower() != ".md"
        ):
            raise PrivateDispatchGuardError("packet_file OPS3 inválido o con traversal.")
        return candidate

    def _load_pack(self, pack_dir: str | Path) -> tuple[Path, dict[str, Any], dict[str, Path]]:
        root = self._private_path(pack_dir, label="OPS3 pack", must_exist=True, expect_dir=True)
        manifest_path = root / "assignment-manifest.json"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise PrivateDispatchGuardError("Falta assignment-manifest.json regular en el pack OPS3.")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrivateDispatchGuardError("El manifest OPS3 no es JSON UTF-8 válido.") from exc
        if not isinstance(manifest, dict):
            raise PrivateDispatchGuardError("El manifest OPS3 debe ser un objeto JSON.")
        _exact_keys(manifest, EXPECTED_MANIFEST_KEYS, "manifest OPS3")
        if manifest.get("schema") != ASSIGNMENT_MANIFEST_SCHEMA:
            raise PrivateDispatchGuardError("Schema de manifest OPS3 no soportado.")
        if _pii_key_paths(manifest):
            raise PrivateDispatchGuardError("El manifest OPS3 contiene claves de identidad prohibidas.")
        expected_flags = {
            "manifest_contains_personal_data": False,
            "packet_files_contain_personal_data": True,
            "input_copied": False,
            "packet_hashes_persisted": False,
            "repository_persistence_allowed": False,
            "campaign_mutated": False,
            "evidence_mutated": False,
            "release_authorization_changed": False,
        }
        for key, expected in expected_flags.items():
            if manifest.get(key) is not expected:
                raise PrivateDispatchGuardError(f"El manifest OPS3 perdió la garantía {key}={expected}.")
        packets_raw = manifest.get("packets")
        if not isinstance(packets_raw, list) or len(packets_raw) != 22 or int(manifest.get("controls") or 0) != 22:
            raise PrivateDispatchGuardError("OPS4 exige un pack OPS3 completo de exactamente 22 controles.")

        seen_refs: set[str] = set()
        seen_files: set[str] = set()
        packet_paths: dict[str, Path] = {}
        for index, row in enumerate(packets_raw, 1):
            if not isinstance(row, dict):
                raise PrivateDispatchGuardError(f"packets[{index}] debe ser objeto.")
            _exact_keys(row, EXPECTED_PACKET_KEYS, f"packets[{index}]")
            if row.get("contains_personal_data") is not True:
                raise PrivateDispatchGuardError("Todo packet OPS3 debe declarar contains_personal_data=true.")
            ref = str(row.get("control_ref") or "").strip()
            if not ref or ref in seen_refs:
                raise PrivateDispatchGuardError("control_ref vacío o duplicado en manifest OPS3.")
            relative = self._safe_packet_relative_path(row.get("packet_file"))
            relative_text = relative.as_posix()
            if relative_text in seen_files:
                raise PrivateDispatchGuardError("packet_file duplicado en manifest OPS3.")
            candidate = root.joinpath(*relative.parts)
            if not candidate.is_file() or candidate.is_symlink():
                raise PrivateDispatchGuardError(f"Falta packet privado regular para {ref}.")
            resolved = candidate.resolve(strict=True)
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise PrivateDispatchGuardError("Un packet OPS3 escapa del directorio privado.") from exc
            body = resolved.read_text(encoding="utf-8")
            bindings = (
                f"- Campaña: `{manifest['campaign_id']}`",
                f"- Control: `{ref}`",
                f"- Estado OPS2: `{row['work_status']}`",
                f"- Rol requerido: `{row['executor_role']}`",
                f"- Rol requerido: `{row['reviewer_role']}`",
                "CONFIDENCIAL / DATOS PERSONALES",
            )
            for marker in bindings:
                if marker not in body:
                    raise PrivateDispatchGuardError(f"Packet {ref} no conserva su binding estructural OPS3.")
            seen_refs.add(ref)
            seen_files.add(relative_text)
            packet_paths[ref] = resolved

        if len(packet_paths) != 22:
            raise PrivateDispatchGuardError("El pack OPS3 no resolvió 22 packets privados únicos.")
        return root, manifest, packet_paths

    def preflight(self, pack_dir: str | Path) -> dict[str, Any]:
        _, manifest, packet_paths = self._load_pack(pack_dir)
        campaign_id = str(manifest.get("campaign_id") or "").strip()
        if not campaign_id:
            raise PrivateDispatchGuardError("El manifest OPS3 no fija campaign_id.")
        try:
            board = EvidenceOperationsBoard(
                self.root,
                campaign_id=campaign_id,
                ledger_path=self.ledger_path,
            ).build()
        except EvidenceOperationsBoardError as exc:
            raise PrivateDispatchGuardError(str(exc)) from exc

        campaign = board["campaign"]
        board_current = str(manifest.get("source_board_sha256") or "") == str(board.get("board_sha256") or "")
        manifest_rows = {str(row["control_ref"]): row for row in manifest["packets"]}
        board_rows = {str(row["control_ref"]): row for row in board["controls"]}
        if set(manifest_rows) != set(board_rows) or set(packet_paths) != set(board_rows):
            raise PrivateDispatchGuardError("El pack OPS3 no coincide con el conjunto canónico actual de controles.")

        structural_mismatches: list[str] = []
        for ref, current in board_rows.items():
            previous = manifest_rows[ref]
            if (
                int(previous["sequence"]) != int(current["sequence"])
                or int(previous["wave"]) != int(current["wave"])
                or str(previous["executor_role"]) != str(current["executor_role"])
                or str(previous["reviewer_role"]) != str(current["reviewer_role"])
            ):
                structural_mismatches.append(ref)
        if structural_mismatches:
            raise PrivateDispatchGuardError(
                "El pack OPS3 no coincide con la estructura canónica actual: " + ", ".join(sorted(structural_mismatches))
            )

        blockers: list[str] = []
        if not bool(campaign.get("plan_hash_current")):
            blockers.append("PLAN_DRIFT")
        if str(campaign.get("status") or "") == "ABORTED":
            blockers.append("CAMPAIGN_ABORTED")
        if not board_current:
            blockers.append("STALE_SOURCE_BOARD")

        dispatchable = [
            row for row in board["controls"]
            if board_current and not blockers and str(row["work_status"]) in DISPATCHABLE_STATUSES
        ]
        nondispatchable = [
            {"control_ref": row["control_ref"], "wave": row["wave"], "status": row["work_status"]}
            for row in board["controls"]
            if row["control_ref"] not in {item["control_ref"] for item in dispatchable}
        ]
        return {
            "schema": PREFLIGHT_SCHEMA,
            "campaign_id": campaign_id,
            "campaign_status": campaign.get("status"),
            "source_board_current": board_current,
            "source_board_sha256": manifest.get("source_board_sha256"),
            "current_board_sha256": board.get("board_sha256"),
            "controls": 22,
            "dispatchable_count": len(dispatchable),
            "dispatchable_controls": [
                {"control_ref": row["control_ref"], "sequence": row["sequence"], "wave": row["wave"], "status": row["work_status"]}
                for row in dispatchable
            ],
            "nondispatchable_controls": nondispatchable,
            "blockers": blockers,
            "dispatch_allowed": bool(dispatchable) and not blockers,
            "contains_personal_data": False,
            "personal_data_echoed": False,
            "network_delivery_performed": False,
            "control_execution_performed": False,
            "campaign_mutated": False,
            "evidence_mutated": False,
            "release_authorization_changed": False,
        }

    def write(self, pack_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
        source_root, manifest, packet_paths = self._load_pack(pack_dir)
        preflight = self.preflight(source_root)
        if not preflight["dispatch_allowed"]:
            reason = ", ".join(preflight["blockers"]) or "NO_READY_CONTROLS"
            raise PrivateDispatchGuardError(f"Despacho privado bloqueado: {reason}.")
        target = self._private_path(output_dir, label="dispatch output", must_exist=False, expect_dir=True)
        if target.exists():
            raise PrivateDispatchGuardError("El dispatch output ya existe; OPS4 nunca sobrescribe.")
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        if parent.is_symlink():
            raise PrivateDispatchGuardError("El padre del dispatch output no puede ser symlink.")

        selected = {str(row["control_ref"]): row for row in preflight["dispatchable_controls"]}
        temp_dir = Path(tempfile.mkdtemp(prefix=".ops4-", dir=str(parent)))
        os.chmod(temp_dir, 0o700)
        try:
            controls_dir = temp_dir / "controls"
            controls_dir.mkdir(mode=0o700)
            dispatch_rows: list[dict[str, Any]] = []
            source_rows = {str(row["control_ref"]): row for row in manifest["packets"]}
            for ref, state in sorted(selected.items(), key=lambda item: int(item[1]["sequence"])):
                source_row = source_rows[ref]
                relative = self._safe_packet_relative_path(source_row["packet_file"])
                destination = controls_dir / relative.name
                shutil.copyfile(packet_paths[ref], destination)
                os.chmod(destination, 0o600)
                dispatch_rows.append({
                    "sequence": int(state["sequence"]),
                    "wave": int(state["wave"]),
                    "control_ref": ref,
                    "work_status": state["status"],
                    "packet_file": f"controls/{relative.name}",
                    "contains_personal_data": True,
                })

            dispatch_manifest = {
                "schema": DISPATCH_MANIFEST_SCHEMA,
                "campaign_id": preflight["campaign_id"],
                "source_ops3_schema": ASSIGNMENT_MANIFEST_SCHEMA,
                "source_board_sha256": preflight["source_board_sha256"],
                "current_board_sha256": preflight["current_board_sha256"],
                "controls": len(dispatch_rows),
                "packets": dispatch_rows,
                "manifest_contains_personal_data": False,
                "packet_files_contain_personal_data": True,
                "packet_hashes_persisted": False,
                "network_delivery_performed": False,
                "control_execution_performed": False,
                "campaign_mutated": False,
                "evidence_mutated": False,
                "release_authorization_changed": False,
            }
            manifest_path = temp_dir / "dispatch-manifest.json"
            fd = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(dispatch_manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")

            notice = "\n".join([
                "# LegalAIZ.it — Despacho privado OPS4",
                "",
                "Este directorio contiene sólo los paquetes OPS3 que estaban READY_TO_EXECUTE en el board exacto fijado al momento del preflight.",
                "",
                "- No enviar automáticamente: OPS4 no tiene transporte de red.",
                "- No versionar ni adjuntar a PR/Issue/CI artifacts.",
                "- Antes de usar un comando de coordinación, verificar que la campaña no haya cambiado; si cambió, regenerar OPS3/OPS4.",
                "- Estos archivos no son evidencia, aprobación, ratificación ni autorización de producción/pagos.",
                "",
            ])
            readme_path = temp_dir / "README_PRIVATE.md"
            fd = os.open(readme_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(notice)

            os.replace(temp_dir, target)
            os.chmod(target, 0o700)
            os.chmod(target / "controls", 0o700)
            for item in target.rglob("*"):
                if item.is_file():
                    os.chmod(item, 0o600)
        except Exception:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return {
            "schema": DISPATCH_MANIFEST_SCHEMA,
            "campaign_id": preflight["campaign_id"],
            "dispatchable_count": len(selected),
            "files_written": len(selected) + 2,
            "source_board_current": True,
            "contains_personal_data_in_private_files": True,
            "personal_data_echoed_to_summary": False,
            "network_delivery_performed": False,
            "control_execution_performed": False,
            "campaign_mutated": False,
            "evidence_mutated": False,
            "release_authorization_changed": False,
        }


__all__ = [
    "DISPATCH_MANIFEST_SCHEMA",
    "DISPATCHABLE_STATUSES",
    "PREFLIGHT_SCHEMA",
    "PrivateDispatchGuardError",
    "PrivateExecutionDispatchGuard",
]
