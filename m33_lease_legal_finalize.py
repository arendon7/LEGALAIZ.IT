from __future__ import annotations

"""Segunda pasada jurídica del arrendamiento de vivienda urbana CO-AR-001 M33.0.

Conserva la biblioteca contractual madura, pero hace explícitas las reglas imperativas
de la Ley 820 de 2003, evita parámetros temporales congelados y mantiene fuentes y
controles fuera del instrumento liberable mediante la presentación M33.0.
"""

from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta
import re
from typing import Any

from legalai_platform.contractual_maturity import ORDINALS
from m33_contractual_adapters import compose_lease_m33


_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _first(data: dict, *paths: str, default=None):
    for path in paths:
        value = _read(data, path)
        if value not in (None, "", [], {}):
            return value
    return default


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _date_es(value: Any) -> str:
    parsed = _parse_date(value)
    if not parsed:
        return str(value or "").strip()
    return f"{parsed.day} de {_MONTHS[parsed.month]} de {parsed.year}"


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _money(value: Any) -> str:
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value or "").strip()
    return "COP $" + f"{amount:,}".replace(",", ".")


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.fullmatch(r"(\d{7,12})(?:-(\d))?", text.replace(".", ""))
    if not match:
        return text
    base, check_digit = match.groups()
    groups = []
    while base:
        groups.append(base[-3:])
        base = base[:-3]
    formatted = ".".join(reversed(groups))
    return f"{formatted}-{check_digit}" if check_digit else formatted


def _identification(answers: dict, prefix: str) -> dict[str, str]:
    ident = _read(answers, f"{prefix}.identification", {})
    if not isinstance(ident, dict):
        ident = {}
    return {
        "type": str(ident.get("type") or "").strip().casefold(),
        "name": str(ident.get("name") or ident.get("legalName") or ident.get("fullName") or "").strip(),
        "id": _format_id(ident.get("id_number") or ident.get("identificationNumber") or ident.get("nit")),
        "address": str(ident.get("address") or "").strip(),
        "email": str(ident.get("email") or "").strip(),
        "phone": str(ident.get("phone") or "").strip(),
    }


def _signatory(answers: dict, prefix: str) -> dict[str, str]:
    data = _read(answers, f"{prefix}.signatory", {})
    if not isinstance(data, dict):
        data = {}
    return {
        "name": str(data.get("name") or data.get("fullName") or "").strip(),
        "id": _format_id(data.get("id_number") or data.get("identificationNumber")),
        "capacity": str(data.get("capacity") or data.get("positionOrCapacity") or "").strip(),
    }


def _additional_tenants(answers: dict) -> list[dict[str, str]]:
    raw = _read(answers, "tenant.additional.names")
    if raw in (None, "", [], {}):
        return []
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append({"name": str(item.get("name") or item.get("fullName") or "").strip(), "id": _format_id(item.get("id") or item.get("id_number"))})
            elif str(item).strip():
                result.extend(_parse_tenant_string(str(item)))
        return [item for item in result if item.get("name")]
    return _parse_tenant_string(str(raw))


def _parse_tenant_string(text: str) -> list[dict[str, str]]:
    result = []
    for part in re.split(r"\s*;\s*", text.strip()):
        if not part:
            continue
        match = re.match(r"^(.*?)(?:,\s*(?:CC|C\.C\.|CE|DOC(?:UMENTO)?)\s*([0-9.\-]+))?$", part, flags=re.IGNORECASE)
        name = (match.group(1) if match else part).strip(" ,")
        identity = _format_id(match.group(2) if match and match.group(2) else "")
        if name:
            result.append({"name": name, "id": identity})
    return result


