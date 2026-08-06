#!/usr/bin/env python3
from __future__ import annotations

"""Punto de entrada compatible para la generación integral M32.3.

Preserva las fábricas especializadas históricas, normaliza sus diferencias de
interfaz y crea expedientes sintéticos coherentes para las seis fábricas
transversales. Ningún dato de muestra se presenta como expediente o resultado real.
"""

from pathlib import Path
import shutil

from scripts import generate_m32_3_full_portfolio as implementation


class FactoryCompatibleEvaluator:
    def __init__(self, documents: list[str], blocks: list[str] | None = None):
        self.document_ids = [str(document_id) for document_id in documents]
        self.documents = [
            {"id": document_id, "name": document_id.replace("-", " ")}
            for document_id in self.document_ids
        ]
        self.blocks = list(blocks or [])

    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": list(self.document_ids),
            "readiness": "ready_for_human_review",
            "status": "ready_for_human_review",
            "professional_review_required": True,
            "professional_reviews": ["Revisión jurídica sustantiva", "QA visual humano"],
            "review_requirements": ["Revisión jurídica sustantiva", "QA visual humano"],
            "findings": [],
            "blockers": [],
            "warnings": [],
            "blocks": list(self.blocks),
        }


def _approval_status(value, default: str = "pending") -> str:
    """Normaliza objetos y cadenas heredadas sin convertir ausencia en aprobación."""
    if isinstance(value, dict):
        value = value.get("status", default)
    if value in (None, ""):
        return default
    return str(value).strip().casefold()


def _released_status(manifest: dict) -> bool:
    """Considera liberado cualquier estado explícito distinto de falso o pendiente."""
    value = manifest.get("released", False)
    if isinstance(value, bool):
        return value
    if value in (None, "", 0):
        return False
    return str(value).strip().casefold() not in {"false", "no", "pending", "draft", "not_released"}


