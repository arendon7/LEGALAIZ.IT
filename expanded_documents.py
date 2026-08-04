from __future__ import annotations

"""Generadores documentales específicos para los once productos del prototipo.

Los textos son borradores estructurados. Cada salida conserva la trazabilidad y debe
ser validada por el especialista responsable antes de uso profesional.
"""

from pilot_documents import *  # reutiliza generadores profundos de los cuatro pilotos v1.0
import complete_legal_models_v215 as v215


def employment_contract_sections(a, result):
    need = a.get('need_type') or '[NECESIDAD]'
    modality = {
        'Permanente': 'término indefinido',
        'Temporal con fecha cierta': 'término fijo',
        'Obra o labor específica': 'obra o labor determinada',
    }.get(need, '[MODALIDAD POR DEFINIR]')
    return [
        {
            'heading': '1. Partes, modalidad y objeto laboral',
            'text': (
                f"Entre {a.get('employer_name') or '[EMPLEADOR]'} y {a.get('worker_name') or '[TRABAJADOR]'} se estructura un "
                f"borrador de contrato de trabajo a {modality}. La modalidad se selecciona por la necesidad real declarada: {need}. "
                'La ejecución material y los soportes prevalecen sobre la denominación usada por las partes.'
            ),
        },
        {
            'heading': '2. Cargo, funciones y lugar de trabajo',
            'bullets': [
                'Cargo y objetivo: completar antes de firma con resultado verificable y línea de reporte.',
                'Funciones: incorporar en anexo separado, coherentes con el cargo y sin listas genéricas incompatibles.',
                f"Modalidad informada: {a.get('remote') or 'Pendiente'}.",
                'El empleador conserva facultades de dirección dentro de la ley, el contrato y el respeto por la dignidad y derechos del trabajador.',
            ],
        },
        {
            'heading': '3. Duración y período de prueba',
            'table': [
                ('Campo', 'Valor informado'),
                ('Necesidad', need),
                ('Modalidad sugerida', modality),
                ('Duración propuesta', str(a.get('term_years') or 'No aplica / pendiente')),
                ('Período de prueba propuesto', str(a.get('probation_months') or 'No pactado')),
            ],
            'text': 'La duración, prórrogas y período de prueba requieren forma escrita y validación frente a los límites vigentes aplicables a la modalidad elegida.',
        },
        {
            'heading': '4. Salario, pagos variables y prestaciones',
            'table': [
                ('Concepto', 'Condición'),
                ('Salario mensual', cop(a.get('monthly_salary'))),
                ('Pagos variables', a.get('variable_payments') or 'No informado'),
            ],
            'bullets': [
                'La naturaleza salarial de cada pago depende de su finalidad y realidad, no únicamente del nombre asignado.',
                'Las prestaciones, aportes y retenciones se aplicarán conforme a la relación laboral real y los parámetros vigentes.',
                'No se incorpora una exclusión salarial general ni descuentos automáticos por pérdidas, daños o equipos.',
            ],
        },
        {
            'heading': '5. Jornada, descansos y desconexión',
            'bullets': [
                f"Jornada semanal declarada: {a.get('weekly_hours') or 'Pendiente'} horas.",
                'La programación deberá respetar el máximo vigente, descansos, recargos y registro de tiempo cuando corresponda.',
                'La autorización previa de trabajo adicional es un control interno y no extingue el pago del trabajo efectivamente ordenado o probado.',
                'En trabajo remoto o híbrido debe incorporarse desconexión laboral y disponibilidad razonable.',
            ],
        },
        {
            'heading': '6. Equipos, información, datos y propiedad intelectual',
            'bullets': [
                'Equipos o herramientas: ' + ('activar inventario, custodia, devolución y soporte' if a.get('work_equipment') == 'Sí' else 'sin entrega empresarial informada'),
                'Datos sensibles o biométricos: ' + ('requiere finalidad, necesidad, seguridad y autorización separada cuando proceda' if a.get('personal_data') in ('Sí', 'No sé') else 'sin tratamiento especial informado'),
                'Propiedad intelectual: ' + ('activar anexo proporcional, delimitar materiales preexistentes y respetar derechos morales' if a.get('ip_relevant') == 'Sí' else 'sin creación relevante informada'),
            ],
        },
        {
            'heading': '7. Debida diligencia y protecciones especiales',
            'bullets': [
                f"Protección especial informada: {a.get('special_protection') or 'Pendiente'}.",
                f"Escenario público o transnacional: {a.get('public_or_crossborder') or 'Pendiente'}.",
                'Si existe embarazo, discapacidad, salud, fuero, minoría de edad, vínculo público o situación transnacional, se bloquea la salida estándar y se exige revisión especializada.',
            ],
        },
        {
            'heading': '8. Terminación y control disciplinario',
            'bullets': [
                'Las causales, procedimientos y efectos de terminación se regirán por la ley y la prueba disponible.',
                'Las actuaciones disciplinarias requieren comunicación de hechos, oportunidad de defensa y decisión motivada cuando corresponda.',
                'La terminación no habilita renuncias generales, descuentos automáticos ni apropiación de derechos del trabajador.',
            ],
        },
        {
            'heading': '9. Control previo a firma',
            'bullets': [
                'Completar identificación, cargo, funciones, sede, fecha de inicio, salario y periodicidad de pago.',
                'Confirmar modalidad contractual por la necesidad real y no por conveniencia de corto plazo.',
                'Activar anexos de funciones, equipos, teletrabajo, datos y propiedad intelectual solo cuando correspondan.',
                'Revisar reglamento, políticas, SG-SST y canales de reporte aplicables.',
                'Entregar copia íntegra y conservar evidencia de aceptación y anexos.',
            ],
        },
    ]


def employment_annex_sections(a):
    return [
        {'heading': '1. Objetivo del cargo', 'text': '[Definir el resultado principal y su relación con la operación del empleador.]'},
        {'heading': '2. Funciones verificables', 'bullets': ['[FUNCIÓN 1]', '[FUNCIÓN 2]', '[FUNCIÓN 3]', 'Otras actividades compatibles con el cargo, razonables y comunicadas.']},
        {'heading': '3. Indicadores y coordinación', 'text': 'Definir entregables, criterios de calidad, responsables, frecuencia de reporte y dependencias sin alterar unilateralmente elementos esenciales.'},
        {'heading': '4. Recursos y equipos', 'text': 'Activar inventario y acta de entrega cuando la empresa suministre equipos, credenciales, licencias o herramientas.'},
        {'heading': '5. Módulos aplicables', 'bullets': [
            f"Trabajo remoto/híbrido: {a.get('remote') or 'Pendiente'}.",
            f"Datos sensibles/biométricos: {a.get('personal_data') or 'Pendiente'}.",
            f"Creación de activos de PI: {a.get('ip_relevant') or 'Pendiente'}.",
        ]},
    ]


def nda_sections(a):
    nda_type = (a.get('nda_type') or '[TIPO]').lower()
    return [
        {'heading': '1. Partes, modalidad y finalidad', 'text': f"{a.get('party_a') or '[PARTE A]'} y {a.get('party_b') or '[PARTE B]'} celebran un acuerdo {nda_type} para la finalidad exclusiva: {a.get('purpose') or '[FINALIDAD PENDIENTE]'}."},
        {'heading': '2. Relación y alcance', 'table': [('Campo','Condición'),('Relación subyacente',a.get('relationship_context') or 'Pendiente'),('Información definida',a.get('info_defined') or 'Pendiente'),('Duración',f"{a.get('duration_years') or 'Pendiente'} año(s)")]},
        {'heading': '3. Categorías y acceso autorizado', 'text': a.get('info_categories') or '[CATEGORÍAS PENDIENTES]', 'bullets': [f"Destinatarios autorizados: {a.get('authorized_recipients') or 'Pendiente'}", 'El acceso se limita a la necesidad de conocer y debe ser revocado cuando cese.']},
        {'heading': '4. Exclusiones', 'bullets': ['Información pública sin infracción del acuerdo.', 'Información conocida legítimamente antes de la revelación.', 'Información recibida de un tercero autorizado.', 'Información desarrollada de manera independiente y demostrable.', 'Conocimientos generales, experiencia y habilidades profesionales.']},
        {'heading': '5. Uso, custodia y divulgación', 'bullets': ['Usar la información solo para la finalidad autorizada.', 'Aplicar mínimo privilegio, autenticación, almacenamiento y transmisión seguros.', 'No cargar información en herramientas públicas o no autorizadas de IA.', 'Documentar divulgaciones obligatorias y avisar cuando sea jurídicamente posible.']},
        {'heading': '6. Secretos empresariales', 'bullets': ['Clasificar la información y limitar el acceso.', 'Conservar evidencia de medidas razonables de reserva y trazabilidad.', 'La denominación contractual no sustituye la verificación material de sus condiciones.']} if a.get('trade_secrets') in ('Sí','No sé') else {'heading': '6. Información confidencial ordinaria', 'text': 'No se informó un secreto empresarial; la protección se limita a las categorías y obligaciones pactadas.'},
        {'heading': '7. Datos personales', 'bullets': ['La confidencialidad no reemplaza las obligaciones de protección de datos.', f"Tratamiento informado: {a.get('personal_data') or 'Pendiente'}; transferencia o nube externa: {a.get('crossborder') or 'Pendiente'}."]},
        {'heading': '8. Propiedad intelectual', 'bullets': ['La confidencialidad no transfiere por sí sola derechos patrimoniales.', 'Toda cesión o licencia debe delimitar resultados, modalidades, territorio, plazo y contraprestación cuando corresponda.', 'Los derechos morales no se renuncian ni transfieren por estipulación general.', 'Los materiales preexistentes y componentes de terceros deben inventariarse.']},
        {'heading': '9. Incidentes, devolución y eliminación', 'bullets': ['Reportar incidentes y preservar evidencia.', 'Al terminar, devolver, eliminar o conservar únicamente copias justificadas y controladas.', 'Registrar responsables, fechas, soportes y excepciones de conservación.']},
        {'heading': '10. Límites y revisión', 'bullets': ['No impone prohibición general de trabajar.', 'No comprende obras o resultados futuros indeterminados.', 'No autoriza datos sensibles ni IA pública sin evaluación especializada.', 'Borrador interno sujeto a validación jurídica y aprobación dual antes de uso profesional.']},
    ]


def information_inventory_sections(a):
    return [
        {'heading':'1. Identificación y finalidad','table':[('Parte reveladora',a.get('party_a') or 'Pendiente'),('Parte receptora',a.get('party_b') or 'Pendiente'),('Finalidad',a.get('purpose') or 'Pendiente')]},
        {'heading':'2. Categorías de información','text':a.get('info_categories') or 'Categorías descritas en el acuerdo principal'},
        {'heading':'3. Matriz de acceso','table':[('Campo','Contenido'),('Rol o persona',a.get('authorized_recipients') or 'Personas autorizadas por la parte reveladora'),('Necesidad de conocer','Solo para la finalidad y función asignada'),('Sistema o soporte','Repositorio privado y canales corporativos'),('Responsable','Director del proyecto designado por la Parte A'),('Revocación','Al cierre o cuando cese la necesidad de acceso')]},
        {'heading':'4. Clasificación y medidas','bullets':['Clasificación: pública, interna, confidencial o secreto empresarial.','Controles: identidad, privilegio mínimo, registro, cifrado, copia, envío y eliminación.','Evidencia de medidas razonables cuando se alegue secreto empresarial.']},
        {'heading':'5. Actualización y control','bullets':['Actualizar ante cambios de finalidad, personas, sistemas o terceros.','No clasificar como secreto información que no cumpla condiciones materiales.','Conservar versión, responsable y fecha de cada cambio.']},
    ]


def relationship_annex_sections(a):
    context=a.get('relationship_context') or 'Otra'
    tailored={
        'Comercial/proveedor':['Definir personal autorizado del proveedor y subcontratistas.','Limitar uso a evaluación, oferta o ejecución del servicio.','Exigir devolución y cierre al terminar la relación.'],
        'Laboral/colaborador':['Relacionar deberes con cargo, funciones y sistemas autorizados.','No apropiar conocimientos generales ni imponer prohibición general de trabajar.','Separar confidencialidad de propiedad intelectual y datos del trabajador.'],
        'Software/tecnología':['Inventariar repositorios, credenciales, arquitectura, datos, antecedentes y OSS.','Definir entornos y herramientas de IA autorizados.','Regular entrega, acceso, respaldos y revocación.'],
        'Contenidos/creativo':['Identificar materiales de referencia, contenidos preexistentes y resultados nuevos.','Diferenciar confidencialidad, licencia y cesión patrimonial.','Respetar derechos morales y créditos aplicables.'],
    }.get(context,['Definir deberes específicos conforme a la relación real.'])
    return [
        {'heading':'1. Relación subyacente','text':f"Este anexo corresponde al contexto: {context}. Complementa el acuerdo principal sin sustituirlo."},
        {'heading':'2. Obligaciones específicas','bullets':tailored},
        {'heading':'3. Personal y terceros','text':f"Acceso autorizado informado: {a.get('authorized_recipients') or 'Pendiente'}. Toda extensión a terceros requiere necesidad, autorización y obligaciones equivalentes."},
        {'heading':'4. Límites','bullets':['Las restricciones deben ser necesarias y proporcionales.','El anexo no crea por sí solo relación laboral, cesión de PI ni autorización de tratamiento de datos.']},
    ]


def ip_annex_sections(a):
    return [
        {'heading':'1. Objeto','text':f"Regular antecedentes, resultados y componentes vinculados a: {a.get('purpose') or '[FINALIDAD]'}."},
        {'heading':'2. Materiales preexistentes','table':[('Existencia informada',a.get('preexisting_materials') or 'Pendiente'),('Activo/titular/licencia/restricciones','Registrar cada activo preexistente en el inventario técnico antes de su uso')]},
        {'heading':'3. Componentes de terceros y OSS','table':[('Uso informado',a.get('oss_components') or 'Pendiente'),('Componente/versión/licencia/obligaciones','Mantener inventario SBOM y verificación de licencias antes de integrar componentes')]},
        {'heading':'4. Resultados nuevos','bullets':['Identificar cada obra, desarrollo o resultado verificable.','Definir titularidad o licencia, modalidades de explotación, territorio, plazo y contraprestación cuando corresponda.','Documentar entregables, repositorios y aceptación.']},
        {'heading':'5. Derechos morales y garantías','bullets':['Los derechos morales no se transfieren ni renuncian por cláusula general.','Cada parte declara facultades sobre sus aportes y revela restricciones de terceros.','No se incorporan componentes incompatibles sin aprobación documentada.']},
        {'heading':'6. Control previo','bullets':['No comprende obras o resultados futuros indeterminados.','La confidencialidad no equivale a cesión o licencia.','Requiere validación jurídica antes de firma.']},
    ]


def data_annex_sections(a):
    return [
        {'heading':'1. Alcance','table':[('Datos personales',a.get('personal_data') or 'Pendiente'),('Datos sensibles',a.get('sensitive_data') or 'Pendiente'),('Transferencia/nube exterior',a.get('crossborder') or 'Pendiente')]},
        {'heading':'2. Finalidad y roles','text':f"Finalidad: {a.get('purpose') or 'Pendiente'}. Identificar responsable, encargado, titulares, categorías, operaciones y canales de atención."},
        {'heading':'3. Instrucciones y seguridad','bullets':['Tratar solo conforme a instrucciones documentadas y finalidad autorizada.','Aplicar mínimo privilegio, cifrado, registro, respaldo, retención y eliminación.','Gestionar incidentes, solicitudes de titulares y evidencias.']},
        {'heading':'4. Proveedores y transferencias','bullets':['Identificar proveedor, país, ubicación, subencargados y garantías.','No transferir o transmitir sin base, autorización y controles aplicables.','Mantener trazabilidad de cambios de infraestructura.']},
        {'heading':'5. Restricciones','bullets':['La confidencialidad no reemplaza el régimen de datos personales.','Los datos sensibles, biométricos o de salud requieren evaluación especializada previa.','No cargar datos en IA pública o servicios no autorizados.']},
    ]


def incident_protocol_sections(a):
    return [
        {'heading':'1. Alcance y responsables','text':f"Aplica a las categorías: {a.get('info_categories') or 'Pendientes'}. Designar responsables jurídico, técnico, de datos y comunicaciones."},
        {'heading':'2. Eventos reportables','bullets':['Pérdida, acceso o divulgación no autorizada.','Envío a destinatario incorrecto.','Credenciales comprometidas.','Carga en servicio, nube o IA no autorizados.','Requerimiento de autoridad o divulgación obligatoria.']},
        {'heading':'3. Respuesta por fases','table':[('Fase','Acción mínima'),('Detección','Registrar fecha, fuente, activos y alcance'),('Contención','Limitar acceso sin destruir evidencia'),('Análisis','Determinar información, personas, sistemas y terceros'),('Escalamiento','Avisar responsables y evaluar notificaciones'),('Recuperación','Restaurar, devolver, eliminar o rotar credenciales'),('Cierre','Causa, impacto, acciones correctivas y evidencia')]},
        {'heading':'4. Evidencia y comunicaciones','bullets':['Conservar cronología, decisiones, respaldos, registros y comunicaciones.','Comunicar solo por canales autorizados y con información verificada.','Coordinar obligaciones contractuales y legales aplicables.']},
        {'heading':'5. Mejora','text':'Registrar lecciones aprendidas, responsables, fechas y verificación de acciones correctivas.'},
    ]


def closure_act_sections(a):
    return [
        {'heading':'1. Identificación','table':[('Parte A',a.get('party_a') or 'Pendiente'),('Parte B',a.get('party_b') or 'Pendiente'),('Finalidad cerrada',a.get('purpose') or 'Pendiente'),('Fecha de cierre','Fecha de firma de la presente acta')]},
        {'heading':'2. Inventario de cierre','table':[('Campo','Contenido'),('Categoría o soporte',a.get('info_categories') or 'Categorías descritas en el acuerdo principal'),('Acción','Devolver originales; eliminar copias operativas; conservar solo evidencia controlada'),('Responsable','Director del proyecto designado por la Parte A'),('Fecha','Fecha de firma de la presente acta'),('Evidencia','Acta firmada, registro de eliminación y constancia de revocación de accesos')]},
        {'heading':'3. Accesos y terceros','bullets':['Revocar credenciales, permisos, tokens y copias compartidas.','Confirmar cierre con destinatarios autorizados, proveedores y subcontratistas.','Registrar excepciones técnicas o legales de conservación.']},
        {'heading':'4. Declaraciones','bullets':['No se certifica eliminación sin evidencia suficiente.','Las copias conservadas permanecen sujetas a controles y plazos.','Los incidentes o controversias pendientes se registran expresamente.']},
        {'heading':'5. Firmas y trazabilidad','text':'Incorporar nombres, cargos, fecha, reservas, anexos probatorios y mecanismo de aceptación verificable.'},
    ]


def lease_contract_sections(a):
    return [
        {
            'heading': '1. Partes e inmueble',
            'text': (
                f"Entre {a.get('landlord') or '[ARRENDADOR]'} y {a.get('tenant') or '[ARRENDATARIO]'} se estructura un contrato de "
                f"arrendamiento de vivienda urbana sobre: {a.get('property') or '[INMUEBLE PENDIENTE]'}"
            ),
        },
        {
            'heading': '2. Destinación y entrega',
            'bullets': [
                'Destinación exclusiva a vivienda urbana ordinaria de los ocupantes autorizados.',
                'La entrega se documentará mediante inventario, fotografías, lecturas de medidores, llaves y defectos preexistentes.',
                'El reglamento de propiedad horizontal se entrega y acepta cuando corresponda.',
            ],
        },
        {
            'heading': '3. Canon, administración y servicios',
            'table': [
                ('Concepto', 'Condición'),
                ('Canon mensual', cop(a.get('rent'))),
                ('Propiedad horizontal', a.get('ph') or 'Pendiente'),
                ('Garantía', a.get('co_debtor') or 'Sin garantía adicional'),
            ],
            'bullets': [
                'Separar canon, administración ordinaria, cuotas extraordinarias, servicios, parqueadero y conceptos adicionales.',
                'El canon y sus reajustes deben respetar límites legales y conservar soporte del valor utilizado.',
                'No se exige depósito en dinero ni caución real a favor del arrendador para garantizar obligaciones residenciales.',
            ],
        },
        {
            'heading': '4. Obligaciones y reparaciones',
            'bullets': [
                'El arrendador entrega y mantiene el inmueble en condiciones de servicio, seguridad y goce convenido.',
                'El arrendatario paga, cuida, informa daños y asume reparaciones locativas atribuibles al uso ordinario o culpa probada.',
                'Las reparaciones indispensables y locativas deben diferenciarse y gestionarse por escrito.',
                'El desgaste normal no se cobra como daño.',
            ],
        },
        {
            'heading': '5. Uso, visitas y convivencia',
            'bullets': [
                'No se permite turismo, plataforma, cambio de destinación o subarriendo sin acuerdo y producto jurídico apropiado.',
                'Las visitas de inspección deben coordinarse razonablemente; no existe ingreso libre del arrendador.',
                'Los ocupantes deben observar normas de convivencia y propiedad horizontal entregadas.',
            ],
        },
        {
            'heading': '6. Terminación y restitución',
            'bullets': [
                'La terminación requiere causal, preaviso, canal y efectos compatibles con el régimen aplicable.',
                'La restitución se documentará con acta, inventario comparado, llaves, medidores y facturas pendientes.',
                'Las reservas por facturas no emitidas o daños no detectables se documentarán sin convertirlas en depósito prohibido.',
            ],
        },
        {
            'heading': '7. Control previo',
            'bullets': [
                'Verificar titularidad o autorización reciente del arrendador.',
                'Confirmar que no hay controversia de tenencia, restitución o litigio activo.',
                'Revisar condiciones de sanidad, seguridad, servicios y defectos antes de entregar.',
                'Anexar inventario, acta de entrega, reglamento y soportes de pago.',
            ],
        },
    ]


