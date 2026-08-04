from __future__ import annotations
from datetime import date

from premium_document_engine import format_cop


def cop(value):
    return format_cop(value)


def base_metadata(case_id, code, product, result, generated_at):
    return [
        ('Caso', case_id),
        ('Producto', f"{code} — {product['title']}"),
        ('Versión jurídica', product.get('version', '—')),
        ('Semáforo', result.get('risk_label', '—')),
        ('Ruta', result.get('route', '—')),
        ('Generado', generated_at),
    ]


def traceability_sections(code, answers, result, product, question_rows):
    sections = [
        {
            'heading': '1. Datos confirmados',
            'table': [('Dato', 'Valor')] + question_rows,
            'text': 'La información se conserva como declaración del usuario y debe contrastarse con los soportes incorporados al expediente.',
        },
        {
            'heading': '2. Diagnóstico jurídico preliminar',
            'text': f"Semáforo: {result.get('risk_label')}. Ruta: {result.get('route')}.",
            'bullets': [
                f"{r.get('id')} — {r.get('message')} Acción: {r.get('action')}"
                for r in result.get('triggered_rules', [])
            ] or ['No se activaron reglas adicionales sobre el riesgo base.'],
        },
        {
            'heading': '3. Control de generación',
            'bullets': [
                'Confirmar identidad, fechas, valores y hechos contra documentos verificables.',
                'Conservar el código del producto y la versión jurídica aplicada.',
                'No utilizar la salida como promesa de resultado ni como sustituto de representación profesional.',
                'Los casos rojos requieren intervención de especialista y no producen documento definitivo automático.',
            ],
        },
        {
            'heading': '4. Fuentes y paquete',
            'table': [('Fuente', 'Estado')] + [
                (s.get('title', 'Fuente'), s.get('status', 'Pendiente'))
                for s in result.get('sources', [])
            ],
            'text': f"Paquete base: {product.get('package')}. Estado de publicación: {product.get('publication_status')}.",
        },
    ]
    return sections


def service_contract_sections(a, result):
    party_a = a.get('party_a') or '[CONTRATANTE]'
    party_b = a.get('party_b') or '[CONTRATISTA]'
    city = a.get('contract_city') or '[CIUDAD]'
    obj = (a.get('object') or '[OBJETO PENDIENTE]').strip().rstrip('.;')
    deliverables = a.get('deliverables') or '[ENTREGABLES PENDIENTES]'
    start = a.get('start_date') or '[FECHA INICIAL]'
    end = a.get('end_date') or '[FECHA FINAL O HITO]'
    fees = cop(a.get('fees'))
    payment = a.get('payment_scheme') or '[ESQUEMA DE PAGO]'
    acceptance = a.get('acceptance_days') or '[PLAZO]'
    sections = [
        {
            'heading': '1. Comparecientes y consideraciones',
            'text': (
                f"Entre {party_a}, identificado(a) con {a.get('party_a_id') or '[IDENTIFICACIÓN]'}, con domicilio o sede en {city}, "
                f"en adelante EL CONTRATANTE, y {party_b}, identificado(a) con {a.get('party_b_id') or '[IDENTIFICACIÓN]'}, "
                'en adelante EL CONTRATISTA, se estructura el presente borrador de contrato de prestación de servicios independientes.\n'
                'Las partes declaran que el vínculo pretende ejecutarse con autonomía técnica, administrativa y operativa. La calificación jurídica depende de la realidad de la ejecución.'
            ),
        },
        {
            'heading': '2. Objeto, alcance y entregables',
            'text': f"EL CONTRATISTA prestará los servicios consistentes en: {obj}.",
            'bullets': [
                f"Entregables informados: {deliverables}",
                'Las actividades adicionales requieren acuerdo escrito sobre alcance, plazo y honorarios.',
                f"EL CONTRATANTE contará con {acceptance} días para formular observaciones concretas a cada entregable.",
            ],
        },
        {
            'heading': '3. Obligaciones esenciales',
            'bullets': [
                'El contratista ejecutará los servicios con diligencia, idoneidad y autonomía, conservará soportes e informará riesgos de retraso.',
                'El contratante suministrará información y accesos, designará un contacto y pagará oportunamente los honorarios.',
                'Ninguna parte implementará horarios, órdenes disciplinarias o controles incompatibles con la autonomía declarada.',
                'El contratista no podrá obligar ni representar al contratante sin autorización expresa.',
            ],
        },
        {
            'heading': '4. Honorarios, pagos y plazo',
            'table': [
                ('Concepto', 'Condición informada'),
                ('Honorarios', fees),
                ('Esquema', payment),
                ('Inicio', start),
                ('Terminación', end),
                ('Ciudad de ejecución', city),
            ],
            'text': 'Los impuestos, retenciones, facturación y gastos extraordinarios deberán aplicarse conforme a la condición real de las partes y a los soportes correspondientes.',
        },
        {
            'heading': '5. Autonomía e inexistencia de subordinación pactada',
            'text': (
                'EL CONTRATISTA organizará sus medios, tiempos y métodos. Podrán acordarse hitos, reuniones razonables, estándares, fechas de reporte y criterios de aceptación, '
                'sin convertirlos en horario laboral obligatorio, órdenes permanentes sobre la forma de trabajo o control disciplinario. '
                'Si la ejecución real contradice esta cláusula, deberá revisarse la naturaleza del vínculo.'
            ),
        },
        {
            'heading': '6. Confidencialidad, datos y propiedad intelectual',
            'bullets': [
                'Confidencialidad: ' + ('módulo requerido' if a.get('confidentiality') == 'Sí' else 'módulo básico o no requerido según confirmación'),
                'Datos personales: ' + ('módulo de tratamiento y seguridad requerido' if a.get('personal_data') == 'Sí' else 'sin tratamiento especial informado'),
                'Propiedad intelectual: ' + ('definir cesión o licencia, usos, territorio, plazo y remuneración' if a.get('ip_relevant') == 'Sí' else 'sin activos relevantes informados'),
                'Subcontratistas: ' + ('requieren autorización y obligaciones equivalentes' if a.get('subcontractors') == 'Sí' else 'no autorizados salvo acuerdo posterior'),
            ],
        },
        {
            'heading': '7. Terminación, cierre y controversias',
            'bullets': [
                'La terminación anticipada debe liquidar entregables ejecutados, anticipos, materiales y obligaciones sobrevivientes.',
                'La parte que alegue incumplimiento deberá describirlo y conceder una oportunidad razonable de subsanación cuando proceda.',
                f"Las notificaciones de coordinación podrán remitirse a {a.get('contact_email_a') or '[CORREO CONTRATANTE]'} y {a.get('contact_email_b') or '[CORREO CONTRATISTA]'}.",
                'La cláusula de solución de controversias debe ser seleccionada y validada antes de firma.',
            ],
        },
        {
            'heading': '8. Control previo a firma',
            'bullets': [
                'Completar identificación, representación, domicilios y datos tributarios.',
                'Convertir los entregables en hitos verificables y anexar cronograma.',
                'Revisar límites de responsabilidad, garantías, seguros y propiedad intelectual.',
                'Confirmar que la operación real no incluya subordinación material.',
                'Obtener aprobación profesional si el semáforo es amarillo o existe cuantía elevada.',
            ],
        },
    ]
    return sections


