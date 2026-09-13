from __future__ import annotations

"""Tercera oleada M33.0: salud y tránsito.

La composición parte de la salida histórica ya generada por `expanded_documents` y
conserva sus metadatos, cálculos y condiciones. Reemplaza el contenido documental
por expedientes jurídicos más profundos, sin convertir alertas o irregularidades en
resultados automáticos. Las compuertas críticas permanecen a cargo del motor y de la
revisión profesional.
"""

from copy import deepcopy
from typing import Any, Callable

from m33_procedural_runtime import document_specs_m33_runtime

WAVE3_CODES = {"CO-SA-001", "CO-TR-001", "CO-TR-002"}


def _value(value: Any, fallback: str = "No consta en esta versión; requiere verificación") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _date(value: Any) -> str:
    return _value(value, "Fecha no confirmada")


def _control(code: str, extra: str = "") -> dict:
    text = (
        f"Documento candidato interno {code} bajo estándar M33.0. El contenido organiza hechos, evidencia, solicitudes y rutas de actuación, pero no sustituye valoración médica, decisión administrativa, defensa judicial ni revisión profesional. "
        "Antes de liberarlo deben verificarse identidad, legitimación, fechas, actos, notificaciones, anexos, fuentes, vigencia normativa y estado procesal. La aprobación jurídica y el QA deben recaer sobre la misma revisión y hash."
    )
    if extra:
        text += " " + extra
    return {"heading": "CONTROL DE USO, FUENTES Y REVISIÓN", "_type": "control", "text": text}


def _signature(label: str, name: Any, identity: Any = None) -> dict:
    return {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [{"label": label, "name": _value(name, "Persona por identificar"), "id": _value(identity, "") if identity else ""}],
    }


def _meta(specs: list[dict]):
    return deepcopy(specs[0].get("metadata", [])) if specs else []


def _candidate(specs: list[dict], predicate: Callable[[str, str], bool]) -> dict | None:
    for spec in specs:
        kind = str(spec.get("kind") or "").casefold()
        title = str(spec.get("title") or "").casefold()
        if predicate(kind, title):
            return deepcopy(spec)
    return None


def _upsert(
    specs: list[dict],
    predicate: Callable[[str, str], bool],
    *,
    kind: str,
    title: str,
    suffix: str,
    sections: list[dict],
    metadata,
) -> None:
    existing = _candidate(specs, predicate)
    new_spec = existing or {
        "kind": kind,
        "title": title,
        "filename_suffix": suffix,
        "metadata": deepcopy(metadata),
    }
    new_spec["title"] = title
    new_spec["subtitle"] = "Composición jurídica profunda M33.0"
    new_spec["sections"] = sections
    new_spec["document_standard"] = "M33.0"
    if existing:
        for index, spec in enumerate(specs):
            if spec.get("kind") == existing.get("kind") and spec.get("title") == existing.get("title"):
                specs[index] = new_spec
                return
    specs.append(new_spec)


def _retain_only(specs: list[dict], allowed_predicates: list[Callable[[str, str], bool]], added_kinds: set[str]) -> list[dict]:
    """Evita duplicados históricos: conserva solo piezas no cubiertas por M33.0."""
    result = []
    for spec in specs:
        if spec.get("kind") in added_kinds or spec.get("document_standard") == "M33.0":
            result.append(spec)
            continue
        kind = str(spec.get("kind") or "").casefold()
        title = str(spec.get("title") or "").casefold()
        if any(predicate(kind, title) for predicate in allowed_predicates):
            # Si una pieza histórica coincide con una categoría ya recompuesta y no
            # fue reemplazada por identidad exacta, se descarta para evitar duplicado.
            continue
        result.append(spec)
    return result


# ---------------------------------------------------------------------------
# CO-SA-001 — salud
# ---------------------------------------------------------------------------


def _patient(a: dict) -> str:
    return _value(a.get("patient_name") or a.get("petitioner_name") or a.get("name"), "Paciente por identificar")


def health_diagnostic(a: dict, result: dict) -> list[dict]:
    c = result.get("calculation") if isinstance(result.get("calculation"), dict) else {}
    return [
        {
            "heading": "1. FINALIDAD DEL DIAGNÓSTICO",
            "paragraphs": [
                "El diagnóstico determina la naturaleza de la barrera reportada, la entidad que debe intervenir, la legitimación de quien solicita, el nivel de prioridad, la documentación clínica estrictamente necesaria y la ruta de escalamiento compatible con el estado real del caso.",
                "La plataforma no reemplaza una valoración médica, no modifica fórmulas ni órdenes, no determina por sí sola la pertinencia clínica de un tratamiento y no orienta a esperar una respuesta documental cuando existe una urgencia que requiere atención inmediata.",
            ],
        },
        {"heading": "2. CLASIFICACIÓN DEL CASO", "table": [
            ["Elemento", "Resultado"],
            ["Paciente", _patient(a)],
            ["Solicitante", _value(a.get("petitioner_name") or a.get("patient_name"))],
            ["EPS", _value(a.get("eps_name"))],
            ["IPS / gestor", _value(a.get("provider_name") or a.get("ips_name") or a.get("pharmacy_manager"))],
            ["Prestación o barrera", _value(a.get("request_mode") or a.get("service_requested"))],
            ["Orden o fórmula", _value(a.get("medical_order") or a.get("medical_order_detail"))],
            ["Riesgo vital reportado", _value(a.get("vital_risk"))],
            ["Tutela o desacato activo", _value(a.get("active_tutela") or a.get("active_contempt"))],
            ["Nivel del motor", _value(result.get("risk"))],
        ]},
        {"heading": "3. HECHOS QUE DEBEN QUEDAR ACREDITADOS", "numbered": [
            "Identidad y afiliación de la persona paciente.",
            "Orden, fórmula, remisión o decisión clínica exacta que sirve de soporte a la solicitud.",
            "Fecha, vigencia, profesional y contenido de la orden, sin modificar denominaciones, dosis o instrucciones.",
            "Barrera concreta: negación, demora, falta de agenda, falta de medicamento, interrupción, traslado entre actores u otra causa.",
            "Radicados, respuestas, autorizaciones, constancias de entrega y comunicaciones previas.",
            "Existencia de signos de alarma, riesgo vital o deterioro que exija atención inmediata y no una ruta documental ordinaria.",
            "Existencia de tutela, desacato, proceso judicial o actuación administrativa por los mismos hechos.",
        ]},
        {"heading": "4. PRINCIPIOS DE ACTUACIÓN", "numbered": [
            "Continuidad: una prestación iniciada no debe interrumpirse injustificadamente por trámites internos.",
            "Oportunidad: la gestión debe responder al riesgo y a las circunstancias particulares, no únicamente al término máximo de una petición.",
            "Integralidad de la coordinación: el usuario no debe convertirse en mensajero permanente entre entidades que participan en la misma prestación.",
            "Respuesta material: un radicado o la expresión 'en trámite' no reemplazan una decisión que resuelva lo solicitado e indique cómo se ejecutará.",
            "Minimización de datos: debe aportarse la información clínica estrictamente pertinente, evitando circular historias completas cuando no sean necesarias.",
        ]},
        {"heading": "5. DOCUMENTOS MÍNIMOS", "numbered": [
            "Documento de identidad y evidencia de afiliación cuando sean necesarios para legitimar la actuación.",
            "Orden médica, fórmula o soporte clínico pertinente y legible.",
            "Autorizaciones, negativas, constancias de no disponibilidad o pruebas de la demora.",
            "Radicados y respuestas anteriores.",
            "Evidencia de continuidad previa cuando el caso se refiera a una prestación ya iniciada.",
            "Poder, autorización o documento de representación cuando actúe un tercero.",
        ]},
        {"heading": "6. DECISIÓN DEL MOTOR", "paragraphs": [f"El expediente se encuentra clasificado por el motor con riesgo {_value(result.get('risk'))}. Estado temporal o de prioridad informado: {_value(c.get('priority') or c.get('classification') or a.get('priority'))}. La generación de documentos no elimina las compuertas de revisión profesional ni autoriza a usar esta ruta ante una urgencia vital." ]},
        _control("CO-SA-001", "Ante dolor extremo, dificultad respiratoria, pérdida de conciencia, deterioro rápido o peligro para la vida o integridad, la ruta documental debe ceder ante la atención asistencial urgente."),
    ]