def lease_inventory_sections(a):
    return [
        {'heading': '1. Identificación', 'table': [('Campo', 'Información'), ('Inmueble', a.get('property') or 'Pendiente'), ('Arrendador', a.get('landlord') or 'Pendiente'), ('Arrendatario', a.get('tenant') or 'Pendiente')]},
        {'heading': '2. Inventario por espacios', 'table': [('Espacio / elemento', 'Estado / observación'), ('Acceso y llaves', '[...]'), ('Muros, pisos y techos', '[...]'), ('Cocina y equipos', '[...]'), ('Baños', '[...]'), ('Ventanas y puertas', '[...]'), ('Medidores y servicios', '[...]'), ('Muebles/equipos', '[...]')]},
        {'heading': '3. Evidencia', 'bullets': ['Adjuntar fotografías fechadas y legibles.', 'Registrar seriales, cantidades y funcionamiento.', 'Identificar humedad, fisuras, fugas, instalaciones o trabajos pendientes.', 'Firmar y entregar copia a las partes.']},
    ]


def delivery_act_sections(a):
    return [
        {'heading': '1. Entrega', 'text': f"Se documenta la entrega del inmueble {a.get('property') or '[INMUEBLE]'} al arrendatario {a.get('tenant') or '[ARRENDATARIO]'}."},
        {'heading': '2. Elementos entregados', 'bullets': ['Llaves y controles: [...]', 'Lecturas de medidores: [...]', 'Reglamento y manuales: [...]', 'Inventario y fotografías: [...]']},
        {'heading': '3. Novedades y compromisos', 'text': '[Defectos, reparaciones, fecha de atención, responsable y evidencia.]'},
        {'heading': '4. Constancia', 'text': 'Las partes reciben copia del acta. La firma no implica renuncia a defectos ocultos, obligaciones legales ni derechos irrenunciables.'},
    ]



def _health_calc(result):
    return (result or {}).get('calculation') or {}


def health_petition_v231_sections(a, result):
    c=_health_calc(result)
    return [
        {'heading':'1. Destinatario y asunto','table':[('Campo','Información'),('Entidad',a.get('entity') or '[ENTIDAD]'),('Tipo de entidad',a.get('entity_type') or '[TIPO]'),('Ciudad',a.get('entity_city') or '[CIUDAD]'),('Asunto',a.get('request_type') or '[SOLICITUD]')]},
        {'heading':'2. Peticionario, paciente y legitimación','table':[('Peticionario',a.get('petitioner_name') or '[NOMBRE]'),('Identificación',a.get('petitioner_id') or '[ID]'),('Calidad',a.get('acting_capacity') or '[CALIDAD]'),('Paciente',a.get('patient_name') or '[PACIENTE]'),('Identificación paciente',a.get('patient_id') or '[ID PACIENTE]'),('Situación',a.get('patient_status') or '[SITUACIÓN]'),('Relación',a.get('relationship_to_patient') or '[RELACIÓN]'),('Soporte',a.get('representation_support') or '[SOPORTE]')]},
        {'heading':'3. Hechos confirmados','text':a.get('request_detail') or '[DESCRIBIR HECHOS]', 'bullets':[f"Soporte médico disponible: {a.get('medical_support') or 'Pendiente'}.",f"Fecha de orden o fórmula: {a.get('prescription_date') or 'No informada'}.",f"Continuidad del tratamiento: {a.get('continuity_risk') or 'Pendiente'}.",f"Condición de priorización: {a.get('priority_condition') or 'Pendiente'}." ]},
        {'heading':'4. Peticiones concretas','text':a.get('requested_outcome') or '[RESULTADO SOLICITADO]', 'bullets':['Emitir respuesta de fondo, clara, precisa, congruente y efectivamente comunicada.','Coordinar autorización, agenda, prestador, medicamento o trámite cuando corresponda.','Informar fechas, responsables, canal y pasos verificables.','Preservar continuidad y priorización cuando estén acreditadas.','Asignar radicado y conservar trazabilidad de la respuesta.']},
        {'heading':'5. Término y prioridad','table':[('Categoría preliminar',c.get('term_category') or 'Pendiente'),('Días hábiles preliminares',str(c.get('preliminary_business_days') or 'Pendiente')),('Fecha de radicación',c.get('filing_date') or a.get('filing_date') or 'Pendiente'),('Vencimiento preliminar',c.get('preliminary_due_date') or 'Pendiente'),('Festivos descontados','No')], 'bullets':['El calendario es preliminar y debe verificarse frente a festivos, traslado, ampliación informada, suspensión y norma especial.','La atención prioritaria no sustituye atención médica de urgencias.']},
        {'heading':'6. Historia clínica, privacidad y seguridad','bullets':[f"Entrega segura: {a.get('secure_delivery') or 'No aplica'}.",f"Autorización de tercero: {a.get('third_party_authorization') or 'No aplica'}.",f"Minimización de datos: {a.get('data_minimized') or 'Pendiente'}.",'Adjuntar únicamente información clínica y personal necesaria.','No usar enlaces abiertos ni canales sin autenticación para historia clínica.']},
        {'heading':'7. Anexos','bullets':['Documento de identidad del peticionario y del paciente.','Autorización, poder, registro civil o soporte de legitimación cuando aplique.','Orden, fórmula o soporte médico pertinente.','Petición previa, radicado y respuesta, si existen.','Otros soportes estrictamente necesarios y legibles.']},
        {'heading':'8. Notificaciones y firma','table':[('Correo',a.get('email') or '[CORREO]'),('Teléfono',a.get('phone') or '[TELÉFONO]'),('Dirección',a.get('address') or '[DIRECCIÓN]'),('Ciudad',a.get('city') or '[CIUDAD]'),('Canal preferido',a.get('notification_channel') or '[CANAL]')], 'text':'Atentamente,\n\n__________________________________\n'+(a.get('petitioner_name') or '[PETICIONARIO]')+'\n'+(a.get('petitioner_id') or '[IDENTIFICACIÓN]')},
        {'heading':'9. Advertencia de uso','bullets':['Este documento no sustituye urgencias, consulta médica, tutela ni representación judicial.','La respuesta o prestación no está garantizada.','Debe revisarse la versión exacta y sus anexos antes de radicar.']},
    ]


def medical_record_request_v231_sections(a, result):
    return [
        {'heading':'1. Solicitud de historia clínica','text':f"A {a.get('entity') or '[ENTIDAD]'} se solicita acceso o copia de la historia clínica del paciente {a.get('patient_name') or '[PACIENTE]'}, identificado con {a.get('patient_id') or '[ID]'}.", 'table':[('Solicitante',a.get('petitioner_name') or '[NOMBRE]'),('Calidad',a.get('acting_capacity') or '[CALIDAD]'),('Relación',a.get('relationship_to_patient') or '[RELACIÓN]'),('Soporte de legitimación',a.get('representation_support') or '[SOPORTE]')]},
        {'heading':'2. Alcance delimitado','text':a.get('medical_record_scope') or 'No aplica o pendiente de delimitar.', 'bullets':['Identificar período, servicio, sede y tipo de registro requerido.','Evitar solicitar información ajena a la finalidad legítima.']},
        {'heading':'3. Finalidad y paciente fallecido','text':a.get('deceased_access_purpose') or 'No aplica.', 'bullets':['El acceso de familiares no es automático y requiere análisis individual.','Aportar identidad, parentesco, finalidad y demás soportes aplicables.']},
        {'heading':'4. Entrega segura','table':[('Canal seguro solicitado',a.get('secure_delivery') or 'Pendiente'),('Autorización de tercero',a.get('third_party_authorization') or 'No aplica'),('Minimización confirmada',a.get('data_minimized') or 'Pendiente')], 'bullets':['Verificar identidad antes de entregar.','Usar descarga autenticada, cifrado o entrega física controlada.','Dejar constancia del período e integridad de la copia.','No divulgar a destinatarios no autorizados.']},
        {'heading':'5. Peticiones','bullets':['Entregar copia legible del alcance solicitado.','Informar si existe información no disponible y su razón.','Indicar canal, fecha y responsable de entrega.','Preservar reserva y trazabilidad.']},
        {'heading':'6. Control profesional','text':'La legitimación, finalidad y suficiencia de soportes deben ser revisadas antes de radicar o entregar información clínica.'},
    ]


def health_reiteration_v231_sections(a, result):
    c=_health_calc(result)
    return [
        {'heading':'1. Petición previa','table':[('Entidad',a.get('entity') or '[ENTIDAD]'),('Fecha',a.get('prior_request_date') or 'No informada'),('Radicado',a.get('prior_radicado') or 'No informado'),('Respuesta recibida',a.get('response_received') or 'No aplica'),('Fecha de respuesta',a.get('response_date') or 'No informada'),('Calidad',a.get('response_quality') or 'No aplica')]},
        {'heading':'2. Término preliminar','table':[('Días aplicados',str(c.get('preliminary_business_days') or 'Pendiente')),('Vencimiento preliminar de la petición previa',c.get('prior_preliminary_due_date') or 'Pendiente'),('Festivos descontados','No')], 'text':'El cálculo debe verificarse antes de alegar vencimiento definitivo.'},
        {'heading':'3. Puntos pendientes','text':a.get('request_detail') or '[PUNTOS NO RESUELTOS]'},
        {'heading':'4. Reiteración','bullets':['Responder cada solicitud de manera separada.','Emitir respuesta de fondo, clara, precisa y congruente.','Explicar razones, actuaciones y responsables.','Notificar efectivamente por el canal indicado.','Conservar el radicado y la cronología anterior.']},
        {'heading':'5. Prevención de duplicidad','table':[('Tutela activa',a.get('tutela_active') or 'No'),('PQRD Supersalud activa',a.get('supersalud_case_active') or 'No')], 'text':'Si existe actuación activa, coordinar la estrategia con el expediente antes de presentar esta reiteración.'},
    ]


def supersalud_escalation_v231_sections(a, result):
    return [
        {'heading':'1. Identificación de la barrera','table':[('Entidad vigilada',a.get('entity') or '[ENTIDAD]'),('Paciente',a.get('patient_name') or '[PACIENTE]'),('Solicitud',a.get('request_type') or '[TIPO]'),('Radicado previo',a.get('prior_radicado') or 'No informado')]},
        {'heading':'2. Relato cronológico','text':a.get('request_detail') or '[HECHOS]', 'bullets':[f"Respuesta recibida: {a.get('response_received') or 'No aplica'}.",f"Calidad de respuesta: {a.get('response_quality') or 'No aplica'}.",f"Continuidad en riesgo: {a.get('continuity_risk') or 'Pendiente'}." ]},
        {'heading':'3. Solicitud a la Superintendencia','bullets':['Registrar y clasificar la PQRD.','Informar radicado, canal y estado de seguimiento.','Adoptar o promover las actuaciones que correspondan dentro de su competencia.','Requerir respuesta verificable a la entidad cuando proceda.']},
        {'heading':'4. Anexos mínimos','bullets':['Petición y constancia de radicación.','Respuesta o evidencia de silencio.','Identidad y legitimación.','Soporte médico estrictamente necesario.','Cronología de comunicaciones.']},
        {'heading':'5. Límites','bullets':['No reemplaza tutela, demanda o representación judicial.','No garantiza una orden o decisión favorable.','No debe duplicarse una PQRD activa sin revisar el expediente.','Ante urgencia médica se usan canales asistenciales inmediatos.']},
    ]


def health_evidence_index_v231_sections(a, result):
    return [
        {'heading':'1. Matriz de identidad y legitimación','table':[('Elemento','Estado declarado'),('Identidad del peticionario','Confirmar'),('Identidad del paciente','Confirmar'),('Calidad o relación',a.get('acting_capacity') or 'Pendiente'),('Soporte de representación',a.get('representation_support') or 'Pendiente'),('Autorización de tercero',a.get('third_party_authorization') or 'No aplica'),('Finalidad paciente fallecido',a.get('deceased_access_purpose') or 'No aplica')]},
        {'heading':'2. Matriz de soportes','table':[('Soporte','Estado'),('Orden, fórmula o soporte médico',a.get('medical_support') or 'Pendiente'),('Petición previa',a.get('prior_request') or 'No'),('Radicado previo',a.get('prior_radicado') or 'No aplica'),('Respuesta previa',a.get('response_received') or 'No aplica'),('Historia clínica delimitada',a.get('medical_record_scope') or 'No aplica')]},
        {'heading':'3. Control de privacidad','table':[('Minimización',a.get('data_minimized') or 'Pendiente'),('Entrega segura',a.get('secure_delivery') or 'No aplica')], 'bullets':['Ocultar datos no necesarios.','No modificar archivos originales.','Registrar origen, fecha y responsable.','Evitar enlaces públicos y destinatarios no autorizados.']},
        {'heading':'4. Trazabilidad de radicación','bullets':['Conservar copia íntegra de la petición.','Guardar comprobante, fecha, hora y canal.','Registrar número de radicado.','Conservar respuesta y evidencia de notificación.']},
    ]


def health_deadline_calendar_v231_sections(a, result):
    c=_health_calc(result)
    return [
        {'heading':'1. Parámetros del calendario','table':[('Tipo de petición',a.get('request_type') or 'Pendiente'),('Categoría preliminar',c.get('term_category') or 'Pendiente'),('Días hábiles preliminares',str(c.get('preliminary_business_days') or 'Pendiente')),('Radicación',c.get('filing_date') or a.get('filing_date') or 'Pendiente'),('Vencimiento preliminar',c.get('preliminary_due_date') or 'Pendiente'),('Festivos aplicados','No')]},
        {'heading':'2. Petición previa','table':[('Fecha previa',c.get('prior_request_date') or 'No aplica'),('Vencimiento preliminar previo',c.get('prior_preliminary_due_date') or 'No aplica'),('Respuesta',a.get('response_received') or 'No aplica'),('Fecha respuesta',a.get('response_date') or 'No aplica')]},
        {'heading':'3. Hitos de seguimiento','table':[('Hito','Fecha / estado'),('Guardar constancia de radicación',a.get('filing_date') or 'Pendiente'),('Verificar traslado o extensión','Pendiente'),('Control preliminar de respuesta',c.get('preliminary_due_date') or 'Pendiente'),('Revisar respuesta de fondo','Pendiente'),('Decidir reiteración o escalamiento','Pendiente')]},
        {'heading':'4. Advertencia','text':'Este calendario excluye fines de semana, pero no festivos. Debe revisarse frente a normas especiales, traslado por competencia, ampliación informada, suspensión y fecha efectiva de recepción.'},
    ]


def health_filing_guide_v231_sections(a, result):
    return [
        {'heading':'1. Antes de radicar','bullets':['Confirmar nombre y competencia de la entidad.','Revisar identidad y legitimación.','Separar urgencia médica de gestión administrativa.','Delimitar la solicitud y el resultado esperado.','Minimizar información clínica y personal.']},
        {'heading':'2. Canal y constancia','table':[('Canal previsto',a.get('filing_channel') or 'Pendiente'),('Entidad',a.get('entity') or 'Pendiente'),('Ciudad',a.get('entity_city') or 'Pendiente')], 'bullets':['Preferir canal oficial que genere radicado.','Guardar copia íntegra y anexos.','Registrar fecha, hora y comprobante.','No depender de redes sociales o canales sin constancia.']},
        {'heading':'3. Después de radicar','bullets':['Controlar el término preliminar.','Verificar si hubo traslado o ampliación.','Comparar la respuesta con cada petición.','Conservar evidencia de notificación.','Escalar solo después de revisar actuaciones activas.']},
        {'heading':'4. Privacidad y seguridad','bullets':['No publicar historia clínica.','Usar archivos protegidos o entrega autenticada.','No compartir vínculos abiertos.','Eliminar copias temporales innecesarias.','Verificar destinatarios antes del envío.']},
        {'heading':'5. Escalamiento','table':[('Tutela activa',a.get('tutela_active') or 'No'),('PQRD activa',a.get('supersalud_case_active') or 'No'),('Urgencia',a.get('urgent') or 'Pendiente')], 'text':'Los procesos activos, la urgencia, el perjuicio irremediable o la disputa de legitimación requieren revisión profesional.'},
    ]

def health_petition_sections(a):
    return [
        {'heading': '1. Destinatario e identificación', 'text': f"Señores {a.get('entity') or '[EPS / IPS / ENTIDAD]'} — paciente {a.get('patient_name') or '[PACIENTE]'}."},
        {
            'heading': '2. Solicitud concreta',
            'text': a.get('request_detail') or '[DESCRIBIR EL SERVICIO, DECISIÓN, INFORMACIÓN O HISTORIA CLÍNICA SOLICITADA.]',
            'bullets': [f"Tipo de necesidad: {a.get('request_type') or 'Pendiente'}.", f"Condición de priorización: {a.get('priority_condition') or 'No informada'}.", f"Soporte médico: {a.get('medical_support') or 'Pendiente'}."],
        },
        {'heading': '3. Hechos', 'bullets': ['Identificar afiliación o relación con la entidad.', 'Describir orden, diagnóstico o soporte sin afirmar información no documentada.', 'Relacionar fechas, canales, radicados y respuestas previas.', 'Explicar la barrera y sus efectos reales confirmados.']},
        {'heading': '4. Peticiones', 'bullets': ['Emitir decisión integral, clara y motivada.', 'Coordinar internamente autorizaciones, red, agenda y proveedor cuando corresponda.', 'Informar fecha, lugar, responsable y pasos concretos.', 'Entregar copia o acceso reservado cuando se trate de historia clínica.', 'Asignar número de radicado y conservar trazabilidad.']},
        {'heading': '5. Soportes', 'bullets': ['Documento de identidad y representación.', 'Orden, fórmula, historia o soporte médico pertinente.', 'Radicados y comunicaciones previas.', 'Autorización del paciente cuando quien solicita sea un tercero.']},
        {'heading': '6. Advertencias', 'bullets': ['Este documento no sustituye atención de urgencias.', 'No se incorporan diagnósticos u órdenes no confirmados.', 'La historia clínica es reservada y exige legitimación.', 'Una tutela o proceso activo requiere coordinación profesional para evitar duplicidad.']},
    ]


def evidence_index_sections(a, topic):
    return [
        {'heading': '1. Índice de evidencia', 'table': [('No.', 'Documento / evidencia'), ('1', 'Identificación y legitimación'), ('2', 'Contrato, factura, reporte, orden o soporte principal'), ('3', 'Comunicaciones y radicados'), ('4', 'Prueba de fechas, pagos, entrega o conocimiento'), ('5', 'Otros soportes pertinentes')]},
        {'heading': '2. Control de datos', 'text': f"Para {topic}, adjuntar únicamente información necesaria, legible y pertinente. Ocultar datos financieros, clínicos o personales no indispensables."},
        {'heading': '3. Trazabilidad', 'bullets': ['Conservar nombre original y fecha.', 'Registrar origen y responsable.', 'No alterar capturas o documentos.', 'Mantener copia de lo radicado y constancia de entrega.']},
    ]


def habeas_claim_sections(a):
    return [
        {'heading': '1. Titular y destinatarios', 'text': f"Titular: {a.get('data_subject') or '[TITULAR]'}. Fuente identificada: {a.get('source_known') or 'Pendiente'}. Operador: {a.get('operator') or a.get('operator_known') or 'Pendiente'}."},
        {'heading': '2. Problema y pretensión', 'table': [('Campo', 'Información'), ('Problema', a.get('issue') or 'Pendiente'), ('Pretensión', a.get('claim_goal') or 'Pendiente'), ('Fecha aproximada', a.get('report_date') or 'Pendiente'), ('Reclamo previo', a.get('prior_claim') or 'No informado')]},
        {'heading': '3. Hechos', 'bullets': ['Describir obligación, cuenta, producto o relación reportada.', 'Precisar dato inexacto, desactualizado, no comunicado, vencido o presuntamente suplantado.', 'Relacionar pagos, fechas, soportes y consultas.', 'Identificar daño o urgencia sin exagerar consecuencias no probadas.']},
        {'heading': '4. Solicitudes', 'bullets': ['Informar origen, soporte, autorización o título del dato.', 'Corregir, actualizar o eliminar cuando jurídicamente proceda.', 'Incluir leyenda de reclamo en trámite durante la actuación.', 'Comunicar la decisión al titular y a los operadores involucrados.', 'Conservar prueba de comunicación previa cuando sea exigible.']},
        {'heading': '5. Reserva y seguridad', 'bullets': ['No incluir claves, contraseñas ni números completos de instrumentos financieros.', 'En suplantación, preservar evidencia y coordinar medidas con fuentes, operadores y autoridades competentes.', 'Los procesos judiciales, insolvencia, embargos o múltiples fuentes requieren revisión profesional.']},
    ]