def service_scope_sections(a):
    return [
        {
            'heading': '1. Objetivo del servicio',
            'text': a.get('object') or '[Definir el objetivo concreto y medible.]',
        },
        {
            'heading': '2. Entregables y criterios de aceptación',
            'text': a.get('deliverables') or '[Describir entregables, formatos, hitos y responsables.]',
            'bullets': [
                f"Plazo para observaciones: {a.get('acceptance_days') or '[—]'} días.",
                'Cada observación debe ser concreta, trazable y relacionada con el alcance aprobado.',
                'Los cambios requieren orden o adición escrita con efectos en plazo y honorarios.',
            ],
        },
        {
            'heading': '3. Cronograma económico',
            'table': [
                ('Campo', 'Valor'),
                ('Inicio', a.get('start_date') or 'Pendiente'),
                ('Fin o hito final', a.get('end_date') or 'Pendiente'),
                ('Honorarios', cop(a.get('fees'))),
                ('Forma de pago', a.get('payment_scheme') or 'Pendiente'),
            ],
        },
        {
            'heading': '4. Dependencias y supuestos',
            'bullets': [
                'Información y accesos que debe suministrar el contratante.',
                'Herramientas, personal y medios que aporta el contratista.',
                'Riesgos de retraso, aprobaciones y terceros involucrados.',
                'Requisitos de seguridad, confidencialidad, datos y propiedad intelectual.',
            ],
        },
    ]



def service_confidentiality_sections(a):
    purpose = a.get('object') or 'la ejecución del servicio descrito en el contrato principal'
    return [
        {
            'heading': '1. Finalidad y relación con el contrato principal',
            'text': (
                f"Este acuerdo complementa el contrato celebrado entre {a.get('party_a') or '[CONTRATANTE]'} y "
                f"{a.get('party_b') or '[CONTRATISTA]'}. La información solo podrá utilizarse para {purpose}."
            ),
        },
        {
            'heading': '2. Información confidencial y exclusiones',
            'bullets': [
                'Comprende información comercial, técnica, financiera, operativa, estratégica, de clientes y cualquier material identificado razonablemente como reservado.',
                'No comprende información pública sin incumplimiento, conocida legítimamente antes de la entrega, recibida de un tercero autorizado o desarrollada de manera independiente y demostrable.',
                'La parte que invoque una exclusión conservará evidencia suficiente de su procedencia.',
            ],
        },
        {
            'heading': '3. Obligaciones de protección y uso',
            'bullets': [
                'Limitar el acceso a las personas que necesiten conocer la información para ejecutar el servicio.',
                'Aplicar medidas razonables de seguridad, custodia, control de accesos y gestión de incidentes.',
                'No copiar, transferir, publicar ni usar la información para fines distintos de la finalidad autorizada.',
                'Responder por terceros autorizados y exigirles obligaciones equivalentes.',
            ],
        },
        {
            'heading': '4. Divulgaciones obligatorias',
            'text': 'Cuando una autoridad competente exija información, la parte receptora limitará la divulgación a lo requerido y avisará previamente cuando la ley y las circunstancias lo permitan.',
        },
        {
            'heading': '5. Devolución, eliminación y duración',
            'bullets': [
                'Al terminar el servicio, devolver o eliminar la información y sus copias, salvo conservación legal o probatoria necesaria.',
                'La confidencialidad subsistirá durante el plazo acordado y, para secretos empresariales, mientras conserven tal carácter y existan medidas razonables de protección.',
                'La terminación del contrato principal no extingue las obligaciones que por su naturaleza deban sobrevivir.',
            ],
        },
        {'_type':'signature','heading':'6. Aceptación','parties':[{'label':'EL CONTRATANTE','name':a.get('party_a') or ''},{'label':'EL CONTRATISTA','name':a.get('party_b') or ''}]},
    ]


def service_ip_sections(a):
    return [
        {
            'heading': '1. Objeto del anexo y resultados',
            'text': f"Este anexo regula los resultados protegibles derivados de: {a.get('object') or '[OBJETO DEL SERVICIO]'}. Los entregables informados son: {a.get('deliverables') or '[ENTREGABLES]'}."
        },
        {
            'heading': '2. Materiales preexistentes',
            'bullets': [
                'Cada parte conserva la titularidad de herramientas, metodologías, bibliotecas, marcas, contenidos y conocimientos desarrollados antes del contrato o fuera de su alcance.',
                'Los materiales preexistentes que deban incorporarse a un entregable se identificarán por escrito y se licenciarán solo en la medida necesaria para usar el resultado.',
                'No se presume transferencia de activos no identificados.',
            ],
        },
        {
            'heading': '3. Resultados creados durante el servicio',
            'text': 'Antes de firma debe elegirse expresamente entre cesión de derechos patrimoniales o licencia de uso. La opción deberá identificar resultados, modalidades de explotación, territorio, plazo, exclusividad y remuneración cuando corresponda.',
        },
        {
            'heading': '4. Derechos morales, créditos y modificaciones',
            'bullets': [
                'Los derechos morales se respetarán conforme al régimen aplicable.',
                'Definir si procede reconocimiento de autoría y cómo se realizarán modificaciones, adaptaciones o integraciones.',
                'La entrega de archivos o soportes no reemplaza por sí sola el instrumento escrito requerido para transferir derechos patrimoniales.',
            ],
        },
        {
            'heading': '5. Garantías y componentes de terceros',
            'bullets': [
                'El contratista informará componentes de terceros, licencias abiertas, restricciones y atribuciones aplicables.',
                'Cada parte responderá por materiales que suministre y conservará soportes de autorización.',
                'Las garantías e indemnidades deben ser proporcionales al control real, la cuantía y el riesgo del servicio.',
            ],
        },
        {'_type':'signature','heading':'6. Aceptación','parties':[{'label':'EL CONTRATANTE','name':a.get('party_a') or ''},{'label':'EL CONTRATISTA','name':a.get('party_b') or ''}]},
    ]


