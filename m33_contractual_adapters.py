from __future__ import annotations

"""Adaptadores M33.0 para los tres contratos restantes de la primera oleada.

Este módulo no duplica la biblioteca jurídica. Traduce la estructura de respuestas
actual de las fábricas activas a `legalai_platform.contractual_maturity` y normaliza
la salida al esquema documental M33.0.
"""

from copy import deepcopy
from typing import Any

from legalai_platform.contractual_maturity import (
    employment_contract_sections,
    lease_contract_sections,
    nda_sections,
)
from m33_legal_composition import normalize_maturity_sections


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


def _name_from_identification(data: dict, prefix: str, fallback: str) -> str:
    identification = _read(data, f'{prefix}.identification', {})
    if isinstance(identification, dict):
        for key in ('name', 'legal_name', 'legalName', 'full_name', 'fullName'):
            if identification.get(key):
                return str(identification[key])
    return str(_first(data, f'{prefix}.name', f'{prefix}.legalName', f'{prefix}.fullName', default=fallback))


def _id_from_identification(data: dict, prefix: str) -> str:
    identification = _read(data, f'{prefix}.identification', {})
    if isinstance(identification, dict):
        for key in ('identification_number', 'identificationNumber', 'id_number', 'idNumber', 'nit'):
            if identification.get(key):
                return str(identification[key])
    return str(_first(data, f'{prefix}.identificationNumber', f'{prefix}.id_number', default='') or '')


def _signatory(data: dict, prefix: str) -> dict[str, str]:
    signatory = _read(data, f'{prefix}.signatory', {})
    if not isinstance(signatory, dict):
        signatory = {}
    return {
        'name': str(signatory.get('name') or signatory.get('fullName') or signatory.get('full_name') or ''),
        'id': str(signatory.get('id_number') or signatory.get('identification_number') or signatory.get('identificationNumber') or ''),
        'role': str(signatory.get('capacity') or signatory.get('positionOrCapacity') or signatory.get('role') or ''),
    }


def _replace_signature(sections: list[dict], parties: list[dict[str, str]]) -> list[dict]:
    result = deepcopy(sections)
    for index, section in enumerate(result):
        if section.get('_type') == 'signature':
            result[index] = {
                'heading': 'FIRMAS',
                '_type': 'signature',
                'heading_align': 'center',
                'parties': parties,
            }
            return result
    result.append({'heading': 'FIRMAS', '_type': 'signature', 'heading_align': 'center', 'parties': parties})
    return result


def _move_single_control_to_end(sections: list[dict], *, product_code: str) -> list[dict]:
    body = [section for section in sections if section.get('_type') != 'control']
    controls = [section for section in sections if section.get('_type') == 'control']
    control = deepcopy(controls[0]) if controls else {'heading': 'CONTROL DE USO', '_type': 'control'}
    control['heading'] = 'CONTROL DE USO, FUENTES Y REVISIÓN'
    control['text'] = (
        f'Documento candidato interno {product_code} bajo estándar M33.0. Antes de su liberación deben verificarse identidad y capacidad de las partes, '
        'hechos, fechas, valores, anexos activados, variables, condiciones reales de ejecución, vigencia normativa, fuentes aplicables y coherencia integral. '
        'La aprobación jurídica y el QA deben recaer sobre la misma revisión y el mismo hash; la generación automática no constituye aprobación profesional.'
    )
    return body + [control]


def employment_answers_to_maturity(answers: dict) -> dict[str, Any]:
    employer_name = str(_first(answers, 'employer.legalName', 'employer.naturalPersonFullName', default='EL EMPLEADOR'))
    worker_name = str(_first(answers, 'worker.fullName', default='LA PERSONA TRABAJADORA'))
    functions = list(_read(answers, 'role.essentialFunctions', []) or [])
    maturity: dict[str, Any] = {
        'employer_name': employer_name,
        'employee_name': worker_name,
        'position': _first(answers, 'role.jobTitle', default='cargo definido en el Anexo No. 1'),
        'role_purpose': _first(answers, 'role.purpose', default='cumplir las responsabilidades permanentes del cargo'),
        'city': _first(answers, 'work.mainWorkplace', default='Medellín'),
        'workplace': _first(answers, 'work.mainWorkplace', default='Medellín'),
        'start_date': _first(answers, 'work.actualStartDate', default='la fecha de inicio efectivamente acordada'),
        'contract_type': 'término indefinido',
        'work_mode': _first(answers, 'work.modality', default='presencial'),
        'remote_work': str(_first(answers, 'work.modality', default='')).casefold() in {'remote', 'hybrid', 'remoto', 'híbrido', 'hibrido'},
        'salary': _first(answers, 'compensation.baseSalary', default=0),
        'pay_frequency': _first(answers, 'compensation.payFrequency', default='mensual'),
        'schedule': (
            f"{_first(answers, 'schedule.weeklyHours', default=42)} horas semanales bajo distribución {_first(answers, 'schedule.type', default='acordada')}"
        ),
    }
    for index in range(4):
        if index < len(functions):
            maturity[f'function_{index + 1}'] = str(functions[index])
    return maturity


