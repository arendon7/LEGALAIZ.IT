from __future__ import annotations

"""Finalización jurídica y de presentación de CO-SA-001.

La capa recompone las siete piezas de salud como copias externas orientadas al
usuario. Mantiene la criticidad y las compuertas de revisión humana, no sustituye
valoración clínica y no convierte PQR/Supersalud en requisito previo automático
para tutela o atención de urgencias.
"""

from copy import deepcopy
from datetime import date
from typing import Any

HEALTH_KINDS = {
    "health_diagnostic", "health_petition", "health_reiteration",
    "health_supersalud", "health_history_request", "health_evidence",
    "health_calendar",
}

CLIENT_TITLES = {
    "health_diagnostic": "Diagnóstico jurídico y operativo de barrera en salud",
    "health_petition": "Petición y reclamo priorizado en salud",
    "health_reiteration": "Reiteración y requerimiento de solución material en salud",
    "health_supersalud": "PQRD y solicitud de intervención ante la Superintendencia Nacional de Salud",
    "health_history_request": "Solicitud reservada de copia de historia clínica",
    "health_evidence": "Matriz probatoria y guía de radicación en salud",
    "health_calendar": "Calendario jurídico de respuesta, seguimiento y escalamiento",
}

CLIENT_SUBTITLES = {
    "health_diagnostic": "Continuidad, oportunidad, integralidad, prioridad y rutas de protección",
    "health_petition": "Gestión coordinada de la prestación · respuesta de fondo y ejecución material",
    "health_reiteration": "Persistencia de la barrera · respuesta insuficiente, vencida o no ejecutada",
    "health_supersalud": "Protección al usuario e IVC · PQRD distinta de la función jurisdiccional",
    "health_history_request": "Acceso del paciente a información clínica reservada · copia íntegra y trazable",
    "health_evidence": "Soportes pertinentes · reserva, minimización, integridad y trazabilidad",
    "health_calendar": "Términos sectoriales máximos y compuertas de actuación urgente",
}


