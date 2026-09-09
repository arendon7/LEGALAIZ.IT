from __future__ import annotations

"""Composición documental M33.0 para la segunda oleada procedimental.

La capa reutiliza `expanded_documents.document_specs` como fuente histórica de
kinds, cálculos, condiciones y matrices. Solo sustituye/expande la presentación y
agrega documentos faltantes de expediente. No modifica `diagnose`, las reglas, los
parámetros dinámicos ni los bloqueos de riesgo.
"""

from copy import deepcopy
from datetime import date
from typing import Any, Callable

from expanded_documents import document_specs as legacy_document_specs
from premium_document_engine import format_cop, format_date_es

M33_PROCEDURAL_CODES = {"CO-LA-001", "CO-CD-001", "CO-CD-003", "CO-CD-004"}


def _value(value: Any, fallback: str = "No informado; requiere verificación") -> str:
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
        return "Valor no determinado"


def _date(value: Any) -> str:
    if not value:
        return "No informada; requiere verificación"
    try:
        return format_date_es(str(value))
    except Exception:
        return str(value)


def _control(code: str, extra: str = "") -> dict:
    text = (
        f"Documento candidato interno {code} bajo estándar M33.0. La salida organiza información y reglas del expediente, pero no sustituye una decisión judicial, administrativa o profesional. "
        "Antes de liberarlo deben verificarse identidad, legitimación, hechos, fechas, cuantías, pagos, anexos, evidencia, vigencia normativa y coherencia entre todas las piezas. "
        "La aprobación jurídica y el QA deben recaer sobre la misma revisión y el mismo hash."
    )
    if extra:
        text += " " + extra
    return {"heading": "CONTROL DE USO, FUENTES Y REVISIÓN", "_type": "control", "text": text}


def _signature(label: str, name: Any, identity: Any = None, role: str = "") -> dict:
    return {
        "heading": "FIRMA",
        "_type": "signature",
        "heading_align": "center",
        "parties": [
            {
                "label": label,
                "name": _value(name, "Persona solicitante por identificar"),
                "id": _value(identity, "Identificación por verificar") if identity not in (None, "") else "",
                "role": role,
            }
        ],
    }


def _append_legacy_tables(sections: list[dict], legacy: list[dict], heading: str) -> list[dict]:
    """Conserva matrices/cálculos maduros sin arrastrar firmas manuales heredadas."""
    preserved = []
    for item in legacy or []:
        if not item.get("table"):
            continue
        preserved.append({
            "heading": str(item.get("heading") or "Matriz de soporte"),
            "table": deepcopy(item["table"]),
            "paragraphs": [str(item.get("text"))] if item.get("text") else [],
            "bullets": list(item.get("bullets") or []),
        })
    if preserved:
        sections.append({"heading": heading, "_type": "annex", "page_break_before": True, "heading_align": "center", "paragraphs": ["Las siguientes matrices reproducen los resultados determinísticos y controles provenientes del motor vigente del producto. Su inclusión permite cotejar la narrativa jurídica con la base matemática y probatoria sin alterar el cálculo original."]})
        sections.extend(preserved)
    return sections


# ---------------------------------------------------------------------------
# CO-LA-001 — liquidación laboral y reclamación
# ---------------------------------------------------------------------------


def _labor_party_rows(a: dict) -> list[list[str]]:
    return [
        ["Elemento", "Información utilizada"],
        ["Persona trabajadora", _value(a.get("employee_name") or a.get("worker_name") or a.get("name"))],
        ["Empleador", _value(a.get("employer_name"))],
        ["Ingreso", _date(a.get("start_date"))],
        ["Terminación o corte", _date(a.get("end_date"))],
        ["Modalidad", _value(a.get("contract_type"))],
        ["Causa informada", _value(a.get("termination"))],
        ["Salario mensual informado", _money(a.get("monthly_salary"))],
    ]


def labor_diagnostic_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    issues = list(c.get("issues") or [])
    assumptions = list(c.get("assumptions") or [])
    exclusions = list(c.get("exclusions") or [])
    return [
        {
            "heading": "1. OBJETO Y ALCANCE DEL DIAGNÓSTICO",
            "paragraphs": [
                "El presente diagnóstico organiza los hechos necesarios para determinar si la información aportada permite elaborar una estimación laboral reproducible, identificar las acreencias matemáticamente liquidables y separar aquellas pretensiones cuya procedencia depende de valoración jurídica, prueba adicional o decisión de autoridad competente.",
                "La estimación no constituye sentencia, confesión del empleador, liquidación oficial ni garantía de pago. Su finalidad es hacer explícitos los supuestos utilizados, impedir dobles cobros y preparar una reclamación cuyo contenido pueda ser contrastado concepto por concepto con los soportes del expediente.",
            ],
        },
        {"heading": "2. IDENTIFICACIÓN DE LA RELACIÓN", "table": _labor_party_rows(a)},
        {
            "heading": "3. HECHOS Y VARIABLES QUE DEBEN QUEDAR PROBADOS",
            "numbered": [
                "Existencia y naturaleza de la relación laboral, junto con sus fechas reales de inicio y terminación.",
                "Salario fijo y componentes variables efectivamente salariales durante cada período relevante.",
                "Auxilio de transporte, cuando corresponda, y su incidencia en las bases prestacionales aplicables.",
                "Vacaciones disfrutadas, compensadas, anticipadas o pendientes.",
                "Pagos anteriores por salario, prima, cesantías, intereses, vacaciones e indemnización.",
                "Causa y autor de la terminación, así como cualquier comunicación o actuación disciplinaria relacionada.",
                "Existencia de suspensiones, licencias no remuneradas, incapacidades u otros períodos que puedan modificar el cálculo.",
                "Existencia de estabilidad laboral reforzada, fuero, accidente, enfermedad laboral, litigio o conciliación previa que impida utilizar una liquidación ordinaria como respuesta final.",
            ],
        },
        {
            "heading": "4. RESULTADO PRELIMINAR DEL MOTOR",
            "table": [
                ["Control", "Resultado"],
                ["Motor", _value(c.get("engine_version"))],
                ["Días de vínculo", _value(c.get("link_days"))],
                ["Base de cesantías", _money(c.get("cesantias_base"))],
                ["Base de prima", _money(c.get("prima_base"))],
                ["Base de vacaciones", _money(c.get("vacation_base"))],
                ["Total bruto estimado", _money(c.get("gross_total"))],
                ["Pagos previos imputados", _money(c.get("prior_paid_total"))],
                ["Total neto preliminar", _money(c.get("total"))],
            ],
            "paragraphs": ["La cifra neta solo puede utilizarse después de confirmar que los períodos, bases y pagos previos corresponden a los documentos reales. Una diferencia entre la liquidación de las partes debe reconducirse al dato, período, fórmula o pago que la produce."],
        },
        {
            "heading": "5. ALERTAS Y SUPUESTOS",
            "bullets": [str(x.get("message") if isinstance(x, dict) else x) for x in issues] + [str(x) for x in assumptions] or ["No se registraron alertas automáticas; continúa siendo obligatoria la validación documental."],
        },
        {
            "heading": "6. CONCEPTOS EXCLUIDOS DE AUTOMATIZACIÓN",
            "paragraphs": ["Los siguientes conceptos no deben sumarse mecánicamente al total, porque su procedencia depende de hechos adicionales, conducta, prueba, régimen aplicable o decisión jurídica individual."],
            "bullets": [str(x) for x in exclusions] or ["Sanciones, perjuicios, indexaciones y demás pretensiones que el motor haya dejado fuera de la estimación ordinaria."],
        },
        {
            "heading": "7. DOCUMENTOS MÍNIMOS PARA CERRAR LA REVISIÓN",
            "numbered": [
                "Contrato de trabajo, otrosíes y anexos aplicables.",
                "Desprendibles de nómina y comprobantes bancarios del período relevante.",
                "Soportes de prima, cesantías e intereses a las cesantías.",
                "Certificación o registro de vacaciones disfrutadas y pendientes.",
                "Comunicación de terminación y documentos que la sustenten.",
                "PILA o soportes de seguridad social cuando sean pertinentes.",
                "Liquidación preparada por el empleador y comprobante de cualquier pago final.",
                "Autorizaciones de descuentos, préstamos o compensaciones que se pretendan aplicar.",
            ],
        },
        _control("CO-LA-001", "Las sanciones moratorias, fueros y controversias sobre contrato realidad o estabilidad reforzada requieren revisión profesional individual."),
    ]


