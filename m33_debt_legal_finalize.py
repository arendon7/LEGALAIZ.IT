from __future__ import annotations

"""Finalización jurídica y de presentación para CO-CD-004.

La capa conserva la selección histórica por etapa y los cálculos del producto,
pero recompone la copia externa para separar diagnóstico, estado de cuenta,
cobranza, acuerdo, cronograma, pagaré, instrucciones, recibos y cierre. No altera
la compuerta de riesgo rojo ni convierte parámetros demostrativos en tasas legales.
"""

from copy import deepcopy
from typing import Any, Callable

from premium_document_engine import format_cop, format_date_es


DEBT_KINDS = {
    "debt_diagnostic",
    "account_statement",
    "collection_evidence_matrix",
    "collection_letter",
    "payment_agreement",
    "payment_schedule",
    "promissory_note",
    "instruction_letter",
    "payment_receipt",
    "settlement_certificate",
}

CLIENT_TITLES = {
    "debt_diagnostic": "Diagnóstico jurídico de obligación y ruta de cobro",
    "account_statement": "Estado de cuenta reconciliado y liquidación de referencia",
    "collection_evidence_matrix": "Matriz probatoria y trazabilidad de cobranza",
    "collection_letter": "Requerimiento prejurídico de pago y propuesta de arreglo",
    "payment_agreement": "Acuerdo de pago",
    "payment_schedule": "Cronograma de pagos e imputación",
    "promissory_note": "Pagaré",
    "instruction_letter": "Carta de instrucciones para diligenciamiento de pagaré",
    "payment_receipt": "Recibo de pago y actualización de saldo",
    "settlement_certificate": "Paz y salvo o constancia de cierre",
}

