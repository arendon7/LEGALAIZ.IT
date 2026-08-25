from __future__ import annotations

"""Finalización jurídica y de presentación para CO-CD-001 en M33.0.

La capa opera después del compositor procedimental existente. No modifica cálculos,
reglas de selección ni compuertas de riesgo. Su objetivo es convertir las piezas de
hábeas data financiero en instrumentos coordinados, separar la ruta ordinaria de la
ruta de posible suplantación y evitar afirmaciones temporales incompatibles con la
vigencia normativa de 2026.
"""

from copy import deepcopy
from datetime import date
from typing import Any


LAW_2573_GENERAL_EFFECTIVE = date(2026, 11, 20)
HABEAS_KINDS = {
    "habeas_consultation",
    "habeas_claim",
    "habeas_reiteration",
    "identity_theft_protocol",
    "habeas_authority_escalation",
    "habeas_evidence_matrix",
    "habeas_deadline_calendar",
}


def _value(value: Any, fallback: str = "Por verificar") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _date(value: Any) -> str:
    parsed = _parse_date(value)
    if not parsed:
        return "Por verificar"
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def _subject(a: dict) -> str:
    return _value(a.get("data_subject_name"), "Titular de la información por identificar")


def _reference_date(a: dict, c: dict) -> date | None:
    return _parse_date(c.get("reference_date") or c.get("filing_date") or a.get("filing_date"))


def _regime_paragraph(a: dict, c: dict) -> str:
    ref = _reference_date(a, c)
    ref_text = _date(ref.isoformat()) if ref else "la fecha de uso"
    if ref and ref < LAW_2573_GENERAL_EFFECTIVE:
        return (
            f"Para {ref_text}, el régimen general de la Ley 2573 de 2026 todavía no ha entrado "
            "íntegramente en vigor: su artículo 13 difiere la vigencia general hasta el 20 de "
            "noviembre de 2026, sin perjuicio de las excepciones expresamente vigentes desde la "
            "promulgación. Por ello, esta pieza se apoya principalmente en la Ley 1266 de 2008, "
            "con las modificaciones vigentes introducidas por la Ley 2157 de 2021, y no anticipa "
            "procedimientos especiales futuros."
        )
    return (
        f"Para {ref_text}, la aplicación de la Ley 2573 de 2026 debe verificarse artículo por "
        "artículo junto con la Ley 1266 de 2008 y sus modificaciones. La fecha de vigencia no "
        "sustituye el análisis de competencia, hechos, soportes ni régimen sectorial aplicable."
    )


def _legal_basis(a: dict, c: dict) -> list[str]:
    return [
        "Constitución Política, artículo 15: derecho a conocer, actualizar y rectificar la información recogida sobre la persona en bancos de datos y archivos.",
        "Ley Estatutaria 1266 de 2008, en especial artículos 12, 13 y 16, sobre comunicación previa, permanencia de la información y trámite de consultas y reclamos.",
        "Ley Estatutaria 2157 de 2021, en cuanto modificó la permanencia de la información, reforzó la comunicación previa y adicionó reglas de suplantación y silencio en el artículo 16 de la Ley 1266 de 2008.",
        _regime_paragraph(a, c),
    ]


def _actors_table(a: dict) -> list[list[str]]:
    return [
        ["Interviniente", "Identificación en el expediente"],
        ["Titular", _subject(a)],
        ["Documento", _value(a.get("data_subject_id"), "Identificación por verificar")],
        ["Fuente", _value(a.get("source_name"), "Fuente por identificar")],
        ["Operador de información", _value(a.get("operator_name"), "Operador por identificar")],
        ["Usuario de la información", _value(a.get("user_entity_name"), "No individualizado")],
    ]


def _ordinary_track(a: dict) -> str:
    return (
        f"La controversia ordinaria descrita en el expediente se refiere a: "
        f"{_value(a.get('facts_detail'), 'hechos por precisar')}. Esta ruta debe conservarse separada "
        "de cualquier producto u obligación que el titular desconozca por posible suplantación."
    )


def _identity_track(a: dict) -> str:
    if not _yes(a.get("identity_theft")):
        return "No se activó una ruta separada de posible suplantación con la información suministrada."
    return (
        "Existe además una hipótesis separada de posible suplantación respecto de "
        f"{_value(a.get('identity_theft_obligation'), 'un producto u obligación por individualizar')}. "
        "Esta hipótesis no transforma automáticamente la obligación reconocida o pagada de la ruta "
        "ordinaria en una obligación fraudulenta; debe tramitarse y probarse de manera independiente."
    )


def _permanence_table(a: dict, c: dict) -> list[list[str]]:
    return [
        ["Variable", "Dato disponible", "Uso jurídico"],
        ["Inicio de mora", _date(a.get("mora_start_date") or c.get("mora_start_date")), "Determina duración de mora y control de caducidad"],
        ["Pago o extinción", _date(a.get("payment_or_extinction_date") or c.get("payment_or_extinction_date")), "Punto de partida del término de permanencia del dato pagado"],
        ["Duración de mora", _value(c.get("mora_duration_days"), "No calculada"), "Debe cotejarse con extractos y fechas de exigibilidad"],
        ["Retiro preliminar del dato pagado", _date(c.get("paid_negative_expiry_preliminary")), "Estimación condicionada a la verificación de fechas y naturaleza del reporte"],
        ["Caducidad preliminar del dato insoluto", _date(c.get("unpaid_negative_expiry_preliminary")), "Control máximo sujeto a verificación del supuesto de obligación insoluta"],
    ]


