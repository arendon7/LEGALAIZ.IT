#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
for candidate in (ROOT, RUNTIME_MODULES):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

CANONICAL_PRODUCTS = (
    "CO-TR-001",
    "CO-TR-002",
    "CO-SA-001",
    "CO-CD-001",
    "CO-CD-003",
    "CO-CD-004",
    "CO-AR-001",
    "CO-EM-003",
    "CO-EM-004",
    "CO-LA-001",
    "CO-LA-002",
)

TRANSVERSAL_KINDS = {
    "CO-TR-001": "sast_report",
    "CO-TR-002": "traffic_record_request",
    "CO-SA-001": "health_petition",
    "CO-CD-001": "habeas_claim",
    "CO-CD-003": "consumer_mechanism_diagnosis",
    "CO-CD-004": "debt_diagnostic",
}

PRIMARY_DOCUMENT_IDS = {
    "CO-AR-001": "DOC-AR-CONTRACT-001",
    "CO-EM-003": "DOC-EM-CONTRACT-001",
    "CO-EM-004": "DOC-EM4-NDA-001",
    "CO-LA-001": "DOC-LA1-CALCULATION-001",
    "CO-LA-002": "DOC-LA-CONTRACT-001",
}


class ControlledEvaluator:
    def __init__(self, documents: list[str], blocks: list[str] | None = None):
        self.documents = list(documents)
        self.blocks = list(blocks or [])

    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": self.documents,
            "readiness": "ready_for_human_review",
            "status": "ready_for_human_review",
            "professional_review_required": True,
            "professional_reviews": ["Revisión jurídica sustantiva", "QA visual humano"],
            "review_requirements": ["Revisión jurídica sustantiva", "QA visual humano"],
            "findings": [],
            "blockers": [],
            "warnings": [],
            "blocks": self.blocks,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _services_answers() -> dict:
    return {
        "client": {
            "identification": {
                "type": "legal_person",
                "name": "Soluciones Andinas S.A.S.",
                "identification_number": "901234567-8",
                "domicile": "Medellín, Antioquia",
                "email": "juridica@demo.legalaiz.it",
            },
            "signatory": {
                "name": "María Fernanda Gómez Ruiz",
                "identification_number": "43678901",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "contractor": {
            "identification": {
                "type": "legal_person",
                "name": "Consultoría Documental Segura S.A.S.",
                "identification_number": "900765432-1",
                "domicile": "Bogotá D.C.",
                "email": "contratos@demo.legalaiz.it",
            },
            "signatory": {
                "name": "Juan David Torres Mejía",
                "identification_number": "79543210",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "service": {
            "object": "prestar servicios independientes de diagnóstico, diseño y mejora de procesos documentales y tecnológicos",
            "expected_result": "entregar una arquitectura documentada, matrices de control, configuración funcional y evidencia de pruebas",
        },
        "scope": {
            "included": [
                "Levantar y documentar requerimientos y restricciones.",
                "Diseñar matrices, flujos y controles de trazabilidad.",
                "Configurar un entorno demostrativo y ejecutar pruebas acordadas.",
                "Entregar documentación técnica y sesiones de transferencia.",
            ],
            "excluded": [
                "Representación judicial o administrativa.",
                "Operación permanente de sistemas del contratante.",
                "Adquisiciones o licencias no aprobadas por escrito.",
            ],
            "deliverables": [
                {"id": "E1", "name": "Informe de diagnóstico", "milestone": "Semana 2", "acceptance_criteria": "Cobertura de procesos y riesgos priorizados", "format": "DOCX/PDF"},
                {"id": "E2", "name": "Diseño funcional y matriz de controles", "milestone": "Semana 5", "acceptance_criteria": "Trazabilidad entre requerimientos, controles y pruebas", "format": "DOCX/XLSX"},
                {"id": "E3", "name": "Cierre y transferencia", "milestone": "Semana 8", "acceptance_criteria": "Entrega de evidencias y acta de cierre", "format": "Digital"},
            ],
            "acceptance_criteria": "conformidad objetiva con el alcance, entregables, evidencias y criterios descritos",
        },
        "schedule": {
            "start_date": "2026-08-15",
            "end_date": "2026-10-15",
            "duration": "dos meses",
            "milestones": "diagnóstico, diseño, configuración, pruebas y cierre",
        },
        "execution": {
            "arrangement": "ejecución autónoma por resultados, con reuniones de coordinación y sin sujeción a jornada laboral",
            "place": "remota, con visitas previamente coordinadas en Medellín",
            "team": "equipo propio del contratista bajo su dirección y responsabilidad",
            "subcontracting": "solo para componentes especializados, con autorización previa y obligaciones equivalentes",
            "dependencies": "accesos, información, decisiones y validaciones oportunas del contratante",
        },
        "fees": {
            "model": "fixed",
            "currency": "COP",
            "amount": 48000000,
            "taxes": "más impuestos legalmente aplicables",
            "invoice": "factura electrónica y soportes del hito",
            "payment_term": "treinta días calendario después de aceptación y factura válida",
            "expenses": "solo gastos previamente autorizados y soportados",
            "retentions": "retenciones y descuentos exclusivamente conforme a la ley",
        },
        "independence": {
            "direction": "el contratista conserva autonomía técnica, administrativa y organizativa",
            "no_exclusivity": "no existe exclusividad salvo conflicto específico informado y aceptado",
            "personnel": "el contratista selecciona, dirige y remunera su personal",
            "social_security": "cada parte cumple las obligaciones de seguridad social que legalmente le correspondan",
        },
        "confidentiality": {
            "applies": True,
            "categories": "información técnica, jurídica, financiera, comercial y operativa no pública",
            "term": "cinco años, y mientras conserve carácter secreto cuando corresponda",
        },
        "data": {
            "personal": True,
            "roles": "se definirán por actividad; el encargado actuará solo bajo instrucciones documentadas",
            "security": "mínimo privilegio, autenticación robusta, cifrado, registro de accesos y gestión de incidentes",
            "crossborder": False,
        },
        "ip": {
            "preexisting": "cada parte conserva sus herramientas, plantillas, bibliotecas y conocimiento previo",
            "results": "los resultados específicamente pagados se asignan según el anexo, con alcance, territorio y duración expresos",
            "third_party": "los componentes de terceros conservan sus licencias",
        },
        "ai": {
            "used": True,
            "rules": "solo herramientas autorizadas, sin datos protegidos en servicios no aprobados y con revisión humana",
        },
        "risk": {
            "allocation": "cada parte responde por los riesgos bajo su control y coopera en prevención y mitigación",
            "liability": "responsabilidad por daños directos, ciertos y probados, con exclusiones y límites sujetos a revisión jurídica",
            "insurance": "coberturas proporcionales a las actividades efectivamente ejecutadas",
        },
        "termination": {
            "rules": "incumplimiento grave, imposibilidad prolongada, acuerdo o terminación sin causa con preaviso de treinta días",
            "cure_period": "diez días hábiles cuando el incumplimiento sea subsanable",
        },
        "closure": {
            "transition": "entrega de avances utilizables, documentación, accesos y activos del contratante",
            "return_destroy": "devolución o eliminación segura de información y credenciales",
        },
        "dispute": {"mechanism": "negotiation_conciliation_courts", "city": "Medellín"},
        "confirmation": {"reviewed": True},
    }


def _labor_contract_answers() -> dict:
    return {
        "employer": {
            "type": "legal_person",
            "legalName": "Soluciones Andinas S.A.S.",
            "identificationNumber": "901234567-8",
        },
        "employerSignatory": {"fullName": "María Fernanda Gómez Ruiz", "positionOrCapacity": "representante legal"},
        "worker": {"fullName": "Carlos Andrés Pérez López", "identificationNumber": "1030123456"},
        "role": {
            "jobTitle": "Analista jurídico y documental",
            "purpose": "gestionar contratos, expedientes y controles de trazabilidad jurídica de la organización",
            "functionsPlacement": "full_in_contract",
            "essentialFunctions": [
                "Revisar y preparar contratos, comunicaciones y actas conforme a los procedimientos internos.",
                "Mantener actualizados los expedientes, matrices de obligaciones y registros de versiones.",
                "Reportar riesgos jurídicos, vencimientos e inconsistencias documentales.",
                "Coordinar la entrega de soportes y preservar la confidencialidad.",
            ],
        },
        "work": {"mainWorkplace": "Medellín, Antioquia", "modality": "onsite", "actualStartDate": "2026-08-10"},
        "schedule": {"weeklyHours": 42, "type": "fixed"},
        "compensation": {"baseSalary": 4200000, "salaryType": "ordinary"},
    }


def _confidentiality_answers() -> dict:
    return {
        "party_a": {
            "identification": {"type": "legal_person", "name": "Soluciones Andinas S.A.S.", "id_number": "901234567-8", "address": "Medellín, Antioquia", "email": "juridica@demo.legalaiz.it"},
            "signatory": {"name": "María Fernanda Gómez Ruiz", "id_number": "43678901", "capacity": "representante legal", "authority_source": "certificado de existencia y representación legal"},
        },
        "party_b": {
            "identification": {"type": "legal_person", "name": "Tecnología Segura S.A.S.", "id_number": "900765432-1", "address": "Bogotá D.C.", "email": "contratos@demo.legalaiz.it"},
            "signatory": {"name": "Juan David Torres", "id_number": "79543210", "capacity": "representante legal", "authority_source": "certificado de existencia y representación legal"},
        },
        "agreement": {"type": "mutual", "reciprocal": True, "purpose": "evaluar y ejecutar una integración tecnológica y documental entre las partes", "reference": "Proyecto Integración Segura 2026"},
        "information": {"categories": "arquitectura, código, documentación técnica, modelos jurídicos, precios, estrategias y datos operativos", "formats_sources": "documentos, reuniones, repositorios autorizados, demostraciones y accesos controlados", "exclusions": "información pública, conocida legítimamente o desarrollada de forma independiente"},
        "access": {"authorized_recipients": "personal directivo, jurídico y técnico expresamente asignado", "representatives": "asesores y subcontratistas autorizados y sometidos a obligaciones equivalentes", "need_to_know": "mínimo privilegio", "permitted_use": "evaluación, integración, pruebas y ejecución del proyecto", "compelled_disclosure": "notificación previa cuando sea posible y revelación mínima"},
        "security": {"controls": {"level": "enhanced", "technical": "cifrado, MFA, registro de accesos, segregación y copias de seguridad", "organizational": "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes", "physical": "control de ingreso y custodia de soportes"}, "incident_protocol": "notificación, contención, investigación y preservación de evidencia"},
        "data": {"personal": False, "roles": {}, "lifecycle": "conservación durante la finalidad y eliminación al cierre", "crossborder": False},
        "ip": {"results_allocation": "case_by_case", "preexisting_materials": "herramientas, bibliotecas, plantillas y conocimientos identificados por cada parte", "source_code_reverse_engineering": "prohibición salvo autorización o excepción legal"},
        "ai": {"used": True, "training_outputs": "uso controlado sin entrenamiento ni retención con información protegida"},
        "term_remedies": {"agreement_years": 2, "ordinary_confidentiality_years": 5, "trade_secret_rule": "while_secret", "penalty_or_liability": "responsabilidad por daños directos, probados y causalmente vinculados"},
        "closure_confirmation": {"return_destroy": "devolución o eliminación segura", "retained_copies": "conservación limitada por obligación legal o defensa de derechos", "dispute_mechanism": "negotiation_conciliation"},
    }


def _copy_primary(factory, answers: dict, product_code: str, output: Path) -> dict:
    manifest = factory.generate(answers, actor={"id": "m32-3-ci", "role": "qa"})
    primary_id = PRIMARY_DOCUMENT_IDS[product_code]
    document = next((item for item in manifest.get("documents", []) if item.get("id") == primary_id), None)
    if not document:
        raise RuntimeError(f"La fábrica {product_code} no produjo el documento primario {primary_id}.")
    source = factory.output_dir / manifest["generation_id"] / manifest["document_folder"] / document["filename"]
    if not source.is_file():
        raise RuntimeError(f"No se encontró la salida primaria de {product_code}: {source}")
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
        "factory_legal_approval": manifest.get("legal_approval", {}).get("status", "pending"),
        "factory_qa_approval": manifest.get("qa_approval", {}).get("status", "pending"),
        "factory_released": bool(manifest.get("released", False)),
    }


def _generate_specialized(output: Path) -> list[dict]:
    from co_ar_001_document_factory_v250 import CoAr001DocumentFactoryV250
    from co_ar_001_test_fixtures_v249 import complete_answers as lease_answers
    from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
    from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
    from co_la_001_document_factory_v253 import CoLa001DocumentFactoryV253
    from co_la_001_test_fixtures_v252 import complete_answers as liquidation_answers
    from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239

    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="legalaiz-m32-3-specialized-") as temporary:
        root = Path(temporary)
        factories = (
            (
                CoAr001DocumentFactoryV250(root / "lease", ControlledEvaluator(["DOC-AR-CONTRACT-001"], ["AR-BASE", "AR-PROPERTY", "AR-ECONOMICS"])),
                lease_answers(),
                "CO-AR-001",
            ),
            (
                CoEm003DocumentFactoryV244(root / "services", ControlledEvaluator(["DOC-EM-CONTRACT-001"], ["EM-BASE-001", "EM-SCOPE-001", "EM-FEES-001"])),
                _services_answers(),
                "CO-EM-003",
            ),
            (
                CoEm004DocumentFactoryV247(root / "nda", ControlledEvaluator(["DOC-EM4-NDA-001"], ["NDA_BASE", "SECURITY", "IP"])),
                _confidentiality_answers(),
                "CO-EM-004",
            ),
            (
                CoLa001DocumentFactoryV253(root / "liquidation", ControlledEvaluator(["DOC-LA1-CALCULATION-001"], ["LABOR_CALCULATION", "EVIDENCE", "PRESCRIPTION"])),
                liquidation_answers(),
                "CO-LA-001",
            ),
            (
                CoLa002DocumentFactoryV239(root / "employment", ControlledEvaluator(["DOC-LA-CONTRACT-001", "ANX-LA-FUN-001"], ["LABOR_BASE", "FUNCTIONS_ANNEX"])),
                _labor_contract_answers(),
                "CO-LA-002",
            ),
        )
        for factory, answers, product_code in factories:
            records.append(_copy_primary(factory, answers, product_code, output))
    return records


def _generate_transversal(output: Path) -> list[dict]:
    import core_v11
    import expanded_documents
    from docx_builder import build_docx
    from scripts.generate_m32_2_visual_samples import _controlled_answers

    records: list[dict] = []
    for product_code, preferred_kind in TRANSVERSAL_KINDS.items():
        product = core_v11.product(product_code)
        if not product:
            raise RuntimeError(f"No existe el producto canónico {product_code}.")
        answers, question_rows = _controlled_answers(core_v11, expanded_documents, product_code)
        result = {
            "risk": "yellow",
            "risk_label": "Amarillo",
            "score": 2,
            "summary": "Expediente sintético sujeto a revisión jurídica sustantiva y QA visual humano.",
            "issues": [],
            "recommendations": [],
            "assumptions": ["Datos sintéticos utilizados exclusivamente para QA documental."],
            "calculation": {},
        }
        specs = expanded_documents.document_specs(
            f"M32-3-{product_code}", product_code, answers, result, product, core_v11.now(), question_rows
        )
        spec = next((item for item in specs if item.get("kind") == preferred_kind), None)
        if not spec:
            available = ", ".join(str(item.get("kind")) for item in specs)
            raise RuntimeError(f"La fábrica de {product_code} no produjo {preferred_kind}. Disponibles: {available}.")
        destination = output / f"{product_code}_{preferred_kind}_M32_3.docx"
        build_docx(destination, spec["title"], spec.get("subtitle") or product.get("name", product_code), spec.get("metadata") or [], spec.get("sections") or [])
        records.append({
            "product_code": product_code,
            "factory": "expanded_documents.document_specs + docx_builder.build_docx",
            "factory_version": "M32.2-transversal",
            "document_id": preferred_kind,
            "source_filename": spec["title"],
            "sample_name": destination.name,
            "generation_id": f"M32-3-{product_code}",
            "factory_legal_approval": "pending",
            "factory_qa_approval": "pending",
            "factory_released": False,
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera el portafolio documental M32.3 de los once productos canónicos.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("LEGAL_PROFILE", "local")
    os.environ.setdefault("LEGAL_ALLOW_DEMO_ACCOUNTS", "true")

    from legalai_platform.document_release_gate import enforce_document_release_gate, install_docx_release_gate, manifest_path_for

    install_docx_release_gate()
    records = _generate_transversal(output) + _generate_specialized(output)
    if {item["product_code"] for item in records} != set(CANONICAL_PRODUCTS) or len(records) != 11:
        raise RuntimeError("El portafolio M32.3 no cubre exactamente los once productos canónicos.")

    for record in records:
        docx = output / record["sample_name"]
        gate = enforce_document_release_gate(docx, expected_product=record["product_code"])
        sidecar = manifest_path_for(docx)
        if not sidecar.is_file():
            raise RuntimeError(f"No se generó el manifiesto de calidad para {docx.name}.")
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if payload.get("approval_state") != {"legal": "pending", "qa": "pending"}:
            raise RuntimeError(f"Estado de aprobación inválido en {sidecar.name}.")
        if payload.get("requires_human_visual_review") is not True:
            raise RuntimeError(f"La revisión visual humana no quedó exigida en {sidecar.name}.")
        if record["factory_legal_approval"] != "pending" or record["factory_qa_approval"] != "pending" or record["factory_released"]:
            raise RuntimeError(f"La fábrica especializada de {record['product_code']} intentó liberar automáticamente el documento.")
        record.update({
            "sha256": _sha256(docx),
            "quality_manifest": sidecar.name,
            "technical_preflight": "passed",
            "human_visual_review": "pending",
            "legal_substantive_review": "pending",
            "release_candidate": False,
            "release_status": payload.get("release_status"),
            "warnings": gate.get("warnings", []),
        })

    records.sort(key=lambda item: CANONICAL_PRODUCTS.index(item["product_code"]))
    portfolio = {
        "iteration": "M32.3",
        "product_count": 11,
        "products": records,
        "technical_preflight": "passed",
        "human_visual_review": "pending",
        "legal_substantive_review": "pending",
        "dual_approval": {"legal": "pending", "qa": "pending"},
        "release_candidate": False,
        "declaration": "La generación y el preflight técnico no equivalen a aprobación jurídica ni QA visual humano.",
    }
    (output / "m32-3-portfolio.json").write_text(json.dumps(portfolio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(portfolio, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
