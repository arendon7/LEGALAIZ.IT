from __future__ import annotations

"""Pulido final del instrumento aprobable CO-EM-004.

Opera sobre la segunda pasada jurídica ya validada. Su función es retirar referencias
internas de plataforma y profundizar cláusulas residuales detectadas en la inspección
visual, sin alterar los módulos sustantivos ni el gobierno de aprobación por hash.
"""

from copy import deepcopy
from typing import Any

from m33_nda_legal_finalize import compose_nda_m33_final


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


def _contact(answers: dict, prefix: str, label: str) -> str:
    identification = _read(answers, f"{prefix}.identification", {})
    identification = identification if isinstance(identification, dict) else {}
    name = str(identification.get("name") or identification.get("legalName") or label).strip()
    email = str(identification.get("email") or "").strip()
    address = str(identification.get("address") or "").strip()
    values = [name]
    if email:
        values.append(f"correo {email}")
    if address:
        values.append(f"domicilio {address}")
    return ", ".join(values)


def _normalize_defined_terms(text: str) -> str:
    replacements = (
        ("La Parte Reveladora", "LA PARTE REVELADORA"),
        ("La Parte Receptora", "LA PARTE RECEPTORA"),
        ("la Parte Reveladora", "LA PARTE REVELADORA"),
        ("la Parte Receptora", "LA PARTE RECEPTORA"),
        ("Parte Reveladora", "PARTE REVELADORA"),
        ("Parte Receptora", "PARTE RECEPTORA"),
        ("identificado(a) con documento No.", "con documento No."),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _clean_section_text(section: dict) -> None:
    for key in ("text", "notes"):
        if isinstance(section.get(key), str):
            section[key] = _normalize_defined_terms(section[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(section.get(key), list):
            section[key] = [
                _normalize_defined_terms(item) if isinstance(item, str) else item
                for item in section[key]
            ]


def compose_nda_m33_release(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_nda_m33_final(answers))
    personal_data = bool(_read(answers, "data.personal", False))

    party_a_contact = _contact(answers, "party_a", "LA PRIMERA PARTE")
    party_b_contact = _contact(answers, "party_b", "LA SEGUNDA PARTE")

    for section in composition.get("sections") or []:
        _clean_section_text(section)
        heading = str(section.get("heading") or "")
        heading_cf = heading.casefold()

        if "garantías sobre terceros" in heading_cf:
            _paragraph(
                section,
                "Cada parte declara que, respecto de la información y materiales que revele o ponga a disposición, "
                "tiene facultad legítima para hacerlo dentro de la finalidad autorizada y comunicará oportunamente "
                "restricciones, licencias, obligaciones de atribución, compromisos de confidencialidad y derechos de "
                "terceros que condicionen su uso. Ninguna parte incorporará conscientemente materiales obtenidos mediante "
                "acceso no autorizado, incumplimiento contractual, violación de secreto empresarial, infracción de "
                "propiedad intelectual o acto de competencia desleal. La revelación no constituye garantía general de "
                "exactitud, comerciabilidad, exclusividad o ausencia de derechos de terceros salvo estipulación expresa; "
                "sin embargo, quien conozca una restricción material deberá informarla antes de inducir a la otra parte a "
                "realizar un uso incompatible."
            )

        elif "auditoría proporcionada" in heading_cf:
            _paragraph(
                section,
                "Cuando existan indicios objetivos de incumplimiento, un incidente relevante o una obligación contractual "
                "de verificación, LA PARTE REVELADORA podrá solicitar evidencia razonable del cumplimiento: certificaciones, "
                "informes, registros pertinentes, resultados de controles o una auditoría acordada. El alcance deberá ser "
                "proporcional al riesgo, limitarse a sistemas, períodos y evidencias relacionados con la información protegida "
                "y preservar secretos de terceros, seguridad, continuidad operacional y privilegios legales. Se preferirá "
                "evidencia documental o certificaciones independientes antes de accesos intrusivos; pruebas técnicas activas "
                "requerirán autorización específica, ventana acordada y reglas de seguridad. La frecuencia, confidencialidad "
                "del informe y distribución de costos se definirán según la causa de la auditoría y no podrán utilizarse como "
                "mecanismo de vigilancia indiscriminada o extracción de información ajena a la finalidad."
            )

        elif "medidas urgentes" in heading_cf:
            _paragraph(
                section,
                "La utilización, apropiación o divulgación no autorizada de información protegida puede producir daños de "
                "difícil reparación. Ante un riesgo actual y suficientemente sustentado, la parte afectada podrá solicitar "
                "las medidas cautelares, de preservación de evidencia, cesación, entrega, bloqueo de acceso u otras protecciones "
                "que el ordenamiento permita. Esta estipulación no presume la procedencia automática de una medida, no elimina "
                "los requisitos procesales, cauciones, defensas o estándares probatorios aplicables y no impide reclamar o "
                "controvertir posteriormente los demás remedios que correspondan. Las acciones de contención deberán procurar "
                "ser proporcionales y evitar la destrucción innecesaria de evidencia."
            )

        elif "reclamos de terceros" in heading_cf:
            _paragraph(
                section,
                "La parte que conozca un reclamo, requerimiento o investigación de un tercero relacionado con información, "
                "secreto empresarial, propiedad intelectual, seguridad o, cuando aplique, datos personales, informará a la "
                "otra parte tan pronto como sea razonablemente posible si la ley lo permite. Preservará evidencia, evitará "
                "admisiones innecesarias y coordinará la defensa cuando los intereses sean comunes. Ninguna parte podrá "
                "celebrar, sin consentimiento de la otra, un acuerdo que le imponga pagos, admisiones, cesiones, licencias, "
                "restricciones o deberes de hacer; ese consentimiento no podrá negarse de manera abusiva cuando el acuerdo no "
                "afecte derechos de quien debe otorgarlo. Cada parte conserva el control de su propia defensa y deberá mitigar "
                "razonablemente los daños bajo su esfera de actuación."
            )

        elif "cesión y cambio de control" in heading_cf:
            data_reference = ", datos personales" if personal_data else ""
            _paragraph(
                section,
                "Ninguna parte cederá íntegramente este acuerdo ni ampliará el acceso a información protegida a un tercero "
                "sin consentimiento previo de la otra, salvo una reorganización societaria o transferencia empresarial que "
                "mantenga controles equivalentes, asuma por escrito las obligaciones aplicables y no incremente materialmente "
                "el riesgo. Un cambio de control que coloque información sensible en manos de un competidor, jurisdicción o "
                "entorno tecnológico materialmente distinto deberá notificarse antes de ampliar accesos cuando sea jurídicamente "
                "posible. La cesión del contrato no transfiere por sí sola secretos empresariales, licencias, derechos de "
                f"propiedad intelectual{data_reference} ni autorizaciones cuya transmisión requiera consentimiento, forma o "
                "evaluación independiente."
            )

        elif "notificaciones" in heading_cf:
            _paragraph(
                section,
                f"Para comunicaciones contractuales ordinarias se utilizarán los siguientes datos: {party_a_contact}; y "
                f"{party_b_contact}. Los avisos deberán permitir acreditar razonablemente remitente, contenido y fecha. Los "
                "incidentes de seguridad utilizarán además el canal urgente que las partes hayan designado operativamente. "
                "Cada parte deberá comunicar de forma trazable cualquier cambio de correo o domicilio; hasta entonces podrán "
                "utilizarse los datos previamente informados. Una comunicación electrónica no sustituirá una forma especial "
                "que una norma imperativa, una orden de autoridad o un mecanismo procesal exija para un acto concreto."
            )

        elif "integridad, prelación y modificaciones" in heading_cf:
            _paragraph(
                section,
                "El presente acuerdo, sus anexos expresamente incorporados y los instrumentos específicos de propiedad "
                "intelectual, seguridad, tratamiento de datos u operación que las partes suscriban para una materia determinada "
                "integran el régimen contractual aplicable a esa materia. Las condiciones específicas válidamente pactadas "
                "prevalecerán sobre las generales únicamente respecto de su objeto y deberán interpretarse de forma coherente "
                "con las obligaciones de confidencialidad que subsistan. Toda modificación material deberá constar por escrito "
                "o en un mensaje de datos que satisfaga los requisitos jurídicos aplicables. La tolerancia, demora o falta de "
                "ejercicio de un derecho no implica renuncia; la invalidez o ineficacia de una estipulación no afectará las "
                "demás y se sustituirá, cuando sea posible, por una regla válida que preserve razonablemente su finalidad lícita."
            )

        elif "firma y evidencia electrónica" in heading_cf:
            _paragraph(
                section,
                "El acuerdo podrá suscribirse manuscrita o electrónicamente. Cuando se utilicen mensajes de datos, el método "
                "deberá permitir identificar al firmante, evidenciar su aprobación y ser confiable y apropiado para la finalidad; "
                "la copia deberá permanecer accesible para consulta posterior y conservar integridad, versión, fecha y evidencia "
                "de aceptación. La fecha de celebración será la correspondiente a la última firma necesaria para perfeccionar "
                "el acuerdo, según la evidencia del método utilizado. Las partes recibirán o tendrán acceso a una copia íntegra. "
                "La plataforma conservará revisiones y aprobaciones conforme a sus reglas de gobierno, sin convertir una "
                "generación automática en aprobación jurídica ni modificar el archivo después de que Jurídico y QA aprueben su hash."
            )

    composition.setdefault("maturity_answers", {})["nda_release_polished"] = True
    return composition


__all__ = ["compose_nda_m33_release"]
