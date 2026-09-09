from __future__ import annotations

"""Pulido final de presentación para CO-CD-004.

Opera después de la finalización jurídica. No modifica selección por etapa,
cálculos, flags de gobierno ni términos económicos. Corrige la representación
visible de ajustes negativos y fortalece cierres documentales que, en el render,
quedaban aislados en páginas con escaso contenido.
"""

from copy import deepcopy
from typing import Any

from premium_document_engine import format_cop


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _adjustment_label(value: Any) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        return "Valor por verificar"
    if amount < 0:
        return f"{format_cop(abs(amount), include_words=False)} · disminución del saldo"
    if amount > 0:
        return f"{format_cop(amount, include_words=False)} · incremento sujeto a soporte"
    return f"{format_cop(0, include_words=False)} · sin ajuste neto"


def _replace_economic_adjustment(spec: dict, result: dict) -> None:
    c = _calc(result)
    adjustment = c.get("other_charges")
    label = _adjustment_label(adjustment)
    for section in spec.get("sections") or []:
        table = section.get("table") if isinstance(section, dict) else None
        if not isinstance(table, list):
            continue
        for row in table:
            if not isinstance(row, list) or not row:
                continue
            heading = str(row[0] or "").casefold()
            if "ajustes netos" in heading and len(row) >= 2:
                row[1] = label

    # La ecuación del estado de cuenta se expresa con el signo semántico correcto.
    if spec.get("kind") == "account_statement":
        try:
            amount = float(adjustment or 0)
        except Exception:
            return
        for section in spec.get("sections") or []:
            if not isinstance(section, dict) or section.get("heading") != "III. ECUACIÓN DE CONTROL":
                continue
            paragraphs = list(section.get("paragraphs") or [])
            if not paragraphs:
                continue
            principal = format_cop(float(c.get("principal") or 0), include_words=False)
            payments = format_cop(float(c.get("partial_payments_total") or 0), include_words=False)
            explained = format_cop(float(c.get("explained_balance") or 0), include_words=False)
            reported = format_cop(float(c.get("reported_balance") or 0), include_words=False)
            if amount < 0:
                movement = f"menos un ajuste neto de {format_cop(abs(amount), include_words=False)} que disminuye el saldo"
            elif amount > 0:
                movement = f"más un ajuste neto de {format_cop(amount, include_words=False)} cuya procedencia debe estar soportada"
            else:
                movement = "sin ajustes netos adicionales"
            paragraphs[0] = (
                f"Capital original {principal} menos pagos o créditos {payments}, {movement}, produce un saldo explicado de {explained}. "
                f"El saldo informado es {reported}."
            )
            section["paragraphs"] = paragraphs


def _insert_before_signature(spec: dict, additions: list[dict]) -> None:
    sections = list(spec.get("sections") or [])
    index = next((i for i, section in enumerate(sections) if isinstance(section, dict) and section.get("_type") == "signature"), len(sections))
    spec["sections"] = sections[:index] + deepcopy(additions) + sections[index:]


def _account_closure(spec: dict, result: dict) -> None:
    c = _calc(result)
    spec["sections"].extend([
        {
            "heading": "VII. CONTROL PREVIO A FORMALIZACIÓN",
            "table": [
                ["Verificación", "Resultado de esta revisión"],
                ["Diferencia de conciliación", format_cop(float(c.get("balance_difference") or 0), include_words=False)],
                ["Saldo reconciliado", "Sí, de manera preliminar" if c.get("balance_reconciled") else "No; formalización bloqueada"],
                ["Documento causal", "Identificado en el expediente; contrastar con el original"],
                ["Pagos y créditos", "Conciliar con comprobantes y notas crédito"],
                ["Intereses", "Revalidar pacto, modalidad, vigencia y límite antes de liquidarlos"],
                ["Representación y titularidad", "Verificar facultades, cesión o cadena de transferencia cuando aplique"],
                ["Pagaré o garantía", "Solo si corresponde a la etapa y reúne requisitos propios"],
            ],
        },
        {
            "heading": "VIII. RESULTADO Y ACTUALIZACIÓN DEL ESTADO",
            "paragraphs": [
                "Este estado de cuenta puede utilizarse como base de contraste únicamente mientras coincida con los soportes que lo originan. Un pago, nota crédito, compensación, corrección o cambio de tasa posterior obliga a emitir una nueva revisión y conservar la anterior para trazabilidad.",
                "La formalización de un reconocimiento, acuerdo o título debe tomar el saldo vigente de la revisión aprobada; no debe copiarse una cifra histórica si ya existen movimientos posteriores.",
            ],
        },
    ])


