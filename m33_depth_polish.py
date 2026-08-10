from __future__ import annotations

"""Profundización jurídica final de piezas procedimentales críticas M33.0.

Esta capa es exclusivamente compositiva. No modifica diagnósticos, cálculos,
selección de mecanismos, niveles de riesgo, condiciones de radicabilidad ni
aprobaciones. Añade desarrollo jurídico, probatorio y de ejecución a tres piezas
que, aun siendo correctas, resultaban demasiado compactas frente al estándar
editorial y jurídico aprobado para LegalAIZ.it.
"""

from copy import deepcopy
from typing import Any


TARGET_CODES = {"CO-CD-003", "CO-SA-001", "CO-TR-002"}


def _heading_exists(sections: list[dict], heading: str) -> bool:
    return any(
        isinstance(item, dict)
        and str(item.get("heading") or "").strip() == heading
        for item in sections
    )


def _insert_before_signature(sections: list[dict], additions: list[dict]) -> list[dict]:
    pending = [item for item in additions if not _heading_exists(sections, str(item.get("heading") or ""))]
    if not pending:
        return sections
    for index, item in enumerate(sections):
        if not isinstance(item, dict):
            continue
        if str(item.get("_type") or item.get("type") or "").casefold() == "signature":
            return sections[:index] + pending + sections[index:]
    return sections + pending


def _consumer_warranty_additions() -> list[dict]:
    return [
        {
            "heading": "VIII. MARCO JURÍDICO ESPECÍFICO Y CARGA DE ACREDITACIÓN",
            "paragraphs": [
                "La garantía legal es una obligación temporal y solidaria a cargo de productor y proveedor respecto de la calidad, idoneidad, seguridad y buen estado o funcionamiento del bien, en los términos de los artículos 7 y siguientes de la Ley 1480 de 2011 y su reglamentación. La reclamación debe analizarse con base en la condición real del producto, la fecha de entrega, el término de garantía, las intervenciones anteriores y la solución efectivamente solicitada por la persona consumidora.",
                "La sola afirmación de uso indebido, fuerza mayor, hecho de un tercero o incumplimiento de instrucciones no basta para negar la garantía. Cuando se invoque una causal de exoneración, la decisión debe individualizar el hecho, explicar su relación causal con el defecto y apoyarse en evidencia técnica susceptible de contradicción. Del mismo modo, una reparación previa no puede tratarse como un antecedente irrelevante cuando la controversia consiste precisamente en la repetición de la falla.",
                "La reclamación directa y la respuesta deben conservarse de forma íntegra. La Ley 1480 exige una respuesta dentro del término legal y que esta contenga las pruebas en que se funda; por ello, un cierre interno, una orden de servicio sin explicación o una comunicación genérica no sustituyen una decisión de fondo sobre la pretensión planteada.",
            ],
        },
        {
            "heading": "IX. TRAZABILIDAD TÉCNICA, PRUEBA Y CONTRADICCIÓN",
            "numbered": [
                "Individualizar cada ingreso del bien a diagnóstico o reparación mediante fecha, orden de servicio, síntomas reportados, pruebas realizadas, piezas intervenidas y resultado de salida.",
                "Conservar fotografías, videos, registros de error, diagnósticos, comunicaciones y archivos originales cuando estos permitan establecer la existencia, repetición o causa de la falla.",
                "Si se atribuye el defecto a un comportamiento de la persona consumidora, identificar la instrucción concreta presuntamente incumplida, la forma en que fue informada y la prueba técnica que conecta ese hecho con el daño.",
                "Si existe falla repetida, dejar constancia escrita de la alternativa elegida por la persona consumidora cuando el régimen permita elección, sin reemplazarla por una opción unilateral del proveedor.",
                "Documentar la entrega, transporte, custodia y devolución del bien, especialmente cuando contenga datos personales o cuando su estado físico sea relevante para determinar responsabilidad.",
            ],
        },
        {
            "heading": "X. CUMPLIMIENTO MATERIAL, CIERRE Y RESERVA DE DERECHOS",
            "paragraphs": [
                "Una respuesta favorable no cierra por sí sola la actuación. El expediente debe permanecer abierto hasta que exista evidencia de la reparación, reposición, devolución de dinero u otra solución legalmente procedente y de la recepción efectiva por la persona consumidora. Si la solución ofrecida no se ejecuta, se ejecuta de manera incompleta o reaparece la falla, el nuevo hecho debe registrarse como evento separado y conservar su propia trazabilidad.",
                "La recepción del bien para diagnóstico, la aceptación de una reparación o la firma de una constancia logística no deben redactarse como renuncia general a derechos. Tampoco debe entenderse que la reclamación reconoce diagnósticos, exclusiones o causas que continúan controvertidas. Si persiste el desacuerdo, deberán valorarse los mecanismos administrativos o jurisdiccionales procedentes conforme a la pretensión, la evidencia y el régimen especial que eventualmente resulte aplicable.",
            ],
        },
    ]


