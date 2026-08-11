from __future__ import annotations

"""Finalización jurídica y de presentación de CO-TR-001 — verificación SAST.

La capa separa autorización, puesta en operación, señalización, metrología,
inspección institucional y expediente individual. Las salidas son borradores
cliente; los controles de gobierno permanecen fuera del instrumento visible.
"""

from copy import deepcopy
from datetime import date
from typing import Any

SAST_KINDS = {
    "sast_report",
    "sast_traceability",
    "sast_registration",
    "sast_record_request",
    "sast_inspection",
    "sast_followup",
    "sast_package",
}

CLIENT_TITLES = {
    "sast_report": "Informe jurídico-operativo de verificación de un sistema SAST",
    "sast_traceability": "Matriz de trazabilidad jurídica, técnica y temporal del SAST",
    "sast_registration": "Autorización de gestión y consulta del expediente SAST",
    "sast_record_request": "Petición de expediente técnico, autorización y soportes de operación SAST",
    "sast_inspection": "Solicitud condicionada de verificación e inspección sobre un SAST",
    "sast_followup": "Reiteración y seguimiento de solicitud de información SAST",
    "sast_package": "Resumen consolidado de verificación SAST y siguientes actuaciones",
}

CLIENT_SUBTITLES = {
    "sast_report": "Autorización · operación · señalización · metrología · control institucional · caso individual",
    "sast_traceability": "Correspondencia entre punto, dispositivo, acto, período, evidencia y fuente oficial",
    "sast_registration": "Alcance de la gestión documental · privacidad · límites de representación",
    "sast_record_request": "Derecho de petición · documentos públicos · temporalidad técnica · trazabilidad oficial",
    "sast_inspection": "Inconsistencia documentada · verificación institucional · sin prejuzgamiento",
    "sast_followup": "Faltantes concretos · términos · traslado · reserva · escalamiento",
    "sast_package": "Semáforo probatorio · vacíos de evidencia · ruta de actuación",
}


def _value(value: Any, fallback: str = "Por verificar") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _date_es(value: Any) -> str:
    parsed = _parse_date(value)
    if parsed is None:
        return _value(value, "Fecha por verificar")
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def _requester(a: dict) -> str:
    return _value(a.get("requester_name") or a.get("name"), "Persona solicitante por identificar")


def _authority(a: dict) -> str:
    return _value(a.get("traffic_authority") or a.get("authority"), "Autoridad de tránsito por identificar")


def _territory(a: dict) -> str:
    return _value(a.get("municipality") or a.get("territory"), "Municipio o distrito por verificar")


def _device(a: dict) -> str:
    return _value(a.get("sast_id") or a.get("device_id"), "Dispositivo o punto por individualizar")


def _location(a: dict) -> str:
    return _value(a.get("location_detail") or a.get("event_location") or a.get("location"), "Ubicación por verificar")


def _reference_date(a: dict) -> date | None:
    return _parse_date(
        a.get("observation_date")
        or a.get("event_date")
        or a.get("reference_date")
        or a.get("detection_date")
    )


def _reference_date_label(a: dict) -> str:
    raw = (
        a.get("observation_date")
        or a.get("event_date")
        or a.get("reference_date")
        or a.get("detection_date")
    )
    return _date_es(raw)


def _performance_regime(a: dict) -> tuple[str, str]:
    """Clasifica temporalmente el antiguo Concepto de Desempeño del INM."""
    d = _reference_date(a)
    start = date(2018, 3, 22)
    end = date(2020, 8, 19)
    if d is None:
        return (
            "Temporalidad por verificar",
            "No puede exigirse ni descartarse el antiguo Concepto de Desempeño sin fijar primero la fecha relevante del hecho y la tecnología concreta.",
        )
    if start <= d <= end:
        return (
            "Período histórico 22/03/2018–19/08/2020",
            "Para este intervalo debe verificarse si el requisito histórico del Concepto de Desempeño resultaba aplicable a la tecnología. Ese concepto era metrológico y no equivalía a autorización de funcionamiento ni a certificación integral del SAST.",
        )
    return (
        "Fuera del intervalo histórico del Concepto de Desempeño",
        "El Concepto de Desempeño del INM no es un requisito actual ni debe exigirse retroactivamente fuera del intervalo 22/03/2018–19/08/2020. Ello no elimina las obligaciones de calibración y trazabilidad metrológica que correspondan.",
    )


def _signage_regime(a: dict) -> str:
    d = _reference_date(a)
    if d is None:
        return "Determinar el manual y las reglas de señalización vigentes en la fecha relevante; una fotografía actual no acredita el estado histórico."
    if d >= date(2024, 10, 2):
        return (
            "Aplicar la Ley 1843 de 2017, la regulación SAST específica y el Manual de Señalización Vial adoptado por la Resolución 20243040045005 de 2024, "
            "considerando las reglas transitorias para elementos y diseños preexistentes."
        )
    return (
        "Aplicar la regulación SAST y el manual de señalización vigentes para la fecha histórica, sin proyectar automáticamente sobre el pasado el Manual 2024. "
        "La evidencia debe corresponder al punto y al período analizados."
    )