def _value(value: Any, fallback: str = "Por verificar") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _yes(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    return text in {"sí", "si", "yes", "true", "1"} or text.startswith("sí,")


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _date_es(value: Any) -> str:
    if not value:
        return "Por verificar"
    text = str(value)
    try:
        parsed = date.fromisoformat(text[:10])
    except Exception:
        return text
    months = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def _patient(a: dict) -> str:
    return _value(a.get("patient_name") or a.get("petitioner_name") or a.get("name"), "Paciente por identificar")


def _petitioner(a: dict) -> str:
    return _value(a.get("petitioner_name") or a.get("patient_name") or a.get("name"), "Peticionario por identificar")


def _is_vital(a: dict) -> bool:
    raw = str(a.get("vital_risk") or "").strip().casefold()
    if not raw or any(x in raw for x in ("no report", "no identificado", "no confirmado", "sin riesgo")):
        return False
    return _yes(raw) or any(x in raw for x in ("riesgo vital", "peligro para la vida", "peligro inminente", "urgencia vital"))


def _priority(a: dict, result: dict) -> str:
    c = _calc(result)
    raw = " ".join(str(x or "") for x in (a.get("priority"), c.get("priority"), c.get("classification"), a.get("risk_classification"))).casefold()
    if _is_vital(a) or "vital" in raw:
        return "vital"
    if "prioriz" in raw or "priority" in raw:
        return "prioritized"
    if "simple" in raw:
        return "simple"
    return "unclassified"


def _priority_label(a: dict, result: dict) -> str:
    return {
        "vital": "Reclamo de riesgo vital",
        "prioritized": "Reclamo de riesgo priorizado",
        "simple": "Reclamo de riesgo simple",
        "unclassified": "Clasificación sectorial por confirmar",
    }[_priority(a, result)]


def _priority_term(a: dict, result: dict) -> str:
    return {
        "vital": "Atención inmediata; máximo 24 horas corridas para resolver el reclamo",
        "prioritized": "Con la inmediatez exigida por el caso; máximo 48 horas corridas",
        "simple": "Máximo 72 horas corridas, salvo que las circunstancias exijan solución anterior",
        "unclassified": "Debe clasificarse al radicar; el término depende del riesgo y nunca desplaza una urgencia",
    }[_priority(a, result)]


def _identity(a: dict, result: dict) -> list[list[str]]:
    return [
        ["Elemento", "Información del expediente"],
        ["Paciente", _patient(a)],
        ["Identificación", _value(a.get("patient_id"))],
        ["Peticionario", _petitioner(a)],
        ["EPS", _value(a.get("eps_name"))],
        ["IPS, gestor o proveedor", _value(a.get("provider_name") or a.get("ips_name") or a.get("pharmacy_manager"))],
        ["Prestación requerida", _value(a.get("service_requested") or a.get("request_mode"))],
        ["Orden o fórmula", _value(a.get("medical_order") or a.get("medical_order_detail"))],
        ["Fecha de la orden", _date_es(a.get("medical_order_date"))],
        ["Clasificación sectorial", _priority_label(a, result)],
    ]


def _chronology(a: dict) -> list[list[str]]:
    return [
        ["Hito", "Fecha / información"],
        ["Orden o soporte clínico", _date_es(a.get("medical_order_date"))],
        ["Barrera reportada", _value(a.get("facts_detail") or a.get("barrier_detail"))],
        ["Radicado previo", _value(a.get("prior_filing_radicado") or a.get("prior_claim_radicado"))],
        ["Fecha del radicado", _date_es(a.get("prior_filing_date") or a.get("prior_claim_date"))],
        ["Respuesta previa", _value(a.get("prior_response"), "No se acredita respuesta material")],
        ["Fecha de esta actuación", _date_es(a.get("filing_date"))],
    ]


def _signature(a: dict) -> dict:
    return {
        "heading": "FIRMA", "_type": "signature", "heading_align": "center",
        "parties": [{
            "label": "PACIENTE O PETICIONARIO LEGITIMADO",
            "name": _petitioner(a),
            "id": _value(a.get("petitioner_id") or a.get("patient_id"), ""),
            "role": "La calidad en que actúa y la representación, cuando corresponda, deben quedar acreditadas",
        }],
    }


def _legal_basis() -> list[str]:
    return [
        "Ley Estatutaria 1751 de 2015: derecho fundamental autónomo a la salud y principios de continuidad, oportunidad e integralidad; acceso oportuno a medicamentos y atención de urgencias.",
        "Ley 1755 de 2015, artículos 14 y 20: términos generales del derecho de petición y atención prioritaria o inmediata cuando sea necesario evitar perjuicio irremediable o peligro inminente para vida o integridad.",
        "Circular Externa 2023151000000010-5 de la Superintendencia Nacional de Salud: máximos sectoriales de 72, 48 y 24 horas para reclamos de riesgo simple, priorizado y vital, respectivamente.",
        "Resolución 1995 de 1999 y Resolución 839 de 2017: historia clínica privada y reservada, acceso, custodia, conservación y protección de información clínica.",
        "Ley 1122 de 2007, artículo 41, modificado por Ley 1949 de 2019: función jurisdiccional de Supersalud para controversias legales determinadas, distinta de la PQRD administrativa.",
        "Constitución Política, artículo 86, y Decreto 2591 de 1991: acción de tutela cuando concurran sus presupuestos; no se presume agotamiento previo de PQRD si el medio administrativo no es idóneo o eficaz para conjurar el riesgo.",
        "Corte Constitucional, T-125 de 2026: la EPS conserva responsabilidad frente al usuario y la indisponibilidad temporal de medicamento no exonera la adopción de soluciones oportunas y coordinadas.",
        "Corte Constitucional, T-008 de 2025: las barreras administrativas y la falta de acompañamiento o seguimiento pueden vulnerar el derecho fundamental a la salud.",
    ]


def _diagnostic(a: dict, result: dict) -> list[dict]:
    urgent = (
        "La información reportada indica posible riesgo vital. La ruta documental no es la actuación principal: debe procurarse atención asistencial inmediata y la urgencia no puede condicionarse a autorización administrativa previa."
        if _is_vital(a) else
        "No se reporta riesgo vital con la información disponible. Esta conclusión es documental, no clínica: cualquier deterioro, signo de alarma o nueva información obliga a reclasificar de inmediato."
    )
    judicial = (
        "Existe tutela o desacato activo. Antes de emitir nuevas comunicaciones debe revisarse el expediente judicial, el alcance exacto de la orden, su notificación, cumplimiento y cualquier término vigente."
        if (_yes(a.get("active_tutela")) or _yes(a.get("active_contempt"))) else
        "No se reporta actuación judicial activa. Ello no significa que la tutela sea improcedente: su necesidad depende del riesgo y de la idoneidad y eficacia de los demás medios en el caso concreto."
    )
    return [
        {"heading": "OBJETO Y ALCANCE", "paragraphs": [
            "Este diagnóstico organiza la barrera de acceso a salud, identifica responsables, nivel de prioridad, evidencia y rutas compatibles con el estado real del caso. No modifica órdenes médicas ni determina pertinencia clínica.",
            "La generación documental no debe retrasar atención urgente, ni convertir un término máximo administrativo en período de espera permitido.",
        ], "_suppress_default_control": True},
        {"heading": "I. IDENTIFICACIÓN DEL CASO", "table": _identity(a, result)},
        {"heading": "II. CRONOLOGÍA Y BARRERA", "table": _chronology(a)},
        {"heading": "III. CLASIFICACIÓN Y TÉRMINO SECTORIAL", "paragraphs": [f"Clasificación propuesta: {_priority_label(a, result)}. Regla aplicable: {_priority_term(a, result)}. Los máximos sectoriales se expresan en horas corridas y no sustituyen la actuación más temprana que exijan las circunstancias."]},
        {"heading": "IV. CONTINUIDAD, OPORTUNIDAD E INTEGRALIDAD", "numbered": [
            "Una prestación iniciada no debe interrumpirse injustificadamente por trámites internos, contratación o falta de coordinación entre actores.",
            "La persona usuaria no debe convertirse en mensajera permanente entre EPS, IPS, gestor, proveedor o auditor de una misma prestación.",
            "Una autorización o respuesta favorable no equivale a solución material si el medicamento, cita, procedimiento o servicio no se ejecuta.",
            "La entidad responsable debe documentar alternativas efectivas cuando el prestador inicialmente asignado no pueda cumplir oportunamente.",
        ]},
        {"heading": "V. COMPUERTA DE URGENCIA", "paragraphs": [urgent]},
        {"heading": "VI. RUTAS DE PROTECCIÓN", "table": [
            ["Ruta", "Finalidad", "Regla de uso"],
            ["PQR ante EPS/actor", "Remover barrera y obtener ejecución", "No desplaza urgencias ni tutela cuando no sea eficaz"],
            ["Reiteración", "Exigir solución ante vencimiento o respuesta insuficiente", "Verificar acuse y respuesta real antes de afirmar silencio"],
            ["PQRD Supersalud", "Intervención administrativa e IVC", "No equivale automáticamente a demanda jurisdiccional"],
            ["Función jurisdiccional Supersalud", "Decisión judicial en asuntos legalmente atribuidos", "Ruta separada; requiere análisis de competencia y pretensión"],
            ["Tutela", "Protección inmediata de derechos fundamentales", "Evaluar urgencia, riesgo e idoneidad/eficacia de otros medios"],
            ["Desacato/cumplimiento", "Hacer efectiva orden judicial previa", "Exige leer fallo, notificación y cumplimiento concreto"],
        ]},
        {"heading": "VII. ACTUACIÓN JUDICIAL EXISTENTE", "paragraphs": [judicial]},
        {"heading": "VIII. FUNDAMENTO JURÍDICO DE REFERENCIA", "numbered": _legal_basis()},
    ]


def _petition(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y PRIORIDAD", "paragraphs": [
            f"{_petitioner(a)} presenta petición y reclamo respecto de {_value(a.get('service_requested') or a.get('request_mode'))}. Se propone la clasificación {_priority_label(a, result)}; la entidad receptora debe validarla y aplicar {_priority_term(a, result)}.",
            "La solicitud busca remover la barrera administrativa y obtener ejecución material; no sustituye la valoración del profesional tratante ni autoriza modificar la orden clínica.",
        ], "_suppress_default_control": True},
        {"heading": "I. IDENTIFICACIÓN", "table": _identity(a, result)},
        {"heading": "II. HECHOS", "numbered": [
            f"Existe orden o soporte clínico identificado como {_value(a.get('medical_order'))}, con fecha {_date_es(a.get('medical_order_date'))}.",
            f"La barrera informada consiste en {_value(a.get('facts_detail') or a.get('barrier_detail'))}.",
            f"Se registra gestión previa {_value(a.get('prior_filing_radicado') or a.get('prior_claim_radicado'))}, radicada el {_date_es(a.get('prior_filing_date') or a.get('prior_claim_date'))}.",
            f"Estado de respuesta informado: {_value(a.get('prior_response'), 'sin respuesta material acreditada')}.",
            "La continuidad o disponibilidad debe resolverse mediante coordinación entre los actores responsables, sin trasladar injustificadamente esa carga al paciente.",
        ]},
        {"heading": "III. FUNDAMENTOS", "numbered": _legal_basis()[:4]},
        {"heading": "IV. SOLICITUDES", "numbered": [
            "Clasificar formalmente el reclamo según el riesgo y aplicar el término sectorial correspondiente.",
            "Verificar integralmente el estado de la orden, autorización, agenda, dispensación o prestación reclamada.",
            "Adoptar las actuaciones necesarias para ejecutar la prestación sin fragmentar la responsabilidad entre actores de la red.",
            "Informar fecha cierta de ejecución o, si depende de una actuación clínica previa, identificar responsable, actividad y fecha de realización.",
            "Si el proveedor asignado no puede cumplir oportunamente, gestionar una alternativa efectiva compatible con la orden y las reglas del sistema.",
            "Si se requiere actualización o aclaración clínica, programarla y explicar su necesidad sin reiniciar injustificadamente el proceso.",
            "Si se niega o modifica la prestación, emitir decisión individual, motivada, comprensible y soportada, indicando alternativa y mecanismos de revisión.",
            "Responder cada solicitud por separado y conservar trazabilidad de los soportes utilizados.",
            "Mantener un canal de seguimiento hasta la ejecución material, no solo hasta la emisión de una respuesta formal.",
        ]},
        {"heading": "V. RESERVA Y MINIMIZACIÓN", "paragraphs": ["La información de salud es reservada. Se aportan únicamente los soportes clínicos pertinentes; no se autoriza la circulación de la historia completa ni usos ajenos a la atención, gestión, control o cumplimiento legal."]},
        {"heading": "VI. CIERRE", "paragraphs": ["Una respuesta favorable, autorización o programación no cierra por sí sola el expediente. El cierre requiere evidencia de entrega, cita, procedimiento, continuidad o solución material compatible con lo ordenado clínicamente."]},
        _signature(a),
    ]


