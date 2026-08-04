from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
from zipfile import ZipFile, ZIP_DEFLATED
import csv
import json
import uuid


BATCH_STATUSES = {
    'Borrador', 'Asignado', 'En progreso', 'Listo para cierre',
    'Cerrado', 'Cancelado', 'Desactualizado',
}
ACTIONABLE_JOB_STATUSES = {
    'Bloqueado por fuente', 'Pendiente', 'Asignado', 'En cotejo',
    'Listo para QA', 'Requiere ajuste', 'Requiere recotejo',
}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _stable_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return sha256(raw.encode('utf-8')).hexdigest()


class ReviewBatchCenter:
    """Orquesta lotes de cotejo sin automatizar decisiones jurídicas.

    El lote congela la identidad de los bloques y permite asignación, seguimiento,
    exportación e integridad. Cada bloque conserva su aprobación individual.
    """

    def __init__(self, review, traceability, factory, canonical, intake, products):
        self.review = review
        self.traceability = traceability
        self.factory = factory
        self.canonical = canonical
        self.intake = intake
        self.products = {x['code']: x for x in products}

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_review_batches(
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          product_code TEXT NOT NULL,
          template_id TEXT,
          priority INTEGER NOT NULL DEFAULT 2,
          status TEXT NOT NULL,
          assigned_to TEXT,
          due_at TEXT,
          notes TEXT,
          manifest_json TEXT NOT NULL,
          manifest_hash TEXT NOT NULL,
          total_jobs INTEGER NOT NULL,
          version INTEGER NOT NULL DEFAULT 1,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          closed_by TEXT,
          closed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_crb_queue ON canonical_review_batches(status,priority,product_code,created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_crb_assignee ON canonical_review_batches(assigned_to,status,updated_at DESC);

        CREATE TABLE IF NOT EXISTS canonical_review_batch_jobs(
          batch_id TEXT NOT NULL,
          job_id INTEGER NOT NULL,
          revision_id INTEGER,
          block_hash TEXT NOT NULL,
          job_version_at_snapshot INTEGER NOT NULL,
          status_at_snapshot TEXT NOT NULL,
          added_at TEXT NOT NULL,
          PRIMARY KEY(batch_id,job_id),
          FOREIGN KEY(batch_id) REFERENCES canonical_review_batches(id),
          FOREIGN KEY(job_id) REFERENCES canonical_review_jobs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_crbj_job ON canonical_review_batch_jobs(job_id,batch_id);

        CREATE TABLE IF NOT EXISTS canonical_review_batch_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          batch_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          actor TEXT NOT NULL,
          actor_role TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          previous_event_hash TEXT,
          event_hash TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(batch_id) REFERENCES canonical_review_batches(id)
        );
        CREATE INDEX IF NOT EXISTS idx_crbe_batch ON canonical_review_batch_events(batch_id,id);
        ''')

    def _event(self, con, batch_id: str, event_type: str, actor: str, role: str, detail) -> str:
        detail_json = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, sort_keys=True)
        prev = con.execute('SELECT event_hash FROM canonical_review_batch_events WHERE batch_id=? ORDER BY id DESC LIMIT 1', (batch_id,)).fetchone()
        previous = prev['event_hash'] if prev else ''
        created = _now()
        payload = '|'.join([batch_id, event_type, actor, role, created, previous, detail_json])
        digest = sha256(payload.encode('utf-8')).hexdigest()
        con.execute('''INSERT INTO canonical_review_batch_events(batch_id,event_type,actor,actor_role,detail_json,previous_event_hash,event_hash,created_at)
                       VALUES(?,?,?,?,?,?,?,?)''',
                    (batch_id, event_type, actor, role, detail_json, previous or None, digest, created))
        return digest

    @staticmethod
    def verify_chain(events: list[dict]) -> bool:
        previous = ''
        for event in sorted(events, key=lambda x: x['id']):
            payload = '|'.join([
                event['batch_id'], event['event_type'], event['actor'], event['actor_role'],
                event['created_at'], previous, event['detail_json'],
            ])
            digest = sha256(payload.encode('utf-8')).hexdigest()
            if (event.get('previous_event_hash') or '') != previous or event.get('event_hash') != digest:
                return False
            previous = digest
        return True

    @staticmethod
    def _validate_specialist(con, user_id: str | None):
        if not user_id:
            return None
        row = con.execute("SELECT id,name,email FROM users WHERE id=? AND role='specialist' AND active=1", (user_id,)).fetchone()
        if not row:
            raise ValueError('Especialista no válido o inactivo.')
        return dict(row)

    def _manifest(self, rows: list[dict]) -> dict:
        jobs = [{
            'job_id': int(x['id']),
            'product_code': x['product_code'],
            'template_id': x['template_id'],
            'block_id': x['block_id'],
            'revision_id': x['revision_id'],
            'block_hash': x['block_hash'],
            'job_version': int(x['version']),
            'status': x['status'],
        } for x in rows]
        return {'schema': 'legalaizit.review-batch.v1', 'jobs': jobs}

    def _active_batch_job_ids(self, con) -> set[int]:
        rows = con.execute('''SELECT bj.job_id FROM canonical_review_batch_jobs bj
                              JOIN canonical_review_batches b ON b.id=bj.batch_id
                              WHERE b.status NOT IN ('Cerrado','Cancelado','Desactualizado')''').fetchall()
        return {int(x['job_id']) for x in rows}

    def create_batch(self, con, name: str, product_code: str, actor: str, role: str,
                     template_id: str | None = None, assigned_to: str | None = None,
                     priority: int = 2, due_at: str | None = None, notes: str = '',
                     statuses: list[str] | None = None, max_jobs: int = 20) -> dict:
        if role != 'admin':
            raise PermissionError('Solo administración puede crear lotes.')
        name = (name or '').strip()
        if len(name) < 5:
            raise ValueError('El nombre del lote debe tener al menos 5 caracteres.')
        if product_code not in self.products:
            raise ValueError('Producto no registrado.')
        priority = int(priority or 2)
        if priority not in {1, 2, 3}:
            raise ValueError('Prioridad inválida.')
        max_jobs = max(1, min(int(max_jobs or 20), 50))
        statuses = statuses or sorted(ACTIONABLE_JOB_STATUSES)
        invalid = set(statuses) - ACTIONABLE_JOB_STATUSES
        if invalid:
            raise ValueError('Estados de selección inválidos: ' + ', '.join(sorted(invalid)))
        specialist = self._validate_specialist(con, assigned_to)
        self.review.init_jobs(con, product_code)
        placeholders = ','.join('?' for _ in statuses)
        sql = f'''SELECT * FROM canonical_review_jobs WHERE product_code=? AND status IN ({placeholders})'''
        params: list = [product_code, *statuses]
        if template_id:
            sql += ' AND template_id=?'
            params.append(template_id)
        sql += ' ORDER BY priority,id'
        rows = [dict(x) for x in con.execute(sql, params).fetchall()]
        active = self._active_batch_job_ids(con)
        rows = [x for x in rows if int(x['id']) not in active]
        if assigned_to:
            rows = [x for x in rows if x.get('assigned_to') in (None, assigned_to)]
        rows = rows[:max_jobs]
        if not rows:
            raise ValueError('No existen trabajos disponibles con los filtros indicados.')

        # Formal assignment is recorded in the underlying review jobs before the frozen snapshot.
        if assigned_to:
            refreshed = []
            for row in rows:
                if row.get('assigned_to') != assigned_to:
                    self.review.assign(con, row['id'], assigned_to, actor, role, priority, row['version'])
                refreshed.append(dict(con.execute('SELECT * FROM canonical_review_jobs WHERE id=?', (row['id'],)).fetchone()))
            rows = refreshed

        manifest = self._manifest(rows)
        digest = _stable_hash(manifest)
        batch_id = 'BAT-' + uuid.uuid4().hex[:12].upper()
        now = _now()
        status = 'Asignado' if assigned_to else 'Borrador'
        con.execute('''INSERT INTO canonical_review_batches(id,name,product_code,template_id,priority,status,assigned_to,due_at,notes,
                       manifest_json,manifest_hash,total_jobs,version,created_by,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)''',
                    (batch_id, name, product_code, template_id, priority, status, assigned_to, due_at, notes.strip(),
                     json.dumps(manifest, ensure_ascii=False, sort_keys=True), digest, len(rows), actor, now, now))
        for row in rows:
            con.execute('''INSERT INTO canonical_review_batch_jobs(batch_id,job_id,revision_id,block_hash,job_version_at_snapshot,status_at_snapshot,added_at)
                           VALUES(?,?,?,?,?,?,?)''',
                        (batch_id, row['id'], row['revision_id'], row['block_hash'], row['version'], row['status'], now))
        self._event(con, batch_id, 'batch_created', actor, role, {
            'jobs': len(rows), 'manifest_hash': digest, 'assigned_to': assigned_to, 'product_code': product_code,
        })
        return self.detail(con, batch_id)

    def _row(self, con, batch_id: str):
        return con.execute('''SELECT b.*,u.name assigned_name,u.email assigned_email
                              FROM canonical_review_batches b LEFT JOIN users u ON u.id=b.assigned_to
                              WHERE b.id=?''', (batch_id,)).fetchone()

    def _job_rows(self, con, batch_id: str) -> list[dict]:
        rows = con.execute('''SELECT bj.*,j.product_code,j.template_id,j.block_id,j.revision_id current_revision_id,
                              j.block_hash current_block_hash,j.status current_status,j.version current_version,
                              j.assigned_to,j.updated_at,u.name assigned_name
                              FROM canonical_review_batch_jobs bj
                              JOIN canonical_review_jobs j ON j.id=bj.job_id
                              LEFT JOIN users u ON u.id=j.assigned_to
                              WHERE bj.batch_id=? ORDER BY j.priority,j.id''', (batch_id,)).fetchall()
        return [dict(x) for x in rows]

    def _computed(self, jobs: list[dict]) -> dict:
        stale = [x for x in jobs if (x['revision_id'] or 0) != (x['current_revision_id'] or 0) or x['block_hash'] != x['current_block_hash']]
        cotejado = sum(x['current_status'] == 'Cotejado' for x in jobs)
        ready_qa = sum(x['current_status'] == 'Listo para QA' for x in jobs)
        blocked = sum(x['current_status'] == 'Bloqueado por fuente' for x in jobs)
        return {
            'jobs': len(jobs), 'cotejado': cotejado, 'ready_qa': ready_qa, 'blocked': blocked,
            'pending': len(jobs) - cotejado - ready_qa,
            'coverage': round(cotejado * 100 / max(1, len(jobs))),
            'stale_jobs': len(stale), 'stale_job_ids': [x['job_id'] for x in stale],
        }

    def refresh(self, con, batch_id: str, actor: str, role: str) -> dict:
        row = self._row(con, batch_id)
        if not row:
            raise ValueError('Lote no encontrado.')
        if role not in {'specialist', 'admin'}:
            raise PermissionError('Sin permisos para actualizar el lote.')
        jobs = self._job_rows(con, batch_id)
        metrics = self._computed(jobs)
        if row['status'] in {'Cerrado', 'Cancelado'}:
            target = row['status']
        elif metrics['stale_jobs']:
            target = 'Desactualizado'
        elif metrics['cotejado'] == metrics['jobs'] and metrics['jobs']:
            target = 'Listo para cierre'
        elif metrics['cotejado'] or metrics['ready_qa'] or any(x['current_status'] in {'En cotejo','Requiere ajuste','Requiere recotejo'} for x in jobs):
            target = 'En progreso'
        elif row['assigned_to']:
            target = 'Asignado'
        else:
            target = 'Borrador'
        if target != row['status']:
            con.execute('UPDATE canonical_review_batches SET status=?,version=version+1,updated_at=? WHERE id=?', (target, _now(), batch_id))
            self._event(con, batch_id, 'batch_status_refreshed', actor, role, {'from': row['status'], 'to': target, **metrics})
        return self.detail(con, batch_id)

    def claim(self, con, batch_id: str, actor: str, role: str, expected_version=None) -> dict:
        if role != 'specialist':
            raise PermissionError('Solo un especialista puede asumir un lote.')
        row = self._row(con, batch_id)
        if not row:
            raise ValueError('Lote no encontrado.')
        if expected_version is not None and int(expected_version) != int(row['version']):
            raise ValueError('El lote cambió; recargue antes de continuar.')
        if row['status'] in {'Cerrado', 'Cancelado', 'Desactualizado'}:
            raise ValueError('El lote no puede asumirse en su estado actual.')
        if row['assigned_to'] not in (None, actor):
            raise ValueError('El lote está asignado a otro especialista.')
        jobs = self._job_rows(con, batch_id)
        if any(item.get('current_status') == 'Bloqueado por fuente' for item in jobs):
            raise ValueError('El lote contiene trabajos bloqueados por ausencia de fuente verificada.')
        for item in jobs:
            if item.get('assigned_to') not in (None, actor):
                raise ValueError('Uno de los trabajos ya está asignado a otro especialista.')
        for item in jobs:
            if item.get('assigned_to') != actor:
                current = con.execute('SELECT * FROM canonical_review_jobs WHERE id=?', (item['job_id'],)).fetchone()
                self.review.claim(con, item['job_id'], actor, role, current['version'])
        now = _now()
        con.execute("UPDATE canonical_review_batches SET assigned_to=?,status='Asignado',version=version+1,updated_at=? WHERE id=?", (actor, now, batch_id))
        self._event(con, batch_id, 'batch_claimed', actor, role, {'jobs': len(jobs)})
        return self.detail(con, batch_id)

    def close(self, con, batch_id: str, actor: str, role: str, comment: str = '') -> dict:
        if role != 'admin':
            raise PermissionError('Solo administración puede cerrar un lote.')
        detail = self.refresh(con, batch_id, actor, role)
        if detail['metrics']['stale_jobs']:
            raise ValueError('El lote está desactualizado y requiere reconstrucción.')
        if detail['metrics']['cotejado'] != detail['metrics']['jobs']:
            raise ValueError('Solo puede cerrarse cuando todos los trabajos estén cotejados individualmente.')
        if len((comment or '').strip()) < 15:
            raise ValueError('Registre un comentario de cierre de al menos 15 caracteres.')
        now = _now()
        con.execute("UPDATE canonical_review_batches SET status='Cerrado',closed_by=?,closed_at=?,version=version+1,updated_at=? WHERE id=?",
                    (actor, now, now, batch_id))
        self._event(con, batch_id, 'batch_closed', actor, role, {'comment': comment.strip()})
        return self.detail(con, batch_id)

    def cancel(self, con, batch_id: str, actor: str, role: str, comment: str = '') -> dict:
        if role != 'admin':
            raise PermissionError('Solo administración puede cancelar un lote.')
        row = self._row(con, batch_id)
        if not row:
            raise ValueError('Lote no encontrado.')
        if row['status'] == 'Cerrado':
            raise ValueError('Un lote cerrado no puede cancelarse.')
        if len((comment or '').strip()) < 15:
            raise ValueError('Registre una razón de cancelación de al menos 15 caracteres.')
        con.execute("UPDATE canonical_review_batches SET status='Cancelado',version=version+1,updated_at=? WHERE id=?", (_now(), batch_id))
        self._event(con, batch_id, 'batch_cancelled', actor, role, {'comment': comment.strip()})
        return self.detail(con, batch_id)

    def summary(self, con, actor: str | None = None, role: str | None = None) -> dict:
        self.review.init_jobs(con)
        rows = [dict(x) for x in con.execute('''SELECT b.*,u.name assigned_name FROM canonical_review_batches b
                                                LEFT JOIN users u ON u.id=b.assigned_to ORDER BY
                                                CASE b.status WHEN 'En progreso' THEN 1 WHEN 'Asignado' THEN 2 WHEN 'Borrador' THEN 3
                                                WHEN 'Listo para cierre' THEN 4 WHEN 'Desactualizado' THEN 5 ELSE 6 END,
                                                b.priority,b.updated_at DESC''').fetchall()]
        if role == 'specialist' and actor:
            rows = [x for x in rows if x['assigned_to'] in (None, actor)]
        batches = []
        broken = 0
        for row in rows:
            jobs = self._job_rows(con, row['id'])
            metrics = self._computed(jobs)
            events = [dict(x) for x in con.execute('SELECT * FROM canonical_review_batch_events WHERE batch_id=? ORDER BY id', (row['id'],)).fetchall()]
            chain_valid = self.verify_chain(events) if events else True
            broken += 0 if chain_valid else 1
            batches.append({**row, 'metrics': metrics, 'chain_valid': chain_valid})
        counts = {status: sum(x['status'] == status for x in rows) for status in BATCH_STATUSES}
        return {
            'metrics': {
                'batches': len(rows), 'active': sum(x['status'] not in {'Cerrado','Cancelado'} for x in rows),
                'closed': counts['Cerrado'], 'stale': counts['Desactualizado'],
                'jobs_in_batches': sum(x['metrics']['jobs'] for x in batches),
                'cotejado_in_batches': sum(x['metrics']['cotejado'] for x in batches),
                'broken_chains': broken,
            },
            'batches': batches,
            'products': [{'code': c, 'title': self.products[c].get('title', c)} for c in sorted(self.products)],
            'specialists': [dict(x) for x in con.execute("SELECT id,name,email,specialty FROM users WHERE role='specialist' AND active=1 ORDER BY name").fetchall()],
            'notice': 'Los lotes organizan trabajo y evidencia; no permiten aprobar varios bloques jurídicos en una sola decisión.',
        }

    def detail(self, con, batch_id: str) -> dict | None:
        row = self._row(con, batch_id)
        if not row:
            return None
        jobs = self._job_rows(con, batch_id)
        metrics = self._computed(jobs)
        events = [dict(x) for x in con.execute('SELECT * FROM canonical_review_batch_events WHERE batch_id=? ORDER BY id DESC', (batch_id,)).fetchall()]
        product = self.products.get(row['product_code'], {'code': row['product_code'], 'title': row['product_code']})
        return {
            'batch': dict(row), 'product': product, 'jobs': jobs, 'metrics': metrics,
            'events': events, 'chain_valid': self.verify_chain(list(reversed(events))) if events else True,
        }

    def readiness(self, con) -> dict:
        intake = {x['product_code']: x for x in self.intake.summary(con)['products']}
        review = {x['product_code']: x for x in self.review.summary(con)['products']}
        factory_rows = self.factory.summary(con)['templates']
        canonical = {x['product_code']: x for x in self.canonical.summary(con)['packages']}
        products = []
        for code in sorted(self.products):
            templates = [x for x in factory_rows if x['product_code'] == code]
            approved_templates = sum(bool(x['published']) for x in templates)
            gate = self.traceability.gate(con, code)
            c = canonical.get(code, {})
            i = intake.get(code, {})
            r = review.get(code, {})
            checks = [
                {'key': 'binary', 'label': 'Fuente binaria verificada', 'passed': gate['verified_source_files'] > 0},
                {'key': 'intake', 'label': 'Entregables obligatorios de ingreso', 'passed': bool(i) and i.get('coverage') == 100},
                {'key': 'trace', 'label': 'Bloques obligatorios cotejados', 'passed': gate['passed']},
                {'key': 'templates', 'label': 'Plantillas aprobadas', 'passed': bool(templates) and approved_templates == len(templates)},
                {'key': 'canonical_legal', 'label': 'Paquete con aprobación jurídica', 'passed': c.get('stage') == 'Aprobado para piloto'},
                {'key': 'issues', 'label': 'Sin brechas críticas abiertas', 'passed': int(c.get('critical_issues') or 0) == 0},
                {'key': 'publication', 'label': 'Puerta de publicación registrada', 'passed': bool(con.execute("SELECT 1 FROM canonical_publication_decisions WHERE product_code=? AND decision='Aprobado' ORDER BY id DESC LIMIT 1", (code,)).fetchone())},
            ]
            passed = sum(x['passed'] for x in checks)
            products.append({
                'product_code': code, 'title': self.products[code].get('title', code),
                'checks': checks, 'passed_checks': passed, 'total_checks': len(checks),
                'score': round(passed * 100 / len(checks)), 'ready': passed == len(checks),
                'verified_sources': gate['verified_source_files'], 'trace_coverage': gate['coverage'],
                'review_jobs': r.get('jobs', 0), 'review_cotejado': r.get('cotejado', 0),
                'templates': len(templates), 'approved_templates': approved_templates,
                'canonical_stage': c.get('stage', 'Sin estado'), 'critical_issues': c.get('critical_issues', 0),
            })
        return {
            'metrics': {
                'products': len(products), 'ready': sum(x['ready'] for x in products),
                'average_score': round(sum(x['score'] for x in products) / max(1, len(products))),
                'verified_sources': sum(x['verified_sources'] for x in products),
                'trace_coverage_average': round(sum(x['trace_coverage'] for x in products) / max(1, len(products))),
            },
            'products': sorted(products, key=lambda x: (not x['ready'], x['score'], x['product_code'])),
            'notice': 'La matriz de release es informativa. La autorización final exige decisiones expresas sobre la versión vigente y no puede inferirse del puntaje.',
        }

    def export_bytes(self, con, batch_id: str, actor: str) -> bytes:
        detail = self.detail(con, batch_id)
        if not detail:
            raise ValueError('Lote no encontrado.')
        memory = BytesIO()
        with ZipFile(memory, 'w', ZIP_DEFLATED) as z:
            z.writestr('00_MANIFIESTO_LOTE.json', json.dumps({
                'batch': detail['batch'], 'metrics': detail['metrics'], 'chain_valid': detail['chain_valid'],
                'exported_by': actor, 'exported_at': _now(),
            }, ensure_ascii=False, indent=2, default=str))
            z.writestr('01_TRABAJOS.json', json.dumps(detail['jobs'], ensure_ascii=False, indent=2, default=str))
            blocks = []
            candidates = []
            for item in detail['jobs']:
                job = self.review.job_detail(con, item['job_id'])
                if job:
                    blocks.append({'job': job['job'], 'block': job.get('block'), 'proposals': job.get('proposals', [])})
                    if job.get('verified_sources') and job['job']['status'] != 'Cotejado':
                        try:
                            candidates.append({'job_id': item['job_id'], **self.review.candidates(con, item['job_id'], actor, 3)})
                        except Exception as exc:
                            candidates.append({'job_id': item['job_id'], 'error': str(exc), 'candidates': []})
            z.writestr('02_BLOQUES_Y_PROPUESTAS.json', json.dumps(blocks, ensure_ascii=False, indent=2, default=str))
            z.writestr('03_CANDIDATOS_ORIENTATIVOS.json', json.dumps(candidates, ensure_ascii=False, indent=2, default=str))
            sio = StringIO(); writer = csv.writer(sio)
            writer.writerow(['trabajo','producto','plantilla','bloque','estado_actual','asignado','revisión','hash_bloque','versión'])
            for x in detail['jobs']:
                writer.writerow([x['job_id'],x['product_code'],x['template_id'],x['block_id'],x['current_status'],x.get('assigned_name') or '',x['current_revision_id'],x['current_block_hash'],x['current_version']])
            z.writestr('04_MATRIZ_LOTE.csv', '\ufeff' + sio.getvalue())
            z.writestr('05_INSTRUCCIONES.md', '''# Paquete de cotejo\n\nEste archivo organiza evidencia para revisión individual.\n\n- Las similitudes son orientativas.\n- Cada bloque requiere motivación jurídica separada.\n- No se permite aprobación masiva.\n- QA debe recaer sobre la misma propuesta y la misma revisión.\n- Un cambio de hash o revisión invalida la evidencia anterior.\n''')
            z.writestr('06_EVENTOS_HASH.json', json.dumps(detail['events'], ensure_ascii=False, indent=2, default=str))
        return memory.getvalue()
