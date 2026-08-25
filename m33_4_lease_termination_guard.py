from __future__ import annotations

"""Guardia sustantiva de terminación para CO-AR-001.

Corrige y completa únicamente las rutas imperativas de terminación de vivienda
urbana verificadas contra los artículos 22 a 26 de la Ley 820 de 2003. No cambia
canon, reajuste, depósitos, servicios, reparaciones, garantías ni demás cláusulas.
"""

from copy import deepcopy
from typing import Any


LANDLORD_TERMINATION_TEXT = (
    "La terminación unilateral por LA PARTE ARRENDADORA se regirá por las causales y "
    "procedimientos imperativos de la Ley 820 de 2003. Las causales de incumplimiento "
    "deberán individualizarse y probarse. Durante las prórrogas, la ruta del numeral 7 "
    "del artículo 22 exige aviso escrito por servicio postal autorizado con antelación "
    "no menor de tres (3) meses, indicando la fecha de terminación y que se pagará la "
    "indemnización legal de tres (3) cánones. Conforme al artículo 23, esa indemnización "
    "deberá consignarse a favor de LA PARTE ARRENDATARIA y a órdenes de la autoridad "
    "competente dentro de los tres (3) meses anteriores a la fecha señalada para terminar."
    "\n"
    "A la fecha de vencimiento del término inicial o de sus prórrogas, el numeral 8 del "
    "artículo 22 permite las causales especiales: (a) ocupación por el propietario o "
    "poseedor para su propia habitación por un término no menor de un (1) año; (b) "
    "demolición para efectuar una nueva construcción o desocupación para ejecutar obras "
    "independientes de reparación; (c) entrega en cumplimiento de obligaciones originadas "
    "en un contrato de compraventa; y (d) plena voluntad, únicamente cuando el contrato "
    "haya cumplido como mínimo cuatro (4) años de ejecución. Las causales de los literales "
    "a), b) y c) requieren preaviso escrito no menor de tres (3) meses y que con el aviso "
    "se acompañe constancia de una caución en dinero, bancaria o de compañía de seguros "
    "legalmente reconocida, a favor de LA PARTE ARRENDATARIA, por una cuantía equivalente "
    "a seis (6) cánones de arrendamiento, calculados con el canon vigente, para garantizar "
    "el cumplimiento de la causal dentro de los seis (6) meses "
    "siguientes a la restitución. El literal d) exige indemnización equivalente a uno punto "
    "cinco (1,5) cánones de arrendamiento, calculados con el canon vigente, pagada mediante "
    "el procedimiento del artículo 23."
    "\n"
    "Cuando LA PARTE ARRENDADORA deba indemnizar, el artículo 26 reconoce a LA PARTE "
    "ARRENDATARIA el derecho a no ser privada del inmueble sin haber recibido previamente "
    "la indemnización o sin que su importe haya sido debidamente asegurado. La ausencia "
    "del preaviso escrito exigible produce la renovación automática por un término igual "
    "al inicialmente pactado en los eventos previstos por la ley. Antes de activar una "
    "ruta deberán verificarse causal exacta, fecha, soporte, forma de comunicación, "
    "consignación o caución y demás presupuestos aplicables."
)

TENANT_TERMINATION_TEXT = (
    "LA PARTE ARRENDATARIA podrá terminar unilateralmente por las causales legales "
    "imputables a LA PARTE ARRENDADORA previstas en el artículo 24 de la Ley 820 de 2003, "
    "con la prueba que corresponda. También podrá terminar por su voluntad dentro del "
    "término inicial o durante sus prórrogas conforme al numeral 4: deberá enviar aviso "
    "escrito por servicio postal autorizado con antelación no menor de tres (3) meses, "
    "indicar la fecha de terminación y manifestar que pagará la indemnización legal de "
    "tres (3) cánones. Conforme al artículo 25, la indemnización deberá consignarse a "
    "favor de LA PARTE ARRENDADORA y a órdenes de la autoridad competente dentro de los "
    "tres (3) meses anteriores a la fecha señalada; su valor se determina con la renta "
    "vigente a la fecha del preaviso y el título deberá identificar la causa y los datos "
    "exigidos por la ley."
    "\n"
    "A la fecha de vencimiento del término inicial o de cualquiera de sus prórrogas, "
    "LA PARTE ARRENDATARIA podrá terminar por plena voluntad sin indemnización mediante "
    "preaviso escrito por servicio postal autorizado con antelación no menor de tres (3) "
    "meses. De faltar la constancia escrita del preaviso, opera la renovación automática "
    "por un término igual al inicialmente pactado. Si LA PARTE ARRENDADORA se niega a "
    "recibir el inmueble después de cumplirse los presupuestos de la ruta utilizada, "
    "podrá acudirse al procedimiento legal de entrega provisional ante la autoridad "
    "competente y, cuando exista indemnización consignada bajo el artículo 25, solicitar "
    "su devolución en los términos legales. La restitución nunca se sustituirá por el "
    "abandono informal del inmueble."
)


def _set_paragraphs(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [item for item in text.split("\n") if item.strip()]


def finalize_lease_termination_routes(composition: dict) -> dict[str, Any]:
    result = deepcopy(composition)
    found: set[str] = set()

    for section in result.get("sections") or []:
        if section.get("_type") != "clause":
            continue
        heading = str(section.get("heading") or "").casefold()
        if "terminación por la parte arrendadora" in heading or "terminación por el arrendador" in heading:
            _set_paragraphs(section, LANDLORD_TERMINATION_TEXT)
            found.add("landlord")
        elif "terminación por la parte arrendataria" in heading or "terminación por el arrendatario" in heading:
            _set_paragraphs(section, TENANT_TERMINATION_TEXT)
            found.add("tenant")

    expected = {"landlord", "tenant"}
    if found != expected:
        raise ValueError(
            "CO-AR-001 revisión de terminación: cláusulas esperadas no localizadas: "
            + ", ".join(sorted(expected - found))
        )

    maturity = result.setdefault("maturity_answers", {})
    maturity["lease_termination_substantive_review"] = "2026-08-11"
    maturity["lease_termination_articles_reviewed"] = "22-26"
    maturity["lease_termination_route_guard"] = True
    return result


__all__ = ["finalize_lease_termination_routes"]
