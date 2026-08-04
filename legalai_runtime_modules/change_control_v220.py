from __future__ import annotations

"""Control de cambios automático de LegalAIZ.it v2.20.

Convierte cada incremento en una unidad auditable: identifica componentes
impactados, hereda evidencia no afectada, genera controles proporcionales y
bloquea el cierre hasta completar únicamente los controles exigibles.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import json
import uuid

from adaptive_validation_v219 import COMPONENTS as V219_COMPONENTS, RISK_ORDER

VERSION = "2.21"
BASELINE_VERSION = "2.20"

COMPONENTS: dict[str, dict[str, Any]] = {
    **V219_COMPONENTS,
    "change_control_v220": {
        "label": "Motor automático de cambios v2.20",
        "risk": "medium",
        "paths": [
            "change_control_v220.py", "app/app-v220.js", "app/styles-v220.css",
            "data/change_baseline_v220.json",
        ],
        "controls": [
            {"code": "change_policy_tests", "label": "Pruebas del motor de impacto", "category": "technical", "owner_role": "admin"},
            {"code": "change_api_tests", "label": "Pruebas API y RBAC del control de cambios", "category": "technical", "owner_role": "admin"},
            {"code": "change_visual_qa", "label": "QA visual focalizado del Centro de Cambios", "category": "technical", "owner_role": "admin"},
        ],
    },
    "release_cycle_v221": {
        "label": "Ciclo de entrega trazable v2.21",
        "risk": "medium",
        "paths": [
            "release_cycle_v221.py", "app/app-v221.js", "app/styles-v221.css",
            "tests/test_v221_release_cycle.py", "tests/test_v221_release_cycle_api.py",
            "tools/run_visual_qa_v221.py",
            "docs/ARQUITECTURA_V221.md", "docs/RELEASE_NOTES_V221.md",
        ],
        "controls": [
            {"code": "release_cycle_tests", "label": "Pruebas del ciclo de entrega", "category": "technical", "owner_role": "admin"},
            {"code": "release_cycle_api_tests", "label": "Pruebas API y RBAC de versiones", "category": "technical", "owner_role": "admin"},
            {"code": "release_cycle_visual_qa", "label": "QA visual focalizado del ciclo de entrega", "category": "technical", "owner_role": "admin"},
            {"code": "release_bundle_integrity", "label": "Integridad del paquete de evidencia", "category": "technical", "owner_role": "admin"},
        ],
    },
}

CONTROL_LIBRARY: dict[str, list[dict[str, str]]] = {
    "legal_content": [
        {"code": "legal_delta_review", "label": "Revisión jurídica del delta", "category": "legal", "owner_role": "specialist"},
        {"code": "legal_rule_tests", "label": "Pruebas de preguntas, reglas y escenarios afectados", "category": "legal", "owner_role": "specialist"},
        {"code": "legal_source_traceability", "label": "Trazabilidad de fuentes jurídicas modificadas", "category": "legal", "owner_role": "specialist"},
    ],
    "document_generation": [
        {"code": "generator_delta_tests", "label": "Pruebas del generador afectado", "category": "technical", "owner_role": "admin"},
        {"code": "affected_document_render", "label": "Renderizado de documentos afectados", "category": "technical", "owner_role": "admin"},
        {"code": "affected_document_visual_qa", "label": "Inspección visual documental focalizada", "category": "technical", "owner_role": "admin"},
    ],
    "approval_release": [
        {"code": "approval_role_tests", "label": "Pruebas de separación de roles", "category": "technical", "owner_role": "admin"},
        {"code": "release_hash_integrity", "label": "Integridad de hashes y liberación", "category": "technical", "owner_role": "admin"},
    ],
    "security_rbac": [
        {"code": "security_delta_regression", "label": "Regresión de seguridad afectada", "category": "technical", "owner_role": "admin"},
        {"code": "rbac_delta_tests", "label": "Pruebas RBAC del delta", "category": "technical", "owner_role": "admin"},
        {"code": "secret_session_scan", "label": "Revisión de secretos, sesiones y datos sensibles", "category": "technical", "owner_role": "admin"},
    ],
    "api_shell": [
        {"code": "affected_api_tests", "label": "Pruebas API afectadas", "category": "technical", "owner_role": "admin"},
        {"code": "http_startup_smoke", "label": "Arranque HTTP y smoke de autenticación", "category": "technical", "owner_role": "admin"},
    ],
    "web_ui": [
        {"code": "affected_web_visual_qa", "label": "QA visual de rutas afectadas", "category": "technical", "owner_role": "admin"},
        {"code": "affected_responsive_qa", "label": "Validación responsive focalizada", "category": "technical", "owner_role": "admin"},
    ],
    "visual_qa": [
        {"code": "visual_evidence_tests", "label": "Pruebas de evidencia visual", "category": "technical", "owner_role": "admin"},
        {"code": "visual_hash_verification", "label": "Verificación de hashes de capturas", "category": "technical", "owner_role": "admin"},
    ],
    "governance_v219": [
        {"code": "adaptive_policy_regression", "label": "Regresión de validación adaptativa", "category": "technical", "owner_role": "admin"},
        {"code": "governance_audit_trail", "label": "Trazabilidad de decisiones de gobernanza", "category": "technical", "owner_role": "admin"},
    ],
    "change_control_v220": [
        {"code": "change_policy_tests", "label": "Pruebas del motor de impacto", "category": "technical", "owner_role": "admin"},
        {"code": "change_api_tests", "label": "Pruebas API y RBAC del control de cambios", "category": "technical", "owner_role": "admin"},
        {"code": "change_visual_qa", "label": "QA visual focalizado del Centro de Cambios", "category": "technical", "owner_role": "admin"},
    ],
    "release_cycle_v221": [
        {"code": "release_cycle_tests", "label": "Pruebas del ciclo de entrega", "category": "technical", "owner_role": "admin"},
        {"code": "release_cycle_api_tests", "label": "Pruebas API y RBAC de versiones", "category": "technical", "owner_role": "admin"},
        {"code": "release_cycle_visual_qa", "label": "QA visual focalizado del ciclo de entrega", "category": "technical", "owner_role": "admin"},
        {"code": "release_bundle_integrity", "label": "Integridad del paquete de evidencia", "category": "technical", "owner_role": "admin"},
    ],
    "other": [
        {"code": "other_change_documentation", "label": "Documentación del cambio no clasificado", "category": "technical", "owner_role": "admin"},
        {"code": "other_change_smoke", "label": "Smoke focalizado del cambio no clasificado", "category": "technical", "owner_role": "admin"},
    ],
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_path(value: str) -> str:
    raw = (value or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError("La ruta del cambio no puede estar vacía.")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("La ruta debe ser relativa al proyecto y no puede contener '..'.")
    return path.as_posix().lstrip("./")


def _path_matches(path: str, configured: str) -> bool:
    configured = configured.rstrip("/")
    return path == configured or path.startswith(configured + "/")


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class ChangeControlV220:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.baseline_path = self.root / "data" / "change_baseline_v220.json"

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS change_sets_v220(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              baseline_version TEXT NOT NULL,
              target_version TEXT NOT NULL,
              declared_paths_json TEXT NOT NULL,
              affected_components_json TEXT NOT NULL,
              inherited_components_json TEXT NOT NULL,
              impact_level TEXT NOT NULL,
              validation_plan_json TEXT NOT NULL,
              plan_sha256 TEXT NOT NULL,
              legal_signoff_required INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              closed_by TEXT,
              closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS change_control_results_v220(
              change_set_id TEXT NOT NULL,
              control_code TEXT NOT NULL,
              label TEXT NOT NULL,
              category TEXT NOT NULL,
              owner_role TEXT NOT NULL,
              required INTEGER NOT NULL DEFAULT 1,
              status TEXT NOT NULL DEFAULT 'pending',
              result TEXT,
              notes TEXT,
              evidence_ref TEXT,
              evidence_sha256 TEXT,
              completed_by TEXT,
              completed_at TEXT,
              PRIMARY KEY(change_set_id,control_code)
            );
            CREATE TABLE IF NOT EXISTS change_events_v220(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              change_set_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )

    def _baseline(self) -> dict[str, Any]:
        if not self.baseline_path.is_file():
            return {"baseline_version": BASELINE_VERSION, "files": {}, "components": {}}
        return json.loads(self.baseline_path.read_text(encoding="utf-8"))

    def _component_files(self, spec: dict[str, Any]) -> set[str]:
        result: set[str] = set()
        for item in spec.get("paths", []):
            path = self.root / item
            if path.is_file():
                result.add(path.relative_to(self.root).as_posix())
            elif path.is_dir():
                result.update(x.relative_to(self.root).as_posix() for x in path.rglob("*") if x.is_file())
        return result

    def release_delta(self) -> dict[str, Any]:
        baseline = self._baseline()
        baseline_files: dict[str, str] = baseline.get("files", {})
        tracked: set[str] = set(baseline_files)
        for spec in COMPONENTS.values():
            tracked.update(self._component_files(spec))
        rows: list[dict[str, str]] = []
        for rel in sorted(tracked):
            path = self.root / rel
            previous = baseline_files.get(rel)
            if not path.is_file():
                if previous:
                    rows.append({"path": rel, "change": "deleted", "baseline_sha256": previous, "current_sha256": ""})
                continue
            current = _file_hash(path)
            if previous is None:
                rows.append({"path": rel, "change": "added", "baseline_sha256": "", "current_sha256": current})
            elif current != previous:
                rows.append({"path": rel, "change": "modified", "baseline_sha256": previous, "current_sha256": current})
        plan = self.plan([x["path"] for x in rows])
        return {"baseline_version": BASELINE_VERSION, "target_version": VERSION, "files": rows, "plan": plan}

    def classify_paths(self, paths: Iterable[str]) -> dict[str, Any]:
        normalized = sorted(set(_safe_path(x) for x in paths))
        affected: set[str] = set()
        path_components: dict[str, list[str]] = {}
        for path in normalized:
            matches: list[str] = []
            for code, spec in COMPONENTS.items():
                if any(_path_matches(path, configured) for configured in spec.get("paths", [])):
                    matches.append(code)
            if not matches:
                matches = ["other"]
            path_components[path] = matches
            affected.update(matches)
        inherited = [code for code in COMPONENTS if code not in affected]
        return {
            "paths": normalized,
            "path_components": path_components,
            "affected_components": sorted(affected),
            "inherited_components": inherited,
        }

    def plan(self, paths: Iterable[str]) -> dict[str, Any]:
        classified = self.classify_paths(paths)
        affected = classified["affected_components"]
        controls: list[dict[str, Any]] = []
        seen: set[str] = set()
        risks: list[str] = []
        for code in affected:
            spec = COMPONENTS.get(code, {"risk": "low", "label": "Cambio no clasificado"})
            risks.append(spec.get("risk", "low"))
            for control in CONTROL_LIBRARY.get(code, CONTROL_LIBRARY["other"]):
                if control["code"] in seen:
                    continue
                seen.add(control["code"])
                controls.append({**control, "required": True, "status": "pending", "source_component": code})
        highest = max((RISK_ORDER.get(x, 1) for x in risks), default=1)
        impact_level = next((name for name, rank in RISK_ORDER.items() if rank == highest), "low")
        legal_required = any(x.get("category") == "legal" for x in controls)
        payload = {
            **classified,
            "impact_level": impact_level,
            "legal_signoff_required": legal_required,
            "controls": controls,
            "metrics": {
                "paths": len(classified["paths"]),
                "affected_components": len(affected),
                "inherited_components": len(classified["inherited_components"]),
                "required_controls": len(controls),
            },
            "operating_rule": (
                "Solo se ejecutan los controles asociados a componentes afectados. Los demás componentes heredan "
                "la evidencia de la línea base v2.20. La aprobación jurídica se exige únicamente cuando cambia contenido jurídico."
            ),
        }
        payload["plan_sha256"] = sha256(_json(payload).encode("utf-8")).hexdigest()
        return payload

    def _event(self, con, change_set_id: str, event_type: str, user: dict[str, Any], detail: Any) -> None:
        con.execute(
            "INSERT INTO change_events_v220(change_set_id,event_type,actor,actor_role,detail_json,created_at) VALUES(?,?,?,?,?,?)",
            (change_set_id, event_type, user["id"], user["role"], _json(detail), _now()),
        )

    def create_change_set(self, con, user: dict[str, Any], title: str, summary: str, paths: Iterable[str]) -> dict[str, Any]:
        self.create_schema(con)
        if user.get("role") not in {"specialist", "admin"}:
            raise PermissionError("Solo especialistas o administración pueden registrar cambios.")
        title = (title or "").strip()
        if len(title) < 4:
            raise ValueError("El cambio requiere un título descriptivo.")
        plan = self.plan(paths)
        if not plan["paths"]:
            raise ValueError("Debe indicar al menos una ruta afectada.")
        cid = "CHG-" + uuid.uuid4().hex[:10].upper()
        now = _now()
        con.execute(
            """INSERT INTO change_sets_v220(
                 id,title,summary,baseline_version,target_version,declared_paths_json,
                 affected_components_json,inherited_components_json,impact_level,
                 validation_plan_json,plan_sha256,legal_signoff_required,status,
                 created_by,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                cid, title[:240], (summary or "").strip()[:4000], BASELINE_VERSION, VERSION,
                _json(plan["paths"]), _json(plan["affected_components"]), _json(plan["inherited_components"]),
                plan["impact_level"], _json(plan), plan["plan_sha256"], int(plan["legal_signoff_required"]),
                "Plan activo", user["id"], now, now,
            ),
        )
        for control in plan["controls"]:
            con.execute(
                """INSERT INTO change_control_results_v220(
                     change_set_id,control_code,label,category,owner_role,required,status
                   ) VALUES(?,?,?,?,?,?,?)""",
                (cid, control["code"], control["label"], control["category"], control["owner_role"], 1, "pending"),
            )
        self._event(con, cid, "change_set_created", user, {"title": title, "plan_sha256": plan["plan_sha256"], "paths": plan["paths"]})
        return self.detail(con, cid)

    def _load(self, con, change_set_id: str):
        row = con.execute("SELECT * FROM change_sets_v220 WHERE id=?", (change_set_id,)).fetchone()
        if not row:
            raise KeyError("Cambio no encontrado.")
        return row

    def complete_control(
        self, con, user: dict[str, Any], change_set_id: str, control_code: str,
        result: str, notes: str = "", evidence_ref: str = "", evidence_sha256: str = "",
    ) -> dict[str, Any]:
        self.create_schema(con)
        change = self._load(con, change_set_id)
        if change["status"] == "Cerrado":
            raise ValueError("El cambio ya está cerrado y es inmutable.")
        control = con.execute(
            "SELECT * FROM change_control_results_v220 WHERE change_set_id=? AND control_code=?",
            (change_set_id, control_code),
        ).fetchone()
        if not control:
            raise KeyError("Control no encontrado.")
        if user.get("role") != control["owner_role"]:
            owner = "especialista" if control["owner_role"] == "specialist" else "administración"
            raise PermissionError(f"Este control corresponde a {owner}.")
        result = (result or "").strip().lower()
        if result not in {"pass", "fail", "not_applicable"}:
            raise ValueError("Resultado inválido. Use pass, fail o not_applicable.")
        status = "passed" if result == "pass" else "failed" if result == "fail" else "not_applicable"
        evidence_sha256 = (evidence_sha256 or "").strip().lower()
        if evidence_sha256 and (len(evidence_sha256) != 64 or any(c not in "0123456789abcdef" for c in evidence_sha256)):
            raise ValueError("El hash de evidencia debe ser SHA-256 hexadecimal.")
        now = _now()
        con.execute(
            """UPDATE change_control_results_v220 SET status=?,result=?,notes=?,evidence_ref=?,evidence_sha256=?,
               completed_by=?,completed_at=? WHERE change_set_id=? AND control_code=?""",
            (status, result, (notes or "").strip()[:4000], (evidence_ref or "").strip()[:1000], evidence_sha256,
             user["id"], now, change_set_id, control_code),
        )
        con.execute("UPDATE change_sets_v220 SET status=?,updated_at=? WHERE id=?", ("Control fallido" if status == "failed" else "En validación", now, change_set_id))
        self._event(con, change_set_id, "control_completed", user, {"control_code": control_code, "result": result, "evidence_sha256": evidence_sha256})
        return self.detail(con, change_set_id)

    def close(self, con, user: dict[str, Any], change_set_id: str) -> dict[str, Any]:
        self.create_schema(con)
        change = self._load(con, change_set_id)
        if user.get("role") != "admin":
            raise PermissionError("El cierre del cambio corresponde a administración.")
        if change["status"] == "Cerrado":
            return self.detail(con, change_set_id)
        controls = [dict(x) for x in con.execute(
            "SELECT * FROM change_control_results_v220 WHERE change_set_id=? ORDER BY category,control_code", (change_set_id,)
        ).fetchall()]
        pending = [x for x in controls if x["required"] and x["status"] not in {"passed", "not_applicable"}]
        if pending:
            raise ValueError("No es posible cerrar: existen controles pendientes o fallidos.")
        now = _now()
        con.execute(
            "UPDATE change_sets_v220 SET status='Cerrado',closed_by=?,closed_at=?,updated_at=? WHERE id=?",
            (user["id"], now, now, change_set_id),
        )
        self._event(con, change_set_id, "change_set_closed", user, {"plan_sha256": change["plan_sha256"], "controls": len(controls)})
        return self.detail(con, change_set_id)

    def _decode_change(self, row: Any) -> dict[str, Any]:
        obj = dict(row)
        for key in ("declared_paths_json", "affected_components_json", "inherited_components_json", "validation_plan_json"):
            name = key.replace("_json", "")
            obj[name] = json.loads(obj.pop(key) or "[]")
        obj["legal_signoff_required"] = bool(obj["legal_signoff_required"])
        return obj

    def detail(self, con, change_set_id: str) -> dict[str, Any]:
        change = self._decode_change(self._load(con, change_set_id))
        controls = [dict(x) for x in con.execute(
            "SELECT * FROM change_control_results_v220 WHERE change_set_id=? ORDER BY category DESC,control_code",
            (change_set_id,),
        ).fetchall()]
        events = [dict(x) for x in con.execute(
            "SELECT * FROM change_events_v220 WHERE change_set_id=? ORDER BY id DESC LIMIT 100", (change_set_id,)
        ).fetchall()]
        required = [x for x in controls if x["required"]]
        completed = [x for x in required if x["status"] in {"passed", "not_applicable"}]
        failed = [x for x in required if x["status"] == "failed"]
        return {
            "change": change,
            "controls": controls,
            "events": events,
            "readiness": {
                "required": len(required), "completed": len(completed), "failed": len(failed),
                "ready_to_close": len(required) == len(completed) and not failed,
                "closed": change["status"] == "Cerrado",
            },
        }

    def summary(self, con) -> dict[str, Any]:
        self.create_schema(con)
        rows = [self._decode_change(x) for x in con.execute(
            "SELECT * FROM change_sets_v220 ORDER BY created_at DESC LIMIT 50"
        ).fetchall()]
        release = self.release_delta()
        return {
            "version": VERSION,
            "title": "Centro de control de cambios",
            "baseline_version": BASELINE_VERSION,
            "release_delta": release,
            "change_sets": rows,
            "metrics": {
                "registered": len(rows),
                "open": sum(x["status"] != "Cerrado" for x in rows),
                "closed": sum(x["status"] == "Cerrado" for x in rows),
                "release_files_changed": len(release["files"]),
                "release_components_affected": release["plan"]["metrics"]["affected_components"],
                "release_controls_required": release["plan"]["metrics"]["required_controls"],
            },
            "operating_rule": release["plan"]["operating_rule"],
        }

    def evidence(self, con, change_set_id: str) -> bytes:
        obj = self.detail(con, change_set_id)
        obj["exported_at"] = _now()
        obj["evidence_sha256"] = sha256(_json(obj).encode("utf-8")).hexdigest()
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
