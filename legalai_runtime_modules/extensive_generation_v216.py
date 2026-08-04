from __future__ import annotations

"""Generación documental extensa y evidencia de cobertura para LegalAIZ.it v2.16.

Esta capa no sustituye la aprobación jurídica. Su función es asegurar que los
productos maduros generen un paquete personalizado consolidado, además de los
archivos separados, y dejar evidencia técnica verificable de qué módulos,
cláusulas y archivos fueron utilizados.
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import json
import math
import re
import uuid

VERSION = "2.16"
SOURCE_MODEL_VERSION = "M4.0"

MATURE_PRODUCTS: dict[str, dict[str, Any]] = {
    "CO-EM-003": {
        "title": "Prestación de servicios independientes",
        "minimum_documents": 4,
        "minimum_words": 5600,
        "minimum_clauses": 20,
        "source_package": "CO-EM-003 · biblioteca contractual profunda M4",
    },
    "CO-AR-001": {
        "title": "Arrendamiento de vivienda urbana",
        "minimum_documents": 5,
        "minimum_words": 2800,
        "minimum_clauses": 20,
        "source_package": "CO-AR-001 · biblioteca contractual profunda M4",
    },
    "CO-LA-002": {
        "title": "Contratación laboral",
        "minimum_documents": 2,
        "minimum_words": 3600,
        "minimum_clauses": 18,
        "source_package": "CO-LA-002 · biblioteca contractual profunda M4",
    },
    "CO-EM-004": {
        "title": "Confidencialidad, secretos empresariales y propiedad intelectual",
        "minimum_documents": 4,
        "minimum_words": 3200,
        "minimum_clauses": 20,
        "source_package": "CO-EM-004 · biblioteca contractual profunda M4",
    },
    "CO-LA-001": {
        "title": "Liquidación laboral y reclamación",
        "minimum_documents": 3,
        "minimum_words": 2400,
        "minimum_clauses": 24,
        "source_package": "CO-LA-001 · modelo madurado v2.22",
    },
    "CO-TR-002": {
        "title": "Fotomulta no notificada",
        "minimum_documents": 7,
        "minimum_words": 2800,
        "minimum_clauses": 24,
        "source_package": "CO-TR-002 · producto jurídico madurado v2.25",
    },
    "CO-TR-001": {
        "title": "Chequeo SAST + inscripción verificada",
        "minimum_documents": 7,
        "minimum_words": 2600,
        "minimum_clauses": 20,
        "source_package": "CO-TR-001 · producto jurídico madurado v2.26",
    },
    "CO-SA-001": {
        "title": "Derecho de petición ante EPS o IPS",
        "minimum_documents": 7,
        "minimum_words": 1800,
        "minimum_clauses": 18,
        "source_package": "CO-SA-001 · producto jurídico madurado v2.31",
    },
    "CO-CD-001": {
        "title": "Centrales de riesgo y hábeas data financiero",
        "minimum_documents": 7,
        "minimum_words": 2200,
        "minimum_clauses": 18,
        "source_package": "CO-CD-001 · producto jurídico madurado v2.32",
    },
    "CO-CD-003": {
        "title": "Garantía, retracto y reversión del pago",
        "minimum_documents": 8,
        "minimum_words": 1800,
        "minimum_clauses": 20,
        "source_package": "CO-CD-003 · producto jurídico madurado v2.33",
    },
    "CO-CD-004": {
        "title": "Cobro, acuerdo de pago y pagaré",
        "minimum_documents": 4,
        "minimum_words": 1600,
        "minimum_clauses": 18,
        "source_package": "CO-CD-004 · producto jurídico madurado v2.34",
    },
}

LEGAL_KINDS = {
    "contract", "scope", "confidentiality", "intellectual_property", "data_processing", "closure",
    "lease_contract", "lease_inventory", "delivery_act", "restitution_act", "lease_guide",
    "employment_contract", "employment_functions_annex", "employment_compensation_annex",
    "employment_confidentiality_annex", "employment_equipment_annex", "employment_remote_annex",
    "nda", "information_inventory", "relationship_annex", "ip_annex", "data_annex",
    "incident_protocol", "closure_act",
    "calculation", "claim", "evidence_matrix", "settlement",
    "traffic_record_request", "traffic_notice_claim", "traffic_hearing_request",
    "traffic_revocation_request", "traffic_registry_correction", "traffic_technical_matrix",
    "traffic_escalation_guide",
    "sast_report", "sast_verification_matrix", "sast_record_request",
    "sast_supertransport_request", "sast_conditional_review", "sast_alert_registry",
    "sast_route_guide",
    "health_petition", "medical_record_request", "health_reiteration",
    "supersalud_escalation", "health_evidence_index", "health_deadline_calendar",
    "health_filing_guide",
    "habeas_consultation", "habeas_claim", "habeas_reiteration",
    "habeas_authority_escalation", "habeas_evidence_matrix", "habeas_deadline_calendar",
    "identity_theft_protocol",
    "consumer_mechanism_diagnosis", "warranty_claim", "withdrawal_notice",
    "payment_reversal_request", "recurring_debit_revocation",
    "ecommerce_non_delivery_termination", "consumer_evidence_matrix",
    "consumer_deadline_calendar",
    "debt_diagnostic", "account_statement", "collection_letter",
    "payment_agreement", "payment_schedule", "promissory_note",
    "instruction_letter", "payment_receipt", "settlement_certificate",
    "collection_evidence_matrix",
}

_UNRESOLVED_RE = re.compile(
    r"\[(?:[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 _/.,;:()\-]{2,}|\.{3}|—)\]|"
    r"\b(?:NULL|undefined|N/?A)\b",
    flags=re.IGNORECASE,
)


def create_generation_schema(con) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS extensive_generation_proofs(
          id TEXT PRIMARY KEY,
          case_id TEXT NOT NULL,
          product_code TEXT NOT NULL,
          generation_version TEXT NOT NULL,
          source_model_version TEXT NOT NULL,
          status TEXT NOT NULL,
          proof_sha256 TEXT NOT NULL,
          proof_json TEXT NOT NULL,
          proof_path TEXT NOT NULL,
          package_document_id TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(case_id) REFERENCES cases(id),
          FOREIGN KEY(package_document_id) REFERENCES documents(id)
        );
        CREATE INDEX IF NOT EXISTS idx_extensive_proofs_case
          ON extensive_generation_proofs(case_id, created_at DESC);
        """
    )