def _claim_timing_table(a: dict, c: dict) -> list[list[str]]:
    return [
        ["Hito", "Fecha / término", "Observación"],
        ["Radicación modelada", _date(c.get("filing_date") or a.get("filing_date")), "Confirmar recepción efectiva y canal"],
        ["Leyenda 'reclamo en trámite'", _date(c.get("claim_legend_due_date")), "Control preliminar; legalmente opera dentro de dos días hábiles desde el reclamo completo"],
        ["Vencimiento ordinario", _date(c.get("preliminary_due_date")), "Quince días hábiles para reclamos"],
        ["Vencimiento máximo modelado", _date(c.get("preliminary_due_with_extension")), "La extensión requiere comunicación de motivos y nueva fecha"],
    ]


def _prior_claim_phase(a: dict, c: dict) -> tuple[str, str]:
    ref = _reference_date(a, c)
    ordinary = _parse_date(c.get("prior_preliminary_due_date"))
    maximum = _parse_date(c.get("prior_max_due_date"))
    if ref and ordinary and ref <= ordinary:
        return (
            "EN TÉRMINO ORDINARIO",
            f"A la fecha de referencia ({_date(ref.isoformat())}) el vencimiento ordinario modelado es {_date(ordinary.isoformat())}; por tanto, no puede afirmarse todavía incumplimiento del término ni silencio por falta de respuesta.",
        )
    if ref and ordinary and maximum and ordinary < ref <= maximum:
        return (
            "TÉRMINO ORDINARIO VENCIDO; EXTENSIÓN POR VERIFICAR",
            "El término ordinario ya transcurrió. Solo puede utilizarse el término adicional cuando la prórroga haya sido comunicada oportunamente, con sus motivos y una fecha de respuesta que respete el máximo aplicable.",
        )
    if ref and maximum and ref > maximum:
        return (
            "PLAZO MÁXIMO MODELADO VENCIDO",
            "El plazo máximo modelado ya transcurrió, sujeto a confirmar que el reclamo estaba completo, que existe prueba de recepción y que no hubo una actuación válida que altere el cómputo.",
        )
    return (
        "ESTADO POR VERIFICAR",
        "No hay fechas suficientes para afirmar vencimiento. Debe reconstruirse la recepción, integridad del reclamo, prórroga y respuesta antes de invocar consecuencias por silencio.",
    )


def _externalize_controls(spec: dict, sections: list[dict]) -> dict:
    result = deepcopy(spec)
    old_sections = list(result.get("sections") or [])
    old_controls = [
        deepcopy(section)
        for section in old_sections
        if isinstance(section, dict)
        and (section.get("_type") == "control" or "control de uso" in str(section.get("heading") or "").casefold())
    ]
    internal = list(deepcopy(result.get("internal_review_sections") or []))
    internal.extend(old_controls)
    internal.append({
        "heading": "CONTROL JURÍDICO CO-CD-001",
        "_type": "control",
        "text": (
            "Verificar identidad y legitimación; recepción efectiva; clasificación consulta/reclamo; "
            "comunicación previa; permanencia; separación entre obligación reconocida y posible "
            "suplantación; vigencia temporal de Ley 2573 de 2026; competencia SIC/SFC; y coherencia "
            "entre la pieza, la matriz probatoria y el calendario. Aprobación jurídica y QA pendientes."
        ),
    })
    client_sections = deepcopy(sections)
    if client_sections:
        client_sections[0]["_suppress_default_control"] = True
    result["sections"] = client_sections
    result["internal_review_sections"] = internal
    result["internal_controls_externalized"] = True
    result["document_standard"] = "M33.0"
    result["legal_approval"] = "pending"
    result["qa_approval"] = "pending"
    result["released"] = False
    return result


