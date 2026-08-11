from __future__ import annotations

"""Finalización jurídica y de presentación para CO-CD-003.

Esta capa se ejecuta después del compositor procedimental M33.0. Conserva la
selección histórica de un único mecanismo sustantivo y los cálculos existentes,
pero recompone la copia externa con reglas vigentes, separa los controles internos
y evita mezclar garantía, retracto, reversión, débito periódico y no entrega.
"""

from copy import deepcopy
from datetime import date
from typing import Any, Callable

from premium_document_engine import format_cop, format_date_es


MECHANISM_KINDS = {
    "warranty_claim",
    "withdrawal_notice",
    "payment_reversal_request",
    "recurring_debit_revocation",
    "ecommerce_non_delivery_termination",
}

CLIENT_SUBTITLES = {
    "consumer_mechanism_diagnosis": "Clasificación del mecanismo aplicable según los hechos y soportes disponibles",
    "warranty_claim": "Defecto o falla repetida · reclamación directa",
    "withdrawal_notice": "Desistimiento dentro del supuesto legal aplicable",
    "payment_reversal_request": "Actuación coordinada frente al proveedor y al emisor del medio de pago",
    "recurring_debit_revocation": "Cese de autorización de cobros periódicos y control de cargos posteriores",
    "ecommerce_non_delivery_termination": "Comercio electrónico · resolución o terminación por falta de entrega",
    "consumer_evidence_matrix": "Trazabilidad de hechos, pretensiones y soportes",
    "consumer_deadline_calendar": "Términos legales y fechas preliminares sujetas a verificación",
}

CLIENT_TITLES = {
    "consumer_mechanism_diagnosis": "Diagnóstico de mecanismo de protección al consumidor",
    "warranty_claim": "Reclamación directa de garantía legal",
    "withdrawal_notice": "Ejercicio del derecho de retracto",
    "payment_reversal_request": "Solicitud de reversión del pago",
    "recurring_debit_revocation": "Revocación de débito periódico",
    "ecommerce_non_delivery_termination": "Terminación por falta de entrega",
    "consumer_evidence_matrix": "Matriz probatoria de protección al consumidor",
    "consumer_deadline_calendar": "Calendario jurídico de protección al consumidor",
}

