from __future__ import annotations

"""Revisión jurídica de segunda pasada para CO-EM-003 M33.0/M33.4.

La biblioteca contractual histórica permanece inmutable. Esta capa recibe su
composición M33.0 y corrige únicamente decisiones que dependen de hechos actuales
del expediente: naturaleza del contratista, datos, IA, seguros, pago y límites de
responsabilidad. M33.4 añade trazabilidad normativa estructurada sin insertar metadatos
internos en el instrumento que firman las partes.
"""

from copy import deepcopy
from datetime import date
import re
from typing import Any

from legalai_platform.legal_source_registry import (
    build_legal_source_manifest,
    source_control_lines,
)
from m33_legal_composition import compose_services_m33 as compose_services_m33_base


_NATURAL = {"natural_person", "persona natural", "persona_natural", "natural", "individual"}
_LEGAL = {"legal_person", "persona jurídica", "persona juridica", "persona_juridica", "company", "corporation", "sas", "s.a.s."}
_MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _read(data: dict, path: str, default=None):
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return default if current is None else current


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"sí", "si", "true", "1", "yes"}


def _contractor_nature(answers: dict) -> str:
    raw = str(_read(answers, "contractor.identification.type", _read(answers, "contractor.type", "")) or "").strip().casefold()
    if raw in _NATURAL:
        return "natural_person"
    if raw in _LEGAL:
        return "legal_person"
    return "unconfirmed"


def _date_es(match: re.Match[str]) -> str:
    try:
        value = date.fromisoformat(match.group(0))
    except ValueError:
        return match.group(0)
    return f"{value.day} de {_MONTHS[value.month]} de {value.year}"


