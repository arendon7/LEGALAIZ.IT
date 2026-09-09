from __future__ import annotations

"""Segunda pasada jurídica del contrato laboral CO-LA-002 M33.0.

Parte de la biblioteca laboral madura y ajusta la salida a la fecha efectiva, la
modalidad y los hechos del expediente. No reutiliza reglas de contratos civiles ni
infiere datos personales ausentes. La aprobación jurídica y QA siguen siendo humanas
sobre el mismo hash del candidato limpio.
"""

from copy import deepcopy
from datetime import date
import re
from typing import Any

from legalai_platform.contractual_maturity import ORDINALS
from m33_contractual_adapters import compose_employment_m33


_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
_HOUR_WORDS = {42: "cuarenta y dos", 44: "cuarenta y cuatro", 46: "cuarenta y seis", 47: "cuarenta y siete", 48: "cuarenta y ocho"}


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


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _date_es(value: Any) -> str:
    parsed = _date(value)
    if not parsed:
        return str(value or "").strip()
    return f"{parsed.day} de {_MONTHS[parsed.month]} de {parsed.year}"


def _money(value: Any) -> str:
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value or "").strip()
    return "COP $" + f"{amount:,}".replace(",", ".")


def _id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.isdigit() and len(text) >= 7:
        groups: list[str] = []
        while text:
            groups.append(text[-3:])
            text = text[:-3]
        return ".".join(reversed(groups))
    return text


def _employer(answers: dict) -> dict[str, str]:
    employer = _read(answers, "employer", {})
    signatory = _read(answers, "employerSignatory", {})
    if not isinstance(employer, dict):
        employer = {}
    if not isinstance(signatory, dict):
        signatory = {}
    return {
        "type": str(employer.get("type") or "").strip().casefold(),
        "name": str(employer.get("legalName") or employer.get("naturalPersonFullName") or "EL EMPLEADOR").strip(),
        "id": _id(employer.get("identificationNumber")),
        "domicile": str(employer.get("domicile") or employer.get("address") or "").strip(),
        "signatory": str(signatory.get("fullName") or signatory.get("name") or "").strip(),
        "signatory_id": _id(signatory.get("identificationNumber") or signatory.get("id_number") or signatory.get("identification")),
        "capacity": str(signatory.get("positionOrCapacity") or signatory.get("capacity") or "representante autorizado").strip(),
    }


def _worker(answers: dict) -> dict[str, str]:
    worker = _read(answers, "worker", {})
    if not isinstance(worker, dict):
        worker = {}
    return {
        "name": str(worker.get("fullName") or "LA PERSONA TRABAJADORA").strip(),
        "id": _id(worker.get("identificationNumber")),
        "domicile": str(worker.get("domicile") or worker.get("address") or "").strip(),
    }


def _join_identity(name: str, identity: str, domicile: str, *, legal: bool = False) -> str:
    parts = [name]
    if identity:
        parts.append(("identificada con NIT " if legal else "identificado(a) con documento No. ") + identity)
    if domicile:
        parts.append("con domicilio en " + domicile)
    return ", ".join(parts)


def _appearance(answers: dict, title: str) -> str:
    employer = _employer(answers)
    worker = _worker(answers)
    is_legal = employer["type"] == "legal_person"
    employer_text = _join_identity(employer["name"], employer["id"], employer["domicile"], legal=is_legal)
    if is_legal and employer["signatory"]:
        employer_text += f", representada para este acto por {employer['signatory']}"
        if employer["signatory_id"]:
            employer_text += f", identificado(a) con documento No. {employer['signatory_id']}"
        employer_text += f", quien actúa en calidad de {employer['capacity']}"
    employer_text += ", en adelante EL EMPLEADOR"
    worker_text = _join_identity(worker["name"], worker["id"], worker["domicile"]) + ", en adelante LA PERSONA TRABAJADORA"
    return (
        f"Entre {employer_text}, y {worker_text}, se celebra el presente {title}. Las partes reconocen que la relación es laboral, "
        "que las normas mínimas y la realidad de la ejecución prevalecen sobre estipulaciones incompatibles y que ninguna cláusula "
        "puede interpretarse como renuncia a derechos ciertos e indiscutibles."
    )


def _weekly_limit(start: date | None) -> int:
    if start is None or start >= date(2026, 7, 15):
        return 42
    if start >= date(2025, 7, 15):
        return 44
    if start >= date(2024, 7, 15):
        return 46
    if start >= date(2023, 7, 15):
        return 47
    return 48


def _night_start(start: date | None) -> str:
    if start is None or start >= date(2025, 12, 25):
        return "7:00 p. m."
    return "9:00 p. m."