MECHANISM_LABELS = {
    "warranty_claim": "Garantía legal",
    "withdrawal_notice": "Derecho de retracto",
    "payment_reversal_request": "Reversión del pago",
    "recurring_debit_revocation": "Revocación de débito periódico",
    "ecommerce_non_delivery_termination": "Terminación por falta de entrega",
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


def _money(value: Any) -> str:
    try:
        return format_cop(float(value or 0), include_words=False)
    except Exception:
        return "Valor por verificar"


def _date(value: Any) -> str:
    if not value:
        return "Por verificar"
    try:
        return format_date_es(str(value))
    except Exception:
        return str(value)


def _selected_kind(specs: list[dict]) -> str | None:
    selected = [spec.get("kind") for spec in specs if spec.get("kind") in MECHANISM_KINDS]
    return selected[0] if len(selected) == 1 else None


def _common_table(a: dict) -> list[list[str]]:
    return [
        ["Elemento", "Información del expediente"],
        ["Persona consumidora", _value(a.get("consumer_name"))],
        ["Identificación", _value(a.get("consumer_id"))],
        ["Productor o proveedor", _value(a.get("supplier_name") or a.get("provider_name"))],
        ["Producto o servicio", _value(a.get("product_or_service") or a.get("product_description"))],
        ["Fecha de compra o contratación", _date(a.get("purchase_date"))],
        ["Fecha de entrega", _date(a.get("delivery_date"))],
        ["Valor informado", _money(a.get("amount") or a.get("purchase_value"))],
        ["Canal", _value(a.get("purchase_channel"))],
    ]


def _legal_basis_common() -> list[str]:
    return [
        "Constitución Política, artículo 78, sobre protección de consumidores y responsabilidad por afectaciones a su salud, seguridad y adecuado aprovisionamiento.",
        "Ley 1480 de 2011 — Estatuto del Consumidor — con sus modificaciones vigentes, aplicada según el mecanismo concreto y sin desplazar un régimen sectorial especial cuando este resulte prevalente.",
        "Decreto 1074 de 2015 y reglamentación incorporada o vigente para garantía legal y reversión del pago, en cuanto resulte aplicable al supuesto comprobado.",
        "Ley 2439 de 2024, para las modificaciones vigentes sobre comercio electrónico, retracto y devolución de dinero, junto con la interpretación constitucional vigente del artículo 47.",
    ]


def _evidence_rows(a: dict, selected: str | None) -> list[list[str]]:
    rows = [
        ["Evidencia", "Hecho que acredita", "Estado", "Acción"],
        ["Factura, orden o prueba de compra", "Relación de consumo, producto, fecha y valor", "Por verificar", "Conservar original o copia íntegra"],
        ["Comprobante de pago", "Medio, fecha y valor efectivamente pagado", "Por verificar", "Minimizar datos del instrumento"],
        ["Confirmación de pedido o contrato", "Condiciones ofrecidas y canal", "Por verificar", "Guardar versión y fecha"],
        ["Comunicaciones con el proveedor", "Reclamos, respuestas y compromisos", "Por verificar", "Conservar acuse y metadatos"],
    ]
    if selected == "warranty_claim":
        rows.extend([
            ["Fotografías, videos o diagnóstico", "Existencia y manifestación de la falla", "Por verificar", "Preservar archivos originales"],
            ["Orden de servicio o primera reparación", "Intervención previa y falla repetida", "Por verificar", "Comparar fechas y diagnóstico"],
        ])
    elif selected == "withdrawal_notice":
        rows.extend([
            ["Prueba de entrega o celebración", "Inicio del término de retracto", "Por verificar", "Confirmar fecha exacta"],
            ["Constancia de ejercicio del retracto", "Fecha y contenido de la decisión", "Por generar", "Obtener recepción verificable"],
            ["Guía o acta de devolución", "Restitución del bien cuando procede", "Condicional", "Conservar trazabilidad logística"],
        ])
    elif selected == "payment_reversal_request":
        rows.extend([
            ["Queja al proveedor", "Cumplimiento de actuación coordinada", "Por generar", "Conservar fecha y recepción"],
            ["Notificación al emisor", "Solicitud frente al participante del pago", "Por generar", "Conservar radicado"],
            ["Soporte de la causal", "Fraude, operación no solicitada, no entrega, diferencia o defecto", "Por verificar", "Vincularlo con la operación concreta"],
        ])
    elif selected == "recurring_debit_revocation":
        rows.extend([
            ["Autorización de débito", "Existencia y alcance del mandato periódico", "Por verificar", "Identificar comercio y periodicidad"],
            ["Revocación durable", "Fecha y contenido del cese", "Por generar", "Conservar acuse"],
            ["Extracto con cargo posterior", "Cobro posterior a la revocación", "Condicional", "Identificar fecha de conocimiento"],
        ])
    elif selected == "ecommerce_non_delivery_termination":
        rows.extend([
            ["Promesa o plazo de entrega", "Fecha pactada o ausencia de pacto", "Por verificar", "Conservar oferta/confirmación"],
            ["Seguimiento logístico", "Falta de entrega o indisponibilidad", "Por verificar", "Guardar trazabilidad del transportador"],
            ["Terminación y solicitud de reembolso", "Ejercicio de la facultad del consumidor", "Por generar", "Obtener recepción verificable"],
        ])
    return rows


def _deadline_rows(a: dict, c: dict, selected: str | None) -> list[list[str]]:
    rows = [["Hito", "Regla", "Fecha modelada", "Control"]]
    rows.append([
        "Reclamación directa",
        "Respuesta de fondo: 15 días hábiles desde la recepción de la reclamación completa, salvo régimen especial.",
        _date(c.get("direct_claim_due_date")),
        "Fecha preliminar: el motor no descuenta festivos.",
    ])
    if selected == "warranty_claim":
        rows.extend([
            ["Reparación", "Como regla reglamentaria: hasta 30 días hábiles; puede llegar a 60 si se suministra bien en préstamo en los supuestos aplicables.", "Según fecha de recibo del bien", "Verificar causal y punto de inicio."],
            ["Reposición", "Como regla reglamentaria: 10 días hábiles; existen reglas especiales para bienes sujetos a registro.", "Según decisión y disponibilidad", "Verificar naturaleza del bien."],
            ["Devolución del dinero", "Como regla reglamentaria: 15 días hábiles desde el presupuesto que legalmente active el reembolso.", "Según decisión y entrega/disposición", "No anticipar el hito."],
        ])
    elif selected == "withdrawal_notice":
        rows.extend([
            ["Ejercicio del retracto", "Máximo 5 días hábiles desde la entrega del bien o celebración del contrato de servicios, según el caso.", _date(c.get("withdrawal_due_date")), "Confirmar excepción y fecha ancla."],
            ["Reembolso", "15 días calendario conforme al régimen vigente, sujeto al cumplimiento de las cargas de restitución y datos cuando correspondan.", _date(c.get("withdrawal_refund_due_date")), "Verificar fecha efectiva de ejercicio y devolución."],
        ])
    elif selected == "payment_reversal_request":
        rows.extend([
            ["Queja y notificación", "Dentro de 5 días hábiles desde el hecho que activa la causal, según el régimen de reversión aplicable.", _date(c.get("reversal_request_due_date")), "Proveedor y emisor deben quedar coordinados."],
            ["Ejecución inicial", "La reglamentación prevé un trámite entre participantes; la fecha modelada no equivale a decisión final de una controversia.", _date(c.get("reversal_effective_due_date")), "Fecha preliminar: verificar recepción y participantes."],
        ])
    elif selected == "recurring_debit_revocation":
        rows.extend([
            ["Revocación", "Puede formularse en cualquier momento y sin necesidad de justificar la decisión, por medio durable.", _date(a.get("debit_revocation_date") or a.get("periodic_debit_revocation_date")), "Conservar prueba de recepción."],
            ["Comunicación al emisor diferente", "Cuando corresponda, comunicar la instrucción de cese al emisor dentro de 5 días; la norma no debe reescribirse como 5 días hábiles.", _date(c.get("periodic_debit_control_due_date")), "La fecha del motor es solo control operativo preliminar."],
            ["Cargo posterior", "La reversión del nuevo cargo debe pedirse dentro de 5 días hábiles desde su conocimiento.", "Según cada cargo", "Anexar prueba de la revocación."],
            ["Pago periódico ya efectuado", "Existe además una ruta de reversión solicitada al emisor dentro del mes siguiente al pago, sujeta al capítulo especial.", "Según fecha del pago", "No confundir con la revocación futura."],
        ])
    elif selected == "ecommerce_non_delivery_termination":
        rows.extend([
            ["Entrega", "Plazo acordado; a falta de pacto, máximo 30 días calendario en comercio electrónico.", _date(c.get("default_ecommerce_delivery_due_date")), "Confirmar si existió plazo especial."],
            ["Reembolso", "Si procede la terminación por falta de entrega o indisponibilidad: devolución total dentro de 15 días calendario.", _date(c.get("ecommerce_refund_due_date")), "Sin retenciones o descuentos incompatibles."],
        ])
    return rows


def _diagnosis_sections(a: dict, result: dict, selected: str | None) -> list[dict]:
    c = _calc(result)
    eligibility = c.get("mechanism_eligibility") if isinstance(c.get("mechanism_eligibility"), dict) else {}
    selected_label = MECHANISM_LABELS.get(selected, _value(a.get("request_mode"), "Mecanismo por confirmar"))
    eligibility_rows = [["Mecanismo", "Resultado preliminar"]]
    normalized = {
        "warranty": "Garantía legal",
        "warranty_claim": "Garantía legal",
        "withdrawal": "Derecho de retracto",
        "withdrawal_notice": "Derecho de retracto",
        "reversal": "Reversión del pago",
        "payment_reversal_request": "Reversión del pago",
        "periodic_debit": "Revocación de débito periódico",
        "recurring_debit_revocation": "Revocación de débito periódico",
        "non_delivery": "Terminación por falta de entrega",
        "ecommerce_non_delivery_termination": "Terminación por falta de entrega",
    }
    seen: set[str] = set()
    for key, value in eligibility.items():
        label = normalized.get(str(key), str(key).replace("_", " ").capitalize())
        if label in seen:
            continue
        seen.add(label)
        eligibility_rows.append([label, "Habilitado preliminarmente" if bool(value) else "No habilitado con los datos actuales"])
    if len(eligibility_rows) == 1:
        eligibility_rows.append([selected_label, "Seleccionado por el expediente; verificar presupuestos antes de uso"])

    return [
        {
            "heading": "OBJETO Y ALCANCE DEL DIAGNÓSTICO",
            "paragraphs": [
                "Este diagnóstico clasifica la controversia antes de redactar una reclamación. La garantía legal, el retracto, la reversión del pago, la revocación de débitos periódicos y la terminación por falta de entrega responden a hechos, términos, destinatarios y efectos diferentes; por ello, el expediente debe emitir una sola pieza sustantiva compatible con la ruta seleccionada.",
                "La clasificación no sustituye la prueba ni asegura un resultado. Un régimen sectorial especial —por ejemplo, financiero, asegurador, telecomunicaciones, transporte o turismo— puede complementar o desplazar reglas generales y debe verificarse antes de radicar una actuación definitiva.",
            ],
        },
        {"heading": "I. DATOS DE LA RELACIÓN DE CONSUMO", "table": _common_table(a)},
        {"heading": "II. MARCO JURÍDICO COMÚN", "numbered": _legal_basis_common()},
        {"heading": "III. ELEGIBILIDAD PRELIMINAR", "table": eligibility_rows},
        {
            "heading": "IV. DIFERENCIACIÓN DE LOS MECANISMOS",
            "numbered": [
                "GARANTÍA LEGAL: responde a calidad, idoneidad, seguridad o funcionamiento; no depende del simple arrepentimiento del consumidor.",
                "RETRACTO: permite desistir en los supuestos legales dentro del término correspondiente, aunque el producto no sea defectuoso; está sujeto a excepciones y restitución cuando procede.",
                "REVERSIÓN DEL PAGO: es una ruta especial para operaciones comprendidas por el régimen de comercio electrónico/venta a distancia y pago electrónico, con causales y actuaciones coordinadas frente a proveedor y emisor.",
                "DÉBITO PERIÓDICO: permite revocar el mandato de cobro futuro y contempla rutas específicas frente a cargos posteriores o pagos periódicos ya efectuados; no extingue por sí solo una obligación principal válida.",
                "FALTA DE ENTREGA: en comercio electrónico atiende el incumplimiento del plazo de entrega o la indisponibilidad y no debe presentarse como retracto cuando el bien nunca llegó.",
            ],
        },
        {
            "heading": "V. DECISIÓN DOCUMENTAL",
            "paragraphs": [
                f"Con los datos actuales, la pieza sustantiva seleccionada es: {selected_label}. Las demás rutas no se incorporan a esta comunicación para evitar peticiones incompatibles o duplicación de remedios.",
                "Si aparecen hechos nuevos que cambien la clasificación, debe abrirse una nueva revisión del expediente, conservar la anterior y volver a comprobar términos, destinatarios, pretensiones y soportes.",
            ],
        },
        {
            "heading": "VI. ESCALAMIENTO OBLIGATORIO",
            "paragraphs": [
                "Lesiones, riesgos de seguridad del producto, afectación colectiva, fraude o suplantación compleja, procesos jurisdiccionales en curso, medidas cautelares, cuantías o daños relevantes y controversias sometidas a regulación sectorial especial requieren revisión profesional individual antes de presentar una actuación definitiva."
            ],
        },
    ]


def _warranty_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    repeated = _yes(a.get("repeated_failure"))
    return [
        {
            "heading": "ASUNTO Y OBJETO DE LA RECLAMACIÓN",
            "paragraphs": [
                "La persona consumidora formula reclamación directa para hacer efectiva la garantía legal frente a una falla de calidad, idoneidad, seguridad o funcionamiento. La reclamación se apoya en el Estatuto del Consumidor y su reglamentación y no se presenta como retracto, pues el fundamento es el defecto o incumplimiento de las condiciones del producto o servicio.",
            ],
        },
        {"heading": "I. IDENTIFICACIÓN DE LA RELACIÓN", "table": _common_table(a)},
        {
            "heading": "II. HECHOS RELEVANTES",
            "numbered": [
                f"La falla informada se describe así: {_value(a.get('defect_detail') or a.get('facts_detail'))}.",
                f"Existencia de una falla repetida informada: {_value(a.get('repeated_failure'))}.",
                "La factura o prueba de compra, las comunicaciones, fotografías, videos, órdenes de servicio y diagnósticos disponibles deben conservarse como anexos identificables.",
                "La garantía se cuenta desde la entrega y su vigencia concreta debe verificarse según el término ofrecido, la naturaleza del bien y las reglas supletivas aplicables.",
            ],
        },
        {
            "heading": "III. FUNDAMENTO Y EFECTOS DE LA GARANTÍA",
            "numbered": [
                "Productor y proveedor responden solidariamente frente al consumidor en los términos legales por la garantía del producto.",
                "La efectividad de la garantía debe ser gratuita para la persona consumidora e incluye las actuaciones necesarias que legalmente correspondan para diagnosticar y ejecutar la solución.",
                "Si se pretende excluir la garantía por uso indebido, debe explicarse la conducta atribuida, la instrucción incumplida, la prueba técnica y la relación causal entre ese uso y la falla.",
                "La decisión debe ser de fondo, escrita y soportada; no basta una respuesta genérica que omita el diagnóstico o la solución efectivamente ofrecida.",
            ],
        },
        {
            "heading": "IV. FALLA REPETIDA Y ELECCIÓN DE LA PERSONA CONSUMIDORA",
            "paragraphs": [
                (
                    "El expediente informa que la falla se repitió después de una intervención. En ese supuesto, y según la naturaleza del bien y de la falla, la Ley 1480 reconoce a la persona consumidora la posibilidad de escoger entre una nueva reparación, la devolución total o parcial del precio o el cambio parcial o total por otro bien de la misma especie o de características similares que no sean inferiores."
                    if repeated else
                    "Con la información suministrada no se ha confirmado una falla repetida. La solución deberá corresponder a la etapa real de la garantía y a la posibilidad o imposibilidad de reparación, sin anticipar remedios que dependan de hechos no acreditados."
                ),
                "La información disponible no identifica de manera inequívoca cuál de esas alternativas ha escogido la persona consumidora. Antes de firmar o radicar esta reclamación debe registrarse esa elección si jurídicamente ya corresponde; el documento no la inventa ni la presume.",
            ],
        },
        {
            "heading": "V. SOLICITUDES",
            "numbered": [
                "Registrar la reclamación, asignar radicado y dejar constancia verificable de su recepción.",
                "Emitir diagnóstico técnico comprensible, identificar las pruebas practicadas y entregar o poner a disposición los soportes utilizados para decidir.",
                "Reconocer y ejecutar la solución que corresponda a la etapa real de la garantía y, en caso de falla repetida, respetar la elección jurídicamente válida de la persona consumidora una vez esta quede expresamente confirmada.",
                "Asumir los costos de transporte, recepción, reparación, reposición o devolución que correspondan conforme al régimen de garantía, sin trasladar cargas incompatibles al consumidor.",
                "Responder de fondo dentro del término legal aplicable e indicar fechas, lugar, responsable y procedimiento concreto para materializar la solución.",
            ],
        },
        {
            "heading": "VI. CONTROL DE TÉRMINOS",
            "table": [
                ["Actuación", "Regla de referencia", "Control del expediente"],
                ["Respuesta a reclamación directa", "15 días hábiles", _date(c.get("direct_claim_due_date"))],
                ["Reparación", "30 días hábiles como regla reglamentaria; 60 en el supuesto de préstamo temporal aplicable", "Verificar fecha de recibo"],
                ["Reposición", "10 días hábiles como regla reglamentaria general", "Verificar decisión y naturaleza del bien"],
                ["Devolución del dinero", "15 días hábiles en el supuesto reglamentario aplicable", "Verificar hito que activa el reembolso"],
            ],
            "paragraphs": ["Las fechas calculadas automáticamente son preliminares porque el calendario del motor excluye fines de semana pero no descuenta festivos nacionales o territoriales. La recepción efectiva, completitud, suspensión o régimen especial pueden modificar el cómputo."],
        },
        {
            "heading": "VII. PRIVACIDAD Y DISPOSITIVOS",
            "paragraphs": [
                "Si el producto almacena datos personales, fotografías, credenciales o información confidencial, el acceso técnico debe limitarse a lo indispensable para el diagnóstico. Cuando sea técnica y razonablemente posible, la persona consumidora debe ser informada antes de restauraciones, formateos o borrados y debe conservar un respaldo independiente de la información necesaria."
            ],
        },
        {
            "heading": "FIRMA",
            "_type": "signature",
            "heading_align": "center",
            "parties": [{"label": "PERSONA CONSUMIDORA", "name": _value(a.get("consumer_name")), "id": _value(a.get("consumer_id"))}],
        },
    ]


def _withdrawal_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "ASUNTO Y DECLARACIÓN", "paragraphs": ["La persona consumidora ejerce el derecho de retracto en el supuesto legal seleccionado. La decisión se fundamenta en el desistimiento permitido por la ley y no en la existencia de una falla, por lo que esta comunicación no se mezcla con una reclamación de garantía."]},
        {"heading": "I. IDENTIFICACIÓN DE LA OPERACIÓN", "table": _common_table(a)},
        {"heading": "II. PRESUPUESTOS DEL RETRACTO", "numbered": [
            f"Modalidad de contratación informada: {_value(a.get('purchase_channel') or a.get('contract_method'))}.",
            f"Fecha relevante de entrega o celebración: {_date(a.get('delivery_date') or a.get('purchase_date'))}.",
            f"Excepción al retracto informada por el expediente: {_value(a.get('withdrawal_exception'))}.",
            f"Fecha de ejercicio registrada: {_date(a.get('withdrawal_exercised_date') or c.get('withdrawal_exercised_date'))}.",
            "El retracto debe ejercerse, como máximo, dentro de los cinco días hábiles siguientes a la entrega del bien o a la celebración del contrato de prestación de servicios, según el supuesto legal aplicable, y no procede cuando concurre una excepción legal.",
        ]},
        {"heading": "III. RESTITUCIÓN DEL BIEN", "paragraphs": ["Cuando exista un bien que deba restituirse, la persona consumidora lo devolverá al productor o proveedor por los mismos medios y en las mismas condiciones en que lo recibió, asumiendo los costos de transporte y los demás que legalmente le correspondan. La devolución y su recepción deben quedar documentadas con fecha, guía o acta y estado del producto."]},
        {"heading": "IV. REEMBOLSO VIGENTE", "paragraphs": ["El régimen vigente fija el reembolso en un máximo de quince (15) días calendario. Tras la Sentencia C-192 de 2026, ese término debe aplicarse de manera uniforme a las modalidades comprendidas por el artículo 47 de la Ley 1480, y no únicamente a operaciones de comercio electrónico. En comercio electrónico deben verificarse, además, las reglas vigentes sobre datos para el reembolso, restitución y medio de pago aplicable."]},
        {"heading": "V. SOLICITUDES", "numbered": [
            "Registrar la fecha y hora de ejercicio del retracto y expedir constancia de recepción.",
            "Informar el procedimiento concreto para la devolución material del bien, cuando corresponda, sin imponer condiciones adicionales incompatibles con la ley.",
            "Resolver el contrato en los términos legalmente procedentes y abstenerse de aplicar penalidades incompatibles con el retracto.",
            "Devolver la totalidad de las sumas pagadas dentro del plazo vigente, identificando fecha, medio y comprobante.",
            "Confirmar el cierre una vez se hayan cumplido las restituciones recíprocas aplicables.",
        ]},
        {"heading": "VI. CALENDARIO", "table": [
            ["Hito", "Regla", "Fecha modelada"],
            ["Último día de ejercicio", "5 días hábiles", _date(c.get("withdrawal_due_date"))],
            ["Reembolso", "15 días calendario", _date(c.get("withdrawal_refund_due_date"))],
        ], "paragraphs": ["El cómputo de días hábiles es preliminar mientras no se incorporen festivos y no se confirme la fecha exacta que activa el término."]},
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "PERSONA CONSUMIDORA", "name": _value(a.get("consumer_name")), "id": _value(a.get("consumer_id"))}]},
    ]


