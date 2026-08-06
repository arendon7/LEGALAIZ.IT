from __future__ import annotations

"""Operación auditable del portafolio documental M32.6.

Esta capa no sustituye la revisión jurídica ni QA del documento concreto. Añade
asignación, prioridad, SLA, alertas, actividad y un expediente exportable sobre
la Mesa Jurídica M32.5, conservando cada cambio como un evento append-only con
cadena SHA-256 independiente.
"""

from datetime import datetime, timedelta
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

import core_v11 as core
from legalai_platform.approval_desk_workspace import (
    ApprovalDeskError,
    ApprovalDeskWorkspace,
    PermissionDenied,
    ReleaseBlocked,
)


M32_6_SCHEMA = "M32.6"
BOGOTA = ZoneInfo("America/Bogota")
PRIORITIES = frozenset({"critical", "high", "normal", "low"})
DEFAULT_SLA_HOURS = {"critical": 4, "high": 24, "normal": 72, "low": 120}
PROFESSIONAL_ROLES = frozenset({"specialist", "admin", "qa"})
QA_ROLES = frozenset({"admin", "qa"})
_LOCK = RLock()

PORTFOLIO_PRODUCTS = (
    {"code": "CO-EM-003", "name": "Contrato de prestación de servicios"},
    {"code": "CO-EM-004", "name": "Acuerdo de confidencialidad y propiedad intelectual"},
    {"code": "CO-AR-001", "name": "Contrato de arrendamiento"},
    {"code": "CO-LA-001", "name": "Contrato laboral"},
    {"code": "CO-LA-002", "name": "Contrato de trabajo a término indefinido"},
    {"code": "CO-TR-001", "name": "Actuación de tránsito"},
    {"code": "CO-TR-002", "name": "Recurso de tránsito"},
    {"code": "CO-SA-001", "name": "Solicitud en salud"},
    {"code": "CO-CD-001", "name": "Derecho de petición"},
    {"code": "CO-CD-003", "name": "Reclamación de consumidor"},
    {"code": "CO-CD-004", "name": "Protección de datos personales"},
)
PORTFOLIO_CODES = tuple(item["code"] for item in PORTFOLIO_PRODUCTS)


class OperationsIntegrityError(ApprovalDeskError):
    pass


def _now_dt() -> datetime:
    return datetime.now(BOGOTA)


