from __future__ import annotations

"""Gobernanza de validación adaptativa de LegalAIZ.it v2.19.

Esta capa separa la responsabilidad jurídica de los controles técnicos y evita
revalidar capacidades cuyo contenido y hash no cambiaron. La aprobación del
especialista designado se reconoce como decisión jurídica interna suficiente
para el alcance registrado; una revisión jurídica externa adicional solo se
exige cuando exista un riesgo concreto o una decisión expresa del proyecto.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "2.19"
BASELINE_VERSION = "2.18"
GOVERNANCE_ID = "GOV-219"

COMPONENTS: dict[str, dict[str, Any]] = {
    "legal_content": {
        "label": "Contenido jurídico, preguntas, reglas y fuentes",
        "risk": "critical",
        "paths": [
            "data/products.json", "data/interviews.json", "data/rules.json",
            "data/sources.json", "data/document_templates.json",
            "complete_legal_models_v215.py", "canonical_sources",
        ],
        "controls": ["revisión jurídica de delta", "pruebas de reglas", "QA documental afectado"],
    },
    "document_generation": {
        "label": "Generación DOCX/PDF y modelos extensos",
        "risk": "high",
        "paths": [
            "docx_builder.py", "complete_models_backend_v215.py",
            "extensive_generation_v216.py", "co_em_003_v213.py", "co_em_004_v214.py",
        ],
        "controls": ["pruebas del generador", "renderizado de documentos afectados", "inspección visual documental"],
    },
    "approval_release": {
        "label": "Aprobación, hashes y liberación",
        "risk": "high",
        "paths": ["extensive_review_v217.py"],
        "controls": ["pruebas de roles", "pruebas de integridad", "prueba de liberación"],
    },
    "security_rbac": {
        "label": "Seguridad, RBAC, secretos e infraestructura",
        "risk": "critical",
        "paths": ["security.py", "infrastructure.py"],
        "controls": ["regresión de seguridad", "pruebas RBAC", "revisión de secretos y sesiones"],
    },
    "api_shell": {
        "label": "API y composición del servidor",
        "risk": "medium",
        "paths": ["run.py"],
        "controls": ["pruebas API afectadas", "arranque HTTP", "smoke de autenticación"],
    },
    "web_ui": {
        "label": "Interfaz estable heredada",
        "risk": "medium",
        "paths": [
            "app/index.html", "app/app-v217.js", "app/app-v218.js",
            "app/styles-v217.css", "app/styles-v218.css",
        ],
        "controls": ["QA visual de rutas afectadas", "validación responsive"],
    },
    "visual_qa": {
        "label": "Motor y evidencia de QA visual",
        "risk": "medium",
        "paths": ["visual_qa_v218.py", "tools/run_visual_qa_v218.py"],
        "controls": ["pruebas de evidencia", "verificación de hashes de capturas"],
    },
    "governance_v219": {
        "label": "Gobernanza adaptativa v2.19",
        "risk": "medium",
        "paths": [
            "adaptive_validation_v219.py", "app/app-v219.js", "app/styles-v219.css",
            "data/validation_baseline_v218.json",
        ],
        "controls": ["pruebas de política", "pruebas API", "QA visual focalizado"],
    },
}

RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _files(root: Path, paths: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    for item in paths:
        path = root / item
        if path.is_dir():
            result.extend(sorted(x for x in path.rglob("*") if x.is_file()))
        elif path.is_file():
            result.append(path)
    return sorted(set(result))


def _component_hash(root: Path, paths: Iterable[str]) -> tuple[str, int]:
    digest = sha256()
    files = _files(root, paths)
    for path in files:
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest(), len(files)


class AdaptiveValidationV219:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.baseline_path = self.root / "data" / "validation_baseline_v218.json"

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS validation_governance_v219(
              id TEXT PRIMARY KEY,
              baseline_version TEXT NOT NULL,
              current_version TEXT NOT NULL,
              validation_mode TEXT NOT NULL,
              legal_owner_user_id TEXT,
              legal_owner_name TEXT,
              legal_owner_statement TEXT,
              legal_owner_confirmed_at TEXT,
              technical_actor TEXT,
              technical_decision TEXT,
              technical_comment TEXT,
              technical_at TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS validation_events_v219(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              governance_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        row = con.execute("SELECT id FROM validation_governance_v219 WHERE id=?", (GOVERNANCE_ID,)).fetchone()
        if not row:
            now = _now()
            con.execute(
                """INSERT INTO validation_governance_v219(
                     id,baseline_version,current_version,validation_mode,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                (GOVERNANCE_ID, BASELINE_VERSION, VERSION, "delta_risk_based", "Política activa", now, now),
            )

    def _baseline(self) -> dict[str, Any]:
        if not self.baseline_path.is_file():
            return {"baseline_version": BASELINE_VERSION, "components": {}}
        return json.loads(self.baseline_path.read_text(encoding="utf-8"))

    def assess(self) -> dict[str, Any]:
        baseline = self._baseline().get("components", {})
        rows: list[dict[str, Any]] = []
        changed: list[dict[str, Any]] = []
        inherited: list[dict[str, Any]] = []
        for code, spec in COMPONENTS.items():
            current_hash, count = _component_hash(self.root, spec["paths"])
            previous = baseline.get(code, {})
            previous_hash = previous.get("sha256")
            is_new = previous_hash is None
            is_changed = is_new or previous_hash != current_hash
            item = {
                "code": code,
                "label": spec["label"],
                "risk": spec["risk"],
                "current_sha256": current_hash,
                "baseline_sha256": previous_hash,
                "files": count,
                "changed": is_changed,
                "inherited": not is_changed,
                "controls": spec["controls"] if is_changed else [],
                "decision": "Validar delta" if is_changed else "Heredar evidencia v2.18",
            }
            rows.append(item)
            (changed if is_changed else inherited).append(item)
        highest = max((RISK_ORDER[x["risk"]] for x in changed), default=1)
        level = next(k for k, v in RISK_ORDER.items() if v == highest)
        required_controls: list[str] = []
        for item in changed:
            for control in item["controls"]:
                if control not in required_controls:
                    required_controls.append(control)
        legal_changed = any(x["code"] == "legal_content" for x in changed)
        docs_changed = any(x["code"] == "document_generation" for x in changed)
        security_changed = any(x["code"] == "security_rbac" for x in changed)
        return {
            "baseline_version": BASELINE_VERSION,
            "current_version": VERSION,
            "mode": "Validación proporcional al cambio",
            "impact_level": level,
            "components": rows,
            "metrics": {
                "components": len(rows),
                "changed": len(changed),
                "inherited": len(inherited),
                "required_controls": len(required_controls),
            },
            "required_controls": required_controls,
            "policy": {
                "external_legal_review_required_by_default": False,
                "responsible_lawyer_approval_is_internal_legal_signoff": True,
                "repeat_full_document_qa": docs_changed,
                "repeat_legal_content_review": legal_changed,
                "repeat_security_regression": security_changed,
                "full_suite_frequency": "En hitos de consolidación, al vencer la línea base o ante cambios transversales de riesgo alto/crítico; en los demás incrementos se hereda la línea base y se prueba el delta.",
                "warnings": "Solo contextuales y asociadas a un riesgo concreto; no advertencias genéricas repetidas.",
                "escalate_only_if": [
                    "cambio en norma, fuente, regla, cláusula o plantilla jurídica",
                    "riesgo rojo o supuesto crítico sin resolver",
                    "cambio en seguridad, RBAC, datos o secretos",
                    "marcadores pendientes, falla de integridad o regresión real",
                ],
            },
        }

    def _event(self, con, event_type: str, actor: str, role: str, detail: Any) -> None:
        con.execute(
            "INSERT INTO validation_events_v219(governance_id,event_type,actor,actor_role,detail_json,created_at) VALUES(?,?,?,?,?,?)",
            (GOVERNANCE_ID, event_type, actor, role, json.dumps(detail, ensure_ascii=False, sort_keys=True), _now()),
        )

    def confirm_legal_owner(self, con, user: dict[str, Any], statement: str = "") -> dict[str, Any]:
        self.create_schema(con)
        if user.get("role") != "specialist":
            raise PermissionError("La responsabilidad jurídica debe asumirla un usuario especialista.")
        text = (statement or "").strip() or (
            "Asumo la responsabilidad jurídica interna del proyecto y apruebo que las decisiones jurídicas "
            "registradas por mí no requieran una segunda revisión externa genérica, salvo riesgo concreto."
        )
        now = _now()
        con.execute(
            """UPDATE validation_governance_v219 SET legal_owner_user_id=?,legal_owner_name=?,
               legal_owner_statement=?,legal_owner_confirmed_at=?,status='Responsable jurídico confirmado',updated_at=? WHERE id=?""",
            (user["id"], user.get("name") or user.get("email") or user["id"], text[:4000], now, now, GOVERNANCE_ID),
        )
        self._event(con, "legal_owner_confirmed", user["id"], user["role"], {"statement": text})
        return self.summary(con)

    def technical_decision(self, con, user: dict[str, Any], decision: str, comment: str = "") -> dict[str, Any]:
        self.create_schema(con)
        if user.get("role") != "admin":
            raise PermissionError("El cierre técnico requiere administración.")
        if decision not in {"approve", "reject"}:
            raise ValueError("Decisión técnica inválida.")
        assessment = self.assess()
        now = _now()
        status = "Gobernanza validada" if decision == "approve" else "Ajustes técnicos requeridos"
        con.execute(
            """UPDATE validation_governance_v219 SET technical_actor=?,technical_decision=?,technical_comment=?,
               technical_at=?,status=?,updated_at=? WHERE id=?""",
            (user["id"], decision, (comment or "").strip()[:4000], now, status, now, GOVERNANCE_ID),
        )
        self._event(con, "technical_decision", user["id"], user["role"], {
            "decision": decision, "comment": comment, "impact_level": assessment["impact_level"],
            "required_controls": assessment["required_controls"],
        })
        return self.summary(con)

    def summary(self, con) -> dict[str, Any]:
        self.create_schema(con)
        governance = con.execute("SELECT * FROM validation_governance_v219 WHERE id=?", (GOVERNANCE_ID,)).fetchone()
        events = [dict(x) for x in con.execute(
            "SELECT * FROM validation_events_v219 WHERE governance_id=? ORDER BY id DESC LIMIT 30", (GOVERNANCE_ID,)
        ).fetchall()]
        assessment = self.assess()
        row = dict(governance)
        legal_owner_confirmed = bool(row.get("legal_owner_user_id") and row.get("legal_owner_confirmed_at"))
        technical_approved = row.get("technical_decision") == "approve"
        return {
            "version": VERSION,
            "title": "Gobernanza de validación adaptativa",
            "governance": row,
            "assessment": assessment,
            "events": events,
            "readiness": {
                "legal_owner_confirmed": legal_owner_confirmed,
                "technical_policy_approved": technical_approved,
                "ready": legal_owner_confirmed and technical_approved,
            },
            "operating_rule": (
                "Las capacidades no modificadas heredan su evidencia. El abogado responsable decide el contenido jurídico; "
                "QA valida funcionamiento e integridad. Solo se repiten controles afectados por el cambio."
            ),
        }