CLIENT_SUBTITLES = {
    "debt_diagnostic": "Origen, exigibilidad, saldo, intereses, títulos y riesgos del expediente",
    "account_statement": "Reconstrucción económica reproducible · capital, movimientos y conceptos accesorios",
    "collection_evidence_matrix": "Trazabilidad del origen, pagos, comunicaciones, títulos y soportes",
    "collection_letter": "Cobranza prejurídica respetuosa · saldo sujeto a contradicción y conciliación",
    "payment_agreement": "Saldo conciliado, pagos, intereses, incumplimiento, garantías y cierre",
    "payment_schedule": "Cuotas y movimientos sujetos a reconciliación con el acuerdo y los comprobantes",
    "promissory_note": "Título valor complementario · sujeto a requisitos, saldo real y control de diligenciamiento",
    "instruction_letter": "Autorización restrictiva para espacios permitidos · sin ampliación unilateral del crédito",
    "payment_receipt": "Imputación verificable del pago y actualización del saldo",
    "settlement_certificate": "Extinción limitada a la obligación identificada y condicionada a saldo cero",
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


def _money_words(value: Any) -> str:
    try:
        return format_cop(float(value or 0), include_words=True)
    except Exception:
        return "Valor por verificar"


def _date(value: Any) -> str:
    if not value:
        return "Por verificar"
    try:
        return format_date_es(str(value))
    except Exception:
        return str(value)


def _pct(value: Any) -> str:
    if value in (None, ""):
        return "Por verificar"
    try:
        number = float(value)
        text = f"{number:.4f}".rstrip("0").rstrip(".")
        return f"{text} %"
    except Exception:
        return str(value)


def _demo_interest_parameter(c: dict) -> bool:
    source = str(c.get("interest_resolution") or "").casefold()
    return any(token in source for token in ("demostr", "prueba", "test", "revalidar en producción"))


def _reconciliation_ok(c: dict) -> bool:
    return bool(c.get("balance_reconciled")) and bool(c.get("agreement_reconciled", True))


def _agreement_amount(c: dict) -> Any:
    return c.get("agreement_total") if c.get("agreement_total") not in (None, "") else c.get("reported_balance")


def _identity_rows(a: dict) -> list[list[str]]:
    return [
        ["Elemento", "Información del expediente"],
        ["Parte acreedora", _value(a.get("creditor_name") or a.get("creditor"))],
        ["Identificación acreedora", _value(a.get("creditor_id"))],
        ["Parte deudora", _value(a.get("debtor_name") or a.get("debtor"))],
        ["Identificación deudora", _value(a.get("debtor_id"))],
        ["Referencia", _value(a.get("document_reference") or a.get("reference"))],
        ["Fecha del documento causal", _date(a.get("document_date"))],
        ["Vencimiento informado", _date(a.get("due_date"))],
        ["Etapa", _value(a.get("package_stage"))],
    ]


def _causal_rows(a: dict) -> list[list[str]]:
    return [
        ["Control", "Dato o estado"],
        ["Naturaleza de la obligación", _value(a.get("obligation_type"))],
        ["Documento principal", _value(a.get("source_document_type"))],
        ["Origen o descripción", _value(a.get("origin_description"))],
        ["Estado de exigibilidad", _value(a.get("obligation_status"))],
        ["Obligación expresa, clara y exigible", _value(a.get("express_clear_enforceable"))],
        ["Firma o aceptación atribuida al deudor", _value(a.get("debtor_signature_status"))],
        ["Original o integridad", _value(a.get("original_integrity_status"))],
        ["Factura/RADIAN", f"{_value(a.get('invoice_acceptance_status'), 'No informado')} / {_value(a.get('radian_status'), 'No informado')}"],
        ["Cesión, endoso o factoring", _value(a.get("assignment_factoring"), "No informado")],
    ]


def _economic_rows(c: dict) -> list[list[str]]:
    adjustment = c.get("other_charges")
    return [
        ["Concepto", "Valor"],
        ["Capital original", _money(c.get("principal"))],
        ["Pagos, abonos o créditos reconocidos", _money(c.get("partial_payments_total"))],
        ["Capital pendiente antes de otros movimientos", _money(c.get("expected_principal_balance"))],
        ["Ajustes netos, notas crédito u otros movimientos", _money(adjustment)],
        ["Saldo explicado", _money(c.get("explained_balance"))],
        ["Saldo informado", _money(c.get("reported_balance"))],
        ["Diferencia de conciliación", _money(c.get("balance_difference"))],
        ["Conciliación del saldo", "Conciliado preliminarmente" if c.get("balance_reconciled") else "No conciliado; no formalizar"],
    ]


def _interest_rows(a: dict, c: dict) -> list[list[str]]:
    maximum = "Revalidar con certificación oficial aplicable al período y modalidad"
    if not _demo_interest_parameter(c) and c.get("maximum_reference_ea") not in (None, "", 0, 0.0):
        maximum = f"{_pct(c.get('maximum_reference_ea'))} E.A. · dato paramétrico sujeto a revalidación"
    return [
        ["Variable", "Información"],
        ["Pacto de intereses", _value(a.get("interest_agreed"))],
        ["Clase o modalidad", _value(c.get("interest_modality") or a.get("interest_type"))],
        ["Tasa informada", f"{_pct(a.get('interest_rate') or c.get('interest_rate_input'))} {_value(a.get('interest_period') or c.get('interest_period'), '')}".strip()],
        ["Equivalente efectivo anual", f"{_pct(c.get('effective_annual_rate'))} E.A."],
        ["Vigencia del parámetro", f"{_date(c.get('interest_valid_from'))} a {_date(c.get('interest_valid_to'))}"],
        ["Límite aplicable", maximum],
        ["Fuente paramétrica", "Parámetro demostrativo: no utilizar como certificación legal" if _demo_interest_parameter(c) else _value(c.get("interest_resolution"), "Fuente oficial por verificar")],
    ]


def _schedule_rows(c: dict) -> list[list[str]]:
    schedule = c.get("payment_schedule") if isinstance(c.get("payment_schedule"), dict) else {}
    rows = [["Cuota", "Fecha", "Valor", "Estado"]]
    for row in schedule.get("rows") or []:
        rows.append([
            _value(row.get("number")),
            _date(row.get("due_date")),
            _money(row.get("amount")),
            _value(row.get("status"), "Pendiente"),
        ])
    if len(rows) == 1:
        rows.append(["—", "Por verificar", "Por verificar", "Cronograma pendiente"])
    return rows


def _schedule_interest_warning(a: dict, c: dict) -> str:
    schedule = c.get("payment_schedule") if isinstance(c.get("payment_schedule"), dict) else {}
    schedule_total = schedule.get("total")
    agreement_total = _agreement_amount(c)
    if _yes(a.get("interest_agreed")) and schedule_total not in (None, "") and agreement_total not in (None, ""):
        try:
            if abs(float(schedule_total) - float(agreement_total)) < 0.01:
                return (
                    "El cronograma reproduce exactamente el valor base del acuerdo y, al mismo tiempo, el expediente informa un pacto de intereses. "
                    "Con los datos actuales no puede asumirse que las cuotas ya incorporan intereses. Antes de firma debe definirse expresamente si el plan corresponde a capital puro, cuota fija con interés incluido, intereses pagaderos por separado u otra metodología, y debe generarse una tabla de amortización que reconcilie capital, interés y saldo período por período."
                )
        except Exception:
            pass
    return (
        "La composición de cada cuota debe reconciliarse con el acuerdo. Si existen intereses, cada movimiento debe distinguir capital, interés causado y cualquier concepto accesorio procedente; el total del cronograma no puede utilizarse como prueba de una tabla de amortización si esa composición no está documentada."
    )


def _legal_basis() -> list[str]:
    return [
        "Código de Comercio, artículos 621, 622 y 709 a 711, sobre requisitos de los títulos valores, espacios en blanco y pagaré.",
        "Código de Comercio, artículos 884 y 886, junto con el Decreto 1454 de 1989, para intereses mercantiles y tratamiento de intereses pendientes.",
        "Código Civil, artículos 1687 y 1693 sobre novación, y artículo 1708 sobre la ampliación del plazo y sus efectos frente a ciertas garantías de terceros.",
        "Código General del Proceso, artículo 422, respecto de obligaciones expresas, claras y exigibles que puedan servir de fundamento a ejecución.",
        "Ley 2300 de 2023 únicamente cuando la gestión y el destinatario se encuentren dentro de su ámbito de aplicación; no se presume su aplicación a toda relación empresarial.",
        "Ley 1266 de 2008 y reglas especiales de hábeas data financiero únicamente si se pretende realizar o actualizar un reporte de información crediticia.",
    ]


def _agreement_signatures(a: dict) -> dict:
    return {
        "heading": "FIRMAS",
        "_type": "signature",
        "heading_align": "center",
        "parties": [
            {
                "label": "PARTE ACREEDORA",
                "name": _value(a.get("creditor_name") or a.get("creditor")),
                "id": _value(a.get("creditor_id"), ""),
                "role": "Firma por representante o apoderado con facultades verificadas",
            },
            {
                "label": "PARTE DEUDORA",
                "name": _value(a.get("debtor_name") or a.get("debtor")),
                "id": _value(a.get("debtor_id"), ""),
                "role": "Firma en calidad representativa; no crea obligación personal distinta salvo aceptación expresa",
            },
        ],
    }


def _single_signature(label: str, name: Any, identity: Any = None, role: str = "") -> dict:
    return {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [{
            "label": label,
            "name": _value(name),
            "id": _value(identity, "") if identity not in (None, "") else "",
            "role": role,
        }],
    }


def _diagnostic_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    issues = [str(x.get("message") if isinstance(x, dict) else x) for x in c.get("issues") or []]
    assumptions = [str(x) for x in c.get("assumptions") or []]
    return [
        {
            "heading": "OBJETO Y ALCANCE DEL DIAGNÓSTICO",
            "paragraphs": [
                "Este diagnóstico reconstruye la obligación antes de producir un requerimiento, acuerdo, pagaré o documento de cierre. Distingue el negocio causal, la legitimación de las partes, la exigibilidad, los movimientos económicos, los intereses, los títulos y las contingencias que pueden impedir una formalización ordinaria.",
                "Una cifra suministrada por una sola parte no se transforma por la generación documental en deuda reconocida, título ejecutivo, obligación vencida o saldo incontrovertible. Cada conclusión debe poder rastrearse a documentos, pagos y hechos verificables.",
            ],
            "_suppress_default_control": True,
        },
        {"heading": "I. IDENTIFICACIÓN DEL EXPEDIENTE", "table": _identity_rows(a)},
        {"heading": "II. NEGOCIO CAUSAL Y EXIGIBILIDAD", "table": _causal_rows(a)},
        {
            "heading": "III. RECONCILIACIÓN ECONÓMICA",
            "table": _economic_rows(c),
            "paragraphs": [
                "Los valores negativos dentro de ajustes u otros movimientos se interpretan como disminuciones del saldo —por ejemplo, notas crédito, descuentos o compensaciones acreditadas— y no como cargos. Todo valor positivo adicional requiere causa, pacto o soporte independiente.",
                "Si la diferencia de conciliación no es cero o el resultado no está reconciliado, el expediente no debe pasar a acuerdo, pagaré o carta de instrucciones como si existiera un saldo definitivo.",
            ],
        },
        {
            "heading": "IV. INTERESES Y LÍMITES",
            "table": _interest_rows(a, c),
            "paragraphs": [
                "La tasa aplicable depende del negocio, la modalidad y el período. Las certificaciones de la Superintendencia Financiera son dinámicas; un parámetro demostrativo o una tasa de un mes anterior no puede incorporarse como límite legal definitivo en un documento que se firme después.",
                "El expediente no incorpora anatocismo por defecto. Cualquier pretensión de intereses sobre intereses debe superar las condiciones legales aplicables y quedar calculada en forma separada, verificable y no duplicada.",
            ],
        },
        {
            "heading": "V. TÍTULOS, GARANTÍAS Y EFECTOS DE LA FORMALIZACIÓN",
            "numbered": [
                "Verificar que un pagaré contenga los requisitos generales y especiales del título y que cualquier espacio en blanco tenga instrucciones expresas, previas y trazables.",
                "No atribuir obligación personal a un representante legal por el solo hecho de firmar en nombre de la sociedad; una obligación personal, aval, fianza o garantía exige su propio fundamento y manifestación.",
                "No asumir que el acuerdo produce novación. La intención de novar debe ser expresa o resultar indudable; de lo contrario, la obligación anterior subsiste en lo compatible.",
                "Aunque una ampliación de plazo no constituya novación por sí sola, puede afectar la responsabilidad de fiadores o ciertas garantías de terceros si estos no consienten; la continuidad de garantías debe revisarse individualmente.",
                "La coexistencia de contrato, acuerdo y pagaré no autoriza cobro duplicado: todo pago sobre la obligación económica debe reflejarse en todos los instrumentos y estados relacionados.",
                "Un documento firmado puede tener consecuencias probatorias o ejecutivas si contiene obligaciones expresas, claras y exigibles; esa consecuencia no debe prometerse automáticamente en el borrador.",
            ],
        },
        {"heading": "VI. MARCO JURÍDICO DE REFERENCIA", "numbered": _legal_basis()},
        {
            "heading": "VII. CONTROVERSIAS Y BLOQUEOS",
            "table": [
                ["Control", "Estado"],
                ["Controversia sobre la obligación", _value(a.get("disputed"), "Por verificar")],
                ["Compensación alegada", _value(a.get("setoff_claimed"), "Por verificar")],
                ["Posible prescripción", _value(a.get("prescription_concern"), "Por verificar")],
                ["Proceso judicial activo", _value(a.get("judicial_process_active"), "Por verificar")],
                ["Insolvencia", _value(a.get("insolvency_active"), "Por verificar")],
                ["Embargo o medida", _value(a.get("embargo_or_measure"), "Por verificar")],
                ["Fraude/suplantación", _value(a.get("fraud_impersonation"), "Por verificar")],
                ["Capacidad o representación", _value(a.get("debtor_capacity_issue"), "Por verificar")],
            ],
            "bullets": issues + assumptions or ["No se registraron alertas automáticas adicionales; la validación documental sigue siendo obligatoria."],
        },
        {
            "heading": "VIII. RESULTADO Y SIGUIENTE PASO",
            "paragraphs": [
                "La ruta documental debe corresponder a la etapa real: cobro inicial, negociación, formalización, seguimiento de pagos o cierre. Cambiar de etapa exige conservar la revisión anterior y actualizar saldo, soportes, facultades, términos y riesgos.",
                "La formalización solo es responsable cuando el saldo está reconciliado, el negocio causal está identificado, las tasas y conceptos accesorios son verificables y no existe un bloqueo que requiera intervención especializada.",
            ],
        },
    ]


def _account_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "OBJETO DEL ESTADO DE CUENTA", "paragraphs": ["Este documento reconstruye el saldo a partir del capital, pagos, créditos, ajustes e intereses que puedan ser acreditados. No constituye por sí solo confesión de la contraparte ni sustituye los soportes del negocio causal."], "_suppress_default_control": True},
        {"heading": "I. IDENTIFICACIÓN", "table": _identity_rows(a)},
        {"heading": "II. RECONCILIACIÓN DEL SALDO", "table": _economic_rows(c)},
        {
            "heading": "III. ECUACIÓN DE CONTROL",
            "paragraphs": [
                f"Capital original {_money(c.get('principal'))} menos pagos o créditos {_money(c.get('partial_payments_total'))}, más ajustes netos {_money(c.get('other_charges'))}, produce un saldo explicado de {_money(c.get('explained_balance'))}. El saldo informado es {_money(c.get('reported_balance'))}.",
                "La ecuación es un control aritmético, no una conclusión sobre procedencia jurídica. Cada ajuste requiere clasificación y soporte; una nota crédito disminuye el saldo, mientras un cargo adicional solo aumenta la obligación si existe fundamento suficiente.",
            ],
        },
        {"heading": "IV. INTERESES", "table": _interest_rows(a, c), "paragraphs": ["La tabla registra la información disponible, pero no congela una certificación de tasa para períodos futuros. La liquidación real debe guardar la tasa oficial, modalidad, vigencia y fórmula empleadas para cada período."]},
        {
            "heading": "V. CONCEPTOS NO INCORPORADOS AUTOMÁTICAMENTE",
            "numbered": [
                "Honorarios o gastos internos sin pacto, causación y soporte suficientes.",
                "Cláusulas penales o sanciones no acreditadas.",
                "Intereses futuros no causados.",
                "Intereses sobre intereses que no satisfagan el régimen aplicable.",
                "Obligaciones de terceros o negocios diferentes al identificado.",
                "Valores ya pagados, compensados, condonados o cubiertos mediante nota crédito.",
            ],
        },
        {
            "heading": "VI. CIERRE DE CONCILIACIÓN",
            "paragraphs": [
                "Antes de utilizar este estado en un acuerdo o título, las partes deben poder identificar los movimientos que explican el saldo y controvertir cualquier concepto. Una corrección posterior debe generar una nueva revisión, no borrar el historial de la cifra anterior.",
                f"Estado actual de conciliación: {'conciliado preliminarmente' if c.get('balance_reconciled') else 'no conciliado; requiere revisión antes de formalizar'}.",
            ],
        },
    ]


