from __future__ import annotations

"""Modelos jurídicos extensos para LegalAIZ.it v2.15.

Esta capa separa las plantillas maestras de los documentos personalizados y
conserva cláusulas completas, anexos activables y controles de publicación.
Los textos son candidatos jurídicos para validación por especialista, no
minutas publicadas para uso profesional irrestricto.
"""

from typing import Any

VERSION = "2.15"

ORDINALS = [
    "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
    "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
    "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
    "DÉCIMA SÉPTIMA", "DÉCIMA OCTAVA", "DÉCIMA NOVENA", "VIGÉSIMA",
    "VIGÉSIMA PRIMERA", "VIGÉSIMA SEGUNDA", "VIGÉSIMA TERCERA",
    "VIGÉSIMA CUARTA", "VIGÉSIMA QUINTA", "VIGÉSIMA SEXTA", "VIGÉSIMA SÉPTIMA",
    "VIGÉSIMA OCTAVA", "VIGÉSIMA NOVENA", "TRIGÉSIMA", "TRIGÉSIMA PRIMERA",
    "TRIGÉSIMA SEGUNDA",
]


def val(a: dict[str, Any], key: str, default: str) -> str:
    raw = a.get(key)
    if raw is None or raw == "":
        return default
    return str(raw)


def cop(raw: Any) -> str:
    try:
        amount = int(float(str(raw).replace(".", "").replace(",", ".")))
    except (TypeError, ValueError):
        return "COP $0"
    return "COP $" + f"{amount:,}".replace(",", ".")


def clause(index: int, title: str, text: str, *, bullets=None, table=None, page_break_before=False):
    return {
        "heading": f"CLÁUSULA {ORDINALS[index - 1]}. {title}",
        "text": text,
        "bullets": bullets or [],
        "table": table,
        "page_break_before": page_break_before,
        "clause_number": index,
    }


def intro(title: str, parties: str, considerations: list[str]):
    return [
        {
            "heading": title,
            "text": parties,
            "page_break_before": True,
        },
        {
            "heading": "CONSIDERACIONES",
            "bullets": considerations,
        },
    ]


def signature(a_name: str, a_label: str, b_name: str, b_label: str):
    return {
        "heading": "FIRMAS",
        "_type": "signature",
        "parties": [
            {"label": a_label, "name": a_name},
            {"label": b_label, "name": b_name},
        ],
    }


def publication_control(source: str, clauses: int, annexes: str, model_version: str | None = None):
    return {
        "heading": "CONTROL DE PUBLICACIÓN Y TRAZABILIDAD",
        "_type": "control",
        "text": (
            f"Modelo jurídico completo v{model_version or VERSION}. Fuente de reconstrucción: {source}. "
            f"Contiene {clauses} cláusulas y contempla {annexes}. Su estructura está habilitada para pruebas internas, "
            "comparación y personalización. El cierre jurídico corresponde al abogado responsable del alcance; "
            "QA valida implementación, integridad y presentación según el impacto del cambio. No se exige una segunda revisión jurídica genérica."
        ),
    }


# ---------------------------------------------------------------------------
# CO-EM-003 - PRESTACIÓN DE SERVICIOS
# ---------------------------------------------------------------------------

def services_contract_sections(a: dict[str, Any], result=None):
    contratante = val(a, "party_a", val(a, "employer_name", "Acme Innovación S.A.S."))
    contratista = val(a, "party_b", "Laura Gómez Consultoría")
    objeto = val(a, "object", "diseñar e implementar una solución de automatización documental")
    ciudad = val(a, "contract_city", "Medellín")
    fees = cop(a.get("fees") or 45_000_000)
    inicio = val(a, "start_date", "20 de julio de 2026")
    fin = val(a, "end_date", "20 de octubre de 2026")
    parties = (
        f"Entre {contratante}, debidamente identificado en la ficha contractual y denominado EL CONTRATANTE, y "
        f"{contratista}, debidamente identificado y denominado EL CONTRATISTA, se celebra en {ciudad} el presente "
        "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES. Las partes declaran capacidad, consentimiento libre "
        "y conocimiento de que la naturaleza del vínculo depende de su ejecución real."
    )
    secs = intro(
        "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES",
        parties,
        [
            f"EL CONTRATANTE requiere apoyo especializado para {objeto}, sin crear un cargo ni integrar al contratista a su estructura subordinada.",
            "EL CONTRATISTA declara contar con experiencia, organización, recursos y autonomía para ejecutar el encargo por su cuenta y riesgo.",
            "LAS PARTES desean documentar alcance, entregables, honorarios, aceptación, información, propiedad intelectual, datos y cierre.",
            "LAS PARTES reconocen la primacía de la realidad y se obligan a no implementar prácticas incompatibles con la autonomía declarada.",
        ],
    )
    texts = [
        ("OBJETO", f"EL CONTRATISTA se obliga a ejecutar con autonomía técnica, administrativa y operativa los servicios consistentes en {objeto}. El objeto se desarrolla exclusivamente mediante los entregables, hitos, exclusiones y criterios de aceptación definidos en el Anexo No. 1. Ninguna instrucción podrá convertir el objeto en una disponibilidad personal indefinida ni en la obligación genérica de realizar cualquier actividad que EL CONTRATANTE solicite."),
        ("ALCANCE Y ENTREGABLES", "El alcance comprende únicamente las actividades necesarias para producir los resultados identificados en el Anexo No. 1. Cada entregable tendrá responsable, formato, fecha o hito, dependencias, insumos del contratante y criterio objetivo de aceptación. Las solicitudes adicionales se tramitarán mediante control de cambios y no se entenderán incluidas por silencio, costumbre o comunicaciones informales."),
        ("AUTONOMÍA E INDEPENDENCIA", "EL CONTRATISTA organizará métodos, secuencia, recursos y tiempos de ejecución, respetando resultados, hitos, seguridad, coordinación y calidad pactados. No estará sujeto a reglamento interno, potestad disciplinaria, jornada laboral ni órdenes permanentes sobre la forma de trabajar. La coordinación contractual, la supervisión del resultado y las reuniones de seguimiento no constituyen por sí mismas subordinación."),
        ("LUGAR Y MEDIOS DE EJECUCIÓN", "Los servicios se ejecutarán principalmente con medios propios y desde los lugares definidos por EL CONTRATISTA, salvo accesos puntuales a instalaciones o sistemas del contratante. Cuando se entreguen equipos, credenciales o licencias se documentarán en acta, se limitarán al objeto y deberán devolverse al cierre. Los desplazamientos extraordinarios requieren autorización y definición previa de gastos."),
        ("PLAZO", f"El contrato inicia el {inicio} y termina el {fin}, sin perjuicio de terminación anticipada o prórroga escrita. El vencimiento no transforma automáticamente el vínculo en indefinido: toda ampliación debe indicar necesidad, plazo, entregables restantes y efectos económicos. La ejecución posterior sin adenda será documentada y revisada antes de generar obligaciones nuevas."),
        ("HONORARIOS", f"EL CONTRATANTE pagará honorarios totales de {fees}, incluidos los costos ordinarios del contratista salvo gastos expresamente aprobados. El valor corresponde al alcance definido y no remunera disponibilidad personal, jornada ni exclusividad general. Los impuestos, retenciones y obligaciones propias se aplicarán conforme a la calidad tributaria acreditada por cada parte."),
        ("FACTURACIÓN Y PAGO", f"El pago seguirá el esquema {val(a, 'payment_scheme', 'anticipo e hitos contra aceptación')}. Cada cobro deberá acompañarse de factura o cuenta de cobro, soporte del hito y certificaciones exigibles. EL CONTRATANTE pagará dentro del plazo pactado contado desde la recepción completa. Las observaciones deberán ser específicas y no podrán utilizarse para retener sumas no discutidas."),
        ("ACEPTACIÓN DE ENTREGABLES", f"EL CONTRATANTE contará con {val(a, 'acceptance_days', 'cinco (5)')} días hábiles para revisar cada entrega. La aceptación podrá ser expresa o derivarse del uso productivo sin reserva, salvo defectos ocultos. Si existen observaciones, deberá indicar el criterio incumplido y permitir una corrección razonable. Las preferencias nuevas o cambios de alcance no se tratarán como defectos."),
        ("OBLIGACIONES DEL CONTRATISTA", "EL CONTRATISTA deberá ejecutar diligentemente, mantener personal idóneo, informar riesgos, proteger activos e información, conservar soportes, cumplir normas aplicables a su actividad y corregir incumplimientos verificables. No garantizará resultados que dependan de terceros, información incompleta o decisiones exclusivas del contratante, pero deberá advertir oportunamente dichas dependencias."),
        ("OBLIGACIONES DEL CONTRATANTE", "EL CONTRATANTE suministrará información, accesos, decisiones, retroalimentación y responsables dentro de los tiempos acordados; pagará oportunamente; verificará que puede compartir datos y materiales; y no impondrá prácticas de subordinación. Los retrasos imputables al contratante ajustarán el cronograma y podrán generar costos demostrables si afectan recursos reservados."),
        ("GOBIERNO Y SEGUIMIENTO", "Las partes designarán responsables contractuales con facultad para coordinar, aceptar y aprobar cambios dentro de los límites asignados. Las reuniones producirán minutas o registros de decisiones. Ningún responsable operativo podrá modificar honorarios, propiedad intelectual, responsabilidad, plazo final o terminación sin documento escrito autorizado."),
        ("CONTROL DE CAMBIOS", "Todo cambio se describirá por escrito con justificación, impacto en entregables, cronograma, costos, riesgos, datos y propiedad intelectual. El contratista no estará obligado a iniciar el cambio antes de su aprobación. En urgencias, las partes podrán emitir autorización provisional con alcance y tope económico definidos, que deberá formalizarse posteriormente."),
        ("PERSONAL Y SUBCONTRATACIÓN", "EL CONTRATISTA podrá apoyarse en colaboradores bajo su dirección y responsabilidad cuando la naturaleza del servicio lo permita. El acceso de terceros a información, datos o sistemas requiere autorización previa y obligaciones equivalentes. La subcontratación no crea vínculo entre EL CONTRATANTE y el personal del contratista ni libera a este de responder por sus entregables."),
        ("SEGURIDAD SOCIAL Y OBLIGACIONES PROPIAS", "Cada parte atenderá las obligaciones laborales, de seguridad social, tributarias y administrativas que correspondan a su organización y personal. Cuando la ley exija soportes para efectuar pagos o permitir acceso a instalaciones, se solicitarán de manera proporcional. La revisión documental no implica dirección laboral sobre EL CONTRATISTA."),
        ("CONFIDENCIALIDAD", "La información no pública recibida para el contrato se usará únicamente para su ejecución, con acceso limitado y medidas razonables. Las categorías, exclusiones, plazo, devolución, incidentes y excepciones legales se desarrollan en el anexo aplicable. La confidencialidad no prohíbe denuncias, ejercicio de derechos, colaboración con autoridades ni uso de conocimientos generales."),
        ("PROTECCIÓN DE DATOS PERSONALES", "Si EL CONTRATISTA trata datos por cuenta de EL CONTRATANTE, las partes identificarán roles, finalidades, instrucciones, categorías, titulares, medidas, subencargados, incidentes, transferencias y eliminación. El contratista no utilizará los datos para fines propios ni los cargará a herramientas no autorizadas. Un acuerdo de confidencialidad no sustituye el módulo de datos requerido."),
        ("PROPIEDAD INTELECTUAL", "Los materiales preexistentes, herramientas generales y componentes de terceros conservarán su titularidad original. Los derechos sobre entregables nuevos se regirán por la modalidad expresamente seleccionada en el anexo: cesión o licencia. Se delimitarán modalidades de explotación, territorio, plazo, remuneración y momento de transferencia. Los derechos morales permanecen en cabeza del autor."),
        ("SOFTWARE, CÓDIGO ABIERTO Y TERCEROS", "Cuando exista software, el contratista mantendrá inventario de repositorios, autores, dependencias, versiones, licencias, servicios, modelos, datos y materiales preexistentes. No se entenderán cedidos componentes que no pueda transferir. Las licencias copyleft, obligaciones de atribución, límites de APIs y dependencias críticas deberán revelarse antes de la aceptación."),
        ("SEGURIDAD DE LA INFORMACIÓN", "Las partes aplicarán mínimo privilegio, autenticación adecuada, cifrado o canales seguros, copias controladas, gestión de vulnerabilidades y revocación de accesos. Todo incidente se reportará sin demora indebida por el canal designado, preservando evidencia. El reporte oportuno no equivale a reconocimiento automático de responsabilidad."),
        ("CUMPLIMIENTO Y ÉTICA", "Cada parte declara que ejecutará el contrato con recursos lícitos y de acuerdo con las normas aplicables. No ofrecerá pagos indebidos, falsificará soportes, infringirá derechos de terceros ni utilizará información obtenida ilícitamente. La parte que detecte una situación material deberá informar y adoptar medidas razonables de contención."),
        ("GARANTÍAS DEL SERVICIO", "EL CONTRATISTA garantiza que prestará el servicio con diligencia profesional y corregirá defectos atribuibles que sean notificados oportunamente. Salvo pacto expreso, no garantiza compatibilidad ilimitada con sistemas no informados, continuidad de servicios de terceros ni un resultado comercial específico. Las garantías legales imperativas prevalecen sobre cualquier limitación."),
        ("RESPONSABILIDAD", "Cada parte responderá por daños directos, previsibles y demostrados derivados de incumplimiento imputable. La distribución de riesgos deberá ser proporcional al objeto, valor, control y seguro disponible. No se limitará responsabilidad por dolo, culpa grave, afectación ilícita de datos, infracción de derechos de terceros o supuestos que la ley no permita excluir."),
        ("FUERZA MAYOR", "La parte afectada por un evento irresistible e imprevisible informará oportunamente, explicará impacto, mitigará consecuencias y reanudará cuando sea posible. El evento no exonera obligaciones ya causadas ni pagos por entregables aceptados. Si la suspensión supera el período acordado, cualquiera podrá solicitar ajuste o terminación ordenada."),
        ("SUSPENSIÓN", "Las partes podrán suspender temporalmente por seguridad, incumplimiento subsanable, falta de insumos críticos o decisión conjunta. El acta de suspensión registrará fecha, causas, custodia de información, costos, obligaciones que continúan y condiciones de reinicio. La suspensión no podrá convertirse en disponibilidad indefinida no remunerada."),
        ("TERMINACIÓN", "El contrato terminará por vencimiento, cumplimiento, mutuo acuerdo, incumplimiento esencial no subsanado, imposibilidad prolongada o las demás causas legales. La parte que invoque incumplimiento describirá hechos, soportes y plazo de corrección cuando proceda. La terminación no afecta pagos causados, confidencialidad, datos, propiedad intelectual ni obligaciones de cierre."),
        ("TERMINACIÓN ANTICIPADA SIN CAUSA", "Cuando se haya habilitado esta opción, cualquiera podrá terminar mediante preaviso escrito razonable. EL CONTRATANTE pagará entregables aceptados, trabajo verificable en curso y compromisos no cancelables previamente autorizados. EL CONTRATISTA entregará avances útiles y devolverá saldos o bienes que correspondan. No habrá penalidad automática desproporcionada."),
        ("CIERRE, ENTREGA Y TRANSICIÓN", "Al cierre se realizará inventario de entregables, pendientes, accesos, datos, equipos, repositorios y documentos. Las partes firmarán acta con aceptación, reservas específicas y obligaciones posteriores. El contratista prestará transición dentro del alcance contratado; cualquier soporte adicional se acordará separadamente."),
        ("SOLUCIÓN DE CONTROVERSIAS", "Las partes intentarán una negociación directa documentada antes de acudir al mecanismo pactado. Podrán utilizar conciliación u otros mecanismos legalmente admisibles. La cláusula no impedirá solicitar medidas urgentes, ejercer derechos laborales o de datos, ni acudir a autoridades competentes cuando la ley así lo permita."),
        ("NOTIFICACIONES", "Las comunicaciones contractuales se enviarán a los canales registrados y se entenderán recibidas conforme a la evidencia técnica disponible, sin sustituir formalidades especiales. Cada parte actualizará oportunamente sus datos. Las decisiones sobre cambios, incumplimiento y terminación deberán conservar contenido íntegro, fecha y remitente identificable."),
        ("INTEGRIDAD, PRELACIÓN Y MODIFICACIONES", "El contrato, sus anexos y adendas conforman el acuerdo. En caso de contradicción prevalecerán normas imperativas, luego el contrato, adendas posteriores y anexos en su materia. Las políticas unilaterales no modificarán elementos esenciales. La nulidad de una estipulación no afectará las demás cuando puedan subsistir."),
        ("LEY APLICABLE Y FIRMA", f"El contrato se rige por las leyes de Colombia y se firma en {ciudad}. Podrá suscribirse física o electrónicamente mediante mecanismo que identifique a los firmantes, exprese aprobación y preserve integridad. Cada parte recibirá copia completa del contrato y anexos activados, con versión y trazabilidad de generación."),
    ]
    for i, (title, text) in enumerate(texts, 1):
        secs.append(clause(i, title, text, page_break_before=i in (11, 21)))
    secs.extend([
        signature(contratante, "EL CONTRATANTE", contratista, "EL CONTRATISTA"),
        publication_control("LegalAIZit_Paquete_01_Prestacion_de_Servicios_v1", len(texts), "alcance, confidencialidad, PI, datos y cierre"),
    ])
    return secs