def _party_description(identity: dict[str, str], signatory: dict[str, str] | None = None, *, landlord: bool = False) -> str:
    legal = identity.get("type") in {"legal", "legal_person", "juridica", "jurídica", "persona_juridica", "persona jurídica"}
    pieces = [identity.get("name") or ("LA PARTE ARRENDADORA" if landlord else "LA PARTE ARRENDATARIA")]
    if identity.get("id"):
        pieces.append(("NIT " if legal else "documento No. ") + identity["id"])
    if identity.get("address"):
        pieces.append("con domicilio en " + identity["address"])
    text = ", ".join(pieces)
    if legal and signatory and signatory.get("name"):
        text += f", representada para este acto por {signatory['name']}"
        if signatory.get("id"):
            text += f", identificado(a) con documento No. {signatory['id']}"
        if signatory.get("capacity"):
            text += f", quien actúa en calidad de {signatory['capacity']}"
    return text


def _appearance(answers: dict) -> str:
    landlord = _identification(answers, "landlord")
    tenant = _identification(answers, "tenant")
    signatory = _signatory(answers, "landlord")
    additional = _additional_tenants(answers)
    tenant_parts = [_party_description(tenant)]
    tenant_parts.extend(
        ", ".join([item["name"], "documento No. " + item["id"]]) if item.get("id") else item["name"]
        for item in additional
    )
    tenants = "; y ".join(tenant_parts)
    city = str(_first(answers, "property.identification.municipality", default="")).strip()
    address = str(_first(answers, "property.identification.address", default="el inmueble identificado en el contrato")).strip()
    place = f" en {city}" if city else ""
    return (
        f"Entre {_party_description(landlord, signatory, landlord=True)}, en adelante LA PARTE ARRENDADORA, y {tenants}, "
        f"en adelante conjuntamente LA PARTE ARRENDATARIA, se celebra{place} el presente CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA "
        f"respecto del inmueble ubicado en {address}. Las partes declaran que la destinación convenida es exclusivamente habitacional y que las normas imperativas de la Ley 820 de 2003 prevalecen sobre cualquier estipulación incompatible."
    )


def _property_description(answers: dict) -> str:
    ident = _read(answers, "property.identification", {})
    included = _read(answers, "property.included_units", {})
    ph = _read(answers, "property.ph_details", {})
    if not isinstance(ident, dict):
        ident = {}
    if not isinstance(included, dict):
        included = {}
    if not isinstance(ph, dict):
        ph = {}
    pieces = [f"Dirección: {ident.get('address') or 'identificada en el expediente'}"]
    if ident.get("registration"):
        pieces.append(f"matrícula inmobiliaria {ident['registration']}")
    if ident.get("cadastral_id"):
        pieces.append(f"identificación catastral {ident['cadastral_id']}")
    units = [str(included.get(key)).strip() for key in ("private_area", "parking", "storage", "other") if included.get(key)]
    if units:
        pieces.append("comprende " + "; ".join(units))
    if bool(_read(answers, "property.horizontal", False)) and ph.get("name"):
        pieces.append(f"sometido al régimen de propiedad horizontal de {ph['name']}")
    return ". ".join(pieces) + ". El inventario, fotografías, lecturas de medidores, llaves y estado de conservación forman parte integral del expediente de entrega."


def _term_text(answers: dict) -> str:
    months_number = _number(_read(answers, "term.duration_months"))
    months = int(months_number) if months_number and months_number > 0 else 12
    start_raw = _first(answers, "term.start_date", "lease.start_date", "delivery.date")
    start = _parse_date(start_raw)
    period = f"El término inicial será de {months} meses"
    if start:
        end = _add_months(start, months) - timedelta(days=1)
        period += f", contado desde el {_date_es(start)} hasta el {_date_es(end)}, ambas fechas inclusive"
    else:
        period += ", contado desde la fecha de entrega material y comienzo de ejecución acreditada"
    return (
        f"{period}. Si al vencimiento ninguna parte ha comunicado válidamente su decisión de terminar y se cumplen los presupuestos legales, "
        "el contrato se prorrogará en iguales condiciones y por el mismo término inicial, sin perjuicio del reajuste legal del canon. "
        "Los preavisos, indemnizaciones, cauciones y formas de comunicación se determinarán por la ruta de terminación efectivamente utilizada; el silencio no sustituye una formalidad legal incumplida."
    )


