from __future__ import annotations

"""Segunda pasada jurídica del NDA CO-EM-004 bajo M33.0.

Distingue confidencialidad contractual y secreto empresarial, activa datos e IA solo
cuando el expediente lo requiere, delimita PI y seguridad y conserva fuentes/control
fuera del instrumento aprobable mediante la presentación M33.0.
"""

from copy import deepcopy
import re
from typing import Any

from legalai_platform.contractual_maturity import ORDINALS
from m33_contractual_adapters import compose_nda_m33


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


def _format_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = text.replace(".", "")
    match = re.fullmatch(r"(\d{7,12})(?:-(\d))?", compact)
    if not match:
        return text
    base, check_digit = match.groups()
    groups: list[str] = []
    while base:
        groups.append(base[-3:])
        base = base[:-3]
    formatted = ".".join(reversed(groups))
    return f"{formatted}-{check_digit}" if check_digit else formatted


def _identity(answers: dict, prefix: str) -> dict[str, str]:
    block = _read(answers, f"{prefix}.identification", {})
    if not isinstance(block, dict):
        block = {}
    return {
        "type": str(block.get("type") or "").strip().casefold(),
        "name": str(block.get("name") or block.get("legalName") or block.get("fullName") or "").strip(),
        "id": _format_id(block.get("id_number") or block.get("identificationNumber") or block.get("nit")),
        "address": str(block.get("address") or "").strip(),
        "email": str(block.get("email") or "").strip(),
    }


def _signatory(answers: dict, prefix: str) -> dict[str, str]:
    block = _read(answers, f"{prefix}.signatory", {})
    if not isinstance(block, dict):
        block = {}
    return {
        "name": str(block.get("name") or block.get("fullName") or "").strip(),
        "id": _format_id(block.get("id_number") or block.get("identificationNumber")),
        "capacity": str(block.get("capacity") or block.get("positionOrCapacity") or "").strip(),
        "authority": str(block.get("authority_source") or block.get("authoritySource") or "").strip(),
    }


def _legal_person(identity: dict[str, str]) -> bool:
    return identity["type"] in {
        "legal_person", "legal", "persona jurídica", "persona_juridica", "juridica", "jurídica",
    }


def _party_description(answers: dict, prefix: str, label: str) -> str:
    identity = _identity(answers, prefix)
    signatory = _signatory(answers, prefix)
    pieces = [identity["name"] or label]
    if identity["id"]:
        pieces.append(("NIT " if _legal_person(identity) else "documento No. ") + identity["id"])
    if identity["address"]:
        pieces.append("con domicilio en " + identity["address"])
    text = ", ".join(pieces)
    if _legal_person(identity) and signatory["name"]:
        text += f", representada para este acto por {signatory['name']}"
        if signatory["id"]:
            text += f", identificado(a) con documento No. {signatory['id']}"
        if signatory["capacity"]:
            text += f", quien actúa en calidad de {signatory['capacity']}"
        if signatory["authority"]:
            text += f", con facultades acreditadas mediante {signatory['authority']}"
    return text


def _is_mutual(answers: dict) -> bool:
    agreement_type = str(_read(answers, "agreement.type") or "").strip().casefold()
    return bool(_read(answers, "agreement.reciprocal", False)) or agreement_type in {
        "mutual", "bilateral", "reciprocal", "recíproco", "reciproco",
    }


def _title(answers: dict) -> str:
    elements = ["ACUERDO DE CONFIDENCIALIDAD", "SECRETOS EMPRESARIALES", "PROPIEDAD INTELECTUAL"]
    if bool(_read(answers, "data.personal", False)):
        elements.append("DATOS PERSONALES")
    if bool(_read(answers, "ai.used", False)):
        elements.append("INTELIGENCIA ARTIFICIAL")
    return ", ".join(elements[:-1]) + (" E " + elements[-1] if len(elements) > 1 else "")


