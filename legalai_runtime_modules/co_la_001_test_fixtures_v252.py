from copy import deepcopy


def complete_answers():
    return {
        'scope': {'private_relation': 'yes'},
        'worker': {'identity': {'name': 'María Fernanda López Gómez', 'id_number': '1.234.567.890', 'email': 'maria@example.com', 'address': 'Medellín, Antioquia'}},
        'employer': {
            'identity': {'name': 'Servicios Integrales Andinos S.A.S.', 'id_number': '900.123.456-7', 'email': 'nomina@example.com', 'address': 'Medellín, Antioquia'},
            'signatory': {'name': 'Carlos Pérez', 'capacity': 'representante legal', 'authority_source': 'certificado de existencia y representación legal'},
        },
        'claim': {'cutoff_date': '2026-07-24'},
        'claimant': {'role': 'advisor'},
        'relationship': {
            'start_date': '2022-02-01', 'end_date': '2026-06-30', 'contract_type': 'indefinite',
            'termination_type': 'without_cause',
            'special_term': {'fixed_end_date': '', 'work_remaining_days': '', 'cause_document': 'carta de terminación'},
            'service_status': 'ended',
        },
        'compensation': {
            'base_salary': 3_500_000, 'salary_type': 'ordinary',
            'variable': {'exists': True, 'monthly_average': 500_000, 'supports': 'complete', 'components': 'comisiones mensuales'},
            'transport_aid': 'no',
            'other_salary': {'overtime': 100_000, 'surcharges': 80_000, 'in_kind': 0, 'description': 'promedios soportados'},
        },
        'periods': {
            'salary_due_days': 15, 'cesantias_start_date': '2026-01-01', 'prima_start_date': '2026-01-01',
            'vacation_pending_days': 12, 'vacation_basis': 'last_salary', 'confirmation': 'complete',
        },
        'payments': {
            'prior': {'salary': 0, 'cesantias': 0, 'interests': 0, 'prima': 0, 'vacation': 0, 'indemnity': 1_000_000},
            'deductions': {'exists': True, 'amount': 250_000, 'reason': 'préstamo alegado', 'authorization': 'no aportada', 'support': 'parcial'},
        },
        'evidence': {
            'support_level': 'complete',
            'items': {'contract': 'complete', 'payroll': 'complete', 'bank': 'complete', 'cesantias': 'complete', 'termination_letter': 'complete'},
            'employer_calculation': 'partial',
        },
        'termination': {
            'without_cause_claim': 'yes', 'cause_support': 'complete', 'indemnity_already_paid': 1_000_000,
            'moratory_claim': 'review', 'delay_days': 20,
            'good_faith_facts': 'El empleador pagó parcialmente, pero no explicó las diferencias.',
        },
        'risk': {'special_protection': 'no', 'protection_details': '', 'public_sector': 'no', 'contract_reality': 'no', 'collective_regime': 'no', 'active_proceeding': 'none'},
        'prescription': {'last_written_claim': '2026-07-01', 'rights_dates': {'earliest': '2026-01-01', 'latest': '2026-06-30'}},
        'settlement': {'generate': True, 'payment_terms': {'installments': 3, 'initial_payment': 2_000_000, 'payment_channel': 'transferencia bancaria'}},
        'data': {'confirmed': True},
        'documents': {'selection': {'claim': True, 'support_request': True, 'prescription_report': True, 'moratory_analysis': True}},
    }


def fixed_term_answers():
    a = deepcopy(complete_answers())
    a['relationship']['contract_type'] = 'fixed'
    a['relationship']['start_date'] = '2026-01-01'
    a['relationship']['end_date'] = '2026-06-30'
    a['relationship']['special_term']['fixed_end_date'] = '2026-12-31'
    return a