def _evidence_sections(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "OBJETO DE LA MATRIZ", "paragraphs": ["La matriz vincula cada afirmación económica o jurídica con la evidencia que debe respaldarla. Su finalidad es impedir que el acuerdo, el pagaré o la cobranza se apoyen únicamente en una cifra trasladada entre documentos sin trazabilidad."], "_suppress_default_control": True},
        {"heading": "I. ORIGEN Y EXIGIBILIDAD", "table": [
            ["Hecho", "Soporte esperado", "Estado"],
            ["Negocio causal", "Contrato, orden, factura, acta, entrega o prestación", "Por verificar"],
            ["Identidad y facultades", "Certificados, documentos, poder o mandato", "Por verificar"],
            ["Aceptación o vinculación del deudor", "Firma, mensaje, recibido, conducta o título", "Por verificar"],
            ["Vencimiento", "Cláusula, factura, cronograma o requerimiento aplicable", "Por verificar"],
            ["Titularidad del crédito", "Original, endoso, cesión o cadena de transferencias", "Por verificar"],
        ]},
        {"heading": "II. MATRIZ ECONÓMICA", "table": [
            ["Componente", "Evidencia mínima", "Control"],
            ["Capital", "Documento de origen y prueba de entrega/desembolso/prestación", "Conciliar con estado"],
            ["Pagos", "Recibos, extractos, notas crédito y comprobantes", "Evitar doble cobro"],
            ["Intereses", "Pacto, tasa, modalidad, vigencia y certificación aplicable", "Liquidar por período"],
            ["Ajustes", "Nota crédito, compensación, descuento o cargo soportado", "Clasificar signo y causa"],
            ["Saldo", "Estado de cuenta reproducible", "Diferencia debe ser cero antes de formalizar"],
        ]},
        {"heading": "III. COBRANZA Y COMUNICACIONES", "table": [
            ["Control", "Evidencia"],
            ["Canal y destinatario", "Registro de contacto y legitimación"],
            ["Contenido enviado", "Copia íntegra del requerimiento o propuesta"],
            ["Recepción", "Radicado, acuse o trazabilidad técnica"],
            ["Objeciones", "Respuesta y soportes presentados por la contraparte"],
            ["Ley 2300 de 2023", "Verificar primero si el destinatario y la gestión están dentro de su ámbito de aplicación"],
        ]},
        {"heading": "IV. ACUERDO, PAGARÉ E INSTRUCCIONES", "table": [
            ["Documento", "Evidencia y control"],
            ["Acuerdo", "Versión firmada, facultades, saldo y cronograma aceptados"],
            ["Pagaré", "Original o soporte íntegro, firma, requisitos y saldo económico coincidente"],
            ["Espacios en blanco", "Carta de instrucciones previa, expresa y vinculada al título"],
            ["Garantías", "Documento específico, capacidad y consentimiento de cada garante"],
            ["Pagos posteriores", "Imputación reflejada simultáneamente en acuerdo, cronograma, recibos y título"],
        ]},
        {"heading": "V. CUSTODIA Y CIERRE", "numbered": [
            "Conservar originales y versiones sin edición; trabajar sobre copias identificadas.",
            "Registrar fecha, fuente, nombre de archivo y relación con el hecho acreditado.",
            "No eliminar evidencia desfavorable ni sustituir silenciosamente una revisión anterior.",
            "Al pago total, documentar saldo cero, cancelar o devolver el título cuando corresponda y detener cobros sobre la obligación extinguida.",
            "Si existe reporte crediticio, tratar su actualización bajo el régimen específico y conservar la evidencia separada.",
        ]},
    ]


