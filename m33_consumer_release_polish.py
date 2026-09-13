from __future__ import annotations

"""Pulido editorial final de las piezas externas CO-CD-003.

No cambia la selección de mecanismo, reglas, cálculos ni compuertas. Sustituye
lenguaje técnico evitable y añade cierres sustantivos a piezas que, al renderizar,
quedaban con páginas finales excesivamente vacías.
"""

from copy import deepcopy
from typing import Any


_TEXT_REPLACEMENTS = (
    ("Fecha modelada", "Fecha preliminar"),
    ("fecha modelada", "fecha preliminar"),
    ("Último día modelado", "Último día preliminar"),
    ("último día modelado", "último día preliminar"),
    ("Fecha supletiva modelada", "Fecha supletiva preliminar"),
    ("fecha supletiva modelada", "fecha supletiva preliminar"),
    ("cuando el motor dispone de fechas suficientes", "cuando existen fechas suficientes"),
    ("los días hábiles automáticos", "los días hábiles calculados"),
    ("el motor no descuenta festivos", "el cómputo preliminar no descuenta festivos"),
    ("el calendario del motor excluye fines de semana pero no descuenta festivos", "el cómputo automático excluye fines de semana pero no descuenta festivos"),
    ("La fecha del motor es solo control operativo preliminar.", "La fecha indicada es preliminar; debe verificarse la recepción y los participantes intervinientes."),
    ("La fecha automática asociada al control de cinco días es auxiliar", "La fecha indicada para el control de cinco días es preliminar"),
    ("la fecha automática asociada al control de cinco días es auxiliar", "la fecha indicada para el control de cinco días es preliminar"),
    ("la fecha modelada no equivale a decisión final", "la fecha preliminar no equivale a decisión final"),
    (
        "Cuando el emisor del instrumento de pago sea diferente de la entidad receptora de la revocación, debe comunicársele la instrucción de cese dentro de cinco (5) días. Ese término no debe presentarse como cinco días hábiles cuando la norma no lo califica de esa manera.",
        "Cuando el emisor del instrumento de pago sea diferente de la entidad receptora de la revocación, debe comunicársele la instrucción de cese dentro de cinco (5) días y conservarse constancia verificable de su envío y recepción.",
    ),
    (
        "Cuando corresponda, comunicar la instrucción de cese al emisor dentro de 5 días; la norma no debe reescribirse como 5 días hábiles.",
        "Cuando corresponda, comunicar la instrucción de cese al emisor dentro de 5 días y conservar prueba de la comunicación.",
    ),
    ("token de cobro", "mecanismo de débito autorizado"),
)


def _polish_text(value: str) -> str:
    result = value
    for old, new in _TEXT_REPLACEMENTS:
        result = result.replace(old, new)
    return result