def _resolve_generated_document(factory, manifest: dict, document: dict) -> Path:
    generation_root = Path(factory.output_dir) / str(manifest["generation_id"])
    filename = str(document["filename"])
    candidates: list[Path] = []

    for key in ("path", "relative_path", "content_location"):
        value = document.get(key)
        if value:
            candidate = Path(str(value))
            candidates.append(candidate if candidate.is_absolute() else generation_root / candidate)

    folder = manifest.get("document_folder")
    if folder:
        candidates.append(generation_root / str(folder) / filename)

    candidates.extend(
        [
            generation_root / "documents" / "revision-0001" / filename,
            generation_root / "documents" / filename,
            generation_root / filename,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    matches = sorted(path for path in generation_root.rglob(filename) if path.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError(
            f"No se encontró {filename} dentro de la generación inmutable {generation_root}."
        )
    raise RuntimeError(
        f"La generación {generation_root} contiene múltiples salidas ambiguas para {filename}: "
        + ", ".join(str(path.relative_to(generation_root)) for path in matches)
    )


def _copy_primary_compatible(factory, answers: dict, product_code: str, output: Path) -> dict:
    manifest = factory.generate(answers, actor={"id": "m32-3-ci", "role": "qa"})
    primary_id = implementation.PRIMARY_DOCUMENT_IDS[product_code]
    document = next(
        (item for item in manifest.get("documents", []) if item.get("id") == primary_id),
        None,
    )
    if not document:
        available = ", ".join(str(item.get("id")) for item in manifest.get("documents", []))
        raise RuntimeError(
            f"La fábrica {product_code} no produjo {primary_id}. Disponibles: {available or 'ninguno'}."
        )
    source = _resolve_generated_document(factory, manifest, document)
    destination = output / f"{product_code}_{Path(document['filename']).stem}_M32_3.docx"
    shutil.copy2(source, destination)
    return {
        "product_code": product_code,
        "factory": type(factory).__name__,
        "factory_version": str(getattr(factory, "VERSION", "")),
        "document_id": primary_id,
        "source_filename": document["filename"],
        "sample_name": destination.name,
        "generation_id": manifest["generation_id"],
        "factory_legal_approval": _approval_status(manifest.get("legal_approval")),
        "factory_qa_approval": _approval_status(manifest.get("qa_approval")),
        "factory_released": _released_status(manifest),
    }


_TRANSVERSAL_OVERRIDES = {
    "CO-TR-001": {
        "requester_name": "Juan Pérez Demo",
        "requester_id": "100000001",
        "acting_capacity": "Propietario",
        "authority": "Secretaría de Movilidad de Medellín",
        "territory": "Medellín",
        "department": "Antioquia",
        "plate": "ABC123",
        "comparendo_number": "05001000000012345678",
        "event_date": "2026-06-15",
        "official_2026_match": "No",
        "official_act_number": "No identificado en la muestra",
        "official_act_status": "Sin actuación individual cotejada",
        "official_act_source": "Consulta oficial pendiente",
    },
    "CO-TR-002": {
        "requester_name": "Juan Pérez Demo",
        "requester_id": "100000001",
        "acting_capacity": "Propietario",
        "authority": "Secretaría de Movilidad de Medellín",
        "territory": "Medellín",
        "plate": "ABC123",
        "comparendo_number": "05001000000012345678",
        "event_date": "2026-06-15",
        "validation_date": "2026-06-16",
        "dispatch_date": "2026-06-18",
        "delivery_date": "No acreditada",
        "effective_knowledge_date": "2026-07-10",
    },
    "CO-SA-001": {
        "entity_name": "EPS Demo S.A.",
        "entity_type": "EPS",
        "city": "Medellín, Antioquia",
        "subject": "Autorización y continuidad de tratamiento",
        "requester_name": "Juan Pérez Demo",
        "requester_id": "100000001",
        "requester_capacity": "Paciente",
        "patient_name": "Juan Pérez Demo",
        "patient_id": "100000001",
        "patient_situation": "Adulto con capacidad",
        "relationship": "El mismo paciente",
        "medical_support_available": "Sí",
        "order_date": "2026-07-20",
        "treatment_continuity": "Sí",
        "priority_condition": "Riesgo de interrupción del tratamiento",
        "secure_delivery": "Sí",
        "third_party_authorization": "No aplica",
        "data_minimized": "Sí",
    },
    "CO-CD-001": {
        "claim_goal": "Actualizar el estado de la obligación a pagada y acreditar la novedad ante los operadores y usuarios autorizados.",
        "issue_type": "Dato desactualizado después del pago total",
        "obligation_status": "Pagada",
        "mora_start_date": "2025-03-01",
        "payment_or_extinction_date": "2026-04-30",
        "report_date": "2025-04-15",
        "obligation_amount": "1000000",
        "prior_communication_received": "Sí",
        "prior_communication_date": "2025-03-10",
        "prior_communication_evidence": "Sí",
        "small_obligation_two_notices": "Sí",
        "identity_theft": "No",
    },
    "CO-CD-003": {
        "consumer_name": "Juan Pérez Demo",
        "consumer_id": "100000001",
        "consumer_capacity": "Consumidor directo",
        "provider_name": "Proveedor Demo S.A.S.",
        "order_reference": "PED-DEMO-2026-001",
        "city": "Medellín, Antioquia",
        "good_or_service": "Electrodoméstico adquirido para uso doméstico",
        "transaction_value": "1000000",
        "channel": "Presencial",
        "problem_type": "Producto defectuoso",
        "defect_or_breach": "El equipo dejó de funcionar dentro del período de garantía y fue presentado al proveedor con sus soportes.",
        "desired_outcome": "Reparación gratuita",
        "purchase_date": "2026-05-10",
        "delivery_date": "2026-05-12",
        "direct_claim_date": "2026-07-01",
    },
    "CO-CD-004": {
        "creditor_name": "Empresa Acreedora Demo S.A.S.",
        "creditor_id": "901234567-8",
        "creditor_representative": "María Fernanda Gómez Ruiz",
        "debtor_name": "Persona Deudora Demo",
        "debtor_id": "100000001",
        "document_reference": "CONTRATO-DEMO-2025-001",
        "creditor_authority": "Representación acreditada en certificado de existencia y representación legal",
        "obligation_type": "Civil",
        "source_document_type": "Contrato escrito",
        "document_date": "2025-01-10",
        "origin_description": "Préstamo documentado con desembolso y calendario de pago verificables.",
        "obligation_status": "Vencida y exigible",
        "due_date": "2026-05-31",
        "express_clear_enforceable": "Sí, sujeto a cotejo del original y sus anexos",
        "debtor_signature_status": "Firma atribuida al deudor; verificación pendiente",
        "original_integrity_status": "Original electrónico con hash disponible",
        "invoice_acceptance_status": "No aplica",
        "radian_status": "No aplica",
        "assignment_factoring": "No",
        "disputed": "No",
        "setoff_claimed": "No",
        "prescription_concern": "No identificada en la muestra",
        "judicial_process_active": "No",
        "insolvency_active": "No",
        "embargo_or_measure": "No",
    },
}


_TRANSVERSAL_ROUTES = {
    "CO-TR-001": "Consulta oficial individual y revisión del expediente administrativo",
    "CO-TR-002": "Radicar solicitud de expediente y preservar evidencia",
    "CO-SA-001": "Radicar petición prioritaria con soportes médicos minimizados",
    "CO-CD-001": "Radicar reclamo ante fuente y operador y verificar actualización",
    "CO-CD-003": "Presentar reclamación directa de garantía y conservar evidencia",
    "CO-CD-004": "Cotejar título, liquidar saldo y adelantar cobro documentado",
}


def _coherent_controlled_answers(core_v11, expanded_documents, product_code: str):
    from scripts.generate_m32_2_visual_samples import _controlled_answers as base_answers

    answers, rows = base_answers(core_v11, expanded_documents, product_code)
    for key, value in list(answers.items()):
        if isinstance(value, str):
            answers[key] = value.replace("M32.2", "M32.3")
    answers.update(_TRANSVERSAL_OVERRIDES.get(product_code, {}))
    return answers, rows


def _generate_transversal_compatible(output: Path) -> list[dict]:
    import core_v11
    import expanded_documents
    from docx_builder import build_docx

    records: list[dict] = []
    for product_code, preferred_kind in implementation.TRANSVERSAL_KINDS.items():
        product = core_v11.product(product_code)
        if not product:
            raise RuntimeError(f"No existe el producto canónico {product_code}.")
        answers, question_rows = _coherent_controlled_answers(core_v11, expanded_documents, product_code)
        calculation = {}
        if product_code == "CO-TR-001":
            calculation = {"dataset_records_included": 10, "historical_master_expected_records": 49}
        elif product_code == "CO-CD-004":
            calculation = {
                "principal": 12000000,
                "partial_payments_total": 2000000,
                "other_charges": 0,
                "explained_balance": 10000000,
                "reported_balance": 10000000,
                "balance_difference": 0,
                "interest_modality": "Intereses no calculados: tasa y período sujetos a validación",
                "effective_annual_rate": 0,
                "interest_banking_current_ea": 0,
                "maximum_reference_ea": 0,
            }
        result = {
            "risk": "yellow",
            "risk_label": "Amarillo",
            "score": 2,
            "route": _TRANSVERSAL_ROUTES[product_code],
            "summary": "Expediente sintético coherente sujeto a revisión jurídica sustantiva y QA visual humano.",
            "issues": [],
            "recommendations": [],
            "assumptions": ["Datos sintéticos utilizados exclusivamente para QA documental."],
            "calculation": calculation,
            "sast_matches": [],
            "triggered_rules": [],
        }
        specs = expanded_documents.document_specs(
            f"M32-3-{product_code}", product_code, answers, result, product, core_v11.now(), question_rows
        )
        spec = next((item for item in specs if item.get("kind") == preferred_kind), None)
        if not spec:
            available = ", ".join(str(item.get("kind")) for item in specs)
            raise RuntimeError(f"La fábrica de {product_code} no produjo {preferred_kind}. Disponibles: {available}.")
        destination = output / f"{product_code}_{preferred_kind}_M32_3.docx"
        build_docx(
            destination,
            spec["title"],
            spec.get("subtitle") or product.get("name", product_code),
            spec.get("metadata") or [],
            spec.get("sections") or [],
        )
        records.append(
            {
                "product_code": product_code,
                "factory": "expanded_documents.document_specs + docx_builder.build_docx",
                "factory_version": "M32.3-transversal-coherente",
                "document_id": preferred_kind,
                "source_filename": spec["title"],
                "sample_name": destination.name,
                "generation_id": f"M32-3-{product_code}",
                "factory_legal_approval": "pending",
                "factory_qa_approval": "pending",
                "factory_released": False,
            }
        )
    return records


implementation.ControlledEvaluator = FactoryCompatibleEvaluator
implementation._copy_primary = _copy_primary_compatible
implementation._generate_transversal = _generate_transversal_compatible


if __name__ == "__main__":
    raise SystemExit(implementation.main())