def _rent_text(answers: dict) -> str:
    rent = _number(_read(answers, "rent.amount"))
    commercial = _number(_read(answers, "rent.values.commercial_value"))
    cadastral = _number(_read(answers, "rent.values.cadastral_value"))
    if commercial is not None and cadastral is not None and commercial > 2 * cadastral:
        raise ValueError("CO-AR-001: el valor comercial suministrado excede dos veces el avalúo catastral para el control del artículo 18 de la Ley 820 de 2003.")
    if rent is not None and commercial is not None and rent > commercial * 0.01:
        raise ValueError("CO-AR-001: el canon suministrado excede el uno por ciento del valor comercial informado.")
    payment_day = _read(answers, "rent.payment.day")
    method = str(_read(answers, "rent.payment.method") or "canal trazable acordado")
    account = str(_read(answers, "rent.payment.account") or "cuenta informada por la parte arrendadora")
    control = ""
    if commercial is not None:
        control = f" Con la información suministrada, el valor comercial de referencia es {_money(commercial)} y el límite mensual resultante del artículo 18 es {_money(commercial * 0.01)}."
    due = f" dentro de los primeros {int(payment_day)} días de cada período" if _number(payment_day) else " dentro del plazo pactado"
    return (
        f"El canon mensual es {_money(rent)} y se pagará por períodos anticipados{due}, mediante {method}, en {account} o en el canal que sea sustituido mediante comunicación trazable. "
        "El canon no podrá exceder el uno por ciento (1 %) del valor comercial del inmueble o de la parte arrendada, y la estimación comercial utilizada para ese control no podrá superar dos (2) veces el avalúo catastral vigente."
        f"{control} El pago deberá permitir identificar período, fecha y cuantía."
    )


def _utilities_text(answers: dict) -> str:
    responsible = str(_read(answers, "charges.utilities.responsible") or "").strip().casefold()
    distribution = str(_read(answers, "charges.utilities.distribution") or "según medidores y facturas aplicables").strip()
    gas = str(_read(answers, "charges.utilities.gas_or_other") or "").strip()
    if responsible in {"tenant", "arrendatario", "arrendataria", "lessee"}:
        payer = "LA PARTE ARRENDATARIA asumirá los consumos y cargos que se causen durante su ocupación"
    elif responsible in {"landlord", "arrendador", "arrendadora", "lessor"}:
        payer = "LA PARTE ARRENDADORA asumirá los consumos y cargos expresamente asignados a su cargo"
    else:
        payer = "La responsabilidad económica por cada servicio se determinará conforme a la distribución pactada y a la factura o medición correspondiente, sin presumir traslados no documentados"
    extra = f" En particular, {gas}." if gas else ""
    return (
        f"{payer}. La liquidación se realizará {distribution}. Cada parte entregará oportunamente los soportes que tenga bajo su control y conciliará saldos al cierre.{extra} "
        "Cuando proceda el mecanismo especial del artículo 15 de la Ley 820 de 2003, se documentarán la denuncia del contrato y las garantías constituidas frente a la empresa prestadora para delimitar la solidaridad del inmueble."
    )