def service_scope_sections(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 1 - ALCANCE, ENTREGABLES Y CRONOGRAMA", "text": "Este anexo individualiza el resultado contratado y prevalece sobre descripciones comerciales generales."},
        {"heading": "1. Objetivo verificable", "text": val(a, "object", "Diseñar e implementar una solución de automatización documental con trazabilidad y documentación técnica.")},
        {"heading": "2. Entregables", "table": [("Entregable", "Criterio de aceptación"), ("Diagnóstico y mapa funcional", "Cobertura, decisiones y riesgos documentados"), ("Prototipo funcional", "Flujos principales ejecutables"), ("Documentación", "Arquitectura, operación y transferencia"), ("Cierre", "Acta, inventario y accesos entregados")]},
        {"heading": "3. Exclusiones", "bullets": ["Desarrollos o integraciones no descritos.", "Licencias, infraestructura o servicios de terceros no presupuestados.", "Soporte indefinido posterior a la aceptación.", "Decisiones jurídicas o de negocio reservadas al contratante."]},
        {"heading": "4. Dependencias del contratante", "bullets": ["Entregar información completa y legítimamente utilizable.", "Designar responsables y responder observaciones.", "Autorizar accesos, pruebas y decisiones dentro del cronograma.", "Validar seguridad y privacidad cuando se traten datos."]},
        {"heading": "5. Cronograma e hitos", "table": [("Hito", "Fecha/condición"), ("Inicio", val(a, "start_date", "20 de julio de 2026")), ("Diseño", "Dos semanas desde la entrega completa de insumos"), ("Prototipo", "Sexta semana"), ("Aceptación", val(a, "acceptance_days", "Cinco días hábiles por entrega")), ("Cierre", val(a, "end_date", "20 de octubre de 2026"))]},
        {"heading": "6. Control de cambios", "text": "Toda modificación registrará descripción, motivo, impacto, valor, plazo, riesgos, datos y propiedad intelectual. No se ejecutará antes de aprobación escrita."},
        {"heading": "7. Matriz de responsables", "table": [("Actividad", "Responsable"), ("Información y decisiones", "EL CONTRATANTE"), ("Ejecución técnica", "EL CONTRATISTA"), ("Pruebas y aceptación", "Ambas partes"), ("Aprobación jurídica", "Especialista designado")]},
        {"heading": "8. Evidencias", "bullets": ["Repositorio o ubicación autorizada.", "Minutas y decisiones.", "Versiones entregadas.", "Pruebas y aceptación.", "Inventario de terceros y licencias."]},
        publication_control("Paquete 01 - Anexo de alcance", 0, "matriz, cronograma y control de cambios"),
    ]


def service_confidentiality_sections(a: dict[str, Any]):
    return nda_sections({
        "party_a": val(a, "party_a", "Acme Innovación S.A.S."),
        "party_b": val(a, "party_b", "Laura Gómez Consultoría"),
        "purpose": val(a, "object", "ejecutar el contrato de prestación de servicios"),
        "nda_type": "unilateral",
        "trade_secrets": "Sí",
        "personal_data": val(a, "personal_data", "Sí"),
        "duration_years": "5",
    }, bilateral=False, source="Paquete 01 - módulo de confidencialidad")


def service_ip_sections(a: dict[str, Any]):
    return ip_annex_sections({
        "party_a": val(a, "party_a", "Acme Innovación S.A.S."),
        "party_b": val(a, "party_b", "Laura Gómez Consultoría"),
        "relationship_context": "Software/tecnología",
        "preexisting_materials": "Sí",
        "oss_components": "Sí",
        "ip_mode": "Cesión delimitada de entregables nuevos",
    }, source="Paquete 01 - módulo de propiedad intelectual")


def service_data_sections(a: dict[str, Any]):
    return data_annex_sections({
        "party_a": val(a, "party_a", "Acme Innovación S.A.S."),
        "party_b": val(a, "party_b", "Laura Gómez Consultoría"),
        "personal_data": val(a, "personal_data", "Sí"),
        "crossborder": "No",
    }, source="Paquete 01 - módulo de datos")


def service_closure_sections(a: dict[str, Any]):
    return [
        {"heading": "ACTA DE TERMINACIÓN, ENTREGA Y CIERRE", "text": f"Contrato entre {val(a, 'party_a', 'Acme Innovación S.A.S.')} y {val(a, 'party_b', 'Laura Gómez Consultoría')}."},
        {"heading": "1. Estado del objeto", "table": [("Componente", "Estado"), ("Entregables", "Recibidos / con reservas detalladas"), ("Cambios", "Cerrados / pendientes"), ("Pagos", "Conciliados"), ("Garantías", "Vigentes según contrato")]},
        {"heading": "2. Inventario de entrega", "bullets": ["Documentos y archivos.", "Repositorios, ramas y versiones.", "Credenciales transferidas o revocadas.", "Materiales preexistentes y licencias.", "Bases de datos y copias autorizadas."]},
        {"heading": "3. Información y datos", "text": "La parte receptora devuelve o elimina copias según instrucciones, salvo retención legal identificada. Se documentan respaldos, plazo de depuración, responsables y restricciones."},
        {"heading": "4. Propiedad intelectual", "text": "Se identifican entregables aceptados, modalidad de derechos, componentes excluidos, atribuciones, licencias y evidencia de pago o condición de transferencia."},
        {"heading": "5. Reservas", "text": "Toda reserva se describe con hecho, soporte, impacto, responsable y fecha de cierre. No se aceptan reservas genéricas ni paz y salvos que eliminen derechos indisponibles."},
        {"heading": "6. Obligaciones posteriores", "bullets": ["Confidencialidad y seguridad.", "Garantías y corrección.", "Soporte de transición contratado.", "Conservación de evidencia.", "Pagos y facturación final."]},
        signature(val(a, "party_a", "Acme Innovación S.A.S."), "EL CONTRATANTE", val(a, "party_b", "Laura Gómez Consultoría"), "EL CONTRATISTA"),
        publication_control("Paquete 01 - acta de cierre", 0, "inventario, PI, datos y reservas"),
    ]