def _reiteration(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO", "paragraphs": [
            f"Se reitera el reclamo radicado como {_value(a.get('prior_filing_radicado') or a.get('prior_claim_radicado'))} el {_date_es(a.get('prior_filing_date') or a.get('prior_claim_date'))}, porque la barrera continúa o no se acredita una solución material.",
            f"La clasificación sectorial propuesta es {_priority_label(a, result)} y su máximo aplicable es: {_priority_term(a, result)}. Para afirmar vencimiento debe verificarse el acuse completo, incluida la hora cuando sea relevante, y que no exista respuesta o actuación posterior no incorporada al expediente.",
        ], "_suppress_default_control": True},
        {"heading": "I. PERSISTENCIA DE LA BARRERA", "table": _chronology(a)},
        {"heading": "II. DEFICIENCIAS A VERIFICAR", "numbered": [
            "Ausencia de solución dentro del término sectorial aplicable, una vez comprobada la recepción real.",
            "Respuesta que solo indica 'en trámite' sin decisión, responsable o fecha cierta.",
            "Remisión a otro actor sin coordinación ni seguimiento.",
            "Negación o demora sin fundamentos, alternativa o mecanismo de revisión.",
            "Autorización o promesa que no llegó a ejecutarse materialmente.",
        ]},
        {"heading": "III. REQUERIMIENTOS", "numbered": [
            "Resolver de fondo los puntos pendientes y ejecutar la solución material.",
            "Informar responsable, estado y fecha cierta de la actuación faltante.",
            "Coordinar directamente a EPS, IPS, gestor o proveedor cuando la prestación dependa de varios actores.",
            "Explicar cualquier negativa o sustitución con fundamento clínico-administrativo verificable y sin alterar la orden por decisión meramente administrativa.",
            "Conservar y comunicar la trazabilidad de las actuaciones realizadas después del primer radicado.",
        ]},
        {"heading": "IV. ESCALAMIENTO", "paragraphs": ["La persistencia puede justificar PQRD ante Supersalud y, según riesgo, tutela u otras actuaciones. No existe una regla automática que obligue a esperar primero a Supersalud cuando esa espera no sea idónea o eficaz para proteger el derecho fundamental. Si ya existe tutela o desacato, debe revisarse primero el expediente judicial."]},
        _signature(a),
    ]