def _separator_section(title: str, subtitle: str, position: int, total: int) -> dict[str, Any]:
    return {
        "heading": f"PARTE {position} DE {total} — {title}",
        "text": subtitle,
        "page_break_before": False,
        "_type": "package_divider",
    }


def _package_index(specs: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [("Documento", "Función dentro del paquete")]
    for spec in specs:
        if spec.get("kind") == "traceability":
            continue
        rows.append((str(spec.get("title") or spec.get("kind")), str(spec.get("subtitle") or "Documento aplicable")))
    return rows


def append_consolidated_package(
    specs: list[dict[str, Any]],
    case_id: str,
    code: str,
    answers: dict[str, Any],
    result: dict[str, Any],
    product: dict[str, Any],
    generated_at: str,
) -> list[dict[str, Any]]:
    """Añade un DOCX consolidado para los cuatro productos jurídicos maduros."""
    if code not in MATURE_PRODUCTS or result.get("risk") == "red":
        return specs
    if any(x.get("kind") == "consolidated_package" for x in specs):
        return specs

    legal_specs = [x for x in specs if x.get("kind") in LEGAL_KINDS]
    trace_spec = next((x for x in specs if x.get("kind") == "traceability"), None)
    if not legal_specs:
        return specs

    sections: list[dict[str, Any]] = [
        {
            "heading": "PAQUETE JURÍDICO PERSONALIZADO CONSOLIDADO",
            "text": (
                f"Expediente {case_id}. Producto {code} — {product.get('title')}. "
                f"Generado el {generated_at} desde los biblioteca contractual profunda {SOURCE_MODEL_VERSION}. "
                "El paquete reúne el documento principal y únicamente los anexos activados por las respuestas y reglas del caso."
            ),
            "page_break_before": True,
        },
        {
            "heading": "ÍNDICE DOCUMENTAL",
            "table": _package_index(legal_specs),
            "text": (
                "Los documentos conservan separación funcional aunque se entreguen en un solo archivo. "
                "Cada parte debe revisarse junto con la ficha de diagnóstico, los soportes y las alertas del expediente."
            ),
        },
        {
            "heading": "CONTROL DE ORIGEN Y APROBACIÓN",
            "bullets": [
                f"Modelo fuente: {MATURE_PRODUCTS[code]['source_package']}.",
                f"Semáforo del caso: {result.get('risk_label', result.get('risk', '—'))}.",
                "El cierre jurídico del alcance corresponde al abogado responsable designado.",
                "QA valida implementación, integridad y presentación según el impacto; no se exige una segunda revisión jurídica genérica.",
            ],
        },
    ]

    total = len(legal_specs)
    for pos, spec in enumerate(legal_specs, 1):
        sections.append(_separator_section(str(spec.get("title")), str(spec.get("subtitle") or ""), pos, total))
        # El paquete consolidado ya incorpora un control global de origen y aprobación.
        # Se omiten los controles repetidos de cada documento para evitar páginas aisladas
        # y conservar una lectura contractual continua; los DOCX individuales sí los mantienen.
        cloned = [section for section in deepcopy(spec.get("sections") or []) if section.get("_type") != "control"]
        if cloned:
            cloned[0]["page_break_before"] = False
        sections.extend(cloned)

    if trace_spec:
        sections.append(_separator_section("FICHA TÉCNICA DE TRAZABILIDAD", "Anexo técnico no contractual", total + 1, total + 1))
        trace_sections = deepcopy(trace_spec.get("sections") or [])
        if trace_sections:
            trace_sections[0]["page_break_before"] = False
        sections.extend(trace_sections)

    package = {
        "kind": "consolidated_package",
        "title": f"Paquete jurídico personalizado — {product.get('title')}",
        "filename_suffix": "paquete_juridico_consolidado",
        "subtitle": f"Motor extenso v{VERSION} · producto jurídico v{product.get('version', VERSION)}",
        "sections": sections,
        "metadata": [
            ("Caso", case_id),
            ("Producto", f"{code} — {product.get('title')}"),
            ("Motor de generación extensa", VERSION),
            ("Versión del producto jurídico", str(product.get("version") or VERSION)),
            ("Modelo fuente", SOURCE_MODEL_VERSION),
            ("Documentos integrados", str(len(legal_specs))),
            ("Semáforo", str(result.get("risk_label") or result.get("risk") or "—")),
            ("Generado", generated_at),
        ],
    }
    return [*specs, package]


def _docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )


