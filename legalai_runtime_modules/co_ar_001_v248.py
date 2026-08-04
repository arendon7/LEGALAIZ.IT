from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CoAr001CanonicalV248:
    """Capa canónica funcional de CO-AR-001 v2.48.

    Conserva la maduración v2.23 y añade una entrevista guiada, controles
    explicables y selección documental para arrendamiento de vivienda urbana.
    """

    VERSION = "2.48"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base = self.root / "app" / "assets" / "advanced-legal-library" / "CO-AR-001"
        self.manifest = self._load("MANIFEST_CO-AR-001.json")
        questions = self._load("PREGUNTAS_CANONICAS.json")
        self.steps = questions["steps"]
        self.questions = questions["questions"]
        self.profiles = self._load("PERFILES_ARRENDAMIENTO.json")
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

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _validate_catalogs(self) -> None:
        actual = {
            "steps": len(self.steps), "questions": len(self.questions),
            "profiles": len(self.profiles), "documents": len(self.documents),
            "validations": len(self.validations), "blocks": len(self.blocks),
            "sources": len(self.sources),
        }
        for key, value in actual.items():
            if self.manifest.get(key) != value:
                raise ValueError(f"Conteo inconsistente para {key}: {value}.")
        for name, items in (
            ("preguntas", self.questions), ("perfiles", self.profiles),
            ("documentos", self.documents), ("validaciones", self.validations),
            ("bloques", self.blocks), ("fuentes", self.sources),
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
        if question.get("type") in {"group", "structured"}:
            if not isinstance(value, dict):
                return [{"path": path, "question_id": question["id"], "step_id": question["step_id"], "label": question["label"]}]
            result = []
            for field in question.get("fields", []):
                if field.get("required") and not self._filled(value.get(field["key"])):
                    result.append({
                        "path": f"{path}.{field['key']}", "question_id": question["id"],
                        "step_id": question["step_id"], "label": f"{question['label']}: {field['label']}",
                    })
            return result
        if not self._filled(value):
            return [{"path": path, "question_id": question["id"], "step_id": question["step_id"], "label": question["label"]}]
        return []

    def evaluate(self, answers: dict[str, Any]) -> dict[str, Any]:
        missing: list[dict[str, Any]] = []
        for question in self.questions:
            missing.extend(self._question_missing(question, answers))

        findings: list[dict[str, Any]] = []
        docs = [
            "DOC-AR-CONTRACT-001", "ANX-AR-PROPERTY-001", "ANX-AR-INVENTORY-001",
            "ACT-AR-DELIVERY-001", "ACT-AR-RESTITUTION-001",
        ]
        blocks = [
            "AR-TIT-001", "AR-CMP-001", "AR-CON-001", "AR-OBJ-001", "AR-ID-001",
            "AR-INCL-001", "AR-DEST-001", "AR-OCC-001", "AR-DEL-001", "AR-HAB-001",
            "AR-INV-001", "AR-RENT-001", "AR-PAY-001", "AR-ADJ-001", "AR-DUR-001",
            "AR-EXT-001", "AR-LAND-OBL-001", "AR-TEN-OBL-001", "AR-MAIN-001",
            "AR-NOT-001", "AR-REST-001", "AR-CLOSE-001", "AR-INT-001", "AR-SIGN-001",
        ]

        landlord_type = self._get(answers, "landlord.identification.type")
        signatory = self._get(answers, "landlord.signatory", {})
        if landlord_type == "legal" and (not isinstance(signatory, dict) or not signatory.get("name") or not signatory.get("authority_source")):
            findings.append({"id": "V-AR-002", "severity": "blocker", "message": "La persona jurídica arrendadora requiere firmante identificado y fuente verificable de facultad."})

        scope = self._get(answers, "scope.urban_home")
        if scope != "yes":
            findings.append({"id": "V-AR-001", "severity": "blocker", "message": "Este producto solo cubre arrendamiento de vivienda urbana ordinaria; el uso comercial, rural o turístico exige otro instrumento."})

        authority = self._get(answers, "landlord.authority_evidence")
        if authority == "absent":
            findings.append({"id": "V-AR-002", "severity": "blocker", "message": "No existe soporte suficiente de propiedad, representación o autorización para entregar el inmueble."})
        elif authority == "pending":
            findings.append({"id": "V-AR-002", "severity": "review", "message": "La facultad del arrendador debe acreditarse antes de la firma y entrega."})

        dispute = self._get(answers, "property.dispute_status")
        if dispute in {"litigation", "restitution", "occupied", "restriction"}:
            findings.append({"id": "V-AR-003", "severity": "blocker", "message": "La controversia, ocupación o limitación informada requiere revisión jurídica y registral antes de contratar."})
        elif dispute == "unknown":
            findings.append({"id": "V-AR-003", "severity": "review", "message": "Debe verificarse la situación jurídica y material del inmueble."})

        ph = self._get(answers, "property.horizontal") is True
        if ph:
            docs.append("ANX-AR-PH-001"); blocks.extend(["AR-PH-001", "AR-CONV-001"])
            rules_delivery = self._get(answers, "property.ph_details.rules_delivery")
            if rules_delivery != "yes":
                findings.append({"id": "V-AR-007", "severity": "review", "message": "Debe entregarse y dejarse trazabilidad de la parte normativa aplicable del reglamento de propiedad horizontal."})

        destination = self._get(answers, "use.destination")
        sublease = self._get(answers, "use.sublease_tourism")
        if destination in {"mixed_or_commercial", "other"} or sublease in {"tourism", "platform"}:
            findings.append({"id": "V-AR-009", "severity": "blocker", "message": "El destino mixto, comercial, turístico o por plataformas se encuentra fuera del alcance de vivienda urbana ordinaria."})
        elif sublease in {"sublease_requested", "unknown"}:
            findings.append({"id": "V-AR-010", "severity": "review", "message": "La cesión o el subarriendo requieren autorización expresa y delimitación del alcance."})
            blocks.append("AR-SUB-001")

        multiple = self._get(answers, "occupants.multiple") is True
        lease_configuration = self._get(answers, "lease.configuration")
        pets = self._get(answers, "pets.exists") is True
        if multiple or lease_configuration in {"joint", "shared", "pension"} or pets:
            docs.append("ANX-AR-OCCUPANTS-001"); blocks.extend(["AR-SHARED-001", "AR-PET-001"])
        if multiple and self._get(answers, "tenant.additional.solidarity") in {None, "", "to_define"}:
            findings.append({"id": "V-AR-013", "severity": "review", "message": "Debe definirse el alcance de las obligaciones de los arrendatarios adicionales y la solidaridad, cuando proceda."})
        if pets and not self._filled(self._get(answers, "pets.conditions")):
            findings.append({"id": "V-AR-013", "severity": "review", "message": "Conviene establecer condiciones proporcionadas sobre mascotas, convivencia, daños y zonas comunes."})

        habitability = self._get(answers, "condition.habitability")
        if habitability == "unsafe":
            findings.append({"id": "V-AR-008", "severity": "blocker", "message": "No debe entregarse un inmueble con riesgo grave de sanidad, seguridad o falta de servicios esenciales."})
        elif habitability in {"material_defects", "unknown"}:
            findings.append({"id": "V-AR-008", "severity": "review", "message": "La entrega exige inspección, reparaciones, plazos y evidencia del estado de habitabilidad."})

        furnished = self._get(answers, "property.furnished") is True
        high_value = self._get(answers, "property.high_value_assets") is True
        if furnished or high_value:
            docs.append("ANX-AR-FURNISHED-001"); blocks.append("AR-FURN-001")
            if self._get(answers, "delivery.inventory_method") not in {"detailed", "combined"}:
                findings.append({"id": "V-AR-012", "severity": "review", "message": "Los muebles y bienes de valor requieren inventario individualizado, estado, evidencia y valor de referencia."})

        rent = self._number(self._get(answers, "rent.amount"))
        commercial = self._number(self._get(answers, "rent.values.commercial_value"))
        cadastral = self._number(self._get(answers, "rent.values.cadastral_value"))
        allowed_commercial = commercial
        if commercial is not None and cadastral is not None and commercial > 2 * cadastral:
            findings.append({"id": "V-AR-006", "severity": "blocker", "message": "Para el límite legal del canon, la estimación comercial informada supera dos veces el avalúo catastral vigente."})
            allowed_commercial = 2 * cadastral
        if rent is not None and allowed_commercial is not None and rent > 0.01 * allowed_commercial:
            findings.append({"id": "V-AR-005", "severity": "blocker", "message": "El canon mensual excede el uno por ciento del valor comercial admisible del inmueble o de la parte arrendada."})
        if commercial is None:
            findings.append({"id": "V-AR-005", "severity": "review", "message": "Debe soportarse el valor comercial para verificar el límite máximo del canon."})

        adjustment = self._get(answers, "rent.adjustment")
        if adjustment in {"fixed_or_other", "none"}:
            findings.append({"id": "V-AR-016", "severity": "review", "message": "El reajuste debe respetar el límite legal, la periodicidad mínima de doce meses y la comunicación oponible al arrendatario."})
        docs.append("COM-AR-ADJUSTMENT-001")

        additional_exists = self._get(answers, "charges.additional_services.exists") is True
        additional_value = self._number(self._get(answers, "charges.additional_services.value")) or 0
        if additional_exists:
            docs.append("ANX-AR-SERVICES-001"); blocks.append("AR-ADD-001")
            if rent and additional_value > 0.5 * rent:
                findings.append({"id": "V-AR-011", "severity": "blocker", "message": "El valor de los servicios, cosas o usos adicionales supera el cincuenta por ciento del canon del inmueble."})

        utilities = self._get(answers, "charges.utilities.responsible")
        denunciation = self._get(answers, "utilities.denunciation")
        if utilities == "special" or denunciation in {"yes", "to_define"} or ph:
            docs.append("ANX-AR-SERVICES-001"); blocks.extend(["AR-UTIL-001", "AR-SERV-GUAR-001", "AR-ADMIN-001"])
        if utilities == "special" and not self._filled(self._get(answers, "charges.utilities.distribution")):
            findings.append({"id": "V-AR-015", "severity": "review", "message": "La distribución especial de servicios requiere fórmula, medidores, soportes, fechas y responsables."})
        if denunciation == "to_define":
            findings.append({"id": "V-AR-015", "severity": "review", "message": "Debe decidirse si se aplicará el procedimiento de denuncia y garantías ante las empresas de servicios públicos."})

        guarantee_type = self._get(answers, "guarantee.type")
        if guarantee_type and guarantee_type != "none":
            docs.append("ANX-AR-GUARANTEE-001"); blocks.append("AR-GUAR-001")
            gd = self._get(answers, "guarantee.details", {})
            if not isinstance(gd, dict) or not gd.get("party") or not gd.get("scope"):
                findings.append({"id": "V-AR-014", "severity": "blocker", "message": "La garantía personal o póliza debe identificar garante, alcance, vigencia y obligaciones cubiertas."})
        if self._get(answers, "guarantee.cash_deposit") is True:
            findings.append({"id": "V-AR-004", "severity": "blocker", "message": "En vivienda urbana no puede exigirse depósito en dinero ni caución real a favor del arrendador para garantizar obligaciones contractuales."})

        special_term = self._get(answers, "term.rules.special_termination")
        notice_days = self._number(self._get(answers, "term.rules.notice_days"))
        if self._filled(special_term) or (notice_days is not None and notice_days < 90):
            docs.append("NOT-AR-TERMINATION-001"); blocks.append("AR-TERM-SPEC-001")
            findings.append({"id": "V-AR-017", "severity": "review", "message": "La terminación especial y los preavisos deben ajustarse a la causal, indemnidad, oportunidad y forma de comunicación legalmente aplicables."})

        screening = self._get(answers, "data.screening", {})
        if isinstance(screening, dict) and (screening.get("credit_study") is True or screening.get("personal_data") or screening.get("sensitive_documents") is True):
            docs.append("AUT-AR-DATA-001"); blocks.append("AR-DATA-001")
        if isinstance(screening, dict) and screening.get("sensitive_documents") is True:
            findings.append({"id": "V-AR-018", "severity": "review", "message": "La solicitud de datos sensibles o documentos especialmente delicados exige necesidad, proporcionalidad, seguridad y revisión especializada."})

        if self._get(answers, "confirmation.reviewed") is not True:
            findings.append({"id": "V-AR-018", "severity": "blocker", "message": "La generación exige confirmar datos, soportes, inventario y decisiones contractuales."})

        docs = list(dict.fromkeys(docs))
        blocks = list(dict.fromkeys(blocks))
        blockers = [x for x in findings if x["severity"] == "blocker"]
        reviews = [x for x in findings if x["severity"] == "review"]
        essential_missing = [x for x in missing if x["step_id"] in {"parties", "property", "use", "economics", "term", "documents"}]
        status = "blocked" if blockers else "incomplete" if essential_missing else "review_required" if reviews else "ready"
        answered = len(self.questions) - len({x["question_id"] for x in missing})
        completion = max(0, min(100, round(100 * answered / len(self.questions))))
        return {
            "version": self.VERSION,
            "status": status,
            "blocked": bool(blockers),
            "findings": findings,
            "blockers": blockers,
            "reviews": reviews,
            "missing_fields": missing,
            "documents": docs,
            "blocks": blocks,
            "professional_reviews": sorted(set(
                ["legal"] * bool(reviews or blockers)
                + ["property_title"] * bool(dispute not in {None, "", "none"})
                + ["habitability"] * bool(habitability in {"unsafe", "material_defects", "unknown"})
                + ["data_protection"] * bool(isinstance(screening, dict) and screening.get("sensitive_documents") is True)
            )),
            "completion": {"answered": answered, "total": len(self.questions), "percent": completion},
            "explanations": [
                "La calificación contractual no reemplaza la verificación de la realidad jurídica, registral y material del inmueble.",
                "El canon, las garantías, los reajustes y la terminación están sujetos a límites imperativos de vivienda urbana.",
                "La aprobación final requiere revisión profesional cuando exista un hallazgo de bloqueo o revisión.",
            ],
        }