def _additional_services_text(answers: dict) -> str:
    exists = bool(_read(answers, "charges.additional_services.exists", False))
    description = str(_read(answers, "charges.additional_services.description") or "").strip()
    value = _number(_read(answers, "charges.additional_services.value"))
    rent = _number(_read(answers, "rent.amount"))
    if value is not None and rent is not None and value > rent * 0.5:
        raise ValueError("CO-AR-001: servicios, cosas o usos adicionales exceden el 50 % del canon del inmueble.")
    if not exists:
        return "No se pactan servicios, cosas o usos adicionales distintos de los conexos y de los expresamente discriminados en servicios públicos o propiedad horizontal. Cualquier incorporación posterior deberá constar por escrito y respetar el límite legal del cincuenta por ciento (50 %) del canon del inmueble."
    return (
        f"Se pacta como servicio adicional: {description or 'el servicio identificado en la ficha'}, por valor de {_money(value)}. "
        "Su precio, sumado al de los demás servicios, cosas o usos adicionales, no podrá exceder el cincuenta por ciento (50 %) del canon del inmueble. "
        "Este valor se discrimina del canon y no puede utilizarse para eludir límites, reajustes u obligaciones propias de la renta de arrendamiento."
    )


def _administration_text(answers: dict) -> str:
    ordinary = _money(_read(answers, "charges.administration.ordinary_amount"))
    ordinary_responsible = str(_read(answers, "charges.administration.ordinary_responsible") or "").casefold()
    extraordinary_responsible = str(_read(answers, "charges.administration.extraordinary_responsible") or "").casefold()
    ordinary_party = "LA PARTE ARRENDATARIA" if ordinary_responsible in {"tenant", "arrendatario", "arrendataria"} else "LA PARTE ARRENDADORA"
    extraordinary_party = "LA PARTE ARRENDATARIA" if extraordinary_responsible in {"tenant", "arrendatario", "arrendataria"} else "LA PARTE ARRENDADORA"
    return (
        f"La administración ordinaria, actualmente informada en {ordinary}, estará a cargo de {ordinary_party}; las cuotas extraordinarias estarán a cargo de {extraordinary_party}. "
        "La distribución corresponde a este contrato concreto y no convierte en obligación de LA PARTE ARRENDATARIA conceptos que legalmente correspondan al propietario. "
        "Las multas atribuibles a conducta de ocupantes exigirán soporte de la actuación de propiedad horizontal y no podrán trasladarse cuando provengan de una omisión propia del propietario."
    )


def _termination_landlord() -> str:
    return (
        "La terminación unilateral por LA PARTE ARRENDADORA se regirá exclusivamente por las causales, preavisos, indemnizaciones, cauciones y procedimientos de los artículos 22 y 23 de la Ley 820 de 2003. "
        "Las causales de incumplimiento deberán probarse de manera individual. Durante las prórrogas, la terminación por plena voluntad exige aviso escrito por servicio postal autorizado con antelación no menor de tres (3) meses y el pago de una indemnización equivalente a tres (3) cánones. "
        "A la fecha de vencimiento del término inicial o de sus prórrogas, las causales especiales de ocupación por el propietario o poseedor, demolición o reparación indispensable y entrega derivada de compraventa exigen preaviso no menor de tres (3) meses y constancia de caución equivalente a seis (6) cánones para garantizar el cumplimiento de la causal. "
        "La plena voluntad al vencimiento solo procede cuando el contrato haya cumplido como mínimo cuatro (4) años de ejecución y exige la indemnización legal de uno punto cinco (1,5) cánones. Antes de activar cualquier ruta deberán verificarse causal exacta, fecha, prueba, forma de comunicación, caución o consignación e intervención de la autoridad cuando corresponda."
    )


def _termination_tenant() -> str:
    return (
        "LA PARTE ARRENDATARIA podrá terminar unilateralmente por las causales legales imputables a LA PARTE ARRENDADORA, con la prueba y procedimiento aplicables. "
        "También podrá terminar dentro del término inicial o durante sus prórrogas por plena voluntad, mediante aviso escrito enviado a través de servicio postal autorizado con antelación no menor de tres (3) meses y pago de una indemnización equivalente a tres (3) cánones. "
        "A la fecha de vencimiento del término inicial o de cualquiera de sus prórrogas podrá terminar sin indemnización mediante preaviso escrito no menor de tres (3) meses. "
        "La comunicación deberá identificar fecha de restitución y conservar prueba de contenido, envío y entrega; la negativa de LA PARTE ARRENDADORA a recibir el inmueble deberá gestionarse por los mecanismos legales aplicables y nunca mediante abandono informal del bien."
    )