# ---------------------------------------------------------------------------
# CO-AR-001 - ARRENDAMIENTO VIVIENDA URBANA
# ---------------------------------------------------------------------------

def lease_contract_sections(a: dict[str, Any]):
    landlord = val(a, "landlord_name", val(a, "landlord", val(a, "party_a", "María Rodríguez")))
    tenant = val(a, "tenant_name", val(a, "tenant", val(a, "party_b", "Juan Pérez")))
    address = val(a, "property_address", val(a, "property", "Carrera 45 No. 10-25, apartamento 502, Medellín"))
    canon = cop(a.get("monthly_rent") or a.get("rent") or 2_500_000)
    parties = f"Entre {landlord}, EL ARRENDADOR, y {tenant}, EL ARRENDATARIO, se celebra contrato de arrendamiento de vivienda urbana sobre el inmueble ubicado en {address}."
    secs = intro(
        "CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA",
        parties,
        [
            "EL ARRENDADOR declara ser titular, poseedor legítimo o estar autorizado para entregar el goce del inmueble.",
            "EL ARRENDATARIO ha revisado las condiciones visibles, sin renunciar a garantías de seguridad, sanidad y defectos ocultos.",
            "LAS PARTES documentarán inventario, medidores, llaves, servicios, expensas, reparaciones, terminación y restitución.",
            "Toda estipulación se interpretará conforme al régimen imperativo de vivienda urbana y la buena fe contractual.",
        ],
    )
    texts = [
        ("OBJETO Y CLASIFICACIÓN", "EL ARRENDADOR concede a EL ARRENDATARIO el goce del inmueble exclusivamente para vivienda, y este se obliga a pagar el canon y cumplir las obligaciones pactadas. La clasificación individual o mancomunada se ajustará a las partes reales y a la solidaridad legal aplicable."),
        ("IDENTIFICACIÓN DEL INMUEBLE", f"El inmueble se ubica en {address} e incluye las áreas privadas, parqueadero, cuarto útil, depósitos, servicios o usos conexos descritos en el inventario. Los datos registrales individualizan el bien y no sustituyen un estudio de títulos."),
        ("DESTINACIÓN Y OCUPANTES", "El inmueble se destina a habitación del arrendatario y ocupantes autorizados. No podrá usarse para hospedaje por días, plataforma turística, establecimiento abierto al público, bodega, actividad ilícita o uso contrario a propiedad horizontal. Las mascotas se sujetarán a reglas razonables y al reglamento aplicable."),
        ("PLAZO", f"El contrato tendrá duración de {val(a, 'duration_months', 'doce (12)')} meses desde {val(a, 'start_date', '1 de agosto de 2026')}. Las prórrogas, preavisos y terminaciones se regirán por la ley. Ninguna comunicación informal reemplaza el aviso escrito exigible."),
        ("CANON", f"El canon mensual es {canon}, pagadero por períodos anticipados dentro de los primeros {val(a, 'payment_day', 'cinco (5)')} días calendario mediante el canal registrado. El arrendador entregará recibo o evidencia. El canon no incluye conceptos que deban identificarse separadamente."),
        ("LÍMITE Y REAJUSTE", "El canon y su reajuste deberán respetar los límites legales. El reajuste solo procederá en la periodicidad y porcentaje permitidos y será comunicado por canal verificable. La falta de información para validar el límite genera advertencia y revisión, no una presunción de legalidad."),
        ("ADMINISTRACIÓN Y EXPENSAS", "Las expensas ordinarias de administración serán asumidas por la parte indicada en la ficha económica. Las extraordinarias corresponden al propietario salvo acuerdo jurídicamente válido y revisado. Multas de propiedad horizontal solo se trasladarán cuando exista decisión, soporte, imputación y oportunidad de contradicción."),
        ("SERVICIOS PÚBLICOS", "EL ARRENDATARIO pagará oportunamente los consumos a su cargo y entregará soportes al cierre. Las garantías relacionadas con servicios se constituirán únicamente bajo el régimen aplicable y a favor de las empresas prestadoras cuando proceda. No se pactará depósito en dinero a favor del arrendador para garantizar obligaciones generales."),
        ("ENTREGA", "La entrega se realizará mediante acta e inventario con estado de muros, pisos, techos, redes, equipos, muebles, llaves, medidores y evidencia fotográfica. Las novedades, obras pendientes y plazos de corrección quedarán individualizados. Defectos graves de seguridad o sanidad bloquean la entrega estándar."),
        ("OBLIGACIONES DEL ARRENDADOR", "EL ARRENDADOR entregará el inmueble en estado apto, mantendrá el goce pacífico, realizará reparaciones a su cargo, entregará copia del contrato y reglamento aplicable, respetará la privacidad y recibirá pagos por canales trazables. Informará cambios de propietario, administrador o cuenta de pago de forma verificable."),
        ("OBLIGACIONES DEL ARRENDATARIO", "EL ARRENDATARIO pagará canon y conceptos válidos, cuidará el inmueble, atenderá reparaciones locativas imputables, avisará daños, permitirá visitas coordinadas, cumplirá convivencia y devolverá en el estado recibido salvo desgaste normal. No modificará redes o estructura sin autorización."),
        ("REPARACIONES NECESARIAS", "Las reparaciones necesarias para conservar habitabilidad, seguridad y funcionamiento corresponden a quien determine la ley y la causa del daño. El arrendatario reportará oportunamente y permitirá diagnóstico. En urgencia podrá adoptar medidas razonables de contención, conservando evidencia y coordinando la reparación definitiva."),
        ("REPARACIONES LOCATIVAS Y DAÑOS", "El arrendatario responde por daños imputables a uso indebido propio, de ocupantes o visitantes, debidamente comparados con el inventario. No se le cobrará desgaste natural, vicios, antigüedad o daños estructurales no imputables. Todo cobro requiere diagnóstico, soporte y oportunidad de contradicción."),
        ("MEJORAS Y MODIFICACIONES", "Las mejoras o modificaciones requieren autorización escrita que defina alcance, licencias, costos, retiro y compensación. La autorización de una obra no implica obligación de reembolso salvo pacto expreso. No se podrán ejecutar obras que afecten estructura, redes, fachada o bienes comunes sin permisos."),
        ("PROPIEDAD HORIZONTAL", "EL ARRENDATARIO recibirá el reglamento y manuales relevantes, respetará bienes comunes, horarios y seguridad. EL ARRENDADOR conservará sus obligaciones como propietario ante la copropiedad. Las restricciones deberán ser compatibles con la ley y no podrán desconocer derechos fundamentales."),
        ("VISITAS E INSPECCIONES", "EL ARRENDADOR o su delegado podrá verificar el inmueble mediante aviso y coordinación razonable, salvo emergencia real. No se autoriza ingreso libre, retención de llaves para acceder sin consentimiento ni vigilancia invasiva. La visita se limitará a su finalidad y respetará intimidad y datos."),
        ("CESIÓN Y SUBARRIENDO", "La cesión, subarriendo, hospedaje o explotación por plataformas requerirá autorización y cumplimiento normativo. Si la finalidad real es turística, comercial o de alojamiento por días, este modelo no resulta aplicable y debe utilizarse un producto especializado."),
        ("CONVIVENCIA Y ACTIVIDADES PROHIBIDAS", "Los ocupantes deberán evitar ruidos, riesgos, afectaciones, actividades ilícitas y usos incompatibles. Las quejas se tramitarán con soportes y debido proceso de la copropiedad. Una acusación no demostrada no habilita terminación o cobros automáticos."),
        ("SEGUROS Y RIESGOS", "Las partes identificarán seguros existentes y responsabilidades. El seguro del inmueble no sustituye el aseguramiento de contenidos del arrendatario ni altera la imputación legal. Los siniestros se informarán de inmediato, preservando evidencia y evitando admisiones no autorizadas."),
        ("MORA", "La mora se configura conforme a la obligación y vencimiento. Los intereses o cobros solo procederán dentro de límites legales, sobre sumas exigibles y por el tiempo real. No se capitalizarán ni duplicarán conceptos. Los gastos de cobro deben ser razonables, demostrados y jurídicamente procedentes."),
        ("TERMINACIÓN POR EL ARRENDADOR", "Las causales, preavisos, indemnizaciones y formalidades para terminar por parte del arrendador serán las legales. La comunicación identificará causal, fecha y soporte. No se utilizarán cláusulas abiertas para crear causales distintas ni mecanismos de hecho para recuperar el inmueble."),
        ("TERMINACIÓN POR EL ARRENDATARIO", "EL ARRENDATARIO podrá terminar conforme a causales, preaviso y efectos legales. La entrega material se coordinará mediante acta. La imposibilidad injustificada del arrendador de recibir llaves deberá documentarse y gestionarse por mecanismos jurídicos, sin abandonar el inmueble de manera insegura."),
        ("TERMINACIÓN DE MUTUO ACUERDO", "Las partes podrán terminar por acuerdo escrito que defina fecha, pagos, reparaciones, facturas pendientes, entrega, llaves y reservas. El acuerdo no validará depósitos prohibidos ni renuncias generales. La conciliación de saldos se soportará en documentos verificables."),
        ("RESTITUCIÓN", "Al finalizar, EL ARRENDATARIO restituirá inmueble, llaves y accesorios mediante acta comparativa con el inventario inicial. Se registrarán lectura de medidores, aseo, daños, desgaste normal, bienes retirados y evidencia. Las diferencias se cuantificarán con soportes y no autorizarán retener sumas inexistentes como depósito."),
        ("FACTURAS FINALES", "Cuando servicios o administración no estén facturados a la fecha de entrega, el acta podrá dejar una reserva documental por conceptos y períodos definidos. La reserva no opera como depósito ni autoriza cobros estimados sin factura. Cada parte atenderá y acreditará las obligaciones que le correspondan."),
        ("TRATAMIENTO DE DATOS", "Los datos de partes, ocupantes, codeudores y contactos se tratarán para celebrar, ejecutar, cobrar y cerrar el contrato, conforme a la política aplicable. Datos sensibles, biométricos o de menores requieren necesidad y controles reforzados. No se publicarán deudas o conflictos en grupos o redes sociales."),
        ("NOTIFICACIONES", "Las partes registran direcciones físicas y electrónicas y se obligan a actualizarlas. Las comunicaciones conservarán contenido, remitente, fecha y evidencia de entrega. Cuando la ley exija servicio postal u otra formalidad, el mensaje electrónico no la sustituirá salvo habilitación jurídica."),
        ("SOLUCIÓN DE CONTROVERSIAS", "Las partes procurarán negociación y conciliación, sin impedir acciones urgentes, restitución, cobro o medidas legalmente procedentes. No se pactan vías de hecho, ingreso forzado, corte de servicios, retención de bienes ni exposición pública como mecanismos de presión."),
        ("INTEGRIDAD Y FIRMA", "El contrato, inventario, actas, reglamento entregado y adendas integran el acuerdo. Las modificaciones deberán ser escritas y compatibles con normas imperativas. Podrá firmarse física o electrónicamente con identificación, aprobación e integridad, y cada parte recibirá copia completa."),
    ]
    for i, (title, text) in enumerate(texts, 1):
        secs.append(clause(i, title, text))
    secs.extend([
        signature(landlord, "EL ARRENDADOR", tenant, "EL ARRENDATARIO"),
        publication_control("LegalAIZit_Paquete_02_Arrendamiento_Vivienda_Urbana_v1", len(texts), "inventario, entrega, restitución y guía", "2.23"),
    ])
    return secs


