#!/usr/bin/env python3
from __future__ import annotations

"""Entrada final M32.3 con casos sintéticos alineados a cada fábrica histórica.

Separa la compatibilidad técnica de fábricas (run_m32_3_full_portfolio) de la
configuración probatoria de los seis productos transversales. No cambia reglas
jurídicas ni convierte los datos demo en hechos o expedientes reales.
"""

from pathlib import Path

from scripts import run_m32_3_full_portfolio as base


VERIFIED_OVERRIDES = {
    "CO-TR-002": {
        "petitioner_name": "Juan Pérez Demo",
        "petitioner_id": "100000001",
        "acting_capacity": "Propietario",
        "authority": "Secretaría de Movilidad de Medellín",
        "plate": "ABC123",
        "comparendo_number": "05001000000012345678",
        "event_date": "2026-06-15",
        "event_location": "Medellín, Antioquia",
        "validation_date": "2026-06-16",
        "sent_date": "2026-06-18",
        "delivery_date": "No acreditada en la muestra",
        "first_knowledge_date": "2026-07-10",
        "evidence": [
            "Consulta SIMIT de muestra",
            "Captura del aviso recibido",
            "Solicitud de preservación de fotografías, video y metadatos",
        ],
    },
    "CO-SA-001": {
        "entity": "EPS Demo S.A.",
        "entity_type": "EPS",
        "entity_city": "Medellín, Antioquia",
        "request_type": "Autorización y continuidad de tratamiento",
        "petitioner_name": "Juan Pérez Demo",
        "petitioner_id": "100000001",
        "acting_capacity": "Paciente que actúa en nombre propio",
        "patient_name": "Juan Pérez Demo",
        "patient_id": "100000001",
        "patient_status": "Adulto con capacidad",
        "relationship_to_patient": "El mismo paciente",
        "representation_support": "No aplica: actúa en nombre propio",
        "request_detail": (
            "El paciente cuenta con orden médica vigente y solicita evitar la interrupción "
            "del tratamiento mientras la EPS coordina autorización, prestador y fecha cierta."
        ),
        "medical_support": "Sí",
        "prescription_date": "2026-07-20",
        "continuity_risk": "Sí",
        "priority_condition": "Riesgo de interrupción del tratamiento",
        "requested_outcome": (
            "Autorizar y coordinar el tratamiento ordenado, informar prestador y fecha de atención, "
            "y comunicar una respuesta de fondo por canal seguro."
        ),
        "filing_date": "2026-08-05",
        "secure_delivery": "Sí",
        "third_party_authorization": "No aplica",
        "data_minimized": "Sí",
        "email": "expediente.demo@legalaiz.it",
        "phone": "3000000000",
        "address": "Dirección Demo, Medellín",
        "city": "Medellín, Antioquia",
        "notification_channel": "Correo electrónico",
    },
    "CO-CD-003": {
        "consumer_name": "Juan Pérez Demo",
        "consumer_id": "100000001",
        "acting_capacity": "Consumidor directo",
        "provider_name": "Proveedor Demo S.A.S.",
        "order_or_contract": "PED-DEMO-2026-001",
        "city": "Medellín, Antioquia",
        "email": "expediente.demo@legalaiz.it",
        "product_description": "Electrodoméstico adquirido para uso doméstico",
        "purchase_value": "1000000",
        "purchase_channel": "Presencial",
        "facts_detail": (
            "El equipo dejó de funcionar dentro del período informado de garantía y fue presentado "
            "al proveedor con factura, serial y evidencia del defecto."
        ),
        "problem_type": "Producto defectuoso",
        "defect_detail": "Falla total de encendido después de uso doméstico ordinario.",
        "claim_goal": "Reparación gratuita; si no resulta procedente, aplicar el remedio legal correspondiente.",
        "request_mode": "Garantía legal",
        "evidence_status": "Factura, serial, fotografías y constancia de entrega al proveedor disponibles",
        "regulated_sector": "No",
        "injury_or_safety": "No",
    },
}

for code, values in VERIFIED_OVERRIDES.items():
    base._TRANSVERSAL_OVERRIDES.setdefault(code, {}).update(values)


VERIFIED_CALCULATIONS = {
    "CO-TR-001": {
        "dataset_records_included": 10,
        "historical_master_expected_records": 49,
    },
    "CO-TR-002": {
        "validation_to_sent_weekdays_preliminary": "2 (preliminar; validar calendario hábil y recepción efectiva)",
    },
    "CO-SA-001": {
        "term_category": "Petición general con prioridad sanitaria; validar norma especial aplicable",
        "preliminary_business_days": "Pendiente de validación jurídica",
        "filing_date": "2026-08-05",
        "preliminary_due_date": "Pendiente de cómputo con festivos, traslado y recepción efectiva",
    },
    "CO-CD-003": {
        "purchase_date": "2026-05-10",
        "delivery_date": "2026-05-12",
        "direct_claim_date": "2026-07-01",
        "direct_claim_due_date": "Pendiente de cómputo con calendario hábil y constancia de recepción",
        "withdrawal_due_date": "No aplica al supuesto de compra presencial",
        "reversal_request_due_date": "No aplica al supuesto demostrado",
        "reversal_effective_due_date": "No aplica al supuesto demostrado",
        "mechanism_eligibility": {
            "warranty": True,
            "withdrawal": False,
            "reversal": False,
            "periodic_debit": False,
            "non_delivery": False,
        },
    },
    "CO-CD-004": {
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
    },
}


def _generate_verified_transversal(output: Path) -> list[dict]:
    import core_v11
    import expanded_documents
    from docx_builder import build_docx

    records: list[dict] = []
    for product_code, preferred_kind in base.implementation.TRANSVERSAL_KINDS.items():
        product = core_v11.product(product_code)
        if not product:
            raise RuntimeError(f"No existe el producto canónico {product_code}.")
        answers, question_rows = base._coherent_controlled_answers(core_v11, expanded_documents, product_code)
        result = {
            "risk": "yellow",
            "risk_label": "Amarillo",
            "score": 2,
            "route": base._TRANSVERSAL_ROUTES[product_code],
            "summary": "Expediente sintético coherente sujeto a revisión jurídica sustantiva y QA visual humano.",
            "issues": [],
            "recommendations": [],
            "assumptions": ["Datos sintéticos utilizados exclusivamente para QA documental."],
            "calculation": VERIFIED_CALCULATIONS.get(product_code, {}),
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
        records.append({
            "product_code": product_code,
            "factory": "expanded_documents.document_specs + docx_builder.build_docx",
            "factory_version": "M32.3-transversal-claves-verificadas",
            "document_id": preferred_kind,
            "source_filename": spec["title"],
            "sample_name": destination.name,
            "generation_id": f"M32-3-{product_code}",
            "factory_legal_approval": "pending",
            "factory_qa_approval": "pending",
            "factory_released": False,
        })
    return records


base.implementation._generate_transversal = _generate_verified_transversal


if __name__ == "__main__":
    raise SystemExit(base.implementation.main())