def _consultation_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {
            "heading": "ASUNTO Y OBJETO DE LA CONSULTA",
            "paragraphs": [
                f"{_subject(a)} ejerce su derecho de consulta respecto de la información financiera, crediticia, comercial y de servicios asociada a su identidad. La finalidad es obtener un registro completo y trazable que permita conocer qué datos circulan, quién los suministró, cuándo fueron actualizados y qué soporte explica su estado actual.",
                "La consulta no presume que un reporte sea ilícito ni solicita suprimir información por el solo hecho de ser negativa. Primero busca reconstruir el dato y su trazabilidad; cualquier petición de corrección, actualización o retiro deberá apoyarse en hechos y documentos identificables.",
            ],
        },
        {"heading": "I. IDENTIFICACIÓN DE LOS INTERVINIENTES", "table": _actors_table(a)},
        {"heading": "II. MARCO JURÍDICO Y VIGENCIA", "numbered": _legal_basis(a, c)},
        {
            "heading": "III. INFORMACIÓN SOLICITADA AL OPERADOR",
            "numbered": [
                "Entregar copia íntegra, clara, comprensible y actualizada del registro individual del titular, incluidas las obligaciones, saldos, estados, fechas, leyendas y novedades vinculadas con su identificación.",
                "Identificar la fuente de cada dato y las fechas de creación, primer reporte, actualizaciones materiales, pago o extinción y retiro, cuando esos hitos existan en el registro.",
                "Informar la naturaleza de cualquier leyenda vigente —reclamo en trámite, discusión judicial, posible suplantación u otra— y la fecha y soporte con que fue incorporada.",
                "Permitir verificar las consultas efectuadas sobre el registro en el alcance legalmente disponible, diferenciando la consulta del propio titular de las consultas realizadas por usuarios autorizados.",
                "Indicar el canal, responsable y número de radicado para formular una reclamación posterior y aportar las políticas o reglas públicas necesarias para comprender el trámite.",
            ],
        },
        {
            "heading": "IV. INFORMACIÓN SOLICITADA A LA FUENTE",
            "numbered": [
                "Individualizar el negocio u obligación que sustenta cada dato reportado, con identificación del producto, fecha de apertura o celebración, exigibilidad, saldo, mora y estado actual.",
                "Aportar o identificar el soporte de la obligación y la trazabilidad de los pagos, abonos, ajustes, notas crédito o extinción que deban reflejarse en el reporte.",
                "Aportar evidencia de la comunicación previa al reporte negativo, con fecha, canal, destino y contenido suficiente para verificar el cumplimiento del artículo 12 de la Ley 1266 de 2008.",
                "Informar la fecha exacta en que se suministró por primera vez la información negativa y cada actualización material comunicada al operador.",
                "Explicar el término de permanencia aplicado y el hito a partir del cual fue contado, cuando el dato permanezca visible después del pago o extinción.",
            ],
        },
        {
            "heading": "V. CONTROL TEMPORAL PRELIMINAR",
            "table": _permanence_table(a, c),
            "paragraphs": [
                "Los resultados temporales son controles de expediente y no sustituyen la evidencia. La fecha de mora debe corresponder a la obligación efectivamente exigible; el pago o extinción debe estar acreditado; y la permanencia debe calcularse con el régimen vigente para el supuesto concreto.",
            ],
        },
        {
            "heading": "VI. PROTECCIÓN DE IDENTIDAD Y MINIMIZACIÓN",
            "paragraphs": [
                "Los documentos de identidad y soportes aportados para autenticar al titular deben utilizarse exclusivamente para verificar legitimación y tramitar la consulta. La entidad deberá evitar exigir o circular información excesiva y aplicar medidas razonables de seguridad frente a copias de documentos, biometría, credenciales y demás datos de autenticación.",
            ],
        },
        {
            "heading": "VII. RESPUESTA, RADICACIÓN Y TRAZABILIDAD",
            "paragraphs": [
                "Se solicita respuesta de fondo, legible y verificable, conservando el radicado, la fecha de recepción y los anexos entregados. Para las consultas, el artículo 16 de la Ley 1266 de 2008 prevé un término máximo de diez (10) días hábiles y, cuando no sea posible atender dentro de ese plazo, una extensión máxima de cinco (5) días hábiles adicionales debidamente informada.",
            ],
        },
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR DE LA INFORMACIÓN", "name": _subject(a), "id": _value(a.get("data_subject_id"), "")}]} ,
    ]


