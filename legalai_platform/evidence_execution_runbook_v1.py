from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from legalai_platform.evidence_execution_plan_v1 import EvidenceExecutionPlan
from legalai_platform.evidence_orchestration_v1_rc8_1 import EvidenceCampaignLedger


RUNBOOK_SCHEMA = "legalaiz-v1-ops1-real-evidence-execution-runbook-v1"
FORBIDDEN_OUTPUT_KEYS = frozenset({
    "evidence_ref",
    "evidence_event_id",
    "actor",
    "actor_id",
    "environment_fingerprint",
    "password",
    "token",
    "api_key",
    "secret",
    "credential",
    "private_key",
})


class EvidenceExecutionRunbookError(RuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().casefold() in FORBIDDEN_OUTPUT_KEYS:
                findings.append(child_path)
            findings.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return findings


class EvidenceExecutionRunbook:
    """Vista operativa derivada de RC6/RC8.1; no contiene ni crea evidencia."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.plan = EvidenceExecutionPlan(self.root)
        validation = self.plan.validate()
        if not validation.valid:
            raise EvidenceExecutionRunbookError(
                "El execution plan RC6 no es estructuralmente válido: " + ", ".join(validation.errors)
            )
        self.ledger = EvidenceCampaignLedger(self.root)
        self.controls = {str(row["ref"]): row for row in self.plan.plan["controls"]}
        self.plan_path = self.root / "config" / "v1" / "evidence_execution_plan.json"

    @property
    def plan_sha256(self) -> str:
        return sha256(self.plan_path.read_bytes()).hexdigest()

    def _waves(self) -> list[list[str]]:
        remaining = set(self.controls)
        completed: set[str] = set()
        waves: list[list[str]] = []
        while remaining:
            ready = sorted(
                ref
                for ref in remaining
                if set(str(dep) for dep in (self.controls[ref].get("prerequisites") or [])) <= completed
            )
            if not ready:
                raise EvidenceExecutionRunbookError("Las dependencias RC6 no permiten construir un orden de ejecución.")
            waves.append(ready)
            completed.update(ready)
            remaining.difference_update(ready)
        return waves

    def build(self) -> dict[str, Any]:
        waves = self._waves()
        wave_index = {ref: index for index, refs in enumerate(waves, 1) for ref in refs}
        packets: list[dict[str, Any]] = []
        for sequence, ref in enumerate(ref for wave in waves for ref in wave, 1):
            packet = dict(self.ledger.task_packet(ref))
            packet.pop("evidence_ref", None)
            packet.update({
                "sequence": sequence,
                "wave": wave_index[ref],
                "execution_status": "PENDING_EXTERNAL_EXECUTION",
                "assignment_status": "ROLE_DEFINED_PERSON_NOT_ASSIGNED",
                "coordination_commands": {
                    "inspect_packet": f'python tools/v1_evidence_campaign.py packet --control "{ref}"',
                    "start_control": (
                        'python tools/v1_evidence_campaign.py start-control '
                        f'--campaign "<CAMPAIGN_ID>" --control "{ref}" '
                        '--actor-id "<EXECUTOR_ID>" '
                        f'--actor-role "{packet["executor_role"]}"'
                    ),
                    "campaign_status": 'python tools/v1_evidence_campaign.py status --campaign "<CAMPAIGN_ID>"',
                },
                "human_actions_required": [
                    "Asignar una persona real al rol ejecutor y una persona distinta al rol revisor.",
                    "Ejecutar materialmente el control en el entorno declarado; la CLI sólo coordina.",
                    "Recolectar, redactar y custodiar todos los artefactos obligatorios.",
                    "Registrar la evidencia en el dossier canónico correspondiente y conservar su referencia interna.",
                    "Completar revisión independiente y ratificación cuando el framework aplicable lo requiera.",
                ],
            })
            packets.append(packet)

        result = {
            "schema": RUNBOOK_SCHEMA,
            "schema_version": 1,
            "source_plan_schema": self.plan.plan.get("schema"),
            "source_plan_sha256": self.plan_sha256,
            "status": "READY_FOR_HUMAN_EXTERNAL_EXECUTION",
            "controls": len(packets),
            "waves": [
                {"wave": index, "controls": refs, "count": len(refs)}
                for index, refs in enumerate(waves, 1)
            ],
            "packets": packets,
            "global_flow": [
                "Crear una campaña RC8.1 fijando revisión Git y fingerprint opaco del entorno.",
                "Asignar personas reales a los roles definidos; ejecutor y revisor deben permanecer separados.",
                "Trabajar por olas. Una dependencia debe estar VERIFIED antes de iniciar el control dependiente.",
                "Registrar sólo el inicio de coordinación; el start-control no ejecuta la prueba externa.",
                "Ejecutar el control fuera de la coordinación y producir exactamente los artefactos RC6 requeridos.",
                "Redactar secretos, PII y detalles explotables antes de cualquier copia de auditoría.",
                "Registrar la evidencia auténtica en RC2 o RC7 y luego vincularla a la campaña RC8.1.",
                "Completar revisión independiente y ratificación sin confundirlas con autorización de go-live.",
                "Repetir hasta que los 22 controles estén verificados y vigentes.",
                "Generar RC9 Evidence Audit Pack y RC10 Custody Export para auditoría y anclaje externo.",
                "Sólo después, tramitar las decisiones humanas versionadas de producción y pagos por separado.",
            ],
            "governance": {
                "derived_from_rc6_and_rc8_1": True,
                "runbook_is_not_evidence": True,
                "runbook_is_not_execution": True,
                "runbook_is_not_review_approval": True,
                "runbook_is_not_release_ratification": True,
                "runbook_is_not_production_authorization": True,
                "runbook_is_not_payment_authorization": True,
                "contains_evidence_payload": False,
                "contains_evidence_reference": False,
                "contains_actor_identifier": False,
                "contains_environment_fingerprint": False,
                "mutates_campaign": False,
                "mutates_evidence_ledgers": False,
                "mutates_release_metadata": False,
            },
        }
        forbidden = _forbidden_paths(result)
        if forbidden:
            raise EvidenceExecutionRunbookError("El runbook contiene claves prohibidas: " + ", ".join(forbidden))
        result["runbook_sha256"] = sha256(_canonical_json(result).encode("utf-8")).hexdigest()
        return result

    def to_markdown(self, runbook: dict[str, Any] | None = None) -> str:
        data = runbook or self.build()
        lines = [
            "# LegalAIZ.it — Runbook operativo de evidencia V1",
            "",
            f"- Estado: **{data['status']}**",
            f"- Controles: **{data['controls']}**",
            f"- Olas de ejecución: **{len(data['waves'])}**",
            f"- Plan RC6: `{data['source_plan_sha256']}`",
            f"- Digest del runbook: `{data['runbook_sha256']}`",
            "",
            "> Este runbook coordina trabajo humano. No ejecuta controles, no constituye evidencia y no autoriza producción ni pagos.",
            "",
            "## Flujo global",
            "",
        ]
        for index, step in enumerate(data["global_flow"], 1):
            lines.append(f"{index}. {step}")

        lines.extend(["", "## Olas de ejecución", ""])
        packets = {row["control_ref"]: row for row in data["packets"]}
        for wave in data["waves"]:
            lines.extend([f"### Ola {wave['wave']} · {wave['count']} controles", ""])
            for ref in wave["controls"]:
                packet = packets[ref]
                dependencies = ", ".join(packet["prerequisites"]) or "Ninguna"
                lines.extend([
                    f"#### {packet['sequence']}. `{ref}`",
                    "",
                    f"- Dominio: `{packet['domain']}`",
                    f"- Entorno: `{packet['environment']}`",
                    f"- Alcance: `{packet['release_scope']}`",
                    f"- Ejecuta: `{packet['executor_role']}`",
                    f"- Revisa: `{packet['reviewer_role']}`",
                    f"- Dependencias: {dependencies}",
                    f"- Vigencia máxima: {packet['max_validity_days']} días",
                    f"- Bundle: `{packet['artifact_type']}`",
                    f"- Estado inicial: `{packet['execution_status']}`",
                    "",
                    "**Artefactos obligatorios**",
                    "",
                ])
                lines.extend(f"- `{artifact}`" for artifact in packet["required_artifacts"])
                lines.extend(["", "**Checklist operativo**", ""])
                lines.extend(f"- {step}" for step in packet["operator_checklist"])
                lines.extend(["", "**Acciones humanas adicionales**", ""])
                lines.extend(f"- {step}" for step in packet["human_actions_required"])
                lines.extend([
                    "",
                    "**Redacción**",
                    "",
                    packet["redaction_policy"],
                    "",
                    "**Comandos de coordinación**",
                    "",
                    "```text",
                    packet["coordination_commands"]["inspect_packet"],
                    packet["coordination_commands"]["start_control"],
                    packet["coordination_commands"]["campaign_status"],
                    "```",
                    "",
                ])

        lines.extend([
            "## Cierre de campaña",
            "",
            "La terminación técnica de los 22 controles sólo demuestra que existe evidencia verificada y vigente bajo los dossiers aplicables. No cambia por sí misma `REAL_PRODUCTION_AUTHORIZED` ni `REAL_PAYMENTS_AUTHORIZED`. Después de la evidencia deben existir las decisiones humanas versionadas y separadas que correspondan.",
            "",
        ])
        return "\n".join(lines)


__all__ = ["EvidenceExecutionRunbook", "EvidenceExecutionRunbookError", "RUNBOOK_SCHEMA"]
