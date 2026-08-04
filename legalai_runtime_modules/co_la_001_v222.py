from __future__ import annotations

import json
from pathlib import Path


class CoLa001MaturityV222:
    """Resumen verificable de la maduración integral de CO-LA-001."""

    def __init__(self, root: Path, products, interviews, rules, sources, scenarios, parameters):
        self.root = Path(root)
        self.products = products
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.scenarios = scenarios
        self.parameters = parameters
        self.spec = json.loads((self.root / 'data' / 'co_la_001_v222.json').read_text(encoding='utf-8'))

    def product(self):
        return next((p for p in self.products if p.get('code') == 'CO-LA-001'), None)

    def expected_documents(self, answers=None, blocked=False):
        answers = answers or {}
        if blocked:
            return [
                {'kind':'traceability','title':'Ficha de diagnóstico y trazabilidad','reason':'Disponible en todo expediente'},
                {'kind':'escalation','title':'Informe de bloqueo y escalamiento','reason':'Se activó un control rojo'},
            ]
        docs = [
            {'kind':'calculation','title':'Informe técnico de liquidación laboral por concepto','reason':'Documento económico principal'},
            {'kind':'claim','title':'Reclamación directa de acreencias laborales','reason':'Salida de reclamación extrajudicial'},
            {'kind':'evidence_matrix','title':'Matriz de soportes y conciliación de pagos','reason':'Cotejo probatorio y de pagos'},
        ]
        if answers.get('generate_settlement') == 'Sí':
            docs.append({'kind':'settlement','title':'Propuesta de acuerdo de pago y cierre','reason':'Módulo condicional solicitado'})
        return docs

    def summary(self):
        product = self.product() or {}
        questions = self.interviews.get('CO-LA-001', {}).get('questions', [])
        rules = self.rules.get('CO-LA-001', [])
        sources = self.sources.get('CO-LA-001', [])
        scenarios = self.scenarios.get('CO-LA-001', [])
        return {
            **self.spec,
            'product': product,
            'parameters': self.parameters.get('CO-LA-001', {}),
            'questions': questions,
            'rules': rules,
            'sources': sources,
            'scenarios': scenarios,
            'standard_documents': self.expected_documents({'generate_settlement':'No'}),
            'full_documents': self.expected_documents({'generate_settlement':'Sí'}),
            'blocked_documents': self.expected_documents({}, blocked=True),
            'counts': {
                'global_products': len(self.products),
                'global_questions': sum(len(v.get('questions', [])) for v in self.interviews.values()),
                'global_rules': sum(len(v) for v in self.rules.values()),
                'global_sources': sum(len(v) for v in self.sources.values()),
                'global_scenarios': sum(len(v) for v in self.scenarios.values()),
                'product_questions': len(questions),
                'product_rules': len(rules),
                'product_sources': len(sources),
                'product_scenarios': len(scenarios),
                'product_documents': len(self.spec.get('documents', [])),
            },
        }