def lease_inventory_sections(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 1 - INVENTARIO Y ESTADO DEL INMUEBLE", "text": val(a, "property_address", val(a, "property", "Carrera 45 No. 10-25, apartamento 502, Medellín"))},
        {"heading": "1. Criterio de registro", "text": "Cada componente se describe por ubicación, material, estado, funcionamiento, cantidad, marca/serial, observación y evidencia. Las expresiones genéricas como ‘buen estado’ deben acompañarse de detalle verificable."},
        {"heading": "2. Accesos y llaves", "table": [("Elemento", "Cantidad/estado"), ("Puerta principal", "2 llaves - funcionamiento verificado"), ("Parqueadero", "1 control"), ("Cuarto útil", "1 llave"), ("Citófono", "Funcionamiento probado")]},
        {"heading": "3. Áreas", "table": [("Área", "Estado y novedades"), ("Sala-comedor", "Pisos, muros, ventanales y luminarias"), ("Cocina", "Muebles, mesón, red, grifería y equipos"), ("Habitaciones", "Puertas, closets, ventanas y tomas"), ("Baños", "Sanitarios, duchas, griferías y sellos"), ("Zona de ropas", "Redes, desagües y ventilación")]},
        {"heading": "4. Servicios y medidores", "table": [("Servicio", "Lectura/cuenta"), ("Energía", "Lectura inicial y número de contrato"), ("Acueducto", "Lectura inicial"), ("Gas", "Lectura y certificado disponible"), ("Internet", "No incluido / cuenta independiente")]},
        {"heading": "5. Muebles y equipos", "text": "Cuando el inmueble sea amoblado se incorporará inventario individual con fotografías, marca, referencia, serial, funcionamiento, valor de referencia y desgaste preexistente. Los bienes de alto valor requieren revisión."},
        {"heading": "6. Evidencia fotográfica", "bullets": ["Fotografías fechadas y relacionadas con cada área.", "Video panorámico opcional.", "Conservación del archivo original.", "Aceptación o comentarios de ambas partes."]},
        {"heading": "7. Pendientes", "table": [("Novedad", "Responsable/plazo"), ("Ajuste de sello en ducha", "Arrendador - 10 días"), ("Retoque de pintura", "Aceptado como condición inicial"), ("Certificado de gas", "Entregar antes de ocupación si aplica")]},
        signature(val(a, "landlord_name", val(a, "landlord", "María Rodríguez")), "EL ARRENDADOR", val(a, "tenant_name", val(a, "tenant", "Juan Pérez")), "EL ARRENDATARIO"),
        publication_control("Paquete 02 - inventario", 0, "evidencia fotográfica y comparación de cierre", "2.23"),
    ]


def delivery_act_sections(a: dict[str, Any]):
    return [
        {"heading": "ACTA DE ENTREGA DEL INMUEBLE", "text": f"Inmueble: {val(a, 'property_address', val(a, 'property', 'Carrera 45 No. 10-25, apartamento 502, Medellín'))}."},
        {"heading": "1. Comparecencia y fecha", "text": "Las partes se reúnen para documentar entrega material, sin que la firma implique renuncia a defectos ocultos, seguridad, sanidad o reparaciones legalmente exigibles."},
        {"heading": "2. Documentos entregados", "bullets": ["Contrato y anexos.", "Inventario y evidencia.", "Reglamento de propiedad horizontal.", "Manual de equipos.", "Datos de administración y emergencias."]},
        {"heading": "3. Llaves, controles y accesos", "table": [("Elemento", "Cantidad"), ("Llaves", "Según inventario"), ("Controles", "Según inventario"), ("Credenciales", "Activadas/revocadas"), ("Parqueadero", "Asignado") ]},
        {"heading": "4. Servicios", "text": "Se registran lecturas, estado de conexión, facturas, responsables y cambios de suscriptor. No se presume saldo cero sin soportes."},
        {"heading": "5. Novedades y compromisos", "text": "Las novedades se relacionan con responsable, prioridad, medida temporal, fecha de solución y evidencia de cierre. Un defecto grave bloquea la ocupación hasta contar con un plan seguro."},
        {"heading": "6. Aceptación con reservas", "text": "EL ARRENDATARIO recibe el inmueble conforme al inventario y reservas expresas. El silencio sobre un defecto no visible no extingue las obligaciones legales."},
        signature(val(a, "landlord_name", val(a, "landlord", "María Rodríguez")), "EL ARRENDADOR", val(a, "tenant_name", val(a, "tenant", "Juan Pérez")), "EL ARRENDATARIO"),
        publication_control("Paquete 02 - acta de entrega", 0, "llaves, medidores, documentos y pendientes", "2.23"),
    ]


def restitution_act_sections(a: dict[str, Any]):
    return [
        {"heading": "ACTA DE RESTITUCIÓN Y CIERRE", "text": f"Inmueble: {val(a, 'property_address', val(a, 'property', 'Carrera 45 No. 10-25, apartamento 502, Medellín'))}."},
        {"heading": "1. Fecha y entrega material", "text": "Se registra fecha, hora, estado de ocupación y entrega de llaves. La recepción podrá hacerse con reservas específicas sin impedir la restitución material."},
        {"heading": "2. Comparación con inventario", "table": [("Componente", "Resultado"), ("Estructura y acabados", "Desgaste normal / novedad"), ("Equipos y muebles", "Completos / faltantes"), ("Llaves y controles", "Devueltos"), ("Aseo y residuos", "Estado") ]},
        {"heading": "3. Daños y desgaste", "text": "Cada daño imputado se compara con evidencia inicial, antigüedad y uso normal. Se excluyen desgaste, vicios, defectos estructurales y hechos no imputables. Las reparaciones se soportarán con diagnóstico y costos razonables."},
        {"heading": "4. Servicios y administración", "text": "Se registran lecturas finales, últimas facturas y conceptos pendientes. Las reservas se limitan a períodos y cuentas identificadas; no se constituyen depósitos ni cobros estimados sin soporte."},
        {"heading": "5. Bienes y documentos", "bullets": ["Llaves y controles.", "Reglamentos o manuales prestados.", "Bienes del arrendador.", "Correspondencia pendiente.", "Evidencia digital compartida."]},
        {"heading": "6. Saldos y reservas", "text": "La conciliación discrimina canon, administración, servicios, daños soportados, pagos y saldos. El paz y salvo se expide cuando proceda y no elimina derechos indisponibles ni obligaciones desconocidas dolosamente."},
        signature(val(a, "landlord_name", val(a, "landlord", "María Rodríguez")), "EL ARRENDADOR", val(a, "tenant_name", val(a, "tenant", "Juan Pérez")), "EL ARRENDATARIO"),
        publication_control("Paquete 02 - acta de restitución", 0, "comparación, facturas, daños y cierre", "2.23"),
    ]


def lease_guide_sections(a: dict[str, Any]):
    return [
        {"heading": "GUÍA OPERATIVA DEL ARRENDAMIENTO", "text": "Lista de control para firma, ejecución y cierre del contrato de vivienda urbana."},
        {"heading": "1. Antes de firmar", "bullets": ["Verificar identidad y autorización del arrendador.", "Confirmar destinación residencial.", "Validar canon, administración y reajuste.", "Revisar propiedad horizontal.", "No pactar depósito en dinero a favor del arrendador."]},
        {"heading": "2. En la entrega", "bullets": ["Inventario detallado y evidencia.", "Lecturas de medidores.", "Pruebas de gas, agua y electricidad.", "Llaves y accesos.", "Pendientes con responsables y fechas."]},
        {"heading": "3. Durante el contrato", "bullets": ["Guardar pagos y comunicaciones.", "Reportar daños oportunamente.", "Coordinar visitas.", "Actualizar datos.", "Documentar modificaciones y mejoras."]},
        {"heading": "4. Terminación", "bullets": ["Revisar causal y preaviso.", "Coordinar entrega.", "Comparar inventario.", "Registrar facturas pendientes.", "No usar vías de hecho."]},
        {"heading": "5. Cuándo escalar", "bullets": ["Título o autorización controvertida.", "Restitución o litigio activo.", "Defectos graves.", "Turismo o uso comercial.", "Cláusulas atípicas o inmueble de alto valor."]},
        publication_control("Paquete 02 - guía", 0, "firma, ejecución y cierre", "2.23"),
    ]


# ---------------------------------------------------------------------------
# CO-LA-002 - CONTRATOS DE TRABAJO
# ---------------------------------------------------------------------------