def _rest_day_surcharge(start: date | None) -> tuple[int, str]:
    if start is not None and start >= date(2027, 7, 1):
        return 100, ""
    if start is None or start >= date(2026, 7, 1):
        return 90, "A partir del 1 de julio de 2027 el recargo mínimo será del cien por ciento (100 %), salvo aplicación anticipada más favorable."
    if start >= date(2025, 7, 1):
        return 80, "A partir del 1 de julio de 2026 será del noventa por ciento (90 %) y desde el 1 de julio de 2027 del cien por ciento (100 %), salvo aplicación anticipada más favorable."
    return 75, "La tarifa deberá actualizarse automáticamente conforme al régimen transitorio vigente al momento de causación."


def _schedule_label(value: Any) -> str:
    mapping = {
        "fixed": "distribución fija",
        "flexible": "distribución flexible",
        "rotating": "turnos rotativos",
        "special": "ciclo especial legalmente aplicable",
    }
    raw = str(value or "").strip()
    return mapping.get(raw.casefold(), raw or "distribución por definir")


def _modality(answers: dict) -> str:
    raw = str(_first(
        answers,
        "contract.type",
        "employment.contractType",
        "employment.modality",
        "work.contractType",
        "need_type",
        default="indefinite",
    ) or "").strip().casefold()
    if raw in {"fixed", "fixed_term", "término fijo", "termino fijo", "temporal con fecha cierta"}:
        return "fixed"
    if raw in {"work", "work_labor", "obra", "obra o labor", "obra o labor específica", "obra o labor especifica"}:
        return "work"
    return "indefinite"


def _title_for_modality(modality: str) -> str:
    return {
        "fixed": "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO FIJO",
        "work": "CONTRATO INDIVIDUAL DE TRABAJO POR DURACIÓN DE OBRA O LABOR DETERMINADA",
        "indefinite": "CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO",
    }[modality]


def _duration_text(answers: dict, modality: str) -> str:
    if modality == "fixed":
        end = _first(answers, "contract.endDate", "employment.endDate", "work.endDate")
        end_text = _date_es(end) if end else "la fecha cierta incorporada y verificada antes de firma"
        return (
            f"El contrato se celebra a término fijo hasta el {end_text}. Debe constar por escrito y, sumadas sus prórrogas bajo el régimen vigente, "
            "no podrá superar cuatro (4) años. Si con treinta (30) días de antelación al vencimiento ninguna parte manifiesta su intención de terminarlo, "
            "operará la prórroga legal aplicable sin superar dicho límite. En contratos inferiores a un año deberán observarse además las reglas especiales "
            "de prórroga previstas en el artículo 46 del Código Sustantivo del Trabajo vigente. El incumplimiento de las condiciones legales de esta modalidad "
            "puede conducir a que el vínculo se entienda a término indefinido desde su inicio."
        )
    if modality == "work":
        work_description = str(_first(answers, "contract.workDescription", "employment.workDescription", "work.workDescription", default="")).strip()
        work_description = work_description or "la obra o labor descrita de forma precisa en el anexo de funciones y alcance"
        return (
            f"El contrato dura el tiempo necesario para ejecutar {work_description}. La obra o labor debe quedar identificada por escrito de forma precisa y detallada, "
            "con un hito objetivo de finalización. Si la persona trabajadora continúa prestando servicios después de terminada la obra sin documentarse una nueva y diferente, "
            "la relación podrá entenderse a término indefinido desde el inicio, conforme al artículo 46 vigente."
        )
    return (
        "El contrato es a término indefinido y permanecerá vigente mientras subsistan las causas que le dieron origen y la materia del trabajo. "
        "Su continuidad no impide las modificaciones lícitas acordadas por escrito ni la terminación por una causa y procedimiento legalmente procedentes."
    )


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


def _clean_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", lambda m: _date_es(m.group(0)), value)
    value = re.sub(r"\bdistribución\s+fixed\b", "distribución fija", value, flags=re.IGNORECASE)
    value = re.sub(r"\besquema\s+fixed\b", "esquema de distribución fija", value, flags=re.IGNORECASE)
    return value


def _clean_section(section: dict) -> dict:
    result = deepcopy(section)
    for key in ("heading", "text", "notes"):
        if key in result:
            result[key] = _clean_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_clean_text(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_clean_text(cell) for cell in row] for row in result["table"]]
    return result


def _clean_considerations(section: dict) -> None:
    if str(section.get("heading") or "").strip().casefold() != "consideraciones":
        return
    section["paragraphs"] = [
        re.sub(r"^([^:]+):\s+Que\s+", r"\1: ", str(item), flags=re.IGNORECASE)
        for item in section.get("paragraphs") or []
    ]


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