def _sources() -> list[str]:
    return [
        "Ley 820 de 2003, especialmente artículos 2 a 10, 15 a 24, sobre vivienda urbana, clasificación, solidaridad, obligaciones, servicios, depósitos, canon, reajuste y terminación.",
        "Decreto 3130 de 2003, reglamentario del artículo 15 de la Ley 820 de 2003 sobre garantías y denuncia frente a empresas de servicios públicos domiciliarios.",
        "Ley 675 de 2001, cuando el inmueble esté sometido a propiedad horizontal.",
        "Código Civil colombiano, reglas de arrendamiento aplicables de manera supletoria cuando sean compatibles con el régimen especial.",
        "Ley 1581 de 2012 y Decreto 1074 de 2015 para tratamiento de datos personales del expediente contractual.",
        "Ley 527 de 1999 cuando se utilicen mensajes de datos o mecanismos de firma electrónica/digital.",
        "Corte Constitucional, Sentencia C-426 de 2023, sobre la caución del numeral 8 del artículo 22 de la Ley 820 de 2003.",
    ]


def _clean_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", lambda m: _date_es(m.group(0)), value)
    replacements = (
        ("EL ARRENDADOR", "LA PARTE ARRENDADORA"),
        ("EL ARRENDATARIO", "LA PARTE ARRENDATARIA"),
        ("El arrendador", "LA PARTE ARRENDADORA"),
        ("El arrendatario", "LA PARTE ARRENDATARIA"),
        ("el arrendador", "la parte arrendadora"),
        ("el arrendatario", "la parte arrendataria"),
        ("al arrendador", "a la parte arrendadora"),
        ("al arrendatario", "a la parte arrendataria"),
    )
    for source, target in replacements:
        value = value.replace(source, target)
    return value


def _clean_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _clean_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_clean_text(item) for item in result[key]]
    return result


def _paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _renumber(sections: list[dict]) -> list[dict]:
    number = 0
    for section in sections:
        if section.get("_type") != "clause":
            continue
        number += 1
        heading = str(section.get("heading") or "").strip()
        title = heading.split(":", 1)[1].strip() if ":" in heading else heading
        ordinal = ORDINALS[number - 1] if number <= len(ORDINALS) else str(number)
        section["heading"] = f"{ordinal}: {title.upper()}"
        section["clause_number"] = number
    return sections