def _supersalud(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y NATURALEZA DE LA ACTUACIÓN", "paragraphs": [
            "Se formula PQRD y solicitud de intervención administrativa ante la Superintendencia Nacional de Salud por persistencia de una barrera de acceso. Esta pieza busca gestión de protección al usuario e inspección, vigilancia y control dentro de las competencias aplicables.",
            "Esta PQRD no constituye automáticamente una demanda ante la función jurisdiccional de Supersalud. Si se pretende una decisión judicial sobre una controversia de las atribuidas por el artículo 41 de la Ley 1122 de 2007, debe estructurarse una actuación separada y revisar competencia, pretensiones y requisitos.",
        ], "_suppress_default_control": True},
        {"heading": "I. IDENTIFICACIÓN Y CRONOLOGÍA", "table": _chronology(a)},
        {"heading": "II. BARRERA Y PRIORIDAD", "paragraphs": [f"Prestación: {_value(a.get('service_requested') or a.get('request_mode'))}. Clasificación propuesta: {_priority_label(a, result)}. Regla sectorial: {_priority_term(a, result)}."]},
        {"heading": "III. SOLICITUDES A SUPERSALUD", "numbered": [
            "Registrar y clasificar la PQRD conforme al riesgo informado y a la evidencia disponible.",
            "Requerir a los actores responsables información concreta sobre causa, estado, responsable y fecha de solución.",
            "Promover la coordinación necesaria para remover la barrera y verificar la ejecución material de la prestación.",
            "Evitar cierres basados únicamente en respuestas formales cuando el servicio continúe sin ejecutarse.",
            "Adoptar, dentro de sus competencias, las actuaciones de inspección, vigilancia, control o protección al usuario que correspondan a los hechos acreditados.",
        ]},
        {"heading": "IV. RELACIÓN CON TUTELA Y FUNCIÓN JURISDICCIONAL", "paragraphs": ["La radicación de esta PQRD no obliga a suspender una tutela ni a esperar su respuesta cuando la protección constitucional requiera una medida inmediata. Del mismo modo, la función jurisdiccional de Supersalud es una vía distinta que solo debe utilizarse tras verificar que la controversia concreta esté dentro de su competencia legal."]},
        {"heading": "V. ANEXOS", "numbered": ["Documento de identificación o soporte de legitimación.", "Orden, fórmula o soporte clínico pertinente.", "Radicados y respuestas previas.", "Evidencia de la barrera y de continuidad previa, cuando aplique.", "Soportes estrictamente necesarios para acreditar prioridad, sin anexar información clínica irrelevante."]},
        _signature(a),
    ]