def health_petition(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y ALCANCE", "paragraphs": [f"{_patient(a)} presenta petición y reclamo en salud para obtener una gestión coordinada y una respuesta de fondo respecto de {_value(a.get('service_requested') or a.get('request_mode'), 'la prestación identificada en el expediente')}. La solicitud no pretende sustituir el criterio médico, sino remover la barrera administrativa, documentar la decisión y obtener una fecha o mecanismo cierto de ejecución." ]},
        {"heading": "I. HECHOS", "numbered": [
            f"La persona paciente se encuentra vinculada a {_value(a.get('eps_name'), 'la EPS por identificar')}.",
            f"La orden o soporte clínico relevante se fecha o identifica como {_value(a.get('medical_order_date') or a.get('medical_order'))}.",
            f"La barrera reportada consiste en {_value(a.get('facts_detail') or a.get('barrier_detail'))}.",
            f"La gestión previa registrada corresponde a {_value(a.get('prior_filing_radicado') or a.get('prior_claim_radicado'), 'un radicado por confirmar')} de {_date(a.get('prior_filing_date') or a.get('prior_claim_date'))}.",
            "La persona solicitante no cuenta con facultades clínicas para sustituir, suspender o modificar por sí misma el tratamiento y requiere que las entidades responsables coordinen las actuaciones necesarias.",
        ]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Verificar el estado integral de la orden, autorización, asignación, agenda, dispensación o prestación objeto del reclamo.",
            "Adoptar las actuaciones administrativas necesarias para ejecutar la prestación sin trasladar al usuario la coordinación fragmentada entre EPS, IPS, gestor, proveedor o auditor.",
            "Informar una fecha cierta o, cuando ello dependa de una actuación clínica previa, identificar el paso, responsable y fecha en que será realizado.",
            "Cuando el proveedor inicialmente asignado no pueda cumplir oportunamente, evaluar y gestionar una alternativa efectiva dentro de las posibilidades jurídicas y clínicas aplicables.",
            "Si se considera necesaria una actualización, aclaración o valoración médica, programarla y explicar por qué es necesaria, evitando reiniciar injustificadamente todo el proceso.",
            "Si la prestación es negada o modificada, emitir una decisión individual, motivada y comprensible que identifique los hechos, soportes, responsable, alternativa y mecanismos de revisión.",
            "Responder por separado cada solicitud y remitir los documentos que soporten la decisión.",
            "Designar un canal de seguimiento que permita verificar la ejecución y no solo la emisión de una respuesta formal.",
        ]},
        {"heading": "III. PRIORIDAD, RESPUESTA Y EJECUCIÓN", "paragraphs": ["La entidad deberá clasificar el reclamo conforme al riesgo y al régimen sectorial vigente, sin utilizar el término máximo como justificación para demorar una actuación que las circunstancias clínicas exijan antes. Cuando un punto corresponda además a petición de información o documentos, deberá respetarse el término específico aplicable. Una respuesta favorable no cierra el expediente hasta que la prestación anunciada sea efectivamente ejecutada o exista evidencia de la solución material." ]},
        {"heading": "IV. DATOS Y RESERVA CLÍNICA", "paragraphs": ["La información de salud deberá circular únicamente entre quienes intervengan legítimamente en la atención, gestión, auditoría, control o cumplimiento legal. La petición no autoriza usos ajenos ni exige anexar una historia clínica completa cuando una fórmula, orden o resumen pertinente resulte suficiente." ]},
        _signature("PACIENTE O PETICIONARIO AUTORIZADO", a.get("petitioner_name") or a.get("patient_name"), a.get("petitioner_id") or a.get("patient_id")),
        _control("CO-SA-001"),
    ]


def health_reiteration(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. ANTECEDENTES", "paragraphs": [f"Se reitera la petición identificada con {_value(a.get('prior_filing_radicado') or a.get('prior_claim_radicado'))}, radicada el {_date(a.get('prior_filing_date') or a.get('prior_claim_date'))}. La reiteración debe utilizarse únicamente cuando exista evidencia de recepción y el problema continúe sin una solución material o la respuesta sea insuficiente." ]},
        {"heading": "2. DEFICIENCIAS", "numbered": [
            "Ausencia de respuesta dentro del término aplicable.",
            "Respuesta que se limita a indicar que el caso se encuentra en trámite sin decisión, fecha o responsable.",
            "Remisión del usuario a otro actor sin coordinación ni seguimiento.",
            "Negación o demora que no identifica fundamentos, alternativa o mecanismo de revisión.",
            "Solución anunciada que no fue ejecutada materialmente.",
        ]},
        {"heading": "3. SOLICITUDES", "numbered": [
            "Resolver integralmente cada punto pendiente.",
            "Informar el estado, responsable y fecha cierta de la actuación necesaria para superar la barrera.",
            "Coordinar directamente con los actores de la red y evitar nuevas remisiones circulares.",
            "Explicar la clasificación de prioridad aplicada y las razones de cualquier demora.",
            "Confirmar la conservación de los anexos ya aportados y abstenerse de exigir nuevamente información disponible en los sistemas de la entidad sin necesidad justificada.",
            "Informar los mecanismos de escalamiento y revisión disponibles si la solución continúa sin ejecutarse.",
        ]},
        _signature("PACIENTE O PETICIONARIO AUTORIZADO", a.get("petitioner_name") or a.get("patient_name"), a.get("petitioner_id") or a.get("patient_id")),
        _control("CO-SA-001"),
    ]