def labor_calculation_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    c = _calc(result)
    rows = [["Concepto", "Bruto", "Pagado", "Saldo", "Fórmula"]]
    for item in c.get("line_items") or []:
        rows.append([
            _value(item.get("label") or item.get("key")),
            _money(item.get("gross")),
            _money(item.get("prior_paid")),
            _money(item.get("net")),
            _value(item.get("formula")),
        ])
    sections = [
        {
            "heading": "1. NATURALEZA Y LÍMITES DE LA LIQUIDACIÓN",
            "paragraphs": [
                "Este informe presenta una estimación determinística de las acreencias que pueden calcularse con las variables confirmadas. Cada línea conserva su base, período, fórmula, pagos previos y saldo, de modo que la cifra final pueda ser auditada y corregida sin rehacer de manera opaca toda la liquidación.",
                "Los conceptos litigiosos o sancionatorios no se incorporan por defecto. La ausencia de una cifra no significa inexistencia del derecho: significa que el expediente todavía no permite cuantificarlo de manera responsable mediante el motor automático.",
            ],
        },
        {"heading": "2. DATOS DE LA RELACIÓN", "table": _labor_party_rows(a)},
        {"heading": "3. LIQUIDACIÓN POR CONCEPTO", "table": rows if len(rows) > 1 else [["Concepto", "Resultado"], ["Estado", "No existen líneas calculadas suficientes"]]},
        {
            "heading": "4. RESULTADO ECONÓMICO",
            "table": [
                ["Resultado", "Valor"],
                ["Total bruto", _money(c.get("gross_total"))],
                ["Pagos previos", _money(c.get("prior_paid_total"))],
                ["Saldo neto estimado", _money(c.get("total"))],
            ],
            "paragraphs": ["El saldo neto deberá compararse con la liquidación del empleador. Cualquier pago adicional descubierto después de esta versión debe incorporarse como un movimiento nuevo y no borrando el historial utilizado para producir la revisión anterior."],
        },
        {
            "heading": "5. CONTROL DE BASES Y PERÍODOS",
            "table": [
                ["Variable", "Valor"],
                ["Días de vínculo", _value(c.get("link_days"))],
                ["Días de cesantías", _value(c.get("cesantias_days"))],
                ["Días de prima", _value(c.get("prima_days"))],
                ["Vacaciones pendientes", _value(c.get("vacation_pending_days"))],
                ["Días indemnizatorios", _value(c.get("indemnity_days"))],
                ["Base cesantías", _money(c.get("cesantias_base"))],
                ["Base prima", _money(c.get("prima_base"))],
                ["Base vacaciones", _money(c.get("vacation_base"))],
                ["Base indemnización", _money(c.get("indemnity_base"))],
            ],
        },
        {
            "heading": "6. RESERVAS JURÍDICAS",
            "bullets": [str(x) for x in c.get("exclusions") or []] + [str(x) for x in c.get("assumptions") or []],
        },
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — MATRICES DEL MOTOR DE LIQUIDACIÓN")
    sections.append(_control("CO-LA-001"))
    return sections


def labor_claim_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    name = a.get("employee_name") or a.get("worker_name") or a.get("name")
    employer = a.get("employer_name")
    requests = [
        "Elaborar y remitir una liquidación definitiva discriminada por concepto, período, base, fórmula, días, pagos previos, deducciones y valor neto.",
        "Comparar la liquidación empresarial con el informe estimativo adjunto y explicar de forma concreta cada diferencia, identificando el dato, soporte o criterio que la produce.",
        "Pagar los valores que sean reconocidos como debidos e informar la fecha, medio e identificación del comprobante correspondiente.",
        "Entregar copia de los documentos de la relación laboral que resulten necesarios para verificar la liquidación y que se encuentren bajo custodia del empleador.",
        "Informar cualquier hecho que modifique la estimación, como pagos anteriores, vacaciones disfrutadas, suspensiones, descuentos autorizados o una causa de terminación diferente de la reportada.",
        "Abstenerse de efectuar descuentos que no cuenten con fundamento legal, orden judicial o autorización previa, expresa y suficientemente determinada cuando esta sea necesaria.",
        "Proponer una reunión o mecanismo de arreglo cuando exista una diferencia conciliable, sin convertir la negociación en renuncia general a derechos ciertos e indiscutibles.",
        "Remitir una respuesta escrita, completa y documentada al canal indicado por la persona trabajadora.",
    ]
    return [
        {
            "heading": "ASUNTO Y ALCANCE",
            "paragraphs": [
                f"{_value(name, 'La persona trabajadora')} presenta reclamación frente a {_value(employer, 'el empleador por identificar')} con el propósito de obtener la verificación, liquidación y pago de las acreencias que puedan encontrarse pendientes al finalizar la relación laboral.",
                "La comunicación no pretende presentar una estimación privada como deuda judicialmente declarada. Busca que las partes comparen hechos, períodos, fórmulas, pagos y soportes de manera transparente y que cualquier diferencia sea explicada antes de aceptar una liquidación, transacción o paz y salvo.",
            ],
        },
        {
            "heading": "I. HECHOS RELEVANTES",
            "numbered": [
                f"La relación se informa entre {_date(a.get('start_date'))} y {_date(a.get('end_date'))}.",
                f"La modalidad reportada es {_value(a.get('contract_type'))} y la causa de terminación informada es {_value(a.get('termination'))}.",
                f"El salario mensual informado para el cálculo es {_money(a.get('monthly_salary'))}.",
                f"El motor determina un saldo neto preliminar de {_money(c.get('total'))}, sujeto a verificación de documentos, pagos y períodos.",
                "La reclamación conserva expresamente la posibilidad de corregir la cifra cuando los soportes revelen información diferente.",
            ],
        },
        {
            "heading": "II. CONCEPTOS OBJETO DE VERIFICACIÓN",
            "table": [["Concepto", "Saldo preliminar"]] + [[_value(x.get("label") or x.get("key")), _money(x.get("net"))] for x in c.get("line_items") or []],
        },
        {"heading": "III. SOLICITUDES", "numbered": requests},
        {
            "heading": "IV. DOCUMENTOS SOLICITADOS",
            "numbered": [
                "Contrato de trabajo completo, otrosíes y anexos.",
                "Desprendibles y comprobantes de nómina del período relevante.",
                "Soportes de pago de prima, cesantías, intereses y vacaciones.",
                "Certificación de vacaciones disfrutadas, compensadas y pendientes.",
                "Comprobantes o planillas de seguridad social pertinentes.",
                "Comunicación de terminación y documentos que la empresa considere fundamento de la decisión.",
                "Liquidación definitiva preparada por el empleador y soportes de cualquier deducción.",
                "Certificación laboral y demás constancias a las que haya lugar.",
            ],
        },
        {
            "heading": "V. RESERVA Y TRAZABILIDAD",
            "paragraphs": [
                "La reclamación no constituye aceptación de una liquidación unilateral, novación, transacción, conciliación o paz y salvo general. Tampoco pretende duplicar conceptos ya pagados.",
                "La persona solicitante conservará copia exacta de esta versión, sus anexos y la constancia de recepción. Las ampliaciones posteriores se radicarán como alcances separados para preservar la cronología y los efectos que jurídicamente correspondan.",
            ],
        },
        _signature("PERSONA TRABAJADORA", name, a.get("employee_id") or a.get("worker_id")),
        _control("CO-LA-001"),
    ]


def labor_support_request_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. FINALIDAD", "paragraphs": ["La presente solicitud se utiliza cuando la información disponible no basta para cerrar la liquidación o cuando conviene obtener primero los soportes que permitan reconstruir de manera verificable la relación laboral. Se limita a información de la persona solicitante y no pretende acceder a datos personales de terceros." ]},
        {"heading": "2. DOCUMENTOS SOLICITADOS", "numbered": [
            "Contrato de trabajo, otrosíes, anexos de remuneración, descripción del cargo y documentos expresamente incorporados a la relación.",
            "Desprendibles de nómina y comprobantes de pago durante los períodos discutidos.",
            "Soportes de prima, vacaciones, cesantías, intereses a las cesantías y liquidaciones parciales o definitivas.",
            "Certificación de períodos de vacaciones disfrutados, compensados, acumulados o pendientes.",
            "Planillas o soportes de aportes al Sistema de Seguridad Social Integral que correspondan a la persona solicitante.",
            "Comunicación de terminación y documentos que la empresa considere relevantes para explicar la causa informada.",
            "Soportes de cualquier préstamo, anticipo, descuento, retención o compensación pretendida.",
            "Liquidación final discriminada y certificación laboral correspondiente.",
        ]},
        {"heading": "3. ENTREGA Y PROTECCIÓN DE LA INFORMACIÓN", "paragraphs": ["Se solicita la entrega por un medio verificable y legible. Cuando algún documento no pueda suministrarse, la respuesta deberá indicar cuál, por qué y, cuando sea posible, qué área o tercero lo conserva. La solicitud no autoriza usos de los datos diferentes de la gestión de la relación laboral y del ejercicio de los derechos correspondientes." ]},
        _signature("PERSONA SOLICITANTE", a.get("employee_name") or a.get("worker_name") or a.get("name"), a.get("employee_id") or a.get("worker_id")),
        _control("CO-LA-001"),
    ]