def _reversal_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "ASUNTO Y ALCANCE", "paragraphs": ["La persona consumidora solicita la reversión del pago dentro del régimen especial aplicable a operaciones comprendidas por las reglas de comercio electrónico o venta a distancia y pagadas mediante instrumento de pago electrónico. La solicitud exige una causal legal concreta y actuaciones coordinadas frente al proveedor y el emisor; no equivale a una declaración definitiva de fraude o responsabilidad."]},
        {"heading": "I. IDENTIFICACIÓN DE LA OPERACIÓN", "table": _common_table(a)},
        {"heading": "II. CAUSAL Y CRONOLOGÍA", "table": [
            ["Elemento", "Dato"],
            ["Causal seleccionada", _value(a.get("reversal_cause"))],
            ["Fecha del hecho o conocimiento", _date(a.get("reversal_event_date") or c.get("reversal_event_date"))],
            ["Último día modelado para solicitar", _date(c.get("reversal_request_due_date"))],
            ["Pago electrónico informado", _value(a.get("electronic_payment"))],
        ]},
        {"heading": "III. ACTUACIÓN FRENTE AL PROVEEDOR", "numbered": [
            "Presentar queja identificando la operación, el valor cuya reversión se solicita y una sola causal principal compatible con los hechos.",
            "Obtener constancia verificable de la fecha de presentación y recepción de la queja.",
            "Cuando se trate de un bien recibido que deba restituirse, manifestar su disponibilidad para ser recogido por el proveedor en el lugar y condiciones exigidos por el régimen aplicable.",
            "Conservar la respuesta y cualquier soporte sobre entrega, estado del producto, devolución o solución ofrecida.",
        ]},
        {"heading": "IV. ACTUACIÓN FRENTE AL EMISOR", "numbered": [
            "Notificar al emisor del instrumento de pago dentro del mismo término legal aplicable, aportar la constancia de la queja al proveedor y solicitar la apertura del procedimiento de reversión.",
            "Si la persona consumidora y el titular del instrumento de pago son diferentes, la notificación al emisor debe ser presentada por el titular del instrumento conforme a la reglamentación aplicable.",
            "Identificar el instrumento únicamente mediante datos minimizados suficientes para localizar la transacción; no incorporar números completos de tarjeta, códigos de seguridad, claves, contraseñas ni factores de autenticación.",
            "Solicitar constancia escrita del trámite y de cualquier movimiento contable practicado.",
        ]},
        {"heading": "V. TÉRMINO Y EFECTOS", "paragraphs": ["La queja al proveedor y la notificación al emisor deben presentarse dentro de cinco (5) días hábiles desde el evento que active la causal, según la regla aplicable. La reversión inicial no impide que una controversia posterior sea decidida a favor del proveedor y produzca los efectos previstos en la reglamentación; por ello, este documento no promete un resultado definitivo."]},
        {"heading": "VI. PROHIBICIÓN DE DOBLE RECUPERACIÓN", "paragraphs": ["La persona solicitante debe informar cualquier devolución, abono, reposición o compensación ya recibida. No puede obtenerse dos veces la restitución económica del mismo pago o perjuicio mediante rutas paralelas incompatibles."]},
        {"heading": "VII. SOLICITUDES", "numbered": [
            "Registrar la queja y la notificación con fecha cierta.",
            "Iniciar el procedimiento de reversión respecto del valor individualizado y la causal seleccionada.",
            "Coordinar las actuaciones entre proveedor, emisor y demás participantes del sistema de pago que legalmente deban intervenir.",
            "Informar por escrito el resultado inicial y cualquier actuación posterior que modifique el movimiento contable.",
        ]},
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR / PERSONA SOLICITANTE", "name": _value(a.get("consumer_name")), "id": _value(a.get("consumer_id"))}]},
    ]


