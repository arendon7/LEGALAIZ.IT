from __future__ import annotations

"""Pulido final del instrumento visible CO-AR-001 M33.0.

Opera después de la revisión jurídica sustantiva. Conserva intactas las reglas
imperativas de la Ley 820 de 2003 y la sección interna de fuentes/gobierno, pero
retira lenguaje de workspace del documento firmable y profundiza sus cláusulas
operativas, económicas, probatorias y de cierre.
"""

from copy import deepcopy
import re
from typing import Any

from m33_lease_legal_finalize import compose_lease_m33_final


_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos", 500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"}


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    number = _number(value)
    if number is None:
        return str(value or "valor no determinado").strip()
    return "COP $" + f"{int(round(number)):,}".replace(",", ".")


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
    number = int(number)
    if number < 1000:
        return _under_thousand(number)
    if number < 1_000_000:
        thousands, remainder = divmod(number, 1000)
        prefix = "mil" if thousands == 1 else f"{_number_words(thousands)} mil"
        return prefix + (f" {_number_words(remainder)}" if remainder else "")
    if number < 1_000_000_000:
        millions, remainder = divmod(number, 1_000_000)
        prefix = "un millón" if millions == 1 else f"{_number_words(millions)} millones"
        return prefix + (f" {_number_words(remainder)}" if remainder else "")
    billions, remainder = divmod(number, 1_000_000_000)
    prefix = "mil millones" if billions == 1 else f"{_number_words(billions)} mil millones"
    return prefix + (f" {_number_words(remainder)}" if remainder else "")