def _authorization_route(a: dict) -> tuple[str, str]:
    text = " ".join(
        str(x or "")
        for x in (
            a.get("device_type"),
            a.get("location_detail"),
            a.get("event_location"),
            a.get("conduct_code"),
            a.get("ansv_authorization"),
            a.get("authorization_status"),
        )
    ).casefold()
    declared = str(a.get("ansv_authorization") or a.get("authorization_status") or "").casefold()
    if "control en vía" in text or "control en via" in text:
        return (
            "Control en vía apoyado en dispositivo electrónico — clasificación por verificar",
            "La regulación vigente contempla una ruta distinta del SAST automático: el control en vía apoyado en dispositivo electrónico puede estar exceptuado de autorización ANSV, pero deben acreditarse sus elementos normativos y fácticos, incluido el control directo por agente cuando corresponda.",
        )
    if (
        "carril exclusivo" in text
        or "carril preferencial" in text
        or "infraestructura de transporte público" in text
        or "infraestructura del sistema de transporte" in text
    ):
        return (
            "Posible excepción legal en infraestructura de transporte público",
            "El parágrafo 2 del artículo 2 de la Ley 1843 permite determinados sistemas fijos o móviles en infraestructura de sistemas de transporte público sin autorización nacional, principalmente para control de carriles exclusivos o preferenciales; el supuesto concreto y la señalización deben probarse.",
        )
    if "excepción legal" in declared or "excepcion legal" in declared:
        return (
            "Excepción declarada, pendiente de individualización",
            "No basta seleccionar 'excepción': debe identificarse la norma, modalidad tecnológica y hechos que realmente ubican el punto dentro del supuesto excepcional.",
        )
    return (
        "Régimen general SAST",
        "Como regla general, la instalación del SAST requiere autorización de la ANSV y la autorización tiene una duración de cinco años desde su otorgamiento; deben verificarse acto, punto, modalidad, coordenadas, fecha y vigencia.",
    )


def _speed_measurement(a: dict) -> bool:
    text = " ".join(str(x or "") for x in (a.get("device_type"), a.get("conduct_code"), a.get("request_mode"))).casefold()
    return "velocidad" in text or "radar" in text


def _operation_rule(a: dict) -> str:
    metrology = (
        "Cuando el equipo mide velocidad, debe acreditarse la calibración y trazabilidad metrológica aplicables al equipo y período."
        if _speed_measurement(a)
        else
        "La exigencia metrológica debe conectarse con la magnitud efectivamente medida; no se presume calibración de velocidad para una conducta que no dependa de medición."
    )
    return (
        "La autorización de instalación no equivale por sí sola a habilitación material de operación en cualquier fecha. "
        "Debe verificarse la viabilidad para el uso de la infraestructura vial, la evidencia de señalización, "
        f"{metrology} Además, debe verificarse la fecha real de inicio de operación registrada en el sistema de información de la ANSV cuando el régimen aplicable la exige."
    )


def _result_category(a: dict, result: dict) -> tuple[str, str]:
    auth = str(a.get("ansv_authorization") or a.get("authorization_status") or "").strip().casefold()
    exact = str(a.get("exact_point_match") or "").strip().casefold()
    evidence = str(a.get("evidence_available") or "").strip().casefold()
    if any(x in auth for x in ("no verificada", "no sé", "no se", "pendiente")) or exact in {"no", "no sé", "no se", "no fue posible consultar"}:
        return (
            "No concluyente",
            "Falta evidencia suficiente para conectar de forma inequívoca el punto real con el régimen de autorización, excepción y operación aplicable.",
        )
    if "no" == auth:
        return (
            "Inconsistencia por verificar",
            "La ausencia declarada de autorización exige confirmar primero la identidad exacta del punto, la fuente oficial, la fecha y la existencia de una excepción; no equivale automáticamente a una decisión jurídica definitiva.",
        )
    if evidence in {"sin soportes verificables", "solo consulta o captura"}:
        return (
            "No concluyente",
            "La evidencia disponible no permite cerrar la verificación.",
        )
    return (
        "Verificado con observaciones",
        "Existen datos útiles, pero el cierre exige cotejo de punto, período, operación y soportes oficiales.",
    )


def _identity_table(a: dict) -> list[list[str]]:
    return [
        ["Elemento", "Dato del expediente"],
        ["Solicitante", _requester(a)],
        ["Identificación", _value(a.get("requester_id"))],
        ["Calidad en que actúa", _value(a.get("acting_capacity"))],
        ["Municipio / distrito", _territory(a)],
        ["Autoridad de tránsito", _authority(a)],
        ["Punto o dispositivo", _device(a)],
        ["Ubicación", _location(a)],
        ["Tipo / modalidad declarada", _value(a.get("device_type"))],
        ["Fecha relevante", _reference_date_label(a)],
        ["Comparendo relacionado", _value(a.get("comparendo_number"), "No incorporado a este chequeo")],
    ]