def _periodic_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "ASUNTO Y ALCANCE", "paragraphs": ["La persona titular revoca la autorización de débito periódico respecto del mandato identificado. La revocación puede formularse en cualquier momento y sin necesidad de justificar la decisión. Su efecto es detener nuevos cargos bajo esa autorización; no declara inexistente ni extingue automáticamente una obligación principal que se hubiera causado válidamente."]},
        {"heading": "I. IDENTIFICACIÓN", "table": _common_table(a)},
        {"heading": "II. RUTA 1 — REVOCACIÓN DEL MANDATO FUTURO", "numbered": [
            "Comunicar por un medio escrito o durable la revocación a la entidad con la que se acordó el débito periódico y conservar prueba de recepción.",
            "Cuando el emisor del instrumento de pago sea diferente de la entidad receptora de la revocación, debe comunicársele la instrucción de cese dentro de cinco (5) días. Ese término no debe presentarse como cinco días hábiles cuando la norma no lo califica de esa manera.",
            "Solicitar confirmación de la fecha efectiva de desactivación del mandato o token de cobro.",
            "Distinguir los cargos válidamente causados antes de la revocación de los cargos nuevos presentados después de ella.",
        ]},
        {"heading": "III. CARGOS POSTERIORES A LA REVOCACIÓN", "paragraphs": ["Si se presenta un nuevo cargo después de completado el procedimiento de revocación, la persona consumidora puede solicitar al emisor su reversión dentro de cinco (5) días hábiles desde que tuvo conocimiento del cargo, aportando prueba de la revocación previa."]},
        {"heading": "IV. RUTA 2 — REVERSIÓN DE UN PAGO PERIÓDICO YA EFECTUADO", "paragraphs": ["La reglamentación contempla, además, una ruta independiente para solicitar directamente al emisor la reversión de un pago periódico dentro del mes siguiente a la fecha en que se efectuó, sujeta a las reglas del capítulo especial. Esta ruta no debe confundirse con la mera revocación de cobros futuros."]},
        {"heading": "V. SOLICITUDES", "numbered": [
            "Registrar la revocación con fecha cierta y cesar nuevas órdenes de débito bajo el mandato revocado.",
            "Comunicar la instrucción a los participantes que legalmente deban intervenir e informar la fecha efectiva de desactivación.",
            "Identificar cualquier cargo posterior y tramitar su reversión dentro del término aplicable cuando la persona consumidora así lo solicite.",
            "Conservar la trazabilidad del mandato, su revocación y los movimientos posteriores, sin mantener credenciales o datos sensibles innecesarios.",
        ]},
        {"heading": "VI. CONTROL TEMPORAL", "table": [
            ["Control", "Regla", "Fecha modelada"],
            ["Revocación", "En cualquier momento", _date(a.get("debit_revocation_date") or a.get("periodic_debit_revocation_date"))],
            ["Comunicación al emisor diferente", "Dentro de 5 días", _date(c.get("periodic_debit_control_due_date"))],
            ["Cargo posterior", "Reversión dentro de 5 días hábiles desde el conocimiento", "Según cada cargo"],
            ["Pago periódico ya efectuado", "Solicitud de reversión dentro del mes siguiente al pago", "Según cada pago"],
        ], "paragraphs": ["La fecha automática asociada al control de cinco días es auxiliar y debe cotejarse con la calificación exacta del término legal, la fecha de recepción y los participantes del mandato."]},
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "TITULAR", "name": _value(a.get("consumer_name")), "id": _value(a.get("consumer_id"))}]},
    ]


