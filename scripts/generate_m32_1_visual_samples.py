from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239


class LaborEvaluator:
    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": ["DOC-LA-CONTRACT-001", "ANX-LA-FUN-001"],
            "readiness": "ready_for_human_review",
            "review_requirements": ["Revisión jurídica laboral y QA visual"],
            "warnings": [],
            "blocks": ["LABOR_BASE", "FUNCTIONS_ANNEX"],
        }


class ConfidentialityEvaluator:
    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": ["DOC-EM4-NDA-001"],
            "readiness": "ready_for_human_review",
            "professional_review_required": True,
            "review_requirements": ["Revisión jurídica contractual y QA visual"],
            "findings": [],
            "blocks": ["NDA_BASE", "SECURITY", "IP"],
        }


def labor_answers():
    return {
        "employer": {
            "type": "legal_person",
            "legalName": "Soluciones Andinas S.A.S.",
            "identificationNumber": "901234567-8",
        },
        "employerSignatory": {
            "fullName": "María Fernanda Gómez Ruiz",
            "positionOrCapacity": "representante legal",
        },
        "worker": {
            "fullName": "Carlos Andrés Pérez López",
            "identificationNumber": "1030123456",
        },
        "role": {
            "jobTitle": "Analista jurídico y documental",
            "purpose": "gestionar contratos, expedientes y controles de trazabilidad jurídica de la organización",
            "functionsPlacement": "full_in_contract",
            "essentialFunctions": [
                "Revisar y preparar contratos, comunicaciones y actas conforme a los procedimientos internos.",
                "Mantener actualizados los expedientes, matrices de obligaciones y registros de versiones.",
                "Reportar riesgos jurídicos, vencimientos, inconsistencias documentales e incidentes de información.",
                "Coordinar la entrega de soportes con las áreas responsables y preservar la confidencialidad.",
            ],
        },
        "work": {
            "mainWorkplace": "Medellín, Antioquia",
            "modality": "onsite",
            "actualStartDate": "2026-08-10",
        },
        "schedule": {"weeklyHours": 42, "type": "fixed"},
        "compensation": {"baseSalary": 4200000, "salaryType": "ordinary"},
    }


def confidentiality_answers():
    return {
        "party_a": {
            "identification": {
                "type": "legal_person",
                "name": "Soluciones Andinas S.A.S.",
                "id_number": "901234567-8",
                "address": "Medellín, Antioquia",
                "email": "juridica@demo.legalaiz.it",
            },
            "signatory": {
                "name": "María Fernanda Gómez Ruiz",
                "id_number": "43678901",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "party_b": {
            "identification": {
                "type": "legal_person",
                "name": "Tecnología Segura S.A.S.",
                "id_number": "900765432-1",
                "address": "Bogotá D.C.",
                "email": "contratos@demo.legalaiz.it",
            },
            "signatory": {
                "name": "Juan David Torres",
                "id_number": "79543210",
                "capacity": "representante legal",
                "authority_source": "certificado de existencia y representación legal",
            },
        },
        "agreement": {
            "type": "mutual",
            "reciprocal": True,
            "purpose": "evaluar y ejecutar una integración tecnológica y documental entre las partes",
            "reference": "Proyecto Integración Segura 2026",
        },
        "information": {
            "categories": "arquitectura, código, documentación técnica, modelos jurídicos, precios, estrategias y datos operativos",
            "formats_sources": "documentos, reuniones, repositorios autorizados, demostraciones y accesos controlados",
            "exclusions": "información pública, conocida legítimamente o desarrollada de forma independiente",
        },
        "access": {
            "authorized_recipients": "personal directivo, jurídico y técnico expresamente asignado",
            "representatives": "asesores y subcontratistas previamente autorizados y sujetos a obligaciones equivalentes",
            "need_to_know": "mínimo privilegio y necesidad estricta de conocer",
            "permitted_use": "evaluación, integración, pruebas controladas y ejecución del proyecto",
            "compelled_disclosure": "notificación previa cuando sea legalmente posible y revelación mínima necesaria",
        },
        "security": {
            "controls": {
                "level": "enhanced",
                "technical": "cifrado, MFA, registro de accesos, segregación y copias de seguridad",
                "organizational": "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes",
                "physical": "control de ingreso y custodia de soportes",
            },
            "incident_protocol": "notificación sin demora injustificada, contención, investigación y preservación de evidencia",
        },
        "data": {"personal": False, "roles": {}, "lifecycle": "conservación durante la finalidad y eliminación al cierre", "crossborder": False},
        "ip": {
            "results_allocation": "case_by_case",
            "preexisting_materials": "herramientas, bibliotecas, plantillas y conocimientos identificados por cada parte",
            "source_code_reverse_engineering": "prohibición salvo autorización expresa o excepción legal",
        },
        "ai": {"used": True, "training_outputs": "uso controlado sin entrenamiento ni retención con información protegida"},
        "term_remedies": {
            "agreement_years": 2,
            "ordinary_confidentiality_years": 5,
            "trade_secret_rule": "while_secret",
            "penalty_or_liability": "responsabilidad por daños directos, probados y causalmente vinculados al incumplimiento",
        },
        "closure_confirmation": {
            "return_destroy": "devolución o eliminación segura de la información al cierre",
            "retained_copies": "conservación limitada por obligación legal, respaldo inalterable o defensa de derechos",
            "dispute_mechanism": "negotiation_conciliation",
        },
    }


def export_primary(factory, answers, runtime_root: Path, output: Path, expected_name: str):
    manifest = factory.generate(answers, actor={"id": "m32-1-ci", "role": "qa"})
    generation = runtime_root / "data" / "generated"
    candidates = list(generation.rglob(expected_name))
    if len(candidates) != 1:
        raise RuntimeError(f"Se esperaba una muestra {expected_name} y se encontraron {len(candidates)}.")
    target = output / expected_name
    shutil.copy2(candidates[0], target)
    return {
        "generation_id": manifest["generation_id"],
        "product_id": manifest["product_id"],
        "source": str(candidates[0]),
        "artifact": target.name,
        "documents": manifest["documents"],
    }


def main():
    parser = argparse.ArgumentParser(description="Genera muestras reales M32.1 para renderizado visual en CI.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="legalaiz-m32-1-") as tmp:
        runtime_root = Path(tmp)
        evidence = []
        evidence.append(
            export_primary(
                CoLa002DocumentFactoryV239(runtime_root, LaborEvaluator()),
                labor_answers(),
                runtime_root,
                args.output,
                "CO-LA-002_Contrato_Indefinido.docx",
            )
        )
        evidence.append(
            export_primary(
                CoEm004DocumentFactoryV247(runtime_root, ConfidentialityEvaluator()),
                confidentiality_answers(),
                runtime_root,
                args.output,
                "CO-EM-004_Acuerdo_Confidencialidad_PI.docx",
            )
        )

    (args.output / "evidence.json").write_text(
        json.dumps({"iteration": "M32.1", "samples": evidence}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"generated": [item["artifact"] for item in evidence]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
