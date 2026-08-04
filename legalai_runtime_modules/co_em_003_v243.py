from __future__ import annotations

from pathlib import Path

from co_em_003_v242 import CoEm003CanonicalV242


class CoEm003CanonicalV243(CoEm003CanonicalV242):
    """Canonical evaluator used by the v2.43 document and governance layer.

    It preserves the v2.42 questionnaire while adding documentary readiness,
    professional-review requirements and more precise contract-reality controls.
    """

    REQUIRED_LABELS = {
        "client.type": "Tipo de contratante",
        "client.identification": "Identificación completa del contratante",
        "client.signatory": "Firmante y fuente de facultad",
        "contractor.type": "Tipo de contratista",
        "contractor.identification": "Identificación completa del contratista",
        "service.category": "Categoría del servicio",
        "service.object": "Objeto contractual",
        "service.expected_result": "Resultado esperado",
        "scope.included": "Actividades incluidas",
        "scope.deliverables": "Entregables y criterios de aceptación",
        "fees.model": "Modelo de honorarios",
        "fees.financial_terms": "Valor, impuestos, facturación y pago",
        "term": "Fecha de inicio y plazo",
        "termination": "Terminación, subsanación y suspensión",
        "closure": "Transición, devolución y cierre",
        "disputes.mechanism": "Mecanismo de solución de controversias",
        "confirmation": "Confirmaciones finales",
    }

    def __init__(self, root: Path):
        super().__init__(root)

    @staticmethod
    def _empty(value):
        return value in (None, "", [], {})

    def summary(self):
        data = super().summary()
        data["manifest"] = dict(data["manifest"])
        data["manifest"].update({
            "version": "2.43",
            "status": "document_factory_and_governance_integrated",
            "document_factory": True,
            "immutable_revisions": True,
            "dual_approval": True,
        })
        data["version"] = "2.43"
        return data

    def evaluate(self, answers):
        answers = answers or {}
        findings = []
        review_requirements = []
        missing = []
        selected = ["DOC-EM-CONTRACT-001", "ANX-EM-SCOPE-001", "ACT-EM-CLOSE-001"]
        blocks = [
            "EM-TIT-001", "EM-CMP-001", "EM-CON-001", "EM-OBJ-001", "EM-SCOPE-001",
            "EM-DEL-001", "EM-ACC-001", "EM-CHG-001", "EM-AUT-001", "EM-NOLAB-001",
            "EM-TERM-001", "EM-FEES-001", "EM-INV-001", "EM-EXP-001", "EM-OBL-CNT-001",
            "EM-OBL-CNR-001", "EM-LIAB-001", "EM-INDEM-001", "EM-FM-001", "EM-SUSP-001",
            "EM-TER-001", "EM-TRANS-001", "EM-DISP-001", "EM-NOT-001", "EM-INT-001", "EM-FIR-001",
        ]

        for path, label in self.REQUIRED_LABELS.items():
            if self._empty(self._get(answers, path)):
                missing.append({"path": path, "label": label, "severity": "required"})

        indicators = [
            "fixed_schedule", "continuous_orders", "org_integration",
            "exclusivity_or_availability", "personal_continuous_periodic",
        ]
        score = sum(2 for key in indicators if self._get(answers, "labor_indicators." + key) is True)
        if self._get(answers, "autonomy.methods") is False:
            score += 2
        if self._get(answers, "autonomy.delegation") is False:
            score += 1

        if score >= 8:
            findings.append({
                "id": "V-EM-003", "severity": "blocker",
                "message": "Riesgo alto de contrato realidad. La configuración debe rediseñarse o manejarse mediante una relación laboral.",
            })
            review_requirements.append("Revisión laboral obligatoria por posible subordinación real.")
        elif score >= 4:
            findings.append({
                "id": "V-EM-004", "severity": "review",
                "message": "Existen indicios materiales de subordinación. La generación requiere revisión jurídica previa.",
            })
            review_requirements.append("Revisión jurídica del riesgo de subordinación y de la operación real.")

        if self._get(answers, "confirmation.public_contracting") is True:
            findings.append({"id": "V-EM-001", "severity": "blocker", "message": "Este producto no cubre contratación estatal."})

        if self._get(answers, "confirmation.true_independence") is False:
            findings.append({
                "id": "V-EM-011", "severity": "blocker",
                "message": "No se confirmó que la ejecución real sea autónoma e independiente.",
            })

        if self._get(answers, "service.regulated") is True:
            if self._get(answers, "service.habilitation_verified") is not True:
                findings.append({
                    "id": "V-EM-002", "severity": "blocker",
                    "message": "El servicio regulado requiere verificar matrícula, licencia, permiso o habilitación antes de contratar.",
                })
            else:
                blocks.append("EM-REG-001")
                review_requirements.append("Verificar vigencia y alcance de la habilitación profesional o regulatoria.")

        deliverables = self._get(answers, "scope.deliverables")
        if self._empty(self._get(answers, "service.object")) or self._empty(deliverables):
            findings.append({"id": "V-EM-005", "severity": "blocker", "message": "El objeto y los entregables deben ser verificables."})
        if not self._empty(deliverables):
            selected.append("ACT-EM-ACCEPT-001")

        fee_model = self._get(answers, "fees.model")
        if fee_model in ("milestone", "success", "mixed"):
            selected.append("ANX-EM-FEES-001")
        if fee_model == "success":
            findings.append({
                "id": "V-EM-006", "severity": "review",
                "message": "La remuneración por éxito requiere definir causación, fuente de verificación y pago posterior a la terminación.",
            })
            review_requirements.append("Revisar la fórmula y causación de la remuneración por éxito.")

        liability = self._get(answers, "liability")
        if isinstance(liability, dict):
            cap = liability.get("cap") or liability.get("limit")
        else:
            cap = None
        if self._empty(cap):
            findings.append({
                "id": "V-EM-007", "severity": "review",
                "message": "No se identificó un límite de responsabilidad ni sus exclusiones.",
            })
            review_requirements.append("Definir la distribución y el límite de responsabilidad.")

        if self._get(answers, "confidentiality.required") is True:
            selected.append("ANX-EM-CONF-001")
            blocks.append("EM-CONF-001")

        if self._get(answers, "data_processing.required") is True:
            selected.append("ANX-EM-DATA-001")
            blocks.append("EM-DATA-001")
            roles = self._get(answers, "data_processing.roles") or self._get(answers, "data_processing.details")
            if self._empty(roles):
                findings.append({
                    "id": "V-EM-008", "severity": "blocker",
                    "message": "Deben definirse los roles de tratamiento, instrucciones, categorías de datos y medidas de seguridad.",
                })

        if self._get(answers, "ip.required") is True:
            selected.append("ANX-EM-IP-001")
            blocks.append("EM-IP-001")
            allocation = self._get(answers, "ip.allocation") or self._get(answers, "ip.details")
            if self._empty(allocation):
                findings.append({
                    "id": "V-EM-009", "severity": "blocker",
                    "message": "Debe definirse la titularidad o licencia, los materiales preexistentes y los componentes de terceros.",
                })

        if self._get(answers, "ai.required") is True:
            selected.append("ANX-EM-AI-001")
            blocks.append("EM-AI-001")
            findings.append({
                "id": "V-EM-010", "severity": "review",
                "message": "El uso de inteligencia artificial requiere controles de información, licencias, trazabilidad y revisión humana.",
            })
            review_requirements.append("Revisión del anexo de IA y de los proveedores autorizados.")

        if self._get(answers, "scope.change_control") is True:
            selected.append("ACT-EM-CHANGE-001")

        risk_allocation = self._get(answers, "risk_allocation")
        if isinstance(risk_allocation, dict) and risk_allocation.get("insurance_required"):
            blocks.append("EM-INS-001")

        mechanism = self._get(answers, "disputes.mechanism")
        if mechanism in ("arbitration", "amicable_composition"):
            review_requirements.append("Validar sede, centro, cuantía, costos y alcance del mecanismo alternativo elegido.")

        blocked = any(item["severity"] == "blocker" for item in findings)
        warnings = [item for item in findings if item["severity"] == "review"]
        return {
            "version": "2.43",
            "blocked": blocked,
            "labor_risk_score": score,
            "risk_level": "high" if score >= 8 else "medium" if score >= 4 else "low",
            "findings": findings,
            "warnings": warnings,
            "review_requirements": list(dict.fromkeys(review_requirements)),
            "missing_fields": missing,
            "documents": list(dict.fromkeys(selected)),
            "blocks": list(dict.fromkeys(blocks)),
            "ready": not blocked and not missing,
            "readiness": "blocked" if blocked else "incomplete" if missing else "requires_review" if review_requirements else "ready_to_generate",
        }