def _sources() -> list[str]:
    return [
        "Código Sustantivo del Trabajo vigente, en especial artículos 46, 47, 115, 160, 161, 162 y 168, según sus modificaciones vigentes.",
        "Ley 2466 de 2025, artículos 5, 6, 7, 10, 11, 12, 13 y 14, según el módulo laboral aplicable.",
        "Ley 2101 de 2021, sobre reducción gradual de la jornada semanal hasta cuarenta y dos (42) horas.",
        "Ley 2191 de 2022, sobre desconexión laboral.",
        "Decreto 1072 de 2015, en materia de Sistema de Gestión de Seguridad y Salud en el Trabajo.",
        "Ley 1010 de 2006, sobre prevención, corrección y sanción del acoso laboral.",
        "Ley 1581 de 2012 y Decreto 1074 de 2015, para tratamiento de datos personales en la relación laboral.",
        "Ley 527 de 1999, cuando se utilicen mensajes de datos o firma electrónica/digital.",
    ]


def compose_employment_m33_final(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_employment_m33(answers))
    modality = _modality(answers)
    title = _title_for_modality(modality)
    start = _date(_read(answers, "work.actualStartDate"))
    weekly_limit = _weekly_limit(start)
    weekly_hours = _read(answers, "schedule.weeklyHours", weekly_limit)
    schedule = _schedule_label(_read(answers, "schedule.type"))
    night_start = _night_start(start)
    surcharge, transition = _rest_day_surcharge(start)
    salary = _money(_read(answers, "compensation.baseSalary"))
    employer = _employer(answers)
    worker = _worker(answers)
    role = str(_read(answers, "role.jobTitle", "cargo definido en el expediente") or "").strip()

    final: list[dict] = []
    controls: list[dict] = []
    for original in composition.get("sections") or []:
        section = _clean_section(original)
        _clean_considerations(section)

        if section.get("_type") == "control" or "control de uso" in str(section.get("heading") or "").casefold():
            controls.append(section)
            continue

        if str(section.get("heading") or "").upper().startswith("CONTRATO DE TRABAJO"):
            section["heading"] = title
            _paragraph(section, _appearance(answers, title))

        elif _has(section, "DURACIÓN") and section.get("_type") == "clause":
            _paragraph(section, _duration_text(answers, modality))

        elif _has(section, "FECHA DE INICIO"):
            _paragraph(section, f"La prestación personal del servicio inicia el {_date_es(_read(answers, 'work.actualStartDate'))}. La afiliación al Sistema de Seguridad Social Integral y la gestión inicial de riesgos deberán realizarse de forma oportuna conforme a la ley. La falta de formalidad no permite desconocer el tiempo realmente trabajado ni los derechos causados desde la ejecución efectiva.")

        elif _has(section, "JORNADA ORDINARIA"):
            limit_words = _HOUR_WORDS.get(weekly_limit, str(weekly_limit))
            if str(_read(answers, "schedule.type", "")).casefold() == "flexible":
                distribution = "Al tratarse de distribución flexible, las partes podrán acordar jornadas variables entre cuatro (4) y nueve (9) horas ordinarias diarias, en máximo seis días por semana y con un día de descanso obligatorio, siempre que no se exceda el promedio semanal legal dentro de la jornada ordinaria."
            else:
                distribution = f"La distribución será {schedule}; el horario concreto deberá comunicarse de forma trazable y respetar descansos, trabajo nocturno, horas suplementarias y cualquier excepción legal aplicable."
            _paragraph(section, f"A la fecha de inicio del vínculo la jornada máxima ordinaria aplicable es de {limit_words} ({weekly_limit}) horas semanales. Para este contrato se pactan {weekly_hours} horas semanales. {distribution} La reducción legal de jornada no disminuye salario, prestaciones ni valor de la hora ordinaria.")

        elif _has(section, "TRABAJO SUPLEMENTARIO Y RECARGOS"):
            tail = f" {transition}" if transition else ""
            _paragraph(section, f"Para la fecha de inicio, el trabajo nocturno comienza a las {night_start} y termina a las 6:00 a. m. El trabajo suplementario no podrá exceder dos (2) horas diarias ni doce (12) semanales, salvo los regímenes sectoriales exceptuados por la ley. No se requiere permiso previo del Ministerio del Trabajo para laborar horas extras, pero EL EMPLEADOR deberá llevar el registro individual exigido por el artículo 162 del Código Sustantivo del Trabajo y entregar al trabajador que lo solicite la relación de horas y el soporte de pago. El trabajo en día de descanso obligatorio causa, como mínimo, un recargo del {surcharge} % sobre el salario ordinario correspondiente, además de los demás efectos legales aplicables.{tail}")

        elif _has(section, "DEBIDO PROCESO DISCIPLINARIO"):
            _paragraph(section, "Toda actuación dirigida a imponer una sanción disciplinaria respetará como mínimo dignidad, presunción de inocencia, in dubio pro disciplinado, proporcionalidad, defensa, contradicción de pruebas, intimidad, buena fe, imparcialidad, buen nombre, honra y non bis in idem. EL EMPLEADOR comunicará formalmente la apertura, trasladará por escrito los hechos, conductas u omisiones y la totalidad de las pruebas, concederá a LA PERSONA TRABAJADORA un término no inferior a cinco (5) días para pronunciarse y aportar o controvertir pruebas, emitirá decisión motivada y permitirá impugnación. Cuando opere la excepción legal para trabajo del hogar o micro y pequeñas empresas de menos de diez (10) trabajadores, se garantizarán en todo caso audiencia previa, defensa y debido proceso.")

        elif _has(section, "TERMINACIÓN") and section.get("_type") == "clause":
            if modality == "indefinite":
                modality_rule = "LA PERSONA TRABAJADORA podrá dar por terminado el contrato indefinido mediante preaviso de treinta (30) días calendario para facilitar el reemplazo; en ningún caso podrá pactarse o imponerse sanción por omitir ese preaviso. El preaviso no será exigible cuando la terminación unilateral del trabajador se funde en una causa imputable al empleador de las previstas legalmente."
            elif modality == "fixed":
                modality_rule = "La terminación por vencimiento del término fijo y sus prórrogas se sujetará al aviso escrito de treinta (30) días y al límite máximo de cuatro (4) años previstos en el artículo 46 vigente, sin perjuicio de las demás causales legales de terminación."
            else:
                modality_rule = "La terminación por finalización de la obra o labor exige que el objeto haya sido definido por escrito de forma precisa y que exista evidencia objetiva de su culminación; la continuidad material del servicio debe revisarse antes de cerrar el vínculo."
            _paragraph(section, f"El contrato terminará únicamente por las causas y procedimientos previstos en la ley. {modality_rule} Antes de una decisión del empleador deberán verificarse estabilidad reforzada, fueros, embarazo, salud, discapacidad, actividad sindical, denuncias, represalias y autorizaciones administrativas o judiciales que resulten exigibles.")

        elif _has(section, "SALARIO") and section.get("_type") == "clause":
            _paragraph(section, f"EL EMPLEADOR pagará a LA PERSONA TRABAJADORA un salario básico mensual de {salary}, con la periodicidad y por el medio trazable pactados. El salario remunera la jornada ordinaria; horas extras, recargos nocturnos, trabajo en día de descanso obligatorio y demás conceptos que legalmente deban reconocerse por separado se liquidarán conforme a la causación real. La denominación contractual de un pago no puede excluir su naturaleza salarial cuando en la realidad remunera directamente el servicio.")

        if section.get("_type") == "signature":
            employer_party = {
                "label": "EL EMPLEADOR",
                "name": employer["signatory"] if employer["type"] == "legal_person" and employer["signatory"] else employer["name"],
                "role": f"{employer['capacity']} de {employer['name']}" + (f" · NIT {employer['id']}" if employer["id"] else "") if employer["type"] == "legal_person" else "Empleador",
            }
            if employer["type"] == "legal_person" and employer["signatory_id"]:
                employer_party["id"] = f"Documento {employer['signatory_id']}"
            elif employer["type"] != "legal_person" and employer["id"]:
                employer_party["id"] = f"Documento {employer['id']}"
            worker_party = {"label": "LA PERSONA TRABAJADORA", "name": worker["name"], "role": role}
            if worker["id"]:
                worker_party["id"] = f"Documento {worker['id']}"
            section["parties"] = [employer_party, worker_party]

        final.append(section)

    if controls:
        control = controls[0]
        control["heading"] = "CONTROL DE USO, FUENTES Y REVISIÓN"
        control["text"] = "Documento candidato interno CO-LA-002 M33.0. La liberación exige verificar identidad, capacidad, modalidad contractual, salario, jornada, fecha efectiva, anexos, protecciones especiales, ejecución real y aprobación jurídica y QA sobre la misma revisión y hash."
        control["bullets"] = [f"Fuente jurídica de control: {source}" for source in _sources()]
        final.append(control)

    composition["sections"] = _renumber(final)
    composition["title"] = title
    composition.setdefault("maturity_answers", {})["legal_review_finalized"] = True
    composition["maturity_answers"]["employment_modality_m33"] = modality
    composition["maturity_answers"]["weekly_limit_at_start"] = weekly_limit
    composition["maturity_answers"]["rest_day_surcharge_at_start"] = surcharge
    return composition


__all__ = ["compose_employment_m33_final"]
