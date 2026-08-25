from __future__ import annotations

"""Adaptadores de composición jurídica M33.0.

La biblioteca contractual madura conserva el contenido sustantivo versionado. Este
módulo traduce estructuras de entrevista actuales y normaliza la presentación al
estándar M33.0 sin duplicar las reglas jurídicas dentro del renderer.
"""

from copy import deepcopy
import re
from typing import Any

from legalai_platform.contractual_maturity import (
    ORDINALS,
    service_scope_sections,
    services_contract_sections,
)


def _read(data: dict, path: str, default=None):
    current = data
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _first(data: dict, *paths: str, default=None):
    for path in paths:
        value = _read(data, path)
        if value not in (None, '', [], {}):
            return value
    return default


def _party_name(data: dict, prefix: str, fallback: str) -> str:
    identification = _read(data, f'{prefix}.identification', {})
    if isinstance(identification, dict):
        for key in ('name', 'legal_name', 'legalName', 'full_name', 'fullName'):
            if identification.get(key):
                return str(identification[key])
    for key in ('name', 'legal_name', 'legalName', 'full_name', 'fullName'):
        value = _read(data, f'{prefix}.{key}')
        if value:
            return str(value)
    return fallback


def _party_identification(data: dict, prefix: str) -> str:
    identification = _read(data, f'{prefix}.identification', {})
    if isinstance(identification, dict):
        for key in ('identification_number', 'identificationNumber', 'nit', 'id_number', 'idNumber', 'identification'):
            if identification.get(key):
                return str(identification[key])
    return ''


def _party_signatory(data: dict, prefix: str) -> dict[str, str]:
    signatory = _read(data, f'{prefix}.signatory', {})
    if not isinstance(signatory, dict):
        signatory = {'name': str(signatory)} if signatory else {}
    return {
        'name': str(signatory.get('name') or signatory.get('full_name') or signatory.get('fullName') or ''),
        'id': str(signatory.get('identification_number') or signatory.get('identificationNumber') or signatory.get('id_number') or signatory.get('identification') or ''),
        'role': str(signatory.get('capacity') or signatory.get('position') or signatory.get('positionOrCapacity') or ''),
    }


def _deliverable_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get('name') or item.get('title') or item.get('deliverable') or item.get('id') or '')
    return str(item or '')


def services_answers_to_maturity(answers: dict) -> dict[str, Any]:
    """Convierte respuestas modernas/nidadas al contrato maduro sin inventar hechos."""
    data = deepcopy(answers or {})
    client = _party_name(data, 'client', 'EL CONTRATANTE')
    contractor = _party_name(data, 'contractor', 'EL CONTRATISTA')
    deliverables = list(_read(data, 'scope.deliverables', []) or [])
    fees = _first(data, 'fees.financial_terms.amount', 'fees.amount', default=0)
    payment_model = str(_first(data, 'fees.model', default='pagos contra hitos aceptados'))
    payment_term = str(_first(data, 'fees.financial_terms.payment_terms', 'fees.payment_term', default=''))
    payment_scheme = '; '.join(x for x in (payment_model, payment_term) if x)
    no_exclusivity = str(_first(data, 'independence.no_exclusivity', default='')).casefold()
    subcontracting_text = str(_first(data, 'execution.subcontracting', default='')).casefold()
    start_date = _first(data, 'term.start_date', 'schedule.start_date', default='la fecha de firma')
    end_date = _first(data, 'term.end_date', 'schedule.end_date', default='la fecha indicada en la ficha contractual')
    object_text = str(_first(data, 'service.object', default='prestar los servicios definidos en el Anexo No. 1')).strip()
    if object_text.casefold().startswith('prestar '):
        object_text = object_text[8:].strip()

    maturity = {
        'party_a': client,
        'party_b': contractor,
        'object': object_text,
        'contract_city': _first(data, 'dispute.city', 'disputes.city', 'client.identification.domicile', default='Medellín'),
        'start_date': start_date,
        'end_date': end_date,
        'fees': fees,
        'payment_scheme': payment_scheme or 'pagos contra hitos aceptados',
        'acceptance_days': 'cinco (5)',
        'exclusivity': bool(no_exclusivity and no_exclusivity not in {'sí', 'si', 'true', '1', 'yes'}),
        'personal_data': bool(_first(data, 'data.personal', default=False)),
        'intellectual_property': bool(_read(data, 'ip', {})),
        'subcontracting': 'autoriz' in subcontracting_text,
        'deliverable_1': _deliverable_name(deliverables[0]) if len(deliverables) > 0 else 'Informe o resultado principal conforme al alcance',
        'deliverable_2': _deliverable_name(deliverables[1]) if len(deliverables) > 1 else 'Documentación intermedia y matriz de control',
        'deliverable_3': _deliverable_name(deliverables[2]) if len(deliverables) > 2 else 'Cierre, transferencia y evidencia de aceptación',
        'milestone_date': _first(data, 'schedule.milestones', default='Según cronograma aprobado'),
    }
    return maturity