def _collection_closure(spec: dict) -> None:
    _insert_before_signature(spec, [
        {
            "heading": "VII. CONSTANCIA DE RADICACIÓN Y ANEXOS",
            "table": [
                ["Control", "Registro requerido"],
                ["Canal de envío", "Registrar el canal efectivamente utilizado"],
                ["Fecha y hora", "Registrar la fecha real de remisión"],
                ["Destinatario", "Verificar que corresponda a la parte obligada o a su canal válido"],
                ["Radicado o acuse", "Conservar la constancia emitida por el receptor o el sistema"],
                ["Anexos", "Identificar exactamente los documentos que acompañaron esta comunicación"],
            ],
        },
        {
            "heading": "VIII. EFECTO Y SEGUIMIENTO",
            "paragraphs": [
                "La radicación inicia una gestión prejurídica y un espacio de verificación; no convierte unilateralmente el saldo en una obligación aceptada ni elimina las defensas que legalmente procedan. Cualquier respuesta de la contraparte deberá incorporarse al expediente antes de formalizar un arreglo.",
                "Si se alcanza un acuerdo, la nueva pieza deberá identificar el saldo conciliado, las concesiones, el cronograma y, cuando existan, las garantías o títulos complementarios. Si no existe acuerdo, la decisión sobre una eventual actuación judicial requiere revisar el título, la exigibilidad, la legitimación, los términos y la evidencia disponibles.",
            ],
        },
    ])


def _agreement_closure(spec: dict) -> None:
    # Inserta cláusulas antes del anexo económico, que tiene salto de página deliberado.
    sections = list(spec.get("sections") or [])
    index = next((i for i, section in enumerate(sections) if isinstance(section, dict) and str(section.get("heading") or "").startswith("ANEXO ECONÓMICO")), len(sections))
    additions = [
        {
            "heading": "DÉCIMA NOVENA: GASTOS, COSTOS Y HONORARIOS",
            "_type": "clause",
            "paragraphs": [
                "Los costos internos de administración o cobranza no se trasladan automáticamente a la PARTE DEUDORA. Solo podrán incorporarse valores adicionales cuando exista fundamento contractual o legal suficiente, hayan sido efectivamente causados y puedan ser discriminados y soportados. Esta cláusula no autoriza porcentajes automáticos de honorarios ni sanciones no pactadas.",
            ],
        },
        {
            "heading": "VIGÉSIMA: DOCUMENTOS INTEGRANTES Y CONCORDANCIA ECONÓMICA",
            "_type": "clause",
            "paragraphs": [
                "Forman parte de la trazabilidad del acuerdo el estado de cuenta conciliado y el cronograma aceptado. El pagaré y la carta de instrucciones, cuando existan, son instrumentos complementarios y deberán reflejar la misma realidad económica. Ninguna discrepancia entre documentos autoriza doble cobro; deberá corregirse mediante una nueva revisión firmada o por el mecanismo jurídico que corresponda.",
            ],
        },
        {
            "heading": "VIGÉSIMA PRIMERA: FIRMA, EJEMPLARES Y CONSERVACIÓN",
            "_type": "clause",
            "paragraphs": [
                "El acuerdo podrá suscribirse en uno o varios ejemplares o mediante un método de firma legalmente válido que permita atribuir la manifestación a cada parte y conservar la integridad del contenido. Cada parte conservará una copia completa junto con sus anexos y comprobantes. La fecha de suscripción deberá corresponder a la actuación real y no alterará retroactivamente la causación de obligaciones anteriores.",
            ],
        },
    ]
    spec["sections"] = sections[:index] + additions + sections[index:]