def _claim_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {
            "heading": "ASUNTO, PRETENSIÓN Y DELIMITACIÓN",
            "paragraphs": [
                f"{_subject(a)} formula reclamación de hábeas data financiero para obtener la verificación, corrección, actualización o retiro condicionado de la información identificada en el expediente. La reclamación no parte de que toda información negativa sea improcedente: exige que el dato sea veraz, completo, comprobable, actualizado y temporalmente legítimo.",
                _ordinary_track(a),
                _identity_track(a),
            ],
        },
        {"heading": "I. IDENTIFICACIÓN DE LOS INTERVINIENTES", "table": _actors_table(a)},
        {
            "heading": "II. HECHOS RELEVANTES DE LA RUTA ORDINARIA",
            "numbered": [
                _value(a.get("facts_detail"), "Los hechos deberán individualizarse antes de radicar."),
                f"Inicio de mora informado: {_date(a.get('mora_start_date') or c.get('mora_start_date'))}.",
                f"Pago o extinción informada: {_date(a.get('payment_or_extinction_date') or c.get('payment_or_extinction_date'))}.",
                f"Fecha de reporte informada: {_date(a.get('report_date'))}.",
                f"Fecha en que el titular manifiesta haber conocido el reporte: {_date(a.get('report_discovery_date'))}.",
                "La exactitud de estos hitos deberá cotejarse con el contrato, extractos, soportes de pago, historia de reporte y comunicación previa; ninguna fecha ingresada en formulario reemplaza por sí sola la prueba documental.",
            ],
        },
        {"heading": "III. FUNDAMENTO JURÍDICO Y VIGENCIA", "numbered": _legal_basis(a, c)},
        {
            "heading": "IV. SOLICITUDES A LA FUENTE",
            "numbered": [
                "Certificar el origen, naturaleza, exigibilidad, valor, mora, pagos y estado actual de la obligación discutida, acompañando los documentos que soporten esa reconstrucción.",
                "Aportar la evidencia de la comunicación previa al reporte negativo, identificando fecha, canal, dirección o destino y contenido enviado al titular.",
                "Precisar la fecha del primer reporte negativo y las fechas de las actualizaciones materiales comunicadas al operador.",
                "Corregir de inmediato los datos que resulten inexactos, incompletos, fraccionados, desactualizados o no comprobables y transmitir la novedad al operador con trazabilidad de la instrucción.",
                "Si la obligación ya fue extinguida y se verifica que el reporte negativo se efectuó sin la comunicación previa exigible, aplicar la consecuencia prevista en el parágrafo del artículo 12 de la Ley 1266 de 2008, adicionado por la Ley 2157 de 2021, sin confundir el retiro del reporte con una declaración sobre otros efectos civiles de la obligación.",
                "Si el término de permanencia aplicable ya concluyó, solicitar al operador el retiro del dato negativo y de las mediciones que jurídicamente deban actualizarse como consecuencia de ese retiro.",
                "Responder de manera individual a cada hecho y solicitud, señalando los documentos y criterios concretos que sustentan cualquier negativa total o parcial.",
            ],
        },
        {
            "heading": "V. SOLICITUDES AL OPERADOR",
            "numbered": [
                "Incorporar y mantener la leyenda 'reclamo en trámite' y la naturaleza de la controversia dentro del término legal, siempre que el reclamo se encuentre completo y cumpla los presupuestos aplicables.",
                "Trasladar a la fuente los aspectos que dependan de esta y conservar evidencia de la coordinación, sin abandonar las obligaciones propias del operador frente al titular.",
                "Ejecutar las correcciones, actualizaciones o retiros que resulten procedentes y permitir al titular verificar el resultado mediante un registro actualizado.",
                "Mantener sincronizadas las leyendas, estados y mediciones vinculadas al dato corregido o retirado cuando el régimen aplicable lo exija.",
                "Entregar una respuesta propia sobre los puntos de su competencia y no limitarse a reproducir una contestación de la fuente si persiste una inconsistencia objetiva en el registro.",
            ],
        },
        {
            "heading": "VI. COMUNICACIÓN PREVIA Y PERMANENCIA",
            "table": _permanence_table(a, c),
            "paragraphs": [
                "El artículo 13 de la Ley 1266 de 2008, modificado por la Ley 2157 de 2021, establece como regla general para datos negativos de obligaciones pagadas un término equivalente al doble del tiempo de mora, con máximo de cuatro años desde el pago o extinción, y un límite de caducidad de ocho años para la información negativa asociada a obligaciones insolutas. La aplicación al caso requiere verificar los hitos reales y la clase de obligación.",
                "La comunicación previa no se presume por la mera existencia del reporte. Debe existir evidencia suficiente del envío en los términos aplicables y con la antelación exigida antes del reporte negativo.",
            ],
        },
        {
            "heading": "VII. TRÁMITE Y TÉRMINOS DEL RECLAMO",
            "table": _claim_timing_table(a, c),
            "paragraphs": [
                "Para reclamos, el artículo 16 de la Ley 1266 de 2008 establece un término máximo de quince (15) días hábiles, prorrogable hasta por ocho (8) días hábiles adicionales cuando la imposibilidad de responder oportunamente sea informada con sus motivos y con una nueva fecha. La leyenda 'reclamo en trámite' debe incorporarse dentro de dos (2) días hábiles desde la recepción del reclamo completo.",
            ],
        },
        {
            "heading": "VIII. PRUEBA, RESPUESTA Y RESERVA",
            "paragraphs": [
                "La respuesta deberá identificar los documentos examinados y permitir relacionar cada conclusión con un soporte. El titular conservará copia exacta del reclamo, anexos, constancia de recepción, respuesta y consulta posterior del registro.",
                "La reclamación no constituye confesión, renuncia, novación ni aceptación de una obligación distinta de la que resulte efectivamente acreditada. Tampoco solicita eliminar información veraz y vigente por razones de conveniencia crediticia.",
            ],
        },
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR DE LA INFORMACIÓN", "name": _subject(a), "id": _value(a.get("data_subject_id"), "")}]} ,
    ]


