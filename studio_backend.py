from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json


WORKFLOW_STATUSES = [
    'Borrador interno',
    'En revisión jurídica',
    'En QA técnico',
    'Aprobado para piloto',
]
QUESTION_TYPES = {'text', 'textarea', 'number', 'date', 'select', 'multiselect', 'checkbox', 'email'}
RISK_VALUES = {'green', 'yellow', 'red'}


class LegalStudio:
    def __init__(self, products, interviews, rules, sources, scenarios, packages, risk_order, eval_conditions, sast_matcher=None):
        self.products = products
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.scenarios = scenarios
        self.packages = packages
        self.risk_order = risk_order
        self.eval_conditions = eval_conditions
        self.sast_matcher = sast_matcher
        self.scenario_risk_hook = None

    @staticmethod
    def now():
        return datetime.now().isoformat(timespec='seconds')

    def product(self, code):
        return next((p for p in self.products if p.get('code') == code), None)

    def package(self, code):
        return next((p for p in self.packages if p.get('product_code') == code), None)

    def payload(self, code):
        p = self.product(code)
        if not p:
            return None
        return {
            'product': json.loads(json.dumps(p, ensure_ascii=False)),
            'interview': json.loads(json.dumps(self.interviews.get(code, {}), ensure_ascii=False)),
            'rules': json.loads(json.dumps(self.rules.get(code, []), ensure_ascii=False)),
            'sources': json.loads(json.dumps(self.sources.get(code, []), ensure_ascii=False)),
            'scenarios': json.loads(json.dumps(self.scenarios.get(code, []), ensure_ascii=False)),
        }

    def apply(self, code, content):
        p = content['product']
        p['code'] = code
        existing = self.product(code)
        if existing is None:
            self.products.append(p)
        else:
            existing.clear(); existing.update(p)
        self.interviews[code] = content['interview']
        self.rules[code] = content['rules']
        self.sources[code] = content['sources']
        self.scenarios[code] = content['scenarios']
        pkg = self.package(code)
        if pkg:
            pkg['version'] = p.get('version', pkg.get('version'))
            pkg['question_count'] = len(content['interview'].get('questions', []))
            pkg['rule_count'] = len(content['rules'])
            pkg['source_count'] = len(content['sources'])
            pkg['test_count'] = len(content['scenarios'])
            pkg['publication_status'] = p.get('publication_status', pkg.get('publication_status'))

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS legal_content_versions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          version_label TEXT NOT NULL,
          workflow_status TEXT NOT NULL,
          actor TEXT NOT NULL,
          note TEXT,
          content_json TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_legal_versions_product ON legal_content_versions(product_code,id DESC);
        CREATE TABLE IF NOT EXISTS legal_content_state(
          product_code TEXT PRIMARY KEY,
          workflow_status TEXT NOT NULL,
          current_revision_id INTEGER NOT NULL,
          updated_at TEXT NOT NULL,
          updated_by TEXT NOT NULL,
          FOREIGN KEY(current_revision_id) REFERENCES legal_content_versions(id)
        );
        ''')

    def init_baselines(self, con):
        for p in self.products:
            code = p['code']
            state = con.execute('SELECT 1 FROM legal_content_state WHERE product_code=?', (code,)).fetchone()
            if state:
                continue
            content = self.payload(code)
            raw = json.dumps(content, ensure_ascii=False, sort_keys=True)
            digest = sha256(raw.encode('utf-8')).hexdigest()
            status = 'Borrador interno'
            cur = con.execute(
                '''INSERT INTO legal_content_versions(product_code,version_label,workflow_status,actor,note,content_json,content_hash,created_at)
                   VALUES(?,?,?,?,?,?,?,?)''',
                (code, p.get('version', '1.0'), status, 'system', 'Línea base canónica del prototipo v1.2.', raw, digest, self.now()),
            )
            rid = cur.lastrowid
            con.execute(
                'INSERT INTO legal_content_state(product_code,workflow_status,current_revision_id,updated_at,updated_by) VALUES(?,?,?,?,?)',
                (code, status, rid, self.now(), 'system'),
            )

    def load_active(self, con):
        rows = con.execute('''SELECT s.product_code,v.content_json FROM legal_content_state s
                              JOIN legal_content_versions v ON v.id=s.current_revision_id''').fetchall()
        for row in rows:
            try:
                self.apply(row['product_code'], json.loads(row['content_json']))
            except Exception:
                continue

    def _condition_fields(self, node):
        if not isinstance(node, dict):
            return []
        if 'all' in node:
            out = []
            for x in node['all']:
                out.extend(self._condition_fields(x))
            return out
        if 'any' in node:
            out = []
            for x in node['any']:
                out.extend(self._condition_fields(x))
            return out
        return [node.get('field')] if node.get('field') else []

    def _scenario_risk(self, code, content, answers):
        p = content['product']
        risk = 'green' if code == 'CO-TR-001' else p.get('base_risk', 'yellow')
        for rule in content['rules']:
            try:
                if self.eval_conditions(rule.get('conditions'), answers):
                    if self.risk_order.get(rule.get('risk'), 0) > self.risk_order.get(risk, 0):
                        risk = rule['risk']
            except Exception:
                continue
        if code == 'CO-TR-001' and self.sast_matcher and self.sast_matcher(answers):
            if self.risk_order.get(risk, 0) < self.risk_order['yellow']:
                risk = 'yellow'
        if self.scenario_risk_hook:
            try:
                hooked = self.scenario_risk_hook(code, content, answers)
                if hooked in self.risk_order and self.risk_order[hooked] > self.risk_order.get(risk, 0):
                    risk = hooked
            except Exception:
                pass
        return risk

    def validate(self, code, content):
        errors, warnings = [], []
        if not isinstance(content, dict):
            return {'valid': False, 'errors': ['El contenido debe ser un objeto JSON.'], 'warnings': [], 'metrics': {}, 'scenario_results': []}
        for key in ('product', 'interview', 'rules', 'sources', 'scenarios'):
            if key not in content:
                errors.append(f'Falta la sección {key}.')
        if errors:
            return {'valid': False, 'errors': errors, 'warnings': warnings, 'metrics': {}, 'scenario_results': []}
        p = content['product']
        if p.get('code') not in (None, code): errors.append('El código del producto no coincide con la ruta.')
        for field in ('title', 'summary', 'version', 'vertical'):
            if not str(p.get(field, '')).strip(): errors.append(f'La ficha requiere {field}.')
        if p.get('base_risk') not in RISK_VALUES: errors.append('El riesgo base debe ser green, yellow o red.')

        interview = content['interview']
        questions = interview.get('questions', []) if isinstance(interview, dict) else []
        if not questions: errors.append('La entrevista debe contener preguntas.')
        qids, qsections = set(), set(interview.get('sections', []))
        for i, q in enumerate(questions, 1):
            qid = str(q.get('id', '')).strip()
            if not qid: errors.append(f'Pregunta {i}: falta id.')
            elif qid in qids: errors.append(f'Pregunta duplicada: {qid}.')
            qids.add(qid)
            if not str(q.get('label', '')).strip(): errors.append(f'Pregunta {qid or i}: falta etiqueta.')
            if q.get('type') not in QUESTION_TYPES: errors.append(f'Pregunta {qid or i}: tipo no permitido.')
            if q.get('type') in ('select', 'multiselect') and not q.get('options'): errors.append(f'Pregunta {qid or i}: requiere opciones.')
            section = q.get('section')
            if section and section not in qsections: warnings.append(f'Pregunta {qid}: sección “{section}” no está declarada.')
            show = q.get('show_if')
            if show and show.get('field') not in qids and show.get('field') not in {x.get('id') for x in questions}:
                warnings.append(f'Pregunta {qid}: show_if referencia un campo inexistente.')

        rules = content['rules'] if isinstance(content['rules'], list) else []
        rids = set()
        for i, rule in enumerate(rules, 1):
            rid = str(rule.get('id', '')).strip()
            if not rid: errors.append(f'Regla {i}: falta id.')
            elif rid in rids: errors.append(f'Regla duplicada: {rid}.')
            rids.add(rid)
            if rule.get('risk') not in RISK_VALUES: errors.append(f'Regla {rid or i}: riesgo inválido.')
            if not rule.get('conditions'): errors.append(f'Regla {rid or i}: faltan condiciones.')
            if not str(rule.get('message', '')).strip(): errors.append(f'Regla {rid or i}: falta mensaje.')
            if not str(rule.get('action', '')).strip(): errors.append(f'Regla {rid or i}: falta acción.')
            for field in self._condition_fields(rule.get('conditions')):
                if field not in qids:
                    warnings.append(f'Regla {rid}: referencia el campo no declarado “{field}”.')

        source_ids = set()
        for i, source in enumerate(content['sources'], 1):
            sid = str(source.get('id', '')).strip()
            if not sid: errors.append(f'Fuente {i}: falta id.')
            elif sid in source_ids: errors.append(f'Fuente duplicada: {sid}.')
            source_ids.add(sid)
            if not str(source.get('title', '')).strip(): errors.append(f'Fuente {sid or i}: falta título.')
            if not source.get('last_verified'):
                warnings.append(f'Fuente {sid or i}: no registra fecha de última verificación.')

        scenario_ids, scenario_results = set(), []
        for i, scenario in enumerate(content['scenarios'], 1):
            sid = str(scenario.get('id', '')).strip()
            if not sid: errors.append(f'Caso de prueba {i}: falta id.')
            elif sid in scenario_ids: errors.append(f'Caso de prueba duplicado: {sid}.')
            scenario_ids.add(sid)
            expected = scenario.get('expected_risk')
            if expected not in RISK_VALUES:
                errors.append(f'Caso {sid or i}: riesgo esperado inválido.')
                continue
            actual = self._scenario_risk(code, content, scenario.get('answers') or {})
            passed = actual == expected
            scenario_results.append({'id': sid, 'name': scenario.get('name'), 'expected': expected, 'actual': actual, 'passed': passed})
            if not passed:
                errors.append(f'Caso {sid}: esperaba {expected} y obtuvo {actual}.')

        metrics = {
            'questions': len(questions),
            'required_questions': sum(bool(q.get('required')) for q in questions),
            'rules': len(rules),
            'blocking_rules': sum(bool(r.get('blocking')) or r.get('risk') == 'red' for r in rules),
            'sources': len(content['sources']),
            'scenarios': len(content['scenarios']),
            'passed_scenarios': sum(x['passed'] for x in scenario_results),
        }
        return {'valid': not errors, 'errors': errors, 'warnings': sorted(set(warnings)), 'metrics': metrics, 'scenario_results': scenario_results}

    def save(self, con, code, content, actor, note, workflow_status):
        if workflow_status not in WORKFLOW_STATUSES:
            raise ValueError('Estado de flujo no permitido.')
        result = self.validate(code, content)
        if not result['valid']:
            raise ValueError('No se puede guardar: ' + ' '.join(result['errors']))
        content['product']['code'] = code
        content['product']['publication_status'] = 'No publicado profesionalmente · ' + workflow_status
        raw = json.dumps(content, ensure_ascii=False, sort_keys=True)
        digest = sha256(raw.encode('utf-8')).hexdigest()
        version_label = content['product'].get('version', 'sin-versión')
        cur = con.execute(
            '''INSERT INTO legal_content_versions(product_code,version_label,workflow_status,actor,note,content_json,content_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?)''',
            (code, version_label, workflow_status, actor, note, raw, digest, self.now()),
        )
        rid = cur.lastrowid
        con.execute(
            '''INSERT INTO legal_content_state(product_code,workflow_status,current_revision_id,updated_at,updated_by)
               VALUES(?,?,?,?,?)
               ON CONFLICT(product_code) DO UPDATE SET workflow_status=excluded.workflow_status,current_revision_id=excluded.current_revision_id,
                 updated_at=excluded.updated_at,updated_by=excluded.updated_by''',
            (code, workflow_status, rid, self.now(), actor),
        )
        self.apply(code, content)
        return {'revision_id': rid, 'content_hash': digest, 'workflow_status': workflow_status, 'validation': result}

    def restore(self, con, code, revision_id, actor):
        row = con.execute('SELECT * FROM legal_content_versions WHERE id=? AND product_code=?', (revision_id, code)).fetchone()
        if not row:
            raise ValueError('Revisión no encontrada.')
        content = json.loads(row['content_json'])
        return self.save(con, code, content, actor, f'Restauración de revisión #{revision_id}.', 'Borrador interno')

    def detail(self, con, code):
        content = self.payload(code)
        if not content:
            return None
        state = con.execute('SELECT * FROM legal_content_state WHERE product_code=?', (code,)).fetchone()
        revisions = [dict(x) for x in con.execute(
            '''SELECT id,product_code,version_label,workflow_status,actor,note,content_hash,created_at
               FROM legal_content_versions WHERE product_code=? ORDER BY id DESC LIMIT 30''', (code,)
        ).fetchall()]
        return {
            'code': code,
            'workflow_status': state['workflow_status'] if state else 'Borrador interno',
            'updated_at': state['updated_at'] if state else None,
            'updated_by': state['updated_by'] if state else None,
            'current_revision_id': state['current_revision_id'] if state else None,
            'content': content,
            'validation': self.validate(code, content),
            'revisions': revisions,
            'workflow_options': WORKFLOW_STATUSES,
        }

    def summary(self, con):
        states = {x['product_code']: dict(x) for x in con.execute('SELECT * FROM legal_content_state').fetchall()}
        revision_counts = dict(con.execute('SELECT product_code,COUNT(*) FROM legal_content_versions GROUP BY product_code').fetchall())
        rows = []
        for p in self.products:
            code = p['code']
            validation = self.validate(code, self.payload(code))
            state = states.get(code, {})
            rows.append({
                'code': code,
                'title': p.get('title'),
                'vertical': p.get('vertical'),
                'version': p.get('version'),
                'workflow_status': state.get('workflow_status', 'Borrador interno'),
                'updated_at': state.get('updated_at'),
                'updated_by': state.get('updated_by'),
                'revision_count': revision_counts.get(code, 0),
                'valid': validation['valid'],
                'metrics': validation['metrics'],
                'warning_count': len(validation['warnings']),
            })
        return {
            'workflow_options': WORKFLOW_STATUSES,
            'summary': {
                'products': len(rows),
                'revisions': sum(x['revision_count'] for x in rows),
                'valid_products': sum(x['valid'] for x in rows),
                'approved_for_pilot': sum(x['workflow_status'] == 'Aprobado para piloto' for x in rows),
                'questions': sum(x['metrics'].get('questions', 0) for x in rows),
                'rules': sum(x['metrics'].get('rules', 0) for x in rows),
            },
            'products': rows,
        }

    def export_bytes(self, con, code):
        detail = self.detail(con, code)
        if not detail:
            return None
        payload = {
            'schema': 'legalaizit.legal-product.v1',
            'exported_at': self.now(),
            'product_code': code,
            'workflow_status': detail['workflow_status'],
            'current_revision_id': detail['current_revision_id'],
            'content': detail['content'],
            'validation': detail['validation'],
            'revisions': detail['revisions'],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