def _health_petition_additions() -> list[dict]:
    return [
        {
            "heading": "VII. DEBER DE COORDINACIÓN Y EJECUCIÓN MATERIAL",
            "paragraphs": [
                "La gestión del caso debe orientarse a materializar la prestación requerida y no únicamente a producir una respuesta formal. Los principios de continuidad, oportunidad e integralidad de la Ley Estatutaria 1751 de 2015 impiden que la fragmentación contractual, administrativa o logística entre EPS, IPS, gestor farmacéutico, proveedor u otros actores traslade al paciente una carga de coordinación que termine interrumpiendo o demorando injustificadamente la atención.",
                "Cuando una entidad receptora no sea quien ejecuta materialmente la prestación, deberá identificar el actor competente, realizar la gestión que le corresponda dentro de la red y conservar evidencia de la remisión, coordinación y seguimiento. Una autorización sin agenda, una fórmula sin dispensación o una respuesta que remita al usuario de un actor a otro no equivalen por sí solas a la satisfacción del derecho reclamado.",
            ],
        },
        {
            "heading": "VIII. PRIORIDAD, URGENCIA Y ESCALAMIENTO",
            "numbered": [
                "Mantener la clasificación de riesgo actualizada durante todo el trámite; el deterioro clínico puede exigir una respuesta distinta de la prevista al momento de la radicación inicial.",
                "Si existe peligro inminente para la vida o integridad, la ruta documental no debe convertirse en una espera: deben adoptarse o buscarse inmediatamente las medidas asistenciales de urgencia que correspondan.",
                "Controlar el término sectorial aplicable al tipo de reclamo y registrar fecha y hora de recepción, respuesta y ejecución material.",
                "Si la barrera persiste, valorar el escalamiento ante la Superintendencia Nacional de Salud y, cuando exista amenaza o vulneración actual de derechos fundamentales, la procedencia de mecanismos constitucionales con revisión profesional.",
                "Si ya existe tutela, incidente de desacato, medida provisional, orden judicial o actuación administrativa sobre los mismos hechos, evitar documentos paralelos que contradigan la estrategia o desconozcan una orden vigente.",
            ],
        },
        {
            "heading": "IX. TRAZABILIDAD CLÍNICO-ADMINISTRATIVA Y CIERRE",
            "numbered": [
                "Conservar la orden o fórmula vigente, únicamente con la información clínica necesaria para acreditar la prestación requerida.",
                "Registrar cada autorización, negación, falta de disponibilidad, asignación, cambio de proveedor, cita, dispensación y entrega como evento separado con fecha y soporte.",
                "No sobrescribir una respuesta anterior cuando cambie el estado del caso; la nueva actuación debe quedar asociada a una revisión posterior del expediente.",
                "Cerrar únicamente cuando exista evidencia de la entrega, cita, procedimiento, continuidad o solución material compatible con la orden clínica y no queden actuaciones pendientes derivadas del mismo reclamo.",
            ],
        },
    ]