def _technical_status_table(a: dict) -> list[list[str]]:
    perf_label, _ = _performance_regime(a)
    return [
        ["Componente", "Dato informado", "Lectura jurídica"],
        ["Coincidencia punto exacto", _value(a.get("exact_point_match")), "Debe cotejarse con ubicación, coordenadas, sentido y dispositivo"],
        ["Autorización ANSV / excepción", _value(a.get("ansv_authorization") or a.get("authorization_status")), "No confundir autorización con operación"],
        ["Acto de autorización", _value(a.get("authorization_number")), "Verificar acto íntegro, anexos y punto"],
        ["Expedición", _date_es(a.get("authorization_issue_date")), "La autorización general tiene vigencia temporal"],
        ["Vencimiento informado", _date_es(a.get("authorization_expiry_date")), "Cotejar con acto y eventuales modificaciones"],
        ["Señalización", _value(a.get("signage_verified") or a.get("signage_status")), "La evidencia debe corresponder a la fecha"],
        ["Metrología", _value(a.get("calibration_traceability") or a.get("metrology_status")), "Condicionada a la medición y al equipo exacto"],
        ["Certificado / fecha", _date_es(a.get("calibration_date")), "Verificar laboratorio, alcance, serial y vigencia"],
        ["Concepto de Desempeño", _value(a.get("performance_concept")), perf_label],
        ["Actuación de control 2026", _value(a.get("official_act_status") or a.get("inspection_status")), "Investigación no equivale a decisión firme"],
    ]


def _signature(a: dict, label: str = "PERSONA PETICIONARIA") -> dict:
    return {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [{
            "label": label,
            "name": _requester(a),
            "id": _value(a.get("requester_id"), ""),
            "role": _value(a.get("acting_capacity"), "Calidad por acreditar"),
        }],
    }


def _legal_basis() -> list[str]:
    return [
        "Ley 1843 de 2017, especialmente artículos 2, 3, 10, 13 y 14: criterios de instalación y operación, autorización, control, señalización y aspectos técnicos/metrológicos de los SAST.",
        "Decreto Ley 2106 de 2019, artículo 109: competencia de la Agencia Nacional de Seguridad Vial para la autorización y vigencia de cinco años del acto de autorización.",
        "Ley 2294 de 2023, artículo 181: excepción específica para determinados sistemas en infraestructura de sistemas de transporte público, sin perjuicio de señalización y demás condiciones aplicables.",
        "Resolución Única Compilatoria de Tránsito 20223040045295 de 2022, con sus modificaciones: reglas vigentes para criterios de instalación, operación, excepciones y registro de los SAST.",
        "Resolución 20203040011245 de 2020: regulación técnica SAST compilada en la Resolución Única de Tránsito; debe leerse con sus modificaciones posteriores.",
        "Resolución 20243040045005 de 2024: Manual de Señalización Vial de Colombia y régimen de transición.",
        "Ley 1755 de 2015: derecho de petición, términos diferenciados para información/documentos y demás solicitudes, y traslado por falta de competencia.",
        "Ley 1712 de 2014: máxima publicidad, motivación de reservas y entrega de versión pública cuando solo una parte del documento esté protegida.",
        "Aclaración oficial del Instituto Nacional de Metrología de 2026: el antiguo Concepto de Desempeño fue un requisito técnico-metrológico entre el 22 de marzo de 2018 y el 19 de agosto de 2020 y nunca constituyó autorización integral de funcionamiento.",
    ]


def _report(a: dict, result: dict) -> list[dict]:
    route, route_detail = _authorization_route(a)
    perf_label, perf_detail = _performance_regime(a)
    category, category_detail = _result_category(a, result)
    official = _value(a.get("official_act_number"), "No individualizada")
    official_status = _value(a.get("official_act_status"), "Estado no confirmado")
    return [
        {
            "heading": "OBJETO Y ALCANCE",
            "paragraphs": [
                "Este informe verifica documentalmente un punto o dispositivo tecnológico frente a su identidad, régimen de autorización o excepción, condiciones de puesta en operación, señalización, metrología y actuaciones institucionales conocidas. No declara por sí solo que una cámara sea legal o ilegal ni decide la validez de un comparendo individual.",
                "La verificación se realiza por período: una condición acreditada hoy no demuestra automáticamente la situación histórica y una ausencia en una consulta pública no prueba por sí sola inexistencia, falta de autorización o irregularidad.",
            ],
            "_suppress_default_control": True,
        },
        {"heading": "I. IDENTIFICACIÓN DEL OBJETO VERIFICADO", "table": _identity_table(a)},
        {"heading": "II. ESTADO DOCUMENTAL Y TÉCNICO", "table": _technical_status_table(a)},
        {
            "heading": "III. CLASIFICACIÓN DEL RÉGIMEN DE AUTORIZACIÓN",
            "paragraphs": [f"Clasificación preliminar: {route}. {route_detail}"],
        },
        {
            "heading": "IV. AUTORIZACIÓN Y PUESTA EN OPERACIÓN SON CONTROLES DISTINTOS",
            "paragraphs": [_operation_rule(a)],
            "numbered": [
                "Individualizar el acto de autorización, su titular, punto, coordenadas, modalidad y vigencia o documentar la excepción realmente aplicable.",
                "Verificar que el punto real coincida con el autorizado o exceptuado y con el período examinado.",
                "Comprobar las condiciones de operación exigibles para la fecha: viabilidad de infraestructura, señalización, configuración técnica y, cuando corresponda, calibración y trazabilidad.",
                "Verificar el inicio real de operación y las suspensiones, reemplazos, modificaciones o mantenimientos relevantes.",
            ],
        },
        {
            "heading": "V. SEÑALIZACIÓN Y TEMPORALIDAD",
            "paragraphs": [_signage_regime(a)],
        },
        {
            "heading": "VI. METROLOGÍA Y CONCEPTO DE DESEMPEÑO",
            "paragraphs": [
                f"Régimen temporal identificado: {perf_label}. {perf_detail}",
                "El análisis metrológico debe relacionar marca, modelo, serial, certificado, laboratorio, alcance, fecha y período de uso. No basta una certificación genérica que no permita vincular el documento con el equipo concreto.",
            ],
        },
        {
            "heading": "VII. ACTUACIONES INSTITUCIONALES E INVESTIGACIONES",
            "paragraphs": [
                f"Acto o radicado oficial informado: {official}. Estado informado: {official_status}.",
                "Los comunicados e investigaciones institucionales de 2026 constituyen antecedentes de control, no decisiones firmes aplicables automáticamente a todo punto o comparendo. Deben individualizarse organismo, punto, tecnología, período, acto, estado, firmeza y alcance de cualquier orden.",
            ],
        },
        {
            "heading": "VIII. RESULTADO CONTROLADO",
            "paragraphs": [
                f"Resultado del chequeo: {category}. {category_detail}",
                "Las categorías admisibles son: verificado favorablemente, verificado con observaciones, no concluyente, inconsistencia documentada, escalamiento obligatorio o fuera del alcance. El chequeo no debe producir automáticamente expresiones como «fotomulta ilegal», «cámara ilegal», «comparendo anulado», «prescribió» o «debe devolver el dinero».",
            ],
        },
        {"heading": "IX. FUNDAMENTO JURÍDICO DE REFERENCIA", "numbered": _legal_basis()},
    ]


