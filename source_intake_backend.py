from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import shutil
import uuid
import tempfile

from source_extractors import extract_source

LEGAL_DECISIONS = {'Aprobado', 'Rechazado'}
QA_DECISIONS = {'Aprobado', 'Rechazado'}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


class SourceIntakeCenter:
    """Ingreso controlado de binarios canónicos con cuarentena y cadena de custodia.

    El ingreso no verifica por sí solo que el archivo sea el original esperado. La fuente solo
    entra a la matriz de trazabilidad después de aprobación jurídica y QA sobre el mismo registro.
    """

    def __init__(self, plan: list[dict], root: Path, canonical, traceability, object_store=None):
        self.plan = {x['product_code']: x for x in plan}
        self.root = Path(root)
        self.canonical = canonical
        self.traceability = traceability
        self.object_store = object_store
        self.quarantine = self.root / 'canonical_sources' / 'quarantine'
        self.verified = self.root / 'canonical_sources' / 'verified'
        self.extractions = self.root / 'data' / 'canonical_imports'
        for folder in (self.quarantine, self.verified, self.extractions):
            folder.mkdir(parents=True, exist_ok=True)

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_intake_records(
          id TEXT PRIMARY KEY,
          product_code TEXT NOT NULL,
          artifact_key TEXT NOT NULL,
          original_name TEXT NOT NULL,
          stored_name TEXT,
          stored_path TEXT,
          extraction_path TEXT,
          sha256 TEXT NOT NULL,
          size_bytes INTEGER NOT NULL,
          detected_type TEXT NOT NULL,
          extraction_format TEXT,
          extraction_error TEXT,
          status TEXT NOT NULL,
          duplicate_of TEXT,
          uploaded_by TEXT NOT NULL,
          uploaded_at TEXT NOT NULL,
          legal_decision TEXT NOT NULL DEFAULT 'Pendiente',
          legal_actor TEXT,
          legal_comment TEXT,
          legal_at TEXT,
          qa_decision TEXT NOT NULL DEFAULT 'Pendiente',
          qa_actor TEXT,
          qa_comment TEXT,
          qa_at TEXT,
          source_file_id INTEGER,
          FOREIGN KEY(duplicate_of) REFERENCES canonical_intake_records(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cir_product ON canonical_intake_records(product_code,artifact_key,uploaded_at DESC);
        CREATE INDEX IF NOT EXISTS idx_cir_sha ON canonical_intake_records(sha256,status);

        CREATE TABLE IF NOT EXISTS canonical_custody_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          intake_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          actor TEXT NOT NULL,
          actor_role TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          previous_event_hash TEXT,
          event_hash TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(intake_id) REFERENCES canonical_intake_records(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cce_intake ON canonical_custody_events(intake_id,id);
        ''')

    def _artifact(self, code: str, key: str) -> dict:
        product = self.plan.get(code)
        if not product:
            raise ValueError('Producto no registrado en el plan de ingreso.')
        artifact = next((x for x in product.get('artifacts', []) if x['key'] == key), None)
        if not artifact:
            raise ValueError('Entregable no registrado para el producto.')
        return artifact

    @staticmethod
    def _safe_name(value: str) -> str:
        keep = ''.join(c if c.isalnum() or c in '._-' else '_' for c in (value or 'fuente'))
        return keep[:160] or 'fuente'

    def _event(self, con, intake_id: str, event_type: str, actor: str, actor_role: str, detail) -> str:
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False, sort_keys=True)
        prev = con.execute('SELECT event_hash FROM canonical_custody_events WHERE intake_id=? ORDER BY id DESC LIMIT 1', (intake_id,)).fetchone()
        previous = prev['event_hash'] if prev else ''
        created = _now()
        payload = '|'.join([intake_id, event_type, actor, actor_role, created, previous, detail])
        digest = sha256(payload.encode('utf-8')).hexdigest()
        con.execute('''INSERT INTO canonical_custody_events(intake_id,event_type,actor,actor_role,detail_json,previous_event_hash,event_hash,created_at)
                       VALUES(?,?,?,?,?,?,?,?)''', (intake_id, event_type, actor, actor_role, detail, previous or None, digest, created))
        return digest

    @staticmethod
    def verify_chain(events: list[dict]) -> bool:
        previous = ''
        for event in sorted(events, key=lambda x: x['id']):
            payload = '|'.join([event['intake_id'], event['event_type'], event['actor'], event['actor_role'], event['created_at'], previous, event['detail_json']])
            digest = sha256(payload.encode('utf-8')).hexdigest()
            if (event.get('previous_event_hash') or '') != previous or event.get('event_hash') != digest:
                return False
            previous = digest
        return True

    @staticmethod
    def _public_record(row) -> dict:
        obj = dict(row)
        obj.pop('stored_path', None)
        obj.pop('extraction_path', None)
        return obj

    def upload(self, con, product_code: str, artifact_key: str, filename: str, raw: bytes,
               detected_type: str, digest: str, actor: str, actor_role: str) -> dict:
        code = product_code.upper().strip()
        artifact = self._artifact(code, artifact_key)
        ext = Path(filename).suffix.lower()
        if ext not in artifact.get('extensions', []):
            raise ValueError('La extensión no corresponde al entregable seleccionado: ' + ', '.join(artifact.get('extensions', [])))
        duplicate = con.execute('''SELECT id,status,original_name FROM canonical_intake_records
                                   WHERE sha256=? AND status NOT LIKE 'Rechazado%' AND (extraction_path IS NOT NULL OR status='Importado y verificado') ORDER BY uploaded_at DESC LIMIT 1''', (digest,)).fetchone()
        intake_id = 'INT-' + uuid.uuid4().hex[:12].upper()
        created = _now()
        if duplicate:
            con.execute('''INSERT INTO canonical_intake_records(id,product_code,artifact_key,original_name,sha256,size_bytes,detected_type,status,duplicate_of,uploaded_by,uploaded_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                        (intake_id, code, artifact_key, filename, digest, len(raw), detected_type, 'Duplicado detectado', duplicate['id'], actor, created))
            self._event(con, intake_id, 'duplicate_detected', actor, actor_role, {'duplicate_of': duplicate['id'], 'original_name': duplicate['original_name'], 'sha256': digest})
            return {'ok': True, 'intake_id': intake_id, 'status': 'Duplicado detectado', 'duplicate_of': duplicate['id'], 'sha256': digest}

        safe = self._safe_name(filename)
        stored_name = f'{intake_id}_{code}_{digest[:12]}_{safe}'
        if self.object_store:
            stored_obj = self.object_store.put(con, f'canonical/quarantine/{code}', filename, raw, detected_type, actor)
            stored_path = stored_obj['stored_path']
        else:
            stored = self.quarantine / stored_name
            stored.write_bytes(raw)
            stored_path = str(stored)
        extraction = None
        extraction_error = None
        extraction_file = None
        temp_path = None
        try:
            if self.object_store:
                suffix = Path(filename).suffix.lower()
                handle = tempfile.NamedTemporaryFile(prefix='legalaiz-intake-', suffix=suffix, delete=False)
                handle.write(raw); handle.close(); temp_path = Path(handle.name)
                extraction = extract_source(temp_path)
            else:
                extraction = extract_source(Path(stored_path))
            extraction.update({'original_name': filename, 'sha256': digest, 'size_bytes': len(raw), 'intake_id': intake_id})
            extraction_file = self.extractions / f'{intake_id}_{digest[:12]}.json'
            extraction_file.write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as exc:
            extraction_error = str(exc)
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

        status = 'En cuarentena' if extraction else 'En cuarentena · extracción pendiente'
        con.execute('''INSERT INTO canonical_intake_records(id,product_code,artifact_key,original_name,stored_name,stored_path,extraction_path,sha256,size_bytes,detected_type,extraction_format,extraction_error,status,uploaded_by,uploaded_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (intake_id, code, artifact_key, filename, stored_name, stored_path, str(extraction_file) if extraction_file else None,
                     digest, len(raw), detected_type, (extraction or {}).get('format'), extraction_error, status, actor, created))
        self._event(con, intake_id, 'received_in_quarantine', actor, actor_role, {
            'product_code': code, 'artifact_key': artifact_key, 'original_name': filename, 'sha256': digest,
            'size_bytes': len(raw), 'detected_type': detected_type, 'extraction_format': (extraction or {}).get('format'),
            'extraction_error': extraction_error,
        })
        return {'ok': True, 'intake_id': intake_id, 'status': status, 'sha256': digest, 'extraction_format': (extraction or {}).get('format'), 'extraction_error': extraction_error}

    def legal_decision(self, con, intake_id: str, decision: str, actor: str, actor_role: str, comment: str) -> dict:
        if actor_role != 'specialist':
            raise PermissionError('La confirmación de identidad jurídica requiere un especialista.')
        if decision not in LEGAL_DECISIONS:
            raise ValueError('Decisión jurídica inválida.')
        if len((comment or '').strip()) < 15:
            raise ValueError('Registre un comentario jurídico de al menos 15 caracteres.')
        row = con.execute('SELECT * FROM canonical_intake_records WHERE id=?', (intake_id,)).fetchone()
        if not row:
            raise ValueError('Registro de ingreso no encontrado.')
        if row['status'] == 'Duplicado detectado':
            raise ValueError('Los duplicados no pueden aprobarse como una nueva fuente.')
        status = 'Identidad jurídica confirmada' if decision == 'Aprobado' else 'Rechazado jurídicamente'
        t = _now()
        con.execute('''UPDATE canonical_intake_records SET legal_decision=?,legal_actor=?,legal_comment=?,legal_at=?,qa_decision='Pendiente',qa_actor=NULL,qa_comment=NULL,qa_at=NULL,status=? WHERE id=?''',
                    (decision, actor, comment, t, status, intake_id))
        self._event(con, intake_id, 'legal_identity_decision', actor, actor_role, {'decision': decision, 'comment': comment})
        return {'ok': True, 'intake_id': intake_id, 'status': status, 'legal_decision': decision}

    def qa_decision(self, con, intake_id: str, decision: str, actor: str, actor_role: str, comment: str) -> dict:
        if actor_role != 'admin':
            raise PermissionError('El QA de integridad requiere administración.')
        if decision not in QA_DECISIONS:
            raise ValueError('Decisión de QA inválida.')
        if len((comment or '').strip()) < 15:
            raise ValueError('Registre un comentario de QA de al menos 15 caracteres.')
        row = con.execute('SELECT * FROM canonical_intake_records WHERE id=?', (intake_id,)).fetchone()
        if not row:
            raise ValueError('Registro de ingreso no encontrado.')
        if row['legal_decision'] != 'Aprobado':
            raise ValueError('QA solo puede decidir después de aprobación jurídica del mismo registro.')
        if str(row['legal_actor']) == str(actor):
            raise ValueError('La aprobación jurídica y el QA deben corresponder a personas distintas.')
        t = _now()
        if decision == 'Rechazado':
            con.execute('UPDATE canonical_intake_records SET qa_decision=?,qa_actor=?,qa_comment=?,qa_at=?,status=? WHERE id=?',
                        (decision, actor, comment, t, 'Rechazado por QA', intake_id))
            self._event(con, intake_id, 'qa_integrity_decision', actor, actor_role, {'decision': decision, 'comment': comment})
            return {'ok': True, 'intake_id': intake_id, 'status': 'Rechazado por QA', 'qa_decision': decision}

        if not row['stored_path']:
            raise ValueError('El binario de cuarentena no está disponible.')
        if self.object_store and (self.object_store.is_reference(row['stored_path']) or str(row['stored_path']).endswith('.lzenc')):
            try:
                raw_verified = self.object_store.get(con, row['stored_path'])
            except Exception as exc:
                raise ValueError('El binario cifrado de cuarentena no supera la verificación.') from exc
        elif not Path(row['stored_path']).is_file():
            raise ValueError('El binario de cuarentena no está disponible.')
        else:
            raw_verified = Path(row['stored_path']).read_bytes()
        if not row['extraction_path'] or not Path(row['extraction_path']).is_file():
            raise ValueError('La extracción auditable no está disponible; complete la extracción antes de QA.')
        extraction = json.loads(Path(row['extraction_path']).read_text(encoding='utf-8'))
        verified_name = f"{row['product_code']}_{row['sha256'][:12]}_{self._safe_name(row['original_name'])}"
        if self.object_store:
            self.object_store.put(con, f"canonical/verified/{row['product_code']}", verified_name, raw_verified, row['detected_type'], actor)
        else:
            verified_path = self.verified / verified_name
            shutil.copy2(row['stored_path'], verified_path)
        canonical_result = self.canonical.register_source(
            con, row['product_code'], verified_name, row['sha256'], row['size_bytes'], actor,
            {'extraction_file': str(Path(row['extraction_path']).relative_to(self.root)), 'intake_id': intake_id, 'artifact_key': row['artifact_key']},
            verified=True,
        )
        trace = self.traceability.register_source_extraction(
            con, row['product_code'], verified_name, row['sha256'], row['size_bytes'], extraction,
            str(Path(row['extraction_path']).relative_to(self.root)), actor, verified=True,
        )
        con.execute('''UPDATE canonical_intake_records SET qa_decision=?,qa_actor=?,qa_comment=?,qa_at=?,status='Importado y verificado',source_file_id=? WHERE id=?''',
                    (decision, actor, comment, t, trace['file_id'], intake_id))
        self._event(con, intake_id, 'qa_integrity_decision', actor, actor_role, {'decision': decision, 'comment': comment})
        self._event(con, intake_id, 'promoted_to_verified_source', actor, actor_role, {
            'verified_name': verified_name, 'source_file_id': trace['file_id'], 'fragment_count': trace['fragment_count'],
            'canonical_snapshot': canonical_result.get('snapshot_id'), 'sha256': row['sha256'],
        })
        return {'ok': True, 'intake_id': intake_id, 'status': 'Importado y verificado', 'qa_decision': decision, 'traceability': trace, **canonical_result}

    def _artifact_status(self, con, code: str, artifact: dict) -> dict:
        row = con.execute('''SELECT * FROM canonical_intake_records WHERE product_code=? AND artifact_key=?
                             ORDER BY CASE status WHEN 'Importado y verificado' THEN 1 WHEN 'Identidad jurídica confirmada' THEN 2 WHEN 'En cuarentena' THEN 3 ELSE 4 END, uploaded_at DESC LIMIT 1''',
                          (code, artifact['key'])).fetchone()
        return {
            **artifact,
            'satisfied': bool(row and row['status'] == 'Importado y verificado'),
            'latest': self._public_record(row) if row else None,
        }

    def summary(self, con) -> dict:
        products = []
        for code, product in sorted(self.plan.items(), key=lambda x: (x[1].get('priority', 9), x[0])):
            artifacts = [self._artifact_status(con, code, x) for x in product.get('artifacts', [])]
            required = [x for x in artifacts if x.get('required')]
            satisfied = [x for x in required if x['satisfied']]
            records = con.execute('SELECT COUNT(*) total,SUM(CASE WHEN status="Importado y verificado" THEN 1 ELSE 0 END) verified FROM canonical_intake_records WHERE product_code=?', (code,)).fetchone()
            products.append({
                'product_code': code,
                'title': product.get('title', code),
                'priority': product.get('priority', 2),
                'required_artifacts': len(required),
                'satisfied_artifacts': len(satisfied),
                'coverage': round(len(satisfied) * 100 / max(1, len(required))),
                'records': records['total'] or 0,
                'verified_records': records['verified'] or 0,
                'artifacts': artifacts,
            })
        counts = con.execute('''SELECT COUNT(*) total,
            SUM(CASE WHEN status LIKE 'En cuarentena%' THEN 1 ELSE 0 END) quarantine,
            SUM(CASE WHEN status='Identidad jurídica confirmada' THEN 1 ELSE 0 END) legal_ok,
            SUM(CASE WHEN status='Importado y verificado' THEN 1 ELSE 0 END) verified,
            SUM(CASE WHEN status='Duplicado detectado' THEN 1 ELSE 0 END) duplicates,
            SUM(CASE WHEN status LIKE 'Rechazado%' THEN 1 ELSE 0 END) rejected
            FROM canonical_intake_records''').fetchone()
        record_ids = [x['id'] for x in con.execute('SELECT id FROM canonical_intake_records').fetchall()]
        broken_chains = 0
        for intake_id in record_ids:
            events = [dict(x) for x in con.execute('SELECT * FROM canonical_custody_events WHERE intake_id=? ORDER BY id', (intake_id,)).fetchall()]
            if events and not self.verify_chain(events):
                broken_chains += 1
        metrics = {k: counts[k] or 0 for k in counts.keys()}
        metrics['broken_chains'] = broken_chains
        return {
            'products': products,
            'metrics': metrics,
            'priority_products': sum(1 for x in products if x['priority'] == 1),
            'ready_products': sum(1 for x in products if x['coverage'] == 100),
            'notice': 'El archivo solo se incorpora como fuente verificada después de aprobación jurídica y QA de integridad sobre el mismo registro.',
        }

    def detail(self, con, code: str) -> dict | None:
        product = self.plan.get(code)
        if not product:
            return None
        records = [self._public_record(x) for x in con.execute('SELECT * FROM canonical_intake_records WHERE product_code=? ORDER BY uploaded_at DESC', (code,)).fetchall()]
        record_ids = [x['id'] for x in records]
        events = []
        if record_ids:
            placeholders = ','.join('?' for _ in record_ids)
            events = [dict(x) for x in con.execute(f'SELECT * FROM canonical_custody_events WHERE intake_id IN ({placeholders}) ORDER BY id DESC', record_ids).fetchall()]
        for record in records:
            chain_events = [x for x in events if x['intake_id'] == record['id']]
            record['chain_valid'] = self.verify_chain(chain_events) if chain_events else True
        artifacts = [self._artifact_status(con, code, x) for x in product.get('artifacts', [])]
        required = [x for x in artifacts if x.get('required')]
        coverage = round(sum(x['satisfied'] for x in required) * 100 / max(1, len(required)))
        return {'product': product, 'artifacts': artifacts, 'records': records, 'events': events, 'coverage': coverage}

    def record(self, con, intake_id: str):
        return con.execute('SELECT * FROM canonical_intake_records WHERE id=?', (intake_id,)).fetchone()

    def export_bytes(self, con) -> bytes:
        out = BytesIO()
        with ZipFile(out, 'w', ZIP_DEFLATED) as z:
            summary = self.summary(con)
            z.writestr('00_RESUMEN_INGESTA.json', json.dumps(summary, ensure_ascii=False, indent=2, default=str))
            for code in sorted(self.plan):
                z.writestr(f'{code}/ingesta_y_custodia.json', json.dumps(self.detail(con, code), ensure_ascii=False, indent=2, default=str))
        return out.getvalue()