def _collection_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    creditor = a.get("creditor_name") or a.get("creditor")
    debtor = a.get("debtor_name") or a.get("debtor")
    return [
        {"heading": "ASUNTO Y NATURALEZA DE LA COMUNICACIÓN", "paragraphs": [f"{_value(creditor, 'La parte acreedora')} informa a {_value(debtor, 'la parte destinataria')} el estado de una obligación que se encuentra en etapa prejurídica y propone verificar el saldo y explorar una solución de pago. Esta comunicación no es una demanda, mandamiento de pago, embargo, orden judicial ni anuncio de una medida ya decretada cuando esta no existe."], "_suppress_default_control": True},
        {"heading": "I. IDENTIFICACIÓN DE LA OBLIGACIÓN", "table": _identity_rows(a)},
        {"heading": "II. ESTADO ECONÓMICO SUJETO A CONTRADICCIÓN", "table": _economic_rows(c)},
        {
            "heading": "III. VERIFICACIÓN Y DERECHO DE CONTRADICCIÓN",
            "paragraphs": ["La parte destinataria puede informar y soportar pagos, notas crédito, compensaciones, desacuerdos sobre entrega o prestación, falta de exigibilidad, cesiones no reconocidas, discrepancias en intereses o cualquier hecho que modifique el saldo. La respuesta debe incorporarse al expediente antes de transformar la cifra en un reconocimiento contractual."],
            "numbered": [
                "Identificar el concepto objetado y, cuando sea posible, el valor asociado.",
                "Aportar o indicar el soporte disponible.",
                "Solicitar el estado de cuenta o documento causal faltante cuando sea necesario.",
                "Distinguir una objeción al saldo de una propuesta de pago sobre la parte no controvertida.",
            ],
        },
        {
            "heading": "IV. PROPUESTA DE SOLUCIÓN",
            "numbered": [
                "Conciliar primero el saldo real y las fechas de exigibilidad.",
                "Definir, si existe disposición de arreglo, una suma y un cronograma que puedan cumplirse.",
                "Documentar expresamente cualquier quita, condonación, interés, gasto o condición de conservación de beneficios.",
                "No atribuir obligación personal al representante de una sociedad ni garantías que no hayan sido asumidas de forma independiente.",
                "Expedir estado de cuenta y recibo después de cada pago y reflejarlo en cualquier título complementario.",
            ],
        },
        {
            "heading": "V. REGLAS DE COBRANZA Y PRIVACIDAD",
            "paragraphs": [
                "La gestión debe ser respetuosa, veraz y proporcional. No se revelará la obligación a referencias, familiares, compañeros, clientes u otros terceros ajenos al vínculo y no se utilizará lenguaje que haga pasar una gestión privada por una actuación judicial o administrativa.",
                "Cuando el destinatario y la gestión se encuentren dentro del ámbito de la Ley 2300 de 2023, deberán respetarse además los canales autorizados, horarios, periodicidad y restricciones de contacto allí previstas. Esa aplicación debe verificarse y no se presume para toda relación empresarial.",
            ],
        },
        {"heading": "VI. SOPORTES DISPONIBLES", "numbered": ["Documento causal y constancia de entrega o prestación.", "Estado de cuenta con movimientos.", "Comprobantes de pagos y créditos reconocidos.", "Pacto y cálculo de intereses, si se reclaman.", "Documentos de representación, cesión o titularidad cuando correspondan."]},
        _single_signature("PARTE ACREEDORA", creditor, a.get("creditor_id"), "Por representante o apoderado con facultades verificadas"),
    ]