def _non_delivery_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "ASUNTO Y CAUSA", "paragraphs": ["La persona consumidora comunica la terminación o resolución del negocio por falta de entrega en una operación de comercio electrónico. La causa es el incumplimiento del plazo de entrega o la indisponibilidad del producto; no se presenta como retracto, pues el bien no fue recibido en los términos pactados."]},
        {"heading": "I. IDENTIFICACIÓN DE LA OPERACIÓN", "table": _common_table(a)},
        {"heading": "II. CRONOLOGÍA DE ENTREGA", "table": [
            ["Hito", "Dato"],
            ["Fecha de compra", _date(a.get("purchase_date"))],
            ["Fecha prometida", _date(a.get("promised_delivery_date"))],
            ["Fecha supletiva modelada", _date(c.get("default_ecommerce_delivery_due_date"))],
            ["Estado actual", _value(a.get("delivery_status") or a.get("facts_detail"))],
        ]},
        {"heading": "III. REGLA VIGENTE DE ENTREGA", "paragraphs": ["El proveedor debe entregar dentro del plazo acordado. A falta de estipulación, el régimen vigente de comercio electrónico establece un máximo de treinta (30) días calendario desde el día siguiente a la confirmación o aceptación de la oferta. Si el producto no está disponible, esa circunstancia debe comunicarse de forma inmediata. Cuando el plazo acordado o el máximo legal se exceda, o concurra la indisponibilidad en los términos legales, la persona consumidora puede resolver o terminar unilateralmente el contrato."]},
        {"heading": "IV. REEMBOLSO", "paragraphs": ["Cuando proceda la terminación por falta de entrega o indisponibilidad, las sumas pagadas deben devolverse en su totalidad, sin retenciones o descuentos incompatibles, dentro de quince (15) días calendario. En el ámbito regulado por la Ley 2439 de 2024 debe respetarse además la regla vigente sobre el medio de pago preferido por el consumidor para el reembolso."]},
        {"heading": "V. SOLICITUDES", "numbered": [
            "Registrar la terminación o resolución con fecha cierta y confirmar que el pedido o los ítems afectados queden cancelados.",
            "Abstenerse de realizar un despacho posterior salvo nueva aceptación expresa de la persona consumidora.",
            "Devolver la totalidad de las sumas pagadas dentro del término vigente, sin convertir unilateralmente el reembolso en bono, saldo o crédito de tienda.",
            "Informar medio, fecha y comprobante de devolución y confirmar el cierre de la operación.",
        ]},
        {"heading": "VI. CALENDARIO", "table": [
            ["Hito", "Regla", "Fecha modelada"],
            ["Entrega supletiva", "30 días calendario a falta de pacto", _date(c.get("default_ecommerce_delivery_due_date"))],
            ["Reembolso", "15 días calendario", _date(c.get("ecommerce_refund_due_date"))],
        ]},
        {"heading": "VII. RELACIÓN CON OTROS MECANISMOS", "paragraphs": ["La eventual reversión del pago por no entrega es una ruta legal distinta que exige sus propios presupuestos y actuaciones. No se incorpora automáticamente a esta comunicación ni se utiliza para obtener una devolución duplicada; si se selecciona esa vía, debe abrirse una actuación coordinada separada."]},
        {"heading": "FIRMA", "_type": "signature", "heading_align": "center", "parties": [{"label": "PERSONA CONSUMIDORA", "name": _value(a.get("consumer_name")), "id": _value(a.get("consumer_id"))}]},
    ]


