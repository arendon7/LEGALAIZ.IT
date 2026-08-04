#!/usr/bin/env python3
from __future__ import annotations

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
from email.parser import BytesParser
from email.policy import default as email_policy
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import json
import os
import mimetypes
import re
import sys
import threading
import traceback
import unicodedata
import uuid
import webbrowser

# M6: las implementaciones versionadas se aíslan fuera de la raíz activa.
_MODULE_ROOT = Path(__file__).resolve().parent
_RUNTIME_MODULES = _MODULE_ROOT / 'legalai_runtime_modules'
if str(_RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_MODULES))

from docx_builder import build_docx
from expanded_documents import document_specs
from economic_calculation_engine import (
    accrued_effective_interest, build_payment_schedule, effective_annual_rate,
    modality_rates, reconcile_amounts,
)
from extensive_generation_v216 import append_consolidated_package, build_generation_proof, create_generation_schema
from studio_backend import LegalStudio, WORKFLOW_STATUSES
from legalai_platform.release_metadata import VERSION as RELEASE_VERSION
from legalai_platform.database import connect_database, selected_backend

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'app'
DATA = ROOT / 'data'
_runtime_setting = os.environ.get('LEGAL_RUNTIME_DIR', '').strip()
RUNTIME = Path(_runtime_setting).expanduser() if _runtime_setting else ROOT / 'runtime'
if not RUNTIME.is_absolute():
    RUNTIME = ROOT / RUNTIME
RUNTIME = RUNTIME.resolve()
GENERATED = RUNTIME / 'generated'
UPLOADS = RUNTIME / 'uploads'
DB = RUNTIME / 'legalaizit.db'
HOST = '127.0.0.1'
PORT = 8765
VERSION = RELEASE_VERSION
RISK_ORDER = {'green': 1, 'yellow': 2, 'red': 3}
RISK_LABEL = {'green': 'Verde', 'yellow': 'Amarillo', 'red': 'Rojo'}
MAX_UPLOAD = 10 * 1024 * 1024


def load_json(name, default=None):
    path = DATA / name
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding='utf-8'))


PRODUCTS = load_json('products.json', [])
INTERVIEWS = load_json('interviews.json', {})
RULES = load_json('rules.json', {})
SOURCES = load_json('sources.json', {})
PARAMETERS = load_json('parameters.json', {})
SCENARIOS = load_json('test_scenarios.json', {})
PACKAGES = load_json('legal_packages.json', [])
SAST = load_json('sast_sample.json', [])


def now():
    # Timestamps jurídicos y de auditoría se expresan en la zona operativa principal.
    return datetime.now(ZoneInfo('America/Bogota')).isoformat(timespec='seconds')


def safe_filename(name, fallback='archivo'):
    base = Path(str(name or fallback)).name
    clean = re.sub(r'[^A-Za-z0-9._-]+', '_', base).strip('._')
    return clean[:180] or fallback


def product(code):
    return next((p for p in PRODUCTS if p['code'] == code), None)


def db():
    """Abre la persistencia seleccionada por LEGAL_DATABASE_BACKEND."""
    return connect_database(DB)


def audit(con, actor, entity_type, entity_id, action, detail):
    if not isinstance(detail, str):
        detail = json.dumps(detail, ensure_ascii=False)
    con.execute(
        'INSERT INTO audit_log(actor,entity_type,entity_id,action,detail,created_at) VALUES(?,?,?,?,?,?)',
        (actor, entity_type, entity_id, action, detail, now()),
    )


def create_schema(con):
    con.executescript(
        '''
        CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT,role TEXT NOT NULL,specialty TEXT,verified INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cases(
          id TEXT PRIMARY KEY,product_code TEXT NOT NULL,title TEXT NOT NULL,risk TEXT NOT NULL,status TEXT NOT NULL,
          owner_id TEXT,specialist_id TEXT,review_status TEXT NOT NULL DEFAULT 'Pendiente',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          answers TEXT NOT NULL,result TEXT NOT NULL,FOREIGN KEY(owner_id) REFERENCES users(id),FOREIGN KEY(specialist_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL,product_code TEXT NOT NULL,kind TEXT NOT NULL,name TEXT NOT NULL,mime_type TEXT NOT NULL,
          file_path TEXT,content TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Borrador',
          FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_case_kind ON documents(case_id,kind);
        CREATE TABLE IF NOT EXISTS document_versions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,version TEXT NOT NULL,created_at TEXT NOT NULL,note TEXT,file_path TEXT,
          FOREIGN KEY(document_id) REFERENCES documents(id)
        );
        CREATE TABLE IF NOT EXISTS reviews(
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL,specialist_id TEXT,action TEXT NOT NULL,comment TEXT,created_at TEXT NOT NULL,
          FOREIGN KEY(case_id) REFERENCES cases(id),FOREIGN KEY(specialist_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS activity(
          id INTEGER PRIMARY KEY AUTOINCREMENT,case_id TEXT,kind TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,entity_type TEXT,entity_id TEXT,action TEXT,detail TEXT,created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attachments(
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL,name TEXT NOT NULL,mime_type TEXT,size_bytes INTEGER NOT NULL,
          category TEXT,file_path TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS case_tasks(
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL,label TEXT NOT NULL,status TEXT NOT NULL,owner_role TEXT NOT NULL,position INTEGER NOT NULL,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        '''
    )
    STUDIO.create_schema(con)
    create_generation_schema(con)


def init_db(reset=False, seed_demo_data=True):
    RUNTIME.mkdir(exist_ok=True)
    GENERATED.mkdir(exist_ok=True)
    UPLOADS.mkdir(exist_ok=True)
    backend = selected_backend()
    if reset and backend == "sqlite" and DB.exists():
        DB.unlink()
    elif reset and backend == "postgresql":
        raise RuntimeError("El reinicio destructivo de PostgreSQL no está permitido desde init_db(). Use el runbook M31.5.")
    con = db()
    create_schema(con)
    users = [
        ('USR-CLIENT', 'Juan Pérez', 'juan@demo.legalaiz.it', 'client', 'Cliente verificado', 1),
        ('USR-LAB', 'María Fernández', 'maria@demo.legalaiz.it', 'specialist', 'Derecho laboral', 1),
        ('USR-COMM', 'Carlos López', 'carlos@demo.legalaiz.it', 'specialist', 'Comercial, contratos y datos', 1),
        ('USR-TRANSIT', 'Laura Gómez', 'laura@demo.legalaiz.it', 'specialist', 'Tránsito y administrativo', 1),
        ('USR-ADMIN', 'Ana Torres', 'ana@demo.legalaiz.it', 'admin', 'Gobernanza jurídica y producto', 1),
    ]
    con.executemany('INSERT INTO users(id,name,email,role,specialty,verified) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING', users)
    STUDIO.init_baselines(con)
    STUDIO.load_active(con)
    con.commit()
    empty = con.execute('SELECT COUNT(*) FROM cases').fetchone()[0] == 0
    con.close()
    if empty and seed_demo_data:
        seed_demo()


def seed_demo():
    demos = [
        (
            'CO-EM-003',
            {
                'party_a': 'Acme S.A.S.', 'party_a_id': '901000111-2', 'party_b': 'Consultor Demo', 'party_b_id': '100000001',
                'contract_city': 'Medellín', 'contact_email_a': 'legal@acme.demo', 'contact_email_b': 'consultor@demo.co',
                'state_entity': 'No', 'regulated_service': 'No', 'object_clear': 'Sí', 'fixed_schedule': 'No',
                'permanent_orders': 'No', 'disciplinary_control': 'No', 'continuous_availability': 'No', 'exclusive': 'No',
                'personal_data': 'Sí', 'confidentiality': 'Sí', 'ip_relevant': 'Sí', 'object': 'Diseñar e implementar un prototipo de automatización documental.',
                'deliverables': 'Mapa funcional, prototipo navegable, documentación técnica y entrega de código.', 'fees': '45000000',
                'start_date': '2026-07-20', 'end_date': '2026-10-20', 'payment_scheme': 'Anticipo e hitos', 'acceptance_days': '5',
                'subcontractors': 'No', 'early_termination': 'Sí',
            },
            'Prestación de servicios para prototipo legal',
        ),
        (
            'CO-LA-001',
            {
                'worker_name': 'Juan Pérez', 'worker_id': '100000002', 'employer_name': 'Empresa Demo S.A.S.', 'employer_id': '901000222-3',
                'claim_email': 'juan@demo.legalaiz.it', 'private_relation': 'Sí', 'start_date': '2025-01-01', 'end_date': '2026-06-30',
                'contract_type': 'Indefinido', 'termination': 'Sin justa causa', 'monthly_salary': '3000000', 'salary_due_days': '15',
                'integral_salary': 'No', 'transport_aid': 'No', 'variable_salary': 'No',
                'cesantias_start_date': '2026-01-01', 'prima_start_date': '2026-01-01', 'vacation_pending_days': '7.5',
                'periods_confirmed': 'Sí', 'prior_salary_paid': '0', 'prior_cesantias_paid': '0',
                'prior_interest_paid': '0', 'prior_prima_paid': '0', 'prior_vacation_paid': '0',
                'prior_indemnity_paid': '0', 'disputed_deductions': 'No', 'salary_supports': 'Sí',
                'special_protection': 'No', 'public_sector': 'No', 'active_litigation': 'No',
                'contract_reality': 'No', 'collective_regime': 'No', 'data_confirmed': 'Sí', 'generate_settlement': 'Sí',
            },
            'Liquidación laboral estimativa',
        ),
        (
            'CO-TR-001',
            {
                'requester_name': 'Juan Pérez', 'requester_id': '100000002', 'email': 'juan@demo.legalaiz.it',
                'phone': '3000000000', 'address': 'Medellín', 'acting_capacity': 'Propietario',
                'plate': 'ABC123', 'comparendo_number': '0500100000001', 'authority': 'Secretaría de Movilidad de Medellín',
                'territory': 'Medellín', 'department': 'Antioquia', 'event_date': '2019-06-15', 'event_time': '10:30',
                'event_location': 'Punto por verificar', 'conduct_code': 'Exceso de velocidad', 'device_known': 'Sí',
                'device_id': 'SAST-MDE-001', 'exact_point_match': 'Sí', 'official_2026_match': 'Sí',
                'official_act_number': '7091', 'official_act_status': 'Apertura o formulación de cargos',
                'official_act_source': 'SuperTransporte', 'ansv_authorization': 'Sí', 'authorization_number': 'ANSV-DEMO-001',
                'authorization_issue_date': '2018-01-01', 'authorization_expiry_date': '2023-01-01',
                'calibration_traceability': 'Sí', 'calibration_date': '2019-05-20', 'signage_verified': 'Sí',
                'performance_concept': 'No existe soporte', 'notice_status': 'Consulta SIMIT/RUNT',
                'first_knowledge_date': '2026-05-20', 'enforcement': 'Comparendo sin decisión conocida', 'paid': 'No',
                'case_count': '1', 'evidence_available': 'Comparendo y consultas oficiales', 'deadline_urgent': 'No',
                'identity_fraud': 'No', 'consent_alerts': 'Sí', 'data_confirmed': 'Sí',
            },
            'Chequeo SAST Medellín',
        ),
    ]
    for code, answers, title in demos:
        try:
            create_case(code, answers, title=title, owner='USR-CLIENT', seed=True)
        except Exception:
            traceback.print_exc()


def compare(actual, op, expected=None):
    if op == 'equals': return actual == expected
    if op == 'not_equals': return actual != expected
    if op == 'in': return actual in (expected or [])
    if op == 'not_in': return actual not in (expected or [])
    if op in ('gt', 'gte', 'lt', 'lte'):
        try:
            a = float(actual); e = float(expected)
        except (TypeError, ValueError):
            return False
        return {'gt': a > e, 'gte': a >= e, 'lt': a < e, 'lte': a <= e}[op]
    if op == 'truthy': return bool(actual)
    if op == 'falsy': return not bool(actual)
    if op == 'missing': return actual in (None, '', [], {})
    if op == 'not_missing': return actual not in (None, '', [], {})
    if op == 'contains':
        try: return expected in actual
        except TypeError: return False
    if op in ('date_before', 'date_after'):
        try:
            a = date.fromisoformat(str(actual)); e = date.fromisoformat(str(expected))
        except Exception:
            return False
        return a < e if op == 'date_before' else a > e
    return False


def visible(question, answers):
    cond = question.get('show_if')
    if not cond:
        return True
    return compare(answers.get(cond.get('field')), 'equals', cond.get('equals'))


def validate_answers(code, answers):
    errors = []
    spec = INTERVIEWS.get(code, {})
    for q in spec.get('questions', []):
        if not visible(q, answers):
            continue
        val = answers.get(q['id'])
        if q.get('required') and val in (None, '', []):
            errors.append({'field': q['id'], 'message': f"{q['label']}: campo obligatorio."})
        if val not in (None, '') and q.get('min_length') and len(str(val).strip()) < q['min_length']:
            errors.append({'field': q['id'], 'message': f"{q['label']}: mínimo {q['min_length']} caracteres."})
        if val not in (None, '') and q.get('max_length') and len(str(val).strip()) > q['max_length']:
            errors.append({'field': q['id'], 'message': f"{q['label']}: máximo {q['max_length']} caracteres."})
        if val not in (None, '') and q.get('format') == 'email':
            email = str(val).strip()
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                errors.append({'field': q['id'], 'message': f"{q['label']}: escribe un correo electrónico válido."})
        if val not in (None, '') and q.get('min') is not None:
            try:
                if float(val) < float(q['min']):
                    errors.append({'field': q['id'], 'message': f"{q['label']}: valor mínimo {q['min']}."})
            except Exception:
                errors.append({'field': q['id'], 'message': f"{q['label']}: número inválido."})
        if val not in (None, '') and q.get('max') is not None:
            try:
                if float(val) > float(q['max']):
                    errors.append({'field': q['id'], 'message': f"{q['label']}: valor máximo {q['max']}."})
            except Exception:
                if not any(x['field'] == q['id'] for x in errors):
                    errors.append({'field': q['id'], 'message': f"{q['label']}: número inválido."})
        if val not in (None, '') and q.get('after_field'):
            other = answers.get(q['after_field'])
            if other not in (None, ''):
                try:
                    if date.fromisoformat(str(val)) <= date.fromisoformat(str(other)):
                        errors.append({'field': q['id'], 'message': f"{q['label']}: debe ser posterior a la fecha de inicio."})
                except Exception:
                    errors.append({'field': q['id'], 'message': f"{q['label']}: fecha inválida."})
    return errors


def eval_conditions(node, answers):
    if not node:
        return False
    if 'all' in node:
        return all(
            eval_conditions(x, answers) if isinstance(x, dict) and ('all' in x or 'any' in x)
            else compare(answers.get(x.get('field')), x.get('op'), x.get('value'))
            for x in node['all']
        )
    if 'any' in node:
        return any(
            eval_conditions(x, answers) if isinstance(x, dict) and ('all' in x or 'any' in x)
            else compare(answers.get(x.get('field')), x.get('op'), x.get('value'))
            for x in node['any']
        )
    return compare(answers.get(node.get('field')), node.get('op'), node.get('value'))


def _money(value):
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _commercial_days(start, end, inclusive=True):
    """Convención laboral 30/360 con día final incluido."""
    if not start or not end or end < start:
        return 0
    d1 = min(start.day, 30)
    d2 = min(end.day, 30)
    days = (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)
    return max(days + (1 if inclusive else 0), 0)


