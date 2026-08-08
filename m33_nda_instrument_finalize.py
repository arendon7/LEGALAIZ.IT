from __future__ import annotations

"""Capa final de instrumento para CO-EM-004.

Retira del documento visible referencias a expediente, plataforma y gobierno interno.
La trazabilidad, revisión dual y hash permanecen en el manifiesto y la Mesa Jurídica,
no dentro del contrato que las partes revisan y suscriben.
"""

from copy import deepcopy
from typing import Any

from m33_nda_release_polish import compose_nda_m33_release


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


def compose_nda_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_nda_m33_release(answers))
    personal_data = bool(_read(answers, "data.personal", False))
    controls = _read(answers, "security.controls", {})
    controls = controls if isinstance(controls, dict) else {}
    technical = str(controls.get("technical") or "controles de acceso, autenticación, cifrado y registros").strip()
    organizational = str(controls.get("organizational") or "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes").strip()
    physical = str(controls.get("physical") or "medidas físicas proporcionales al soporte y al lugar de acceso").strip()
    ai_rule = str(_read(answers, "ai.training_outputs") or "uso controlado sin entrenamiento ni retención con información protegida").strip()
    liability_rule = str(_read(answers, "term_remedies.penalty_or_liability") or "responsabilidad conforme a la ley por daños demostrados").strip()
    agreement_years = int(float(_read(answers, "term_remedies.agreement_years", 2)))
    ordinary_years = int(float(_read(answers, "term_remedies.ordinary_confidentiality_years", 5)))

    for section in composition.get("sections") or []:
        heading_cf = str(section.get("heading") or "").casefold()

        if "seguridad de la información" in heading_cf:
            _paragraph(
                section,
                f"LA PARTE RECEPTORA aplicará medidas razonables y proporcionales al riesgo, incluyendo controles técnicos de {technical}; "
                f"controles organizacionales de {organizational}; y controles físicos de {physical}. Los accesos deberán ser individualizables, "
                "revisables y limitados a la necesidad de conocer; las excepciones deberán justificarse, autorizarse, documentarse y tener fecha de cierre. "
                "Los controles deberán mantenerse durante todo el tiempo en que la información permanezca bajo custodia o acceso de la PARTE RECEPTORA. "
                "Ninguna parte podrá reducir deliberadamente las medidas de protección con el propósito o efecto de eludir la condición de secreto empresarial "
                "o el deber contractual de reserva."
            )

        elif "proveedores, nube y terceros" in heading_cf:
            data_tail = (
                " Cuando un tercero trate datos personales por cuenta de alguna parte, deberán documentarse previamente los roles, instrucciones y garantías aplicables bajo la normativa correspondiente."
                if personal_data
                else " Si en el futuro un tercero fuera a tratar datos personales por cuenta de alguna parte, ese tratamiento requerirá habilitación y documentación separadas antes de conceder el acceso."
            )
            _paragraph(
                section,
                "El uso de nube, repositorios, asesores, proveedores o subcontratistas que puedan acceder a información protegida requiere autorización compatible con la finalidad del acuerdo y controles equivalentes de confidencialidad, seguridad, retención, respaldo, eliminación y respuesta a incidentes. "
                "La parte que habilite al tercero deberá conocer dónde y para qué se almacena o procesa la información, verificar condiciones contractuales y de seguridad, limitar el acceso al mínimo necesario y gestionar oportunamente su retiro, devolución o eliminación al finalizar el servicio. "
                "La intervención de un tercero no libera a la parte que lo habilita de sus deberes de selección, instrucción, supervisión y respuesta."
                + data_tail
            )

        elif "inteligencia artificial" in heading_cf:
            _paragraph(
                section,
                f"Las partes autorizan únicamente el uso de sistemas de inteligencia artificial bajo la siguiente condición contractual: {ai_rule}. "
                "No se cargarán secretos empresariales, credenciales, código restringido, información confidencial de terceros ni otros activos protegidos en herramientas no autorizadas. "
                "Antes de utilizar un sistema se verificarán proveedor, modelo o servicio, finalidad, condiciones de uso, retención, entrenamiento, ubicación cuando sea relevante, controles de acceso, trazabilidad y posibilidad de revisión humana. "
                "Las salidas deberán revisarse antes de incorporarse a decisiones o entregables y no se presumirán exactas, originales, exclusivas ni libres de derechos de terceros. "
                "Esta cláusula establece obligaciones contractuales de gobernanza tecnológica y no atribuye a políticas públicas o normas sectoriales un alcance de ley general que no tengan."
            )

        elif "desarrollo independiente y conocimiento residual" in heading_cf and not personal_data:
            _paragraph(
                section,
                "Podrá utilizarse conocimiento general y experiencia profesional sin reproducir Información Confidencial, siempre que exista evidencia de desarrollo independiente. "
                "No se reconoce una excepción amplia de memoria residual para secretos empresariales, código, datasets, estrategias, combinaciones identificables o reproducciones sustanciales. "
                "La experiencia legítimamente adquirida no autoriza reconstruir, extraer o explotar activos protegidos ni aprovechar una ventaja obtenida mediante incumplimiento del presente acuerdo."
            )

        elif "duración y supervivencia" in heading_cf:
            data_survival = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"El acuerdo tendrá una vigencia operativa de {agreement_years} años contados desde su firma, salvo terminación anticipada conforme a sus estipulaciones. "
                f"La confidencialidad contractual ordinaria subsistirá durante {ordinary_years} años contados desde la última revelación de la información correspondiente. "
                "Los secretos empresariales conservarán protección mientras reúnan los requisitos jurídicos que les otorgan esa condición, aunque dicho período exceda la vigencia contractual ordinaria. "
                f"Las obligaciones sobre propiedad intelectual, conservación probatoria, incidentes, copias retenidas{data_survival} y demás deberes que por su naturaleza deban sobrevivir continuarán por el tiempo que resulte del instrumento específico o de la ley. "
                "La expiración no autoriza un uso nuevo de información recibida durante la vigencia."
            )

        elif "responsabilidad y mitigación" in heading_cf:
            _paragraph(
                section,
                f"Las partes acuerdan como regla de responsabilidad para este contrato: {liability_rule}. Esta estipulación no constituye por sí sola cláusula penal, liquidación anticipada de perjuicios ni presunción de daño. "
                "Quien reclame deberá sustentar incumplimiento, daño, causalidad y cuantía conforme al régimen aplicable, sin perjuicio de las presunciones o remedios que una norma imperativa establezca. "
                "Las partes deberán adoptar medidas razonables de contención y mitigación, preservar evidencia y cooperar para evitar la expansión innecesaria del daño. "
                "Cualquier límite de responsabilidad que se pretenda incorporar deberá ser expreso, cuantificado o determinable y revisado frente a dolo, culpa grave, derechos de terceros y materias legalmente indisponibles."
            )

        elif "reclamos de terceros" in heading_cf:
            data_reference = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"La parte que conozca un reclamo, requerimiento o investigación de un tercero relacionado con información, secreto empresarial, propiedad intelectual, seguridad{data_reference} informará a la otra parte tan pronto como sea razonablemente posible si la ley lo permite. "
                "Preservará evidencia, evitará admisiones innecesarias y coordinará la defensa cuando los intereses sean comunes. Ninguna parte podrá celebrar, sin consentimiento de la otra, un acuerdo que le imponga pagos, admisiones, cesiones, licencias, restricciones o deberes de hacer; ese consentimiento no podrá negarse de manera abusiva cuando el acuerdo no afecte derechos de quien debe otorgarlo. "
                "Cada parte conserva el control de su propia defensa y deberá mitigar razonablemente los daños bajo su esfera de actuación."
            )

        elif "integridad, prelación y modificaciones" in heading_cf:
            data_instrument = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"El presente acuerdo, sus anexos expresamente incorporados y los instrumentos específicos de propiedad intelectual, seguridad{data_instrument} u operación que las partes suscriban para una materia determinada integran el régimen contractual aplicable a esa materia. "
                "Las condiciones específicas válidamente pactadas prevalecerán sobre las generales únicamente respecto de su objeto y deberán interpretarse de forma coherente con las obligaciones de confidencialidad que subsistan. "
                "Toda modificación material deberá constar por escrito o en un mensaje de datos que satisfaga los requisitos jurídicos aplicables. La tolerancia, demora o falta de ejercicio de un derecho no implica renuncia; la invalidez o ineficacia de una estipulación no afectará las demás y se sustituirá, cuando sea posible, por una regla válida que preserve razonablemente su finalidad lícita."
            )

        elif "firma y evidencia electrónica" in heading_cf:
            _paragraph(
                section,
                "El acuerdo podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos, el método deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad; la copia deberá permanecer accesible para consulta posterior y conservar integridad, versión, fecha y evidencia de aceptación. "
                "La fecha de celebración será la correspondiente a la última firma necesaria para perfeccionar el acuerdo, según la evidencia del método utilizado. Las partes recibirán o tendrán acceso a una copia íntegra. "
                "La versión suscrita deberá preservarse sin modificaciones posteriores; cualquier cambio material requerirá una nueva versión y una nueva manifestación de aceptación de las partes cuando corresponda."
            )

    composition.setdefault("maturity_answers", {})["nda_instrument_finalized"] = True
    return composition


__all__ = ["compose_nda_m33_instrument"]