def _evidence_sections(a: dict, result: dict, selected: str | None) -> list[dict]:
    return [
        {"heading": "OBJETO DE LA MATRIZ", "paragraphs": ["La matriz vincula cada afirmación y solicitud con su soporte y permite distinguir evidencia común de evidencia específica del mecanismo seleccionado. Los originales deben preservarse sin edición; las copias de trabajo deben minimizar datos personales y financieros que no sean necesarios."]},
        {"heading": "I. EVIDENCIA DEL EXPEDIENTE", "table": _evidence_rows(a, selected)},
        {"heading": "II. REGLAS DE TRAZABILIDAD", "numbered": [
            "Registrar nombre de archivo, fecha, fuente y versión de cada soporte.",
            "Conservar mensajes de datos con información suficiente para acreditar envío, recepción y contenido.",
            "No modificar fotografías, videos, extractos, diagnósticos ni documentos originales; las anotaciones deben hacerse sobre copias identificadas.",
            "Vincular cada soporte con el hecho, causal o solicitud que pretende acreditar y evitar anexos masivos sin relación explicada.",
            "Ocultar números completos de tarjeta, códigos de seguridad, contraseñas, claves y demás credenciales que no deban circular en el expediente.",
            "Incorporar la respuesta de fondo y la prueba de ejecución material de la solución antes de cerrar el caso.",
        ]},
        {"heading": "III. CONTROL DE CIERRE", "numbered": [
            "Verificar que la respuesta corresponda al mecanismo realmente ejercido.",
            "Comprobar reparación, reposición, restitución, reembolso, reversión o cese de débito mediante evidencia independiente.",
            "Confirmar que no existan cargos posteriores o devoluciones duplicadas.",
            "Conservar cualquier escalamiento administrativo o jurisdiccional como una actuación distinta, con su propio radicado y estado.",
        ]},
    ]