def labor_difference_matrix_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "1. FINALIDAD DE LA MATRIZ", "paragraphs": ["La matriz permite comparar la estimación del expediente con la liquidación o respuesta del empleador. Toda diferencia debe reconducirse a un hecho, período, base, fórmula, pago previo o deducción identificable; no debe resolverse mediante ajustes globales sin explicación." ]},
        {"heading": "2. COMPARACIÓN POR CONCEPTO", "table": [["Concepto", "Estimación LegalAIZ.it", "Valor empleador", "Diferencia / causa", "Estado"]] + [[_value(x.get("label") or x.get("key")), _money(x.get("net")), "Por incorporar desde respuesta", "Pendiente de cotejo", "Abierto"] for x in c.get("line_items") or []]},
        {"heading": "3. REGLAS DE CONCILIACIÓN", "numbered": [
            "No duplicar conceptos reconocidos o pagados.",
            "No aceptar un valor global cuando impida conocer qué derechos comprende.",
            "Distinguir derechos ciertos e indiscutibles de pretensiones controvertibles.",
            "Documentar las concesiones recíprocas cuando se pretenda celebrar una transacción o conciliación.",
            "Identificar expresamente valores reconocidos, controvertidos, pagados y pendientes.",
            "No extender un paz y salvo a períodos o conceptos desconocidos que no hayan sido individualizados.",
        ]},
        _control("CO-LA-001"),
    ]


def labor_deadline_calendar_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. CALENDARIO DE ACTUACIONES", "table": [
            ["Actuación", "Fecha o condición", "Evidencia exigida", "Estado"],
            ["Confirmar variables", "Antes de radicar", "Aprobación del usuario", "Pendiente"],
            ["Radicar reclamación", "Fecha efectiva de envío/recepción", "Radicado o acuse", "Pendiente"],
            ["Solicitar soportes faltantes", "Con reclamación o actuación separada", "Solicitud y respuesta", "Pendiente"],
            ["Comparar liquidaciones", "Al recibir respuesta", "Matriz de diferencias", "Pendiente"],
            ["Evaluar arreglo", "Después del cotejo", "Acta o propuesta", "Condicional"],
            ["Revisar prescripción", "Por cada concepto", "Cálculo individual", "Obligatorio"],
            ["Cerrar expediente", "Después del pago o resultado final", "Acta de cierre", "Pendiente"],
        ]},
        {"heading": "2. CONTROL DE PRESCRIPCIÓN", "paragraphs": ["Los derechos laborales pueden tener fechas de exigibilidad diferentes. El sistema debe conservar un calendario individual por concepto y no deducir un único vencimiento para toda la relación. La recepción de una reclamación escrita deberá registrarse con precisión para analizar los efectos jurídicos que correspondan sobre el derecho específicamente reclamado." ]},
        {"heading": "3. CRITERIO DE CIERRE", "paragraphs": ["El expediente solo podrá cerrarse cuando consten el resultado final, los valores pagados, su imputación, la fecha, el comprobante, los conceptos que continúan controvertidos y cualquier reserva expresa. Una respuesta sin ejecución material no equivale al cierre económico del caso." ]},
        _control("CO-LA-001"),
    ]


# ---------------------------------------------------------------------------
# CO-CD-001 — hábeas data financiero
# ---------------------------------------------------------------------------


def _habeas_subject(a: dict) -> str:
    return _value(a.get("data_subject_name"), "Titular de la información por identificar")


def habeas_consultation_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    subject = _habeas_subject(a)
    return [
        {"heading": "ASUNTO Y FINALIDAD", "paragraphs": [f"{subject} presenta consulta integral para conocer el contenido, origen, circulación, actualización y utilización de la información financiera, crediticia, comercial o de servicios asociada a su identidad. La solicitud busca reunir la información necesaria para ejercer, si corresponde, los derechos de actualización, rectificación y reclamación; no parte de la premisa de que todo dato negativo deba ser eliminado." ]},
        {"heading": "I. IDENTIFICACIÓN DE LOS ACTORES", "table": [
            ["Rol", "Información"],
            ["Titular", subject],
            ["Fuente", _value(a.get("source_name"), "Por identificar")],
            ["Operador", _value(a.get("operator_name"), "Por identificar")],
            ["Usuario de la información", _value(a.get("user_entity_name"), "No identificado")],
        ]},
        {"heading": "II. SOLICITUDES DE INFORMACIÓN", "numbered": [
            "Suministrar copia íntegra, clara, comprensible y actualizada del registro individual, incluyendo estados, saldos, fechas, leyendas y demás información asociada al titular.",
            "Identificar cada obligación, fuente, producto, fecha de apertura, exigibilidad, inicio de mora, primer reporte, actualizaciones, saldo actual, pago o extinción y término de permanencia aplicado.",
            "Informar las fechas en que la fuente suministró o actualizó cada dato y conservar trazabilidad suficiente para auditar las modificaciones.",
            "Identificar los usuarios que hayan consultado el registro durante el período disponible, con fecha y finalidad registrada, dentro de los límites legales aplicables.",
            "Informar las leyendas actualmente asociadas a reclamos, discusión, fraude, pago, mora, procesos u otras novedades relevantes.",
            "Entregar o identificar el soporte jurídico y contractual de la circulación cuando resulte necesario para comprender la legitimidad del tratamiento.",
            "Explicar el procedimiento para corregir, actualizar o retirar datos cuando se configuren los presupuestos jurídicos correspondientes.",
            "Indicar el responsable del trámite, número de radicado y canal de seguimiento.",
        ]},
        {"heading": "III. CONTROL TEMPORAL PRELIMINAR", "table": [
            ["Hito", "Resultado del motor"],
            ["Radicación", _date(c.get("filing_date"))],
            ["Vencimiento ordinario", _date(c.get("preliminary_due_date"))],
            ["Vencimiento máximo modelado", _date(c.get("preliminary_due_with_extension"))],
            ["Inicio de mora", _date(c.get("mora_start_date"))],
            ["Pago o extinción", _date(c.get("payment_or_extinction_date"))],
            ["Vencimiento preliminar del dato pagado", _date(c.get("paid_negative_expiry_preliminary"))],
        ], "paragraphs": ["Las fechas del motor son controles preliminares. Antes de formular una consecuencia definitiva deben cotejarse con el soporte de la obligación, la comunicación previa, los registros de reporte y el régimen temporal aplicable." ]},
        {"heading": "IV. PROTECCIÓN DE IDENTIDAD Y DATOS", "paragraphs": ["Los documentos de identidad aportados deben utilizarse únicamente para verificar legitimación y tramitar la actuación. No se autoriza la incorporación de la información a finalidades comerciales adicionales ni la exigencia de datos excesivos sin una explicación de necesidad y proporcionalidad." ]},
        _signature("TITULAR DE LA INFORMACIÓN", subject, a.get("data_subject_id")),
        _control("CO-CD-001"),
    ]


def habeas_claim_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    subject = _habeas_subject(a)
    mode = _value(a.get("request_mode"), "Reclamación de corrección o actualización")
    return [
        {"heading": "ASUNTO Y DELIMITACIÓN", "paragraphs": [f"{subject} presenta {mode.lower()} respecto de la información identificada en el expediente. La actuación no desconoce automáticamente la existencia histórica de una obligación ni exige alterar un registro válido: solicita que la fuente y el operador acrediten que la información es exacta, completa, actualizada, temporalmente procedente y comunicada bajo el procedimiento aplicable." ]},
        {"heading": "I. HECHOS RELEVANTES", "numbered": [
            _value(a.get("facts_detail"), "Los hechos detallados deben cotejarse con los anexos antes de radicar."),
            f"La fuente identificada es {_value(a.get('source_name'), 'por determinar')} y el operador identificado es {_value(a.get('operator_name'), 'por determinar')}.",
            f"La fecha de inicio de mora informada es {_date(a.get('mora_start_date'))}; la fecha de pago o extinción informada es {_date(a.get('payment_or_extinction_date'))}.",
            f"La fecha de reporte informada es {_date(a.get('report_date'))} y el conocimiento del titular se ubica en {_date(a.get('report_discovery_date'))}.",
            "La permanencia, comunicación previa y exactitud deben resolverse con la evidencia de la fuente y el operador y no exclusivamente con la captura visible para el usuario.",
        ]},
        {"heading": "II. SOLICITUDES A LA FUENTE", "numbered": [
            "Certificar el origen, naturaleza, valor, exigibilidad, fecha de mora, duración, pago o extinción y estado actual de la obligación discutida.",
            "Aportar la evidencia de la comunicación previa al reporte, identificando fecha, canal, destino, contenido y prueba técnica de envío o recepción según corresponda.",
            "Informar la fecha exacta del primer reporte y de cada actualización material comunicada al operador.",
            "Corregir cualquier saldo, fecha, estado o dato inexacto y transmitir inmediatamente la novedad al operador.",
            "Solicitar el retiro del dato negativo cuando se verifique que el término de permanencia aplicable ya finalizó, sin confundir ese retiro con la extinción de una obligación que pudiera subsistir por otra razón.",
            "Solicitar la actualización de mediciones o leyendas que sigan utilizando un dato que ya no deba circular como información negativa.",
            "Explicar de manera individual cualquier negativa, relacionando hechos, documentos, fechas y criterio jurídico concreto.",
        ]},
        {"heading": "III. SOLICITUDES AL OPERADOR", "numbered": [
            "Incorporar la leyenda de reclamo en trámite dentro del término aplicable cuando se cumplan sus presupuestos y mantenerla mientras la controversia se encuentre abierta.",
            "Trasladar el reclamo a la fuente cuando resulte necesario y conservar evidencia de la coordinación entre ambos actores.",
            "Ejecutar las correcciones, actualizaciones o retiros comunicados válidamente y permitir al titular verificar el resultado mediante una nueva consulta.",
            "Actualizar simultáneamente las leyendas y mediciones vinculadas al dato corregido o retirado cuando jurídicamente corresponda.",
            "Responder de fondo las cuestiones propias de su rol y no limitarse a copiar una respuesta de la fuente cuando subsistan inconsistencias objetivas.",
        ]},
        {"heading": "IV. CONTROL DE TÉRMINOS Y PERMANENCIA", "table": [
            ["Control", "Resultado preliminar"],
            ["Término de la actuación", _value(c.get("term_category"))],
            ["Vencimiento ordinario", _date(c.get("preliminary_due_date"))],
            ["Vencimiento máximo modelado", _date(c.get("preliminary_due_with_extension"))],
            ["Leyenda en trámite", _date(c.get("claim_legend_due_date"))],
            ["Duración de mora", _value(c.get("mora_duration_days"))],
            ["Vencimiento dato pagado", _date(c.get("paid_negative_expiry_preliminary"))],
            ["Caducidad dato insoluto", _date(c.get("unpaid_negative_expiry_preliminary"))],
        ]},
        {"heading": "V. VIGENCIA TEMPORAL Y SUPLANTACIÓN", "paragraphs": [f"Estado preliminar del régimen especial de 2026 para la fecha de referencia: {_value(c.get('law_2573_status_at_reference'))}. La plataforma no debe aplicar anticipadamente disposiciones cuya vigencia se encuentre diferida ni utilizar la ruta ordinaria cuando el caso corresponda realmente a suplantación, fraude complejo o un proceso judicial activo." ]},
        _signature("TITULAR DE LA INFORMACIÓN", subject, a.get("data_subject_id")),
        _control("CO-CD-001", "La plataforma no promete retiro de obligaciones válidas, aumento de puntaje ni aprobación de crédito."),
    ]


