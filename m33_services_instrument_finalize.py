from __future__ import annotations

"""Capa final de instrumento visible para CO-EM-003 M33.0.

Profundiza la redacción contractual que reciben y firman las partes, corrige
inconsistencias entre respuestas y cláusulas y retira lenguaje interno de plataforma.
La gobernanza, aprobaciones y trazabilidad permanecen fuera del instrumento.
"""

from copy import deepcopy
import re
from typing import Any

from m33_services_legal_finalize import compose_services_m33_final


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraphs(section: dict, *values: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [value for value in values if str(value or "").strip()]


def _format_nit_match(match: re.Match[str]) -> str:
    base = match.group(1)
    digit = match.group(2)
    groups = []
    while base:
        groups.append(base[-3:])
        base = base[:-3]
    return "NIT " + ".".join(reversed(groups)) + f"-{digit}"


def _normalize_visible_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = re.sub(r"\bNIT\s+(\d{7,12})-(\d)\b", _format_nit_match, value)
    text = text.replace("servicios independientes de diagnóstico, diseño y mejora", "diagnóstico, diseño y mejora")
    return text


def _normalize_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _normalize_visible_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_normalize_visible_text(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_normalize_visible_text(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        parties = []
        for party in result["parties"]:
            if not isinstance(party, dict):
                parties.append(party)
                continue
            parties.append({key: _normalize_visible_text(value) for key, value in party.items()})
        result["parties"] = parties
    return result


_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos", 500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"}


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


def _number_words_es(number: int) -> str:
    number = int(number)
    if number < 1000:
        return _under_thousand(number)
    if number < 1_000_000:
        thousands, remainder = divmod(number, 1000)
        prefix = "mil" if thousands == 1 else f"{_number_words_es(thousands)} mil"
        return prefix + (f" {_number_words_es(remainder)}" if remainder else "")
    if number < 1_000_000_000:
        millions, remainder = divmod(number, 1_000_000)
        prefix = "un millón" if millions == 1 else f"{_number_words_es(millions)} millones"
        return prefix + (f" {_number_words_es(remainder)}" if remainder else "")
    billions, remainder = divmod(number, 1_000_000_000)
    prefix = "mil millones" if billions == 1 else f"{_number_words_es(billions)} mil millones"
    return prefix + (f" {_number_words_es(remainder)}" if remainder else "")


def _cop(amount: Any) -> tuple[str, str]:
    try:
        integer = int(round(float(amount)))
    except (TypeError, ValueError):
        return str(amount or "valor pendiente de determinación"), "valor pendiente de determinación"
    formatted = f"${integer:,.0f}".replace(",", ".")
    words = _number_words_es(integer)
    # Apócope contractual antes de "pesos".
    words = re.sub(r"\bveintiuno$", "veintiún", words)
    words = re.sub(r"\by uno$", "y un", words)
    words = re.sub(r"\buno$", "un", words)
    return f"COP {formatted}", f"{words} pesos moneda corriente"


def _contact(answers: dict, prefix: str, fallback: str) -> str:
    identification = _read(answers, f"{prefix}.identification", {})
    identification = identification if isinstance(identification, dict) else {}
    name = str(identification.get("name") or fallback).strip()
    email = str(identification.get("email") or "").strip()
    domicile = str(identification.get("domicile") or "").strip()
    values = [name]
    if email:
        values.append(f"correo {email}")
    if domicile:
        values.append(f"domicilio {domicile}")
    return ", ".join(values)


def compose_services_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_services_m33_final(answers))

    service_object = str(_read(answers, "service.object") or "ejecutar las actividades profesionales descritas en el Anexo No. 1").strip()
    expected_result = str(_read(answers, "service.expected_result") or "producir y entregar los resultados verificables definidos por las partes").strip()
    included = _read(answers, "scope.included", [])
    included = included if isinstance(included, list) else []
    excluded = _read(answers, "scope.excluded", [])
    excluded = excluded if isinstance(excluded, list) else []
    payment_term = str(_read(answers, "fees.payment_term") or "dentro del término pactado después de la aceptación y de la presentación del documento de cobro válido").strip()
    amount_display, amount_words = _cop(_read(answers, "fees.amount", 0))
    taxes = str(_read(answers, "fees.taxes") or "con el tratamiento tributario que legalmente corresponda").strip()
    no_exclusivity = str(_read(answers, "independence.no_exclusivity") or "").strip()
    termination_rules = str(_read(answers, "termination.rules") or "las causales previstas en este contrato y en la ley").strip()
    cure_period = str(_read(answers, "termination.cure_period") or "un plazo razonable cuando el incumplimiento sea subsanable").strip()
    client_contact = _contact(answers, "client", "EL CONTRATANTE")
    contractor_contact = _contact(answers, "contractor", "EL CONTRATISTA")

    final: list[dict] = []
    for original in composition.get("sections") or []:
        section = _normalize_section(original)
        heading_cf = str(section.get("heading") or "").strip().casefold()
        is_clause = section.get("_type") == "clause"

        if heading_cf == "consideraciones":
            _paragraphs(
                section,
                f"PRIMERA: EL CONTRATANTE ha identificado una necesidad especializada relacionada con {service_object}, cuya atención se pretende estructurar por resultados verificables y no mediante la provisión permanente de un cargo sometido a subordinación laboral.",
                f"SEGUNDA: EL CONTRATISTA manifiesta contar con organización, experiencia, medios y capacidad de gestión suficientes para asumir el encargo con autonomía técnica, administrativa y operativa, respondiendo por la adecuada dirección de su propio equipo y por los riesgos que se encuentren bajo su esfera de control.",
                f"TERCERA: Las partes consideran esencial que el alcance se mida por entregables, hitos, criterios objetivos de aceptación y evidencia de cumplimiento. El resultado esperado consiste en {expected_result}, sin que una coordinación legítima del proyecto pueda utilizarse para ampliar informalmente el objeto, imponer disponibilidad personal indefinida o sustituir el procedimiento de control de cambios.",
                "CUARTA: Las partes reconocen que la ejecución puede involucrar información reservada, activos de propiedad intelectual, datos personales, infraestructura tecnológica, proveedores y riesgos de seguridad. Tales materias requieren reglas específicas de acceso, uso, responsabilidad, trazabilidad, devolución o eliminación, sin presumir transferencias de derechos ni autorizaciones más amplias que las expresamente pactadas.",
                "QUINTA: El equilibrio económico del contrato depende de que las obligaciones de cooperación del CONTRATANTE, las dependencias del proyecto y los cambios de alcance sean identificables. Los retrasos o sobrecostos atribuibles a información, decisiones, accesos o terceros bajo control de una parte deberán documentarse y tratarse conforme a su incidencia real, evitando trasladar automáticamente a la otra parte riesgos que no controla.",
                "SEXTA: Las partes desean que el presente instrumento sea suficientemente operativo para prevenir controversias y, al mismo tiempo, conserve evidencia útil sobre entregas, observaciones, cambios, aceptación, pagos, incidentes, terminación y cierre. Su interpretación atenderá la buena fe, la realidad de la ejecución y las normas imperativas aplicables en Colombia.",
            )

        elif is_clause and _has(section, "OBJETO"):
            _paragraphs(
                section,
                f"EL CONTRATISTA se obliga a {service_object}, con autonomía técnica, administrativa y operativa y dentro de los límites establecidos en el contrato y sus anexos. El encargo se entiende orientado a {expected_result}.",
                "El objeto se delimita por los entregables, criterios de aceptación, exclusiones, dependencias y supuestos expresamente documentados. Ninguna reunión, mensaje, instrucción operativa o tolerancia podrá ampliar materialmente el alcance, alterar el precio, modificar el plazo o convertir el vínculo en disponibilidad personal indefinida sin el procedimiento de cambio aplicable.",
                "EL CONTRATISTA asume una obligación profesional de ejecución diligente respecto de las actividades bajo su control; no garantiza hechos, aprobaciones, decisiones, disponibilidades o resultados externos que dependan exclusivamente del CONTRATANTE, de autoridades o de terceros, salvo que una obligación concreta haya sido asumida expresamente por escrito.",
            )

        elif is_clause and _has(section, "ALCANCE Y EXCLUSIONES"):
            included_text = "; ".join(str(value).strip().rstrip(".") for value in included if str(value).strip())
            excluded_text = "; ".join(str(value).strip().rstrip(".") for value in excluded if str(value).strip())
            _paragraphs(
                section,
                "El alcance comprende las actividades razonablemente necesarias para producir los resultados definidos en el Anexo No. 1, siempre que sean compatibles con la estimación económica, el cronograma, las dependencias y el perfil profesional contratado. " + (f"A título de precisión, se encuentran incluidas: {included_text}." if included_text else ""),
                (f"Se encuentran expresamente excluidas: {excluded_text}. " if excluded_text else "") + "También se excluyen soporte permanente, disponibilidad fuera del plazo, adquisiciones no autorizadas y cualquier actividad que modifique materialmente esfuerzo, riesgo, arquitectura, tratamiento de datos, propiedad intelectual o responsabilidades sin aprobación del cambio correspondiente.",
                "Una actividad no se considerará incluida únicamente por ser conveniente o estar relacionada temáticamente con el proyecto. Cuando exista duda razonable, las partes documentarán si se trata de una aclaración del alcance existente, una corrección de incumplimiento o un cambio sujeto a ajuste de plazo, precio y riesgos.",
            )

        elif is_clause and _has(section, "ENTREGABLES Y TRAZABILIDAD"):
            _paragraphs(
                section,
                "Cada entregable deberá poder individualizarse por nombre o código, versión, formato, responsable, fecha o hito, insumos, dependencias y criterio objetivo de aceptación. La entrega se realizará por el canal o repositorio acordado y deberá permitir acreditar razonablemente su integridad, fecha y destinatario.",
                "EL CONTRATISTA conservará evidencia suficiente de entrega, observaciones, correcciones y aceptación. EL CONTRATANTE formulará sus observaciones vinculándolas al requisito o criterio que considere incumplido. Las solicitudes que introduzcan funcionalidades, alcance, calidad, volumen o condiciones nuevas se tramitarán como cambio y no como defecto del entregable originalmente pactado.",
            )

        elif is_clause and _has(section, "HONORARIOS"):
            _paragraphs(
                section,
                f"Como contraprestación total por el alcance inicialmente contratado, EL CONTRATANTE pagará a EL CONTRATISTA la suma de {amount_display} ({amount_words}), {taxes}. El precio corresponde al alcance, entregables, supuestos y distribución de riesgos descritos en el contrato y no remunera disponibilidad personal, jornada laboral ni subordinación.",
                f"El pago se realizará {payment_term}. Los costos ordinarios de organización y ejecución de EL CONTRATISTA se entienden incorporados en el precio, salvo gastos reembolsables o adquisiciones que hayan sido expresamente autorizados bajo las condiciones del contrato.",
                "Toda variación económica deberá quedar documentada antes de su ejecución e identificar, como mínimo, la causa del cambio, alcance afectado, base de cálculo, impuestos, fecha, hito de pago y persona con facultad suficiente para aprobarla. La ejecución de una solicitud no autorizada no genera automáticamente derecho a un precio adicional, sin perjuicio de las reglas legales aplicables a prestaciones efectivamente solicitadas y recibidas.",
            )

        elif is_clause and _has(section, "ACEPTACIÓN") and not _has(section, "ACTA"):
            _paragraphs(
                section,
                "EL CONTRATANTE contará con cinco (5) días hábiles desde la entrega completa para aceptar o formular observaciones suficientemente determinadas. Cada observación deberá identificar el entregable, requisito o criterio afectado, la evidencia disponible y la corrección razonablemente esperada; no será suficiente una inconformidad genérica o una preferencia no pactada.",
                "Cuando las observaciones correspondan a un incumplimiento del criterio acordado, EL CONTRATISTA realizará la corrección procedente y presentará una nueva versión para verificación. Cuando constituyan una necesidad nueva o una modificación del resultado originalmente contratado, se tramitarán mediante control de cambios.",
                "El silencio no producirá por sí solo aceptación automática salvo pacto expreso aplicable al entregable concreto. El uso productivo, publicación, explotación o incorporación consciente de un entregable sin reserva podrá constituir evidencia relevante de aceptación respecto de la parte efectivamente utilizada, sin extinguir reclamos por defectos ocultos ni por obligaciones que deban sobrevivir.",
            )

        elif is_clause and _has(section, "EXCLUSIVIDAD Y NO COMPETENCIA"):
            if "no existe exclusividad" in no_exclusivity.casefold() or "no exclusividad" in no_exclusivity.casefold():
                _paragraphs(
                    section,
                    "El presente contrato no establece exclusividad general ni obligación de no competencia. EL CONTRATISTA podrá prestar servicios a terceros y EL CONTRATANTE podrá contratar otros proveedores, siempre que ello no implique incumplimiento de confidencialidad, uso indebido de activos protegidos, conflicto de interés no gestionado o afectación de obligaciones específicas ya asumidas.",
                    "Cuando surja un conflicto concreto por cliente, proyecto, información o interés incompatible, deberá informarse y gestionarse mediante separación de equipos, restricciones de acceso, recusación, autorización específica u otra medida proporcional. Cualquier restricción comercial adicional deberá pactarse expresamente, delimitar su alcance y someterse a las normas imperativas aplicables.",
                )
            else:
                _paragraphs(
                    section,
                    f"En materia de exclusividad y competencia regirá la siguiente condición particular: {no_exclusivity or 'no se presume exclusividad más allá de obligaciones específicas de conflicto de interés y confidencialidad'}. Cualquier restricción adicional deberá ser expresa, delimitada y compatible con las normas imperativas aplicables.",
                )

        elif is_clause and _has(section, "TERMINACIÓN ANTICIPADA"):
            _paragraphs(
                section,
                f"El contrato podrá terminar conforme a las siguientes reglas particulares: {termination_rules}. Cuando el incumplimiento sea susceptible de corrección, la parte cumplida concederá {cure_period}, contado desde una comunicación suficientemente determinada, salvo que la gravedad, urgencia, ilegalidad, riesgo de seguridad o naturaleza del incumplimiento hagan improcedente esperar su subsanación.",
                "Si se ha pactado terminación sin causa o por conveniencia, deberá respetarse el preaviso expresamente convenido. En tal evento se pagarán los entregables aceptados, el trabajo verificable y útil efectivamente ejecutado hasta la fecha de terminación y los compromisos no cancelables que hubiesen sido previamente autorizados, descontando anticipos no causados y valores que deban reintegrarse.",
                "La terminación no extingue las obligaciones que por su naturaleza deban sobrevivir, incluyendo confidencialidad, secretos empresariales, datos personales, propiedad intelectual, devolución de activos, conservación probatoria, pagos causados, responsabilidad por incumplimientos anteriores y cooperación razonable para el cierre.",
            )

        elif is_clause and _has(section, "NOTIFICACIONES"):
            _paragraphs(
                section,
                f"Para las comunicaciones contractuales ordinarias se utilizarán, mientras no sean modificados de manera trazable, los siguientes datos: {client_contact}; y {contractor_contact}. Las notificaciones deberán permitir acreditar razonablemente remitente, contenido, fecha y destinatario.",
                "Las comunicaciones operativas o de mensajería instantánea no sustituyen las notificaciones de incumplimiento, reclamación, cambio material, suspensión o terminación cuando el contrato exija una forma específica. Cada parte deberá informar oportunamente cambios de correo, domicilio o responsable contractual; hasta entonces podrán utilizarse válidamente los datos previamente informados, sin perjuicio de las formas especiales que una norma imperativa exija.",
            )

        elif is_clause and _has(section, "SOLUCIÓN ESCALONADA DE CONTROVERSIAS"):
            _paragraphs(
                section,
                "Las partes procurarán resolver de buena fe cualquier diferencia mediante negociación directa entre responsables con capacidad suficiente para proponer una solución. Si la controversia persiste, será escalada a los representantes con capacidad decisoria y posteriormente, cuando resulte jurídicamente procedente, a conciliación ante un centro o conciliador competente.",
                "El agotamiento de las etapas anteriores no será exigible cuando resulte incompatible con la finalidad de una medida cautelar, la preservación de evidencia, la protección urgente de información o datos, la prevención de un daño inminente o el ejercicio oportuno de un derecho sujeto a término. Si no se alcanza acuerdo, cualquiera de las partes podrá acudir a la jurisdicción competente conforme a las reglas legales aplicables.",
            )

        elif is_clause and _has(section, "FIRMA ELECTRÓNICA Y EJEMPLARES"):
            _paragraphs(
                section,
                "El contrato podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos o mecanismos electrónicos, el método deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad del acto, de acuerdo con las reglas aplicables.",
                "La fecha de celebración será la correspondiente a la última firma necesaria para perfeccionar el contrato. Cada parte tendrá acceso a una copia íntegra y la versión suscrita deberá preservarse sin modificaciones posteriores, conservando razonablemente su integridad y evidencia de aceptación.",
                "Las contrapartes o ejemplares suscritos forman un solo instrumento. Toda modificación material posterior deberá documentarse mediante una nueva versión, adenda u otro instrumento válido y requerirá la aceptación de quienes deban obligarse por ella.",
            )

        elif heading_cf == "1. objetivo operativo":
            _paragraphs(
                section,
                f"El objetivo operativo del encargo consiste en {service_object}, de manera que EL CONTRATISTA pueda {expected_result}. Las actividades del anexo se interpretarán como medios para alcanzar estos resultados verificables y no como una autorización abierta para incorporar trabajos ajenos al objeto o exigir disponibilidad permanente.",
            )

        elif heading_cf == "7. gobierno y raci":
            section["heading"] = "7. GOBIERNO Y MATRIZ DE RESPONSABILIDADES (RACI)"
            _paragraphs(
                section,
                "La matriz RACI identifica, para cada actividad relevante, quién ejecuta, quién aprueba, quién debe ser consultado y quién debe mantenerse informado. Su propósito es evitar vacíos de decisión y duplicidades; no modifica por sí sola las facultades legales de representación ni convierte la coordinación del proyecto en subordinación laboral.",
            )

        final.append(section)

    composition["sections"] = final
    composition.setdefault("maturity_answers", {})["services_instrument_finalized"] = True
    return composition


__all__ = ["compose_services_m33_instrument"]