def _note_closure(spec: dict) -> None:
    _insert_before_signature(spec, [
        {
            "heading": "OCTAVA: CUSTODIA, DILIGENCIAMIENTO Y TRAZABILIDAD",
            "_type": "clause",
            "paragraphs": [
                "El original o soporte íntegro del título deberá permanecer bajo custodia controlada. Si se diligencia posteriormente un espacio autorizado, deberá conservarse la liquidación utilizada, la fecha real de la actuación y la carta de instrucciones aplicable. Todo pago posterior deberá reflejarse en el saldo exigible para impedir que el título represente una suma superior a la obligación vigente.",
            ],
        },
    ])


def _receipt_closure(spec: dict) -> None:
    _insert_before_signature(spec, [
        {
            "heading": "IV. CONSTANCIAS DEL RECEPTOR",
            "numbered": [
                "Verificar que el valor y la fecha correspondan al comprobante de pago efectivamente recibido.",
                "Registrar la referencia, cuota o concepto de imputación cuando esté determinado.",
                "Actualizar el saldo sin desconocer pagos, notas crédito o ajustes anteriores.",
                "Si existe pagaré, acuerdo o cronograma, reflejar el movimiento en esos instrumentos o en su registro de control.",
                "No utilizar este recibo parcial como paz y salvo mientras subsista saldo pendiente.",
            ],
        },
        {
            "heading": "V. ARCHIVO Y TRAZABILIDAD",
            "paragraphs": [
                "El comprobante financiero y este recibo deben conservarse vinculados a la misma obligación y revisión. Si posteriormente se corrige la imputación, deberá emitirse un registro nuevo que explique el cambio y preserve el recibo anterior como antecedente, evitando modificaciones silenciosas del historial económico.",
            ],
        },
    ])


def _settlement_closure(spec: dict) -> None:
    _insert_before_signature(spec, [
        {
            "heading": "IV. VERIFICACIONES DE CIERRE",
            "table": [
                ["Control", "Constancia requerida"],
                ["Saldo", "Estado de cuenta final en cero"],
                ["Pagos", "Comprobantes reconciliados con todos los movimientos"],
                ["Pagaré", "Cancelación, devolución o inutilización acreditada cuando exista"],
                ["Garantías", "Liberación o actuación de cierre que jurídicamente corresponda"],
                ["Cobranza", "Cese de nuevas gestiones sobre la obligación extinguida"],
                ["Reporte crediticio", "Actualización separada bajo el régimen aplicable, si existe"],
            ],
        },
        {
            "heading": "V. CONSTANCIA DOCUMENTAL",
            "paragraphs": [
                "La parte acreedora deberá conservar evidencia suficiente para demostrar qué obligación fue extinguida, qué pagos produjeron el saldo cero y qué actuaciones de cancelación se realizaron sobre títulos o garantías. La constancia no debe ampliarse a negocios que no hayan sido individualizados.",
                "Si después de expedido el cierre aparece un error material en la conciliación, la corrección deberá documentarse con trazabilidad y revisión profesional; no procede reactivar silenciosamente la cobranza sobre un saldo declarado extinguido.",
            ],
        },
    ])


def finalize_debt_release_polish(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    if (result or {}).get("risk") == "red":
        return specs

    polished = deepcopy(specs)
    for spec in polished:
        if not spec.get("internal_controls_externalized"):
            continue
        kind = str(spec.get("kind") or "")
        _replace_economic_adjustment(spec, result)
        if kind == "account_statement":
            _account_closure(spec, result)
        elif kind == "collection_letter":
            _collection_closure(spec)
        elif kind == "payment_agreement":
            _agreement_closure(spec)
        elif kind == "promissory_note":
            _note_closure(spec)
        elif kind == "payment_receipt":
            _receipt_closure(spec)
        elif kind == "settlement_certificate":
            _settlement_closure(spec)
    return polished
