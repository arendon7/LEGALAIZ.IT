from __future__ import annotations
import json
from pathlib import Path


class CoEm003MaturityV213:
    """Read-only product maturity center for CO-EM-003 v2.13."""

    def __init__(self, root: Path, products, interviews, rules, sources, scenarios):
        self.root = Path(root)
        self.products = products
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.scenarios = scenarios
        self.spec = json.loads((self.root / 'data' / 'co_em_003_v213.json').read_text(encoding='utf-8'))

    def product(self):
        return next((p for p in self.products if p.get('code') == 'CO-EM-003'), None)

    def expected_documents(self, answers=None, blocked=False):
        answers = answers or {}
        if blocked:
            return [
                {'kind': 'traceability', 'title': 'Ficha de diagnóstico y trazabilidad', 'reason': 'Siempre disponible'},
                {'kind': 'escalation', 'title': 'Informe de bloqueo y escalamiento profesional', 'reason': 'Caso bloqueado'},
            ]
        docs = [
            {'kind': 'contract', 'title': 'Contrato de prestación de servicios independientes', 'reason': 'Documento principal'},
            {'kind': 'scope', 'title': 'Anexo No. 1 — Alcance, entregables y cronograma', 'reason': 'Siempre aplicable'},
        ]
        if answers.get('confidentiality') == 'Sí':
            docs.append({'kind': 'confidentiality', 'title': 'Acuerdo de confidencialidad', 'reason': 'Información reservada confirmada'})
        if answers.get('ip_relevant') == 'Sí':
            docs.append({'kind': 'intellectual_property', 'title': 'Anexo de propiedad intelectual', 'reason': 'Resultados protegibles confirmados'})
        if answers.get('personal_data') == 'Sí':
            docs.append({'kind': 'data_processing', 'title': 'Anexo de tratamiento de datos personales', 'reason': 'Tratamiento de datos confirmado'})
        docs.append({'kind': 'closure', 'title': 'Acta de terminación y cierre', 'reason': 'Cierre y trazabilidad'})
        return docs

    def summary(self):
        product = self.product() or {}
        questions = self.interviews.get('CO-EM-003', {}).get('questions', [])
        rules = self.rules.get('CO-EM-003', [])
        return {
            **self.spec,
            'product': product,
            'questions': questions,
            'rules': rules,
            'sources': self.sources.get('CO-EM-003', []),
            'scenarios': self.scenarios.get('CO-EM-003', []),
            'standard_documents': self.expected_documents({}),
            'full_documents': self.expected_documents({'confidentiality': 'Sí', 'ip_relevant': 'Sí', 'personal_data': 'Sí'}),
            'counts': {
                'global_products': len(self.products),
                'global_questions': sum(len(v.get('questions', [])) for v in self.interviews.values()),
                'global_rules': sum(len(v) for v in self.rules.values()),
                'product_questions': len(questions),
                'product_rules': len(rules),
                'product_sources': len(self.sources.get('CO-EM-003', [])),
                'product_scenarios': len(self.scenarios.get('CO-EM-003', [])),
            },
        }
