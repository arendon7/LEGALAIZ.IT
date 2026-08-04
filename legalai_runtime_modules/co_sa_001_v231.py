from __future__ import annotations
import json
from pathlib import Path

class CoSa001MaturityV231:
    """Resumen verificable de la maduración integral de CO-SA-001."""
    def __init__(self, root: Path, products, interviews, rules, sources, scenarios, parameters):
        self.root=Path(root); self.products=products; self.interviews=interviews; self.rules=rules; self.sources=sources; self.scenarios=scenarios; self.parameters=parameters
        self.spec=json.loads((self.root/'data'/'co_sa_001_v231.json').read_text(encoding='utf-8'))
    def product(self): return next((p for p in self.products if p.get('code')=='CO-SA-001'),None)
    def expected_documents(self, blocked=False):
        if blocked:
            return [
                {'kind':'traceability','title':'Ficha de diagnóstico y trazabilidad','reason':'Disponible en todo expediente'},
                {'kind':'escalation','title':'Informe de bloqueo y escalamiento','reason':'Se activó un control rojo'},
            ]
        return [{**x,'reason':'Documento especializado integrado v2.31'} for x in self.spec.get('documents',[])]
    def summary(self):
        q=self.interviews.get('CO-SA-001',{}).get('questions',[]); r=self.rules.get('CO-SA-001',[]); s=self.sources.get('CO-SA-001',[]); t=self.scenarios.get('CO-SA-001',[])
        return {**self.spec,'product':self.product() or {},'parameters':self.parameters.get('CO-SA-001',{}),'questions':q,'rules':r,'sources':s,'scenarios':t,'documents':self.expected_documents(False),'blocked_documents':self.expected_documents(True),'counts':{'global_products':len(self.products),'global_questions':sum(len(v.get('questions',[])) for v in self.interviews.values()),'global_rules':sum(len(v) for v in self.rules.values()),'global_sources':sum(len(v) for v in self.sources.values()),'global_scenarios':sum(len(v) for v in self.scenarios.values()),'product_questions':len(q),'product_rules':len(r),'product_sources':len(s),'product_scenarios':len(t),'product_documents':len(self.spec.get('documents',[]))}}
