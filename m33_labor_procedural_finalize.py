from __future__ import annotations

"""Cierre jurídico y probatorio de CO-LA-001 sobre la composición procedimental M33.0.

La capa elimina del instrumento visible matrices heredadas que no correspondan a las
variables usadas por el cálculo vigente. No modifica el motor matemático: reconstruye
la traza documental exclusivamente desde ``answers`` y ``result.calculation`` para que
el informe, la reclamación y el anexo compartan una única verdad reproducible.
"""

from copy import deepcopy
from typing import Any

from premium_document_engine import format_cop, format_date_es


_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos", 500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"}


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _value(value: Any, fallback: str = "No confirmado en esta revisión") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _money(value: Any) -> str:
    try:
        return format_cop(float(value or 0), include_words=False)
    except Exception:
        return "Valor no determinado"


def _date(value: Any) -> str:
    if not value:
        return "Fecha no confirmada"
    try:
        return format_date_es(str(value))
    except Exception:
        return str(value)


def _under_thousand(number: int) -> str:
    if number < 30:
        return _UNITS[number]
    if number < 100:
        tens = (number // 10) * 10
        remainder = number % 10
        return _TENS[tens] + (f" y {_UNITS[remainder]}" if remainder else "")
    if number in _HUNDREDS:
        return _HUNDREDS[number]
    hundreds = (number // 100) * 100
    remainder = number % 100
    prefix = "ciento" if hundreds == 100 else _HUNDREDS[hundreds]
    return prefix + (f" {_under_thousand(remainder)}" if remainder else "")


def _number_words(number: int) -> str:
    if number < 1000:
        return _under_thousand(number)
    if number < 1_000_000:
        thousands, remainder = divmod(number, 1000)
        prefix = "mil" if thousands == 1 else f"{_number_words(thousands)} mil"
        return prefix + (f" {_number_words(remainder)}" if remainder else "")
    millions, remainder = divmod(number, 1_000_000)
    prefix = "un millón" if millions == 1 else f"{_number_words(millions)} millones"
    return prefix + (f" {_number_words(remainder)}" if remainder else "")


def _money_words(value: Any) -> str:
    try:
        number = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return _money(value)
    words = _number_words(number)
    if number >= 1_000_000 and number % 1_000_000 == 0:
        words += " de"
    return f"{_money(number)} ({words} pesos moneda corriente)"


def _existing(section_list: list[dict], kind: str) -> dict | None:
    return next((deepcopy(section) for section in section_list if section.get("_type") == kind), None)


def _labor_control() -> dict:
    return {
        "heading": "CONTROL DE USO, FUENTES Y REVISIÓN",
        "_type": "control",
        "text": (
            "Documento candidato interno CO-LA-001. El cálculo es una estimación reproducible construida con los datos confirmados en esta revisión; "
            "no constituye sentencia, confesión del empleador ni liquidación oficial. Antes de liberarlo deben cotejarse contrato, nómina, pagos, vacaciones, "
            "cesantías, terminación, deducciones, seguridad social y cualquier protección especial. La aprobación jurídica y QA deben recaer sobre la misma revisión y hash."
        ),
        "bullets": [
            "Fuente jurídica de control: Código Sustantivo del Trabajo, artículos 64, 186, 249, 306, 488 y 489, según el concepto y los hechos realmente acreditados.",
            "Fuente jurídica de control: Ley 52 de 1975, artículo 1, sobre intereses anuales a las cesantías de trabajadores particulares, cuando resulte aplicable.",
            "Fuente jurídica de control: Ley 2466 de 2025, artículo 62, que modificó el artículo 488 del Código Sustantivo del Trabajo.",
            "Control profesional: la indemnización moratoria, estabilidad laboral reforzada, fueros, contrato realidad, sanciones, perjuicios e indexaciones no se agregan automáticamente sin análisis individual.",
        ],
    }


def _line_context(item: dict, calculation: dict) -> tuple[str, str]:
    key = str(item.get("key") or "").strip().casefold()
    if key == "cesantias":
        return _value(calculation.get("cesantias_days")), _money(calculation.get("cesantias_base"))
    if key == "intereses_cesantias":
        return _value(calculation.get("cesantias_days")), "Cesantías causadas en la misma revisión"
    if key == "prima":
        return _value(calculation.get("prima_days")), _money(calculation.get("prima_base"))
    if key == "vacaciones":
        return _value(calculation.get("vacation_pending_days")), _money(calculation.get("vacation_base"))
    if key == "indemnizacion":
        return _value(calculation.get("indemnity_days")), _money(calculation.get("indemnity_base"))
    return "Según motor", "Según motor"


def _calculation_sections(answers: dict, result: dict, prior_sections: list[dict]) -> list[dict]:
    c = _calc(result)
    line_items = list(c.get("line_items") or [])
    rows = [["Concepto", "Días / parámetro", "Base", "Bruto", "Pagado", "Saldo", "Fórmula"]]
    for item in line_items:
        days, base = _line_context(item, c)
        rows.append([
            _value(item.get("label") or item.get("key")),
            days,
            base,
            _money(item.get("gross")),
            _money(item.get("prior_paid")),
            _money(item.get("net")),
            _value(item.get("formula")),
        ])

    assumptions = [str(value) for value in c.get("assumptions") or []]
    exclusions = [str(value) for value in c.get("exclusions") or []]
    issues = [str(value.get("message") if isinstance(value, dict) else value) for value in c.get("issues") or []]
    if not assumptions:
        assumptions = ["No se registraron supuestos adicionales del motor; continúan sujetos a verificación los datos de entrada y pagos previos."]
    if not exclusions:
        exclusions = ["No se agregan sanciones, perjuicios, indexaciones ni conceptos cuya procedencia no haya sido determinada por el motor vigente."]

    sections: list[dict] = [
        {
            "heading": "1. ALCANCE, FECHA DE CORTE Y NATURALEZA DEL INFORME",
            "paragraphs": [
                f"Este informe presenta la estimación de acreencias laborales construida con la información disponible hasta {_date(answers.get('end_date'))}. La cifra se obtiene del motor determinístico vigente y se conserva concepto por concepto para que pueda ser reproducida, discutida y corregida sin alterar silenciosamente una revisión anterior.",
                "La estimación no constituye sentencia, confesión, reconocimiento unilateral de deuda ni liquidación oficial. Su función es identificar la cifra que resulta de unos datos y supuestos determinados y mostrar exactamente qué soporte puede modificar cada línea.",
                "Cuando aparezca un pago, una fecha, un período de suspensión, una vacación disfrutada, un factor salarial o una causa de terminación diferente, deberá generarse una nueva revisión que conserve la anterior para comparación y trazabilidad.",
            ],
        },
        {
            "heading": "2. DATOS UTILIZADOS EN ESTA REVISIÓN",
            "table": [
                ["Variable", "Dato utilizado", "Control"],
                ["Persona trabajadora", _value(answers.get("employee_name") or answers.get("worker_name") or answers.get("name")), "Identidad por cotejar con documento"],
                ["Empleador", _value(answers.get("employer_name")), "Denominación por cotejar con contrato/certificado"],
                ["Fecha de ingreso", _date(answers.get("start_date")), "Debe coincidir con ejecución real y soportes"],
                ["Fecha de terminación o corte", _date(answers.get("end_date")), "Define períodos y exigibilidad"],
                ["Modalidad reportada", _value(answers.get("contract_type")), "Sujeta a contrato y realidad de ejecución"],
                ["Causa de terminación reportada", _value(answers.get("termination")), "Condiciona la línea indemnizatoria"],
                ["Salario mensual informado", _money_words(answers.get("monthly_salary")), "Base salarial por cotejar con nómina"],
                ["Auxilio de transporte informado", _money(answers.get("transport_aid")), "Incidencia solo donde jurídicamente corresponda"],
            ],
        },
        {
            "heading": "3. LIQUIDACIÓN REPRODUCIBLE POR CONCEPTO",
            "table": rows if len(rows) > 1 else [["Concepto", "Estado"], ["Liquidación", "No existen líneas suficientes para cuantificar"]],
            "paragraphs": [
                "La columna 'Pagado' refleja únicamente valores que hayan sido incorporados al motor como pagos previos. Un comprobante posterior debe imputarse al concepto y período que corresponda antes de disminuir el saldo.",
                "La inclusión de una línea indemnizatoria depende de la causa de terminación informada y no reemplaza el análisis de hechos, modalidad contractual, estabilidad reforzada, autorización previa o controversias sobre la terminación.",
            ],
        },
        {
            "heading": "4. RECONCILIACIÓN DEL RESULTADO",
            "table": [
                ["Control", "Valor"],
                ["Total bruto calculado", _money(c.get("gross_total"))],
                ["Pagos previos imputados", _money(c.get("prior_paid_total"))],
                ["Saldo neto preliminar", _money_words(c.get("total"))],
                ["Ecuación de cierre", f"{_money(c.get('gross_total'))} - {_money(c.get('prior_paid_total'))} = {_money(c.get('total'))}"],
            ],
            "paragraphs": [
                "El saldo neto solo puede disminuir mediante pagos, compensaciones o deducciones jurídicamente procedentes y suficientemente individualizadas. Un valor global no explicado no debe imputarse de forma automática a todas las acreencias.",
                "Si la liquidación del empleador arroja un resultado distinto, la diferencia debe llevarse a una variable, período, base, fórmula, pago o deducción concreta. La comparación debe evitar tanto el doble cobro como la renuncia implícita a conceptos no explicados.",
            ],
        },
        {
            "heading": "5. BASES, PERÍODOS Y CONTROLES DEL MOTOR",
            "table": [
                ["Variable", "Valor de esta revisión"],
                ["Versión del motor", _value(c.get("engine_version"))],
                ["Días de vínculo", _value(c.get("link_days"))],
                ["Días computados para cesantías", _value(c.get("cesantias_days"))],
                ["Días computados para prima", _value(c.get("prima_days"))],
                ["Días computados para vacaciones", _value(c.get("vacation_pending_days"))],
                ["Días indemnizatorios modelados", _value(c.get("indemnity_days"))],
                ["Base de cesantías", _money(c.get("cesantias_base"))],
                ["Base de prima", _money(c.get("prima_base"))],
                ["Base de vacaciones", _money(c.get("vacation_base"))],
                ["Base de indemnización", _money(c.get("indemnity_base"))],
            ],
        },
        {
            "heading": "6. SUPUESTOS, EXCLUSIONES Y PUNTOS DE REVISIÓN",
            "paragraphs": ["Estos elementos delimitan el alcance matemático de la cifra. No deben ocultarse ni convertirse en hechos probados por el solo hecho de aparecer en el informe."],
            "bullets": [f"Supuesto: {value}" for value in assumptions] + [f"Exclusión: {value}" for value in exclusions] + [f"Alerta: {value}" for value in issues],
        },
        {
            "heading": "7. SOPORTES QUE DEBEN COTEJARSE ANTES DE CERRAR LA CIFRA",
            "numbered": [
                "Contrato de trabajo, otrosíes, anexos salariales y constancia de la fecha real de inicio.",
                "Desprendibles de nómina y comprobantes bancarios del período relevante.",
                "Soportes de prima, cesantías e intereses a las cesantías ya pagados o consignados.",
                "Registro de vacaciones disfrutadas, compensadas, anticipadas o pendientes.",
                "Comunicación de terminación, causa invocada y soportes asociados.",
                "Liquidación elaborada por el empleador y comprobante de cualquier pago final.",
                "Soportes de descuentos, préstamos, anticipos o compensaciones que se pretendan imputar.",
                "PILA y demás evidencia de seguridad social cuando sea pertinente para el caso.",
            ],
        },
        {
            "heading": "ANEXO No. 1 — TRAZA REPRODUCIBLE DE ESTA LIQUIDACIÓN",
            "_type": "annex",
            "page_break_before": True,
            "heading_align": "center",
            "paragraphs": [
                "Este anexo no reutiliza matrices históricas vacías. Reproduce exclusivamente las variables y resultados de la misma revisión que sustenta el cuerpo del informe, de modo que no existan dos capas contradictorias de información.",
            ],
            "table": [
                ["Control de traza", "Valor"],
                ["Persona trabajadora", _value(answers.get("employee_name") or answers.get("worker_name") or answers.get("name"))],
                ["Período modelado", f"{_date(answers.get('start_date'))} a {_date(answers.get('end_date'))}"],
                ["Salario informado", _money(answers.get("monthly_salary"))],
                ["Días de vínculo", _value(c.get("link_days"))],
                ["Total bruto", _money(c.get("gross_total"))],
                ["Pagos previos", _money(c.get("prior_paid_total"))],
                ["Saldo neto", _money(c.get("total"))],
                ["Número de líneas calculadas", str(len(line_items))],
            ],
        },
    ]
    sections.append(_labor_control())
    return sections


def _claim_sections(answers: dict, result: dict, prior_sections: list[dict]) -> list[dict]:
    c = _calc(result)
    name = _value(answers.get("employee_name") or answers.get("worker_name") or answers.get("name"), "Persona trabajadora por identificar")
    employer = _value(answers.get("employer_name"), "Empleador por identificar")
    signature = _existing(prior_sections, "signature") or {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [{"label": "PERSONA TRABAJADORA", "name": name, "id": _value(answers.get("employee_id") or answers.get("worker_id"), "")}],
    }
    rows = [["Concepto", "Saldo preliminar reclamado para cotejo"]]
    for item in c.get("line_items") or []:
        rows.append([_value(item.get("label") or item.get("key")), _money(item.get("net"))])
    rows.append(["TOTAL NETO PRELIMINAR", _money(c.get("total"))])

    requests = [
        "Remitir una liquidación definitiva discriminada por concepto, período, base, días, fórmula, pagos previos, deducciones y saldo, de manera que pueda compararse con la estimación adjunta.",
        "Explicar de forma concreta cada diferencia frente al informe adjunto, identificando el hecho, documento, período, base, fórmula, pago o deducción que la produce.",
        "Pagar oportunamente los valores que sean reconocidos como ciertos y debidos, aun cuando subsista controversia sobre otros conceptos, e identificar fecha, medio y comprobante de cada pago.",
        "Entregar los documentos de la relación laboral que se encuentren bajo custodia del empleador y sean necesarios para verificar la liquidación, dentro de los límites de protección de datos y reserva aplicables.",
        "Informar cualquier pago anterior, período de vacaciones, suspensión, licencia no remunerada, variación salarial, descuento, préstamo o compensación que deba incorporarse a una nueva revisión.",
        "Aportar la comunicación de terminación y los documentos que sustenten la causa reportada, sin perjuicio de la valoración jurídica que corresponda sobre sus efectos.",
        "Abstenerse de efectuar descuentos no autorizados por la ley, una decisión competente o una autorización válida y suficientemente determinada cuando esta sea necesaria.",
        "Expedir o entregar las certificaciones laborales y soportes de seguridad social que legalmente correspondan al cierre de la relación.",
        "Preservar los registros de nómina, pagos, vacaciones, terminación y comunicaciones relevantes mientras exista una controversia razonablemente previsible sobre estos conceptos.",
        "Remitir respuesta de fondo por un medio verificable, identificando el responsable, la fecha y los anexos en que se apoya la posición del empleador.",
    ]

    sections: list[dict] = [
        {
            "heading": "ASUNTO, DESTINATARIO Y ALCANCE DE LA RECLAMACIÓN",
            "paragraphs": [
                f"{name} formula reclamación directa frente a {employer} respecto de acreencias derivadas de la relación laboral reportada entre {_date(answers.get('start_date'))} y {_date(answers.get('end_date'))}. Se adjunta una estimación reproducible cuyo saldo neto preliminar asciende a {_money_words(c.get('total'))}.",
                "La comunicación busca obtener una liquidación empresarial completa, confrontar soportes y lograr el pago de los valores que resulten debidos. La cifra adjunta no se presenta como obligación judicialmente declarada ni impide corregir la estimación cuando aparezca evidencia nueva.",
            ],
        },
        {
            "heading": "I. HECHOS RELEVANTES INFORMADOS",
            "numbered": [
                f"La persona trabajadora se identifica como {name}.",
                f"El empleador reportado es {employer}.",
                f"La relación se informa entre {_date(answers.get('start_date'))} y {_date(answers.get('end_date'))}.",
                f"La modalidad reportada es {_value(answers.get('contract_type'))}.",
                f"La causa de terminación informada es {_value(answers.get('termination'))}.",
                f"El salario mensual informado para la estimación es {_money_words(answers.get('monthly_salary'))}.",
                f"Con los datos y pagos previos incorporados al motor, el saldo neto preliminar es {_money(c.get('total'))}.",
                "La persona reclamante se reserva el derecho de ampliar, reducir o corregir la cuantía cuando la documentación solicitada revele datos diferentes, evitando duplicar valores ya pagados.",
            ],
        },
        {
            "heading": "II. ACREENCIAS IDENTIFICADAS PARA COTEJO",
            "table": rows,
            "paragraphs": [
                "Cada concepto se reclama de manera individualizable para efectos de verificación. La procedencia y cuantía definitiva dependen de las fechas, bases, pagos, causa de terminación y demás hechos que resulten acreditados.",
            ],
        },
        {
            "heading": "III. PRESCRIPCIÓN, RECEPCIÓN Y DETERMINACIÓN DE LOS DERECHOS",
            "paragraphs": [
                "Como regla general, el artículo 488 del Código Sustantivo del Trabajo dispone un término de prescripción de tres (3) años contado desde que la respectiva obligación se hace exigible, sin perjuicio de prescripciones especiales aplicables a determinados asuntos.",
                "El artículo 489 del mismo Código prevé que el simple reclamo escrito de la persona trabajadora, recibido por el empleador y referido a un derecho debidamente determinado, interrumpe la prescripción por una sola vez y hace que el término correspondiente vuelva a contarse desde el reclamo. Por ello, esta actuación debe conservar prueba verificable de contenido, fecha de envío y, especialmente, recepción.",
                "La sola preparación o envío de este documento no permite afirmar que el efecto interruptivo se produjo. Su análisis exige acreditar la recepción y relacionar el reclamo con cada derecho suficientemente determinado.",
            ],
        },
        {"heading": "IV. SOLICITUDES", "numbered": requests},
        {
            "heading": "V. DOCUMENTOS SOLICITADOS PARA RECONCILIAR LA LIQUIDACIÓN",
            "numbered": [
                "Contrato de trabajo completo, otrosíes, anexos y documentos salariales aplicables.",
                "Desprendibles de nómina y comprobantes de pago durante los períodos discutidos.",
                "Soportes de prima, cesantías, intereses a las cesantías y vacaciones pagadas, consignadas o disfrutadas.",
                "Certificación de vacaciones disfrutadas, compensadas, anticipadas o pendientes.",
                "Comunicación de terminación y documentos invocados como fundamento de la decisión.",
                "Liquidación definitiva preparada por el empleador, incluyendo bases, fórmulas y deducciones.",
                "Soportes de préstamos, anticipos, descuentos, compensaciones o retenciones aplicadas al cierre.",
                "Certificación laboral y soportes de seguridad social que correspondan a la relación y al cierre.",
            ],
        },
        {
            "heading": "VI. RADICACIÓN, EVIDENCIA Y TRAZABILIDAD",
            "paragraphs": [
                "La persona reclamante conservará una copia exacta de la versión radicada y de todos sus anexos. La constancia de recepción deberá permitir asociar razonablemente destinatario, fecha, contenido y canal utilizado.",
                "Las respuestas, pagos y documentos posteriores se incorporarán como eventos separados. No se sobrescribirá la versión radicada ni se modificará retrospectivamente la cuantía que fue objeto de esta reclamación; cualquier ajuste se documentará en una nueva revisión.",
            ],
        },
        {
            "heading": "VII. RESERVA DE DERECHOS Y EVENTUAL ARREGLO",
            "paragraphs": [
                "La reclamación no constituye aceptación de una liquidación unilateral, novación, transacción, conciliación o paz y salvo general. Tampoco pretende duplicar conceptos que se acrediten como efectivamente pagados.",
                "El pago de valores no controvertidos puede realizarse sin condicionar su recepción a la renuncia de otros derechos. Si existe una diferencia susceptible de arreglo, las partes podrán explorar una conciliación o transacción dentro de los límites de disponibilidad de los derechos y con identificación suficiente de los conceptos discutidos y las concesiones que correspondan.",
            ],
        },
        signature,
        _labor_control(),
    ]
    return sections


def finalize_labor_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    if str((result or {}).get("risk") or "").casefold() == "red":
        return specs

    finalized = deepcopy(specs)
    for spec in finalized:
        kind = str(spec.get("kind") or "")
        prior_sections = list(spec.get("sections") or [])
        if kind == "calculation":
            spec["subtitle"] = f"Informe de cálculo verificable · corte al {_date(answers.get('end_date'))}"
            spec["sections"] = _calculation_sections(answers, result, prior_sections)
            spec["document_standard"] = "M33.0"
        elif kind == "claim":
            spec["subtitle"] = "Reclamación directa · cuantías individualizadas y trazabilidad de recepción"
            spec["sections"] = _claim_sections(answers, result, prior_sections)
            spec["document_standard"] = "M33.0"
    return finalized


__all__ = ["finalize_labor_specs"]
