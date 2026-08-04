from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from co_tr_002_v254 import CoTr002CanonicalV254 as _BaseV254
    BASE_V254_AVAILABLE = True
except ImportError:
    BASE_V254_AVAILABLE = False

    class _BaseV254:
        """Adaptador de QA. La publicación exige instalar sobre la base v2.54 real."""

        VERSION = "2.54-adapter"

        def __init__(self, root: Path | None = None):
            self.root = Path(root or ".")

        @staticmethod
        def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
            value: Any = data
            for part in path.split("."):
                if not isinstance(value, dict) or part not in value:
                    return default
                value = value[part]
            return value

        def summary(self) -> dict[str, Any]:
            return {
                "manifest": {
                    "product_id": "CO-TR-002",
                    "version": self.VERSION,
                    "status": "macro_a_functional_adapter",
                }
            }

        def evaluate(self, answers: dict[str, Any]) -> dict[str, Any]:
            get = self._get
            required = [
                ("identity.full_name", "Nombre completo"),
                ("identity.document_number", "Documento de identidad"),
                ("identity.email", "Correo para notificaciones"),
                ("authority.name", "Autoridad de tránsito"),
                ("infraction.comparendo_number", "Número de comparendo"),
                ("infraction.plate", "Placa"),
                ("infraction.date", "Fecha de la infracción"),
                ("infraction.notice_status", "Estado de notificación"),
            ]
            missing = [
                {"path": path, "label": label}
                for path, label in required
                if get(answers, path) in (None, "", [])
            ]
            findings: list[dict[str, Any]] = []
            reviews: list[str] = []
            blocked = False

            red_conditions = [
                ("procedure.judicial_active", "COTR2-RED-JUDICIAL", "Existe proceso judicial activo."),
                ("procedure.embargo_active", "COTR2-RED-EMBARGO", "Existe embargo activo."),
                ("procedure.imminent_judicial_deadline", "COTR2-RED-TERM", "Existe término judicial inminente."),
                ("procedure.possible_fraud", "COTR2-RED-FRAUD", "Existe indicio de fraude o alteración documental."),
                ("payment.paid", "COTR2-RED-PAID", "La obligación fue pagada y cualquier devolución exige análisis individual."),
                ("payment.agreement", "COTR2-RED-AGREEMENT", "Existe acuerdo de pago y deben evaluarse sus efectos antes de actuar."),
            ]
            for path, finding_id, message in red_conditions:
                if bool(get(answers, path)):
                    blocked = True
                    findings.append({"id": finding_id, "risk": "red", "message": message})
                    reviews.append(message)

            collection = str(get(answers, "procedure.collection_stage") or "").lower()
            if collection in {"advanced", "mandamiento_pago", "embargo", "cobro_coactivo_avanzado"}:
                blocked = True
                message = "Existe cobro coactivo avanzado o mandamiento de pago."
                findings.append({"id": "COTR2-RED-COBRO", "risk": "red", "message": message})
                reviews.append(message)
            elif collection in {"pre_cobro", "persuasivo", "cobro_persuasivo"}:
                message = "Existe gestión de cobro previa; deben controlarse términos, actos y pagos."
                findings.append({"id": "COTR2-YEL-COBRO", "risk": "yellow", "message": message})
                reviews.append(message)

            if get(answers, "procedure.sanction_resolution") or str(get(answers, "procedure.stage") or "").lower() == "sanction":
                message = "La existencia de acto sancionatorio requiere revisión jurídica antes de radicar revocatoria."
                reviews.append(message)
                findings.append({"id": "COTR2-YEL-SANCTION", "risk": "yellow", "message": message})
            if get(answers, "procedure.driver_identification_complex"):
                message = "La identificación del presunto infractor presenta complejidad probatoria."
                reviews.append(message)
                findings.append({"id": "COTR2-YEL-DRIVER", "risk": "yellow", "message": message})
            if get(answers, "procedure.multiple_comparendos") or get(answers, "procedure.multiple_authorities"):
                message = "Existen múltiples actuaciones; cada autoridad y comparendo debe conservar expediente separado."
                reviews.append(message)
                findings.append({"id": "COTR2-YEL-MULTI", "risk": "yellow", "message": message})

            documents = ["traffic_record_request", "traffic_notice_claim", "traceability"]
            stage = str(get(answers, "procedure.stage") or "").lower()
            if get(answers, "requests.hearing") or stage in {"comparendo", "pre_sanction"}:
                documents.append("traffic_hearing_request")
            if get(answers, "procedure.sanction_resolution") or stage == "sanction":
                documents.append("traffic_revocation_request")
            if get(answers, "registry.simit_incorrect") or get(answers, "registry.runt_incorrect"):
                documents.append("traffic_registry_correction")
            if get(answers, "prior_filing.no_response"):
                documents.append("traffic_reiteration")
            if blocked or reviews:
                documents.append("traffic_escalation_guide")

            blocks = [
                "B256-CONTROL-PREVIO",
                "B256-IDENTIFICACION",
                "B256-HECHOS-NOTIFICACION",
                "B256-SOLICITUD-EXPEDIENTE",
                "B256-PRUEBAS",
                "B256-ANEXOS",
                "B256-FIRMA",
            ]
            if get(answers, "procedure.sanction_resolution") or stage == "sanction":
                blocks.append("B256-REVOCATORIA-CONDICIONADA")
            if get(answers, "registry.simit_incorrect") or get(answers, "registry.runt_incorrect"):
                blocks.append("B256-CORRECCION-REGISTROS")
            if reviews:
                blocks.append("B256-REVISION-PROFESIONAL")

            status = "blocked" if blocked else "incomplete" if missing else "ready_with_review" if reviews else "ready"
            return {
                "product_id": "CO-TR-002",
                "version": self.VERSION,
                "blocked": blocked,
                "status": status,
                "missing_fields": missing,
                "findings": findings,
                "professional_reviews": reviews,
                "documents": list(dict.fromkeys(documents)),
                "blocks": list(dict.fromkeys(blocks)),
                "risk": "red" if blocked else "yellow" if reviews else "green",
            }