def employment_contract_sections(a: dict[str, Any], result=None, forced_modality: str | None = None):
    employer = val(a, "employer_name", "Empresa Demo S.A.S.")
    worker = val(a, "worker_name", "Andrea Martínez")
    need = val(a, "need_type", "Permanente")
    modality = forced_modality or {
        "Permanente": "indefinido",
        "Temporal con fecha cierta": "fijo",
        "Obra o labor específica": "obra",
    }.get(need, "indefinido")
    modality_label = {"indefinido": "A TÉRMINO INDEFINIDO", "fijo": "A TÉRMINO FIJO", "obra": "POR DURACIÓN DE OBRA O LABOR DETERMINADA"}[modality]
    cargo = val(a, "job_title", "Coordinadora de Operaciones")
    salary = cop(a.get("monthly_salary") or 3_500_000)
    city = val(a, "city", "Medellín")
    parties = f"Entre {employer}, EL EMPLEADOR, y {worker}, EL TRABAJADOR, se celebra contrato individual de trabajo {modality_label.lower()} para el cargo de {cargo}."
    secs = intro(
        f"CONTRATO INDIVIDUAL DE TRABAJO {modality_label}",
        parties,
        [
            f"EL EMPLEADOR requiere vincular una persona para desempeñar el cargo de {cargo} bajo subordinación legítima y con funciones definidas.",
            "EL TRABAJADOR declara capacidad e información auténtica, sin que ello implique renunciar a la protección laboral.",
            "LAS PARTES documentan remuneración, jornada, lugar, funciones, seguridad, información, activos, debido proceso y terminación.",
            "Las estipulaciones se interpretarán conforme a favorabilidad, primacía de la realidad e irrenunciabilidad de derechos mínimos.",
        ],
    )
    if modality == "fijo":
        duration_text = f"El contrato regirá desde {val(a, 'start_date', '1 de agosto de 2026')} hasta {val(a, 'end_date', '31 de julio de 2027')}. Deberá constar por escrito, no superar el límite legal acumulado y observar las reglas de prórroga y preaviso vigentes. Si incumple los requisitos legales, la modalidad se ajustará a la consecuencia prevista por la ley."
    elif modality == "obra":
        duration_text = f"El contrato durará exclusivamente el tiempo requerido para ejecutar la obra o labor: {val(a, 'work_description', 'implementación del sistema de gestión documental del proyecto Alfa')}, cuya terminación objetiva será {val(a, 'completion_milestone', 'la aceptación final documentada del sistema')}. La obra debe permanecer precisa, detallada y verificable."
    else:
        duration_text = "El contrato es a término indefinido y tendrá vigencia mientras subsistan las causas que le dieron origen y la materia del trabajo, sin perjuicio de las formas legales de terminación. La necesidad permanente se documenta como fundamento de esta modalidad preferente."
    texts = [
        ("OBJETO, CARGO Y SERVICIO PERSONAL", f"EL TRABAJADOR se obliga a prestar personalmente sus servicios en el cargo de {cargo}, cumplir las funciones esenciales del Anexo No. 1 y atender instrucciones legítimas relacionadas con el cargo. Las funciones deben guardar coherencia con la denominación, nivel, remuneración, riesgos y formación, y no podrán modificarse abusivamente."),
        ("MODALIDAD Y DURACIÓN", duration_text),
        ("FECHA DE INICIO Y ANTIGÜEDAD", f"La prestación inicia el {val(a, 'start_date', '1 de agosto de 2026')}. La antigüedad se contará desde la fecha real demostrable. Ningún documento posterior podrá desconocer servicios anteriores efectivamente prestados."),
        ("PERÍODO DE PRUEBA", f"Se pacta por escrito un período de prueba de {val(a, 'probation_months', 'dos (2) meses')}, dentro de los máximos aplicables. En contratos fijos inferiores a un año se respetará el límite proporcional. No se repetirá para funciones sustancialmente equivalentes salvo supuesto legal documentado."),
        ("LUGAR Y MODALIDAD", f"EL TRABAJADOR prestará servicios principalmente en {val(a, 'workplace', city)}, bajo modalidad {val(a, 'remote', 'presencial')}. Los cambios permanentes que afecten condiciones esenciales se concertarán o implementarán dentro de facultades legales razonables. Teletrabajo, trabajo remoto o híbrido activan anexo específico."),
        ("JORNADA", f"La jornada ordinaria será de {val(a, 'weekly_hours', 'cuarenta y dos (42)')} horas semanales, distribuida conforme al horario informado, descansos y necesidades del servicio. La programación respetará máximos vigentes. Los turnos y modificaciones se comunicarán con antelación razonable."),
        ("TRABAJO SUPLEMENTARIO, NOCTURNO Y DESCANSOS", "El trabajo adicional, nocturno, dominical o festivo será autorizado y reconocido conforme a la ley. La autorización previa es un control administrativo y no elimina el pago del trabajo efectivamente ordenado, tolerado o probado. EL EMPLEADOR conservará registros cuando sean exigibles."),
        ("DESCONEXIÓN LABORAL", "Fuera de jornada, descansos, vacaciones y licencias, EL TRABAJADOR tendrá derecho a desconexión conforme a la ley y política aplicable, salvo situaciones exceptuadas y proporcionadas. Las comunicaciones no generarán obligación de respuesta inmediata sin causa legítima."),
        ("SALARIO", f"EL EMPLEADOR pagará un salario básico mensual de {salary}, en la periodicidad registrada, más los conceptos salariales causados. El salario remunera la jornada ordinaria y no comprende prestaciones, recargos o beneficios que legalmente deban reconocerse separadamente."),
        ("PAGOS VARIABLES Y BENEFICIOS", "Comisiones, bonificaciones, incentivos, auxilios y beneficios se detallarán en anexo con condición de causación, medición, período y naturaleza jurídica. La denominación de un pago como no salarial no prevalece si remunera directamente el servicio de manera habitual. No se utilizarán exclusiones generales."),
        ("PRESTACIONES Y SEGURIDAD SOCIAL", "EL EMPLEADOR afiliará y realizará aportes al sistema, reconocerá prestaciones, vacaciones y demás derechos conforme a la ley y al tiempo efectivamente laborado. EL TRABAJADOR suministrará información necesaria y reportará cambios, sin que esto habilite tratamiento excesivo de datos."),
        ("SUBORDINACIÓN LEGÍTIMA", "EL EMPLEADOR podrá impartir órdenes relacionadas con el servicio, verificar resultados, organizar la operación y aplicar medidas dentro de la ley, el contrato, la dignidad y los derechos fundamentales. No podrá exigir actos ilícitos, discriminatorios, inseguros o ajenos a la relación."),
        ("FUNCIONES Y RENDIMIENTO", "Las funciones, responsabilidades, indicadores, relaciones de reporte y herramientas se describen en el Anexo No. 1. La evaluación utilizará criterios comunicados y evidencia. Las metas deberán ser razonables y no convertir riesgos empresariales en obligaciones automáticas del trabajador."),
        ("OBLIGACIONES DEL EMPLEADOR", "EL EMPLEADOR pagará oportunamente, proveerá condiciones seguras, afiliará, respetará derechos, entregará herramientas, prevenirá acoso y discriminación, protegerá datos, comunicará políticas y atenderá reportes. Mantendrá canales para quejas, conflictos y situaciones de salud o seguridad."),
        ("OBLIGACIONES DEL TRABAJADOR", "EL TRABAJADOR prestará diligentemente el servicio, cuidará activos, cumplirá instrucciones legítimas, políticas comunicadas y medidas de seguridad, protegerá información, reportará riesgos y devolverá bienes. Estas obligaciones no implican disponibilidad permanente ni renuncia a derechos."),
        ("SEGURIDAD Y SALUD EN EL TRABAJO", "Las partes cumplirán el SG-SST. EL EMPLEADOR identificará peligros, capacitará, suministrará elementos, investigará incidentes y adoptará ajustes razonables. EL TRABAJADOR participará, utilizará protecciones y reportará condiciones. Ninguna cláusula traslada al trabajador la obligación empresarial de prevención."),
        ("ACOSO, DISCRIMINACIÓN Y VIOLENCIAS", "Se prohíben acoso laboral, acoso sexual, discriminación y represalias. EL EMPLEADOR informará canales, medidas de atención, confidencialidad y debido proceso. La denuncia de buena fe no constituye incumplimiento de reserva ni falta disciplinaria."),
        ("INFORMACIÓN CONFIDENCIAL", "EL TRABAJADOR utilizará información no pública exclusivamente para sus funciones, dentro de sistemas y canales autorizados. La obligación no se extiende a información pública, conocimientos generales, experiencia, denuncias o ejercicio de derechos. La información estratégica y sus medidas se individualizarán en anexo."),
        ("PROPIEDAD INTELECTUAL", "Cuando el cargo incluya creación de obras, software, contenidos o resultados, el anexo identificará entregables, funciones creativas, materiales preexistentes, modalidad de derechos y usos. Los derechos morales son intransferibles e irrenunciables. No se pactará cesión general de producción futura indeterminada."),
        ("DATOS PERSONALES", "EL EMPLEADOR tratará datos necesarios para vinculación, nómina, seguridad social, bienestar, seguridad y cumplimiento, con información y medidas apropiadas. Finalidades facultativas, biometría, datos sensibles o transferencias requieren evaluación separada. EL TRABAJADOR podrá ejercer sus derechos por los canales informados."),
        ("EQUIPOS, ACTIVOS Y CREDENCIALES", "Los equipos se entregarán mediante inventario con estado, serial, accesorios y reglas de uso. EL TRABAJADOR cuidará y reportará incidentes; no se autoriza descuento automático por pérdida o daño. La responsabilidad se determinará con soporte, causalidad, defensa y límites legales."),
        ("POLÍTICAS Y REGLAMENTO", "El reglamento, políticas y manuales válidamente adoptados y comunicados serán aplicables dentro de la ley y su materia. No podrán modificar unilateralmente salario, jornada, modalidad, duración u otros elementos esenciales ni establecer renuncias o sanciones no permitidas."),
        ("CONFLICTOS DE INTERÉS Y EXCLUSIVIDAD", "EL TRABAJADOR informará conflictos reales que afecten su deber durante el vínculo. La exclusividad solo se activará cuando exista interés legítimo, proporcionalidad y alcance definido. No se crea prohibición general poscontractual de trabajar ni de utilizar conocimientos y experiencia."),
        ("LICENCIAS, PERMISOS Y VACACIONES", "EL EMPLEADOR reconocerá licencias, permisos, incapacidades, descansos y vacaciones conforme a la ley y política válida. EL TRABAJADOR informará y aportará soportes razonables. La gestión no podrá desconocer situaciones protegidas ni exigir diagnósticos médicos excesivos."),
        ("PROTECCIONES ESPECIALES", "Embarazo, discapacidad, salud, fuero, condición de víctima u otra protección se gestionarán con confidencialidad, ajustes y autorizaciones cuando correspondan. Ninguna decisión de terminación o sanción se automatizará en estos casos; se exige revisión profesional."),
        ("DEBIDO PROCESO DISCIPLINARIO", "Antes de sancionar, EL EMPLEADOR comunicará hechos, normas presuntamente incumplidas y pruebas; otorgará oportunidad razonable de defensa y contradicción; valorará descargos imparcialmente; y adoptará decisión motivada y proporcional. Se respetarán presunción de inocencia, intimidad, buen nombre y no doble sanción."),
        ("TERMINACIÓN", "La terminación se sujetará a causales, procedimientos, autorizaciones, preavisos, liquidación y pruebas legales. Las justas causas deberán ser oportunas, concretas y demostrables. La terminación no autoriza descuentos no soportados, renuncias generales ni condicionamiento de pagos mínimos."),
        ("ENTREGA DEL CARGO", "Al finalizar, EL TRABAJADOR entregará archivos, accesos, equipos, llaves, inventarios y asuntos pendientes mediante acta. EL EMPLEADOR pagará y expedirá documentos dentro de términos aplicables. El paz y salvo no extingue acreencias laborales irrenunciables."),
        ("NOTIFICACIONES", "Las comunicaciones se dirigirán a datos registrados y conservarán trazabilidad. EL TRABAJADOR actualizará cambios razonablemente. Las comunicaciones electrónicas serán válidas cuando permitan identificar remitente y conservar contenido, sin sustituir formalidades especiales."),
        ("INTEGRIDAD, ANEXOS Y PRELACIÓN", "Integran el contrato los anexos de cargo, compensación, confidencialidad/PI/datos, equipos y modalidad no presencial que se activen, además de reglamentos y políticas válidas. Prevalecen Constitución, ley y norma más favorable; luego contrato y adendas; después anexos y políticas."),
        ("FIRMA Y LEY APLICABLE", f"El contrato se rige por las leyes de Colombia y se firma en {city}. Podrá suscribirse física o electrónicamente con identificación, aprobación e integridad. Cada parte recibirá copia completa y se conservará la versión, anexos y evidencia de aceptación."),
    ]
    for i, (title, text) in enumerate(texts, 1):
        secs.append(clause(i, title, text, page_break_before=i in (11, 21)))
    secs.extend([
        signature(employer, "EL EMPLEADOR", worker, "EL TRABAJADOR"),
        publication_control("LegalAIZit_Paquete_03_Contrato_Trabajo_Consolidado_v2.24", len(texts), "cinco anexos laborales activables", "2.24"),
    ])
    return secs