def compose_employment_m33(answers: dict) -> dict[str, Any]:
    maturity = employment_answers_to_maturity(answers)
    sections = normalize_maturity_sections(employment_contract_sections(maturity))
    employer = maturity['employer_name']
    worker = maturity['employee_name']
    signatory_name = str(_first(answers, 'employerSignatory.fullName', default='') or '')
    signatory_role = str(_first(answers, 'employerSignatory.positionOrCapacity', default='') or '')
    employer_id = str(_first(answers, 'employer.identificationNumber', default='') or '')
    worker_id = str(_first(answers, 'worker.identificationNumber', default='') or '')
    sections = _replace_signature(
        sections,
        [
            {
                'label': 'EL EMPLEADOR',
                'name': signatory_name or employer,
                'role': signatory_role or ('Representante autorizado' if signatory_name else ''),
                'id': employer_id,
            },
            {
                'label': 'LA PERSONA TRABAJADORA',
                'name': worker,
                'role': str(maturity.get('position') or ''),
                'id': worker_id,
            },
        ],
    )
    sections = _move_single_control_to_end(sections, product_code='CO-LA-002')
    return {
        'title': 'CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO',
        'subtitle': 'CO-LA-002 · Candidato jurídico M33.0',
        'sections': sections,
        'maturity_answers': maturity,
    }


def nda_answers_to_maturity(answers: dict) -> dict[str, Any]:
    party_a = _name_from_identification(answers, 'party_a', 'PARTE A')
    party_b = _name_from_identification(answers, 'party_b', 'PARTE B')
    reciprocal = bool(_first(answers, 'agreement.reciprocal', default=False))
    agreement_type = str(_first(answers, 'agreement.type', default='')).casefold()
    bilateral = reciprocal or agreement_type in {'mutual', 'bilateral', 'reciprocal'}
    return {
        'party_a': party_a,
        'party_b': party_b,
        'bilateral': bilateral,
        'purpose': _first(answers, 'agreement.purpose', default='la evaluación y ejecución de la relación identificada'),
        'relationship': _first(answers, 'agreement.reference', default='la relación descrita en la ficha'),
        'confidentiality_term': (
            f"{_first(answers, 'term_remedies.ordinary_confidentiality_years', default=5)} años"
        ),
        'personal_data': bool(_first(answers, 'data.personal', default=False)),
        'ai': bool(_first(answers, 'ai.used', default=False)),
        'start_date': _first(answers, 'agreement.start_date', default='la fecha de firma'),
    }


def compose_nda_m33(answers: dict) -> dict[str, Any]:
    maturity = nda_answers_to_maturity(answers)
    sections = normalize_maturity_sections(nda_sections(maturity, bilateral=bool(maturity['bilateral'])))
    party_a = maturity['party_a']
    party_b = maturity['party_b']
    sign_a = _signatory(answers, 'party_a')
    sign_b = _signatory(answers, 'party_b')
    sections = _replace_signature(
        sections,
        [
            {
                'label': 'LA PRIMERA PARTE',
                'name': sign_a['name'] or party_a,
                'role': sign_a['role'] or ('Representante autorizado' if sign_a['name'] else ''),
                'id': sign_a['id'] or _id_from_identification(answers, 'party_a'),
            },
            {
                'label': 'LA SEGUNDA PARTE',
                'name': sign_b['name'] or party_b,
                'role': sign_b['role'] or ('Representante autorizado' if sign_b['name'] else ''),
                'id': sign_b['id'] or _id_from_identification(answers, 'party_b'),
            },
        ],
    )
    sections = _move_single_control_to_end(sections, product_code='CO-EM-004')
    return {
        'title': 'ACUERDO DE CONFIDENCIALIDAD, SECRETOS EMPRESARIALES, PROPIEDAD INTELECTUAL, DATOS E IA',
        'subtitle': f"CO-EM-004 · {'Bilateral' if maturity['bilateral'] else 'Unilateral'} · Candidato jurídico M33.0",
        'sections': sections,
        'maturity_answers': maturity,
    }


def lease_answers_to_maturity(answers: dict) -> dict[str, Any]:
    landlord = _name_from_identification(answers, 'landlord', 'LA PARTE ARRENDADORA')
    tenant = _name_from_identification(answers, 'tenant', 'LA PARTE ARRENDATARIA')
    address = str(_first(answers, 'property.identification.address', default='el inmueble identificado en la ficha'))
    municipality = str(_first(answers, 'property.identification.municipality', default='Medellín'))
    configuration = str(_first(answers, 'lease.configuration', default='individual')).casefold()
    return {
        'landlord_name': landlord,
        'tenant_name': tenant,
        'party_a': landlord,
        'party_b': tenant,
        'property_address': address,
        'city': municipality,
        'rent': _first(answers, 'rent.amount', default=0),
        'start_date': _first(answers, 'delivery.date', default='la fecha de entrega'),
        'term_months': _first(answers, 'term.duration_months', default=12),
        'horizontal_property': bool(_first(answers, 'property.horizontal', default=False)),
        'pets': bool(_first(answers, 'pets.exists', default=False)),
        'lease_type': 'con pluralidad de arrendatarios' if configuration == 'joint' else 'individual',
    }


def compose_lease_m33(answers: dict) -> dict[str, Any]:
    maturity = lease_answers_to_maturity(answers)
    sections = normalize_maturity_sections(lease_contract_sections(maturity))
    landlord = maturity['landlord_name']
    tenant = maturity['tenant_name']
    signatory = _signatory(answers, 'landlord')
    sections = _replace_signature(
        sections,
        [
            {
                'label': 'LA PARTE ARRENDADORA',
                'name': signatory['name'] or landlord,
                'role': signatory['role'] or ('Representante autorizado' if signatory['name'] else ''),
                'id': signatory['id'] or _id_from_identification(answers, 'landlord'),
            },
            {
                'label': 'LA PARTE ARRENDATARIA',
                'name': tenant,
                'id': _id_from_identification(answers, 'tenant'),
            },
        ],
    )
    sections = _move_single_control_to_end(sections, product_code='CO-AR-001')
    return {
        'title': 'CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA',
        'subtitle': 'CO-AR-001 · Candidato jurídico M33.0',
        'sections': sections,
        'maturity_answers': maturity,
    }