def service_data_sections(a):
    return [
        {
            'heading': '1. Alcance e instrucciones',
            'text': f"EL CONTRATISTA tratará datos personales únicamente para ejecutar {a.get('object') or 'el servicio contratado'}, siguiendo instrucciones documentadas de EL CONTRATANTE y sin destinarlos a fines propios incompatibles."
        },
        {
            'heading': '2. Roles, categorías y finalidades',
            'table': [
                ('Elemento','Definición previa a firma'),
                ('Rol de las partes','Determinar responsable, encargado u otra posición aplicable según la operación real.'),
                ('Titulares y datos','Identificar categorías de titulares, datos y posibles datos sensibles.'),
                ('Finalidad','Relacionar cada tratamiento con un entregable o actividad autorizada.'),
                ('Sistemas y ubicación','Identificar aplicaciones, repositorios, proveedores y países involucrados.'),
            ],
        },
        {
            'heading': '3. Seguridad y confidencialidad',
            'bullets': [
                'Aplicar control de accesos, autenticación, respaldo, registro, actualización y protección proporcional al riesgo.',
                'Autorizar acceso solo a personal necesario y vinculado por confidencialidad.',
                'No descargar, transferir o alojar datos en servicios no autorizados.',
                'Conservar evidencia de medidas, accesos y devoluciones relevantes.',
            ],
        },
        {
            'heading': '4. Incidentes y atención de titulares',
            'bullets': [
                'Notificar sin demora indebida cualquier incidente, pérdida, acceso no autorizado o vulnerabilidad relevante.',
                'Preservar evidencia, contener el incidente y colaborar con las obligaciones legales y contractuales.',
                'Apoyar consultas, reclamos, actualizaciones, supresiones y demás solicitudes de titulares según las instrucciones recibidas.',
            ],
        },
        {
            'heading': '5. Subencargados, transferencias y cierre',
            'bullets': [
                'No incorporar terceros que traten datos sin autorización y obligaciones equivalentes.',
                'Revisar transferencias o transmisiones internacionales antes de realizarlas.',
                'Al terminar, devolver o eliminar los datos y certificar el cierre, salvo conservación legal justificada.',
            ],
        },
        {'_type':'signature','heading':'6. Aceptación','parties':[{'label':'EL CONTRATANTE','name':a.get('party_a') or ''},{'label':'EL CONTRATISTA','name':a.get('party_b') or ''}]},
    ]


def service_closure_sections(a):
    return [
        {
            'heading': '1. Identificación del cierre',
            'table': [
                ('Campo','Información'),
                ('Contrato','Prestación de servicios independientes'),
                ('Contratante',a.get('party_a') or 'Pendiente de confirmación'),
                ('Contratista',a.get('party_b') or 'Pendiente de confirmación'),
                ('Fecha prevista de cierre',a.get('end_date') or 'Pendiente de confirmación'),
            ],
        },
        {
            'heading': '2. Entregables y aceptación',
            'text': a.get('deliverables') or 'Relacionar los entregables recibidos, pendientes, observaciones y fecha de aceptación.',
            'bullets': [
                f"Plazo pactado para observaciones: {a.get('acceptance_days') or 'Pendiente'} días.",
                'Registrar entregas parciales, correcciones y aceptación sin sustituir la evidencia del expediente.',
                'Dejar constancia de elementos pendientes y responsable de cierre.',
            ],
        },
        {
            'heading': '3. Estado económico',
            'table': [
                ('Concepto','Estado'),
                ('Honorarios pactados',cop(a.get('fees'))),
                ('Esquema de pago',a.get('payment_scheme') or 'Pendiente'),
                ('Pagos realizados','Completar con soportes'),
                ('Saldo o devolución','Completar después de conciliación'),
            ],
        },
        {
            'heading': '4. Devoluciones y obligaciones sobrevivientes',
            'bullets': [
                'Devolver accesos, equipos, documentos y materiales de la otra parte.',
                'Confirmar devolución o eliminación de información confidencial y datos personales cuando corresponda.',
                'Identificar licencias, cesiones, garantías, soporte y obligaciones que continúan después del cierre.',
                'Conservar los soportes de pago, entrega, aceptación y comunicaciones relevantes.',
            ],
        },
        {
            'heading': '5. Alcance de la constancia',
            'text': 'La firma del acta acredita los aspectos expresamente registrados. No implica renuncia general a derechos, reclamaciones desconocidas o obligaciones que deban sobrevivir por ley o por acuerdo válido.',
        },
        {'_type':'signature','heading':'6. Firmas de cierre','parties':[{'label':'EL CONTRATANTE','name':a.get('party_a') or ''},{'label':'EL CONTRATISTA','name':a.get('party_b') or ''}]},
    ]

def _labor_value(calc, key):
    for item in (calc or {}).get('line_items', []):
        if item.get('key') == key:
            return item
    return {'gross': 0, 'prior_paid': 0, 'net': 0, 'formula': 'No disponible', 'source_ids': []}