def _reiteration_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    phase, phase_detail = _prior_claim_phase(a, c)
    prior_result = _value(a.get("prior_claim_result"), "Sin resultado documentado")
    return [
        {
            "heading": "ASUNTO Y FINALIDAD DE LA REITERACIÓN",
            "paragraphs": [
                f"{_subject(a)} hace seguimiento a la reclamación radicada el {_date(a.get('prior_claim_date') or c.get('prior_claim_date'))}, identificada con {_value(a.get('prior_claim_radicado'), 'radicado por verificar')}. La finalidad es preservar la trazabilidad del trámite, precisar los puntos pendientes y evitar atribuir efectos jurídicos a un silencio que todavía no se haya configurado.",
                f"Estado reportado por el titular: {prior_result}. Este dato describe la percepción o información disponible y no reemplaza la verificación del expediente de recepción, prórroga y respuesta.",
            ],
        },
        {
            "heading": "I. ESTADO TEMPORAL DEL RECLAMO PREVIO",
            "table": [
                ["Control", "Resultado"],
                ["Fecha de reclamo previo", _date(a.get("prior_claim_date") or c.get("prior_claim_date"))],
                ["Vencimiento ordinario modelado", _date(c.get("prior_preliminary_due_date"))],
                ["Vencimiento máximo modelado", _date(c.get("prior_max_due_date"))],
                ["Fase a la fecha de referencia", phase],
                ["Leyenda de reclamo", "Debe verificarse dentro de dos días hábiles desde la recepción completa; no se reutiliza la fecha de una actuación distinta"],
            ],
            "paragraphs": [phase_detail],
        },
        {
            "heading": "II. MARCO JURÍDICO APLICABLE",
            "numbered": _legal_basis(a, c) + [
                "La Superintendencia de Industria y Comercio ha precisado en decisión divulgada en febrero de 2026 que el efecto del silencio del numeral 8 del artículo 16 no debe trasladarse mecánicamente a toda respuesta tardía; en el precedente citado lo vinculó al supuesto de suplantación. En consecuencia, esta reiteración no declara por sí sola aceptada la reclamación ordinaria.",
            ],
        },
        {
            "heading": "III. PUNTOS QUE DEBEN SER VERIFICADOS EN LA RESPUESTA",
            "numbered": [
                "Que exista respuesta expresa a la exactitud, actualización y permanencia del dato discutido.",
                "Que se aporte la evidencia de comunicación previa cuando el reporte negativo la requiera.",
                "Que el operador haya incorporado y mantenido la leyenda correspondiente durante la controversia cuando proceda.",
                "Que cualquier corrección anunciada haya sido ejecutada materialmente en el registro consultable y no se limite a una promesa futura.",
                "Que se identifiquen las actuaciones de traslado entre operador y fuente y las fechas de su recepción.",
                "Que la ruta ordinaria y la eventual ruta de posible suplantación se mantengan separadas cuando correspondan a obligaciones distintas.",
            ],
        },
        {
            "heading": "IV. SOLICITUDES DE SEGUIMIENTO",
            "numbered": [
                "Confirmar la fecha y hora de recepción del reclamo previo y si fue considerado completo desde su radicación.",
                "Informar el estado actual del trámite y, si existe prórroga, aportar la comunicación mediante la cual se informaron sus motivos y la nueva fecha de respuesta.",
                "Indicar la fecha en que se incorporó la leyenda 'reclamo en trámite' y permitir verificar su permanencia mientras la controversia continúe abierta.",
                "Resolver de fondo los puntos pendientes y adjuntar los documentos anunciados o utilizados como fundamento de la respuesta.",
                "Ejecutar materialmente las correcciones o actualizaciones ya aceptadas y entregar un registro posterior que permita constatar el resultado.",
                "Identificar el mecanismo de revisión o autoridad competente en caso de decisión adversa, sin presentar esta comunicación como recurso judicial ni como orden administrativa.",
            ],
        },
        {
            "heading": "V. PRESERVACIÓN DE EVIDENCIA Y ESCALAMIENTO",
            "paragraphs": [
                "Se conservarán la reclamación original, el acuse o radicado, la constancia de integridad, cualquier comunicación de prórroga, la respuesta recibida y las consultas del registro antes y después de la decisión. Si persiste una vulneración, la competencia administrativa deberá verificarse entre la Superintendencia de Industria y Comercio y, cuando corresponda por la naturaleza de la entidad vigilada y la materia, la Superintendencia Financiera de Colombia.",
            ],
        },
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR DE LA INFORMACIÓN", "name": _subject(a), "id": _value(a.get("data_subject_id"), "")}]} ,
    ]