def _agreement_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    amount = _agreement_amount(c)
    reconcile = _reconciliation_ok(c)
    warning = _schedule_interest_warning(a, c)
    sections = [
        {
            "heading": "CONSIDERACIONES",
            "numbered": [
                "Que las partes identifican una relación jurídica previa y reconocen que sus documentos causales, pagos, notas crédito y demás soportes deben conservarse y poder ser revisados.",
                f"Que el saldo de referencia para esta versión es {_money_words(amount)} y solo podrá tratarse como saldo conciliado si la reconciliación económica y sus soportes son confirmados por ambas partes.",
                "Que el presente instrumento regula una solución de pago y no pretende crear cobro duplicado entre el negocio causal, el acuerdo y cualquier título valor complementario.",
                "Que la firma de un representante de una persona jurídica se entiende realizada en esa calidad, salvo que exista una obligación personal independiente, expresa y jurídicamente válida.",
                "Que las partes conocen que un acuerdo escrito puede producir efectos probatorios y, si contiene obligaciones expresas, claras y exigibles, eventualmente consecuencias ejecutivas cuya valoración corresponde al caso concreto.",
                "Que la formalización y sus garantías requieren revisión profesional antes de firma por su impacto patrimonial.",
            ],
            "_suppress_default_control": True,
        },
    ]
    if not reconcile:
        sections.append({"heading": "BLOQUEO DE FORMALIZACIÓN", "paragraphs": ["El saldo o el valor del acuerdo no se encuentra reconciliado. Esta revisión no es apta para firma como reconocimiento de deuda ni para soportar un pagaré hasta corregir la diferencia y conservar la evidencia de esa conciliación."]})
    sections.extend([
        {"heading": "PRIMERA: PARTES, CAPACIDAD Y REPRESENTACIÓN", "_type": "clause", "paragraphs": [f"Son partes {_value(a.get('creditor_name') or a.get('creditor'))}, como PARTE ACREEDORA, y {_value(a.get('debtor_name') or a.get('debtor'))}, como PARTE DEUDORA. Cada firmante deberá acreditar su identidad, calidad y facultades. La representación de una sociedad no transforma al representante en deudor, avalista, fiador o codeudor por el solo hecho de suscribir el acuerdo en nombre de la entidad."]},
        {"heading": "SEGUNDA: NEGOCIO CAUSAL Y ALCANCE DEL RECONOCIMIENTO", "_type": "clause", "paragraphs": ["El acuerdo se relaciona exclusivamente con el negocio causal identificado en el expediente. La aceptación del saldo se limita a los conceptos expresamente conciliados; no comprende obligaciones de terceros, negocios diferentes, valores ya pagados ni conceptos accesorios que no hayan sido individualizados y soportados."]},
        {"heading": "TERCERA: SALDO BASE DEL ACUERDO", "_type": "clause", "paragraphs": [f"El valor base de esta revisión es {_money_words(amount)}. Su composición deberá corresponder al estado de cuenta anexo y a la ecuación de conciliación. Los ajustes negativos reducen el saldo; los cargos positivos solo lo incrementan cuando su causa y procedencia estén acreditadas."]},
        {"heading": "CUARTA: NO NOVACIÓN Y EFECTOS SOBRE GARANTÍAS", "_type": "clause", "paragraphs": ["La modificación de plazos, cuotas o forma de pago no constituye novación por sí sola. Las obligaciones previas subsisten en lo compatible salvo que las partes declaren inequívocamente un efecto novatorio. Si existen fiadores, prendas, hipotecas u otras garantías de terceros, cualquier ampliación del plazo o modificación relevante deberá revisarse con sus efectos legales y, cuando sea necesario, con el consentimiento expreso de quienes resulten afectados."]},
        {"heading": "QUINTA: CRONOGRAMA Y COMPOSICIÓN DE LAS CUOTAS", "_type": "clause", "paragraphs": ["Las fechas y valores aplicables serán únicamente los contenidos en el cronograma aceptado y firmado con esta revisión. Cada pago deberá permitir reconstruir saldo anterior, capital imputado, interés causado —si procede—, otros conceptos soportados y saldo posterior."], "table": _schedule_rows(c)},
        {"heading": "SEXTA: INTERESES REMUNERATORIOS Y MORATORIOS", "_type": "clause", "paragraphs": [f"El expediente informa como tasa pactada {_pct(a.get('interest_rate') or c.get('interest_rate_input'))} {_value(a.get('interest_period') or c.get('interest_period'), '')}. Su aplicación queda condicionada a la validez del pacto, la modalidad real del crédito, la vigencia de la certificación oficial aplicable y el límite legal correspondiente. El parámetro interno de referencia no sustituye la certificación de la Superintendencia Financiera. Los intereses moratorios solo se causarán sobre obligaciones vencidas y no pagadas y no se extenderán retroactivamente a capital que aún no era exigible.".strip(), warning]},
        {"heading": "SÉPTIMA: INTERESES SOBRE INTERESES", "_type": "clause", "paragraphs": ["No se pacta anatocismo automático. Cualquier interés sobre intereses vencidos deberá cumplir las condiciones legales aplicables, incluido el régimen del artículo 886 del Código de Comercio y su reglamentación, y constar en una liquidación separada. La simple denominación de una cuota como 'financiada' no autoriza a capitalizar intereses atrasados por fuera de esas reglas."]},
        {"heading": "OCTAVA: PAGOS, IMPUTACIÓN Y ABONOS ANTICIPADOS", "_type": "clause", "paragraphs": ["Todo pago se acreditará mediante recibo o soporte verificable. La imputación deberá identificar el concepto al que se aplica conforme al acuerdo y a la ley. Los abonos anticipados modificarán el saldo desde su fecha efectiva y, cuando alteren cuotas o plazo, originarán un cronograma revisado que conserve la versión anterior."]},
        {"heading": "NOVENA: INCUMPLIMIENTO Y OPORTUNIDAD DE SUBSANACIÓN", "_type": "clause", "paragraphs": ["El incumplimiento se determinará respecto de una obligación efectivamente vencida, identificando cuota, fecha, valor y pago recibido. Cuando el acuerdo contemple requerimiento u oportunidad de subsanación, estos deberán cumplirse y quedar acreditados antes de activar consecuencias adicionales."]},
        {"heading": "DÉCIMA: ACELERACIÓN", "_type": "clause", "paragraphs": ["La aceleración solo operará si fue pactada de manera suficientemente determinada y se acredita el evento que la activa. La fecha de vencimiento anticipado será la actuación real jurídicamente procedente, no una fecha retroactiva. La liquidación acelerada descontará todos los pagos y no incorporará intereses futuros no causados como si ya hubieran vencido."]},
        {"heading": "DÉCIMA PRIMERA: PAGARÉ Y CARTA DE INSTRUCCIONES", "_type": "clause", "paragraphs": ["Si se utiliza pagaré, será un instrumento complementario del mismo saldo económico. Los espacios en blanco solo podrán existir cuando estén autorizados mediante instrucciones previas y expresas. El título y las instrucciones no podrán utilizarse para alterar identidad, moneda, negocio causal, firma, pagos efectuados ni incorporar obligaciones ajenas."]},
        {"heading": "DÉCIMA SEGUNDA: GARANTÍAS", "_type": "clause", "paragraphs": ["Ninguna garantía personal o real se entiende creada por inferencia. El aval, fianza, codeuda, garantía mobiliaria, prenda, hipoteca u otra figura que se pretenda utilizar deberá reunir sus propios requisitos y manifestaciones. La firma representativa de una sociedad no se reinterpreta como garantía personal."]},
        {"heading": "DÉCIMA TERCERA: ESTADOS DE CUENTA, RECIBOS Y TRAZABILIDAD", "_type": "clause", "paragraphs": ["La PARTE ACREEDORA conservará un registro de los movimientos que permita explicar el saldo. Cada recibo indicará fecha, valor e imputación; toda corrección sustancial generará una nueva revisión. No se eliminarán pagos históricos ni se mantendrá un pagaré por un valor nominal que desconozca abonos efectivamente recibidos."]},
        {"heading": "DÉCIMA CUARTA: COBRANZA, DATOS Y REPORTES", "_type": "clause", "paragraphs": ["Las gestiones de cobro se realizarán mediante canales legítimos y de forma respetuosa. La información de personas naturales vinculadas a las partes se tratará solo en la medida necesaria y bajo el régimen aplicable. Cualquier reporte a operadores de información crediticia exige un análisis independiente de sus presupuestos; este acuerdo no constituye por sí mismo autorización suficiente para reportar o mantener información negativa."]},
        {"heading": "DÉCIMA QUINTA: SOLUCIÓN DE CONTROVERSIAS", "_type": "clause", "paragraphs": ["Las diferencias sobre saldo, imputación, interés, cumplimiento o interpretación deberán documentarse antes de iniciar una nueva actuación. Las partes podrán acudir a negociación directa, conciliación u otros mecanismos procedentes, sin que esta cláusula suprima acciones o defensas legalmente disponibles."]},
        {"heading": "DÉCIMA SEXTA: NOTIFICACIONES", "_type": "clause", "paragraphs": ["Las comunicaciones relacionadas con el acuerdo deberán enviarse a los canales válidamente informados por cada parte y conservar evidencia de envío y recepción. Las modificaciones de canal se registrarán sin borrar el dato anterior cuando sea necesario para la trazabilidad del expediente."]},
        {"heading": "DÉCIMA SÉPTIMA: MODIFICACIONES E INTEGRIDAD", "_type": "clause", "paragraphs": ["Toda modificación de saldo, plazo, tasa, cuota, garantía, aceleración o condonación deberá constar por escrito y vincularse con esta revisión. Ninguna modificación autoriza a reescribir retrospectivamente comprobantes, cronogramas o versiones firmadas."]},
        {"heading": "DÉCIMA OCTAVA: CIERRE Y CANCELACIÓN DE INSTRUMENTOS", "_type": "clause", "paragraphs": ["El pago total se acreditará mediante saldo cero y evidencia de los pagos. Cumplido lo anterior, se expedirá la constancia de cierre correspondiente y se cancelará, devolverá o inutilizará jurídicamente el pagaré cuando exista. El paz y salvo se limitará a las obligaciones expresamente individualizadas y no comprenderá negocios diferentes."]},
        {"heading": "ANEXO ECONÓMICO — CONTROL DE INTERESES", "_type": "annex", "page_break_before": True, "heading_align": "center", "table": _interest_rows(a, c), "paragraphs": [warning]},
        _agreement_signatures(a),
    ])
    return sections