def habeas_reiteration_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "1. ANTECEDENTES", "paragraphs": [f"Se reitera la actuación previamente radicada el {_date(a.get('prior_claim_date'))}, identificada con {_value(a.get('prior_claim_radicado'), 'radicado por verificar')}. La reiteración solo procede después de comprobar la recepción del reclamo original y el estado real de la respuesta." ]},
        {"heading": "2. DEFICIENCIAS QUE DEBEN PRECISARSE", "numbered": [
            "Ausencia de respuesta dentro del término o respuesta cuya prórroga no fue comunicada válidamente.",
            "Contestación que no resuelve hechos, soportes o solicitudes individualizadas.",
            "Falta de incorporación o mantenimiento de la leyenda correspondiente durante el reclamo.",
            "Corrección anunciada pero no ejecutada materialmente en el registro consultable.",
            "Ausencia de explicación sobre comunicación previa, permanencia, fuente, traslado o actualización.",
        ]},
        {"heading": "3. SOLICITUDES DE REITERACIÓN", "numbered": [
            "Resolver integralmente los puntos pendientes y aportar los documentos anunciados.",
            "Informar el estado de la leyenda de reclamación y la fecha en que fue incorporada.",
            "Explicar los traslados realizados entre fuente y operador y aportar evidencia de su recepción.",
            "Ejecutar materialmente cualquier corrección aceptada y entregar una nueva consulta del registro.",
            "Identificar el responsable del cierre y los mecanismos disponibles frente a una decisión desfavorable.",
        ]},
        {"heading": "4. CALENDARIO DEL EXPEDIENTE", "table": [["Hito", "Fecha preliminar"], ["Reclamo previo", _date(c.get("prior_claim_date"))], ["Vencimiento ordinario", _date(c.get("prior_preliminary_due_date"))], ["Vencimiento máximo", _date(c.get("prior_max_due_date"))], ["Leyenda", _date(c.get("claim_legend_due_date"))]]},
        _signature("TITULAR DE LA INFORMACIÓN", _habeas_subject(a), a.get("data_subject_id")),
        _control("CO-CD-001"),
    ]


def identity_theft_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    c = _calc(result)
    sections = [
        {"heading": "1. REGLA DE ACTIVACIÓN", "paragraphs": ["Este protocolo solo debe utilizarse cuando la persona desconoce la obligación o producto y existe una hipótesis real de utilización no autorizada de su identidad. La simple inconformidad con una deuda reconocida no puede reconducirse artificialmente a suplantación." ]},
        {"heading": "2. PRESERVACIÓN INMEDIATA", "numbered": [
            "Conservar la consulta original, alertas, correos, mensajes, contratos, grabaciones y metadatos sin modificar los archivos fuente.",
            "Identificar la fecha exacta en que la persona tuvo conocimiento del producto u obligación.",
            "Solicitar a la fuente la preservación de documentos de apertura, validaciones de identidad, biometría, IP, dispositivos, geolocalización, desembolso y soportes de entrega que existan legítimamente.",
            "Cambiar credenciales comprometidas y activar mecanismos de autenticación reforzada cuando exista riesgo actual.",
            "Evitar circular copias completas del documento de identidad por canales abiertos o a destinatarios que no intervienen en el caso.",
        ]},
        {"heading": "3. RECLAMACIONES COORDINADAS", "numbered": [
            "Comunicar formalmente el desconocimiento a cada fuente y operador involucrado.",
            "Solicitar la marcación o medida preventiva aplicable mientras se verifica la identidad, sin afirmar un efecto que dependa de la fecha y régimen legal vigente.",
            "Obtener copia de la solicitud, contrato, mecanismos de autenticación, datos de contacto, cuenta receptora y demás trazabilidad utilizada para crear la obligación.",
            "Exigir una investigación de fondo y una decisión motivada sobre las discrepancias entre los datos auténticos y los utilizados en la operación cuestionada.",
            "Cuando la suplantación se confirme, solicitar las correcciones y comunicaciones necesarias para impedir la persistencia de efectos adversos.",
        ]},
        {"heading": "4. CONTROL TEMPORAL DEL RÉGIMEN 2026", "table": [["Control", "Resultado"], ["Estado aplicable", _value(c.get("law_2573_status_at_reference"))], ["Alcance inmediato", _value(c.get("law_2573_immediate_scope"))]], "paragraphs": ["Antes de invocar un procedimiento especial debe verificarse la fecha efectiva del caso y la entrada en vigor de cada disposición. La plataforma debe conservar una regla temporal y bloquear conclusiones que utilicen anticipadamente normas diferidas." ]},
        {"heading": "5. ESCALAMIENTO", "paragraphs": ["La existencia de múltiples productos, desembolsos, medidas judiciales, biometría discutida, daño relevante o investigación penal exige estrategia profesional individual y bloquea una salida automática definitiva." ]},
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — CONTROLES HISTÓRICOS DE SUPLANTACIÓN")
    sections.append(_control("CO-CD-001"))
    return sections


# ---------------------------------------------------------------------------
# CO-CD-003 — mecanismos de protección al consumidor
# ---------------------------------------------------------------------------


def consumer_diagnosis_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    eligibility = c.get("mechanism_eligibility") if isinstance(c.get("mechanism_eligibility"), dict) else {}
    return [
        {"heading": "1. OBJETO DE LA CLASIFICACIÓN", "paragraphs": ["El diagnóstico determina qué mecanismo de protección al consumidor corresponde a los hechos confirmados. Garantía legal, retracto, reversión del pago, terminación por falta de entrega y revocación de débitos periódicos tienen presupuestos, términos y destinatarios distintos y no deben acumularse por simple conveniencia." ]},
        {"heading": "2. DATOS PRINCIPALES", "table": [
            ["Elemento", "Información"],
            ["Persona consumidora", _value(a.get("consumer_name"))],
            ["Proveedor", _value(a.get("supplier_name"))],
            ["Producto o servicio", _value(a.get("product_or_service"))],
            ["Mecanismo seleccionado", _value(a.get("request_mode"))],
            ["Fecha de compra o contrato", _date(a.get("purchase_date"))],
            ["Fecha de entrega", _date(a.get("delivery_date"))],
            ["Valor", _money(a.get("amount"))],
        ]},
        {"heading": "3. ELEGIBILIDAD DEL MOTOR", "table": [["Mecanismo", "Habilitación preliminar"]] + [[str(key), "Sí" if bool(value) else "No"] for key, value in eligibility.items()]},
        {"heading": "4. REGLAS DE SELECCIÓN", "numbered": [
            "La garantía responde a defectos de calidad, idoneidad, seguridad o funcionamiento y conserva una lógica distinta del simple arrepentimiento.",
            "El retracto requiere una modalidad contractual incluida, ausencia de excepción y ejercicio dentro del término correspondiente.",
            "La reversión del pago exige una operación electrónica, una causal compatible, actuaciones coordinadas y control estricto de los términos.",
            "La falta de entrega se analiza como incumplimiento del comercio electrónico y no debe disfrazarse como retracto cuando el supuesto real es que el producto nunca llegó.",
            "La revocación de un débito periódico impide cobros futuros bajo la autorización revocada, pero no extingue automáticamente obligaciones válidamente causadas.",
        ]},
        {"heading": "5. ALERTAS", "bullets": [str(x.get("message") if isinstance(x, dict) else x) for x in c.get("issues") or []] + [str(x) for x in c.get("assumptions") or []]},
        {"heading": "6. DECISIÓN DOCUMENTAL", "paragraphs": [f"Con los datos actuales, el expediente conserva como mecanismo principal: {_value(a.get('request_mode'))}. Solo la comunicación compatible con ese mecanismo debe formar parte del paquete sustantivo, además de la matriz probatoria y el calendario de seguimiento." ]},
        _control("CO-CD-003", "Lesiones, productos inseguros, fraude complejo, regímenes sectoriales y procesos activos exigen escalamiento profesional."),
    ]


def warranty_claim_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y NATURALEZA DE LA RECLAMACIÓN", "paragraphs": ["La persona consumidora formula reclamación directa para hacer efectiva la garantía legal frente a una falla de calidad, idoneidad, seguridad o funcionamiento. La solicitud no debe presentarse como retracto cuando el verdadero fundamento es el defecto del producto o servicio." ]},
        {"heading": "I. HECHOS", "numbered": [
            f"El producto o servicio identificado es {_value(a.get('product_or_service'))}, adquirido a {_value(a.get('supplier_name'), 'el proveedor por identificar')}.",
            f"La compra o contratación se informa para {_date(a.get('purchase_date'))} y la entrega para {_date(a.get('delivery_date'))}.",
            f"La falla o inconformidad se describe así: {_value(a.get('defect_detail') or a.get('facts_detail'))}.",
            f"Falla repetida informada: {_value(a.get('repeated_failure'))}.",
            "La reclamación conserva como anexos la factura o prueba de compra, las comunicaciones previas, fotografías, videos, diagnósticos y constancias de intervenciones anteriores disponibles.",
        ]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Registrar la reclamación dentro del término de garantía y entregar constancia de su recepción.",
            "Identificar el diagnóstico técnico, las pruebas practicadas y cualquier causal que se pretenda invocar para excluir la garantía.",
            "Aplicar la solución jurídicamente compatible con la etapa del caso y con la elección válida de la persona consumidora cuando exista falla repetida o imposibilidad de reparación.",
            "Asumir los costos que legalmente correspondan para hacer efectiva la garantía y coordinar la recepción, recogida o entrega del producto de manera razonable.",
            "Cuando se alegue uso indebido, identificar la conducta, la instrucción incumplida, su entrega al consumidor, la prueba técnica y la relación causal con la falla.",
            "Emitir respuesta de fondo, acompañada de los soportes utilizados y del procedimiento concreto para ejecutar la solución aceptada.",
        ]},
        {"heading": "III. PRIVACIDAD Y DISPOSITIVOS", "paragraphs": ["Cuando el producto almacene datos personales, el acceso técnico deberá limitarse a lo indispensable para el diagnóstico. La persona consumidora debe ser informada antes de operaciones de restablecimiento o borrado cuando ello sea técnicamente posible y razonable." ]},
        _signature("PERSONA CONSUMIDORA", a.get("consumer_name"), a.get("consumer_id")),
        _control("CO-CD-003"),
    ]


