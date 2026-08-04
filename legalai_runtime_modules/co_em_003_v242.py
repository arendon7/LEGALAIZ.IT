from __future__ import annotations
import json
from pathlib import Path

class CoEm003CanonicalV242:
    def __init__(self, root: Path):
        self.root=Path(root)
        self.base=self.root/'app'/'assets'/'advanced-legal-library'/'CO-EM-003'
        self.manifest=self._load('MANIFEST_CO-EM-003.json')
        q=self._load('PREGUNTAS_CANONICAS.json'); self.steps=q['steps']; self.questions=q['questions']
        self.profiles=self._load('PERFILES_SERVICIO.json'); self.documents=self._load('DOCUMENTOS_CANONICOS.json')
        self.validations=self._load('VALIDACIONES_CANONICAS.json'); self.blocks=self._load('BLOQUES_CANONICOS.json')
    def _load(self,name): return json.loads((self.base/name).read_text(encoding='utf-8'))
    @staticmethod
    def _get(d,path,default=None):
        for p in path.split('.'):
            if not isinstance(d,dict) or p not in d:return default
            d=d[p]
        return d
    def summary(self):
        return {'manifest':self.manifest,'steps':self.steps,'questions':self.questions,'profiles':self.profiles,'documents':self.documents,'validations':self.validations,'blocks':self.blocks}
    def evaluate(self,a):
        findings=[]; missing=[]; selected=['DOC-EM-CONTRACT-001','ANX-EM-SCOPE-001','ACT-EM-CLOSE-001']; blocks=['EM-TIT-001','EM-CMP-001','EM-OBJ-001','EM-SCOPE-001','EM-AUT-001','EM-NOLAB-001','EM-FEES-001','EM-TER-001','EM-INT-001','EM-FIR-001']
        required=['client.type','client.identification','contractor.type','contractor.identification','service.category','service.object','service.expected_result','scope.included','scope.deliverables','fees.model','fees.financial_terms','term','termination','closure','disputes.mechanism']
        for p in required:
            if self._get(a,p) in (None,'',[],{}): missing.append({'path':p,'severity':'required'})
        indicators=['fixed_schedule','continuous_orders','org_integration','exclusivity_or_availability','personal_continuous_periodic']
        score=sum(2 for k in indicators if self._get(a,'labor_indicators.'+k) is True)
        if self._get(a,'autonomy.methods') is False: score+=2
        if self._get(a,'autonomy.delegation') is False: score+=1
        if score>=8: findings.append({'id':'V-EM-003','severity':'blocker','message':'Riesgo alto de contrato realidad. La configuración debe rediseñarse o manejarse laboralmente.'})
        elif score>=4: findings.append({'id':'V-EM-004','severity':'review','message':'Riesgo material de subordinación; se requiere revisión jurídica antes de generar.'})
        if self._get(a,'service.regulated') is True: findings.append({'id':'V-EM-002','severity':'review','message':'Verificar habilitación, matrícula o permiso aplicable.'})
        if self._get(a,'confidentiality.required') is True: selected.append('ANX-EM-CONF-001'); blocks.append('EM-CONF-001')
        if self._get(a,'data_processing.required') is True: selected.append('ANX-EM-DATA-001'); blocks.append('EM-DATA-001')
        if self._get(a,'ip.required') is True: selected.append('ANX-EM-IP-001'); blocks.append('EM-IP-001')
        if self._get(a,'ai.required') is True: selected.append('ANX-EM-AI-001'); blocks.append('EM-AI-001'); findings.append({'id':'V-EM-010','severity':'review','message':'El uso de IA requiere controles de información, licencias y revisión humana.'})
        if self._get(a,'fees.model') in ('milestone','success','mixed'): selected.append('ANX-EM-FEES-001')
        if self._get(a,'scope.deliverables') not in (None,'',[],{}): selected.append('ACT-EM-ACCEPT-001'); blocks+=['EM-DEL-001','EM-ACC-001','EM-CHG-001']
        if self._get(a,'confirmation.public_contracting') is True: findings.append({'id':'V-EM-001','severity':'blocker','message':'Este producto no cubre contratación estatal.'})
        blocked=any(x['severity']=='blocker' for x in findings)
        return {'version':'2.42','blocked':blocked,'labor_risk_score':score,'risk_level':'high' if score>=8 else 'medium' if score>=4 else 'low','findings':findings,'missing_fields':missing,'documents':list(dict.fromkeys(selected)),'blocks':list(dict.fromkeys(blocks)),'ready':not blocked and not missing}
