from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import json

STAGES = [
    'Inventariado',
    'Texto parcial cotejado',
    'Importación estructurada',
    'En revisión jurídica',
    'En QA técnico',
    'Aprobado para piloto',
]
ISSUE_STATUSES = {'Abierta', 'En curso', 'Resuelta', 'Aceptada como limitación'}
SEVERITIES = {'Crítica', 'Alta', 'Media', 'Baja'}


class CanonicalImportCenter:
    def __init__(self, packages, products, templates, interviews, rules, sources, scenarios):
        self.packages = {x['product_code']: x for x in packages}
        self.products = {x['code']: x for x in products}
        self.templates = templates
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.scenarios = scenarios

    @staticmethod
    def now():
        return datetime.now().isoformat(timespec='seconds')

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_package_snapshots(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          snapshot_json TEXT NOT NULL,
          snapshot_hash TEXT NOT NULL,
          source_file TEXT,
          source_sha256 TEXT,
          source_size INTEGER,
          created_by TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cps_product ON canonical_package_snapshots(product_code,id DESC);
        CREATE TABLE IF NOT EXISTS canonical_package_state(
          product_code TEXT PRIMARY KEY,
          stage TEXT NOT NULL,
          current_snapshot_id INTEGER NOT NULL,
          technical_score INTEGER NOT NULL,
          canonical_score INTEGER NOT NULL,
          source_binary_status TEXT NOT NULL,
          legal_approval_status TEXT NOT NULL DEFAULT 'Pendiente',
          legal_approved_by TEXT,
          qa_status TEXT NOT NULL DEFAULT 'Pendiente',
          qa_approved_by TEXT,
          updated_by TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(current_snapshot_id) REFERENCES canonical_package_snapshots(id)
        );
        CREATE TABLE IF NOT EXISTS canonical_cotejo_issues(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          area TEXT NOT NULL,
          severity TEXT NOT NULL,
          title TEXT NOT NULL,
          detail TEXT NOT NULL,
          status TEXT NOT NULL,
          owner_role TEXT NOT NULL,
          source_ref TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cci_product ON canonical_cotejo_issues(product_code,status,severity);
        CREATE TABLE IF NOT EXISTS canonical_variable_mappings(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          canonical_token TEXT NOT NULL,
          canonical_label TEXT,
          app_field TEXT,
          template_variable TEXT,
          status TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(product_code,canonical_token,template_variable)
        );
        ''')
        columns = {row[1] for row in con.execute('PRAGMA table_info(canonical_package_state)').fetchall()}
        if 'legal_approved_by' not in columns:
            con.execute('ALTER TABLE canonical_package_state ADD COLUMN legal_approved_by TEXT')
        if 'qa_approved_by' not in columns:
            con.execute('ALTER TABLE canonical_package_state ADD COLUMN qa_approved_by TEXT')

    def _counts(self, code):
        templates = [t for t in self.templates if t.get('product_code') == code]
        questions = self.interviews.get(code, {}).get('questions', [])
        rules = self.rules.get(code, [])
        sources = self.sources.get(code, [])
        scenarios = self.scenarios.get(code, [])
        return {
            'templates': len(templates),
            'template_ids': [t.get('template_id') for t in templates],
            'questions': len(questions),
            'rules': len(rules),
            'sources': len(sources),
            'tests': len(scenarios),
        }

    def coverage(self, code):
        p = self.packages[code]
        c = self._counts(code)
        expected_docs = max(1, len(p.get('expected_documents', [])))
        qmin = max(1, int(p.get('expected_min_questions', 1)))
        rmin = max(1, int(p.get('expected_min_rules', 1)))
        smin = max(1, int(p.get('expected_min_sources', 1)))
        # Technical score assesses whether the app has structured artifacts, not whether the legal text is complete.
        technical = round(
            min(1, c['templates'] / expected_docs) * 30
            + min(1, c['questions'] / qmin) * 22
            + min(1, c['rules'] / rmin) * 22
            + min(1, c['sources'] / smin) * 14
            + min(1, c['tests'] / 10) * 12
        )
        canonical = int(p.get('canonical_text_coverage', 0))
        missing_docs = max(0, expected_docs - c['templates'])
        return {
            **c,
            'expected_documents': expected_docs,
            'expected_document_names': p.get('expected_documents', []),
            'missing_document_templates': missing_docs,
            'technical_score': max(0, min(100, technical)),
            'canonical_score': max(0, min(100, canonical)),
            'question_target': qmin,
            'rule_target': rmin,
            'source_target': smin,
        }

    def _initial_stage(self, p):
        tier = p.get('import_tier', '')
        if 'Texto' in tier or 'cotejad' in tier or 'fórmulas' in tier or 'Modelos' in tier or 'Contrato' in tier or 'Modalidades' in tier or 'Semáforo' in tier or 'Clasificador' in tier or 'Reglas' in tier:
            return 'Texto parcial cotejado'
        return 'Inventariado'

    def _seed_issues(self, con, code, p, cov):
        if con.execute('SELECT 1 FROM canonical_cotejo_issues WHERE product_code=? LIMIT 1', (code,)).fetchone():
            return
        t = self.now()
        issues = [
            ('Fuente canónica', 'Crítica', 'Binario canónico no incorporado',
             f"El archivo {p['source_file']} está referenciado, pero sus bytes no están dentro del prototipo. No puede declararse importación literal.",
             'Abogada/o especialista', p['source_file']),
            ('Texto jurídico', 'Alta', 'Cotejo literal incompleto',
             f"La cobertura textual canónica registrada es {p.get('canonical_text_coverage', 0)}%. Debe verificarse cada cláusula, anexo, tabla y nota contra el original.",
             'Abogada/o especialista', p['source_file']),
            ('Publicación', 'Alta', 'Aprobación jurídica y QA pendientes',
             'Ninguna plantilla derivada debe publicarse hasta que la misma revisión supere revisión jurídica y QA técnico.',
             'Administración', 'Flujo de aprobación dual'),
        ]
        if cov['missing_document_templates']:
            issues.append(('Entregables', 'Alta', 'Cobertura documental incompleta',
                           f"El paquete espera {cov['expected_documents']} entregables y la fábrica contiene {cov['templates']} plantillas para este producto.",
                           'Producto y desarrollo', ', '.join(p.get('expected_documents', []))))
        if cov['questions'] < cov['question_target']:
            issues.append(('Entrevista', 'Media', 'Entrevista por debajo del objetivo canónico',
                           f"Existen {cov['questions']} preguntas estructuradas frente a un objetivo mínimo de {cov['question_target']}.",
                           'Producto jurídico', 'Entrevista canónica'))
        if cov['rules'] < cov['rule_target']:
            issues.append(('Reglas', 'Alta', 'Reglas por debajo del objetivo canónico',
                           f"Existen {cov['rules']} reglas frente a un objetivo mínimo de {cov['rule_target']}.",
                           'Abogada/o + desarrollo', 'Motor de riesgo'))
        if cov['sources'] < cov['source_target']:
            issues.append(('Fuentes', 'Alta', 'Fuentes estructuradas insuficientes',
                           f"Existen {cov['sources']} fuentes vinculadas frente a un objetivo mínimo de {cov['source_target']}.",
                           'Investigación jurídica', 'Fuentes oficiales'))
        for area, severity, title, detail, owner, source_ref in issues:
            con.execute('''INSERT INTO canonical_cotejo_issues(product_code,area,severity,title,detail,status,owner_role,source_ref,created_at,updated_at)
                           VALUES(?,?,?,?,?,'Abierta',?,?,?,?)''',
                        (code, area, severity, title, detail, owner, source_ref, t, t))

    def _seed_mappings(self, con, code):
        if con.execute('SELECT 1 FROM canonical_variable_mappings WHERE product_code=? LIMIT 1', (code,)).fetchone():
            return
        t = self.now()
        question_map = {q.get('id'): q.get('label', q.get('id')) for q in self.interviews.get(code, {}).get('questions', []) if q.get('id')}
        template_vars = {}
        for tpl in self.templates:
            if tpl.get('product_code') != code:
                continue
            for v in tpl.get('variables', []):
                if v.get('id'):
                    template_vars[v['id']] = v.get('label', v['id'])
        all_ids = sorted(set(question_map) | set(template_vars))
        for vid in all_ids:
            in_q = vid in question_map
            in_t = vid in template_vars
            status = 'Alineado automáticamente' if in_q and in_t else 'Revisión pendiente'
            label = question_map.get(vid) or template_vars.get(vid) or vid
            token = f'[[{label.upper()}]]'
            note = 'ID común entre entrevista y plantilla.' if in_q and in_t else ('Variable solo presente en entrevista.' if in_q else 'Variable solo presente en plantilla.')
            con.execute('''INSERT INTO canonical_variable_mappings(product_code,canonical_token,canonical_label,app_field,template_variable,status,note,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(product_code,canonical_token,template_variable) DO NOTHING''',
                        (code, token, label, vid if in_q else None, vid if in_t else None, status, note, t, t))

    def init_baselines(self, con):
        for code, p in self.packages.items():
            cov = self.coverage(code)
            state = con.execute('SELECT * FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
            if not state:
                raw = json.dumps(p, ensure_ascii=False, sort_keys=True)
                digest = sha256(raw.encode()).hexdigest()
                cur = con.execute('''INSERT INTO canonical_package_snapshots(product_code,snapshot_json,snapshot_hash,source_file,created_by,note,created_at)
                                     VALUES(?,?,?,?,?,?,?)''',
                                  (code, raw, digest, p.get('source_file'), 'system', 'Registro canónico inicial v1.4 construido a partir del inventario y extractos verificados.', self.now()))
                con.execute('''INSERT INTO canonical_package_state(product_code,stage,current_snapshot_id,technical_score,canonical_score,source_binary_status,legal_approval_status,qa_status,updated_by,updated_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)''',
                            (code, self._initial_stage(p), cur.lastrowid, cov['technical_score'], cov['canonical_score'],
                             'Pendiente de incorporación', 'Pendiente', 'Pendiente', 'system', self.now()))
            else:
                con.execute('UPDATE canonical_package_state SET technical_score=?,canonical_score=? WHERE product_code=?',
                            (cov['technical_score'], max(int(state['canonical_score']), cov['canonical_score']), code))
            self._seed_issues(con, code, p, cov)
            self._seed_mappings(con, code)

    def summary(self, con):
        rows = []
        for code in sorted(self.packages):
            p = self.packages[code]
            cov = self.coverage(code)
            state = con.execute('SELECT * FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
            counts = con.execute('''SELECT COUNT(*) total,
                SUM(CASE WHEN status IN ('Abierta','En curso') THEN 1 ELSE 0 END) open_count,
                SUM(CASE WHEN severity='Crítica' AND status IN ('Abierta','En curso') THEN 1 ELSE 0 END) critical_count
                FROM canonical_cotejo_issues WHERE product_code=?''', (code,)).fetchone()
            rows.append({
                'product_code': code,
                'product_title': self.products.get(code, {}).get('title', code),
                'package_title': p['package_title'],
                'source_file': p['source_file'],
                'canonical_version': p['canonical_version'],
                'stage': state['stage'],
                'source_binary_status': state['source_binary_status'],
                'technical_score': state['technical_score'],
                'canonical_score': state['canonical_score'],
                'templates': cov['templates'],
                'expected_documents': cov['expected_documents'],
                'questions': cov['questions'],
                'rules': cov['rules'],
                'sources': cov['sources'],
                'tests': cov['tests'],
                'open_issues': counts['open_count'] or 0,
                'critical_issues': counts['critical_count'] or 0,
            })
        open_total = con.execute("SELECT COUNT(*) FROM canonical_cotejo_issues WHERE status IN ('Abierta','En curso')").fetchone()[0]
        critical_total = con.execute("SELECT COUNT(*) FROM canonical_cotejo_issues WHERE severity='Crítica' AND status IN ('Abierta','En curso')").fetchone()[0]
        return {
            'packages': rows,
            'metrics': {
                'packages': len(rows),
                'technical_average': round(sum(r['technical_score'] for r in rows) / max(1, len(rows))),
                'canonical_average': round(sum(r['canonical_score'] for r in rows) / max(1, len(rows))),
                'open_issues': open_total,
                'critical_issues': critical_total,
                'binaries_pending': sum(r['source_binary_status'] != 'Incorporado y verificado' for r in rows),
                'approved': sum(r['stage'] == 'Aprobado para piloto' for r in rows),
            },
            'stages': STAGES,
        }

    def detail(self, con, code):
        if code not in self.packages:
            return None
        p = self.packages[code]
        cov = self.coverage(code)
        state = con.execute('SELECT * FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
        cov['technical_score'] = state['technical_score']
        cov['canonical_score'] = state['canonical_score']
        issues = [dict(x) for x in con.execute('SELECT * FROM canonical_cotejo_issues WHERE product_code=? ORDER BY CASE severity WHEN \'Crítica\' THEN 1 WHEN \'Alta\' THEN 2 WHEN \'Media\' THEN 3 ELSE 4 END,id', (code,)).fetchall()]
        mappings = [dict(x) for x in con.execute('SELECT * FROM canonical_variable_mappings WHERE product_code=? ORDER BY status,canonical_label', (code,)).fetchall()]
        snapshots = [dict(x) for x in con.execute('''SELECT id,snapshot_hash,source_file,source_sha256,source_size,created_by,note,created_at
                                                      FROM canonical_package_snapshots WHERE product_code=? ORDER BY id DESC''', (code,)).fetchall()]
        templates = []
        for tpl in self.templates:
            if tpl.get('product_code') == code:
                templates.append({
                    'template_id': tpl.get('template_id'),
                    'kind': tpl.get('kind'),
                    'title': tpl.get('title'),
                    'version_label': tpl.get('version_label'),
                    'blocks': len(tpl.get('blocks', [])),
                    'variables': len(tpl.get('variables', [])),
                    'canonical_status': tpl.get('canonical_status'),
                })
        return {
            'package': p,
            'product': self.products.get(code),
            'state': dict(state),
            'coverage': cov,
            'issues': issues,
            'mappings': mappings,
            'snapshots': snapshots,
            'templates': templates,
            'stages': STAGES,
        }

    def update_stage(self, con, code, stage, actor, note=''):
        if code not in self.packages:
            raise ValueError('Producto no registrado.')
        if stage not in STAGES:
            raise ValueError('Etapa inválida.')
        state = con.execute('SELECT * FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
        if stage in ('Importación estructurada', 'En revisión jurídica', 'En QA técnico', 'Aprobado para piloto') and state['source_binary_status'] != 'Incorporado y verificado':
            raise ValueError('No puede avanzar a esa etapa sin incorporar y verificar el binario canónico.')
        if stage == 'Aprobado para piloto' and (state['legal_approval_status'] != 'Aprobado' or state['qa_status'] != 'Aprobado'):
            raise ValueError('La aprobación para piloto requiere aprobación jurídica y QA.')
        con.execute('UPDATE canonical_package_state SET stage=?,updated_by=?,updated_at=? WHERE product_code=?',
                    (stage, actor, self.now(), code))
        self.add_snapshot(con, code, {'stage': stage, 'note': note, 'package': self.packages[code]}, actor, note or f'Cambio de etapa a {stage}.')
        return {'ok': True, 'stage': stage}

    def update_approval(self, con, code, approval_type, decision, actor, actor_role, comment=''):
        if code not in self.packages:
            raise ValueError('Producto no registrado.')
        if decision not in ('Aprobado', 'Rechazado', 'Pendiente'):
            raise ValueError('Decisión inválida.')
        current = con.execute('SELECT source_binary_status,stage FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
        if decision == 'Aprobado' and current['source_binary_status'] != 'Incorporado y verificado':
            raise ValueError('No puede aprobarse sin incorporar y verificar el binario canónico.')
        if approval_type == 'legal':
            if actor_role != 'specialist':
                raise PermissionError('La aprobación jurídica requiere especialista.')
            field = 'legal_approval_status'
        elif approval_type == 'qa':
            if actor_role != 'admin':
                raise PermissionError('La aprobación de QA requiere administración.')
            state = con.execute('SELECT legal_approval_status,legal_approved_by FROM canonical_package_state WHERE product_code=?', (code,)).fetchone()
            if decision == 'Aprobado' and state['legal_approval_status'] != 'Aprobado':
                raise ValueError('QA solo puede aprobar después de la aprobación jurídica.')
            if decision == 'Aprobado' and str(state['legal_approved_by']) == str(actor):
                raise ValueError('La aprobación jurídica y el QA deben corresponder a personas distintas.')
            field = 'qa_status'
        else:
            raise ValueError('Tipo de aprobación inválido.')
        actor_field = 'legal_approved_by' if approval_type == 'legal' else 'qa_approved_by'
        reset_clause = ",qa_status='Pendiente',qa_approved_by=NULL" if approval_type == 'legal' else ''
        con.execute(f'UPDATE canonical_package_state SET {field}=?,{actor_field}=?{reset_clause},updated_by=?,updated_at=? WHERE product_code=?',
                    (decision, actor, actor, self.now(), code))
        t = self.now()
        con.execute('''INSERT INTO canonical_cotejo_issues(product_code,area,severity,title,detail,status,owner_role,source_ref,created_at,updated_at)
                       VALUES(?,?,?,?,?,'Resuelta',?,?,?,?)''',
                    (code, 'Aprobación', 'Media', f'Decisión {approval_type}: {decision}', comment or 'Decisión registrada.', actor_role, actor, t, t))
        return {'ok': True, 'approval_type': approval_type, 'decision': decision}

    def update_issue(self, con, issue_id, status, actor, note=''):
        if status not in ISSUE_STATUSES:
            raise ValueError('Estado de brecha inválido.')
        row = con.execute('SELECT * FROM canonical_cotejo_issues WHERE id=?', (issue_id,)).fetchone()
        if not row:
            raise ValueError('Brecha no encontrada.')
        detail = row['detail']
        if note:
            detail = f"{detail}\n\nActualización de {actor}: {note}"
        con.execute('UPDATE canonical_cotejo_issues SET status=?,detail=?,updated_at=? WHERE id=?',
                    (status, detail, self.now(), issue_id))
        return {'ok': True, 'id': issue_id, 'status': status}

    def save_mapping(self, con, code, canonical_token, canonical_label, app_field, template_variable, status, note, actor):
        if code not in self.packages:
            raise ValueError('Producto no registrado.')
        if not canonical_token:
            raise ValueError('El token canónico es obligatorio.')
        t = self.now()
        con.execute('''INSERT INTO canonical_variable_mappings(product_code,canonical_token,canonical_label,app_field,template_variable,status,note,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(product_code,canonical_token,template_variable) DO UPDATE SET canonical_label=excluded.canonical_label,app_field=excluded.app_field,status=excluded.status,note=excluded.note,updated_at=excluded.updated_at''',
                    (code, canonical_token, canonical_label, app_field or None, template_variable or None, status or 'Revisión pendiente', note or f'Actualizado por {actor}', t, t))
        return {'ok': True}

    def add_snapshot(self, con, code, snapshot, actor, note='', source_file=None, source_sha256=None, source_size=None):
        raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        digest = sha256(raw.encode()).hexdigest()
        cur = con.execute('''INSERT INTO canonical_package_snapshots(product_code,snapshot_json,snapshot_hash,source_file,source_sha256,source_size,created_by,note,created_at)
                             VALUES(?,?,?,?,?,?,?,?,?)''',
                          (code, raw, digest, source_file or self.packages[code].get('source_file'), source_sha256, source_size, actor, note, self.now()))
        con.execute('UPDATE canonical_package_state SET current_snapshot_id=?,updated_by=?,updated_at=? WHERE product_code=?',
                    (cur.lastrowid, actor, self.now(), code))
        return {'ok': True, 'snapshot_id': cur.lastrowid, 'snapshot_hash': digest}

    def register_source(self, con, code, filename, file_sha256, size, actor, extraction, verified=False):
        if code not in self.packages:
            raise ValueError('Producto no registrado.')
        status = 'Incorporado y verificado' if verified else 'Incorporado con hash; verificación pendiente'
        stage = 'Importación estructurada' if verified else 'Texto parcial cotejado'
        snapshot = {
            'package': self.packages[code],
            'source_file': filename,
            'source_sha256': file_sha256,
            'source_size': size,
            'source_verified': bool(verified),
            'extraction': extraction,
        }
        note = ('Binario canónico incorporado, identificado expresamente por el operador y extracción estructurada registrada.'
                if verified else
                'Binario incorporado con hash y extracción registrada; identidad canónica aún pendiente de verificación humana.')
        result = self.add_snapshot(con, code, snapshot, actor, note, filename, file_sha256, size)
        cov = self.coverage(code)
        score_floor = 70 if verified else 55
        con.execute('''UPDATE canonical_package_state SET source_binary_status=?,stage=?,technical_score=?,canonical_score=?,updated_by=?,updated_at=? WHERE product_code=?''',
                    (status, stage, cov['technical_score'], max(cov['canonical_score'], score_floor), actor, self.now(), code))
        if verified:
            con.execute("UPDATE canonical_cotejo_issues SET status='Resuelta',updated_at=? WHERE product_code=? AND title IN ('Binario canónico no incorporado','Binario incorporado pendiente de verificación')", (self.now(), code))
        else:
            con.execute("UPDATE canonical_cotejo_issues SET title='Binario incorporado pendiente de verificación',detail=?,status='En curso',updated_at=? WHERE product_code=? AND title IN ('Binario canónico no incorporado','Binario incorporado pendiente de verificación')",
                        (f'El archivo {filename} fue incorporado con SHA-256 {file_sha256}, pero una persona autorizada debe confirmar que corresponde al original canónico esperado.', self.now(), code))
        return {**result, 'source_binary_status': status, 'verified': bool(verified)}

    def export_bytes(self, con, code=None):
        payload = self.detail(con, code) if code else self.summary(con)
        if not payload:
            return None
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        if code:
            return raw
        out = BytesIO()
        with ZipFile(out, 'w', ZIP_DEFLATED) as z:
            z.writestr('resumen_cotejo.json', raw)
            for product_code in sorted(self.packages):
                z.writestr(f'{product_code}_cotejo.json', json.dumps(self.detail(con, product_code), ensure_ascii=False, indent=2))
        return out.getvalue()