def _calendar_year_segments(start, end):
    cursor = start
    while cursor <= end:
        segment_end = min(end, date(cursor.year, 12, 30))
        yield cursor, segment_end
        cursor = date(cursor.year + 1, 1, 1)


def labor_calc(a):
    """Liquidación laboral M16 por concepto, período, base y pago previo.

    El motor produce una estimación determinística y trazable. Separa las
    bases de cesantías, prima, vacaciones e indemnización; segmenta
    anualidades y semestres; y excluye sanciones o pretensiones litigiosas.
    """
    issues = []
    assumptions = []
    exclusions = [
        'Indemnización moratoria del artículo 65 CST: requiere valoración judicial de conducta y buena fe.',
        'Sanción por no consignar cesantías: requiere anualidad, mora, prescripción, conducta y prueba.',
        'Horas extra, recargos, comisiones o factores salariales sin soportes suficientes.',
        'Estabilidad laboral reforzada, fueros, discriminación, accidente o enfermedad laboral.',
        'Indexación, perjuicios, intereses judiciales, costas y agencias en derecho.',
        'Descuentos discutidos: no se restan sin autorización válida o mandamiento judicial.',
        'Aportes omitidos: se corrigen en seguridad social y no siempre constituyen pago directo al trabajador.',
    ]
    try:
        start = date.fromisoformat(str(a.get('start_date')))
        end = date.fromisoformat(str(a.get('end_date')))
        ces_start = date.fromisoformat(str(a.get('cesantias_start_date') or a.get('start_date')))
        prima_start = date.fromisoformat(str(a.get('prima_start_date') or a.get('start_date')))
    except Exception:
        return None
    if end < start:
        return None
    if ces_start < start:
        issues.append({'id':'LA1-M16-01','risk':'yellow','message':'La fecha inicial de cesantías precede el vínculo; se ajustó al ingreso.'})
        ces_start = start
    if prima_start < start:
        issues.append({'id':'LA1-M16-02','risk':'yellow','message':'La fecha inicial de prima precede el vínculo; se ajustó al ingreso.'})
        prima_start = start
    if ces_start > end:
        issues.append({'id':'LA1-M16-03','risk':'red','message':'La fecha inicial de cesantías es posterior al corte.'})
    if prima_start > end:
        issues.append({'id':'LA1-M16-04','risk':'red','message':'La fecha inicial de prima es posterior al corte.'})

    prm = PARAMETERS.get('CO-LA-001', {})
    fixed_salary = _money(a.get('monthly_salary'))
    general_variable = _money(a.get('variable_average')) if a.get('variable_salary') == 'Sí' else 0.0
    salary = fixed_salary + general_variable
    if salary <= 0:
        issues.append({'id':'LA1-M16-05','risk':'red','message':'El salario base no permite calcular la liquidación.'})

    smmlv = float(prm.get('smmlv', 0))
    aux = float(prm.get('transport_aid', 0))
    threshold = float(prm.get('transport_threshold_smmlv', 2))
    aux_requested = a.get('transport_aid') == 'Sí'
    aux_ok = aux_requested and salary <= smmlv * threshold
    if aux_requested and not aux_ok:
        issues.append({'id':'LA1-M16-06','risk':'yellow','message':'El salario informado supera el umbral configurado; no se aplicó auxilio de transporte.'})
    if a.get('transport_aid') == 'No sé':
        assumptions.append('No se aplicó auxilio de transporte porque el derecho no fue confirmado.')

    is_integral = a.get('integral_salary') == 'Sí'
    if is_integral and salary < 13 * smmlv:
        issues.append({'id':'LA1-M16-07','risk':'red','message':'El salario integral informado está por debajo del mínimo legal de referencia (10 SMLMV más factor prestacional mínimo). Debe revisarse su validez.'})
    if is_integral:
        assumptions.append('Se informó salario integral; prima, cesantías e intereses se excluyeron del cálculo automático, salvo controversia sobre su validez.')

    ces_variable = _money(a.get('cesantias_variable_average')) if a.get('cesantias_variable_average') not in (None, '') else general_variable
    prima_variable = _money(a.get('prima_variable_average')) if a.get('prima_variable_average') not in (None, '') else general_variable
    vacation_variable = _money(a.get('vacation_variable_average')) if a.get('vacation_variable_average') not in (None, '') else general_variable
    indemnity_base = _money(a.get('indemnity_salary_base')) or salary
    ces_base = fixed_salary + ces_variable + (aux if aux_ok else 0)
    prima_base = fixed_salary + prima_variable + (aux if aux_ok else 0)
    vacation_base = fixed_salary + vacation_variable

    link_days = _commercial_days(start, end)
    ces_days = _commercial_days(ces_start, end) if ces_start <= end else 0
    prima_days = _commercial_days(prima_start, end) if prima_start <= end else 0
    salary_due_days = _money(a.get('salary_due_days'))
    accrued_vacation_days = round(link_days * float(prm.get('vacation_days_per_year', 15)) / 360, 4)
    vacation_pending_days = _money(a.get('vacation_pending_days')) if a.get('vacation_pending_days') not in (None, '') else accrued_vacation_days
    if vacation_pending_days > accrued_vacation_days + 0.01:
        issues.append({'id':'LA1-M16-08','risk':'red','message':f'Los {vacation_pending_days:g} días de vacaciones pendientes superan los {accrued_vacation_days:g} días causados según el vínculo informado.'})

    def semester_segments(seg_start, seg_end):
        cursor = seg_start
        while cursor <= seg_end:
            half_end = date(cursor.year, 6, 30) if cursor.month <= 6 else date(cursor.year, 12, 30)
            segment_end = min(seg_end, half_end)
            yield cursor, segment_end
            cursor = date(cursor.year, 7, 1) if cursor.month <= 6 else date(cursor.year + 1, 1, 1)

    gross = {}
    gross['salario_pendiente'] = salary / 30 * salary_due_days
    gross['cesantias'] = 0.0 if is_integral else ces_base * ces_days / 360
    interest_total = 0.0
    interest_segments = []
    cesantias_segments = []
    if ces_days and not is_integral:
        for seg_start, seg_end in _calendar_year_segments(ces_start, end):
            seg_days = _commercial_days(seg_start, seg_end)
            seg_ces = ces_base * seg_days / 360
            seg_interest = seg_ces * float(prm.get('interest_cesantias', 0.12)) * seg_days / 360
            interest_total += seg_interest
            cesantias_segments.append({'year':seg_start.year,'start':seg_start.isoformat(),'end':seg_end.isoformat(),'days':seg_days,'base':round(ces_base,2),'cesantias':round(seg_ces,2)})
            interest_segments.append({'year':seg_start.year,'start':seg_start.isoformat(),'end':seg_end.isoformat(),'days':seg_days,'cesantias_base':round(seg_ces,2),'interest':round(seg_interest,2)})
    gross['intereses_cesantias'] = interest_total

    prima_segments = []
    prima_total = 0.0
    if prima_days and not is_integral:
        for seg_start, seg_end in semester_segments(prima_start, end):
            seg_days = _commercial_days(seg_start, seg_end)
            seg_value = prima_base * seg_days / 360
            prima_total += seg_value
            prima_segments.append({'year':seg_start.year,'semester':1 if seg_start.month <= 6 else 2,'start':seg_start.isoformat(),'end':seg_end.isoformat(),'days':seg_days,'base':round(prima_base,2),'prima':round(seg_value,2)})
    gross['prima'] = prima_total
    gross['vacaciones'] = vacation_base / 30 * vacation_pending_days

    indemn_days = 0.0
    indemn_formula = 'No aplica según la causa informada.'
    if a.get('termination') == 'Sin justa causa':
        if a.get('protected_status') in ('Sí','No sé'):
            issues.append({'id':'LA1-M16-09','risk':'red','message':'Existe o puede existir protección reforzada; la indemnización estándar no resuelve reintegro, autorización ni efectos constitucionales.'})
        ctype = a.get('contract_type')
        if ctype == 'Indefinido':
            excess_days = max(link_days - 360, 0)
            if indemnity_base < 10 * smmlv:
                indemn_days = 30 + (excess_days * 20 / 360)
                indemn_formula = '30 días por el primer año y 20 proporcionales por tiempo adicional (salario inferior a 10 SMLMV).'
            else:
                indemn_days = 20 + (excess_days * 15 / 360)
                indemn_formula = '20 días por el primer año y 15 proporcionales por tiempo adicional (salario igual o superior a 10 SMLMV).'
        elif ctype == 'Término fijo':
            try:
                fixed_end = date.fromisoformat(str(a.get('fixed_term_end')))
                if fixed_end <= end:
                    issues.append({'id':'LA1-M16-10','risk':'red','message':'La fecha final pactada no es posterior a la terminación informada.'})
                else:
                    indemn_days = (fixed_end - end).days
                    indemn_formula = 'Salarios correspondientes al tiempo faltante del término pactado.'
            except Exception:
                issues.append({'id':'LA1-M16-11','risk':'red','message':'No existe fecha final válida para el contrato a término fijo.'})
        elif ctype == 'Obra o labor':
            remaining = _money(a.get('work_remaining_days'))
            if remaining <= 0:
                issues.append({'id':'LA1-M16-12','risk':'red','message':'No se informó duración restante verificable de la obra o labor.'})
            else:
                indemn_days = max(remaining, 15)
                indemn_formula = 'Tiempo estimado restante de la obra o labor, con mínimo legal de 15 días.'
        else:
            issues.append({'id':'LA1-M16-13','risk':'yellow','message':'La modalidad no permite estimar automáticamente la indemnización.'})
    gross['indemnizacion_estandar'] = indemnity_base / 30 * indemn_days

    payment_fields = {
        'salario_pendiente':'prior_salary_paid',
        'cesantias':'prior_cesantias_paid',
        'intereses_cesantias':'prior_interest_paid',
        'prima':'prior_prima_paid',
        'vacaciones':'prior_vacation_paid',
        'indemnizacion_estandar':'prior_indemnity_paid',
    }
    source_map = {
        'salario_pendiente':['LA1-S1'],
        'cesantias':['LA1-S1','LA1-S2'],
        'intereses_cesantias':['LA1-S3'],
        'prima':['LA1-S1'],
        'vacaciones':['LA1-S1'],
        'indemnizacion_estandar':['LA1-S1','LA1-S4'],
    }
    formula_map = {
        'salario_pendiente':'salario mensual ÷ 30 × días pendientes',
        'cesantias':'base de cesantías × días pendientes ÷ 360',
        'intereses_cesantias':'cesantías del segmento × 12% × días del segmento ÷ 360',
        'prima':'base de prima × días de cada semestre ÷ 360',
        'vacaciones':'base de vacaciones ÷ 30 × días pendientes confirmados',
        'indemnizacion_estandar':indemn_formula,
    }
    labels = {
        'salario_pendiente':'Salario ordinario pendiente','cesantias':'Cesantías',
        'intereses_cesantias':'Intereses a las cesantías','prima':'Prima de servicios',
        'vacaciones':'Vacaciones compensables','indemnizacion_estandar':'Indemnización estándar por terminación',
    }
    line_items=[]
    for key in payment_fields:
        prior = _money(a.get(payment_fields[key]))
        value = max(gross[key], 0.0)
        if prior > value + 0.01:
            issues.append({'id':f'LA1-M16-PAY-{key}','risk':'yellow','message':f'El pago previo para {labels[key].lower()} supera el valor bruto; el saldo se llevó a cero y debe conciliarse.'})
        net=max(value-prior,0.0)
        line_items.append({'key':key,'label':labels[key],'gross':round(value,2),'prior_paid':round(prior,2),'net':round(net,2),'formula':formula_map[key],'source_ids':source_map[key]})
    subtotal=sum(x['gross'] for x in line_items)
    prior_total=sum(x['prior_paid'] for x in line_items)
    total=sum(x['net'] for x in line_items)
    if a.get('disputed_deductions') in ('Sí','No sé'):
        assumptions.append('Los descuentos discutidos no se restaron del total estimado.')
    if a.get('periods_confirmed') != 'Sí':
        assumptions.append('Los cortes por concepto requieren conciliación con soportes antes de tratarlos como definitivos.')
    if a.get('cesantias_regime') in ('Tradicional','No sé'):
        issues.append({'id':'LA1-M16-14','risk':'red','message':'El régimen de cesantías informado requiere análisis especial; el cálculo mostrado usa el régimen anualizado.'})

    return {
        'engine_version':'M16.1','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'periods':{
            'employment':{'start':start.isoformat(),'end':end.isoformat(),'days_30_360':link_days},
            'cesantias':{'start':ces_start.isoformat(),'end':end.isoformat(),'days_30_360':ces_days},
            'prima':{'start':prima_start.isoformat(),'end':end.isoformat(),'days_30_360':prima_days},
            'vacaciones':{'pending_days':round(vacation_pending_days,4),'accrued_ceiling_days':accrued_vacation_days},
        },
        'days':link_days,'salary':round(salary,2),'fixed_salary':round(fixed_salary,2),'variable_average':round(general_variable,2),
        'bases':{'salary':round(salary,2),'cesantias':round(ces_base,2),'prima':round(prima_base,2),'vacaciones':round(vacation_base,2),'indemnizacion':round(indemnity_base,2)},
        'integral_salary_applied':is_integral,'transport_aid_applied':aux_ok,'transport_aid_value':round(aux if aux_ok else 0,2),
        'base_prestacional':round(ces_base,2),'salary_due_days':round(salary_due_days,4),'benefit_days':ces_days,
        'vacation_days':round(vacation_pending_days,4),'indemnizacion_dias':round(indemn_days,4),
        'cesantias_segments':cesantias_segments,'interest_segments':interest_segments,'prima_segments':prima_segments,'line_items':line_items,
        **{x['key']:x['gross'] for x in line_items},
        'subtotal_matematico':round(subtotal,2),'pagos_previos_confirmados':round(prior_total,2),'total_estimado':round(total,2),
        'prescription':{'general_years':int(prm.get('prescription_years',3)),'written_claim_interrupts_once':bool(prm.get('written_claim_interrupts_once',True)),'control_by_concept':True},
        'issues':issues,'assumptions':assumptions,'exclusions':exclusions,
        'warning':'Estimación matemática por concepto y período. No incorpora sanciones, reintegros ni partidas que dependan de prueba o valoración jurídica.',
    }

