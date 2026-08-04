from __future__ import annotations
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

class CoLa001CanonicalV251:
    VERSION = "2.51"
    def __init__(self, root: Path):
        self.root=Path(root); self.base=self.root/"app"/"assets"/"advanced-legal-library"/"CO-LA-001"
        self.manifest=self._load("MANIFEST_CO-LA-001.json"); q=self._load("PREGUNTAS_CANONICAS.json")
        self.steps=q["steps"]; self.questions=q["questions"]; self.profiles=self._load("PERFILES_LIQUIDACION.json")
        self.documents=self._load("DOCUMENTOS_CANONICOS.json"); self.validations=self._load("VALIDACIONES_CANONICAS.json")
        self.blocks=self._load("BLOQUES_CANONICOS.json"); self.sources=self._load("FUENTES_CANONICAS.json"); self.traceability=self._load("MATRIZ_TRAZABILIDAD.json")
        self._validate()
    def _load(self,n): return json.loads((self.base/n).read_text(encoding="utf-8"))
    @staticmethod
    def _get(data,path,default=None):
        cur=data
        for p in path.split('.'):
            if not isinstance(cur,dict) or p not in cur:return default
            cur=cur[p]
        return cur
    @staticmethod
    def _filled(v): return v not in (None,'') and (not isinstance(v,(list,dict)) or bool(v))
    @staticmethod
    def _num(v):
        try:return None if v in (None,'') else float(v)
        except (TypeError,ValueError):return None
    @staticmethod
    def _date(v):
        try:return datetime.strptime(v,'%Y-%m-%d').date() if v else None
        except (TypeError,ValueError):return None
    def _validate(self):
        actual={'steps':len(self.steps),'questions':len(self.questions),'profiles':len(self.profiles),'documents':len(self.documents),'validations':len(self.validations),'blocks':len(self.blocks),'sources':len(self.sources)}
        for k,v in actual.items():
            if self.manifest.get(k)!=v: raise ValueError(f'Conteo inconsistente {k}: {v}')
        for name,items in [('questions',self.questions),('profiles',self.profiles),('documents',self.documents),('validations',self.validations),('blocks',self.blocks),('sources',self.sources)]:
            ids=[x['id'] for x in items]
            if len(ids)!=len(set(ids)): raise ValueError(f'IDs duplicados en {name}')
    def summary(self): return {'manifest':self.manifest,'steps':self.steps,'questions':self.questions,'profiles':self.profiles,'documents':self.documents,'validations':self.validations,'blocks':self.blocks,'sources':self.sources,'traceability':self.traceability}
    def _missing(self,q,a):
        if not q.get('required'): return []
        path=q['variable_path']; val=self._get(a,path)
        if q.get('type') in {'group','structured'}:
            if not isinstance(val,dict): return [{'path':path,'question_id':q['id'],'step_id':q['step_id'],'label':q['label']}]
            return [{'path':f"{path}.{f['key']}",'question_id':q['id'],'step_id':q['step_id'],'label':f"{q['label']}: {f['label']}"} for f in q.get('fields',[]) if f.get('required') and not self._filled(val.get(f['key']))]
        return [] if self._filled(val) else [{'path':path,'question_id':q['id'],'step_id':q['step_id'],'label':q['label']}]
    def evaluate(self,a:dict[str,Any]):
        missing=[]
        for q in self.questions: missing.extend(self._missing(q,a))
        findings=[]; docs=['DOC-LA1-CALCULATION-001','ANX-LA1-CONCEPTS-001','ANX-LA1-EVIDENCE-001']; blocks=[x['id'] for x in self.blocks[:31]]
        def add(i,s,m): findings.append({'id':i,'severity':s,'message':m})
        if self._get(a,'scope.private_relation')!='yes': add('V-LA1-001','blocker','El producto solo calcula relaciones laborales privadas regidas por el derecho colombiano.')
        start=self._date(self._get(a,'relationship.start_date')); end=self._date(self._get(a,'relationship.end_date')); cutoff=self._date(self._get(a,'claim.cutoff_date'))
        if start and end and start>end: add('V-LA1-003','blocker','La fecha de inicio no puede ser posterior a la terminación o corte.')
        if end and cutoff and end>cutoff: add('V-LA1-003','blocker','La fecha de terminación no puede ser posterior a la fecha de corte del cálculo.')
        salary=self._num(self._get(a,'compensation.base_salary'))
        if salary is not None and salary<=0: add('V-LA1-004','blocker','El salario básico debe ser un valor positivo y verificable.')
        if self._get(a,'compensation.salary_type') in {'integral','mixed','unknown'}: add('V-LA1-005','review','El salario integral o discutido exige verificar pacto escrito, umbral, factor prestacional y conceptos excluidos.')
        if self._get(a,'compensation.variable.exists') is True:
            v=self._get(a,'compensation.variable',{}) or {}; avg=self._num(v.get('monthly_average')); supports=v.get('supports')
            if avg is None or avg<0: add('V-LA1-006','blocker','La remuneración variable requiere promedio cuantificado o reconstrucción documentada.')
            if supports!='complete': add('V-LA1-006','review','El promedio variable debe contrastarse con nómina, extractos, ventas, turnos y demás soportes del período aplicable.')
        if self._get(a,'compensation.transport_aid')=='unknown': add('V-LA1-007','review','Debe definirse la procedencia del auxilio de transporte o conectividad según salario, modalidad y tiempo efectivamente servido.')
        if self._get(a,'periods.confirmation')!='complete': add('V-LA1-008','review','Los períodos pendientes deben conciliarse por concepto con nómina, fondos y comprobantes para evitar duplicidad.')
        prior=self._get(a,'payments.prior',{}) or {}
        if any((self._num(v) or 0)<0 for v in prior.values()): add('V-LA1-009','blocker','Los pagos previos no pueden registrarse como valores negativos.')
        if self._get(a,'payments.deductions.exists') is True:
            d=self._get(a,'payments.deductions',{}) or {}
            docs.append('ANX-LA1-EVIDENCE-001'); blocks.append('LA1-B022')
            if not d.get('reason') or not d.get('authorization'): add('V-LA1-010','review','Todo descuento discutido exige concepto, soporte, autorización o fundamento legal y análisis de procedencia.')
        ctype=self._get(a,'relationship.contract_type'); without=self._get(a,'termination.without_cause_claim')
        if without in {'yes','unknown'} or self._get(a,'relationship.termination_type')=='without_cause':
            docs.append('DOC-LA1-CLAIM-001'); blocks.extend(['LA1-B018','LA1-B019','LA1-B020'])
            if ctype=='fixed' and not self._get(a,'relationship.special_term.fixed_end_date'): add('V-LA1-012','blocker','La indemnización de término fijo requiere fecha final pactada verificable.')
            if ctype=='work' and self._num(self._get(a,'relationship.special_term.work_remaining_days')) is None: add('V-LA1-012','blocker','La indemnización de obra o labor requiere estimar y soportar el período faltante.')
            if self._get(a,'termination.cause_support')!='complete': add('V-LA1-011','review','La causa y forma de terminación deben verificarse antes de definir la indemnización.')
        if self._get(a,'termination.moratory_claim') in {'yes','review'}:
            docs.append('DOC-LA1-MORATORY-001'); blocks.extend(['LA1-B041','LA1-B042','LA1-B043'])
            add('V-LA1-013','review','La indemnización moratoria no es automática: requiere analizar deuda, oportunidad de pago, conducta y buena fe del empleador.')
            if not self._filled(self._get(a,'termination.good_faith_facts')): add('V-LA1-013','review','Faltan hechos concretos para el análisis de buena fe y mora.')
        prot=self._get(a,'risk.special_protection')
        if prot=='yes': add('V-LA1-014','blocker','La protección especial exige revisión jurídica del despido, autorizaciones, reintegro, indemnizaciones y estrategia; la liquidación aritmética es insuficiente.')
        elif prot=='unknown': add('V-LA1-014','review','Debe descartarse estabilidad laboral reforzada u otra protección especial.')
        pub=self._get(a,'risk.public_sector')
        if pub=='yes': add('V-LA1-015','blocker','Los vínculos del sector público requieren régimen y jurisdicción específicos, fuera del motor ordinario privado.')
        elif pub=='unknown': add('V-LA1-015','review','Debe establecerse la naturaleza pública o privada del vínculo.')
        reality=self._get(a,'risk.contract_reality')
        if reality=='yes': add('V-LA1-016','blocker','La declaración de contrato realidad exige análisis probatorio y judicial; este motor no puede asumir automáticamente fechas, salario y prestaciones.')
        elif reality=='unknown': add('V-LA1-016','review','Debe definirse si existe controversia sobre la verdadera naturaleza del vínculo.')
        if self._get(a,'risk.collective_regime') in {'yes','unknown'}: add('V-LA1-017','review','Convenciones, pactos, laudos o beneficios extralegales pueden modificar bases, derechos y períodos.')
        proc=self._get(a,'risk.active_proceeding')
        if proc in {'conciliation','lawsuit','settlement'}: add('V-LA1-018','review','La actuación existente debe revisarse para evitar contradicciones, cosa juzgada, transacción, doble cobro o afectación de la estrategia.')
        earliest=self._date(self._get(a,'prescription.rights_dates.earliest')); claim=self._date(self._get(a,'prescription.last_written_claim'))
        if earliest:
            reference=cutoff or date.today(); days=(reference-earliest).days
            if days>=900:
                docs.append('DOC-LA1-PRESCRIPTION-001'); blocks.extend(['LA1-B038','LA1-B039','LA1-B040'])
                add('V-LA1-019','review','Existen derechos cercanos o superiores al horizonte trienal; debe reconstruirse exigibilidad e interrupción por reclamo escrito debidamente recibido.')
            if claim and claim<earliest: add('V-LA1-019','review','El reclamo informado es anterior al derecho más antiguo y puede no interrumpir su prescripción.')
        selection=self._get(a,'documents.selection',{}) or {}
        if selection.get('claim'): docs.append('DOC-LA1-CLAIM-001')
        if selection.get('support_request') or self._get(a,'evidence.support_level')!='complete': docs.append('DOC-LA1-SUPPORT-REQUEST-001')
        if selection.get('prescription_report'): docs.append('DOC-LA1-PRESCRIPTION-001')
        if selection.get('moratory_analysis'): docs.append('DOC-LA1-MORATORY-001')
        if self._get(a,'settlement.generate') is True:
            docs.extend(['DOC-LA1-CONCILIATION-001','AGR-LA1-PAYMENT-001','ACT-LA1-CLOSE-001']); blocks.extend(['LA1-B048','LA1-B049','LA1-B050','LA1-B051','LA1-B052','LA1-B053','LA1-B054'])
            terms=self._get(a,'settlement.payment_terms',{}) or {}
            if self._num(terms.get('installments')) is None or not terms.get('payment_channel'): add('V-LA1-020','review','La propuesta de pago debe definir monto, cuotas, vencimientos, canal, incumplimiento y alcance del cierre.')
        if self._get(a,'data.confirmed') is not True: add('V-LA1-021','blocker','La generación exige confirmar que datos, pagos y soportes corresponden a hechos verificables.')
        docs=list(dict.fromkeys(docs)); blocks=list(dict.fromkeys(blocks)); blockers=[x for x in findings if x['severity']=='blocker']; reviews=[x for x in findings if x['severity']=='review']
        essential=[x for x in missing if x['step_id'] in {'parties','relationship','salary','accruals','payments','documents'}]
        status='blocked' if blockers else 'incomplete' if essential else 'review_required' if reviews else 'ready'
        answered=len(self.questions)-len({x['question_id'] for x in missing}); completion=max(0,min(100,round(100*answered/len(self.questions))))
        return {'version':self.VERSION,'status':status,'blocked':bool(blockers),'findings':findings,'blockers':blockers,'reviews':reviews,'missing_fields':missing,'documents':docs,'blocks':blocks,'professional_reviews':sorted(set(['legal']*bool(findings)+['payroll_accounting']*bool(self._get(a,'compensation.variable.exists'))+['litigation']*bool(proc in {'conciliation','lawsuit','settlement'} or prot=='yes' or reality=='yes'))),'completion':{'answered':answered,'total':len(self.questions),'percent':completion},'explanations':['El informe separa cada concepto, período, base y pago previo para evitar duplicidades.','La indemnización moratoria, la protección reforzada y el contrato realidad no se resuelven mediante una fórmula automática.','La versión final debe ser revisada por un profesional con acceso a los soportes completos.']}