def employment_functions_annex(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 1 - PERFIL DEL CARGO Y MATRIZ DE FUNCIONES", "text": f"Cargo: {val(a, 'job_title', 'Coordinadora de Operaciones')}"},
        {"heading": "1. Objetivo", "text": val(a, "job_objective", "Coordinar la operación, asegurar trazabilidad, calidad, cumplimiento y disponibilidad oportuna de información para decisiones.")},
        {"heading": "2. Resultados esenciales", "bullets": ["Plan operativo actualizado.", "Indicadores y reportes confiables.", "Gestión de riesgos y novedades.", "Coordinación de recursos.", "Evidencia documental y mejora continua."]},
        {"heading": "3. Funciones", "bullets": ["Planear y priorizar actividades del área.", "Coordinar equipos y proveedores autorizados.", "Verificar calidad, seguridad y cumplimiento.", "Mantener registros y trazabilidad.", "Reportar incidentes y desviaciones.", "Proponer mejoras dentro de sus facultades."]},
        {"heading": "4. Autoridad y límites", "text": "La persona podrá decidir dentro de presupuestos, políticas y delegaciones comunicadas. No podrá comprometer a la empresa, modificar contratos o asumir obligaciones fuera de sus facultades."},
        {"heading": "5. Indicadores", "table": [("Indicador", "Criterio"), ("Cumplimiento del plan", "Hitos ejecutados y justificados"), ("Calidad", "Incidentes y reprocesos"), ("Trazabilidad", "Registros completos y oportunos"), ("Seguridad", "Acciones preventivas y reportes") ]},
        {"heading": "6. Riesgos y herramientas", "text": "Se identificarán riesgos del cargo, EPP, formación, sistemas, equipos y accesos. Todo activo se entrega mediante inventario."},
        publication_control("Paquete 03 - Anexo 1 madurado", 0, "perfil, funciones e indicadores", "2.24"),
    ]


def employment_compensation_annex(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 2 - COMPENSACIÓN VARIABLE Y BENEFICIOS", "text": f"Salario básico: {cop(a.get('monthly_salary') or 3_500_000)}."},
        {"heading": "1. Pagos variables", "table": [("Concepto", "Causación"), ("Comisión", "Venta efectivamente registrada y condiciones definidas"), ("Bono", "Metas comunicadas y verificables"), ("Auxilio", "Finalidad y soporte del gasto") ]},
        {"heading": "2. Naturaleza", "text": "La naturaleza salarial se determina por la realidad, finalidad y relación con el servicio. Ninguna etiqueta contractual excluye un pago que legalmente constituya salario."},
        {"heading": "3. Medición y controversias", "text": "La empresa entregará datos de medición y permitirá aclaraciones. Los ajustes retroactivos deberán soportarse. No se perderá un pago causado por terminación posterior."},
        {"heading": "4. Beneficios", "bullets": ["Identificar beneficiario y vigencia.", "Definir si es legal o extralegal.", "Evitar condiciones discriminatorias.", "Documentar cambios prospectivos cuando sean jurídicamente posibles."]},
        publication_control("Paquete 03 - Anexo 2 madurado", 0, "variables y beneficios", "2.24"),
    ]


def employment_confidentiality_annex(a: dict[str, Any]):
    base = relationship_annex_sections({
        "relationship_context": "Laboral/colaborador",
        "party_a": val(a, "employer_name", "Empresa Demo S.A.S."),
        "party_b": val(a, "worker_name", "Andrea Martínez"),
        "trade_secrets": "Sí",
        "personal_data": val(a, "personal_data", "Sí"),
    }, source="Paquete 03 - Anexo 3 madurado", model_version="2.24")
    return base


def employment_equipment_annex(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 4 - EQUIPOS, ACTIVOS Y CREDENCIALES", "text": "Inventario de elementos suministrados para el cargo."},
        {"heading": "1. Inventario", "table": [("Elemento", "Identificación/estado"), ("Computador", "Marca, serial y accesorios"), ("Teléfono", "IMEI y línea"), ("Credenciales", "Sistemas y nivel de acceso"), ("EPP/herramientas", "Cantidad y estado") ]},
        {"heading": "2. Uso y custodia", "text": "Los activos se utilizarán para fines autorizados, con cuidado razonable, actualizaciones y controles de seguridad. El uso personal tolerado se regirá por política informada."},
        {"heading": "3. Incidentes", "text": "Pérdida, daño, acceso o envío erróneo se reportarán inmediatamente. El reporte de buena fe no implica culpa. La empresa activará contención y análisis."},
        {"heading": "4. Descuentos", "text": "No se autorizan descuentos automáticos. Cualquier responsabilidad requiere soporte, imputación, debido proceso y autorización o mecanismo legal procedente."},
        {"heading": "5. Devolución", "text": "Al finalizar o cambiar el cargo se devolverán elementos y se revocarán accesos mediante acta. Se registrará desgaste normal, novedades y pendientes."},
        signature(val(a, "employer_name", "Empresa Demo S.A.S."), "EL EMPLEADOR", val(a, "worker_name", "Andrea Martínez"), "EL TRABAJADOR"),
        publication_control("Paquete 03 - Anexo 4 madurado", 0, "inventario y devolución", "2.24"),
    ]


def employment_remote_annex(a: dict[str, Any]):
    return [
        {"heading": "ANEXO NO. 5 - MODALIDAD NO PRESENCIAL", "text": f"Modalidad: {val(a, 'remote', 'híbrida simple')}."},
        {"heading": "1. Lugar y alternancia", "text": "Se identifican sede, domicilio autorizado, días, desplazamientos y procedimiento de cambio. La modalidad se ajustará a la figura jurídica real aplicable."},
        {"heading": "2. Jornada y disponibilidad", "text": "Se mantiene la jornada contractual, registro cuando proceda, descansos y desconexión. No se presume disponibilidad permanente por uso de herramientas digitales."},
        {"heading": "3. Equipos y costos", "text": "Se define qué suministra cada parte, mantenimiento, conectividad, energía, soporte y auxilios aplicables. No se trasladan costos empresariales sin base legal o acuerdo válido."},
        {"heading": "4. Seguridad y salud", "text": "Se evaluarán condiciones del puesto, autocuidado, pausas, riesgos y reporte de accidentes. La visita o evidencia del domicilio respetará privacidad y proporcionalidad."},
        {"heading": "5. Seguridad digital", "bullets": ["Acceso seguro y autenticación.", "Redes y dispositivos autorizados.", "Protección de pantallas y documentos.", "Reporte de incidentes.", "Separación de cuentas personales."]},
        {"heading": "6. Reversibilidad o cambios", "text": "Los cambios de modalidad atenderán la figura aplicable, necesidad, preaviso y condiciones individuales. Se documentarán y no afectarán derechos mínimos."},
        publication_control("Paquete 03 - Anexo 5 madurado", 0, "jornada, costos, SST y seguridad", "2.24"),
    ]


# ---------------------------------------------------------------------------
# CO-EM-004 - CONFIDENCIALIDAD, SECRETOS Y PI
# ---------------------------------------------------------------------------

