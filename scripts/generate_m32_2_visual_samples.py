#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil


PRODUCT_KINDS = {
    "CO-TR-001": "sast_report",
    "CO-TR-002": "traffic_record_request",
    "CO-SA-001": "health_petition",
    "CO-CD-001": "habeas_claim",
    "CO-CD-003": "consumer_mechanism_diagnosis",
    "CO-CD-004": "debt_diagnostic",
}

PRODUCT_LABELS = {
    "CO-TR-001": "Diagnóstico SAST controlado",
    "CO-TR-002": "Defensa y expediente de tránsito controlado",
    "CO-SA-001": "Petición de acceso a salud controlada",
    "CO-CD-001": "Reclamo de hábeas data controlado",
    "CO-CD-003": "Reclamación de consumo controlada",
    "CO-CD-004": "Diagnóstico y cobro de obligación controlado",
}


YES_NO_HINTS = (
    "active", "available", "confirmed", "consent", "disputed", "fraud", "urgent",
    "identity_theft", "litigation", "paid", "prior_claim", "public", "sensitive",
    "support", "verified", "known", "exists", "received", "response", "appeal",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_value(field: str):
    key = field.casefold()
    if "email" in key:
        return "expediente.demo@legalaiz.it"
    if any(token in key for token in ("phone", "celular", "telefono")):
        return "3000000000"
    if any(token in key for token in ("nit", "identification", "identity", "document_number", "_id")):
        return "100000001"
    if "date" in key or key.endswith("_at"):
        return "2026-06-15"
    if "time" in key:
        return "10:00"
    if "year" in key:
        return "2026"
    if any(token in key for token in ("amount", "balance", "capital", "canon", "commercial_value", "cost", "debt", "fee", "income", "rent", "salary", "value")):
        return "1000000"
    if any(token in key for token in ("days", "hours", "months", "years", "count", "rate", "percentage", "term")):
        return "10"
    if any(token in key for token in YES_NO_HINTS):
        return "No"
    if any(token in key for token in ("name", "creditor", "debtor", "holder", "requester", "consumer", "patient", "representative")):
        return "Persona Demo LegalAIZ.it"
    if any(token in key for token in ("authority", "entity", "provider", "source", "operator", "company", "eps", "ips")):
        return "Entidad Demo LegalAIZ.it"
    if "address" in key or "location" in key or "territory" in key or "city" in key:
        return "Medellín, Antioquia"
    if "plate" in key:
        return "ABC123"
    if any(token in key for token in ("facts", "detail", "description", "object", "purpose", "request", "claim", "reason", "evidence")):
        return (
            "Información demostrativa suficientemente detallada para probar la generación, "
            "trazabilidad y revisión documental de LegalAIZ.it sin representar un caso real."
        )
    return "Información demostrativa confirmada para el control documental M32.2."


def _choice_value(question: dict, fallback):
    options = question.get("options") or question.get("choices") or []
    normalized = []
    for option in options:
        if isinstance(option, dict):
            value = option.get("value", option.get("label"))
        else:
            value = option
        if value not in (None, ""):
            normalized.append(str(value))
    for preferred in ("No", "No aplica", "Ninguno", "Pendiente", "Sí"):
        if preferred in normalized:
            return preferred
    return normalized[0] if normalized else fallback


def _controlled_answers(core_v11, expanded_documents, product_code: str) -> tuple[dict, list[dict]]:
    """Completa variables reales del generador y todas las preguntas del producto."""
    source = inspect.getsource(expanded_documents)
    fields = set(re.findall(r"\ba\.get\(['\"]([^'\"]+)['\"]", source))
    answers = {field: _safe_value(field) for field in fields}

    interview = core_v11.INTERVIEWS.get(product_code, {})
    questions = list(interview.get("questions") or [])
    question_rows = []
    for question in questions:
        field = str(question.get("id") or "").strip()
        if not field:
            continue
        fallback = _safe_value(field)
        value = _choice_value(question, fallback)
        answers[field] = value
        question_rows.append({
            "id": field,
            "label": question.get("label") or field,
            "answer": value,
        })

    # Identidad y narrativa común para evitar ambigüedad entre sujetos y campos.
    answers.update({
        "requester_name": "Juan Pérez Demo",
        "data_subject_name": "Juan Pérez Demo",
        "consumer_name": "Juan Pérez Demo",
        "patient_name": "Juan Pérez Demo",
        "creditor_name": "Empresa Acreedora Demo S.A.S.",
        "debtor_name": "Persona Deudora Demo",
        "authority": "Secretaría o autoridad competente Demo",
        "entity_name": "Entidad Destinataria Demo",
        "provider_name": "Proveedor Demo S.A.S.",
        "source_name": "Fuente de Información Demo S.A.S.",
        "operator_name": "Operador de Información Demo S.A.S.",
        "email": "expediente.demo@legalaiz.it",
        "filing_email": "expediente.demo@legalaiz.it",
        "facts_detail": (
            "El expediente demostrativo describe hechos, cronología, soportes y solicitudes "
            "de forma suficiente para probar la fábrica documental sin corresponder a una persona real."
        ),
        "request_detail": (
            "Se solicita verificar el expediente, entregar los soportes, responder cada punto "
            "y dejar trazabilidad completa de la actuación demostrativa."
        ),
        "data_confirmed": "Sí",
        "data_minimized": "Sí",
        "deadline_urgent": "No",
        "active_litigation": "No",
        "judicial_or_insolvency": "No",
        "identity_theft": "No",
    })
    return answers, question_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera evidencia visual M32.2 mediante las fábricas activas.")
    parser.add_argument("--output", required=True, help="Directorio de salida para las seis muestras.")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    runtime = output.parent / "runtime"
    samples = output
    shutil.rmtree(output.parent, ignore_errors=True)
    samples.mkdir(parents=True, exist_ok=True)
    os.environ["LEGAL_RUNTIME_DIR"] = str(runtime)
    os.environ.setdefault("LEGAL_PROFILE", "local")
    os.environ.setdefault("LEGAL_ALLOW_DEMO_ACCOUNTS", "true")

    # La instalación debe ocurrir antes de importar core_v11, que conserva la
    # importación histórica directa de build_docx.
    from legalai_platform.document_release_gate import install_docx_release_gate, manifest_path_for

    install_docx_release_gate()
    import core_v11
    import expanded_documents
    from docx_builder import build_docx

    records: list[dict] = []
    for product_code, preferred_kind in PRODUCT_KINDS.items():
        product = core_v11.product(product_code)
        if not product:
            raise RuntimeError(f"No existe el producto canónico {product_code}.")
        answers, question_rows = _controlled_answers(core_v11, expanded_documents, product_code)
        result = {
            "risk": "yellow",
            "risk_label": "Amarillo",
            "score": 2,
            "summary": "Expediente demostrativo sujeto a revisión jurídica y QA.",
            "issues": [],
            "recommendations": [],
            "assumptions": ["Datos sintéticos utilizados exclusivamente para QA documental."],
            "calculation": {},
        }
        case_id = f"M32-2-{product_code}"
        specs = expanded_documents.document_specs(
            case_id,
            product_code,
            answers,
            result,
            product,
            core_v11.now(),
            question_rows,
        )
        spec = next((item for item in specs if item.get("kind") == preferred_kind), None)
        if not spec:
            available = ", ".join(str(item.get("kind")) for item in specs)
            raise RuntimeError(
                f"La fábrica activa de {product_code} no produjo {preferred_kind}. Disponibles: {available}."
            )

        destination = samples / f"{product_code}_{preferred_kind}_M32_2.docx"
        build_docx(
            destination,
            spec["title"],
            spec.get("subtitle") or PRODUCT_LABELS[product_code],
            spec.get("metadata") or [],
            spec.get("sections") or [],
        )
        destination_manifest = manifest_path_for(destination)
        if not destination_manifest.is_file():
            raise RuntimeError(f"La compuerta no generó manifiesto para {product_code}.")
        gate = json.loads(destination_manifest.read_text(encoding="utf-8"))
        if gate.get("approval_state") != {"legal": "pending", "qa": "pending"}:
            raise RuntimeError(f"La muestra {product_code} no conserva aprobación dual pendiente.")
        if gate.get("requires_human_visual_review") is not True:
            raise RuntimeError(f"La muestra {product_code} no exige revisión visual humana.")
        records.append({
            "product_code": product_code,
            "kind": preferred_kind,
            "source_name": spec["title"],
            "sample_name": destination.name,
            "factory": "expanded_documents.document_specs + docx_builder.build_docx",
            "sha256": _sha256(destination),
            "quality_manifest": destination_manifest.name,
            "release_status": gate.get("release_status"),
        })

    if {record["product_code"] for record in records} != set(PRODUCT_KINDS):
        raise RuntimeError("La evidencia no cubre exactamente los seis productos de M32.2.")
    manifest = {
        "iteration": "M32.2",
        "generator": "fábricas activas expanded_documents.document_specs/docx_builder.build_docx",
        "products": records,
        "approval_state": "pending_dual_approval",
        "requires_human_visual_review": True,
    }
    (samples / "m32-2-samples.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