def _schedule_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    schedule = c.get("payment_schedule") if isinstance(c.get("payment_schedule"), dict) else {}
    return [
        {"heading": "OBJETO DEL CRONOGRAMA", "paragraphs": ["El cronograma registra las cuotas vigentes del acuerdo y debe poder reconciliarse con el saldo, los recibos y cualquier pagaré relacionado. No sustituye una tabla de amortización cuando los datos no permiten separar capital e intereses."], "_suppress_default_control": True},
        {"heading": "I. RESUMEN", "table": [
            ["Variable", "Resultado"],
            ["Valor base del acuerdo", _money_words(_agreement_amount(c))],
            ["Número de cuotas", _value(c.get("installments") or a.get("installments"))],
            ["Primera cuota", _date(c.get("first_payment_date") or a.get("first_payment_date"))],
            ["Periodicidad", _value(c.get("frequency") or a.get("frequency"))],
            ["Total de cuotas registradas", _money(schedule.get("total"))],
            ["Conciliación matemática", "Sí" if schedule.get("reconciled") else "No"],
        ]},
        {"heading": "II. CRONOGRAMA VIGENTE", "table": _schedule_rows(c)},
        {"heading": "III. COMPOSICIÓN DE LAS CUOTAS", "paragraphs": [_schedule_interest_warning(a, c)]},
        {"heading": "IV. REGLAS DE IMPUTACIÓN Y ACTUALIZACIÓN", "numbered": [
            "Registrar cada pago con fecha efectiva, valor, comprobante y concepto.",
            "Distinguir capital, interés y otros conceptos soportados cuando existan.",
            "No eliminar movimientos anteriores ni alterar el estado histórico de una cuota ya pagada.",
            "Un abono anticipado deberá reflejarse desde su fecha y, si modifica el plan, originar una nueva revisión.",
            "Una aceleración deberá registrar evento, fecha real, saldo y soporte; no cambiar retroactivamente las fechas de las cuotas anteriores.",
            "El total de cuotas no se interpretará como monto final con intereses cuando el expediente no demuestre cómo fueron incorporados.",
        ]},
        {"heading": "V. CONTROL DE CIERRE", "paragraphs": ["El cronograma se cierra únicamente cuando todos los movimientos pueden reconciliarse con saldo cero o con la modificación posterior debidamente documentada. Un estado 'pagado' sin comprobante no sustituye la evidencia económica."]},
    ]