def labor_report_sections(a, calc, result):
    if not calc:
        return [{'heading': '1. Resultado no calculable', 'text': 'No fue posible producir un cálculo porque las fechas, los períodos o el salario no están completos o no son válidos.'}]
    period = calc.get('periods', {})
    concept_rows = [('Concepto', 'Bruto · pago previo · saldo')]
    for item in calc.get('line_items', []):
        concept_rows.append((
            item.get('label'),
            f"{cop(item.get('gross'))} · {cop(item.get('prior_paid'))} · {cop(item.get('net'))}"
        ))
    formula_bullets = [
        f"{item.get('label')}: {item.get('formula')}. Fuentes: {', '.join(item.get('source_ids') or [])}."
        for item in calc.get('line_items', [])
    ]
    interest_rows = [('Año/segmento', 'Días · cesantías base · intereses')]
    for segment in calc.get('interest_segments', []):
        interest_rows.append((
            f"{segment.get('start')} a {segment.get('end')}",
            f"{segment.get('days')} días · {cop(segment.get('cesantias_base'))} · {cop(segment.get('interest'))}"
        ))
    return [
        {
            'heading': '1. Objeto, alcance y naturaleza del informe',
            'text': (
                'Este informe reconstruye por separado salarios pendientes, cesantías, intereses a las cesantías, prima de servicios, '
                'vacaciones compensables e indemnización estándar por terminación. Cada concepto tiene período, fórmula, pago previo y saldo '
                'propios. El resultado es una estimación técnica basada en los datos confirmados; no decide controversias probatorias ni incorpora '
                'sanciones de forma automática.'
            ),
        },
        {
            'heading': '2. Identificación del vínculo y del corte',
            'table': [
                ('Campo', 'Información confirmada'),
                ('Trabajador', a.get('worker_name') or 'No informado'),
                ('Identificación', a.get('worker_id') or 'No informada'),
                ('Empleador', a.get('employer_name') or 'No informado'),
                ('Identificación empleador', a.get('employer_id') or 'No informada'),
                ('Ingreso', a.get('start_date') or 'No informado'),
                ('Terminación o corte', a.get('end_date') or 'No informado'),
                ('Modalidad', a.get('contract_type') or 'No informada'),
                ('Causa informada', a.get('termination') or 'No informada'),
                ('Duración 30/360', str(period.get('employment', {}).get('days_30_360', 0)) + ' días'),
            ],
        },
        {
            'heading': '3. Salario y bases de liquidación',
            'table': [
                ('Parámetro', 'Valor aplicado'),
                ('Salario fijo mensual', cop(calc.get('fixed_salary'))),
                ('Promedio variable mensual', cop(calc.get('variable_average'))),
                ('Ingreso salarial usado', cop(calc.get('salary'))),
                ('Auxilio de transporte aplicado', 'Sí · ' + cop(calc.get('transport_aid_value')) if calc.get('transport_aid_applied') else 'No'),
                ('Base prestacional', cop(calc.get('base_prestacional'))),
                ('Versión de parámetros', calc.get('parameter_version') or 'No disponible'),
                ('Fecha de verificación', calc.get('verified_at') or 'No disponible'),
            ],
            'text': 'El auxilio de transporte, cuando procede, integra la base de cesantías y prima, pero no la base de vacaciones ni de indemnización. Los pagos variables solo se incorporan cuando existe promedio informado y soporte suficiente.',
        },
        {
            'heading': '4. Períodos individualizados por concepto',
            'table': [
                ('Concepto', 'Período o cantidad aplicada'),
                ('Salario ordinario', f"{calc.get('salary_due_days', 0)} días pendientes"),
                ('Cesantías', f"{period.get('cesantias', {}).get('start')} a {period.get('cesantias', {}).get('end')} · {period.get('cesantias', {}).get('days_30_360', 0)} días"),
                ('Prima de servicios', f"{period.get('prima', {}).get('start')} a {period.get('prima', {}).get('end')} · {period.get('prima', {}).get('days_30_360', 0)} días"),
                ('Vacaciones', f"{period.get('vacaciones', {}).get('pending_days', 0)} días pendientes; techo causado estimado: {period.get('vacaciones', {}).get('accrued_ceiling_days', 0)} días"),
                ('Indemnización', f"{calc.get('indemnizacion_dias', 0)} días según modalidad y causa informadas"),
            ],
            'text': 'La separación de cortes evita liquidar nuevamente períodos ya pagados o consignados. Las fechas deben conciliarse con nómina, fondo de cesantías, desprendibles, vacaciones y comunicaciones de terminación.',
        },
        {
            'heading': '5. Resultado económico por concepto',
            'table': concept_rows,
            'text': (
                f"Subtotal bruto: {cop(calc.get('subtotal_matematico'))}. "
                f"Pagos previos confirmados: {cop(calc.get('pagos_previos_confirmados'))}. "
                f"Saldo matemático estimado: {cop(calc.get('total_estimado'))}."
            ),
        },
        {
            'heading': '6. Fórmulas, fuentes y trazabilidad',
            'bullets': formula_bullets,
            'text': 'Las fórmulas se ejecutan con convención laboral 30/360 para prestaciones. La indemnización se determina según modalidad, salario, duración y causa informada. Cada línea conserva sus fuentes jurídicas identificadas.',
        },
        {
            'heading': '7. Desglose anual de intereses a las cesantías',
            'table': interest_rows if len(interest_rows) > 1 else [('Segmento', 'No se calculó un período pendiente')],
            'text': 'El cálculo segmenta los intereses por año para evitar aplicar el porcentaje anual sobre un acumulado plurianual como si correspondiera a un único período.',
        },
        {
            'heading': '8. Pagos previos y conciliación',
            'bullets': [
                f"{item.get('label')}: bruto {cop(item.get('gross'))}; pago previo {cop(item.get('prior_paid'))}; saldo {cop(item.get('net'))}."
                for item in calc.get('line_items', [])
            ],
            'text': 'Un pago previo superior al valor bruto no genera saldo negativo ni se traslada automáticamente a otro concepto. Esa diferencia debe conciliarse con su soporte y causa.',
        },
        {
            'heading': '9. Supuestos expresos',
            'bullets': calc.get('assumptions') or ['No se registraron supuestos adicionales distintos de los datos suministrados.'],
        },
        {
            'heading': '10. Partidas excluidas del cálculo automático',
            'bullets': calc.get('exclusions') or [calc.get('warning')],
        },
        {
            'heading': '11. Alertas jurídicas y controles activados',
            'bullets': [
                f"{r.get('id')} — {r.get('message')} Acción: {r.get('action')}"
                for r in result.get('triggered_rules', [])
            ] or ['No se activaron alertas adicionales.'],
        },
        {
            'heading': '12. Conclusión y pasos de cierre',
            'bullets': [
                f"Saldo matemático estimado a conciliar: {cop(calc.get('total_estimado'))}.",
                'Comparar cada línea con contrato, nómina, desprendibles, PILA, consignaciones, vacaciones y comprobantes bancarios.',
                'Corregir las alertas rojas antes de usar el cálculo como base de pago o reclamación definitiva.',
                'Conservar este informe y la evidencia JSON del expediente como soporte de versión y trazabilidad.',
            ],
        },
    ]


def labor_claim_sections(a, calc):
    total = cop(calc.get('total_estimado')) if calc else 'valor pendiente de determinar'
    line_items = (calc or {}).get('line_items', [])
    return [
        {
            'heading': '1. Destinatario, remitente y asunto',
            'text': (
                f"Señores\n{a.get('employer_name') or 'Empleador informado'}\n"
                f"Asunto: reclamación directa y solicitud de liquidación detallada de {a.get('worker_name') or 'trabajador informado'}.\n"
                f"Canal de respuesta: {a.get('claim_email') or 'correo registrado en el expediente'}."
            ),
        },
        {
            'heading': '2. Identificación de la relación',
            'table': [
                ('Dato', 'Información'),
                ('Trabajador', a.get('worker_name') or 'No informado'),
                ('Identificación', a.get('worker_id') or 'No informada'),
                ('Empleador', a.get('employer_name') or 'No informado'),
                ('Ingreso', a.get('start_date') or 'No informado'),
                ('Terminación/corte', a.get('end_date') or 'No informado'),
                ('Contrato', a.get('contract_type') or 'No informado'),
                ('Causa informada', a.get('termination') or 'No informada'),
            ],
        },
        {
            'heading': '3. Hechos relevantes',
            'bullets': [
                f"El vínculo se desarrolló desde {a.get('start_date') or 'la fecha informada'} hasta {a.get('end_date') or 'la fecha de corte informada'}.",
                f"El ingreso salarial mensual usado para la reconstrucción fue {cop((calc or {}).get('salary'))}.",
                f"La causa de terminación o situación al corte fue: {a.get('termination') or 'no informada'}.",
                'Los períodos pendientes se individualizaron por concepto y los pagos previos se descontaron únicamente de la línea correspondiente.',
                'Los valores se presentan para conciliación y están sujetos a los documentos que obren en poder del empleador y del trabajador.',
            ],
        },
        {
            'heading': '4. Resumen de acreencias reclamadas',
            'table': [('Concepto', 'Saldo estimado')] + [(x.get('label'), cop(x.get('net'))) for x in line_items] + [('Total estimado', total)],
            'text': 'Este resumen no incluye sanciones, perjuicios, estabilidad reforzada, horas extra o partidas no acreditadas. Su omisión automática no implica renuncia.',
        },
        {
            'heading': '5. Solicitudes principales',
            'bullets': [
                'Entregar una liquidación discriminada por concepto, período, base, fórmula, pago y saldo.',
                f"Revisar y pagar, cuando proceda, el saldo estimado de {total}, o explicar de manera precisa y documentada cualquier diferencia.",
                'Remitir comprobantes de salarios, primas, cesantías, intereses, vacaciones, aportes, indemnizaciones y deducciones.',
                'Informar si existen consignaciones en fondos, pagos directos, acuerdos, compensaciones o novedades no consideradas en el expediente.',
                'Abstenerse de aplicar descuentos discutidos sin autorización o fundamento legal verificable.',
            ],
        },
        {
            'heading': '6. Solicitud de soportes',
            'bullets': [
                'Contrato, adiciones, prórrogas y comunicaciones de terminación.',
                'Desprendibles de nómina, planillas PILA y comprobantes bancarios.',
                'Certificaciones y extractos del fondo de cesantías.',
                'Registro de vacaciones disfrutadas, compensadas o pendientes.',
                'Soportes del salario variable y metodología de promedio, cuando aplique.',
                'Autorizaciones y documentos de cualquier deducción efectuada.',
            ],
        },
        {
            'heading': '7. Propuesta de conciliación directa',
            'text': 'Se solicita abrir una revisión conjunta de los soportes y conciliar cada línea. Cualquier acuerdo debe identificar los conceptos, valores, fechas y forma de pago, sin renuncias generales ni afectación de derechos ciertos e indiscutibles.',
        },
        {
            'heading': '8. Reserva y alcance',
            'text': 'La presente reclamación se formula con base en la información disponible. La recepción de pagos parciales no extingue conceptos diferentes a los expresamente imputados. Se reservan las actuaciones administrativas, conciliatorias o judiciales que resulten procedentes.',
        },
        {
            'heading': '9. Anexos',
            'bullets': [
                'Documento de identidad.', 'Contrato y adiciones disponibles.', 'Carta de terminación o renuncia.',
                'Desprendibles, extractos y comprobantes de pago.', 'Informe técnico de liquidación laboral.',
                'Matriz de soportes y conciliación del expediente.',
            ],
        },
        {'_type':'signature','heading':'10. Firma','parties':[{'label':'TRABAJADOR / RECLAMANTE','name':a.get('worker_name') or ''},{'label':'RECIBIDO POR EL EMPLEADOR','name':a.get('employer_name') or ''}]},
    ]