def _traceability(a: dict, result: dict) -> list[dict]:
    route, _ = _authorization_route(a)
    perf_label, _ = _performance_regime(a)
    return [
        {
            "heading": "FINALIDAD DE LA MATRIZ",
            "paragraphs": [
                "La matriz separa cada afirmación del documento que debería acreditarla. Su objetivo es impedir que una coincidencia parcial, captura de pantalla o noticia se transforme en una conclusión jurídica que la evidencia no soporta.",
            ],
            "_suppress_default_control": True,
        },
        {
            "heading": "I. MATRIZ DE TRAZABILIDAD",
            "table": [
                ["ID", "Capa", "Documento o dato esperado", "Estado / criterio"],
                ["TR-EV-001", "Identidad", "Código/serial, tecnología, ubicación, coordenadas, sentido", _value(a.get("exact_point_match"), "Por cotejar")],
                ["TR-EV-002", "Competencia", "Autoridad y jurisdicción territorial", _authority(a)],
                ["TR-EV-003", "Régimen", "Clasificación general o excepción", route],
                ["TR-EV-004", "Autorización", "Acto ANSV, anexos y modificaciones", _value(a.get("authorization_number"), "Por obtener")],
                ["TR-EV-005", "Vigencia", "Fecha de otorgamiento, expiración y actos posteriores", f"{_date_es(a.get('authorization_issue_date'))} / {_date_es(a.get('authorization_expiry_date'))}"],
                ["TR-EV-006", "Operación", "Viabilidad de infraestructura y fecha real de inicio registrada", "Por verificar"],
                ["TR-EV-007", "Instalación", "Criterio técnico que justificó el punto y documentos asociados", "Por verificar"],
                ["TR-EV-008", "Señalización", "Plan, ubicación, instalación, mantenimiento y evidencia del período", _value(a.get("signage_verified") or a.get("signage_status"))],
                ["TR-EV-009", "Metrología", "Certificado, laboratorio, alcance, serial y vigencia", _value(a.get("calibration_traceability") or a.get("metrology_status"))],
                ["TR-EV-010", "Régimen histórico", "Concepto de Desempeño, solo si temporalmente aplicable", perf_label],
                ["TR-EV-011", "Operación histórica", "Inicio, suspensión, mantenimiento, reemplazo y deshabilitación", "Por verificar"],
                ["TR-EV-012", "Control", "Visitas, autos, cargos, decisiones, recursos y firmeza", _value(a.get("official_act_status") or a.get("inspection_status"))],
                ["TR-EV-013", "Caso individual", "Comparendo y expediente completo, si se pretende analizarlo", _value(a.get("individual_case_status"), "Fuera del cierre de este chequeo")],
            ],
        },
        {
            "heading": "II. REGLAS DE CORRESPONDENCIA PROBATORIA",
            "numbered": [
                "Toda fuente debe registrar autoridad, fecha de consulta, enlace o radicado, versión, período cubierto y archivo preservado.",
                "Una consulta sin resultados se registra como «no localizado en la fuente consultada», no como «no autorizado».",
                "Una autorización posterior no prueba autorización histórica; una autorización vencida no prueba por sí sola operación posterior irregular sin reconstruir actos y excepciones.",
                "Fotografías actuales no prueban señalización histórica. La evidencia debe corresponder al punto, sentido vial y período.",
                "El certificado metrológico debe coincidir con equipo, magnitud, serial y período; un documento de otro equipo no subsana el vacío.",
                "Un comunicado de investigación no reemplaza el auto, expediente, decisión ni constancia de firmeza.",
                "El chequeo del sistema no sustituye el procedimiento de defensa de un comparendo individual.",
            ],
        },
        {
            "heading": "III. REGLA DE CIERRE",
            "paragraphs": [
                "La matriz solo puede cerrarse cuando cada conclusión relevante tenga un soporte trazable o se identifique expresamente el vacío. Los vacíos no deben rellenarse mediante inferencias favorables ni adversas.",
            ],
        },
    ]