def health_supersalud(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO", "paragraphs": ["Se solicita la intervención de la Superintendencia Nacional de Salud frente a una barrera que persiste pese a las gestiones realizadas ante los actores responsables. La reclamación debe describir la situación, acreditar los radicados previos y pedir seguimiento dentro de las competencias de inspección, vigilancia, control y protección al usuario, sin anticipar una responsabilidad sancionatoria." ]},
        {"heading": "I. CRONOLOGÍA", "table": [
            ["Hito", "Fecha / estado"],
            ["Orden o soporte clínico", _date(a.get("medical_order_date"))],
            ["Primera gestión", _date(a.get("prior_filing_date") or a.get("prior_claim_date"))],
            ["Radicado", _value(a.get("prior_filing_radicado") or a.get("prior_claim_radicado"))],
            ["Respuesta", _value(a.get("prior_response") or a.get("response_status"))],
            ["Situación material", _value(a.get("facts_detail") or a.get("barrier_detail"))],
        ]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Clasificar la reclamación conforme a la naturaleza y riesgo del caso.",
            "Requerir a las entidades vigiladas para que expliquen y gestionen la barrera dentro de sus responsabilidades.",
            "Solicitar una respuesta que identifique la solución, responsable y fecha de ejecución.",
            "Verificar el trámite dado a los radicados previos y las razones de la falta de solución material.",
            "Realizar seguimiento al cumplimiento de la actuación anunciada y no únicamente a la expedición de una contestación.",
            "Informar a la persona usuaria el número de radicado, dependencia, clasificación y canales de consulta.",
            "Adoptar las actuaciones de control que resulten procedentes, respetando el debido proceso de los vigilados.",
        ]},
        {"heading": "III. RESERVA", "paragraphs": ["Los anexos clínicos deben utilizarse exclusivamente para la finalidad de protección y control asociada al expediente. La reclamación deberá minimizar datos sensibles no necesarios para comprender la barrera." ]},
        _signature("PACIENTE O PETICIONARIO AUTORIZADO", a.get("petitioner_name") or a.get("patient_name"), a.get("petitioner_id") or a.get("patient_id")),
        _control("CO-SA-001"),
    ]


def health_history_request(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y LEGITIMACIÓN", "paragraphs": [f"{_patient(a)} solicita acceso a la información clínica que le corresponde como titular. Cuando actúe una persona diferente, deberá acreditarse la autorización, representación o supuesto legal que habilite el acceso. La historia clínica es información sometida a reserva y no debe entregarse a terceros por simple parentesco o interés." ]},
        {"heading": "I. SOLICITUDES", "numbered": [
            "Entregar copia completa, legible, cronológica e íntegra del período solicitado.",
            "Incluir notas, evoluciones, epicrisis, órdenes, fórmulas, remisiones, consentimientos, informes, procedimientos y demás documentos que formen parte del expediente clínico pertinente.",
            "Entregar resultados e interpretaciones disponibles e informar el mecanismo técnico para obtener imágenes cuando no puedan suministrarse en el mismo formato.",
            "Identificar los profesionales y fechas de los registros tal como reposen en los sistemas.",
            "Informar expresamente cualquier documento inexistente, no generado, transferido a otro custodio o sujeto a una restricción jurídica específica.",
            "Entregar la información por un canal seguro y evitar remitirla a destinatarios distintos de los autorizados.",
        ]},
        {"heading": "II. SEGURIDAD DE LA ENTREGA", "paragraphs": ["Cuando la información se remita electrónicamente, la institución deberá utilizar un mecanismo razonable de seguridad. La identidad debe verificarse de manera proporcional y sin exigir información adicional que no sea necesaria para acreditar la calidad de titular o representante." ]},
        _signature("TITULAR O REPRESENTANTE AUTORIZADO", a.get("petitioner_name") or a.get("patient_name"), a.get("petitioner_id") or a.get("patient_id")),
        _control("CO-SA-001"),
    ]


def health_evidence(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. ÍNDICE PROBATORIO", "table": [
            ["ID", "Documento", "Hecho", "Sensibilidad", "Estado"],
            ["SA-EV-001", "Documento de identidad", "Identidad y legitimación", "Media", "Por verificar"],
            ["SA-EV-002", "Afiliación", "Relación con la EPS", "Media", "Por verificar"],
            ["SA-EV-003", "Orden o fórmula", "Prestación y condiciones clínicas", "Alta", "Obligatorio"],
            ["SA-EV-004", "Resumen clínico pertinente", "Necesidad, continuidad o contexto", "Alta", "Condicional"],
            ["SA-EV-005", "Autorización o constancia de entrega", "Estado de ejecución", "Media", "Condicional"],
            ["SA-EV-006", "Negativa, demora o no disponibilidad", "Barrera", "Media", "Por verificar"],
            ["SA-EV-007", "Petición previa", "Gestión del usuario", "Baja", "Condicional"],
            ["SA-EV-008", "Acuse / radicado", "Fecha de recepción", "Baja", "Crítico para términos"],
            ["SA-EV-009", "Respuesta", "Posición de la entidad", "Variable", "Condicional"],
        ]},
        {"heading": "2. REGLAS DE PRIVACIDAD", "numbered": [
            "No anexar la historia clínica completa si una orden y un resumen pertinente son suficientes.",
            "Suprimir datos de terceros que no resulten necesarios.",
            "No circular información especialmente sensible sin relación directa con la pretensión.",
            "Conservar originales y una copia exacta de la versión radicada.",
            "Utilizar canales verificados y proteger archivos clínicos cuando el riesgo lo justifique.",
        ]},
        {"heading": "3. GUÍA DE RADICACIÓN", "numbered": [
            "Verificar el canal oficial vigente de la entidad destinataria.",
            "Conservar evidencia del canal utilizado y de la fecha y hora de envío.",
            "Radicar los anexos en un conjunto ordenado y comprobar que puedan abrirse.",
            "Solicitar número de radicado o acuse y conservarlo con la versión exacta del documento.",
            "Presentar cualquier ampliación como alcance separado para no perder la cronología.",
        ]},
        _control("CO-SA-001"),
    ]


def health_calendar(a: dict, result: dict) -> list[dict]:
    c = result.get("calculation") if isinstance(result.get("calculation"), dict) else {}
    return [
        {"heading": "1. CALENDARIO DE SEGUIMIENTO", "table": [
            ["Actuación", "Fecha o regla", "Estado"],
            ["Radicación", _date(a.get("filing_date") or a.get("prior_filing_date")), "Por confirmar"],
            ["Clasificación sectorial", _value(c.get("priority") or c.get("classification") or a.get("priority")), "Requiere seguimiento"],
            ["Respuesta documental", _value(c.get("petition_due_date") or c.get("due_date")), "Automático si el motor dispone del dato"],
            ["Reiteración", "Después de vencimiento o respuesta insuficiente", "Condicional"],
            ["Supersalud", "Persistencia de barrera o falta de solución", "Condicional"],
            ["Tutela", "Solo tras evaluación jurídica de riesgo y subsidiariedad", "Revisión humana"],
            ["Cierre", "Solución material o decisión final documentada", "Pendiente"],
        ]},
        {"heading": "2. REGLA DE CIERRE", "paragraphs": ["El expediente distingue respuesta, autorización, programación y ejecución. No deberá marcarse como resuelto únicamente porque exista una contestación si la prestación sigue sin materializarse. Ante aparición de riesgo vital o deterioro urgente, el seguimiento documental ordinario deja de ser la ruta principal." ]},
        _control("CO-SA-001"),
    ]


# ---------------------------------------------------------------------------
# CO-TR-001 — verificación SAST
# ---------------------------------------------------------------------------