def labor_evidence_sections(a, calc, result):
    items=(calc or {}).get('line_items', [])
    return [
        {
            'heading':'1. Propósito de la matriz',
            'text':'Esta matriz organiza los documentos necesarios para validar cada dato, período, pago y diferencia de la liquidación. No presume la inexistencia de soportes que aún no hayan sido aportados.',
        },
        {
            'heading':'2. Inventario mínimo del expediente',
            'table':[
                ('Soporte','Estado informado / finalidad'),
                ('Contrato y adiciones',f"Soporte general: {a.get('salary_supports') or 'No informado'} · modalidad, salario y duración"),
                ('Desprendibles de nómina',f"Soporte general: {a.get('salary_supports') or 'No informado'} · bases y pagos"),
                ('Comprobantes bancarios','Conciliar fechas, beneficiario, valor e imputación'),
                ('PILA','Verificar ingreso base y períodos reportados'),
                ('Fondo de cesantías','Verificar consignaciones y retiros por vigencia'),
                ('Registro de vacaciones','Verificar días causados, disfrutados y compensados'),
                ('Comunicación de terminación','Verificar fecha, causa y modalidad de terminación'),
                ('Soporte de variables',f"{a.get('variable_salary_supports') or 'No aplica'} · promedio informado {cop((calc or {}).get('variable_average'))}"),
                ('Autorización de descuentos',f"Estado de controversia: {a.get('disputed_deductions') or 'No informado'}"),
            ],
        },
        {
            'heading':'3. Conciliación por concepto',
            'table':[('Concepto','Valor calculado · pago previo · soporte a cotejar')] + [
                (x.get('label'),f"{cop(x.get('gross'))} · {cop(x.get('prior_paid'))} · {', '.join(x.get('source_ids') or [])}") for x in items
            ],
        },
        {
            'heading':'4. Hechos que requieren prueba específica',
            'bullets':[
                'Fecha real de ingreso y continuidad del vínculo.', 'Naturaleza salarial de pagos variables o beneficios.',
                'Períodos efectivamente pagados o consignados.', 'Días de vacaciones disfrutados, compensados y pendientes.',
                'Causa y forma de terminación.', 'Autorización y fundamento de deducciones.',
            ],
        },
        {
            'heading':'5. Alertas del expediente',
            'bullets':[f"{r.get('id')} — {r.get('message')}" for r in result.get('triggered_rules', [])] or ['No se registraron alertas adicionales.'],
        },
        {
            'heading':'6. Acta de conciliación documental',
            'table':[
                ('Control','Resultado a diligenciar durante la revisión'),
                ('Documentos recibidos','Registrar nombre, fecha, emisor y hash o ubicación'),
                ('Diferencias identificadas','Relacionar concepto, valor y causa'),
                ('Datos corregidos','Dejar versión anterior y nueva con responsable'),
                ('Pendientes','Asignar responsable y fecha objetivo'),
                ('Cierre','Confirmar si procede regenerar la liquidación'),
            ],
        },
        {'_type':'signature','heading':'7. Validación del cotejo','parties':[{'label':'TRABAJADOR / APODERADO','name':a.get('worker_name') or ''},{'label':'RESPONSABLE DEL COTEJO','name':''}]},
    ]


def labor_settlement_sections(a, calc):
    total=cop((calc or {}).get('total_estimado'))
    return [
        {
            'heading':'1. Partes y antecedentes',
            'text':f"Entre {a.get('employer_name') or 'el empleador informado'} y {a.get('worker_name') or 'el trabajador informado'} se presenta esta propuesta de acuerdo para conciliar exclusivamente los conceptos y valores discriminados en el expediente de liquidación con corte a {a.get('end_date') or 'la fecha informada'}.",
        },
        {
            'heading':'2. Reconocimiento y alcance económico',
            'table':[('Concepto','Saldo propuesto')] + [(x.get('label'),cop(x.get('net'))) for x in (calc or {}).get('line_items', [])] + [('Total propuesto',total)],
            'text':'Los valores deberán verificarse contra los soportes. El acuerdo final debe indicar qué conceptos se reconocen, cuáles se discuten y cómo se imputará cada pago.',
        },
        {
            'heading':'3. Forma de pago propuesta',
            'table':[
                ('Elemento','Condición propuesta'),
                ('Valor total',total),
                ('Número de pagos','Definir en la negociación'),
                ('Fechas de pago','Definir fechas ciertas'),
                ('Medio','Transferencia a cuenta informada por el trabajador'),
                ('Imputación','Cada pago se imputará a los conceptos expresamente discriminados'),
                ('Soporte','Comprobante con fecha, valor, origen y beneficiario'),
            ],
        },
        {
            'heading':'4. Incumplimiento',
            'bullets':[
                'El incumplimiento de una cuota hará exigible el saldo en los términos válidamente acordados.',
                'La mora, intereses o cláusulas de aceleración deben definirse de forma expresa, proporcionada y jurídicamente válida.',
                'Los pagos parciales se imputarán conforme al cuadro económico y no extinguirán conceptos no incluidos.',
            ],
        },
        {
            'heading':'5. Derechos ciertos e indiscutibles y ausencia de renuncia general',
            'text':'Esta propuesta no contiene renuncia general a derechos laborales ni pretende disponer de derechos ciertos e indiscutibles. El efecto liberatorio se limitará a los conceptos, períodos y valores efectivamente conciliados y pagados.',
        },
        {
            'heading':'6. Soportes, aportes y certificaciones',
            'bullets':[
                'El empleador entregará la liquidación final y los comprobantes de pago.',
                'Se conservarán certificados de aportes, retenciones, cesantías y demás soportes aplicables.',
                'Cualquier corrección de nómina o seguridad social se documentará separadamente.',
            ],
        },
        {
            'heading':'7. Solución de diferencias y formalización',
            'text':'Cuando la materia lo exija o las partes busquen efectos conciliatorios, el acuerdo deberá formalizarse ante la autoridad o centro competente. La firma privada de este borrador no sustituye los requisitos legales aplicables.',
        },
        {
            'heading':'8. Integridad y trazabilidad',
            'text':'El documento final deberá identificar el expediente, la versión de cálculo, la fecha de generación y los anexos usados. Toda modificación económica requiere regenerar la evidencia y obtener una nueva aceptación de las partes.',
        },
        {'_type':'signature','heading':'9. Firmas','parties':[{'label':'EL EMPLEADOR','name':a.get('employer_name') or ''},{'label':'EL TRABAJADOR','name':a.get('worker_name') or ''}]},
    ]

