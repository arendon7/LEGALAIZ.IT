from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import tempfile
from typing import Any

from legalai_platform.evidence_execution_board_v1 import (
    EvidenceOperationsBoard,
    EvidenceOperationsBoardError,
)


ASSIGNMENT_INPUT_SCHEMA = "legalaiz-v1-ops3-private-assignment-input-v1"
ASSIGNMENT_MANIFEST_SCHEMA = "legalaiz-v1-ops3-private-assignment-manifest-v1"
VALIDATION_SCHEMA = "legalaiz-v1-ops3-private-assignment-validation-v1"
PRIVATE_TOP_LEVEL_DIRS = frozenset({"runtime", "secrets", "output", "artifacts", "generated"})
PERSON_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ACTOR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@:-]{0,127}$")
CONTROL_FILE_RE = re.compile(r"[^A-Za-z0-9._-]+")
MAX_NAME = 120
MAX_CONTACT = 200


class PrivateAssignmentError(RuntimeError):
    pass


def _clean_text(value: Any, *, field: str, limit: int, required: bool = True) -> str:
    text = " ".join(str(value or "").replace("\x00", "").split())
    if required and not text:
        raise PrivateAssignmentError(f"{field} es obligatorio.")
    if len(text) > limit:
        raise PrivateAssignmentError(f"{field} excede {limit} caracteres.")
    return text


def _exact_keys(row: dict[str, Any], *, allowed: set[str], required: set[str], label: str) -> None:
    extra = sorted(set(row) - allowed)
    missing = sorted(required - set(row))
    if extra:
        raise PrivateAssignmentError(f"{label} contiene claves no permitidas: {', '.join(extra)}")
    if missing:
        raise PrivateAssignmentError(f"{label} omite claves obligatorias: {', '.join(missing)}")


def _safe_control_filename(control_ref: str) -> str:
    slug = CONTROL_FILE_RE.sub("-", control_ref).strip("-._")
    if not slug:
        raise PrivateAssignmentError("No fue posible derivar un nombre seguro para el control.")
    return f"{slug}.md"