def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode('ascii').lower()
    value = re.sub(r'[^a-z0-9 ]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def sast_matches(a):
    query = normalize(a.get('territory') or a.get('authority'))
    dt = str(a.get('event_date') or '')
    if not query or not dt:
        return []
    matches = []
    for row in SAST:
        territory = normalize(row.get('territory'))
        authority = normalize(row.get('authority'))
        place_match = query == territory or query in authority or territory in query
        if place_match and row.get('start', '') <= dt <= row.get('end', ''):
            matches.append(row)
    return matches


STUDIO = LegalStudio(PRODUCTS, INTERVIEWS, RULES, SOURCES, SCENARIOS, PACKAGES, RISK_ORDER, eval_conditions, sast_matches)


def lease_calc(a):
    """Control económico y documental CO-AR-001 revalidado en M11."""
    prm = PARAMETERS.get('CO-AR-001', {})
    rent = _money(a.get('rent'))
    commercial_known = a.get('commercial_value_known') == 'Sí'
    commercial = _money(a.get('commercial_value')) if commercial_known else 0.0
    cadastral = _money(a.get('cadastral_value'))
    issues = []
    assumptions = []
    if rent <= 0:
        issues.append({'id':'AR-CALC-01','risk':'red','message':'El canon debe ser mayor que cero.'})
    effective_commercial = commercial
    if commercial_known and commercial <= 0:
        issues.append({'id':'AR-CALC-02','risk':'red','message':'El valor comercial informado no es válido para controlar el canon.'})
    if not commercial_known:
        assumptions.append('El límite del canon no pudo verificarse por falta de soporte del valor comercial.')
    if commercial and cadastral:
        cadastral_cap = cadastral * float(prm.get('max_commercial_value_vs_cadastral', 2.0))
        if commercial > cadastral_cap:
            issues.append({'id':'AR-CALC-03','risk':'yellow','message':'El valor comercial informado supera dos veces el avalúo catastral; para el control se usó ese límite.'})
            effective_commercial = cadastral_cap
    max_ratio = float(prm.get('max_rent_ratio_commercial_value', 0.01))
    max_rent = effective_commercial * max_ratio if effective_commercial else None
    if max_rent is not None and rent > max_rent + 0.01:
        issues.append({'id':'AR-CALC-04','risk':'red','message':f'El canon informado excede el límite calculado de ${max_rent:,.0f}.'})
    ipc = float(prm.get('ipc_previous_calendar_year', 0.0))
    return {
        'engine_version':'M11.1','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'rent':round(rent,2),
        'commercial_value_reported':round(commercial,2) if commercial else None,
        'cadastral_value_reported':round(cadastral,2) if cadastral else None,
        'effective_commercial_value':round(effective_commercial,2) if effective_commercial else None,
        'maximum_legal_rent':round(max_rent,2) if max_rent is not None else None,
        'rent_ratio':round(rent/effective_commercial,6) if effective_commercial else None,
        'ipc_previous_calendar_year':ipc,
        'illustrative_max_rent_after_annual_adjustment':round(rent*(1+ipc),2) if rent else None,
        'adjustment_wait_months':int(prm.get('annual_adjustment_wait_months',12)),
        'issues':issues,
        'assumptions':assumptions,
        'controls':['canon <= 1% del valor comercial controlado','valor comercial <= 2x avalúo catastral para este cálculo','reajuste solo después de 12 meses y hasta IPC anterior','servicios adicionales <= 50% del canon','copia escrita dentro de 10 días','prohibición de depósito en dinero o caución real a favor del arrendador','terminación sujeta a causal, preaviso, indemnización, caución y notificación aplicables'],
        'documentary_controls':{
            'additional_services_max_ratio':float(prm.get('max_additional_services_ratio_rent',0.5)),
            'contract_copy_deadline_days':int(prm.get('contract_copy_deadline_days',10)),
            'termination_notice_months':int(prm.get('termination_notice_months',3)),
            'cash_deposit_prohibited':bool(prm.get('cash_deposit_prohibited',True)),
            'next_revalidation':prm.get('next_revalidation'),
        },
    }

def employment_contract_calc(a):
    """Validación determinística del contrato de trabajo CO-LA-002, revalidada en M10."""
    prm = PARAMETERS.get('CO-LA-002', {})
    issues, assumptions = [], []
    need = a.get('need_type') or 'Permanente'
    modality = {'Permanente':'indefinido','Temporal con fecha cierta':'fijo','Obra o labor específica':'obra'}.get(need,'indefinido')
    weekly = _money(a.get('weekly_hours'))
    daily = _money(a.get('max_daily_hours'))
    overtime_daily = _money(a.get('planned_overtime_daily'))
    overtime_weekly = _money(a.get('planned_overtime_weekly'))
    salary = _money(a.get('monthly_salary'))
    smmlv = float(prm.get('smmlv', 0) or 0)
    required_ordinary = round(smmlv * min(weekly / float(prm.get('maximum_weekly_hours', 42) or 42), 1.0), 2) if weekly and smmlv else smmlv
    fixed_months = None
    accumulated_fixed_months = None
    try:
        start = date.fromisoformat(str(a.get('start_date')))
    except Exception:
        start = None
    if modality == 'fijo':
        try:
            end = date.fromisoformat(str(a.get('end_date')))
        except Exception:
            end = None
        if not start or not end or end <= start:
            issues.append({'id':'LA2-CALC-01','risk':'red','message':'El contrato a término fijo requiere fechas válidas y una terminación posterior al inicio.'})
        else:
            fixed_months = round((end-start).days / 30.4375, 2)
            accumulated_fixed_months = round(fixed_months + _money(a.get('prior_fixed_term_months')), 2)
            if accumulated_fixed_months > float(prm.get('fixed_term_max_months',48)) + 0.01:
                issues.append({'id':'LA2-CALC-02','risk':'red','message':f'La duración fija acumulada ({accumulated_fixed_months:.1f} meses) supera el máximo parametrizado de cuatro años.'})
    if modality == 'obra':
        if len(str(a.get('work_description') or '').strip()) < 40:
            issues.append({'id':'LA2-CALC-03','risk':'red','message':'La obra o labor no está descrita de forma precisa y detallada.'})
        if len(str(a.get('completion_milestone') or '').strip()) < 20:
            issues.append({'id':'LA2-CALC-04','risk':'red','message':'El hito de terminación de la obra o labor no es objetivo ni verificable.'})
    if weekly > float(prm.get('maximum_weekly_hours',42)):
        issues.append({'id':'LA2-CALC-05','risk':'red','message':'La jornada semanal supera el máximo legal parametrizado de 42 horas.'})
    if daily > float(prm.get('maximum_daily_flexible_hours',9)):
        issues.append({'id':'LA2-CALC-06','risk':'red','message':'La jornada ordinaria diaria supera el máximo flexible parametrizado de nueve horas.'})
    if overtime_daily > float(prm.get('maximum_overtime_daily',2)) or overtime_weekly > float(prm.get('maximum_overtime_weekly',12)):
        issues.append({'id':'LA2-CALC-07','risk':'red','message':'La planeación de horas extra supera los máximos diarios o semanales parametrizados.'})
    probation = a.get('probation') == 'Sí'
    probation_months = _money(a.get('probation_months')) if probation else 0
    if probation and probation_months > float(prm.get('probation_max_months',2)):
        issues.append({'id':'LA2-CALC-08','risk':'red','message':'El período de prueba supera dos meses.'})
    if probation and modality == 'fijo' and fixed_months and fixed_months < 12 and probation_months > fixed_months / 5 + 0.01:
        issues.append({'id':'LA2-CALC-09','risk':'red','message':'En un contrato fijo inferior a un año, el período de prueba supera la quinta parte del término inicial.'})
    salary_type = a.get('salary_type') or 'Ordinario'
    integral_minimum = smmlv * float(prm.get('integral_salary_minimum_smmlv',13))
    if salary_type == 'Integral':
        if salary < integral_minimum:
            issues.append({'id':'LA2-CALC-10','risk':'red','message':f'El salario integral informado es inferior al mínimo parametrizado de ${integral_minimum:,.0f}.'})
    elif salary < required_ordinary:
        issues.append({'id':'LA2-CALC-11','risk':'red','message':f'El salario ordinario informado es inferior al mínimo proporcional estimado de ${required_ordinary:,.0f}.'})
    if a.get('variable_payments') == 'Sí' and a.get('variable_formula_clear') in (None,'','No','En construcción'):
        issues.append({'id':'LA2-CALC-12','risk':'yellow','message':'La compensación variable aún no tiene fórmula completa y verificable.'})
    if a.get('special_protection') == 'Sí' and a.get('reasonable_adjustments') in (None,'','No','En proceso'):
        issues.append({'id':'LA2-CALC-13','risk':'yellow','message':'Los ajustes razonables y medidas de inclusión no están cerrados.'})
    if a.get('remote') == 'Trabajo remoto integral' and a.get('remote_compliance_ready') in (None,'','No','En proceso'):
        issues.append({'id':'LA2-CALC-14','risk':'yellow','message':'La implementación de trabajo remoto integral no tiene cerrados ARL, SG-SST, equipos, desconexión y lugar autorizado.'})
    return {
        'engine_version':'M10.1','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'selected_modality':modality,'fixed_term_months':fixed_months,'accumulated_fixed_term_months':accumulated_fixed_months,
        'weekly_hours':weekly,'maximum_weekly_hours':prm.get('maximum_weekly_hours',42),'max_daily_hours':daily,
        'planned_overtime_daily':overtime_daily,'planned_overtime_weekly':overtime_weekly,
        'salary_type':salary_type,'monthly_salary':round(salary,2),'smmlv':smmlv,
        'minimum_ordinary_salary_estimate':required_ordinary,'minimum_integral_salary':round(integral_minimum,2),
        'transport_aid_reference':prm.get('transport_aid'),'night_start_hour':prm.get('night_start_hour',19),
        'rest_day_surcharge_percent':prm.get('rest_day_surcharge_percent',90),
        'rest_day_surcharge_full_percent':prm.get('rest_day_surcharge_full_percent',100),
        'rest_day_surcharge_next_effective':prm.get('rest_day_surcharge_next_effective','2027-07-01'),
        'disciplinary_defense_min_days':prm.get('disciplinary_defense_min_days',5),
        'employee_resignation_pre_notice_days':prm.get('employee_resignation_pre_notice_days',30),
        'employee_resignation_pre_notice_penalty':prm.get('employee_resignation_pre_notice_penalty',False),
        'issues':issues,'assumptions':assumptions,
        'controls':['modalidad según necesidad real','término fijo acumulado <= 48 meses','obra/labor precisa y verificable','jornada <= 42 horas semanales','horas extra <= 2 diarias y 12 semanales','recargo en descanso obligatorio vigente','debido proceso disciplinario con defensa mínima','prueba escrita dentro de límites','salario mínimo ordinario o integral','protección especial sin discriminación'],
    }


def _weekdays_after(start, end):
    """Días lunes-viernes posteriores a start y hasta end, sin festivos."""
    if not start or not end or end < start:
        return 0
    from datetime import timedelta
    cur=start+timedelta(days=1); total=0
    while cur <= end:
        if cur.weekday() < 5: total += 1
        cur += timedelta(days=1)
    return total


def traffic_calc(a):
    """Control cronológico, técnico y de imputación CO-TR-002 v2.25.

    Los conteos son preliminares: excluyen fines de semana, pero no festivos.
    No declaran nulidad, caducidad, revocatoria ni pérdida automática de competencia.
    """
    prm=PARAMETERS.get('CO-TR-002',{})
    issues=[]; assumptions=[]
    def dt(k):
        v=a.get(k)
        if not v: return None
        try: return date.fromisoformat(str(v))
        except Exception: return None
    event=dt('event_date'); validation=dt('validation_date'); sent=dt('sent_date'); delivery=dt('delivery_date'); knowledge=dt('first_knowledge_date')
    chronology=[('hecho',event),('validación',validation),('envío',sent),('entrega',delivery)]
    known=[x for x in chronology if x[1]]
    for (n1,d1),(n2,d2) in zip(known,known[1:]):
        if d2 < d1:
            issues.append({'id':'TR2-CALC-01','risk':'red','message':f'La cronología es imposible: {n2} ({d2}) precede a {n1} ({d1}).'})
            break
    if knowledge and event and knowledge < event:
        issues.append({'id':'TR2-CALC-02','risk':'red','message':'La fecha de conocimiento efectivo precede a la presunta infracción.'})
    event_to_validation=_weekdays_after(event,validation) if event and validation else None
    validation_to_sent=_weekdays_after(validation,sent) if validation and sent else None
    if validation_to_sent is not None and validation_to_sent > int(prm.get('send_after_validation_business_days',3)):
        issues.append({'id':'TR2-CALC-03','risk':'yellow','message':f'El envío aparece {validation_to_sent} días hábiles preliminares después de la validación; debe cotejarse el expediente y los festivos.'})
    if event_to_validation is not None and event_to_validation > int(prm.get('preliminary_validation_control_business_days',10)):
        issues.append({'id':'TR2-CALC-04','risk':'yellow','message':f'La validación aparece {event_to_validation} días hábiles preliminares después del hecho; este control no produce invalidez automática.'})
    if not validation or not sent:
        issues.append({'id':'TR2-CALC-05','risk':'yellow','message':'Faltan fechas de validación o envío; debe solicitarse la trazabilidad completa.'})
    concept_relevant=False
    if event:
        try:
            concept_relevant=date.fromisoformat(prm['performance_concept_start']) <= event <= date.fromisoformat(prm['performance_concept_end'])
        except Exception: pass
    if concept_relevant and a.get('performance_concept') in ('No existe soporte','No sé'):
        issues.append({'id':'TR2-CALC-06','risk':'yellow','message':'El hecho está dentro del período histórico del concepto de desempeño; debe verificarse el trámite exacto, sin inferir nulidad automática.'})
    elif event and event > date.fromisoformat(prm.get('performance_concept_end','2020-08-19')) and a.get('performance_concept') in ('No existe soporte','No sé'):
        assumptions.append('La falta del concepto de desempeño no se usa como causal para hechos posteriores al 19 de agosto de 2020; sí se conservan controles de calibración y trazabilidad.')
    category=a.get('conduct_category')
    owner_duty=category in ('SOAT','Revisión técnico-mecánica','Pico y placa o restricción','Exceso de velocidad','Semáforo en rojo')
    imputation='deber propio del propietario sujeto a prueba de incumplimiento culpable' if owner_duty else 'imputación personal de la conducta al presunto infractor'
    if a.get('owner_was_driver') in ('No','No sé'):
        assumptions.append('La calidad de propietario no identifica por sí sola al conductor ni habilita responsabilidad objetiva.')
    if a.get('official_2026_match') in ('Sí','No sé'):
        assumptions.append('Cualquier anuncio o investigación oficial de 2026 requiere coincidencia individual por autoridad, dispositivo, período y decisión administrativa.')
    return {
        'engine_version':'2.25','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'event_to_validation_weekdays_preliminary':event_to_validation,'validation_to_sent_weekdays_preliminary':validation_to_sent,
        'send_control_days':prm.get('send_after_validation_business_days',3),'appearance_days_after_delivery':prm.get('appearance_after_delivery_business_days',11),
        'concept_performance_relevant':concept_relevant,'imputation_model':imputation,
        'current_technical_resolution':prm.get('current_technical_resolution'),'calculation_note':prm.get('date_calculation_note'),
        'issues':issues,'assumptions':assumptions,
        'controls':['comparendo no equivale a sanción firme','cronología y trazabilidad de notificación','imputación personal y culpable','deberes propios del propietario sin responsabilidad objetiva','autorización, calibración, trazabilidad y señalización SAST','revocatoria directa condicionada y sin revivir términos'],
    }


def sast_calc(a):
    """Control técnico y de cobertura CO-TR-001 v2.26.

    La coincidencia es preliminar y se limita al snapshot local. La función no
    declara nulidad, revocatoria, devolución ni regularidad del dispositivo.
    """
    prm=PARAMETERS.get('CO-TR-001',{})
    issues=[]; assumptions=[]
    matches=sast_matches(a)
    def dt(k):
        v=a.get(k)
        if not v: return None
        try: return date.fromisoformat(str(v))
        except Exception: return None
    event=dt('event_date'); issued=dt('authorization_issue_date'); expiry=dt('authorization_expiry_date'); calibration=dt('calibration_date')
    if issued and expiry and expiry < issued:
        issues.append({'id':'TR1-CALC-01','risk':'red','message':'La vigencia declarada de la autorización es imposible: el vencimiento precede a la expedición.'})
    if event and issued and event < issued:
        issues.append({'id':'TR1-CALC-02','risk':'yellow','message':'La fecha del hecho precede a la expedición declarada de la autorización; debe verificarse el acto aplicable al período.'})
    if event and expiry and event > expiry:
        issues.append({'id':'TR1-CALC-03','risk':'yellow','message':'La fecha del hecho es posterior al vencimiento declarado de la autorización; debe verificarse renovación, sustitución o excepción.'})
    if event and calibration and calibration > event:
        issues.append({'id':'TR1-CALC-04','risk':'yellow','message':'El certificado técnico declarado es posterior al hecho; no acredita por sí solo el estado del equipo para esa fecha.'})
    concept_relevant=False
    if event:
        try:
            concept_relevant=date.fromisoformat(prm['performance_concept_start']) <= event <= date.fromisoformat(prm['performance_concept_end'])
        except Exception: pass
    if concept_relevant and a.get('performance_concept') in ('No existe soporte','No sé','No aplica por fecha'):
        issues.append({'id':'TR1-CALC-05','risk':'yellow','message':'El hecho está dentro del período histórico del concepto de desempeño y el soporte no está acreditado; debe individualizarse tecnología, organismo y período.'})
    elif event and not concept_relevant and a.get('performance_concept') in ('No existe soporte','No sé'):
        assumptions.append('La ausencia del concepto de desempeño no se usa como causal para fechas fuera del período 22/03/2018-19/08/2020; permanecen autorización, calibración, trazabilidad y señalización.')
    if matches:
        assumptions.append(f'Se encontraron {len(matches)} coincidencia(s) preliminar(es) en el snapshot local de {prm.get("dataset_records_included",10)} registros. Debe verificarse el acto individual y la fuente oficial vigente.')
    else:
        assumptions.append(f'No hubo coincidencia en el snapshot local de {prm.get("dataset_records_included",10)} registros. Esto no acredita regularidad ni ausencia de actuaciones dentro del universo histórico esperado de {prm.get("historical_master_expected_records",49)} registros.')
    status=a.get('official_act_status')
    if status in ('Apertura o formulación de cargos','Investigación en curso'):
        assumptions.append('La actuación oficial declarada no es una decisión individual firme y no produce por sí sola revocatoria, archivo o devolución.')
    if status == 'Decisión firme favorable individual':
        assumptions.append('La decisión favorable debe cotejarse por sujeto, autoridad, dispositivo, período, ejecutoria y efectos exactos antes de solicitar una actuación derivada.')
    return {
        'engine_version':'2.26','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'local_match_count':len(matches),'dataset_records_included':prm.get('dataset_records_included',10),
        'historical_master_expected_records':prm.get('historical_master_expected_records',49),
        'dataset_coverage_complete':False,'concept_performance_relevant':concept_relevant,
        'authorization_covers_event_preliminary':bool(event and issued and expiry and issued <= event <= expiry),
        'official_registry':prm.get('official_registry'),'current_technical_resolution':prm.get('current_technical_resolution'),
        'issues':issues,'assumptions':assumptions,
        'controls':['snapshot local incompleto','coincidencia preliminar por territorio y fecha','dispositivo y punto exactos','autorización o excepción y vigencia','calibración y trazabilidad','señalización','concepto de desempeño por período','acto oficial y firmeza individual'],
    }


def _business_day_add(start, days):
    """Suma días hábiles de lunes a viernes. No descuenta festivos."""
    if not start or days is None:
        return None
    cursor = start
    added = 0
    while added < int(days):
        cursor = cursor.fromordinal(cursor.toordinal() + 1)
        if cursor.weekday() < 5:
            added += 1
    return cursor


def health_petition_calc(a):
    """Control de términos, legitimación y privacidad CO-SA-001 v2.31.

    El calendario es preliminar: excluye fines de semana, pero no festivos,
    traslados, ampliaciones informadas, suspensiones o términos sectoriales.
    """
    prm = PARAMETERS.get('CO-SA-001', {})
    issues = []
    assumptions = []

    def dt(key):
        value = a.get(key)
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except Exception:
            return None

    reference = dt('filing_date')
    verified = None
    try:
        verified = date.fromisoformat(str(prm.get('verified_at')))
    except Exception:
        pass

    request_type = a.get('request_type')
    term_days = (
        int(prm.get('information_documents_business_days', 10))
        if request_type in ('Historia clínica', 'Información o documentos')
        else int(prm.get('general_response_business_days', 15))
    )
    term_category = 'información o documentos' if term_days == int(prm.get('information_documents_business_days', 10)) else 'petición general'
    preliminary_due = _business_day_add(reference, term_days) if reference else None

    if reference and verified and reference > verified:
        issues.append({'id':'SA-CALC-01','risk':'red','message':'La fecha prevista de radicación es posterior a la fecha de verificación del expediente v2.31; debe confirmarse antes de generar una salida definitiva.'})

    prior = dt('prior_request_date')
    response = dt('response_date')
    prior_due = _business_day_add(prior, term_days) if prior else None
    if prior and reference and prior > reference:
        issues.append({'id':'SA-CALC-02','risk':'red','message':'La fecha de la petición previa es posterior a la fecha prevista de la nueva radicación.'})
    if prior and verified and prior > verified:
        issues.append({'id':'SA-CALC-03','risk':'red','message':'La fecha de la petición previa es posterior a la fecha de verificación del expediente.'})
    if response and prior and response < prior:
        issues.append({'id':'SA-CALC-04','risk':'red','message':'La fecha de respuesta precede a la petición previa y la cronología es imposible.'})
    if a.get('prior_request') == 'Sí' and prior_due and verified and prior_due < verified and a.get('response_received') in ('No','Parcial'):
        issues.append({'id':'SA-CALC-05','risk':'yellow','message':'El término preliminar de la petición previa aparece vencido sin respuesta completa acreditada.'})
    if response and prior_due and response > prior_due:
        issues.append({'id':'SA-CALC-06','risk':'yellow','message':'La respuesta declarada fue posterior al vencimiento preliminar calculado; deben verificarse festivos, traslado, extensión y norma especial.'})

    if a.get('patient_status') == 'Fallecido':
        purpose = str(a.get('deceased_access_purpose') or '').strip()
        if len(purpose) < 20:
            issues.append({'id':'SA-CALC-07','risk':'red','message':'No se acreditó una finalidad concreta y suficiente para el acceso a la historia clínica de un paciente fallecido.'})
        if a.get('representation_support') in ('No','Parcial'):
            risk = 'red' if a.get('representation_support') == 'No' else 'yellow'
            issues.append({'id':'SA-CALC-08','risk':risk,'message':'El acceso a información clínica de un paciente fallecido exige acreditar parentesco, identidad, finalidad y soportes suficientes.'})

    if request_type == 'Historia clínica' and a.get('secure_delivery') in ('No','No sé'):
        issues.append({'id':'SA-CALC-09','risk':'yellow','message':'La entrega de historia clínica debe configurarse por un canal reservado y verificable.'})
    if a.get('deterioration') == 'Grave' and a.get('immediate_attention_sought') == 'No':
        issues.append({'id':'SA-CALC-10','risk':'red','message':'El deterioro grave no puede gestionarse únicamente mediante una petición administrativa.'})
    if a.get('prescription_date'):
        prescription = dt('prescription_date')
        if prescription and reference and prescription > reference:
            issues.append({'id':'SA-CALC-11','risk':'red','message':'La fecha de la orden o fórmula médica es posterior a la fecha prevista de radicación.'})

    assumptions.extend([
        'El cálculo de días hábiles excluye sábados y domingos, pero no descuenta festivos nacionales o territoriales.',
        'El término puede variar por traslado por competencia, ampliación informada, suspensión, regulación sectorial o naturaleza exacta de la solicitud.',
        'La atención prioritaria y la continuidad deben sustentarse con hechos confirmados; la herramienta no formula diagnósticos clínicos.',
        'La historia clínica y los datos de salud requieren legitimación, finalidad, minimización y canal seguro.',
        'El paquete no garantiza autorización, entrega de medicamento, asignación de cita ni resultado ante EPS, IPS o Supersalud.',
    ])
    if a.get('urgent') in ('Sí','No sé') or a.get('deterioration') in ('Grave','No sé'):
        assumptions.append('La petición no reemplaza atención de urgencias, valoración médica ni otros canales asistenciales inmediatos.')

    return {
        'engine_version':'2.31',
        'parameter_version':prm.get('version'),
        'verified_at':prm.get('verified_at'),
        'request_type':request_type,
        'term_category':term_category,
        'preliminary_business_days':term_days,
        'filing_date':reference.isoformat() if reference else None,
        'preliminary_due_date':preliminary_due.isoformat() if preliminary_due else None,
        'prior_request_date':prior.isoformat() if prior else None,
        'prior_preliminary_due_date':prior_due.isoformat() if prior_due else None,
        'holiday_calendar_applied':False,
        'deadline_is_preliminary':True,
        'priority_attention_flag':bool(a.get('priority_condition') != 'No' or a.get('continuity_risk') in ('Sí','No sé') or a.get('urgent') in ('Sí','No sé')),
        'privacy_sensitive_data':True,
        'issues':issues,
        'assumptions':assumptions,
        'controls':['urgencia asistencial','legitimación','historia clínica reservada','datos sensibles y minimización','cronología','término preliminar','petición previa','canal de radicación','procesos activos'],
    }



def _add_months(start, months):
    if not start:
        return None
    import calendar
    total = start.year * 12 + (start.month - 1) + int(months)
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(start, years):
    if not start:
        return None
    try:
        return start.replace(year=start.year + int(years))
    except ValueError:
        return start.replace(month=2, day=28, year=start.year + int(years))


def habeas_data_calc(a):
    """Control de términos, permanencia y trazabilidad CO-CD-001 v2.32.

    Los términos hábiles excluyen sábados y domingos, pero no festivos. Los
    resultados sobre permanencia, caducidad, comunicación y silencio son
    preliminares y exigen cotejo de soportes, recepción y norma vigente.
    """
    prm = PARAMETERS.get('CO-CD-001', {})
    issues, assumptions = [], []

    def dt(key):
        value = a.get(key)
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except Exception:
            issues.append({'id':f'CD1-CALC-DATE-{key}','risk':'red','message':f'La fecha informada para {key} no tiene formato válido.'})
            return None

    try:
        verified = date.fromisoformat(str(prm.get('verified_at')))
    except Exception:
        verified = None
    try:
        law_2573_effective = date.fromisoformat(str(prm.get('law_2573_general_effective_date')))
    except Exception:
        law_2573_effective = None

    filing = dt('filing_date')
    prior_claim = dt('prior_claim_date')
    response = dt('response_date')
    mora = dt('mora_start_date')
    payment = dt('payment_or_extinction_date')
    report = dt('report_date')
    communication = dt('prior_communication_date')
    discovery = dt('report_discovery_date')

    mode = a.get('request_mode')
    is_query = mode == 'Consulta de información'
    term_days = int(prm.get('query_response_business_days', 10) if is_query else prm.get('claim_response_business_days', 15))
    extension_days = int(prm.get('query_extension_business_days', 5) if is_query else prm.get('claim_extension_business_days', 8))
    due = _business_day_add(filing, term_days) if filing else None
    due_with_extension = _business_day_add(due, extension_days) if due else None
    prior_due = _business_day_add(prior_claim, term_days) if prior_claim else None
    prior_max_due = _business_day_add(prior_due, extension_days) if prior_due and a.get('extension_notified') == 'Sí' else prior_due
    legend_due = _business_day_add(prior_claim, int(prm.get('claim_legend_business_days', 2))) if prior_claim else None
    transfer_due = _business_day_add(filing, int(prm.get('transfer_business_days', 2))) if filing else None

    if filing and verified and filing > verified:
        issues.append({'id':'CD1-CALC-01','risk':'red','message':'La fecha prevista de radicación es posterior a la fecha de verificación del expediente v2.32.'})
    if prior_claim and filing and prior_claim > filing:
        issues.append({'id':'CD1-CALC-02','risk':'red','message':'La actuación previa aparece después de la nueva radicación.'})
    if response and prior_claim and response < prior_claim:
        issues.append({'id':'CD1-CALC-03','risk':'red','message':'La respuesta informada precede al reclamo o consulta previa.'})
    if report and mora and report < mora:
        issues.append({'id':'CD1-CALC-04','risk':'red','message':'El reporte negativo aparece fechado antes de la constitución en mora.'})
    if payment and mora and payment < mora:
        issues.append({'id':'CD1-CALC-05','risk':'red','message':'La fecha de pago o extinción precede al inicio de mora.'})
    if communication and report and communication > report:
        issues.append({'id':'CD1-CALC-06','risk':'red','message':'La comunicación previa aparece después del reporte negativo.'})
    if discovery and report and discovery < report:
        issues.append({'id':'CD1-CALC-07','risk':'yellow','message':'La fecha declarada de conocimiento precede al reporte; debe conciliarse la cronología.'})

    initial_report_limit = _add_months(mora, int(prm.get('initial_report_max_months_after_mora', 18))) if mora else None
    report_after_limit = bool(report and initial_report_limit and report > initial_report_limit)
    if report_after_limit:
        issues.append({'id':'CD1-CALC-08','risk':'yellow','message':'El primer reporte informado aparece posterior al límite preliminar de dieciocho meses desde la mora.'})

    communication_lead = None
    if communication and report:
        communication_lead = (report - communication).days
        if communication_lead < int(prm.get('communication_lead_calendar_days', 20)):
            issues.append({'id':'CD1-CALC-09','risk':'yellow','message':'La comunicación previa no acredita preliminarmente veinte días calendario antes del reporte.'})

    amount = a.get('obligation_amount')
    try:
        amount_num = float(amount) if amount not in (None, '') else None
    except Exception:
        amount_num = None
        issues.append({'id':'CD1-CALC-10','risk':'red','message':'El valor de la obligación no puede interpretarse numéricamente.'})
    small_reference = float(prm.get('small_obligation_reference_value', 0) or 0)
    small_obligation = bool(amount_num is not None and small_reference and amount_num <= small_reference)
    if small_obligation and a.get('small_obligation_two_notices') != 'Sí':
        issues.append({'id':'CD1-CALC-11','risk':'yellow','message':'La obligación está bajo el umbral económico de referencia y no se acreditan dos comunicaciones en días diferentes.'})

    paid_expiry = None
    mora_days = None
    if mora and payment and payment >= mora:
        mora_days = (payment - mora).days
        double_mora_expiry = date.fromordinal(payment.toordinal() + max(0, mora_days * 2))
        four_year_cap = _add_years(payment, int(prm.get('paid_negative_max_years', 4)))
        paid_expiry = min(double_mora_expiry, four_year_cap)
        if verified and paid_expiry < verified and a.get('obligation_status') in ('Pagada','Extinguida por otro modo'):
            issues.append({'id':'CD1-CALC-12','risk':'yellow','message':'La permanencia preliminar del dato pagado o extinguido aparece vencida.'})

    unpaid_expiry = _add_years(mora, int(prm.get('unpaid_negative_caducity_years', 8))) if mora else None
    if unpaid_expiry and verified and unpaid_expiry < verified and a.get('obligation_status') == 'Vigente y en mora':
        issues.append({'id':'CD1-CALC-13','risk':'yellow','message':'La caducidad preliminar del dato negativo insoluto aparece cumplida; esto no extingue la obligación.'})

    prior_overdue = bool(prior_max_due and verified and prior_max_due < verified)
    prior_complete = a.get('prior_claim_complete') == 'Sí'
    response_complete = a.get('response_received') == 'Sí' and a.get('response_quality') == 'De fondo y completa'
    silence_preliminary = bool(a.get('prior_claim') == 'Sí' and prior_overdue and prior_complete and not response_complete)
    if prior_overdue and not response_complete:
        issues.append({'id':'CD1-CALC-14','risk':'yellow','message':'La actuación previa aparece vencida sin respuesta completa, según calendario preliminar.'})
    if silence_preliminary:
        issues.append({'id':'CD1-CALC-15','risk':'yellow','message':'Puede existir aceptación legal preliminar por silencio; debe verificarse integridad del reclamo, recepción, prórroga y respuesta.'})
    if prior_claim and a.get('claim_legend_present') in ('No','No sé') and verified and legend_due and verified > legend_due:
        issues.append({'id':'CD1-CALC-16','risk':'yellow','message':'No está acreditada oportunamente la leyenda de reclamo en trámite.'})

    law_2573_reference_date = filing or verified
    law_2573_general_effective = bool(law_2573_reference_date and law_2573_effective and law_2573_reference_date >= law_2573_effective)
    law_2573_status_at_reference = (
        'vigencia general activa; exige nueva verificación normativa y reglamentaria'
        if law_2573_general_effective
        else 'vigencia general diferida; solo parágrafos 1 y 2 del artículo 5 vigentes desde la promulgación'
    )
    if a.get('identity_theft') in ('Sí','No sé') and not law_2573_general_effective:
        issues.append({'id':'CD1-CALC-17','risk':'yellow','message':'La Ley 2573 de 2026 ya fue promulgada, pero su vigencia general inicia el 20 de noviembre de 2026; no deben invocarse anticipadamente como operativas sus reglas diferidas.'})

    assumptions.extend([
        'Los días hábiles excluyen sábados y domingos, pero no descuentan festivos nacionales o territoriales.',
        'Los términos dependen de la recepción efectiva, integridad de la solicitud, traslado, requerimientos y prórroga informada.',
        'La conclusión sobre silencio es preliminar y solo aplica tras verificar reclamo completo, vencimiento y ausencia de respuesta de fondo.',
        'La corrección, actualización o retiro del dato no extingue por sí misma una obligación válida.',
        'La permanencia y caducidad se estiman con fechas aportadas y requieren prueba del inicio de mora, primer reporte, pago o extinción.',
        'El umbral del 15 % usa una referencia 2026 sujeta a verificación normativa y judicial al momento de uso.',
        'La herramienta no garantiza eliminación del reporte, aprobación crediticia, sanción administrativa ni resultado judicial.',
        'Las copias de documentos deben minimizar datos personales y enviarse por canales verificables y seguros.',
        'La Ley 2573 de 2026 fue publicada el 20 de mayo de 2026 y tiene vigencia general desde el 20 de noviembre de 2026, salvo los parágrafos 1 y 2 del artículo 5 vigentes desde la promulgación.',
        'La aplicación de la Ley 2573 de 2026 debe respetar los condicionamientos fijados por la Sentencia C-413 de 2025 y verificar los protocolos administrativos que se expidan.',
    ])
    if a.get('identity_theft') in ('Sí','No sé'):
        assumptions.append('La suplantación exige preservación inmediata de evidencia, alertas, reclamación individual y valoración de denuncias o medidas adicionales, distinguiendo las reglas actualmente vigentes de las de vigencia diferida.')

    return {
        'engine_version':'2.32','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'request_mode':mode,'term_category':'consulta' if is_query else 'reclamo','preliminary_business_days':term_days,
        'extension_business_days':extension_days,'filing_date':filing.isoformat() if filing else None,
        'preliminary_due_date':due.isoformat() if due else None,'preliminary_due_with_extension':due_with_extension.isoformat() if due_with_extension else None,
        'transfer_due_date':transfer_due.isoformat() if transfer_due else None,'prior_claim_date':prior_claim.isoformat() if prior_claim else None,
        'prior_preliminary_due_date':prior_due.isoformat() if prior_due else None,'prior_max_due_date':prior_max_due.isoformat() if prior_max_due else None,
        'claim_legend_due_date':legend_due.isoformat() if legend_due else None,'prior_term_overdue_preliminary':prior_overdue,
        'silence_acceptance_preliminary':silence_preliminary,'holiday_calendar_applied':False,'deadline_is_preliminary':True,
        'mora_start_date':mora.isoformat() if mora else None,'report_date':report.isoformat() if report else None,
        'initial_report_limit_date':initial_report_limit.isoformat() if initial_report_limit else None,'report_after_18_month_limit_preliminary':report_after_limit,
        'prior_communication_date':communication.isoformat() if communication else None,'communication_lead_calendar_days':communication_lead,
        'small_obligation_reference_value':small_reference,'small_obligation_preliminary':small_obligation,
        'smmlv_reference':prm.get('smmlv_reference_2026'),'smmlv_parameter_status':prm.get('smmlv_parameter_status'),
        'law_2573_publication_date':prm.get('law_2573_publication_date'),
        'law_2573_general_effective_date':prm.get('law_2573_general_effective_date'),
        'law_2573_general_effective_at_reference':law_2573_general_effective,
        'law_2573_status_at_reference':law_2573_status_at_reference,
        'law_2573_immediate_scope':prm.get('law_2573_immediate_scope'),
        'mora_duration_days':mora_days,'paid_negative_expiry_preliminary':paid_expiry.isoformat() if paid_expiry else None,
        'unpaid_negative_expiry_preliminary':unpaid_expiry.isoformat() if unpaid_expiry else None,
        'issues':issues,'assumptions':assumptions,
        'controls':['titularidad y legitimación','fuente, operador y usuario','soporte de obligación','comunicación previa','umbral 15 % SMLMV','primer reporte y límite de 18 meses','pago, permanencia y caducidad','consulta, reclamo y prórroga','leyenda en trámite','silencio preliminar','suplantación','minimización de datos'],
    }



def consumer_protection_calc(a):
    """Clasificación y control preliminar de términos CO-CD-003 v2.33.

    Los días hábiles excluyen sábados y domingos, pero no festivos. El motor
    separa garantía, retracto, reversión, débito periódico y falta de entrega;
    no presume elegibilidad definitiva ni reemplaza el cotejo de soportes.
    """
    prm = PARAMETERS.get('CO-CD-003', {})
    issues, assumptions = [], []

    def dt(key):
        value = a.get(key)
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except Exception:
            issues.append({'id':f'CD3-CALC-DATE-{key}','risk':'red','message':f'La fecha informada para {key} no tiene formato válido.'})
            return None

    try:
        verified = date.fromisoformat(str(prm.get('verified_at')))
    except Exception:
        verified = None

    purchase = dt('purchase_date')
    delivery = dt('delivery_date')
    transaction = dt('transaction_date')
    event = dt('reversal_event_date')
    direct_claim = dt('prior_claim_date')
    response = dt('response_date')
    issuer_notice = dt('issuer_notification_date')
    withdrawal = dt('withdrawal_exercised_date')
    debit_revocation = dt('recurring_debit_revoked_date')
    latest_charge = dt('latest_periodic_charge_date')

    dates = {
        'purchase_date': purchase, 'delivery_date': delivery, 'transaction_date': transaction,
        'reversal_event_date': event, 'prior_claim_date': direct_claim, 'response_date': response,
        'issuer_notification_date': issuer_notice, 'withdrawal_exercised_date': withdrawal,
        'recurring_debit_revoked_date': debit_revocation, 'latest_periodic_charge_date': latest_charge,
    }
    for key, value in dates.items():
        if value and verified and value > verified:
            issues.append({'id':f'CD3-CALC-FUTURE-{key}','risk':'red','message':f'La fecha {key} es posterior a la fecha de verificación del expediente v2.33.'})

    if delivery and purchase and delivery < purchase:
        issues.append({'id':'CD3-CALC-01','risk':'red','message':'La entrega o fecha esperada precede a la compra informada.'})
    if transaction and purchase and transaction < purchase:
        issues.append({'id':'CD3-CALC-02','risk':'yellow','message':'La transacción precede a la compra; debe verificarse reserva, anticipo o error de cronología.'})
    if direct_claim and purchase and direct_claim < purchase:
        issues.append({'id':'CD3-CALC-03','risk':'red','message':'La reclamación directa aparece antes de la compra.'})
    if response and direct_claim and response < direct_claim:
        issues.append({'id':'CD3-CALC-04','risk':'red','message':'La respuesta precede a la reclamación directa.'})
    if issuer_notice and event and issuer_notice < event:
        issues.append({'id':'CD3-CALC-05','risk':'yellow','message':'La notificación al emisor aparece antes del conocimiento de la causal de reversión.'})
    if latest_charge and debit_revocation and latest_charge < debit_revocation:
        assumptions.append('El último cargo informado precede a la revocación; no se identificó cargo posterior en las fechas aportadas.')

    direct_days = int(prm.get('direct_claim_response_business_days', 15))
    claim_due = _business_day_add(direct_claim, direct_days) if direct_claim else None
    if response and claim_due and response > claim_due:
        issues.append({'id':'CD3-CALC-06','risk':'yellow','message':'La respuesta fue posterior al término preliminar de quince días hábiles; deben verificarse recepción, completitud, festivos y régimen especial.'})
    if direct_claim and not response and verified and claim_due and verified > claim_due and a.get('response_received') == 'No':
        issues.append({'id':'CD3-CALC-07','risk':'yellow','message':'La reclamación directa aparece vencida preliminarmente sin respuesta acreditada.'})

    withdrawal_days = int(prm.get('withdrawal_exercise_business_days', 5))
    withdrawal_anchor = delivery or purchase
    withdrawal_due = _business_day_add(withdrawal_anchor, withdrawal_days) if withdrawal_anchor else None
    withdrawal_refund_days = int(prm.get('withdrawal_refund_calendar_days', 15))
    withdrawal_refund_due = date.fromordinal(withdrawal.toordinal() + withdrawal_refund_days) if withdrawal else None
    withdrawal_in_time = bool(withdrawal and withdrawal_due and withdrawal <= withdrawal_due)
    if a.get('request_mode') == 'Derecho de retracto':
        if not withdrawal:
            issues.append({'id':'CD3-CALC-08','risk':'yellow','message':'No se informó la fecha de ejercicio del retracto.'})
        elif withdrawal_due and withdrawal > withdrawal_due:
            issues.append({'id':'CD3-CALC-09','risk':'yellow','message':'El retracto aparece ejercido después del término preliminar de cinco días hábiles.'})
        if a.get('withdrawal_exception') in ('Sí','No sé'):
            issues.append({'id':'CD3-CALC-10','risk':'yellow','message':'Debe verificarse una posible excepción legal al retracto antes de exigir reembolso.'})
        if a.get('product_type') == 'Servicio' and a.get('service_started_with_consent') in ('Sí','No sé'):
            issues.append({'id':'CD3-CALC-11','risk':'yellow','message':'El inicio del servicio con acuerdo del consumidor puede afectar la procedencia del retracto.'})

    reversal_days = int(prm.get('reversal_request_business_days', 5))
    reversal_anchor = event or delivery or transaction
    reversal_due = _business_day_add(reversal_anchor, reversal_days) if reversal_anchor else None
    reversal_effective_days = int(prm.get('reversal_effective_business_days', 15))
    reversal_effective_due = _business_day_add(issuer_notice, reversal_effective_days) if issuer_notice else None
    reversal_in_time = bool(issuer_notice and reversal_due and issuer_notice <= reversal_due)
    if a.get('request_mode') == 'Reversión del pago':
        if a.get('electronic_payment') != 'Sí':
            issues.append({'id':'CD3-CALC-12','risk':'yellow','message':'La reversión ordinaria exige una compra pagada mediante instrumento electrónico; debe reclasificarse el mecanismo.'})
        if a.get('reversal_cause') in ('No aplica','Otra',None,''):
            issues.append({'id':'CD3-CALC-13','risk':'yellow','message':'La causal de reversión no está clasificada dentro de las causales legales configuradas.'})
        if a.get('provider_complaint_for_reversal') != 'Sí':
            issues.append({'id':'CD3-CALC-14','risk':'yellow','message':'No se acredita la queja de reversión ante el proveedor.'})
        if a.get('issuer_notification') != 'Sí' or not issuer_notice:
            issues.append({'id':'CD3-CALC-15','risk':'yellow','message':'No se acredita notificación completa y fechada al emisor del instrumento de pago.'})
        elif reversal_due and issuer_notice > reversal_due:
            issues.append({'id':'CD3-CALC-16','risk':'yellow','message':'La notificación al emisor aparece después del término preliminar de cinco días hábiles.'})
        if _money(a.get('reversal_amount')) > _money(a.get('purchase_value')) + 0.01:
            issues.append({'id':'CD3-CALC-17','risk':'red','message':'El valor solicitado en reversión supera el valor total controvertido.'})
        if a.get('partial_reversal') == 'Sí' and not a.get('reversal_amount'):
            issues.append({'id':'CD3-CALC-18','risk':'yellow','message':'La reversión parcial exige identificar el valor exacto solicitado.'})

    delivery_default_days = int(prm.get('ecommerce_default_delivery_calendar_days', 30))
    default_delivery_due = date.fromordinal(purchase.toordinal() + delivery_default_days) if purchase else None
    ecommerce_refund_days = int(prm.get('ecommerce_refund_calendar_days', 15))
    ecommerce_refund_due = date.fromordinal((direct_claim or verified).toordinal() + ecommerce_refund_days) if (direct_claim or verified) else None
    if a.get('request_mode') == 'Terminación por falta de entrega':
        if a.get('purchase_channel') not in ('Internet o aplicación','PSE o enlace de pago','Red social o mensajería','Call center o teléfono'):
            issues.append({'id':'CD3-CALC-19','risk':'yellow','message':'La terminación especial por falta de entrega requiere verificar que la operación esté comprendida en comercio electrónico o venta a distancia.'})

    periodic_new_charge_days = int(prm.get('periodic_debit_new_charge_business_days', 5))
    periodic_control_due = _business_day_add(debit_revocation, periodic_new_charge_days) if debit_revocation else None
    if a.get('request_mode') == 'Revocación de débito periódico':
        if not debit_revocation:
            issues.append({'id':'CD3-CALC-21','risk':'yellow','message':'No se informó la fecha de revocación del débito periódico.'})
        if a.get('payment_instrument') != 'Débito automático':
            issues.append({'id':'CD3-CALC-22','risk':'yellow','message':'Debe verificarse que exista una instrucción de débito periódico o mecanismo equivalente.'})
        if latest_charge and periodic_control_due and latest_charge > periodic_control_due:
            issues.append({'id':'CD3-CALC-23','risk':'yellow','message':'Existe un cargo posterior al período de control configurado tras la revocación; debe preservarse el comprobante y clasificarse la actuación aplicable.'})

    if a.get('request_mode') == 'Garantía legal':
        if a.get('warranty_announced') == 'Vencido':
            issues.append({'id':'CD3-CALC-24','risk':'yellow','message':'La garantía anunciada aparece vencida; debe revisarse garantía legal, vida útil, información y prueba del defecto.'})
        if a.get('repeated_failure') == 'Sí' and a.get('claim_goal') not in ('Cambio o reposición','Devolución del dinero','Otra'):
            issues.append({'id':'CD3-CALC-25','risk':'yellow','message':'La falla repetida requiere verificar la opción legal del consumidor y la naturaleza del bien o servicio.'})

    assumptions.extend([
        'Los días hábiles excluyen sábados y domingos, pero no descuentan festivos nacionales o territoriales.',
        'Los términos se calculan desde fechas aportadas y dependen de recepción efectiva, completitud, canal y régimen especial.',
        'Garantía, retracto, reversión, revocación de débito y terminación por falta de entrega son mecanismos diferentes.',
        'El diagnóstico no acredita por sí solo defecto, incumplimiento, causal de reversión, legitimación ni procedencia del reembolso.',
        'La reclamación directa y las comunicaciones deben conservar radicado, contenido, anexos, destinatario y constancia de recepción.',
        'No deben incorporarse números completos de tarjeta, claves, CVV, contraseñas ni datos innecesarios.',
        'Lesiones, productos peligrosos, fraude complejo, procesos activos y regímenes especiales requieren revisión profesional.',
        'La herramienta no garantiza reparación, devolución, reversión, sanción administrativa ni decisión judicial favorable.',
    ])

    return {
        'engine_version':'2.33','parameter_version':prm.get('version'),'verified_at':prm.get('verified_at'),
        'request_mode':a.get('request_mode'),'problem_type':a.get('problem_type'),'claim_goal':a.get('claim_goal'),
        'purchase_date':purchase.isoformat() if purchase else None,'delivery_date':delivery.isoformat() if delivery else None,
        'direct_claim_date':direct_claim.isoformat() if direct_claim else None,'direct_claim_due_date':claim_due.isoformat() if claim_due else None,
        'direct_claim_business_days':direct_days,
        'withdrawal_anchor_date':withdrawal_anchor.isoformat() if withdrawal_anchor else None,'withdrawal_due_date':withdrawal_due.isoformat() if withdrawal_due else None,
        'withdrawal_exercised_date':withdrawal.isoformat() if withdrawal else None,'withdrawal_in_time_preliminary':withdrawal_in_time,
        'withdrawal_refund_due_date':withdrawal_refund_due.isoformat() if withdrawal_refund_due else None,
        'reversal_event_date':reversal_anchor.isoformat() if reversal_anchor else None,'reversal_request_due_date':reversal_due.isoformat() if reversal_due else None,
        'issuer_notification_date':issuer_notice.isoformat() if issuer_notice else None,'reversal_in_time_preliminary':reversal_in_time,
        'reversal_effective_due_date':reversal_effective_due.isoformat() if reversal_effective_due else None,
        'default_ecommerce_delivery_due_date':default_delivery_due.isoformat() if default_delivery_due else None,
        'ecommerce_refund_due_date':ecommerce_refund_due.isoformat() if ecommerce_refund_due else None,
        'periodic_debit_control_due_date':periodic_control_due.isoformat() if periodic_control_due else None,
        'holiday_calendar_applied':False,'deadline_is_preliminary':True,
        'mechanism_eligibility':{
            'warranty':a.get('request_mode') == 'Garantía legal' and a.get('consumer_relationship') == 'Sí',
            'withdrawal':a.get('request_mode') == 'Derecho de retracto' and a.get('withdrawal_exception') == 'No' and withdrawal_in_time,
            'reversal':a.get('request_mode') == 'Reversión del pago' and a.get('electronic_payment') == 'Sí' and reversal_in_time,
            'periodic_debit':a.get('request_mode') == 'Revocación de débito periódico' and bool(debit_revocation),
            'non_delivery':a.get('request_mode') == 'Terminación por falta de entrega',
        },
        'issues':issues,'assumptions':assumptions,
        'controls':['relación de consumo','legitimación','garantía y falla repetida','retracto y excepciones','reversión y causal','queja al proveedor','notificación al emisor','reversión parcial','débito periódico','falta de entrega','reclamación directa','cronología','evidencia','privacidad'],
    }


def collection_management_calc(a):
    """Cálculo económico y controles de cumplimiento para CO-CD-004 v3.9.0.

    Usa Decimal, selecciona el límite por modalidad, reconcilia capital/abonos/
    cargos/saldo, construye cuotas exactas y conserva los parámetros aplicados.
    No decide exigibilidad, prescripción, mérito ejecutivo ni procedencia jurídica.
    """
    prm = PARAMETERS.get('CO-CD-004', {})
    issues = []
    assumptions = []

    def dt(key):
        value = a.get(key)
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except Exception:
            return None

    try:
        reference = date.fromisoformat(str(prm.get('reference_date') or date.today().isoformat()))
    except Exception:
        reference = date.today()
    document_date = dt('document_date')
    due_date = dt('due_date')
    first_payment = dt('first_payment_date')
    report_notice = dt('report_notice_date')

    reconciliation = reconcile_amounts(
        principal=a.get('principal'),
        payments=a.get('partial_payments_total'),
        charges=a.get('other_charges'),
        reported_balance=a.get('reported_balance'),
        agreement_total=a.get('agreement_total'),
    )
    principal = reconciliation['principal']
    partial_total = reconciliation['payments']
    other_charges = reconciliation['charges']
    reported_balance = reconciliation['reported_balance']
    expected_principal_balance = reconciliation['expected_principal_balance']
    explained_balance = reconciliation['explained_balance']
    balance_difference = reconciliation['balance_difference']

    if principal <= 0 and a.get('package_stage') not in ('Cierre',):
        issues.append({'id':'CD4-CALC-01','risk':'red','message':'El capital informado no permite estructurar un cobro o acuerdo.'})
    if partial_total > principal and a.get('currency') == 'COP':
        issues.append({'id':'CD4-CALC-02','risk':'red','message':'Los abonos informados superan el capital original; debe reconstruirse el estado de cuenta.'})
    if not reconciliation['balance_reconciled']:
        issues.append({'id':'CD4-CALC-03','risk':'yellow','message':f'El saldo pretendido difiere en COP ${abs(balance_difference):,.2f} del capital menos abonos más cargos informados.'})
    if due_date and document_date and due_date < document_date:
        issues.append({'id':'CD4-CALC-04','risk':'red','message':'La fecha de vencimiento precede la fecha del documento u obligación.'})
    if a.get('obligation_status') == 'Vencida y exigible' and due_date and due_date > reference:
        issues.append({'id':'CD4-CALC-05','risk':'red','message':'La obligación se declaró vencida, pero la fecha de exigibilidad es posterior al corte de verificación.'})
    if a.get('obligation_status') == 'No vencida' and due_date and due_date <= reference:
        issues.append({'id':'CD4-CALC-06','risk':'yellow','message':'La fecha informada ya venció, aunque el estado fue marcado como no vencido.'})

    rate = a.get('interest_rate') or 0
    period = a.get('interest_period')
    effective_annual = effective_annual_rate(rate, period) if a.get('interest_agreed') == 'Sí' else 0
    selected_rates = modality_rates(prm, a.get('interest_modality'))
    max_ea = float(selected_rates['maximum_ea'])
    ibc_ea = float(selected_rates['ibc_ea'])
    effective_annual_float = float(effective_annual)
    if a.get('interest_agreed') == 'Sí' and not effective_annual_float and period not in ('No aplica', None, ''):
        assumptions.append('No se convirtió la tasa porque su periodicidad no está definida o no es compatible con el motor.')
    if effective_annual_float and max_ea and effective_annual_float > max_ea + 1e-9:
        issues.append({'id':'CD4-CALC-07','risk':'red','message':f'La tasa equivalente ({effective_annual_float:.4f}% E.A.) supera el límite de referencia para {selected_rates["modality"]} ({max_ea:.2f}% E.A.).'})
    if a.get('interest_agreed') == 'Sí' and not selected_rates['configured']:
        issues.append({'id':'CD4-CALC-08','risk':'yellow','message':'No se definió una modalidad crediticia con parámetro vigente para seleccionar el límite aplicable.'})

    try:
        installments = max(int(float(a.get('installments') or 1)), 1)
    except (TypeError, ValueError):
        installments = 1
    agreement_total = max(float(a.get('agreement_total') or 0), 0.0)
    schedule = build_payment_schedule(agreement_total, installments, a.get('first_payment_date'), a.get('frequency'))
    installment_value = schedule['regular_installment']
    if a.get('package_stage') in ('Negociación','Formalización') and agreement_total <= 0:
        issues.append({'id':'CD4-CALC-09','risk':'red','message':'El valor total del acuerdo no permite construir un plan de pago.'})
    if first_payment and first_payment < reference and a.get('package_stage') in ('Negociación','Formalización'):
        issues.append({'id':'CD4-CALC-10','risk':'yellow','message':'La primera cuota está programada antes del corte de verificación; confirme si ya fue pagada o actualice el cronograma.'})
    for index, warning in enumerate(schedule['warnings'], 1):
        issues.append({'id':f'CD4-SCHEDULE-{index:02d}','risk':'yellow','message':warning})
    agreement_reconciliation_active = (
        a.get('package_stage') in ('Negociación', 'Formalización')
        or a.get('settlement_goal') in ('Pago único con plazo', 'Acuerdo por cuotas', 'Dación o fórmula especial')
    )
    if agreement_reconciliation_active and agreement_total and not reconciliation.get('agreement_reconciled', True):
        issues.append({'id':'CD4-CALC-18','risk':'yellow','message':f'El valor total del acuerdo difiere en COP ${abs(reconciliation.get("agreement_vs_reported_difference",0)):,.2f} del saldo pretendido; documente quita, intereses, gastos o ajuste.'})

    accrued_interest = accrued_effective_interest(
        expected_principal_balance,
        effective_annual_float,
        due_date.isoformat() if due_date else None,
        reference.isoformat(),
    ) if a.get('interest_agreed') == 'Sí' and due_date else {'calculable':False,'days':0,'interest':0.0,'total':expected_principal_balance,'reason':'No se activó cálculo de causación.'}

    smlmv = float(prm.get('smmlv_2026_transitory') or 0)
    threshold_percent = float(prm.get('low_value_report_threshold_percent') or 15)
    low_value_threshold = round(smlmv * threshold_percent / 100.0, 2) if smlmv else 0.0
    is_low_value = reported_balance <= low_value_threshold if low_value_threshold else False
    report_due = None
    if report_notice:
        report_due = report_notice.fromordinal(report_notice.toordinal() + int(prm.get('report_wait_calendar_days') or 20))
    if a.get('negative_report_planned') == 'Sí':
        if not report_notice:
            issues.append({'id':'CD4-CALC-11','risk':'red','message':'No se informó fecha de comunicación previa para controlar el reporte negativo.'})
        elif report_due and report_due > reference:
            issues.append({'id':'CD4-CALC-12','risk':'yellow','message':f'El término preliminar de veinte días calendario vencería el {report_due.isoformat()}.'})
        if is_low_value and a.get('prior_report_notice_status') != 'Dos comunicaciones en días distintos':
            issues.append({'id':'CD4-CALC-13','risk':'yellow','message':'Por la baja cuantía configurada, deben verificarse al menos dos comunicaciones en días distintos antes del reporte.'})

    if a.get('promissory_note_requested') == 'Sí':
        if a.get('note_format') == 'No aplica' or a.get('maturity_form') == 'No aplica':
            issues.append({'id':'CD4-CALC-14','risk':'red','message':'El pagaré no tiene formato o forma de vencimiento compatible con sus requisitos esenciales.'})
        if a.get('blanks_present') == 'Sí' and a.get('instructions_signed') != 'Sí':
            issues.append({'id':'CD4-CALC-15','risk':'red','message':'No puede habilitarse un pagaré con espacios sin instrucciones específicas y firmadas.'})

    if a.get('package_stage') == 'Cierre' and reported_balance > 0:
        issues.append({'id':'CD4-CALC-16','risk':'red','message':'No puede emitirse una constancia de cierre mientras exista saldo positivo informado.'})
    if a.get('package_stage') == 'Seguimiento de pagos' and partial_total <= 0:
        issues.append({'id':'CD4-CALC-17','risk':'yellow','message':'La etapa de seguimiento no registra un pago o abono confirmado.'})

    assumptions.extend([
        'La selección del límite depende de la modalidad crediticia y del parámetro vigente a la fecha de uso.',
        'El interés causado es una estimación matemática; exige pacto válido, base, fecha inicial, imputación de pagos y control jurídico.',
        'El cronograma reconcilia centavos, pero solo obliga cuando es aceptado y firmado por las partes.',
    ])
    return {
        'engine_version': '3.9.0-m28.2',
        'reference_date': reference.isoformat(),
        'document_date': document_date.isoformat() if document_date else None,
        'due_date': due_date.isoformat() if due_date else None,
        'principal': round(principal,2),
        'partial_payments_total': round(partial_total,2),
        'expected_principal_balance': round(expected_principal_balance,2),
        'other_charges': round(other_charges,2),
        'explained_balance': round(explained_balance,2),
        'reported_balance': round(reported_balance,2),
        'balance_difference': round(balance_difference,2),
        'balance_reconciled': reconciliation['balance_reconciled'],
        'agreement_vs_reported_difference': reconciliation.get('agreement_vs_reported_difference', 0.0),
        'agreement_reconciled': reconciliation.get('agreement_reconciled', True),
        'interest_rate_input': float(rate or 0),
        'interest_period': period,
        'interest_modality': selected_rates['modality'],
        'interest_banking_current_ea': round(ibc_ea,4),
        'effective_annual_rate': round(effective_annual_float,4),
        'maximum_reference_ea': round(max_ea,4),
        'interest_valid_from': prm.get('interest_valid_from'),
        'interest_valid_to': prm.get('interest_valid_to'),
        'interest_resolution': prm.get('interest_resolution'),
        'accrued_interest_preliminary': accrued_interest,
        'agreement_total': round(agreement_total,2),
        'installments': installments,
        'installment_value_preliminary': installment_value,
        'last_installment_value': schedule['last_installment'],
        'payment_schedule': schedule,
        'first_payment_date': first_payment.isoformat() if first_payment else None,
        'smmlv_2026_transitory': smlmv,
        'low_value_report_threshold': low_value_threshold,
        'low_value_report': is_low_value,
        'report_notice_date': report_notice.isoformat() if report_notice else None,
        'report_earliest_date_preliminary': report_due.isoformat() if report_due else None,
        'issues': issues,
        'assumptions': assumptions,
        'controls': ['exigibilidad','título ejecutivo','saldo','abonos','intereses','tasa por modalidad','causación preliminar','cronograma conciliado','cobranza Ley 2300','reporte negativo','pagaré','instrucciones','garantías','insolvencia','cierre condicionado'],
        'deadline_is_preliminary': True,
        'dynamic_parameters_require_revalidation': True,
        'economic_reconciliation': reconciliation,
    }

def diagnose(code, answers, strict=False):
    p = product(code)
    if not p:
        raise ValueError('Producto no encontrado')
    errors = validate_answers(code, answers) if strict else []
    matches = sast_matches(answers) if code in ('CO-TR-001', 'CO-TR-002') else []
    risk = 'green' if code == 'CO-TR-001' else p.get('base_risk', 'yellow')
    triggered = []
    for rule in RULES.get(code, []):
        if eval_conditions(rule.get('conditions'), answers):
            triggered.append(rule)
            if RISK_ORDER[rule['risk']] > RISK_ORDER[risk]:
                risk = rule['risk']
    if code == 'CO-TR-001' and matches:
        rule = {
            'id': 'SAST-MATCH', 'risk': 'yellow', 'category': 'review', 'blocking': False,
            'message': f'Se encontraron {len(matches)} coincidencia(s) preliminar(es) en la porción piloto SAST.',
            'action': 'Validar dispositivo, expediente, acto individual y aplicar la matriz maestra completa.',
        }
        triggered.append(rule)
        risk = 'yellow' if RISK_ORDER[risk] < RISK_ORDER['yellow'] else risk
    calc = labor_calc(answers) if code == 'CO-LA-001' else lease_calc(answers) if code == 'CO-AR-001' else employment_contract_calc(answers) if code == 'CO-LA-002' else traffic_calc(answers) if code == 'CO-TR-002' else sast_calc(answers) if code == 'CO-TR-001' else health_petition_calc(answers) if code == 'CO-SA-001' else habeas_data_calc(answers) if code == 'CO-CD-001' else consumer_protection_calc(answers) if code == 'CO-CD-003' else collection_management_calc(answers) if code == 'CO-CD-004' else None
    if code in ('CO-LA-001','CO-AR-001','CO-LA-002','CO-TR-002','CO-TR-001','CO-SA-001','CO-CD-001','CO-CD-003','CO-CD-004') and calc:
        for issue in calc.get('issues', []):
            dynamic_rule = {
                'id': issue.get('id'), 'risk': issue.get('risk', 'yellow'),
                'category': 'calculation_validation' if code == 'CO-LA-001' else 'lease_economic_validation' if code == 'CO-AR-001' else 'employment_contract_validation' if code == 'CO-LA-002' else 'traffic_procedure_validation' if code == 'CO-TR-002' else 'sast_technical_validation' if code == 'CO-TR-001' else 'health_petition_validation' if code == 'CO-SA-001' else 'habeas_data_validation' if code == 'CO-CD-001' else 'consumer_protection_validation' if code == 'CO-CD-003' else 'collection_management_validation',
                'blocking': issue.get('risk') == 'red',
                'message': issue.get('message'),
                'action': 'Corregir o conciliar el dato antes de utilizar el valor como definitivo.',
                'source_ids': ['LA1-S1'] if code == 'CO-LA-001' else ['AR-S1','AR-S6'] if code == 'CO-AR-001' else ['LA2-S1','LA2-S2','LA2-S3'] if code == 'CO-LA-002' else ['TR2-S1','TR2-S2','TR2-S3'] if code == 'CO-TR-002' else ['TR1-S1','TR1-S5','TR1-S8'] if code == 'CO-TR-001' else ['SA-S2','SA-S4','SA-S5','SA-S7','SA-S11'] if code == 'CO-SA-001' else ['CD1-S2','CD1-S3','CD1-S5','CD1-S9','CD1-S14'] if code == 'CO-CD-001' else ['CD3-S2','CD3-S3','CD3-S4','CD3-S5','CD3-S8','CD3-S9'] if code == 'CO-CD-003' else ['CD4-S3','CD4-S4','CD4-S5','CD4-S7','CD4-S10','CD4-S15','CD4-S16'],
            }
            if not any(r.get('id') == dynamic_rule['id'] for r in triggered):
                triggered.append(dynamic_rule)
            if RISK_ORDER[dynamic_rule['risk']] > RISK_ORDER[risk]:
                risk = dynamic_rule['risk']
    red = [r for r in triggered if r['risk'] == 'red']
    yellow = [r for r in triggered if r['risk'] == 'yellow']
    green = [r for r in triggered if r['risk'] == 'green']
    can_generate = not red and not errors
    # v2.4 separates risk, document generation and professional review. A yellow
    # alert no longer makes a lawyer mandatory by itself: the user may generate
    # a personalized draft with visible warnings and add review as an optional
    # service. Red/blocking rules stop definitive self-service generation.
    review_required = bool(red)
    review_recommended = bool(yellow) and not red
    service_mode = (
        'blocked' if red
        else 'self_service_with_warnings' if yellow
        else 'self_service'
    )
    route = (
        'Documento personalizado disponible' if risk == 'green'
        else 'Documento disponible con alertas y revisión opcional' if risk == 'yellow'
        else 'Revisión profesional obligatoria antes de una salida definitiva'
    )
    score = {'green': 25, 'yellow': 58, 'red': 92}[risk]
    return {
        'product': p,
        'answers': answers,
        'risk': risk,
        'risk_label': RISK_LABEL[risk],
        'risk_score': score,
        'route': route,
        'can_generate': can_generate,
        'review_required': review_required,
        'review_recommended': review_recommended,
        'service_mode': service_mode,
        'validation_errors': errors,
        'triggered_rules': triggered,
        'blocking_rules': red,
        'review_rules': yellow,
        'modules': green,
        'calculation': calc,
        'sast_matches': matches,
        'sources': SOURCES.get(code, []),
        'package': next((x for x in PACKAGES if x['product_code'] == code), None),
        'disclaimer': 'Este resultado se basa en la información suministrada y en reglas jurídicas configuradas para el producto. No garantiza un resultado ante terceros ni reemplaza representación judicial. Revisa los datos y las alertas antes de firmar, radicar o utilizar el documento.',
    }


def answer_rows(code, answers):
    qmap = {q['id']: q['label'] for q in INTERVIEWS.get(code, {}).get('questions', [])}
    rows = []
    for key, val in answers.items():
        if val not in (None, '', []):
            rows.append((qmap.get(key, key), ', '.join(map(str, val)) if isinstance(val, list) else str(val)))
    return rows


def next_doc_version(con, document_id, base_version):
    count = con.execute('SELECT COUNT(*) FROM document_versions WHERE document_id=?', (document_id,)).fetchone()[0]
    return base_version if count == 0 else f'{base_version}-r{count}'


def generate_case_documents(case_id, code, answers, result, actor='system', note='Generación inicial'):
    p = product(code)
    generated_at = now()
    specs = document_specs(case_id, code, answers, result, p, generated_at, answer_rows(code, answers))
    specs = append_consolidated_package(specs, case_id, code, answers, result, p, generated_at)
    con = db()
    created = []
    for spec in specs:
        existing = con.execute('SELECT * FROM documents WHERE case_id=? AND kind=?', (case_id, spec['kind'])).fetchone()
        document_id = existing['id'] if existing else 'DOC-' + uuid.uuid4().hex[:8].upper()
        version = next_doc_version(con, document_id, p.get('version', VERSION))
        safe_version = re.sub(r'[^A-Za-z0-9._-]+', '_', version)
        filename = f"{code}_{case_id}_{spec['filename_suffix']}_{safe_version}.docx"
        path = GENERATED / filename
        build_docx(path, spec['title'], spec['subtitle'], spec['metadata'], spec['sections'])
        if existing:
            con.execute(
                'UPDATE documents SET name=?,mime_type=?,file_path=?,updated_at=?,version=?,status=? WHERE id=?',
                (filename, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', str(path), generated_at, version, 'Borrador personalizado' if result.get('can_generate') else 'Material de escalamiento', document_id),
            )
        else:
            con.execute(
                'INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,version,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (document_id, case_id, code, spec['kind'], filename, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', str(path), None, generated_at, generated_at, version, 'Borrador personalizado' if result.get('can_generate') else 'Material de escalamiento',),
            )
        con.execute(
            'INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)',
            (document_id, version, generated_at, note, str(path)),
        )
        created.append({'id': document_id, 'kind': spec['kind'], 'name': filename, 'version': version})
    generation_proof = build_generation_proof(
        con, GENERATED, case_id, code, answers, result, created, generated_at
    )
    audit_payload = {
        'case_id': case_id,
        'product_code': code,
        'product_version': p.get('version'),
        'generation_version': VERSION,
        'generated_at': generated_at,
        'answers': answers,
        'result': result,
        'documents': created,
        'generation_proof': generation_proof,
    }
    audit_path = GENERATED / f'{code}_{case_id}_auditoria.json'
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    existing_audit = con.execute('SELECT * FROM documents WHERE case_id=? AND kind=?', (case_id, 'audit')).fetchone()
    audit_id = existing_audit['id'] if existing_audit else 'AUD-' + uuid.uuid4().hex[:8].upper()
    audit_version = next_doc_version(con, audit_id, p.get('version', VERSION))
    if existing_audit:
        con.execute('UPDATE documents SET name=?,file_path=?,updated_at=?,version=?,status=? WHERE id=?', (audit_path.name, str(audit_path), generated_at, audit_version, 'Auditoría', audit_id))
    else:
        con.execute(
            'INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,version,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (audit_id, case_id, code, 'audit', audit_path.name, 'application/json', str(audit_path), None, generated_at, generated_at, audit_version, 'Auditoría'),
        )
    con.execute('INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)', (audit_id, audit_version, generated_at, note, str(audit_path)))
    audit(con, actor, 'case', case_id, 'generate_documents', {'count': len(created), 'versions': created, 'generation_proof': generation_proof.get('proof_id'), 'coverage_status': generation_proof.get('status')})
    con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (case_id, 'document', f"Se generaron {len(created)} documentos jurídicos, paquete consolidado cuando aplica y evidencia de cobertura {generation_proof.get('proof_id')}.", generated_at))
    con.commit()
    con.close()
    return created