def withdrawal_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO", "paragraphs": ["La presente comunicación ejerce el derecho de retracto dentro de un supuesto que el motor ha clasificado preliminarmente como elegible. No se fundamenta en una falla del producto y no debe mezclarse con una reclamación de garantía salvo que existan hechos independientes que justifiquen actuaciones separadas." ]},
        {"heading": "I. PRESUPUESTOS", "numbered": [
            f"La modalidad de contratación informada es {_value(a.get('purchase_channel') or a.get('contract_method'))}.",
            f"La fecha de entrega o celebración relevante es {_date(a.get('delivery_date') or a.get('purchase_date'))}.",
            f"La existencia de una excepción al retracto se reporta como {_value(a.get('withdrawal_exception'))}.",
            "La persona consumidora manifiesta su decisión de desistir dentro del término que el motor debe verificar antes de habilitar la salida definitiva.",
        ]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Registrar la fecha y hora de ejercicio del retracto.",
            "Informar el procedimiento razonable para la devolución material del bien cuando corresponda.",
            "Resolver el contrato en los términos jurídicamente aplicables y abstenerse de imponer penalidades o condiciones incompatibles con el mecanismo.",
            "Devolver las sumas pagadas dentro del término aplicable, identificando medio, fecha y comprobante.",
            "Expedir constancia de recepción del bien o de cierre cuando se completen las actuaciones a cargo de ambas partes.",
        ]},
        _signature("PERSONA CONSUMIDORA", a.get("consumer_name"), a.get("consumer_id")),
        _control("CO-CD-003"),
    ]


def reversal_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. ESTRUCTURA DE LA ACTUACIÓN", "paragraphs": ["La reversión del pago requiere actuaciones coordinadas frente al proveedor y al emisor del instrumento de pago. El documento debe conservar una sola causal principal compatible con los hechos y distinguir el valor total de la compra del valor cuya reversión se solicita." ]},
        {"heading": "2. COMUNICACIÓN AL PROVEEDOR", "numbered": [
            f"Identificar la operación, fecha, valor y causal: {_value(a.get('reversal_cause'))}.",
            "Registrar la queja con fecha cierta y suministrar constancia de recepción.",
            "Identificar el producto o servicio, estado de entrega y disponibilidad para devolución cuando corresponda.",
            "Coordinar la información necesaria con los participantes del proceso de pago sin exigir una admisión previa de responsabilidad.",
        ]},
        {"heading": "3. NOTIFICACIÓN AL EMISOR", "numbered": [
            "Identificar al titular, instrumento mediante datos minimizados, fecha, referencia y valor solicitado.",
            "Aportar la constancia de la queja presentada ante el proveedor.",
            "Solicitar la apertura del procedimiento de reversión y la coordinación con los participantes del sistema de pago.",
            "Solicitar confirmación escrita de la ejecución contable o de la decisión que corresponda.",
        ]},
        {"heading": "4. CONTROL DE SEGURIDAD", "paragraphs": ["El documento nunca debe incluir el número completo de la tarjeta, código de seguridad, contraseñas, claves dinámicas o credenciales. La persona solicitante debe declarar la veracidad de la causal y evitar una devolución duplicada del mismo pago." ]},
        _signature("TITULAR DEL INSTRUMENTO / PERSONA CONSUMIDORA", a.get("consumer_name"), a.get("consumer_id")),
        _control("CO-CD-003"),
    ]


def recurring_debit_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. REVOCACIÓN DE AUTORIZACIÓN", "paragraphs": ["La persona titular revoca de manera expresa la autorización de débito periódico para impedir nuevos cargos bajo el mandato identificado. La revocación del mecanismo de pago no constituye por sí sola una declaración de inexistencia de obligaciones principales que se hubieran causado válidamente." ]},
        {"heading": "2. SOLICITUDES", "numbered": [
            "Registrar inmediatamente la revocación y expedir constancia con fecha cierta.",
            "Cesar la presentación de nuevas órdenes de débito bajo la autorización revocada y comunicar la instrucción a los participantes pertinentes.",
            "Informar la fecha efectiva de desactivación y cualquier factura ya causada antes de la revocación.",
            "Cuando exista un débito posterior, tramitar la reversión correspondiente dentro de los presupuestos y términos aplicables.",
            "Bloquear o desactivar tokens o mandatos de cobro en lo jurídicamente procedente, sin eliminar información cuya conservación sea obligatoria.",
        ]},
        _signature("TITULAR", a.get("consumer_name"), a.get("consumer_id")),
        _control("CO-CD-003"),
    ]


def non_delivery_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "ASUNTO Y CAUSA", "paragraphs": ["La comunicación se fundamenta en la falta de entrega del producto adquirido mediante comercio electrónico. No constituye retracto: la causa es el incumplimiento de la entrega dentro del plazo prometido o del límite supletivo aplicable, o la inexistencia de disponibilidad cuando esta impida cumplir el negocio." ]},
        {"heading": "I. HECHOS", "numbered": [
            f"Pedido o producto: {_value(a.get('product_or_service'))}.",
            f"Fecha de compra: {_date(a.get('purchase_date'))}.",
            f"Fecha prometida de entrega: {_date(a.get('promised_delivery_date'))}.",
            f"Estado actual: {_value(a.get('delivery_status') or a.get('facts_detail'))}.",
        ]},
        {"heading": "II. SOLICITUDES", "numbered": [
            "Registrar la terminación o resolución del negocio en las condiciones jurídicamente procedentes.",
            "Cancelar el pedido o los ítems afectados y abstenerse de despacharlos después de la comunicación, salvo nueva aceptación expresa.",
            "Devolver las sumas pagadas sin imponer bonos, saldos o mecanismos diferentes del reintegro aceptado libremente por la persona consumidora.",
            "Informar el medio, fecha y comprobante de devolución y confirmar el cierre del pedido.",
        ]},
        _signature("PERSONA CONSUMIDORA", a.get("consumer_name"), a.get("consumer_id")),
        _control("CO-CD-003"),
    ]