def _normalize_clause_heading(heading: str) -> tuple[str, bool]:
    text = str(heading or '').strip()
    match = re.match(r'^CL[ÁA]USULA\s+(.+?)\.\s*(.+)$', text, flags=re.IGNORECASE)
    if not match:
        return text, False
    ordinal = match.group(1).strip().upper()
    title = match.group(2).strip().upper()
    return f'{ordinal}: {title}', True


def _number_considerations(items: list[str]) -> list[str]:
    paragraphs = []
    for index, item in enumerate(items, 1):
        ordinal = ORDINALS[index - 1] if index <= len(ORDINALS) else str(index)
        paragraphs.append(f'{ordinal}: Que {str(item).strip().removeprefix("Que ").removeprefix("que ")}')
    return paragraphs


def normalize_maturity_sections(sections: list[dict], *, annex_start_index: int | None = None) -> list[dict]:
    """Adapta la biblioteca heredada al modelo de bloques de presentación M33.0."""
    normalized: list[dict] = []
    for index, original in enumerate(sections):
        section = deepcopy(original)
        heading = str(section.get('heading') or '').strip()
        normalized_heading, is_clause = _normalize_clause_heading(heading)
        section['heading'] = normalized_heading

        if is_clause or section.get('clause_number'):
            section['_type'] = 'clause'
            # La biblioteca sustantiva ya contiene prosa jurídica; M33 la trata como
            # párrafo contractual para mantener estructura y comparación modular.
            if section.get('text'):
                section['paragraphs'] = [str(section.pop('text')).strip()]

        if heading.casefold() == 'consideraciones' and section.get('bullets'):
            section['paragraphs'] = _number_considerations(list(section.pop('bullets')))

        if heading.upper().startswith('ANEXO'):
            section['_type'] = 'annex'
            section['page_break_before'] = True
            section['heading_align'] = 'center'

        if annex_start_index is not None and index == annex_start_index:
            section['page_break_before'] = True

        if section.get('_type') == 'signature':
            section['heading'] = 'FIRMAS'
            section['heading_align'] = 'center'

        normalized.append(section)
    return normalized


def compose_services_m33(answers: dict) -> dict[str, Any]:
    """Contrato patrón M33.0: contrato maduro + anexo de alcance integrado."""
    maturity_answers = services_answers_to_maturity(answers)
    principal = normalize_maturity_sections(services_contract_sections(maturity_answers))
    scope = normalize_maturity_sections(service_scope_sections(maturity_answers))

    # El control del contrato principal debe cerrar el paquete, no quedar entre
    # contrato y anexo. Conservamos su contenido y lo movemos al final.
    principal_controls = [item for item in principal if item.get('_type') == 'control']
    principal = [item for item in principal if item.get('_type') != 'control']
    scope_controls = [item for item in scope if item.get('_type') == 'control']
    scope = [item for item in scope if item.get('_type') != 'control']

    if scope:
        scope[0]['_type'] = 'annex'
        scope[0]['page_break_before'] = True
        scope[0]['heading_align'] = 'center'

    client = _party_name(answers, 'client', 'EL CONTRATANTE')
    contractor = _party_name(answers, 'contractor', 'EL CONTRATISTA')
    client_signatory = _party_signatory(answers, 'client')
    contractor_signatory = _party_signatory(answers, 'contractor')
    client_id = _party_identification(answers, 'client')
    contractor_id = _party_identification(answers, 'contractor')

    # Sustituye la firma básica de la biblioteca por una firma estructurada con
    # identificación y calidad cuando la entrevista dispone de esos datos.
    for index, item in enumerate(principal):
        if item.get('_type') != 'signature':
            continue
        principal[index] = {
            'heading': 'FIRMAS',
            '_type': 'signature',
            'parties': [
                {
                    'label': 'EL CONTRATANTE',
                    'name': client_signatory['name'] or client,
                    'role': client_signatory['role'] or ('Representante autorizado' if client_signatory['name'] else ''),
                    'id': client_signatory['id'] or client_id,
                },
                {
                    'label': 'EL CONTRATISTA',
                    'name': contractor_signatory['name'] or contractor,
                    'role': contractor_signatory['role'] or ('Representante autorizado' if contractor_signatory['name'] else ''),
                    'id': contractor_signatory['id'] or contractor_id,
                },
            ],
        }
        break

    controls = principal_controls + scope_controls
    if controls:
        controls[0]['heading'] = 'CONTROL DE USO, FUENTES Y REVISIÓN'
        controls[0]['text'] = (
            'Documento candidato interno M33.0. La composición reutiliza la biblioteca contractual madura y el Anexo No. 1; '
            'su liberación exige validar identidad, capacidad, hechos, cuantías, fechas, variables condicionales, vigencia normativa, '
            'ejecución real, fuentes aplicables y aprobación jurídica y QA sobre la misma revisión y hash.'
        )
        controls = [controls[0]]

    return {
        'title': 'CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES INDEPENDIENTES',
        'subtitle': 'CO-EM-003 · Candidato jurídico M33.0',
        'sections': principal + scope + controls,
        'maturity_answers': maturity_answers,
    }