def nda_sections(a: dict[str, Any], bilateral: bool | None = None, source: str = "LegalAIZit_Paquete_04_Confidencialidad_PI_Consolidado_v2"):
    party_a = val(a, "party_a", "Innovación Andina S.A.S.")
    party_b = val(a, "party_b", "Aliado Estratégico S.A.S.")
    if bilateral is None:
        bilateral = val(a, "nda_type", "bilateral").lower().startswith("bi")
    label = "BILATERAL" if bilateral else "UNILATERAL"
    purpose = val(a, "purpose", "evaluar y, en su caso, estructurar una alianza tecnológica y comercial")
    parties = f"Entre {party_a} y {party_b} se celebra ACUERDO DE CONFIDENCIALIDAD {label} para la finalidad exclusiva de {purpose}."
    secs = intro(
        f"ACUERDO DE CONFIDENCIALIDAD {label}",
        parties,
        [
            "Las partes prevén revelar información no pública para una finalidad concreta y limitada.",
            "La información puede incluir secretos, datos personales, activos técnicos, comerciales y documentación de terceros.",
            "La confidencialidad no transfiere propiedad intelectual ni autoriza finalidades distintas.",
            "Las partes desean establecer acceso, seguridad, incidentes, devolución, excepciones y trazabilidad.",
        ],
    )
    direction = "Cada parte será Reveladora respecto de su información y Receptora respecto de la información de la otra." if bilateral else f"{party_a} será LA PARTE REVELADORA y {party_b} LA PARTE RECEPTORA."
    texts = [
        ("MODALIDAD Y DIRECCIÓN", direction),
        ("FINALIDAD AUTORIZADA", f"La información se utilizará únicamente para {purpose}. La finalidad no incluye explotación comercial, entrenamiento de modelos, contacto directo con clientes, ingeniería inversa, publicación o desarrollo competitivo, salvo autorización escrita específica."),
        ("INFORMACIÓN CONFIDENCIAL", "Comprende información no pública identificada o que razonablemente deba entenderse reservada por su naturaleza y contexto: estrategia, precios, clientes, proveedores, finanzas, fórmulas, procesos, diseños, software, código, arquitectura, credenciales, datos, documentos, prototipos, negociaciones e información de terceros."),
        ("IDENTIFICACIÓN Y CLASIFICACIÓN", "La Parte Reveladora procurará clasificar, marcar o registrar la información y su sensibilidad. La falta de marca no elimina protección cuando la naturaleza sea evidente, pero una afirmación de secreto empresarial exige además medidas razonables de reserva, acceso y control."),
        ("EXCLUSIONES", "No será confidencial la información que la Receptora demuestre que era pública sin infracción, conocía legítimamente, recibió de tercero autorizado, desarrolló independientemente o cuya divulgación fue autorizada. Los conocimientos generales, habilidades y experiencia profesional no se apropian."),
        ("OBLIGACIÓN DE USO LIMITADO", "La Receptora utilizará la información solo para la finalidad, evitará beneficios propios no autorizados y no la incorporará a productos, decisiones o bases distintas. La comparación competitiva, descompilación, minería o extracción masiva requieren autorización expresa y legalidad."),
        ("ACCESO Y NECESIDAD DE CONOCER", "El acceso se limitará a personas que lo necesiten y estén sujetas a obligaciones equivalentes. Se mantendrá lista o criterio de autorizados, se revisarán permisos y se revocarán al cesar la necesidad. La Parte Receptora responderá por divulgaciones imputables de su personal o proveedores."),
        ("MEDIDAS DE SEGURIDAD", "Se aplicarán medidas razonables según sensibilidad: mínimo privilegio, autenticación, cifrado o canales seguros, clasificación, respaldo controlado, registro de accesos, protección física, actualización, eliminación segura y capacitación. La Parte Reveladora comunicará requisitos especiales antes de entregar."),
        ("HERRAMIENTAS DE IA", "La información no se cargará a herramientas públicas o servicios que puedan reutilizarla para entrenamiento, mejora o fines propios sin autorización, minimización y evaluación de condiciones. Cuando se autorice IA, se documentarán proveedor, cuenta, retención, ubicación, controles y datos excluidos."),
        ("NUBE Y PROVEEDORES", "El almacenamiento o procesamiento por terceros requiere diligencia, configuración segura, contrato y control de acceso. La Receptora no trasladará información a cuentas personales. Operaciones internacionales, nube exterior o subprocesadores de alto riesgo serán evaluados antes de su uso."),
        ("DATOS PERSONALES", "Si la información incluye datos personales, las partes definirán roles, base o autorización, finalidades, categorías, titulares, medidas, atención de derechos, incidentes, transferencias y eliminación. Este acuerdo no sustituye autorizaciones, avisos o contratos de transmisión que resulten necesarios."),
        ("DATOS SENSIBLES Y MENORES", "Datos sensibles, biometría, salud o información de menores no se tratarán mediante autoservicio estándar. Su inclusión exige necesidad estricta, evaluación de riesgos, controles reforzados y revisión profesional previa. La entrega accidental deberá reportarse y contenerse."),
        ("SECRETOS EMPRESARIALES", "La protección como secreto depende de que la información sea secreta, tenga valor por ello y esté sometida a medidas razonables. La Parte Reveladora mantendrá inventario, clasificación, responsables y controles. El acuerdo apoya, pero no reemplaza, dichas medidas materiales."),
        ("INFORMACIÓN DE TERCEROS", "Cada revelador declara estar autorizado para compartir información de terceros. La Receptora respetará avisos, licencias y restricciones comunicadas. Si se detecta un posible origen ilícito o exceso de autorización, suspenderá el uso y solicitará aclaración."),
        ("PROPIEDAD INTELECTUAL", "La revelación no transfiere propiedad ni concede licencia salvo la estrictamente necesaria para evaluar la finalidad. Las cesiones, licencias, obras por encargo, software, contenidos e imagen se regularán en anexos independientes y delimitados. Los derechos morales no se transfieren ni renuncian."),
        ("MATERIALES PREEXISTENTES Y TERCEROS", "Cada parte conserva sus materiales preexistentes. Software abierto, bancos, fuentes, APIs, datos, modelos y otros componentes se identificarán con licencia y restricciones. No se presume que fueron creados para la relación ni que pueden cederse."),
        ("NO OBLIGACIÓN DE CONTRATAR", "La revelación no obliga a celebrar negocio, conceder exclusividad, entregar información adicional ni continuar conversaciones. Cada parte asume sus costos de evaluación, salvo pacto diferente, y podrá detener la revelación preservando obligaciones ya causadas."),
        ("EXACTITUD Y DECISIONES", "Salvo declaración expresa, la información se suministra para evaluación y puede estar incompleta. Cada parte verificará antes de adoptar decisiones. Esta cláusula no protege declaraciones fraudulentas ni excluye deberes legales o garantías expresamente asumidas."),
        ("DIVULGACIÓN OBLIGATORIA", "La Receptora podrá divulgar cuando una autoridad competente o la ley lo exijan, limitando el alcance y avisando previamente cuando sea lícito. Podrá ejercer derechos, denunciar conductas, colaborar con autoridades y obtener asesoría profesional sujeta a reserva."),
        ("INCIDENTES", "Pérdida, acceso, divulgación, envío erróneo o sospecha se reportará sin demora indebida por el canal definido. La Receptora preservará evidencia, contendrá, investigará y cooperará. El reporte oportuno no equivale a confesión de responsabilidad ni autoriza ocultar hechos."),
        ("DEVOLUCIÓN Y ELIMINACIÓN", "A solicitud o cierre, la Receptora devolverá o eliminará copias bajo su control y confirmará el proceso. Podrá conservar una copia restringida cuando exista obligación legal, archivo probatorio o respaldo no inmediatamente depurable, sujeta a acceso limitado y prohibición de uso."),
        ("PLAZO", f"El acuerdo rige durante la relación y por {val(a, 'duration_years', 'cinco (5)')} años después de la última revelación para información confidencial ordinaria. Los secretos empresariales se protegerán mientras conserven jurídicamente dicho carácter y se mantengan las condiciones de reserva."),
        ("REMEDIOS Y RESPONSABILIDAD", "El incumplimiento podrá dar lugar a medidas de cesación, protección y reparación conforme a la ley y prueba. Una cláusula penal, si se pacta, deberá ser proporcional, delimitada y revisada; no sustituye automáticamente la prueba ni autoriza doble recuperación incompatible."),
        ("NO COMPETENCIA Y LIBERTAD PROFESIONAL", "El acuerdo no impone prohibición general de trabajar, competir o prestar servicios después del vínculo. Solo restringe uso o divulgación ilícita de información protegida. Cualquier restricción adicional requerirá interés legítimo, alcance, plazo, territorio, proporcionalidad y revisión independiente."),
        ("NOTIFICACIONES", "Los avisos sobre autorizaciones, incidentes, devolución y divulgación obligatoria se enviarán a los canales designados, conservando remitente, contenido y fecha. Los cambios de responsables o direcciones se informarán oportunamente."),
        ("INTEGRIDAD Y PRELACIÓN", "El acuerdo y anexos específicos conforman el régimen de información. En conflicto con un anexo posterior y especializado, este prevalecerá en su materia. Ninguna política o mensaje informal ampliará categorías, finalidad o transferencia de derechos sin aceptación válida."),
        ("LEY APLICABLE Y FIRMA", "El acuerdo se rige por las leyes de Colombia. Podrá firmarse física o electrónicamente con identificación, aprobación e integridad. Cada parte recibirá copia completa y conservará versión, anexos, autorizaciones y evidencia."),
    ]
    for i, (title, text) in enumerate(texts, 1):
        secs.append(clause(i, title, text))
    secs.extend([
        signature(party_a, "PARTE A", party_b, "PARTE B"),
        publication_control(source, len(texts), "inventario, relación, PI, datos, incidentes y cierre"),
    ])
    return secs


def information_inventory_sections(a: dict[str, Any]):
    return [
        {"heading": "INVENTARIO DE INFORMACIÓN, SISTEMAS Y ACCESOS", "text": f"Finalidad: {val(a, 'purpose', 'evaluar y ejecutar la relación autorizada')}."},
        {"heading": "1. Categorías", "table": [("Categoría", "Clasificación/propietario"), ("Comercial", "Reservada - Parte A"), ("Financiera", "Confidencial - acceso limitado"), ("Técnica", "Secreto potencial - medidas reforzadas"), ("Datos personales", "Rol y finalidad por definir"), ("Terceros", "Sujeta a licencia o autorización") ]},
        {"heading": "2. Sistemas y ubicaciones", "table": [("Sistema", "Control"), ("Repositorio", "MFA y permisos por rol"), ("Gestor documental", "Registro de accesos"), ("Correo", "Cuenta corporativa"), ("Nube", "Proveedor y región aprobados") ]},
        {"heading": "3. Personas autorizadas", "text": "Se registra nombre/rol, necesidad, nivel, fecha de alta, aprobación, obligaciones y fecha de revocación. El acceso grupal no identificado requiere justificación y control."},
        {"heading": "4. Transferencias y copias", "text": "Toda copia, exportación, impresión o transferencia relevante se asocia a finalidad, destinatario, canal, fecha, autorización y plazo de eliminación."},
        {"heading": "5. Medidas", "bullets": ["Clasificación y etiquetado.", "Mínimo privilegio.", "Autenticación y cifrado.", "Registro y revisión.", "Backups controlados.", "Retiro y eliminación."]},
        {"heading": "6. Cierre", "text": "El inventario se actualiza durante la relación y se utiliza para revocar accesos, devolver información y emitir el acta de cierre."},
        publication_control("Paquete 04 - inventario", 0, "clasificación y mínimo privilegio"),
    ]


def relationship_annex_sections(a: dict[str, Any], source="Paquete 04 - anexo según relación", model_version: str | None = None):
    context = val(a, "relationship_context", "Comercial/proveedor")
    pa = val(a, "party_a", val(a, "employer_name", "Innovación Andina S.A.S."))
    pb = val(a, "party_b", val(a, "worker_name", "Proveedor/colaborador autorizado"))
    sections = [
        {"heading": f"ANEXO DE CONFIDENCIALIDAD PARA RELACIÓN {context.upper()}", "text": f"Entre {pa} y {pb}. Este anexo complementa el acuerdo o contrato principal y se limita a la relación real indicada."},
        {"heading": "1. Accesos funcionales", "text": "Se identifican información, sistemas, clientes, procesos y activos necesarios. Todo acceso adicional requiere aprobación y registro."},
        {"heading": "2. Deberes específicos", "bullets": ["Usar canales autorizados.", "No trasladar archivos a cuentas personales.", "Verificar destinatarios.", "Proteger credenciales.", "Reportar incidentes.", "Devolver información al cierre."]},
        {"heading": "3. Secretos y conocimientos", "text": "Los secretos debidamente protegidos se sujetan a medidas reforzadas. Los conocimientos generales, experiencia, habilidades y aprendizaje no se apropian."},
        {"heading": "4. Datos personales", "text": "El acceso a datos se limita a finalidades y roles documentados. No se usarán para bases propias, marketing, perfilamiento o entrenamiento no autorizado."},
        {"heading": "5. Resultados y propiedad intelectual", "text": "Los resultados creativos o tecnológicos se regulan por anexo de PI. Este anexo no transfiere derechos ni impone renuncia moral."},
        {"heading": "6. Incidentes y cooperación", "text": "Se define canal, plazo interno, preservación, contención, investigación, comunicaciones y aprendizaje. El reporte de buena fe no constituye aceptación automática de culpa."},
        {"heading": "7. Terminación", "text": "Al terminar se revocan accesos, devuelven activos, eliminan copias y documentan retenciones legítimas. No se impone no competencia general."},
        signature(pa, "PARTE RESPONSABLE", pb, "PERSONA AUTORIZADA"),
        publication_control(source, 0, "accesos, datos, PI e incidentes", model_version),
    ]
    return sections


def ip_annex_sections(a: dict[str, Any], source="Paquete 04 - anexo PI"):
    client = val(a, "party_a", "Innovación Andina S.A.S.")
    creator = val(a, "party_b", "Desarrollador Creativo S.A.S.")
    return [
        {"heading": "ANEXO DE PROPIEDAD INTELECTUAL, SOFTWARE Y MATERIALES PREEXISTENTES", "text": f"Entre {client}, EL CLIENTE, y {creator}, EL CREADOR/DESARROLLADOR."},
        {"heading": "1. Entregables determinables", "text": "Los resultados cubiertos se enumeran con nombre, versión, formato, autor, fecha, repositorio y criterio de aceptación. No se incluye toda producción futura o ajena al proyecto."},
        {"heading": "2. Modalidad de derechos", "text": f"Modalidad seleccionada: {val(a, 'ip_mode', 'cesión delimitada de derechos patrimoniales sobre entregables nuevos')}. La transferencia o licencia se limita a modalidades expresas, territorio, plazo y condición económica pactados."},
        {"heading": "3. Derechos morales", "text": "Los derechos morales permanecen en cabeza de los autores. Se podrán acordar autorizaciones específicas de adaptación o no oposición dentro de límites legales, sin renuncia general."},
        {"heading": "4. Materiales preexistentes", "text": "Cada parte conserva herramientas, metodologías, librerías, plantillas, conocimiento y activos desarrollados antes o fuera del encargo. Cuando sean necesarios para usar el entregable, se concede licencia suficiente expresamente delimitada."},
        {"heading": "5. Componentes de terceros y OSS", "text": "Se mantendrá SBOM o inventario con componente, versión, licencia, fuente, obligación, modificación y dependencia. No se incorporarán licencias incompatibles con el uso previsto sin aprobación."},
        {"heading": "6. Repositorios y entrega", "bullets": ["Repositorio y titular de la cuenta.", "Ramas y versión aceptada.", "Código fuente y objetos necesarios.", "Documentación de despliegue.", "Credenciales transferidas de forma segura.", "Plan de continuidad."]},
        {"heading": "7. Datos, modelos e IA", "text": "Datasets, prompts, embeddings, modelos, pesos, salidas y proveedores se inventariarán. Se verificará autorización, licencias, privacidad, entrenamiento y restricciones. No se promete titularidad sobre componentes de terceros o resultados que la ley no reconozca."},
        {"heading": "8. Garantías", "text": "El creador declara originalidad o autorización razonable, informa terceros y coopera frente a reclamaciones. El cliente garantiza que sus insumos pueden usarse. Las garantías se limitan al conocimiento y control de cada parte, sin excluir dolo o infracciones imputables."},
        {"heading": "9. Portafolio y créditos", "text": "El uso en portafolio, créditos o casos de éxito requiere regla expresa sobre momento, contenido, anonimización y aprobación. No se publicará información confidencial o datos sin autorización."},
        {"heading": "10. Registro y formalidades", "text": "Las partes cooperarán con documentos de cesión, registro o evidencia cuando corresponda, sin que el registro cree por sí solo derechos no transferidos. Se conservarán contratos y actas de aceptación."},
        {"heading": "11. Terminación y continuidad", "text": "La terminación no revoca licencias irrevocables ya causadas ni transfiere componentes impagos cuando la transferencia se condicionó al pago. Se entregarán avances, repositorios y materiales conforme al estado de aceptación."},
        signature(client, "EL CLIENTE", creator, "EL CREADOR/DESARROLLADOR"),
        publication_control(source, 0, "software, OSS, IA y contenidos"),
    ]