def _calendar_sections(a: dict, result: dict, selected: str | None) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "OBJETO Y NATURALEZA DEL CALENDARIO", "paragraphs": ["Este calendario reúne los términos asociados con la ruta seleccionada y muestra, cuando el motor dispone de fechas suficientes, un vencimiento preliminar. No sustituye el cómputo jurídico final: los días hábiles automáticos excluyen sábados y domingos, pero el motor no descuenta festivos nacionales o territoriales y tampoco puede inferir por sí solo una recepción defectuosa, suspensión, prórroga válida o régimen sectorial especial."]},
        {"heading": "I. HITOS Y TÉRMINOS", "table": _deadline_rows(a, c, selected)},
        {"heading": "II. REGLAS DE USO", "numbered": [
            "Confirmar la fecha exacta de compra, entrega, conocimiento, reclamación, retracto, revocación o recepción que active cada término.",
            "Comprobar festivos y reglas especiales antes de afirmar vencimiento o incumplimiento.",
            "No convertir un vencimiento preliminar en aceptación automática de todas las pretensiones sin verificar el efecto jurídico específico.",
            "Actualizar el calendario cuando exista respuesta, nueva entrega, devolución, reparación, cargo posterior o actuación de autoridad.",
            "Conservar la versión anterior para que la modificación del calendario sea auditable.",
        ]},
    ]