def sast_report_sections(a, result):
    matches = result.get('sast_matches', [])
    match_rows = [('Actuación', 'Coincidencia')]
    for m in matches:
        match_rows.append((m.get('id'), f"{m.get('territory')} · {m.get('start')} a {m.get('end')} · Grupo {m.get('group')} · Resolución de apertura {m.get('resolution')}"))
    return [
        {
            'heading': '1. Datos del chequeo',
            'table': [
                ('Campo', 'Información'),
                ('Interesado', a.get('owner_name') or 'Pendiente'),
                ('Identificación', a.get('owner_id') or 'Pendiente'),
                ('Placa', a.get('plate') or 'Pendiente'),
                ('Autoridad/municipio', a.get('territory') or 'Pendiente'),
                ('Fecha del comparendo', a.get('event_date') or 'Pendiente'),
                ('Número', a.get('comparendo_number') or 'No informado'),
                ('Estado procesal', a.get('enforcement') or 'No informado'),
            ],
        },
        {
            'heading': '2. Resultado de coincidencia',
            'table': match_rows if matches else [('Resultado', 'No se encontró coincidencia en la porción piloto incorporada.')],
            'text': (
                'La coincidencia es preliminar y se produce únicamente por autoridad/territorio y fecha. '
                'No individualiza por sí sola el dispositivo, no acredita una decisión firme y no demuestra automáticamente invalidez, archivo o devolución.'
            ),
        },
        {
            'heading': '3. Validaciones indispensables',
            'bullets': [
                'Identificar cámara, dispositivo, ubicación y acto individual.',
                'Solicitar expediente, trazabilidad de validación y notificación.',
                'Verificar resolución sancionatoria, ejecutoria, cobro coactivo, embargo y proceso judicial.',
                'Diferenciar apertura de investigación de decisión administrativa firme.',
                'Aplicar la matriz maestra completa y la versión vigente antes de emitir una conclusión.',
            ],
        },
        {
            'heading': '4. Estado de la base piloto',
            'text': 'La aplicación incorpora diez actuaciones reales del Grupo A como porción demostrativa. La matriz canónica registra 49 actuaciones y debe importarse íntegramente antes del piloto externo.',
        },
    ]


def _traffic_identity(a):
    return [('Campo','Información'),('Peticionario',a.get('petitioner_name') or 'No informado'),('Identificación',a.get('petitioner_id') or 'No informada'),('Calidad',a.get('acting_capacity') or 'No informada'),('Autoridad',a.get('authority') or 'No informada'),('Placa',a.get('plate') or 'No informada'),('Comparendo',a.get('comparendo_number') or 'No informado'),('Hecho',a.get('event_date') or 'No informado'),('Lugar',a.get('event_location') or 'No informado')]

def _traffic_chronology(a,result):
    c=result.get('calculation') or {}
    return [('Hito','Fecha / control'),('Presunta infracción',a.get('event_date') or 'No informada'),('Validación',a.get('validation_date') or 'No informada'),('Envío',a.get('sent_date') or 'No informado'),('Entrega acreditada',a.get('delivery_date') or 'No informada'),('Conocimiento efectivo',a.get('first_knowledge_date') or 'No informado'),('Días hábiles preliminares validación-envío',str(c.get('validation_to_sent_weekdays_preliminary') if c.get('validation_to_sent_weekdays_preliminary') is not None else 'No calculable'))]

def traffic_record_request_sections(a,result):
    ev=a.get('evidence') or []; ev=[ev] if isinstance(ev,str) else ev
    return [
      {'heading':'1. Destinatario, peticionario y actuación','table':_traffic_identity(a),'text':'En ejercicio del derecho de petición solicito acceso completo, legible y ordenado al expediente administrativo asociado a la detección tecnológica identificada.'},
      {'heading':'2. Reconstrucción cronológica','table':_traffic_chronology(a,result),'text':'Las fechas se incorporan como datos declarados. La autoridad debe certificar la secuencia real de detección, validación, envío, entrega, audiencia, decisión y ejecutoria.'},
      {'heading':'3. Solicitud de expediente íntegro','bullets':['Comparendo y orden de comparendo en formato íntegro.','Fotografías, video, metadatos, cadena de custodia y registros de validación.','Identificación del agente que validó, fecha, hora y criterio aplicado.','Actos de trámite y definitivos, constancias de ejecutoria y recursos.','Histórico completo de consultas, anotaciones y novedades en SIMIT y RUNT.']},
      {'heading':'4. Trazabilidad de notificación','bullets':['Dirección y fuente de datos utilizada para cada envío.','Guía postal, planilla, entrega, devolución, causal, aviso o publicación.','Constancia de autorización si se empleó correo electrónico.','Fecha exacta a partir de la cual la autoridad considera surtida la notificación.','Explicación de cualquier diferencia entre dirección RUNT y dirección utilizada.']},
      {'heading':'5. Evidencia técnica del SAST','bullets':['Acto de autorización del punto, código, coordenadas y vigencia.','Identificación inequívoca del equipo asociado a la evidencia.','Certificado de calibración, laboratorio y trazabilidad metrológica aplicable.','Soporte de señalización preventiva para la fecha y lugar.','Manuales, bitácoras o reportes necesarios para interpretar la medición, con las reservas legalmente justificadas.']},
      {'heading':'6. Preservación, formato y entrega','text':'Solicito preservar los archivos nativos y entregar copias electrónicas en formato accesible, con índice, foliación o equivalente digital y explicación de cualquier reserva parcial. La inexistencia de un documento deberá certificarse expresamente.'},
      {'heading':'7. Soportes aportados','bullets':ev or ['Documento de identidad y consultas oficiales que se anexen al momento de radicar.']},
      {'heading':'8. Radicación y notificaciones','text':f"Solicito radicado, respuesta de fondo y notificación en {a.get('email') or 'el correo registrado'} y {a.get('address') or 'la dirección registrada'}."},
    ]

