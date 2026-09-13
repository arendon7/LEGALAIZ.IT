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


def _client_facing_controls(value: Any) -> str:
    """Conserva el dato dinámico, pero desarrolla siglas técnicas para el lector contractual."""
    text = str(value or "").strip()
    if "MFA" in text and "multifactor" not in text.casefold():
        text = text.replace("MFA", "autenticación multifactor (MFA)")
    return text


def compose_nda_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_nda_m33_release(answers))
    personal_data = bool(_read(answers, "data.personal", False))
    controls = _read(answers, "security.controls", {})
    controls = controls if isinstance(controls, dict) else {}
    technical = _client_facing_controls(
        controls.get("technical") or "controles de acceso, autenticación, cifrado y registros"
    )
    organizational = str(controls.get("organizational") or "mínimo privilegio, capacitación, gestión de terceros y respuesta a incidentes").strip()
    physical = str(controls.get("physical") or "medidas físicas proporcionales al soporte y al lugar de acceso").strip()
    ai_rule = str(_read(answers, "ai.training_outputs") or "uso controlado sin entrenamiento ni retención con información protegida").strip()
    liability_rule = str(_read(answers, "term_remedies.penalty_or_liability") or "responsabilidad conforme a la ley por daños demostrados").strip()
    agreement_years = int(float(_read(answers, "term_remedies.agreement_years", 2)))
    ordinary_years = int(float(_read(answers, "term_remedies.ordinary_confidentiality_years", 5)))
    purpose = str(_read(answers, "agreement.purpose") or "desarrollar la finalidad común expresamente acordada por las partes").strip()
    reference = str(_read(answers, "agreement.reference") or "la relación negocial identificada por las partes").strip()

    for section in composition.get("sections") or []:
        heading = str(section.get("heading") or "")
        heading_cf = heading.casefold()
        is_clause = section.get("_type") == "clause"

        if heading_cf.strip() == "consideraciones":
            section.pop("text", None)
            section["paragraphs"] = [
                f"PRIMERA: Las partes prevén intercambiar información no pública en relación con {reference}, exclusivamente para {purpose}; por ello consideran necesario fijar de manera previa y verificable las condiciones de acceso, uso, custodia, revelación, conservación y cierre aplicables a dicha información.",
                "SEGUNDA: Las partes reconocen que la confidencialidad contractual y el secreto empresarial son categorías relacionadas pero no equivalentes. La obligación de reserva puede proteger información que no reúna todos los requisitos de un secreto empresarial, mientras que la protección reforzada del secreto exige que concurran y se mantengan los presupuestos jurídicos correspondientes y medidas razonables de protección.",
                "TERCERA: La información se administrará conforme a una finalidad determinada, al principio de necesidad de conocer y a controles proporcionales a su sensibilidad y riesgo. La revelación a una persona autorizada no convierte la información en pública ni amplía la finalidad, y cada parte deberá poder identificar razonablemente quién tuvo acceso, para qué lo tuvo y cuándo debió cesar.",
                "CUARTA: La entrega o acceso a información no transfiere por sí sola propiedad intelectual, titularidad sobre materiales preexistentes, licencias, exclusividad, derechos sobre resultados ni facultades de explotación distintas de las expresamente pactadas. Cuando un resultado requiera cesión, licencia o asignación específica, deberá instrumentarse con el alcance exigido por el régimen jurídico aplicable.",
                "QUINTA: El uso de proveedores, servicios en la nube, repositorios externos o sistemas de inteligencia artificial puede modificar materialmente el riesgo de divulgación, retención, reutilización o acceso por terceros. En consecuencia, tales herramientas solo podrán utilizarse dentro de la finalidad autorizada, con controles equivalentes y sin trasladar información protegida a entornos no autorizados.",
                "SEXTA: Las partes pretenden que este acuerdo funcione como un instrumento operativo y probatorio de prevención, no como una declaración genérica de reserva. Por ello incorporan reglas sobre incidentes, devolución o eliminación, conservación excepcional, evidencia, responsabilidad y medidas urgentes, sin sustituir requisitos imperativos, competencias de autoridad ni cargas probatorias que correspondan en una controversia concreta.",
            ]
            continue

        # Todas las sustituciones de esta capa se limitan a cláusulas. La portada y
        # la sección de comparecencia pueden contener palabras como "IA" o "PI" en
        # el título y nunca deben confundirse con módulos sustantivos.
        if is_clause and "definiciones operativas" in heading_cf and not personal_data:
            _paragraph(
                section,
                "Para interpretar y operar el acuerdo se utilizarán, según el rol real de cada operación, las categorías PARTE REVELADORA, PARTE RECEPTORA, INFORMACIÓN CONFIDENCIAL, SECRETO EMPRESARIAL, MATERIAL PREEXISTENTE, RESULTADO, INCIDENTE, PROVEEDOR AUTORIZADO y, cuando corresponda, SISTEMA DE INTELIGENCIA ARTIFICIAL. "
                "Estas definiciones describen funciones y activos dentro del acuerdo; no modifican por sí mismas la titularidad, autoría, representación, relación laboral, licenciamiento, responsabilidad ni condición jurídica de secreto empresarial. La denominación utilizada deberá interpretarse conforme a los hechos y al alcance de cada revelación o acceso."
            )

        elif is_clause and "finalidad autorizada" in heading_cf:
            permitted = str(_read(answers, "access.permitted_use") or purpose).strip()
            _paragraph(
                section,
                f"La información solo podrá utilizarse para {purpose}; dentro de esa finalidad, el uso permitido se limita a {permitted}. "
                "Quedan excluidos los usos secundarios incompatibles, la prospección ajena al proyecto, la publicidad basada en información reservada, las evaluaciones comparativas destinadas a identificar o reconstruir activos protegidos, la extracción de bases, el entrenamiento no autorizado, la ingeniería competitiva y cualquier explotación que exceda la necesidad documentada. "
                "Un cambio material de finalidad requerirá autorización previa, expresa y trazable de la parte legitimada para concederla; el silencio, la tolerancia operativa o la mera disponibilidad técnica de la información no se interpretarán como ampliación del permiso."
            )

        elif is_clause and "seguridad de la información" in heading_cf:
            _paragraph(
                section,
                f"LA PARTE RECEPTORA aplicará medidas razonables y proporcionales al riesgo, incluyendo controles técnicos de {technical}; "
                f"controles organizacionales de {organizational}; y controles físicos de {physical}. Los accesos deberán ser individualizables, "
                "revisables y limitados a la necesidad de conocer; las excepciones deberán justificarse, autorizarse, documentarse y tener fecha de cierre. "
                "Los controles deberán mantenerse durante todo el tiempo en que la información permanezca bajo custodia o acceso de la PARTE RECEPTORA. "
                "Ninguna parte podrá reducir deliberadamente las medidas de protección con el propósito o efecto de eludir la condición de secreto empresarial "
                "o el deber contractual de reserva."
            )

        elif is_clause and "proveedores, nube y terceros" in heading_cf:
            data_tail = (
                " Cuando un tercero trate datos personales por cuenta de alguna parte, deberán documentarse previamente los roles, instrucciones y garantías aplicables bajo la normativa correspondiente."
                if personal_data
                else ""
            )
            _paragraph(
                section,
                "El uso de nube, repositorios, asesores, proveedores o subcontratistas que puedan acceder a información protegida requiere autorización compatible con la finalidad del acuerdo y controles equivalentes de confidencialidad, seguridad, retención, respaldo, eliminación y respuesta a incidentes. "
                "La parte que habilite al tercero deberá conocer dónde y para qué se almacena o procesa la información, verificar condiciones contractuales y de seguridad, limitar el acceso al mínimo necesario y gestionar oportunamente su retiro, devolución o eliminación al finalizar el servicio. "
                "La intervención de un tercero no libera a la parte que lo habilita de sus deberes de selección, instrucción, supervisión y respuesta."
                + data_tail
            )

        elif is_clause and "inteligencia artificial" in heading_cf:
            _paragraph(
                section,
                f"Las partes autorizan únicamente el uso de sistemas de inteligencia artificial bajo la siguiente condición contractual: {ai_rule}. "
                "No se cargarán secretos empresariales, credenciales, código restringido, información confidencial de terceros ni otros activos protegidos en herramientas no autorizadas. "
                "Antes de utilizar un sistema se verificarán proveedor, modelo o servicio, finalidad, condiciones de uso, retención, entrenamiento, ubicación cuando sea relevante, controles de acceso, trazabilidad y posibilidad de revisión humana. "
                "Las salidas deberán revisarse antes de incorporarse a decisiones o entregables y no se presumirán exactas, originales, exclusivas ni libres de derechos de terceros. "
                "Esta cláusula establece obligaciones contractuales de gobernanza tecnológica y no atribuye a políticas públicas o normas sectoriales un alcance de ley general que no tengan."
            )

        elif is_clause and "desarrollo independiente y conocimiento residual" in heading_cf and not personal_data:
            _paragraph(
                section,
                "Podrá utilizarse conocimiento general y experiencia profesional sin reproducir Información Confidencial, siempre que exista evidencia de desarrollo independiente. "
                "No se reconoce una excepción amplia de memoria residual para secretos empresariales, código, datasets, estrategias, combinaciones identificables o reproducciones sustanciales. "
                "La experiencia legítimamente adquirida no autoriza reconstruir, extraer o explotar activos protegidos ni aprovechar una ventaja obtenida mediante incumplimiento del presente acuerdo."
            )

        elif is_clause and "duración y supervivencia" in heading_cf:
            data_survival = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"El acuerdo tendrá una vigencia operativa de {agreement_years} años contados desde su firma, salvo terminación anticipada conforme a sus estipulaciones. "
                f"La confidencialidad contractual ordinaria subsistirá durante {ordinary_years} años contados desde la última revelación de la información correspondiente. "
                "Los secretos empresariales conservarán protección mientras reúnan los requisitos jurídicos que les otorgan esa condición, aunque dicho período exceda la vigencia contractual ordinaria. "
                f"Las obligaciones sobre propiedad intelectual, conservación probatoria, incidentes, copias retenidas{data_survival} y demás deberes que por su naturaleza deban sobrevivir continuarán por el tiempo que resulte del instrumento específico o de la ley. "
                "La expiración no autoriza un uso nuevo de información recibida durante la vigencia."
            )

        elif is_clause and "conservación y legal hold" in heading_cf:
            ordinal = heading.split(":", 1)[0].strip() if ":" in heading else ""
            section["heading"] = f"{ordinal}: CONSERVACIÓN PROBATORIA Y RETENCIÓN LEGAL" if ordinal else "CONSERVACIÓN PROBATORIA Y RETENCIÓN LEGAL"

        elif is_clause and "responsabilidad y mitigación" in heading_cf:
            _paragraph(
                section,
                f"Las partes acuerdan como regla de responsabilidad para este contrato: {liability_rule}. Esta estipulación no constituye por sí sola cláusula penal, liquidación anticipada de perjuicios ni presunción de daño. "
                "Quien reclame deberá sustentar incumplimiento, daño, causalidad y cuantía conforme al régimen aplicable, sin perjuicio de las presunciones o remedios que una norma imperativa establezca. "
                "Las partes deberán adoptar medidas razonables de contención y mitigación, preservar evidencia y cooperar para evitar la expansión innecesaria del daño. "
                "Cualquier límite de responsabilidad que se pretenda incorporar deberá ser expreso, cuantificado o determinable y revisado frente a dolo, culpa grave, derechos de terceros y materias legalmente indisponibles."
            )

        elif is_clause and "reclamos de terceros" in heading_cf:
            data_reference = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"La parte que conozca un reclamo, requerimiento o investigación de un tercero relacionado con información, secreto empresarial, propiedad intelectual, seguridad{data_reference} informará a la otra parte tan pronto como sea razonablemente posible si la ley lo permite. "
                "Preservará evidencia, evitará admisiones innecesarias y coordinará la defensa cuando los intereses sean comunes. Ninguna parte podrá celebrar, sin consentimiento de la otra, un acuerdo que le imponga pagos, admisiones, cesiones, licencias, restricciones o deberes de hacer; ese consentimiento no podrá negarse de manera abusiva cuando el acuerdo no afecte derechos de quien debe otorgarlo. "
                "Cada parte conserva el control de su propia defensa y deberá mitigar razonablemente los daños bajo su esfera de actuación."
            )

        elif is_clause and "restricciones comerciales" in heading_cf:
            _paragraph(
                section,
                "El presente acuerdo no crea obligaciones de no competencia, no captación, exclusividad, reparto de mercado, contratación preferente ni impedimentos generales para desarrollar actividades lícitas de manera independiente. "
                "La protección recae sobre la información y los derechos jurídicamente protegibles, no sobre el conocimiento general, la experiencia legítima ni la competencia por méritos. "
                "Cualquier restricción comercial adicional deberá constar en instrumento separado, responder a una finalidad legítima, estar delimitada en alcance, sujetos, duración y ámbito de aplicación, y someterse a revisión frente a las normas imperativas de libre competencia y demás reglas aplicables."
            )

        elif is_clause and "solución de controversias" in heading_cf and not personal_data:
            _paragraph(
                section,
                "Las partes procurarán resolver las controversias mediante negociación directa entre responsables con capacidad de decisión y, si no existe solución, conciliación ante un centro o conciliador legalmente competente. Lo anterior no impide solicitar medidas cautelares o urgentes para contener una divulgación, preservar evidencia o evitar un daño inminente, ni desplaza competencias administrativas, penales, de propiedad intelectual, secretos empresariales o competencia desleal. "
                "El acuerdo se interpreta conforme al derecho aplicable en Colombia; la competencia territorial o judicial concreta se determinará por las normas aplicables y los hechos del caso, salvo pacto válido posterior que la defina expresamente."
            )

        elif is_clause and "integridad, prelación y modificaciones" in heading_cf:
            data_instrument = ", tratamiento de datos personales" if personal_data else ""
            _paragraph(
                section,
                f"El presente acuerdo, sus anexos expresamente incorporados y los instrumentos específicos de propiedad intelectual, seguridad{data_instrument} u operación que las partes suscriban para una materia determinada integran el régimen contractual aplicable a esa materia. "
                "Las condiciones específicas válidamente pactadas prevalecerán sobre las generales únicamente respecto de su objeto y deberán interpretarse de forma coherente con las obligaciones de confidencialidad que subsistan. "
                "Toda modificación material deberá constar por escrito o en un mensaje de datos que satisfaga los requisitos jurídicos aplicables. La tolerancia, demora o falta de ejercicio de un derecho no implica renuncia; la invalidez o ineficacia de una estipulación no afectará las demás y se sustituirá, cuando sea posible, por una regla válida que preserve razonablemente su finalidad lícita."
            )

        elif is_clause and "firma y evidencia electrónica" in heading_cf:
            _paragraph(
                section,
                "El acuerdo podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos, el método deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad; la copia deberá permanecer accesible para consulta posterior y conservar integridad, versión, fecha y evidencia de aceptación. "
                "La fecha de celebración será la correspondiente a la última firma necesaria para perfeccionar el acuerdo, según la evidencia del método utilizado. Las partes recibirán o tendrán acceso a una copia íntegra. "
                "La versión suscrita deberá preservarse sin modificaciones posteriores; cualquier cambio material requerirá una nueva versión y una nueva manifestación de aceptación de las partes cuando corresponda."
            )

    composition.setdefault("maturity_answers", {})["nda_instrument_finalized"] = True
    return composition


__all__ = ["compose_nda_m33_instrument"]