def _registration(a: dict, result: dict) -> list[dict]:
    alerts = _value(a.get("consent_alerts"), "No informado")
    return [
        {
            "heading": "OBJETO DE LA AUTORIZACIÓN",
            "paragraphs": [
                "La persona usuaria autoriza la creación y gestión de un expediente documental de verificación SAST en LegalAIZ.it. La autorización permite organizar los datos aportados, consultar fuentes públicas, preparar borradores y mantener trazabilidad; no constituye poder, mandato judicial o administrativo ni certifica la legalidad del sistema.",
            ],
            "_suppress_default_control": True,
        },
        {
            "heading": "I. DATOS DEL EXPEDIENTE",
            "table": [
                ["Campo", "Información"],
                ["Usuario", _requester(a)],
                ["Identificación", _value(a.get("requester_id"))],
                ["Calidad", _value(a.get("acting_capacity"))],
                ["Punto / sistema", _device(a)],
                ["Municipio", _territory(a)],
                ["Alertas y seguimiento", alerts],
            ],
        },
        {
            "heading": "II. GESTIONES AUTORIZADAS",
            "numbered": [
                "Organizar y conservar las respuestas, documentos y consultas incorporadas al expediente.",
                "Consultar fuentes públicas oficiales sobre autorización, regulación técnica, actuaciones de control y documentos relacionados con el punto.",
                "Generar borradores para revisión de la persona usuaria y, cuando corresponda, del especialista jurídico.",
                "Registrar versiones, fechas, fuentes, radicados y resultados para permitir auditoría y comparación.",
                "Enviar alertas de seguimiento únicamente cuando exista consentimiento y dentro de los canales habilitados.",
            ],
        },
        {
            "heading": "III. LÍMITES DE LA GESTIÓN",
            "numbered": [
                "LegalAIZ.it no firma en nombre del usuario, no acepta infracciones, no identifica conductores por inferencia y no desiste de actuaciones.",
                "La inscripción no autoriza presentar recursos, conciliar, comparecer, sustituir defensa profesional ni ejecutar actos reservados a un apoderado.",
                "Una consulta automática no reemplaza la verificación oficial del punto y fecha, ni una decisión administrativa.",
                "Los datos de terceros o documentos de un expediente individual solo deben tratarse cuando sean necesarios, legítimos y proporcionales al propósito del caso.",
            ],
        },
        {
            "heading": "IV. TRAZABILIDAD Y RETIRO",
            "paragraphs": [
                "Las consultas y documentos relevantes deberán conservar fecha, origen y versión. El usuario puede solicitar actualización de datos o retiro de alertas, sin que ello implique borrar registros que deban conservarse por trazabilidad, seguridad o deber legal.",
            ],
        },
        _signature(a, "PERSONA USUARIA"),
    ]