def consumer_claim_sections(a):
    mechanism = a.get('mechanism') or a.get('problem_type') or '[MECANISMO]'
    title = {
        'Producto o servicio defectuoso': 'Reclamación de garantía legal',
        'Me arrepentí de compra a distancia': 'Ejercicio de retracto',
        'Compra electrónica no solicitada': 'Solicitud de reversión por operación no solicitada',
        'No entregaron': 'Reclamación por incumplimiento de entrega y devolución',
        'Producto distinto': 'Reclamación por producto distinto y reversión cuando proceda',
        'Débito periódico que quiero cesar': 'Revocación de débito periódico y reversión aplicable',
    }.get(mechanism, 'Reclamación directa de protección al consumidor')
    return [
        {'heading': '1. Clasificación preliminar', 'text': f"Documento: {title}. Consumidor: {a.get('consumer_name') or '[CONSUMIDOR]'}. Proveedor/productor: {a.get('provider') or '[PROVEEDOR]'}."},
        {'heading': '2. Operación', 'table': [('Campo', 'Información'), ('Canal', a.get('channel') or 'Pendiente'), ('Fecha de compra', a.get('purchase_date') or 'Pendiente'), ('Mecanismo', mechanism), ('Pago electrónico', a.get('electronic_payment') or 'Pendiente'), ('Días hábiles aproximados', str(a.get('days_since') or 'Pendiente'))]},
        {'heading': '3. Hechos', 'bullets': ['Identificar bien, servicio, pedido, factura o suscripción.', 'Precisar entrega, falla, arrepentimiento, operación no solicitada o débito.', 'Relacionar comunicaciones, reparaciones, devoluciones y respuestas.', 'Conservar producto y evidencia cuando sea razonable y seguro.']},
        {'heading': '4. Solicitudes compatibles', 'bullets': [
            'Garantía: reparación, repetición, cambio o devolución según el supuesto probado.',
            'Retracto: resolución y devolución cuando el canal, producto y término lo permitan.',
            'Reversión: actuación coordinada frente a proveedor y emisor cuando exista compra electrónica y causal legal.',
            'Débito periódico: revocación de autorización, cesación y reversión de cargos que procedan.',
            'Incumplimiento de entrega: terminación, entrega o devolución según contrato y régimen aplicable.',
        ]},
        {'heading': '5. Pruebas y datos', 'bullets': ['Factura, pedido, contrato o soporte equivalente.', 'Comprobante de pago y canal de compra.', 'Fotografías, videos, diagnósticos o constancias de reparación.', 'Queja previa, número de radicado y respuesta.', 'No incluir datos completos de tarjeta ni credenciales.']},
        {'heading': '6. Control previo', 'bullets': ['Verificar mecanismo y término antes de radicar.', 'No mezclar garantía, retracto y reversión como si fueran equivalentes.', 'Lesiones, productos peligrosos, servicios regulados, fraude complejo o procesos activos exigen escalamiento.']},
    ]


def consumer_calendar_sections(a):
    return [
        {'heading': '1. Hitos a controlar', 'table': [('Hito', 'Fecha / estado'), ('Compra', a.get('purchase_date') or 'Pendiente'), ('Entrega o conocimiento', '[...]'), ('Queja al proveedor', '[...]'), ('Notificación al emisor', '[...]'), ('Respuesta', '[...]'), ('Escalamiento', '[...]')]},
        {'heading': '2. Regla operativa', 'text': 'Los términos dependen del mecanismo, canal, evento y normativa vigente. La aplicación debe calcularlos desde fechas confirmadas y mantener la fuente y versión utilizadas.'},
    ]




def _consumer_calc(result):
    return (result or {}).get('calculation') or {}


def _consumer_identity_table(a):
    return [
        ('Consumidor', a.get('consumer_name') or '[CONSUMIDOR]'),
        ('Identificación', a.get('consumer_id') or '[IDENTIFICACIÓN]'),
        ('Calidad', a.get('acting_capacity') or 'Pendiente'),
        ('Proveedor / productor', a.get('provider_name') or '[PROVEEDOR]'),
        ('Pedido, factura o contrato', a.get('order_or_contract') or 'Pendiente'),
        ('Ciudad', a.get('city') or 'Pendiente'),
        ('Correo', a.get('email') or 'Pendiente'),
    ]


def consumer_mechanism_diagnosis_v233_sections(a, result):
    c=_consumer_calc(result)
    flags=c.get('mechanism_eligibility') or {}
    return [
        {'heading':'1. Identificación de la relación de consumo','table':[('Campo','Información')]+_consumer_identity_table(a),'text':f"Bien o servicio: {a.get('product_description') or 'Pendiente'}. Valor informado: {cop(a.get('purchase_value'))}. Canal: {a.get('purchase_channel') or 'Pendiente'}."},
        {'heading':'2. Hechos confirmados','text':a.get('facts_detail') or '[RELATO PENDIENTE]','bullets':[f"Problema: {a.get('problem_type') or 'Pendiente'}.",f"Defecto o incumplimiento: {a.get('defect_detail') or 'Pendiente'}.",f"Objetivo: {a.get('claim_goal') or 'Pendiente'}."]},
        {'heading':'3. Clasificación del mecanismo','table':[('Mecanismo','Elegibilidad preliminar'),('Garantía legal','Sí' if flags.get('warranty') else 'No confirmada'),('Retracto','Sí' if flags.get('withdrawal') else 'No confirmada'),('Reversión del pago','Sí' if flags.get('reversal') else 'No confirmada'),('Revocación de débito periódico','Sí' if flags.get('periodic_debit') else 'No confirmada'),('Terminación por falta de entrega','Sí' if flags.get('non_delivery') else 'No confirmada')],'text':f"Mecanismo seleccionado: {a.get('request_mode') or 'No definido'}. Los mecanismos no son equivalentes ni se acumulan automáticamente."},
        {'heading':'4. Cronología y términos preliminares','table':[('Hito','Fecha'),('Compra',c.get('purchase_date') or 'Pendiente'),('Entrega / fecha esperada',c.get('delivery_date') or 'Pendiente'),('Reclamación directa',c.get('direct_claim_date') or 'Pendiente'),('Vencimiento preliminar de respuesta',c.get('direct_claim_due_date') or 'Pendiente'),('Límite preliminar de retracto',c.get('withdrawal_due_date') or 'No aplica'),('Límite preliminar de reversión',c.get('reversal_request_due_date') or 'No aplica'),('Ejecución preliminar de reversión',c.get('reversal_effective_due_date') or 'No aplica')],'text':'Los cálculos excluyen fines de semana, pero no festivos, traslados, interrupciones ni normas especiales.'},
        {'heading':'5. Pretensiones compatibles','bullets':['Garantía: reparación gratuita o repetición del servicio; cambio o devolución cuando el supuesto legal esté acreditado.','Retracto: resolución y reembolso si el canal, el término y las excepciones lo permiten.','Reversión: coordinación simultánea con proveedor y emisor por una causal legal y dentro del término.','Débito periódico: revocación de la instrucción y control de cargos posteriores.','Falta de entrega: entrega, terminación y devolución según el régimen y la cronología probada.']},
        {'heading':'6. Alertas, exclusiones y evidencia','bullets':[x.get('message') for x in c.get('issues',[])] or ['No se identificaron alertas dinámicas adicionales con los datos aportados.'],'text':f"Estado probatorio: {a.get('evidence_status') or 'Pendiente'}. Régimen sectorial: {a.get('regulated_sector') or 'Pendiente'}. Lesión o seguridad: {a.get('injury_or_safety') or 'Pendiente'}."},
        {'heading':'7. Ruta recomendada y control de uso','bullets':['Confirmar destinatarios, legitimación, fechas, valor, causal y soportes.','Elegir un mecanismo principal y formular pretensiones compatibles.','Radicar por canal verificable y conservar copia íntegra con anexos.','No incluir números completos de tarjeta, claves, CVV o credenciales.','No usar como versión profesional hasta aprobación jurídica y QA dual sobre este documento exacto.']},
    ]


def warranty_claim_v233_sections(a, result):
    c=_consumer_calc(result)
    repeated=a.get('repeated_failure')
    return [
        {'heading':'1. Destinatario, consumidor y operación','table':[('Campo','Información')]+_consumer_identity_table(a)+[('Fecha de compra',a.get('purchase_date') or 'Pendiente'),('Fecha de entrega',a.get('delivery_date') or 'Pendiente'),('Valor',cop(a.get('purchase_value')))]},
        {'heading':'2. Objeto de la reclamación','text':f"Presento reclamación directa para hacer efectiva la garantía legal respecto de {a.get('product_description') or '[BIEN O SERVICIO]'}, por el defecto o incumplimiento siguiente: {a.get('defect_detail') or '[DETALLE]'}"},
        {'heading':'3. Hechos','text':a.get('facts_detail') or '[HECHOS PENDIENTES]','bullets':[f"Garantía anunciada: {a.get('warranty_announced') or 'Pendiente'}.",f"Falla repetida después de reparación: {repeated or 'Pendiente'}.",f"Respuesta recibida: {a.get('response_received') or 'Pendiente'}."]},
        {'heading':'4. Fundamentos y alcance de la garantía','bullets':['La garantía legal protege calidad, idoneidad, seguridad y buen funcionamiento en los términos aplicables.','La efectividad debe ser gratuita y comprende los costos necesarios cuando proceda.','La reparación es la respuesta inicial ordinaria; la repetición de la falla puede habilitar elección entre nueva reparación, cambio o devolución, según la naturaleza del bien y el supuesto probado.','La expiración de una garantía anunciada no autoriza conclusiones automáticas sin revisar garantía legal, información suministrada, vida útil y prueba del defecto.']},
        {'heading':'5. Pretensiones','bullets':[f"Pretensión principal: {a.get('claim_goal') or 'Pendiente'}.",'Emitir respuesta escrita, completa, congruente y motivada.','Informar procedimiento, lugar, plazo, responsable y constancia de recepción del bien o servicio.','Asumir transporte, repuestos, diagnóstico y demás costos que legalmente correspondan.','Conservar y entregar trazabilidad de ingreso, intervención, diagnóstico, pruebas y decisión.']},
        {'heading':'6. Entrega, custodia y seguridad','bullets':[f"Estado de devolución o puesta a disposición: {a.get('return_status') or 'Pendiente'}.",'La recepción debe documentar serial, accesorios, estado aparente y fecha.','No debe exigirse una renuncia general de derechos ni cobros incompatibles con la garantía.','Si existe riesgo de seguridad o lesión, suspender el uso razonablemente y escalar de inmediato.']},
        {'heading':'7. Pruebas y notificaciones','bullets':['Factura, pedido, contrato o soporte de la relación de consumo.','Fotografías, videos, diagnósticos y constancias de falla.','Órdenes de reparación, ingresos previos y respuestas.','Comprobante de radicación y anexos remitidos.'],'text':f"Vencimiento preliminar de respuesta: {c.get('direct_claim_due_date') or 'Pendiente, sujeto a radicación efectiva y calendario aplicable'}."},
        {'heading':'8. Reserva y control de uso','bullets':['Se reservan las acciones administrativas y jurisdiccionales procedentes.','La reclamación no admite hechos, defectos o reparaciones no acreditados.','Revisar regímenes especiales, procesos activos y alta cuantía antes de radicar.','Borrador interno sujeto a aprobación jurídica y QA dual.']},
    ]


def withdrawal_notice_v233_sections(a, result):
    c=_consumer_calc(result)
    return [
        {'heading':'1. Destinatario y contrato','table':[('Campo','Información')]+_consumer_identity_table(a)+[('Canal',a.get('purchase_channel') or 'Pendiente'),('Compra',a.get('purchase_date') or 'Pendiente'),('Entrega',a.get('delivery_date') or 'Pendiente')]},
        {'heading':'2. Declaración expresa','text':f"Por medio de la presente ejerzo el derecho de retracto respecto de {a.get('product_description') or '[BIEN O SERVICIO]'} y solicito la resolución de la operación y la devolución de {cop(a.get('purchase_value'))}, sujeto a la verificación de procedencia legal."},
        {'heading':'3. Canal, término y excepciones','table':[('Control','Resultado'),('Fecha de ejercicio',a.get('withdrawal_exercised_date') or 'Pendiente'),('Límite preliminar',c.get('withdrawal_due_date') or 'Pendiente'),('Dentro del término preliminar','Sí' if c.get('withdrawal_in_time_preliminary') else 'No confirmado'),('Excepción declarada',a.get('withdrawal_exception') or 'Pendiente'),('Servicio iniciado con consentimiento',a.get('service_started_with_consent') or 'No aplica')],'text':'La procedencia depende del tipo de venta, naturaleza del bien o servicio y excepciones legales.'},
        {'heading':'4. Devolución o puesta a disposición','bullets':[f"Estado informado: {a.get('return_status') or 'Pendiente'}.",'Coordinar lugar, fecha, persona y constancia de entrega.','Conservar el bien en condiciones razonables y entregar accesorios recibidos, salvo imposibilidad justificada.','No enviar bienes inseguros sin instrucciones de manejo.']},
        {'heading':'5. Reembolso','bullets':['Devolver las sumas pagadas por el mismo medio o por el mecanismo legalmente procedente.','No imponer retenciones o descuentos sin fundamento verificable.','Informar por escrito la fecha y trazabilidad del reembolso.'],'text':f"Fecha preliminar máxima de reembolso configurada: {c.get('withdrawal_refund_due_date') or 'Pendiente'}."},
        {'heading':'6. Anexos y notificaciones','bullets':['Factura, pedido o contrato.','Prueba del canal de compra y fecha de entrega.','Comunicación de retracto y constancia de recepción.','Prueba de devolución o puesta a disposición.','Comprobante de pago con datos sensibles minimizados.']},
        {'heading':'7. Control de uso','bullets':['No confundir retracto con garantía por defecto ni con reversión del pago.','Confirmar que no opere una excepción legal.','La cronología debe verificarse con días festivos y recepción efectiva.','Borrador interno sujeto a aprobación jurídica y QA dual.']},
    ]


def payment_reversal_v233_sections(a, result):
    c=_consumer_calc(result)
    return [
        {'heading':'1. Destinatarios y legitimación','text':f"Dirigido simultáneamente a {a.get('provider_name') or '[PROVEEDOR]'} y al emisor o participante del instrumento de pago que corresponda.",'table':[('Campo','Información')]+_consumer_identity_table(a)},
        {'heading':'2. Compra y transacción','table':[('Concepto','Información'),('Bien o servicio',a.get('product_description') or 'Pendiente'),('Valor de compra',cop(a.get('purchase_value'))),('Valor solicitado',cop(a.get('reversal_amount'))),('Instrumento',a.get('payment_instrument') or 'Pendiente'),('Referencia parcial',a.get('transaction_reference') or 'Pendiente'),('Fecha',a.get('transaction_date') or 'Pendiente'),('Reversión parcial',a.get('partial_reversal') or 'No')]},
        {'heading':'3. Causal legal alegada','text':f"Causal informada: {a.get('reversal_cause') or 'Pendiente'}. Problema: {a.get('problem_type') or 'Pendiente'}.",'bullets':['La causal debe corresponder a fraude, operación no solicitada, producto no recibido, producto distinto o defectuoso, u otro supuesto legal aplicable.','El documento no declara probada la causal; solicita su trámite con base en los soportes anexos.']},
        {'heading':'4. Queja al proveedor y notificación al emisor','table':[('Actuación','Estado / fecha'),('Queja al proveedor',a.get('provider_complaint_for_reversal') or 'Pendiente'),('Reclamación directa',a.get('prior_claim_date') or 'Pendiente'),('Notificación al emisor',a.get('issuer_notification') or 'Pendiente'),('Fecha al emisor',a.get('issuer_notification_date') or 'Pendiente'),('Límite preliminar',c.get('reversal_request_due_date') or 'Pendiente'),('Dentro del término preliminar','Sí' if c.get('reversal_in_time_preliminary') else 'No confirmado')]},
        {'heading':'5. Solicitudes coordinadas','bullets':['Registrar la solicitud y asignar radicado.','Reversar total o parcialmente el valor identificado cuando se verifiquen los requisitos.','Abstenerse de cerrar unilateralmente la actuación sin respuesta motivada.','Informar participantes, movimientos, fechas, objeciones y resultado.','Preservar la trazabilidad de la operación y de la reversión.']},
        {'heading':'6. Devolución y controversia posterior','bullets':[f"Estado del bien: {a.get('return_status') or 'Pendiente'}.",'Cuando corresponda, el consumidor manifiesta disponibilidad para devolver o poner a disposición el bien.','La reversión no decide definitivamente controversias sobre responsabilidad ni impide los mecanismos posteriores de las partes.'],'text':f"Fecha preliminar de ejecución: {c.get('reversal_effective_due_date') or 'Pendiente, condicionada a notificación completa'}."},
        {'heading':'7. Anexos y seguridad','bullets':['Factura, pedido y evidencia del canal electrónico.','Comprobante de pago con únicamente referencia parcial.','Queja al proveedor y constancia de recepción.','Notificación al emisor y radicado.','Prueba de causal, no entrega, diferencia o defecto.','No anexar CVV, claves, contraseñas ni número completo de tarjeta.']},
        {'heading':'8. Reserva y control de uso','bullets':['Verificar régimen sectorial y proveedor en el exterior.','Fraude complejo o suplantación requiere preservación adicional y revisión profesional.','No mezclar la reversión con el retracto o la garantía sin clasificar cada pretensión.','Borrador interno sujeto a aprobación jurídica y QA dual.']},
    ]


def recurring_debit_v233_sections(a, result):
    c=_consumer_calc(result)
    return [
        {'heading':'1. Identificación de la instrucción periódica','table':[('Campo','Información')]+_consumer_identity_table(a)+[('Producto / suscripción',a.get('product_description') or 'Pendiente'),('Instrumento',a.get('payment_instrument') or 'Pendiente'),('Referencia parcial',a.get('transaction_reference') or 'Pendiente')]},
        {'heading':'2. Revocación expresa','text':f"Revoco la autorización o instrucción de débito periódico asociada a la operación identificada y solicito cesar nuevos cargos desde la fecha comunicada: {a.get('recurring_debit_revoked_date') or 'Pendiente'}."},
        {'heading':'3. Cargos controvertidos','table':[('Campo','Información'),('Último cargo',a.get('latest_periodic_charge_date') or 'Pendiente'),('Valor controvertido',cop(a.get('reversal_amount') or a.get('purchase_value'))),('Causal',a.get('reversal_cause') or 'Pago periódico'),('Control preliminar',c.get('periodic_debit_control_due_date') or 'Pendiente')]},
        {'heading':'4. Solicitudes','bullets':['Confirmar recepción y fecha efectiva de revocación.','Impedir nuevos cargos bajo la instrucción revocada.','Revisar y tramitar los cargos posteriores o controvertidos conforme al régimen aplicable.','Informar estado, participantes y soportes de cada cargo.','Entregar constancia de cancelación o modificación de la instrucción.']},
        {'heading':'5. Coordinación con proveedor y emisor','bullets':['Remitir la comunicación a ambos destinatarios cuando intervengan proveedor y emisor.','Diferenciar cancelación del servicio, revocación del débito y reversión de cargos.','Conservar radicados, extractos y comunicaciones.']},
        {'heading':'6. Evidencia y privacidad','bullets':['Contrato o aceptación de la suscripción.','Constancia de cancelación o revocación.','Extractos con datos innecesarios ocultos.','Identificación de cargos por fecha, valor y referencia parcial.','No compartir credenciales ni números completos del instrumento.']},
        {'heading':'7. Control de uso','bullets':['Verificar si existen obligaciones contractuales distintas del mecanismo de pago.','No asumir que la revocación extingue automáticamente deudas válidas.','Escalar fraude complejo, múltiples cargos o procesos activos.','Borrador interno sujeto a aprobación jurídica y QA dual.']},
    ]