def create_tasks(con, case_id, result):
    t = now()
    rows = [
        ('Confirmar datos del formulario', 'Completada', 'client'),
        ('Cargar soportes cuando sean necesarios', 'Pendiente', 'client'),
        ('Aplicar validaciones y alertas del producto', 'Completada', 'system'),
        ('Añadir revisión profesional', 'Pendiente' if result.get('review_required') else 'Opcional', 'specialist'),
        (
            'Aprobar versión documental para uso' if result.get('review_required') else 'Revisar y descargar los documentos',
            'Bloqueada' if result.get('review_required') else 'Pendiente',
            'specialist' if result.get('review_required') else 'client',
        ),
    ]
    for pos, (label, status, role) in enumerate(rows, 1):
        con.execute('INSERT INTO case_tasks VALUES(?,?,?,?,?,?,?,?)', ('TSK-' + uuid.uuid4().hex[:8].upper(), case_id, label, status, role, pos, t, t))


def create_case(code, answers, title=None, owner='USR-CLIENT', seed=False):
    result = diagnose(code, answers, strict=True)
    if result['validation_errors']:
        message = '; '.join(x['message'] for x in result['validation_errors'])
        raise ValueError(message)
    p = product(code)
    cid = 'LZ-' + uuid.uuid4().hex[:8].upper()
    t = now()
    status = 'Requiere especialista' if result['risk'] == 'red' else 'Expediente abierto'
    con = db()
    con.execute(
        'INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
        (cid, code, title or p['title'], result['risk'], status, owner, None, 'Pendiente', t, t, json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False)),
    )
    create_tasks(con, cid, result)
    con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (cid, 'case', f'Caso creado con semáforo {result["risk_label"]}.', t))
    audit(con, owner, 'case', cid, 'create', {'risk': result['risk'], 'rules': [r['id'] for r in result['triggered_rules']]})
    con.commit()
    con.close()
    docs = generate_case_documents(cid, code, answers, result, actor=owner, note='Generación inicial del prototipo v1.1')
    return {'case_id': cid, 'documents': docs, 'result': result}