def _history(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO", "paragraphs": [f"{_petitioner(a)} solicita al prestador o custodio competente acceso y copia de la historia clínica de {_patient(a)}. La historia clínica es un documento privado, obligatorio y sometido a reserva; su entrega debe respetar legitimación, integridad, confidencialidad y trazabilidad."], "_suppress_default_control": True},
        {"heading": "I. LEGITIMACIÓN", "table": [["Elemento", "Dato"], ["Paciente", _patient(a)], ["Identificación", _value(a.get('patient_id'))], ["Solicitante", _petitioner(a)], ["Calidad", "Paciente o tercero cuya representación/autorización debe verificarse"], ["Prestador/custodio", _value(a.get('provider_name') or a.get('ips_name'))]]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Permitir la consulta y entregar copia legible, íntegra y ordenada de los registros solicitados.",
            "Incluir, cuando correspondan al episodio requerido, evoluciones, órdenes, fórmulas, resultados, remisiones, consentimientos y demás registros clínicos asociados.",
            "Informar el período cubierto por la copia y advertir cualquier faltante, inconsistencia de foliación o documento no disponible.",
            "Entregar por canal seguro y conservar constancia de la identidad y legitimación de quien recibe.",
            "No modificar ni reconstruir silenciosamente registros clínicos con ocasión de la solicitud; cualquier corrección debe conservar trazabilidad.",
        ]},
        {"heading": "III. ALCANCE Y MINIMIZACIÓN", "paragraphs": ["Para una reclamación concreta puede solicitarse inicialmente el episodio clínico pertinente para reducir circulación innecesaria de datos. Ello no implica renunciar al derecho del paciente a consultar la totalidad de su historia y obtener copia cuando la solicite legítimamente."]},
        {"heading": "IV. TÉRMINO", "paragraphs": ["Cuando la solicitud sea tramitada como petición de documentos o información bajo la Ley 1755 de 2015, la referencia general es de diez (10) días. Este término es distinto de los máximos sectoriales de 72, 48 o 24 horas aplicables al reclamo por barrera de salud."]},
        {"heading": "V. CONSERVACIÓN Y RESERVA", "paragraphs": ["La Resolución 839 de 2017 establece, como regla general, un tiempo mínimo de retención y conservación de quince (15) años contado desde la última atención, sin perjuicio de reglas especiales de conservación. La entrega de copia no elimina los deberes de custodia, reserva y protección de datos del responsable del archivo."]},
        _signature(a),
    ]