def ecommerce_non_delivery_v233_sections(a, result):
    c=_consumer_calc(result)
    return [
        {'heading':'1. Operación de comercio electrónico','table':[('Campo','Información')]+_consumer_identity_table(a)+[('Canal',a.get('purchase_channel') or 'Pendiente'),('Compra',a.get('purchase_date') or 'Pendiente'),('Entrega pactada / esperada',a.get('delivery_date') or 'Pendiente'),('Límite supletivo preliminar',c.get('default_ecommerce_delivery_due_date') or 'Pendiente')]},
        {'heading':'2. Incumplimiento alegado','text':a.get('facts_detail') or '[HECHOS PENDIENTES]','bullets':[f"Problema: {a.get('problem_type') or 'Producto no recibido'}.",f"Producto o servicio: {a.get('product_description') or 'Pendiente'}.",f"Valor: {cop(a.get('purchase_value'))}."]},
        {'heading':'3. Declaración de terminación o requerimiento','text':'Con fundamento en la falta de entrega informada, se solicita ejecutar la opción indicada por el consumidor: entrega inmediata y verificable, o terminación de la operación con devolución integral de las sumas pagadas, según proceda.'},
        {'heading':'4. Solicitudes','bullets':[f"Resultado principal: {a.get('claim_goal') or 'Terminación del contrato'}.",'Confirmar el estado real del pedido y la causa del incumplimiento.','Indicar fecha cierta y verificable de entrega si el consumidor conserva interés.','Cuando corresponda, terminar la operación y devolver las sumas pagadas.','Informar el trámite de reversión si el pago electrónico y la causal lo permiten.']},
        {'heading':'5. Reembolso y trazabilidad','table':[('Hito','Fecha'),('Reclamación directa',a.get('prior_claim_date') or 'Pendiente'),('Respuesta preliminar',c.get('direct_claim_due_date') or 'Pendiente'),('Devolución preliminar',c.get('ecommerce_refund_due_date') or 'Pendiente')],'text':'Las fechas son preliminares y dependen de recepción, acuerdo de entrega, hechos y norma especial.'},
        {'heading':'6. Pruebas','bullets':['Pedido, factura o confirmación de compra.','Oferta, publicidad y plazo informado.','Comprobante de pago.','Seguimiento logístico, comunicaciones y radicados.','Prueba de que el producto no fue recibido.']},
        {'heading':'7. Control de uso','bullets':['Diferenciar falta de entrega, retraso pactado, pérdida logística y producto recibido por tercero.','No afirmar fraude sin evidencia.','Verificar proveedor en el exterior y régimen especial.','Borrador interno sujeto a aprobación jurídica y QA dual.']},
    ]


def consumer_evidence_matrix_v233_sections(a, result):
    return [
        {'heading':'1. Identificación del expediente','table':[('Campo','Información')]+_consumer_identity_table(a)+[('Mecanismo',a.get('request_mode') or 'Pendiente'),('Objetivo',a.get('claim_goal') or 'Pendiente')]},
        {'heading':'2. Matriz de hechos y prueba','table':[('Hecho a probar','Soporte esperado'),('Relación de consumo','Factura, pedido, contrato o equivalente'),('Canal y fecha','Confirmación, metadatos y comunicaciones'),('Pago','Comprobante con datos minimizados'),('Defecto o diferencia','Fotos, videos, diagnóstico, serial o actas'),('No entrega','Seguimiento, recepción y comunicaciones'),('Queja y notificación','Radicados y constancias'),('Devolución','Guía, acta o puesta a disposición')]},
        {'heading':'3. Destinatarios y pretensiones','table':[('Destinatario','Actuación'),(a.get('provider_name') or 'Proveedor','Reclamación directa, garantía, retracto o queja de reversión'),('Emisor del instrumento','Notificación y trámite de reversión cuando proceda'),('Autoridad competente','Escalamiento condicionado a competencia y agotamiento')]},
        {'heading':'4. Cronología','table':[('Hito','Fecha'),('Compra',a.get('purchase_date') or 'Pendiente'),('Entrega / esperada',a.get('delivery_date') or 'Pendiente'),('Evento de reversión',a.get('reversal_event_date') or 'Pendiente'),('Reclamación',a.get('prior_claim_date') or 'Pendiente'),('Notificación al emisor',a.get('issuer_notification_date') or 'Pendiente'),('Respuesta',a.get('response_date') or 'Pendiente')]},
        {'heading':'5. Custodia y autenticidad','bullets':['Conservar archivos originales y copias de trabajo diferenciadas.','Registrar origen, fecha, autor y método de obtención.','No editar capturas de manera que altere su significado.','Conservar encabezados, correos completos y metadatos pertinentes.']},
        {'heading':'6. Privacidad y minimización','bullets':['Ocultar números completos de instrumentos, CVV, claves y saldos ajenos al caso.','Compartir solo datos necesarios con cada destinatario.','Aplicar canal seguro a identificación y soportes financieros.','Documentar autorizaciones de representantes o terceros.']},
        {'heading':'7. Control final','bullets':[f"Evidencia declarada: {a.get('evidence_status') or 'Pendiente'}.",f"Datos minimizados: {a.get('data_minimized') or 'Pendiente'}.",'Conciliar fechas y valores antes de radicar.','Numerar anexos y referenciarlos dentro del escrito.','No publicar profesionalmente sin aprobación jurídica y QA dual.']},
    ]


def consumer_deadline_calendar_v233_sections(a, result):
    c=_consumer_calc(result)
    return [
        {'heading':'1. Alcance del calendario','text':'Calendario preliminar para organizar la actuación. Excluye festivos en los cálculos hábiles y no sustituye el cotejo de la norma, la recepción efectiva, la completitud ni el régimen sectorial.'},
        {'heading':'2. Reclamación directa','table':[('Hito','Fecha'),('Radicación',c.get('direct_claim_date') or 'Pendiente'),('Respuesta preliminar',c.get('direct_claim_due_date') or 'Pendiente'),('Días hábiles configurados',str(c.get('direct_claim_business_days') or 15)),('Respuesta recibida',a.get('response_date') or 'No informada')]},
        {'heading':'3. Retracto','table':[('Hito','Fecha / estado'),('Compra',c.get('purchase_date') or 'Pendiente'),('Entrega',c.get('delivery_date') or 'Pendiente'),('Límite preliminar',c.get('withdrawal_due_date') or 'No aplica'),('Ejercicio',c.get('withdrawal_exercised_date') or 'No informado'),('Dentro de término preliminar','Sí' if c.get('withdrawal_in_time_preliminary') else 'No confirmado'),('Reembolso preliminar',c.get('withdrawal_refund_due_date') or 'No aplica')]},
        {'heading':'4. Reversión del pago','table':[('Hito','Fecha / estado'),('Conocimiento de causal',c.get('reversal_event_date') or 'Pendiente'),('Límite de solicitud',c.get('reversal_request_due_date') or 'Pendiente'),('Notificación al emisor',c.get('issuer_notification_date') or 'No informada'),('Dentro de término preliminar','Sí' if c.get('reversal_in_time_preliminary') else 'No confirmado'),('Ejecución preliminar',c.get('reversal_effective_due_date') or 'Pendiente')]},
        {'heading':'5. Comercio electrónico y falta de entrega','table':[('Hito','Fecha'),('Compra',c.get('purchase_date') or 'Pendiente'),('Entrega supletiva preliminar',c.get('default_ecommerce_delivery_due_date') or 'Pendiente'),('Reembolso preliminar',c.get('ecommerce_refund_due_date') or 'Pendiente')]},
        {'heading':'6. Débito periódico','table':[('Hito','Fecha'),('Revocación',a.get('recurring_debit_revoked_date') or 'Pendiente'),('Último cargo',a.get('latest_periodic_charge_date') or 'Pendiente'),('Control preliminar',c.get('periodic_debit_control_due_date') or 'Pendiente')]},
        {'heading':'7. Alertas dinámicas','bullets':[x.get('message') for x in c.get('issues',[])] or ['No se identificaron alertas dinámicas adicionales.']},
        {'heading':'8. Seguimiento y control','bullets':['Registrar cada radicado, destinatario, fecha, contenido y anexos.','Programar verificación antes y después de cada vencimiento.','Actualizar el calendario cuando exista respuesta, traslado, requerimiento o acuerdo.','No tratar las fechas como definitivas sin verificar festivos y norma vigente.','Escalar procesos activos, fraude complejo, lesiones o regímenes especiales.']},
    ]


def _collection_calc(result):
    return (result or {}).get('calculation') or {}


def _collection_identity_table(a):
    return [
        ('Acreedor', a.get('creditor_name') or 'Pendiente de confirmación'),
        ('Identificación del acreedor', a.get('creditor_id') or 'Pendiente de confirmación'),
        ('Representante', a.get('creditor_representative') or 'No informado'),
        ('Deudor', a.get('debtor_name') or 'Pendiente de confirmación'),
        ('Identificación del deudor', a.get('debtor_id') or 'Pendiente de confirmación'),
        ('Documento / referencia', a.get('document_reference') or 'Pendiente de confirmación'),
    ]