def _clean_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = re.sub(r"\b202\d-\d{2}-\d{2}\b", _date_es, value)
    text = re.sub(r"\bbajo el esquema\s+fixed\b", "bajo el esquema precio fijo", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmodelo\s+fixed\b", "modelo de precio fijo", text, flags=re.IGNORECASE)
    text = text.replace("servicios consistentes en servicios independientes de ", "actividades de ")
    text = text.replace("para servicios independientes de ", "para ")
    return text


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


def _has(section: dict, phrase: str) -> bool:
    return phrase.casefold() in str(section.get("heading") or "").casefold()


def _paragraph(section: dict, text: str) -> None:
    section.pop("text", None)
    section["paragraphs"] = [text]


def _source_ids(nature: str) -> list[str]:
    values = [
        "CO-CST-ART23-2025",
        "CO-COM-ART871",
        "CO-LEY2024-ART3",
        "CO-D1072-SGRL-SGSST",
        "CO-LEY23-ART183",
        "CO-LEY1955-ART181",
        "CAN-DEC351-DA",
        "CO-LEY1581-2012",
        "CO-D1074-DATOS",
        "CO-LEY527-ARTS6-7-14",
    ]
    if nature == "natural_person":
        values.insert(3, "CO-LEY2277-ART89")
    return values


def _apply_source_control(section: dict, source_ids: list[str]) -> None:
    section["source_ids"] = list(source_ids)
    section["bullets"] = source_control_lines(source_ids)


def _review_principal(sections: list[dict], answers: dict, nature: str) -> list[dict]:
    ai_used = _bool(_read(answers, "ai.used", False))
    insurance_required = _bool(_read(answers, "risk.insurance_required", False))
    liability_cap = _read(answers, "risk.liability_cap", _read(answers, "risk.cap", None))
    source_ids = _source_ids(nature)
    reviewed: list[dict] = []

    for original in sections:
        section = _clean_section(original)
        if _has(section, "USO DE INTELIGENCIA ARTIFICIAL") and not ai_used:
            continue
        if _has(section, "SEGUROS") and not insurance_required:
            continue

        if _has(section, "PREVENCIÓN DEL RIESGO DE LABORALIDAD"):
            _paragraph(section, "Las partes controlarán que la ejecución preserve la autonomía pactada y valorarán de forma conjunta y contextual las señales que puedan revelar subordinación material, como la imposición estable de horario o permanencia, la potestad disciplinaria, órdenes continuas sobre la forma de ejecutar el trabajo o la inserción funcional equivalente a un cargo dependiente. La exclusividad, la dependencia económica, el uso de herramientas del contratante o la asistencia a reuniones no producen por sí solos una relación laboral. Si la práctica contradice el contrato, prevalecerá la realidad conforme al artículo 23 del Código Sustantivo del Trabajo vigente.")

        elif _has(section, "FACTURACIÓN, SOPORTES Y PAGO"):
            _paragraph(section, "Cada cobro se acompañará de la factura o documento procedente, la identificación del hito y los soportes contractualmente exigibles. Las observaciones deberán ser concretas, oportunas y vinculadas al entregable; no podrán retener sumas no controvertidas ni prolongar artificialmente un término legal de pago. Cuando la operación esté sometida a la Ley 2024 de 2020, se aplicarán el plazo imperativo, su forma legal de cómputo y las excepciones vigentes, aunque una estipulación contractual prevea un término distinto. EL CONTRATANTE informará las retenciones practicadas y entregará los certificados correspondientes dentro del término legal.")

        elif _has(section, "SEGURIDAD SOCIAL DEL CONTRATISTA"):
            if nature == "natural_person":
                _paragraph(section, "Cuando EL CONTRATISTA sea persona natural, ejecute personalmente el servicio y se encuentre dentro de los presupuestos del artículo 89 de la Ley 2277 de 2022, realizará sus aportes mes vencido sobre el ingreso base de cotización legalmente aplicable, que para esa hipótesis parte del cuarenta por ciento (40 %) del valor mensualizado del contrato sin incluir IVA cuando haya lugar, respetando mínimos, máximos y reglas vigentes. El cálculo deberá atender los ingresos y condiciones reales del periodo y no una cifra fija predeterminada por la plantilla.")
            elif nature == "legal_person":
                _paragraph(section, "EL CONTRATISTA es una persona jurídica. El valor de este contrato no constituye por sí mismo un ingreso base de cotización personal ni se le aplica automáticamente la regla del cuarenta por ciento (40 %) prevista para determinadas personas naturales independientes. EL CONTRATISTA responderá, según cada relación jurídica real, por la afiliación, cotización, nómina, riesgos laborales y demás obligaciones respecto de sus trabajadores, contratistas y subcontratistas; EL CONTRATANTE conservará los deberes de verificación y coordinación que legalmente le correspondan frente al personal que participe en la ejecución.")
            else:
                _paragraph(section, "Antes de aplicar una regla de ingreso base de cotización deberá confirmarse si EL CONTRATISTA es persona natural, persona jurídica u otra forma de organización y cómo se ejecutará materialmente el servicio. Mientras esa naturaleza no esté acreditada, el contrato no presume una base de cotización derivada de su valor. Cada parte cumplirá las obligaciones de seguridad social correspondientes a sus relaciones jurídicas reales.")

        elif _has(section, "VERIFICACIÓN DE APORTES"):
            if nature == "legal_person":
                _paragraph(section, "Cuando sea jurídicamente procedente, EL CONTRATANTE podrá solicitar soportes razonables y minimizados sobre el cumplimiento laboral, de seguridad social y de riesgos del personal efectivamente destinado a la ejecución, sin asumir dirección del personal ajeno. La revisión se limitará a personas y periodos pertinentes, protegerá los datos personales y no trasladará a EL CONTRATANTE obligaciones propias de EL CONTRATISTA como empleador o contratante.")

        elif _has(section, "RIESGOS LABORALES Y SEGURIDAD Y SALUD EN EL TRABAJO"):
            if nature == "natural_person":
                _paragraph(section, "Cuando la persona natural contratista quede comprendida en el Sistema General de Riesgos Laborales por la naturaleza y duración de su contrato, la afiliación, clasificación, inicio de cobertura y responsable de la cotización se determinarán conforme al Decreto 1072 de 2015 y las normas vigentes. La coordinación del SG-SST y los controles de acceso son medidas preventivas y no autorizan subordinación laboral.")
            else:
                _paragraph(section, "Las partes coordinarán el SG-SST respecto de las actividades, lugares y riesgos que puedan afectar a quienes intervengan en la ejecución. EL CONTRATISTA mantendrá sus propios deberes como empleador o contratante frente a su personal; EL CONTRATANTE informará riesgos de sus instalaciones, controles de acceso y medidas de emergencia y realizará la coordinación empresarial legalmente exigible. Esta coordinación preventiva no implica dirección laboral del personal de EL CONTRATISTA.")

        elif _has(section, "TRATAMIENTO DE DATOS PERSONALES"):
            _paragraph(section, "Cuando la ejecución implique datos personales, cada actividad deberá identificar finalidad, categorías de datos y titulares, calidad de responsable o encargado, instrucciones documentadas, base jurídica, medidas de seguridad, plazo de conservación y destinatarios. Si EL CONTRATISTA actúa como encargado, el anexo de tratamiento regulará además confidencialidad, personal autorizado, subencargados, transmisión o transferencia internacional, atención de derechos, incidentes, auditoría razonable y devolución o eliminación al cierre. La confidencialidad contractual no sustituye las obligaciones de la Ley 1581 de 2012 y su reglamentación.")

        elif _has(section, "USO DE INTELIGENCIA ARTIFICIAL"):
            _paragraph(section, "El uso de inteligencia artificial o servicios en nube solo se autoriza para finalidades documentadas y mediante herramientas aprobadas. Antes de cargar información se verificará proveedor, ubicación y retención de datos, uso para entrenamiento, subprocesadores, transferencias internacionales, controles de acceso y eliminación. No se introducirán secretos, datos personales o información reservada en servicios públicos o no aprobados. Los resultados automatizados deberán tener revisión humana competente antes de incorporarse a entregables o decisiones de impacto jurídico, técnico, financiero o de seguridad.")

        elif _has(section, "RESPONSABILIDAD CONTRACTUAL"):
            if liability_cap not in (None, "", 0, "0"):
                _paragraph(section, f"Cada parte responderá por daños directos, ciertos, demostrables y causalmente atribuibles a su incumplimiento. El límite cuantitativo pactado para los eventos jurídicamente limitables es {liability_cap}; no cubrirá dolo, culpa grave ni responsabilidades que por norma imperativa no puedan limitarse. Datos, confidencialidad, propiedad intelectual, personal, seguridad e indemnidad frente a terceros se regirán además por sus cláusulas específicas.")
            else:
                _paragraph(section, "Cada parte responderá por daños directos, ciertos, demostrables y causalmente atribuibles a su incumplimiento conforme al régimen legal y a las asignaciones específicas del contrato. En esta versión no se pacta un límite cuantitativo general; ninguna referencia a límites contractuales podrá interpretarse como un tope inexistente. No se excluyen dolo, culpa grave ni responsabilidades que por norma imperativa no puedan limitarse.")

        elif _has(section, "INDEMNIDAD"):
            _paragraph(section, "La parte cuyo hecho u omisión origine una reclamación de un tercero asumirá, en la proporción jurídicamente imputable, la defensa y los costos o condenas procedentes. Comprende, cuando corresponda, infracción de propiedad intelectual por materiales aportados sin derecho suficiente, reclamaciones laborales o de seguridad social respecto del personal bajo control de una parte, tratamiento indebido de datos, incidentes de seguridad imputables o incumplimientos regulatorios propios. La parte afectada notificará oportunamente, permitirá participación razonable en la defensa y no celebrará acuerdos que impongan obligaciones a la otra sin su consentimiento, salvo exigencia legal.")

        elif _has(section, "SEGUROS"):
            description = str(_read(answers, "risk.insurance", "las coberturas definidas en la matriz de riesgos"))
            _paragraph(section, f"Por la valoración de riesgo de este servicio se exige mantener {description}. El anexo identificará cobertura, asegurado, vigencia, límites, deducibles y evidencia de mantenimiento. La existencia de seguro no amplía por sí misma la responsabilidad contractual ni sustituye obligaciones de prevención.")

        if section.get("_type") == "control":
            _apply_source_control(section, source_ids)
        reviewed.append(section)
    return reviewed


def _review_scope(sections: list[dict], nature: str) -> list[dict]:
    result: list[dict] = []
    for original in sections:
        section = _clean_section(original)
        if _has(section, "MATRIZ DE EJECUCIÓN Y RIESGOS LABORALES") and nature == "legal_person":
            section["heading"] = "9. MATRIZ DE EJECUCIÓN, PERSONAL Y SG-SST"
            section["table"] = [
                ("Variable", "Definición verificable"),
                ("Tiempo", "Ventanas de coordinación, hitos y duración; no jornada impuesta al personal del contratista"),
                ("Modo", "Métodos autónomos del contratista, estándares de resultado y controles de seguridad"),
                ("Lugar", "Sitios autorizados, riesgos informados y condiciones de acceso"),
                ("Personal", "Afiliación, dirección y obligaciones a cargo de quien corresponda según cada vínculo real"),
                ("SG-SST", "Coordinación entre organizaciones, inducción, reporte de incidentes y controles del lugar de ejecución"),
            ]
        elif _has(section, "SEGURIDAD SOCIAL Y SOPORTES"):
            if nature == "legal_person":
                section["heading"] = "10. CUMPLIMIENTO DEL PERSONAL Y SOPORTES"
                section["table"] = [
                    ("Control", "Dato / responsable / periodicidad"),
                    ("Persona jurídica contratista", "No se calcula IBC personal como porcentaje del valor de este contrato"),
                    ("Personal dependiente", "Afiliación, nómina y aportes a cargo del empleador correspondiente"),
                    ("Otros contratistas", "Obligaciones determinadas por su vínculo y forma real de ejecución"),
                    ("Verificación", "Soporte pertinente, minimizado y limitado a personal y periodos relacionados con la ejecución"),
                ]
            elif nature == "natural_person":
                section["table"] = [
                    ("Control", "Dato / responsable / periodicidad"),
                    ("IBC", "Artículo 89 de la Ley 2277 de 2022 cuando concurran sus presupuestos; cálculo con periodo y topes vigentes"),
                    ("PILA", "Periodo ejecutado y pago mes vencido cuando resulte exigible"),
                    ("ARL", "Afiliación, clase de riesgo y responsable de cotización según la norma vigente"),
                    ("Verificación", "Soporte pertinente, minimizado y coherente con el contrato"),
                ]
            else:
                section["table"] = [
                    ("Control", "Dato / responsable / periodicidad"),
                    ("Naturaleza del contratista", "Pendiente de confirmar antes de aplicar reglas personales de cotización"),
                    ("IBC", "No se presume a partir del valor contractual mientras la naturaleza y ejecución no estén determinadas"),
                    ("Verificación", "Solo soportes legalmente procedentes una vez clasificado el vínculo real"),
                ]
        result.append(section)
    return result


def compose_services_m33_reviewed(answers: dict) -> dict[str, Any]:
    composition = deepcopy(compose_services_m33_base(answers))
    nature = _contractor_nature(answers)
    source_ids = _source_ids(nature)
    source_manifest = build_legal_source_manifest(source_ids)
    sections = composition.get("sections") or []

    annex_index = next((i for i, section in enumerate(sections) if section.get("_type") == "annex"), len(sections))
    control_index = next((i for i, section in enumerate(sections) if section.get("_type") == "control"), len(sections))
    principal = sections[:annex_index]
    scope = sections[annex_index:control_index]
    controls = sections[control_index:]

    reviewed = _review_principal(principal, answers, nature) + _review_scope(scope, nature)
    controls = [_clean_section(section) for section in controls]
    for section in controls:
        if section.get("_type") == "control":
            _apply_source_control(section, source_ids)
            section["source_manifest_status"] = source_manifest["status"]
            section["text"] = (
                "Documento candidato interno CO-EM-003 M33.4. La liberación exige verificar identidad y naturaleza "
                "de las partes, capacidad, hechos, cuantías, fechas, módulos condicionales, ejecución real, fuentes "
                "jurídicas estructuradas y vigentes, y aprobación jurídica y QA sobre la misma revisión y hash. "
                "Si el manifiesto normativo indica needs_reverification, la fuente debe revalidarse antes de liberar."
            )
    reviewed += controls

    professional = _bool(_read(answers, "service.professional", False))
    composition["title"] = "CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES INDEPENDIENTES" if professional else "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES"
    composition["sections"] = reviewed
    composition["legal_source_manifest"] = source_manifest
    composition.setdefault("maturity_answers", {})["contractor_type_m33"] = nature
    composition["maturity_answers"]["ai_used_m33"] = _bool(_read(answers, "ai.used", False))
    composition["maturity_answers"]["legal_source_standard"] = "M33.4"
    composition["maturity_answers"]["legal_source_gate_m334"] = source_manifest["status"]
    composition["maturity_answers"]["legal_source_ids_m334"] = list(source_ids)
    return composition