def _evidence(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "OBJETO", "paragraphs": ["Esta matriz organiza la evidencia necesaria para demostrar orden clínica, barrera, prioridad, radicación, respuesta y ejecución. No convierte una inferencia administrativa en hecho clínico ni exige circular información médica que no sea pertinente."], "_suppress_default_control": True},
        {"heading": "I. MATRIZ PROBATORIA", "table": [
            ["ID", "Soporte", "Qué acredita", "Sensibilidad", "Control"],
            ["SA-01", "Identificación / afiliación", "Legitimación", "Media", "Usar solo cuando sea necesario"],
            ["SA-02", "Orden o fórmula", "Prestación prescrita", "Alta", "Conservar copia exacta"],
            ["SA-03", "Resumen clínico pertinente", "Necesidad/continuidad/prioridad", "Alta", "No anexar historia completa por defecto"],
            ["SA-04", "Radicado y acuse", "Recepción, fecha y hora", "Baja", "Crítico para cómputo"],
            ["SA-05", "Respuesta de la entidad", "Decisión o gestión", "Variable", "Contrastar con ejecución"],
            ["SA-06", "Constancia de no disponibilidad", "Persistencia de barrera", "Media", "Preservar origen y fecha"],
            ["SA-07", "Comprobante de entrega/cita", "Solución material", "Alta", "Necesario para cierre"],
            ["SA-08", "Poder o autorización", "Representación", "Media", "Solo si aplica"],
            ["SA-09", "Tutela, medida o fallo", "Orden judicial vigente", "Alta", "Obligatorio si hay proceso activo"],
        ]},
        {"heading": "II. INTEGRIDAD Y TRAZABILIDAD", "numbered": ["Conservar el archivo original y una copia de trabajo.", "Registrar fecha, canal, remitente y destinatario de cada actuación.", "Vincular capturas a la comunicación o consulta que permita contextualizarlas.", "Distinguir documento clínico, documento administrativo y afirmación del usuario.", "Vincular el cierre a soporte de ejecución material, no solo a autorización."]},
        {"heading": "III. PRIVACIDAD Y MINIMIZACIÓN", "numbered": ["No anexar historia clínica completa si soportes menos invasivos bastan.", "Eliminar datos de terceros no pertinentes.", "No incorporar contraseñas ni información ajena al expediente.", "Usar canales verificados y acceso restringido.", "Conservar un índice exacto de anexos por radicación."]},
        {"heading": "IV. RADICACIÓN", "numbered": ["Verificar canal oficial y destinatario.", "Radicar documento y anexos en orden legible.", "Conservar número, fecha y hora del acuse.", "Verificar apertura e integridad de cada archivo.", "Identificar toda ampliación posterior como alcance, sin sustituir silenciosamente la versión inicial."]},
    ]