def debt_diagnostic_v234_sections(a, result):
    c = _collection_calc(result)
    return [
        {'heading':'1. Partes y legitimación','table':[('Campo','Información')]+_collection_identity_table(a)+[('Facultad del acreedor',a.get('creditor_authority') or 'Pendiente')]},
        {'heading':'2. Negocio causal y soporte','table':[('Campo','Información'),('Naturaleza',a.get('obligation_type') or 'Pendiente'),('Documento principal',a.get('source_document_type') or 'Pendiente'),('Fecha del documento',a.get('document_date') or 'Pendiente'),('Origen',a.get('origin_description') or 'Pendiente')]},
        {'heading':'3. Exigibilidad preliminar','table':[('Control','Resultado'),('Estado',a.get('obligation_status') or 'Pendiente'),('Vencimiento',a.get('due_date') or 'Pendiente'),('Expresa, clara y exigible',a.get('express_clear_enforceable') or 'Pendiente'),('Firma o aceptación',a.get('debtor_signature_status') or 'Pendiente'),('Integridad u original',a.get('original_integrity_status') or 'Pendiente')]},
        {'heading':'4. Factura, cesión y RADIAN','table':[('Control','Resultado'),('Aceptación de factura',a.get('invoice_acceptance_status') or 'No aplica'),('RADIAN',a.get('radian_status') or 'No aplica'),('Cesión, endoso o factoring',a.get('assignment_factoring') or 'No')]},
        {'heading':'5. Saldo e intereses','table':[('Concepto','Valor'),('Capital',cop(c.get('principal'))),('Abonos',cop(c.get('partial_payments_total'))),('Cargos adicionales',cop(c.get('other_charges'))),('Saldo explicado',cop(c.get('explained_balance'))),('Saldo pretendido',cop(c.get('reported_balance'))),('Diferencia',cop(c.get('balance_difference'))),('Modalidad',c.get('interest_modality') or 'No definida'),('Tasa equivalente E.A.',f"{c.get('effective_annual_rate',0):.4f}%"),('IBC vigente',f"{c.get('interest_banking_current_ea',0):.2f}% E.A."),('Límite de referencia',f"{c.get('maximum_reference_ea',0):.2f}% E.A.")]},
        {'heading':'6. Controversias y bloqueos','table':[('Control','Respuesta'),('Controversia',a.get('disputed') or 'Pendiente'),('Compensación',a.get('setoff_claimed') or 'Pendiente'),('Prescripción',a.get('prescription_concern') or 'Pendiente'),('Proceso activo',a.get('judicial_process_active') or 'Pendiente'),('Insolvencia',a.get('insolvency_active') or 'Pendiente'),('Medida cautelar',a.get('embargo_or_measure') or 'Pendiente')]},
        {'heading':'7. Ruta recomendada','bullets':[f"Etapa seleccionada: {a.get('package_stage') or 'Pendiente'}.",f"Objetivo: {a.get('settlement_goal') or 'Pendiente'}.",f"Riesgo calculado: {(result or {}).get('risk','Pendiente').upper()}.",f"Salida: {(result or {}).get('route','Pendiente')}."]},
        {'heading':'8. Alertas dinámicas','bullets':[x.get('message') for x in c.get('issues',[])] or ['No se identificaron alertas calculadas adicionales.']},
        {'heading':'9. Control de uso','bullets':['Este diagnóstico no declara definitivamente mérito ejecutivo, prescripción, titularidad ni procedencia de intereses.','Revalidar tasa, SMLMV, insolvencia, medidas, competencia y estado del título al día de uso.','No usar para amenazas, hostigamiento, divulgación a terceros o cobro de valores no soportados.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def account_statement_v234_sections(a, result):
    c = _collection_calc(result)
    return [
        {'heading':'1. Identificación del estado','table':[('Campo','Información')]+_collection_identity_table(a)+[('Fecha de corte',c.get('reference_date') or 'Pendiente')]},
        {'heading':'2. Capital y movimientos','table':[('Concepto','Valor'),('Capital original',cop(c.get('principal'))),('Abonos, notas crédito o compensaciones',cop(c.get('partial_payments_total'))),('Capital pendiente preliminar',cop(c.get('expected_principal_balance'))),('Otros cargos informados',cop(c.get('other_charges')))]},
        {'heading':'3. Intereses','table':[('Campo','Información'),('Pacto de intereses',a.get('interest_agreed') or 'Pendiente'),('Clase',a.get('interest_type') or 'Pendiente'),('Tasa informada',f"{a.get('interest_rate') or 0}%"),('Periodicidad',a.get('interest_period') or 'Pendiente'),('Modalidad',c.get('interest_modality') or 'No definida'),('Equivalente preliminar',f"{c.get('effective_annual_rate',0):.4f}% E.A."),('IBC vigente',f"{c.get('interest_banking_current_ea',0):.2f}% E.A."),('Límite configurado',f"{c.get('maximum_reference_ea',0):.2f}% E.A."),('Vigencia del parámetro',f"{c.get('interest_valid_from') or 'Pendiente'} a {c.get('interest_valid_to') or 'Pendiente'}"),('Resolución',c.get('interest_resolution') or 'Revalidación pendiente'),('Interés causado preliminar',cop((c.get('accrued_interest_preliminary') or {}).get('interest')) if (c.get('accrued_interest_preliminary') or {}).get('calculable') else 'No calculable')]},
        {'heading':'4. Conciliación del saldo','table':[('Campo','Valor'),('Saldo explicado',cop(c.get('explained_balance'))),('Saldo pretendido',cop(c.get('reported_balance'))),('Diferencia por conciliar',cop(c.get('balance_difference'))),('Conciliación automática','Conciliado' if c.get('balance_reconciled') else 'Requiere conciliación'),('Conciliación declarada',a.get('balance_reconciled') or 'Pendiente')]},
        {'heading':'5. Soportes mínimos','bullets':['Documento que origina la obligación y anexos.','Comprobantes de entrega, prestación o desembolso.','Relación cronológica de facturas, notas, abonos y recibos.','Pacto de intereses y certificación vigente aplicable.','Cadena de titularidad cuando hubo cesión, endoso o factoring.']},
        {'heading':'6. Aprobación del estado','text':'El saldo solo debe presentarse como definitivo cuando capital, abonos, cargos, tasa, periodo y titularidad estén conciliados con soportes verificables.'},
        {'heading':'7. Control de uso','bullets':['Este documento no incluye intereses históricos no calculados con fechas y bases verificadas.','No duplicar capital, intereses, cláusulas penales, honorarios o gastos.','Actualizar después de cada pago, nota crédito, acuerdo o decisión.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def collection_letter_v234_sections(a, result):
    c = _collection_calc(result)
    return [
        {'heading':'1. Destinatario','table':[('Campo','Información'),('Deudor',a.get('debtor_name') or 'Pendiente'),('Identificación',a.get('debtor_id') or 'Pendiente'),('Canal autorizado',a.get('debtor_email') or 'Pendiente')]},
        {'heading':'2. Acreedor y obligación','table':[('Campo','Información'),('Acreedor',a.get('creditor_name') or 'Pendiente'),('Documento',a.get('document_reference') or 'Pendiente'),('Origen',a.get('origin_description') or 'Pendiente'),('Vencimiento',a.get('due_date') or 'Pendiente')]},
        {'heading':'3. Estado de cuenta','table':[('Concepto','Valor'),('Capital',cop(c.get('principal'))),('Abonos',cop(c.get('partial_payments_total'))),('Otros cargos',cop(c.get('other_charges'))),('Saldo pretendido',cop(c.get('reported_balance')))]},
        {'heading':'4. Requerimiento respetuoso','text':'Se solicita revisar la información anterior y, si coincide con sus soportes, efectuar el pago o proponer una alternativa de solución. Si existe desacuerdo, se solicita identificar de forma concreta el hecho, valor o soporte controvertido para conciliar el estado de cuenta.'},
        {'heading':'5. Alternativas de solución','bullets':['Pago único por el canal identificado.','Propuesta de acuerdo por cuotas, sujeta a aceptación expresa.','Conciliación de abonos, notas crédito o compensaciones.','Entrega de soportes cuando se controvierta existencia, monto, titularidad o exigibilidad.']},
        {'heading':'6. Canales, horarios y privacidad','bullets':['Usar únicamente canales autorizados por el consumidor.','No efectuar más de un contacto directo en el mismo día ni varios canales en una misma semana después del contacto directo.','Contactar de lunes a viernes entre 7:00 a. m. y 7:00 p. m., y sábados entre 8:00 a. m. y 3:00 p. m., salvo autorización posterior válida.','No contactar referencias, familiares o terceros no obligados.','No divulgar la deuda ni incorporar datos innecesarios.']},
        {'heading':'7. Reporte a operadores de información','text':f"Cualquier reporte negativo exige comunicación previa y espera legal. Umbral de baja cuantía configurado: {cop(c.get('low_value_report_threshold'))}. Fecha preliminar más temprana según último aviso: {c.get('report_earliest_date_preliminary') or 'No aplica'}."},
        {'heading':'8. Anexos','bullets':['Estado de cuenta conciliable.','Copia o extracto pertinente del soporte de la obligación.','Relación de abonos y cargos.','Canales para respuesta y pago.']},
        {'heading':'9. Control de uso','bullets':['No afirmar mérito ejecutivo, fraude, sanciones o reporte inminente sin soporte.','No usar lenguaje intimidatorio ni aparentar autoridad judicial.','Revalidar tasa y situación procesal antes de enviar.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def payment_agreement_v234_sections(a, result):
    c = _collection_calc(result)
    return [
        {'heading':'1. Partes','table':[('Campo','Información')]+_collection_identity_table(a)},
        {'heading':'2. Antecedentes y alcance','text':a.get('origin_description') or 'Pendiente','bullets':['El acuerdo se basa en la información y soportes anexos.','El reconocimiento se limita al valor conciliado y no cubre cobros no descritos.','Las partes declaran su capacidad y facultad de obligarse.']},
        {'heading':'3. Valor acordado','table':[('Campo','Información'),('Capital y saldo de referencia',cop(c.get('reported_balance'))),('Valor total del acuerdo',cop(c.get('agreement_total'))),('Número de cuotas',str(c.get('installments') or 1)),('Cuota ordinaria',cop(c.get('installment_value_preliminary'))),('Última cuota ajustada',cop(c.get('last_installment_value'))),('Conciliación del plan','Exacta' if (c.get('payment_schedule') or {}).get('reconciled') else 'Requiere revisión'),('Periodicidad',a.get('frequency') or 'Pendiente'),('Primera cuota',a.get('first_payment_date') or 'Pendiente')]},
        {'heading':'4. Imputación y pagos','bullets':['Cada pago se imputará según pacto válido y constancia emitida.','Los abonos deben registrarse con fecha, valor, medio, referencia y saldo.','Los pagos anticipados se aplicarán sin cobros no pactados.','El canal de pago es: '+str(a.get('payment_channel') or 'Pendiente')+'.']},
        {'heading':'5. Mora y cláusula aceleratoria','text':f"Días de gracia: {a.get('grace_days') or 0}. Cláusula aceleratoria: {a.get('acceleration_clause') or 'No'}. Cualquier aceleración debe ser expresa, proporcional, compatible con la ley y sustentada en un incumplimiento verificable."},
        {'heading':'6. Intereses y cargos','table':[('Campo','Información'),('Interés pactado',a.get('interest_agreed') or 'Pendiente'),('Clase',a.get('interest_type') or 'Pendiente'),('Equivalente preliminar',f"{c.get('effective_annual_rate',0):.4f}% E.A."),('Límite configurado',f"{c.get('maximum_reference_ea',0):.2f}% E.A."),('Cargos adicionales',cop(c.get('other_charges')))]},
        {'heading':'7. Novación','text':f"Intención informada: {a.get('novation_intent') or 'No'}. La novación no se presume; si se pretende sustituir la obligación anterior debe expresarse de manera inequívoca y definir el efecto sobre títulos y garantías."},
        {'heading':'8. Comunicaciones y datos','bullets':['Canales autorizados y actualizables.','Cobranza respetuosa dentro de horarios y periodicidad legales.','Prohibición de divulgar la obligación a terceros no legitimados.','Custodia segura de identificaciones, firmas y comprobantes.']},
        {'heading':'9. Diferencias y modificaciones','bullets':['Las modificaciones requieren constancia escrita o mensaje de datos atribuible.','Las controversias sobre saldo se concilian con soportes.','Procesos, insolvencia o medidas posteriores deben informarse.','La invalidez de una estipulación no autoriza cobros distintos a los permitidos.']},
        {'heading':'10. Firma y anexos','bullets':['Estado de cuenta aprobado.','Cronograma de cuotas.','Soportes de representación.','Pagaré y carta de instrucciones solo cuando procedan.','Firmas o mecanismo electrónico confiable.']},
        {'heading':'11. Control de uso','bullets':['No usar este acuerdo para renunciar a derechos ciertos e indisponibles.','No incorporar garantías reales sin instrumentación especializada.','Verificar que tasa, saldo y cronograma coincidan en todos los anexos.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def payment_schedule_v234_sections(a, result):
    c = _collection_calc(result)
    schedule = c.get('payment_schedule') or {}
    rows=[('Cuota','Fecha','Valor','Estado')]
    for row in schedule.get('rows', []):
        rows.append((str(row.get('number')), row.get('due_date') or 'Fecha por definir', cop(row.get('amount')), row.get('status') or 'Pendiente'))
    if not schedule.get('rows'):
        rows.append(('1', a.get('first_payment_date') or 'Fecha por definir', cop(c.get('agreement_total')), 'Pendiente'))
    return [
        {'heading':'1. Datos del acuerdo','table':[('Campo','Información')]+_collection_identity_table(a)+[('Valor total',cop(c.get('agreement_total'))),('Cuotas',str(schedule.get('installments') or c.get('installments') or 1)),('Periodicidad',a.get('frequency') or 'Pendiente'),('Suma del cronograma',cop(schedule.get('sum_installments'))),('Conciliación','Exacta' if schedule.get('reconciled') else 'Requiere revisión')]},
        {'heading':'2. Cronograma calculado','table':rows},
        {'heading':'3. Ajuste de redondeo','text':f"Cuota ordinaria: {cop(schedule.get('regular_installment'))}. Última cuota: {cop(schedule.get('last_installment'))}. Ajuste de centavos: {cop(schedule.get('rounding_adjustment'))}."},
        {'heading':'4. Imputación','bullets':['Registrar cada pago contra la cuota correspondiente.','Separar capital, interés y cargos solo cuando estén pactados y liquidados.','Actualizar saldo y entregar constancia.','Conciliar pagos no identificados antes de declarar mora.']},
        {'heading':'5. Mora y días de gracia','text':f"Días de gracia informados: {a.get('grace_days') or 0}. La mora, tasa y aceleración requieren control del acuerdo y del límite vigente."},
        {'heading':'6. Abonos anticipados','text':'Los pagos anticipados deben registrarse y aplicarse conforme al acuerdo y a las normas aplicables, indicando si reducen plazo, cuota o saldo.'},
        {'heading':'7. Alertas del cronograma','bullets':schedule.get('warnings') or ['No se detectaron alertas matemáticas de cronograma.']},
        {'heading':'8. Control de uso','bullets':['Las fechas se calculan desde la primera cuota y la periodicidad declarada.','No declarar incumplimiento con base en un cronograma no firmado.','Recalcular después de abonos, modificaciones o decisiones.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]

def promissory_note_v234_sections(a, result):
    c = _collection_calc(result)
    return [
        {'heading':'PAGARÉ','text':'El suscriptor promete incondicionalmente pagar a la orden del beneficiario la suma determinada en este título, en los términos aquí establecidos.'},
        {'heading':'1. Partes y título','table':[('Campo','Información'),('Suscriptor',a.get('debtor_name') or 'Pendiente'),('Identificación',a.get('debtor_id') or 'Pendiente'),('Beneficiario',a.get('creditor_name') or 'Pendiente'),('Identificación',a.get('creditor_id') or 'Pendiente'),('Referencia',a.get('document_reference') or 'Pendiente')]},
        {'heading':'2. Suma y moneda','table':[('Campo','Información'),('Valor del pagaré',cop(c.get('agreement_total') or c.get('reported_balance'))),('Moneda',a.get('currency') or 'COP'),('Valor en letras',cop(c.get('agreement_total') or c.get('reported_balance')))]},
        {'heading':'3. Vencimiento y pago','table':[('Campo','Información'),('Forma de vencimiento',a.get('maturity_form') or 'Pendiente'),('Primera fecha',a.get('first_payment_date') or a.get('due_date') or 'Pendiente'),('Periodicidad',a.get('frequency') or 'Pendiente'),('Lugar o canal de pago',a.get('payment_channel') or 'Pendiente')]},
        {'heading':'4. Intereses','table':[('Campo','Información'),('Clase',a.get('interest_type') or 'No aplica'),('Tasa informada',f"{a.get('interest_rate') or 0}% {a.get('interest_period') or ''}"),('Equivalente preliminar',f"{c.get('effective_annual_rate',0):.4f}% E.A."),('Límite configurado',f"{c.get('maximum_reference_ea',0):.2f}% E.A.")],'text':'En ningún caso se causarán intereses superiores al límite vigente para la modalidad aplicable.'},
        {'heading':'5. Firma y atribución','text':'La firma manuscrita o electrónica debe permitir identificar al suscriptor y demostrar su aprobación del contenido. Conservar original, integridad, fecha, entrega y trazabilidad.'},
        {'heading':'6. Aval, codeudor o solidaridad','text':f"Configuración informada: {a.get('guarantor_or_aval') or 'No'}. Ningún tercero queda obligado sin identificación, calidad, consentimiento y firma verificables."},
        {'heading':'7. Espacios y carta de instrucciones','table':[('Campo','Información'),('Formato',a.get('note_format') or 'Pendiente'),('Espacios en blanco',a.get('blanks_present') or 'Pendiente'),('Instrucciones firmadas',a.get('instructions_signed') or 'Pendiente')],'text':'Todo espacio debe llenarse estrictamente conforme a instrucciones específicas otorgadas antes de presentar el título.'},
        {'heading':'8. Suscripción','table':[('Rol','Nombre / firma'),('Suscriptor',a.get('debtor_name') or 'Pendiente'),('Avalista o codeudor','No aplica o pendiente de identificación'),('Fecha',a.get('document_date') or 'Pendiente')]},
        {'heading':'9. Control de uso','bullets':['No firmar con valores, beneficiario, vencimiento o alcance indeterminados.','No usar espacios sin instrucciones suficientes y firmadas.','No incorporar tasa que exceda el límite vigente.','No asumir que el pagaré sanea una obligación inexistente, discutida o prescrita.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def instruction_letter_v234_sections(a, result):
    c=_collection_calc(result)
    return [
        {'heading':'1. Título asociado','table':[('Campo','Información'),('Pagaré de referencia',a.get('document_reference') or 'Pendiente'),('Suscriptor',a.get('debtor_name') or 'Pendiente'),('Beneficiario',a.get('creditor_name') or 'Pendiente'),('Formato',a.get('note_format') or 'Pendiente')]},
        {'heading':'2. Finalidad','text':'Estas instrucciones delimitan de forma expresa los únicos datos que podrán completarse en el pagaré asociado y las condiciones para hacerlo.'},
        {'heading':'3. Eventos de diligenciamiento','bullets':['Incumplimiento verificable de una obligación vencida según el acuerdo.','Conciliación previa de capital, abonos, intereses y cargos soportados.','Respeto de días de gracia y comunicaciones pactadas.','Ausencia de suspensión, insolvencia, orden judicial o medida que impida la actuación.']},
        {'heading':'4. Valores autorizados','table':[('Campo','Límite'),('Capital','Saldo de capital efectivamente pendiente'),('Intereses','Solo los válidamente pactados, causados y dentro del límite vigente'),('Cargos','Únicamente procedentes, pactados y soportados'),('Valor máximo de referencia',cop(c.get('agreement_total') or c.get('reported_balance')))]},
        {'heading':'5. Vencimiento','text':f"La forma de vencimiento autorizada es {a.get('maturity_form') or 'Pendiente'}. La fecha deberá corresponder al acuerdo y al evento de incumplimiento verificado, sin antedatar el título."},
        {'heading':'6. Intereses y límites','text':f"Tasa equivalente preliminar: {c.get('effective_annual_rate',0):.4f}% E.A. Límite configurado: {c.get('maximum_reference_ea',0):.2f}% E.A., válido entre {c.get('interest_valid_from') or 'Pendiente'} y {c.get('interest_valid_to') or 'Pendiente'}. Debe revalidarse al diligenciar."},
        {'heading':'7. Notificación y evidencia','bullets':['Conservar acuerdo, estado de cuenta y prueba del incumplimiento.','Informar el diligenciamiento por canal verificable cuando corresponda.','Entregar copia completa del pagaré diligenciado.','Registrar persona, fecha, valores, fuente y método de diligenciamiento.']},
        {'heading':'8. Prohibiciones','bullets':['No completar valores no causados.','No cambiar beneficiario o moneda sin autorización.','No omitir abonos o notas crédito.','No modificar firma ni texto original.','No usar el título durante insolvencia o contra orden de autoridad.']},
        {'heading':'9. Firma de instrucciones','table':[('Rol','Nombre / firma'),('Suscriptor',a.get('debtor_name') or 'Pendiente'),('Beneficiario receptor',a.get('creditor_name') or 'Pendiente'),('Fecha',a.get('document_date') or 'Pendiente')]},
        {'heading':'10. Control de uso','bullets':['La carta debe vincularse inequívocamente al pagaré específico.','Las instrucciones genéricas o posteriores a la firma elevan el riesgo probatorio.','Verificar vigencia normativa y parámetros al diligenciar.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def payment_receipt_v234_sections(a, result):
    c=_collection_calc(result)
    paid=float(a.get('partial_payments_total') or 0)
    return [
        {'heading':'RECIBO DE PAGO','text':'Constancia de recepción sujeta a verificación efectiva del abono y a su correcta imputación.'},
        {'heading':'1. Identificación','table':[('Campo','Información')]+_collection_identity_table(a)},
        {'heading':'2. Pago recibido','table':[('Campo','Información'),('Valor acumulado informado',cop(paid)),('Medio',a.get('payment_channel') or 'Pendiente'),('Fecha o soporte','Debe anexarse comprobante verificable'),('Referencia de cuota','Según cronograma o estado de cuenta')]},
        {'heading':'3. Imputación','table':[('Concepto','Valor'),('Capital original',cop(c.get('principal'))),('Abonos acumulados',cop(c.get('partial_payments_total'))),('Saldo informado',cop(c.get('reported_balance'))),('Diferencia pendiente de conciliar',cop(c.get('balance_difference')))]},
        {'heading':'4. Alcance','text':'La constancia acredita únicamente el pago efectivamente recibido e identificado. No implica paz y salvo total salvo declaración expresa y saldo cero conciliado.'},
        {'heading':'5. Soportes','bullets':['Comprobante de pago.','Estado de cuenta anterior y actualizado.','Cronograma aplicable.','Identificación del emisor de la constancia.']},
        {'heading':'6. Firma','table':[('Rol','Nombre / firma'),('Recibe por el acreedor',a.get('creditor_representative') or a.get('creditor_name') or 'Pendiente'),('Pagador',a.get('debtor_name') or 'Pendiente'),('Fecha','Pendiente de comprobante')]},
        {'heading':'7. Control de uso','bullets':['No emitir antes de verificar ingreso o compensación.','No borrar la trazabilidad de pagos previos.','Actualizar saldo y operadores de información cuando proceda.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def settlement_certificate_v234_sections(a, result):
    c=_collection_calc(result)
    return [
        {'heading':'PAZ Y SALVO / CONSTANCIA DE CIERRE','text':'Documento condicionado a la comprobación del pago o extinción total de la obligación descrita.'},
        {'heading':'1. Partes y obligación','table':[('Campo','Información')]+_collection_identity_table(a)+[('Origen',a.get('origin_description') or 'Pendiente')]},
        {'heading':'2. Estado final','table':[('Concepto','Valor'),('Capital original',cop(c.get('principal'))),('Abonos o pagos',cop(c.get('partial_payments_total'))),('Saldo final informado',cop(c.get('reported_balance'))),('Conciliación',a.get('balance_reconciled') or 'Pendiente')]},
        {'heading':'3. Declaración condicionada','text':'Una vez verificado saldo cero, el acreedor declara satisfecha la obligación identificada, dentro del alcance exacto del documento y sin extender la constancia a obligaciones distintas o posteriores.'},
        {'heading':'4. Títulos y garantías','bullets':['Marcar como pagado o cancelado el título cuando proceda.','Entregar o inutilizar el original conforme al régimen aplicable.','Registrar el pago en RADIAN cuando se trate de factura electrónica como título valor.','Liberar garantías únicamente mediante los actos y registros requeridos.']},
        {'heading':'5. Reportes y datos','bullets':['Actualizar la información suministrada a operadores.','Retirar o actualizar reportes según la ley y el estado real.','Conservar la trazabilidad necesaria sin divulgar datos innecesarios.','Atender solicitudes de corrección o actualización.']},
        {'heading':'6. Reservas','text':'La constancia no cubre obligaciones no identificadas ni hechos fraudulentos demostrados posteriormente. Cualquier reserva debe ser concreta, lícita y compatible con la extinción declarada.'},
        {'heading':'7. Firma','table':[('Rol','Nombre / firma'),('Acreedor o representante',a.get('creditor_representative') or a.get('creditor_name') or 'Pendiente'),('Deudor receptor',a.get('debtor_name') or 'Pendiente'),('Fecha de expedición','Pendiente de verificación final')]},
        {'heading':'8. Control de uso','bullets':['No emitir con saldo positivo o movimientos sin conciliar.','No prometer levantamiento automático de medidas o garantías registradas.','Confirmar actualización de título, RADIAN y centrales cuando aplique.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]


def collection_evidence_matrix_v234_sections(a, result):
    return [
        {'heading':'1. Identificación del expediente','table':[('Campo','Información')]+_collection_identity_table(a)+[('Etapa',a.get('package_stage') or 'Pendiente')]},
        {'heading':'2. Matriz del origen','table':[('Hecho a probar','Soporte esperado'),('Negocio causal','Contrato, orden, factura, entrega o prestación'),('Identidad y facultades','Documentos, certificados, poder o mandato'),('Aceptación del deudor','Firma, mensaje, recibido, conducta o título'),('Vencimiento','Cláusula, factura, cronograma o requerimiento'),('Titularidad','Original, endoso, cesión, RADIAN o cadena de transferencias')]},
        {'heading':'3. Matriz económica','table':[('Hecho a probar','Soporte esperado'),('Capital','Documento de origen y desembolso o prestación'),('Abonos','Comprobantes, recibos, extractos y notas crédito'),('Intereses','Pacto, fechas, base, periodicidad y certificación vigente'),('Cargos','Pacto, factura, razonabilidad y causación'),('Saldo','Estado de cuenta reproducible y conciliado')]},
        {'heading':'4. Comunicaciones y cobranza','table':[('Control','Evidencia'),('Canales autorizados','Autorización o actualización de preferencias'),('Contactos','Fecha, hora, canal, contenido y resultado'),('Comunicación previa a reporte','Constancia de envío y término'),('Requerimientos y respuestas','Radicados y archivos íntegros'),('Acuerdos','Oferta, aceptación, versiones y firmas')]},
        {'heading':'5. Títulos, facturas y pagaré','table':[('Control','Evidencia'),('Factura','Recepción, aceptación, pagos y reclamos'),('RADIAN','Eventos, tenedor, endosos, limitaciones y pagos'),('Pagaré','Original, requisitos, entrega y firma'),('Espacios','Carta de instrucciones vinculada y firmada'),('Aval o solidaridad','Calidad, consentimiento y firma')]},
        {'heading':'6. Procesos y riesgos','table':[('Control','Estado'),('Controversia',a.get('disputed') or 'Pendiente'),('Prescripción',a.get('prescription_concern') or 'Pendiente'),('Proceso activo',a.get('judicial_process_active') or 'Pendiente'),('Insolvencia',a.get('insolvency_active') or 'Pendiente'),('Medidas',a.get('embargo_or_measure') or 'Pendiente'),('Fraude o capacidad',f"{a.get('fraud_impersonation') or 'Pendiente'} / {a.get('debtor_capacity_issue') or 'Pendiente'}")]},
        {'heading':'7. Privacidad y custodia','bullets':['Conservar originales y copias de trabajo diferenciadas.','Registrar origen, fecha, autor, hash o mecanismo de integridad cuando sea pertinente.','No anexar claves, credenciales, datos financieros completos ni información de terceros.','Limitar acceso por rol y conservar registro de consulta, edición, aprobación y descarga.']},
        {'heading':'8. Índice de anexos','table':[('Anexo','Estado'),('1. Soporte del negocio','Pendiente de numeración'),('2. Estado de cuenta y movimientos','Pendiente de numeración'),('3. Comunicaciones y autorizaciones','Pendiente de numeración'),('4. Títulos, firmas y transferencias','Pendiente de numeración'),('5. Soportes procesales o de insolvencia','Si aplica')]},
        {'heading':'9. Control de uso','bullets':[f"Evidencia declarada: {a.get('evidence_status') or 'Pendiente'}.",f"Datos minimizados: {a.get('data_minimized') or 'Pendiente'}.",f"Datos esenciales confirmados: {a.get('data_confirmed') or 'Pendiente'}.",'No radicar documentos que contradigan los soportes o entre sí.','Uso profesional sujeto a aprobación jurídica y QA dual.']},
    ]

def collection_letter_sections(a):
    return [
        {'heading': '1. Identificación de la obligación', 'text': f"Acreedor: {a.get('creditor') or '[ACREEDOR]'}. Deudor: {a.get('debtor') or '[DEUDOR]'}. Exigibilidad informada: {a.get('due_date') or '[FECHA]'}."},
        {'heading': '2. Estado de cuenta', 'table': [('Concepto', 'Valor / condición'), ('Capital informado', cop(a.get('principal') or a.get('amount'))), ('Abonos previos', a.get('partial_payments') or 'Pendiente'), ('Tasa pactada mensual', str(a.get('interest_rate') or 'No informada') + '%'), ('Cuotas propuestas', str(a.get('payment_plan') or 'Pendiente'))]},
        {'heading': '3. Requerimiento', 'text': 'Se solicita verificar el estado de cuenta, informar objeciones documentadas y proponer pago o formalización dentro de un plazo razonable. Este borrador no debe afirmar hechos no soportados ni usar amenazas, hostigamiento o canales no autorizados.'},
        {'heading': '4. Intereses y gastos', 'bullets': ['No aplicar tasa fija desactualizada.', 'Consultar certificación vigente y modalidad correspondiente.', 'Liquidar sobre capital o suma vencida conforme a pacto y ley, sin duplicidad.', 'Los gastos deben ser razonables, procedentes y soportados.']},
        {'heading': '5. Canales y tratamiento de datos', 'bullets': ['Usar canales, horarios y periodicidad autorizados.', 'Evitar divulgación a terceros no legitimados.', 'Conservar evidencia de mensajes, llamadas y acuerdos.', 'Permitir actualización de datos y preferencias de contacto.']},
    ]


def payment_agreement_sections(a):
    principal = float(a.get('principal') or a.get('amount') or 0)
    installments = max(int(float(a.get('payment_plan') or 1)), 1)
    simple = principal / installments if principal else 0
    return [
        {'heading': '1. Reconocimiento delimitado', 'text': f"Las partes registran un capital informado de {cop(principal)} sujeto a conciliación de soportes, abonos, notas crédito e intereses válidos."},
        {'heading': '2. Plan preliminar', 'table': [('Campo', 'Condición'), ('Número de cuotas', str(installments)), ('Capital simple por cuota', cop(simple)), ('Fecha inicial', '[...]'), ('Periodicidad', '[...]'), ('Canal de pago', '[...]')]},
        {'heading': '3. Imputación y mora', 'bullets': ['Registrar saldo de capital, intereses y pagos por separado.', 'Imputar pagos conforme a la ley y al acuerdo escrito.', 'La mora se calcula sobre sumas vencidas y por tiempo real, con tasa vigente válida.', 'La cláusula aceleratoria exige supuesto, decisión y reliquidación trazable.']},
        {'heading': '4. Incumplimiento y modificación', 'bullets': ['Definir eventos claros y oportunidad de subsanación cuando proceda.', 'Toda modificación, condonación, prórroga o novación debe constar por escrito.', 'No llenar espacios ni alterar el documento después de firma sin autorización y trazabilidad.']},
        {'heading': '5. Cierre', 'bullets': ['Expedir recibos y estado actualizado.', 'Al pago total, entregar paz y salvo y devolver o cancelar garantías.', 'Conservar soportes y versión final del acuerdo.']},
    ]


def promissory_note_sections(a):
    return [
        {'heading': '1. Pagaré — datos mínimos', 'table': [('Campo', 'Valor'), ('Otorgante/deudor', a.get('debtor') or 'Pendiente'), ('Beneficiario/acreedor', a.get('creditor') or 'Pendiente'), ('Capital', cop(a.get('principal') or a.get('amount'))), ('Vencimiento', a.get('due_date') or 'Pendiente'), ('Lugar de pago', '[...]')]},
        {'heading': '2. Intereses', 'text': 'La tasa remuneratoria o moratoria solo se incorpora después de verificar pacto, modalidad, certificación vigente y tope aplicable. El sistema conservará fuente, vigencia, fórmula y redondeo.'},
        {'heading': '3. Carta de instrucciones', 'bullets': ['Identificar espacios autorizados y evento de diligenciamiento.', 'No permitir espacios indeterminados sin instrucción.', 'Conservar copia firmada e integridad del título.', 'Registrar custodia, devolución o cancelación al pago total.']},
        {'heading': '4. Advertencia', 'text': 'Este borrador no se genera como reconocimiento automático cuando la deuda, saldo o exigibilidad estén controvertidos, ni cuando exista proceso ejecutivo, insolvencia o embargo activo.'},
    ]


def employment_onboarding_checklist_sections(a, result):
    calc = result.get('calculation') or {}
    selected = calc.get('selected_modality') or 'por confirmar'
    return [
        {'heading':'LISTA DE ALISTAMIENTO, AFILIACIONES Y CUMPLIMIENTO','text':f"Empleador: {a.get('employer_name') or 'Por confirmar'} · Trabajador: {a.get('worker_name') or 'Por confirmar'} · Modalidad contractual seleccionada: {selected}."},
        {'heading':'1. Datos y capacidad','table':[
            ('Control','Estado'),('Identificación completa de las partes','Confirmada'),('Mayoría de edad',str(a.get('worker_age_status') or 'Pendiente')),('Régimen público/transnacional',str(a.get('public_or_crossborder') or 'Pendiente')),('Régimen colectivo especial',str(a.get('collective_regime') or 'Pendiente')),
        ]},
        {'heading':'2. Modalidad y duración','bullets':[
            f"Necesidad real: {a.get('need_type') or 'Pendiente'}.",f"Inicio: {a.get('start_date') or 'Pendiente'}.",f"Terminación fija: {a.get('end_date') or 'No aplica'}.",f"Obra o labor: {a.get('work_description') or 'No aplica'}.",f"Hito de terminación: {a.get('completion_milestone') or 'No aplica'}.",
        ]},
        {'heading':'3. Jornada y remuneración','table':[
            ('Control','Valor'),('Jornada semanal',str(calc.get('weekly_hours'))),('Máximo legal parametrizado',str(calc.get('maximum_weekly_hours'))),('Jornada diaria máxima',str(calc.get('max_daily_hours'))),('Horas extra previstas',f"{calc.get('planned_overtime_daily')} diarias / {calc.get('planned_overtime_weekly')} semanales"),('Salario',cop(calc.get('monthly_salary'))),('Mínimo proporcional estimado',cop(calc.get('minimum_ordinary_salary_estimate'))),('Mínimo integral',cop(calc.get('minimum_integral_salary'))),
        ]},
        {'heading':'4. Antes del inicio','bullets':[
            f"Afiliaciones y aportes: {a.get('social_security_plan_confirmed') or 'Pendiente'}.",f"Examen médico ocupacional: {a.get('occupational_exam_ready') or 'Pendiente'}.",'Entregar copia íntegra del contrato y anexos firmados.','Registrar equipos, accesos y credenciales.','Comunicar reglamento, políticas, SG-SST, canales de queja y desconexión.','Configurar nómina, periodicidad, recargos y pagos variables aplicables.',
        ]},
        {'heading':'5. Protecciones e inclusión','bullets':[
            f"Protección conocida: {a.get('special_protection') or 'No'}.",f"Decisión basada negativamente en la protección: {a.get('protected_status_decision') or 'No aplica'}.",f"Ajustes razonables: {a.get('reasonable_adjustments') or 'No aplica'}.",'Conservar únicamente la evidencia necesaria, con acceso restringido y sin diagnósticos excesivos.',
        ]},
        {'heading':'6. Módulos y anexos','table':[
            ('Módulo','Activación'),('Funciones','Obligatorio'),('Compensación variable',str(a.get('variable_payments') or 'No')),('Modalidad no presencial',str(a.get('remote') or 'Presencial')),('Equipos y credenciales',str(a.get('work_equipment') or 'No')),('Datos sensibles/biometría',str(a.get('personal_data') or 'No')),('Propiedad intelectual',str(a.get('ip_relevant') or 'No')),('Confidencialidad',str(a.get('confidential_information') or 'No')),
        ]},
        {'heading':'7. Cierre responsable','bullets':['Verificar que no existan campos sin resolver.','Confirmar correspondencia entre entrevista, reglas, contrato y anexos.','Registrar aprobación del abogado responsable cuando el cambio jurídico lo requiera.','Ejecutar QA documental y conservar hashes del paquete liberado.']},
    ]



def _sast_identity(a):
    return [('Campo','Información'),('Interesado',a.get('requester_name') or 'No informado'),('Identificación',a.get('requester_id') or 'No informada'),('Calidad',a.get('acting_capacity') or 'No informada'),('Autoridad',a.get('authority') or 'No informada'),('Municipio',a.get('territory') or 'No informado'),('Departamento',a.get('department') or 'No informado'),('Placa',a.get('plate') or 'No informada'),('Comparendo',a.get('comparendo_number') or 'No informado'),('Fecha del hecho',a.get('event_date') or 'No informada')]

def _sast_match_rows(result):
    rows=[('Actuación local','Coincidencia preliminar')]
    for m in result.get('sast_matches',[]):
        rows.append((m.get('id') or 'Sin ID',f"{m.get('authority') or m.get('territory')} · {m.get('start')} a {m.get('end')} · acto {m.get('resolution') or 'sin número'} · {m.get('status') or 'estado no informado'}"))
    return rows if len(rows)>1 else [('Resultado','Sin coincidencia en el snapshot local incorporado; la consulta oficial individual sigue siendo obligatoria.')]

def sast_mature_report_sections(a,result):
    c=result.get('calculation') or {}
    return [
      {'heading':'1. Objeto y límites del diagnóstico','text':'El informe organiza una coincidencia preliminar entre autoridad o territorio y fecha sobre un snapshot local curado. No declara nulidad, revocatoria, archivo, devolución, regularidad del dispositivo ni efectos frente a terceros. La conclusión exige individualizar cámara, punto, acto, tecnología, período y expediente.'},
      {'heading':'2. Identificación del caso','table':_sast_identity(a)},
      {'heading':'3. Resultado del cruce local','table':_sast_match_rows(result),'text':f"La base local contiene {c.get('dataset_records_included',10)} registros dentro de un universo histórico esperado de {c.get('historical_master_expected_records',49)}. Cobertura completa: No."},
      {'heading':'4. Estado oficial declarado','table':[('Control','Dato'),('Coincidencia oficial 2026',a.get('official_2026_match') or 'No informada'),('Acto o radicado',a.get('official_act_number') or 'No informado'),('Estado',a.get('official_act_status') or 'No informado'),('Fuente',a.get('official_act_source') or 'No informada')]},
      {'heading':'5. Control jurídico','bullets':['Una apertura, formulación de cargos o investigación en curso no equivale a una decisión firme.','Una decisión favorable requiere coincidencia individual por sujeto, organismo, punto, período y efectos.','La ausencia de coincidencia en la base local no acredita validez o regularidad.','El propietario no responde objetivamente por la sola titularidad; debe analizarse la conducta y la imputación aplicable.','El pago no produce por sí mismo devolución ni extingue la necesidad de identificar el acto y la ruta.']},
      {'heading':'6. Alertas activadas','bullets':[f"{x.get('id')}: {x.get('message')} Acción: {x.get('action')}" for x in result.get('triggered_rules',[])] or ['No se activaron reglas adicionales; subsiste el carácter preliminar del chequeo.']},
      {'heading':'7. Conclusión condicionada','text':f"Semáforo: {result.get('risk_label')}. Ruta: {result.get('route')}. El resultado debe cotejarse en el Sistema de Información de Fotodetección de la ANSV y en las actuaciones individuales de la autoridad y la Superintendencia de Transporte."},
    ]

def sast_verification_matrix_sections(a,result):
    c=result.get('calculation') or {}
    return [
      {'heading':'MATRIZ INDIVIDUAL DE AUTORIZACIÓN Y EVIDENCIA TÉCNICA','text':'Cada fila debe cerrarse con documento, fecha, fuente y correspondencia exacta con el punto y el equipo.'},
      {'heading':'1. Punto y dispositivo','table':[('Elemento','Estado declarado'),('Ubicación del hecho',a.get('event_location') or 'No informada'),('Dispositivo conocido',a.get('device_known') or 'No informado'),('Código o serial',a.get('device_id') or 'No informado'),('Coincidencia con punto autorizado',a.get('exact_point_match') or 'No informada')]},
      {'heading':'2. Autorización','table':[('Elemento','Dato'),('Soporte ANSV o excepción',a.get('ansv_authorization') or 'No informado'),('Número',a.get('authorization_number') or 'No informado'),('Expedición',a.get('authorization_issue_date') or 'No informada'),('Vencimiento',a.get('authorization_expiry_date') or 'No informado'),('Cobertura temporal preliminar','Sí' if c.get('authorization_covers_event_preliminary') else 'No confirmada')]},
      {'heading':'3. Tecnología y metrología','table':[('Elemento','Dato'),('Calibración/trazabilidad',a.get('calibration_traceability') or 'No informada'),('Fecha de certificado',a.get('calibration_date') or 'No informada'),('Concepto de desempeño',a.get('performance_concept') or 'No informado'),('Período histórico aplicable','Sí' if c.get('concept_performance_relevant') else 'No')]},
      {'heading':'4. Señalización y operación','table':[('Elemento','Estado'),('Señalización preventiva',a.get('signage_verified') or 'No informada'),('Conducta',a.get('conduct_code') or 'No informada'),('Resolución técnica de referencia',c.get('current_technical_resolution') or 'Verificar')]},
      {'heading':'5. Evidencia mínima a anexar','bullets':['Acto íntegro de autorización o fundamento de la excepción legal.','Mapa, coordenadas y correspondencia entre punto autorizado y lugar del hecho.','Certificado de calibración, trazabilidad, laboratorio y alcance.','Evidencia del serial o identificador asociado a fotografías, video y metadatos.','Soporte temporal de señalización y condiciones de operación.','Acto individual de la Supertransporte y constancia de estado o ejecutoria.']},
      {'heading':'6. Resultado de la matriz','text':'Los vacíos se registran como alertas probatorias. Ninguna casilla aislada sustituye la valoración integral del expediente ni produce un efecto automático sobre el comparendo o la sanción.'},
    ]

def sast_record_request_sections(a,result):
    return [
      {'heading':'1. Destinatario y actuación','table':_sast_identity(a),'text':'Solicito acceso íntegro y legible al expediente administrativo y técnico asociado al sistema de detección utilizado.'},
      {'heading':'2. Identificación del SAST','bullets':['Código, serial, fabricante, modelo, tecnología y ubicación exacta.','Coordenadas y acto que autorizó el punto para la fecha del hecho.','Fecha de inicio, suspensión, renovación, traslado o terminación de operación.','Identidad y competencia del agente que validó la evidencia.']},
      {'heading':'3. Autorización y criterios técnicos','bullets':['Copia íntegra del acto de autorización ANSV o explicación motivada de la excepción legal invocada.','Estudio técnico de seguridad vial y documentos que soportaron la instalación.','Vigencia y modificaciones del acto para la fecha exacta.','Evidencia de inclusión del punto en los instrumentos de seguridad vial aplicables.']},
      {'heading':'4. Metrología y evidencia digital','bullets':['Certificado de calibración o trazabilidad aplicable al equipo y fecha.','Laboratorio, acreditación, alcance, incertidumbre y patrón utilizado cuando corresponda.','Archivos nativos, metadatos, sellos de tiempo, integridad y cadena de custodia.','Manual o parámetros necesarios para interpretar la medición.']},
      {'heading':'5. Señalización y operación','bullets':['Registro fotográfico, acta, ubicación y fecha de instalación de señales.','Bitácoras de mantenimiento, fallas, suspensión y puesta en servicio.','Contrato u operador tecnológico, sin trasladar a privados la competencia sancionatoria.']},
      {'heading':'6. Expediente contravencional','bullets':['Orden de comparendo y evidencia íntegra.','Trazabilidad de validación, envío, entrega y conocimiento.','Actos, audiencias, recursos, ejecutoria, pagos y estado actual.','Histórico de anotaciones en SIMIT y RUNT.']},
      {'heading':'7. Forma de respuesta','text':f"Solicito radicado, índice de anexos, entrega electrónica y explicación de cualquier reserva o inexistencia. Notificaciones: {a.get('email') or 'correo registrado'} y {a.get('address') or 'dirección registrada'}."},
    ]

def sast_supertransport_request_sections(a,result):
    return [
      {'heading':'1. Objeto','text':'Solicito certificar el estado individual de la actuación administrativa SAST que pueda relacionarse con el organismo, período y dispositivo informados, sin extender automáticamente sus efectos a expedientes no individualizados.'},
      {'heading':'2. Datos para la búsqueda','table':_sast_identity(a)+[('Acto o radicado declarado',a.get('official_act_number') or 'No informado'),('Estado declarado',a.get('official_act_status') or 'No informado')]},
      {'heading':'3. Información solicitada','bullets':['Número y fecha de apertura, cargos, decisión, recursos y ejecutoria.','Organismo investigado y período exacto objeto de la actuación.','Tecnología, dispositivos o puntos comprendidos, si fueron individualizados.','Hallazgos, órdenes, medidas y efectos expresamente dispuestos.','Estado actual, actos posteriores y canales oficiales de consulta.']},
      {'heading':'4. Efecto individual','text':'Solicito indicar si existe una decisión firme que ordene revocación, corrección, devolución u otra actuación respecto del comparendo identificado, o si corresponde formular la petición ante el organismo de tránsito con base en el expediente individual.'},
      {'heading':'5. Protección probatoria','text':'La respuesta será incorporada al expediente con su radicado, anexos y hash. La solicitud no presume irregularidad, responsabilidad ni decisión favorable.'},
    ]

def sast_conditional_review_sections(a,result):
    return [
      {'heading':'1. Solicitud condicionada','table':_sast_identity(a),'text':'Solicito revisar integralmente la actuación a la luz de la evidencia técnica y de los actos oficiales individualizados. La petición se formula de manera condicionada: no afirma una causal definitiva que no esté demostrada en el expediente.'},
      {'heading':'2. Hechos por verificar','bullets':['Correspondencia entre lugar del hecho, punto autorizado y dispositivo.','Vigencia de la autorización o procedencia de una excepción legal.','Calibración, trazabilidad, señalización y cadena de evidencia.','Estado y alcance exactos de la actuación de vigilancia de la Supertransporte.','Notificación, defensa, decisión, ejecutoria y registros derivados.']},
      {'heading':'3. Pretensiones graduadas','bullets':['Primero: completar y entregar el expediente.','Segundo: motivar la validez y aplicabilidad de cada soporte.','Tercero: corregir la actuación o el registro si la autoridad confirma una irregularidad individual relevante.','Cuarto: cuando exista acto firme aplicable, ejecutar estrictamente sus efectos respecto del expediente identificado.','Quinto: explicar recursos, actuaciones o autoridades competentes si no accede.']},
      {'heading':'4. Pago y devolución','text':f"Pago declarado: {a.get('paid') or 'No informado'}. No se solicita devolución automática; cualquier restitución exige identificar pago, beneficiario, acto, causal, legitimación, procedimiento y decisión aplicable."},
      {'heading':'5. Reserva de términos','text':'La petición no revive recursos o acciones vencidos ni sustituye defensas dentro de cobro coactivo, embargo o proceso judicial. Esos eventos deben escalarse.'},
    ]

def sast_alert_registry_sections(a,result):
    return [
      {'heading':'REGISTRO DE ALERTAS Y SEGUIMIENTO','table':[('Campo','Dato'),('Interesado',a.get('requester_name') or 'No informado'),('Correo',a.get('email') or 'No informado'),('Autoridad',a.get('authority') or 'No informada'),('Comparendo',a.get('comparendo_number') or 'No informado'),('Consentimiento',a.get('consent_alerts') or 'No informado')]},
      {'heading':'1. Eventos a vigilar','bullets':['Nuevos actos de la Superintendencia de Transporte.','Cambio de estado o ejecutoria de la actuación individual.','Respuesta del organismo de tránsito y entrega del expediente técnico.','Modificación del estado en SIMIT/RUNT.','Cobro, mandamiento, embargo, audiencia o vencimiento próximo.','Actualización de autorización, mapa ANSV o soporte técnico.']},
      {'heading':'2. Registro mínimo por evento','table':[('Dato','Contenido'),('Fecha de consulta','Registrar'),('Fuente oficial','Registrar URL o radicado'),('Cambio detectado','Describir sin interpretar en exceso'),('Documento descargado','Nombre y hash'),('Responsable','Usuario o abogado'),('Próxima fecha de control','Definir')]},
      {'heading':'3. Límites','text':'La inscripción a alertas no suspende términos, no sustituye notificación oficial y no garantiza que todas las fuentes publiquen cambios en tiempo real.'},
    ]

def sast_route_guide_sections(a,result):
    return [
      {'heading':'1. Clasificación del caso','table':[('Control','Resultado'),('Semáforo',result.get('risk_label') or 'No disponible'),('Etapa',a.get('enforcement') or 'No informada'),('Pago',a.get('paid') or 'No informado'),('Comparendos relacionados',str(a.get('case_count') or 1)),('Soportes',a.get('evidence_available') or 'No informados')]},
      {'heading':'2. Ruta recomendada','bullets':['Consolidar comparendo, consultas, dirección histórica y datos del punto.','Consultar el mapa ANSV y descargar el acto aplicable.','Solicitar expediente técnico y contravencional.','Certificar el estado de la actuación oficial de vigilancia.','Comparar dispositivo, punto, período y efectos.','Seleccionar petición, audiencia, recurso, revocatoria, corrección o defensa según etapa.','Registrar versión, radicado, respuesta y decisión.']},
      {'heading':'3. Escalamiento obligatorio','bullets':['Cobro coactivo, embargo o proceso judicial.','Término menor a diez días o imposible de descartar.','Suplantación, clonación, hurto o fraude.','Más de diez expedientes relacionados.','Dudas sobre autenticidad, ejecutoria o identidad del acto.']},
      {'heading':'4. Reglas de interpretación','bullets':['Coincidencia no equivale a nulidad.','Investigación no equivale a decisión firme.','No coincidencia local no equivale a regularidad.','Irregularidad técnica no reemplaza análisis de etapa y efectos.','Pago no equivale a renuncia absoluta ni genera devolución automática.','Revocatoria directa no revive términos judiciales.']},
      {'heading':'5. Cierre responsable','text':'El abogado responsable cierra la conclusión jurídica cuando el impacto lo requiera. QA verifica integridad, correspondencia de datos, generación documental y trazabilidad, sin repetir controles no modificados.'},
    ]



def _habeas_calc(result):
    return (result or {}).get('calculation') or {}


def _habeas_parties(a):
    return [('Titular',a.get('data_subject_name') or '[TITULAR]'),('Identificación',a.get('data_subject_id') or '[IDENTIFICACIÓN]'),('Calidad',a.get('acting_capacity') or '[CALIDAD]'),('Fuente',a.get('source_name') or 'Por identificar'),('Operador',a.get('operator_name') or 'Por identificar'),('Obligación',a.get('obligation_identifier') or '[OBLIGACIÓN]')]


def habeas_consultation_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Destinatario, titular y alcance','table':_habeas_parties(a),'text':'Consulta para conocer, verificar y documentar el ciclo completo del dato financiero, crediticio, comercial o de servicios controvertido.'},
        {'heading':'2. Hechos confirmados','text':a.get('facts_detail') or '[HECHOS CONFIRMADOS]','bullets':[f"Problema: {a.get('issue_type') or 'Pendiente'}.",f"Categoría: {a.get('data_category') or 'Pendiente'}.",f"Estado de la obligación: {a.get('obligation_status') or 'Pendiente'}.",f"Fecha de conocimiento: {a.get('report_discovery_date') or 'No informada'}." ]},
        {'heading':'3. Información solicitada','bullets':['Contenido completo y actualizado del dato registrado.','Identificación de la fuente que suministró el dato y fecha exacta del reporte.','Identificación de operadores y usuarios que consultaron o recibieron la información, cuando proceda.','Copia del soporte de la obligación, saldo, mora, pago, extinción y novedades.','Copia y trazabilidad de la comunicación previa al reporte.','Políticas, criterios y trazabilidad de calificación o decisión automatizada cuando corresponda.','Constancia de correcciones, actualizaciones, bloqueos o leyendas asociadas.']},
        {'heading':'4. Término preliminar','table':[('Fecha de radicación',c.get('filing_date') or a.get('filing_date') or 'Pendiente'),('Término ordinario',str(c.get('preliminary_business_days') or 10)+' días hábiles'),('Vencimiento preliminar',c.get('preliminary_due_date') or 'Pendiente'),('Prórroga máxima modelada',str(c.get('extension_business_days') or 5)+' días hábiles'),('Festivos descontados','No')],'text':'El vencimiento debe recalcularse con recepción efectiva, festivos, traslado y prórroga debidamente informada.'},
        {'heading':'5. Privacidad y entrega','bullets':['Responder por canal verificable y reservado.','No remitir datos de terceros ni información ajena a la finalidad.','Entregar soportes legibles y conservar metadatos de trazabilidad.','Confirmar identidad antes de revelar información financiera.']},
        {'heading':'6. Notificaciones y firma','table':[('Correo',a.get('email') or '[CORREO]'),('Teléfono',a.get('phone') or '[TELÉFONO]'),('Dirección',a.get('address') or '[DIRECCIÓN]'),('Ciudad',a.get('city') or '[CIUDAD]')],'text':'Atentamente,\n\n__________________________________\n'+(a.get('data_subject_name') or '[TITULAR]')+'\n'+(a.get('data_subject_id') or '[IDENTIFICACIÓN]')},
        {'heading':'7. Control de uso','bullets':['La consulta no reconoce la obligación ni renuncia a controversias.','La información recibida debe cotejarse antes de formular una pretensión definitiva.','La herramienta no garantiza modificación del dato ni resultado crediticio.']},
    ]


def habeas_claim_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Reclamo y responsables','table':_habeas_parties(a),'text':f"Se formula reclamo de hábeas data para: {a.get('claim_goal') or '[PRETENSIÓN]'}.",},
        {'heading':'2. Hechos y dato controvertido','text':a.get('facts_detail') or '[HECHOS]','table':[('Problema principal',a.get('issue_type') or 'Pendiente'),('Estado obligación',a.get('obligation_status') or 'Pendiente'),('Inicio de mora',a.get('mora_start_date') or 'No informado'),('Pago o extinción',a.get('payment_or_extinction_date') or 'No informado'),('Fecha de reporte',a.get('report_date') or 'No informada'),('Valor aproximado',str(a.get('obligation_amount') if a.get('obligation_amount') not in (None,'') else 'No informado'))]},
        {'heading':'3. Fundamento de la reclamación','bullets':['El dato debe ser veraz, completo, exacto, actualizado, comprobable y comprensible.','La fuente debe conservar y exhibir soporte suficiente de la obligación y de cada novedad.','La comunicación previa, cuando es exigible, debe poder acreditarse con contenido, canal y fecha.','La permanencia, caducidad y oportunidad del primer reporte se revisan con cronología probada.','El reclamo no extingue por sí mismo una obligación válida.','En casos de suplantación, la Ley 2573 de 2026 tiene vigencia general desde el 20 de noviembre de 2026, salvo los parágrafos 1 y 2 del artículo 5 vigentes desde la promulgación; no se anticipan reglas diferidas.']},
        {'heading':'4. Pretensiones concretas','bullets':[a.get('claim_goal') or '[PRETENSIÓN PRINCIPAL]','Incluir la leyenda “reclamo en trámite” dentro del término aplicable.','Responder cada hecho y solicitud de fondo, con soportes legibles.','Corregir, actualizar, retirar o mantener motivadamente el dato, según proceda.','Comunicar la decisión y la novedad a los operadores y usuarios involucrados.','Informar recursos, canales y responsable de cumplimiento.']},
        {'heading':'5. Control de comunicación y umbral','table':[('Comunicación recibida',a.get('prior_communication_received') or 'Pendiente'),('Fecha comunicación',a.get('prior_communication_date') or 'No informada'),('Prueba',a.get('prior_communication_evidence') or 'Pendiente'),('Obligación pequeña preliminar','Sí' if c.get('small_obligation_preliminary') else 'No / no determinable'),('Dos comunicaciones',a.get('small_obligation_two_notices') or 'Pendiente'),('Referencia del umbral',str(c.get('small_obligation_reference_value') or 'Pendiente'))],'text':c.get('smmlv_parameter_status') or 'El parámetro económico debe revalidarse al momento de uso.'},
        {'heading':'6. Término, leyenda y traslado','table':[('Radicación',c.get('filing_date') or 'Pendiente'),('Vencimiento preliminar',c.get('preliminary_due_date') or 'Pendiente'),('Vencimiento con prórroga modelada',c.get('preliminary_due_with_extension') or 'Pendiente'),('Traslado preliminar',c.get('transfer_due_date') or 'Pendiente'),('Festivos descontados','No')],'bullets':['La prórroga no se presume: debe comunicarse y motivarse.','La leyenda y el traslado deben verificarse en la operación real.']},
        {'heading':'7. Anexos','bullets':['Documento de identidad minimizado.','Consulta del reporte o captura legible y fechada.','Contrato, título, extractos, paz y salvo o soportes disponibles.','Comunicación previa y prueba de envío o recepción.','Reclamo anterior, radicado y respuesta, si existen.','Evidencia de suplantación o daño, únicamente cuando corresponda.']},
        {'heading':'8. Notificaciones y firma','table':[('Correo',a.get('email') or '[CORREO]'),('Teléfono',a.get('phone') or '[TELÉFONO]'),('Dirección',a.get('address') or '[DIRECCIÓN]'),('Canal',a.get('filing_channel') or '[CANAL]')],'text':'Atentamente,\n\n__________________________________\n'+(a.get('data_subject_name') or '[TITULAR]')+'\n'+(a.get('data_subject_id') or '[IDENTIFICACIÓN]')},
        {'heading':'9. Advertencia','text':'Borrador sujeto a revisión de fechas, prueba, responsables y norma vigente. No garantiza retiro del reporte, aprobación de crédito ni decisión administrativa favorable.'},
    ]


def habeas_reiteration_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Actuación previa','table':[('Fuente u operador',a.get('source_name') or a.get('operator_name') or '[DESTINATARIO]'),('Fecha',a.get('prior_claim_date') or 'No informada'),('Radicado',a.get('prior_claim_radicado') or 'No informado'),('Reclamo completo',a.get('prior_claim_complete') or 'Pendiente'),('Respuesta',a.get('response_received') or 'Pendiente'),('Calidad',a.get('response_quality') or 'Pendiente'),('Prórroga',a.get('extension_notified') or 'Pendiente')]},
        {'heading':'2. Calendario preliminar','table':[('Vencimiento ordinario',c.get('prior_preliminary_due_date') or 'Pendiente'),('Vencimiento máximo modelado',c.get('prior_max_due_date') or 'Pendiente'),('Leyenda en trámite',c.get('claim_legend_due_date') or 'Pendiente'),('Término vencido preliminar','Sí' if c.get('prior_term_overdue_preliminary') else 'No / indeterminado'),('Silencio preliminar','Posible' if c.get('silence_acceptance_preliminary') else 'No establecido')],'text':'Ninguna conclusión debe usarse como definitiva sin acreditar recepción, integridad, prórroga, festivos y respuesta.'},
        {'heading':'3. Reiteración','bullets':['Incorporar de inmediato la leyenda de reclamo en trámite, si falta.','Responder de fondo cada hecho, soporte y pretensión pendiente.','Explicar la calidad de fuente, operador o usuario y efectuar el traslado oportuno cuando corresponda.','Entregar soporte de la obligación, comunicación previa y novedades reportadas.','Informar la ejecución concreta de la corrección, actualización o retiro decidido.']},
        {'heading':'4. Reserva sobre silencio','text':'Se deja constancia de la posible consecuencia legal del vencimiento únicamente como conclusión preliminar. La aceptación no debe declararse automáticamente si el reclamo era incompleto, hubo prórroga válida, traslado, respuesta o término especial.'},
        {'heading':'5. Anexos y notificación','bullets':['Reclamo inicial y constancia de recepción.','Respuesta parcial o insuficiente.','Consulta actualizada del dato.','Cronología y cálculo preliminar.'],'table':[('Correo',a.get('email') or '[CORREO]'),('Canal',a.get('filing_channel') or '[CANAL]')]},
    ]


def habeas_authority_escalation_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Evaluación de procedencia','table':[('Actuación principal',a.get('request_mode') or 'Pendiente'),('Actuación ante autoridad activa',a.get('authority_case_active') or 'Pendiente'),('Proceso judicial o insolvencia',a.get('judicial_or_insolvency') or 'Pendiente'),('Daño relevante o urgencia crediticia',a.get('high_damage_or_urgent_credit') or 'Pendiente'),('Múltiples fuentes',a.get('multiple_sources') or 'Pendiente'),('Suplantación',a.get('identity_theft') or 'Pendiente')]},
        {'heading':'2. Hechos y agotamiento previo','text':a.get('facts_detail') or '[HECHOS]','table':[('Reclamo previo',a.get('prior_claim') or 'Pendiente'),('Fecha',a.get('prior_claim_date') or 'No informada'),('Radicado',a.get('prior_claim_radicado') or 'No informado'),('Vencimiento preliminar',c.get('prior_max_due_date') or 'Pendiente'),('Respuesta',a.get('response_quality') or 'Pendiente')]},
        {'heading':'3. Peticiones sugeridas a la autoridad','bullets':['Verificar el cumplimiento de deberes de fuente, operador y usuario.','Ordenar la corrección, actualización, retiro, bloqueo o acreditación que jurídicamente corresponda.','Verificar comunicación previa, soporte, oportunidad del reporte, leyenda y respuesta al reclamo.','Adoptar medidas sobre seguridad, suplantación y circulación no autorizada cuando estén probadas.','Informar el trámite, competencia y canales de seguimiento.']},
        {'heading':'4. Selección de ruta','bullets':['SIC: evaluar competencia respecto del régimen de protección de datos y hábeas data financiero.','Superintendencia Financiera: evaluar competencia frente a entidades vigiladas y protección al consumidor financiero.','Fiscalía u otras autoridades: considerar solo ante suplantación, falsedad u otros hechos con relevancia penal.','Tutela o proceso judicial: requiere evaluación profesional individual, especialmente ante daño urgente o proceso activo.','No duplicar trámites sin informar actuaciones y decisiones existentes.']},
        {'heading':'5. Expediente mínimo','bullets':['Identidad y legitimación.','Consulta actual del reporte.','Soporte de obligación o prueba de su inexistencia.','Comunicación previa.','Reclamo, radicado, respuesta y cálculo de términos.','Evidencia de daño o suplantación.','Índice cronológico y copia minimizada de anexos.']},
        {'heading':'6. Bloqueo de automatización','text':'La selección final de autoridad, pretensiones, medidas urgentes y estrategia judicial exige revisión profesional cuando existen procesos activos, daño relevante, suplantación compleja o múltiples responsables.'},
    ]


def habeas_evidence_matrix_v232_sections(a, result):
    return [
        {'heading':'1. Identificación del expediente','table':_habeas_parties(a)},
        {'heading':'2. Matriz de evidencia','table':[('Elemento','Estado / acción'),('Consulta del reporte',a.get('report_support_available') or 'Pendiente'),('Soporte de obligación',a.get('source_obligation_support') or 'Pendiente'),('Comunicación previa',a.get('prior_communication_evidence') or 'Pendiente'),('Prueba de pago/extinción','Adjuntar si aplica'),('Reclamo y radicado',a.get('prior_claim_radicado') or 'No informado'),('Respuesta','Adjuntar completa y con metadatos'),('Leyenda en trámite',a.get('claim_legend_present') or 'Pendiente'),('Evidencia de suplantación','Preservar original si aplica')]},
        {'heading':'3. Cronología','table':[('Hito','Fecha'),('Inicio de mora',a.get('mora_start_date') or 'No informada'),('Comunicación previa',a.get('prior_communication_date') or 'No informada'),('Reporte',a.get('report_date') or 'No informada'),('Pago/extinción',a.get('payment_or_extinction_date') or 'No informada'),('Conocimiento',a.get('report_discovery_date') or 'No informada'),('Reclamo previo',a.get('prior_claim_date') or 'No informado'),('Respuesta',a.get('response_date') or 'No informada'),('Nueva radicación',a.get('filing_date') or 'No informada')]},
        {'heading':'4. Responsables y destinatarios','table':[('Rol','Identificación / control'),('Titular',a.get('data_subject_name') or 'Pendiente'),('Representante',a.get('representative_name') or 'No aplica'),('Fuente',a.get('source_name') or 'Por identificar'),('Operador',a.get('operator_name') or 'Por identificar'),('Usuario',a.get('user_entity_name') or 'No identificado'),('Autoridad','Definir según competencia')]},
        {'heading':'5. Integridad y privacidad','bullets':[f"Datos confirmados: {a.get('data_confirmed') or 'Pendiente'}.",f"Minimización: {a.get('data_minimized') or 'Pendiente'}.",'Conservar originales sin editar y copias de trabajo minimizadas.','Registrar fecha, origen, formato, hash cuando sea posible y responsable de custodia.','Ocultar datos no necesarios de terceros.']},
    ]


def habeas_deadline_calendar_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Términos de la actuación','table':[('Tipo',c.get('term_category') or 'Pendiente'),('Radicación',c.get('filing_date') or 'Pendiente'),('Vencimiento ordinario',c.get('preliminary_due_date') or 'Pendiente'),('Vencimiento con extensión',c.get('preliminary_due_with_extension') or 'Pendiente'),('Traslado preliminar',c.get('transfer_due_date') or 'Pendiente'),('Festivos descontados','No')]},
        {'heading':'2. Reclamo previo y leyenda','table':[('Fecha reclamo previo',c.get('prior_claim_date') or 'No aplica'),('Vencimiento ordinario',c.get('prior_preliminary_due_date') or 'No aplica'),('Vencimiento máximo',c.get('prior_max_due_date') or 'No aplica'),('Leyenda en trámite',c.get('claim_legend_due_date') or 'No aplica'),('Silencio preliminar','Posible' if c.get('silence_acceptance_preliminary') else 'No establecido')]},
        {'heading':'3. Comunicación y oportunidad del reporte','table':[('Inicio de mora',c.get('mora_start_date') or 'No informado'),('Límite de primer reporte',c.get('initial_report_limit_date') or 'No calculable'),('Fecha de reporte',c.get('report_date') or 'No informada'),('Reporte posterior a 18 meses','Sí, preliminar' if c.get('report_after_18_month_limit_preliminary') else 'No / indeterminado'),('Anticipación comunicación',str(c.get('communication_lead_calendar_days'))+' días' if c.get('communication_lead_calendar_days') is not None else 'No calculable')]},
        {'heading':'4. Permanencia y caducidad','table':[('Duración de mora',str(c.get('mora_duration_days'))+' días' if c.get('mora_duration_days') is not None else 'No calculable'),('Vencimiento dato pagado',c.get('paid_negative_expiry_preliminary') or 'No calculable'),('Caducidad dato insoluto',c.get('unpaid_negative_expiry_preliminary') or 'No calculable')],'text':'La caducidad del dato negativo no extingue la obligación y todas las fechas requieren soporte.'},
        {'heading':'5. Vigencia temporal del régimen de suplantación','table':[('Publicación Ley 2573 de 2026','20 de mayo de 2026'),('Vigencia general','20 de noviembre de 2026'),('Estado en la fecha de referencia',c.get('law_2573_status_at_reference') or 'Debe verificarse'),('Alcance inmediato',c.get('law_2573_immediate_scope') or 'Debe verificarse')],'text':'Antes de invocar una medida, debe comprobarse la fecha efectiva del caso, la vigencia aplicable, los condicionamientos de la Sentencia C-413 de 2025 y los protocolos expedidos por las autoridades.'},
        {'heading':'6. Tareas de seguimiento','bullets':['Guardar constancia completa de radicación y recepción.','Verificar leyenda en el operador dentro del hito aplicable.','Controlar respuesta, prórroga y traslado.','Obtener nueva consulta del reporte después de cada novedad.','Escalar únicamente con expediente completo y autoridad competente.']},
        {'heading':'7. Advertencias','bullets':list(c.get('assumptions') or ['Calendario preliminar sujeto a validación.'])},
    ]


def identity_theft_protocol_v232_sections(a, result):
    c=_habeas_calc(result)
    return [
        {'heading':'1. Activación','table':[('Suplantación alegada',a.get('identity_theft') or 'Pendiente'),('Complejidad',a.get('identity_theft_complex') or 'Pendiente'),('Múltiples fuentes',a.get('multiple_sources') or 'Pendiente'),('Daño urgente',a.get('high_damage_or_urgent_credit') or 'Pendiente'),('Proceso activo',a.get('judicial_or_insolvency') or 'Pendiente')]},
        {'heading':'2. Preservación inmediata','bullets':['Conservar consulta del reporte, alertas, correos, contratos, grabaciones y metadatos.','No modificar archivos originales; generar copias de trabajo.','Registrar fecha, canal, usuario, IP o dispositivo cuando esté disponible legítimamente.','Cambiar credenciales comprometidas y activar autenticación reforzada.','Evitar enviar cédulas completas por canales abiertos.']},
        {'heading':'3. Reclamaciones coordinadas','bullets':['Presentar reclamo individual a cada fuente y operador involucrado.','Solicitar bloqueo preventivo o leyenda mientras se verifica la identidad.','Exigir copia del contrato, solicitud, validaciones, desembolso, destino y trazabilidad.','Informar a usuarios o entidades afectadas por decisiones recientes.','Solicitar constancia escrita de corrección y cierre.']},
        {'heading':'4. Autoridades y medidas adicionales','bullets':['Evaluar denuncia penal cuando existan hechos de falsedad, fraude o uso de identidad.','Evaluar queja de protección de datos ante la autoridad competente.','Evaluar medidas urgentes si existe perjuicio actual y grave.','Coordinar con entidades financieras, comercios, operadores y proveedores de identidad.']},
        {'heading':'5. Régimen temporal Ley 2573 de 2026','table':[('Publicación','20 de mayo de 2026'),('Vigencia general','20 de noviembre de 2026'),('Estado aplicable',c.get('law_2573_status_at_reference') or 'Debe verificarse'),('Alcance inmediato',c.get('law_2573_immediate_scope') or 'Debe verificarse')],'bullets':['No invocar anticipadamente como obligatorias las disposiciones cuya vigencia general está diferida.','Aplicar los condicionamientos de la Sentencia C-413 de 2025, especialmente sobre carga dinámica de la prueba y competencias.','Verificar si ya fueron expedidos los protocolos interinstitucionales previstos por la ley.']},
        {'heading':'6. Control de escalamiento','text':'La suplantación compleja, múltiples productos, desembolsos, procesos judiciales o afectación relevante bloquean una salida automática definitiva y exigen estrategia jurídica individual.'},
        {'heading':'7. Registro de cierre','bullets':['Nueva consulta del reporte.','Respuestas y actos de corrección.','Confirmación de bloqueo de credenciales.','Relación de trámites y radicados.','Pendientes, responsables y fecha de próxima verificación.']},
    ]

def document_specs(case_id, code, answers, result, product, generated_at, question_rows):
    meta = base_metadata(case_id, code, product, result, generated_at)
    specs = [{
        'kind': 'traceability',
        'title': 'Ficha de diagnóstico y trazabilidad',
        'filename_suffix': 'ficha_trazabilidad',
        'subtitle': 'Expediente técnico-jurídico versionado',
        'sections': traceability_sections(code, answers, result, product, question_rows),
        'metadata': meta,
    }]
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
            {'kind':'contract','title':'Contrato de prestación de servicios independientes','filename_suffix':'contrato_servicios','subtitle':'Modelo completo v2.15 · documento personalizado','sections':v215.services_contract_sections(answers,result),'metadata':meta},
            {'kind':'scope','title':'Anexo No. 1 — Alcance, entregables y cronograma','filename_suffix':'anexo_alcance','subtitle':'Modelo completo v2.15 · anexo operativo','sections':v215.service_scope_sections(answers),'metadata':meta},
        ]
        if answers.get('confidentiality') == 'Sí':
            specs.append({'kind':'confidentiality','title':'Acuerdo de confidencialidad','filename_suffix':'acuerdo_confidencialidad','subtitle':'Módulo madurado v2.24','sections':v215.service_confidentiality_sections(answers),'metadata':meta})
        if answers.get('ip_relevant') == 'Sí':
            specs.append({'kind':'intellectual_property','title':'Anexo de propiedad intelectual','filename_suffix':'anexo_propiedad_intelectual','subtitle':'Módulo madurado v2.24','sections':v215.service_ip_sections(answers),'metadata':meta})
        if answers.get('personal_data') == 'Sí':
            specs.append({'kind':'data_processing','title':'Anexo de tratamiento de datos personales','filename_suffix':'anexo_tratamiento_datos','subtitle':'Módulo madurado v2.24','sections':v215.service_data_sections(answers),'metadata':meta})
        specs.append({'kind':'closure','title':'Acta de terminación y cierre','filename_suffix':'acta_cierre','subtitle':'Modelo completo v2.15 · cierre y trazabilidad','sections':v215.service_closure_sections(answers),'metadata':meta})
    elif code == 'CO-LA-001':
        specs += [
            {'kind':'calculation','title':'Informe técnico de liquidación laboral por concepto','filename_suffix':'informe_liquidacion','subtitle':'Modelo madurado v2.22 · períodos, pagos y fuentes por línea','sections':labor_report_sections(answers,result.get('calculation'),result),'metadata':meta},
            {'kind':'claim','title':'Reclamación directa de acreencias laborales','filename_suffix':'reclamacion_laboral','subtitle':'Modelo madurado v2.22 · reclamación trazable y documentada','sections':labor_claim_sections(answers,result.get('calculation')),'metadata':meta},
            {'kind':'evidence_matrix','title':'Matriz de soportes y conciliación de pagos','filename_suffix':'matriz_soportes','subtitle':'Modelo madurado v2.22 · cotejo por concepto','sections':labor_evidence_sections(answers,result.get('calculation'),result),'metadata':meta},
        ]
        if answers.get('generate_settlement') == 'Sí':
            specs.append({'kind':'settlement','title':'Propuesta de acuerdo de pago y cierre','filename_suffix':'propuesta_acuerdo','subtitle':'Módulo condicional v2.22 · sin renuncias generales','sections':labor_settlement_sections(answers,result.get('calculation')),'metadata':meta})
    elif code == 'CO-TR-001':
        specs += [
            {'kind':'sast_report','title':'Informe de coincidencia y diagnóstico SAST','filename_suffix':'informe_coincidencia_sast','subtitle':'Modelo madurado v2.26 · coincidencia preliminar y límites','sections':sast_mature_report_sections(answers,result),'metadata':meta},
            {'kind':'sast_verification_matrix','title':'Matriz individual de autorización y evidencia técnica','filename_suffix':'matriz_verificacion_sast','subtitle':'Modelo madurado v2.26 · punto, dispositivo y vigencia','sections':sast_verification_matrix_sections(answers,result),'metadata':meta},
            {'kind':'sast_record_request','title':'Solicitud de expediente técnico y acto de autorización','filename_suffix':'solicitud_expediente_autorizacion','subtitle':'Modelo madurado v2.26 · evidencia completa','sections':sast_record_request_sections(answers,result),'metadata':meta},
            {'kind':'sast_supertransport_request','title':'Solicitud de certificación del estado de la actuación oficial','filename_suffix':'solicitud_estado_supertransporte','subtitle':'Modelo madurado v2.26 · estado y efectos individualizados','sections':sast_supertransport_request_sections(answers,result),'metadata':meta},
            {'kind':'sast_conditional_review','title':'Solicitud condicionada de revisión administrativa','filename_suffix':'solicitud_revision_condicionada','subtitle':'Modelo madurado v2.26 · sin efectos automáticos','sections':sast_conditional_review_sections(answers,result),'metadata':meta},
            {'kind':'sast_alert_registry','title':'Registro de alertas y seguimiento','filename_suffix':'registro_alertas','subtitle':'Modelo madurado v2.26 · vigilancia trazable','sections':sast_alert_registry_sections(answers,result),'metadata':meta},
            {'kind':'sast_route_guide','title':'Guía de verificación, términos y escalamiento','filename_suffix':'guia_ruta_sast','subtitle':'Modelo madurado v2.26 · ruta operativa','sections':sast_route_guide_sections(answers,result),'metadata':meta},
        ]
    elif code == 'CO-TR-002':
        specs += [
            {'kind':'traffic_record_request','title':'Solicitud integral de expediente y preservación de evidencia','filename_suffix':'solicitud_expediente_evidencia','subtitle':'Modelo madurado v2.25 · expediente y prueba','sections':traffic_record_request_sections(answers,result),'metadata':meta},
            {'kind':'traffic_notice_claim','title':'Reclamación por notificación y debido proceso','filename_suffix':'reclamacion_notificacion','subtitle':'Modelo madurado v2.25 · afectación y etapa','sections':traffic_notice_claim_sections(answers,result),'metadata':meta},
            {'kind':'traffic_hearing_request','title':'Solicitud de audiencia, pruebas y contradicción','filename_suffix':'solicitud_audiencia_pruebas','subtitle':'Modelo madurado v2.25 · oportunidad procesal condicionada','sections':traffic_hearing_sections(answers,result),'metadata':meta},
            {'kind':'traffic_revocation_request','title':'Solicitud condicionada de revocatoria directa','filename_suffix':'revocatoria_directa_condicionada','subtitle':'Modelo madurado v2.25 · no revive términos','sections':traffic_revocation_sections(answers,result),'metadata':meta},
            {'kind':'traffic_registry_correction','title':'Solicitud de corrección y actualización SIMIT/RUNT','filename_suffix':'correccion_simit_runt','subtitle':'Modelo madurado v2.25 · registro conforme al expediente','sections':traffic_registry_sections(answers,result),'metadata':meta},
            {'kind':'traffic_technical_matrix','title':'Matriz técnica y probatoria del SAST','filename_suffix':'matriz_tecnica_sast','subtitle':'Modelo madurado v2.25 · autorización, calibración y señalización','sections':traffic_technical_matrix_sections(answers,result),'metadata':meta},
            {'kind':'traffic_escalation_guide','title':'Guía de términos, radicación y escalamiento','filename_suffix':'guia_terminos_escalamiento','subtitle':'Modelo madurado v2.25 · control operativo','sections':traffic_escalation_guide_sections(answers,result),'metadata':meta},
        ]
    elif code == 'CO-LA-002':
        need = answers.get('need_type') or 'Permanente'
        modality = {'Permanente':'indefinido','Temporal con fecha cierta':'fijo','Obra o labor específica':'obra'}.get(need,'indefinido')
        modality_title = {'indefinido':'Contrato de trabajo a término indefinido','fijo':'Contrato de trabajo a término fijo','obra':'Contrato de trabajo por obra o labor'}[modality]
        specs += [
            {'kind':'employment_contract','title':modality_title,'filename_suffix':'contrato_trabajo','subtitle':'Modelo madurado v2.24 · modalidad seleccionada por la necesidad real','sections':v215.employment_contract_sections(answers,result,modality),'metadata':meta},
            {'kind':'employment_functions_annex','title':'Anexo No. 1 — Perfil del cargo y matriz de funciones','filename_suffix':'anexo_funciones','subtitle':'Modelo madurado v2.24','sections':v215.employment_functions_annex(answers),'metadata':meta},
        ]
        if answers.get('variable_payments') not in (None,'','No'):
            specs.append({'kind':'employment_compensation_annex','title':'Anexo No. 2 — Compensación variable y beneficios','filename_suffix':'anexo_compensacion','subtitle':'Módulo madurado v2.24','sections':v215.employment_compensation_annex(answers),'metadata':meta})
        if answers.get('ip_relevant') == 'Sí' or answers.get('personal_data') in ('Sí','No sé') or answers.get('confidential_information') == 'Sí':
            specs.append({'kind':'employment_confidentiality_annex','title':'Anexo No. 3 — Confidencialidad, PI y datos','filename_suffix':'anexo_confidencialidad_pi_datos','subtitle':'Módulo madurado v2.24','sections':v215.employment_confidentiality_annex(answers),'metadata':meta})
        if answers.get('work_equipment') == 'Sí':
            specs.append({'kind':'employment_equipment_annex','title':'Anexo No. 4 — Equipos, activos y credenciales','filename_suffix':'anexo_equipos','subtitle':'Módulo madurado v2.24','sections':v215.employment_equipment_annex(answers),'metadata':meta})
        if answers.get('remote') not in (None,'','Presencial','No'):
            specs.append({'kind':'employment_remote_annex','title':'Anexo No. 5 — Modalidad no presencial','filename_suffix':'anexo_modalidad_no_presencial','subtitle':'Módulo madurado v2.24','sections':v215.employment_remote_annex(answers),'metadata':meta})
        specs.append({'kind':'employment_onboarding_checklist','title':'Lista de alistamiento, afiliaciones y cumplimiento','filename_suffix':'lista_alistamiento','subtitle':'Control operativo v2.24 · antes de inicio y firma','sections':employment_onboarding_checklist_sections(answers,result),'metadata':meta})
    elif code == 'CO-EM-004':
        is_bilateral = str(answers.get('nda_type') or '').lower().startswith('bi')
        specs += [
            {'kind':'nda','title':'Acuerdo de confidencialidad bilateral' if is_bilateral else 'Acuerdo de confidencialidad unilateral','filename_suffix':'acuerdo_confidencialidad','subtitle':'Modelo completo v2.15 · modalidad y finalidad delimitadas','sections':v215.nda_sections(answers,bilateral=is_bilateral),'metadata':meta},
            {'kind':'information_inventory','title':'Inventario de información y matriz de acceso','filename_suffix':'inventario_informacion_accesos','subtitle':'Modelo completo v2.15 · clasificación y mínimo privilegio','sections':v215.information_inventory_sections(answers),'metadata':meta},
        ]
        if answers.get('relationship_context') in ('Comercial/proveedor','Laboral/colaborador','Software/tecnología','Contenidos/creativo'):
            specs.append({'kind':'relationship_annex','title':'Anexo de confidencialidad según la relación','filename_suffix':'anexo_relacion','subtitle':'Módulo madurado v2.24','sections':v215.relationship_annex_sections(answers),'metadata':meta})
        if answers.get('preexisting_materials') in ('Sí','No sé') or answers.get('oss_components') in ('Sí','No sé') or answers.get('relationship_context') in ('Software/tecnología','Contenidos/creativo'):
            specs.append({'kind':'ip_annex','title':'Anexo de propiedad intelectual, antecedentes y OSS','filename_suffix':'anexo_pi_antecedentes_oss','subtitle':'Módulo madurado v2.24','sections':v215.ip_annex_sections(answers),'metadata':meta})
        if answers.get('personal_data') == 'Sí' or answers.get('crossborder') in ('Sí','No sé'):
            specs.append({'kind':'data_annex','title':'Anexo de datos personales y transferencias','filename_suffix':'anexo_datos_transferencias','subtitle':'Módulo madurado v2.24','sections':v215.data_annex_sections(answers),'metadata':meta})
        if answers.get('incident_protocol') == 'Sí' or answers.get('trade_secrets') in ('Sí','No sé'):
            specs.append({'kind':'incident_protocol','title':'Protocolo de incidentes de información','filename_suffix':'protocolo_incidentes','subtitle':'Módulo madurado v2.24','sections':v215.incident_protocol_sections(answers),'metadata':meta})
        specs.append({'kind':'closure_act','title':'Acta de devolución, eliminación y cierre','filename_suffix':'acta_cierre_confidencialidad','subtitle':'Modelo completo v2.15 · evidencia de cierre','sections':v215.closure_act_sections(answers),'metadata':meta})
    elif code == 'CO-AR-001':
        specs += [
            {'kind':'lease_contract','title':'Contrato de arrendamiento de vivienda urbana','filename_suffix':'contrato_arrendamiento','subtitle':'Modelo completo v2.23 · contrato residencial madurado','sections':v215.lease_contract_sections(answers),'metadata':meta},
            {'kind':'lease_inventory','title':'Inventario del inmueble y evidencia de estado','filename_suffix':'inventario_inmueble','subtitle':'Modelo completo v2.23 · anexo comparativo madurado','sections':v215.lease_inventory_sections(answers),'metadata':meta},
            {'kind':'delivery_act','title':'Acta de entrega del inmueble','filename_suffix':'acta_entrega','subtitle':'Modelo completo v2.23 · llaves, medidores y pendientes','sections':v215.delivery_act_sections(answers),'metadata':meta},
            {'kind':'restitution_act','title':'Acta de restitución y cierre','filename_suffix':'acta_restitucion','subtitle':'Modelo completo v2.23 · comparación y saldos','sections':v215.restitution_act_sections(answers),'metadata':meta},
            {'kind':'lease_guide','title':'Guía operativa de firma, ejecución y cierre','filename_suffix':'guia_arrendamiento','subtitle':'Modelo completo v2.23 · control de uso','sections':v215.lease_guide_sections(answers),'metadata':meta},
        ]
    elif code == 'CO-SA-001':
        specs += [
            {'kind':'health_petition','title':'Derecho de petición integral ante EPS o IPS','filename_suffix':'derecho_peticion_integral_salud','subtitle':'Solicitud estructurada, términos y controles v2.31','sections':health_petition_v231_sections(answers, result),'metadata':meta},
            {'kind':'medical_record_request','title':'Solicitud de historia clínica y entrega segura','filename_suffix':'solicitud_historia_clinica_segura','subtitle':'Acceso delimitado, legitimación y reserva','sections':medical_record_request_v231_sections(answers, result),'metadata':meta},
            {'kind':'health_reiteration','title':'Reiteración por falta o insuficiencia de respuesta','filename_suffix':'reiteracion_peticion_salud','subtitle':'Cronología, término preliminar y puntos pendientes','sections':health_reiteration_v231_sections(answers, result),'metadata':meta},
            {'kind':'supersalud_escalation','title':'Ruta y borrador de PQRD ante Supersalud','filename_suffix':'ruta_pqrd_supersalud','subtitle':'Escalamiento administrativo condicionado','sections':supersalud_escalation_v231_sections(answers, result),'metadata':meta},
            {'kind':'health_evidence_index','title':'Matriz de soportes, legitimación y privacidad','filename_suffix':'matriz_soportes_legitimacion','subtitle':'Control de identidad, evidencia y datos sensibles','sections':health_evidence_index_v231_sections(answers, result),'metadata':meta},
            {'kind':'health_deadline_calendar','title':'Calendario preliminar de términos y seguimiento','filename_suffix':'calendario_terminos_salud','subtitle':'Días hábiles, hitos y advertencias','sections':health_deadline_calendar_v231_sections(answers, result),'metadata':meta},
            {'kind':'health_filing_guide','title':'Guía de radicación, privacidad y seguimiento','filename_suffix':'guia_radicacion_salud','subtitle':'Preparación, constancia, seguridad y escalamiento','sections':health_filing_guide_v231_sections(answers, result),'metadata':meta},
        ]
    elif code == 'CO-CD-001':
        specs += [
            {'kind':'habeas_consultation','title':'Consulta integral del dato, fuente, usuarios y soportes','filename_suffix':'consulta_integral_habeas_data','subtitle':'Consulta, responsables, trazabilidad y términos v2.32','sections':habeas_consultation_v232_sections(answers, result),'metadata':meta},
            {'kind':'habeas_claim','title':'Reclamo integral de hábeas data financiero','filename_suffix':'reclamo_integral_habeas_data','subtitle':'Corrección, actualización, retiro o acreditación v2.32','sections':habeas_claim_v232_sections(answers, result),'metadata':meta},
            {'kind':'habeas_reiteration','title':'Reiteración, leyenda y control de silencio','filename_suffix':'reiteracion_control_silencio','subtitle':'Cronología y vencimiento preliminar v2.32','sections':habeas_reiteration_v232_sections(answers, result),'metadata':meta},
            {'kind':'habeas_authority_escalation','title':'Ruta y borrador de escalamiento ante autoridad','filename_suffix':'escalamiento_autoridad','subtitle':'Competencia, agotamiento y expediente v2.32','sections':habeas_authority_escalation_v232_sections(answers, result),'metadata':meta},
            {'kind':'habeas_evidence_matrix','title':'Matriz de evidencia, responsables y trazabilidad','filename_suffix':'matriz_evidencia_responsables','subtitle':'Cronología, custodia y minimización v2.32','sections':habeas_evidence_matrix_v232_sections(answers, result),'metadata':meta},
            {'kind':'habeas_deadline_calendar','title':'Calendario de términos, permanencia y caducidad','filename_suffix':'calendario_terminos_permanencia','subtitle':'Cálculos preliminares y seguimiento v2.32','sections':habeas_deadline_calendar_v232_sections(answers, result),'metadata':meta},
            {'kind':'identity_theft_protocol','title':'Protocolo de suplantación, alertas y preservación','filename_suffix':'protocolo_suplantacion','subtitle':'Preservación, reclamos y escalamiento v2.32','sections':identity_theft_protocol_v232_sections(answers, result),'metadata':meta},
        ]
    elif code == 'CO-CD-003':
        # El catálogo ofrece ocho tipos documentales, pero cada expediente solo
        # incorpora la comunicación sustantiva compatible con el mecanismo
        # seleccionado. Esto evita generar declaraciones de retracto, reversión,
        # débito periódico o falta de entrega cuando los hechos corresponden a
        # una garantía u otro mecanismo distinto.
        specs.append({'kind':'consumer_mechanism_diagnosis','title':'Diagnóstico jurídico del mecanismo de consumo','filename_suffix':'diagnostico_mecanismo_consumo','subtitle':'Clasificación, elegibilidad y términos v2.33','sections':consumer_mechanism_diagnosis_v233_sections(answers, result),'metadata':meta})
        mechanism_specs = {
            'Garantía legal': {'kind':'warranty_claim','title':'Reclamación directa de garantía legal','filename_suffix':'reclamacion_garantia_legal','subtitle':'Defecto, falla repetida y pretensiones compatibles v2.33','sections':warranty_claim_v233_sections(answers, result),'metadata':meta},
            'Derecho de retracto': {'kind':'withdrawal_notice','title':'Comunicación de ejercicio del derecho de retracto','filename_suffix':'ejercicio_retracto','subtitle':'Canal, término, excepciones y reembolso v2.33','sections':withdrawal_notice_v233_sections(answers, result),'metadata':meta},
            'Reversión del pago': {'kind':'payment_reversal_request','title':'Solicitud coordinada de reversión del pago','filename_suffix':'solicitud_reversion_pago','subtitle':'Causal, queja al proveedor y notificación al emisor v2.33','sections':payment_reversal_v233_sections(answers, result),'metadata':meta},
            'Revocación de débito periódico': {'kind':'recurring_debit_revocation','title':'Revocación de débito periódico y control de cargos','filename_suffix':'revocacion_debito_periodico','subtitle':'Cesación, cargos posteriores y trazabilidad v2.33','sections':recurring_debit_v233_sections(answers, result),'metadata':meta},
            'Terminación por falta de entrega': {'kind':'ecommerce_non_delivery_termination','title':'Terminación por falta de entrega y devolución','filename_suffix':'terminacion_falta_entrega','subtitle':'Comercio electrónico, cronología y devolución v2.33','sections':ecommerce_non_delivery_v233_sections(answers, result),'metadata':meta},
        }
        selected = mechanism_specs.get(answers.get('request_mode'))
        if selected:
            specs.append(selected)
        specs += [
            {'kind':'consumer_evidence_matrix','title':'Matriz de evidencia, pretensiones y destinatarios','filename_suffix':'matriz_evidencia_consumidor','subtitle':'Prueba, custodia, privacidad y radicación v2.33','sections':consumer_evidence_matrix_v233_sections(answers, result),'metadata':meta},
            {'kind':'consumer_deadline_calendar','title':'Calendario de términos y actuaciones de consumo','filename_suffix':'calendario_terminos_consumo','subtitle':'Reclamación, retracto, reversión y entrega v2.33','sections':consumer_deadline_calendar_v233_sections(answers, result),'metadata':meta},
        ]
    elif code == 'CO-CD-004':
        stage = answers.get('package_stage')
        specs += [
            {'kind':'debt_diagnostic','title':'Diagnóstico de obligación, título y ruta de cobro','filename_suffix':'diagnostico_obligacion','subtitle':'Exigibilidad, saldo, interés y controles v2.35 · revalidación M20','sections':debt_diagnostic_v234_sections(answers,result),'metadata':meta},
            {'kind':'account_statement','title':'Estado de cuenta conciliable y liquidación preliminar','filename_suffix':'estado_cuenta','subtitle':'Capital, abonos, cargos y tasa dinámica v2.35 · revalidación M20','sections':account_statement_v234_sections(answers,result),'metadata':meta},
            {'kind':'collection_evidence_matrix','title':'Matriz de evidencia, comunicaciones y trazabilidad','filename_suffix':'matriz_evidencia','subtitle':'Origen, saldo, cobranza, títulos y custodia v2.35 · revalidación M20','sections':collection_evidence_matrix_v234_sections(answers,result),'metadata':meta},
        ]
        if stage == 'Cobro inicial':
            specs.append({'kind':'collection_letter','title':'Requerimiento de pago y propuesta de solución','filename_suffix':'requerimiento_pago','subtitle':'Cobranza respetuosa, saldo y alternativas v2.35 · revalidación M20','sections':collection_letter_v234_sections(answers,result),'metadata':meta})
        if stage in ('Negociación','Formalización'):
            specs += [
                {'kind':'payment_agreement','title':'Acuerdo de pago integral','filename_suffix':'acuerdo_pago','subtitle':'Reconocimiento delimitado, cuotas y control v2.35 · revalidación M20','sections':payment_agreement_v234_sections(answers,result),'metadata':meta},
                {'kind':'payment_schedule','title':'Cronograma e imputación de cuotas','filename_suffix':'cronograma_cuotas','subtitle':'Seguimiento reproducible del plan v2.35 · revalidación M20','sections':payment_schedule_v234_sections(answers,result),'metadata':meta},
            ]
        if stage == 'Formalización' and answers.get('promissory_note_requested') == 'Sí':
            specs += [
                {'kind':'promissory_note','title':'Pagaré diligenciado y controlado','filename_suffix':'pagare','subtitle':'Título valor, vencimiento, tasa y firma v2.35 · revalidación M20','sections':promissory_note_v234_sections(answers,result),'metadata':meta},
                {'kind':'instruction_letter','title':'Carta de instrucciones para pagaré','filename_suffix':'carta_instrucciones','subtitle':'Límites de diligenciamiento y trazabilidad v2.35 · revalidación M20','sections':instruction_letter_v234_sections(answers,result),'metadata':meta},
            ]
        if stage == 'Seguimiento de pagos':
            specs.append({'kind':'payment_receipt','title':'Recibo de pago y actualización de saldo','filename_suffix':'recibo_pago','subtitle':'Imputación y saldo verificable v2.35 · revalidación M20','sections':payment_receipt_v234_sections(answers,result),'metadata':meta})
        if stage == 'Cierre':
            specs.append({'kind':'settlement_certificate','title':'Paz y salvo o constancia de cierre condicionada','filename_suffix':'paz_salvo','subtitle':'Extinción, títulos, reportes y reservas v2.35 · revalidación M20','sections':settlement_certificate_v234_sections(answers,result),'metadata':meta})
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