def sast_report(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. OBJETO DEL INFORME", "paragraphs": ["El informe verifica si el punto tecnológico identificado puede relacionarse de manera suficiente con una autorización, ubicación, autoridad competente, modalidad tecnológica, condiciones de operación, señalización, soportes metrológicos y actuaciones de inspección. No declara por sí mismo que el sistema sea legal o ilegal y no anula comparendos individuales." ]},
        {"heading": "2. IDENTIFICACIÓN PRELIMINAR", "table": [
            ["Elemento", "Información"],
            ["Solicitante", _value(a.get("requester_name") or a.get("name"))],
            ["Municipio", _value(a.get("municipality"))],
            ["Autoridad", _value(a.get("traffic_authority"))],
            ["Punto / identificador", _value(a.get("sast_id") or a.get("device_id"))],
            ["Ubicación", _value(a.get("location_detail") or a.get("location"))],
            ["Tipo", _value(a.get("device_type"))],
            ["Fecha relevante", _date(a.get("observation_date") or a.get("reference_date"))],
        ]},
        {"heading": "3. CUATRO CAPAS DE VERIFICACIÓN", "numbered": [
            "Autorización del punto: acto, autoridad, coordenadas, modalidad, vigencia, modificaciones y eventual excepción legal.",
            "Condiciones de operación: estudios, señalización, dispositivo, configuración, mantenimiento, trazabilidad metrológica y períodos efectivos de uso.",
            "Inspección y control: requerimientos, investigaciones, decisiones, recursos, firmeza y órdenes expedidas por las autoridades competentes.",
            "Caso individual: detección, validación, comparendo, notificación, audiencia, sanción, ejecutoria, reportes, pago y cobro cuando una persona concreta resulte afectada.",
        ]},
        {"heading": "4. REGLAS DE INTERPRETACIÓN", "numbered": [
            "No encontrado no equivale a inexistente ni a no autorizado.",
            "Autorizado no demuestra por sí solo que todas las condiciones de operación se cumplieron durante cada período.",
            "Investigado no equivale a responsable ni a decisión firme.",
            "Una decisión general no determina automáticamente el resultado de cada comparendo individual.",
            "La coincidencia exige relacionar punto, equipo, período, autoridad y, cuando exista, expediente individual.",
        ]},
        {"heading": "5. RESULTADO", "paragraphs": [f"Resultado preliminar informado por el motor: {_value(result.get('status') or result.get('summary') or result.get('risk'))}. La conclusión final debe utilizar categorías controladas como verificado, verificado con observaciones, no concluyente, inconsistencia documentada o escalamiento obligatorio, evitando expresiones automáticas como 'fotomulta ilegal' o 'comparendo anulado'." ]},
        _control("CO-TR-001"),
    ]


def sast_traceability(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. MATRIZ DE TRAZABILIDAD", "table": [
            ["Capa", "Componente", "Documento esperado", "Estado"],
            ["Identificación", "Autoridad", "Certificación de competencia", "Por verificar"],
            ["Identificación", "Punto", "Ficha, ubicación y coordenadas", "Por verificar"],
            ["Autorización", "Acto principal", "Resolución o autorización", "Por verificar"],
            ["Autorización", "Renovación o modificación", "Actos posteriores", "Condicional"],
            ["Excepción", "Régimen especial", "Soporte jurídico y fáctico", "Condicional"],
            ["Operación", "Estudio técnico", "Accidentalidad, flujo y justificación", "Por verificar"],
            ["Operación", "Señalización", "Plan, instalación y evidencia histórica", "Por verificar"],
            ["Operación", "Dispositivo", "Marca, modelo, serial y configuración", "Por verificar"],
            ["Metrología", "Soporte", "Certificado aplicable al período", "Condicional"],
            ["Control", "Actuaciones", "Autos, decisiones y firmeza", "Condicional"],
            ["Individual", "Comparendo", "Expediente completo", "Solo si existe"],
        ]},
        {"heading": "2. REGLAS DE EVIDENCIA", "paragraphs": ["Cada documento debe registrar entidad, fecha, versión, fuente, período al que corresponde y relación concreta con el punto. Las fotografías actuales no acreditan por sí solas la señalización o configuración histórica; una autorización posterior tampoco demuestra automáticamente la situación de un período anterior." ]},
        _control("CO-TR-001"),
    ]


def sast_registration(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. FINALIDAD DE LA INSCRIPCIÓN", "paragraphs": ["La inscripción abre un expediente en LegalAIZ.it para organizar información, consultar fuentes públicas, preparar solicitudes y mantener trazabilidad. No es una inscripción oficial del dispositivo, no otorga representación y no certifica la legalidad o ilegalidad del punto." ]},
        {"heading": "2. AUTORIZACIONES LIMITADAS", "numbered": [
            "Tratar los datos necesarios para crear y gestionar el expediente.",
            "Consultar fuentes públicas relacionadas con autorizaciones, actos, decisiones, normas, conceptos y actuaciones de control.",
            "Generar documentos y registrar revisiones para que la persona usuaria los revise antes de radicarlos.",
            "Enviar comunicaciones relacionadas con el expediente por los canales autorizados.",
        ]},
        {"heading": "3. LÍMITES", "numbered": ["La inscripción no constituye poder ni mandato.", "LegalAIZ.it no firma por el usuario, no acepta infracciones, no desiste, no presenta recursos ni concilia sin la habilitación profesional y documental correspondiente.", "Las fuentes consultadas y sus limitaciones deberán quedar registradas en el expediente."]},
        _signature("PERSONA USUARIA", a.get("requester_name") or a.get("name"), a.get("requester_id")),
        _control("CO-TR-001"),
    ]


def sast_record_request(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y FINALIDAD", "paragraphs": ["Se solicita información y documentación oficial para identificar correctamente el sistema tecnológico observado y diferenciar autorización, operación, inspección y eventual relación con actuaciones individuales. La petición no afirma anticipadamente que el dispositivo carezca de autorización o funcione irregularmente." ]},
        {"heading": "I. IDENTIFICACIÓN DEL PUNTO", "numbered": [
            "Confirmar si el dispositivo existe y se encuentra bajo responsabilidad o utilización de la autoridad destinataria.",
            "Identificar código, marca, modelo, serial, tecnología, carácter fijo o móvil, propietario, operador, contratista, ubicación, coordenadas y sentido vial.",
            "Informar las infracciones o eventos para los cuales se encuentra configurado el sistema.",
        ]},
        {"heading": "II. AUTORIZACIÓN Y VIGENCIA", "numbered": [
            "Entregar el acto de autorización aplicable, sus anexos, modificaciones, renovaciones, suspensiones y períodos de vigencia.",
            "Informar la correspondencia entre el punto real y las coordenadas o referencias del acto.",
            "Si se invoca una excepción a la autorización, identificar su fundamento y aportar los documentos que demuestren que el supuesto fáctico se cumple.",
        ]},
        {"heading": "III. OPERACIÓN TÉCNICA", "numbered": [
            "Entregar estudios de accidentalidad, flujo, riesgo vial, geometría, velocidad y justificación del punto que correspondan al régimen aplicable.",
            "Entregar la documentación histórica de señalización, incluyendo ubicación, fecha de instalación, mantenimiento y evidencia del período consultado.",
            "Entregar hoja de vida, mantenimiento y soportes metrológicos del dispositivo cuando efectúe mediciones.",
            "Informar fechas de inicio, suspensión, mantenimiento, reemplazo o deshabilitación del sistema.",
        ]},
        {"heading": "IV. INSPECCIÓN Y CONTROL", "numbered": [
            "Informar investigaciones, visitas, requerimientos, decisiones, recursos, órdenes o medidas relacionadas con el punto o el organismo.",
            "Distinguir expresamente actuaciones en trámite de decisiones firmes.",
            "Identificar cualquier período de operación que una decisión firme haya determinado como no cubierto por autorización y las medidas adoptadas respecto de ese período.",
        ]},
        {"heading": "V. RESPUESTA Y TRASLADO", "paragraphs": ["Cada entidad deberá responder dentro de sus competencias, trasladar los puntos ajenos cuando corresponda e informar el traslado. Una negativa por reserva debe identificar la regla específica y el alcance de la restricción. La remisión a un portal solo es suficiente si identifica exactamente el documento consultable y este se encuentra disponible." ]},
        _signature("PERSONA PETICIONARIA", a.get("requester_name") or a.get("name"), a.get("requester_id")),
        _control("CO-TR-001"),
    ]


