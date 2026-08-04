from __future__ import annotations
from co_em_003_v243 import CoEm003CanonicalV243


class CoEm003CanonicalV244(CoEm003CanonicalV243):
    """Closure evaluator with expanded contract-reality indicators and scenario metadata."""

    WEIGHTS = {
        "fixed_schedule": 2,
        "attendance_control": 1,
        "continuous_orders": 3,
        "daily_method_control": 3,
        "continuous_supervision": 2,
        "org_integration": 2,
        "absence_authorization": 2,
        "employee_identity": 2,
        "internal_labor_rules": 2,
        "disciplinary_measures": 4,
        "vacation_permission": 2,
        "exclusivity_or_availability": 2,
        "economic_dependence": 1,
        "personal_continuous_periodic": 1,
        "periodic_payment_without_outputs": 1,
        "personal_service_required": 1,
        "fixed_location": 1,
    }

    def summary(self):
        data = super().summary()
        data["manifest"] = dict(data["manifest"])
        data["manifest"].update({
            "version": "2.44",
            "status": "macro_c_validated_and_closed",
            "canonical_scenarios": 12,
            "negative_scenarios": 15,
            "structured_form_controls": True,
            "expanded_labor_risk_factors": len(self.WEIGHTS) + 2,
        })
        data["version"] = "2.44"
        return data

    def evaluate(self, answers):
        result = super().evaluate(answers)
        indicators = self._get(answers or {}, "labor_indicators") or {}
        factors = []
        score = 0
        for key, weight in self.WEIGHTS.items():
            if isinstance(indicators, dict) and indicators.get(key) is True:
                score += weight
                factors.append({"id": key, "weight": weight})
        if self._get(answers or {}, "autonomy.methods") is False:
            score += 3
            factors.append({"id": "no_method_autonomy", "weight": 3})
        if self._get(answers or {}, "autonomy.delegation") is False:
            score += 1
            factors.append({"id": "no_delegation", "weight": 1})

        findings = [x for x in result.get("findings", []) if x.get("id") not in ("V-EM-003", "V-EM-004")]
        reviews = [x for x in result.get("review_requirements", []) if "subordinación" not in x.lower()]

        disciplinary = isinstance(indicators, dict) and indicators.get("disciplinary_measures") is True
        incompatible_combo = disciplinary and (
            indicators.get("continuous_orders") is True or indicators.get("daily_method_control") is True
        )
        strong_single = any(
            isinstance(indicators, dict) and indicators.get(k) is True
            for k in ("fixed_schedule", "continuous_orders", "daily_method_control", "disciplinary_measures")
        )
        if incompatible_combo:
            findings.append({
                "id": "V-EM-013", "severity": "blocker",
                "message": "La combinación de dirección continuada y disciplina es incompatible con la autonomía declarada y debe rediseñarse como relación laboral o como operación verdaderamente independiente.",
            })
            reviews.append("Revisión laboral obligatoria por dirección y disciplina incompatibles con un contrato independiente.")
        elif score >= 8:
            findings.append({
                "id": "V-EM-003", "severity": "blocker",
                "message": "Riesgo alto de contrato realidad. La configuración debe rediseñarse o manejarse mediante una relación laboral.",
            })
            reviews.append("Revisión laboral obligatoria por posible subordinación real.")
        elif score >= 4 or strong_single:
            findings.append({
                "id": "V-EM-004", "severity": "review",
                "message": "Existen indicios materiales de subordinación o integración organizacional. La generación requiere revisión jurídica previa y contraste con la operación real.",
            })
            reviews.append("Revisión jurídica del riesgo de subordinación y de la operación real.")

        # Conditional completeness for sensitive modules.
        conditional_requirements = []
        if self._get(answers or {}, "confidentiality.required") is True:
            conditional_requirements.extend((
                ("confidentiality.categories", "Categorías de información confidencial"),
                ("confidentiality.duration", "Duración de la confidencialidad"),
                ("confidentiality.return_rule", "Regla de devolución y conservación"),
            ))
        if self._get(answers or {}, "data_processing.required") is True:
            conditional_requirements.extend((
                ("data_processing.roles.client", "Rol del contratante en datos personales"),
                ("data_processing.roles.contractor", "Rol del contratista en datos personales"),
                ("data_processing.roles.categories", "Categorías de datos y titulares"),
                ("data_processing.instructions", "Instrucciones y seguridad del tratamiento"),
            ))
        if self._get(answers or {}, "ip.required") is True:
            conditional_requirements.extend((
                ("ip.allocation.new_results", "Asignación de resultados nuevos"),
                ("ip.allocation.background", "Tratamiento de materiales preexistentes"),
                ("ip.allocation.open_source", "Regla de código abierto y licencias"),
            ))
        for path, label in conditional_requirements:
            if self._empty(self._get(answers or {}, path)):
                result["missing_fields"].append({"path": path, "label": label, "severity": "required"})
        if self._get(answers or {}, "ai.required") is True:
            for path, label in (
                ("ai.allowed_tools", "Herramientas de IA autorizadas"),
                ("ai.permitted_uses", "Usos permitidos de IA"),
                ("ai.prohibited_data", "Información prohibida en IA"),
                ("ai.human_review", "Revisión humana de IA"),
            ):
                if self._empty(self._get(answers or {}, path)):
                    result["missing_fields"].append({"path": path, "label": label, "severity": "required"})
        if self._get(answers or {}, "service.regulated") is True and self._get(answers or {}, "service.habilitation_verified") is True:
            for path, label in (("service.habilitation_type", "Tipo de habilitación"), ("service.habilitation_reference", "Referencia y vigencia de la habilitación")):
                if self._empty(self._get(answers or {}, path)):
                    result["missing_fields"].append({"path":path,"label":label,"severity":"required"})

        result["version"] = "2.44"
        result["labor_risk_score"] = score
        result["labor_risk_factors"] = factors
        result["findings"] = findings
        result["warnings"] = [x for x in findings if x.get("severity") == "review"]
        result["review_requirements"] = list(dict.fromkeys(reviews))
        result["blocked"] = any(x.get("severity") == "blocker" for x in findings)
        result["risk_level"] = "high" if result["blocked"] or score >= 8 else "medium" if score >= 4 or strong_single else "low"
        # Deduplicate missing paths after conditional checks.
        seen = set(); missing = []
        for item in result.get("missing_fields", []):
            if item["path"] not in seen:
                seen.add(item["path"]); missing.append(item)
        result["missing_fields"] = missing
        result["ready"] = not result["blocked"] and not missing
        result["readiness"] = "blocked" if result["blocked"] else "incomplete" if missing else "requires_review" if result["review_requirements"] else "ready_to_generate"
        return result