def _appearance(answers: dict, title: str) -> str:
    purpose = str(_read(answers, "agreement.purpose") or "la finalidad identificada en el expediente").strip()
    reference = str(_read(answers, "agreement.reference") or "la relación descrita en el expediente").strip()
    mutual = _is_mutual(answers)
    role_rule = (
        "Cada parte tendrá la calidad de PARTE REVELADORA respecto de la información que comunique y de PARTE RECEPTORA respecto de la información que reciba."
        if mutual
        else "Los roles de PARTE REVELADORA y PARTE RECEPTORA serán los identificados expresamente en el expediente y no se invertirán por el solo intercambio operativo de comunicaciones."
    )
    return (
        f"Entre {_party_description(answers, 'party_a', 'LA PRIMERA PARTE')}, en adelante LA PRIMERA PARTE, y "
        f"{_party_description(answers, 'party_b', 'LA SEGUNDA PARTE')}, en adelante LA SEGUNDA PARTE, se celebra el presente {title}. "
        f"El acuerdo se vincula a {reference} y tiene por finalidad exclusiva {purpose}. {role_rule} La celebración del acuerdo no obliga a revelar información, perfeccionar la operación proyectada ni transferir derechos distintos de los expresamente concedidos."
    )


def _clean_considerations(section: dict) -> None:
    if str(section.get("heading") or "").strip().casefold() != "consideraciones":
        return
    cleaned = []
    for item in section.get("paragraphs") or []:
        text = re.sub(r"^([^:]+):\s+Que\s+", r"\1: ", str(item), flags=re.IGNORECASE)
        text = re.sub(r"^([^:]+):\s+(La|El)\s+", lambda m: f"{m.group(1)}: {m.group(2)} ", text)
        cleaned.append(text)
    section["paragraphs"] = cleaned


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


def _object_text(answers: dict) -> str:
    purpose = str(_read(answers, "agreement.purpose") or "la finalidad autorizada").strip()
    categories = str(_read(answers, "information.categories") or "la información no pública identificada en el expediente").strip()
    permitted = str(_read(answers, "access.permitted_use") or purpose).strip()
    return (
        f"El acuerdo regula la revelación, recepción, acceso, uso, custodia, reproducción, seguridad, devolución y eliminación de información relacionada con {purpose}, incluida, cuando sea aplicable, {categories}. "
        f"La PARTE RECEPTORA solo podrá utilizarla para {permitted}. Ninguna revelación concede por sí sola licencia, cesión, exclusividad, derecho de explotación, autorización de tratamiento de datos, derecho a entrenar modelos ni facultad para desarrollar un producto competitivo. "
        "La PARTE REVELADORA conserva la decisión sobre qué información comunica y podrá exigir medidas adicionales razonables antes de revelar activos de mayor sensibilidad."
    )


def _confidential_information_text(answers: dict) -> str:
    categories = str(_read(answers, "information.categories") or "información técnica, comercial, jurídica, financiera u operativa no pública").strip()
    formats = str(_read(answers, "information.formats_sources") or "documentos, reuniones, sistemas y demostraciones autorizadas").strip()
    return (
        f"Se considerará Información Confidencial la información no pública comunicada por {formats}, incluida {categories}, cuando esté marcada como reservada o cuando una persona razonable deba entender su carácter confidencial por su naturaleza, contexto, contenido, forma de acceso o circunstancias de revelación. "
        "La protección no depende exclusivamente de una leyenda formal. Las partes deberán evitar clasificaciones indiscriminadas: el nivel de protección y las medidas de manejo se asignarán según sensibilidad, finalidad y riesgo."
    )


def _secret_text() -> str:
    return (
        "Solo tendrá el régimen reforzado de secreto empresarial la información no divulgada legítimamente poseída que sea secreta —por no ser generalmente conocida ni fácilmente accesible en los círculos que normalmente la manejan—, tenga valor comercial precisamente por ser secreta y haya sido objeto de medidas razonables para mantenerla reservada. "
        "La etiqueta contractual 'confidencial' no crea por sí sola un secreto empresarial. La protección especial subsistirá mientras se mantengan esos requisitos y deberá poder sustentarse mediante controles, trazabilidad, clasificación, acceso restringido y demás evidencia disponible."
    )


def _exclusions_text(answers: dict) -> str:
    exclusions = str(_read(answers, "information.exclusions") or "información pública, conocida legítimamente, recibida lícitamente de un tercero o desarrollada de forma independiente").strip()
    return (
        f"Quedan excluidos, cuando la PARTE RECEPTORA pueda demostrarlo con evidencia contemporánea suficiente, {exclusions}. También quedará excluida la información cuya divulgación haya sido autorizada de manera expresa por su titular. "
        "La simple existencia pública de componentes aislados no elimina la protección de una selección, combinación, arquitectura o relación no pública que reúna autónomamente los requisitos de reserva. La carga contractual de sustentar una exclusión corresponde a quien la invoca, sin alterar las reglas probatorias imperativas aplicables en una controversia."
    )