def _identity_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {
            "heading": "1. ACTIVACIÓN Y DELIMITACIÓN DE LA RUTA",
            "paragraphs": [
                _identity_track(a),
                "El protocolo se activa únicamente para el producto u obligación que la persona afirma no haber solicitado, contratado o autorizado. No debe utilizarse para convertir en suplantación una obligación reconocida cuando la controversia real sea pago, saldo, permanencia o comunicación previa.",
            ],
        },
        {
            "heading": "2. RÉGIMEN JURÍDICO Y CONTROL TEMPORAL",
            "numbered": _legal_basis(a, c) + [
                "Mientras no haya entrado en vigor el régimen general diferido de la Ley 2573 de 2026, la ruta debe operar con las reglas actualmente vigentes de la Ley 1266 de 2008 y la Ley 2157 de 2021, sin anticipar términos, cargas o efectos futuros.",
            ],
        },
        {
            "heading": "3. PRESERVACIÓN INMEDIATA DE EVIDENCIA",
            "numbered": [
                "Conservar la primera consulta en la que aparece el producto desconocido, con fecha, hora y fuente de obtención.",
                "Conservar correos, mensajes, llamadas, alertas, contratos, comprobantes, enlaces y archivos originales sin sobrescribirlos ni editar metadatos cuando sea posible.",
                "Registrar la fecha exacta en que el titular conoció el producto u obligación y las acciones realizadas desde ese momento.",
                "Solicitar a la fuente la preservación de solicitudes de apertura, contratos, grabaciones, validaciones de identidad, biometría, direcciones IP, dispositivos, geolocalización, cuentas receptoras y soportes de entrega que existan legítimamente.",
                "Cambiar credenciales comprometidas y reforzar autenticación cuando exista un riesgo actual, evitando circular copias completas del documento de identidad por canales abiertos.",
            ],
        },
        {
            "heading": "4. SOLICITUDES A LA FUENTE",
            "numbered": [
                "Individualizar el producto u obligación desconocida y entregar copia de los documentos y datos utilizados para su aprobación o contratación, en el alcance jurídicamente procedente.",
                "Comparar los documentos y datos utilizados en la operación con los aportados por el titular y explicar de manera motivada cualquier coincidencia o discrepancia.",
                "Preservar la evidencia técnica y documental mientras se resuelve la controversia y evitar la destrucción ordinaria de registros relevantes.",
                "Aplicar las medidas de corrección, marcación o actualización que correspondan bajo el régimen vigente, sin presentar como decisión judicial una conclusión interna sobre la existencia o inexistencia del delito.",
                "Informar si existen desembolsos, entregas, cuentas receptoras, dispositivos, números, direcciones o terceros vinculados que permitan reconstruir el flujo de la operación.",
            ],
        },
        {
            "heading": "5. SOLICITUDES AL OPERADOR DE INFORMACIÓN",
            "numbered": [
                "Registrar la controversia y las leyendas que correspondan conforme al régimen vigente y a la actuación efectivamente radicada.",
                "Coordinar con la fuente la verificación del dato y mantener trazabilidad del traslado y de la respuesta.",
                "Evitar que una corrección aceptada permanezca sin ejecutar materialmente en el registro consultable.",
                "Permitir al titular obtener una consulta posterior que evidencie el resultado de la investigación y las leyendas vigentes.",
            ],
        },
        {
            "heading": "6. SILENCIO Y RESPUESTA TARDÍA",
            "paragraphs": [
                "La falta de respuesta debe documentarse con la prueba de recepción y el cómputo completo de términos. La SIC ha señalado en una decisión divulgada en febrero de 2026 que el efecto del silencio previsto en el numeral 8 del artículo 16 se vincula de manera específica con la protección de víctimas de suplantación; aun en ese escenario, la pieza debe identificar la obligación concreta y los hechos que sustentan la hipótesis, en lugar de utilizar el silencio como fórmula automática para borrar cualquier dato.",
            ],
        },
        {
            "heading": "7. AUTORIDADES Y ESCALAMIENTO PROFESIONAL",
            "numbered": [
                "Evaluar la presentación de denuncia penal cuando los hechos revelen una posible conducta delictiva, preservando el número de noticia criminal y los anexos aportados si se radica.",
                "Verificar la autoridad administrativa competente para la protección del hábeas data según la naturaleza de la fuente, operador y entidad vigilada.",
                "Escalar a revisión profesional si existen múltiples productos, desembolsos relevantes, procesos ejecutivos, embargos, biometría controvertida, afectación tributaria, investigación penal compleja o daño económico significativo.",
            ],
        },
        {
            "heading": "8. CRITERIO DE CIERRE",
            "paragraphs": [
                "El expediente de posible suplantación solo se considerará técnicamente cerrado cuando consten la decisión de cada fuente u operador, las correcciones ejecutadas, las consultas posteriores del registro y el estado de cualquier actuación administrativa, judicial o penal vinculada. Una promesa de investigación o una respuesta sin ejecución material no equivale a cierre.",
            ],
        },
    ]


