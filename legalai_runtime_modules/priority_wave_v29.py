from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import os
from zipfile import ZIP_DEFLATED, ZipFile
import csv
import json
import re
import uuid

from docx_builder import build_docx
from pilot_documents import (
    labor_claim_sections,
    labor_report_sections,
    sast_report_sections,
    traffic_request_sections,
)

def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "documento")).strip("._") or "documento"


def cop(value) -> str:
    try:
        return "$" + f"{float(value):,.0f}".replace(",", ".") + " COP"
    except Exception:
        return "$0 COP"



def _runtime_root(project_root: Path) -> Path:
    raw = os.environ.get("LEGAL_RUNTIME_DIR", "").strip()
    path = Path(raw).expanduser() if raw else Path(project_root) / "runtime"
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()

class PriorityWaveV29:
    """Ola prioritaria de candidatos estructurados.

    Esta capa no verifica ni aprueba originales. Sirve para convertir la información
    accesible de los paquetes CO-LA-001, CO-TR-002 y CO-TR-001 en salidas físicas,
    trazables y probables, manteniendo cerrada la generación primaria canónica.
    """

    VERSION = "2.9"
    CODES = ("CO-LA-001", "CO-TR-002", "CO-TR-001")

    DEFINITIONS = {
        "CO-LA-001": {
            "title": "Liquidación laboral y reclamación de acreencias",
            "originals": [
                "LegalAIZit_Paquete_09_Liquidacion_Laboral_Consolidado_v2.pdf",
                "00_Manual_Producto_CO-LA-001.docx",
                "01_Informe_Estimativo_Liquidacion_Laboral.docx",
                "Calculadora_Liquidacion_Laboral.xlsx",
                "Reclamacion_Acreencias_Laborales.docx",
            ],
            "documents": [
                {"kind": "v29_labor_report", "title": "Informe estimativo de liquidación laboral", "format": "DOCX"},
                {"kind": "v29_labor_claim", "title": "Reclamación directa de acreencias laborales", "format": "DOCX"},
                {"kind": "v29_labor_evidence", "title": "Checklist probatorio y de validación", "format": "DOCX"},
                {"kind": "v29_labor_calculator", "title": "Matriz de cálculo y trazabilidad", "format": "CSV"},
            ],
            "limitations": [
                "No suma automáticamente sanción moratoria, sanción por cesantías, perjuicios ni conceptos que dependan de prueba.",
                "Fuero, estabilidad reforzada, sector público, contrato realidad, litigio o salario variable sin soporte bloquean el resultado definitivo.",
                "Los parámetros deben permanecer versionados y ser revalidados cuando cambie la normativa.",
            ],
        },
        "CO-TR-002": {
            "title": "Fotomulta no notificada o indebidamente notificada",
            "originals": [
                "LegalAIZit_Paquete_10_Fotomulta_No_Notificada_Consolidado_v2.pdf",
                "Manual_Producto_CO-TR-002.docx",
                "Solicitud_Integral_Expediente_Fotomulta.docx",
                "Solicitud_Audiencia_Pruebas.docx",
                "Revocatoria_Directa_Condicionada.docx",
                "Guia_Escalamiento_Fotomulta.docx",
            ],
            "documents": [
                {"kind": "v29_traffic_request", "title": "Solicitud integral de expediente y reclamación", "format": "DOCX"},
                {"kind": "v29_traffic_hearing", "title": "Solicitud de audiencia y pruebas", "format": "DOCX"},
                {"kind": "v29_traffic_evidence", "title": "Índice de evidencias y trazabilidad", "format": "DOCX"},
                {"kind": "v29_traffic_guide", "title": "Guía de etapa y escalamiento", "format": "DOCX"},
            ],
            "limitations": [
                "No promete anulación, archivo, devolución ni eliminación automática de registros.",
                "Resolución sancionatoria, cobro coactivo, embargo, pago o proceso judicial exigen valoración profesional.",
                "La ruta depende de la etapa, el expediente, la notificación y la afectación material del derecho de defensa.",
            ],
        },
        "CO-TR-001": {
            "title": "Chequeo SAST e inscripción de seguimiento",
            "originals": [
                "Matriz_Maestra_SAST_Legalaizit_v1.xlsx",
                "Actos_individuales_SAST_disponibles.pdf",
                "Fuentes_y_notas_SAST.md",
            ],
            "documents": [
                {"kind": "v29_sast_report", "title": "Informe de coincidencia preliminar SAST", "format": "DOCX"},
                {"kind": "v29_sast_checklist", "title": "Checklist de validación individual", "format": "DOCX"},
                {"kind": "v29_sast_alerts", "title": "Registro de alertas y seguimiento", "format": "DOCX"},
                {"kind": "v29_sast_snapshot", "title": "Snapshot de matriz piloto", "format": "CSV"},
            ],
            "limitations": [
                "La porción incorporada es demostrativa y no sustituye la matriz maestra de 49 actuaciones.",
                "La coincidencia por autoridad y fecha es preliminar; debe individualizar dispositivo, expediente y acto.",
                "Una apertura de investigación no equivale a una decisión firme ni habilita por sí sola revocación o devolución.",
            ],
        },
    }

    def __init__(self, root: Path, products: list[dict], interviews: dict, rules: dict, sast_sample: list[dict]):
        self.root = Path(root)
        self.products = {p.get("code"): p for p in products}
        self.interviews = interviews
        self.rules = rules
        self.sast_sample = list(sast_sample or [])
        self.candidate_root = self.root / "canonical_sources" / "candidates"
        self.generated = _runtime_root(self.root) / "generated"
        self.generated.mkdir(parents=True, exist_ok=True)

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS priority_candidate_sources_v29(
              id TEXT PRIMARY KEY,
              product_code TEXT NOT NULL,
              candidate_version TEXT NOT NULL,
              source_name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              original_sources_json TEXT NOT NULL,
              original_binary_embedded INTEGER NOT NULL DEFAULT 0,
              original_identity_verified INTEGER NOT NULL DEFAULT 0,
              professional_use_authorized INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_priority_candidate_source_v29
              ON priority_candidate_sources_v29(product_code,candidate_version,mime_type);
            CREATE TABLE IF NOT EXISTS priority_generation_runs_v29(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              source_snapshot_json TEXT NOT NULL,
              source_snapshot_sha256 TEXT NOT NULL,
              documents_json TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_priority_runs_v29_case
              ON priority_generation_runs_v29(case_id,created_at DESC);
            """
        )

    def init_baseline(self, con) -> None:
        now = utc_iso()
        for code in self.CODES:
            folder = self.candidate_root / code
            manifest_path = folder / "source_manifest_v29.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest.get("files", []):
                path = folder / entry["name"]
                if not path.is_file():
                    continue
                digest = sha256(path.read_bytes()).hexdigest()
                ident = "PCS29-" + sha256(f"{code}|{entry['mime_type']}".encode()).hexdigest()[:14].upper()
                con.execute(
                    """INSERT INTO priority_candidate_sources_v29(
                       id,product_code,candidate_version,source_name,file_path,mime_type,sha256,
                       original_sources_json,original_binary_embedded,original_identity_verified,
                       professional_use_authorized,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(product_code,candidate_version,mime_type) DO UPDATE SET
                         source_name=excluded.source_name,file_path=excluded.file_path,sha256=excluded.sha256,
                         status=excluded.status,updated_at=excluded.updated_at""",
                    (
                        ident, code, self.VERSION, path.name, str(path), entry["mime_type"], digest,
                        json.dumps(self.DEFINITIONS[code]["originals"], ensure_ascii=False),
                        0, 0, 0, "Candidato estructurado v2.9 - original pendiente", now, now,
                    ),
                )

    def _source_rows(self, con, code: str) -> list[dict]:
        return [dict(x) for x in con.execute(
            "SELECT * FROM priority_candidate_sources_v29 WHERE product_code=? ORDER BY mime_type", (code,)
        ).fetchall()]

    def _product_summary(self, con, code: str) -> dict:
        d = self.DEFINITIONS[code]
        sources = self._source_rows(con, code)
        return {
            "product_code": code,
            "title": d["title"],
            "questions": len(self.interviews.get(code, {}).get("questions", [])),
            "rules": len(self.rules.get(code, [])),
            "candidate_documents": d["documents"],
            "candidate_sources": [{**x, "file_path": None} for x in sources],
            "expected_originals": d["originals"],
            "limitations": d["limitations"],
            "original_binary_embedded": False,
            "original_identity_verified": False,
            "professional_use_authorized": False,
            "publication_authorized": False,
            "status": "Candidato estructurado - pendiente de original y cotejo",
            "package_url": f"/api/v29/priority-wave/{code}/candidate-package",
        }

    def summary(self, con) -> dict:
        products = [self._product_summary(con, code) for code in self.CODES]
        return {
            "version": self.VERSION,
            "title": "Ola prioritaria de estructuración jurídica",
            "products": products,
            "metrics": {
                "priority_products": len(products),
                "candidate_documents": sum(len(x["candidate_documents"]) for x in products),
                "questions": sum(x["questions"] for x in products),
                "rules": sum(x["rules"] for x in products),
                "candidate_source_files": sum(len(x["candidate_sources"]) for x in products),
                "verified_originals": 0,
                "publicable_products": 0,
                "sast_sample_records": len(self.sast_sample),
            },
            "sequence": [
                "Incorporar físicamente los originales por Ingesta Canónica.",
                "Verificar identidad y SHA-256 sin aprobación unilateral.",
                "Cotejar cada bloque obligatorio con fragmento y localizador.",
                "Aprobar jurídicamente y ejecutar QA sobre la misma revisión.",
                "Superar las puertas de publicación y actualización normativa.",
            ],
            "honesty_notice": (
                "Los archivos v2.9 son candidatos estructurados obtenidos del contenido accesible de los paquetes. "
                "No contienen los bytes de los originales de File Library y no autorizan uso profesional."
            ),
        }

    def package_bytes(self, con, code: str) -> bytes:
        if code not in self.CODES:
            raise ValueError("Producto no incluido en la ola prioritaria v2.9.")
        folder = self.candidate_root / code
        out = BytesIO()
        with ZipFile(out, "w", ZIP_DEFLATED) as z:
            for path in sorted(folder.glob("*")):
                if path.is_file():
                    z.write(path, arcname=path.name)
            z.writestr(
                "ESTADO_V29.json",
                json.dumps(self._product_summary(con, code), ensure_ascii=False, indent=2, default=str),
            )
        return out.getvalue()

    def _insert_document(self, con, case, actor_id: str, *, kind: str, title: str, suffix: str,
                         sections: list[dict], source_hash: str, extension: str = "docx",
                         binary_builder=None) -> dict:
        now = utc_iso()
        case_id = case["id"]
        code = case["product_code"]
        filename = safe_name(f"{code}_{case_id}_{suffix}_candidato_v2.9.{extension}")
        target = self.generated / filename
        if binary_builder:
            binary_builder(target)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if extension == "xlsx" else "text/csv"
        else:
            build_docx(
                target,
                title,
                "Borrador candidato estructurado · pendiente cotejo original",
                [
                    ("Expediente", case_id),
                    ("Producto", code),
                    ("Versión candidata", self.VERSION),
                    ("Fuente de trabajo", "Contenido accesible del paquete - original binario pendiente"),
                    ("Snapshot de fuente", source_hash),
                ],
                sections,
                footer=f"LegalAIZ.it · {code} · Candidato v2.9 · No canónico · Pendiente cotejo original",
                append_default_control=True,
            )
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        digest = sha256(target.read_bytes()).hexdigest()
        existing = con.execute("SELECT * FROM documents WHERE case_id=? AND kind=?", (case_id, kind)).fetchone()
        document_id = existing["id"] if existing else "DOC-" + uuid.uuid4().hex[:8].upper()
        lineage = {
            "generation_engine": "priority-structured-candidate-v2.9",
            "candidate_version": self.VERSION,
            "source_snapshot_sha256": source_hash,
            "original_binary_embedded": False,
            "original_identity_verified": False,
            "professional_use_authorized": False,
            "publication_authorized": False,
        }
        version = "candidate-2.9"
        status = "Borrador candidato estructurado v2.9 - pendiente cotejo original"
        if existing:
            con.execute(
                """UPDATE documents SET name=?,mime_type=?,file_path=?,content_sha256=?,updated_at=?,version=?,status=?,
                   canonical_status=?,generation_engine=?,lineage_json=? WHERE id=?""",
                (filename, mime, str(target), digest, now, version, status,
                 "No canónico - original pendiente", "priority-structured-candidate-v2.9",
                 json.dumps(lineage, ensure_ascii=False, sort_keys=True), document_id),
            )
        else:
            con.execute(
                """INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,
                   version,status,content_sha256,canonical_status,generation_engine,lineage_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (document_id, case_id, code, kind, filename, mime, str(target), None, now, now,
                 version, status, digest, "No canónico - original pendiente",
                 "priority-structured-candidate-v2.9", json.dumps(lineage, ensure_ascii=False, sort_keys=True)),
            )
        con.execute(
            "INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",
            (document_id, version, now,
             "Generación candidata v2.9; original jurídico pendiente de incorporación, cotejo y aprobación.", str(target)),
        )
        return {"id": document_id, "kind": kind, "name": filename, "version": version, "sha256": digest, "mime_type": mime}

    def _labor_evidence_sections(self, answers: dict, result: dict) -> list[dict]:
        return [
            {"heading": "1. Identificación del expediente", "table": [
                ("Campo", "Información"),
                ("Trabajador", answers.get("worker_name") or "Pendiente"),
                ("Empleador", answers.get("employer_name") or "Pendiente"),
                ("Período", f"{answers.get('start_date') or 'Pendiente'} a {answers.get('end_date') or 'Pendiente'}"),
                ("Riesgo", result.get("risk") or "Pendiente"),
            ]},
            {"heading": "2. Soportes mínimos", "bullets": [
                "Contrato, adiciones, carta de terminación o renuncia.",
                "Desprendibles de nómina y comprobantes bancarios.",
                "PILA, certificado y extractos de cesantías.",
                "Soportes de vacaciones, primas, comisiones, recargos y horas extra.",
                "Autorizaciones o fundamento de deducciones.",
                "Conciliaciones, reclamaciones o procesos previos.",
            ]},
            {"heading": "3. Datos que requieren confirmación", "bullets": [
                f"Relación privada confirmada: {answers.get('private_relation') or 'Pendiente'}.",
                f"Soportes salariales: {answers.get('salary_supports') or 'Pendiente'}.",
                f"Pagos previos: {answers.get('prior_payments') or 'Pendiente'}.",
                f"Datos confirmados por el usuario: {answers.get('data_confirmed') or 'Pendiente'}.",
            ]},
            {"heading": "4. Alertas activadas", "bullets": [
                f"{x.get('id')} — {x.get('message')}" for x in result.get("triggered_rules", [])
            ] or ["No se activaron alertas adicionales."]},
        ]

    def _labor_csv_builder(self, answers: dict, calc: dict, result: dict):
        def build(path: Path):
            rows = [
                ("Metadato", "Valor", "Control"),
                ("Trabajador", answers.get("worker_name") or "", "Dato suministrado"),
                ("Empleador", answers.get("employer_name") or "", "Dato suministrado"),
                ("Fecha inicial", answers.get("start_date") or "", "Dato suministrado"),
                ("Fecha final/corte", answers.get("end_date") or "", "Dato suministrado"),
                ("Versión de parámetros", (calc or {}).get("parameter_version") or "", "Parámetros versionados"),
                ("Salario pendiente", (calc or {}).get("salario_pendiente") or 0, "salario / 30 × días adeudados"),
                ("Cesantías", (calc or {}).get("cesantias") or 0, "base prestacional × días / 360"),
                ("Intereses cesantías", (calc or {}).get("intereses_cesantias") or 0, "cesantías × 12 % × días / 360"),
                ("Prima", (calc or {}).get("prima") or 0, "base prestacional × días / 360"),
                ("Vacaciones", (calc or {}).get("vacaciones") or 0, "salario × días / 720"),
                ("Indemnización estándar", (calc or {}).get("indemnizacion_estandar") or 0, "Solo bajo supuesto estándar confirmado"),
                ("Subtotal matemático", (calc or {}).get("subtotal_matematico") or 0, "No incluye sanciones o perjuicios"),
                ("Pagos previos", (calc or {}).get("pagos_previos_confirmados") or 0, "Solo pagos confirmados"),
                ("Total estimado", (calc or {}).get("total_estimado") or 0, "Estimación; no declaración judicial"),
            ]
            with path.open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerows(rows)
                writer.writerow([])
                writer.writerow(["Regla activada", "Mensaje", "Acción"])
                for item in result.get("triggered_rules", []):
                    writer.writerow([item.get("id") or "", item.get("message") or "", item.get("action") or ""])
        return build

    def _traffic_hearing_sections(self, a: dict, result: dict) -> list[dict]:
        return [
            {"heading": "1. Solicitud de comparecencia", "text": (
                f"Solicito a {a.get('authority') or '[AUTORIDAD]'} informar y habilitar la oportunidad de audiencia o comparecencia "
                f"relacionada con el comparendo {a.get('comparendo_number') or '[NÚMERO]'} y la placa {a.get('plate') or '[PLACA]'}."
            )},
            {"heading": "2. Pruebas solicitadas", "bullets": [
                "Copia íntegra del comparendo, evidencia y registro de validación.",
                "Identificación del agente validador, fecha, hora y competencia.",
                "Certificados, autorización y ubicación del dispositivo para la fecha.",
                "Guía postal, contenido enviado, constancia de entrega o devolución y aviso, si existió.",
                "Resolución, acta de audiencia, constancia de ejecutoria y recursos, cuando existan.",
            ]},
            {"heading": "3. Garantías procesales", "bullets": [
                "Permitir contradicción, aportación y solicitud de pruebas.",
                "No exigir pago como condición para ejercer defensa.",
                "Informar término, canal y funcionario competente.",
                "Emitir respuesta expresa y motivada sobre cada solicitud.",
            ]},
            {"heading": "4. Alertas del diagnóstico", "bullets": [
                f"{x.get('id')} — {x.get('message')}" for x in result.get("triggered_rules", [])
            ] or ["No se activaron alertas adicionales."]},
        ]

    def _traffic_evidence_sections(self, a: dict) -> list[dict]:
        return [
            {"heading": "1. Identificación", "table": [
                ("Campo", "Información"), ("Autoridad", a.get("authority") or "Pendiente"),
                ("Comparendo", a.get("comparendo_number") or "Pendiente"), ("Placa", a.get("plate") or "Pendiente"),
                ("Fecha", a.get("event_date") or "Pendiente"),
            ]},
            {"heading": "2. Evidencia que debe integrar el expediente", "bullets": [
                "Comparendo y evidencia original legible.", "Registro de validación y agente validador.",
                "Prueba de envío, entrega, devolución o aviso.", "Consulta oficial SIMIT y RUNT.",
                "Resolución sancionatoria y constancia de notificación, si existe.",
                "Mandamiento de pago, embargo o actuación judicial, si existe.",
            ]},
            {"heading": "3. Control de autenticidad", "bullets": [
                "Verificar la información únicamente en canales oficiales.",
                "No abrir enlaces de mensajes no verificados ni realizar pagos desde ellos.",
                "Conservar capturas, encabezados de correo y fecha de cada consulta.",
            ]},
        ]

    def _traffic_guide_sections(self, a: dict) -> list[dict]:
        return [
            {"heading": "1. Etapa informada", "table": [
                ("Indicador", "Respuesta"), ("Notificación recibida", a.get("notice_received") or "Pendiente"),
                ("Resolución conocida", a.get("resolution") or "Pendiente"),
                ("Cobro coactivo/embargo", a.get("coercive") or "Pendiente"),
                ("Proceso judicial", a.get("court") or "Pendiente"), ("Pago", a.get("paid") or "Pendiente"),
            ]},
            {"heading": "2. Ruta orientativa", "bullets": [
                "Sin resolución: expediente, notificación, audiencia y pruebas.",
                "Resolución identificada: revisar notificación, ejecutoria, recursos y oportunidad.",
                "Cobro coactivo o embargo: revisión profesional inmediata; no usar el flujo automático como defensa definitiva.",
                "Pago realizado: identificar acto, fundamento y ruta; no prometer devolución.",
                "Coincidencia SAST: individualizar dispositivo, período, actuación y estado firme.",
            ]},
            {"heading": "3. Próximos pasos", "bullets": [
                "Radicar por canal oficial y conservar número de radicado.",
                "Registrar cada respuesta y documento dentro del expediente.",
                "Controlar términos y solicitar asistencia si existe actuación sancionatoria avanzada.",
            ]},
        ]

    def _sast_checklist_sections(self, a: dict, result: dict) -> list[dict]:
        return [
            {"heading": "1. Coincidencia preliminar", "table": [
                ("Campo", "Información"), ("Territorio/autoridad", a.get("territory") or "Pendiente"),
                ("Fecha", a.get("event_date") or "Pendiente"), ("Placa", a.get("plate") or "Pendiente"),
                ("Coincidencias en muestra", str(len(result.get("sast_matches", [])))),
            ]},
            {"heading": "2. Validación individual obligatoria", "bullets": [
                "Número exacto de comparendo y autoridad competente.", "Dispositivo, cámara, ubicación y período de operación.",
                "Acto individual de apertura y estado actual de la actuación.", "Existencia de decisión firme de la Supertransporte.",
                "Resolución sancionatoria, ejecutoria y actuaciones posteriores del expediente individual.",
            ]},
            {"heading": "3. Advertencias", "bullets": self.DEFINITIONS["CO-TR-001"]["limitations"]},
        ]

    def _sast_alerts_sections(self, a: dict) -> list[dict]:
        return [
            {"heading": "1. Datos para seguimiento", "table": [
                ("Campo", "Información"), ("Interesado", a.get("owner_name") or "Pendiente"),
                ("Correo", a.get("email") or "Pendiente"), ("Comparendo", a.get("comparendo_number") or "Pendiente"),
                ("Autoridad", a.get("territory") or "Pendiente"), ("Consentimiento de alertas", a.get("consent_alerts") or "Pendiente"),
            ]},
            {"heading": "2. Eventos a vigilar", "bullets": [
                "Nuevos actos individuales o decisiones firmes de la Supertransporte.",
                "Cambios de estado del comparendo o del proceso contravencional.",
                "Resolución, cobro coactivo, mandamiento de pago o embargo.",
                "Actualizaciones de la matriz SAST y sus fuentes oficiales.",
            ]},
            {"heading": "3. Alcance", "text": "La inscripción no suspende términos ni sustituye la revisión del expediente individual."},
        ]

    def _sast_csv_builder(self, answers: dict):
        def build(path: Path):
            fields = ["id", "group", "territory", "department", "start", "end", "cause", "resolution", "status"]
            with path.open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                for row in self.sast_sample:
                    writer.writerow({k: row.get(k, "") for k in fields})
        return build

    def generate(self, con, case_id: str, actor_id: str) -> dict:
        case = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise ValueError("Expediente no encontrado.")
        code = case["product_code"]
        if code not in self.CODES:
            raise ValueError("La generación v2.9 solo está habilitada para la ola prioritaria.")
        if case["risk"] == "red":
            raise ValueError("El expediente está bloqueado por riesgo alto y requiere revisión profesional.")
        answers = json.loads(case["answers"])
        result = json.loads(case["result"])
        sources = self._source_rows(con, code)
        snapshot = {
            "product_code": code,
            "candidate_version": self.VERSION,
            "sources": [{k: v for k, v in x.items() if k != "file_path"} for x in sources],
            "original_binary_embedded": False,
            "original_identity_verified": False,
            "professional_use_authorized": False,
        }
        snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        snapshot_hash = sha256(snapshot_json.encode()).hexdigest()
        created = []
        if code == "CO-LA-001":
            calc = result.get("calculation") or {}
            created.append(self._insert_document(con, case, actor_id, kind="v29_labor_report", title="Informe estimativo de liquidación laboral", suffix="informe_liquidacion_v29", sections=labor_report_sections(answers, calc, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_labor_claim", title="Reclamación directa de acreencias laborales", suffix="reclamacion_laboral_v29", sections=labor_claim_sections(answers, calc), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_labor_evidence", title="Checklist probatorio y de validación", suffix="checklist_laboral_v29", sections=self._labor_evidence_sections(answers, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_labor_calculator", title="Matriz de cálculo y trazabilidad", suffix="matriz_calculo_v29", sections=[], source_hash=snapshot_hash, extension="csv", binary_builder=self._labor_csv_builder(answers, calc, result)))
        elif code == "CO-TR-002":
            created.append(self._insert_document(con, case, actor_id, kind="v29_traffic_request", title="Solicitud integral de expediente y reclamación", suffix="solicitud_integral_fotomulta_v29", sections=traffic_request_sections(answers, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_traffic_hearing", title="Solicitud de audiencia y pruebas", suffix="solicitud_audiencia_pruebas_v29", sections=self._traffic_hearing_sections(answers, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_traffic_evidence", title="Índice de evidencias y trazabilidad", suffix="indice_evidencias_fotomulta_v29", sections=self._traffic_evidence_sections(answers), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_traffic_guide", title="Guía de etapa y escalamiento", suffix="guia_etapa_fotomulta_v29", sections=self._traffic_guide_sections(answers), source_hash=snapshot_hash))
        else:
            created.append(self._insert_document(con, case, actor_id, kind="v29_sast_report", title="Informe de coincidencia preliminar SAST", suffix="informe_sast_v29", sections=sast_report_sections(answers, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_sast_checklist", title="Checklist de validación individual SAST", suffix="checklist_sast_v29", sections=self._sast_checklist_sections(answers, result), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_sast_alerts", title="Registro de alertas y seguimiento SAST", suffix="alertas_sast_v29", sections=self._sast_alerts_sections(answers), source_hash=snapshot_hash))
            created.append(self._insert_document(con, case, actor_id, kind="v29_sast_snapshot", title="Snapshot de matriz piloto SAST", suffix="snapshot_sast_v29", sections=[], source_hash=snapshot_hash, extension="csv", binary_builder=self._sast_csv_builder(answers)))
        run_id = "V29-" + uuid.uuid4().hex[:14].upper()
        now = utc_iso()
        con.execute(
            """INSERT INTO priority_generation_runs_v29(id,case_id,product_code,source_snapshot_json,
               source_snapshot_sha256,documents_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)""",
            (run_id, case_id, code, snapshot_json, snapshot_hash, json.dumps(created, ensure_ascii=False, sort_keys=True), actor_id, now),
        )
        con.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, case_id))
        con.execute(
            "INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",
            (case_id, "priority_generation_v29", f"Se generó un paquete candidato v2.9 de {len(created)} archivos para {code}. Los originales permanecen pendientes.", now),
        )
        return {
            "ok": True,
            "run_id": run_id,
            "case_id": case_id,
            "product_code": code,
            "source_snapshot_sha256": snapshot_hash,
            "documents": created,
            "status": "Borrador candidato estructurado v2.9 - no canónico",
            "professional_use_authorized": False,
            "notice": "Los archivos permiten probar el recorrido documental, pero requieren original, cotejo, aprobación jurídica y QA antes de uso profesional.",
        }