class PrivateAssignmentPacketGenerator:
    """Genera paquetes locales con PII; nunca escribe en campañas, dossiers o Git."""

    def __init__(self, root: str | Path, *, ledger_path: str | Path | None = None) -> None:
        self.root = Path(root).resolve()
        self.ledger_path = Path(ledger_path).expanduser() if ledger_path is not None else None

    def _assert_private_location(self, path: str | Path, *, label: str, must_exist: bool) -> Path:
        raw = Path(path).expanduser().absolute()
        try:
            relative = raw.relative_to(self.root)
        except ValueError:
            relative = None
        if relative is not None:
            top = relative.parts[0] if relative.parts else ""
            if top not in PRIVATE_TOP_LEVEL_DIRS:
                raise PrivateAssignmentError(
                    f"{label} no puede vivir en una ruta versionable del repositorio; use runtime/, secrets/, output/, artifacts/, generated/ o una ruta externa."
                )
        if must_exist:
            if not raw.exists() or not raw.is_file():
                raise PrivateAssignmentError(f"{label} no existe o no es un archivo regular.")
            if raw.is_symlink():
                raise PrivateAssignmentError(f"{label} no puede ser un enlace simbólico.")
            return raw.resolve(strict=True)
        if raw.exists() and raw.is_symlink():
            raise PrivateAssignmentError(f"{label} no puede ser un enlace simbólico.")
        return raw

    def _load_input(self, assignment_path: str | Path) -> dict[str, Any]:
        path = self._assert_private_location(assignment_path, label="assignment input", must_exist=True)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrivateAssignmentError("El assignment input no es JSON UTF-8 válido.") from exc
        if not isinstance(payload, dict):
            raise PrivateAssignmentError("El assignment input debe ser un objeto JSON.")
        _exact_keys(
            payload,
            allowed={"schema", "campaign_id", "people", "assignments"},
            required={"schema", "campaign_id", "people", "assignments"},
            label="assignment input",
        )
        if payload.get("schema") != ASSIGNMENT_INPUT_SCHEMA:
            raise PrivateAssignmentError("Schema de assignment input no soportado.")
        return payload

    def _board(self, campaign_id: str) -> dict[str, Any]:
        try:
            board = EvidenceOperationsBoard(
                self.root,
                campaign_id=campaign_id,
                ledger_path=self.ledger_path,
            ).build()
        except EvidenceOperationsBoardError as exc:
            raise PrivateAssignmentError(str(exc)) from exc
        campaign = board["campaign"]
        if not campaign.get("bound"):
            raise PrivateAssignmentError("OPS3 requiere una campaña RC8.1 real.")
        if campaign.get("campaign_id") != campaign_id:
            raise PrivateAssignmentError("La campaña resuelta no coincide con el assignment input.")
        if not campaign.get("plan_hash_current"):
            raise PrivateAssignmentError("La campaña tiene PLAN_DRIFT; no se pueden emitir asignaciones.")
        if str(campaign.get("status")) == "ABORTED":
            raise PrivateAssignmentError("La campaña está abortada; no se pueden emitir asignaciones.")
        return board

    def validate(self, assignment_path: str | Path) -> dict[str, Any]:
        payload = self._load_input(assignment_path)
        campaign_id = _clean_text(payload.get("campaign_id"), field="campaign_id", limit=128)
        board = self._board(campaign_id)
        controls = {str(row["control_ref"]): row for row in board["controls"]}
        allowed_roles = {
            str(role)
            for row in controls.values()
            for role in (row["executor_role"], row["reviewer_role"])
        }

        people_raw = payload.get("people")
        assignments_raw = payload.get("assignments")
        if not isinstance(people_raw, list) or not people_raw:
            raise PrivateAssignmentError("people debe ser una lista no vacía.")
        if not isinstance(assignments_raw, list):
            raise PrivateAssignmentError("assignments debe ser una lista.")

        people: dict[str, dict[str, Any]] = {}
        actor_ids: set[str] = set()
        for index, raw_person in enumerate(people_raw, 1):
            if not isinstance(raw_person, dict):
                raise PrivateAssignmentError(f"people[{index}] debe ser objeto.")
            _exact_keys(
                raw_person,
                allowed={"person_ref", "display_name", "actor_id", "roles", "contact"},
                required={"person_ref", "display_name", "actor_id", "roles"},
                label=f"people[{index}]",
            )
            person_ref = _clean_text(raw_person.get("person_ref"), field=f"people[{index}].person_ref", limit=64)
            actor_id = _clean_text(raw_person.get("actor_id"), field=f"people[{index}].actor_id", limit=128)
            display_name = _clean_text(raw_person.get("display_name"), field=f"people[{index}].display_name", limit=MAX_NAME)
            contact = _clean_text(raw_person.get("contact"), field=f"people[{index}].contact", limit=MAX_CONTACT, required=False)
            roles_raw = raw_person.get("roles")
            if not PERSON_REF_RE.fullmatch(person_ref):
                raise PrivateAssignmentError(f"person_ref inválido: {person_ref!r}")
            if not ACTOR_ID_RE.fullmatch(actor_id):
                raise PrivateAssignmentError(f"actor_id inválido para {person_ref}.")
            if person_ref in people:
                raise PrivateAssignmentError(f"person_ref duplicado: {person_ref}")
            if actor_id in actor_ids:
                raise PrivateAssignmentError("Un actor_id real no puede representarse mediante dos person_ref distintos.")
            if not isinstance(roles_raw, list) or not roles_raw:
                raise PrivateAssignmentError(f"roles inválidos para {person_ref}.")
            roles = []
            for role in roles_raw:
                normalized = _clean_text(role, field=f"roles de {person_ref}", limit=64)
                if normalized not in allowed_roles:
                    raise PrivateAssignmentError(f"Rol no utilizado por OPS1/OPS2: {normalized}")
                if normalized not in roles:
                    roles.append(normalized)
            people[person_ref] = {
                "person_ref": person_ref,
                "display_name": display_name,
                "actor_id": actor_id,
                "roles": roles,
                "contact": contact,
            }
            actor_ids.add(actor_id)

        assignments: dict[str, dict[str, str]] = {}
        for index, raw_assignment in enumerate(assignments_raw, 1):
            if not isinstance(raw_assignment, dict):
                raise PrivateAssignmentError(f"assignments[{index}] debe ser objeto.")
            _exact_keys(
                raw_assignment,
                allowed={"control_ref", "executor_person_ref", "reviewer_person_ref"},
                required={"control_ref", "executor_person_ref", "reviewer_person_ref"},
                label=f"assignments[{index}]",
            )
            control_ref = _clean_text(raw_assignment.get("control_ref"), field=f"assignments[{index}].control_ref", limit=160)
            executor_ref = _clean_text(raw_assignment.get("executor_person_ref"), field=f"assignments[{index}].executor_person_ref", limit=64)
            reviewer_ref = _clean_text(raw_assignment.get("reviewer_person_ref"), field=f"assignments[{index}].reviewer_person_ref", limit=64)
            if control_ref not in controls:
                raise PrivateAssignmentError(f"Control no canónico: {control_ref}")
            if control_ref in assignments:
                raise PrivateAssignmentError(f"Control duplicado en assignments: {control_ref}")
            if executor_ref not in people or reviewer_ref not in people:
                raise PrivateAssignmentError(f"Asignación {control_ref} referencia una persona inexistente.")
            if executor_ref == reviewer_ref:
                raise PrivateAssignmentError(f"Separación de funciones inválida en {control_ref}: ejecutor y revisor deben ser personas distintas.")
            executor = people[executor_ref]
            reviewer = people[reviewer_ref]
            expected_executor = str(controls[control_ref]["executor_role"])
            expected_reviewer = str(controls[control_ref]["reviewer_role"])
            if expected_executor not in executor["roles"]:
                raise PrivateAssignmentError(f"{executor_ref} no posee el rol ejecutor {expected_executor} requerido por {control_ref}.")
            if expected_reviewer not in reviewer["roles"]:
                raise PrivateAssignmentError(f"{reviewer_ref} no posee el rol revisor {expected_reviewer} requerido por {control_ref}.")
            assignments[control_ref] = {
                "executor_person_ref": executor_ref,
                "reviewer_person_ref": reviewer_ref,
            }

        missing = sorted(set(controls) - set(assignments))
        extra = sorted(set(assignments) - set(controls))
        if missing or extra or len(assignments) != len(controls):
            details = []
            if missing:
                details.append("faltan=" + ",".join(missing))
            if extra:
                details.append("sobran=" + ",".join(extra))
            raise PrivateAssignmentError("La asignación debe cubrir exactamente los 22 controles: " + "; ".join(details))

        used_refs = {
            ref
            for assignment in assignments.values()
            for ref in (assignment["executor_person_ref"], assignment["reviewer_person_ref"])
        }
        unused = sorted(set(people) - used_refs)
        if unused:
            raise PrivateAssignmentError("people contiene personas no asignadas: " + ", ".join(unused))

        return {
            "schema": VALIDATION_SCHEMA,
            "campaign_id": campaign_id,
            "campaign_status": board["campaign"]["status"],
            "controls": len(assignments),
            "people_count": len(people),
            "people": people,
            "assignments": assignments,
            "board": board,
            "separation_of_duties_valid": True,
            "contains_personal_data": True,
            "repository_persistence_allowed": False,
            "ledger_mutation_allowed": False,
            "release_authorization_changed": False,
        }

    @staticmethod
    def public_validation_summary(validated: dict[str, Any]) -> dict[str, Any]:
        board = validated["board"]
        return {
            "schema": VALIDATION_SCHEMA,
            "campaign_id": validated["campaign_id"],
            "campaign_status": validated["campaign_status"],
            "controls": validated["controls"],
            "people_count": validated["people_count"],
            "waves": len(board["waves"]),
            "separation_of_duties_valid": True,
            "contains_personal_data_in_input": True,
            "personal_data_echoed": False,
            "repository_persistence_allowed": False,
            "ledger_mutation_allowed": False,
            "release_authorization_changed": False,
        }

    def _packet_markdown(
        self,
        *,
        campaign_id: str,
        control: dict[str, Any],
        executor: dict[str, Any],
        reviewer: dict[str, Any],
    ) -> str:
        def show(value: str) -> str:
            return value.replace("`", "'")

        artifacts = "\n".join(f"- `{item}`" for item in control["required_artifacts"])
        dependencies = ", ".join(control["prerequisites"]) or "Ninguna"
        blockers = ", ".join(control["dependency_blockers"]) or "Ninguno"
        command = (
            "python tools/v1_evidence_campaign.py start-control "
            f"--campaign {shlex.quote(campaign_id)} "
            f"--control {shlex.quote(str(control['control_ref']))} "
            f"--actor-id {shlex.quote(str(executor['actor_id']))} "
            f"--actor-role {shlex.quote(str(control['executor_role']))}"
        )
        contact_executor = show(executor["contact"]) if executor["contact"] else "No suministrado"
        contact_reviewer = show(reviewer["contact"]) if reviewer["contact"] else "No suministrado"
        return "\n".join([
            "# LegalAIZ.it — Paquete privado de asignación",
            "",
            "> **CONFIDENCIAL / DATOS PERSONALES.** Mantener únicamente en almacenamiento privado autorizado. Este archivo no es evidencia, aprobación, ratificación ni autorización de go-live.",
            "",
            f"- Campaña: `{campaign_id}`",
            f"- Control: `{control['control_ref']}`",
            f"- Ola: **{control['wave']}**",
            f"- Estado OPS2: `{control['work_status']}`",
            f"- Siguiente acción OPS2: `{control['next_action']}`",
            f"- Dependencias: {dependencies}",
            f"- Dependencias pendientes: {blockers}",
            f"- Entorno: `{control['environment']}`",
            f"- Alcance: `{control['release_scope']}`",
            "",
            "## Ejecutor",
            "",
            f"- Persona: **{show(executor['display_name'])}**",
            f"- Person ref local: `{executor['person_ref']}`",
            f"- Actor ID: `{show(executor['actor_id'])}`",
            f"- Rol requerido: `{control['executor_role']}`",
            f"- Contacto: {contact_executor}",
            "",
            "## Revisor independiente",
            "",
            f"- Persona: **{show(reviewer['display_name'])}**",
            f"- Person ref local: `{reviewer['person_ref']}`",
            f"- Actor ID: `{show(reviewer['actor_id'])}`",
            f"- Rol requerido: `{control['reviewer_role']}`",
            f"- Contacto: {contact_reviewer}",
            "",
            "**Separación de funciones:** validada; ejecutor y revisor son identidades distintas para este control.",
            "",
            "## Artefactos obligatorios",
            "",
            artifacts,
            "",
            f"Vigencia máxima del control: **{control['max_validity_days']} días**.",
            "",
            "## Redacción y custodia",
            "",
            str(control["redaction_policy"]),
            "",
            "No copiar secretos, credenciales, datos personales innecesarios ni detalles explotables al audit pack. La evidencia auténtica debe registrarse exclusivamente mediante los dossiers canónicos RC2/RC7.",
            "",
            "## Coordinación",
            "",
            "El siguiente comando **sólo registra inicio de coordinación** y sólo debe utilizarse si OPS2 muestra que el control puede iniciarse. No ejecuta la prueba externa:",
            "",
            "```text",
            command,
            "```",
            "",
            "La revisión y eventual ratificación se completan después por los flujos canónicos aplicables. Este paquete no sustituye ninguna de esas etapas.",
            "",
        ])

    def write(self, assignment_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
        validated = self.validate(assignment_path)
        target = self._assert_private_location(output_dir, label="output dir", must_exist=False)
        if target.exists():
            raise PrivateAssignmentError("El output dir ya existe; OPS3 no sobrescribe paquetes privados.")
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        if parent.is_symlink():
            raise PrivateAssignmentError("El directorio padre de salida no puede ser un enlace simbólico.")

        board = validated["board"]
        controls = {str(row["control_ref"]): row for row in board["controls"]}
        people = validated["people"]
        assignments = validated["assignments"]
        temp_dir = Path(tempfile.mkdtemp(prefix=".ops3-", dir=str(parent)))
        os.chmod(temp_dir, 0o700)
        created = 0
        try:
            packets_dir = temp_dir / "controls"
            packets_dir.mkdir(mode=0o700)
            manifest_rows = []
            for control in sorted(controls.values(), key=lambda row: int(row["sequence"])):
                ref = str(control["control_ref"])
                assignment = assignments[ref]
                executor = people[assignment["executor_person_ref"]]
                reviewer = people[assignment["reviewer_person_ref"]]
                filename = _safe_control_filename(ref)
                packet_path = packets_dir / filename
                content = self._packet_markdown(
                    campaign_id=validated["campaign_id"],
                    control=control,
                    executor=executor,
                    reviewer=reviewer,
                )
                fd = os.open(packet_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(content)
                created += 1
                manifest_rows.append({
                    "sequence": int(control["sequence"]),
                    "wave": int(control["wave"]),
                    "control_ref": ref,
                    "work_status": control["work_status"],
                    "executor_role": control["executor_role"],
                    "reviewer_role": control["reviewer_role"],
                    "packet_file": f"controls/{filename}",
                    "contains_personal_data": True,
                })

            manifest = {
                "schema": ASSIGNMENT_MANIFEST_SCHEMA,
                "campaign_id": validated["campaign_id"],
                "source_board_sha256": board["board_sha256"],
                "controls": len(manifest_rows),
                "waves": len(board["waves"]),
                "packets": manifest_rows,
                "manifest_contains_personal_data": False,
                "packet_files_contain_personal_data": True,
                "input_copied": False,
                "packet_hashes_persisted": False,
                "repository_persistence_allowed": False,
                "campaign_mutated": False,
                "evidence_mutated": False,
                "release_authorization_changed": False,
            }
            manifest_path = temp_dir / "assignment-manifest.json"
            fd = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            created += 1

            notice_path = temp_dir / "README_PRIVATE.md"
            notice = "\n".join([
                "# LegalAIZ.it — Custodia de paquetes privados OPS3",
                "",
                "Este directorio contiene archivos con datos personales de responsables humanos.",
                "",
                "- No versionar ni adjuntar a PR/Issue.",
                "- No subir como artifact de CI.",
                "- No copiar a RC9/RC10.",
                "- Mantener acceso bajo mínimo privilegio.",
                "- Eliminar conforme a la política interna aplicable una vez cumplida su finalidad.",
                "- La asignación no constituye ejecución, evidencia, aprobación, ratificación ni autorización de producción/pagos.",
                "",
            ])
            fd = os.open(notice_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(notice)
            created += 1

            os.replace(temp_dir, target)
            os.chmod(target, 0o700)
            os.chmod(target / "controls", 0o700)
            for file_path in target.rglob("*"):
                if file_path.is_file():
                    os.chmod(file_path, 0o600)
        except Exception:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return {
            "schema": ASSIGNMENT_MANIFEST_SCHEMA,
            "campaign_id": validated["campaign_id"],
            "controls": validated["controls"],
            "people_count": validated["people_count"],
            "files_written": created,
            "packet_files": len(controls),
            "contains_personal_data_in_private_files": True,
            "personal_data_echoed_to_summary": False,
            "repository_persistence_allowed": False,
            "campaign_mutated": False,
            "evidence_mutated": False,
            "release_authorization_changed": False,
        }


__all__ = [
    "ASSIGNMENT_INPUT_SCHEMA",
    "ASSIGNMENT_MANIFEST_SCHEMA",
    "PrivateAssignmentError",
    "PrivateAssignmentPacketGenerator",
    "VALIDATION_SCHEMA",
]