def _note_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    amount = _agreement_amount(c)
    debtor = a.get("debtor_name") or a.get("debtor")
    creditor = a.get("creditor_name") or a.get("creditor")
    blank_spaces = _yes(a.get("promissory_note_blank_spaces") or a.get("blanks_present"))
    return [
        {"heading": "PAGARÉ — DATOS ESENCIALES", "table": [
            ["Elemento", "Información"],
            ["Suscriptor", _value(debtor)],
            ["Identificación", _value(a.get("debtor_id"))],
            ["Beneficiario", _value(creditor)],
            ["Identificación", _value(a.get("creditor_id"))],
            ["Suma incorporada", _money_words(amount)],
            ["Orden", f"A la orden de {_value(creditor)}"],
            ["Forma de vencimiento", _value(a.get("maturity_form"))],
            ["Fecha de creación", _date(a.get("document_date"))],
            ["Espacios autorizados", "Sí; sujetos estrictamente a carta de instrucciones" if blank_spaces else "No informados"],
        ], "_suppress_default_control": True},
        {"heading": "PROMESA INCONDICIONAL DE PAGO", "paragraphs": [f"El SUSCRIPTOR promete pagar incondicionalmente a la orden de {_value(creditor)} la suma de {_money_words(amount)}, en la forma de vencimiento indicada en este título y con sujeción a los pagos parciales que reduzcan efectivamente el saldo. La coexistencia del pagaré con el acuerdo y el negocio causal no autoriza el recaudo duplicado de la misma obligación económica."]},
        {"heading": "PRIMERA: FORMA DE VENCIMIENTO", "_type": "clause", "paragraphs": ["Cuando el pagaré sea atendido mediante vencimientos ciertos y sucesivos, las fechas y valores deberán ser determinables a partir del título o de la información incorporada de manera jurídicamente válida. La aceleración, si existe, solo operará bajo el evento y procedimiento expresamente pactados y con la fecha real de su ejercicio."], "table": _schedule_rows(c)},
        {"heading": "SEGUNDA: INTERESES", "_type": "clause", "paragraphs": [f"Los intereses solo se causarán cuando exista pacto válido o regla legal aplicable. La tasa informada para el expediente es {_pct(a.get('interest_rate') or c.get('interest_rate_input'))} {_value(a.get('interest_period') or c.get('interest_period'), '')}, pero deberá revalidarse frente a la modalidad, período y límite vigente al momento correspondiente. El título no incorpora como tasa legal un parámetro demostrativo.".strip(), _schedule_interest_warning(a, c)]},
        {"heading": "TERCERA: PAGOS PARCIALES E IMPUTACIÓN", "_type": "clause", "paragraphs": ["Todo pago parcial disminuirá el saldo real y deberá constar en recibo, estado de cuenta o registro trazable. El tenedor no podrá exigir mediante el título valores ya pagados, condonados, compensados o reconocidos mediante notas crédito."]},
        {"heading": "CUARTA: INTERESES SOBRE INTERESES", "_type": "clause", "paragraphs": ["No se incorpora capitalización automática de intereses atrasados. Cualquier interés sobre intereses deberá satisfacer el régimen legal aplicable y constar en liquidación diferenciada; los intereses futuros no causados no se convierten en capital por el solo diligenciamiento del título."]},
        {"heading": "QUINTA: RELACIÓN CON EL NEGOCIO CAUSAL", "_type": "clause", "paragraphs": ["El pagaré se utiliza como título complementario de la obligación identificada. Entre las partes del negocio, sus pagos, créditos y modificaciones deberán conservar trazabilidad con el acuerdo y el estado de cuenta. Esta cláusula no elimina los efectos propios de la circulación del título ni sustituye el análisis jurídico que corresponda frente a terceros."]},
        {"heading": "SEXTA: ESPACIOS EN BLANCO", "_type": "clause", "paragraphs": ["Si el original conserva espacios en blanco, únicamente podrán diligenciarse los campos y bajo los eventos autorizados en la carta de instrucciones suscrita. No se autoriza cambiar identidad del suscriptor o beneficiario, moneda, firma, negocio causal, ni incorporar obligaciones diferentes o valores que desconozcan pagos realizados."] if blank_spaces else ["La versión destinada a firma deberá completarse íntegramente antes de suscripción. Si posteriormente se pretende utilizar espacios en blanco, deberá generarse y aceptarse una carta de instrucciones específica antes de la entrega del título."]},
        {"heading": "SÉPTIMA: CANCELACIÓN Y ENTREGA", "_type": "clause", "paragraphs": ["Una vez acreditado el pago total de la obligación incorporada, el tenedor deberá cancelar y devolver el título o dejar evidencia suficiente de su inutilización jurídica conforme al soporte utilizado, evitando que subsista en circulación como si representara una obligación pendiente."]},
        _single_signature("SUSCRIPTOR", debtor, a.get("debtor_id"), "Firma en nombre propio o en la calidad expresamente indicada; verificar representación si el suscriptor es persona jurídica"),
    ]


def _instruction_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    debtor = a.get("debtor_name") or a.get("debtor")
    creditor = a.get("creditor_name") or a.get("creditor")
    return [
        {"heading": "OBJETO Y VINCULACIÓN CON EL PAGARÉ", "paragraphs": [f"Estas instrucciones se otorgan exclusivamente para el pagaré suscrito por {_value(debtor)} a favor de {_value(creditor)} dentro del negocio identificado en el expediente. Solo son aplicables si el original fue entregado con alguno de los espacios expresamente autorizados sin completar."], "_suppress_default_control": True},
        {"heading": "I. CAMPOS QUE PUEDEN DILIGENCIARSE", "numbered": [
            "Valor exigible: únicamente el saldo realmente insoluto de la obligación identificada, más los conceptos accesorios jurídicamente causados y procedentes, menos todos los pagos, créditos, condonaciones y compensaciones acreditados.",
            "Fecha de vencimiento anticipado: únicamente cuando se haya configurado y ejercido válidamente el evento de aceleración previsto; será la fecha real de la actuación y nunca una fecha retroactiva.",
            "Lugar de pago: solo cuando el título permita su determinación y el campo no haya quedado fijado en la versión suscrita.",
            "Fecha de diligenciamiento: la fecha real en que el tenedor complete el título para el ejercicio del derecho, sin alterar la fecha auténtica de creación o entrega.",
        ]},
        {"heading": "II. FÓRMULA DEL VALOR EXIGIBLE", "paragraphs": [f"El valor base de referencia de esta revisión es {_money_words(_agreement_amount(c))}. Para diligenciar un valor diferente deberá existir una liquidación fechada y reproducible: saldo de capital insoluto + intereses efectivamente causados y jurídicamente procedentes + conceptos accesorios expresamente soportados − pagos, notas crédito, compensaciones y demás créditos reconocidos. No se incluyen intereses futuros no causados, intereses sobre intereses no permitidos, honorarios automáticos, penalidades inexistentes ni obligaciones ajenas." ]},
        {"heading": "III. CONDICIONES PREVIAS AL DILIGENCIAMIENTO", "numbered": [
            "Verificar que el tenedor esté legitimado y conserve el título original o soporte íntegro correspondiente.",
            "Identificar la obligación incumplida y su vencimiento efectivo.",
            "Cumplir el requerimiento y oportunidad de subsanación previstos en el acuerdo, si existen.",
            "Actualizar el estado de cuenta hasta la fecha real de diligenciamiento.",
            "Descontar todos los pagos y créditos, incluso los recibidos después de la firma del pagaré.",
            "Revalidar la tasa y límite aplicables por modalidad y período; un parámetro demostrativo no sirve como certificación legal.",
            "Conservar copia de la liquidación, del pagaré diligenciado y de los soportes utilizados.",
        ]},
        {"heading": "IV. CAMPOS Y ACTUACIONES NO AUTORIZADOS", "numbered": [
            "Cambiar identidad, calidad o firma del suscriptor.",
            "Cambiar al beneficiario por una persona sin cadena legítima de transferencia cuando sea exigible acreditarla.",
            "Modificar la moneda o el negocio causal.",
            "Agregar avalistas, fiadores, codeudores o garantías no otorgadas.",
            "Incorporar capital ya pagado o valores de otros negocios.",
            "Fijar intereses futuros como si estuvieran causados.",
            "Capitalizar intereses atrasados por fuera del régimen legal aplicable.",
            "Antedatar el vencimiento, diligenciamiento o incumplimiento.",
        ]},
        {"heading": "V. TRAZABILIDAD, CUSTODIA Y CIERRE", "paragraphs": ["El tenedor conservará la carta de instrucciones vinculada al pagaré y registrará cualquier diligenciamiento posterior. Una vez pagada totalmente la obligación, el título y estas instrucciones deberán quedar cancelados o asociados con evidencia de cierre para impedir usos posteriores incompatibles con el saldo cero."]},
        _single_signature("OTORGANTE DE LAS INSTRUCCIONES / SUSCRIPTOR", debtor, a.get("debtor_id"), "Verificar que la firma y calidad correspondan al mismo suscriptor del pagaré"),
    ]


