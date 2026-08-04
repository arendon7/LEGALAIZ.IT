from __future__ import annotations
import json
from pathlib import Path

class CoLa002CanonicalV236:
    def __init__(self, root: Path):
        self.root=Path(root)
        self.base=self.root/'app'/'assets'/'advanced-legal-library'/'CO-LA-002'
    def _load(self,name):
        return json.loads((self.base/name).read_text(encoding='utf-8'))
    def summary(self):
        manifest=self._load('MANIFEST_CO-LA-002.json')
        questions=self._load('PREGUNTAS_CANONICAS.json')
        profiles=self._load('PERFILES_CARGO.json')
        documents=self._load('DOCUMENTOS_CANONICOS.json')
        validations=self._load('VALIDACIONES.json')
        trace=self._load('MATRIZ_TRAZABILIDAD.json')
        ids={
            'questions':[x['id'] for x in questions['questions']],
            'profiles':[x['id'] for x in profiles],
            'documents':[x['id'] for x in documents],
        }
        integrity={k:len(v)==len(set(v)) for k,v in ids.items()}
        return {'manifest':manifest,'steps':questions['steps'],'questions':questions['questions'],'profiles':profiles,'documents':documents,'validations':validations,'traceability':trace,'integrity':integrity}
    def evaluate(self, answers: dict):
        """Evaluate canonical answers without mutating the submitted draft.

        The response is intentionally explicit: machine-readable validation IDs are
        preserved for compatibility, while the UI receives severity, explanation,
        missing fields, selected blocks, documents and professional-review gates.
        """
        issues = []
        documents = ['DOC-LA-CONTRACT-001']
        blocks = [
            'LA-TIT-001', 'LA-CON-001', 'LA-OBJ-001', 'LA-DUR-001',
            'LA-INI-001', 'LA-DES-001', 'LA-PRE-001', 'LA-OBE-001',
            'LA-OBT-001', 'LA-SST-001', 'LA-DIG-001', 'LA-CONF-001',
            'LA-DAT-001', 'LA-DUE-DISC-001', 'LA-INT-001', 'LA-NOT-001',
            'LA-DOC-001', 'LA-FIR-001'
        ]
        missing_fields = []
        review_requirements = []
        explanations = []

        def value(path, default=None):
            current = answers
            for part in path.split('.'):
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
            return current

        def missing(path, label, step_id):
            current = value(path)
            if current is None or current == '' or current == []:
                missing_fields.append({'path': path, 'label': label, 'step_id': step_id})
                return True
            return False

        def issue(validation_id, severity, message, explanation, fields=None, review=False):
            item = {
                'id': validation_id,
                'severity': severity,
                'message': message,
                'explanation': explanation,
                'fields': fields or [],
                'requires_professional_review': bool(review),
            }
            issues.append(item)
            if review and validation_id not in review_requirements:
                review_requirements.append(validation_id)

        # Completeness controls for the nine essential decision points.
        missing('employer.type', 'Tipo de empleador', 'STEP-LA-01')
        missing('worker.isAdult', 'Mayoría de edad', 'STEP-LA-02')
        missing('role.jobTitle', 'Cargo', 'STEP-LA-03')
        missing('role.profileId', 'Perfil ocupacional', 'STEP-LA-03')
        missing('work.actualStartDate', 'Fecha real de inicio', 'STEP-LA-04')
        missing('work.modality', 'Modalidad de trabajo', 'STEP-LA-04')
        missing('schedule.type', 'Tipo de jornada', 'STEP-LA-05')
        missing('schedule.weeklyHours', 'Horas semanales', 'STEP-LA-05')
        missing('compensation.baseSalary', 'Salario mensual', 'STEP-LA-06')

        employer_type = value('employer.type')
        if employer_type == 'legal_person':
            blocks.append('LA-CMP-001')
            if not value('employer.legalName') or not value('employer.identificationNumber'):
                issue('V-LA-001', 'blocker', 'Debe completarse la identidad del empleador.',
                      'La comparecencia contractual requiere razón social e identificación verificables.',
                      ['employer.legalName', 'employer.identificationNumber'])
            if not value('employerSignatory.fullName') or not value('employerSignatory.authoritySource'):
                issue('V-LA-011', 'blocker', 'Falta acreditar el firmante del empleador.',
                      'La persona que suscribe debe estar identificada y contar con una fuente verificable de facultad.',
                      ['employerSignatory.fullName', 'employerSignatory.authoritySource'])
        elif employer_type in ('natural_person', 'household'):
            blocks.append('LA-CMP-002')
            if not (value('employer.legalName') or value('employer.naturalPersonFullName')) or not value('employer.identificationNumber'):
                issue('V-LA-001', 'blocker', 'Debe completarse la identidad del empleador.',
                      'La persona natural empleadora debe quedar plenamente identificada.',
                      ['employer.legalName', 'employer.identificationNumber'])

        if value('worker.fullName') in (None, '') or value('worker.identificationNumber') in (None, ''):
            issue('V-LA-002', 'blocker', 'Debe completarse la identidad del trabajador.',
                  'El contrato no puede generarse sin nombre e identificación del trabajador.',
                  ['worker.fullName', 'worker.identificationNumber'])

        if value('worker.isAdult') is False:
            issue('V-LA-003', 'blocker', 'El flujo estándar no cubre contratación de menores.',
                  'La contratación de menores exige autorizaciones y controles especiales fuera de este producto.',
                  ['worker.isAdult'], True)

        blocks.extend(['LA-CAR-001', 'LA-PUR-001'])
        placement = value('role.functionsPlacement')
        if not value('role.jobTitle') or not value('role.profileId'):
            issue('V-LA-004', 'blocker', 'El cargo y el perfil deben estar definidos.',
                  'Las funciones no pueden ensamblarse de forma trazable sin cargo y perfil aprobables.',
                  ['role.jobTitle', 'role.profileId'])
        if placement == 'full_in_contract':
            blocks.append('LA-FUN-001')
        elif placement == 'summary_annex':
            blocks.append('LA-FUN-002'); documents.append('ANX-LA-FUN-001')
        elif placement == 'annex_only':
            blocks.append('LA-FUN-003'); documents.append('ANX-LA-FUN-001')
        elif placement:
            issue('V-LA-012', 'blocker', 'La ubicación de funciones no es válida.',
                  'Debe seleccionarse una de las tres variantes canónicas de funciones.',
                  ['role.functionsPlacement'])

        if value('authorities.hasSpecialAuthorities') is True:
            blocks.append('LA-REP-001')
            if not value('authorities.summary'):
                issue('V-LA-013', 'blocker', 'Las facultades especiales deben delimitarse.',
                      'Toda facultad requiere alcance material, económico y funcional expreso.',
                      ['authorities.summary'], True)

        blocks.append('LA-LUG-002' if value('work.noFixedWorkplace') else 'LA-LUG-001')
        if value('work.livesAtWorkplace') is True:
            blocks.append('LA-RES-001')
            explanations.append({'id': 'EXP-LA-RES-001', 'message': 'Residir en el lugar de trabajo no equivale a disponibilidad permanente.'})

        modality = value('work.modality')
        modality_blocks = {
            'onsite': 'LA-MOD-001', 'telework_hybrid': 'LA-MOD-002',
            'telework_autonomous': 'LA-MOD-003', 'telework_mobile': 'LA-MOD-004',
            'remote_work': 'LA-MOD-005'
        }
        if modality in modality_blocks:
            blocks.append(modality_blocks[modality])
        if modality in ('telework_hybrid', 'telework_autonomous', 'telework_mobile', 'remote_work'):
            documents.append('ANX-LA-MOD-001')
            if not value('remoteWork.authorizedLocation'):
                issue('V-LA-014', 'warning', 'Falta precisar el lugar o alcance remoto autorizado.',
                      'La modalidad no presencial debe delimitar lugar, medios, coordinación y seguridad.',
                      ['remoteWork.authorizedLocation'], True)

        if value('work.probationSelected') is True:
            blocks.append('LA-PRU-001')
            days = value('work.probationDurationDays')
            if not isinstance(days, (int, float)) or days <= 0 or days > 60:
                issue('V-LA-015', 'blocker', 'El período de prueba debe tener una duración válida.',
                      'Para este flujo se admite un valor positivo no superior a sesenta días, sujeto a revisión del caso.',
                      ['work.probationDurationDays'])
            if value('priorRelationship.continuityRisk') is True:
                issue('V-LA-016', 'blocker', 'El período de prueba es incompatible con la continuidad advertida.',
                      'La continuidad material puede impedir pactar un nuevo período de prueba.',
                      ['work.probationSelected', 'priorRelationship.continuityRisk'], True)
        else:
            blocks.append('LA-PRU-002')

        if value('priorRelationship.continuityRisk') is True:
            issue('V-LA-009', 'warning', 'Existe riesgo de continuidad laboral que requiere revisión.',
                  'La fecha real de inicio, antigüedad y período de prueba deben analizarse a partir de la realidad ejecutada.',
                  ['priorRelationship.continuityRisk'], True)

        schedule_type = value('schedule.type')
        schedule_blocks = {'fixed': 'LA-JOR-001', 'flexible': 'LA-JOR-002', 'rotating': 'LA-JOR-003', 'special': 'LA-JOR-004'}
        if schedule_type in schedule_blocks:
            blocks.append(schedule_blocks[schedule_type])
        weekly = value('schedule.weeklyHours')
        max_hours = 42
        if isinstance(weekly, (int, float)) and weekly > max_hours:
            issue('V-LA-007', 'blocker', 'La jornada supera el máximo aplicable.',
                  f'La parametrización vigente del módulo fija un máximo general de {max_hours} horas semanales.',
                  ['schedule.weeklyHours'], True)
        if schedule_type == 'special':
            issue('V-LA-017', 'warning', 'El ciclo especial exige revisión jurídica y de SST.',
                  'No debe publicarse automáticamente sin validar descansos, fatiga, recargos y régimen aplicable.',
                  ['schedule.type'], True)
        if any(value(x) is True for x in ('schedule.includesNightWork', 'schedule.includesSundayWork', 'schedule.overtimePossible')):
            blocks.append('LA-REC-001')

        if value('availability.required') is True:
            blocks.append('LA-DIS-001'); documents.append('ANX-LA-DIS-001')
            if not value('availability.eventsSummary'):
                issue('V-LA-018', 'blocker', 'La disponibilidad debe delimitar eventos y condiciones.',
                      'No se admite una disponibilidad abierta o permanente.', ['availability.eventsSummary'], True)

        salary_type = value('compensation.salaryType')
        salary = value('compensation.baseSalary')
        if salary_type == 'integral':
            blocks.append('LA-SAL-002')
            # The precise threshold remains parameterized; missing a reviewed threshold blocks publication.
            issue('V-LA-006', 'warning', 'El salario integral requiere validación del umbral vigente.',
                  'Antes de aprobar debe resolverse el umbral legal aplicable a la fecha efectiva.',
                  ['compensation.baseSalary'], True)
        else:
            blocks.append('LA-SAL-001')
        if isinstance(salary, (int, float)) and salary <= 0:
            issue('V-LA-005', 'blocker', 'El salario debe ser superior a cero y cumplir el mínimo aplicable.',
                  'El motor definitivo deberá resolver el salario mínimo según fecha, jornada y régimen.',
                  ['compensation.baseSalary'])

        if value('variableCompensation.exists') is True:
            blocks.append('LA-VAR-001')
            documents.append('ANX-LA-VAR-001')
            if not value('variableCompensation.summary'):
                issue('V-LA-019', 'blocker', 'Debe definirse la remuneración variable.',
                      'Se requieren hecho generador, base, fórmula, fuente, período y fecha de pago.',
                      ['variableCompensation.summary'])
        if value('benefits.exists') is True:
            blocks.append('LA-BEN-001')
            if not value('benefits.summary'):
                issue('V-LA-020', 'warning', 'Los beneficios deben describirse y clasificarse.',
                      'La naturaleza salarial depende de su finalidad y realidad, no solo de la denominación.',
                      ['benefits.summary'], True)

        if value('assets.hasItems') is True or value('assets.items'):
            blocks.append('LA-ACT-001'); documents.append('ACT-LA-EQP-001')
            if not (value('assets.summary') or value('assets.items')):
                issue('V-LA-021', 'blocker', 'Debe identificarse cada activo entregado.',
                      'El acta requiere bien, estado, accesorios y reglas de devolución.', ['assets.summary'])

        if value('mobility.required') is True:
            blocks.append('LA-VIA-001')
        owner = value('mobility.vehicleOwnership')
        if owner == 'worker':
            blocks.append('LA-VPR-001'); documents.append('ANX-LA-VPR-001')
            review_requirements.append('R-LA-VPR-001')
        elif owner == 'employer':
            blocks.append('LA-VEH-001')

        if value('specialConditions.criticalRisk') is True:
            documents.append('ANX-LA-RIE-001')
            issue('V-LA-022', 'warning', 'Los riesgos críticos requieren validación SST.',
                  'La firma del anexo no sustituye controles, capacitación, aptitud ni permisos.',
                  ['specialConditions.criticalRisk'], True)
        if value('specialConditions.sensitiveInformation') is True:
            blocks.append('LA-INF-002')
        else:
            blocks.append('LA-INF-001')
        if value('specialConditions.intellectualProperty') is True:
            blocks.extend(['LA-PI-001', 'LA-IA-001', 'LA-IA-002'])
            review_requirements.append('R-LA-PI-001')

        docs = value('documents', {}) or {}
        if docs.get('imageAuthorization') is True:
            documents.append('AUT-LA-IMG-001')
        if docs.get('biometricAuthorization') is True:
            documents.append('AUT-LA-BIO-001'); review_requirements.append('R-LA-DAT-BIO-001')
        if docs.get('geolocationAuthorization') is True:
            documents.append('AUT-LA-GEO-001'); review_requirements.append('R-LA-DAT-GEO-001')

        documents = list(dict.fromkeys(documents))
        blocks = list(dict.fromkeys(blocks))
        review_requirements = list(dict.fromkeys(review_requirements))
        blockers = [x['id'] for x in issues if x['severity'] == 'blocker']
        warnings = [x['id'] for x in issues if x['severity'] == 'warning']
        completion = self.completion(answers)
        readiness = 'blocked' if blockers else ('review_required' if review_requirements or warnings else ('incomplete' if missing_fields else 'ready'))
        return {
            'blocked': bool(blockers),
            'blockers': blockers,
            'warnings': warnings,
            'issues': issues,
            'documents': documents,
            'blocks': blocks,
            'missing_fields': missing_fields,
            'review_requirements': review_requirements,
            'legal_explanations': explanations,
            'completion': completion,
            'readiness': readiness,
            'counts': {
                'issues': len(issues), 'documents': len(documents), 'blocks': len(blocks),
                'missing_fields': len(missing_fields), 'review_requirements': len(review_requirements)
            }
        }

    def completion(self, answers: dict):
        required=[
            ('employer.type', answers.get('employer',{}).get('type')),
            ('worker.isAdult', answers.get('worker',{}).get('isAdult')),
            ('role.jobTitle', answers.get('role',{}).get('jobTitle')),
            ('role.profileId', answers.get('role',{}).get('profileId')),
            ('work.actualStartDate', answers.get('work',{}).get('actualStartDate')),
            ('work.modality', answers.get('work',{}).get('modality')),
            ('schedule.type', answers.get('schedule',{}).get('type')),
            ('schedule.weeklyHours', answers.get('schedule',{}).get('weeklyHours')),
            ('compensation.baseSalary', answers.get('compensation',{}).get('baseSalary')),
        ]
        completed=sum(v is not None and v!='' for _,v in required)
        return {'completed':completed,'total':len(required),'percent':round(completed*100/len(required))}