def compose_lease_m33_final(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_lease_m33(answers))
    configuration = str(_read(answers, "lease.configuration") or "individual").casefold()
    additional_tenants = _additional_tenants(answers)
    pets = bool(_read(answers, "pets.exists", False))
    guarantee_type = str(_read(answers, "guarantee.type") or "").casefold()
    landlord = _identification(answers, "landlord")
    signatory = _signatory(answers, "landlord")
    tenant = _identification(answers, "tenant")

    final: list[dict] = []
    controls: list[dict] = []
    for original in composition.get("sections") or []:
        section = _clean_section(original)
        if str(section.get("heading") or "").strip().casefold() == "consideraciones":
            section["paragraphs"] = [re.sub(r"^([^:]+):\s+Que\s+", r"\1: ", str(item), flags=re.IGNORECASE) for item in section.get("paragraphs") or []]

        if section.get("_type") == "control" or "control de uso" in str(section.get("heading") or "").casefold():
            controls.append(section)
            continue

        if str(section.get("heading") or "").upper() == "CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA":
            _paragraph(section, _appearance(answers))

        elif _has(section, "IDENTIFICACIÓN DEL INMUEBLE"):
            _paragraph(section, _property_description(answers))

        elif _has(section, "MODALIDAD"):
            if configuration == "joint" or additional_tenants:
                names = [tenant["name"]] + [item["name"] for item in additional_tenants]
                _paragraph(section, f"Por intervenir dos o más personas naturales como arrendatarias, el contrato se clasifica como arrendamiento mancomunado en los términos de la Ley 820 de 2003. Reciben el goce {', '.join(name for name in names if name)} y las obligaciones derivadas del contrato son solidarias en los términos del artículo 7 de la misma ley. La clasificación responde a la realidad del uso y no puede alterarse por una denominación distinta.")
            else:
                _paragraph(section, "El contrato se clasifica como arrendamiento individual de vivienda urbana. La clasificación responde a la realidad del uso y a la Ley 820 de 2003, con independencia del nombre que las partes asignen al documento.")

        elif _has(section, "ENTREGA") and section.get("_type") == "clause":
            delivery_date = _date_es(_read(answers, "delivery.date"))
            defects = str(_read(answers, "condition.defects") or "").strip().rstrip(".")
            pending = str(_read(answers, "condition.repairs_pending.items") or "").strip().rstrip(".")
            responsible = str(_read(answers, "condition.repairs_pending.responsible") or "").strip().rstrip(".")
            details = []
            if defects:
                details.append(f"Se deja constancia inicial de {defects}.")
            if pending:
                pending_text = f"Queda pendiente {pending}."
                if responsible:
                    pending_text += f" Responsable y plazo informados: {responsible}."
                details.append(pending_text)
            suffix = " " + " ".join(details) if details else ""
            _paragraph(section, f"La entrega material se realizará el {delivery_date} mediante acta, inventario detallado, evidencia fotográfica, lectura de medidores y relación de llaves. El inmueble deberá entregarse en condiciones de servicio, seguridad y sanidad compatibles con la destinación habitacional.{suffix} La recepción no implica renuncia a reclamar defectos ocultos, incumplimientos o daños preexistentes no razonablemente detectables en ese momento.")

        elif _has(section, "TÉRMINO") and section.get("_type") == "clause":
            _paragraph(section, _term_text(answers))

        elif _has(section, "CANON") and section.get("_type") == "clause":
            _paragraph(section, _rent_text(answers))

        elif _has(section, "REAJUSTE"):
            _paragraph(section, "Cada doce (12) meses de ejecución del contrato bajo un mismo precio, LA PARTE ARRENDADORA podrá incrementar el canon hasta una proporción que no supere el cien por ciento (100 %) del incremento del IPC del año calendario inmediatamente anterior al reajuste, sin exceder el límite del artículo 18 de la Ley 820 de 2003. El porcentaje no se congela en este contrato: deberá verificarse en la publicación oficial del DANE correspondiente al momento de cada reajuste. El nuevo monto y su fecha de vigencia deberán comunicarse por servicio postal autorizado o por el mecanismo de notificación personal expresamente pactado; sin esa comunicación el reajuste será inoponible. No habrá reajuste antes de completar doce meses bajo el mismo precio ni cobro retroactivo del incremento no comunicado.")

        elif _has(section, "SERVICIOS PÚBLICOS"):
            _paragraph(section, _utilities_text(answers))

        elif _has(section, "ADMINISTRACIÓN Y CUOTAS"):
            _paragraph(section, _administration_text(answers))

        elif _has(section, "SERVICIOS, COSAS Y USOS ADICIONALES"):
            _paragraph(section, _additional_services_text(answers))

        elif _has(section, "DEPÓSITOS Y GARANTÍAS"):
            _paragraph(section, "No se exigirán depósitos en dinero efectivo ni cauciones reales para garantizar las obligaciones ordinarias de LA PARTE ARRENDATARIA, por prohibición del artículo 16 de la Ley 820 de 2003. Esta prohibición no se confunde con las garantías o depósitos que, cuando el pago de servicios públicos esté a cargo de LA PARTE ARRENDATARIA, puedan constituirse a favor de la respectiva empresa prestadora dentro del procedimiento especial del artículo 15 de la Ley 820 y el Decreto 3130 de 2003. Las garantías personales, pólizas u otros mecanismos permitidos deberán estar identificados, ser proporcionales y no autorizan retenciones o cobros automáticos sin liquidación y soporte.")

        elif _has(section, "MASCOTAS") and not pets:
            continue

        elif _has(section, "MASCOTAS") and pets:
            conditions = str(_read(answers, "pets.conditions") or "manejo responsable, convivencia y reparación de daños demostrados")
            _paragraph(section, f"Se autoriza la permanencia de la mascota o mascotas informadas en el expediente bajo las siguientes condiciones: {conditions} Las reglas de convivencia, salubridad y propiedad horizontal serán exigibles de manera objetiva; cualquier daño deberá acreditarse y diferenciarse del desgaste normal.")

        elif _has(section, "SEGUROS") and guarantee_type not in {"policy", "póliza", "poliza", "insurance"}:
            continue

        elif _has(section, "TERMINACIÓN POR EL ARRENDADOR"):
            section["heading"] = str(section.get("heading") or "").replace("ARRENDADOR", "PARTE ARRENDADORA")
            _paragraph(section, _termination_landlord())

        elif _has(section, "TERMINACIÓN POR EL ARRENDATARIO"):
            section["heading"] = str(section.get("heading") or "").replace("ARRENDATARIO", "PARTE ARRENDATARIA")
            _paragraph(section, _termination_tenant())

        if section.get("_type") == "signature":
            parties = []
            capacity = signatory["capacity"] or "representante autorizado"
            capacity_display = capacity[:1].upper() + capacity[1:] if capacity else "Representante autorizado"
            landlord_role = f"{capacity_display} de {landlord['name']}" if signatory["name"] else "Parte arrendadora"
            if landlord["id"]:
                landlord_role += f" · NIT {landlord['id']}" if landlord["type"] in {"legal", "legal_person"} else f" · Documento {landlord['id']}"
            landlord_party = {
                "label": "LA PARTE ARRENDADORA",
                "name": signatory["name"] or landlord["name"],
                "role": landlord_role,
            }
            if signatory["id"]:
                landlord_party["id"] = f"Documento {signatory['id']}"
            parties.append(landlord_party)
            tenant_party = {"label": "LA PARTE ARRENDATARIA", "name": tenant["name"]}
            if tenant["id"]:
                tenant_party["id"] = f"Documento {tenant['id']}"
            parties.append(tenant_party)
            for item in additional_tenants:
                extra = {"label": "LA PARTE ARRENDATARIA", "name": item["name"]}
                if item.get("id"):
                    extra["id"] = f"Documento {item['id']}"
                parties.append(extra)
            section["parties"] = parties

        final.append(section)

    control = controls[0] if controls else {"heading": "CONTROL DE USO, FUENTES Y REVISIÓN", "_type": "control"}
    control["heading"] = "CONTROL DE USO, FUENTES Y REVISIÓN"
    control["text"] = "Documento candidato interno CO-AR-001 M33.0. Antes de liberar deben verificarse identidad y capacidad, titularidad o facultad para arrendar, clasificación real, inmueble, canon y soportes de valor, servicios, administración, garantías, inventario, comunicaciones, módulos condicionales y rutas de terminación. La aprobación jurídica y QA deben recaer sobre la misma revisión y hash."
    control["bullets"] = [f"Fuente jurídica de control: {source}" for source in _sources()]
    final.append(control)

    composition["sections"] = _renumber(final)
    composition.setdefault("maturity_answers", {})["lease_legal_review_finalized"] = True
    composition["maturity_answers"]["lease_classification_m33"] = "mancomunado" if configuration == "joint" or additional_tenants else "individual"
    composition["maturity_answers"]["legal_sources"] = _sources()
    return composition


__all__ = ["compose_lease_m33_final"]