def _record_request(a: dict, result: dict) -> list[dict]:
    perf_label, _ = _performance_regime(a)
    return [
        {
            "heading": "DESTINATARIO, ASUNTO Y ALCANCE",
            "paragraphs": [
                f"Señores {_authority(a)}. Asunto: solicitud de información, documentos y certificaciones para verificar el sistema {_device(a)}, ubicado o reportado en {_location(a)}, con referencia temporal {_reference_date_label(a)}.",
                "La petición busca reconstruir documentalmente autorización, excepción, puesta en operación, señalización, metrología y actuaciones de control. No afirma anticipadamente que el sistema sea irregular ni solicita que la entidad emita una declaración abstracta de legalidad o ilegalidad.",
            ],
            "_suppress_default_control": True,
        },
        {
            "heading": "I. IDENTIFICACIÓN Y COMPETENCIA",
            "numbered": [
                "Confirmar si el punto o dispositivo identificado obra en sus registros y precisar código, marca, modelo, serial, tecnología, carácter fijo/móvil, propietario u operador, ubicación, coordenadas, sentido vial y conductas detectadas.",
                "Identificar la autoridad responsable de instalación y operación, su competencia territorial y cualquier contratista u operador técnico relacionado.",
                "Si algún punto corresponde a otra autoridad, efectuar el traslado por competencia e informar el oficio remisorio, sin obligar al peticionario a reiniciar la solicitud.",
            ],
        },
        {
            "heading": "II. RÉGIMEN DE AUTORIZACIÓN O EXCEPCIÓN",
            "numbered": [
                "Entregar copia íntegra del acto de autorización ANSV aplicable, anexos, estudios, modificaciones, renovaciones, suspensiones y constancias que permitan determinar su vigencia.",
                "Explicar la correspondencia entre el punto físico y el autorizado: coordenadas, sentido, modalidad tecnológica y conductas cubiertas.",
                "Si se sostiene que el sistema no requería autorización ANSV, identificar la excepción normativa exacta y aportar los hechos y documentos que acrediten que el punto encaja en ese supuesto.",
                "Informar la fecha de otorgamiento y el vencimiento del acto de autorización, teniendo en cuenta su duración legal y los actos posteriores que hayan podido modificar su alcance.",
            ],
        },
        {
            "heading": "III. INSTALACIÓN Y PUESTA EN OPERACIÓN",
            "numbered": [
                "Entregar los documentos con los que se acreditó el o los criterios técnicos que justificaron la instalación para la fecha aplicable.",
                "Entregar la viabilidad para el uso de infraestructura vial y los documentos que soporten la instalación en el sitio concreto.",
                "Certificar la fecha real de inicio de operación registrada en el sistema de información de la ANSV y cualquier suspensión, reanudación, reemplazo o deshabilitación.",
                "Identificar los períodos en que el sistema produjo detecciones y cualquier cambio relevante de dispositivo o configuración.",
            ],
        },
        {
            "heading": "IV. SEÑALIZACIÓN",
            "numbered": [
                "Entregar el plan, fichas, ubicación y evidencia de instalación de la señalización preventiva correspondiente al punto y período consultados.",
                "Aportar soportes de mantenimiento, reposición o cambios de señalización y precisar el manual o regla técnica aplicada en cada período relevante.",
                "Cuando se pretenda usar fotografías como prueba, indicar fecha, ubicación, sentido vial y fuente, para evitar atribuir al pasado evidencia tomada en otro momento.",
            ],
        },
        {
            "heading": "V. METROLOGÍA Y SOPORTE TÉCNICO",
            "numbered": [
                "Si la detección depende de una medición de velocidad u otra magnitud, entregar certificado de calibración o soporte metrológico aplicable, con laboratorio, alcance, marca/modelo/serial, fecha y vigencia.",
                "Entregar hoja de vida, mantenimientos, verificaciones, fallas, reemplazos y registros técnicos del equipo correspondientes al período consultado.",
                f"Respecto del antiguo Concepto de Desempeño, informar y aportar soporte únicamente si resulta temporal y tecnológicamente pertinente. Clasificación del caso: {perf_label}.",
                "Distinguir expresamente el Concepto de Desempeño histórico de la autorización de instalación y de los certificados de calibración o trazabilidad.",
            ],
        },
        {
            "heading": "VI. INSPECCIÓN, VIGILANCIA Y CONTROL",
            "numbered": [
                "Informar visitas, requerimientos, investigaciones, aperturas, formulaciones de cargos, decisiones, recursos, órdenes de suspensión o medidas relacionadas con el punto u organismo para el período consultado.",
                "Entregar copia de los actos individualizados e indicar su estado actual y firmeza.",
                "Si existe una decisión firme que identifique un período de operación no cubierto o incumplimientos concretos, precisar exactamente el punto, tecnología, fechas y medidas adoptadas.",
                "No sustituir actos o decisiones por enlaces genéricos a noticias o comunicados; si se remite a un portal, identificar el documento exacto y garantizar su acceso.",
            ],
        },
        {
            "heading": "VII. TÉRMINOS, TRASLADO Y ACCESO A INFORMACIÓN",
            "numbered": [
                "Las peticiones de información y documentos tienen el término especial de diez (10) días previsto en el artículo 14 de la Ley 1755 de 2015; las demás peticiones se rigen, en principio, por el término general de quince (15) días, salvo norma especial.",
                "Si la autoridad carece de competencia sobre alguno de los puntos, debe aplicar el artículo 21 de la Ley 1755 de 2015: informar y trasladar dentro de los cinco (5) días siguientes a la recepción escrita; el término corre desde la recepción por la autoridad competente.",
                "Si algún contenido está clasificado o reservado, identificar la norma constitucional o legal específica, motivar su aplicación y entregar una versión pública que preserve únicamente la parte indispensable de la reserva.",
                "La reserva sobre parte del contenido no elimina el deber de informar sobre la existencia del documento cuando la ley no autoriza ocultarla.",
            ],
        },
        {
            "heading": "VIII. FORMA DE RESPUESTA",
            "paragraphs": [
                "Se solicita respuesta numerada siguiendo el orden anterior, entrega de documentos en formato legible y copia del oficio de traslado cuando proceda. Si un documento no existe, no fue producido o no está bajo custodia de la entidad, debe indicarse de forma expresa, evitando reemplazar el dato por una remisión genérica.",
            ],
        },
        _signature(a),
    ]


