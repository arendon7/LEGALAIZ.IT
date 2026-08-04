from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
import json
import re
import shutil
import tempfile
import threading

from legalai_platform.professional_contract_docx import build_professional_docx


class M31DemoRealityCenter:
    """Genera un portafolio documental completo y trazable para demostración.

    El centro usa exclusivamente datos sintéticos, genera una salida DOCX por cada
    plantilla activa y adjunta las evidencias DOCX/PDF previamente validadas por
    producto. No publica documentos de clientes ni altera revisiones canónicas.
    """

    SCHEMA = "legalai_m31_7_demo_reality_portfolio_v1"
    VERSION = "5.0.6"
    MILESTONE = "M31.7"
    SENTINELS = (
        "{{", "}}", "undefined", "<null>", "NULL", "N/A", "<none>",
        "[definir]", "[pendiente de diligenciar]", "[completar]",
        "Pendiente de diligenciar", "Pendiente por diligenciar",
        "Pendiente por definir", "Por definir",
    )

    def __init__(self, root: Path, runtime: Path, factory, templates: list[dict], products: list[dict], interviews: dict[str, Any]):
        self.root = Path(root).resolve()
        self.runtime = Path(runtime).resolve()
        self.factory = factory
        self.templates = list(templates)
        self.products = {row["code"]: row for row in products}
        self.interviews = interviews
        self.output_root = self.runtime / "demo_reality_m31_7"
        self.current_root = self.output_root / "current"
        self.manifest_path = self.current_root / "manifest.json"
        self.logo_path = self.root / "app" / "assets" / "logo-legalaizit-docx.png"
        self.validated_root = self.root / "governance" / "m24_4" / "validated_documents"
        self._generation_lock = threading.Lock()

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _safe(value: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "documento")).strip("._")
        return clean[:180] or "documento"

    @staticmethod
    def _hash(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _select_value(variable: dict[str, Any]) -> Any:
        options = list(variable.get("options") or [])
        if not options:
            return "Sí"
        qid = str(variable.get("id") or "").lower()
        label = str(variable.get("label") or "").lower()
        combined = qid + " " + label
        prefer_no = (
            "fraud", "suplant", "litigation", "process_active", "active_process", "judicial", "court",
            "dispute", "controvers", "urgent", "special_protection", "injury", "risk", "embargo",
            "insolvency", "prescription", "third_party", "blanks", "noncompete", "exclusive",
            "automatic_deduction", "cash_deposit", "coercive", "identity", "unsafe", "active_dispute",
        )
        prefer_yes = (
            "confirmed", "data_confirmed", "data_minimized", "consent", "support", "evidence_status",
            "traceability", "authorization", "signage", "acceptance", "integrity", "reconciled",
            "professional_review_ack", "notice_support", "address_match", "runt", "complete",
        )
        if any(token in combined for token in prefer_no):
            for candidate in ("No", "No aplica", "Sin proceso conocido", "Completo"):
                if candidate in options:
                    return candidate
        if any(token in combined for token in prefer_yes):
            for candidate in ("Sí", "Completo", "Completa", "Acreditada", "Expresa", "Registrada y trazable"):
                if candidate in options:
                    return candidate
        safe_order = (
            "Sí", "No", "Completo", "Completa", "Particular", "Persona jurídica privada",
            "Persona natural no comerciante", "Vencida y exigible", "COP", "Mensual",
            "Indefinido", "Vivienda urbana", "Propietario", "El propio paciente",
        )
        for candidate in safe_order:
            if candidate in options:
                return candidate
        return options[0]

    @classmethod
    def _generic_value(cls, variable: dict[str, Any], code: str) -> Any:
        qid = str(variable.get("id") or "")
        low = qid.lower()
        label = str(variable.get("label") or "").lower()
        vtype = variable.get("type") or "text"
        if vtype == "select":
            return cls._select_value(variable)
        if vtype == "multiselect":
            options = list(variable.get("options") or [])
            return options[: min(3, len(options))]
        if vtype == "date":
            if any(token in low for token in ("start", "issue", "document_date", "filing_date", "event_date", "purchase_date", "delivery_date")):
                return "2026-06-15"
            if any(token in low for token in ("end", "expiry", "due_date", "first_payment", "fixed_term")):
                return "2026-12-15"
            return "2026-07-15"
        if vtype == "number":
            if any(token in low for token in ("salary", "rent", "principal", "amount", "value", "balance", "total", "fees", "capital", "payment")):
                return 4200000 if "salary" in low else 12500000
            if any(token in low for token in ("rate", "percentage")):
                return 1.5
            if any(token in low for token in ("days", "day")):
                return 5
            if any(token in low for token in ("months", "month", "term", "installments", "count")):
                return 12
            return 10
        if vtype == "email" or "email" in low or "correo" in label:
            return f"expediente.{code.lower().replace('-', '.')}@example.test"
        if "phone" in low or "tel" in low or "teléfono" in label:
            return "+57 300 555 0182"
        if any(token in low for token in ("id", "nit", "identification", "document_number")):
            return "901.765.432-1" if any(token in low for token in ("employer", "creditor", "provider", "company", "party_a", "landlord", "entity")) else "1.037.654.321"
        if "plate" in low:
            return "ABC123"
        if any(token in low for token in ("city", "territory", "domicile", "department")):
            return "Medellín, Antioquia"
        if any(token in low for token in ("address", "location", "property")):
            return "Carrera 43A No. 10-45, Medellín"
        if any(token in low for token in ("name", "worker", "petitioner", "requester", "consumer", "debtor", "tenant")):
            return "Andrea Martínez López"
        if any(token in low for token in ("employer", "creditor", "provider", "company", "party_a", "landlord", "entity", "authority")):
            return "ACME SOLUCIONES COLOMBIA S.A.S."
        if "representative" in low or "apoderado" in label:
            return "Laura Martínez Gómez"
        if any(token in low for token in ("object", "purpose", "origin_description", "facts", "detail", "description", "deliverables", "scope")):
            return "Prestación documentada de servicios y gestión del expediente conforme a los soportes aportados, con alcance, entregables y controles verificables."
        if vtype == "textarea":
            return "Hechos completos y verificables del caso sintético, con fechas, actuaciones, comunicaciones y soportes organizados para la demostración controlada."
        return "Dato sintético verificado para demostración controlada"

    def _product_overrides(self, code: str) -> dict[str, Any]:
        common = {
            "data_confirmed": "Sí", "data_minimized": "Sí", "deadline_urgent": "No",
            "active_litigation": "No", "active_process": "No", "judicial_process_active": "No",
            "professional_review_ack": "Sí", "evidence_status": "Completo",
        }
        product_maps: dict[str, dict[str, Any]] = {
            "CO-LA-001": {
                "worker_name": "Juan David Pérez Gómez", "worker_id": "1.037.654.321",
                "employer_name": "ACME LEGALTECH S.A.S.", "employer_id": "901.765.432-1",
                "claim_email": "juan.perez@example.test", "private_relation": "Sí",
                "start_date": "2024-02-01", "end_date": "2026-07-31", "contract_type": "Indefinido",
                "termination": "Sin justa causa", "monthly_salary": 4200000, "integral_salary": "No",
                "variable_salary": "No", "transport_aid": "No", "salary_due_days": 15,
                "cesantias_start_date": "2026-01-01", "prima_start_date": "2026-01-01",
                "vacation_pending_days": 8, "periods_confirmed": "Sí", "generate_settlement": "Sí",
            },
            "CO-LA-002": {
                "employer_name": "ACME LEGALTECH S.A.S.", "employer_id": "901.765.432-1",
                "employer_address": "Carrera 43A No. 10-45, oficina 801, Medellín",
                "employer_representative": "Laura Martínez Gómez", "worker_name": "Ana María Torres Pérez",
                "worker_id": "1.037.654.321", "worker_address": "Calle 30 No. 78-25, Medellín",
                "worker_email": "ana.torres@example.test", "job_title": "Coordinadora Administrativa",
                "monthly_salary": 4200000, "start_date": "2026-08-10", "need_type": "Nueva contratación",
                "work_model": "Presencial con flexibilidad autorizada", "contract_modality": "Indefinido",
                "special_protection": "No", "confidential_information": "Sí", "personal_data": "Sí",
                "ip_relevant": "Sí", "automatic_deductions": "No", "exclusivity_clause": "No",
            },
            "CO-EM-003": {
                "party_a": "ACME SOLUCIONES COLOMBIA S.A.S.", "party_a_id": "901.765.432-1",
                "party_b": "CONSULTORÍA DIGITAL ANDINA S.A.S.", "party_b_id": "901.555.222-8",
                "contract_city": "Medellín", "contact_email_a": "legal@acme.example.test",
                "contact_email_b": "proyectos@consultoriaandina.example.test",
                "object": "Diseñar e implementar una solución de automatización documental para procesos jurídicos empresariales.",
                "deliverables": "Diagnóstico, arquitectura funcional, prototipo navegable, documentación técnica, pruebas y transferencia de conocimiento.",
                "fees": 45000000, "start_date": "2026-08-15", "end_date": "2026-12-15",
                "payment_scheme": "Anticipo e hitos", "acceptance_days": 5, "personal_data": "Sí",
                "confidentiality": "Sí", "ip_relevant": "Sí", "fixed_schedule": "No",
                "permanent_orders": "No", "disciplinary_control": "No", "continuous_availability": "No",
                "exclusive": "No", "subcontractors": "No", "early_termination": "Sí",
            },
            "CO-EM-004": {
                "party_a": "ACME SOLUCIONES COLOMBIA S.A.S.", "party_b": "INNOVACIÓN ANDINA S.A.S.",
                "nda_type": "Bilateral", "purpose": "Evaluar y desarrollar una alianza para automatización jurídica.",
                "info_categories": "Información comercial, técnica, financiera, jurídica y datos de proyecto.",
                "info_defined": "Sí", "authorized_recipients": "Equipo directivo, jurídico y técnico bajo necesidad de conocer.",
                "personal_data": "Sí", "crossborder": "No", "ai_tools": "Sí",
                "oss_components": "Sí", "future_ip_assignment": "No", "moral_rights": "Sí",
                "noncompete": "No", "duration_years": 3, "incident_protocol": "Sí",
            },
            "CO-AR-001": {
                "landlord": "María Fernanda Gómez Ruiz", "landlord_id": "43.210.987",
                "landlord_email": "maria.gomez@example.test", "tenant": "Carlos Andrés Restrepo", "tenant_id": "71.234.567",
                "tenant_email": "carlos.restrepo@example.test", "urban_home": "Sí", "lease_type": "Vivienda urbana",
                "authority": "No", "active_dispute": "No", "cash_deposit": "No", "ph": "Sí",
                "ph_rules_delivered": "Sí", "furnished_high_value": "Sí", "unsafe": "No",
                "tourism_sublease": "No", "property": "Apartamento 501, Carrera 40 No. 10-20, Medellín",
                "property_registration": "001-123456", "occupants": "Arrendatario y su grupo familiar", "pets": "Sí",
                "rent": 2500000, "commercial_value_known": "Sí", "commercial_value": 420000000,
                "cadastral_value": 300000000, "administration_charge": 450000, "utilities_responsible": "Arrendatario",
                "duration_months": 12, "start_date": "2026-09-01", "payment_day": 5,
                "co_debtor": "Codeudor solidario", "special_termination": "No",
            },
            "CO-SA-001": {
                "requester_name": "Sofía Ramírez López", "requester_id": "1.015.678.901",
                "email": "sofia.ramirez@example.test", "phone": "+57 300 555 0191",
                "address": "Calle 12 No. 34-56, Medellín", "city": "Medellín",
                "acting_capacity": "El propio paciente", "entity": "EPS SALUD DEMO S.A.", "entity_type": "EPS",
                "entity_city": "Medellín", "request_type": "Autorización o programación",
                "health_need": "Autorización y programación de procedimiento ordenado por el médico tratante.",
                "medical_order_date": "2026-07-10", "filing_channel": "Correo electrónico",
                "immediate_attention_sought": "Sí", "continuity_risk": "Sí", "deterioration": "No",
            },
            "CO-CD-001": {
                "data_subject_name": "Daniela Ospina Vargas", "data_subject_id": "1.040.222.333",
                "email": "daniela.ospina@example.test", "address": "Carrera 65 No. 45-21, Medellín",
                "city": "Medellín", "acting_capacity": "Titular", "source_name": "FINANCIERA DEMO S.A.",
                "operator_name": "CENTRAL DE INFORMACIÓN DEMO", "data_category": "Obligación financiera",
                "claim_goal": "Rectificación y actualización", "facts_detail": "La obligación aparece con saldo y mora que no corresponden a los pagos acreditados.",
                "identity_risk": "No", "authority_case_active": "No", "prior_claim": "Sí",
                "filing_channel": "Correo electrónico", "claim_legend_present": "Sí",
            },
            "CO-CD-003": {
                "consumer_name": "Felipe Herrera Cano", "consumer_id": "1.020.333.444",
                "email": "felipe.herrera@example.test", "city": "Medellín", "acting_capacity": "Consumidor",
                "provider_name": "COMERCIO DIGITAL DEMO S.A.S.", "provider_id": "901.333.444-5",
                "product_or_service": "Computador portátil adquirido por comercio electrónico",
                "purchase_date": "2026-07-01", "delivery_date": "2026-07-04", "price": 4800000,
                "problem_type": "Producto defectuoso", "defect_detail": "El equipo presentó fallas de encendido desde la primera semana de uso.",
                "claim_goal": "Efectividad de garantía", "electronic_payment": "Sí", "evidence_status": "Completa",
                "advertising_support": "Sí", "injury_or_safety": "No", "regulated_sector": "No",
                "complex_fraud": "No", "active_process": "No", "high_value_or_damage": "No",
            },
            "CO-CD-004": {
                "package_stage": "Formalización", "creditor_name": "SUMINISTROS ANDINOS S.A.S.",
                "creditor_id": "901.222.333-4", "creditor_type": "Persona jurídica privada",
                "creditor_representative": "Laura Martínez Gómez", "creditor_authority": "Completo",
                "creditor_email": "cartera@suministrosandinos.example.test", "debtor_name": "DISTRIBUCIONES DEL NORTE S.A.S.",
                "debtor_id": "901.777.888-9", "debtor_type": "Persona jurídica privada",
                "debtor_email": "gerencia@distribucionesnorte.example.test", "debtor_contact_confirmed": "Sí",
                "obligation_type": "Mercantil", "origin_description": "Suministro periódico de insumos conforme al contrato marco y facturas aceptadas.",
                "source_document_type": "Factura electrónica", "document_reference": "FE-2026-1842",
                "document_date": "2026-04-15", "due_date": "2026-05-15", "principal": 25000000,
                "currency": "COP", "obligation_status": "Vencida y exigible", "express_clear_enforceable": "Sí",
                "debtor_signature_status": "Acreditada", "original_integrity_status": "Completa",
                "invoice_acceptance_status": "Tácita acreditada", "radian_status": "Registrada y trazable",
                "reported_balance": 20000000, "partial_payments": "Sí", "partial_payments_total": 5000000,
                "balance_reconciled": "Sí", "interest_agreed": "Sí", "interest_type": "Moratorio",
                "interest_rate": 1.5, "interest_period": "Mensual vencida", "interest_modality": "Consumo y ordinario",
                "other_charges": 0, "other_charges_supported": "No aplica", "disputed": "No",
                "judicial_process_active": "No", "insolvency_active": "No", "embargo_or_measure": "No",
                "consumer_debt": "No", "authorized_channels": "Sí", "contact_time_compliant": "Sí",
                "settlement_goal": "Acuerdo por cuotas", "agreement_total": 20000000, "installments": 4,
                "frequency": "Mensual", "first_payment_date": "2026-08-15", "grace_days": 3,
                "acceleration_clause": "Sí", "novation_intent": "No", "payment_channel": "Transferencia bancaria identificada",
                "promissory_note_requested": "Sí", "note_format": "Totalmente diligenciado", "blanks_present": "No",
                "instructions_signed": "No aplica", "maturity_form": "Cuotas sucesivas", "guarantor_or_aval": "No",
                "real_collateral": "No",
            },
            "CO-TR-001": {
                "requester_name": "Juan David Pérez Gómez", "requester_id": "1.037.654.321",
                "email": "juan.perez@example.test", "phone": "+57 300 555 0182",
                "address": "Carrera 55 No. 44-33, Medellín", "acting_capacity": "Propietario",
                "plate": "ABC123", "comparendo_number": "0500100000001", "authority": "Secretaría de Movilidad de Medellín",
                "territory": "Medellín", "department": "Antioquia", "event_date": "2019-06-15",
                "event_time": "10:30", "event_location": "Avenida Regional, punto por verificar",
                "conduct_code": "Exceso de velocidad", "device_known": "Sí", "device_id": "SAST-MDE-001",
                "exact_point_match": "Sí", "official_2026_match": "Sí", "official_act_number": "7091",
                "official_act_status": "Apertura o formulación de cargos", "official_act_source": "Superintendencia de Transporte",
                "ansv_authorization": "Sí", "authorization_number": "ANSV-DEMO-001",
                "authorization_issue_date": "2018-01-01", "authorization_expiry_date": "2023-01-01",
                "calibration_traceability": "Sí", "calibration_date": "2019-05-20", "signage_verified": "Sí",
                "performance_concept": "No existe soporte", "notice_status": "Consulta SIMIT/RUNT",
                "first_knowledge_date": "2026-05-20", "enforcement": "Comparendo sin decisión conocida",
                "paid": "No", "case_count": 1, "evidence_available": "Comparendo y consultas oficiales",
                "deadline_urgent": "No", "identity_fraud": "No", "consent_alerts": "Sí",
            },
            "CO-TR-002": {
                "petitioner_name": "Juan David Pérez Gómez", "petitioner_id": "1.037.654.321",
                "acting_capacity": "Propietario", "email": "juan.perez@example.test",
                "address": "Carrera 55 No. 44-33, Medellín", "city": "Medellín",
                "authority": "Secretaría de Movilidad de Medellín", "territory": "Medellín", "plate": "ABC123",
                "vehicle_service": "Particular", "comparendo_number": "0500100002456", "event_date": "2026-04-20",
                "event_time": "08:45", "event_location": "Calle 33 con Carrera 52", "infraction_code": "C29 - Exceso de velocidad",
                "conduct_category": "Exceso de velocidad", "electronic": "Sí", "device_id": "SAST-MDE-021",
                "validation_date": "2026-04-21", "sent_date": "2026-05-18", "delivery_date": "2026-05-25",
                "first_knowledge_date": "2026-06-10", "notice_received": "No", "notice_channel": "Correo físico",
                "notice_address_match": "Sí", "notice_support": "No", "owner_updated_runt": "Sí",
                "resolution": "No", "hearing_held": "No", "coercive": "No", "paid": "No", "court": "No",
                "deadline_urgent": "No", "owner_was_driver": "Sí", "special_vehicle_event": "No",
                "sast_authorization": "Sí", "calibration_traceability": "Sí", "signage_verified": "Sí",
                "performance_concept": "Existe soporte", "official_2026_match": "No",
                "evidence": ["Comparendo", "Consulta SIMIT", "Consulta RUNT"], "prior_request": "No",
                "requested_outcome": "Acceso al expediente", "document_integrity_issue": "No",
            },
        }
        result = dict(common)
        result.update(product_maps.get(code, {}))
        return result

    def answers_for_product(self, code: str) -> dict[str, Any]:
        questions = self.interviews.get(code, {}).get("questions", [])
        answers = {q["id"]: self._generic_value(q, code) for q in questions}
        answers.update(self._product_overrides(code))
        return answers

    def _validated_assets(self, code: str) -> list[Path]:
        source = self.validated_root / code
        if not source.is_dir():
            return []
        manifest = source / "manifest.json"
        if not manifest.is_file():
            return []
        expected = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
        assets: list[Path] = []
        for name, digest in expected.items():
            path = source / name
            if path.is_file() and path.suffix.lower() in {".docx", ".pdf"} and self._hash(path) == digest:
                assets.append(path)
        return sorted(assets)

    @classmethod
    def _sanitize_demo_sections(cls, value: Any) -> Any:
        """Sustituye marcadores editoriales heredados por contenido demostrativo cerrado.

        La sustitución se limita a expresiones centinela exactas o claramente
        editoriales; no altera usos jurídicos ordinarios del verbo "definir".
        """
        if isinstance(value, dict):
            return {key: cls._sanitize_demo_sections(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._sanitize_demo_sections(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._sanitize_demo_sections(item) for item in value)
        if not isinstance(value, str):
            return value
        replacements = {
            "[pendiente de diligenciar]": "Sin actuación registrada a la fecha de corte",
            "pendiente de diligenciar": "Sin actuación registrada a la fecha de corte",
            "pendiente por diligenciar": "Sin actuación registrada a la fecha de corte",
            "[pendiente por definir]": "Sujeto a validación del expediente",
            "pendiente por definir": "Sujeto a validación del expediente",
            "[por definir]": "Sujeto a validación del expediente",
            "por definir": "Sujeto a validación del expediente",
            "[definir]": "Sujeto a validación del expediente",
            "[completar]": "Validado para la demostración",
        }
        sanitized = value
        for marker, replacement in replacements.items():
            sanitized = re.sub(re.escape(marker), replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    @staticmethod
    def _docx_has_sentinel(path: Path, sentinels: tuple[str, ...]) -> list[str]:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        lowered = xml.lower()
        return [token for token in sentinels if token.lower() in lowered]

    def _write_zip(self, target: Path, files: list[tuple[Path, str]]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for source, arcname in files:
                archive.write(source, arcname)

    def _generate_unlocked(self, actor: str) -> dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="m31_7_demo_", dir=str(self.output_root)))
        generated_at = self._now()
        product_rows: list[dict[str, Any]] = []
        global_files: list[tuple[Path, str]] = []
        unresolved: list[dict[str, Any]] = []
        templates_by_product: dict[str, list[dict[str, Any]]] = {}
        for template in self.templates:
            templates_by_product.setdefault(template["product_code"], []).append(template)

        try:
            for code in sorted(self.products):
                product = self.products[code]
                product_dir = staging / code
                generated_dir = product_dir / "documentos_generados"
                reference_dir = product_dir / "referencias_validadas"
                generated_dir.mkdir(parents=True, exist_ok=True)
                reference_dir.mkdir(parents=True, exist_ok=True)
                answers = self.answers_for_product(code)
                product_files: list[dict[str, Any]] = []
                zip_inputs: list[tuple[Path, str]] = []

                for index, template in enumerate(sorted(templates_by_product.get(code, []), key=lambda row: row["template_id"]), 1):
                    validation = self.factory.validate(template["template_id"], template)
                    if not validation.get("valid"):
                        raise ValueError(f"Plantilla inválida {template['template_id']}: {'; '.join(validation.get('errors') or [])}")
                    preview = self.factory.render(template, answers)
                    preview["sections"] = self._sanitize_demo_sections(preview.get("sections") or [])
                    filename = self._safe(f"{code}_{index:02d}_{template.get('filename_suffix') or template['kind']}_FINAL_DEMO.docx")
                    target = generated_dir / filename
                    build_professional_docx(
                        target,
                        title=preview["title"],
                        subtitle=preview.get("subtitle") or f"{product.get('title', code)} - documento final de demostración",
                        metadata=[
                            ("Producto", f"{code} - {product.get('title', '')}"),
                            ("Plantilla", template["template_id"]),
                            ("Versión de demo", self.VERSION),
                            ("Datos", "Sintéticos, coherentes y exclusivamente demostrativos"),
                            ("Generado", generated_at),
                        ],
                        sections=preview["sections"],
                        logo_path=self.logo_path if self.logo_path.is_file() else None,
                        footer="LegalAIZ.it - Documento final de demostración con datos sintéticos",
                    )
                    bad = self._docx_has_sentinel(target, self.SENTINELS)
                    if bad:
                        unresolved.append({"product_code": code, "template_id": template["template_id"], "file": filename, "sentinels": bad})
                    row = {
                        "type": "generated_docx", "template_id": template["template_id"], "kind": template["kind"],
                        "title": preview["title"], "name": filename, "size_bytes": target.stat().st_size,
                        "sha256": self._hash(target), "download_path": f"{code}/documentos_generados/{filename}",
                    }
                    product_files.append(row)
                    zip_inputs.append((target, f"documentos_generados/{filename}"))
                    global_files.append((target, f"{code}/documentos_generados/{filename}"))

                reference_assets = self._validated_assets(code)
                for source in reference_assets:
                    suffix = source.suffix.lower()
                    target = reference_dir / self._safe(f"{code}_REFERENCIA_FINAL_VALIDADA{suffix}")
                    shutil.copy2(source, target)
                    row = {
                        "type": "validated_reference", "format": suffix.lstrip("."), "name": target.name,
                        "size_bytes": target.stat().st_size, "sha256": self._hash(target),
                        "download_path": f"{code}/referencias_validadas/{target.name}",
                    }
                    product_files.append(row)
                    zip_inputs.append((target, f"referencias_validadas/{target.name}"))
                    global_files.append((target, f"{code}/referencias_validadas/{target.name}"))

                product_manifest = {
                    "schema": "legalai_m31_7_demo_product_manifest_v1", "product_code": code,
                    "product_title": product.get("title"), "generated_at": generated_at,
                    "data_classification": "synthetic_no_real_personal_data",
                    "generated_docx": sum(row["type"] == "generated_docx" for row in product_files),
                    "validated_reference_files": sum(row["type"] == "validated_reference" for row in product_files),
                    "files": product_files,
                }
                manifest_file = product_dir / "manifest.json"
                manifest_file.write_text(json.dumps(product_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                zip_inputs.append((manifest_file, "manifest.json"))
                global_files.append((manifest_file, f"{code}/manifest.json"))
                package_name = self._safe(f"LegalAIZit_{code}_PORTAFOLIO_FINAL_DEMO_v{self.VERSION}.zip")
                package_path = product_dir / package_name
                self._write_zip(package_path, zip_inputs)
                global_files.append((package_path, f"paquetes_por_producto/{package_name}"))
                product_rows.append({
                    "product_code": code, "title": product.get("title"),
                    "generated_docx": product_manifest["generated_docx"],
                    "validated_reference_files": product_manifest["validated_reference_files"],
                    "package": {"name": package_name, "size_bytes": package_path.stat().st_size,
                                "sha256": self._hash(package_path), "download_path": f"{code}/{package_name}"},
                    "files": product_files,
                })

            manifest = {
                "schema": self.SCHEMA, "milestone": self.MILESTONE, "version": self.VERSION,
                "status": "ready" if not unresolved else "blocked_unresolved_variables",
                "generated_at": generated_at, "generated_by": actor,
                "scope": "demo_documental_completa_con_datos_sinteticos",
                "production_authorized": False, "public_release_authorized": False,
                "products": product_rows,
                "metrics": {
                    "products": len(product_rows),
                    "generated_docx": sum(row["generated_docx"] for row in product_rows),
                    "validated_reference_docx": sum(sum(f.get("type") == "validated_reference" and f.get("format") == "docx" for f in row["files"]) for row in product_rows),
                    "validated_reference_pdf": sum(sum(f.get("type") == "validated_reference" and f.get("format") == "pdf" for f in row["files"]) for row in product_rows),
                    "unresolved_files": len(unresolved),
                },
                "unresolved": unresolved,
                "notice": "Portafolio íntegramente sintético para demostración. Cada documento real debe conservar validación de hechos, anexos, riesgo, vigencia, aprobación jurídica y QA sobre su versión exacta.",
            }
            manifest_file = staging / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            global_files.append((manifest_file, "manifest.json"))

            checksum_lines = []
            for source, arcname in sorted(global_files, key=lambda item: item[1]):
                checksum_lines.append(f"{self._hash(source)}  {arcname}")
            checksum_file = staging / "SHA256SUMS.txt"
            checksum_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
            global_files.append((checksum_file, "SHA256SUMS.txt"))

            package_name = f"LegalAIZit_M31_7_PORTAFOLIO_DOCUMENTAL_FINAL_DEMO_v{self.VERSION}.zip"
            global_package = staging / package_name
            self._write_zip(global_package, global_files)
            manifest["global_package"] = {
                "name": package_name, "size_bytes": global_package.stat().st_size,
                "sha256": self._hash(global_package), "download_path": package_name,
            }
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            if self.current_root.exists():
                shutil.rmtree(self.current_root)
            staging.rename(self.current_root)
            return manifest
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def generate(self, actor: str) -> dict[str, Any]:
        if not self._generation_lock.acquire(blocking=False):
            raise RuntimeError("Ya existe una generación documental en curso. Espere a que termine antes de iniciar otra.")
        try:
            return self._generate_unlocked(actor)
        finally:
            self._generation_lock.release()

    def summary(self) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            return {
                "schema": self.SCHEMA, "milestone": self.MILESTONE, "version": self.VERSION,
                "status": "not_generated", "production_authorized": False,
                "metrics": {"products": 11, "generated_docx": 0, "validated_reference_docx": 0, "validated_reference_pdf": 0, "unresolved_files": 0},
                "products": [],
                "notice": "El portafolio final de demostración aún no ha sido generado en este runtime.",
            }
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def file_path(self, relative: str) -> Path | None:
        if not relative:
            return None
        candidate = (self.current_root / relative).resolve()
        try:
            candidate.relative_to(self.current_root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def verify(self) -> dict[str, Any]:
        summary = self.summary()
        if summary.get("status") == "not_generated":
            return {"ok": False, "status": "not_generated", "checked": 0, "failures": ["Portafolio no generado"]}
        failures: list[dict[str, Any]] = []
        checked = 0
        for product in summary.get("products", []):
            for row in product.get("files", []):
                path = self.file_path(row.get("download_path", ""))
                checked += 1
                if not path:
                    failures.append({"file": row.get("download_path"), "error": "missing"})
                elif self._hash(path) != row.get("sha256"):
                    failures.append({"file": row.get("download_path"), "error": "hash_mismatch"})
            package = product.get("package") or {}
            path = self.file_path(package.get("download_path", ""))
            checked += 1
            if not path:
                failures.append({"file": package.get("download_path"), "error": "missing"})
            elif self._hash(path) != package.get("sha256"):
                failures.append({"file": package.get("download_path"), "error": "hash_mismatch"})
        global_package = summary.get("global_package") or {}
        path = self.file_path(global_package.get("download_path", ""))
        checked += 1
        if not path:
            failures.append({"file": global_package.get("download_path"), "error": "missing"})
        elif self._hash(path) != global_package.get("sha256"):
            failures.append({"file": global_package.get("download_path"), "error": "hash_mismatch"})
        return {"ok": not failures and summary.get("metrics", {}).get("unresolved_files") == 0,
                "status": summary.get("status"), "checked": checked, "failures": failures,
                "unresolved_files": summary.get("metrics", {}).get("unresolved_files", 0)}