def traffic_notice_claim_sections(a,result):
    return [
      {'heading':'1. Comparecencia y objeto','table':_traffic_identity(a),'text':'Solicito revisar la regularidad y eficacia de la notificación, garantizar acceso al expediente y restablecer una oportunidad material de defensa compatible con la etapa real.'},
      {'heading':'2. Hechos relevantes','bullets':[f"Notificación recibida: {a.get('notice_received') or 'No informado'}.",f"Canal reportado: {a.get('notice_channel') or 'No informado'}.",f"Soporte de entrega o devolución: {a.get('notice_support') or 'No informado'}.",f"Coincidencia de dirección: {a.get('notice_address_match') or 'No informada'}.",f"Primera fecha de conocimiento: {a.get('first_knowledge_date') or 'No informada'}." ]},
      {'heading':'3. Fundamento de debido proceso','text':'La detección y el comparendo dan inicio a una actuación, pero no sustituyen la imputación personal, la oportunidad de contradicción ni una decisión motivada. La consecuencia concreta depende de la trazabilidad del expediente y de la afectación real del derecho de defensa.'},
      {'heading':'4. Solicitudes principales','bullets':['Certificar cómo, cuándo, dónde y a quién se intentó notificar.','Entregar todos los soportes de entrega, devolución, aviso o publicación.','Informar la etapa actual y abstenerse de presentar el comparendo como sanción firme sin el acto y la ejecutoria correspondientes.','Habilitar la actuación defensiva que jurídicamente corresponda si se acredita una afectación material.','Responder de manera expresa cada hecho y solicitud.']},
      {'heading':'5. Imputación personal','text':f"Modelo de análisis configurado: {(result.get('calculation') or {}).get('imputation_model','debe verificarse en el expediente')}. La sola titularidad registral no sustituye la prueba de la conducta ni permite responsabilidad objetiva."},
      {'heading':'6. Reserva de argumentos','text':'Esta reclamación no supone aceptación de la infracción, renuncia a recursos, convalidación de la notificación ni elección anticipada de un medio de control.'},
      {'heading':'7. Notificaciones','text':f"Correo: {a.get('email') or 'registrado en el expediente'}. Dirección: {a.get('address') or 'registrada en el expediente'}."},
    ]

def traffic_hearing_sections(a,result):
    return [
      {'heading':'1. Solicitud de audiencia y contradicción','table':_traffic_identity(a),'text':'Solicito que se informe y habilite la oportunidad procesal vigente para comparecer, conocer la imputación, solicitar pruebas, controvertirlas y presentar explicaciones.'},
      {'heading':'2. Pruebas solicitadas','bullets':['Evidencia original de la detección y sus metadatos.','Declaración o certificación del agente validador.','Autorización del punto y correspondencia con el dispositivo.','Calibración y trazabilidad metrológica aplicables.','Señalización existente para la fecha.','Prueba de identificación del conductor o del incumplimiento culpable del deber atribuido al propietario.']},
      {'heading':'3. Cuestiones a decidir','bullets':['Regularidad de la notificación y oportunidad efectiva de defensa.','Identidad del sujeto imputado y elemento subjetivo exigible.','Confiabilidad, autenticidad e integridad de la evidencia.','Correspondencia entre equipo, autorización, ubicación, fecha y conducta.','Existencia de una decisión motivada y susceptible de contradicción.']},
      {'heading':'4. Petición subsidiaria','text':'Si la autoridad considera que la oportunidad de audiencia concluyó, solicito decisión motivada que identifique el acto, la fecha y forma de notificación, los recursos y la constancia de ejecutoria.'},
      {'heading':'5. Alcance','text':'La solicitud no exige una conclusión anticipada ni presume que toda irregularidad produzca archivo automático. Busca una decisión individual, probada y respetuosa del debido proceso.'},
    ]

def traffic_revocation_sections(a,result):
    return [
      {'heading':'1. Solicitud condicionada','table':_traffic_identity(a),'text':'De manera condicionada a la existencia de un acto administrativo definitivo, solicito evaluar la revocatoria directa únicamente si el expediente demuestra una causal legal y sin desconocer derechos de terceros.'},
      {'heading':'2. Circunstancias que deben verificarse','bullets':['Existencia, contenido y ejecutoria del acto sancionatorio.','Notificación real del comparendo y del acto definitivo.','Oportunidad efectiva de defensa y contradicción.','Imputación personal y culpable.','Integridad de la evidencia y correspondencia técnica del SAST.']},
      {'heading':'3. Límites expresos','bullets':['La revocatoria no se plantea como mecanismo automático.','Su solicitud no revive términos para recursos o control judicial.','No reemplaza excepciones en cobro coactivo ni medidas judiciales urgentes.','No se solicita devolución de pagos sin análisis específico del acto, causa y situación patrimonial.']},
      {'heading':'4. Solicitud de decisión motivada','text':'Solicito pronunciamiento individual sobre cada causal examinada, identificación de pruebas y explicación de las consecuencias sobre SIMIT, RUNT y cualquier actuación de cobro.'},
      {'heading':'5. Reserva','text':'El peticionario conserva las acciones y defensas procedentes y no acepta por este escrito hechos, responsabilidad o ejecutoria que no estén demostrados.'},
    ]

def traffic_registry_sections(a,result):
    return [
      {'heading':'1. Identificación del registro','table':_traffic_identity(a),'text':'Solicito confrontar los sistemas internos, SIMIT y RUNT con el expediente y corregir datos inexactos, desactualizados, duplicados o que no reflejen la decisión administrativa vigente.'},
      {'heading':'2. Datos que deben certificarse','bullets':['Estado actual: comparendo, sanción, acuerdo, pago, cobro o cierre.','Número y fecha del acto que soporta la anotación.','Fecha y canal de reporte a cada sistema.','Identidad del responsable del reporte y del último cambio.','Bloqueos, restricciones o efectos asociados.']},
      {'heading':'3. Corrección condicionada','text':'La actualización se solicita conforme a la realidad jurídica acreditada. No se pide eliminar información válida ni alterar el historial; se pide que cada sistema refleje exactamente la etapa y decisión vigente.'},
      {'heading':'4. Evidencia de cumplimiento','bullets':['Constancia de modificación o ratificación motivada.','Captura o certificado posterior del registro.','Comunicación al operador o entidad que deba replicar el cambio.','Plazo y canal de seguimiento.']},
      {'heading':'5. Notificaciones','text':f"Respuesta al correo {a.get('email') or 'registrado'} y radicado trazable."},
    ]