def _inspection(a: dict, result: dict) -> list[dict]:
    route, _ = _authorization_route(a)
    inconsistency = _value(
        a.get("documented_inconsistency") or a.get("facts_detail"),
        "No se ha individualizado una inconsistencia documental suficiente; no debe radicarse esta pieza hasta completar el soporte.",
    )
    return [
        {
            "heading": "REGLA DE ACTIVACIÓN Y NO PREJUZGAMIENTO",
            "paragraphs": [
                "Esta solicitud solo debe radicarse cuando exista una discrepancia verificable entre fuentes, actos, respuestas o evidencia técnica. Una consulta sin resultados, una noticia o una afirmación de parte no bastan para sostener que el SAST carece de autorización o que operó irregularmente.",
                "Se solicita a la autoridad de inspección competente verificar hechos concretos, sin pedirle que adopte anticipadamente una sanción ni trasladar automáticamente conclusiones institucionales a comparendos individuales.",
            ],
            "_suppress_default_control": True,
        },
        {"heading": "I. IDENTIFICACIÓN", "table": _identity_table(a)},
        {
            "heading": "II. INCONSISTENCIA DOCUMENTADA",
            "paragraphs": [inconsistency],
            "numbered": [
                "Relacionar cada inconsistencia con la fuente, fecha de consulta, documento y apartado específico que la soporta.",
                "Descartar previamente errores de identificación de punto, coordenadas, sentido, serial, modalidad tecnológica y período.",
                f"Verificar la clasificación del régimen aplicable antes de sostener ausencia de autorización. Clasificación preliminar: {route}.",
            ],
        },
        {
            "heading": "III. SOLICITUDES DE VERIFICACIÓN",
            "numbered": [
                "Cotejar el dispositivo y punto real con el acto de autorización o con la excepción que se invoque.",
                "Determinar los períodos de autorización y operación documentados, incluidas suspensiones y modificaciones.",
                "Verificar el cumplimiento de las condiciones de puesta en operación exigibles para el período, incluida señalización y, cuando corresponda, metrología.",
                "Examinar las actuaciones institucionales previas e indicar cuáles se encuentran en trámite y cuáles son decisiones firmes.",
                "Si existe mérito, adoptar dentro de las competencias legales las actuaciones de inspección, vigilancia o control pertinentes e informar su resultado.",
                "Precisar el alcance de cualquier hallazgo respecto del sistema, sin asumir que determina automáticamente la situación jurídica de cada actuación contravencional individual.",
            ],
        },
        {
            "heading": "IV. CONTEXTO DE ACTUACIONES 2026",
            "paragraphs": [
                f"Acto o radicado informado: {_value(a.get('official_act_number'), 'No individualizado')}. Estado informado: {_value(a.get('official_act_status'), 'No confirmado')}.",
                "Los comunicados oficiales de 2026 sobre investigaciones SAST son antecedentes relevantes únicamente cuando se demuestra correspondencia con la autoridad, punto, tecnología y período. Una apertura o formulación de cargos no equivale a decisión sancionatoria firme.",
            ],
        },
        {
            "heading": "V. LÍMITE FRENTE AL CASO INDIVIDUAL",
            "paragraphs": [
                "Si existe comparendo, sanción, pago, cobro o embargo, su defensa exige reconstruir el expediente individual, las notificaciones, la imputación y los términos aplicables. Esta solicitud de inspección no suspende por sí sola actuaciones ni términos del caso individual.",
            ],
        },
        _signature(a, "PERSONA SOLICITANTE"),
    ]


def _followup(a: dict, result: dict) -> list[dict]:
    return [
        {
            "heading": "OBJETO DE LA REITERACIÓN",
            "paragraphs": [
                "La reiteración se utiliza para identificar faltantes concretos de una solicitud ya recibida. No debe afirmar silencio, vencimiento o negativa sin verificar previamente el acuse, la fecha de recepción, los traslados por competencia, la respuesta completa y cualquier ampliación del término jurídicamente comunicada.",
            ],
            "_suppress_default_control": True,
        },
        {
            "heading": "I. CONTROL DE RADICACIÓN",
            "table": [
                ["Elemento", "Dato"],
                ["Radicado previo", _value(a.get("prior_filing_radicado") or a.get("request_radicado"), "Por verificar")],
                ["Fecha de recepción", _date_es(a.get("prior_filing_date") or a.get("request_date"))],
                ["Autoridad receptora", _authority(a)],
                ["Traslado por competencia", _value(a.get("transfer_status"), "Por verificar")],
                ["Respuesta recibida", _value(a.get("prior_response"), "Por verificar")],
            ],
        },
        {
            "heading": "II. TÉRMINO SEGÚN EL CONTENIDO",
            "numbered": [
                "Información y documentos: término especial de diez (10) días desde la recepción por la autoridad competente.",
                "Otras solicitudes o certificaciones que no tengan término especial: en principio quince (15) días.",
                "Si la petición fue enviada a autoridad incompetente, verificar el traslado dentro de cinco (5) días y recalcular desde la recepción por la competente.",
                "Si la autoridad informó imposibilidad de responder dentro del término, verificar que lo hubiera comunicado antes del vencimiento, con motivos y una fecha razonable dentro del límite legal.",
            ],
        },
        {
            "heading": "III. FALTANTES A EXIGIR",
            "numbered": [
                "Identificación inequívoca del punto, dispositivo y período.",
                "Acto de autorización, modificaciones y vigencia o fundamento documentado de la excepción.",
                "Viabilidad de infraestructura, fecha real de inicio de operación y períodos de funcionamiento.",
                "Evidencia histórica de señalización.",
                "Soportes metrológicos conectados con el equipo y período, cuando correspondan.",
                "Aplicación temporal correcta del antiguo Concepto de Desempeño, sin tratarlo como autorización integral.",
                "Actos de inspección o control y su estado de firmeza, sin sustituirlos por comunicados generales.",
            ],
        },
        {
            "heading": "IV. RESERVA, INEXISTENCIA Y VERSIÓN PÚBLICA",
            "numbered": [
                "Si se invoca reserva, exigir fundamento legal específico y motivación.",
                "Solicitar versión pública cuando solo una parte del documento esté protegida.",
                "Si el documento no existe o no está bajo custodia, solicitar que se informe expresamente y se identifique, si se conoce, la autoridad competente.",
            ],
        },
        {
            "heading": "V. RUTAS DE ESCALAMIENTO",
            "table": [
                ["Situación", "Ruta compatible"],
                ["Falta de respuesta/documentos", "Reiteración y control del derecho de petición"],
                ["Discrepancia técnica documentada", "Inspección/vigilancia por autoridad competente"],
                ["Comparendo o sanción individual", "Reconstrucción y defensa CO-TR-002"],
                ["Cobro coactivo o embargo", "Revisión profesional inmediata"],
                ["Pago y eventual devolución", "Análisis del acto habilitante y expediente individual"],
                ["Proceso judicial o término próximo", "Bloqueo de automatización ordinaria y revisión profesional"],
            ],
        },
        _signature(a, "PERSONA SOLICITANTE"),
    ]