def consumer_evidence_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    sections = [
        {"heading": "1. OBJETO DE LA MATRIZ", "paragraphs": ["La matriz vincula cada hecho y pretensión con la evidencia disponible y evita que documentos correspondientes a un mecanismo sean utilizados de forma descontextualizada para otro. Los originales deben conservarse sin edición y las copias de trabajo deben minimizar datos innecesarios." ]},
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — MATRIZ PROBATORIA DEL MECANISMO")
    sections.extend([
        {"heading": "2. CONTROL DE CIERRE", "numbered": ["Conservar la respuesta de fondo.", "Verificar la ejecución material de la solución.", "Conservar comprobantes de devolución, recogida, cambio, reparación o reversión.", "Confirmar que no existan cargos posteriores o devoluciones duplicadas.", "Documentar cualquier escalamiento ante autoridad o jurisdicción competente."]},
        _control("CO-CD-003"),
    ])
    return sections


# ---------------------------------------------------------------------------
# CO-CD-004 — cobro, acuerdo y pagaré
# ---------------------------------------------------------------------------


def debt_diagnostic_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    c = _calc(result)
    sections = [
        {"heading": "1. OBJETO DEL DIAGNÓSTICO", "paragraphs": ["El diagnóstico reconstruye el origen, evolución, exigibilidad y saldo de la obligación antes de producir un requerimiento, acuerdo, pagaré o documento de cierre. El sistema no debe convertir una cifra unilateral en reconocimiento de deuda ni generar un título sobre conceptos que no puedan explicarse mediante el negocio causal, los pagos y los soportes del expediente." ]},
        {"heading": "2. RECONCILIACIÓN ECONÓMICA", "table": [
            ["Concepto", "Valor"],
            ["Capital original", _money(c.get("principal"))],
            ["Pagos previos", _money(c.get("partial_payments_total"))],
            ["Capital esperado", _money(c.get("expected_principal_balance"))],
            ["Otros cargos soportados", _money(c.get("other_charges"))],
            ["Saldo explicado", _money(c.get("explained_balance"))],
            ["Saldo informado", _money(c.get("reported_balance"))],
            ["Diferencia", _money(c.get("balance_difference"))],
            ["Conciliado", "Sí" if c.get("balance_reconciled") else "No; requiere revisión"],
        ]},
        {"heading": "3. EXIGIBILIDAD Y DOCUMENTOS CAUSALES", "numbered": [
            "Identificar el contrato, factura, título, orden, acta o documento que origina la obligación.",
            "Verificar entrega, cumplimiento de condiciones, vencimiento y cualquier objeción de la contraparte.",
            "Incorporar todos los pagos, notas crédito, compensaciones y retenciones confirmadas antes de fijar el saldo.",
            "Separar capital, intereses y gastos y prohibir cargos globales cuya causa no pueda demostrarse.",
            "Comprobar cesiones, representación, garantías y cualquier proceso judicial o de insolvencia relacionado.",
        ]},
        {"heading": "4. CONTROL DE INTERESES", "table": [
            ["Variable", "Resultado"],
            ["Tasa informada", _value(c.get("interest_rate_input"))],
            ["Periodicidad", _value(c.get("interest_period"))],
            ["Modalidad", _value(c.get("interest_modality"))],
            ["Equivalente efectivo anual", _value(c.get("effective_annual_rate"))],
            ["Límite de referencia", _value(c.get("maximum_reference_ea"))],
            ["Vigencia parámetro", f"{_date(c.get('interest_valid_from'))} a {_date(c.get('interest_valid_to'))}"],
            ["Fuente paramétrica", _value(c.get("interest_resolution"))],
        ], "paragraphs": ["La plataforma no debe congelar una tasa futura dentro de una plantilla. Cada liquidación de mora debe registrar el parámetro oficial vigente para el período, convertir la tasa de manera reproducible y evitar capitalización no permitida o cobros duplicados." ]},
        {"heading": "5. PAGARÉ Y GARANTÍAS", "paragraphs": ["La solicitud de un pagaré no sustituye el negocio causal. Si el título conserva espacios, la carta de instrucciones debe identificar exactamente qué campos pueden completarse, cuándo, con qué fórmula y qué conceptos están excluidos. No se presume solidaridad personal del representante legal ni se crea una garantía real sin documento y formalidades independientes." ]},
        {"heading": "6. ALERTAS DEL MOTOR", "bullets": [str(x.get("message") if isinstance(x, dict) else x) for x in c.get("issues") or []] + [str(x) for x in c.get("assumptions") or []]},
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — MATRICES DEL MOTOR ECONÓMICO")
    sections.append(_control("CO-CD-004", "Un proceso ejecutivo, insolvencia, cesión controvertida o pagaré perdido bloquean la ruta automática ordinaria."))
    return sections


def collection_letter_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    creditor = a.get("creditor_name") or a.get("creditor")
    debtor = a.get("debtor_name") or a.get("debtor")
    return [
        {"heading": "ASUNTO Y NATURALEZA PREJURÍDICA", "paragraphs": [f"{_value(creditor, 'La parte acreedora')} comunica a {_value(debtor, 'la parte deudora')} el estado preliminar de la obligación y propone una instancia de verificación y negociación antes de evaluar otras actuaciones de recuperación. La comunicación no constituye una orden judicial, embargo, demanda ni amenaza de medidas que no hayan sido efectivamente adoptadas por autoridad competente." ]},
        {"heading": "I. ESTADO DE CUENTA", "table": [["Concepto", "Valor"], ["Capital original", _money(c.get("principal"))], ["Pagos", _money(c.get("partial_payments_total"))], ["Cargos soportados", _money(c.get("other_charges"))], ["Saldo informado", _money(c.get("reported_balance"))]]},
        {"heading": "II. DERECHO DE CONTRADICCIÓN", "paragraphs": ["Antes de formalizar un reconocimiento o título, la parte destinataria podrá controvertir el origen, las entregas, facturas, pagos, créditos, compensaciones, exigibilidad, intereses, identidad del acreedor o cualquier otro componente del saldo. La objeción deberá vincularse, cuando sea posible, con un concepto, valor y soporte concreto." ]},
        {"heading": "III. PROPUESTA DE SOLUCIÓN", "numbered": ["Confirmar o conciliar el saldo real.", "Definir una fecha o plan de pago compatible con la capacidad y el interés negocial de las partes.", "Documentar las concesiones, intereses, quitas o gastos que formen parte del acuerdo.", "Evitar solidaridad implícita y garantías no consentidas.", "Expedir recibos y estado de cuenta después de cada pago."]},
        {"heading": "IV. COBRANZA Y PRIVACIDAD", "paragraphs": ["Las gestiones deberán utilizar canales legítimos, lenguaje respetuoso y medidas de protección de datos. La obligación no debe divulgarse a referencias personales, familiares, compañeros o terceros ajenos al cobro, ni presentarse una actuación prejurídica como si fuera una decisión judicial." ]},
        _signature("PARTE ACREEDORA", creditor),
        _control("CO-CD-004"),
    ]


def payment_agreement_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    c = _calc(result)
    schedule = (c.get("payment_schedule") or {}).get("rows") if isinstance(c.get("payment_schedule"), dict) else []
    rows = [["Cuota", "Fecha", "Valor", "Estado"]]
    for row in schedule or []:
        rows.append([_value(row.get("number")), _date(row.get("due_date")), _money(row.get("amount")), _value(row.get("status"), "Pendiente")])
    sections = [
        {"heading": "CONSIDERACIONES", "numbered": [
            "Que las partes identificaron el negocio causal y tuvieron oportunidad de revisar sus soportes.",
            f"Que el saldo informado para la negociación es {_money(c.get('reported_balance'))} y el valor total del acuerdo es {_money(c.get('agreement_total'))}.",
            "Que los pagos, quitas, intereses o cargos que expliquen una diferencia deben constar expresamente y no presumirse.",
            "Que el acuerdo regula la forma de pago y no produce novación salvo declaración inequívoca y jurídicamente válida de las partes.",
            "Que cualquier pagaré o garantía será complementario y no permitirá cobrar valores ya pagados ni conceptos ajenos al acuerdo.",
        ]},
        {"heading": "PRIMERA: OBJETO Y SALDO CONCILIADO", "_type": "clause", "paragraphs": [f"El acuerdo tiene por objeto fijar las condiciones bajo las cuales la parte deudora atenderá la obligación identificada en el expediente. El valor total informado por el motor para el acuerdo es {_money(c.get('agreement_total'))}, sujeto a que la reconciliación económica, el origen y los pagos hayan sido confirmados por ambas partes antes de la firma." ]},
        {"heading": "SEGUNDA: NEGOCIO CAUSAL Y NO NOVACIÓN", "_type": "clause", "paragraphs": ["Los contratos, facturas, entregas, notas crédito, comprobantes y demás documentos del negocio original conservan su valor probatorio. El cambio de plazo, el cronograma o la suscripción de un título complementario no implica por sí solo la sustitución integral de la obligación original. Cualquier efecto novatorio requerirá una manifestación expresa y suficientemente determinada." ]},
        {"heading": "TERCERA: CRONOGRAMA", "_type": "clause", "paragraphs": ["Las cuotas y fechas serán exclusivamente las registradas en el cronograma aceptado. Las modificaciones deberán documentarse mediante una nueva revisión; no podrá alterarse retrospectivamente el historial de pagos para hacer coincidir el saldo con una cifra diferente." ], "table": rows},
        {"heading": "CUARTA: INTERESES Y LÍMITE", "_type": "clause", "paragraphs": [f"Cuando se hayan pactado intereses, la tasa deberá poder expresarse y auditarse en términos equivalentes, respetar el límite aplicable y corresponder al período real. El motor registra como equivalente efectivo anual {_value(c.get('effective_annual_rate'))} y como límite de referencia {_value(c.get('maximum_reference_ea'))}; ambos parámetros requieren revalidación en la fecha de uso cuando sean dinámicos. No se admite capitalización automática de intereses ni cobro simultáneo de conceptos incompatibles." ]},
        {"heading": "QUINTA: PAGOS, IMPUTACIÓN Y RECIBOS", "_type": "clause", "paragraphs": ["Cada pago deberá quedar asociado con fecha, valor, cuota, capital, interés procedente, gastos soportados y saldo posterior. Los pagos anticipados reducirán el saldo conforme a la instrucción válida de la parte deudora y al régimen aplicable, sin crear una penalidad que no haya sido jurídicamente acordada." ]},
        {"heading": "SEXTA: INCUMPLIMIENTO, REQUERIMIENTO Y ACELERACIÓN", "_type": "clause", "paragraphs": ["La aceleración no se presumirá por el solo retraso. Antes de exigir cuotas futuras deberá verificarse el evento pactado, el requerimiento correspondiente, cualquier oportunidad de subsanación y la fecha efectiva de la declaración. La liquidación del saldo acelerado deberá descontar todos los pagos y no podrá calcular mora retroactivamente sobre capital que aún no era exigible." ]},
        {"heading": "SÉPTIMA: PAGARÉ Y GARANTÍAS", "_type": "clause", "paragraphs": ["Si las partes utilizan un pagaré, este será complementario, deberá reflejar el saldo real y no convertirá al representante de una sociedad en obligado personal salvo aceptación expresa en una calidad distinta. Las garantías personales o reales requerirán documentación específica y no podrán deducirse de una firma meramente representativa." ]},
        {"heading": "OCTAVA: DATOS Y COBRANZA", "_type": "clause", "paragraphs": ["Los datos se utilizarán para ejecutar, acreditar y cobrar el acuerdo dentro de las finalidades permitidas. Las gestiones de cobranza deberán ser respetuosas, trazables y no divulgarán la obligación a terceros no autorizados. Cualquier reporte a operadores de información requerirá el cumplimiento independiente de sus presupuestos." ]},
        {"heading": "NOVENA: CIERRE", "_type": "clause", "paragraphs": ["El pago total producirá un cierre documentado: estado de cuenta en cero, paz y salvo sobre las obligaciones identificadas, cancelación o devolución del título cuando corresponda, actualización de registros y archivo de la evidencia. Una comunicación de aprobación sin ejecución económica no equivale al cierre." ]},
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — ESTADO ECONÓMICO Y CRONOGRAMA DEL MOTOR")
    sections.append(_control("CO-CD-004"))
    return sections


def promissory_note_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    debtor = a.get("debtor_name") or a.get("debtor")
    creditor = a.get("creditor_name") or a.get("creditor")
    return [
        {"heading": "PAGARÉ — IDENTIFICACIÓN DEL TÍTULO", "table": [["Elemento", "Información"], ["Suscriptor", _value(debtor)], ["Beneficiario", _value(creditor)], ["Valor del acuerdo", _money(c.get("agreement_total") or c.get("reported_balance"))], ["Forma de vencimiento", _value(a.get("maturity_form"))], ["Fecha", _date(a.get("document_date"))]]},
        {"heading": "PROMESA DE PAGO", "paragraphs": [f"La parte suscriptora promete pagar incondicionalmente a la orden de {_value(creditor, 'la parte beneficiaria')} la suma incorporada en este título, de acuerdo con la forma de vencimiento y el cronograma expresamente relacionados. Los pagos efectuados reducirán el saldo y deberán reflejarse en los registros y recibos correspondientes." ]},
        {"heading": "PRIMERA: INTERESES", "_type": "clause", "paragraphs": ["Los intereses solo se causarán cuando exista un pacto válido o una regla legal aplicable y nunca excederán el límite correspondiente. La liquidación deberá identificar la tasa y vigencia utilizadas. No se capitalizarán automáticamente intereses ni se incorporarán intereses futuros no causados." ]},
        {"heading": "SEGUNDA: PAGOS PARCIALES", "_type": "clause", "paragraphs": ["Todo pago parcial deberá disminuir el saldo real y constar en recibo o registro trazable. El título no podrá presentarse por valores ya pagados ni conservar un saldo nominal diferente del que resulte de la ejecución efectiva del acuerdo." ]},
        {"heading": "TERCERA: ACELERACIÓN", "_type": "clause", "paragraphs": ["Cuando el acuerdo contemple vencimiento anticipado, su ejercicio deberá obedecer al evento y procedimiento pactados. El vencimiento anticipado no autoriza fechas retroactivas ni intereses de mora sobre cuotas futuras antes de la declaración jurídicamente procedente." ]},
        {"heading": "CUARTA: NEGOCIO CAUSAL", "_type": "clause", "paragraphs": ["El título se suscribe como instrumento complementario del negocio y acuerdo identificados en el expediente. La tenencia del pagaré no autoriza desconocer pagos, créditos, excepciones procedentes ni la realidad económica documentada." ]},
        {"heading": "QUINTA: CANCELACIÓN Y ENTREGA", "_type": "clause", "paragraphs": ["Pagada totalmente la obligación, la parte tenedora deberá cancelar el título y devolverlo o dejar evidencia suficiente de su inutilización jurídica, según el soporte utilizado, evitando la circulación de duplicados como si existieran obligaciones vigentes independientes." ]},
        _signature("SUSCRIPTOR", debtor, a.get("debtor_id")),
        _control("CO-CD-004"),
    ]


def instruction_letter_m33(a: dict, result: dict) -> list[dict]:
    return [
        {"heading": "1. ALCANCE RESTRICTIVO", "paragraphs": ["La carta de instrucciones solo se utiliza cuando el pagaré conserva espacios permitidos. No habilita a modificar la identidad del suscriptor, beneficiario, negocio causal, moneda, firma o naturaleza del título ni a incorporar obligaciones futuras o pertenecientes a terceros." ]},
        {"heading": "2. CAMPOS AUTORIZADOS", "numbered": ["Valor exigible, limitado al capital insoluto y conceptos jurídicamente procedentes.", "Fecha de vencimiento anticipado, únicamente cuando se active válidamente el evento previsto.", "Lugar de pago, cuando el título lo permita y no haya quedado determinado.", "Fecha de diligenciamiento, correspondiente a la actuación real y nunca retroactiva."]},
        {"heading": "3. EVENTO DE DILIGENCIAMIENTO", "numbered": ["Verificar el incumplimiento previsto.", "Enviar el requerimiento exigido por el acuerdo.", "Permitir el período de subsanación cuando corresponda.", "Descontar todos los pagos y créditos.", "Elaborar una liquidación discriminada.", "Conservar copia del título diligenciado y de la liquidación utilizada."]},
        {"heading": "4. VALORES EXCLUIDOS", "numbered": ["Capital ya pagado.", "Intereses futuros no causados.", "Intereses sobre intereses no permitidos.", "Gastos internos no trasladables.", "Cláusulas penales inexistentes.", "Honorarios automáticos no soportados.", "Obligaciones diferentes del negocio identificado."]},
        _signature("OTORGANTE DE LAS INSTRUCCIONES", a.get("debtor_name") or a.get("debtor"), a.get("debtor_id")),
        _control("CO-CD-004"),
    ]


def payment_schedule_m33(a: dict, result: dict, legacy: list[dict]) -> list[dict]:
    c = _calc(result)
    schedule = c.get("payment_schedule") if isinstance(c.get("payment_schedule"), dict) else {}
    rows = [["Cuota", "Fecha", "Valor", "Estado"]]
    for row in schedule.get("rows") or []:
        rows.append([_value(row.get("number")), _date(row.get("due_date")), _money(row.get("amount")), _value(row.get("status"), "Pendiente")])
    sections = [
        {"heading": "1. CRONOGRAMA VIGENTE", "table": rows},
        {"heading": "2. REGLAS DE ACTUALIZACIÓN", "numbered": ["No eliminar movimientos históricos.", "Registrar pagos con fecha y comprobante.", "Separar capital e intereses.", "Recalcular las cuotas futuras cuando exista pago anticipado conforme al acuerdo.", "Crear una nueva revisión cuando cambie el plan y conservar la versión anterior.", "Si existe aceleración, registrar fecha, saldo y fundamento de la declaración."]},
    ]
    _append_legacy_tables(sections, legacy, "ANEXO No. 1 — CRONOGRAMA HISTÓRICO DEL MOTOR")
    sections.append(_control("CO-CD-004"))
    return sections


def settlement_certificate_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "PAZ Y SALVO O CONSTANCIA DE CIERRE", "paragraphs": ["Esta constancia solo podrá utilizarse cuando el expediente acredite saldo cero y la extinción de las obligaciones expresamente identificadas. No deberá generarse con un saldo positivo ni utilizarse para cubrir negocios diferentes." ]},
        {"heading": "1. VERIFICACIÓN ECONÓMICA", "table": [["Concepto", "Resultado"], ["Saldo informado", _money(c.get("reported_balance"))], ["Pagos registrados", _money(c.get("partial_payments_total"))], ["Estado de cierre", "Apto solo si el saldo es cero y existe evidencia de pago total"]]},
        {"heading": "2. EFECTOS DEL CIERRE", "numbered": ["Expedir constancia de saldo cero respecto de las obligaciones identificadas.", "Cancelar y devolver o inutilizar jurídicamente el pagaré cuando exista.", "Cerrar la cartera y detener nuevas gestiones de cobro sobre el saldo extinguido.", "Actualizar registros o reportes que deban reflejar el pago total.", "Conservar únicamente la documentación necesaria para obligaciones legales, auditoría y defensa de derechos."]},
        {"heading": "3. ALCANCE LIMITADO", "paragraphs": ["El paz y salvo se limita al negocio y obligaciones individualizadas. No implica renuncia frente a relaciones diferentes ni puede utilizarse para ocultar obligaciones recíprocas que no formaron parte del acuerdo de cierre." ]},
        _signature("PARTE ACREEDORA", a.get("creditor_name") or a.get("creditor")),
        _control("CO-CD-004"),
    ]


def payment_receipt_m33(a: dict, result: dict) -> list[dict]:
    c = _calc(result)
    return [
        {"heading": "RECIBO DE PAGO Y ACTUALIZACIÓN DE SALDO", "table": [["Campo", "Información"], ["Deudor", _value(a.get("debtor_name") or a.get("debtor"))], ["Fecha del pago", _date(a.get("last_payment_date") or a.get("payment_date"))], ["Valor registrado", _money(a.get("last_payment_amount") or a.get("partial_payments_total"))], ["Saldo reportado", _money(c.get("reported_balance"))]]},
        {"heading": "1. IMPUTACIÓN", "paragraphs": ["El recibo debe identificar a qué cuota, capital, interés o gasto soportado se imputó el pago. Si existe un excedente o pago anticipado, la instrucción y el efecto sobre el cronograma deberán registrarse de forma separada." ]},
        {"heading": "2. EFECTO", "paragraphs": ["La expedición de un recibo parcial no constituye paz y salvo total salvo que el documento lo declare expresamente después de verificar saldo cero. El nuevo saldo debe poder reconciliarse con todos los movimientos anteriores." ]},
        _control("CO-CD-004"),
    ]


# ---------------------------------------------------------------------------
# Wrapper sobre document_specs
# ---------------------------------------------------------------------------


def _replace(specs: list[dict], kind: str, sections: list[dict], *, subtitle: str | None = None) -> None:
    for spec in specs:
        if spec.get("kind") == kind:
            spec["sections"] = sections
            spec["document_standard"] = "M33.0"
            spec["subtitle"] = subtitle or f"Composición jurídica profunda M33.0 · {spec.get('subtitle', '')}".strip(" ·")
            return


def _legacy_sections(specs: list[dict], kind: str) -> list[dict]:
    for spec in specs:
        if spec.get("kind") == kind:
            return deepcopy(spec.get("sections") or [])
    return []


def _add_spec(specs: list[dict], *, kind: str, title: str, suffix: str, sections: list[dict], metadata: Any) -> None:
    if any(spec.get("kind") == kind for spec in specs):
        return
    specs.append({
        "kind": kind,
        "title": title,
        "filename_suffix": suffix,
        "subtitle": "Composición jurídica profunda M33.0",
        "sections": sections,
        "metadata": metadata,
        "document_standard": "M33.0",
    })


def document_specs_m33(case_id, code, answers, result, product, generated_at, question_rows):
    specs = legacy_document_specs(case_id, code, answers, result, product, generated_at, question_rows)
    if code not in M33_PROCEDURAL_CODES or result.get("risk") == "red":
        return specs

    metadata = specs[0].get("metadata") if specs else []

    if code == "CO-LA-001":
        _replace(specs, "calculation", labor_calculation_m33(answers, result, _legacy_sections(specs, "calculation")))
        _replace(specs, "claim", labor_claim_m33(answers, result))
        # La matriz histórica sigue disponible, pero se convierte en una matriz de
        # cotejo M33.0 y se complementa con los documentos faltantes del expediente.
        _replace(specs, "evidence_matrix", labor_difference_matrix_m33(answers, result), subtitle="Matriz probatoria y de diferencias M33.0")
        _add_spec(specs, kind="labor_diagnostic", title="Diagnóstico jurídico y ficha de supuestos laborales", suffix="diagnostico_juridico_laboral", sections=labor_diagnostic_m33(answers, result), metadata=metadata)
        _add_spec(specs, kind="labor_support_request", title="Solicitud autónoma de soportes laborales", suffix="solicitud_soportes_laborales", sections=labor_support_request_m33(answers, result), metadata=metadata)
        _add_spec(specs, kind="labor_deadline_calendar", title="Calendario de seguimiento, prescripción y cierre", suffix="calendario_laboral", sections=labor_deadline_calendar_m33(answers, result), metadata=metadata)

    elif code == "CO-CD-001":
        _replace(specs, "habeas_consultation", habeas_consultation_m33(answers, result))
        _replace(specs, "habeas_claim", habeas_claim_m33(answers, result))
        _replace(specs, "habeas_reiteration", habeas_reiteration_m33(answers, result))
        _replace(specs, "identity_theft_protocol", identity_theft_m33(answers, result, _legacy_sections(specs, "identity_theft_protocol")))
        # Las matrices, autoridad y calendario históricos se conservan porque ya
        # contienen cálculo temporal específico; se marcan como M33 y se sanea su
        # control final sin alterar los resultados del motor.
        for kind in ("habeas_authority_escalation", "habeas_evidence_matrix", "habeas_deadline_calendar"):
            for spec in specs:
                if spec.get("kind") == kind:
                    spec["document_standard"] = "M33.0"
                    spec["subtitle"] = "Matriz o ruta histórica preservada · composición M33.0 pendiente de aprobación"

    elif code == "CO-CD-003":
        _replace(specs, "consumer_mechanism_diagnosis", consumer_diagnosis_m33(answers, result))
        replacements: dict[str, Callable[[dict, dict], list[dict]]] = {
            "warranty_claim": warranty_claim_m33,
            "withdrawal_notice": withdrawal_m33,
            "payment_reversal_request": reversal_m33,
            "recurring_debit_revocation": recurring_debit_m33,
            "ecommerce_non_delivery_termination": non_delivery_m33,
        }
        for kind, function in replacements.items():
            if any(spec.get("kind") == kind for spec in specs):
                _replace(specs, kind, function(answers, result))
        _replace(specs, "consumer_evidence_matrix", consumer_evidence_m33(answers, result, _legacy_sections(specs, "consumer_evidence_matrix")))
        for spec in specs:
            if spec.get("kind") == "consumer_deadline_calendar":
                spec["document_standard"] = "M33.0"
                spec["subtitle"] = "Calendario determinístico preservado · control M33.0"

    elif code == "CO-CD-004":
        _replace(specs, "debt_diagnostic", debt_diagnostic_m33(answers, result, _legacy_sections(specs, "debt_diagnostic")))
        for spec in specs:
            if spec.get("kind") in {"account_statement", "collection_evidence_matrix"}:
                spec["document_standard"] = "M33.0"
                spec["subtitle"] = "Motor económico preservado · control documental M33.0"
        if any(spec.get("kind") == "collection_letter" for spec in specs):
            _replace(specs, "collection_letter", collection_letter_m33(answers, result))
        if any(spec.get("kind") == "payment_agreement" for spec in specs):
            _replace(specs, "payment_agreement", payment_agreement_m33(answers, result, _legacy_sections(specs, "payment_agreement")))
        if any(spec.get("kind") == "payment_schedule" for spec in specs):
            _replace(specs, "payment_schedule", payment_schedule_m33(answers, result, _legacy_sections(specs, "payment_schedule")))
        if any(spec.get("kind") == "promissory_note" for spec in specs):
            _replace(specs, "promissory_note", promissory_note_m33(answers, result))
        if any(spec.get("kind") == "instruction_letter" for spec in specs):
            _replace(specs, "instruction_letter", instruction_letter_m33(answers, result))
        if any(spec.get("kind") == "payment_receipt" for spec in specs):
            _replace(specs, "payment_receipt", payment_receipt_m33(answers, result))
        if any(spec.get("kind") == "settlement_certificate" for spec in specs):
            _replace(specs, "settlement_certificate", settlement_certificate_m33(answers, result))

    return specs