def _authority_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    authority = _value(a.get("competent_authority"), "Autoridad competente por verificar")
    phase, phase_detail = _prior_claim_phase(a, c)
    return [
        {
            "heading": "ASUNTO Y DESTINATARIO",
            "paragraphs": [
                f"Se prepara solicitud de intervención administrativa dirigida preliminarmente a {authority}, sujeta a verificación de competencia antes de la radicación. El propósito es poner en conocimiento una posible vulneración del derecho de hábeas data y aportar un expediente trazable que permita a la autoridad ejercer las facultades que legalmente le correspondan.",
                "La comunicación no solicita a la autoridad declarar una deuda inexistente ni ordenar consecuencias por fuera de su competencia; delimita hechos, actuaciones previas, evidencia y medidas de protección de datos que requieren valoración administrativa.",
            ],
        },
        {"heading": "I. TITULAR Y ENTIDADES INVOLUCRADAS", "table": _actors_table(a)},
        {
            "heading": "II. ACTUACIÓN PREVIA",
            "table": [
                ["Elemento", "Información"],
                ["Reclamo previo", _date(a.get("prior_claim_date") or c.get("prior_claim_date"))],
                ["Radicado", _value(a.get("prior_claim_radicado"), "Por verificar")],
                ["Resultado informado", _value(a.get("prior_claim_result"), "Por verificar")],
                ["Fase temporal", phase],
                ["Vencimiento ordinario modelado", _date(c.get("prior_preliminary_due_date"))],
                ["Vencimiento máximo modelado", _date(c.get("prior_max_due_date"))],
            ],
            "paragraphs": [phase_detail],
        },
        {"heading": "III. FUNDAMENTO JURÍDICO Y VIGENCIA", "numbered": _legal_basis(a, c)},
        {
            "heading": "IV. HECHOS QUE SE SOMETEN A VERIFICACIÓN",
            "numbered": [
                _ordinary_track(a),
                "Se requiere verificar la comunicación previa al reporte, la exactitud de la historia de mora y pago, el término de permanencia utilizado y la ejecución material de cualquier actualización solicitada.",
                _identity_track(a),
                "La ausencia o tardanza de respuesta solo se invocará con el alcance que resulte jurídicamente procedente después de confirmar recepción, integridad del reclamo, prórroga y régimen aplicable.",
            ],
        },
        {
            "heading": "V. SOLICITUDES A LA AUTORIDAD",
            "numbered": [
                "Verificar, dentro de sus competencias, el cumplimiento de las obligaciones de la fuente y del operador frente a la exactitud, actualización, comunicación previa, permanencia y trámite del reclamo.",
                "Requerir los documentos y registros necesarios para reconstruir la trazabilidad del dato y de las actuaciones adelantadas frente al titular.",
                "Adoptar las órdenes o medidas administrativas que resulten legalmente procedentes para hacer efectivo el derecho de hábeas data, sin prejuzgar sobre controversias contractuales o penales ajenas a la competencia administrativa.",
                "Cuando corresponda, verificar la correcta marcación y tratamiento de una controversia por posible suplantación y la ejecución efectiva de las correcciones que hayan sido aceptadas.",
                "Informar al titular el número de radicado, dependencia responsable y canal para aportar documentos adicionales o consultar la decisión.",
            ],
        },
        {
            "heading": "VI. ANEXOS MÍNIMOS",
            "numbered": [
                "Documento de identidad aportado con las medidas de seguridad y minimización necesarias.",
                "Consulta o reporte donde conste el dato discutido.",
                "Reclamo previo completo y constancia de recepción o radicado.",
                "Respuesta, prórroga o evidencia de ausencia de respuesta, según el estado real del expediente.",
                "Soportes de pago o extinción, cuando la controversia verse sobre permanencia del dato.",
                "Documentos sobre comunicación previa, si fueron entregados por la fuente.",
                "Soportes separados de posible suplantación cuando esa ruta haya sido activada.",
                "Matriz probatoria y calendario del expediente.",
            ],
        },
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR DE LA INFORMACIÓN", "name": _subject(a), "id": _value(a.get("data_subject_id"), "")}]} ,
    ]


def _evidence_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    rows = [
        ["ID", "Evidencia", "Hecho o control", "Estado"],
        ["HD-EV-001", "Documento de identidad", "Legitimación del titular", "Por verificar"],
        ["HD-EV-002", "Consulta del operador", "Dato, saldo, estado y fecha visible", "Por conservar"],
        ["HD-EV-003", "Contrato / soporte de obligación", "Origen y exigibilidad", "Solicitar a la fuente"],
        ["HD-EV-004", "Historia de pagos / paz y salvo", "Pago o extinción", "Por verificar"],
        ["HD-EV-005", "Comunicación previa", "Cumplimiento previo al reporte", "Solicitar evidencia"],
        ["HD-EV-006", "Historia de reportes", "Primer reporte y actualizaciones", "Solicitar a fuente/operador"],
        ["HD-EV-007", "Reclamo previo", "Contenido exacto de la controversia", "Conservar versión radicada"],
        ["HD-EV-008", "Acuse / radicado", "Fecha de recepción y cómputo", "Obligatorio"],
        ["HD-EV-009", "Prórroga o respuesta", "Cumplimiento de términos y decisión", "Por incorporar"],
        ["HD-EV-010", "Consulta posterior", "Ejecución material de la corrección", "Pendiente"],
    ]
    if _yes(a.get("identity_theft")):
        rows.extend([
            ["HD-EV-011", "Documentos de apertura del producto desconocido", "Comparación de identidad y trazabilidad", "Solicitar a la fuente"],
            ["HD-EV-012", "Registros técnicos de autenticación", "IP, dispositivo, biometría u otros controles existentes", "Preservar / solicitar"],
            ["HD-EV-013", "Soporte de denuncia, si se radica", "Trazabilidad de actuación penal", "Condicional"],
        ])
    return [
        {
            "heading": "1. FINALIDAD Y REGLA DE TRAZABILIDAD",
            "paragraphs": [
                "La matriz relaciona cada afirmación relevante con la evidencia que puede confirmarla o controvertirla. Un dato informado por el usuario o extraído de una captura se registra como insumo, pero no se convierte en hecho definitivamente probado hasta ser cotejado con una fuente suficientemente confiable.",
                "La matriz conserva por separado la controversia ordinaria sobre permanencia, actualización o comunicación previa y la eventual ruta de posible suplantación, evitando contaminar una con las inferencias de la otra.",
            ],
        },
        {"heading": "2. MATRIZ DE EVIDENCIAS", "table": rows},
        {
            "heading": "3. REGLAS DE CUSTODIA",
            "numbered": [
                "Conservar el archivo original y trabajar sobre copias identificadas cuando sea posible.",
                "Registrar nombre de archivo, fecha de obtención, emisor, canal y versión.",
                "No eliminar evidencia desfavorable ni sobrescribir documentos anteriores con versiones nuevas.",
                "Vincular cada documento con el hecho, fecha o solicitud que soporta.",
                "Distinguir hechos confirmados, manifestaciones del titular, respuestas de terceros e inferencias jurídicas.",
                "Actualizar la matriz cada vez que llegue una respuesta, consulta o soporte adicional.",
            ],
        },
        {"heading": "4. CONTROLES TEMPORALES A COTEJAR", "table": _permanence_table(a, c)},
        {
            "heading": "5. CRITERIO DE SUFICIENCIA",
            "paragraphs": [
                "La salida documental puede considerarse lista para revisión jurídica cuando los hechos centrales tengan soporte identificable, las fechas de recepción y reporte sean coherentes, la permanencia pueda reproducirse y exista evidencia suficiente para separar una obligación reconocida de cualquier producto presuntamente obtenido mediante suplantación.",
            ],
        },
    ]