def sast_inspection(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. REGLA DE ACTIVACIÓN", "paragraphs": ["La solicitud de revisión o inspección solo debe generarse cuando las respuestas oficiales, actos o pruebas revelen una inconsistencia verificable. Una búsqueda sin resultados o una noticia no constituyen por sí solas fundamento suficiente para afirmar incumplimiento." ]},
        {"heading": "2. INCONSISTENCIAS DOCUMENTADAS", "numbered": [
            _value(a.get("documented_inconsistency") or a.get("facts_detail"), "Las inconsistencias deben incorporarse desde los documentos oficiales antes de radicar."),
            "Comparar punto real, coordenadas, modalidad, serial, vigencia, señalización, soportes metrológicos y período de operación.",
            "Distinguir cualquier diferencia de identificación de una conclusión sobre la validez de comparendos concretos.",
        ]},
        {"heading": "3. SOLICITUDES", "numbered": [
            "Verificar la correspondencia entre dispositivo, punto, autorización y período.",
            "Verificar las condiciones técnicas y de señalización que resulten exigibles.",
            "Determinar si la ubicación se encontraba autorizada o comprendida en una excepción.",
            "Examinar la trazabilidad metrológica cuando exista una medición relevante.",
            "Identificar las detecciones producidas durante cualquier período objeto de revisión.",
            "Adelantar, si existe mérito, las actuaciones de inspección, vigilancia o control correspondientes y comunicar su resultado.",
        ]},
        _signature("PERSONA SOLICITANTE", a.get("requester_name") or a.get("name"), a.get("requester_id")),
        _control("CO-TR-001"),
    ]


def sast_followup(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. MOTIVO DE LA REITERACIÓN", "paragraphs": ["La reiteración se utiliza frente a silencio, respuesta parcial, remisión sin documento, falta de identificación del punto, omisión de vigencia, reserva no explicada o contradicciones entre respuesta y anexos. Debe identificar exactamente qué solicitud sigue pendiente." ]},
        {"heading": "2. SOLICITUDES", "numbered": [
            "Resolver separadamente cada punto pendiente.",
            "Entregar los documentos faltantes o certificar expresamente su inexistencia o falta de custodia.",
            "Informar los criterios utilizados para localizar e identificar el dispositivo.",
            "Precisar vigencia, ubicación, excepción y régimen técnico aplicable.",
            "Distinguir investigaciones de decisiones firmes y aportar las constancias correspondientes.",
            "Corregir contradicciones y trasladar las materias ajenas a la competencia de la entidad.",
        ]},
        {"heading": "3. ESCALAMIENTO", "table": [
            ["Situación", "Ruta"],
            ["Falta de documentos", "Reiteración y control del derecho de petición"],
            ["Posible incumplimiento técnico", "Autoridad de inspección competente"],
            ["Comparendo o sanción individual", "CO-TR-002"],
            ["Cobro o embargo", "Revisión profesional urgente"],
            ["Pago y eventual devolución", "Análisis individual del acto habilitante"],
            ["Proceso judicial", "Bloqueo de automatización ordinaria"],
        ]},
        _signature("PERSONA SOLICITANTE", a.get("requester_name") or a.get("name"), a.get("requester_id")),
        _control("CO-TR-001"),
    ]


def sast_package(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. SEMÁFORO JURÍDICO", "table": [
            ["Componente", "Estado"],
            ["Identificación", _value(a.get("identification_status"), "Pendiente de cotejo")],
            ["Autorización", _value(a.get("authorization_status"), "Pendiente de cotejo")],
            ["Vigencia", _value(a.get("authorization_validity"), "Pendiente de cotejo")],
            ["Excepción", _value(a.get("exception_status"), "No determinada")],
            ["Señalización", _value(a.get("signage_status"), "Pendiente de cotejo")],
            ["Metrología", _value(a.get("metrology_status"), "Pendiente de cotejo")],
            ["Control institucional", _value(a.get("inspection_status"), "No determinado")],
            ["Caso individual", _value(a.get("individual_case_status"), "No aportado")],
        ]},
        {"heading": "2. RESULTADOS PERMITIDOS", "numbered": ["Verificado favorablemente.", "Verificado con observaciones.", "No concluyente.", "Inconsistencia documentada.", "Escalamiento obligatorio.", "Fuera del alcance del producto."]},
        {"heading": "3. EXPRESIONES NO AUTOMATIZABLES", "numbered": ["Fotomulta ilegal.", "Cámara ilegal.", "Comparendo anulado.", "No tiene que pagar.", "Prescribió.", "La autoridad debe devolver el dinero." ]},
        {"heading": "4. QA", "numbered": ["Verificar identidad exacta del punto.", "Relacionar la autorización con el período.", "Descartar excepciones antes de concluir ausencia de autorización.", "Distinguir investigación, decisión y firmeza.", "Analizar el régimen temporal de requisitos técnicos.", "Separar siempre el chequeo del sistema de la defensa de un caso individual."]},
        _control("CO-TR-001"),
    ]


# ---------------------------------------------------------------------------
# CO-TR-002 — fotodetección no notificada
# ---------------------------------------------------------------------------


def traffic_diagnostic(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. OBJETO DEL DIAGNÓSTICO", "paragraphs": ["El diagnóstico reconstruye la secuencia completa del procedimiento contravencional y evita deducir el estado jurídico a partir de una captura aislada. Detección, validación, comparendo, envío, entrega, conocimiento real, audiencia, sanción, notificación del acto, ejecutoria y cobro son hitos distintos y cada uno requiere su propio soporte." ]},
        {"heading": "2. DATOS DEL CASO", "table": [
            ["Elemento", "Información"],
            ["Persona", _value(a.get("requester_name") or a.get("owner_name"))],
            ["Vehículo", _value(a.get("vehicle_plate"))],
            ["Comparendo", _value(a.get("citation_number") or a.get("comparendo_number"))],
            ["Detección", _date(a.get("detection_date"))],
            ["Validación", _date(a.get("validation_date"))],
            ["Conocimiento real", _date(a.get("actual_knowledge_date"))],
            ["Sanción conocida", _value(a.get("sanction_exists"))],
            ["Cobro coactivo", _value(a.get("collection_exists"))],
            ["Pago", _value(a.get("paid"))],
        ]},
        {"heading": "3. CRONOLOGÍA A RECONSTRUIR", "numbered": [
            "Fecha y soporte de la detección tecnológica.",
            "Fecha y registro de validación.",
            "Generación de la orden de comparendo.",
            "Consulta de datos del propietario o destinatario.",
            "Envío, intentos, entrega o devolución.",
            "Notificación subsidiaria cuando corresponda.",
            "Comparecencia, audiencia y pruebas.",
            "Resolución sancionatoria y notificación.",
            "Recursos y ejecutoria.",
            "Mandamiento de pago, notificación, excepciones y medidas si existe cobro.",
        ]},
        {"heading": "4. REGLAS DE INTERPRETACIÓN", "numbered": [
            "El comparendo no es la sanción.",
            "El envío no equivale automáticamente a entrega.",
            "El conocimiento posterior en una consulta no reemplaza sin análisis la oportunidad procesal que debió existir antes.",
            "La propiedad del vehículo no sustituye automáticamente la individualización de la conducta y la responsabilidad que la autoridad pretenda atribuir.",
            "La falta de notificación no produce una fórmula universal de nulidad: debe analizarse qué actuaciones siguieron y cómo afectó materialmente la defensa.",
            "Caducidad y prescripción son instituciones diferentes y requieren fechas y actos distintos.",
        ]},
        {"heading": "5. RESULTADO", "paragraphs": [f"Nivel del motor: {_value(result.get('risk'))}. Estado preliminar: {_value(result.get('status') or result.get('summary'))}. El documento habilita la solicitud de expediente y, según la respuesta, una reclamación de notificación, audiencia, revocación condicionada, corrección de registros o escalamiento profesional." ]},
        _control("CO-TR-002", "Una resolución próxima a quedar firme, un cobro coactivo, embargo, pago previo o término judicial exige revisión profesional inmediata."),
    ]