def _money_with_words(value: Any) -> str:
    number = _number(value)
    if number is None:
        return _money(value)
    integer = int(round(number))
    words = _number_words(integer)
    words = re.sub(r"\bveintiuno$", "veintiún", words)
    words = re.sub(r"\by uno$", "y un", words)
    words = re.sub(r"\buno$", "un", words)
    connector = " de" if integer >= 1_000_000 and integer % 1_000_000 == 0 else ""
    return f"{_money(integer)} ({words}{connector} pesos moneda corriente)"


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraphs(section: dict, *items: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [item for item in items if str(item or "").strip()]


def _public_polish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value
    replacements = (
        ("identificada en la ficha", "definida en el presente contrato y sus anexos"),
        ("descritos en la ficha e inventario", "descritos en el presente contrato, sus anexos y el inventario"),
        ("identificado en la ficha", "identificado en el presente contrato o anexo aplicable"),
        ("informadas en el expediente", "informadas por las partes y documentadas para la ejecución del contrato"),
        ("expediente de entrega", "acta e inventario de entrega"),
        ("Edificio Ejemplo P.H..", "Edificio Ejemplo P.H."),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    text = re.sub(r"(?<!\.)\.\.(?!\.)", ".", text)
    return text


def _polish_section(section: dict) -> dict:
    result = deepcopy(section)
    if result.get("_type") == "control":
        return result
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _public_polish(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_public_polish(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_public_polish(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        result["parties"] = [
            {key: _public_polish(value) for key, value in party.items()} if isinstance(party, dict) else party
            for party in result["parties"]
        ]
    return result


def _contact(answers: dict, prefix: str, label: str) -> str:
    block = _read(answers, f"{prefix}.identification", {})
    block = block if isinstance(block, dict) else {}
    name = str(block.get("name") or label).strip()
    email = str(block.get("email") or "").strip()
    address = str(block.get("address") or "").strip().rstrip(".")
    phone = str(block.get("phone") or "").strip()
    values = [name]
    if email:
        values.append(f"correo {email}")
    if address:
        values.append(f"dirección {address}")
    if phone:
        values.append(f"teléfono {phone}")
    return ", ".join(values)


def _rent_clause(answers: dict) -> tuple[str, str, str]:
    rent = _number(_read(answers, "rent.amount"))
    commercial = _number(_read(answers, "rent.values.commercial_value"))
    cadastral = _number(_read(answers, "rent.values.cadastral_value"))
    source_date = str(_read(answers, "rent.values.source_date") or "").strip()
    payment_day = _number(_read(answers, "rent.payment.day"))
    method = str(_read(answers, "rent.payment.method") or "canal trazable acordado").strip()
    account = _public_polish(str(_read(answers, "rent.payment.account") or "cuenta informada por LA PARTE ARRENDADORA").strip())
    due = f"dentro de los primeros {int(payment_day)} días de cada período mensual" if payment_day else "dentro del plazo mensual pactado"

    first = (
        f"El canon mensual de arrendamiento se fija en {_money_with_words(rent)}, pagadero por períodos anticipados, "
        f"{due}, mediante {method}, en {account} o en el canal que LA PARTE ARRENDADORA sustituya mediante comunicación trazable. "
        "El comprobante deberá permitir identificar pagador, período, fecha, cuantía y destino; el pago parcial no extingue el saldo ni altera por sí solo las condiciones del contrato."
    )
    control_parts = [
        "El canon deberá respetar en todo momento el límite imperativo del artículo 18 de la Ley 820 de 2003: no podrá exceder el uno por ciento (1 %) del valor comercial del inmueble o de la parte arrendada, y la estimación comercial utilizada para ese control no podrá superar dos (2) veces el avalúo catastral vigente."
    ]
    if commercial is not None:
        control_parts.append(
            f"Para la celebración se informó un valor comercial de referencia de {_money(commercial)}, cuyo uno por ciento (1 %) equivale a {_money(commercial * 0.01)}."
        )
    if cadastral is not None:
        control_parts.append(f"El avalúo catastral informado para el control de consistencia es {_money(cadastral)}.")
    if source_date:
        control_parts.append(f"La fuente o fecha de referencia reportada es: {source_date}.")
    second = " ".join(control_parts)
    third = (
        "Los valores de referencia anteriores documentan la verificación realizada al celebrar el contrato y no sustituyen la comprobación que proceda cuando cambien las circunstancias jurídicas o económicas relevantes. Cualquier modificación del canon deberá ajustarse a las reglas legales de reajuste y quedar debidamente comunicada."
    )
    return first, second, third


def compose_lease_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_lease_m33_final(answers))
    landlord_contact = _contact(answers, "landlord", "LA PARTE ARRENDADORA")
    tenant_contact = _contact(answers, "tenant", "LA PARTE ARRENDATARIA")
    address = str(_read(answers, "property.identification.address") or "el inmueble individualizado en este contrato").strip()
    municipality = str(_read(answers, "property.identification.municipality") or "").strip()
    ph_name = str(_read(answers, "property.ph_details.name") or "").strip()
    pets_conditions = str(_read(answers, "pets.conditions") or "manejo responsable, convivencia y reparación de daños demostrados").strip()

    final: list[dict] = []
    for original in composition.get("sections") or []:
        section = _polish_section(original)
        if section.get("_type") == "control":
            final.append(section)
            continue

        heading_cf = str(section.get("heading") or "").strip().casefold()
        is_clause = section.get("_type") == "clause"

        if heading_cf == "consideraciones":
            _paragraphs(
                section,
                f"PRIMERA: LA PARTE ARRENDADORA ha ofrecido en arrendamiento el inmueble ubicado en {address}{', ' + municipality if municipality else ''}, y LA PARTE ARRENDATARIA manifiesta su interés en recibirlo exclusivamente para vivienda urbana, junto con las unidades, bienes, servicios y usos que hayan sido expresamente incorporados al contrato y al inventario.",
                "SEGUNDA: Las partes reconocen que el contrato se somete al régimen especial de la Ley 820 de 2003 y a las demás normas imperativas aplicables. Por ello, la autonomía contractual no podrá utilizarse para desconocer límites al canon, prohibiciones de depósitos, reglas de solidaridad, obligaciones mínimas de las partes ni procedimientos legales de terminación y restitución.",
                "TERCERA: La adecuada ejecución exige evidencia suficiente sobre estado del inmueble, inventario, medidores, llaves, pagos, servicios, administración, reparaciones, comunicaciones y restitución. Las partes acuerdan documentar esos hechos de forma contemporánea y trazable, diferenciando desgaste normal, daños imputables, reparaciones necesarias y obligaciones propias del propietario o de los ocupantes.",
                f"CUARTA: {'El inmueble está sometido al régimen de propiedad horizontal de ' + ph_name + ', por lo que se integrarán las reglas de convivencia y uso que resulten válidamente aplicables, sin trasladar a LA PARTE ARRENDATARIA obligaciones que correspondan exclusivamente al propietario.' if ph_name else 'Cuando resulten aplicables reglas de propiedad horizontal, estas se comunicarán y se integrarán al uso del inmueble únicamente dentro de su ámbito jurídico correspondiente.'}",
                "QUINTA: Las partes procuran que canon, servicios públicos, administración, servicios adicionales y demás conceptos económicos permanezcan discriminados. Ningún cobro accesorio podrá emplearse para eludir límites legales del canon ni presumirse causado sin fundamento contractual, legal y probatorio suficiente.",
                "SEXTA: El presente instrumento busca prevenir controversias mediante reglas claras sobre entrega, habitabilidad, reparaciones, acceso, incumplimiento, terminación, restitución y liquidación. Su ejecución se regirá por la buena fe y por la realidad acreditada de los hechos; las formalidades, preavisos, cauciones e indemnizaciones exigidas por normas imperativas no podrán sustituirse por fórmulas genéricas del contrato.",
            )

        elif is_clause and _has(section, "OBJETO"):
            _paragraphs(
                section,
                f"LA PARTE ARRENDADORA concede a LA PARTE ARRENDATARIA el goce y tenencia del inmueble ubicado en {address}, junto con las unidades privadas, anexidades, elementos y usos expresamente descritos en este contrato, sus anexos y el inventario, para destinación exclusivamente habitacional y durante el término convenido.",
                "LA PARTE ARRENDATARIA se obliga, a su vez, a pagar oportunamente el canon y los conceptos que válidamente se encuentren a su cargo, conservar el inmueble con la diligencia exigible, respetar su destinación y las reglas de convivencia aplicables, informar daños o riesgos relevantes y restituir el bien al finalizar el contrato en el estado que corresponda, descontado el deterioro derivado del uso legítimo y del transcurso normal del tiempo.",
                "El objeto no comprende transferir dominio, opción de compra, derecho real, explotación comercial, alojamiento turístico, subarriendo ni cesión no autorizada. Las unidades, servicios o beneficios no individualizados de forma suficiente no se presumirán incluidos por el solo hecho de estar físicamente próximos al inmueble."
            )

        elif is_clause and _has(section, "IDENTIFICACIÓN DEL INMUEBLE"):
            paragraphs = list(section.get("paragraphs") or [])
            base = paragraphs[0] if paragraphs else ""
            base = _public_polish(base).replace("forman parte integral del acta e inventario de entrega", "se documentarán en el acta e inventario de entrega")
            _paragraphs(
                section,
                base,
                "La identificación física y registral deberá ser coherente con los documentos disponibles y con la unidad material entregada. El inventario, las fotografías, las lecturas de medidores y la relación de llaves complementan la descripción contractual, pero no sustituyen la individualización jurídica del inmueble ni atribuyen a una parte derechos que no tenga."
            )

        elif is_clause and _has(section, "CANON") and not _has(section, "REAJUSTE"):
            _paragraphs(section, *_rent_clause(answers))

        elif is_clause and _has(section, "MORA"):
            _paragraphs(
                section,
                "La mora en el pago se configurará conforme al vencimiento de la obligación y a las reglas legales aplicables. LA PARTE ARRENDATARIA deberá pagar los saldos efectivamente causados y demostrables; la recepción de pagos parciales, tardíos o imputados a períodos determinados no constituye por sí sola novación, renuncia permanente ni modificación del plazo contractual.",
                "Los intereses, gastos de cobranza, honorarios o conceptos equivalentes solo procederán cuando exista fundamento jurídico suficiente, sean proporcionales, estén debidamente discriminados y no dupliquen indemnizaciones por un mismo hecho. Toda gestión de cobro deberá respetar dignidad, privacidad, protección de datos y las prohibiciones legales aplicables.",
                "La mora no autoriza vías de hecho, ingreso no consentido, corte arbitrario de servicios, retención indebida de bienes ni desalojo informal. La terminación o restitución deberá adelantarse por las rutas contractuales y legales que correspondan."
            )

        elif is_clause and _has(section, "DEPÓSITOS Y GARANTÍAS"):
            _paragraphs(
                section,
                "No se exigirán depósitos en dinero efectivo ni cauciones reales para garantizar las obligaciones ordinarias de LA PARTE ARRENDATARIA, conforme a la prohibición del artículo 16 de la Ley 820 de 2003. Tampoco podrán encubrirse depósitos prohibidos bajo denominaciones distintas cuando su función económica sea la misma.",
                "Esta prohibición es distinta de las garantías o depósitos que, cuando el pago de servicios públicos corresponda a LA PARTE ARRENDATARIA, puedan constituirse directamente a favor de la empresa prestadora dentro del procedimiento especial del artículo 15 de la Ley 820 de 2003 y su reglamentación, originalmente expedida mediante el Decreto 3130 de 2003 y actualmente compilada en el Decreto 1077 de 2015.",
                "Las garantías personales, pólizas u otros mecanismos jurídicamente permitidos deberán individualizar obligado, beneficiario, riesgos cubiertos, vigencia, límites y procedimiento de reclamación. Su existencia no convierte una estimación unilateral en deuda cierta ni autoriza retenciones o cobros automáticos sin liquidación y soporte."
            )

        elif is_clause and _has(section, "REPARACIONES NECESARIAS"):
            _paragraphs(
                section,
                "LA PARTE ARRENDATARIA informará por un canal trazable las fallas, daños o circunstancias que razonablemente requieran una reparación a cargo de LA PARTE ARRENDADORA, describiendo su urgencia y aportando, cuando sea posible, evidencia suficiente sin asumir diagnósticos técnicos que no le correspondan.",
                "LA PARTE ARRENDADORA deberá evaluar y gestionar las reparaciones necesarias dentro de un plazo compatible con la naturaleza del daño, la habitabilidad, la seguridad y la disponibilidad razonable de acceso. Las partes coordinarán ingreso, horario y ejecución procurando reducir afectaciones innecesarias a la ocupación legítima.",
                "Ante un riesgo grave o una urgencia que amenace personas, inmueble o bienes, LA PARTE ARRENDATARIA podrá adoptar medidas razonables e inmediatas de contención y deberá preservar soportes. Lo anterior se entiende sin perjuicio de las reglas legales sobre reparaciones indispensables no locativas, reembolsos que puedan resultar procedentes y responsabilidades derivadas de la causa del daño."
            )

        elif is_clause and _has(section, "INVENTARIO Y EVIDENCIA"):
            _paragraphs(
                section,
                "El inventario de entrega deberá describir de manera suficientemente objetiva el estado funcional y estético del inmueble y, cuando aplique, muebles, equipos, accesorios, medidores, llaves, controles, fotografías, videos y defectos conocidos. Las observaciones deberán asociarse, en lo posible, con ubicación, fecha y evidencia para permitir comparación posterior.",
                "Si durante los primeros días de ocupación aparecen defectos que razonablemente no podían detectarse al momento de la entrega, LA PARTE ARRENDATARIA podrá reportarlos de manera trazable para complementar el acta, sin que ello implique aceptación automática de responsabilidad por su origen.",
                "En la restitución se realizará una comparación razonable entre el estado inicial y final, diferenciando desgaste normal, envejecimiento, defectos preexistentes, reparaciones necesarias, daños imputables y mejoras autorizadas. La evidencia deberá valorarse en conjunto y con posibilidad de contradicción cuando exista desacuerdo."
            )

        elif is_clause and _has(section, "MASCOTAS"):
            _paragraphs(
                section,
                f"Se autoriza la permanencia de la mascota o mascotas informadas por las partes bajo las siguientes condiciones: {pets_conditions} La autorización se entiende sometida a las reglas válidas de convivencia, salubridad, seguridad y propiedad horizontal que resulten aplicables.",
                "La sola tenencia de una mascota no presume daño ni incumplimiento. Cualquier reparación, limpieza extraordinaria, sanción o reclamación deberá vincularse con hechos demostrables y diferenciarse del desgaste normal; LA PARTE ARRENDATARIA responderá por los daños que jurídicamente le sean imputables."
            )

        elif is_clause and (_has(section, "COMUNICACIONES") or _has(section, "NOTIFICACIONES")):
            _paragraphs(
                section,
                f"Para comunicaciones contractuales ordinarias se informan los siguientes datos: {landlord_contact}; y {tenant_contact}. Los canales específicos declarados por las partes podrán complementarse con los incorporados en el contrato, siempre que permitan acreditar razonablemente remitente, contenido, fecha y destinatario.",
                "Los cambios de dirección para notificaciones judiciales o extrajudiciales deberán comunicarse en la forma legalmente exigible. Los reajustes, preavisos y terminaciones se remitirán por los mecanismos que la Ley 820 de 2003 requiera para cada actuación; un correo electrónico o mensaje informal no sustituirá el servicio postal autorizado cuando este sea requisito de la ruta jurídica utilizada.",
                "Las comunicaciones sobre reparaciones, acceso, pagos, convivencia y coordinación operativa podrán utilizar medios electrónicos trazables. Cada parte conservará evidencia suficiente de las comunicaciones materialmente relevantes y actualizará oportunamente sus datos de contacto."
            )

        elif is_clause and _has(section, "RESTITUCIÓN"):
            _paragraphs(
                section,
                "La restitución material se realizará en la fecha jurídicamente aplicable mediante entrega de llaves y controles, lectura de medidores, inventario comparado y acta que registre el estado del inmueble, novedades, servicios y documentos pendientes. La entrega no podrá condicionarse a la aceptación inmediata de cargos controvertidos que puedan liquidarse separadamente.",
                "LA PARTE ARRENDATARIA deberá retirar sus bienes y entregar el inmueble libre de ocupantes, salvo acuerdo distinto válido. LA PARTE ARRENDADORA deberá facilitar la recepción y no podrá negarse injustificadamente; si existe negativa o controversia sobre la entrega, cualquiera de las partes acudirá a los mecanismos legales aplicables y conservará evidencia de sus actuaciones.",
                "La restitución del inmueble no extingue automáticamente obligaciones causadas con anterioridad ni convierte estimaciones de daños en obligaciones ciertas. Los saldos se determinarán en la liquidación correspondiente con fundamento en soportes y reglas de imputación aplicables."
            )

        elif is_clause and _has(section, "LIQUIDACIÓN DE SALDOS"):
            _paragraphs(
                section,
                "Al cierre se conciliarán por separado canon, servicios públicos, administración, servicios adicionales, pagos, créditos, anticipos y daños que hayan sido demostrados. Cada concepto deberá identificar período, causa, cuantía y soporte, evitando compensaciones globales que impidan conocer el origen del saldo.",
                "En materia de daños se distinguirán desgaste normal, envejecimiento, vicios o fallas no imputables y afectaciones atribuibles a incumplimiento. Las cotizaciones constituyen elementos de estimación, pero no prueban por sí solas que una reparación se hubiera causado, ejecutado o pagado; deberán valorarse junto con inventarios, fotografías, facturas, conceptos técnicos y demás evidencia disponible.",
                "La liquidación que una parte prepare unilateralmente podrá servir como reclamación o estado de cuenta, pero no elimina el derecho de la otra a formular objeciones ni sustituye una decisión de autoridad cuando exista controversia sobre responsabilidad o cuantía."
            )

        elif is_clause and _has(section, "INTEGRIDAD"):
            _paragraphs(
                section,
                "El presente contrato, el inventario, las actas de entrega y restitución, los anexos expresamente incorporados, el reglamento de propiedad horizontal entregado cuando corresponda y las modificaciones válidamente suscritas integran el acuerdo aplicable a la relación arrendaticia.",
                "Toda modificación material deberá constar de manera verificable y no podrá desconocer normas imperativas. La tolerancia frente a un incumplimiento, la recepción de un pago tardío o la falta de ejercicio inmediato de un derecho no constituyen renuncia permanente ni modificación general de las obligaciones, salvo acuerdo válido en contrario."
            )

        elif is_clause and _has(section, "FIRMA Y COPIA"):
            _paragraphs(
                section,
                "El contrato podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos o mecanismos electrónicos, el método deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad, conforme a las reglas aplicables.",
                "Cada parte recibirá o tendrá acceso a una copia íntegra del contrato y de los anexos que legal o contractualmente deban entregarse. La versión suscrita deberá preservarse sin modificaciones posteriores y conservar razonablemente su integridad, fecha y evidencia de aceptación.",
                "Toda modificación material posterior requerirá una nueva versión, otrosí o instrumento válido y la aceptación de quienes deban obligarse por ella. La firma de una modificación no sustituye los requisitos especiales de comunicación, preaviso, caución o procedimiento que la ley exija para actuaciones concretas."
            )

        final.append(section)

    composition["sections"] = final
    composition.setdefault("maturity_answers", {})["lease_release_polished"] = True
    return composition


__all__ = ["compose_lease_m33_release"]