def _now() -> str:
    return _now_dt().isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_segment(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ApprovalDeskError(f"{field} contiene caracteres no permitidos.")
    return text


def _parse_datetime(value: str, field: str = "fecha") -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ApprovalDeskError(f"{field} es obligatoria.")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalDeskError(f"{field} debe usar formato ISO 8601.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BOGOTA)
    return parsed.astimezone(BOGOTA)


def _actor(user: dict[str, Any]) -> dict[str, str]:
    actor_id = str(user.get("id") or "").strip()
    role = str(user.get("role") or "").strip().casefold()
    if not actor_id or role not in PROFESSIONAL_ROLES:
        raise PermissionDenied("La operación requiere un actor profesional autenticado.")
    return {"id": actor_id, "role": role, "name": str(user.get("name") or "").strip()}


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ApprovalDeskOperations:
    """Gobierno operativo complementario de la Mesa Jurídica."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        workspace: ApprovalDeskWorkspace | None = None,
        db_factory: Callable[[], Any] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self.root = Path(root or (core.RUNTIME / "approval-desk")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.workspace = workspace or ApprovalDeskWorkspace(self.root)
        self.db_factory = db_factory or core.db
        self.now_factory = now_factory or _now_dt

    def _case_dir(self, case_id: str) -> Path:
        return self.root / _safe_segment(case_id, "desk_case_id")

    def _events_path(self, case_id: str) -> Path:
        return self._case_dir(case_id) / "operations.jsonl"

    def _read_events(self, case_id: str) -> list[dict[str, Any]]:
        path = self._events_path(case_id)
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise OperationsIntegrityError("La bitácora operativa contiene un registro inválido.")
                events.append(item)
        return events

    def verify_chain(self, case_id: str) -> dict[str, Any]:
        previous = "0" * 64
        events = self._read_events(case_id)
        for expected_sequence, event in enumerate(events, 1):
            stored_hash = str(event.get("event_hash") or "")
            candidate = dict(event)
            candidate.pop("event_hash", None)
            calculated = sha256(_canonical_json(candidate).encode("utf-8")).hexdigest()
            if (
                int(event.get("sequence") or 0) != expected_sequence
                or event.get("previous_hash") != previous
                or stored_hash != calculated
            ):
                return {
                    "valid": False,
                    "events": len(events),
                    "failed_sequence": expected_sequence,
                    "last_hash": previous,
                }
            previous = stored_hash
        return {"valid": True, "events": len(events), "failed_sequence": None, "last_hash": previous}

    def _append_event(
        self,
        case_id: str,
        event_type: str,
        user: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        actor = _actor(user)
        path = self._events_path(case_id)
        with _LOCK:
            integrity = self.verify_chain(case_id)
            if not integrity["valid"]:
                raise OperationsIntegrityError("La cadena operativa está alterada; no se admiten nuevas actuaciones.")
            sequence = int(integrity["events"]) + 1
            event = {
                "schema_version": M32_6_SCHEMA,
                "sequence": sequence,
                "event_id": f"OPS-{sequence:06d}",
                "event_type": str(event_type),
                "created_at": self.now_factory().astimezone(BOGOTA).isoformat(timespec="seconds"),
                "actor": actor,
                "payload": payload,
                "previous_hash": integrity["last_hash"],
            }
            event["event_hash"] = sha256(_canonical_json(event).encode("utf-8")).hexdigest()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return event

    @staticmethod
    def _current_revision(detail: dict[str, Any]) -> dict[str, Any] | None:
        current_id = detail.get("case", {}).get("current_revision_id")
        return next((item for item in detail.get("revisions", []) if item.get("revision_id") == current_id), None)

    def _state_from_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        state: dict[str, Any] = {
            "assigned_specialist": None,
            "assigned_qa": None,
            "priority": "normal",
            "sla_hours": DEFAULT_SLA_HOURS["normal"],
            "due_at": None,
            "notes": [],
            "acknowledged_alerts": {},
            "last_operational_update": None,
        }
        for event in events:
            payload = event.get("payload") or {}
            event_type = event.get("event_type")
            if event_type == "assignment.updated":
                state["assigned_specialist"] = payload.get("specialist")
                state["assigned_qa"] = payload.get("qa")
            elif event_type == "priority.updated":
                state["priority"] = payload.get("priority") or state["priority"]
                state["sla_hours"] = int(payload.get("sla_hours") or state["sla_hours"])
                state["due_at"] = payload.get("due_at") or state["due_at"]
            elif event_type == "deadline.updated":
                state["due_at"] = payload.get("due_at")
                state["sla_hours"] = int(payload.get("sla_hours") or state["sla_hours"])
            elif event_type == "note.added":
                state["notes"].append({
                    "event_id": event.get("event_id"),
                    "created_at": event.get("created_at"),
                    "actor": event.get("actor"),
                    "text": payload.get("text"),
                })
            elif event_type == "alert.acknowledged":
                code = str(payload.get("code") or "")
                if code:
                    state["acknowledged_alerts"][code] = {
                        "created_at": event.get("created_at"),
                        "actor": event.get("actor"),
                        "comment": payload.get("comment"),
                    }
            state["last_operational_update"] = event.get("created_at")
        return state

    def _sla(self, state: dict[str, Any], workflow_status: str) -> dict[str, Any]:
        due_at = state.get("due_at")
        if workflow_status == "released":
            return {"status": "closed", "due_at": due_at, "hours_remaining": None, "percent_elapsed": 100}
        if not due_at:
            return {"status": "not_scheduled", "due_at": None, "hours_remaining": None, "percent_elapsed": None}
        due = _parse_datetime(due_at, "due_at")
        now = self.now_factory().astimezone(BOGOTA)
        remaining = (due - now).total_seconds() / 3600
        sla_hours = max(1, int(state.get("sla_hours") or 1))
        elapsed_percent = max(0, min(100, round((1 - max(remaining, 0) / sla_hours) * 100)))
        if remaining < 0:
            status = "overdue"
        elif remaining <= max(4, sla_hours * 0.2):
            status = "at_risk"
        else:
            status = "in_time"
        return {
            "status": status,
            "due_at": due.isoformat(timespec="seconds"),
            "hours_remaining": round(remaining, 1),
            "percent_elapsed": elapsed_percent,
        }

    def _alerts(
        self,
        detail: dict[str, Any],
        state: dict[str, Any],
        integrity: dict[str, Any],
        sla: dict[str, Any],
    ) -> list[dict[str, Any]]:
        workflow = str(detail.get("workflow_status") or "")
        current = self._current_revision(detail) or {}
        findings = current.get("findings") or []
        approvals = current.get("approvals") or {}
        alerts: list[dict[str, Any]] = []

        def add(code: str, severity: str, title: str, description: str) -> None:
            acknowledgement = state.get("acknowledged_alerts", {}).get(code)
            alerts.append({
                "code": code,
                "severity": severity,
                "title": title,
                "description": description,
                "acknowledged": bool(acknowledgement),
                "acknowledgement": acknowledgement,
            })

        if not integrity.get("valid"):
            add("operations_chain_invalid", "critical", "Cadena operativa inválida", "La bitácora M32.6 fue alterada y requiere investigación antes de continuar.")
        if not detail.get("audit", {}).get("valid"):
            add("approval_chain_invalid", "critical", "Cadena de aprobación inválida", "La liberación y descarga permanecen bloqueadas por la Mesa Jurídica.")
        if not state.get("assigned_specialist"):
            add("specialist_unassigned", "high", "Especialista sin asignar", "El documento no tiene responsable jurídico operativo.")
        if not state.get("assigned_qa"):
            add("qa_unassigned", "high", "QA sin asignar", "No existe responsable independiente para la compuerta QA.")
        if state.get("assigned_specialist") and state.get("assigned_qa") and state["assigned_specialist"].get("id") == state["assigned_qa"].get("id"):
            add("separation_conflict", "critical", "Conflicto de separación de funciones", "La responsabilidad jurídica y QA no puede recaer en la misma persona.")
        if sla["status"] == "not_scheduled":
            add("deadline_missing", "medium", "Vencimiento no programado", "Administración debe definir una fecha objetivo o aceptar el SLA sugerido.")
        elif sla["status"] == "overdue":
            add("sla_overdue", "critical", "SLA vencido", f"La fecha objetivo venció hace {abs(sla['hours_remaining']):.1f} horas.")
        elif sla["status"] == "at_risk":
            add("sla_at_risk", "high", "SLA próximo a vencer", f"Restan aproximadamente {sla['hours_remaining']:.1f} horas.")
        open_blocking = sum(item.get("state") == "open" and item.get("severity") in {"blocking", "major"} for item in findings)
        if open_blocking:
            add("blocking_findings", "critical", "Hallazgos bloqueantes abiertos", f"Existen {open_blocking} hallazgos mayores o bloqueantes en la revisión vigente.")
        if workflow == "legal_pending":
            add("legal_pending", "medium", "Decisión jurídica pendiente", "El especialista asignado todavía no ha decidido sobre el SHA-256 vigente.")
        elif workflow == "qa_pending":
            add("qa_pending", "medium", "Control QA pendiente", "La aprobación jurídica existe, pero falta QA independiente sobre el mismo hash.")
        elif workflow == "ready_to_release":
            add("ready_to_release", "info", "Documento listo para liberar", "Las compuertas vigentes permiten liberar el SHA-256 exacto.")
        return alerts

    def state(self, user: dict[str, Any], case_id: str) -> dict[str, Any]:
        detail = self.workspace.detail(user, case_id)
        events = self._read_events(case_id)
        integrity = self.verify_chain(case_id)
        state = self._state_from_events(events)
        sla = self._sla(state, str(detail.get("workflow_status") or ""))
        alerts = self._alerts(detail, state, integrity, sla)
        return {
            "schema_version": M32_6_SCHEMA,
            "case_id": case_id,
            "source_case_id": detail.get("source_case_id"),
            "product_code": detail.get("case", {}).get("product_code"),
            "workflow_status": detail.get("workflow_status"),
            "operations": state,
            "sla": sla,
            "alerts": alerts,
            "operations_audit": integrity,
            "capabilities": {
                "manage_assignment": user.get("role") == "admin",
                "manage_priority": user.get("role") == "admin",
                "manage_deadline": user.get("role") == "admin",
                "add_note": user.get("role") in PROFESSIONAL_ROLES,
                "acknowledge_alert": user.get("role") in PROFESSIONAL_ROLES,
                "export_dossier": user.get("role") in PROFESSIONAL_ROLES,
            },
        }

    def professionals(self, user: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede consultar el directorio de asignación.")
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            active_clause = "AND active=1" if "active" in columns else ""
            specialty = ",specialty" if "specialty" in columns else ",NULL AS specialty"
            rows = [dict(row) for row in con.execute(
                f"SELECT id,name,role{specialty} FROM users WHERE role IN ('specialist','admin','qa') {active_clause} ORDER BY role,name"
            ).fetchall()]
        finally:
            con.close()
        return {
            "schema_version": M32_6_SCHEMA,
            "specialists": [row for row in rows if row.get("role") == "specialist"],
            "qa": [row for row in rows if row.get("role") in QA_ROLES],
        }

    def _user_record(self, user_id: str) -> dict[str, Any]:
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            active = ",active" if "active" in columns else ",1 AS active"
            row = con.execute(f"SELECT id,name,role{active} FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else {}
        finally:
            con.close()

    def update_assignment(self, user: dict[str, Any], case_id: str, specialist_id: str, qa_id: str) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede asignar responsables.")
        detail = self.workspace.detail(user, case_id)
        specialist = self._user_record(_safe_segment(specialist_id, "specialist_id"))
        qa = self._user_record(_safe_segment(qa_id, "qa_id"))
        if not specialist or specialist.get("role") != "specialist" or not specialist.get("active"):
            raise ApprovalDeskError("El responsable jurídico debe ser un especialista activo.")
        if not qa or qa.get("role") not in QA_ROLES or not qa.get("active"):
            raise ApprovalDeskError("El responsable QA debe ser un perfil QA o administrador activo.")
        if specialist["id"] == qa["id"]:
            raise ApprovalDeskError("La separación de funciones exige responsables distintos.")
        source_case_id = str(detail.get("source_case_id") or "")
        con = self.db_factory()
        try:
            columns = {row[1] for row in con.execute("PRAGMA table_info(cases)")}
            if "specialist_id" not in columns:
                raise ApprovalDeskError("El esquema del expediente no admite asignación de especialista.")
            updated = con.execute("UPDATE cases SET specialist_id=? WHERE id=?", (specialist["id"], source_case_id)).rowcount
            if updated != 1:
                raise ApprovalDeskError("El expediente fuente no está disponible para asignación.")
            con.commit()
        finally:
            con.close()
        event = self._append_event(case_id, "assignment.updated", user, {
            "specialist": {"id": specialist["id"], "name": specialist.get("name"), "role": specialist.get("role")},
            "qa": {"id": qa["id"], "name": qa.get("name"), "role": qa.get("role")},
            "source_case_id": source_case_id,
        })
        return {"event": event, "state": self.state(user, case_id)}

    def update_priority(self, user: dict[str, Any], case_id: str, priority: str) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar prioridad y SLA.")
        self.workspace.detail(user, case_id)
        priority_value = str(priority or "").strip().casefold()
        if priority_value not in PRIORITIES:
            raise ApprovalDeskError("Prioridad inválida. Use critical, high, normal o low.")
        hours = DEFAULT_SLA_HOURS[priority_value]
        due_at = (self.now_factory().astimezone(BOGOTA) + timedelta(hours=hours)).isoformat(timespec="seconds")
        event = self._append_event(case_id, "priority.updated", user, {
            "priority": priority_value,
            "sla_hours": hours,
            "due_at": due_at,
            "policy": "M32.6 operational default; not a statutory deadline",
        })
        return {"event": event, "state": self.state(user, case_id)}

    def update_deadline(self, user: dict[str, Any], case_id: str, due_at: str, sla_hours: int | None = None) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede modificar el vencimiento operativo.")
        self.workspace.detail(user, case_id)
        due = _parse_datetime(due_at, "due_at")
        hours = int(sla_hours or max(1, round((due - self.now_factory().astimezone(BOGOTA)).total_seconds() / 3600)))
        if hours < 1 or hours > 24 * 365:
            raise ApprovalDeskError("El SLA debe estar entre 1 hora y 365 días.")
        event = self._append_event(case_id, "deadline.updated", user, {
            "due_at": due.isoformat(timespec="seconds"),
            "sla_hours": hours,
            "source": "administrative_override",
        })
        return {"event": event, "state": self.state(user, case_id)}

    def add_note(self, user: dict[str, Any], case_id: str, text: str) -> dict[str, Any]:
        self.workspace.detail(user, case_id)
        clean = re.sub(r"[\r\n]+", " ", str(text or "")).strip()
        if len(clean) < 3 or len(clean) > 2000:
            raise ApprovalDeskError("La nota debe tener entre 3 y 2.000 caracteres.")
        event = self._append_event(case_id, "note.added", user, {"text": clean})
        return {"event": event, "state": self.state(user, case_id)}

    def acknowledge_alert(self, user: dict[str, Any], case_id: str, code: str, comment: str = "") -> dict[str, Any]:
        current = self.state(user, case_id)
        code_value = _safe_segment(code, "alert_code")
        available = {item["code"] for item in current["alerts"]}
        if code_value not in available:
            raise ApprovalDeskError("La alerta no está activa para este documento.")
        event = self._append_event(case_id, "alert.acknowledged", user, {
            "code": code_value,
            "comment": re.sub(r"[\r\n]+", " ", str(comment or "")).strip()[:1000],
        })
        return {"event": event, "state": self.state(user, case_id)}

    def _activity(self, case_id: str) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for event in self._read_events(case_id):
            values.append({
                "source": "operations",
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "created_at": event.get("created_at"),
                "actor": event.get("actor"),
                "payload": event.get("payload"),
                "event_hash": event.get("event_hash"),
            })
        approval_path = self._case_dir(case_id) / "events.jsonl"
        if approval_path.is_file():
            for line in approval_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    event = json.loads(line)
                    values.append({
                        "source": "approval",
                        "event_id": event.get("event_id"),
                        "event_type": event.get("event_type"),
                        "created_at": event.get("created_at"),
                        "actor": event.get("actor"),
                        "payload": event.get("payload"),
                        "event_hash": event.get("event_hash"),
                    })
        values.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return values

    def case_detail(self, user: dict[str, Any], case_id: str) -> dict[str, Any]:
        operational = self.state(user, case_id)
        operational["activity"] = self._activity(case_id)[:200]
        operational["dossier"] = self.build_dossier(user, case_id, include_activity=False)
        return operational

    def portfolio(self, user: dict[str, Any]) -> dict[str, Any]:
        summary = self.workspace.list_for_user(user)
        rows: list[dict[str, Any]] = []
        alert_count = 0
        overdue = 0
        at_risk = 0
        unassigned = 0
        covered: set[str] = set()
        for row in summary.get("cases", []):
            state = self.state(user, row["desk_case_id"])
            operational = state["operations"]
            covered.add(str(row.get("product_code") or "").upper())
            alert_count += sum(not item["acknowledged"] for item in state["alerts"])
            overdue += state["sla"]["status"] == "overdue"
            at_risk += state["sla"]["status"] == "at_risk"
            unassigned += not operational.get("assigned_specialist") or not operational.get("assigned_qa")
            rows.append({**row, "operations": operational, "sla": state["sla"], "alerts": state["alerts"], "operations_audit": state["operations_audit"]})
        expected = set(PORTFOLIO_CODES)
        coverage = [item for item in PORTFOLIO_PRODUCTS if item["code"] in covered]
        missing = [item for item in PORTFOLIO_PRODUCTS if item["code"] not in covered]
        return {
            "schema_version": M32_6_SCHEMA,
            "portfolio": {
                "expected_products": len(expected),
                "covered_products": len(expected & covered),
                "coverage_percent": round(len(expected & covered) * 100 / len(expected)),
                "covered": coverage,
                "missing": missing,
                "scope": "all" if user.get("role") == "admin" else "assigned",
            },
            "metrics": {
                **summary.get("metrics", {}),
                "active_alerts": alert_count,
                "overdue": overdue,
                "at_risk": at_risk,
                "unassigned": unassigned,
            },
            "cases": rows,
            "notice": "Los SLA de M32.6 son metas operativas configurables y no reemplazan términos legales, judiciales, administrativos o contractuales aplicables.",
        }

    def sync_portfolio(self, user: dict[str, Any], limit: int = 500) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede sincronizar el portafolio.")
        result = self.workspace.bootstrap(user, limit=limit)
        for case_id in result.get("created", []):
            self._append_event(case_id, "operations.initialized", user, {
                "priority": "normal",
                "sla_hours": DEFAULT_SLA_HOURS["normal"],
                "professional_approval_pending": True,
            })
        portfolio = self.portfolio(user)
        return {"schema_version": M32_6_SCHEMA, "bootstrap": result, "portfolio": portfolio["portfolio"], "metrics": portfolio["metrics"]}

    def build_dossier(self, user: dict[str, Any], case_id: str, *, include_activity: bool = True) -> dict[str, Any]:
        detail = self.workspace.detail(user, case_id)
        operational = self.state(user, case_id)
        current = self._current_revision(detail)
        approvals = (current or {}).get("approvals") or {}
        release = detail.get("release")
        payload: dict[str, Any] = {
            "schema_version": M32_6_SCHEMA,
            "generated_at": self.now_factory().astimezone(BOGOTA).isoformat(timespec="seconds"),
            "case": {
                "desk_case_id": case_id,
                "source_case_id": detail.get("source_case_id"),
                "document_id": detail.get("case", {}).get("document_id"),
                "product_code": detail.get("case", {}).get("product_code"),
                "title": detail.get("case", {}).get("title"),
                "workflow_status": detail.get("workflow_status"),
            },
            "current_revision": current,
            "approvals": approvals,
            "release": release,
            "approval_audit": detail.get("audit"),
            "operations": operational["operations"],
            "sla": operational["sla"],
            "alerts": operational["alerts"],
            "operations_audit": operational["operations_audit"],
            "professional_approval_complete": bool(
                release
                and (approvals.get("legal") or {}).get("decision") == "approve"
                and (approvals.get("qa") or {}).get("decision") == "approve"
            ),
            "human_review_required": not bool(release),
            "declaration": (
                "Este expediente acredita trazabilidad técnica y decisiones registradas. "
                "No presume que un documento pendiente haya sido revisado o aprobado profesionalmente."
            ),
        }
        if include_activity:
            payload["activity"] = self._activity(case_id)
        payload["dossier_sha256"] = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return payload

    def export_dossier(self, user: dict[str, Any], case_id: str) -> tuple[Path, str]:
        detail = self.workspace.detail(user, case_id)
        operational_integrity = self.verify_chain(case_id)
        if not operational_integrity["valid"] or not detail.get("audit", {}).get("valid"):
            raise OperationsIntegrityError("No puede exportarse evidencia con una cadena de auditoría inválida.")
        dossier = self.build_dossier(user, case_id)
        current = self._current_revision(detail)
        if not current:
            raise ReleaseBlocked("El expediente no tiene una revisión documental exportable.")
        _, source = self.workspace._revision_file(detail, current["revision_id"])
        package_id = f"EXP-{current['revision_id']}-{current['sha256'][:12]}"
        filename = f"{case_id}_{package_id}_expediente_aprobacion.zip"
        target_dir = self._case_dir(case_id) / "dossiers"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        if target.is_file():
            return target, filename
        approval_events = []
        approval_path = self._case_dir(case_id) / "events.jsonl"
        if approval_path.is_file():
            approval_events = [json.loads(line) for line in approval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        operations_events = self._read_events(case_id)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("expediente_aprobacion.json", json.dumps(dossier, ensure_ascii=False, indent=2))
            archive.writestr("cadena_aprobacion.json", json.dumps(approval_events, ensure_ascii=False, indent=2))
            archive.writestr("actividad_operativa.json", json.dumps(operations_events, ensure_ascii=False, indent=2))
            archive.writestr("revision_vigente.json", json.dumps(current, ensure_ascii=False, indent=2))
            archive.write(source, arcname="revision_vigente.docx")
            archive.writestr(
                "LEAME.txt",
                "LegalAIZ.it — Expediente de aprobación M32.6\n\n"
                "El paquete conserva la revisión DOCX vigente, sus hashes, decisiones y actividad.\n"
                "La existencia del paquete no equivale a aprobación si expediente_aprobacion.json indica human_review_required=true.\n"
                "Los SLA incluidos son metas operativas y no sustituyen términos legales aplicables.\n",
            )
        temporary = target.with_suffix(target.suffix + f".{uuid4().hex}.tmp")
        temporary.write_bytes(buffer.getvalue())
        os.replace(temporary, target)
        if not target.is_file() or _hash_file(target) == "":
            raise ApprovalDeskError("No fue posible consolidar el expediente de aprobación.")
        return target, filename


__all__ = [
    "ApprovalDeskOperations",
    "OperationsIntegrityError",
    "M32_6_SCHEMA",
    "PORTFOLIO_PRODUCTS",
    "PORTFOLIO_CODES",
    "DEFAULT_SLA_HOURS",
]
