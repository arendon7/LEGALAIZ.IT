from __future__ import annotations
import json
from pathlib import Path

class PublicPortal:
    def __init__(self, root: Path, products, interviews, rules, sources, templates):
        self.root = Path(root)
        self.products = products
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.templates = templates
        self.content = json.loads((self.root / 'data' / 'public_content.json').read_text(encoding='utf-8'))
        self.product_map = {p['code']: p for p in products}
        self.experience = json.loads((self.root / 'data' / 'product_experience.json').read_text(encoding='utf-8'))
        self.template_map = {}
        for template in templates:
            self.template_map.setdefault(template.get('product_code'), []).append(template)

    def question(self, code, q):
        x = dict(q)
        x['help'] = self.content.get('question_help', {}).get(f"{code}:{q.get('id')}", {})
        return x

    def product(self, code):
        p = self.product_map.get(code)
        if not p:
            return None
        c = self.content['products'].get(code, {})
        return {
            'code': code,
            'title': c.get('public_title') or p.get('title'),
            'internal_title': p.get('title'),
            'vertical': p.get('vertical'),
            'icon': p.get('icon'),
            'summary': c.get('short') or p.get('summary'),
            'best_for': c.get('best_for'),
            'duration': c.get('duration'),
            'price_auto': p.get('price_auto'),
            'price_review': p.get('price_review'),
            'documents': c.get('documents', []),
            'review_default': c.get('review_default', 'optional'),
            'review_value': c.get('review_value'),
            'jurisdiction': p.get('jurisdiction', 'Colombia'),
            'outcomes': p.get('outcomes', []),
            'exclusions': p.get('exclusions', []),
            'value_points': c.get('value_points', []),
            'before_you_start': c.get('before_you_start', []),
            'not_included': c.get('not_included', []),
            'client_note': c.get('client_note', ''),
            'document_details': [
                {
                    'template_id': t.get('template_id'),
                    'title': t.get('title'),
                    'kind': t.get('kind'),
                    'format': 'DOCX',
                    'status': 'Estructurada para demostración',
                    'canonical_status': t.get('canonical_status'),
                } for t in self.template_map.get(code, [])
            ],
        }

    def catalog(self):
        return {'brand': self.content.get('brand', {}), 'products': [self.product(p['code']) for p in self.products]}

    def detail(self, code):
        p = self.product(code)
        if not p:
            return None
        spec = self.interviews.get(code, {})
        return {
            'product': p,
            'interview': {
                'intro': 'Responde con la información más precisa que tengas. Cada pregunta incluye una explicación y puedes corregir los datos antes de generar documentos.',
                'sections': spec.get('sections', []),
                'questions': [self.question(code, q) for q in spec.get('questions', [])],
                'question_count': len(spec.get('questions', [])),
            },
            'how_it_works': ['Responde el formulario guiado', 'Revisa tus datos y alertas', 'Confirma los documentos que recibirás', 'Guarda el caso y descarga tus archivos'],
            'rule_count': len(self.rules.get(code, [])),
            'source_count': len(self.sources.get(code, [])),
            'experience': self.experience.get(code, {}),
            'transparency': {
                'document_status': 'Borradores personalizados de demostración',
                'professional_use': False,
                'notice': self.content.get('brand', {}).get('environment_notice', ''),
            },
        }

    def expected_documents(self, code, answers, blocked=False):
        if blocked:
            return ['Ficha de diagnóstico y trazabilidad', 'Informe de bloqueo y escalamiento profesional']
        p = self.product(code) or {}
        if code == 'CO-EM-004':
            docs = ['Acuerdo de confidencialidad', 'Inventario de información y matriz de acceso']
            if answers.get('relationship_context') in ('Comercial/proveedor', 'Laboral/colaborador', 'Software/tecnología', 'Contenidos/creativo'):
                docs.append('Anexo de confidencialidad según la relación')
            if answers.get('preexisting_materials') in ('Sí', 'No sé') or answers.get('oss_components') in ('Sí', 'No sé') or answers.get('relationship_context') in ('Software/tecnología', 'Contenidos/creativo'):
                docs.append('Anexo de propiedad intelectual, antecedentes y OSS')
            if answers.get('personal_data') == 'Sí' or answers.get('crossborder') in ('Sí', 'No sé'):
                docs.append('Anexo de datos personales y transferencias')
            if answers.get('incident_protocol') == 'Sí' or answers.get('trade_secrets') in ('Sí', 'No sé'):
                docs.append('Protocolo de incidentes de información')
            docs.append('Acta de devolución, eliminación y cierre')
            return docs
        if code != 'CO-EM-003':
            return p.get('documents', [])
        docs = [
            'Contrato de prestación de servicios independientes',
            'Anexo No. 1 — Alcance, entregables y cronograma',
        ]
        if answers.get('confidentiality') == 'Sí':
            docs.append('Acuerdo de confidencialidad')
        if answers.get('ip_relevant') == 'Sí':
            docs.append('Anexo de propiedad intelectual')
        if answers.get('personal_data') == 'Sí':
            docs.append('Anexo de tratamiento de datos personales')
        docs.append('Acta de terminación y cierre')
        return docs

    def result(self, raw):
        p = self.product(raw['product']['code'])
        mode = raw.get('service_mode') or ('blocked' if raw.get('risk') == 'red' else 'self_service')
        labels = {
            'self_service': 'Listo para generar',
            'self_service_with_warnings': 'Puedes generar con alertas',
            'blocked': 'Necesita revisión profesional',
        }
        return {
            **raw,
            'product': p,
            'service_mode': mode,
            'service_label': labels[mode],
            'review_required': mode == 'blocked',
            'review_recommended': mode == 'self_service_with_warnings',
            'documents_expected': self.expected_documents(raw['product']['code'], raw.get('answers') or {}, blocked=mode == 'blocked'),
            'client_alerts': [
                {'level': r.get('risk'), 'title': r.get('message'), 'guidance': r.get('action')}
                for r in raw.get('triggered_rules', [])
            ],
        }