_BUILDERS: dict[str, Callable[[dict, dict], list[dict]]] = {
    "warranty_claim": _warranty_sections,
    "withdrawal_notice": _withdrawal_sections,
    "payment_reversal_request": _reversal_sections,
    "recurring_debit_revocation": _periodic_sections,
    "ecommerce_non_delivery_termination": _non_delivery_sections,
}


def _externalize(spec: dict, client_sections: list[dict]) -> dict:
    rewritten = deepcopy(spec)
    old_sections = list(rewritten.get("sections") or [])
    old_controls = [
        deepcopy(section)
        for section in old_sections
        if isinstance(section, dict)
        and (section.get("_type") == "control" or "control de uso" in str(section.get("heading") or "").casefold())
    ]
    internal = list(deepcopy(rewritten.get("internal_review_sections") or []))
    internal.extend(old_controls)
    internal.append({
        "heading": "CONTROL JURÍDICO CO-CD-003",
        "_type": "control",
        "text": (
            "Verificar relación de consumo; régimen sectorial especial; mecanismo seleccionado; identidad y legitimación; "
            "fechas de compra, entrega y recepción; causal; términos y festivos; restituciones; inexistencia de doble recuperación; "
            "y coherencia entre reclamación, evidencia y calendario. Fuentes mínimas: Constitución art. 78; Ley 1480 de 2011; "
            "Decreto 735 de 2013 / Decreto 1074 de 2015; Decreto 587 de 2016; Ley 2439 de 2024; Sentencia C-192 de 2026. "
            "Aprobación jurídica y QA pendientes sobre esta revisión."
        ),
    })
    sections = deepcopy(client_sections)
    if sections:
        sections[0]["_suppress_default_control"] = True
    rewritten["sections"] = sections
    rewritten["internal_review_sections"] = internal
    rewritten["internal_controls_externalized"] = True
    rewritten["document_standard"] = "M33.0"
    rewritten["legal_approval"] = "pending"
    rewritten["qa_approval"] = "pending"
    rewritten["released"] = False
    rewritten["title"] = CLIENT_TITLES.get(str(rewritten.get("kind")), rewritten.get("title"))
    rewritten["subtitle"] = CLIENT_SUBTITLES.get(str(rewritten.get("kind")), "Protección al consumidor · documento sujeto a verificación")
    return rewritten


def finalize_consumer_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Recompone CO-CD-003 sin alterar selección ni compuertas rojas."""
    if (result or {}).get("risk") == "red":
        return specs

    selected = _selected_kind(specs)
    if selected is None:
        # Si la fuente histórica no produjo exactamente una ruta sustantiva, se
        # conserva el paquete para que la inconsistencia sea visible y revisable.
        return specs

    finalized: list[dict] = []
    for spec in specs:
        kind = spec.get("kind")
        if kind == "consumer_mechanism_diagnosis":
            finalized.append(_externalize(spec, _diagnosis_sections(answers, result, selected)))
        elif kind == selected and kind in _BUILDERS:
            finalized.append(_externalize(spec, _BUILDERS[kind](answers, result)))
        elif kind == "consumer_evidence_matrix":
            finalized.append(_externalize(spec, _evidence_sections(answers, result, selected)))
        elif kind == "consumer_deadline_calendar":
            finalized.append(_externalize(spec, _calendar_sections(answers, result, selected)))
        else:
            finalized.append(spec)
    return finalized