def _receipt_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    payment_amount = a.get("last_payment_amount") if a.get("last_payment_amount") not in (None, "") else a.get("payment_amount")
    payment_date = a.get("last_payment_date") or a.get("payment_date")
    prior_balance = a.get("balance_before_payment")
    new_balance = a.get("balance_after_payment") if a.get("balance_after_payment") not in (None, "") else c.get("reported_balance")
    return [
        {"heading": "RECIBO DE PAGO", "table": [
            ["Campo", "Información"],
            ["Parte deudora", _value(a.get("debtor_name") or a.get("debtor"))],
            ["Referencia", _value(a.get("document_reference") or a.get("reference"))],
            ["Fecha del pago", _date(payment_date)],
            ["Valor recibido", _money_words(payment_amount)],
            ["Saldo anterior", _money(prior_balance) if prior_balance not in (None, "") else "Por verificar"],
            ["Saldo posterior", _money(new_balance)],
        ], "_suppress_default_control": True},
        {"heading": "I. IMPUTACIÓN", "paragraphs": ["El pago deberá quedar asociado con la cuota o concepto correspondiente y distinguir, cuando aplique, capital, interés causado y otros valores jurídicamente procedentes. Si esa distribución aún no está confirmada, el recibo no debe inventarla: se registrará como pendiente de conciliación y deberá corregirse mediante una nueva revisión trazable."]},
        {"heading": "II. EFECTO DEL PAGO", "paragraphs": ["El valor recibido reduce la obligación en la medida de su imputación válida. Este recibo parcial no constituye paz y salvo total salvo que el saldo posterior sea cero y se expida una constancia específica de cierre después de verificar todos los movimientos e instrumentos relacionados."]},
        {"heading": "III. ACTUALIZACIÓN DE INSTRUMENTOS", "numbered": ["Actualizar estado de cuenta y cronograma.", "Reflejar el pago en el saldo del pagaré cuando exista.", "Conservar comprobante bancario o evidencia equivalente.", "Generar una nueva revisión si el pago anticipado cambia cuotas o plazo."]},
        _single_signature("PARTE ACREEDORA / RECEPTOR DEL PAGO", a.get("creditor_name") or a.get("creditor"), a.get("creditor_id"), "Constancia expedida por representante o responsable autorizado"),
    ]


def _settlement_sections(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    balance = c.get("reported_balance")
    try:
        zero = abs(float(balance or 0)) < 0.01
    except Exception:
        zero = False
    first_heading = "PAZ Y SALVO Y CONSTANCIA DE CIERRE" if zero else "CONSTANCIA DE CIERRE PENDIENTE — NO ES PAZ Y SALVO"
    return [
        {"heading": first_heading, "paragraphs": ["La presente constancia se limita a la obligación y negocio expresamente identificados. Solo puede operar como paz y salvo cuando el expediente acredite saldo cero, pago total y tratamiento coherente de cualquier pagaré o garantía relacionada." if zero else "El expediente aún refleja un saldo positivo o no verificable. Esta pieza no debe utilizarse como paz y salvo; se conserva únicamente para mostrar las actuaciones pendientes antes del cierre."], "_suppress_default_control": True},
        {"heading": "I. VERIFICACIÓN ECONÓMICA", "table": [
            ["Control", "Resultado"],
            ["Capital original", _money(c.get("principal"))],
            ["Pagos y créditos registrados", _money(c.get("partial_payments_total"))],
            ["Saldo final informado", _money(balance)],
            ["Estado", "Saldo cero acreditado preliminarmente" if zero else "Cierre bloqueado hasta reconciliar saldo cero"],
        ]},
        {"heading": "II. EFECTOS DEL CIERRE", "numbered": [
            "Cerrar el estado de cuenta de la obligación individualizada.",
            "Cancelar, devolver o inutilizar jurídicamente el pagaré cuando exista y conservar evidencia de esa actuación.",
            "Detener nuevas gestiones de cobro sobre el saldo extinguido.",
            "Actualizar los registros internos y, si aplica un régimen de información crediticia, gestionar su actualización bajo las reglas específicas correspondientes.",
            "Conservar exclusivamente los documentos necesarios para deberes legales, contables, auditoría y defensa de derechos, bajo controles de acceso adecuados.",
        ] if zero else [
            "Reconciliar el saldo hasta cero o identificar el valor legítimamente pendiente.",
            "Verificar pagos aún no imputados, créditos, notas y ajustes.",
            "No cancelar el título ni declarar extinción total mientras subsista una obligación pendiente.",
        ]},
        {"heading": "III. ALCANCE LIMITADO", "paragraphs": ["El paz y salvo, cuando proceda, cubre únicamente las obligaciones expresamente identificadas y pagadas. No constituye renuncia general frente a negocios diferentes ni altera por sí solo obligaciones recíprocas que no hayan formado parte del cierre."]},
        _single_signature("PARTE ACREEDORA", a.get("creditor_name") or a.get("creditor"), a.get("creditor_id"), "Por representante o responsable autorizado"),
    ]


_BUILDERS: dict[str, Callable[[dict, dict], list[dict]]] = {
    "debt_diagnostic": _diagnostic_sections,
    "account_statement": _account_sections,
    "collection_evidence_matrix": _evidence_sections,
    "collection_letter": _collection_sections,
    "payment_agreement": _agreement_sections,
    "payment_schedule": _schedule_sections,
    "promissory_note": _note_sections,
    "instruction_letter": _instruction_sections,
    "payment_receipt": _receipt_sections,
    "settlement_certificate": _settlement_sections,
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
        "heading": "CONTROL JURÍDICO CO-CD-004",
        "_type": "control",
        "text": (
            "Verificar negocio causal, legitimación, representación, exigibilidad, prescripción, pagos, créditos, saldo, tasa y modalidad; "
            "reconciliar acuerdo, cronograma, pagaré e instrucciones; distinguir obligación social de garantías personales; revisar novación y efectos de ampliación sobre terceros; "
            "controlar títulos en blanco conforme a los artículos 621, 622 y 709 a 711 del Código de Comercio; intereses bajo artículos 884 y 886 y Decreto 1454 de 1989; "
            "novación bajo artículos 1687, 1693 y 1708 del Código Civil; mérito ejecutivo bajo artículo 422 del CGP; Ley 2300 de 2023 solo si aplica; Ley 1266 de 2008 si existe reporte. "
            "Procesos ejecutivos, insolvencia, cesión controvertida, pagaré extraviado, fraude, garantías complejas o diferencias no conciliadas requieren revisión profesional individual. "
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
    kind = str(rewritten.get("kind") or "")
    rewritten["title"] = CLIENT_TITLES.get(kind, rewritten.get("title"))
    rewritten["subtitle"] = CLIENT_SUBTITLES.get(kind, "Cobro y acuerdo de pago · documento sujeto a verificación")
    return rewritten


def finalize_debt_specs(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Recompone las piezas CO-CD-004 presentes sin cambiar la etapa histórica."""
    if (result or {}).get("risk") == "red":
        return specs

    finalized: list[dict] = []
    for spec in specs:
        kind = str(spec.get("kind") or "")
        builder = _BUILDERS.get(kind)
        if builder is None:
            finalized.append(spec)
            continue
        finalized.append(_externalize(spec, builder(answers, result)))
    return finalized