def data_annex_sections(a: dict[str, Any], source="Paquete 04 - anexo datos"):
    responsible = val(a, "party_a", "Innovación Andina S.A.S.")
    processor = val(a, "party_b", "Proveedor Autorizado S.A.S.")
    return [
        {"heading": "ANEXO DE TRATAMIENTO Y SEGURIDAD DE DATOS PERSONALES", "text": f"Entre {responsible}, como responsable o parte que define finalidades, y {processor}, como encargado o receptor autorizado según la operación real."},
        {"heading": "1. Roles y alcance", "text": "Se confirmarán los roles reales, finalidad, instrucciones, categorías, titulares, operaciones, sistemas, ubicación y duración. La denominación contractual no reemplaza el análisis de la actividad."},
        {"heading": "2. Instrucciones", "text": "El encargado tratará únicamente conforme a instrucciones documentadas y advertirá si una instrucción parece contraria a la normativa. No usará datos para fines propios, marketing, perfilamiento o entrenamiento no autorizado."},
        {"heading": "3. Seguridad", "bullets": ["Mínimo privilegio y MFA.", "Cifrado o canales seguros.", "Registro y monitoreo.", "Gestión de vulnerabilidades.", "Copias y recuperación.", "Capacitación y confidencialidad."]},
        {"heading": "4. Subencargados", "text": "La incorporación de terceros requiere autorización, diligencia, contrato equivalente, inventario y control. El encargado conserva responsabilidad por su selección y obligaciones."},
        {"heading": "5. Derechos de titulares", "text": "Las solicitudes se remitirán al responsable y se atenderán dentro de los procedimientos aplicables. El encargado cooperará con búsqueda, corrección, eliminación o evidencia."},
        {"heading": "6. Incidentes", "text": "Se notificará sin demora indebida con naturaleza, datos, titulares, sistemas, medidas y contacto. Se preservará evidencia y se coordinarán comunicaciones, evitando reportes incompletos o contradictorios."},
        {"heading": "7. Transferencias", "text": f"Operación internacional o nube exterior: {val(a, 'crossborder', 'No')}. Si aplica, se evaluarán país, proveedor, roles, salvaguardas y requisitos antes de transferir o transmitir."},
        {"heading": "8. Retención y eliminación", "text": "Los datos se conservarán solo durante finalidad y términos aplicables. Al cierre se devolverán o eliminarán, salvo retención legal identificada y protegida. Los backups tendrán ciclo y acceso restringido."},
        {"heading": "9. Auditoría", "text": "El encargado proporcionará evidencia razonable de controles y permitirá verificaciones proporcionales, protegiendo información de otros clientes y seguridad. Las desviaciones generarán plan y seguimiento."},
        signature(responsible, "RESPONSABLE / PARTE A", processor, "ENCARGADO / PARTE B"),
        publication_control(source, 0, "roles, seguridad, incidentes y transferencias"),
    ]


def incident_protocol_sections(a: dict[str, Any]):
    return [
        {"heading": "PROTOCOLO DE INCIDENTES DE INFORMACIÓN Y DATOS", "text": "Procedimiento operativo para detectar, contener, analizar, comunicar y cerrar incidentes."},
        {"heading": "1. Eventos reportables", "bullets": ["Pérdida o robo.", "Acceso no autorizado.", "Envío equivocado.", "Credencial comprometida.", "Malware o indisponibilidad.", "Carga indebida a IA/nube.", "Divulgación o publicación."]},
        {"heading": "2. Canal y tiempo", "text": "El reporte interno será inmediato al canal designado e incluirá hechos conocidos sin especulación. La ausencia de todos los datos no debe retrasar el aviso inicial."},
        {"heading": "3. Contención", "bullets": ["Revocar o rotar accesos.", "Aislar activos.", "Solicitar eliminación al destinatario.", "Bloquear enlaces.", "Preservar logs y archivos.", "Evitar destrucción de evidencia."]},
        {"heading": "4. Evaluación", "text": "Se determinarán información, titulares, volumen, sensibilidad, origen, alcance, riesgos, responsables y obligaciones. Las conclusiones se diferenciarán de hechos e hipótesis."},
        {"heading": "5. Comunicaciones", "text": "Las comunicaciones a partes, titulares, autoridades o terceros se coordinarán por responsables autorizados, con precisión y oportunidad. No se ocultarán hechos ni se harán admisiones no verificadas."},
        {"heading": "6. Recuperación y cierre", "text": "Se restaurará operación, verificará eliminación o contención, corregirá causa, actualizará controles y documentará lecciones. El cierre tendrá aprobación técnica, jurídica y de negocio según impacto."},
        {"heading": "7. Registro", "table": [("Campo", "Contenido"), ("Identificador", "INC-AAAA-NNN"), ("Detección", "Fecha, persona y fuente"), ("Impacto", "Información/sistemas/titulares"), ("Acciones", "Responsable y evidencia"), ("Cierre", "Causa y plan preventivo") ]},
        publication_control("Paquete 04 - protocolo", 0, "detección, contención y cierre"),
    ]


def closure_act_sections(a: dict[str, Any]):
    return [
        {"heading": "ACTA DE DEVOLUCIÓN, ELIMINACIÓN Y CIERRE", "text": f"Relación entre {val(a, 'party_a', 'Innovación Andina S.A.S.')} y {val(a, 'party_b', 'Aliado Estratégico S.A.S.')}"},
        {"heading": "1. Fecha y causa", "text": "Se identifica contrato, acuerdo, fecha efectiva, causa de cierre y responsables."},
        {"heading": "2. Información", "table": [("Categoría", "Acción"), ("Documentos", "Devueltos/eliminados"), ("Datos", "Devueltos/eliminados/retención legal"), ("Repositorios", "Transferidos o accesos revocados"), ("Copias", "Confirmación y backups") ]},
        {"heading": "3. Accesos", "text": "Se revocan cuentas, tokens, llaves, dispositivos, VPN, repositorios y permisos de terceros. Las excepciones se documentan con responsable y fecha."},
        {"heading": "4. PI y activos", "text": "Se relacionan entregables, licencias, componentes preexistentes, créditos, soportes y obligaciones que sobreviven."},
        {"heading": "5. Retención legal", "text": "La copia retenida se identifica, justifica, protege, restringe y programa para eliminación. No podrá utilizarse para fines operativos o comerciales."},
        {"heading": "6. Incidentes y pendientes", "text": "Se registran incidentes abiertos, reclamaciones, investigaciones y acciones pendientes. El cierre documental no oculta obligaciones o controversias."},
        {"heading": "7. Declaraciones", "text": "Cada parte declara, según su conocimiento y controles razonables, haber cumplido las acciones registradas. La declaración no extingue responsabilidad por ocultamiento o incumplimiento."},
        signature(val(a, "party_a", "Innovación Andina S.A.S."), "PARTE A", val(a, "party_b", "Aliado Estratégico S.A.S."), "PARTE B"),
        publication_control("Paquete 04 - acta de cierre", 0, "accesos, copias, datos y PI"),
    ]


# Static model registry used by the v2.15 library builder.
MODEL_REGISTRY = {
    "CO-EM-003": {
        "title": "Prestación de servicios independientes",
        "source_package": "LegalAIZit_Paquete_01_Prestacion_de_Servicios_v1",
        "source_status": "Original DOCX disponible dentro del repositorio y reconstrucción estructurada v2.15",
    },
    "CO-AR-001": {
        "title": "Arrendamiento de vivienda urbana",
        "source_package": "LegalAIZit_Paquete_02_Arrendamiento_Vivienda_Urbana_v1",
        "source_status": "Reconstrucción estructurada desde paquete maestro; cotejo binario pendiente",
    },
    "CO-LA-002": {
        "title": "Contrato de trabajo personalizado",
        "source_package": "LegalAIZit_Paquete_03_Contrato_Trabajo_Consolidado_v2",
        "source_status": "Reconstrucción estructurada desde paquete maestro; cotejo binario pendiente",
    },
    "CO-EM-004": {
        "title": "Confidencialidad, secretos y propiedad intelectual",
        "source_package": "LegalAIZit_Paquete_04_Confidencialidad_PI_Consolidado_v2",
        "source_status": "Reconstrucción estructurada desde paquete maestro; cotejo binario pendiente",
    },
}


# M4 contractual maturity overrides
# The historical v2.15 module remains as compatibility surface, while all
# active P0 contractual generators resolve to the single M4 implementation.
from legalai_platform import contractual_maturity as _m4_contracts

services_contract_sections = _m4_contracts.services_contract_sections
service_scope_sections = _m4_contracts.service_scope_sections
service_confidentiality_sections = _m4_contracts.service_confidentiality_sections
service_ip_sections = _m4_contracts.service_ip_sections
service_data_sections = _m4_contracts.service_data_sections
service_closure_sections = _m4_contracts.service_closure_sections
employment_contract_sections = _m4_contracts.employment_contract_sections
employment_functions_annex = _m4_contracts.employment_functions_annex
employment_compensation_annex = _m4_contracts.employment_compensation_annex
employment_confidentiality_annex = _m4_contracts.employment_confidentiality_annex
employment_equipment_annex = _m4_contracts.employment_equipment_annex
employment_remote_annex = _m4_contracts.employment_remote_annex
nda_sections = _m4_contracts.nda_sections
information_inventory_sections = _m4_contracts.information_inventory_sections
relationship_annex_sections = _m4_contracts.relationship_annex_sections
ip_annex_sections = _m4_contracts.ip_annex_sections
data_annex_sections = _m4_contracts.data_annex_sections
incident_protocol_sections = _m4_contracts.incident_protocol_sections
closure_act_sections = _m4_contracts.closure_act_sections
lease_contract_sections = _m4_contracts.lease_contract_sections
lease_inventory_sections = _m4_contracts.lease_inventory_sections
delivery_act_sections = _m4_contracts.delivery_act_sections
restitution_act_sections = _m4_contracts.restitution_act_sections
lease_guide_sections = _m4_contracts.lease_guide_sections