def case_detail(cid):
    con = db()
    row = con.execute(
        '''SELECT c.*,p.name specialist_name,p.specialty specialist_specialty,u.name owner_name
           FROM cases c LEFT JOIN users p ON p.id=c.specialist_id LEFT JOIN users u ON u.id=c.owner_id WHERE c.id=?''',
        (cid,),
    ).fetchone()
    if not row:
        con.close(); return None
    case = dict(row)
    case['answers'] = json.loads(case['answers'])
    case['result'] = json.loads(case['result'])
    case['documents'] = [dict(x) for x in con.execute('SELECT id,kind,name,mime_type,created_at,updated_at,version,status FROM documents WHERE case_id=? ORDER BY updated_at DESC', (cid,)).fetchall()]
    case['attachments'] = [dict(x) for x in con.execute('SELECT * FROM attachments WHERE case_id=? ORDER BY created_at DESC', (cid,)).fetchall()]
    case['tasks'] = [dict(x) for x in con.execute('SELECT * FROM case_tasks WHERE case_id=? ORDER BY position', (cid,)).fetchall()]
    case['activity'] = [dict(x) for x in con.execute('SELECT * FROM activity WHERE case_id=? ORDER BY id DESC', (cid,)).fetchall()]
    case['reviews'] = [dict(x) for x in con.execute('SELECT r.*,u.name specialist_name FROM reviews r LEFT JOIN users u ON u.id=r.specialist_id WHERE r.case_id=? ORDER BY r.created_at DESC', (cid,)).fetchall()]
    con.close()
    return case


