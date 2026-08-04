from __future__ import annotations
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

class CoTr002CanonicalV254:
    VERSION = "2.54"
    def __init__(self, root: Path):
        self.root=Path(root); self.base=self.root/"app"/"assets"/"advanced-legal-library"/"CO-TR-002"
        self.manifest=self._load("MANIFEST_CO-TR-002.json"); q=self._load("PREGUNTAS_CANONICAS.json")
        self.steps=q["steps"]; self.questions=q["questions"]; self.profiles=self._load("PERFILES_FOTODETECCION.json")
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
        findings=[]; docs=['DOC-TR2-DIAG-001','DOC-TR2-PETITION-001','ANX-TR2-EVIDENCE-001','ANX-TR2-DEADLINES-001','ACT-TR2-FILING-001']; blocks=[x['id'] for x in self.blocks[:24]]
        def add(i,s,m): findings.append({'id':i,'severity':s,'message':m})
        if self._get(a,'scope.colombian_traffic_case')!='yes': add('V-TR2-001','blocker','El producto solo cubre actuaciones administrativas de tránsito en Colombia.')
        role=self._get(a,'petitioner.role'); ident=self._get(a,'petitioner.identity',{}) or {}; auth=self._get(a,'authority.identity',{}) or {}
        if not role or not ident.get('name') or not ident.get('id_number') or not auth.get('name'): add('V-TR2-002','blocker','Faltan identidad, calidad del peticionario o autoridad destinataria.')
        event=self._date(self._get(a,'case.identifiers.event_date')); issue=self._date(self._get(a,'case.identifiers.issue_date'))
        if event and event>date.today(): add('V-TR2-003','blocker','La fecha de la presunta infracción no puede ser futura.')
        if event and issue and issue<event: add('V-TR2-003','blocker','La fecha de expedición o validación no puede anteceder a la presunta infracción.')
        timeline=self._get(a,'notice.timeline',{}) or {}; sent=self._date(timeline.get('sent_date')); received=self._date(timeline.get('received_date')); returned=self._date(timeline.get('returned_date')); knowledge=self._date(self._get(a,'notice.actual_knowledge.date'))
        if sent and received and received<sent: add('V-TR2-003','blocker','La recepción no puede anteceder al envío informado.')
        if sent and returned and returned<sent: add('V-TR2-003','blocker','La devolución no puede anteceder al envío informado.')
        runt=self._get(a,'runt.status_at_event'); address=self._get(a,'notice.address_match')
        if runt in {'outdated','not_registered','unknown'} or address in {'different','incomplete','unknown'}: add('V-TR2-004','review','Debe reconstruirse el histórico RUNT y compararse con la dirección utilizada por la autoridad.')
        notice=self._get(a,'notice.comparendo_received'); method=self._get(a,'notice.method')
        if notice in {'no','unknown'} or method in {'none','other'}:
            docs.append('DOC-TR2-NOTICE-001'); blocks.extend(['TR2-B018','TR2-B019','TR2-B020','TR2-B021','TR2-B043'])
            add('V-TR2-005','review','La falta o defecto de comunicación exige revisar medio, fecha, dirección, entrega, devolución y conocimiento efectivo; no produce automáticamente la anulación.')
        elif notice=='yes' and knowledge and received and knowledge!=received:
            add('V-TR2-005','review','La fecha de conocimiento efectivo difiere de la recepción informada y debe explicarse con soportes.')
        if self._get(a,'notice.method')=='email' and self._get(a,'notice.electronic_consent') in {'no','unknown'}: add('V-TR2-005','review','Debe verificarse la validez del canal electrónico utilizado para la notificación.')
        auth_status=self._get(a,'sast.authorization_status'); signaling=self._get(a,'sast.signaling')
        if auth_status in {'not_found','unknown'} or signaling in {'missing','insufficient','unknown'}:
            docs.append('ANX-TR2-SAST-001'); blocks.extend(['TR2-B011','TR2-B012','TR2-B013','TR2-B014'])
            add('V-TR2-006','review','La autorización, ubicación y señalización del SAST deben verificarse para la fecha de la detección.')
        if self._get(a,'sast.detection_type')=='speed_device' and self._get(a,'sast.speed_measurement') not in {'complete','not_applicable'}:
            docs.append('ANX-TR2-SAST-001'); blocks.append('TR2-B015'); add('V-TR2-007','review','La medición de velocidad requiere revisar calibración, trazabilidad metrológica y correspondencia del equipo.')
        if self._get(a,'sast.agent_validation') in {'not_documented','unknown'}: add('V-TR2-008','review','Debe solicitarse la validación realizada por autoridad o agente competente y su trazabilidad.')
        was_driver=self._get(a,'responsibility.was_driver'); duty=self._get(a,'responsibility.owner_duty_category')
        if role in {'owner','company'} and was_driver in {'no','unknown'}:
            add('V-TR2-009','review','La calidad de propietario no basta por sí sola para imponer responsabilidad por la conducta de otra persona; debe examinarse la imputación concreta.')
        if duty in {'soat','technical_review','route_or_schedule','speed','red_light'}:
            add('V-TR2-010','review','La conducta puede relacionarse con un deber legal del propietario, pero la sanción exige procedimiento, vinculación, prueba y culpabilidad.')
        rel=self._get(a,'vehicle.relationship')
        if rel in {'sold','stolen','owner_no_control'} or self._get(a,'responsibility.transfer.exists')=='yes' or self._get(a,'responsibility.theft.exists')=='yes':
            add('V-TR2-011','review','La pérdida de control material, venta, entrega o hurto debe probarse y relacionarse temporalmente con la infracción.')
        resolution=self._get(a,'stage.resolution_exists')
        if resolution in {'yes','unknown'}:
            docs.append('DOC-TR2-REVOCATION-001'); blocks.extend(['TR2-B024','TR2-B025','TR2-B027','TR2-B028','TR2-B044'])
            add('V-TR2-012','review','Debe obtenerse la resolución, su notificación, constancia de ejecutoria y recursos antes de definir la estrategia.')
        else:
            docs.append('DOC-TR2-HEARING-001'); blocks.extend(['TR2-B026','TR2-B041','TR2-B042'])
        coercive=self._get(a,'stage.coercive')
        if coercive in {'payment_order','exceptions_pending','embargo'}:
            docs.append('DOC-TR2-COERCIVE-001'); blocks.extend(['TR2-B030','TR2-B031','TR2-B032']); add('V-TR2-013','blocker','El cobro coactivo o una medida cautelar exige revisión especializada inmediata; la automatización queda limitada a diagnóstico y solicitud de expediente.')
        process=self._get(a,'stage.active_process')
        if process in {'tutela','administrative_lawsuit','other'}: add('V-TR2-014','blocker','La actuación judicial activa exige coordinación procesal y no debe ser contradicha por documentos automáticos.')
        if self._get(a,'stage.payment') in {'discount_paid','full_paid','payment_agreement'}: add('V-TR2-015','review','El pago debe analizarse por sus efectos, oportunidad y soportes; no genera devolución automática.')
        if self._get(a,'strategy.documents.selection.revocation') is True: docs.append('DOC-TR2-REVOCATION-001'); add('V-TR2-016','review','La revocatoria directa no revive términos judiciales ni sustituye recursos legalmente disponibles.')
        urgency=self._get(a,'deadlines.urgency')
        if urgency in {'under_3_days','under_10_days'}: add('V-TR2-017','review','Existe urgencia procesal: debe verificarse hoy mismo el expediente, el acto y el término aplicable.')
        if self._get(a,'evidence.integrity_concern')=='yes': add('V-TR2-018','blocker','No se generarán documentos ante indicios de falsedad, alteración de soportes o suplantación.')
        if self._get(a,'case.multiple')=='yes': add('V-TR2-019','review','Cada comparendo debe separarse por acto, fecha, dispositivo, notificación, resolución y etapa procesal.')
        prior=self._get(a,'evidence.prior_actions',{}) or {}
        if prior.get('exists')=='yes' and prior.get('answered') in {'no','unknown'}:
            docs.append('DOC-TR2-REITERATION-001'); blocks.extend(['TR2-B049','TR2-B050','TR2-B051'])
        objective=self._get(a,'strategy.objective'); selection=self._get(a,'documents.selection',{}) or {}
        if objective=='registry_correction' or selection.get('registry_correction'): docs.append('DOC-TR2-CORRECTION-001')
        if objective=='technical_review': docs.append('ANX-TR2-SAST-001')
        if objective=='coercive_defense' or selection.get('coercive_file'): docs.append('DOC-TR2-COERCIVE-001')
        if selection.get('notice_claim'): docs.append('DOC-TR2-NOTICE-001')
        if selection.get('hearing_request'): docs.append('DOC-TR2-HEARING-001')
        if selection.get('reiteration'): docs.append('DOC-TR2-REITERATION-001')
        if self._get(a,'data.confirmed') is not True: add('V-TR2-020','blocker','La generación exige confirmar que los datos y soportes corresponden a hechos verificables.')
        docs=list(dict.fromkeys(docs)); blocks=list(dict.fromkeys(blocks)); blockers=[x for x in findings if x['severity']=='blocker']; reviews=[x for x in findings if x['severity']=='review']
        essential=[x for x in missing if x['step_id'] in {'parties','case','notice','stage','responsibility','strategy'}]
        status='blocked' if blockers else 'incomplete' if essential else 'review_required' if reviews else 'ready'
        answered=len(self.questions)-len({x['question_id'] for x in missing}); completion=max(0,min(100,round(100*answered/len(self.questions))))
        professionals=['legal']
        if coercive in {'payment_order','exceptions_pending','embargo'} or process!='none': professionals.append('administrative_litigation')
        if 'ANX-TR2-SAST-001' in docs: professionals.append('technical_sast')
        return {'version':self.VERSION,'status':status,'blocked':bool(blockers),'findings':findings,'blockers':blockers,'reviews':reviews,'missing_fields':missing,'documents':docs,'blocks':blocks,'professional_reviews':sorted(set(professionals)),'completion':{'answered':answered,'total':len(self.questions),'percent':completion},'explanations':['El comparendo es una orden de comparecencia y no equivale por sí solo a una sanción en firme.','La falta de notificación puede afectar oportunidades de defensa, pero sus consecuencias dependen de la etapa, el expediente y la afectación concreta.','La responsabilidad del propietario requiere diferenciar deberes propios, conducta del conductor, imputación personal y culpabilidad.','La revocatoria directa no sustituye recursos ni revive automáticamente términos judiciales.']}