def _authorized_people_text(answers: dict) -> str:
    recipients = str(_read(answers, "access.authorized_recipients") or "personal expresamente asignado").strip()
    reps = str(_read(answers, "access.representatives") or "asesores y terceros autorizados sometidos a obligaciones equivalentes").strip()
    need = str(_read(answers, "access.need_to_know") or "necesidad estricta de conocer").strip()
    return (
        f"El acceso se limitará a {recipients} y, cuando sea necesario, a {reps}. En todos los casos regirá el criterio de {need}. "
        "La PARTE RECEPTORA deberá verificar que cada persona tenga una necesidad funcional vigente, conozca las restricciones aplicables, esté sometida a obligaciones de reserva suficientes y pierda el acceso oportunamente cuando cambie su función o termine su participación. "
        "La autorización a un tercero no convierte la información en pública ni libera a la PARTE RECEPTORA de sus deberes de selección, instrucción, supervisión y respuesta contractual."
    )


def _care_text(answers: dict) -> str:
    controls = _read(answers, "security.controls", {})
    controls = controls if isinstance(controls, dict) else {}
    technical = str(controls.get("technical") or "controles de acceso, autenticación, cifrado y registros").strip()
    organizational = str(controls.get("organizational") or "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes").strip()
    physical = str(controls.get("physical") or "medidas físicas proporcionales al soporte y al lugar de tratamiento").strip()
    return (
        f"La PARTE RECEPTORA aplicará, como mínimo, medidas razonables y proporcionales al riesgo. Para este expediente se han identificado controles técnicos de {technical}; controles organizacionales de {organizational}; y controles físicos de {physical}. "
        "Los accesos deberán ser individualizables y revisables; las excepciones deberán justificarse, autorizarse, documentarse y tener fecha de cierre. La PARTE RECEPTORA no podrá reducir deliberadamente los controles con el propósito o efecto de eludir la condición de secreto empresarial o el deber contractual de reserva."
    )


def _copies_reverse_engineering_text(answers: dict) -> str:
    reverse = str(_read(answers, "ip.source_code_reverse_engineering") or "prohibición salvo autorización o excepción legal").strip()
    return (
        "Las copias y extracciones se limitarán a las necesarias para la finalidad autorizada y conservarán clasificación y controles. No se utilizarán cuentas personales, repositorios públicos, servicios no aprobados ni soportes no gestionados cuando ello incremente injustificadamente el riesgo. "
        f"Respecto de código, binarios, modelos, dispositivos o muestras técnicas regirá la siguiente condición: {reverse}. Ninguna restricción se interpretará para impedir una conducta que una norma imperativa permita de forma no renunciable, pero quien invoque una excepción deberá limitar su alcance y preservar evidencia de su fundamento."
    )


def _compelled_disclosure_text(answers: dict) -> str:
    instruction = str(_read(answers, "access.compelled_disclosure") or "notificación previa cuando sea lícita y revelación mínima").strip()
    return (
        f"Ante una orden legal, judicial o administrativa se aplicará como protocolo contractual: {instruction}. La PARTE RECEPTORA verificará competencia, autenticidad, destinatario y alcance; procurará medidas de reserva cuando sean procedentes; revelará únicamente lo exigido y conservará evidencia del requerimiento, análisis, información entregada, fecha y destinatario. "
        "La obligación de notificación previa cede cuando esté legalmente prohibida o cuando una urgencia jurídicamente acreditada haga imposible realizarla oportunamente."
    )


def _security_text(answers: dict) -> str:
    return _care_text(answers)


def _incident_text(answers: dict) -> str:
    protocol = str(_read(answers, "security.incident_protocol") or "notificación, contención, investigación y preservación de evidencia").strip()
    hours = _first(answers, "security.notification_hours", "security.incident_notification_hours")
    timing = (
        f"y, contractualmente, dentro de las primeras {int(float(hours))} horas desde su confirmación"
        if hours not in (None, "")
        else "tan pronto como razonablemente sea posible desde su confirmación, sin esperar el informe definitivo"
    )
    return (
        f"Ante pérdida, acceso no autorizado, divulgación, alteración, indisponibilidad relevante o uso incompatible de información protegida, la PARTE RECEPTORA aplicará {protocol}. Notificará a la otra parte {timing}. "
        "El aviso inicial distinguirá hechos confirmados de hipótesis y comunicará, en la medida conocida, activos afectados, momento de detección, alcance, medidas de contención, riesgos, contacto responsable y siguientes actualizaciones. "
        "La cooperación contractual no implica admitir responsabilidad y no sustituye reportes a autoridades o titulares que resulten legalmente exigibles."
    )