def _calendar(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    inherited = c.get("petition_due_date") or c.get("due_date")
    return [
        {"heading": "REGLA DE CÓMPUTO", "paragraphs": [f"Clasificación propuesta: {_priority_label(a, result)}. Regla sectorial: {_priority_term(a, result)}. Los términos expresados en horas se cuentan como horas corridas. No se calcula hora exacta si el expediente no conserva la hora real de recepción."], "_suppress_default_control": True},
        {"heading": "I. HITOS", "table": [
            ["Actuación", "Fecha / regla", "Estado"],
            ["Orden o fórmula", _date_es(a.get('medical_order_date')), "Soporte clínico"],
            ["Radicado previo", f"{_date_es(a.get('prior_filing_date') or a.get('prior_claim_date'))} · {_value(a.get('prior_filing_radicado') or a.get('prior_claim_radicado'))}", "Verificar fecha y hora"],
            ["Clasificación sectorial", _priority_label(a, result), _priority_term(a, result)],
            ["Vencimiento genérico heredado", _date_es(inherited) if inherited else "No informado", "No usar como término rector del reclamo sectorial"],
            ["Reiteración", "Vencimiento, respuesta insuficiente o falta de ejecución", "Condicional"],
            ["PQRD Supersalud", "Persistencia o necesidad de intervención administrativa", "Puede coexistir con otras rutas"],
            ["Tutela", "Según urgencia, riesgo e idoneidad/eficacia de otros medios", "Sin agotamiento automático de PQRD"],
            ["Desacato/cumplimiento", "Si existe orden judicial previa incumplida", "Revisar fallo y notificación"],
            ["Cierre", "Solución material documentada", "Pendiente hasta verificar ejecución"],
        ]},
        {"heading": "II. REGLAS ESPECIALES", "numbered": [
            "Riesgo simple: máximo 72 horas corridas, salvo necesidad de solución anterior.",
            "Riesgo priorizado: atención con la inmediatez exigida y máximo 48 horas corridas.",
            "Riesgo vital: actuación inmediata y máximo 24 horas corridas; el peligro inminente exige medidas urgentes sin esperar vencimiento.",
            "Petición de documentos o información: cuando aplique Ley 1755, referencia general de 10 días, separada del término sectorial del reclamo de salud.",
            "Tutela: no es un hito que necesariamente deba esperar a Supersalud; su oportunidad depende de riesgo e idoneidad/eficacia real de otros mecanismos.",
        ]},
        {"heading": "III. SEGUIMIENTO Y CIERRE", "table": [["Control", "Qué verificar"], ["Respuesta de fondo", "Que resuelva cada solicitud"], ["Ejecución", "Entrega, cita, procedimiento o prestación efectivamente realizada"], ["Continuidad", "Ausencia de nueva interrupción administrativa"], ["Cambio clínico", "Nueva orden, deterioro o signo de alarma que obligue a reclasificar"], ["Actuación judicial", "Tutela, medida, fallo o desacato que modifique la estrategia"], ["Cierre", "Solución material antes de cerrar el expediente"]]},
    ]


def _kind(spec: dict) -> str | None:
    kind = str(spec.get("kind") or "")
    if kind in HEALTH_KINDS:
        return kind
    hay = f"{kind} {spec.get('title') or ''}".casefold()
    tests = (
        ("health_diagnostic", ("diagn",)),
        ("health_history_request", ("historia clínica", "history", "clinical")),
        ("health_reiteration", ("reiter",)),
        ("health_supersalud", ("supersalud", "superintend", "authority")),
        ("health_evidence", ("evidenc", "probatorio", "radicación")),
        ("health_calendar", ("calendar", "calendario", "seguimiento")),
        ("health_petition", ("petition", "petición", "reclamo")),
    )
    for target, tokens in tests:
        if any(token in hay for token in tokens):
            return target
    return None


def _sections(kind: str, a: dict, result: dict) -> list[dict]:
    return {
        "health_diagnostic": _diagnostic,
        "health_petition": _petition,
        "health_reiteration": _reiteration,
        "health_supersalud": _supersalud,
        "health_history_request": _history,
        "health_evidence": _evidence,
        "health_calendar": _calendar,
    }[kind](a, result)


def finalize_health_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Profundiza CO-SA-001 sin relajar las compuertas de revisión humana."""
    finalized: list[dict] = []
    for spec in deepcopy(specs):
        kind = _kind(spec)
        if kind is None:
            finalized.append(spec)
            continue
        internal = deepcopy(spec.get("internal_review_sections") or [])
        internal.extend(deepcopy(s) for s in (spec.get("sections") or []) if isinstance(s, dict) and s.get("_type") == "control")
        spec["kind"] = kind
        spec["title"] = CLIENT_TITLES[kind]
        spec["subtitle"] = CLIENT_SUBTITLES[kind]
        spec["sections"] = _sections(kind, answers, result)
        spec["internal_review_sections"] = internal
        spec["internal_controls_externalized"] = True
        spec["document_standard"] = "M33.0"
        spec["legal_approval"] = "pending"
        spec["qa_approval"] = "pending"
        spec["released"] = False
        spec["requires_human_review"] = True
        if str((result or {}).get("risk") or "").casefold() == "red":
            spec["critical_human_review"] = True
        finalized.append(spec)
    return finalized