def analyze_docx(path: Path) -> dict[str, Any]:
    text = _docx_text(path)
    words = re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", text, flags=re.UNICODE)
    headings = [x.strip() for x in text.splitlines() if x.strip()]
    clause_headings = [
        h for h in headings
        if h.upper().startswith("CLÁUSULA ") or re.match(r"^\d+\.\s+", h)
    ]
    unresolved = sorted(set(m.group(0) for m in _UNRESOLVED_RE.finditer(text)))
    raw = path.read_bytes()
    return {
        "filename": path.name,
        "size_bytes": len(raw),
        "sha256": sha256(raw).hexdigest(),
        "word_count": len(words),
        "section_heading_count": len(clause_headings),
        "estimated_pages": max(1, math.ceil(len(words) / 340)),
        "unresolved_markers": unresolved,
    }


def _proof_status(code: str, documents: list[dict[str, Any]], result: dict[str, Any]) -> tuple[str, list[str]]:
    if result.get("risk") == "red":
        return "Bloqueado para revisión profesional", ["El semáforo rojo impide una salida jurídica definitiva automática."]
    if code not in MATURE_PRODUCTS:
        return "Generación estándar", ["El producto aún no pertenece a la ola de modelos jurídicos extensos."]

    policy = MATURE_PRODUCTS[code]
    legal_docs = [d for d in documents if d.get("kind") in LEGAL_KINDS]
    package = next((d for d in documents if d.get("kind") == "consolidated_package"), None)
    reasons: list[str] = []
    if len(legal_docs) < policy["minimum_documents"]:
        reasons.append(f"Se esperaban al menos {policy['minimum_documents']} documentos jurídicos aplicables.")
    if not package:
        reasons.append("No se generó el paquete consolidado.")
    else:
        if package.get("word_count", 0) < policy["minimum_words"]:
            reasons.append(f"El paquete no alcanzó el umbral interno de {policy['minimum_words']} palabras.")
        if package.get("section_heading_count", 0) < policy["minimum_clauses"]:
            reasons.append(f"El paquete no alcanzó el umbral interno de {policy['minimum_clauses']} cláusulas o secciones.")
        if package.get("unresolved_markers"):
            reasons.append("El paquete contiene marcadores sin resolver.")
    return ("Cobertura extensa verificada" if not reasons else "Requiere revisión de cobertura", reasons)