def _provider_text(answers: dict, personal_data: bool) -> str:
    if personal_data:
        return (
            "Antes de habilitar proveedores, nube, encargados o subencargados, las partes identificarán servicio, roles de tratamiento, jurisdicción, región, subprocesadores, seguridad, retención, respaldo, uso secundario, auditoría, portabilidad, eliminación, retorno y apoyo en incidentes. "
            "Las transferencias y transmisiones internacionales de datos personales deberán evaluarse conforme al régimen colombiano aplicable; un cambio material de proveedor, país, finalidad o categoría de datos exige nueva evaluación antes de ampliar el acceso."
        )
    return (
        "El uso de nube, repositorios, asesores, proveedores o subcontratistas que puedan acceder a información protegida requiere autorización compatible con el expediente y controles equivalentes de confidencialidad, seguridad, retención, respaldo, eliminación y respuesta a incidentes. "
        "La parte que habilite al tercero deberá conocer dónde y para qué se almacena o procesa la información, limitar el acceso al mínimo necesario y gestionar el retiro o devolución al finalizar el servicio. En este expediente no se activa un régimen contractual de encargado/subencargado de datos personales porque no se ha declarado tratamiento de datos personales."
    )


def _ai_text(answers: dict) -> str:
    outputs = str(_read(answers, "ai.training_outputs") or "uso controlado sin entrenamiento ni retención con información protegida").strip()
    return (
        f"Las partes autorizan únicamente el uso de sistemas de inteligencia artificial bajo la siguiente condición del expediente: {outputs}. No se cargarán secretos empresariales, credenciales, código restringido, información confidencial de terceros ni otros activos protegidos en herramientas no autorizadas. "
        "Antes de usar un sistema se verificarán proveedor, modelo o servicio, finalidad, condiciones de uso, retención, entrenamiento, ubicación cuando sea relevante, controles de acceso, trazabilidad y posibilidad de revisión humana. Las salidas deberán revisarse antes de incorporarse a decisiones o entregables y no se presumirán exactas, originales, exclusivas ni libres de derechos de terceros. "
        "Esta cláusula es una regla contractual de gobernanza tecnológica y no atribuye a políticas públicas o normas sectoriales un alcance de ley general de inteligencia artificial que no tengan."
    )


def _ip_results_text(answers: dict) -> str:
    allocation = str(_read(answers, "ip.results_allocation") or "case_by_case").strip().casefold()
    if allocation in {"case_by_case", "caso_a_caso", "case by case"}:
        allocation_text = "La titularidad o licencia de cada resultado se definirá caso por caso mediante instrumento escrito específico"
    else:
        allocation_text = f"La asignación declarada en el expediente es {allocation}; antes de producir efectos deberá traducirse a una estipulación escrita que identifique activos y alcance"
    return (
        f"{allocation_text}. El inventario de resultados identificará activo, autor o creador, fecha, aportes, materiales preexistentes, dependencias y restricciones de terceros. "
        "Toda transferencia o licencia de derechos patrimoniales de autor deberá delimitar las modalidades de explotación, el tiempo y el ámbito territorial que correspondan; las transferencias deberán constar por escrito. No se entenderá cedida de manera general o indeterminable la producción futura ni concedidas modalidades de explotación no pactadas. "
        "Cuando se pretenda exclusividad u oponibilidad frente a terceros, deberá verificarse además el régimen de registro aplicable. Los derechos morales y demás derechos indisponibles se preservan."
    )


def _preexisting_text(answers: dict) -> str:
    preexisting = str(_read(answers, "ip.preexisting_materials") or "materiales, herramientas y conocimientos preexistentes identificados por cada parte").strip()
    return (
        f"Se consideran materiales preexistentes, entre otros, {preexisting}. Cada parte conservará los derechos que tenga sobre ellos y deberá identificarlos antes de incorporarlos de forma material a un resultado conjunto o entregable. "
        "El acceso técnico, interoperabilidad, entrega de una copia o integración no implica cesión. Si un resultado requiere un material preexistente para ser utilizado conforme a su finalidad, la licencia necesaria deberá establecerse de manera expresa, suficiente y compatible con las licencias de terceros."
    )