def _package(a: dict, result: dict) -> list[dict]:
    route, route_detail = _authorization_route(a)
    perf_label, perf_detail = _performance_regime(a)
    category, category_detail = _result_category(a, result)
    return [
        {
            "heading": "ALCANCE DEL RESUMEN",
            "paragraphs": [
                "Este documento consolida el estado probatorio del chequeo SAST y las actuaciones pendientes. No es una decisión administrativa, no certifica la legalidad del dispositivo y no reemplaza la defensa de un comparendo individual.",
            ],
            "_suppress_default_control": True,
        },
        {"heading": "I. IDENTIFICACIÓN", "table": _identity_table(a)},
        {
            "heading": "II. SEMÁFORO DOCUMENTAL",
            "table": [
                ["Componente", "Estado informado", "Pendiente de cierre"],
                ["Identidad del punto", _value(a.get("exact_point_match"), "Por cotejar"), "Código, serial, coordenadas, sentido y fuente"],
                ["Régimen", route, "Confirmar hechos y excepción, si aplica"],
                ["Autorización", _value(a.get("ansv_authorization") or a.get("authorization_status")), "Acto, anexos, vigencia y correspondencia"],
                ["Operación", _value(a.get("operation_status"), "Por verificar"), "Viabilidad, inicio real y períodos"],
                ["Señalización", _value(a.get("signage_verified") or a.get("signage_status")), "Evidencia del período y manual aplicable"],
                ["Metrología", _value(a.get("calibration_traceability") or a.get("metrology_status")), "Equipo, certificado, laboratorio y período"],
                ["Concepto histórico", _value(a.get("performance_concept")), perf_label],
                ["Control institucional", _value(a.get("official_act_status") or a.get("inspection_status")), "Actos, estado y firmeza"],
                ["Caso individual", _value(a.get("individual_case_status"), "No incorporado"), "Analizar por separado si existe afectación concreta"],
            ],
        },
        {
            "heading": "III. REGLAS DE INTERPRETACIÓN",
            "numbered": [
                "«No localizado en una consulta» no significa «no autorizado».",
                "«Autorizado» no significa que todas las condiciones de operación hayan estado satisfechas en todo período.",
                "«Investigado» o «formulación de cargos» no significa responsabilidad administrativa firme.",
                "Una irregularidad del sistema no anula automáticamente cada comparendo; el expediente individual requiere análisis propio.",
                "La ausencia del antiguo Concepto de Desempeño solo es jurídicamente relevante dentro de su período histórico y no equivale por sí misma a ausencia de autorización.",
                "La señalización debe probarse con evidencia temporalmente correspondiente; una foto actual no resuelve el pasado.",
            ],
        },
        {
            "heading": "IV. CONCLUSIÓN CONTROLADA",
            "paragraphs": [
                f"Categoría: {category}. {category_detail}",
                f"Régimen de autorización: {route_detail}",
                f"Concepto de Desempeño: {perf_detail}",
            ],
        },
        {
            "heading": "V. SIGUIENTES ACTUACIONES",
            "numbered": [
                "Completar los vacíos de la matriz de trazabilidad mediante consulta y documentos oficiales.",
                "Radicar solicitud de expediente técnico cuando falten actos, soportes o datos de operación.",
                "Solicitar inspección solo si surge una inconsistencia documentada y suficientemente individualizada.",
                "Separar cualquier comparendo, sanción, pago o cobro y tramitarlo como expediente individual.",
                "Escalar inmediatamente a revisión profesional si existe término próximo, cobro coactivo, embargo, fraude de identidad o proceso judicial.",
            ],
        },
        {"heading": "VI. FUNDAMENTO JURÍDICO DE REFERENCIA", "numbered": _legal_basis()},
    ]


def _sections(kind: str, a: dict, result: dict) -> list[dict]:
    return {
        "sast_report": _report,
        "sast_traceability": _traceability,
        "sast_registration": _registration,
        "sast_record_request": _record_request,
        "sast_inspection": _inspection,
        "sast_followup": _followup,
        "sast_package": _package,
    }[kind](a, result)


def _kind(spec: dict) -> str | None:
    kind = str(spec.get("kind") or "")
    if kind in SAST_KINDS:
        return kind
    title = str(spec.get("title") or "").casefold()
    checks = (
        ("sast_traceability", ("trazabilidad",)),
        ("sast_registration", ("inscripción", "inscripcion")),
        ("sast_record_request", ("expediente", "certificación", "certificacion")),
        ("sast_inspection", ("inspección", "inspeccion", "revisión", "revision")),
        ("sast_followup", ("reiteración", "reiteracion", "seguimiento")),
        ("sast_package", ("paquete", "consolidado", "semáforo", "semaforo")),
        ("sast_report", ("informe", "sast")),
    )
    for candidate, tokens in checks:
        if any(token in title for token in tokens):
            return candidate
    return None


def finalize_sast_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Profundiza CO-TR-001 sin relajar compuertas ni liberar salidas."""
    finalized: list[dict] = []
    for spec in deepcopy(specs):
        kind = _kind(spec)
        if kind is None:
            finalized.append(spec)
            continue
        internal = deepcopy(spec.get("internal_review_sections") or [])
        internal.extend(
            deepcopy(section)
            for section in (spec.get("sections") or [])
            if isinstance(section, dict) and section.get("_type") == "control"
        )
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