def traffic_record_request(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y RESERVA", "paragraphs": ["Se solicita copia íntegra del expediente y determinación del estado procesal. La petición no implica aceptación de la infracción, identificación voluntaria de conductor, convalidación de notificaciones, renuncia a recursos ni reconocimiento de exigibilidad." ]},
        {"heading": "I. EXPEDIENTE TÉCNICO", "numbered": [
            "Entregar imagen o video original, metadatos y registros necesarios para verificar fecha, hora, ubicación, placa, dispositivo, medición e integridad.",
            "Identificar el SAST, punto, autorización, vigencia, señalización y soportes técnicos o metrológicos aplicables.",
            "Identificar al funcionario que validó la detección, su competencia, fecha y registro de la actuación.",
        ]},
        {"heading": "II. DATOS Y NOTIFICACIÓN", "numbered": [
            "Certificar la consulta realizada para obtener los datos de notificación y la fecha de esa consulta.",
            "Entregar el dato obtenido y la dirección, correo o canal efectivamente utilizados.",
            "Entregar la orden postal, guía, intentos, novedades, devolución y certificaciones del operador.",
            "Informar cualquier segundo intento, notificación electrónica o aviso y aportar sus constancias completas.",
            "Emitir una explicación motivada sobre la validez de la notificación y la forma en que se produjo la vinculación al procedimiento.",
        ]},
        {"heading": "III. ESTADO PROCESAL", "numbered": [
            "Informar si existe únicamente comparendo, audiencia, resolución, recursos, ejecutoria, acuerdo, pago, mandamiento de pago, cobro o medida cautelar.",
            "Entregar copia íntegra de cada acto existente y su constancia de notificación y firmeza.",
            "Aportar actas, grabaciones o registros de comparecencia y cualquier manifestación atribuida a la persona investigada.",
        ]},
        {"heading": "IV. RESPONSABILIDAD", "numbered": [
            "Indicar si la imputación se dirige contra la persona como conductora, propietaria por un deber propio u otra calidad.",
            "Identificar la conducta, norma, prueba y análisis de responsabilidad utilizados.",
            "Abstenerse de fundamentar una sanción exclusivamente en la titularidad o en la falta de identificación voluntaria de un tercero sin desarrollar la imputación individual pertinente.",
        ]},
        {"heading": "V. COBRO", "numbered": [
            "Si existe cobro, entregar título, liquidación, mandamiento de pago, prueba de notificación, excepciones, decisiones, medidas cautelares, pagos y acuerdos.",
            "Informar si existe alguna restricción registral o medida vigente y su fundamento.",
        ]},
        _signature("PERSONA PETICIONARIA", a.get("requester_name") or a.get("owner_name"), a.get("requester_id") or a.get("owner_id")),
        _control("CO-TR-002"),
    ]


def traffic_notification_claim(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. REGLA DE ACTIVACIÓN", "paragraphs": ["La reclamación por indebida notificación solo se genera cuando el expediente suministra evidencia suficiente para comparar los datos oficiales, el canal utilizado, el resultado del envío y las actuaciones posteriores. La simple manifestación de no haber recibido el comparendo no debe convertirse en una conclusión automática de invalidez." ]},
        {"heading": "2. HALLAZGOS", "numbered": [
            f"Dato oficial o histórico relevante: {_value(a.get('official_address') or a.get('runt_address'))}.",
            f"Dato utilizado por la autoridad: {_value(a.get('used_address') or a.get('notification_address'))}.",
            f"Resultado del envío: {_value(a.get('postal_result'))}.",
            f"Actuación subsidiaria acreditada: {_value(a.get('secondary_notification'))}.",
            f"Fecha de conocimiento real: {_date(a.get('actual_knowledge_date'))}.",
        ]},
        {"heading": "3. AFECTACIÓN A EXAMINAR", "paragraphs": ["La autoridad debe determinar si la irregularidad impidió conocer oportunamente la imputación, acceder a la evidencia, comparecer, solicitar audiencia, pedir y controvertir pruebas, ejercer alternativas o recurrir la decisión. La consecuencia jurídica debe responder a esa afectación material y al estado actual del expediente." ]},
        {"heading": "4. SOLICITUDES", "numbered": [
            "Pronunciarse expresamente sobre la validez de la notificación con base en los documentos del expediente.",
            "Efectuar la actuación de notificación que corresponda cuando la anterior no resulte jurídicamente suficiente.",
            "Reconocer los términos que deban comenzar desde una notificación válida.",
            "Determinar qué actuaciones posteriores fueron afectadas por la falta de vinculación y restablecer la oportunidad de defensa cuando proceda.",
            "Si no se retrotrae el trámite, explicar cuál actuación subsanó el defecto, cuándo ocurrió, qué conocimiento se atribuye y qué defensa efectiva permaneció disponible.",
        ]},
        _signature("PERSONA RECLAMANTE", a.get("requester_name") or a.get("owner_name"), a.get("requester_id") or a.get("owner_id")),
        _control("CO-TR-002"),
    ]


def traffic_hearing(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "COMPARECENCIA Y RESERVA", "paragraphs": ["La persona comparece para ejercer defensa y contradicción. La comparecencia no constituye por sí sola aceptación de la infracción, confesión de conducción, renuncia a cuestionar la notificación ni aceptación de la suficiencia de la evidencia tecnológica." ]},
        {"heading": "I. PRUEBAS SOLICITADAS", "numbered": [
            "Expediente íntegro y archivo original de la evidencia tecnológica.",
            "Metadatos, identificación del dispositivo, punto, autorización, señalización y soportes técnicos pertinentes.",
            "Registro de validación y competencia del funcionario que intervino.",
            "Consulta histórica de datos utilizada para la notificación y todas las constancias de envío, entrega, devolución o aviso.",
            "Pruebas necesarias para establecer la persona y conducta que se pretende imputar.",
            "Incorporación y valoración de la evidencia aportada por la defensa.",
        ]},
        {"heading": "II. RESPONSABILIDAD", "paragraphs": ["La autoridad deberá precisar si atribuye la conducta a la persona como conductora o por el incumplimiento de un deber propio en otra calidad, y desarrollar el fundamento normativo, la conducta, la prueba y el análisis de responsabilidad correspondientes. No debe sustituirse ese análisis por una presunción automática derivada de la propiedad del vehículo." ]},
        {"heading": "III. CONTRADICCIÓN Y DECISIÓN", "numbered": [
            "Permitir acceso, copia y estudio de las pruebas antes de su valoración definitiva.",
            "Resolver motivadamente cualquier negativa probatoria.",
            "Valorar los descargos y explicar por qué cada prueba conduce o no a la conclusión adoptada.",
            "Notificar la decisión y explicar los recursos o mecanismos procedentes.",
        ]},
        _signature("PERSONA COMPARECIENTE", a.get("requester_name") or a.get("owner_name"), a.get("requester_id") or a.get("owner_id")),
        _control("CO-TR-002"),
    ]