def dashboard(role='client'):
    con = db()
    cases = [dict(x) for x in con.execute('SELECT * FROM cases ORDER BY updated_at DESC').fetchall()]
    docs = [dict(x) for x in con.execute('SELECT id,name,case_id,created_at,status FROM documents ORDER BY updated_at DESC LIMIT 8').fetchall()]
    acts = [dict(x) for x in con.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 12').fetchall()]
    reviews = [dict(x) for x in con.execute("SELECT c.id,c.title,c.product_code,c.risk,c.review_status,c.updated_at FROM cases c WHERE c.review_status!='Aprobado' ORDER BY CASE c.risk WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END,c.updated_at DESC").fetchall()]
    pending_tasks = con.execute("SELECT COUNT(*) FROM case_tasks WHERE status IN ('Pendiente','Bloqueada')").fetchone()[0]
    con.close()
    return {
        'role': role,
        'stats': {
            'cases': len(cases), 'green': sum(x['risk'] == 'green' for x in cases), 'yellow': sum(x['risk'] == 'yellow' for x in cases),
            'red': sum(x['risk'] == 'red' for x in cases), 'documents': len(docs), 'pending_reviews': len(reviews), 'pending_tasks': pending_tasks,
        },
        'cases': cases[:8], 'documents': docs, 'activity': acts, 'reviews': reviews,
    }


def governance():
    con = db()
    approvals = dict(con.execute("SELECT product_code,COUNT(*) FROM cases WHERE review_status='Aprobado' GROUP BY product_code").fetchall())
    studio_summary = STUDIO.summary(con)
    con.close()
    state_map = {x['code']: x for x in studio_summary['products']}
    rows = []
    for pkg in PACKAGES:
        code = pkg['product_code']
        p = product(code) or {}
        level = p.get('pilot_level')
        integral = level == 'Piloto integral'
        documental = level == 'Piloto documental'
        score = round(
            (pkg['question_count'] > 7) * 15 + (pkg['rule_count'] > 5) * 20 + (pkg['source_count'] >= 2) * 15 +
            (pkg['test_count'] >= 2) * 15 + (pkg['version'] not in ('1.0-demo',)) * 10 + integral * 25 + documental * 15
        )
        studio = state_map.get(code, {})
        rows.append({**pkg, 'pilot_level': level, 'implementation_status': p.get('implementation_status'),
                     'approved_cases': approvals.get(code, 0), 'ready_score': min(score, 100), 'sources': SOURCES.get(code, []),
                     'workflow_status': studio.get('workflow_status'), 'revision_count': studio.get('revision_count', 0),
                     'content_valid': studio.get('valid', False), 'warning_count': studio.get('warning_count', 0)})
    return {
        'summary': {
            'products': len(PRODUCTS),
            'pilot_products': sum(p.get('pilot_level') == 'Piloto integral' for p in PRODUCTS),
            'documental_products': sum(p.get('pilot_level') == 'Piloto documental' for p in PRODUCTS),
            'questions': sum(len(x.get('questions', [])) for x in INTERVIEWS.values()),
            'rules': sum(len(x) for x in RULES.values()),
            'sources': sum(len(x) for x in SOURCES.values()),
            'tests': sum(len(x) for x in SCENARIOS.values()),
            'sast_rows': len(SAST),
            'content_revisions': studio_summary['summary']['revisions'],
            'valid_products': studio_summary['summary']['valid_products'],
            'approved_for_pilot': studio_summary['summary']['approved_for_pilot'],
            'published': 0,
        },
        'products': rows,
        'principles': [
            'IA para orientación y explicación; reglas determinísticas para decisiones críticas.',
            'Casos rojos bloquean la salida definitiva y solo producen expediente de escalamiento.',
            'Cada documento conserva producto, versión, respuestas, reglas y archivos relacionados.',
            'El Studio Jurídico versiona ficha, entrevista, reglas, fuentes y pruebas sin modificar código.',
            'La revisión profesional cambia el estado del expediente y de los documentos, sin borrar versiones anteriores.',
            'Ningún producto se publica sin fuentes vigentes, plantilla completa, pruebas adversariales y aprobación responsable.',
        ],
    }


def case_export_bytes(cid):
    case = case_detail(cid)
    if not case:
        return None
    out = BytesIO()
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        z.writestr('expediente.json', json.dumps(case, ensure_ascii=False, indent=2, default=str))
        for d in case['documents']:
            con = db(); row = con.execute('SELECT file_path,name FROM documents WHERE id=?', (d['id'],)).fetchone(); con.close()
            if row and Path(row['file_path']).exists():
                z.write(row['file_path'], arcname=f"documentos/{row['name']}")
        for a in case['attachments']:
            if Path(a['file_path']).exists():
                z.write(a['file_path'], arcname=f"soportes/{a['id']}_{safe_filename(a['name'])}")
    return out.getvalue()


class Handler(SimpleHTTPRequestHandler):
    server_version = "LegalAIZ.it"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    def translate_path(self, path):
        clean = unquote(urlparse(path).path).lstrip('/')
        app_root = APP.resolve()
        target = (APP / clean).resolve()
        try:
            inside_app = target.is_relative_to(app_root)
        except AttributeError:
            inside_app = str(target).startswith(str(app_root) + str(Path('/')))
        if inside_app and target.is_file():
            return str(target)
        return str(APP / 'index.html')

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; manifest-src 'self'; worker-src 'none'")
        super().end_headers()

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body, content_type, filename=None, status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{safe_filename(filename)}"')
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        return json.loads(self.rfile.read(length) or b'{}')

    def read_multipart(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length > MAX_UPLOAD + 1024 * 1024:
            raise ValueError('El archivo supera el límite de 10 MB.')
        body = self.rfile.read(length)
        content_type = self.headers.get('Content-Type', '')
        raw = f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n'.encode() + body
        message = BytesParser(policy=email_policy).parsebytes(raw)
        fields = {}
        files = []
        for part in message.iter_parts():
            name = part.get_param('name', header='content-disposition')
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b''
            if filename:
                files.append({'field': name, 'filename': Path(filename).name, 'content_type': part.get_content_type(), 'data': payload})
            elif name:
                fields[name] = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
        return fields, files

    def send_file(self, path, download_name=None):
        p = Path(path)
        if not p.exists():
            return self.send_json({'error': 'Archivo no encontrado'}, 404)
        body = p.read_bytes()
        ctype = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        return self.send_bytes(body, ctype, download_name or p.name)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)
        if path == '/api/health':
            return self.send_json({'ok': True, 'version': VERSION})
        if path == '/api/config':
            return self.send_json({'version': VERSION, 'name': 'LegalAIZ.it', 'slogan': 'Más que respuestas, soluciones.', 'roles': ['client', 'specialist', 'admin'], 'max_upload_mb': 10})
        if path == '/api/products':
            return self.send_json(PRODUCTS)
        if path.startswith('/api/products/'):
            code = path.split('/')[-1]
            p = product(code)
            return self.send_json({'product': p, 'interview': INTERVIEWS.get(code, {}), 'rules': RULES.get(code, []), 'sources': SOURCES.get(code, []), 'scenarios': SCENARIOS.get(code, [])}, 200 if p else 404)
        if path == '/api/dashboard':
            return self.send_json(dashboard(qs.get('role', ['client'])[0]))
        if path == '/api/cases':
            con = db(); rows = [dict(x) for x in con.execute('SELECT c.*,u.name specialist_name FROM cases c LEFT JOIN users u ON u.id=c.specialist_id ORDER BY c.updated_at DESC').fetchall()]; con.close()
            return self.send_json(rows)
        if path.startswith('/api/cases/') and path.endswith('/export'):
            cid = path.split('/')[-2]
            body = case_export_bytes(cid)
            return self.send_bytes(body, 'application/zip', f'LegalAIZit_Expediente_{cid}.zip') if body else self.send_json({'error': 'Caso no encontrado'}, 404)
        if path.startswith('/api/cases/'):
            cid = path.split('/')[-1]
            obj = case_detail(cid)
            return self.send_json(obj or {}, 200 if obj else 404)
        if path == '/api/documents':
            con = db(); rows = [dict(x) for x in con.execute('SELECT id,case_id,product_code,kind,name,mime_type,created_at,updated_at,version,status FROM documents ORDER BY updated_at DESC').fetchall()]; con.close()
            return self.send_json(rows)
        if path.startswith('/api/documents/') and path.endswith('/download'):
            did = path.split('/')[-2]
            con = db(); row = con.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone(); con.close()
            return self.send_file(row['file_path'], row['name']) if row and row['file_path'] else self.send_json({'error': 'Documento no disponible'}, 404)
        if path.startswith('/api/documents/'):
            did = path.split('/')[-1]
            con = db(); row = con.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone(); versions = [dict(x) for x in con.execute('SELECT * FROM document_versions WHERE document_id=? ORDER BY id DESC', (did,)).fetchall()] if row else []; con.close()
            obj = dict(row) if row else {}; obj['versions'] = versions
            return self.send_json(obj, 200 if row else 404)
        if path.startswith('/api/attachments/') and path.endswith('/download'):
            aid = path.split('/')[-2]
            con = db(); row = con.execute('SELECT * FROM attachments WHERE id=?', (aid,)).fetchone(); con.close()
            return self.send_file(row['file_path'], row['name']) if row else self.send_json({'error': 'Soporte no encontrado'}, 404)
        if path == '/api/users':
            con = db(); rows = [dict(x) for x in con.execute('SELECT * FROM users ORDER BY role,name').fetchall()]; con.close()
            return self.send_json(rows)
        if path == '/api/reviews':
            con = db(); rows = [dict(x) for x in con.execute("SELECT c.id,c.product_code,c.title,c.risk,c.status,c.review_status,c.updated_at,u.name specialist_name FROM cases c LEFT JOIN users u ON u.id=c.specialist_id WHERE c.review_status!='Aprobado' ORDER BY CASE c.risk WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END,c.updated_at DESC").fetchall()]; con.close()
            return self.send_json(rows)
        if path == '/api/legal-studio':
            con = db(); obj = STUDIO.summary(con); con.close(); return self.send_json(obj)
        if path.startswith('/api/legal-studio/') and path.endswith('/export'):
            code = path.split('/')[-2]
            con = db(); body = STUDIO.export_bytes(con, code); con.close()
            return self.send_bytes(body, 'application/json', f'LegalAIZit_{code}_paquete_juridico.json') if body else self.send_json({'error': 'Producto no encontrado'}, 404)
        if path.startswith('/api/legal-studio/'):
            code = path.split('/')[-1]
            con = db(); obj = STUDIO.detail(con, code); con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path == '/api/governance':
            return self.send_json(governance())
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path.startswith('/api/cases/') and path.endswith('/attachments'):
                cid = path.split('/')[-2]
                fields, files = self.read_multipart()
                if not files:
                    return self.send_json({'error': 'No se recibió ningún archivo.'}, 400)
                if not case_detail(cid):
                    return self.send_json({'error': 'Caso no encontrado.'}, 404)
                f = files[0]
                if len(f['data']) > MAX_UPLOAD:
                    return self.send_json({'error': 'El archivo supera el límite de 10 MB.'}, 400)
                folder = UPLOADS / cid
                folder.mkdir(parents=True, exist_ok=True)
                aid = 'ATT-' + uuid.uuid4().hex[:8].upper()
                safe = safe_filename(f['filename'])
                target = folder / f'{aid}_{safe}'
                target.write_bytes(f['data'])
                t = now(); category = fields.get('category', 'Soporte general')
                con = db()
                con.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?,?)', (aid, cid, f['filename'], f['content_type'], len(f['data']), category, str(target), t))
                con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Cargar y clasificar soportes'", (t, cid))
                con.execute('UPDATE cases SET updated_at=? WHERE id=?', (t, cid))
                con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (cid, 'attachment', f'Soporte cargado: {f["filename"]} ({category}).', t))
                audit(con, 'USR-CLIENT', 'attachment', aid, 'upload', {'case_id': cid, 'name': f['filename'], 'size': len(f['data']), 'category': category})
                con.commit(); con.close()
                return self.send_json({'ok': True, 'attachment_id': aid, 'name': f['filename']}, 201)

            data = self.read_json()
            if path == '/api/diagnose':
                return self.send_json(diagnose(data.get('product_code'), data.get('answers') or {}, strict=bool(data.get('strict'))))
            if path == '/api/cases':
                return self.send_json(create_case(data.get('product_code'), data.get('answers') or {}, data.get('title'), data.get('owner_id', 'USR-CLIENT')), 201)
            if path.startswith('/api/cases/') and path.endswith('/regenerate'):
                cid = path.split('/')[-2]
                case = case_detail(cid)
                if not case:
                    return self.send_json({'error': 'Caso no encontrado'}, 404)
                docs = generate_case_documents(cid, case['product_code'], case['answers'], case['result'], actor=data.get('actor', 'USR-ADMIN'), note=data.get('note', 'Regeneración desde expediente v1.1'))
                con = db(); con.execute('UPDATE cases SET updated_at=? WHERE id=?', (now(), cid)); con.commit(); con.close()
                return self.send_json({'ok': True, 'documents': docs})
            if path.startswith('/api/cases/') and path.endswith('/assign'):
                cid = path.split('/')[-2]; specialist = data.get('specialist_id'); t = now(); con = db()
                con.execute('UPDATE cases SET specialist_id=?,review_status=?,status=?,updated_at=? WHERE id=?', (specialist, 'Asignado', 'En revisión', t, cid))
                con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (cid, 'assignment', f'Caso asignado a {specialist}.', t))
                audit(con, specialist, 'case', cid, 'assign', {'specialist_id': specialist})
                con.commit(); con.close(); return self.send_json({'ok': True})
            if path.startswith('/api/cases/') and path.endswith('/review'):
                cid = path.split('/')[-2]; action = data.get('action'); comment = data.get('comment', ''); specialist = data.get('specialist_id', 'USR-COMM')
                status_map = {'approve': ('Aprobado', 'Completado'), 'request_info': ('Información requerida', 'Pendiente de información'), 'reject': ('Rechazado', 'Requiere ajuste')}
                review_status, status = status_map.get(action, ('Pendiente', 'En revisión'))
                rid = 'REV-' + uuid.uuid4().hex[:8].upper(); t = now(); con = db()
                con.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)', (rid, cid, specialist, action, comment, t))
                con.execute('UPDATE cases SET review_status=?,status=?,specialist_id=?,updated_at=? WHERE id=?', (review_status, status, specialist, t, cid))
                if action == 'approve':
                    con.execute("UPDATE documents SET status='Aprobado',updated_at=? WHERE case_id=? AND kind!='audit'", (t, cid))
                    con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label IN ('Asignar y obtener revisión profesional','Aprobar versión documental para uso')", (t, cid))
                elif action == 'request_info':
                    con.execute("UPDATE case_tasks SET status='Pendiente',updated_at=? WHERE case_id=? AND label='Cargar y clasificar soportes'", (t, cid))
                con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (cid, 'review', f'Revisión: {review_status}. {comment}', t))
                audit(con, specialist, 'case', cid, action, comment)
                con.commit(); con.close(); return self.send_json({'ok': True, 'review_status': review_status, 'status': status})
            if path.startswith('/api/tasks/') and path.endswith('/toggle'):
                tid = path.split('/')[-2]
                con = db(); row = con.execute('SELECT * FROM case_tasks WHERE id=?', (tid,)).fetchone()
                if not row:
                    con.close(); return self.send_json({'error': 'Tarea no encontrada'}, 404)
                new_status = 'Completada' if row['status'] != 'Completada' else 'Pendiente'; t = now()
                con.execute('UPDATE case_tasks SET status=?,updated_at=? WHERE id=?', (new_status, t, tid))
                con.execute('INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)', (row['case_id'], 'task', f'Tarea “{row["label"]}” marcada como {new_status}.', t))
                audit(con, data.get('actor', 'USR-CLIENT'), 'task', tid, 'toggle', {'status': new_status})
                con.commit(); con.close(); return self.send_json({'ok': True, 'status': new_status})
            if path.startswith('/api/legal-studio/'):
                parts = path.strip('/').split('/')
                if len(parts) >= 4:
                    code, action = parts[2], parts[3]
                    con = db()
                    try:
                        if action == 'validate':
                            result = STUDIO.validate(code, data.get('content') or {})
                            con.close(); return self.send_json(result, 200 if result['valid'] else 422)
                        if action == 'save':
                            result = STUDIO.save(con, code, data.get('content') or {}, data.get('actor', 'USR-ADMIN'),
                                                 data.get('note', 'Actualización desde Studio Jurídico.'),
                                                 data.get('workflow_status', 'Borrador interno'))
                            audit(con, data.get('actor', 'USR-ADMIN'), 'legal_product', code, 'save_content',
                                  {'revision_id': result['revision_id'], 'workflow_status': result['workflow_status'], 'hash': result['content_hash']})
                            con.commit(); con.close(); return self.send_json(result, 201)
                        if action == 'restore':
                            result = STUDIO.restore(con, code, int(data.get('revision_id')), data.get('actor', 'USR-ADMIN'))
                            audit(con, data.get('actor', 'USR-ADMIN'), 'legal_product', code, 'restore_content', {'revision_id': data.get('revision_id')})
                            con.commit(); con.close(); return self.send_json(result, 201)
                    except Exception:
                        con.close(); raise
            if path == '/api/reset-demo':
                init_db(reset=True); return self.send_json({'ok': True})
            return self.send_json({'error': 'Ruta no encontrada'}, 404)
        except ValueError as exc:
            return self.send_json({'error': str(exc)}, 400)
        except Exception as exc:
            traceback.print_exc()
            return self.send_json({'error': 'Error interno del prototipo', 'detail': str(exc)}, 500)


def main():
    init_db()
    port = PORT
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
    server = ThreadingHTTPServer((HOST, port), Handler)
    url = f'http://{HOST}:{port}'
    print(f'LegalAIZ.it v{VERSION} disponible en {url}')
    if '--no-browser' not in sys.argv:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')


if __name__ == '__main__':
    main()
