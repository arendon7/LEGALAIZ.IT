from __future__ import annotations

"""Pulido final del instrumento firmable CO-LA-002 M33.0.

Conserva la lógica temporal y modal de la revisión jurídica M33.0, incluyendo
Ley 2466 de 2025 y Ley 2101 de 2021, y profundiza únicamente el documento que
reciben las partes. Las fuentes y aprobaciones permanecen como gobierno interno.
"""

from copy import deepcopy
import re
from typing import Any

from m33_employment_legal_finalize import compose_employment_m33_final


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


def _money_with_words(value: Any) -> str:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value or "valor pendiente de determinación").strip()
    visible = "COP $" + f"{number:,}".replace(",", ".")
    words = _number_words(number)
    words = re.sub(r"\bveintiuno$", "veintiún", words)
    words = re.sub(r"\by uno$", "y un", words)
    words = re.sub(r"\buno$", "un", words)
    connector = " de" if number >= 1_000_000 and number % 1_000_000 == 0 else ""
    return f"{visible} ({words}{connector} pesos moneda corriente)"


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraphs(section: dict, *items: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [item for item in items if str(item or "").strip()]


def _clean_visible(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    replacements = (
        ("constan en la ficha", "se encuentran definidos en el presente contrato y en el Anexo No. 1"),
        ("consta en la ficha", "se encuentra definido en el presente contrato y en el Anexo No. 1"),
        ("definido en el expediente", "definido para la relación laboral"),
        ("identificado(a) con documento No.", "con documento No."),
        ("EL TRABAJADOR", "LA PERSONA TRABAJADORA"),
    )
    text = value
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _clean_section(section: dict) -> dict:
    result = deepcopy(section)
    if result.get("_type") == "control":
        return result
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _clean_visible(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_clean_visible(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_clean_visible(cell) for cell in row] for row in result["table"]]
    if isinstance(result.get("parties"), list):
        result["parties"] = [
            {key: _clean_visible(value) for key, value in party.items()} if isinstance(party, dict) else party
            for party in result["parties"]
        ]
    return result


def compose_employment_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_employment_m33_final(answers))
    role = str(_read(answers, "role.jobTitle") or "cargo contratado").strip()
    purpose = str(_read(answers, "role.purpose") or "cumplir las responsabilidades propias del cargo").strip()
    workplace = str(_read(answers, "work.mainWorkplace") or "el lugar de trabajo acordado").strip()
    salary = _money_with_words(_read(answers, "compensation.baseSalary"))
    modality = str(_read(answers, "work.modality") or "onsite").strip().casefold()

    final: list[dict] = []
    for original in composition.get("sections") or []:
        section = _clean_section(original)
        if section.get("_type") == "control":
            final.append(section)
            continue
        heading_cf = str(section.get("heading") or "").strip().casefold()
        is_clause = section.get("_type") == "clause"

        if heading_cf == "consideraciones":
            _paragraphs(
                section,
                f"PRIMERA: EL EMPLEADOR requiere de manera estable el cargo de {role}, orientado a {purpose}, y ha determinado que su ejecución se realizará mediante una relación laboral subordinada, personal y remunerada, con aplicación integral de las garantías mínimas del ordenamiento laboral colombiano.",
                "SEGUNDA: LA PERSONA TRABAJADORA declara haber recibido información suficiente sobre cargo, funciones esenciales, lugar de trabajo, jornada, salario, dependencia, riesgos y reglas internas válidamente aplicables, sin que esta declaración implique renuncia a información adicional, inducción, capacitación o medidas de prevención que legalmente correspondan al empleador.",
                "TERCERA: Las partes reconocen que la subordinación faculta a EL EMPLEADOR para impartir órdenes e instrucciones dentro de límites constitucionales y legales, pero no autoriza afectaciones arbitrarias de dignidad, salud, intimidad, igualdad, salario, jornada, estabilidad reforzada, libertad sindical ni demás derechos fundamentales y mínimos laborales.",
                "CUARTA: La realidad de la prestación prevalece sobre las denominaciones formales. Los cambios de funciones, horario, lugar, modalidad, compensación, herramientas o dependencia deberán mantenerse dentro del poder de dirección legítimo o documentarse cuando impliquen una modificación material que requiera acuerdo, evaluación de riesgos o reconocimiento económico.",
                "QUINTA: El contrato se ejecutará con trazabilidad suficiente sobre jornada, pagos, recargos, vacaciones, licencias, seguridad social, SST, activos, evaluaciones, procesos disciplinarios y comunicaciones relevantes. Los registros del empleador constituyen evidencia de gestión, pero no excluyen otros medios de prueba ni convierten unilateralmente una controversia en hecho probado.",
                "SEXTA: Ninguna cláusula, política, anexo, paz y salvo, autorización general o herramienta tecnológica podrá interpretarse como renuncia a derechos ciertos e indiscutibles, exclusión artificial de factores salariales, autorización ilimitada de vigilancia o habilitación para desconocer el debido proceso, la favorabilidad o la primacía de la realidad."
            )

        elif is_clause and _has(section, "OBJETO Y VINCULACIÓN"):
            _paragraphs(
                section,
                f"EL EMPLEADOR vincula a LA PERSONA TRABAJADORA para desempeñar el cargo de {role}, cuya finalidad principal es {purpose}. Las funciones esenciales, responsabilidades, autoridad, resultados esperados y riesgos asociados se desarrollan en el Anexo No. 1, que forma parte del contrato sin sustituir la naturaleza laboral del vínculo.",
                "LA PERSONA TRABAJADORA prestará personalmente el servicio con diligencia, buena fe y observancia de instrucciones legítimas. Las funciones conexas podrán asignarse cuando guarden relación razonable con el cargo, formación, experiencia y necesidades del servicio; no podrán utilizarse para imponer una desmejora injustificada, alterar de hecho la categoría profesional o trasladar riesgos empresariales propios del empleador.",
                "Cuando un cambio funcional sea material por su permanencia, complejidad, responsabilidad, exposición a riesgos o impacto económico, EL EMPLEADOR deberá documentarlo y evaluar las consecuencias laborales, salariales y de seguridad y salud que correspondan antes o desde su implementación."
            )

        elif is_clause and _has(section, "CARGO, DEPENDENCIA Y AUTORIDAD"):
            _paragraphs(
                section,
                f"El cargo de {role}, su dependencia funcional, responsables autorizados y nivel de autonomía se encuentran definidos en el presente contrato y en el Anexo No. 1. Las órdenes deberán guardar relación con el servicio, provenir de personas facultadas y respetar dignidad, legalidad, proporcionalidad, seguridad y competencias profesionales.",
                "LA PERSONA TRABAJADORA podrá solicitar aclaración sobre instrucciones ambiguas y reportar, por canales razonables, órdenes que considere ilegales, discriminatorias, inseguras o materialmente incompatibles con las funciones. El reporte de buena fe no constituye insubordinación ni autoriza represalias, sin perjuicio del deber de cumplir instrucciones legítimas mientras permanezcan vigentes."
            )

        elif is_clause and _has(section, "LUGAR Y MOVILIDAD"):
            _paragraphs(
                section,
                f"El lugar principal de prestación del servicio será {workplace}. Los desplazamientos temporales razonablemente asociados al cargo deberán coordinarse con antelación compatible con la necesidad, condiciones de seguridad, tiempos de desplazamiento y reconocimiento de gastos cuando corresponda.",
                "Un cambio permanente de ciudad, sede o modalidad deberá valorar funciones, riesgos, costos y circunstancias personales relevantes y no podrá utilizarse como mecanismo de desmejora, represalia o terminación indirecta. Cuando por su entidad requiera consentimiento, modificación escrita o aplicación de una figura legal específica, EL EMPLEADOR deberá formalizarla antes de exigir su ejecución."
            )

        elif is_clause and _has(section, "DESCANSOS Y DESCONEXIÓN"):
            _paragraphs(
                section,
                "LA PERSONA TRABAJADORA tendrá los descansos dentro de la jornada, el descanso semanal obligatorio, vacaciones, licencias y demás períodos de descanso reconocidos por la ley. La organización del trabajo deberá permitir su disfrute real y evitar que cargas ordinarias, metas o canales de comunicación los conviertan de hecho en tiempo disponible permanente.",
                "Fuera de la jornada no existirá obligación ordinaria de atender comunicaciones, órdenes o tareas, salvo las excepciones legales y situaciones verdaderamente extraordinarias que resulten aplicables. Las comunicaciones enviadas fuera del horario no generan por sí mismas deber de respuesta inmediata ni autorizan evaluación negativa por no atenderlas.",
                "Cuando una actividad realizada fuera de la jornada constituya tiempo de trabajo o trabajo suplementario, se registrará y remunerará conforme a su causación real; el derecho a la desconexión no puede utilizarse para invisibilizar tiempo efectivamente laborado."
            )

        elif is_clause and _has(section, "SALARIO"):
            _paragraphs(
                section,
                f"EL EMPLEADOR pagará a LA PERSONA TRABAJADORA un salario básico mensual de {salary}, correspondiente a la jornada ordinaria pactada y pagadero con la periodicidad y por el medio trazable definidos por las partes o por la nómina institucional válidamente comunicada.",
                "El salario básico no comprende horas extras, recargos nocturnos, trabajo en días de descanso obligatorio, comisiones, variables ni otros conceptos que por su causación o por mandato legal deban liquidarse separadamente. Cada período de pago deberá permitir identificar concepto, base, cantidad, tarifa, deducción y valor neto.",
                "La denominación contractual o contable de un pago no puede excluir su naturaleza salarial cuando en la realidad remunera directamente el servicio. Los pactos no salariales solo producen los efectos jurídicamente permitidos respecto de conceptos específicos cuya naturaleza y finalidad sean compatibles con la ley."
            )

        elif is_clause and _has(section, "PRESTACIONES, VACACIONES Y APORTES"):
            _paragraphs(
                section,
                "EL EMPLEADOR reconocerá y pagará oportunamente las prestaciones sociales, vacaciones, aportes al Sistema de Seguridad Social Integral, parafiscales, dotación y demás beneficios legal o convencionalmente procedentes de acuerdo con salario, tiempo y condiciones reales de ejecución.",
                "Las vacaciones deberán procurar descanso efectivo y su programación atenderá simultáneamente las necesidades del servicio y el derecho de la persona trabajadora. Solo podrán compensarse, acumularse o interrumpirse en los eventos y condiciones legalmente permitidos.",
                "Las diferencias de nómina, aportes o bases de cotización que se detecten deberán corregirse con trazabilidad, sin trasladar a LA PERSONA TRABAJADORA consecuencias imputables al incumplimiento del empleador."
            )

        elif is_clause and _has(section, "FORMACIÓN Y EVALUACIÓN"):
            _paragraphs(
                section,
                "EL EMPLEADOR suministrará la inducción, información y formación razonablemente necesarias para el cargo, las herramientas, los riesgos y los cambios relevantes de proceso. La falta de capacitación exigible deberá considerarse al valorar desempeño o eventuales incumplimientos.",
                "La evaluación utilizará criterios previamente comunicados, objetivos, verificables y relacionados con funciones o resultados bajo control razonable de LA PERSONA TRABAJADORA. Deberá permitir retroalimentación, acceso a la información esencial de la evaluación y oportunidad razonable de mejora cuando la naturaleza del asunto lo permita.",
                "Los sistemas automatizados o de inteligencia artificial podrán apoyar análisis, pero no deberán producir de manera opaca una decisión disciplinaria, discriminatoria, de terminación u otra medida de alto impacto sin revisión humana responsable, verificación de calidad de datos y posibilidad de controvertir la información relevante."
            )

        elif is_clause and _has(section, "PROPIEDAD INTELECTUAL"):
            _paragraphs(
                section,
                "La titularidad y los derechos de explotación sobre obras, software, documentos, diseños, bases, desarrollos u otros resultados se determinarán conforme a la ley, la naturaleza de las funciones, el encargo concreto y los instrumentos escritos que resulten necesarios. Los derechos morales permanecen sometidos al régimen imperativo aplicable.",
                "Los activos, herramientas, bibliotecas, metodologías y conocimientos preexistentes de cada parte conservarán su régimen propio. Ninguna cláusula se interpretará como cesión indeterminada de toda creación futura, de conocimientos generales, experiencia profesional o desarrollos realizados fuera del ámbito jurídicamente atribuible a la relación.",
                "Cuando sea necesaria una cesión o licencia específica, deberán identificarse con suficiente precisión el activo, modalidades de explotación, alcance, territorio, duración y demás elementos requeridos por el régimen aplicable, sin perjuicio de las reglas especiales que operen por ministerio de la ley."
            )

        elif is_clause and _has(section, "DATOS PERSONALES"):
            _paragraphs(
                section,
                "EL EMPLEADOR tratará datos personales para gestión de la relación laboral, nómina, seguridad social, seguridad y salud en el trabajo, cumplimiento, administración de activos y demás finalidades legítimas e informadas, aplicando necesidad, finalidad, circulación restringida, seguridad y los derechos de los titulares.",
                "Los datos sensibles, biométricos, de salud, disciplinarios o de ubicación requerirán controles reforzados y no deberán utilizarse para finalidades incompatibles, discriminatorias o desproporcionadas. Una autorización general no reemplaza las demás bases jurídicas aplicables ni legitima recolección ilimitada.",
                "El acceso se limitará a quienes lo necesiten por función; la conservación después de terminado el vínculo se reducirá a los plazos y finalidades legales, probatorias o de defensa de derechos que correspondan."
            )

        elif is_clause and _has(section, "MONITOREO Y PRIVACIDAD"):
            _paragraphs(
                section,
                "Los controles sobre equipos, cuentas, accesos, registros, comunicaciones corporativas o ubicación deberán responder a finalidades legítimas, ser necesarios y proporcionales al riesgo e informarse con suficiente claridad. Se preferirán medidas menos intrusivas cuando permitan alcanzar razonablemente la misma finalidad.",
                "No se autoriza vigilancia permanente de espacios privados, acceso indiscriminado a comunicaciones personales ni recopilación ajena a la relación laboral. La entrega de un equipo empresarial o el uso de una red corporativa no elimina por sí solos toda expectativa legítima de privacidad.",
                "La evidencia obtenida mediante monitoreo se custodiará con acceso limitado, integridad y período de conservación apropiado y deberá valorarse dentro de las garantías de contradicción y debido proceso cuando se utilice para adoptar medidas frente a LA PERSONA TRABAJADORA."
            )

        elif is_clause and _has(section, "TERMINACIÓN") and not _has(section, "JUSTA CAUSA"):
            current = " ".join(str(item) for item in section.get("paragraphs") or [])
            _paragraphs(
                section,
                current,
                "La terminación decidida por EL EMPLEADOR deberá distinguir entre justa causa, terminación sin justa causa, vencimiento o finalización modal cuando aplique y demás hipótesis legales. La simple denominación utilizada en la comunicación no sustituye la existencia de hechos, procedimiento, autorizaciones, indemnizaciones o efectos jurídicos exigibles.",
                "Antes del cierre se verificará si existen circunstancias de estabilidad laboral reforzada, fueros, embarazo, salud, discapacidad, actividad sindical, denuncia, licencia, represalia u otras protecciones que requieran autorización o análisis reforzado. Ninguna política interna podrá presumir la renuncia de tales garantías."
            )

        elif is_clause and _has(section, "LIQUIDACIÓN Y CERTIFICACIONES"):
            _paragraphs(
                section,
                "Al finalizar el vínculo se liquidarán salarios, recargos, prestaciones, vacaciones, indemnizaciones y demás conceptos efectivamente causados, aplicando únicamente deducciones jurídicamente válidas. El comprobante final deberá discriminar bases, períodos, cantidades y valores suficientes para permitir su revisión.",
                "EL EMPLEADOR entregará las certificaciones y soportes legalmente exigibles y realizará las novedades de seguridad social que correspondan. La devolución pendiente de un activo o una controversia sobre daños no autoriza retener indiscriminadamente la totalidad de la liquidación.",
                "La firma de un recibo, paz y salvo o constancia de pago no implica renuncia a derechos ciertos e indiscutibles ni valida errores de liquidación; cualquier conciliación o transacción deberá limitarse a materias jurídicamente disponibles y cumplir los requisitos aplicables."
            )

        elif is_clause and _has(section, "NOTIFICACIONES"):
            _paragraphs(
                section,
                "Las comunicaciones formales se remitirán a los datos que cada parte haya suministrado y actualizado de manera trazable. El medio utilizado deberá ser razonablemente apto para acreditar remitente, contenido, fecha y destinatario cuando la naturaleza de la actuación lo requiera.",
                "La mensajería instantánea y las comunicaciones operativas no sustituyen documentos, audiencias, traslados, preavisos o autorizaciones que deban cumplir una forma particular. La falta de actualización de un dato de contacto se valorará según las circunstancias y no habilita ficciones de notificación contrarias a normas imperativas."
            )

        elif is_clause and _has(section, "FIRMA Y ENTREGA"):
            _paragraphs(
                section,
                "El contrato podrá suscribirse manuscrita o electrónicamente mediante un método que permita identificar al firmante, evidenciar su aprobación y resulte confiable y apropiado para la finalidad del acto. Cada parte recibirá o tendrá acceso a una copia íntegra del contrato y de los anexos que correspondan.",
                "La versión suscrita deberá preservarse sin modificaciones posteriores, con evidencia razonable de identidad, fecha, integridad y aceptación. Cualquier modificación material requerirá una nueva versión, otrosí o instrumento válido cuando corresponda y no podrá utilizarse para desconocer condiciones mínimas o derechos ya causados.",
                "La firma electrónica o digital no sustituye actuaciones laborales que por su naturaleza exijan audiencia, traslado, autorización de autoridad, constancia especial o procedimiento distinto."
            )

        final.append(section)

    composition["sections"] = final
    composition.setdefault("maturity_answers", {})["employment_release_polished"] = True
    return composition


__all__ = ["compose_employment_m33_release"]