def traffic_revocation(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. CONTROL DE ACTIVACIÓN", "numbered": ["Existe un acto administrativo identificado y se cuenta con copia íntegra.", "Se conoce su forma de notificación y estado de ejecutoria.", "Se han revisado los recursos ejercidos o disponibles.", "Se ha verificado si existe proceso judicial, pago, cobro o medida cautelar.", "Existe una causal de revocación conectada con hechos y pruebas concretas." ]},
        {"heading": "2. ACTO OBJETO", "table": [["Elemento", "Información"], ["Resolución", _value(a.get("sanction_resolution"))], ["Fecha", _date(a.get("sanction_date"))], ["Comparendo", _value(a.get("citation_number") or a.get("comparendo_number"))], ["Notificación", _value(a.get("sanction_notification"))], ["Ejecutoria", _date(a.get("enforceability_date"))]]},
        {"heading": "3. FUNDAMENTOS", "paragraphs": ["La solicitud debe conectar la causal jurídica concreta con la irregularidad demostrada. No debe utilizarse como sustituto automático de recursos vencidos, como mecanismo para suspender por sí sola el acto o como forma de detener términos judiciales que deban ser evaluados separadamente." ]},
        {"heading": "4. SOLICITUDES", "numbered": ["Revocar el acto cuando se configuren los presupuestos legales demostrados.", "Adoptar las medidas necesarias para restablecer el procedimiento y definir expresamente el estado del comparendo.", "Comunicar la decisión a las dependencias y sistemas que deban reflejarla.", "Informar el resultado al área de cobro cuando exista actuación coactiva.", "En caso de negativa, resolver los argumentos individualmente y explicar los mecanismos posteriores disponibles." ]},
        _signature("PERSONA SOLICITANTE", a.get("requester_name") or a.get("owner_name"), a.get("requester_id") or a.get("owner_id")),
        _control("CO-TR-002"),
    ]


def traffic_registry(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. ACTO HABILITANTE", "paragraphs": ["La corrección registral únicamente se solicita después de contar con un acto, decisión judicial, pago, archivo, revocación u otro soporte que jurídicamente obligue a modificar el estado reflejado. La actualización del sistema no sustituye el acto fuente ni puede utilizarse para declarar por sí sola la invalidez de una sanción." ]},
        {"heading": "2. INCONSISTENCIAS", "table": [["Registro", "Estado actual", "Estado que debe reflejar"], ["Sistema interno", _value(a.get("internal_registry_status")), _value(a.get("expected_registry_status"))], ["SIMIT", _value(a.get("simit_status")), _value(a.get("expected_simit_status"))], ["RUNT", _value(a.get("runt_status")), _value(a.get("expected_runt_status"))], ["Cobro", _value(a.get("collection_status")), _value(a.get("expected_collection_status"))]]},
        {"heading": "3. SOLICITUDES", "numbered": ["Ejecutar integralmente el acto habilitante.", "Actualizar la base interna y transmitir la novedad a los sistemas externos correspondientes.", "Informar la fecha, mecanismo y resultado de la transmisión.", "Verificar la recepción y corregir inconsistencias residuales.", "Entregar evidencia del estado final y señalar cualquier dependencia que continúe reflejando una obligación incompatible con el acto fuente." ]},
        _signature("PERSONA SOLICITANTE", a.get("requester_name") or a.get("owner_name"), a.get("requester_id") or a.get("owner_id")),
        _control("CO-TR-002"),
    ]


def traffic_evidence(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. CRONOLOGÍA PROBATORIA", "table": [
            ["Hito", "Fecha", "Documento", "Estado"],
            ["Detección", _date(a.get("detection_date")), "Archivo original", "Por verificar"],
            ["Validación", _date(a.get("validation_date")), "Registro de validación", "Por verificar"],
            ["Consulta de datos", _date(a.get("registry_query_date")), "Log o certificación", "Por verificar"],
            ["Envío", _date(a.get("mailing_date")), "Guía", "Por verificar"],
            ["Entrega o devolución", _date(a.get("delivery_or_return_date")), "Trazabilidad postal", "Por verificar"],
            ["Aviso", _date(a.get("notice_date")), "Constancia", "Condicional"],
            ["Audiencia", _date(a.get("hearing_date")), "Acta / grabación", "Condicional"],
            ["Resolución", _date(a.get("sanction_date")), "Acto íntegro", "Condicional"],
            ["Ejecutoria", _date(a.get("enforceability_date")), "Constancia", "Condicional"],
            ["Mandamiento de pago", _date(a.get("payment_order_date")), "Expediente coactivo", "Condicional"],
            ["Conocimiento real", _date(a.get("actual_knowledge_date")), "Consulta o evidencia", "Por verificar"],
        ]},
        {"heading": "2. MATRIZ DE NOTIFICACIÓN", "numbered": ["Histórico oficial de datos para la fecha relevante.", "Consulta efectuada por la autoridad.", "Dirección o canal obtenido.", "Orden de envío y guía completa.", "Intentos y causal de devolución.", "Notificación electrónica, cuando exista.", "Aviso subsidiario, cuando exista.", "Prueba de notificación de la resolución sancionatoria.", "Constancia de ejecutoria."]},
        {"heading": "3. MATRIZ DE RESPONSABILIDAD", "numbered": ["Calidad en la que se vincula a la persona.", "Conducta concreta imputada.", "Norma aplicable.", "Prueba de autoría o deber propio.", "Análisis de responsabilidad y culpabilidad que corresponda.", "Oportunidad real de defensa y contradicción." ]},
        {"heading": "4. CADUCIDAD, PRESCRIPCIÓN Y COBRO", "paragraphs": ["Estas instituciones no se calculan únicamente desde la fecha de la captura o de la consulta. El expediente debe incorporar decisión, notificación, recursos, ejecutoria, mandamiento de pago, notificación del cobro y demás actos que puedan modificar el cómputo. La matriz organiza las fechas; no declara automáticamente una consecuencia jurídica." ]},
        _control("CO-TR-002"),
    ]