def traffic_technical_matrix_sections(a,result):
    c=result.get('calculation') or {}
    return [
      {'heading':'1. Identificación técnica','table':[('Control','Dato'),('Punto o dispositivo',a.get('device_id') or 'No informado'),('Ubicación',a.get('event_location') or 'No informada'),('Fecha',a.get('event_date') or 'No informada'),('Conducta',a.get('conduct_category') or 'No informada'),('Resolución técnica vigente',c.get('current_technical_resolution') or 'Verificar')]},
      {'heading':'2. Matriz de control','table':[('Elemento','Estado declarado'),('Autorización SAST',a.get('sast_authorization') or 'No informado'),('Calibración y trazabilidad',a.get('calibration_traceability') or 'No informado'),('Señalización preventiva',a.get('signage_verified') or 'No informada'),('Concepto de desempeño',a.get('performance_concept') or 'No informado'),('Coincidencia anuncio/investigación 2026',a.get('official_2026_match') or 'No informada')]},
      {'heading':'3. Concepto de desempeño: control temporal','text':f"Aplicabilidad histórica calculada: {'Sí' if c.get('concept_performance_relevant') else 'No'}. La exigencia existió únicamente entre el 22 de marzo de 2018 y el 19 de agosto de 2020. Fuera de ese período no se usa su ausencia como causal; permanecen calibración y trazabilidad."},
      {'heading':'4. Verificaciones requeridas','bullets':['Correspondencia entre número de serie, evidencia y certificado.','Vigencia del certificado para la fecha.','Acreditación y alcance del laboratorio.','Acto de autorización y localización exacta.','Evidencia temporal de señalización.','Integridad de archivos, sellos de tiempo y metadatos.']},
      {'heading':'5. Conclusión técnica condicionada','text':'La matriz identifica vacíos probatorios; no reemplaza peritaje, inspección, certificación del laboratorio ni decisión administrativa individual.'},
    ]

def traffic_escalation_guide_sections(a,result):
    return [
      {'heading':'1. Estado del expediente','table':_traffic_chronology(a,result),'text':f"Semáforo: {result.get('risk_label')}. Ruta: {result.get('route')}."},
      {'heading':'2. Secuencia de actuación','bullets':['Radicar solicitud de expediente con anexos y conservar comprobante.','Controlar respuesta y requerir información faltante de forma específica.','Definir la actuación según comparendo, resolución, ejecutoria o cobro.','No mezclar petición, recurso, revocatoria, excepciones y demanda sin identificar su finalidad y término.','Registrar cada decisión y versión documental en el expediente LegalAIZ.it.']},
      {'heading':'3. Términos configurados','bullets':['Envío del comparendo: control preliminar de tres días hábiles posteriores a la validación.','Comparecencia: once días hábiles posteriores a la entrega, sujeto al expediente.','Los conteos del motor omiten festivos y no producen nulidad automática.','Revocatoria directa: no revive términos judiciales.','Cobro coactivo, embargo, proceso judicial o urgencia: revisión inmediata del abogado responsable.']},
      {'heading':'4. Evidencia mínima','bullets':['Documento de identidad y calidad de actuación.','Comparendo y consulta oficial.','Prueba de dirección RUNT para la fecha.','Trazabilidad postal o electrónica.','Actos administrativos y constancias de ejecutoria.','Evidencia técnica del SAST.']},
      {'heading':'5. Resultado esperado','text':'Obtener un expediente completo y una decisión individual motivada. Ningún anuncio general, irregularidad técnica aislada o ausencia documental se transforma por sí sola en una anulación automática.'},
    ]

# compatibility alias
def traffic_request_sections(a,result):
    return traffic_record_request_sections(a,result)

def escalation_sections(result):
    return [
        {
            'heading': '1. Motivo del bloqueo',
            'text': 'El motor jurídico detectó uno o más escenarios incompatibles con una salida automática definitiva.',
            'bullets': [f"{r.get('id')} — {r.get('message')} Acción: {r.get('action')}" for r in result.get('blocking_rules', [])],
        },
        {
            'heading': '2. Acción requerida',
            'bullets': [
                'Asignar el caso a un especialista de la vertical correspondiente.',
                'Verificar términos, procesos activos, medidas, cuantía y documentos originales.',
                'No radicar, firmar o presentar el borrador como documento definitivo.',
                'Registrar la decisión profesional y la versión documental resultante.',
            ],
        },
    ]


def document_specs(case_id, code, answers, result, product, generated_at, question_rows):
    meta = base_metadata(case_id, code, product, result, generated_at)
    specs = []
    specs.append({
        'kind': 'traceability',
        'title': 'Ficha de diagnóstico y trazabilidad',
        'filename_suffix': 'ficha_trazabilidad',
        'subtitle': 'Expediente técnico-jurídico versionado',
        'sections': traceability_sections(code, answers, result, product, question_rows),
        'metadata': meta,
    })
    if result.get('risk') == 'red':
        specs.append({
            'kind': 'escalation',
            'title': 'Informe de bloqueo y escalamiento profesional',
            'filename_suffix': 'informe_escalamiento',
            'subtitle': 'Salida automática definitiva bloqueada',
            'sections': escalation_sections(result),
            'metadata': meta,
        })
        return specs
    if code == 'CO-EM-003':
        specs += [
            {'kind':'contract','title':'Contrato de prestación de servicios independientes','filename_suffix':'contrato_servicios','subtitle':'Borrador modular para revisión profesional','sections':service_contract_sections(answers,result),'metadata':meta},
            {'kind':'scope','title':'Anexo No. 1 — Alcance, entregables y cronograma','filename_suffix':'anexo_alcance','subtitle':'Anexo operativo del contrato','sections':service_scope_sections(answers),'metadata':meta},
        ]
    elif code == 'CO-LA-001':
        specs += [
            {'kind':'calculation','title':'Informe desglosado de liquidación laboral','filename_suffix':'informe_liquidacion','subtitle':'Cálculo determinístico versionado y alertas jurídicas','sections':labor_report_sections(answers,result.get('calculation'),result),'metadata':meta},
            {'kind':'claim','title':'Reclamación directa de acreencias laborales','filename_suffix':'reclamacion_laboral','subtitle':'Borrador sujeto a soportes y revisión','sections':labor_claim_sections(answers,result.get('calculation')),'metadata':meta},
        ]
    elif code == 'CO-TR-001':
        specs.append({'kind':'sast_report','title':'Informe de coincidencia preliminar SAST','filename_suffix':'informe_sast','subtitle':'Chequeo por autoridad, territorio y fecha','sections':sast_report_sections(answers,result),'metadata':meta})
    elif code == 'CO-TR-002':
        specs.append({'kind':'traffic_request','title':'Solicitud integral de expediente y reclamación por notificación','filename_suffix':'solicitud_expediente_fotomulta','subtitle':'Borrador condicionado por etapa y prueba','sections':traffic_request_sections(answers,result),'metadata':meta})
    else:
        specs.append({
            'kind':'generic','title':product.get('primary_document','Documento preliminar'),
            'filename_suffix':'documento_preliminar','subtitle':'Estructura preliminar del paquete jurídico',
            'sections':[
                {'heading':'1. Alcance','text':product.get('summary')},
                {'heading':'2. Resultados esperados','bullets':product.get('outcomes',[])},
                {'heading':'3. Controles','bullets':['Validar datos y soportes.','Aplicar las reglas activadas.','Integrar el paquete canónico completo.','Obtener revisión profesional antes de uso.']},
            ],'metadata':meta,
        })
    return specs