def _walk(value: Any) -> Any:
    if isinstance(value, str):
        return _polish_text(value)
    if isinstance(value, list):
        return [_walk(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_walk(item) for item in value)
    if isinstance(value, dict):
        return {key: _walk(item) for key, item in value.items()}
    return value


def _insert_before_signature(sections: list[dict], section: dict) -> list[dict]:
    if any(str(item.get("heading") or "") == str(section.get("heading") or "") for item in sections if isinstance(item, dict)):
        return sections
    for index, item in enumerate(sections):
        if isinstance(item, dict) and item.get("_type") == "signature":
            return sections[:index] + [section] + sections[index:]
    return sections + [section]


def _append_unique(sections: list[dict], section: dict) -> list[dict]:
    if any(str(item.get("heading") or "") == str(section.get("heading") or "") for item in sections if isinstance(item, dict)):
        return sections
    return sections + [section]


def _diagnosis_closure() -> dict:
    return {
        "heading": "VII. RESULTADO Y PRÓXIMAS ACTUACIONES",
        "numbered": [
            "Completar los soportes faltantes y confirmar las fechas que activan términos antes de utilizar la pieza sustantiva seleccionada.",
            "Radicar únicamente el mecanismo compatible con los hechos actuales y obtener constancia verificable de recepción, contenido y anexos.",
            "Controlar la respuesta y la ejecución material de la solución; una respuesta favorable sin reparación, reembolso, reversión o cese efectivo no cierra por sí sola el expediente.",
            "Si la respuesta es negativa, incompleta o incumplida, valorar el mecanismo administrativo o jurisdiccional procedente según la pretensión, cuantía, sector y evidencia disponible.",
        ],
    }


def _calendar_update_section() -> dict:
    return {
        "heading": "III. REGISTRO DE ACTUALIZACIONES",
        "table": [
            ["Evento", "Fecha efectiva", "Soporte de verificación"],
            ["Radicación o ejercicio del mecanismo", "Por registrar", "Acuse, radicado o mensaje de datos"],
            ["Respuesta del proveedor o emisor", "Por registrar", "Respuesta íntegra y anexos"],
            ["Ejecución material de la solución", "Por registrar", "Orden, guía, abono, reversión o constancia de cese"],
            ["Cierre o escalamiento", "Por registrar", "Constancia de cumplimiento o nuevo radicado"],
        ],
        "paragraphs": [
            "Cada actualización debe conservar la fecha efectiva y el soporte que la acredita. Si cambia un hito que sirve de base para un término, el calendario debe recalcularse sin borrar la versión anterior."
        ],
    }


def _evidence_custody_section() -> dict:
    return {
        "heading": "IV. CUSTODIA, PRIVACIDAD Y AUTENTICIDAD",
        "numbered": [
            "Conservar los originales en su formato nativo cuando sea posible y trabajar sobre copias identificadas para anotaciones o preparación de anexos.",
            "Minimizar números de tarjeta, cuentas, direcciones, credenciales y demás datos que no sean necesarios para acreditar la operación o la causal.",
            "Cuando un archivo sea determinante, registrar su origen, fecha de obtención y una huella o mecanismo equivalente de integridad si el expediente dispone de esa capacidad.",
            "No atribuir autenticidad, autoría o recepción a una captura aislada cuando el contexto, encabezados, metadatos o acuse puedan y deban verificarse por otro medio.",
        ],
    }


def _reversal_closure() -> dict:
    return {
        "heading": "VIII. ANEXOS Y CIERRE DE LA ACTUACIÓN",
        "numbered": [
            "Anexar la prueba de la operación y del pago, la queja presentada al proveedor, la notificación al emisor y el soporte específico de la causal invocada.",
            "Registrar por separado cualquier devolución, abono o movimiento provisional para evitar una recuperación económica duplicada.",
            "El expediente solo debe cerrarse cuando exista evidencia del resultado del procedimiento y, si hubo movimiento contable, de su ejecución efectiva.",
            "Una controversia posterior sobre la procedencia de la reversión debe conservarse como actuación diferenciada, con sus propios soportes y estado.",
        ],
    }


def _periodic_closure() -> dict:
    return {
        "heading": "VII. CONSTANCIAS Y CIERRE",
        "numbered": [
            "Anexar la autorización original de débito, la comunicación de revocación y la prueba de recepción por los participantes a quienes corresponda.",
            "Verificar en el siguiente período de facturación que no se presenten nuevos cargos bajo el mandato revocado y conservar el extracto o comprobante pertinente.",
            "Si aparece un cargo posterior, registrar por separado su fecha, la fecha de conocimiento y la solicitud de reversión correspondiente.",
            "Cerrar la actuación únicamente cuando exista constancia del cese del mandato y se hayan conciliado los cargos anteriores, posteriores y cualquier devolución efectuada.",
        ],
    }


def _non_delivery_closure() -> dict:
    return {
        "heading": "VIII. ANEXOS Y CIERRE",
        "numbered": [
            "Anexar la orden o confirmación de compra, el plazo de entrega ofrecido, la trazabilidad logística disponible y la comunicación de terminación o resolución.",
            "Conservar el comprobante del pago y, cuando exista, la evidencia de indisponibilidad o del incumplimiento del plazo pactado o supletivo.",
            "El cierre requiere acreditar la cancelación del pedido y la devolución total de las sumas pagadas en el medio jurídicamente procedente.",
            "Si el proveedor realiza un despacho después de la terminación sin nueva aceptación, registrar el hecho y evitar que la recepción material sea tratada automáticamente como renuncia a la reclamación.",
        ],
    }


def finalize_consumer_release_polish(specs: list[dict]) -> list[dict]:
    """Limpia la copia cliente y fortalece las páginas finales sin alterar el fondo."""
    finalized: list[dict] = []
    for original in specs:
        spec = deepcopy(original)
        if not spec.get("internal_controls_externalized"):
            finalized.append(spec)
            continue

        spec = _walk(spec)
        kind = spec.get("kind")
        sections = list(spec.get("sections") or [])
        if kind == "consumer_mechanism_diagnosis":
            sections = _append_unique(sections, _diagnosis_closure())
        elif kind == "consumer_deadline_calendar":
            sections = _append_unique(sections, _calendar_update_section())
        elif kind == "consumer_evidence_matrix":
            sections = _append_unique(sections, _evidence_custody_section())
        elif kind == "payment_reversal_request":
            sections = _insert_before_signature(sections, _reversal_closure())
        elif kind == "recurring_debit_revocation":
            sections = _insert_before_signature(sections, _periodic_closure())
        elif kind == "ecommerce_non_delivery_termination":
            sections = _insert_before_signature(sections, _non_delivery_closure())
        spec["sections"] = sections
        finalized.append(spec)
    return finalized