def traffic_guide(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. RADICACIÓN Y TRAZABILIDAD", "numbered": ["Conservar la versión exacta radicada.", "Registrar hash o identificador, fecha, hora, canal, autoridad, radicado y anexos.", "Verificar que todos los archivos puedan abrirse.", "Presentar ampliaciones como alcances separados.", "Conservar la respuesta y todos los anexos anunciados por la autoridad." ]},
        {"heading": "2. COMPUERTA DE ACTO ADVERSO", "paragraphs": ["La llegada de una resolución, decisión de recurso, mandamiento de pago o medida cautelar exige una alerta inmediata. El sistema debe extraer número, fecha, autoridad, decisión, forma de notificación, recurso, término y fecha límite, y no esperar al siguiente ciclo ordinario de seguimiento." ]},
        {"heading": "3. SEMÁFORO PROCESAL", "table": [
            ["Estado", "Acción"],
            ["Solo comparendo sin notificación acreditada", "Obtener expediente y definir vinculación"],
            ["Oportunidad de defensa abierta", "Audiencia y pruebas"],
            ["Acto no firme", "Revisar recursos inmediatamente"],
            ["Acto firme", "Evaluar revocación y medio judicial"],
            ["Cobro coactivo", "Obtener expediente coactivo y analizar excepciones"],
            ["Embargo", "Revisión profesional urgente"],
            ["Pago previo", "Analizar sus efectos y eventual devolución únicamente con soporte"],
            ["Proceso judicial", "Bloquear automatización ordinaria"],
        ]},
        {"heading": "4. LENGUAJE CONTROLADO", "paragraphs": ["Las conclusiones deberán describir lo que está acreditado y lo que falta: 'la notificación no se encuentra acreditada', 'existe una inconsistencia entre la dirección histórica y la utilizada' o 'la consecuencia debe definirse con el expediente completo'. Se prohíben resultados automáticos como 'la fotomulta es ilegal', 'la multa está anulada', 'no tiene que pagar', 'prescribió' o 'le deben devolver el dinero'." ]},
        _control("CO-TR-002"),
    ]


# ---------------------------------------------------------------------------
# Integración semántica con kinds históricos
# ---------------------------------------------------------------------------


def _health(specs, a, result, metadata):
    mappings = [
        (lambda k,t: "diagn" in k or "diagn" in t, "health_diagnostic", "Diagnóstico jurídico y clínico-administrativo", "diagnostico_salud", health_diagnostic(a,result)),
        (lambda k,t: ("history" in k or "historia" in t or "clinical" in k) and "diagn" not in k, "health_history_request", "Solicitud reservada de historia clínica", "historia_clinica", health_history_request(a,result)),
        (lambda k,t: "reiter" in k or "reiter" in t, "health_reiteration", "Reiteración de petición y reclamo en salud", "reiteracion_salud", health_reiteration(a,result)),
        (lambda k,t: "super" in k or "super" in t or "authority" in k, "health_supersalud", "Reclamación y solicitud de intervención ante Supersalud", "supersalud", health_supersalud(a,result)),
        (lambda k,t: "evidence" in k or "evidenc" in t or "matrix" in k or "radic" in t, "health_evidence", "Índice probatorio y guía de radicación", "evidencia_salud", health_evidence(a,result)),
        (lambda k,t: "calendar" in k or "deadline" in k or "calend" in t or "seguimiento" in t, "health_calendar", "Calendario de términos, seguimiento y escalamiento", "calendario_salud", health_calendar(a,result)),
        (lambda k,t: "petition" in k or "peticion" in t or ("claim" in k and "super" not in k), "health_petition", "Petición y reclamo priorizado en salud", "peticion_salud", health_petition(a,result)),
    ]
    added=set()
    predicates=[]
    for pred, kind, title, suffix, sections in mappings:
        predicates.append(pred); _upsert(specs,pred,kind=kind,title=title,suffix=suffix,sections=sections,metadata=metadata); added.add(kind)
    return _retain_only(specs,predicates,added)


def _tr1(specs,a,result,metadata):
    mappings=[
        (lambda k,t:"diagn" in k or "informe" in t or "report" in k,"sast_report","Informe jurídico-operativo de verificación SAST","informe_sast",sast_report(a,result)),
        (lambda k,t:"trace" in k or "traz" in t or "matrix" in k,"sast_traceability","Matriz de trazabilidad jurídica y técnica","trazabilidad_sast",sast_traceability(a,result)),
        (lambda k,t:"register" in k or "inscrip" in t or "registration" in k,"sast_registration","Inscripción verificada al servicio de chequeo SAST","inscripcion_sast",sast_registration(a,result)),
        (lambda k,t:"record" in k or "exped" in t or ("request" in k and "inspection" not in k),"sast_record_request","Solicitud coordinada de expediente y certificación oficial","expediente_sast",sast_record_request(a,result)),
        (lambda k,t:"inspect" in k or "revisi" in t,"sast_inspection","Solicitud condicionada de revisión e inspección","revision_sast",sast_inspection(a,result)),
        (lambda k,t:"follow" in k or "reiter" in k or "seguimiento" in t,"sast_followup","Reiteración, seguimiento y escalamiento","seguimiento_sast",sast_followup(a,result)),
        (lambda k,t:"package" in k or "paquete" in t or "summary" in k,"sast_package","Paquete consolidado, semáforo y control de cierre","paquete_sast",sast_package(a,result)),
    ]
    added=set(); predicates=[]
    for pred,kind,title,suffix,sections in mappings:
        predicates.append(pred); _upsert(specs,pred,kind=kind,title=title,suffix=suffix,sections=sections,metadata=metadata); added.add(kind)
    return _retain_only(specs,predicates,added)


def _tr2(specs,a,result,metadata):
    mappings=[
        (lambda k,t:"diagn" in k or "diagn" in t,"traffic_diagnostic","Diagnóstico jurídico del procedimiento contravencional","diagnostico_fotodeteccion",traffic_diagnostic(a,result)),
        (lambda k,t:"record" in k or "exped" in t or ("request" in k and "hearing" not in k),"traffic_record_request","Solicitud integral de expediente y estado procesal","expediente_fotodeteccion",traffic_record_request(a,result)),
        (lambda k,t:"notifi" in k or "notifi" in t or "claim" in k,"traffic_notification_claim","Reclamación por indebida notificación y restablecimiento","reclamacion_notificacion",traffic_notification_claim(a,result)),
        (lambda k,t:"hearing" in k or "audien" in t,"traffic_hearing_request","Comparecencia, audiencia y solicitud de pruebas","audiencia_pruebas",traffic_hearing(a,result)),
        (lambda k,t:"revoc" in k or "revoc" in t,"traffic_revocation_request","Solicitud condicionada de revocación directa","revocacion_directa",traffic_revocation(a,result)),
        (lambda k,t:"registry" in k or "simit" in t or "runt" in t or "correcci" in t,"traffic_registry_correction","Solicitud de corrección y sincronización de registros","correccion_registros",traffic_registry(a,result)),
        (lambda k,t:"evidence" in k or "matrix" in k or "matriz" in t,"traffic_evidence_matrix","Matrices de control probatorio y términos","matrices_transito",traffic_evidence(a,result)),
        (lambda k,t:"guide" in k or "filing" in k or "guia" in t or "seguimiento" in t,"traffic_filing_guide","Guía jurídica de radicación, escalamiento y cierre","guia_transito",traffic_guide(a,result)),
    ]
    added=set(); predicates=[]
    for pred,kind,title,suffix,sections in mappings:
        predicates.append(pred); _upsert(specs,pred,kind=kind,title=title,suffix=suffix,sections=sections,metadata=metadata); added.add(kind)
    return _retain_only(specs,predicates,added)


def document_specs_m33_wave3(case_id, code, answers, result, product, generated_at, question_rows):
    specs=document_specs_m33_runtime(case_id,code,answers,result,product,generated_at,question_rows)
    if code not in WAVE3_CODES:
        return specs
    metadata=_meta(specs)
    if code=="CO-SA-001": return _health(specs,answers,result,metadata)
    if code=="CO-TR-001": return _tr1(specs,answers,result,metadata)
    return _tr2(specs,answers,result,metadata)