def _duration_text(answers: dict) -> str:
    agreement_years = int(float(_read(answers, "term_remedies.agreement_years", 2)))
    ordinary_years = int(float(_read(answers, "term_remedies.ordinary_confidentiality_years", 5)))
    return (
        f"El acuerdo tendrá una vigencia operativa de {agreement_years} años contados desde su firma, salvo terminación anticipada conforme a sus estipulaciones. La confidencialidad contractual ordinaria subsistirá durante {ordinary_years} años contados desde la última revelación de la información correspondiente. "
        "Los secretos empresariales conservarán protección mientras reúnan los requisitos jurídicos que les otorgan esa condición, aunque dicho período exceda la vigencia contractual ordinaria. Las obligaciones sobre propiedad intelectual, conservación probatoria, incidentes, copias retenidas y, cuando aplique, datos personales, sobrevivirán por el tiempo que resulte de su naturaleza, del instrumento específico o de la ley. "
        "La expiración no autoriza un uso nuevo de información recibida durante la vigencia."
    )


def _return_destroy_text(answers: dict) -> str:
    return_rule = str(_read(answers, "closure_confirmation.return_destroy") or "devolución o eliminación segura").strip()
    retained = str(_read(answers, "closure_confirmation.retained_copies") or "conservación limitada por obligación legal o defensa de derechos").strip()
    return (
        f"Al terminar la finalidad, vencer el acuerdo o mediar solicitud legítima se aplicará {return_rule}: se revocarán accesos, devolverán soportes cuando corresponda y eliminarán copias de trabajo y derivados que ya no deban conservarse. "
        f"Las excepciones se limitan a {retained}. Toda copia retenida quedará aislada del uso operativo, con acceso restringido, finalidad de conservación identificada y eliminación al desaparecer su fundamento. "
        "Cuando la otra parte lo solicite razonablemente, se emitirá certificación de cierre que identifique responsable, fecha, alcance, excepciones y método aplicado, sin revelar información de seguridad cuya divulgación incremente el riesgo."
    )


def _liability_text(answers: dict) -> str:
    rule = str(_read(answers, "term_remedies.penalty_or_liability") or "responsabilidad conforme a la ley por daños demostrados").strip()
    return (
        f"La regla económica acordada para este expediente es: {rule}. Esta estipulación no constituye por sí sola cláusula penal, liquidación anticipada de perjuicios ni presunción de daño. "
        "Quien reclame deberá sustentar incumplimiento, daño, causalidad y cuantía conforme al régimen aplicable, sin perjuicio de las presunciones o remedios que una norma imperativa establezca. Las partes deberán adoptar medidas razonables de contención y mitigación, preservar evidencia y cooperar para evitar la expansión innecesaria del daño. "
        "Cualquier límite de responsabilidad que se pretenda incorporar deberá ser expreso, cuantificado o determinable y revisado frente a dolo, culpa grave, derechos de terceros y materias legalmente indisponibles."
    )


def _dispute_text(answers: dict) -> str:
    mechanism = str(_read(answers, "closure_confirmation.dispute_mechanism") or "negotiation_conciliation").casefold()
    if mechanism in {"negotiation_conciliation", "negociacion_conciliacion", "negotiation and conciliation"}:
        path = "negociación directa entre responsables con capacidad de decisión y, si no existe solución, conciliación ante un centro o conciliador legalmente competente"
    else:
        path = f"el mecanismo identificado en el expediente ({mechanism}) previa verificación de su validez y alcance"
    return (
        f"Las partes procurarán resolver las controversias mediante {path}. Lo anterior no impide solicitar medidas cautelares o urgentes para contener una divulgación, preservar evidencia o evitar un daño inminente, ni desplaza competencias administrativas, penales, de protección de datos, propiedad intelectual o competencia desleal. "
        "El acuerdo se interpreta conforme al derecho aplicable en Colombia; la competencia territorial o judicial concreta se determinará por las normas aplicables y los hechos del caso, salvo pacto válido posterior que la defina expresamente."
    )


