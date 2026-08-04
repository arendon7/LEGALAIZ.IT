from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CoEm004CanonicalV245:
    """Capa canónica funcional de CO-EM-004 v2.45.

    La capa conserva la maduración v2.14 y añade un modelo explicable para
    entrevista, validación, selección de bloques y selección documental.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base = self.root / "app" / "assets" / "advanced-legal-library" / "CO-EM-004"
        self.manifest = self._load("MANIFEST_CO-EM-004.json")
        questions = self._load("PREGUNTAS_CANONICAS.json")
        self.steps = questions["steps"]
        self.questions = questions["questions"]
        self.profiles = self._load("PERFILES_RELACION.json")
        self.documents = self._load("DOCUMENTOS_CANONICOS.json")
        self.validations = self._load("VALIDACIONES_CANONICAS.json")
        self.blocks = self._load("BLOQUES_CANONICOS.json")
        self.sources = self._load("FUENTES_CANONICAS.json")
        self.traceability = self._load("MATRIZ_TRAZABILIDAD.json")
        self._validate_catalogs()

    def _load(self, name: str) -> Any:
        return json.loads((self.base / name).read_text(encoding="utf-8"))

    @staticmethod
    def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def _filled(value: Any) -> bool:
        if value is None or value == "":
            return False
        if isinstance(value, (list, dict)):
            return bool(value)
        return True

    def _validate_catalogs(self) -> None:
        expected = {
            "steps": len(self.steps),
            "questions": len(self.questions),
            "profiles": len(self.profiles),
            "documents": len(self.documents),
            "validations": len(self.validations),
            "blocks": len(self.blocks),
            "sources": len(self.sources),
        }
        for key, value in expected.items():
            if self.manifest.get(key) != value:
                raise ValueError(f"Conteo inconsistente para {key}: {value}.")
        for name, items in (
            ("preguntas", self.questions),
            ("perfiles", self.profiles),
            ("documentos", self.documents),
            ("validaciones", self.validations),
            ("bloques", self.blocks),
            ("fuentes", self.sources),
        ):
            ids = [item.get("id") for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Existen identificadores duplicados en {name}.")

    def summary(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest,
            "steps": self.steps,
            "questions": self.questions,
            "profiles": self.profiles,
            "documents": self.documents,
            "validations": self.validations,
            "blocks": self.blocks,
            "sources": self.sources,
            "traceability": self.traceability,
        }

    def _question_missing(self, question: dict[str, Any], answers: dict[str, Any]) -> list[dict[str, Any]]:
        if not question.get("required"):
            return []
        path = question["variable_path"]
        value = self._get(answers, path)
        result: list[dict[str, Any]] = []
        if question.get("type") in {"group", "structured"}:
            if not isinstance(value, dict):
                result.append({"path": path, "question_id": question["id"], "step_id": question["step_id"], "label": question["label"]})
                return result
            for field in question.get("fields", []):
                if field.get("required") and not self._filled(value.get(field["key"])):
                    result.append({
                        "path": f"{path}.{field['key']}",
                        "question_id": question["id"],
                        "step_id": question["step_id"],
                        "label": f"{question['label']}: {field['label']}",
                    })
            return result
        if not self._filled(value):
            result.append({"path": path, "question_id": question["id"], "step_id": question["step_id"], "label": question["label"]})
        return result

    def evaluate(self, answers: dict[str, Any]) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for question in self.questions:
            missing.extend(self._question_missing(question, answers))

        selected_documents = [
            "DOC-EM4-NDA-001",
            "ANX-EM4-INFO-001",
            "ACT-EM4-DISC-001",
            "ACT-EM4-CLOSE-001",
        ]
        selected_blocks = [
            "EM4-TIT-001", "EM4-CMP-001", "EM4-CON-001", "EM4-DEF-001",
            "EM4-PUR-001", "EM4-INFO-001", "EM4-CAT-001", "EM4-EXC-001",
            "EM4-REC-001", "EM4-NEED-001", "EM4-USE-001", "EM4-COMP-001",
            "EM4-SEC-001", "EM4-TERM-001", "EM4-SURV-001", "EM4-RETURN-001",
            "EM4-DESTROY-001", "EM4-RETAIN-001", "EM4-NOT-001", "EM4-LAW-001",
            "EM4-DISP-001", "EM4-INT-001", "EM4-SIGN-001",
        ]

        relationship = self._get(answers, "relationship.context")
        if relationship and relationship != "other":
            selected_documents.append("ANX-EM4-REL-001")

        categories = self._get(answers, "information.categories")
        purpose = self._get(answers, "agreement.purpose")
        exclusions = self._get(answers, "information.exclusions")
        recipients = self._get(answers, "access.authorized_recipients")
        trade_secrets = self._get(answers, "information.trade_secrets") is True
        security_level = self._get(answers, "security.controls.level")
        incident_protocol = self._get(answers, "security.incident_protocol")

        if not self._filled(categories) or not self._filled(purpose):
            findings.append({"id": "V-EM4-002", "severity": "blocker", "message": "La finalidad y las categorías de información deben quedar delimitadas."})
        if not self._filled(exclusions) or not self._filled(recipients):
            findings.append({"id": "V-EM4-003", "severity": "review", "message": "Deben definirse exclusiones y destinatarios autorizados."})
        if trade_secrets:
            selected_blocks.append("EM4-TRADE-001")
            selected_documents.append("PRO-EM4-INC-001")
            if security_level in (None, "", "basic") or not self._filled(self._get(answers, "access.need_to_know")):
                findings.append({"id": "V-EM4-004", "severity": "blocker", "message": "Los secretos empresariales requieren controles reforzados, acceso por necesidad de conocer e inventario verificable."})
            if not self._filled(incident_protocol):
                findings.append({"id": "V-EM4-014", "severity": "review", "message": "La información crítica requiere protocolo de incidentes, notificación y preservación de evidencia."})

        personal_data = self._get(answers, "data.personal") is True
        crossborder = self._get(answers, "data.crossborder")
        if personal_data or crossborder in {"yes", "unknown"}:
            selected_documents.append("ANX-EM4-DATA-001")
            selected_blocks.append("EM4-DATA-001")
        if personal_data:
            roles = self._get(answers, "data.roles", {})
            if not isinstance(roles, dict) or not roles.get("party_a_role") or not roles.get("party_b_role") or not roles.get("instructions"):
                findings.append({"id": "V-EM4-005", "severity": "blocker", "message": "El tratamiento de datos personales exige roles, instrucciones, finalidades y ciclo de vida definidos."})
        if self._get(answers, "data.sensitive_or_children") is True:
            findings.append({"id": "V-EM4-006", "severity": "blocker", "message": "Los datos sensibles, biométricos, de salud o de menores requieren revisión jurídica especializada."})
        if crossborder in {"yes", "unknown"}:
            selected_blocks.append("EM4-XBORDER-001")
            findings.append({"id": "V-EM4-007", "severity": "review", "message": "La transferencia internacional o nube externa requiere análisis de país, proveedor, garantías y roles."})

        ip_allocation = self._get(answers, "ip.results_allocation")
        preexisting = self._get(answers, "ip.preexisting_materials")
        oss = self._get(answers, "ip.oss_third_party")
        ip_context = relationship in {"software_technology", "creative_content", "research_development"}
        if ip_context or ip_allocation not in (None, "", "none") or self._filled(preexisting) or self._filled(oss):
            selected_documents.append("ANX-EM4-IP-001")
            selected_blocks.extend(["EM4-IP-001", "EM4-PRE-001", "EM4-MORAL-001"])
        if self._filled(oss):
            selected_documents.append("ANX-EM4-OSS-001")
            selected_blocks.append("EM4-OSS-001")
        if self._get(answers, "ip.future_assignment_broad") is True:
            findings.append({"id": "V-EM4-008", "severity": "blocker", "message": "No procede una cesión general de obras o resultados futuros indeterminados."})
        if self._get(answers, "ip.moral_rights_waiver") is True:
            findings.append({"id": "V-EM4-009", "severity": "blocker", "message": "Los derechos morales son inalienables, imprescriptibles e irrenunciables."})
        if (self._filled(preexisting) or self._filled(oss)) and ip_allocation in {None, "", "to_define"}:
            findings.append({"id": "V-EM4-011", "severity": "review", "message": "Materiales preexistentes, OSS y componentes de terceros deben inventariarse y conservar sus licencias."})

        ai_used = self._get(answers, "ai.used") is True
        ai_public = self._get(answers, "ai.public_upload") is True
        if ai_used or ai_public:
            selected_documents.append("ANX-EM4-AI-001")
            selected_blocks.extend(["EM4-AI-001", "EM4-AI-TRAIN-001"])
        if ai_public:
            findings.append({"id": "V-EM4-010", "severity": "blocker", "message": "No debe cargarse información confidencial en herramientas públicas o no autorizadas de IA."})
        elif ai_used and not self._filled(self._get(answers, "ai.training_outputs")):
            findings.append({"id": "V-EM4-AI-REVIEW", "severity": "review", "message": "Debe definirse retención, entrenamiento, revisión humana y titularidad de resultados de IA."})

        term = self._get(answers, "term_remedies", {})
        if isinstance(term, dict):
            ordinary_years = term.get("ordinary_confidentiality_years")
            try:
                if ordinary_years not in (None, "") and float(ordinary_years) > 5:
                    findings.append({"id": "V-EM4-012", "severity": "review", "message": "Una reserva ordinaria superior a cinco años debe justificarse y diferenciarse de los secretos empresariales."})
            except (TypeError, ValueError):
                findings.append({"id": "V-EM4-DURATION", "severity": "review", "message": "La duración de la reserva ordinaria debe expresarse en un valor verificable."})
            if term.get("general_noncompete") is True:
                selected_blocks.append("EM4-NONCOMP-001")
                findings.append({"id": "V-EM4-013", "severity": "blocker", "message": "El acuerdo de confidencialidad no debe imponer una prohibición general de trabajar después de terminar."})
            if not self._filled(term.get("penalty_or_liability")):
                findings.append({"id": "V-EM4-015", "severity": "review", "message": "Debe precisarse el régimen de responsabilidad, prueba del daño, cláusula penal y remedios."})

        if self._get(answers, "agreement.type") == "mutual" and self._get(answers, "agreement.reciprocal") is False:
            findings.append({"id": "V-EM4-CONFIG", "severity": "review", "message": "El acuerdo se indicó como mutuo, pero la reciprocidad fue negada. Debe armonizarse la configuración."})
        if self._get(answers, "information.marking_rule") == "marked_only":
            selected_blocks.append("EM4-MARK-001")
            findings.append({"id": "V-EM4-MARK", "severity": "review", "message": "Proteger únicamente lo marcado puede dejar por fuera información que objetivamente deba reconocerse como reservada."})
        if self._get(answers, "information.oral_visual_rule"):
            selected_blocks.append("EM4-ORAL-001")
        if self._filled(self._get(answers, "access.representatives")):
            selected_blocks.append("EM4-REP-001")
        if self._filled(self._get(answers, "security.incident_protocol")) or security_level == "critical":
            selected_documents.append("PRO-EM4-INC-001")
            selected_blocks.extend(["EM4-INC-001", "EM4-NOTIFY-001"])

        blockers = [item for item in findings if item["severity"] == "blocker"]
        reviews = [item for item in findings if item["severity"] == "review"]
        completed_questions = len(self.questions) - len({item["question_id"] for item in missing})
        completion = {
            "completed": max(0, completed_questions),
            "total": len(self.questions),
            "percent": round(max(0, completed_questions) * 100 / len(self.questions)),
        }
        risk_level = "high" if blockers else "medium" if reviews else "low"
        return {
            "version": "2.45",
            "blocked": bool(blockers),
            "risk_level": risk_level,
            "findings": findings,
            "missing_fields": missing,
            "documents": list(dict.fromkeys(selected_documents)),
            "blocks": list(dict.fromkeys(selected_blocks)),
            "professional_review_required": bool(blockers or reviews),
            "completion": completion,
            "ready": not blockers and not missing,
        }
