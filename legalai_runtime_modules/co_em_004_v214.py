from __future__ import annotations
import json
from pathlib import Path


class CoEm004MaturityV214:
    """Centro de maduración de solo lectura para CO-EM-004 v2.14."""

    def __init__(self, root: Path, products, interviews, rules, sources, scenarios):
        self.root = Path(root)
        self.products = products
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.scenarios = scenarios
        self.spec = json.loads((self.root / 'data' / 'co_em_004_v214.json').read_text(encoding='utf-8'))

    def product(self):
        return next((p for p in self.products if p.get('code') == 'CO-EM-004'), None)

    def expected_documents(self, answers=None, blocked=False):
        answers = answers or {}
        if blocked:
            return [
                {'kind': 'traceability', 'title': 'Ficha de diagnóstico y trazabilidad', 'reason': 'Siempre disponible'},
                {'kind': 'escalation', 'title': 'Informe de bloqueo y escalamiento profesional', 'reason': 'Caso bloqueado'},
            ]
        docs = [
            {'kind': 'nda', 'title': 'Acuerdo de confidencialidad', 'reason': 'Documento principal'},
            {'kind': 'information_inventory', 'title': 'Inventario de información y matriz de acceso', 'reason': 'Control mínimo de categorías y accesos'},
        ]
        if answers.get('relationship_context') in ('Comercial/proveedor', 'Laboral/colaborador', 'Software/tecnología', 'Contenidos/creativo'):
            docs.append({'kind': 'relationship_annex', 'title': 'Anexo de confidencialidad según la relación', 'reason': 'Relación especializada confirmada'})
        if answers.get('preexisting_materials') in ('Sí', 'No sé') or answers.get('oss_components') in ('Sí', 'No sé') or answers.get('relationship_context') in ('Software/tecnología', 'Contenidos/creativo'):
            docs.append({'kind': 'ip_annex', 'title': 'Anexo de propiedad intelectual, antecedentes y OSS', 'reason': 'Propiedad intelectual o componentes de terceros relevantes'})
        if answers.get('personal_data') == 'Sí' or answers.get('crossborder') in ('Sí', 'No sé'):
            docs.append({'kind': 'data_annex', 'title': 'Anexo de datos personales y transferencias', 'reason': 'Tratamiento o transferencia de datos confirmado'})
        if answers.get('incident_protocol') == 'Sí' or answers.get('trade_secrets') in ('Sí', 'No sé'):
            docs.append({'kind': 'incident_protocol', 'title': 'Protocolo de incidentes de información', 'reason': 'Secreto empresarial o protocolo solicitado'})
        docs.append({'kind': 'closure_act', 'title': 'Acta de devolución, eliminación y cierre', 'reason': 'Cierre y evidencia'})
        return docs

    def summary(self):
        product = self.product() or {}
        questions = self.interviews.get('CO-EM-004', {}).get('questions', [])
        rules = self.rules.get('CO-EM-004', [])
        full_answers = {
            'relationship_context': 'Software/tecnología', 'preexisting_materials': 'Sí', 'oss_components': 'Sí',
            'personal_data': 'Sí', 'crossborder': 'Sí', 'incident_protocol': 'Sí', 'trade_secrets': 'Sí',
        }
        return {
            **self.spec,
            'product': product,
            'questions': questions,
            'rules': rules,
            'sources': self.sources.get('CO-EM-004', []),
            'scenarios': self.scenarios.get('CO-EM-004', []),
            'standard_documents': self.expected_documents({'relationship_context': 'Otra'}),
            'full_documents': self.expected_documents(full_answers),
            'blocked_documents': self.expected_documents({}, blocked=True),
            'counts': {
                'global_products': len(self.products),
                'global_questions': sum(len(v.get('questions', [])) for v in self.interviews.values()),
                'global_rules': sum(len(v) for v in self.rules.values()),
                'global_sources': sum(len(v) for v in self.sources.values()),
                'global_scenarios': sum(len(v) for v in self.scenarios.values()),
                'product_questions': len(questions),
                'product_rules': len(rules),
                'product_sources': len(self.sources.get('CO-EM-004', [])),
                'product_scenarios': len(self.scenarios.get('CO-EM-004', [])),
            },
        }