def _signature_parties(answers: dict) -> list[dict[str, str]]:
    result = []
    for prefix, label in (("party_a", "LA PRIMERA PARTE"), ("party_b", "LA SEGUNDA PARTE")):
        identity = _identity(answers, prefix)
        signatory = _signatory(answers, prefix)
        name = signatory["name"] or identity["name"]
        capacity = signatory["capacity"] or ("representante autorizado" if signatory["name"] else "")
        role = f"{capacity[:1].upper() + capacity[1:]} de {identity['name']}" if signatory["name"] and identity["name"] else capacity
        ids = []
        if signatory["id"]:
            ids.append(f"Documento {signatory['id']}")
        if identity["id"]:
            ids.append(("NIT " if _legal_person(identity) else "Documento ") + identity["id"])
        party = {"label": label, "name": name, "role": role}
        if ids:
            party["id"] = " · ".join(ids)
        result.append(party)
    return result


def _sources(personal_data: bool) -> list[str]:
    sources = [
        "Decisión 486 de 2000 de la Comisión de la Comunidad Andina, artículos 260 a 265, sobre secretos empresariales, duración de su protección y deberes de quien accede legítimamente.",
        "Ley 256 de 1996, artículo 16, sobre violación de secretos como acto de competencia desleal.",
        "Ley 23 de 1982, artículo 183 vigente, modificado por la Ley 1955 de 2019, sobre transferencias y licencias de derechos patrimoniales de autor.",
        "Decisión Andina 351 de 1993, régimen común sobre derecho de autor y derechos conexos.",
        "Ley 527 de 1999, especialmente reglas sobre escrito, firma y mensajes de datos cuando el acuerdo se celebra o conserva electrónicamente.",
    ]
    if personal_data:
        sources.extend([
            "Ley 1581 de 2012, régimen general de protección de datos personales.",
            "Decreto 1074 de 2015, reglas reglamentarias aplicables al tratamiento, transmisión y demás operaciones con datos personales.",
        ])
    return sources


