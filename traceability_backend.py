from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import re
import unicodedata

LINK_TYPES = {'Literal', 'Adaptado', 'Derivado', 'Referencia', 'Excepción justificada'}
LINK_STATUSES = {'Pendiente', 'Cotejado', 'Rechazado'}
APPROVAL_TYPES = {'legal', 'qa'}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def normalize_text(value: str) -> str:
    text = unicodedata.normalize('NFKD', value or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r'\{\{[^}]+\}\}', ' variable ', text)
    text = re.sub(r'\[\[[^\]]+\]\]', ' variable ', text)
    text = re.sub(r'[^a-z0-9áéíóúüñ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def token_set(value: str) -> set[str]:
    return {x for x in normalize_text(value).split() if len(x) > 2}


def similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    sa, sb = token_set(na), token_set(nb)
    jaccard = len(sa & sb) / max(1, len(sa | sb))
    sequence = SequenceMatcher(None, na, nb).ratio()
    containment = min(len(sa & sb) / max(1, len(sa)), len(sa & sb) / max(1, len(sb)))
    return round((sequence * 0.50 + jaccard * 0.35 + containment * 0.15) * 100, 2)


def classification(score: float) -> str:
    if score >= 92:
        return 'Coincidencia alta'
    if score >= 75:
        return 'Ajuste menor probable'
    if score >= 50:
        return 'Adaptación material probable'
    if score >= 25:
        return 'Referencia débil'
    return 'Sin correspondencia suficiente'


def block_text(block: dict) -> str:
    parts = [block.get('heading', ''), block.get('text', '')]
    parts.extend(block.get('bullets', []) or [])
    for row in block.get('table', []) or []:
        parts.extend(str(x) for x in row)
    return '\n'.join(str(x) for x in parts if x)


def semantic_diff(block_value: str, fragment_value: str) -> dict:
    block_tokens = token_set(block_value)
    source_tokens = token_set(fragment_value)
    added = sorted(block_tokens - source_tokens)
    omitted = sorted(source_tokens - block_tokens)
    score = similarity(block_value, fragment_value)
    return {
        'similarity_score': score,
        'semantic_class': classification(score),
        'terms_added_in_block': added[:40],
        'terms_omitted_from_source': omitted[:40],
        'added_count': len(added),
        'omitted_count': len(omitted),
        'requires_legal_review': True,
        'notice': 'La diferencia léxica no determina por sí sola cambio de efecto jurídico.',
    }


class TraceabilityCenter:
    """Trazabilidad exacta entre binarios fuente, fragmentos y bloques de plantilla.

    La similitud es una ayuda determinística de búsqueda. Nunca sustituye el cotejo jurídico.
    """

    def __init__(self, packages, templates, products):
        self.packages = {x['product_code']: x for x in packages}
        self.templates = templates
        self.products = {x['code']: x for x in products}

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_source_files(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          filename TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          size_bytes INTEGER NOT NULL,
          source_format TEXT NOT NULL,
          extraction_path TEXT,
          verified INTEGER NOT NULL DEFAULT 0,
          imported_by TEXT NOT NULL,
          imported_at TEXT NOT NULL,
          UNIQUE(product_code,sha256)
        );
        CREATE INDEX IF NOT EXISTS idx_csf_product ON canonical_source_files(product_code,verified,id DESC);

        CREATE TABLE IF NOT EXISTS canonical_source_fragments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_file_id INTEGER NOT NULL,
          product_code TEXT NOT NULL,
          locator_type TEXT NOT NULL,
          locator TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          fragment_text TEXT NOT NULL,
          normalized_text TEXT NOT NULL,
          fragment_hash TEXT NOT NULL,
          metadata_json TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(source_file_id) REFERENCES canonical_source_files(id),
          UNIQUE(source_file_id,fragment_hash,locator)
        );
        CREATE INDEX IF NOT EXISTS idx_csf_frag_product ON canonical_source_fragments(product_code,source_file_id,ordinal);

        CREATE TABLE IF NOT EXISTS canonical_block_trace_links(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          template_id TEXT NOT NULL,
          revision_id INTEGER,
          block_id TEXT NOT NULL,
          fragment_id INTEGER,
          link_type TEXT NOT NULL,
          status TEXT NOT NULL,
          similarity_score REAL NOT NULL DEFAULT 0,
          semantic_class TEXT NOT NULL,
          legal_note TEXT,
          exception_reason TEXT,
          linked_by TEXT NOT NULL,
          linked_at TEXT NOT NULL,
          legal_decision TEXT NOT NULL DEFAULT 'Pendiente',
          legal_actor TEXT,
          legal_comment TEXT,
          legal_at TEXT,
          qa_decision TEXT NOT NULL DEFAULT 'Pendiente',
          qa_actor TEXT,
          qa_comment TEXT,
          qa_at TEXT,
          FOREIGN KEY(fragment_id) REFERENCES canonical_source_fragments(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cbtl_block ON canonical_block_trace_links(template_id,block_id,id DESC);
        CREATE INDEX IF NOT EXISTS idx_cbtl_product ON canonical_block_trace_links(product_code,status,legal_decision,qa_decision);

        CREATE TABLE IF NOT EXISTS canonical_semantic_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          template_id TEXT NOT NULL,
          revision_id INTEGER,
          block_id TEXT NOT NULL,
          fragment_id INTEGER NOT NULL,
          similarity_score REAL NOT NULL,
          semantic_class TEXT NOT NULL,
          block_hash TEXT NOT NULL,
          fragment_hash TEXT NOT NULL,
          algorithm TEXT NOT NULL,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_csr_block ON canonical_semantic_runs(template_id,block_id,id DESC);

        CREATE TABLE IF NOT EXISTS canonical_publication_decisions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_code TEXT NOT NULL,
          snapshot_hash TEXT NOT NULL,
          decision TEXT NOT NULL,
          actor TEXT NOT NULL,
          actor_role TEXT NOT NULL,
          comment TEXT,
          gate_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cpd_product ON canonical_publication_decisions(product_code,id DESC);
        ''')

    @staticmethod
    def _fragment_payloads(extraction: dict) -> list[dict]:
        fmt = extraction.get('format', 'unknown')
        out: list[dict] = []
        ordinal = 0

        def add(locator_type: str, locator: str, text: str, metadata=None):
            nonlocal ordinal
            cleaned = re.sub(r'\s+', ' ', text or '').strip()
            if not cleaned:
                return
            ordinal += 1
            out.append({
                'locator_type': locator_type,
                'locator': locator,
                'ordinal': ordinal,
                'text': cleaned,
                'metadata': metadata or {},
            })

        if fmt == 'docx':
            for index, text in enumerate(extraction.get('paragraphs', []), 1):
                add('párrafo', f'Párrafo {index}', text, {'paragraph': index})
            for t_index, table in enumerate(extraction.get('tables', []), 1):
                for r_index, row in enumerate(table, 1):
                    add('tabla', f'Tabla {t_index}, fila {r_index}', ' | '.join(str(x) for x in row), {'table': t_index, 'row': r_index})
        elif fmt == 'pdf':
            for page in extraction.get('pages', []):
                p = int(page.get('page') or 0)
                chunks = [x.strip() for x in re.split(r'\n\s*\n|(?<=[.;:])\s*\n', page.get('text', '')) if x.strip()]
                if not chunks and page.get('text'):
                    chunks = [page['text']]
                for index, text in enumerate(chunks, 1):
                    add('página', f'Página {p}, fragmento {index}', text, {'page': p, 'fragment': index})
        elif fmt == 'xlsx':
            for sheet in extraction.get('sheets', []):
                name = sheet.get('name', 'Hoja')
                for row_index, row in enumerate(sheet.get('rows', []), 1):
                    add('hoja', f'{name}, fila {row_index}', ' | '.join(str(x) for x in row), {'sheet': name, 'row': row_index})
        elif fmt in {'txt', 'md'}:
            text = extraction.get('text', '')
            chunks = [x.strip() for x in re.split(r'\n\s*\n', text) if x.strip()]
            for index, chunk in enumerate(chunks, 1):
                add('sección', f'Sección {index}', chunk, {'section': index})
        return out

    def register_source_extraction(self, con, product_code: str, filename: str, digest: str,
                                   size_bytes: int, extraction: dict, extraction_path: str,
                                   actor: str, verified: bool = False) -> dict:
        if product_code not in self.packages:
            raise ValueError('Producto no registrado.')
        fmt = extraction.get('format', Path(filename).suffix.lower().lstrip('.') or 'unknown')
        row = con.execute('SELECT id FROM canonical_source_files WHERE product_code=? AND sha256=?', (product_code, digest)).fetchone()
        if row:
            file_id = row['id']
            con.execute('''UPDATE canonical_source_files SET filename=?,size_bytes=?,source_format=?,extraction_path=?,verified=CASE WHEN verified=1 OR ?=1 THEN 1 ELSE 0 END,imported_by=?,imported_at=? WHERE id=?''',
                        (filename, size_bytes, fmt, extraction_path, 1 if verified else 0, actor, _now(), file_id))
            con.execute('DELETE FROM canonical_source_fragments WHERE source_file_id=?', (file_id,))
        else:
            cur = con.execute('''INSERT INTO canonical_source_files(product_code,filename,sha256,size_bytes,source_format,extraction_path,verified,imported_by,imported_at)
                                 VALUES(?,?,?,?,?,?,?,?,?)''',
                              (product_code, filename, digest, size_bytes, fmt, extraction_path, 1 if verified else 0, actor, _now()))
            file_id = cur.lastrowid
        fragments = self._fragment_payloads(extraction)
        for fragment in fragments:
            text = fragment['text']
            norm = normalize_text(text)
            fh = sha256(text.encode('utf-8')).hexdigest()
            con.execute('''INSERT INTO canonical_source_fragments(source_file_id,product_code,locator_type,locator,ordinal,fragment_text,normalized_text,fragment_hash,metadata_json,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source_file_id,fragment_hash,locator) DO NOTHING''',
                        (file_id, product_code, fragment['locator_type'], fragment['locator'], fragment['ordinal'], text, norm, fh,
                         json.dumps(fragment['metadata'], ensure_ascii=False), _now()))
        return {'file_id': file_id, 'fragment_count': len(fragments), 'verified': bool(verified), 'format': fmt}

    def _templates_for(self, code: str) -> list[dict]:
        return [x for x in self.templates if x.get('product_code') == code]

    def _block_inventory(self, con, code: str) -> list[dict]:
        items = []
        for tpl in self._templates_for(code):
            state = con.execute('SELECT current_revision_id FROM canonical_template_state WHERE template_id=?', (tpl['template_id'],)).fetchone()
            revision_id = state['current_revision_id'] if state else None
            content = tpl
            if revision_id:
                row = con.execute('SELECT content_json FROM canonical_template_versions WHERE id=?', (revision_id,)).fetchone()
                if row:
                    try:
                        content = json.loads(row['content_json'])
                    except Exception:
                        content = tpl
            for block in content.get('blocks', []):
                required = bool(block.get('required', True)) and block.get('type') != 'control'
                latest = con.execute('''SELECT l.*,f.locator,f.fragment_text,s.filename,s.verified source_verified
                                        FROM canonical_block_trace_links l
                                        LEFT JOIN canonical_source_fragments f ON f.id=l.fragment_id
                                        LEFT JOIN canonical_source_files s ON s.id=f.source_file_id
                                        WHERE l.template_id=? AND l.block_id=?
                                          AND COALESCE(l.revision_id,0)=COALESCE(?,0)
                                        ORDER BY l.id DESC LIMIT 1''',
                                     (content.get('template_id', tpl['template_id']), block.get('id'), revision_id)).fetchone()
                items.append({
                    'product_code': code,
                    'template_id': content.get('template_id', tpl['template_id']),
                    'template_title': content.get('title', tpl.get('title')),
                    'revision_id': revision_id,
                    'block_id': block.get('id'),
                    'heading': block.get('heading') or block.get('id'),
                    'type': block.get('type', 'section'),
                    'required_for_gate': required,
                    'text': block_text(block),
                    'block_hash': sha256(block_text(block).encode('utf-8')).hexdigest(),
                    'link': dict(latest) if latest else None,
                })
        return items

    def gate(self, con, code: str) -> dict:
        files = [dict(x) for x in con.execute('SELECT * FROM canonical_source_files WHERE product_code=? ORDER BY id DESC', (code,)).fetchall()]
        verified_files = [x for x in files if x['verified']]
        blocks = self._block_inventory(con, code)
        required = [x for x in blocks if x['required_for_gate']]
        approved = []
        pending = []
        exceptions = []
        for item in required:
            link = item['link']
            ok = bool(link and link.get('status') == 'Cotejado' and link.get('legal_decision') == 'Aprobado' and link.get('qa_decision') == 'Aprobado')
            if ok:
                approved.append(item)
                if link.get('link_type') == 'Excepción justificada':
                    exceptions.append(item)
            else:
                pending.append(item)
        coverage = round(len(approved) * 100 / max(1, len(required)))
        reasons = []
        if not verified_files:
            reasons.append('No existe una fuente binaria verificada para el producto.')
        if pending:
            reasons.append(f'{len(pending)} bloques obligatorios no tienen trazabilidad dualmente aprobada.')
        return {
            'product_code': code,
            'passed': bool(verified_files) and not pending,
            'coverage': coverage,
            'total_blocks': len(blocks),
            'required_blocks': len(required),
            'approved_blocks': len(approved),
            'pending_blocks': len(pending),
            'exception_blocks': len(exceptions),
            'verified_source_files': len(verified_files),
            'reasons': reasons,
            'pending_ids': [x['block_id'] for x in pending[:100]],
        }

    def summary(self, con) -> dict:
        packages = []
        for code in sorted(self.packages):
            gate = self.gate(con, code)
            files = con.execute('SELECT COUNT(*) total,SUM(verified) verified FROM canonical_source_files WHERE product_code=?', (code,)).fetchone()
            packages.append({
                'product_code': code,
                'title': self.products.get(code, {}).get('title', code),
                'source_files': files['total'] or 0,
                'verified_files': files['verified'] or 0,
                **gate,
            })
        return {
            'packages': packages,
            'metrics': {
                'products': len(packages),
                'blocks': sum(x['total_blocks'] for x in packages),
                'required_blocks': sum(x['required_blocks'] for x in packages),
                'approved_blocks': sum(x['approved_blocks'] for x in packages),
                'pending_blocks': sum(x['pending_blocks'] for x in packages),
                'verified_sources': sum(x['verified_files'] for x in packages),
                'publication_ready': sum(1 for x in packages if x['passed']),
                'coverage_average': round(sum(x['coverage'] for x in packages) / max(1, len(packages))),
            },
            'notice': 'La similitud es una ayuda determinística de búsqueda; toda equivalencia jurídica requiere aprobación expresa del especialista y QA.',
        }

    def detail(self, con, code: str) -> dict | None:
        if code not in self.packages:
            return None
        files = [dict(x) for x in con.execute('SELECT * FROM canonical_source_files WHERE product_code=? ORDER BY verified DESC,id DESC', (code,)).fetchall()]
        fragments = con.execute('SELECT COUNT(*) FROM canonical_source_fragments WHERE product_code=?', (code,)).fetchone()[0]
        blocks = self._block_inventory(con, code)
        decisions = [dict(x) for x in con.execute('SELECT * FROM canonical_publication_decisions WHERE product_code=? ORDER BY id DESC LIMIT 20', (code,)).fetchall()]
        templates = []
        for tpl in self._templates_for(code):
            subset = [x for x in blocks if x['template_id'] == tpl['template_id']]
            req = [x for x in subset if x['required_for_gate']]
            approved = sum(bool(x['link'] and x['link'].get('status') == 'Cotejado' and x['link'].get('legal_decision') == 'Aprobado' and x['link'].get('qa_decision') == 'Aprobado') for x in req)
            templates.append({
                'template_id': tpl['template_id'],
                'title': tpl.get('title'),
                'blocks': len(subset),
                'required_blocks': len(req),
                'approved_blocks': approved,
                'coverage': round(approved * 100 / max(1, len(req))),
            })
        return {
            'package': self.packages[code],
            'product': self.products.get(code, {'code': code, 'title': code}),
            'gate': self.gate(con, code),
            'source_files': files,
            'fragment_count': fragments,
            'templates': templates,
            'blocks': blocks,
            'publication_decisions': decisions,
            'link_types': sorted(LINK_TYPES),
        }

    def search_fragments(self, con, code: str, query: str = '', limit: int = 30) -> list[dict]:
        if code not in self.packages:
            return []
        rows = [dict(x) for x in con.execute('''SELECT f.*,s.filename,s.verified FROM canonical_source_fragments f
                                                JOIN canonical_source_files s ON s.id=f.source_file_id
                                                WHERE f.product_code=? ORDER BY s.verified DESC,f.ordinal LIMIT 1000''', (code,)).fetchall()]
        if not query:
            return rows[:limit]
        scored = [(similarity(query, row['fragment_text']), row) for row in rows]
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, row in scored[:limit]:
            row = dict(row)
            row['similarity_score'] = score
            row['semantic_class'] = classification(score)
            out.append(row)
        return out

    def suggest(self, con, code: str, template_id: str, block_id: str, actor: str, limit: int = 5) -> dict:
        block = next((x for x in self._block_inventory(con, code) if x['template_id'] == template_id and x['block_id'] == block_id), None)
        if not block:
            raise ValueError('Bloque no encontrado.')
        candidates = self.search_fragments(con, code, block['text'], max(1, min(20, limit)))
        for row in candidates:
            row['diff'] = semantic_diff(block['text'], row['fragment_text'])
            con.execute('''INSERT INTO canonical_semantic_runs(product_code,template_id,revision_id,block_id,fragment_id,similarity_score,semantic_class,block_hash,fragment_hash,algorithm,created_by,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (code, template_id, block['revision_id'], block_id, row['id'], row.get('similarity_score', 0), row.get('semantic_class', ''),
                         block['block_hash'], row['fragment_hash'], 'normalize+jaccard+sequence-v1.5', actor, _now()))
        return {'block': block, 'candidates': candidates, 'notice': 'Sugerencia automática no vinculante. Debe cotejarse con contexto, estructura y efecto jurídico.'}

    def save_link(self, con, code: str, template_id: str, block_id: str, fragment_id: int | None,
                  link_type: str, actor: str, legal_note: str = '', exception_reason: str = '') -> dict:
        if link_type not in LINK_TYPES:
            raise ValueError('Tipo de vínculo inválido.')
        block = next((x for x in self._block_inventory(con, code) if x['template_id'] == template_id and x['block_id'] == block_id), None)
        if not block:
            raise ValueError('Bloque no encontrado.')
        fragment = None
        score = 0.0
        if link_type == 'Excepción justificada':
            if not exception_reason or len(exception_reason.strip()) < 20:
                raise ValueError('La excepción requiere una justificación sustancial de al menos 20 caracteres.')
        else:
            if not fragment_id:
                raise ValueError('Debe seleccionar un fragmento fuente.')
            fragment = con.execute('''SELECT f.*,s.verified,s.filename FROM canonical_source_fragments f
                                      JOIN canonical_source_files s ON s.id=f.source_file_id
                                      WHERE f.id=? AND f.product_code=?''', (fragment_id, code)).fetchone()
            if not fragment:
                raise ValueError('Fragmento fuente inválido.')
            if not fragment['verified']:
                raise ValueError('El fragmento pertenece a una fuente aún no verificada.')
            score = similarity(block['text'], fragment['fragment_text'])
        cur = con.execute('''INSERT INTO canonical_block_trace_links(product_code,template_id,revision_id,block_id,fragment_id,link_type,status,similarity_score,semantic_class,legal_note,exception_reason,linked_by,linked_at)
                             VALUES(?,?,?,?,?,?,"Pendiente",?,?,?,?,?,?)''',
                          (code, template_id, block['revision_id'], block_id, fragment_id, link_type, score, classification(score), legal_note, exception_reason, actor, _now()))
        return {'ok': True, 'link_id': cur.lastrowid, 'similarity_score': score, 'semantic_class': classification(score)}

    def approve_link(self, con, link_id: int, approval_type: str, decision: str,
                     actor: str, actor_role: str, comment: str = '') -> dict:
        if approval_type not in APPROVAL_TYPES:
            raise ValueError('Tipo de aprobación inválido.')
        if decision not in {'Aprobado', 'Rechazado'}:
            raise ValueError('Decisión inválida.')
        row = con.execute('SELECT * FROM canonical_block_trace_links WHERE id=?', (link_id,)).fetchone()
        if not row:
            raise ValueError('Vínculo no encontrado.')
        if approval_type == 'legal' and actor_role != 'specialist':
            raise PermissionError('La decisión jurídica requiere un especialista.')
        if approval_type == 'qa' and actor_role != 'admin':
            raise PermissionError('La decisión de QA requiere administración.')
        if approval_type == 'qa':
            if row['legal_decision'] != 'Aprobado':
                raise ValueError('QA solo puede decidir después de aprobación jurídica del mismo vínculo.')
            if str(row['legal_actor']) == str(actor):
                raise ValueError('La aprobación jurídica y el QA deben corresponder a personas distintas.')
            con.execute('UPDATE canonical_block_trace_links SET qa_decision=?,qa_actor=?,qa_comment=?,qa_at=? WHERE id=?',
                        (decision, actor, comment, _now(), link_id))
        else:
            con.execute('''UPDATE canonical_block_trace_links SET legal_decision=?,legal_actor=?,legal_comment=?,legal_at=?,qa_decision='Pendiente',qa_actor=NULL,qa_comment=NULL,qa_at=NULL WHERE id=?''',
                        (decision, actor, comment, _now(), link_id))
        updated = con.execute('SELECT * FROM canonical_block_trace_links WHERE id=?', (link_id,)).fetchone()
        status = 'Cotejado' if updated['legal_decision'] == 'Aprobado' and updated['qa_decision'] == 'Aprobado' else ('Rechazado' if decision == 'Rechazado' else 'Pendiente')
        con.execute('UPDATE canonical_block_trace_links SET status=? WHERE id=?', (status, link_id))
        return {'ok': True, 'link_id': link_id, 'status': status, 'legal_decision': updated['legal_decision'], 'qa_decision': updated['qa_decision']}

    def publication_decision(self, con, code: str, decision: str, actor: str, actor_role: str, comment: str = '') -> dict:
        if actor_role != 'admin':
            raise PermissionError('La decisión final de publicación requiere administración.')
        if decision not in {'Autorizar piloto controlado', 'Rechazar publicación'}:
            raise ValueError('Decisión de publicación inválida.')
        gate = self.gate(con, code)
        if decision == 'Autorizar piloto controlado' and not gate['passed']:
            raise ValueError('La publicación permanece bloqueada: ' + ' '.join(gate['reasons']))
        payload = json.dumps(gate, ensure_ascii=False, sort_keys=True)
        snapshot_hash = sha256(payload.encode('utf-8')).hexdigest()
        con.execute('''INSERT INTO canonical_publication_decisions(product_code,snapshot_hash,decision,actor,actor_role,comment,gate_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?)''', (code, snapshot_hash, decision, actor, actor_role, comment, payload, _now()))
        return {'ok': True, 'decision': decision, 'snapshot_hash': snapshot_hash, 'gate': gate}

    def export_bytes(self, con, code: str | None = None) -> bytes:
        if code:
            detail = self.detail(con, code)
            if not detail:
                return b''
            return json.dumps(detail, ensure_ascii=False, indent=2, default=str).encode('utf-8')
        memory = BytesIO()
        with ZipFile(memory, 'w', ZIP_DEFLATED) as z:
            summary = self.summary(con)
            z.writestr('00_RESUMEN_TRAZABILIDAD.json', json.dumps(summary, ensure_ascii=False, indent=2))
            for product_code in sorted(self.packages):
                z.writestr(f'{product_code}/trazabilidad.json', json.dumps(self.detail(con, product_code), ensure_ascii=False, indent=2, default=str))
        return memory.getvalue()
