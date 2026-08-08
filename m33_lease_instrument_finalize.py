from __future__ import annotations

"""Cierre del instrumento firmable CO-AR-001 M33.0.

Elimina referencias residuales de workspace y desarrolla cláusulas que, aun después
del pulido jurídico, seguían siendo demasiado esquemáticas para un contrato final.
La sección interna de control y fuentes permanece intacta y externalizable.
"""

from copy import deepcopy
from typing import Any

from m33_lease_release_polish import compose_lease_m33_release


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraphs(section: dict, *items: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [item for item in items if str(item or "").strip()]


def _clean_public_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    replacements = (
        ("La ficha indicará", "El presente contrato o el anexo correspondiente indicará"),
        ("la ficha indicará", "el presente contrato o el anexo correspondiente indicará"),
        ("Cuenta informada por el arrendador", "cuenta informada por LA PARTE ARRENDADORA"),
        ("cuenta informada por el arrendador", "cuenta informada por LA PARTE ARRENDADORA"),
        ("identificado(a) con documento No.", "con documento No."),
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
            result[key] = _clean_public_text(result[key])
    for key in ("paragraphs", "bullets", "numbered"):
        if isinstance(result.get(key), list):
            result[key] = [_clean_public_text(item) for item in result[key]]
    if isinstance(result.get("table"), list):
        result["table"] = [[_clean_public_text(cell) for cell in row] for row in result["table"]]
    return result


def compose_lease_m33_instrument(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_lease_m33_release(answers))
    guarantee = _read(answers, "guarantee", {})
    guarantee = guarantee if isinstance(guarantee, dict) else {}
    details = guarantee.get("details") if isinstance(guarantee.get("details"), dict) else {}
    policy_party = str(details.get("party") or "").strip()
    policy_number = str(details.get("id_number") or "").strip()
    policy_scope = str(details.get("scope") or "").strip()
    policy_validity = str(details.get("validity") or "").strip()
    data_purpose = str(_read(answers, "data.screening.personal_data") or "celebración, ejecución, pagos, seguridad, reclamaciones y cierre contractual").strip()

    final: list[dict] = []
    for original in composition.get("sections") or []:
        section = _clean_section(original)
        if section.get("_type") == "control":
            final.append(section)
            continue
        is_clause = section.get("_type") == "clause"

        if is_clause and _has(section, "SEGUROS"):
            policy_reference = "; ".join(
                value for value in (
                    f"aseguradora o garante: {policy_party}" if policy_party else "",
                    f"referencia: {policy_number}" if policy_number else "",
                    f"cobertura informada: {policy_scope}" if policy_scope else "",
                    f"vigencia informada: {policy_validity}" if policy_validity else "",
                ) if value
            )
            _paragraphs(
                section,
                ("Para este contrato se ha informado el siguiente mecanismo de aseguramiento o garantía: " + policy_reference + ".") if policy_reference else "Cualquier seguro o garantía relacionado con el arrendamiento deberá constar en el presente contrato, póliza o anexo identificable y permitir conocer asegurador o garante, riesgos cubiertos, vigencia, límites y condiciones relevantes.",
                "La existencia de una póliza no traslada automáticamente a la aseguradora todos los riesgos de la relación ni reemplaza las obligaciones legales o contractuales de las partes. La cobertura efectiva dependerá del texto vigente de la póliza y de la ocurrencia y acreditación del riesgo asegurado.",
                "Una reclamación deberá formularse con información veraz y soportes suficientes. Ninguna parte podrá obtener doble recuperación por un mismo daño ni presentar como obligación cierta una suma que dependa todavía de evaluación, deducible, exclusión, objeción o decisión del asegurador."
            )

        elif is_clause and _has(section, "DATOS PERSONALES"):
            _paragraphs(
                section,
                f"Los datos personales suministrados con ocasión de la relación podrán tratarse para {data_purpose}, dentro de las finalidades informadas y de las bases jurídicas aplicables. El tratamiento deberá limitarse a información pertinente y razonablemente necesaria para cada finalidad.",
                "La parte que actúe como responsable del tratamiento deberá informar su identidad, canales de atención, finalidades, derechos de los titulares, destinatarios y criterios de conservación cuando corresponda. No se divulgarán antecedentes financieros, documentos de identidad, información de contacto, datos de convivencia u otra información personal a vecinos, copropietarios o terceros sin autorización o fundamento jurídico suficiente.",
                "Los documentos y datos deberán conservarse con medidas razonables de seguridad y acceso restringido. La terminación del contrato no implica eliminación inmediata de aquello que deba conservarse para cumplimiento legal, contable, probatorio o defensa de derechos, pero sí exige cesar usos incompatibles con esas finalidades."
            )

        elif is_clause and _has(section, "INCUMPLIMIENTO Y SUBSANACIÓN"):
            _paragraphs(
                section,
                "La parte que alegue incumplimiento deberá identificar de manera suficientemente determinada los hechos, la obligación presuntamente infringida, la evidencia disponible y, cuando proceda, la conducta necesaria para subsanar. La comunicación no convierte por sí sola la afirmación de una parte en hecho probado ni modifica las causales imperativas de terminación previstas por la ley.",
                "Cuando la naturaleza del incumplimiento permita corrección y la ley o el contrato no autoricen una actuación inmediata distinta, se concederá un plazo razonable atendiendo gravedad, urgencia, habitabilidad, seguridad y posibilidad material de cumplimiento. La subsanación no impide reclamar perjuicios demostrados que ya se hubieran causado, cuando jurídicamente proceda.",
                "Las medidas de reacción deberán ser proporcionales y no autorizan vías de hecho, corte arbitrario de servicios, ingreso no consentido, retención indebida de bienes, hostigamiento o desalojo sin el procedimiento aplicable."
            )

        elif is_clause and _has(section, "ABANDONO Y BIENES"):
            _paragraphs(
                section,
                "La mera ausencia temporal, falta de respuesta o atraso en pagos no autoriza a presumir abandono, ingresar al inmueble ni disponer de bienes. Antes de adoptar cualquier medida deberán verificarse hechos objetivos y el procedimiento jurídicamente aplicable, teniendo en cuenta privacidad, inviolabilidad del domicilio y derechos sobre los bienes encontrados.",
                "Si al recibir válidamente el inmueble quedan bienes cuya titularidad corresponda a LA PARTE ARRENDATARIA u ocupantes, se procurará inventariarlos y conservar evidencia razonable de su estado. La custodia, requerimiento de retiro, entrega, gastos y eventual disposición se manejarán conforme a la ley y a las circunstancias acreditadas, sin apropiación automática ni destrucción arbitraria.",
                "Las actuaciones realizadas por razones de emergencia deberán limitarse a lo necesario para contener el riesgo y documentarse tan pronto como sea razonablemente posible."
            )

        elif is_clause and _has(section, "SOLUCIÓN DE CONTROVERSIAS"):
            _paragraphs(
                section,
                "Las partes procurarán resolver de buena fe las diferencias mediante comunicación documentada que permita identificar hechos, pretensión y soportes. Cuando resulte útil y jurídicamente procedente, podrán acudir a conciliación ante un centro o conciliador competente.",
                "La negociación o conciliación no será requisito para adoptar medidas urgentes de protección, preservar evidencia, atender riesgos de habitabilidad o seguridad, impedir una afectación grave de servicios ni ejercer oportunamente derechos sometidos a término. Tampoco sustituye procedimientos especiales de restitución, cobro o actuación administrativa cuando correspondan.",
                "Si no existe acuerdo, cada parte podrá acudir a la autoridad o jurisdicción competente conforme a las reglas legales aplicables. El contrato no presume competencia territorial distinta de la que válidamente resulte de la ley y de los hechos del caso."
            )

        elif is_clause and _has(section, "LEY APLICABLE"):
            _paragraphs(
                section,
                "El contrato se interpreta principalmente conforme a la Ley 820 de 2003 por tratarse de arrendamiento de vivienda urbana. En lo compatible y no regulado de manera especial se aplicarán las disposiciones pertinentes del Código Civil y las demás normas colombianas que correspondan a servicios públicos, propiedad horizontal, protección de datos, mensajes de datos, garantías y materias relacionadas.",
                "Las normas imperativas prevalecen sobre estipulaciones incompatibles. La invalidez, ineficacia o inaplicabilidad de una disposición no afectará las restantes cuando puedan conservar sentido autónomo y lícito, y ninguna cláusula se interpretará como renuncia anticipada a derechos legalmente indisponibles."
            )

        final.append(section)

    composition["sections"] = final
    composition.setdefault("maturity_answers", {})["lease_instrument_finalized"] = True
    return composition


__all__ = ["compose_lease_m33_instrument"]
