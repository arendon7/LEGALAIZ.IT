from __future__ import annotations

from datetime import datetime
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
import json
import re

from docx_builder import build_docx
from premium_document_engine import format_display_value, format_cop, format_date_es
from economic_calculation_engine import (
    accrued_effective_interest, build_payment_schedule, effective_annual_rate,
    modality_rates, reconcile_amounts,
)

FACTORY_STATUSES = ['Borrador interno','En revisión jurídica','En QA técnico','Aprobado para piloto']
BLOCK_TYPES = {'section','clause','notice','control'}
APPROVAL_TYPES = {'legal','qa'}
VAR_RE = re.compile(r'\{\{\s*([A-Za-z0-9_\-]+)(?:\s*\|\s*([A-Za-z0-9_\-]+))?\s*\}\}')


class DocumentFactory:
    def __init__(self, templates, products, interviews, sources, eval_conditions):
        self.templates = {x['template_id']: x for x in templates}
        self.products = {x['code']: x for x in products}
        self.interviews = interviews
        self.sources = sources
        self.eval_conditions = eval_conditions
        parameter_path = Path(__file__).resolve().parent / 'data' / 'parameters.json'
        self.parameters = json.loads(parameter_path.read_text(encoding='utf-8')) if parameter_path.exists() else {}

    @staticmethod
    def now():
        return datetime.now().isoformat(timespec='seconds')

    def create_schema(self, con):
        con.executescript('''
        CREATE TABLE IF NOT EXISTS canonical_template_versions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          template_id TEXT NOT NULL,
          product_code TEXT NOT NULL,
          kind TEXT NOT NULL,
          version_label TEXT NOT NULL,
          workflow_status TEXT NOT NULL,
          content_json TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          created_by TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ctv_template ON canonical_template_versions(template_id,id DESC);
        CREATE TABLE IF NOT EXISTS canonical_template_state(
          template_id TEXT PRIMARY KEY,
          current_revision_id INTEGER NOT NULL,
          workflow_status TEXT NOT NULL,
          publication_revision_id INTEGER,
          updated_by TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(current_revision_id) REFERENCES canonical_template_versions(id)
        );
        CREATE TABLE IF NOT EXISTS canonical_template_approvals(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          template_id TEXT NOT NULL,
          revision_id INTEGER NOT NULL,
          approval_type TEXT NOT NULL,
          actor TEXT NOT NULL,
          actor_role TEXT NOT NULL,
          decision TEXT NOT NULL,
          comment TEXT,
          created_at TEXT NOT NULL,
          UNIQUE(template_id,revision_id,approval_type),
          FOREIGN KEY(revision_id) REFERENCES canonical_template_versions(id)
        );
        ''')

    def init_baselines(self, con):
        for tid, content in self.templates.items():
            exists=con.execute('SELECT 1 FROM canonical_template_state WHERE template_id=?',(tid,)).fetchone()
            if exists: continue
            raw=json.dumps(content,ensure_ascii=False,sort_keys=True)
            digest=sha256(raw.encode()).hexdigest()
            cur=con.execute('''INSERT INTO canonical_template_versions(template_id,product_code,kind,version_label,workflow_status,content_json,content_hash,created_by,note,created_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)''',
                (tid,content['product_code'],content['kind'],content.get('version_label','1.0'),'Borrador interno',raw,digest,'system','Línea base estructural de la Fábrica Documental v1.3.',self.now()))
            con.execute('''INSERT INTO canonical_template_state(template_id,current_revision_id,workflow_status,publication_revision_id,updated_by,updated_at)
                           VALUES(?,?,?,?,?,?)''',(tid,cur.lastrowid,'Borrador interno',None,'system',self.now()))

    def _content(self,row):
        return json.loads(row['content_json']) if row else None

    def _state_row(self,con,tid):
        return con.execute('''SELECT s.*,v.version_label,v.content_hash,v.product_code,v.kind,v.created_at revision_created_at,v.created_by
                              FROM canonical_template_state s JOIN canonical_template_versions v ON v.id=s.current_revision_id
                              WHERE s.template_id=?''',(tid,)).fetchone()

    def summary(self,con):
        rows=[]
        for row in con.execute('''SELECT s.*,v.version_label,v.product_code,v.kind,v.content_json,v.content_hash
                                  FROM canonical_template_state s JOIN canonical_template_versions v ON v.id=s.current_revision_id
                                  ORDER BY v.product_code,v.kind''').fetchall():
            content=self._content(row)
            approvals=con.execute('SELECT approval_type,decision,actor,created_at FROM canonical_template_approvals WHERE template_id=? AND revision_id=?',(row['template_id'],row['current_revision_id'])).fetchall()
            amap={a['approval_type']:dict(a) for a in approvals}
            rows.append({
                'template_id':row['template_id'],'product_code':row['product_code'],'kind':row['kind'],
                'title':content.get('title'),'version_label':row['version_label'],'workflow_status':row['workflow_status'],
                'blocks':len(content.get('blocks',[])),'variables':len(content.get('variables',[])),
                'legal_approval':amap.get('legal'),'qa_approval':amap.get('qa'),
                'published':row['publication_revision_id']==row['current_revision_id'],
                'content_hash':row['content_hash'],
            })
        return {'templates':rows,'metrics':{
            'templates':len(rows),'products':len({r['product_code'] for r in rows}),
            'approved':sum(r['workflow_status']=='Aprobado para piloto' for r in rows),
            'legal_pending':sum(not r['legal_approval'] for r in rows),
            'qa_pending':sum(not r['qa_approval'] for r in rows),
            'blocks':sum(r['blocks'] for r in rows),
        }}

    def detail(self,con,tid):
        state=self._state_row(con,tid)
        if not state:return None
        content=self._content(con.execute('SELECT content_json FROM canonical_template_versions WHERE id=?',(state['current_revision_id'],)).fetchone())
        revisions=[dict(x) for x in con.execute('''SELECT id,version_label,workflow_status,content_hash,created_by,note,created_at
                                                    FROM canonical_template_versions WHERE template_id=? ORDER BY id DESC''',(tid,)).fetchall()]
        approvals=[dict(x) for x in con.execute('''SELECT id,revision_id,approval_type,actor,actor_role,decision,comment,created_at
                                                   FROM canonical_template_approvals WHERE template_id=? ORDER BY id DESC''',(tid,)).fetchall()]
        return {'template_id':tid,'content':content,'state':dict(state),'revisions':revisions,'approvals':approvals,
                'validation':self.validate(tid,content),'workflow_options':FACTORY_STATUSES}

    def _strings(self,block):
        vals=[block.get('heading',''),block.get('text',''),block.get('notes','')]
        vals += [str(x) for x in block.get('bullets',[])]
        for row in block.get('table',[]): vals += [str(x) for x in row]
        return vals

    def validate(self,tid,content):
        errors=[]; warnings=[]
        if not isinstance(content,dict): return {'valid':False,'errors':['La plantilla debe ser un objeto.'],'warnings':[],'metrics':{}}
        for field in ('template_id','product_code','kind','title','version_label','blocks','variables'):
            if field not in content: errors.append(f'Falta {field}.')
        if errors:return {'valid':False,'errors':errors,'warnings':warnings,'metrics':{}}
        if content.get('template_id')!=tid:errors.append('El template_id no coincide con la ruta.')
        if content.get('product_code') not in self.products:errors.append('El producto no existe en el catálogo.')
        vars_=content.get('variables') if isinstance(content.get('variables'),list) else []
        var_ids=[]
        for v in vars_:
            vid=str(v.get('id','')).strip()
            if not vid:errors.append('Existe una variable sin ID.')
            elif vid in var_ids:errors.append(f'Variable duplicada: {vid}.')
            var_ids.append(vid)
        aliases=content.get('variable_aliases') or {}
        if not isinstance(aliases,dict):
            errors.append('variable_aliases debe ser un objeto.')
            aliases={}
        alias_owner={}
        for canonical, values in aliases.items():
            if canonical not in var_ids:
                errors.append(f'Alias definido para variable no declarada: {canonical}.')
            if not isinstance(values,list) or not values:
                errors.append(f'Los alias de {canonical} deben ser una lista no vacía.')
                continue
            for alias in values:
                alias=str(alias or '').strip()
                if not alias:
                    errors.append(f'{canonical} contiene un alias vacío.')
                elif alias in var_ids and alias != canonical:
                    errors.append(f'El alias {alias} también es una variable declarada.')
                elif alias in alias_owner and alias_owner[alias] != canonical:
                    errors.append(f'El alias {alias} está asignado a más de una variable.')
                else:
                    alias_owner[alias]=canonical
        source_ids={s.get('id') for s in self.sources.get(content.get('product_code'),[]) if s.get('id')}
        blocks=content.get('blocks') if isinstance(content.get('blocks'),list) else []
        if not blocks:errors.append('La plantilla no contiene bloques.')
        ids=[]; controls=0; referenced=set()
        for i,b in enumerate(blocks,1):
            bid=str(b.get('id','')).strip()
            if not bid:errors.append(f'Bloque {i}: falta ID.')
            elif bid in ids:errors.append(f'Bloque duplicado: {bid}.')
            ids.append(bid)
            if b.get('type') not in BLOCK_TYPES:errors.append(f'Bloque {bid or i}: tipo inválido.')
            if not str(b.get('heading','')).strip():errors.append(f'Bloque {bid or i}: falta título.')
            if b.get('type')=='control': controls+=1
            for text in self._strings(b): referenced.update(match[0] for match in VAR_RE.findall(text))
            cond=b.get('condition')
            if cond:
                field=cond.get('field') if isinstance(cond,dict) else None
                if field and field not in var_ids:warnings.append(f'Bloque {bid}: condición usa variable no declarada {field}.')
            for sid in b.get('source_ids',[]):
                if sid not in source_ids:warnings.append(f'Bloque {bid}: fuente {sid} no está registrada para el producto.')
        if controls<1:errors.append('Debe existir al menos un bloque de control de uso.')
        missing=sorted(referenced-set(var_ids))
        if missing:warnings.append('Variables usadas pero no declaradas: '+', '.join(missing))
        unused=sorted(set(var_ids)-referenced)
        if unused:warnings.append(f'{len(unused)} variables declaradas aún no aparecen en los bloques.')
        if 'definitiv' in json.dumps(content,ensure_ascii=False).lower():warnings.append('Revise expresiones que puedan presentar el resultado como definitivo.')
        return {'valid':not errors,'errors':errors,'warnings':warnings,'metrics':{
            'blocks':len(blocks),'variables':len(var_ids),'referenced_variables':len(referenced),'control_blocks':controls,'sources_linked':sum(len(b.get('source_ids',[])) for b in blocks)}}

    def save(self,con,tid,content,actor,note,status='Borrador interno'):
        result=self.validate(tid,content)
        if not result['valid']:raise ValueError('; '.join(result['errors']))
        if status not in ('Borrador interno','En revisión jurídica'):status='Borrador interno'
        raw=json.dumps(content,ensure_ascii=False,sort_keys=True)
        digest=sha256(raw.encode()).hexdigest()
        cur=con.execute('''INSERT INTO canonical_template_versions(template_id,product_code,kind,version_label,workflow_status,content_json,content_hash,created_by,note,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)''',(tid,content['product_code'],content['kind'],content.get('version_label','1.0'),status,raw,digest,actor,note,self.now()))
        con.execute('''UPDATE canonical_template_state SET current_revision_id=?,workflow_status=?,publication_revision_id=NULL,updated_by=?,updated_at=? WHERE template_id=?''',(cur.lastrowid,status,actor,self.now(),tid))
        return {'ok':True,'revision_id':cur.lastrowid,'workflow_status':status,'content_hash':digest,'validation':result}

    def approve(self,con,tid,actor,actor_role,approval_type,decision,comment=''):
        if approval_type not in APPROVAL_TYPES:raise ValueError('Tipo de aprobación inválido.')
        if decision not in ('approve','reject'):raise ValueError('Decisión inválida.')
        if approval_type=='legal' and actor_role!='specialist':raise PermissionError('La aprobación jurídica requiere un especialista.')
        if approval_type=='qa' and actor_role!='admin':raise PermissionError('La aprobación de QA requiere administración.')
        state=self._state_row(con,tid)
        if not state:raise ValueError('Plantilla no encontrada.')
        rid=state['current_revision_id']
        if approval_type=='qa':
            legal=con.execute("SELECT decision,actor FROM canonical_template_approvals WHERE template_id=? AND revision_id=? AND approval_type='legal'",(tid,rid)).fetchone()
            if not legal or legal['decision']!='approve':raise ValueError('QA solo puede aprobar después de la aprobación jurídica de la misma revisión.')
            if str(legal['actor']) == str(actor):raise ValueError('La aprobación jurídica y el QA deben ser realizados por personas distintas sobre la misma revisión.')
        con.execute('''INSERT INTO canonical_template_approvals(template_id,revision_id,approval_type,actor,actor_role,decision,comment,created_at)
                       VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(template_id,revision_id,approval_type) DO UPDATE SET actor=excluded.actor,actor_role=excluded.actor_role,decision=excluded.decision,comment=excluded.comment,created_at=excluded.created_at''',
                    (tid,rid,approval_type,actor,actor_role,decision,comment,self.now()))
        legal=con.execute("SELECT decision FROM canonical_template_approvals WHERE template_id=? AND revision_id=? AND approval_type='legal'",(tid,rid)).fetchone()
        qa=con.execute("SELECT decision FROM canonical_template_approvals WHERE template_id=? AND revision_id=? AND approval_type='qa'",(tid,rid)).fetchone()
        if decision=='reject':status='Borrador interno'; published=None
        elif legal and legal['decision']=='approve' and qa and qa['decision']=='approve':status='Aprobado para piloto';published=rid
        elif legal and legal['decision']=='approve':status='En QA técnico';published=None
        else:status='En revisión jurídica';published=None
        con.execute('UPDATE canonical_template_state SET workflow_status=?,publication_revision_id=?,updated_by=?,updated_at=? WHERE template_id=?',(status,published,actor,self.now(),tid))
        return {'ok':True,'revision_id':rid,'workflow_status':status,'published':published==rid}

    def revision_content(self,con,tid,rid):
        row=con.execute('SELECT content_json FROM canonical_template_versions WHERE template_id=? AND id=?',(tid,rid)).fetchone()
        return self._content(row)

    def compare(self,con,tid,from_id,to_id):
        a=self.revision_content(con,tid,from_id);b=self.revision_content(con,tid,to_id)
        if not a or not b:return None
        al=json.dumps(a,ensure_ascii=False,indent=2,sort_keys=True).splitlines()
        bl=json.dumps(b,ensure_ascii=False,indent=2,sort_keys=True).splitlines()
        lines=list(unified_diff(al,bl,fromfile=f'revisión-{from_id}',tofile=f'revisión-{to_id}',lineterm=''))
        amap={x['id']:x for x in a.get('blocks',[])};bmap={x['id']:x for x in b.get('blocks',[])}
        return {'from_revision':from_id,'to_revision':to_id,'diff_lines':lines[:800],
                'blocks_added':sorted(set(bmap)-set(amap)),'blocks_removed':sorted(set(amap)-set(bmap)),
                'blocks_changed':sorted(k for k in set(amap)&set(bmap) if amap[k]!=bmap[k])}

    def _format_value(self,key,value,variable_defs=None,override=None):
        variable_defs = variable_defs or {}
        return format_display_value(key, value, variable_defs.get(key, {}), override=override)

    def _replace(self,text,answers,variable_defs=None):
        return VAR_RE.sub(lambda m:self._format_value(m.group(1),answers.get(m.group(1)),variable_defs,m.group(2)),str(text or ''))

    def _normalize_answers(self, content, answers):
        normalized=dict(answers or {})
        for canonical, aliases in (content.get('variable_aliases') or {}).items():
            if normalized.get(canonical) not in (None, ''):
                continue
            for alias in aliases or []:
                if normalized.get(alias) not in (None, ''):
                    normalized[canonical]=normalized[alias]
                    break
        if content.get('product_code') == 'CO-CD-004':
            prm = self.parameters.get('CO-CD-004', {})
            reconciliation = reconcile_amounts(
                principal=normalized.get('principal'),
                payments=normalized.get('partial_payments_total'),
                charges=normalized.get('other_charges'),
                reported_balance=normalized.get('reported_balance'),
                agreement_total=normalized.get('agreement_total'),
            )
            rate_ea = effective_annual_rate(normalized.get('interest_rate'), normalized.get('interest_period')) if normalized.get('interest_agreed') == 'Sí' else 0
            rates = modality_rates(prm, normalized.get('interest_modality'))
            schedule = build_payment_schedule(
                normalized.get('agreement_total'), normalized.get('installments'),
                normalized.get('first_payment_date'), normalized.get('frequency'),
            )
            accrued = accrued_effective_interest(
                reconciliation.get('expected_principal_balance'), rate_ea,
                normalized.get('due_date'), prm.get('reference_date'),
            ) if normalized.get('interest_agreed') == 'Sí' else {'calculable': False, 'interest': 0.0, 'days': 0}
            normalized['_economic_calculation'] = {
                'reconciliation': reconciliation,
                'effective_annual_rate': float(rate_ea),
                'rates': {k:(float(v) if hasattr(v, 'as_tuple') else v) for k,v in rates.items()},
                'schedule': schedule,
                'accrued_interest': accrued,
                'valid_from': prm.get('interest_valid_from'),
                'valid_to': prm.get('interest_valid_to'),
                'resolution': prm.get('interest_resolution'),
            }
        return normalized

    def render(self,content,answers):
        answers=self._normalize_answers(content,answers)
        sections=[];included=[];excluded=[]
        variable_defs={v.get('id'):v for v in content.get('variables',[]) if v.get('id')}
        for block in content.get('blocks',[]):
            cond=block.get('condition')
            include=True
            if cond:
                try:include=bool(self.eval_conditions(cond,answers))
                except Exception:include=False
            (included if include else excluded).append(block.get('id'))
            if not include:continue
            sec={'heading':self._replace(block.get('heading'),answers,variable_defs),'_type':block.get('type','section'),'page_break_before':bool(block.get('page_break_before'))}
            if block.get('text'):sec['text']=self._replace(block.get('text'),answers,variable_defs)
            if block.get('bullets'):sec['bullets']=[self._replace(x,answers,variable_defs) for x in block['bullets']]
            computed = block.get('computed_table')
            economic = answers.get('_economic_calculation') or {}
            if computed == 'economic_reconciliation':
                r = economic.get('reconciliation') or {}
                sec['table'] = [
                    ['Concepto','Valor'],
                    ['Capital original', format_cop(r.get('principal'), include_words=False)],
                    ['Abonos confirmados', format_cop(r.get('payments'), include_words=False)],
                    ['Cargos soportados', format_cop(r.get('charges'), include_words=False)],
                    ['Saldo explicado', format_cop(r.get('explained_balance'), include_words=False)],
                    ['Saldo informado', format_cop(r.get('reported_balance'), include_words=False)],
                    ['Diferencia', format_cop(r.get('balance_difference'), include_words=False)],
                    ['Resultado', 'Conciliado' if r.get('balance_reconciled') else 'Requiere conciliación'],
                ]
            elif computed == 'interest_control':
                rates = economic.get('rates') or {}; accrued = economic.get('accrued_interest') or {}
                sec['table'] = [
                    ['Control','Resultado'],
                    ['Modalidad', str(rates.get('modality') or 'No definida')],
                    ['Tasa informada equivalente', f"{economic.get('effective_annual_rate',0):.4f}% E.A."],
                    ['Interés bancario corriente', f"{rates.get('ibc_ea',0):.2f}% E.A."],
                    ['Límite máximo de referencia', f"{rates.get('maximum_ea',0):.2f}% E.A."],
                    ['Vigencia', f"{format_date_es(economic.get('valid_from'))} a {format_date_es(economic.get('valid_to'))}"],
                    ['Fuente paramétrica', str(economic.get('resolution') or 'Revalidación pendiente')],
                    ['Interés causado preliminar', format_cop(accrued.get('interest'), include_words=False) if accrued.get('calculable') else 'No calculable con los datos aportados'],
                ]
            elif computed == 'payment_schedule':
                schedule = economic.get('schedule') or {}
                sec['table'] = [['Cuota','Fecha','Valor','Estado']] + [
                    [str(row.get('number')), format_date_es(row.get('due_date')), format_cop(row.get('amount'), include_words=False), str(row.get('status') or 'Pendiente')]
                    for row in schedule.get('rows', [])
                ]
                if schedule.get('warnings'):
                    sec['bullets'] = list(sec.get('bullets') or []) + list(schedule['warnings'])
            elif block.get('table'):
                sec['table']=[[self._replace(x,answers,variable_defs) for x in row] for row in block['table']]
            sections.append(sec)
        return {'title':self._replace(content.get('title'),answers,variable_defs),'subtitle':self._replace(content.get('subtitle'),answers,variable_defs),'sections':sections,'included_blocks':included,'excluded_blocks':excluded}

    def preview(self,con,tid,answers,revision_id=None):
        state=self._state_row(con,tid)
        if not state:return None
        rid=revision_id or state['current_revision_id']
        content=self.revision_content(con,tid,rid)
        rendered=self.render(content,answers or {})
        rendered['revision_id']=rid;rendered['workflow_status']=state['workflow_status']
        return rendered

    def published_for_product(self,con,product_code):
        rows=con.execute('''SELECT s.template_id,s.publication_revision_id,v.content_json,v.content_hash
                            FROM canonical_template_state s JOIN canonical_template_versions v ON v.id=s.publication_revision_id
                            WHERE s.publication_revision_id IS NOT NULL AND v.product_code=? ORDER BY v.kind''',(product_code,)).fetchall()
        return [{'template_id':r['template_id'],'revision_id':r['publication_revision_id'],'content_hash':r['content_hash'],'content':json.loads(r['content_json'])} for r in rows]

    def build_preview_docx(self,con,tid,answers,target_dir,revision_id=None):
        preview=self.preview(con,tid,answers,revision_id)
        if not preview:return None
        state=self._state_row(con,tid);rid=preview['revision_id']
        content=self.revision_content(con,tid,rid)
        filename=re.sub(r'[^A-Za-z0-9._-]+','_',f"{tid}_rev{rid}_{content.get('filename_suffix','documento')}.docx")
        path=Path(target_dir)/filename
        build_docx(path,preview['title'],preview['subtitle'],[
            ('Plantilla',tid),('Revisión',str(rid)),('Estado',state['workflow_status']),('Hash',state['content_hash'][:24]+'…')],preview['sections'])
        return path