class CoTr002CanonicalV256(_BaseV254):
    """CO-TR-002, Macrofase C: validación, endurecimiento y cierre controlado."""

    VERSION = "2.56"
    BASE_AVAILABLE = BASE_V254_AVAILABLE

    def __init__(self, root: Path | None = None):
        try:
            super().__init__(root or Path("."))
        except TypeError:
            super().__init__()
            self.root = Path(root or ".")

    @staticmethod
    def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
        value: Any = data
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _business_days_between(start: date, end: date) -> int:
        if end <= start:
            return 0
        days = 0
        current = start
        while current < end:
            current += timedelta(days=1)
            if current.weekday() < 5:
                days += 1
        return days

    @staticmethod
    def _append_finding(result: dict[str, Any], finding_id: str, risk: str, message: str) -> None:
        findings = list(result.get("findings") or [])
        if finding_id not in {item.get("id") for item in findings}:
            findings.append({"id": finding_id, "risk": risk, "message": message})
        result["findings"] = findings
        reviews = list(result.get("professional_reviews") or result.get("review_requirements") or [])
        if message not in reviews:
            reviews.append(message)
        result["professional_reviews"] = reviews
        result["review_requirements"] = reviews

    def summary(self) -> dict[str, Any]:
        data = super().summary()
        manifest = dict(data.get("manifest") or {})
        manifest.update(
            {
                "product_id": "CO-TR-002",
                "version": self.VERSION,
                "status": "macro_c_validation_closure",
                "document_factory": True,
                "governance": True,
                "immutable_revisions": True,
                "dual_approval": True,
                "cryptographic_integrity": True,
                "validation_closed": True,
                "release_gate": True,
                "official_source_control": True,
                "api_error_hardening": True,
                "canonical_scope_frozen": True,
                "supersedes": "2.55",
                "base_v254_available": self.BASE_AVAILABLE,
            }
        )
        data["manifest"] = manifest
        data["version"] = self.VERSION
        return data

    @staticmethod
    def _looks_like_v256_schema(answers: dict[str, Any]) -> bool:
        return any(key in answers for key in ("identity", "infraction", "procedure", "payment", "registry", "requests"))

    def to_document_answers(self, answers: dict[str, Any]) -> dict[str, Any]:
        """Normaliza la entrevista canónica v2.54 al contrato documental v2.56.

        La Macrofase C puede recibir tanto los escenarios compactos usados por la
        suite de validación como las respuestas reales del formulario canónico.
        Nunca inventa identificadores ni hechos: los valores faltantes permanecen
        vacíos para que la fábrica bloquee la generación.
        """
        if self._looks_like_v256_schema(answers):
            return answers

        get = self._get
        petitioner = get(answers, "petitioner.identity", {}) or {}
        authority = get(answers, "authority.identity", {}) or {}
        vehicle = get(answers, "vehicle.identity", {}) or {}
        case = get(answers, "case.identifiers", {}) or {}
        notice = get(answers, "notice.timeline", {}) or {}
        actual_knowledge = get(answers, "notice.actual_knowledge", {}) or {}
        resolution = get(answers, "stage.resolution", {}) or {}
        hearing = get(answers, "stage.hearing", {}) or {}
        prior = get(answers, "evidence.prior_actions", {}) or {}
        selection = get(answers, "documents.selection", {}) or {}
        inventory = get(answers, "evidence.inventory", {}) or {}

        received = str(get(answers, "notice.comparendo_received") or "").lower()
        notice_status = {
            "yes": "Recibida",
            "no": "No recibida",
            "unknown": "No determinada",
        }.get(received, received or "")

        resolution_exists = str(get(answers, "stage.resolution_exists") or "").lower()
        coercive = str(get(answers, "stage.coercive") or "").lower()
        active_process = str(get(answers, "stage.active_process") or "").lower()
        payment_state = str(get(answers, "stage.payment") or "").lower()
        urgency = str(get(answers, "deadlines.urgency") or "").lower()
        integrity = str(get(answers, "evidence.integrity_concern") or "").lower()

        if coercive in {"payment_order", "exceptions_pending", "embargo"}:
            collection_stage = "advanced"
        elif coercive not in {"", "none", "not_applicable"}:
            collection_stage = "pre_cobro"
        else:
            collection_stage = "none"

        evidence_items: list[str] = []
        evidence_labels = {
            "comparendo": "Copia o consulta de la orden de comparendo.",
            "images": "Fotografías o video asociados a la detección.",
            "mailing": "Guía de envío, entrega o devolución.",
            "resolution": "Copia de la resolución sancionatoria.",
            "runt": "Histórico o consulta de datos RUNT.",
            "simit": "Consulta del estado en SIMIT.",
            "sale_or_theft": "Soportes de venta, traspaso, hurto o entrega.",
            "prior_filings": "Radicados y respuestas previas.",
        }
        for key, label in evidence_labels.items():
            value = inventory.get(key)
            if value in (True, "yes", "sí", "si", "available", "attached"):
                evidence_items.append(label)

        stage = "sanction" if resolution_exists == "yes" else "pre_sanction"
        if payment_state in {"discount_paid", "full_paid", "payment_agreement"}:
            stage = "paid"

        return {
            "identity": {
                "full_name": petitioner.get("name"),
                "document_type": petitioner.get("id_type"),
                "document_number": petitioner.get("id_number"),
                "email": petitioner.get("email"),
                "address": petitioner.get("address"),
                "city": authority.get("municipality"),
                "phone": petitioner.get("phone"),
            },
            "authority": {
                "name": authority.get("name"),
                "city": authority.get("municipality"),
                "email": authority.get("email"),
                "office": authority.get("office"),
            },
            "infraction": {
                "comparendo_number": case.get("comparendo_number"),
                "plate": vehicle.get("plate"),
                "date": case.get("event_date"),
                "validation_date": case.get("issue_date"),
                "sent_date": notice.get("sent_date"),
                "notice_date": notice.get("received_date") or notice.get("notice_date") or actual_knowledge.get("date"),
                "notice_status": notice_status,
                "address_used": get(answers, "notice.address_used") or petitioner.get("address"),
                "location": case.get("location"),
                "code": case.get("infraction_code"),
                "amount": case.get("amount"),
            },
            "notice": {
                "delivery_proof_received": bool(inventory.get("mailing")),
            },
            "procedure": {
                "stage": stage,
                "sanction_resolution": resolution.get("number") if resolution_exists == "yes" else None,
                "judicial_active": active_process not in {"", "none", "not_applicable"},
                "embargo_active": coercive == "embargo",
                "collection_stage": collection_stage,
                "imminent_judicial_deadline": urgency in {"under_3_days", "under_10_days"},
                "possible_fraud": integrity == "yes",
                "driver_identification_complex": str(get(answers, "responsibility.was_driver") or "").lower() == "unknown",
                "multiple_comparendos": str(get(answers, "case.multiple") or "").lower() == "yes",
                "multiple_authorities": False,
            },
            "payment": {
                "paid": payment_state in {"discount_paid", "full_paid"},
                "agreement": payment_state == "payment_agreement",
            },
            "requests": {
                "hearing": bool(hearing.get("requested")) or bool(selection.get("hearing_request")) or resolution_exists == "no",
            },
            "registry": {
                "simit_incorrect": bool(selection.get("registry_correction")) or get(answers, "strategy.objective") == "registry_correction",
                "runt_incorrect": bool(selection.get("registry_correction")) or get(answers, "strategy.objective") == "registry_correction",
            },
            "prior_filing": {
                "no_response": prior.get("exists") == "yes" and prior.get("answered") in {"no", "unknown"},
                "number": prior.get("filing_number"),
                "date": prior.get("filing_date"),
            },
            "evidence": {"items": evidence_items},
            "case": {"narrative": get(answers, "responsibility.facts")},
            "filing": {
                "city": authority.get("municipality"),
                "date": date.today().isoformat(),
            },
        }

    def _evaluate_simple_schema(self, answers: dict[str, Any]) -> dict[str, Any]:
        """Motor determinístico usado por los escenarios v2.56."""
        get = self._get
        required = [
            ("identity.full_name", "Nombre completo"),
            ("identity.document_number", "Documento de identidad"),
            ("identity.email", "Correo para notificaciones"),
            ("authority.name", "Autoridad de tránsito"),
            ("infraction.comparendo_number", "Número de comparendo"),
            ("infraction.plate", "Placa"),
            ("infraction.date", "Fecha de la infracción"),
            ("infraction.notice_status", "Estado de notificación"),
        ]
        missing = [
            {"path": path, "label": label}
            for path, label in required
            if get(answers, path) in (None, "", [])
        ]
        findings: list[dict[str, Any]] = []
        reviews: list[str] = []
        blocked = False

        red_conditions = [
            ("procedure.judicial_active", "COTR2-RED-JUDICIAL", "Existe proceso judicial activo."),
            ("procedure.embargo_active", "COTR2-RED-EMBARGO", "Existe embargo activo."),
            ("procedure.imminent_judicial_deadline", "COTR2-RED-TERM", "Existe término judicial inminente."),
            ("procedure.possible_fraud", "COTR2-RED-FRAUD", "Existe indicio de fraude o alteración documental."),
            ("payment.paid", "COTR2-RED-PAID", "La obligación fue pagada y cualquier devolución exige análisis individual."),
            ("payment.agreement", "COTR2-RED-AGREEMENT", "Existe acuerdo de pago y deben evaluarse sus efectos antes de actuar."),
        ]
        for path, finding_id, message in red_conditions:
            if bool(get(answers, path)):
                blocked = True
                findings.append({"id": finding_id, "risk": "red", "message": message})
                reviews.append(message)

        collection = str(get(answers, "procedure.collection_stage") or "").lower()
        if collection in {"advanced", "mandamiento_pago", "embargo", "cobro_coactivo_avanzado"}:
            blocked = True
            message = "Existe cobro coactivo avanzado o mandamiento de pago."
            findings.append({"id": "COTR2-RED-COBRO", "risk": "red", "message": message})
            reviews.append(message)
        elif collection in {"pre_cobro", "persuasivo", "cobro_persuasivo"}:
            message = "Existe gestión de cobro previa; deben controlarse términos, actos y pagos."
            findings.append({"id": "COTR2-YEL-COBRO", "risk": "yellow", "message": message})
            reviews.append(message)

        if get(answers, "procedure.sanction_resolution") or str(get(answers, "procedure.stage") or "").lower() == "sanction":
            message = "La existencia de acto sancionatorio requiere revisión jurídica antes de radicar revocatoria."
            reviews.append(message)
            findings.append({"id": "COTR2-YEL-SANCTION", "risk": "yellow", "message": message})
        if get(answers, "procedure.driver_identification_complex"):
            message = "La identificación del presunto infractor presenta complejidad probatoria."
            reviews.append(message)
            findings.append({"id": "COTR2-YEL-DRIVER", "risk": "yellow", "message": message})
        if get(answers, "procedure.multiple_comparendos") or get(answers, "procedure.multiple_authorities"):
            message = "Existen múltiples actuaciones; cada autoridad y comparendo debe conservar expediente separado."
            reviews.append(message)
            findings.append({"id": "COTR2-YEL-MULTI", "risk": "yellow", "message": message})

        documents = ["traffic_record_request", "traffic_notice_claim", "traceability"]
        stage = str(get(answers, "procedure.stage") or "").lower()
        if get(answers, "requests.hearing") or stage in {"comparendo", "pre_sanction"}:
            documents.append("traffic_hearing_request")
        if get(answers, "procedure.sanction_resolution") or stage == "sanction":
            documents.append("traffic_revocation_request")
        if get(answers, "registry.simit_incorrect") or get(answers, "registry.runt_incorrect"):
            documents.append("traffic_registry_correction")
        if get(answers, "prior_filing.no_response"):
            documents.append("traffic_reiteration")
        if blocked or reviews:
            documents.append("traffic_escalation_guide")

        blocks = [
            "B256-CONTROL-PREVIO", "B256-IDENTIFICACION", "B256-HECHOS-NOTIFICACION",
            "B256-SOLICITUD-EXPEDIENTE", "B256-PRUEBAS", "B256-ANEXOS", "B256-FIRMA",
        ]
        if get(answers, "procedure.sanction_resolution") or stage == "sanction":
            blocks.append("B256-REVOCATORIA-CONDICIONADA")
        if get(answers, "registry.simit_incorrect") or get(answers, "registry.runt_incorrect"):
            blocks.append("B256-CORRECCION-REGISTROS")
        if reviews:
            blocks.append("B256-REVISION-PROFESIONAL")

        status = "blocked" if blocked else "incomplete" if missing else "ready_with_review" if reviews else "ready"
        return {
            "product_id": "CO-TR-002", "version": self.VERSION, "blocked": blocked,
            "status": status, "missing_fields": missing, "findings": findings,
            "professional_reviews": reviews, "documents": list(dict.fromkeys(documents)),
            "blocks": list(dict.fromkeys(blocks)),
            "risk": "red" if blocked else "yellow" if reviews else "green",
        }

    def _normalize_v254_result(self, raw: dict[str, Any], document_answers: dict[str, Any]) -> dict[str, Any]:
        doc_map = {
            "DOC-TR2-PETITION-001": "traffic_record_request",
            "DOC-TR2-NOTICE-001": "traffic_notice_claim",
            "DOC-TR2-HEARING-001": "traffic_hearing_request",
            "DOC-TR2-REVOCATION-001": "traffic_revocation_request",
            "DOC-TR2-CORRECTION-001": "traffic_registry_correction",
            "DOC-TR2-REITERATION-001": "traffic_reiteration",
            "DOC-TR2-COERCIVE-001": "traffic_escalation_guide",
        }
        documents = [doc_map[item] for item in raw.get("documents", []) if item in doc_map]
        if "traffic_record_request" not in documents:
            documents.insert(0, "traffic_record_request")
        if "traceability" not in documents:
            documents.append("traceability")

        findings: list[dict[str, Any]] = []
        reviews: list[str] = []
        for item in raw.get("findings", []) or []:
            severity = item.get("severity") or item.get("risk") or "review"
            risk = "red" if severity == "blocker" else "yellow" if severity in {"review", "warning"} else str(severity)
            normalized = {"id": item.get("id"), "risk": risk, "message": item.get("message", "")}
            findings.append(normalized)
            if normalized["message"] and risk in {"red", "yellow"}:
                reviews.append(normalized["message"])

        missing = list(raw.get("missing_fields") or [])
        compact_required = [
            ("identity.full_name", "Nombre completo"),
            ("identity.document_number", "Documento de identidad"),
            ("identity.email", "Correo para notificaciones"),
            ("authority.name", "Autoridad de tránsito"),
            ("infraction.comparendo_number", "Número de comparendo"),
            ("infraction.plate", "Placa"),
            ("infraction.date", "Fecha de la infracción"),
            ("infraction.notice_status", "Estado de notificación"),
        ]
        existing_paths = {item.get("path") for item in missing if isinstance(item, dict)}
        for path, label in compact_required:
            if self._get(document_answers, path) in (None, "", []) and path not in existing_paths:
                missing.append({"path": path, "label": label, "source": "document_contract_v256"})

        blocked = bool(raw.get("blocked"))
        if blocked and "traffic_escalation_guide" not in documents:
            documents.append("traffic_escalation_guide")
        return {
            "product_id": "CO-TR-002",
            "version": self.VERSION,
            "blocked": blocked,
            "status": raw.get("status", "blocked" if blocked else "incomplete" if missing else "ready"),
            "missing_fields": missing,
            "findings": findings,
            "professional_reviews": list(dict.fromkeys(reviews)),
            "documents": list(dict.fromkeys(documents)),
            "blocks": list(dict.fromkeys(raw.get("blocks") or [])),
            "risk": "red" if blocked else "yellow" if findings else "green",
            "completion": raw.get("completion"),
            "explanations": raw.get("explanations", []),
        }

    def evaluate(self, answers: dict[str, Any]) -> dict[str, Any]:
        document_answers = self.to_document_answers(answers)
        if self._looks_like_v256_schema(answers):
            result = self._evaluate_simple_schema(document_answers)
        else:
            result = self._normalize_v254_result(dict(super().evaluate(answers)), document_answers)

        result["version"] = self.VERSION
        result.setdefault("documents", [])
        result.setdefault("blocks", [])
        result.setdefault("findings", [])
        result.setdefault("missing_fields", [])

        notice_status = str(self._get(document_answers, "infraction.notice_status") or "").strip().lower()
        properly_notified = notice_status in {
            "recibida", "notificada", "debidamente notificada", "properly_notified", "received",
        }
        if properly_notified:
            message = (
                "La persona reporta notificación recibida; el producto de no notificación no debe formular una afirmación contraria sin revisar el expediente."
            )
            self._append_finding(result, "COTR2-YEL-NOTIFIED", "yellow", message)
            result["documents"] = [doc for doc in result["documents"] if doc != "traffic_notice_claim"]
            for doc in ("traffic_record_request", "traffic_escalation_guide", "traceability"):
                if doc not in result["documents"]:
                    result["documents"].append(doc)

        proof_received = bool(self._get(document_answers, "notice.delivery_proof_received"))
        if notice_status in {"no recibida", "no_notificada", "not_received"} and proof_received:
            self._append_finding(
                result, "COTR2-YEL-NOTICE-CONTRADICTION", "yellow",
                "Existe contradicción entre el relato de no recepción y un soporte de entrega; debe aclararse antes de radicar.",
            )

        infraction_date = self._parse_date(self._get(document_answers, "infraction.date"))
        validation_date = self._parse_date(self._get(document_answers, "infraction.validation_date"))
        sent_date = self._parse_date(self._get(document_answers, "infraction.sent_date"))
        if infraction_date and validation_date:
            delta = self._business_days_between(infraction_date, validation_date)
            if delta > 10:
                self._append_finding(
                    result, "COTR2-YEL-VALIDATION-LATE", "yellow",
                    f"La validación informada ocurrió {delta} días hábiles después de la presunta infracción; debe contrastarse con el expediente y la regla aplicable.",
                )
            elif validation_date < infraction_date:
                self._append_finding(result, "COTR2-YEL-DATE-CONTRADICTION", "yellow", "La fecha de validación es anterior a la presunta infracción; el dato debe corregirse.")
        if validation_date and sent_date:
            delta = self._business_days_between(validation_date, sent_date)
            if delta > 3:
                self._append_finding(
                    result, "COTR2-YEL-SEND-LATE", "yellow",
                    f"El envío informado ocurrió {delta} días hábiles después de la validación; debe verificarse la trazabilidad de notificación.",
                )
            elif sent_date < validation_date:
                self._append_finding(result, "COTR2-YEL-DATE-CONTRADICTION", "yellow", "La fecha de envío es anterior a la validación; el dato debe corregirse.")

        paid = bool(self._get(document_answers, "payment.paid")) or str(self._get(document_answers, "procedure.stage") or "").lower() == "paid"
        agreement = bool(self._get(document_answers, "payment.agreement"))
        possible_fraud = bool(self._get(document_answers, "procedure.possible_fraud"))
        if paid:
            self._append_finding(result, "COTR2-RED-PAID", "red", "La obligación figura pagada; no se automatiza una solicitud de devolución ni se promete reintegro.")
        if agreement:
            self._append_finding(result, "COTR2-RED-AGREEMENT", "red", "Existe acuerdo de pago; deben analizarse reconocimiento, efectos y estado de cumplimiento.")
        if possible_fraud:
            self._append_finding(result, "COTR2-RED-FRAUD", "red", "Se reporta posible fraude o alteración documental; el flujo automático queda excluido.")
        if paid or agreement or possible_fraud:
            result["blocked"] = True
            safe_docs = ["traffic_record_request", "traffic_escalation_guide", "traceability"]
            result["documents"] = [doc for doc in safe_docs if doc in set(result["documents"]) or doc != "traffic_record_request"]
            for doc in safe_docs:
                if doc not in result["documents"]:
                    result["documents"].append(doc)

        reviews = list(result.get("professional_reviews") or result.get("review_requirements") or [])
        result["professional_reviews"] = list(dict.fromkeys(reviews))
        result["review_requirements"] = result["professional_reviews"]
        result["professional_review_required"] = bool(result["professional_reviews"] or result.get("blocked"))

        if result.get("blocked"):
            result["risk"] = "red"
            result["status"] = "blocked"
        elif result.get("missing_fields"):
            result["risk"] = "yellow"
            result["status"] = "incomplete"
        elif result["professional_reviews"]:
            result["risk"] = "yellow"
            result["status"] = "ready_with_review"
        else:
            result["risk"] = "green"
            result["status"] = "ready"

        blockers: list[str] = []
        if result.get("blocked"):
            blockers.append("El caso contiene una exclusión o riesgo rojo de automatización.")
        if result.get("missing_fields"):
            blockers.append("Faltan datos esenciales para generar documentos completos.")
        if not self.BASE_AVAILABLE:
            blockers.append("La versión debe instalarse sobre la base canónica v2.54 para habilitar publicación.")
        result["release_blockers"] = list(dict.fromkeys(blockers))
        result["release_blocked"] = bool(blockers)
        result["readiness"] = result.get("status")
        result["documents"] = list(dict.fromkeys(result.get("documents") or []))
        result["blocks"] = [str(block).replace("B255-", "B256-") for block in dict.fromkeys(result.get("blocks") or [])]
        result["decision_trace"] = [item.get("id") for item in result.get("findings", []) if item.get("id")]
        return result