def _traffic_notification_additions() -> list[dict]:
    return [
        {
            "heading": "V. MARCO JURÍDICO DE NOTIFICACIÓN Y DEBIDO PROCESO",
            "paragraphs": [
                "La reclamación debe analizarse bajo el artículo 29 de la Constitución, el procedimiento especial de la Ley 1843 de 2017 para detecciones mediante sistemas automáticos o semiautomáticos y las reglas vigentes del Código Nacional de Tránsito. El comparendo constituye una orden de comparecencia y un acto de vinculación al trámite; no equivale por sí mismo a una sanción ejecutoriada.",
                "La Ley 1843 diferencia la validación de la detección, el envío del comparendo y sus soportes, la entrega o devolución y la notificación subsidiaria cuando resulte procedente. Por ello, una guía generada, un intento de envío o el conocimiento posterior obtenido al consultar una base de datos no deben tratarse automáticamente como prueba de que la persona tuvo una oportunidad real y oportuna de ejercer defensa.",
                "El parágrafo incorporado al artículo 136 del Código Nacional de Tránsito prevé efectos específicos cuando se demuestra que un comparendo detectado por medios tecnológicos no fue notificado o fue indebidamente notificado. Ese efecto no autoriza a declarar de manera automática la inexistencia de toda actuación posterior: debe reconstruirse el procedimiento y determinarse qué oportunidad de defensa resultó materialmente afectada.",
            ],
        },
        {
            "heading": "VI. PRUEBA MÍNIMA PARA RESOLVER LA CONTROVERSIA",
            "numbered": [
                "Certificación o evidencia histórica del dato de contacto consultado por la autoridad en la fecha relevante, evitando comparar únicamente el RUNT actual con una actuación pasada.",
                "Registro de la consulta, fuente de datos, fecha de validación y copia íntegra del comparendo y de los soportes enviados.",
                "Guía postal, trazabilidad del operador, intentos de entrega, causal de devolución y constancias de cualquier actuación subsidiaria o electrónica invocada por la autoridad.",
                "Actas, grabaciones o registros de comparecencia, audiencia y pruebas, si el procedimiento avanzó pese a la controversia de notificación.",
                "Resolución sancionatoria, constancia de su notificación, recursos y ejecutoria, cuando exista un acto sancionatorio posterior.",
                "Mandamiento de pago, notificación, excepciones y medidas cautelares cuando el asunto ya haya pasado a cobro coactivo.",
            ],
        },
        {
            "heading": "VII. RESPONSABILIDAD, EFECTOS Y RESERVAS",
            "paragraphs": [
                "La autoridad debe separar la vinculación al procedimiento de la atribución de responsabilidad. La Sentencia C-038 de 2020 excluyó una responsabilidad sancionatoria automática del propietario por el solo hecho de ser titular del vehículo; la decisión administrativa debe explicar la conducta, la calidad en que se imputa, la prueba y el juicio de responsabilidad aplicable al caso concreto.",
                "La radicación de esta reclamación no suspende por sí sola términos judiciales, ejecutoria, cobro coactivo ni medidas cautelares. Si existe resolución, mandamiento de pago, embargo, pago previo o una actuación próxima a vencer, el expediente exige revisión profesional inmediata para determinar la vía idónea y evitar que una petición administrativa sea utilizada como sustituto de un recurso o medio de control con término propio.",
                "Si se acredita una irregularidad de notificación, la respuesta debe indicar con precisión qué actuación se repetirá o corregirá, desde qué momento se reconocen términos, qué oportunidades de defensa se restablecen y cómo se sincronizarán los registros administrativos. Si se niega la reclamación, la motivación deberá identificar los soportes que acreditan la notificación y explicar por qué la defensa material no resultó afectada.",
            ],
        },
    ]


def finalize_depth_polish(
    code: str,
    specs: list[dict],
    answers: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> list[dict]:
    """Añade profundidad sin alterar selección, riesgo, firma ni estado de gobierno."""
    if code not in TARGET_CODES:
        return specs

    polished = deepcopy(specs)
    for spec in polished:
        kind = str(spec.get("kind") or "")
        sections = list(spec.get("sections") or [])

        if code == "CO-CD-003" and kind == "warranty_claim":
            spec["sections"] = _insert_before_signature(sections, _consumer_warranty_additions())
        elif code == "CO-SA-001" and kind in {"health_petition", "health_priority_claim"}:
            spec["sections"] = _insert_before_signature(sections, _health_petition_additions())
        elif code == "CO-TR-002" and kind == "traffic_notification_claim":
            spec["sections"] = _insert_before_signature(sections, _traffic_notification_additions())

    return polished