def build_generation_proof(
    con,
    generated_dir: Path,
    case_id: str,
    code: str,
    answers: dict[str, Any],
    result: dict[str, Any],
    created: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    create_generation_schema(con)
    rows = []
    package_document_id = None
    for item in created:
        row = con.execute("SELECT id,kind,name,file_path,version,status FROM documents WHERE id=?", (item["id"],)).fetchone()
        if not row:
            continue
        path = Path(row["file_path"])
        analysis = analyze_docx(path) if path.suffix.lower() == ".docx" and path.is_file() else {
            "filename": row["name"], "size_bytes": path.stat().st_size if path.is_file() else 0,
            "sha256": sha256(path.read_bytes()).hexdigest() if path.is_file() else "",
            "word_count": 0, "section_heading_count": 0, "estimated_pages": 0, "unresolved_markers": [],
        }
        doc = {"id": row["id"], "kind": row["kind"], "version": row["version"], "status": row["status"], **analysis}
        rows.append(doc)
        if row["kind"] == "consolidated_package":
            package_document_id = row["id"]

    status, reasons = _proof_status(code, rows, result)
    package = next((x for x in rows if x.get("kind") == "consolidated_package"), None)
    proof = {
        "proof_id": "PRF-" + uuid.uuid4().hex[:10].upper(),
        "case_id": case_id,
        "product_code": code,
        "generation_version": VERSION,
        "source_model_version": SOURCE_MODEL_VERSION,
        "created_at": generated_at,
        "status": status,
        "reasons": reasons,
        "risk": result.get("risk"),
        "risk_label": result.get("risk_label"),
        "activated_document_kinds": [x.get("kind") for x in rows if x.get("kind") not in {"traceability", "consolidated_package"}],
        "documents": rows,
        "metrics": {
            "files": len(rows),
            "legal_documents": len([x for x in rows if x.get("kind") in LEGAL_KINDS]),
            "total_words": sum(int(x.get("word_count", 0)) for x in rows),
            "total_sections": sum(int(x.get("section_heading_count", 0)) for x in rows),
            "unresolved_markers": sum(len(x.get("unresolved_markers") or []) for x in rows),
            "package_words": int((package or {}).get("word_count", 0)),
            "package_sections": int((package or {}).get("section_heading_count", 0)),
            "package_estimated_pages": int((package or {}).get("estimated_pages", 0)),
        },
        "controls": {
            "complete_model_source_recorded": code in MATURE_PRODUCTS,
            "consolidated_package_generated": package is not None,
            "all_files_hashed": all(bool(x.get("sha256")) for x in rows),
            "unresolved_markers_absent": not any(x.get("unresolved_markers") for x in rows),
            "dual_approval_required": True,
            "professional_use_authorized": False,
        },
        "answers_sha256": sha256(json.dumps(answers, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
    }
    canonical = json.dumps(proof, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    proof_hash = sha256(canonical).hexdigest()
    proof["proof_sha256"] = proof_hash
    proof_path = generated_dir / f"{code}_{case_id}_evidencia_generacion_v216_{proof['proof_id']}.json"
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    con.execute(
        """INSERT INTO extensive_generation_proofs(
             id,case_id,product_code,generation_version,source_model_version,status,
             proof_sha256,proof_json,proof_path,package_document_id,created_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            proof["proof_id"], case_id, code, VERSION, SOURCE_MODEL_VERSION, status,
            proof_hash, json.dumps(proof, ensure_ascii=False), str(proof_path), package_document_id, generated_at,
        ),
    )
    return proof


class ExtensiveGenerationV216:
    def __init__(self, root: Path):
        self.root = Path(root)

    def summary(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "title": "Generación documental extensa y verificación de cobertura",
            "source_model_version": SOURCE_MODEL_VERSION,
            "products": [{"product_code": k, **v} for k, v in MATURE_PRODUCTS.items()],
            "controls": [
                "paquete personalizado consolidado",
                "hash SHA-256 por archivo",
                "conteo de palabras y secciones",
                "detección de marcadores sin resolver",
                "registro de módulos activados",
                "aprobación dual obligatoria",
            ],
        }

    def latest_proof(self, con, case_id: str) -> dict[str, Any] | None:
        create_generation_schema(con)
        row = con.execute(
            "SELECT proof_json FROM extensive_generation_proofs WHERE case_id=? ORDER BY rowid DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        return json.loads(row["proof_json"]) if row else None

    def proof_path(self, con, case_id: str) -> Path | None:
        create_generation_schema(con)
        row = con.execute(
            "SELECT proof_path FROM extensive_generation_proofs WHERE case_id=? ORDER BY rowid DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        path = Path(row["proof_path"]) if row else None
        return path if path and path.is_file() else None
