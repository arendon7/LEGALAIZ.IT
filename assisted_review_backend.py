from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
from zipfile import ZipFile, ZIP_DEFLATED
import csv
import json

from traceability_backend import semantic_diff, similarity, classification

JOB_STATUSES = {
    'Bloqueado por fuente',
    'Pendiente',
    'Asignado',
    'En cotejo',
    'Listo para QA',
    'Cotejado',
    'Requiere ajuste',
    'Requiere recotejo',
}
LINK_TYPES = {'Literal', 'Adaptado', 'Derivado', 'Referencia', 'Excepción justificada'}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _risk_level(score: float, added: int, omitted: int, link_type: str | None = None) -> str:
    if link_type == 'Excepción justificada':
        return 'alto'
    if score < 25 or omitted >= 18:
        return 'crítico'
    if score < 50 or omitted >= 10 or added >= 12:
        return 'alto'
    if score < 75 or omitted >= 5 or added >= 7:
        return 'medio'
    return 'bajo'


class AssistedReviewWorkbench:
    """Mesa de trabajo para cotejo bloque–fragmento con asignación, control optimista y QA.

    Las sugerencias son determinísticas y no sustituyen la decisión jurídica. Cada propuesta
    crea un vínculo trazable, recibe aprobación jurídica del especialista y queda pendiente de QA.
    """

    def __init__(self, traceability, products: list[dict], intake_plan: list[dict]):
        self.traceability = traceability
        self.products = {x['code']: x for x in products}
        self.plan = {x['product_code']: x for x in intake_plan}

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_review_jobs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          template_id TEXT NOT NULL,
          block_id TEXT NOT NULL,
          revision_id INTEGER,
          block_hash TEXT NOT NULL,
          required_for_gate INTEGER NOT NULL DEFAULT 1,
          priority INTEGER NOT NULL DEFAULT 3,
          status TEXT NOT NULL,
          assigned_to TEXT,
          assigned_at TEXT,
          due_at TEXT,
          active_proposal_id INTEGER,
          version INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(product_code,template_id,block_id)
        );
        CREATE INDEX IF NOT EXISTS idx_crj_queue ON canonical_review_jobs(status,priority,product_code,id);
        CREATE INDEX IF NOT EXISTS idx_crj_assignee ON canonical_review_jobs(assigned_to,status,updated_at DESC);

        CREATE TABLE IF NOT EXISTS canonical_review_proposals(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id INTEGER NOT NULL,
          proposal_version INTEGER NOT NULL,
          fragment_id INTEGER,
          link_type TEXT NOT NULL,
          legal_rationale TEXT NOT NULL,
          effect_assessment TEXT NOT NULL,
          exception_reason TEXT,
          block_hash TEXT NOT NULL,
          source_fragment_hash TEXT,
          similarity_score REAL NOT NULL DEFAULT 0,
          semantic_class TEXT NOT NULL,
          discrepancy_level TEXT NOT NULL,
          added_terms_json TEXT NOT NULL,
          omitted_terms_json TEXT NOT NULL,
          trace_link_id INTEGER,
          status TEXT NOT NULL,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          decided_by TEXT,
          decided_at TEXT,
          qa_comment TEXT,
          FOREIGN KEY(job_id) REFERENCES canonical_review_jobs(id),
          FOREIGN KEY(fragment_id) REFERENCES canonical_source_fragments(id),
          UNIQUE(job_id,proposal_version)
        );
        CREATE INDEX IF NOT EXISTS idx_crp_job ON canonical_review_proposals(job_id,id DESC);

        CREATE TABLE IF NOT EXISTS canonical_review_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          actor TEXT NOT NULL,
          actor_role TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          previous_event_hash TEXT,
          event_hash TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES canonical_review_jobs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cre_job ON canonical_review_events(job_id,id);
        ''')

    def _event(self, con, job_id: int, event_type: str, actor: str, role: str, detail) -> str:
        detail_json = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, sort_keys=True)
        prev = con.execute('SELECT event_hash FROM canonical_review_events WHERE job_id=? ORDER BY id DESC LIMIT 1', (job_id,)).fetchone()
        previous = prev['event_hash'] if prev else ''
        created = _now()
        payload = '|'.join([str(job_id), event_type, actor, role, created, previous, detail_json])
        digest = sha256(payload.encode('utf-8')).hexdigest()
        con.execute('''INSERT INTO canonical_review_events(job_id,event_type,actor,actor_role,detail_json,previous_event_hash,event_hash,created_at)
                       VALUES(?,?,?,?,?,?,?,?)''',
                    (job_id, event_type, actor, role, detail_json, previous or None, digest, created))
        return digest

    @staticmethod
    def verify_chain(events: list[dict]) -> bool:
        previous = ''
        for event in sorted(events, key=lambda x: x['id']):
            payload = '|'.join([
                str(event['job_id']), event['event_type'], event['actor'], event['actor_role'],
                event['created_at'], previous, event['detail_json'],
            ])
            digest = sha256(payload.encode('utf-8')).hexdigest()
            if (event.get('previous_event_hash') or '') != previous or event.get('event_hash') != digest:
                return False
            previous = digest
        return True

    def _priority(self, code: str) -> int:
        value = int((self.plan.get(code) or {}).get('priority', 3))
        return 1 if value <= 1 else (2 if value == 2 else 3)

    def _has_verified_source(self, con, code: str) -> bool:
        return bool(con.execute('SELECT 1 FROM canonical_source_files WHERE product_code=? AND verified=1 LIMIT 1', (code,)).fetchone())

    def init_jobs(self, con, code: str | None = None) -> dict:
        codes = [code] if code else sorted(self.products)
        created = changed = 0
        now = _now()
        for product_code in codes:
            detail = self.traceability.detail(con, product_code)
            if not detail:
                continue
            has_source = self._has_verified_source(con, product_code)
            for block in detail['blocks']:
                if not block['required_for_gate']:
                    continue
                row = con.execute('''SELECT * FROM canonical_review_jobs
                                     WHERE product_code=? AND template_id=? AND block_id=?''',
                                  (product_code, block['template_id'], block['block_id'])).fetchone()
                link = block.get('link') or {}
                dual = link.get('status') == 'Cotejado' and link.get('legal_decision') == 'Aprobado' and link.get('qa_decision') == 'Aprobado'
                if dual and link.get('revision_id') == block.get('revision_id'):
                    target_status = 'Cotejado'
                elif not has_source:
                    target_status = 'Bloqueado por fuente'
                else:
                    target_status = 'Pendiente'
                if not row:
                    cur = con.execute('''INSERT INTO canonical_review_jobs(product_code,template_id,block_id,revision_id,block_hash,required_for_gate,priority,status,version,created_at,updated_at)
                                         VALUES(?,?,?,?,?,?,?, ?,1,?,?)''',
                                      (product_code, block['template_id'], block['block_id'], block.get('revision_id'), block['block_hash'], 1,
                                       self._priority(product_code), target_status, now, now))
                    self._event(con, cur.lastrowid, 'job_created', 'system', 'system', {'status': target_status, 'block_hash': block['block_hash']})
                    created += 1
                    continue
                if row['block_hash'] != block['block_hash'] or (row['revision_id'] or 0) != (block.get('revision_id') or 0):
                    new_status = 'Requiere recotejo' if has_source else 'Bloqueado por fuente'
                    con.execute('''UPDATE canonical_review_jobs SET revision_id=?,block_hash=?,status=?,active_proposal_id=NULL,
                                   version=version+1,updated_at=? WHERE id=?''',
                                (block.get('revision_id'), block['block_hash'], new_status, now, row['id']))
                    self._event(con, row['id'], 'block_revision_changed', 'system', 'system', {
                        'previous_hash': row['block_hash'], 'new_hash': block['block_hash'], 'status': new_status,
                    })
                    changed += 1
                elif row['status'] == 'Bloqueado por fuente' and has_source:
                    con.execute('UPDATE canonical_review_jobs SET status="Pendiente",version=version+1,updated_at=? WHERE id=?', (now, row['id']))
                    self._event(con, row['id'], 'source_available', 'system', 'system', {'status': 'Pendiente'})
                    changed += 1
                elif target_status == 'Cotejado' and row['status'] != 'Cotejado':
                    con.execute('UPDATE canonical_review_jobs SET status="Cotejado",version=version+1,updated_at=? WHERE id=?', (now, row['id']))
                    self._event(con, row['id'], 'trace_link_synchronized', 'system', 'system', {'status': 'Cotejado'})
                    changed += 1
        return {'ok': True, 'created': created, 'changed': changed}

    def _job_row(self, con, job_id: int):
        return con.execute('''SELECT j.*,u.name assigned_name,u.email assigned_email
                              FROM canonical_review_jobs j LEFT JOIN users u ON u.id=j.assigned_to
                              WHERE j.id=?''', (job_id,)).fetchone()

    @staticmethod
    def _check_version(row, expected_version) -> None:
        if expected_version is None:
            return
        if int(expected_version) != int(row['version']):
            raise ValueError('El trabajo cambió desde que fue abierto. Recargue la mesa antes de continuar.')

    def summary(self, con, actor: str | None = None, role: str | None = None) -> dict:
        self.init_jobs(con)
        where = ''
        params: list = []
        if role == 'specialist' and actor:
            where = ' WHERE (assigned_to=? OR assigned_to IS NULL)'
            params = [actor]
        rows = [dict(x) for x in con.execute('SELECT * FROM canonical_review_jobs' + where, params).fetchall()]
        products = []
        for code in sorted(self.products, key=lambda c: (self._priority(c), c)):
            subset = [x for x in rows if x['product_code'] == code]
            total = len(subset)
            done = sum(x['status'] == 'Cotejado' for x in subset)
            products.append({
                'product_code': code,
                'title': self.products[code].get('title', code),
                'priority': self._priority(code),
                'jobs': total,
                'blocked': sum(x['status'] == 'Bloqueado por fuente' for x in subset),
                'pending': sum(x['status'] in {'Pendiente', 'Asignado', 'En cotejo', 'Requiere ajuste', 'Requiere recotejo'} for x in subset),
                'ready_qa': sum(x['status'] == 'Listo para QA' for x in subset),
                'cotejado': done,
                'coverage': round(done * 100 / max(1, total)),
                'verified_sources': con.execute('SELECT COUNT(*) FROM canonical_source_files WHERE product_code=? AND verified=1', (code,)).fetchone()[0],
            })
        counts = {status: sum(x['status'] == status for x in rows) for status in JOB_STATUSES}
        broken = 0
        for job_id in [x['id'] for x in rows]:
            events = [dict(e) for e in con.execute('SELECT * FROM canonical_review_events WHERE job_id=? ORDER BY id', (job_id,)).fetchall()]
            if events and not self.verify_chain(events):
                broken += 1
        return {
            'metrics': {
                'jobs': len(rows),
                'blocked': counts['Bloqueado por fuente'],
                'pending': sum(counts[x] for x in {'Pendiente', 'Asignado', 'En cotejo', 'Requiere ajuste', 'Requiere recotejo'}),
                'ready_qa': counts['Listo para QA'],
                'cotejado': counts['Cotejado'],
                'coverage': round(counts['Cotejado'] * 100 / max(1, len(rows))),
                'broken_event_chains': broken,
            },
            'products': products,
            'notice': 'La mesa organiza el cotejo; ninguna sugerencia automática constituye equivalencia jurídica ni autorización de publicación.',
        }

    def product_detail(self, con, code: str, actor: str | None = None, role: str | None = None) -> dict | None:
        if code not in self.products:
            return None
        self.init_jobs(con, code)
        params: list = [code]
        extra = ''
        if role == 'specialist' and actor:
            extra = ' AND (j.assigned_to=? OR j.assigned_to IS NULL)'
            params.append(actor)
        rows = [dict(x) for x in con.execute('''SELECT j.*,u.name assigned_name,p.status proposal_status,p.link_type,p.similarity_score,p.discrepancy_level
                                                FROM canonical_review_jobs j
                                                LEFT JOIN users u ON u.id=j.assigned_to
                                                LEFT JOIN canonical_review_proposals p ON p.id=j.active_proposal_id
                                                WHERE j.product_code=?''' + extra + ' ORDER BY j.priority,j.status,j.template_id,j.id', params).fetchall()]
        templates = {}
        for row in rows:
            key = row['template_id']
            templates.setdefault(key, {'template_id': key, 'jobs': 0, 'cotejado': 0})
            templates[key]['jobs'] += 1
            templates[key]['cotejado'] += row['status'] == 'Cotejado'
        for item in templates.values():
            item['coverage'] = round(item['cotejado'] * 100 / max(1, item['jobs']))
        return {
            'product': self.products[code],
            'priority': self._priority(code),
            'verified_sources': con.execute('SELECT COUNT(*) FROM canonical_source_files WHERE product_code=? AND verified=1', (code,)).fetchone()[0],
            'jobs': rows,
            'templates': list(templates.values()),
            'coverage': round(sum(x['status'] == 'Cotejado' for x in rows) * 100 / max(1, len(rows))),
        }

    def job_detail(self, con, job_id: int) -> dict | None:
        row = self._job_row(con, job_id)
        if not row:
            return None
        trace = self.traceability.detail(con, row['product_code'])
        block = next((x for x in trace['blocks'] if x['template_id'] == row['template_id'] and x['block_id'] == row['block_id']), None)
        proposals = [dict(x) for x in con.execute('SELECT * FROM canonical_review_proposals WHERE job_id=? ORDER BY id DESC', (job_id,)).fetchall()]
        events = [dict(x) for x in con.execute('SELECT * FROM canonical_review_events WHERE job_id=? ORDER BY id DESC', (job_id,)).fetchall()]
        return {
            'job': dict(row),
            'block': block,
            'proposals': proposals,
            'events': events,
            'chain_valid': self.verify_chain(list(reversed(events))) if events else True,
            'verified_sources': con.execute('SELECT COUNT(*) FROM canonical_source_files WHERE product_code=? AND verified=1', (row['product_code'],)).fetchone()[0],
            'link_types': sorted(LINK_TYPES),
        }

    def candidates(self, con, job_id: int, actor: str, limit: int = 8) -> dict:
        row = self._job_row(con, job_id)
        if not row:
            raise ValueError('Trabajo de cotejo no encontrado.')
        if not self._has_verified_source(con, row['product_code']):
            raise ValueError('El producto no tiene una fuente binaria verificada.')
        suggested = self.traceability.suggest(con, row['product_code'], row['template_id'], row['block_id'], actor, max(1, min(12, limit)))
        for item in suggested['candidates']:
            diff = item.get('diff') or semantic_diff(suggested['block']['text'], item['fragment_text'])
            item['discrepancy_level'] = _risk_level(
                diff['similarity_score'], diff['added_count'], diff['omitted_count']
            )
            item['verified_source'] = bool(item.get('verified'))
        return {
            'job': dict(row),
            'block': suggested['block'],
            'candidates': suggested['candidates'],
            'notice': suggested['notice'],
        }

    def claim(self, con, job_id: int, actor: str, role: str, expected_version=None) -> dict:
        if role != 'specialist':
            raise PermissionError('Solo un especialista puede asumir un trabajo de cotejo.')
        row = self._job_row(con, job_id)
        if not row:
            raise ValueError('Trabajo no encontrado.')
        self._check_version(row, expected_version)
        if row['status'] == 'Bloqueado por fuente':
            raise ValueError('El trabajo permanece bloqueado hasta incorporar una fuente verificada.')
        if row['status'] == 'Cotejado':
            raise ValueError('El bloque ya está cotejado.')
        if row['assigned_to'] and row['assigned_to'] != actor:
            raise ValueError('El trabajo ya está asignado a otro especialista.')
        t = _now()
        con.execute('''UPDATE canonical_review_jobs SET assigned_to=?,assigned_at=COALESCE(assigned_at,?),status='Asignado',version=version+1,updated_at=? WHERE id=?''',
                    (actor, t, t, job_id))
        self._event(con, job_id, 'job_claimed', actor, role, {'assigned_to': actor})
        return {'ok': True, 'job_id': job_id, 'status': 'Asignado', 'version': int(row['version']) + 1}

    def assign(self, con, job_id: int, assignee: str, actor: str, role: str, priority: int | None = None, expected_version=None) -> dict:
        if role != 'admin':
            raise PermissionError('Solo administración puede asignar trabajos.')
        row = self._job_row(con, job_id)
        if not row:
            raise ValueError('Trabajo no encontrado.')
        self._check_version(row, expected_version)
        specialist = con.execute('SELECT id,role,active FROM users WHERE id=?', (assignee,)).fetchone()
        if not specialist or specialist['role'] != 'specialist' or not specialist['active']:
            raise ValueError('El usuario asignado no es un especialista activo.')
        p = int(priority or row['priority'])
        if p not in {1, 2, 3}:
            raise ValueError('Prioridad inválida.')
        status = row['status'] if row['status'] in {'Listo para QA', 'Cotejado'} else ('Bloqueado por fuente' if row['status'] == 'Bloqueado por fuente' else 'Asignado')
        t = _now()
        con.execute('''UPDATE canonical_review_jobs SET assigned_to=?,assigned_at=?,priority=?,status=?,version=version+1,updated_at=? WHERE id=?''',
                    (assignee, t, p, status, t, job_id))
        self._event(con, job_id, 'job_assigned', actor, role, {'assigned_to': assignee, 'priority': p})
        return {'ok': True, 'job_id': job_id, 'status': status, 'version': int(row['version']) + 1}

    def submit_proposal(self, con, job_id: int, fragment_id: int | None, link_type: str,
                        actor: str, role: str, legal_rationale: str, effect_assessment: str,
                        exception_reason: str = '', expected_version=None) -> dict:
        if role != 'specialist':
            raise PermissionError('La propuesta jurídica requiere un especialista.')
        if link_type not in LINK_TYPES:
            raise ValueError('Tipo de relación inválido.')
        if len((legal_rationale or '').strip()) < 30:
            raise ValueError('La motivación jurídica debe tener al menos 30 caracteres.')
        if len((effect_assessment or '').strip()) < 20:
            raise ValueError('Describa el efecto jurídico comparado en al menos 20 caracteres.')
        row = self._job_row(con, job_id)
        if not row:
            raise ValueError('Trabajo no encontrado.')
        self._check_version(row, expected_version)
        if row['status'] == 'Bloqueado por fuente':
            raise ValueError('No puede cotejarse sin una fuente binaria verificada.')
        if row['assigned_to'] not in (None, actor):
            raise ValueError('El trabajo está asignado a otro especialista.')
        if link_type != 'Excepción justificada' and not fragment_id:
            raise ValueError('Seleccione un fragmento fuente.')
        if link_type == 'Excepción justificada' and len((exception_reason or '').strip()) < 30:
            raise ValueError('La excepción exige una justificación de al menos 30 caracteres.')

        trace = self.traceability.detail(con, row['product_code'])
        block = next((x for x in trace['blocks'] if x['template_id'] == row['template_id'] and x['block_id'] == row['block_id']), None)
        if not block:
            raise ValueError('El bloque vigente no está disponible.')
        fragment = None
        diff = {
            'similarity_score': 0.0,
            'semantic_class': classification(0),
            'terms_added_in_block': [],
            'terms_omitted_from_source': [],
            'added_count': 0,
            'omitted_count': 0,
        }
        if fragment_id:
            fragment = con.execute('''SELECT f.*,s.verified FROM canonical_source_fragments f
                                      JOIN canonical_source_files s ON s.id=f.source_file_id
                                      WHERE f.id=? AND f.product_code=?''', (fragment_id, row['product_code'])).fetchone()
            if not fragment or not fragment['verified']:
                raise ValueError('El fragmento no pertenece a una fuente verificada del producto.')
            diff = semantic_diff(block['text'], fragment['fragment_text'])

        link = self.traceability.save_link(
            con, row['product_code'], row['template_id'], row['block_id'], fragment_id,
            link_type, actor, legal_note=legal_rationale, exception_reason=exception_reason,
        )
        self.traceability.approve_link(
            con, link['link_id'], 'legal', 'Aprobado', actor, role,
            f'{legal_rationale.strip()} Efecto jurídico: {effect_assessment.strip()}',
        )
        proposal_version = con.execute('SELECT COALESCE(MAX(proposal_version),0)+1 FROM canonical_review_proposals WHERE job_id=?', (job_id,)).fetchone()[0]
        discrepancy = _risk_level(diff['similarity_score'], diff['added_count'], diff['omitted_count'], link_type)
        cur = con.execute('''INSERT INTO canonical_review_proposals(job_id,proposal_version,fragment_id,link_type,legal_rationale,effect_assessment,
                           exception_reason,block_hash,source_fragment_hash,similarity_score,semantic_class,discrepancy_level,added_terms_json,
                           omitted_terms_json,trace_link_id,status,created_by,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (job_id, proposal_version, fragment_id, link_type, legal_rationale.strip(), effect_assessment.strip(),
                           exception_reason.strip() or None, block['block_hash'], fragment['fragment_hash'] if fragment else None,
                           diff['similarity_score'], diff['semantic_class'], discrepancy,
                           json.dumps(diff['terms_added_in_block'], ensure_ascii=False),
                           json.dumps(diff['terms_omitted_from_source'], ensure_ascii=False),
                           link['link_id'], 'Submitted', actor, _now()))
        proposal_id = cur.lastrowid
        if row['active_proposal_id']:
            con.execute("UPDATE canonical_review_proposals SET status='Superseded' WHERE id=? AND status NOT IN ('Accepted','Rejected')", (row['active_proposal_id'],))
        t = _now()
        con.execute('''UPDATE canonical_review_jobs SET assigned_to=?,assigned_at=COALESCE(assigned_at,?),active_proposal_id=?,status='Listo para QA',version=version+1,updated_at=? WHERE id=?''',
                    (actor, t, proposal_id, t, job_id))
        self._event(con, job_id, 'legal_proposal_submitted', actor, role, {
            'proposal_id': proposal_id, 'trace_link_id': link['link_id'], 'link_type': link_type,
            'fragment_id': fragment_id, 'discrepancy_level': discrepancy,
        })
        return {
            'ok': True,
            'job_id': job_id,
            'proposal_id': proposal_id,
            'trace_link_id': link['link_id'],
            'status': 'Listo para QA',
            'version': int(row['version']) + 1,
            'similarity_score': diff['similarity_score'],
            'semantic_class': diff['semantic_class'],
            'discrepancy_level': discrepancy,
        }

    def qa_decision(self, con, job_id: int, decision: str, actor: str, role: str,
                    comment: str, expected_version=None) -> dict:
        if role != 'admin':
            raise PermissionError('La decisión de QA requiere administración.')
        if decision not in {'Aprobado', 'Rechazado'}:
            raise ValueError('Decisión de QA inválida.')
        if len((comment or '').strip()) < 20:
            raise ValueError('El comentario de QA debe tener al menos 20 caracteres.')
        row = self._job_row(con, job_id)
        if not row:
            raise ValueError('Trabajo no encontrado.')
        self._check_version(row, expected_version)
        if row['status'] != 'Listo para QA' or not row['active_proposal_id']:
            raise ValueError('El trabajo no tiene una propuesta jurídica pendiente de QA.')
        proposal = con.execute('SELECT * FROM canonical_review_proposals WHERE id=?', (row['active_proposal_id'],)).fetchone()
        if not proposal or not proposal['trace_link_id']:
            raise ValueError('La propuesta no tiene un vínculo trazable.')
        result = self.traceability.approve_link(
            con, proposal['trace_link_id'], 'qa', decision, actor, role, comment.strip()
        )
        status = 'Cotejado' if decision == 'Aprobado' else 'Requiere ajuste'
        proposal_status = 'Accepted' if decision == 'Aprobado' else 'Rejected'
        t = _now()
        con.execute('''UPDATE canonical_review_proposals SET status=?,decided_by=?,decided_at=?,qa_comment=? WHERE id=?''',
                    (proposal_status, actor, t, comment.strip(), proposal['id']))
        con.execute('''UPDATE canonical_review_jobs SET status=?,version=version+1,updated_at=? WHERE id=?''',
                    (status, t, job_id))
        self._event(con, job_id, 'qa_decision', actor, role, {
            'decision': decision, 'proposal_id': proposal['id'], 'trace_link_id': proposal['trace_link_id'], 'status': status,
        })
        return {'ok': True, 'job_id': job_id, 'status': status, 'version': int(row['version']) + 1, 'traceability': result}

    def export_bytes(self, con) -> bytes:
        summary = self.summary(con)
        memory = BytesIO()
        with ZipFile(memory, 'w', ZIP_DEFLATED) as z:
            z.writestr('00_RESUMEN_MESA_COTEJO.json', json.dumps(summary, ensure_ascii=False, indent=2, default=str))
            jobs = [dict(x) for x in con.execute('SELECT * FROM canonical_review_jobs ORDER BY priority,product_code,template_id,id').fetchall()]
            proposals = [dict(x) for x in con.execute('SELECT * FROM canonical_review_proposals ORDER BY job_id,id').fetchall()]
            events = [dict(x) for x in con.execute('SELECT * FROM canonical_review_events ORDER BY job_id,id').fetchall()]
            z.writestr('01_TRABAJOS.json', json.dumps(jobs, ensure_ascii=False, indent=2, default=str))
            z.writestr('02_PROPUESTAS.json', json.dumps(proposals, ensure_ascii=False, indent=2, default=str))
            z.writestr('03_EVENTOS_HASH.json', json.dumps(events, ensure_ascii=False, indent=2, default=str))
            sio = StringIO()
            writer = csv.writer(sio)
            writer.writerow(['id','producto','plantilla','bloque','estado','asignado','prioridad','versión','actualizado'])
            for row in jobs:
                writer.writerow([row['id'],row['product_code'],row['template_id'],row['block_id'],row['status'],row.get('assigned_to') or '',row['priority'],row['version'],row['updated_at']])
            z.writestr('04_MATRIZ_TRABAJOS.csv', '\ufeff' + sio.getvalue())
        return memory.getvalue()