def compose_nda_m33_final(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_nda_m33(answers))
    title = _title(answers)
    personal_data = bool(_read(answers, "data.personal", False))
    ai_used = bool(_read(answers, "ai.used", False))
    crossborder = bool(_read(answers, "data.crossborder", False))
    final: list[dict] = []
    controls: list[dict] = []

    for original in composition.get("sections") or []:
        section = deepcopy(original)
        _clean_considerations(section)
        heading = str(section.get("heading") or "")
        heading_cf = heading.casefold()

        if section.get("_type") == "control" or "control de uso" in heading_cf:
            controls.append(section)
            continue

        if heading.upper().startswith("ACUERDO DE CONFIDENCIALIDAD"):
            section["heading"] = title
            _paragraph(section, _appearance(answers, title))

        elif "objeto" in heading_cf and section.get("_type") == "clause":
            _paragraph(section, _object_text(answers))

        elif "definiciones operativas" in heading_cf:
            concepts = ["PARTE REVELADORA", "PARTE RECEPTORA", "INFORMACIÓN CONFIDENCIAL", "SECRETO EMPRESARIAL", "MATERIAL PREEXISTENTE", "RESULTADO", "INCIDENTE", "PROVEEDOR AUTORIZADO"]
            if personal_data:
                concepts.append("DATOS PERSONALES")
            if ai_used:
                concepts.append("SISTEMA DE INTELIGENCIA ARTIFICIAL")
            _paragraph(section, "Para interpretar y operar el acuerdo se utilizarán las siguientes categorías según el rol real de cada operación: " + ", ".join(concepts) + ". Las definiciones describen funciones y activos; no alteran por sí mismas titularidad, calidad de responsable/encargado, autoría, relación laboral ni condición jurídica de secreto empresarial.")

        elif "finalidad autorizada" in heading_cf:
            purpose = str(_read(answers, "agreement.purpose") or "la finalidad autorizada").strip()
            permitted = str(_read(answers, "access.permitted_use") or purpose).strip()
            _paragraph(section, f"La información solo podrá utilizarse para {purpose}; dentro de esa finalidad, el uso permitido se limita a {permitted}. Quedan excluidos usos secundarios incompatibles, prospección ajena al proyecto, publicidad, benchmarking identificable, extracción de bases, entrenamiento no autorizado, ingeniería competitiva o cualquier explotación que exceda la necesidad documentada. Un cambio material de finalidad requiere autorización previa y trazable de la parte legitimada para concederla.")

        elif "información confidencial" in heading_cf:
            _paragraph(section, _confidential_information_text(answers))

        elif "secretos empresariales" in heading_cf:
            _paragraph(section, _secret_text())

        elif "medidas razonables del titular" in heading_cf:
            _paragraph(section, "La PARTE REVELADORA que pretenda invocar protección como secreto empresarial deberá adoptar y poder acreditar medidas razonables conforme al activo y al riesgo: clasificación, acceso por necesidad, controles técnicos, instrucciones, acuerdos con terceros, inventario de revelaciones, custodia, revisión periódica y respuesta frente a incidentes. La ausencia de una medida aislada no decide automáticamente la condición del secreto, pero el conjunto de actuaciones será relevante para demostrar que la reserva fue realmente protegida.")

        elif "exclusiones y carga de prueba" in heading_cf:
            _paragraph(section, _exclusions_text(answers))

        elif "personas autorizadas" in heading_cf:
            _paragraph(section, _authorized_people_text(answers))

        elif "deber de cuidado" in heading_cf or "seguridad de la información" in heading_cf:
            # Se conserva una sola cláusula profunda de controles, evitando duplicación.
            if any("SEGURIDAD DE LA INFORMACIÓN" in str(item.get("heading") or "") for item in final):
                continue
            section["heading"] = "SEGURIDAD DE LA INFORMACIÓN"
            _paragraph(section, _security_text(answers))

        elif "copias, soportes y extracción" in heading_cf:
            _paragraph(section, _copies_reverse_engineering_text(answers))

        elif "revelación obligatoria" in heading_cf:
            _paragraph(section, _compelled_disclosure_text(answers))

        elif "datos personales" in heading_cf or "datos sensibles" in heading_cf or "reporte regulatorio" in heading_cf:
            if not personal_data:
                continue
            if "datos personales" in heading_cf:
                lifecycle = str(_read(answers, "data.lifecycle") or "conservación limitada a la finalidad y obligaciones aplicables").strip()
                cross = "Se ha declarado flujo transfronterizo y deberá documentarse su mecanismo jurídico antes de realizarse." if crossborder else "No se ha declarado transferencia o transmisión internacional; cualquier activación posterior exige evaluación previa."
                _paragraph(section, f"Cuando la ejecución involucre datos personales, las partes documentarán por operación finalidades, bases jurídicas, categorías, titulares, roles de Responsable y Encargado cuando correspondan, instrucciones, atención de derechos, seguridad, terceros y conservación. Para este expediente se define como ciclo de vida: {lifecycle}. {cross} La confidencialidad contractual no sustituye la Ley 1581 de 2012 ni su reglamentación.")
            elif "datos sensibles" in heading_cf:
                _paragraph(section, "Los datos sensibles, biométricos, de salud y de niñas, niños o adolescentes solo podrán tratarse cuando sean necesarios, exista base jurídica suficiente y se apliquen información y controles reforzados. No se exigirán ni usarán por mera conveniencia contractual y no se incorporarán a sistemas de IA, pruebas o datasets sin habilitación específica y evaluación del riesgo.")
            else:
                _paragraph(section, "Cada parte determinará y cumplirá los reportes o comunicaciones a la Superintendencia de Industria y Comercio, titulares u otras autoridades que correspondan a su rol y al incidente concreto. El aviso contractual entre partes no sustituye ni modifica términos regulatorios y deberá suministrar oportunamente la información que la otra parte necesite para cumplir sus propias obligaciones.")

        elif "incidentes y notificación" in heading_cf:
            _paragraph(section, _incident_text(answers))

        elif "nube, subprocesadores y terceros" in heading_cf:
            section["heading"] = "PROVEEDORES, NUBE Y TERCEROS" if not personal_data else "NUBE, ENCARGADOS, SUBENCARGADOS Y TERCEROS"
            _paragraph(section, _provider_text(answers, personal_data))

        elif "inteligencia artificial" in heading_cf:
            if not ai_used:
                continue
            _paragraph(section, _ai_text(answers))

        elif "propiedad y no licencia" in heading_cf:
            _paragraph(section, "La revelación de información no transfiere titularidad sobre marcas, invenciones, diseños, obras, software, bases de datos, modelos, documentación, know-how, secretos empresariales ni otros activos. Solo se concede el permiso de acceso y uso estrictamente necesario para la finalidad autorizada durante el tiempo en que ese acceso sea legítimo. Cualquier licencia adicional deberá identificar activo, titular, alcance, modalidades de uso, restricciones, duración, territorio y facultad de sublicenciar cuando corresponda.")

        elif "materiales preexistentes" in heading_cf:
            _paragraph(section, _preexisting_text(answers))

        elif "resultados y cadena de titularidad" in heading_cf:
            _paragraph(section, _ip_results_text(answers))

        elif "software y código abierto" in heading_cf:
            _paragraph(section, "Cuando la colaboración involucre software, cada resultado deberá acompañarse del inventario de componentes propios y de terceros, licencias aplicables, avisos, dependencias, documentación y código fuente que contractualmente corresponda entregar. La incorporación de código abierto no está prohibida, pero deberá verificarse compatibilidad de licencias y obligaciones de atribución, entrega de fuente, copyleft u otras condiciones antes de integrarlo a activos que se pretendan explotar bajo un régimen incompatible.")

        elif "duración y supervivencia" in heading_cf:
            _paragraph(section, _duration_text(answers))

        elif "devolución, eliminación y certificación" in heading_cf:
            _paragraph(section, _return_destroy_text(answers))

        elif "conservación y legal hold" in heading_cf:
            retained = str(_read(answers, "closure_confirmation.retained_copies") or "conservación limitada por obligación legal o defensa de derechos").strip()
            _paragraph(section, f"Una obligación legal, investigación, requerimiento de autoridad o necesidad razonable de preservar evidencia podrá suspender de manera delimitada la eliminación únicamente respecto de la información necesaria. La regla declarada para copias retenidas es: {retained}. Se documentarán fundamento, custodio, alcance, accesos, fecha de revisión y evento de liberación; la conservación excepcional no amplía la finalidad ni autoriza explotación operativa.")

        elif "responsabilidad y mitigación" in heading_cf:
            _paragraph(section, _liability_text(answers))

        elif "restricciones comerciales" in heading_cf:
            _paragraph(section, "Este NDA no crea no competencia, no captación, exclusividad, reparto de mercado, obligación de contratar, preferencia comercial ni impedimento para desarrollar de forma independiente actividades lícitas. La protección recae sobre la información y los derechos jurídicamente protegibles, no sobre el conocimiento general, la experiencia legítima ni la competencia por méritos. Cualquier restricción comercial adicional requiere instrumento separado, finalidad legítima, necesidad, proporcionalidad, duración y revisión frente a las normas de libre competencia y demás reglas aplicables.")

        elif "solución de controversias" in heading_cf:
            _paragraph(section, _dispute_text(answers))

        elif "firma y evidencia electrónica" in heading_cf:
            _paragraph(section, "El acuerdo podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos, el método deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad; la copia deberá permanecer accesible para consulta posterior y conservar integridad, versión, fecha y evidencia de aceptación. La plataforma mantendrá las revisiones y aprobaciones conforme a sus reglas de gobierno, sin convertir una generación automática en aprobación jurídica.")

        if section.get("_type") == "signature":
            section["parties"] = _signature_parties(answers)

        final.append(section)

    control = controls[0] if controls else {"heading": "CONTROL DE USO, FUENTES Y REVISIÓN", "_type": "control"}
    control["heading"] = "CONTROL DE USO, FUENTES Y REVISIÓN"
    control["text"] = "Documento candidato interno CO-EM-004 M33.0. Antes de liberar deben verificarse identidad, representación y facultades, carácter unilateral o mutuo, finalidad, categorías de información, medidas razonables para secretos empresariales, personas/proveedores autorizados, seguridad, incidentes, PI, IA, tratamiento de datos si se activa, duración, retorno/eliminación y remedios. Jurídico y QA deben aprobar la misma revisión y hash."
    control["bullets"] = [f"Fuente jurídica de control: {source}" for source in _sources(personal_data)]
    final.append(control)

    composition["title"] = title
    composition["subtitle"] = f"CO-EM-004 · {'Mutuo' if _is_mutual(answers) else 'Unilateral'} · M33.0"
    composition["sections"] = _renumber(final)
    composition.setdefault("maturity_answers", {})["nda_legal_review_finalized"] = True
    composition["maturity_answers"]["legal_sources"] = _sources(personal_data)
    composition["maturity_answers"]["personal_data_module_active"] = personal_data
    composition["maturity_answers"]["ai_module_active"] = ai_used
    return composition


__all__ = ["compose_nda_m33_final"]
