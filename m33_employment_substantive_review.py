from __future__ import annotations

"""Cierre jurídico sustantivo de CO-LA-002 posterior a la trazabilidad M33.4.

La capa corrige únicamente tres materias verificadas contra el CST vigente:
período de prueba, licencias remuneradas y debido proceso disciplinario.
No infiere un pacto de período de prueba cuando la entrevista no lo recoge.
"""

from copy import deepcopy
from typing import Any

from m33_4_employment_source_finalize import (
    compose_employment_m33_release as compose_employment_m33_release_base,
)


def _heading(section: dict) -> str:
    return str(section.get("heading") or "").casefold()


def _set_paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


PROBATION_TEXT = (
    "El período de prueba solo existe cuando ha sido estipulado de manera expresa y por escrito. "
    "Esta cláusula no constituye por sí sola un pacto de período de prueba ni permite presumirlo a partir "
    "del inicio de la prestación del servicio. Si las partes deciden pactarlo válidamente, su duración no "
    "podrá exceder de dos (2) meses; en contratos a término fijo inferiores a un (1) año no podrá superar "
    "la quinta parte del término inicialmente pactado, sin exceder en ningún caso dos (2) meses; y entre "
    "el mismo EMPLEADOR y LA PERSONA TRABAJADORA no será válida una nueva estipulación en contratos "
    "sucesivos, salvo para el primero. Durante cualquier período de prueba válidamente pactado subsisten "
    "el salario, la seguridad social, la seguridad y salud en el trabajo y los demás derechos laborales. "
    "Su terminación no autoriza discriminación, represalias, abuso del derecho ni desconocimiento de "
    "protecciones de estabilidad reforzada que resulten aplicables."
)

LICENSES_TEXT = (
    "EL EMPLEADOR reconocerá las licencias remuneradas legalmente exigibles y aplicará procedimientos "
    "de aviso y soporte razonables, proporcionales y compatibles con la urgencia de cada caso. Entre ellas "
    "se encuentran las necesarias para ejercer el sufragio; desempeñar cargos oficiales transitorios de "
    "forzosa aceptación; atender una grave calamidad doméstica debidamente comprobada en los términos "
    "legales; desempeñar comisiones sindicales inherentes a la organización o asistir al entierro de "
    "compañeros de trabajo bajo las condiciones legales; asistir a citas médicas de urgencia o a citas "
    "programadas con especialistas con el soporte exigible; cumplir obligaciones escolares como acudiente "
    "cuando la asistencia de LA PERSONA TRABAJADORA sea obligatoria por requerimiento del centro educativo; "
    "y atender citaciones judiciales, administrativas o legales. El día de descanso remunerado por uso "
    "certificado de bicicleta como medio de transporte opera únicamente cuando sea acordado con EL EMPLEADOR "
    "y se cumplan las condiciones legales. La urgencia podrá justificar un aviso posterior y no se exigirá "
    "información excesiva, irrelevante o desproporcionada para acreditar la situación."
)

DISCIPLINARY_TEXT = (
    "Toda actuación dirigida a imponer una sanción disciplinaria respetará, como mínimo, dignidad, "
    "presunción de inocencia, in dubio pro disciplinado, proporcionalidad, defensa, contradicción y "
    "controversia de las pruebas, intimidad, lealtad y buena fe, imparcialidad, buen nombre, honra y "
    "non bis in idem. EL EMPLEADOR comunicará formalmente la apertura; indicará por escrito los hechos, "
    "conductas u omisiones; trasladará la totalidad de las pruebas que los sustentan; y concederá a "
    "LA PERSONA TRABAJADORA un término no inferior a cinco (5) días para pronunciarse, controvertir y "
    "aportar pruebas. Si los descargos son verbales, se levantará un acta que transcriba la versión rendida. "
    "La decisión definitiva será motivada, identificará específicamente sus causas, impondrá únicamente "
    "una sanción proporcional cuando haya lugar y permitirá impugnación. El procedimiento se adelantará "
    "en un término razonable conforme al principio de inmediatez, sin perjuicio de reglas más favorables "
    "previstas en convención colectiva, laudo arbitral o reglamento interno. Cuando LA PERSONA TRABAJADORA "
    "esté afiliada a una organización sindical, podrá ser asistida o acompañada en los términos legales por "
    "uno (1) o dos (2) representantes sindicales que sean trabajadores de la empresa y estén presentes en "
    "la diligencia. Si tiene discapacidad, deberán implementarse medidas y ajustes razonables que garanticen "
    "comunicación y comprensión recíproca. El uso de tecnologías de la información y las comunicaciones "
    "solo procederá cuando LA PERSONA TRABAJADORA cuente con esas herramientas a disposición. Para "
    "trabajadores del hogar y micro o pequeñas empresas de menos de diez (10) trabajadores opera la "
    "excepción legal al procedimiento completo, sin perjuicio de la audiencia previa, la defensa y el "
    "debido proceso."
)


def compose_employment_m33_substantive(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_employment_m33_release_base(answers))
    found: set[str] = set()

    for section in composition.get("sections") or []:
        if section.get("_type") != "clause":
            continue
        heading = _heading(section)

        if "período de prueba" in heading or "periodo de prueba" in heading:
            _set_paragraph(section, PROBATION_TEXT)
            found.add("probation")
        elif "licencias y calamidades" in heading:
            _set_paragraph(section, LICENSES_TEXT)
            found.add("licenses")
        elif "debido proceso disciplinario" in heading:
            _set_paragraph(section, DISCIPLINARY_TEXT)
            found.add("disciplinary")

    expected = {"probation", "licenses", "disciplinary"}
    if found != expected:
        raise ValueError(
            "CO-LA-002 revisión sustantiva: cláusulas esperadas no localizadas: "
            + ", ".join(sorted(expected - found))
        )

    maturity = composition.setdefault("maturity_answers", {})
    maturity["employment_substantive_review"] = "2026-08-11"
    maturity["probation_inference_policy"] = "written_express_stipulation_required"
    maturity["licenses_reviewed_against_cst57"] = True
    maturity["disciplinary_reviewed_against_cst115"] = True
    return composition


__all__ = ["compose_employment_m33_substantive"]