def _calendar_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    phase, phase_detail = _prior_claim_phase(a, c)
    return [
        {
            "heading": "1. REGLAS LEGALES DE CÓMPUTO",
            "table": [
                ["Actuación", "Término legal de referencia", "Control"],
                ["Consulta", "10 días hábiles", "Puede extenderse hasta 5 días hábiles adicionales con información de motivos y nueva fecha"],
                ["Leyenda de reclamo", "2 días hábiles", "Desde la recepción del reclamo completo"],
                ["Reclamo", "15 días hábiles", "Se cuenta conforme al artículo 16 de la Ley 1266 de 2008"],
                ["Prórroga de reclamo", "Hasta 8 días hábiles adicionales", "No es automática; requiere comunicación de motivos y nueva fecha"],
                ["Traslado operador-fuente", "2 días hábiles", "Cuando exista fuente independiente y el reclamo se presenta al operador"],
            ],
        },
        {
            "heading": "2. RECLAMO PREVIO",
            "table": [
                ["Hito", "Resultado"],
                ["Radicación previa", _date(a.get("prior_claim_date") or c.get("prior_claim_date"))],
                ["Radicado", _value(a.get("prior_claim_radicado"), "Por verificar")],
                ["Vencimiento ordinario modelado", _date(c.get("prior_preliminary_due_date"))],
                ["Vencimiento máximo modelado", _date(c.get("prior_max_due_date"))],
                ["Fase a fecha de referencia", phase],
            ],
            "paragraphs": [phase_detail],
        },
        {
            "heading": "3. ACTUACIÓN ACTUAL MODELADA",
            "table": _claim_timing_table(a, c),
            "paragraphs": [
                "La fecha de radicación electrónica puede coincidir con un día no hábil. El expediente debe conservar la evidencia del canal y la regla aplicable a la recepción para justificar el cómputo; el calendario modelado no reemplaza esa constatación.",
            ],
        },
        {"heading": "4. HITOS DE PERMANENCIA", "table": _permanence_table(a, c)},
        {
            "heading": "5. ESCALAMIENTO Y CIERRE",
            "numbered": [
                "No declarar incumplimiento antes del vencimiento aplicable.",
                "Si se comunica prórroga, conservar la comunicación y recalcular el máximo sin alterar el historial anterior.",
                "Si la respuesta es adversa o incompleta, actualizar la matriz probatoria antes de escalar a autoridad.",
                "Si existe posible suplantación, mantener un calendario separado para sus actuaciones y no aplicar anticipadamente el régimen general diferido de la Ley 2573 de 2026.",
                "Cerrar solo después de verificar la decisión, la ejecución material de correcciones y la consulta posterior del registro.",
            ],
        },
    ]


_BUILDERS = {
    "habeas_consultation": _consultation_sections,
    "habeas_claim": _claim_sections,
    "habeas_reiteration": _reiteration_sections,
    "identity_theft_protocol": _identity_sections,
    "habeas_authority_escalation": _authority_sections,
    "habeas_evidence_matrix": _evidence_sections,
    "habeas_deadline_calendar": _calendar_sections,
}

_TITLE_OVERRIDES = {
    "habeas_consultation": "Consulta integral de información financiera, crediticia, comercial y de servicios",
    "habeas_claim": "Reclamación de hábeas data financiero — corrección, actualización y retiro condicionado",
    "habeas_reiteration": "Reiteración de reclamación y control de cumplimiento",
    "identity_theft_protocol": "Protocolo de actuación por posible suplantación de identidad",
    "habeas_authority_escalation": "Solicitud de intervención administrativa por hábeas data financiero",
    "habeas_evidence_matrix": "Matriz probatoria y trazabilidad del expediente de hábeas data",
    "habeas_deadline_calendar": "Calendario jurídico de consulta, reclamo y seguimiento",
}


def finalize_habeas_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Profundiza CO-CD-001 sin alterar compuertas de riesgo ni condicionalidad."""
    if (result or {}).get("risk") == "red":
        return specs

    finalized: list[dict] = []
    for spec in specs:
        kind = spec.get("kind")
        builder = _BUILDERS.get(kind)
        if builder is None:
            finalized.append(spec)
            continue
        rewritten = _externalize_controls(spec, builder(answers, result))
        rewritten["title"] = _TITLE_OVERRIDES.get(kind, rewritten.get("title"))
        rewritten["subtitle"] = "Instrumento jurídico CO-CD-001 · régimen temporal 2026 · candidato para revisión humana"
        finalized.append(rewritten)

    return finalized
