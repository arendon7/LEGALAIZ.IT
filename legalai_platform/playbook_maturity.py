from __future__ import annotations

"""Biblioteca M5 de playbooks jurídicos profundos para siete productos no contractuales.

Los documentos organizan hechos, pruebas, términos, actuaciones y escalamiento. No sustituyen
representación judicial ni producen automáticamente nulidad, sanción, pago, reconocimiento de
prestaciones o decisiones de autoridad. La liberación exige validación del caso concreto.
"""

from datetime import date
from typing import Any, Iterable
import re

BUILD_ID = "M20-COBRO-ACUERDO-PAGARE-2026-07-31"
MODEL_VERSION = "M20.1"
VERIFIED_AT = "31 de julio de 2026"


def val(data: dict[str, Any], key: str, default: str) -> str:
    raw = data.get(key)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip()


def yes(data: dict[str, Any], key: str, default: bool = False) -> bool:
    raw = data.get(key)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().casefold() in {"sí", "si", "true", "1", "yes", "y"}


def money(raw: Any, default: int = 0) -> str:
    if raw is None or raw == "":
        amount = default
    else:
        cleaned = re.sub(r"[^0-9,.-]", "", str(raw))
        try:
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            amount = int(round(float(cleaned)))
        except (TypeError, ValueError):
            amount = default
    return "COP $" + f"{amount:,}".replace(",", ".")


def section(heading: str, text: str = "", *, bullets: Iterable[str] | None = None,
            table: list[tuple[str, ...]] | None = None, page_break_before: bool = False,
            kind: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"heading": heading, "page_break_before": page_break_before}
    if text:
        out["text"] = text
    if bullets:
        out["bullets"] = list(bullets)
    if table:
        out["table"] = [tuple(row) for row in table]
    if kind:
        out["_type"] = kind
    return out


def control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo {MODEL_VERSION} del producto {product}. La información normativa fue verificada al {VERIFIED_AT}. "
            "El documento diferencia hechos suministrados, inferencias, reglas jurídicas y recomendaciones. No asegura resultados, "
            "no reemplaza la valoración probatoria ni autoriza actuaciones judiciales automáticas. Antes de firma, radicación o envío "
            "debe verificarse identidad, competencia, términos, anexos, autenticidad, vigencia, canal y estrategia del caso concreto."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def signature(name: str, label: str = "SOLICITANTE") -> dict[str, Any]:
    return {"heading": "FIRMA", "_type": "signature", "parties": [{"label": label, "name": name}]}


def evidence_table(items: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return [("EVIDENCIA", "ESTADO", "FINALIDAD"), *items]


# ---------------------------------------------------------------------------
# CO-LA-001 - LIQUIDACIÓN LABORAL Y RECLAMACIÓN (REVALIDACIÓN M16)
# ---------------------------------------------------------------------------

def la001_control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO M16, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo M16.1 del producto {product}. Información jurídica verificada al 31 de julio de 2026. "
            "El resultado separa cálculo matemático, calificación jurídica, prueba y estrategia. No declara deuda, mala fe, "
            "ineficacia del retiro, estabilidad reforzada, contrato realidad, sanción moratoria ni derecho litigioso. Antes de "
            "firma, pago, conciliación o demanda deben verificarse identidad, régimen, fechas de exigibilidad, bases, soportes, "
            "pagos, descuentos, prescripción, seguridad social y situación especial del trabajador."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def la001_diagnostic(a: dict[str, Any]) -> list[dict[str, Any]]:
    worker = val(a, "worker_name", "MARÍA FERNANDA LÓPEZ")
    employer = val(a, "employer_name", "SERVICIOS INTEGRALES DEL NORTE S.A.S.")
    start = val(a, "start_date", "1 de febrero de 2023")
    end = val(a, "end_date", "30 de junio de 2026")
    salary = money(a.get("salary"), 3_800_000)
    return [
        section("INFORME TÉCNICO DE DIAGNÓSTICO Y LIQUIDACIÓN LABORAL", f"Trabajador: {worker}. Empleador: {employer}. Periodo informado: {start} a {end}. Último salario fijo reportado: {salary}."),
        section("1. OBJETO, ALCANCE Y RESULTADO ESPERADO", "Reconstruir la relación y el cierre laboral por concepto, periodo, base y soporte; distinguir valores determinados, estimaciones condicionadas y pretensiones litigiosas; y producir una ruta de pago, reclamación o escalamiento. El informe no sustituye una sentencia, conciliación ante autoridad ni revisión profesional de alto impacto."),
        section("2. FILTRO DE ADMISIBILIDAD", table=[
            ("Control", "Resultado esperado", "Bloqueo o escalamiento"),
            ("Naturaleza del vínculo", "Trabajo particular regido por el CST", "Sector público, cooperativa, aprendizaje o contrato realidad"),
            ("Situación procesal", "Sin sentencia, conciliación o demanda activa", "Litigio, acuerdo con cosa juzgada o actuación administrativa"),
            ("Protección especial", "Sin fuero o estabilidad reforzada informada", "Salud, discapacidad, maternidad, paternidad, sindical, acoso o discriminación"),
            ("Régimen salarial", "Ordinario o integral válido y documentado", "Salario integral dudoso, pagos no salariales controvertidos o variables sin soporte"),
            ("Régimen de cesantías", "Anualizado Ley 50 o régimen identificado", "Régimen tradicional o transición no documentada"),
        ]),
        section("3. CRONOLOGÍA JURÍDICA", table=[
            ("Hito", "Dato", "Prueba mínima", "Efecto"),
            ("Ingreso", start, "Contrato, afiliación, certificación", "Inicio de causación"),
            ("Cambios salariales", val(a, "salary_changes", "Por verificar"), "Nómina, otrosí, extractos", "Bases por concepto"),
            ("Vacaciones disfrutadas", val(a, "vacations_taken", "Por conciliar"), "Registro y comprobantes", "Saldo de descanso"),
            ("Cesantías consignadas", val(a, "cesantias_history", "Por conciliar"), "Certificados de fondo", "Saldo anualizado"),
            ("Terminación", end, "Carta, acta, mensaje, PILA", "Exigibilidad y causa"),
            ("Pago final", val(a, "final_payment_date", "No acreditado"), "Comprobante discriminado", "Saldo y eventual mora"),
        ]),
        section("4. ARQUITECTURA DE BASES", table=[
            ("Concepto", "Base principal", "Auxilio de transporte", "Periodo de promedio/control"),
            ("Salario pendiente", "Salario ordinario y factores salariales causados", "Solo si corresponde al periodo trabajado", "Periodo adeudado"),
            ("Cesantías", "Último salario estable o promedio legal si hubo variación/variable", "Integra cuando existe derecho", "Último año o tiempo servido si menor"),
            ("Intereses de cesantías", "Cesantías causadas por anualidad o fracción", "Sigue la base de cesantías", "12 % anual proporcional"),
            ("Prima de servicios", "Salario devengado en el semestre", "Integra cuando existe derecho", "Cada semestre"),
            ("Vacaciones", "Salario ordinario; promedio anual si variable", "No integra", "Año anterior o tiempo aplicable"),
            ("Indemnización art. 64", "Salario sin auxilio de transporte", "No integra", "Modalidad y tiempo restante/servido"),
        ]),
        section("5. RUBROS Y ESTADO DE DECISIÓN", table=[
            ("Rubro", "Tratamiento M16", "Resultado permitido"),
            ("Salario, cesantías, intereses, prima y vacaciones", "Cálculo determinístico con líneas separadas", "Estimación reproducible"),
            ("Indemnización por terminación", "Módulo independiente por modalidad y causa", "Estimación condicionada"),
            ("Sanción art. 65 CST", "Exige análisis judicial de conducta y buena fe", "No se suma automáticamente"),
            ("Sanción por no consignar cesantías", "Exige anualidad, mora, prescripción y conducta", "No se suma automáticamente"),
            ("Horas extra, recargos, comisiones y bonos", "Solo con trazabilidad de tiempo y naturaleza salarial", "Pendiente o cuantificado con soporte"),
            ("Aportes a seguridad social", "Conciliación por periodo e ingreso base", "Corrección o escalamiento"),
        ]),
        section("6. PRESCRIPCIÓN Y EXIGIBILIDAD", "Cada derecho tiene su propia fecha de exigibilidad. La regla general es de tres años; el reclamo escrito recibido por el empleador, respecto de un derecho debidamente determinado, interrumpe la prescripción una sola vez y hace comenzar un nuevo lapso igual. El sistema debe controlar cada concepto y no usar una única fecha global."),
        section("7. RESULTADO PRELIMINAR", "La salida final debe contener: línea de cálculo, base, periodo, fórmula, valor bruto, pago previo imputado, saldo, soporte, fuente y nivel de certeza. Los pagos globales o descuentos discutidos permanecen sin imputar hasta conciliación probatoria."),
        section("8. RIESGOS Y SIGUIENTE PASO", bullets=[
            "Obtener contrato, otrosíes, nómina, extractos, PILA, fondo de cesantías, vacaciones y soporte de terminación.",
            "Revisar salario integral, variables, pagos no salariales y cambios de los últimos tres meses.",
            "Construir calendario de exigibilidad y prescripción por concepto.",
            "Escalar fuero, salud, accidente, acoso, discriminación, contrato realidad, insolvencia o prescripción próxima.",
        ]),
        la001_control("CO-LA-001", assumptions=["Relación laboral privada", "Información salarial verificable", "Sin litigio ni protección especial activa"], sources=["CST, artículos 13 a 15, 64, 65, 149, 186, 192, 249, 253, 306, 488 y 489", "Ley 50 de 1990, artículo 99", "Ley 52 de 1975", "Ley 2466 de 2025", "Decretos 1469 y 1470 de 2025"], red_flags=["Fuero o estabilidad reforzada", "Contrato realidad", "Salario integral o variable dudoso", "Prescripción próxima", "Proceso judicial o insolvencia"]),
    ]


def la001_calculation(a: dict[str, Any]) -> list[dict[str, Any]]:
    salary = int(a.get("salary", 3_800_000))
    ces_base = int(a.get("cesantias_base", salary + 249_095))
    prima_base = int(a.get("prima_base", salary + 249_095))
    vacation_base = int(a.get("vacation_base", salary))
    days = int(a.get("settlement_days", 180))
    paid = int(a.get("payments_received", 2_500_000))
    ces = round(ces_base * days / 360)
    ints = round(ces * 0.12 * days / 360)
    prima = round(prima_base * days / 360)
    vac = round(vacation_base * days / 720)
    total = ces + ints + prima + vac
    balance = max(0, total - paid)
    return [
        section("ANEXO DE CÁLCULO LABORAL DETERMINÍSTICO M16", "Ejemplo controlado. Las cifras deben sustituirse por bases y periodos efectivamente probados. La hoja distingue prestaciones, vacaciones, salarios, indemnización, pagos y partidas litigiosas."),
        section("1. PARÁMETROS Y VERSIONADO", table=[
            ("Parámetro", "Valor", "Control"),
            ("Salario ordinario", money(salary), "Sin auxilio de transporte"),
            ("Base de cesantías", money(ces_base), "Incluye auxilio solo si hay derecho"),
            ("Base de prima", money(prima_base), "Promedio del semestre cuando corresponda"),
            ("Base de vacaciones", money(vacation_base), "Sin auxilio; promedio anual si variable"),
            ("Días 30/360", str(days), "Corte independiente por concepto"),
            ("Pagos identificados", money(paid), "Pendientes de imputación individual"),
            ("Parámetro 2026", "SMLMV COP $1.750.905; auxilio COP $249.095", "Revalidar antes de usar en otra vigencia"),
        ]),
        section("2. LÍNEAS DE CÁLCULO", table=[
            ("Concepto", "Fórmula", "Valor bruto", "Pago imputado", "Saldo"),
            ("Cesantías", f"{money(ces_base)} x {days} / 360", money(ces), "Por conciliar", money(ces)),
            ("Intereses de cesantías", f"{money(ces)} x 12 % x {days} / 360", money(ints), "Por conciliar", money(ints)),
            ("Prima de servicios", f"{money(prima_base)} x {days} / 360", money(prima), "Por conciliar", money(prima)),
            ("Vacaciones", f"{money(vacation_base)} x {days} / 720", money(vac), "Por conciliar", money(vac)),
            ("Subtotal", "Suma de líneas", money(total), money(paid), money(balance)),
        ]),
        section("3. SEGMENTACIÓN OBLIGATORIA", table=[
            ("Concepto", "Segmento", "Razón"),
            ("Cesantías", "Cada anualidad y fracción final", "Consignación anual, saldo directo y eventual mora separados"),
            ("Intereses", "Cada año o fracción", "Pago en enero, retiro o liquidación parcial"),
            ("Prima", "Primer y segundo semestre", "Exigibilidad y pagos semestrales"),
            ("Vacaciones", "Causación, disfrute, compensación", "Evitar duplicar días ya disfrutados"),
            ("Indemnización", "Una línea separada", "No es prestación social"),
        ]),
        section("4. SALARIO VARIABLE Y FACTORES", bullets=[
            "Cesantías: último salario si no varió en los tres meses finales; en caso contrario, promedio del último año o de todo el tiempo si fue menor.",
            "Vacaciones: salario ordinario vigente al iniciar el descanso; si es variable, promedio del año inmediatamente anterior.",
            "Prima: reconstruir lo devengado en cada semestre, incluidos factores salariales probados.",
            "Comisiones, recargos y pagos habituales se clasifican antes de promediar; la etiqueta contractual no decide por sí sola su naturaleza.",
            "El salario integral válido compensa prestaciones distintas de vacaciones; si su validez es dudosa, bloquear el cálculo automático de prestaciones.",
        ]),
        section("5. PAGOS, DEDUCCIONES Y REDONDEO", "Cada pago requiere fecha, valor, concepto, periodo y soporte. No se descuenta globalmente una transferencia sin concepto. Las deducciones por daños, equipos, deudas o pérdidas exigen autorización válida para el caso o mandamiento judicial y no pueden desconocer límites legales. Se conservan valores con dos decimales en el motor y se redondea a pesos únicamente en la presentación."),
        section("6. PARTIDAS EXCLUIDAS DEL TOTAL AUTOMÁTICO", table=[
            ("Partida", "Motivo de exclusión", "Ruta"),
            ("Sanción moratoria art. 65", "Depende de conducta y buena fe", "Valoración judicial"),
            ("Sanción por cesantías no consignadas", "Depende de anualidad, mora, prescripción y conducta", "Análisis separado"),
            ("Indexación e intereses judiciales", "Dependen de decisión y periodo", "Módulo litigioso"),
            ("Horas extra y recargos", "Exigen jornada, autorización y prueba", "Matriz de tiempo"),
            ("Aportes omitidos", "No equivalen siempre a pago directo al trabajador", "Corrección de seguridad social"),
        ]),
        section("7. REPRODUCIBILIDAD", "El expediente conserva parámetros, fórmulas, fuentes, segmentos, redondeos, pagos y versión normativa. Un tercero debe poder recalcular cada línea y distinguir dato suministrado, inferencia y decisión profesional."),
        la001_control("CO-LA-001-CÁLCULO", assumptions=["Parámetros de ejemplo", "Régimen privado y anualizado", "Pagos conciliables por concepto"], sources=["CST, artículos 127 a 130, 149, 186, 192, 249, 253 y 306", "Ley 50 de 1990, artículo 99", "Ley 52 de 1975"], red_flags=["Salario variable sin soportes", "Salario integral dudoso", "Pagos no discriminados", "Sanción o indemnización controvertida"]),
    ]


def la001_termination(a: dict[str, Any]) -> list[dict[str, Any]]:
    salary = money(a.get("salary"), 3_800_000)
    return [
        section("MATRIZ DE TERMINACIÓN, INDEMNIZACIONES Y PROTECCIONES", f"Base salarial ilustrativa sin auxilio de transporte: {salary}. La causa debe fijarse al momento de terminar; no pueden agregarse posteriormente motivos distintos."),
        section("1. CLASIFICACIÓN DE LA TERMINACIÓN", table=[
            ("Escenario", "Documento mínimo", "Cálculo automático", "Escalamiento"),
            ("Renuncia libre", "Carta y fecha efectiva", "Prestaciones y salarios", "Coacción o renuncia inducida"),
            ("Mutuo acuerdo", "Acuerdo claro y libre", "Prestaciones y suma pactada", "Derechos ciertos, vicios o fuero"),
            ("Justa causa del empleador", "Carta contemporánea, hechos y prueba", "No indemnización art. 64", "Debido proceso, proporcionalidad o causa controvertida"),
            ("Sin justa causa", "Carta y modalidad contractual", "Indemnización art. 64", "Fuero o estabilidad reforzada"),
            ("Terminación por trabajador con justa causa", "Carta contemporánea y prueba", "Potencial indemnización art. 64", "Valoración judicial"),
            ("Vencimiento fijo/fin de obra", "Contrato, preaviso o prueba de finalización", "Prestaciones", "Prórroga, límite legal o falsa obra"),
        ]),
        section("2. INDEMNIZACIÓN DEL ARTÍCULO 64", table=[
            ("Modalidad", "Regla legal", "Base", "Control"),
            ("Término fijo", "Salarios del tiempo faltante", "Salario diario sin auxilio", "Fecha final válida y no vencida"),
            ("Obra o labor", "Duración restante estimada, mínimo 15 días", "Salario diario sin auxilio", "Obra individualizada y saldo demostrable"),
            ("Indefinido < 10 SMLMV", "30 días primer año + 20 por cada año adicional y fracción", "Último salario", "Antigüedad 30/360"),
            ("Indefinido >= 10 SMLMV", "20 días primer año + 15 por cada año adicional y fracción", "Último salario", "Umbral vigente al retiro"),
        ]),
        section("3. CONTRATOS A TÉRMINO FIJO DESPUÉS DE LA REFORMA", "Verificar forma escrita, plazo, prórrogas y límite máximo legal de cuatro años. La clasificación contractual no se acepta por etiqueta: un contrato vencido, prorrogado o celebrado sin requisitos puede exigir una calificación distinta antes de calcular la indemnización."),
        section("4. ESTABILIDAD REFORZADA Y FUEROS", table=[
            ("Factor", "Señal", "Acción M16"),
            ("Salud/discapacidad", "Incapacidad, restricciones, diagnóstico conocido", "Bloquear cierre automático y remitir a abogado"),
            ("Maternidad/lactancia", "Embarazo, licencia o periodo protegido", "Verificar autorización y efectos"),
            ("Sindical/circunstancial", "Cargo, afiliación o conflicto colectivo", "Verificar fuero y juez competente"),
            ("Acoso/discriminación/represalia", "Queja o trato diferenciado", "Preservar evidencia y análisis constitucional"),
            ("Pensión próxima", "Condición de prepensionado alegada", "Análisis jurisprudencial individual"),
        ]),
        section("5. SEGURIDAD SOCIAL Y CERTIFICADOS", bullets=[
            "Conciliar aportes de salud, pensión, riesgos y parafiscales por los periodos aplicables.",
            "Verificar la información escrita y soportes de cotizaciones de los tres meses anteriores cuando corresponda al régimen del artículo 65.",
            "Entregar certificación laboral, desprendible final, soporte de retiro y documentos de seguridad social sin condicionar derechos mínimos a un paz y salvo general.",
        ]),
        section("6. SANCIONES Y PRETENSIONES CONDICIONADAS", "La indemnización moratoria del artículo 65 y la sanción por falta de consignación de cesantías no operan por simple mora aritmética. Deben revisarse deuda, conducta, razones del empleador, anualidades, prescripción y prueba. M16 las muestra como escenarios, nunca como saldo cierto."),
        section("7. DECISIÓN", "Solo se libera una cifra de indemnización cuando modalidad, causa, fechas, salario base y ausencia de protección especial están verificadas. De lo contrario, el documento informa escenarios y conserva el rubro fuera del total cierto."),
        la001_control("CO-LA-001-TERMINACIÓN", assumptions=["Modalidad y causa verificables", "Ausencia de protección especial", "Salario base soportado"], sources=["CST, artículos 46, 47, 62, 64, 65 y 66", "Ley 2466 de 2025", "Jurisprudencia aplicable a estabilidad reforzada"], red_flags=["Salud o discapacidad", "Maternidad o fuero", "Renuncia inducida", "Justa causa discutida", "Contrato fijo/obra desnaturalizado"]),
    ]


def la001_claim(a: dict[str, Any]) -> list[dict[str, Any]]:
    worker = val(a, "worker_name", "MARÍA FERNANDA LÓPEZ")
    employer = val(a, "employer_name", "SERVICIOS INTEGRALES DEL NORTE S.A.S.")
    return [
        section("RECLAMACIÓN LABORAL DIRECTA E INTERRUPCIÓN CONTROLADA DE PRESCRIPCIÓN", f"Señores {employer}. {worker}, identificado en los anexos, formula reclamación escrita, concreta y verificable sobre los derechos individualizados a continuación."),
        section("1. IDENTIFICACIÓN Y CRONOLOGÍA", table=[
            ("Dato", "Información", "Anexo"),
            ("Vínculo", f"{val(a,'start_date','1 de febrero de 2023')} a {val(a,'end_date','30 de junio de 2026')}", "Contrato y afiliaciones"),
            ("Salario", money(a.get('salary'),3_800_000), "Nómina y extractos"),
            ("Terminación", val(a,'termination_reason','terminación sin justa causa informada por el empleador'), "Carta y comunicaciones"),
            ("Pago final", val(a,'final_payment_date','No acreditado'), "Comprobante y liquidación"),
        ]),
        section("2. DERECHOS DETERMINADOS", table=[
            ("Derecho", "Periodo exigible", "Saldo reclamado", "Soporte"),
            ("Salarios", val(a,'salary_period','Por individualizar'), money(a.get('salary_due'),0), "Nómina/turnos"),
            ("Cesantías", val(a,'cesantias_period','Anualidad y fracción final'), money(a.get('cesantias_due'),0), "Fondo y cálculo"),
            ("Intereses", val(a,'interest_period','Anualidad y fracción final'), money(a.get('interest_due'),0), "Cálculo anual"),
            ("Prima", val(a,'prima_period','Semestre aplicable'), money(a.get('prima_due'),0), "Nómina y cálculo"),
            ("Vacaciones", val(a,'vacation_period','Saldo de días'), money(a.get('vacation_due'),0), "Registro de disfrute"),
            ("Indemnización", val(a,'indemnity_basis','Condicionada a modalidad y causa'), money(a.get('indemnity_due'),0), "Contrato y carta"),
        ]),
        section("3. SOLICITUDES", bullets=[
            "Entregar liquidación discriminada por concepto, periodo, base, fórmula, días, deducciones y pagos.",
            "Remitir contrato, otrosíes, nómina, vacaciones, prima, cesantías, intereses, PILA y autorizaciones de descuento.",
            "Pagar inmediatamente el saldo no controvertido y explicar de fondo las diferencias restantes.",
            "Corregir aportes y registros de seguridad social cuando proceda, con soportes verificables.",
            "Proponer reunión o conciliación ante autoridad respecto de derechos discutibles, sin condicionar valores ciertos.",
        ]),
        section("4. PRESCRIPCIÓN", "Esta reclamación identifica los derechos, periodos y fundamentos cuya prescripción se pretende interrumpir conforme a los artículos 488 y 489 del CST. Debe acreditarse la recepción por el empleador. La interrupción opera una sola vez y no sustituye la presentación oportuna de la acción judicial."),
        section("5. RESERVAS", "La cuantificación puede ajustarse con nuevos soportes. No se renuncia a derechos mínimos ni se afirma automáticamente la procedencia de sanciones, fueros, reintegro, indexación o perjuicios. Cualquier pago debe imputarse expresamente."),
        section("6. ANEXOS Y CANAL", bullets=["Informe técnico M16", "Anexo de cálculo", "Matriz de terminación", "Matriz probatoria", "Soportes enumerados", f"Respuesta al correo {val(a,'email','maria.lopez@example.com')} y dirección registrada"]),
        signature(worker),
        la001_control("CO-LA-001-RECLAMACIÓN", assumptions=["Reclamación directa y recibida", "Derechos individualizados", "Sin demanda activa"], sources=["CST, artículos 488 y 489", "Constitución, artículo 53", "Reglas de derecho de petición cuando resulten aplicables"], red_flags=["Prescripción próxima", "Empleador insolvente", "Fuero, salud o discriminación", "Negativa a recibir", "Liquidación colectiva"]),
    ]


def la001_evidence(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ PROBATORIA, PAGOS, PERIODOS Y VACÍOS", "Inventario vivo para sostener cada hecho, base, línea de cálculo, pago y decisión de cierre."),
        section("1. MATRIZ MAESTRA", table=[
            ("Evidencia", "Estado", "Periodo", "Finalidad", "Hallazgo"),
            ("Contrato y otrosíes", "Aportado", "Vínculo", "Modalidad, cargo, salario", "Validar prórrogas"),
            ("Desprendibles de nómina", "Parcial", "Mes a mes", "Factores salariales y pagos", "Faltan variables"),
            ("Extractos bancarios", "Aportado", "Mes a mes", "Conciliar transferencias", "Concepto no siempre visible"),
            ("PILA e historia laboral", "Pendiente", "Vínculo completo", "Aportes y continuidad", "Solicitar operadores"),
            ("Fondo de cesantías", "Parcial", "Cada anualidad", "Consignaciones y retiros", "Comparar 14 de febrero"),
            ("Vacaciones", "Pendiente", "Cada periodo", "Días causados/disfrutados", "Evitar duplicidad"),
            ("Terminación", "Aportado", "Fecha final", "Causa y autor", "Revisar contemporaneidad"),
        ]),
        section("2. MATRIZ DE PAGOS", table=[
            ("Fecha", "Valor", "Concepto declarado", "Periodo", "Soporte", "Imputación M16"),
            (val(a,'payment_date','15/07/2026'), money(a.get('payments_received'),2_500_000), "Liquidación parcial", "No discriminado", "Transferencia", "Pendiente"),
        ]),
        section("3. MATRIZ DE BASES", table=[
            ("Periodo", "Salario fijo", "Variable salarial", "No salarial", "Auxilio", "Base por concepto"),
            ("Último año", money(a.get('salary'),3_800_000), "Por certificar", "Por clasificar", money(249_095), "Cesantías/vacaciones"),
            ("Semestre final", money(a.get('salary'),3_800_000), "Por certificar", "Por clasificar", money(249_095), "Prima"),
        ]),
        section("4. REGLAS DE INTEGRIDAD", bullets=[
            "Conservar original, fecha, origen y hash; no alterar capturas ni metadatos.",
            "Relacionar cada documento con el hecho y concepto que pretende demostrar.",
            "Marcar duplicados, contradicciones, documentos incompletos y evidencia producida por una parte.",
            "No convertir una inferencia contable en un hecho jurídico sin soporte.",
            "Minimizar datos personales y separar historia clínica o información sensible.",
        ]),
        section("5. VACÍOS CRÍTICOS", bullets=["Promedios de salario variable", "Historial de vacaciones", "Certificados de cesantías", "PILA y aportes", "Autorizaciones de descuento", "Soporte de justa causa o preaviso", "Prueba de pago e imputación"]),
        section("6. PLAN DE OBTENCIÓN", "Solicitar primero al empleador, fondos, EPS, AFP, ARL y operador PILA según competencia. Conservar acuse, reiterar únicamente lo faltante y escalar a inspección, conciliación o proceso con revisión profesional cuando exista negativa, alteración, urgencia o prescripción."),
        la001_control("CO-LA-001-EVIDENCIA", assumptions=["Matriz actualizada por versión", "Soportes obtenidos lícitamente"], sources=["CST y reglas probatorias laborales", "Ley 1581 de 2012", "Política de auditoría LegalAIZ.it"], red_flags=["Documento dudoso", "Descuento por daño o equipo", "Historia clínica", "Contradicción material", "Pérdida de evidencia"]),
    ]


def la001_settlement(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("PROPUESTA CONDICIONAL DE PAGO, TRANSACCIÓN Y CIERRE", "Borrador para negociación. No sustituye conciliación ante autoridad cuando esta sea necesaria ni permite renunciar a derechos ciertos e indiscutibles."),
        section("1. CLASIFICACIÓN DE VALORES", table=[
            ("Categoría", "Valor", "Tratamiento"),
            ("Cierto y no controvertido", money(a.get('recognized_amount'),8_000_000), "Pago inmediato, sin condicionamiento"),
            ("Discutible o incierto", money(a.get('disputed_amount'),3_500_000), "Negociación/transacción específica"),
            ("No conciliable o de terceros", "Por verificar", "Aportes, derechos de terceros y límites legales"),
            ("Sanciones y perjuicios", "No incluidos", "Revisión profesional y eventual autoridad"),
        ]),
        section("2. OBJETO LIMITADO", "El acuerdo identifica hechos, conceptos, periodos, valores y soportes. La transacción solo alcanza derechos discutibles o inciertos expresamente delimitados; no contiene renuncia general, cláusula de paz y salvo universal ni declaración ficticia de pago."),
        section("3. FORMA DE PAGO", table=[
            ("Cuota", "Fecha", "Valor", "Concepto", "Condición de cierre"),
            ("1", "Firma", money(4_000_000), "Saldo cierto parcial", "Comprobante identificado"),
            ("2", "+30 días", money(4_000_000), "Saldo cierto restante", "Sin mora"),
            ("3", "Según acuerdo", "Por definir", "Derechos discutibles", "Conciliación específica"),
        ]),
        section("4. SEGURIDAD SOCIAL Y DOCUMENTOS", bullets=["Corregir y acreditar aportes", "Entregar certificación laboral", "Emitir liquidación final discriminada", "Actualizar fondos y registros", "Conservar comprobantes y constancias de recepción"]),
        section("5. INCUMPLIMIENTO", "Cualquier cláusula aceleratoria, interés, mérito ejecutivo o consecuencia de incumplimiento debe cumplir requisitos legales. No se permiten descuentos, compensaciones o autotutela distintos de los expresamente válidos."),
        section("6. EFECTOS Y RESERVAS", "El cierre se limita a los conceptos pagados o transados de manera específica. Permanecen fuera hechos ocultos, derechos de terceros, aportes no corregidos, protección especial desconocida, obligaciones no conciliables y asuntos judiciales no identificados."),
        section("7. APROBACIÓN", "Antes de firma debe existir cuadro comparativo, prueba de facultades, calendario, datos bancarios, evaluación de derechos ciertos, explicación comprensible y aprobación del especialista jurídico y QA."),
        la001_control("CO-LA-001-ACUERDO", assumptions=["Negociación libre e informada", "Valores separados por certeza", "Facultades verificadas"], sources=["CST, artículos 13, 14 y 15", "Constitución, artículo 53", "Reglas de conciliación y transacción"], red_flags=["Renuncia general", "Derecho cierto e indiscutible", "Incapacidad o fuero", "Litigio", "Presión o asimetría grave"]),
    ]


def la001_followup(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("GUÍA DE RADICACIÓN, PRESCRIPCIÓN, SEGUIMIENTO Y CIERRE", "Ruta operativa posterior al cálculo y reclamación."),
        section("1. RADICACIÓN CONTROLADA", bullets=["Usar canal oficial", "Firmar e identificar derechos y periodos", "Numerar anexos", "Obtener acuse con fecha", "Conservar versión exacta enviada", "No enviar múltiples cifras contradictorias"]),
        section("2. CALENDARIO POR DERECHO", table=[
            ("Derecho", "Fecha de exigibilidad", "Prescripción inicial", "Reclamo recibido", "Nuevo vencimiento"),
            ("Salario", "Fecha de pago pactada", "+3 años", val(a,'filing_date','31/07/2026'), "Calcular por línea"),
            ("Prima", "30 de junio/20 de diciembre o retiro", "+3 años", val(a,'filing_date','31/07/2026'), "Calcular por semestre"),
            ("Cesantías", "Consignación anual o retiro", "+3 años", val(a,'filing_date','31/07/2026'), "Calcular por anualidad"),
            ("Vacaciones", "Según exigibilidad aplicable", "+3 años", val(a,'filing_date','31/07/2026'), "Revisión profesional"),
            ("Indemnización", "Terminación", "+3 años", val(a,'filing_date','31/07/2026'), "Calcular individualmente"),
        ]),
        section("3. CONTROL DE RESPUESTA", table=[
            ("Pregunta", "Sí", "No", "Acción"),
            ("¿Respondió cada concepto?", "Conciliar", "Reiterar puntualmente", "No reiniciar reclamación genérica"),
            ("¿Aportó soportes?", "Verificar", "Registrar vacío", "Solicitar documento preciso"),
            ("¿Pagó saldo cierto?", "Imputar", "Mantener reclamación", "Conservar comprobante"),
            ("¿Alegó descuentos?", "Validar autorización", "Objetar", "No descontar automáticamente"),
            ("¿Hay riesgo de prescripción?", "Escalar", "Continuar", "No esperar indefinidamente"),
        ]),
        section("4. RUTAS DE ESCALAMIENTO", table=[
            ("Escenario", "Ruta principal", "Control"),
            ("Pago total probado", "Cierre", "Conciliar aportes y documentos"),
            ("Pago parcial", "Actualizar saldo", "Imputación por concepto"),
            ("Diferencia negociable", "Conciliación", "Autoridad competente cuando convenga"),
            ("Negativa o silencio", "Demanda laboral", "Abogado y prescripción"),
            ("Fuero/mínimo vital", "Tutela o ruta especial", "Urgencia y subsidiariedad"),
            ("Insolvencia", "Estrategia de cobro/proceso concursal", "Prelación y oportunidad"),
        ]),
        section("5. CIERRE DEL EXPEDIENTE", bullets=["Comprobantes conciliados", "Aportes verificados", "Documentos laborales entregados", "Acuerdo o decisión archivados", "Saldo en cero por concepto", "Retención y eliminación de datos conforme a política", "Auditoría de creación, revisión, aprobación y descarga"]),
        section("6. REAPERTURA", "Reabrir únicamente ante nuevo pago, soporte, respuesta, actuación administrativa/judicial o cambio normativo material. Toda reapertura crea revisión inmutable, comparación y explicación del cambio."),
        la001_control("CO-LA-001-SEGUIMIENTO", assumptions=["Cada fecha tiene soporte", "No hay representación automática"], sources=["CST, artículos 488 y 489", "Código Procesal del Trabajo y de la Seguridad Social", "Reglas de conciliación laboral"], red_flags=["Prescripción", "Medidas cautelares", "Insolvencia", "Tutela por mínimo vital", "Respuesta contradictoria"]),
    ]


# ---------------------------------------------------------------------------
# CO-SA-001 - SALUD (REVALIDACIÓN M17)
# ---------------------------------------------------------------------------

def sa001_control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO M17, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo M17.1 del producto {product}. Información jurídica verificada al 31 de julio de 2026. "
            "El resultado diferencia petición general, solicitud de información o documentos, reclamo asistencial simple, "
            "priorizado o vital, urgencia médica, historia clínica, inspección administrativa y tutela. No diagnostica, prescribe, "
            "autoriza servicios, sustituye triage ni garantiza una decisión favorable. Antes de radicar deben verificarse entidad "
            "responsable, orden clínica, riesgo, representación, términos, canales, anexos y necesidad de atención inmediata."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def sa001_diagnostic(a: dict[str, Any]) -> list[dict[str, Any]]:
    patient = val(a, "patient_name", "JULIÁN ANDRÉS PÉREZ")
    entity = val(a, "health_entity", "EPS SALUD EJEMPLO")
    return [
        section("DIAGNÓSTICO JURÍDICO Y RUTA DE ACCESO A SALUD M17", f"Paciente o usuario: {patient}. Entidad principal informada: {entity}. El análisis organiza la barrera, el riesgo, la evidencia, el término y la ruta; no reemplaza valoración médica."),
        section("1. NECESIDAD ASISTENCIAL", table=[
            ("Campo", "Dato informado", "Validación obligatoria"),
            ("Servicio o tecnología", val(a,'requested_service','consulta especializada, exámenes y tratamiento ordenados'), "Orden y alcance clínico"),
            ("Fecha de orden", val(a,'order_date','15 de julio de 2026'), "Vigencia y profesional tratante"),
            ("EPS/EAPB", entity, "Afiliación y competencia"),
            ("IPS o proveedor", val(a,'provider','IPS CLÍNICA EJEMPLO'), "Red y capacidad"),
            ("Barrera", val(a,'barrier','falta de autorización y asignación oportuna'), "Negativa, demora o incumplimiento material"),
        ]),
        section("2. CLASIFICACIÓN DE RIESGO Y TÉRMINO", table=[
            ("Clase", "Criterio operativo", "Máximo orientador"),
            ("Urgencia clínica", "Síntomas o condición que exigen atención inmediata", "No esperar un derecho de petición; acudir a urgencias"),
            ("Reclamo vital", "Riesgo inminente para vida o integridad", "Inmediato; máximo 24 horas para respuesta del vigilado"),
            ("Reclamo priorizado", "Vulnerabilidad o deterioro relevante sin riesgo vital acreditado", "Máximo 48 horas"),
            ("Reclamo simple", "Barrera asistencial sin prioridad o riesgo vital clasificado", "Máximo 72 horas"),
            ("Petición general", "Solicitud no asistencial ni ligada al acceso", "15 días hábiles"),
            ("Información/documentos", "Copias o datos no clasificados como reclamo asistencial", "10 días hábiles"),
            ("Consulta jurídica", "Concepto sobre materias a cargo de una autoridad", "30 días hábiles"),
        ]),
        section("3. TRIAGE JURÍDICO Y CLÍNICO", bullets=[
            "Registrar signos de alarma, dolor, progresión, interrupción del tratamiento y concepto del médico tratante.",
            "Identificar niñez, embarazo, vejez, discapacidad, enfermedad huérfana, condición catastrófica o dependencia.",
            "Si existe urgencia o riesgo inminente, activar atención asistencial y tutela/medida provisional según el caso; la radicación administrativa no debe retrasar la atención.",
            "No convertir la clasificación jurídica en diagnóstico médico ni minimizar el riesgo por ausencia de una etiqueta formal de la EPS.",
        ]),
        section("4. MATRIZ DE RESPONSABILIDADES", table=[
            ("Actor", "Obligación a verificar", "Documento"),
            ("EPS/EAPB", "Gestión, autorización, red, continuidad y solución de barreras", "Petición/reclamo y soportes"),
            ("IPS", "Prestación, agenda, historia clínica, información y continuidad asistencial", "Petición o solicitud clínica"),
            ("Proveedor/gestor", "Entrega efectiva de tecnología o medicamento", "Orden, autorización y constancia"),
            ("Supersalud", "Protección al usuario, seguimiento e inspección", "PQRD con riesgo clasificado"),
            ("Juez de tutela", "Protección inmediata de derechos fundamentales", "Acción revisada profesionalmente"),
        ]),
        section("5. PRUEBAS Y CRONOLOGÍA", bullets=["Orden o fórmula médica legible", "Historia clínica pertinente", "Autorización, negativa o direccionamiento", "Radicados y respuestas", "Agenda, cancelación o falta de red", "Prueba de riesgo y afectación", "Afiliación y datos de contacto", "Gastos, desplazamientos y continuidad", "Poder, autorización o agencia oficiosa cuando aplique"]),
        section("6. DECISIÓN DE RUTA", table=[
            ("Escenario", "Ruta principal", "Ruta paralela"),
            ("Riesgo vital o urgencia", "Atención inmediata + reclamo vital", "Tutela y medida provisional"),
            ("Barrera priorizada", "Reclamo priorizado de 48 horas", "Supersalud y seguimiento clínico"),
            ("Barrera simple", "Reclamo simple de 72 horas", "Reiteración y control"),
            ("Solo documentos", "Solicitud de información/copia", "Protección de datos y reserva"),
            ("Silencio o respuesta evasiva", "Reiteración precisa", "Tutela de petición y/o salud"),
        ]),
        sa001_control("CO-SA-001-DIAGNÓSTICO", assumptions=["Existe un usuario o paciente identificable", "La entidad y la barrera pueden individualizarse"], sources=["Ley 1751 de 2015", "Ley 1755 de 2015", "Circular Externa 008 de 2018 y actualización Supersalud 2023", "Sentencia T-370 de 2025"], red_flags=["Riesgo vital", "Urgencia no atendida", "Interrupción de servicio", "Menor o sujeto protegido", "Falta de legitimación"]),
    ]


def sa001_petition(a: dict[str, Any]) -> list[dict[str, Any]]:
    patient = val(a, "patient_name", "JULIÁN ANDRÉS PÉREZ")
    entity = val(a, "health_entity", "EPS SALUD EJEMPLO")
    return [
        section("DERECHO DE PETICIÓN Y RECLAMO PRIORITARIO EN SALUD M17", f"Señores {entity}. {patient}, identificado como aparece al pie de su firma, presenta solicitud respetuosa para obtener solución material, oportuna, continua e integral. La clasificación de riesgo debe confirmarse con los anexos y la condición actual."),
        section("1. IDENTIFICACIÓN Y LEGITIMACIÓN", table=[
            ("Campo", "Contenido"),
            ("Paciente", patient),
            ("Solicitante", val(a,'requester_name',patient)),
            ("Calidad", val(a,'requester_capacity','Titular del derecho')), 
            ("Documento", val(a,'patient_id','C.C. 1.000.000.001')),
            ("Afiliación", val(a,'affiliation','Afiliación activa por verificar')),
        ]),
        section("2. HECHOS EN ORDEN CRONOLÓGICO", table=[
            ("Fecha", "Hecho", "Soporte"),
            (val(a,'order_date','15/07/2026'), f"Orden de {val(a,'requested_service','consulta especializada, exámenes y tratamiento')}", "Orden médica"),
            (val(a,'first_request_date','17/07/2026'), "Solicitud inicial a la entidad", val(a,'first_filing','Radicado por aportar')),
            (val(a,'barrier_date','20/07/2026'), val(a,'barrier','Falta de autorización y asignación'), "Respuesta, captura o constancia"),
            (val(a,'current_date','31/07/2026'), val(a,'health_impact','Dolor persistente y riesgo de deterioro funcional'), "Historia y declaración"),
        ]),
        section("3. CLASIFICACIÓN SOLICITADA", table=[
            ("Factor", "Dato", "Petición"),
            ("Riesgo", val(a,'risk_level','Priorizar por verificar'), "Clasificar como simple, priorizado o vital y motivar"),
            ("Vulnerabilidad", val(a,'special_protection','No informada'), "Aplicar enfoque reforzado cuando corresponda"),
            ("Continuidad", val(a,'continuity','Tratamiento en curso'), "Evitar interrupciones administrativas o económicas"),
            ("Urgencia", val(a,'urgency','No descartada'), "Adoptar medida inmediata si vida o integridad están en peligro"),
        ]),
        section("4. SOLICITUDES ASISTENCIALES", bullets=[
            "Autorizar, direccionar y garantizar materialmente el servicio o tecnología ordenado, identificando prestador, sede, fecha, hora, canal y responsable.",
            "Resolver barreras de red, contratación, agenda, auditoría, entrega o traslado sin devolver la carga administrativa al usuario.",
            "Mantener la continuidad y adoptar una alternativa transitoria clínicamente adecuada si la solución definitiva requiere gestión adicional.",
            "Informar cualquier negativa mediante razones médicas y jurídicas individualizadas, la fuente técnica, el profesional responsable y la alternativa disponible.",
            "Coordinar integralmente órdenes relacionadas para evitar fragmentación del diagnóstico, tratamiento, rehabilitación o paliación.",
        ]),
        section("5. SOLICITUDES DE INFORMACIÓN Y TRAZABILIDAD", bullets=[
            "Remitir copia de la orden, autorizaciones, direccionamientos, auditorías, negaciones, devoluciones y comunicaciones asociadas.",
            "Identificar la fecha de recepción, clasificación de riesgo, funcionario o área responsable, actuaciones realizadas y término aplicado.",
            "Explicar qué entidad conserva cada soporte y trasladar de manera inmediata lo que no sea de su competencia, informando al peticionario.",
            "Responder cada punto de manera clara, precisa, congruente y consecuente; una respuesta favorable sin materialización no satisface la barrera asistencial.",
        ]),
        section("6. PRIORIDAD Y TÉRMINO", "Solicito aplicar el término especial del reclamo asistencial según el riesgo: solución inmediata y máximo 24 horas para riesgo vital, 48 horas para priorizado y 72 horas para simple. Subsidiariamente, las solicitudes generales se resuelven en 15 días hábiles y las de documentos o información en 10 días hábiles. Si existe peligro inminente para la vida o integridad, deben adoptarse medidas urgentes sin esperar el vencimiento de ningún término."),
        section("7. NOTIFICACIÓN SEGURA", f"Correo autorizado: {val(a,'email','julian.perez@example.com')}. Teléfono: {val(a,'phone','300 000 0000')}. Dirección: {val(a,'address','Medellín, Antioquia')}. Los datos clínicos deben remitirse por canal seguro y únicamente a las personas legitimadas."),
        section("8. ANEXOS", bullets=["Documento de identidad", "Orden o fórmula médica", "Historia clínica estrictamente pertinente", "Autorizaciones o negaciones", "Radicados y respuestas", "Prueba de urgencia o vulnerabilidad", "Poder/autorización/agencia oficiosa cuando aplique"]),
        signature(patient),
        sa001_control("CO-SA-001-PETICIÓN", assumptions=["La petición contiene hechos verificables y solicitudes determinadas", "El canal oficial de la entidad fue identificado"], sources=["Constitución, artículos 23, 48 y 49", "Ley 1755 de 2015, artículos 13, 14, 20, 21, 32 y 33", "Ley 1751 de 2015, artículos 2, 6, 8, 10 y 14", "Circular Externa 008 de 2018 y lineamientos Supersalud 2023"], red_flags=["Urgencia", "Riesgo vital", "Paciente sin capacidad", "Orden médica vencida o contradictoria", "Entidad no competente"]),
    ]


def sa001_record(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD DE HISTORIA CLÍNICA Y SOPORTES ASISTENCIALES M17", "Documento reservado para el titular o persona legitimada. La solicitud debe minimizar datos, fijar periodo y finalidad, y utilizar un canal seguro."),
        section("1. IDENTIFICACIÓN Y LEGITIMACIÓN", table=[
            ("Campo", "Dato", "Soporte"),
            ("Titular", val(a,'patient_name','JULIÁN ANDRÉS PÉREZ'), "Documento de identidad"),
            ("Solicitante", val(a,'requester_name','El propio titular'), val(a,'requester_capacity','Titular')),
            ("Institución custodio", val(a,'provider','IPS CLÍNICA EJEMPLO'), "Sede y NIT por verificar"),
            ("Periodo", val(a,'record_period','1 de enero a 31 de julio de 2026'), "Atenciones a individualizar"),
            ("Finalidad", val(a,'record_purpose','Continuidad del tratamiento y ejercicio de derechos'), "Uso limitado"),
        ]),
        section("2. DOCUMENTOS SOLICITADOS", bullets=[
            "Copia íntegra, legible, cronológica y gratuita de la historia clínica del periodo indicado.",
            "Órdenes, fórmulas, resultados, informes, imágenes disponibles, epicrisis, remisiones y planes de manejo.",
            "Consentimientos informados, registros de enfermería y demás anexos que formen parte del expediente clínico.",
            "Registros de entrega de copias, trazabilidad, correcciones y responsables de cada anotación cuando sean necesarios para verificar integridad.",
            "Índice o relación de documentos y explicación concreta de cualquier pieza inexistente o no custodiada por la institución.",
        ]),
        section("3. TÉRMINO APLICABLE", table=[
            ("Uso de la copia", "Clasificación", "Término orientador"),
            ("Consulta, tratamiento o urgencia actual", "Reclamo asistencial según riesgo", "24, 48 o 72 horas; inmediato si la clínica lo exige"),
            ("Copia sin incidencia asistencial inmediata", "Petición de documentos/información", "10 días hábiles"),
            ("Consulta jurídica general", "Consulta ante autoridad competente", "30 días hábiles"),
        ]),
        section("4. RESERVA, INTEGRIDAD Y SEGURIDAD", bullets=[
            "La historia clínica es privada, obligatoria y reservada; el acceso por terceros exige autorización o habilitación legal.",
            "La entidad debe verificar identidad y legitimación con medidas proporcionales, sin imponer barreras innecesarias al titular.",
            "La entrega electrónica debe usar PDF o formato disponible, enlace seguro, contraseña separada cuando proceda e índice de extracción.",
            "No se autoriza la publicación, transferencia a terceros, entrenamiento de modelos de IA ni uso diferente de la finalidad indicada.",
            "Cualquier corrección debe preservar el registro original, autor, fecha, hora y trazabilidad; no se solicita alterar la historia retrospectivamente.",
        ]),
        section("5. CASOS ESPECIALES", table=[
            ("Caso", "Validación adicional", "Riesgo"),
            ("Menor", "Representación y protección del interés superior", "Conflicto entre representantes"),
            ("Persona incapaz", "Apoyos, representación o agencia según el caso", "Exceso de datos"),
            ("Paciente fallecido", "Jurisprudencia y legitimación individual", "Reserva y derechos familiares"),
            ("Tercero autorizado", "Autorización específica y vigente", "Uso secundario"),
            ("Autoridad", "Competencia y finalidad legal", "Entrega excesiva"),
        ]),
        section("6. RESPUESTA Y TRASLADO", "Si la institución no conserva una parte de la información, debe identificar al custodio conocido, trasladar lo que corresponda cuando sea competente hacerlo e informar. Una respuesta que solo indique que el usuario consulte un portal, sin acceso efectivo o sin explicar faltantes, no satisface la solicitud."),
        signature(val(a,'requester_name',val(a,'patient_name','JULIÁN ANDRÉS PÉREZ'))),
        sa001_control("CO-SA-001-HISTORIA", assumptions=["El solicitante está legitimado", "El custodio y periodo pueden individualizarse"], sources=["Ley 1751 de 2015, artículo 10", "Resolución 1995 de 1999, artículos 1, 13 y 14", "Ley 2015 de 2020", "Ley 1755 de 2015"], red_flags=["Fallecido", "Menor o persona sin capacidad", "Conflicto familiar", "Solicitud por tercero", "Riesgo asistencial actual"]),
    ]


def sa001_evidence(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ DE EVIDENCIA, TÉRMINOS Y RESPUESTA M17", "Herramienta de control para separar hechos probados, afirmaciones, solicitudes, términos y cumplimiento material."),
        section("1. CRONOLOGÍA PROBATORIA", table=[
            ("Hito", "Fecha", "Soporte", "Confianza"),
            ("Orden médica", val(a,'order_date','15/07/2026'), "Orden/fórmula", "Alta si es legible"),
            ("Primera radicación", val(a,'first_request_date','17/07/2026'), val(a,'first_filing','Radicado pendiente'), "Por verificar"),
            ("Respuesta o negativa", val(a,'response_date','No informada'), val(a,'response_status','Sin respuesta de fondo'), "Pendiente"),
            ("Afectación clínica", val(a,'impact_date','31/07/2026'), val(a,'health_impact','Dolor y deterioro funcional'), "Requiere soporte clínico"),
            ("Escalamiento", val(a,'escalation_date','Por definir'), "PQRD/tutela", "No iniciado"),
        ]),
        section("2. MATRIZ DE TÉRMINOS", table=[
            ("Actuación", "Inicio", "Máximo", "Control"),
            ("Reclamo vital", "Recepción/traslado", "24 horas", "Solución inmediata si clínica lo exige"),
            ("Reclamo priorizado", "Recepción/traslado", "48 horas", "Vulnerabilidad y afectación"),
            ("Reclamo simple", "Recepción/traslado", "72 horas", "Barrera asistencial"),
            ("Petición general", "Recepción", "15 días hábiles", "Respuesta completa"),
            ("Información/documentos", "Recepción", "10 días hábiles", "Aceptación y entrega posterior según ley cuando aplique a autoridad"),
            ("Consulta a autoridad", "Recepción", "30 días hábiles", "Concepto no vinculante"),
        ]),
        section("3. CÁLCULO RESPONSABLE", bullets=[
            "Registrar la zona horaria, fecha y hora exactas de radicación y constancia de recepción.",
            "Para términos en horas, no convertir automáticamente a días hábiles; confirmar la instrucción sectorial aplicable.",
            "Para días hábiles, excluir fines de semana y verificar festivos nacionales y territoriales; el cálculo de la plataforma es preliminar.",
            "Registrar traslado por falta de competencia, solicitud de subsanación, prórroga motivada y fecha de notificación efectiva.",
            "No usar el vencimiento como sustituto de la urgencia clínica ni esperar pasivamente si existe deterioro.",
        ]),
        section("4. CONTROL DE RESPUESTA DE FONDO", table=[
            ("Requisito", "Pregunta de verificación", "Resultado"),
            ("Clara", "¿Es comprensible y sin fórmulas genéricas?", "Pendiente"),
            ("Precisa", "¿Responde cada solicitud concreta?", "Pendiente"),
            ("Congruente", "¿Corresponde a los hechos y servicio pedido?", "Pendiente"),
            ("Consecuente", "¿Explica el trámite y las actuaciones realizadas?", "Pendiente"),
            ("Notificada", "¿Llegó al canal autorizado con evidencia?", "Pendiente"),
            ("Materializada", "¿La cita, entrega o servicio ocurrió efectivamente?", "Pendiente"),
        ]),
        section("5. ÍNDICE DE ANEXOS", table=[
            ("No.", "Documento", "Fecha", "Integridad"),
            ("1", "Identificación y afiliación", "Por registrar", "Pendiente"),
            ("2", "Orden médica", val(a,'order_date','15/07/2026'), "Verificar firma y contenido"),
            ("3", "Historia clínica pertinente", "Por registrar", "Minimizada"),
            ("4", "Radicados/respuestas", "Por registrar", "Completa"),
            ("5", "Prueba de riesgo", "Por registrar", "Actualizada"),
            ("6", "Representación", "Si aplica", "Específica"),
        ]),
        section("6. DECISIÓN DE CIERRE O ESCALAMIENTO", "Cerrar solo cuando exista respuesta completa y solución material, o una decisión motivada y una ruta posterior definida. Reabrir ante incumplimiento, nueva orden, deterioro, cancelación, respuesta contradictoria o cambio de entidad responsable."),
        sa001_control("CO-SA-001-EVIDENCIA", assumptions=["Las fechas y documentos se conservan íntegros", "El nivel de riesgo se actualiza con la condición del paciente"], sources=["Ley 1755 de 2015", "Circular Externa 008 de 2018", "Lineamientos Supersalud 2023", "Sentencia T-370 de 2025"], red_flags=["Término vencido", "Respuesta no notificada", "Autorización no materializada", "Deterioro clínico", "Festivo o traslado no verificado"]),
    ]


def sa001_reiteration(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("REITERACIÓN, CUMPLIMIENTO MATERIAL Y MEDIDA URGENTE M17", "Para silencio, respuesta incompleta, autorización no materializada, cancelación repetida o barrera persistente. No sustituye atención de urgencias."),
        section("1. ACTUACIÓN PREVIA", table=[
            ("Dato", "Contenido", "Soporte"),
            ("Radicado", val(a,'filing_number','RAD-2026-001245'), "Constancia de recepción"),
            ("Fecha/hora", val(a,'filing_date','20/07/2026 09:30'), "Sello o email"),
            ("Clasificación solicitada", val(a,'risk_level','Priorizado por verificar'), "Anexos clínicos"),
            ("Respuesta", val(a,'response_status','Sin respuesta de fondo'), "Comunicación recibida"),
            ("Estado del servicio", val(a,'service_status','No materializado'), "Agenda/entrega"),
        ]),
        section("2. DEFICIENCIAS IDENTIFICADAS", bullets=[
            "No se respondió cada solicitud o se usó una fórmula genérica.",
            "Se expidió autorización sin prestador, fecha o disponibilidad efectiva.",
            "Se trasladó al usuario la gestión entre EPS, IPS, proveedor o auditoría.",
            "No se clasificó el riesgo ni se explicó el término aplicado.",
            "No se notificó por el canal autorizado o faltan soportes.",
            "La respuesta no abordó la continuidad ni el impacto clínico actual.",
        ]),
        section("3. REQUERIMIENTOS", bullets=[
            "Emitir respuesta clara, precisa, congruente, consecuente y notificada sobre todos los puntos pendientes.",
            "Materializar el servicio con fecha, lugar, prestador y responsable verificables.",
            "Adoptar medida transitoria segura cuando la espera pueda agravar la condición.",
            "Corregir la clasificación de riesgo y aplicar el término sectorial correspondiente.",
            "Remitir trazabilidad completa del caso, incluidos traslados, autorizaciones, cancelaciones y gestiones de red.",
        ]),
        section("4. ACTUALIZACIÓN DE RIESGO", table=[
            ("Indicador", "Estado actual", "Acción"),
            ("Dolor/deterioro", val(a,'health_impact','Persistente'), "Nueva valoración médica"),
            ("Interrupción", val(a,'continuity','Tratamiento en riesgo'), "Restablecer continuidad"),
            ("Vulnerabilidad", val(a,'special_protection','Por verificar'), "Priorización reforzada"),
            ("Riesgo vital", val(a,'vital_risk','No descartado'), "Urgencias + reclamo vital + tutela"),
        ]),
        section("5. ESCALAMIENTO RESPONSABLE", "Si persiste la barrera, se conservará la evidencia para PQRD ante Supersalud y valoración de tutela. Esta advertencia no prejuzga responsabilidad, no amenaza a la entidad y no obliga al usuario a esperar cuando exista riesgo clínico."),
        section("6. RESERVA", "La reiteración no renuncia a otros mecanismos, no acepta una negativa, no convalida demoras ni reinicia automáticamente términos ya vencidos. Toda nueva respuesta debe compararse con la solicitud original y con la situación clínica actual."),
        signature(val(a,'patient_name','JULIÁN ANDRÉS PÉREZ')),
        sa001_control("CO-SA-001-REITERACIÓN", assumptions=["Existe radicado y copia de la solicitud inicial", "La barrera continúa o la respuesta es insuficiente"], sources=["Ley 1755 de 2015", "Ley 1751 de 2015", "Sentencias T-016, T-370 y T-500 de 2025"], red_flags=["Empeoramiento", "Silencio en reclamo vital", "Cancelación repetida", "Menor o sujeto protegido", "Desacato o tutela previa"]),
    ]


def sa001_supersalud(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("PQRD Y SOLICITUD DE INTERVENCIÓN ANTE SUPERSALUD M17", "Actuación administrativa de protección al usuario e inspección, vigilancia y control. No reemplaza atención de urgencias, acción de tutela, responsabilidad médica ni proceso jurisdiccional."),
        section("1. IDENTIFICACIÓN DEL CASO", table=[
            ("Campo", "Dato"),
            ("Usuario", val(a,'patient_name','JULIÁN ANDRÉS PÉREZ')),
            ("EPS/EAPB", val(a,'health_entity','EPS SALUD EJEMPLO')),
            ("IPS/proveedor", val(a,'provider','IPS CLÍNICA EJEMPLO')),
            ("Servicio", val(a,'requested_service','Consulta, exámenes y tratamiento')),
            ("Barrera", val(a,'barrier','Falta de autorización y agenda')),
            ("Radicado previo", val(a,'filing_number','RAD-2026-001245')),
        ]),
        section("2. CLASIFICACIÓN DE RIESGO PROPUESTA", table=[
            ("Nivel", "Criterio", "Máximo"),
            ("Vital", "Riesgo inminente para vida o integridad", "24 horas y solución inmediata según clínica"),
            ("Priorizado", "Vulnerabilidad o riesgo relevante", "48 horas"),
            ("Simple", "Barrera asistencial sin prioridad acreditada", "72 horas"),
        ]),
        section("3. HECHOS Y GESTIONES", bullets=["Orden y necesidad clínica", "Radicación inicial", "Respuesta o silencio", "Autorización sin materialización", "Contactos con EPS/IPS/proveedor", "Afectación y evolución", "Reiteración y anexos"]),
        section("4. SOLICITUDES A SUPERSALUD", bullets=[
            "Registrar, clasificar y asignar número de PQRD, indicando el nivel de riesgo aplicado.",
            "Trasladar y requerir a los vigilados la solución integral dentro del término sectorial correspondiente.",
            "Hacer seguimiento a la materialización, no solo a la emisión de una respuesta formal.",
            "Informar actuaciones, entidad responsable, canal de consulta y resultado del seguimiento.",
            "Evaluar medidas de inspección, vigilancia o control cuando exista incumplimiento, reincidencia o riesgo.",
            "Preservar la confidencialidad de los datos clínicos y limitar su circulación a lo necesario.",
        ]),
        section("5. ALCANCE Y LÍMITES", bullets=[
            "La PQRD no suspende el deterioro ni sustituye urgencias; el usuario debe acudir a atención inmediata cuando corresponda.",
            "La intervención administrativa no garantiza autorización, sanción o indemnización.",
            "Cuando el asunto requiera protección judicial inmediata, debe valorarse tutela sin esperar el cierre administrativo.",
            "La responsabilidad médica o indemnizatoria requiere ruta, prueba y competencia diferentes.",
        ]),
        section("6. ANEXOS", bullets=["Petición y radicado", "Respuesta o evidencia de silencio", "Orden/historia pertinente", "Prueba de riesgo", "Autorizaciones/cancelaciones", "Identidad y representación", "Cronología M17"]),
        signature(val(a,'patient_name','JULIÁN ANDRÉS PÉREZ')),
        sa001_control("CO-SA-001-SUPERSALUD", assumptions=["La entidad vigilada está identificada", "Se aporta evidencia suficiente para clasificar el riesgo"], sources=["Ley 1751 de 2015", "Circular Externa 008 de 2018", "Circular Externa Supersalud 2023151000000010-5", "Régimen de inspección, vigilancia y control"], red_flags=["Riesgo vital", "Falla repetida", "Tutela inmediata", "Posible responsabilidad médica", "Datos de tercero"]),
    ]


def sa001_tutela_guide(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("GUÍA PARA VALORACIÓN PROFESIONAL DE ACCIÓN DE TUTELA M17", "No es una demanda automática. Organiza hechos, derechos, legitimación, subsidiariedad, urgencia y medidas para revisión jurídica antes de presentar."),
        section("1. DERECHOS Y PROBLEMAS", table=[
            ("Derecho", "Posible vulneración", "Prueba"),
            ("Petición", "Silencio o respuesta no clara, completa, congruente y notificada", "Radicado y respuesta"),
            ("Salud", "Barrera a servicio requerido", "Orden, historia y negativa"),
            ("Vida digna/integridad", "Dolor, deterioro o dependencia", "Concepto clínico"),
            ("Diagnóstico", "Falta de valoración o exámenes", "Orden/remisión"),
            ("Continuidad", "Interrupción por razones administrativas/económicas", "Tratamiento previo"),
        ]),
        section("2. LEGITIMACIÓN", table=[
            ("Modalidad", "Requisito"),
            ("Titular", "Identidad y afectación propia"),
            ("Representante", "Calidad legal y documentos"),
            ("Apoderado", "Poder y tarjeta profesional cuando corresponda"),
            ("Agente oficioso", "Manifestar y justificar por qué el titular no puede actuar"),
        ]),
        section("3. PROCEDENCIA Y URGENCIA", bullets=[
            "La tutela es el mecanismo directo para proteger el derecho de petición cuando no existe respuesta adecuada.",
            "En salud, valorar idoneidad y eficacia real de otros mecanismos según condición, tiempo y riesgo; la existencia de PQRD no excluye tutela urgente.",
            "Identificar perjuicio irremediable, sujeto de protección reforzada, interrupción y deterioro.",
            "No pedir servicios sin fundamento clínico cuando se requiera valoración del médico tratante; puede solicitarse diagnóstico o valoración integral.",
        ]),
        section("4. PRETENSIONES POSIBLES", bullets=[
            "Responder de fondo y notificar efectivamente cada punto de la petición.",
            "Realizar valoración diagnóstica y definir plan de manejo cuando la necesidad no esté determinada.",
            "Autorizar y garantizar materialmente el servicio ordenado, removiendo barreras administrativas.",
            "Asegurar continuidad, integralidad y coordinación entre EPS, IPS y proveedor.",
            "Entregar historia clínica o información reservada por canal seguro a persona legitimada.",
            "Adoptar medida provisional cuando la espera pueda causar daño grave o irreparable.",
        ]),
        section("5. MEDIDA PROVISIONAL", table=[
            ("Elemento", "Contenido mínimo"),
            ("Urgencia", "Qué puede ocurrir antes del fallo"),
            ("Necesidad", "Por qué la medida concreta evita el daño"),
            ("Soporte", "Orden, concepto, historia o signos de alarma"),
            ("Proporcionalidad", "Medida temporal y ejecutable"),
            ("Responsable", "Entidad con capacidad real de cumplir"),
        ]),
        section("6. PRUEBAS Y ACCIONADOS", bullets=["Identidad y legitimación", "Afiliación", "Orden/historia", "Cronología y radicados", "Respuesta o silencio", "Prueba de riesgo", "EPS, IPS, proveedor y terceros con responsabilidad concreta", "Datos de notificación"]),
        section("7. RIESGOS DE REDACCIÓN", bullets=["Hechos sin fecha o soporte", "Entidad equivocada", "Pretensiones médicas no ordenadas", "Solicitudes indemnizatorias", "Datos clínicos excesivos", "Tutela o incidente previo omitido", "No justificar agencia oficiosa", "Confundir respuesta formal con solución material"]),
        section("8. CIERRE PROFESIONAL", "El abogado debe definir competencia territorial, accionados, hechos, derechos, subsidiariedad, medida provisional, pretensiones, anexos y reserva. La plataforma no representa judicialmente ni garantiza admisión, medida o fallo favorable."),
        sa001_control("CO-SA-001-TUTELA", assumptions=["Los hechos y soportes fueron revisados", "La urgencia y subsidiariedad se analizaron individualmente"], sources=["Constitución, artículo 86", "Decreto 2591 de 1991", "Ley 1751 de 2015", "Sentencias T-016, T-370 y T-500 de 2025"], red_flags=["Riesgo vital", "Medida provisional", "Desacato o tutela previa", "Responsabilidad médica", "Agencia oficiosa dudosa"]),
    ]



# ---------------------------------------------------------------------------
# CO-CD-001 - HÁBEAS DATA FINANCIERO (REVALIDACIÓN M18)
# ---------------------------------------------------------------------------

def cd001_control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO M18, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo M18.1 del producto {product}. Información jurídica verificada al 31 de julio de 2026. "
            "El resultado diferencia consulta, reclamo, corrección, retiro, permanencia, caducidad, suplantación y cobro. "
            "El hábeas data no extingue por sí solo una obligación válida ni garantiza eliminación inmediata del dato. "
            "Antes de radicar debe verificarse identidad, legitimación, fuente, operador, obligación, mora, pago, comunicación previa, "
            "fecha del primer reporte, estado procesal, términos, régimen temporal y evidencia íntegra."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def cd001_diagnostic(a: dict[str, Any]) -> list[dict[str, Any]]:
    holder=val(a,'holder_name','CAROLINA MEJÍA RÍOS'); source=val(a,'source_entity','FINANCIERA EJEMPLO S.A.'); operator=val(a,'operator','OPERADOR DE INFORMACIÓN EJEMPLO')
    return [
        section("DIAGNÓSTICO JURÍDICO DE REPORTE FINANCIERO M18", f"Titular: {holder}. Fuente informada: {source}. Operador informado: {operator}. El diagnóstico clasifica el dato, sus responsables, la cronología y el remedio jurídicamente compatible."),
        section("1. IDENTIFICACIÓN Y LEGITIMACIÓN", table=[
            ("Campo", "Dato informado", "Verificación obligatoria"),
            ("Titular", holder, "Documento, contacto y calidad para actuar"),
            ("Obligación", val(a,'obligation','Crédito de consumo No. 45821'), "Contrato, desembolso, extractos y exigibilidad"),
            ("Fuente", source, "Quién originó y suministró el dato"),
            ("Operador", operator, "Quién administra y divulga la historia"),
            ("Usuario", val(a,'data_user','Entidad que consultó el dato, por identificar'), "Finalidad y fecha de consulta"),
        ]),
        section("2. CLASIFICACIÓN DEL PROBLEMA", table=[
            ("Hipótesis", "Pregunta decisiva", "Remedio preliminar"),
            ("Obligación inexistente", "¿El titular contrató o recibió el producto?", "Rectificación, retiro y protocolo de suplantación"),
            ("Dato inexacto", "¿Monto, mora, fecha o estado difieren de los soportes?", "Actualización y corrección trazable"),
            ("Pago no actualizado", "¿Existe extinción y fecha cierta?", "Actualizar estado y calcular permanencia"),
            ("Sin comunicación previa", "¿Se acreditó envío previo al reporte?", "Retiro inmediato o retiro para comunicar, según estado"),
            ("Permanencia vencida", "¿Se cumplió doble de mora, máximo cuatro años, o caducidad de ocho?", "Retiro por temporalidad"),
            ("Reporte tardío", "¿La fuente reportó después de 18 meses desde la mora?", "Cuestionar procedencia y trazabilidad"),
            ("Score afectado", "¿La medición no fue actualizada con el dato?", "Actualización simultánea de la medición"),
        ]),
        section("3. CRONOLOGÍA MÍNIMA", table=[
            ("Hito", "Fecha", "Soporte", "Riesgo"),
            ("Nacimiento de la obligación", val(a,'obligation_date','Por verificar'), "Contrato/desembolso", "Titularidad"),
            ("Mora", val(a,'mora_date','01/03/2026'), "Extracto/estado", "Inicio de permanencia y reporte"),
            ("Comunicación previa", val(a,'notice_date','Por verificar'), "Guía, correo, SMS o constancia", "Validez del reporte"),
            ("Primer reporte", val(a,'first_report_date','30/04/2026'), "Histórico del operador", "Límite de 18 meses"),
            ("Pago o extinción", val(a,'payment_date','10/07/2026'), "Paz y salvo/comprobante", "Actualización y permanencia"),
            ("Consulta/reclamo", val(a,'claim_date','20/07/2026'), "Radicado y acuse", "Términos especiales"),
        ]),
        section("4. RESPONSABLE CORRECTO", bullets=[
            "La fuente responde por calidad, veracidad, comunicación previa, actualización y soporte de la obligación.",
            "El operador administra, refleja novedades, incluye leyendas y permite consulta del titular.",
            "El usuario solo puede consultar y usar el dato para finalidades autorizadas; una decisión crediticia no debe basarse exclusivamente en el dato negativo.",
            "La pretensión debe dirigirse a quien puede ejecutar cada corrección; copiar indiscriminadamente no sustituye competencia.",
        ]),
        section("5. VIGENCIA DE LEY 2573 DE 2026", "A 31 de julio de 2026 el régimen general de la Ley 2573 de 2026 aún no está vigente: entra el 20 de noviembre de 2026. Solo sus excepciones expresas de vigencia inmediata pueden aplicarse. El expediente debe conservar la fecha de cada hecho y no anticipar efectos futuros."),
        section("6. RESULTADO PRELIMINAR", table=[
            ("Variable", "Estado"),
            ("Calidad del dato", val(a,'data_quality_status','Inconsistencia alegada; pendiente de cotejo')),
            ("Comunicación previa", val(a,'notice_status','No acreditada')),
            ("Permanencia/caducidad", val(a,'permanence_status','Pendiente de fechas ciertas')),
            ("Suplantación", val(a,'identity_theft','No descartada; requiere protocolo si se alega')),
            ("Cobro judicial o coactivo", val(a,'active_collection','No verificado')),
            ("Ruta", val(a,'recommended_route','Consulta integral + reclamo a fuente y operador')),
        ]),
        cd001_control("CO-CD-001-DIAGNÓSTICO", assumptions=["El reporte pertenece al régimen financiero, crediticio, comercial o de servicios", "Los datos aportados corresponden al titular"], sources=["Constitución, artículo 15", "Ley 1266 de 2008", "Ley 2157 de 2021", "Ley 2573 de 2026 con vigencia temporal controlada"], red_flags=["Suplantación", "Proceso ejecutivo o embargo", "Daño crediticio urgente", "Múltiples obligaciones", "Datos de terceros"]),
    ]


def cd001_consultation(a: dict[str, Any]) -> list[dict[str, Any]]:
    holder=val(a,'holder_name','CAROLINA MEJÍA RÍOS')
    return [
        section("CONSULTA INTEGRAL DE HÁBEAS DATA FINANCIERO M18", "Solicitud dirigida al operador y, cuando sea necesario, a la fuente para conocer el dato completo, su origen, circulación, soportes y modificaciones."),
        section("1. IDENTIFICACIÓN", table=[("Titular", holder), ("Documento", val(a,'holder_id','CC 43.000.000')), ("Obligación", val(a,'obligation','Crédito de consumo No. 45821')), ("Correo seguro", val(a,'email','carolina.mejia@example.com')), ("Canal de respuesta", val(a,'response_channel','Correo electrónico cifrado o portal autenticado'))]),
        section("2. SOLICITUDES AL OPERADOR", bullets=[
            "Entregar gratuitamente la historia completa positiva y negativa asociada al titular.",
            "Identificar fuente, usuarios que consultaron, fechas, finalidad, estado, monto, mora, pago, permanencia y cualquier score afectado.",
            "Entregar histórico de novedades, reclamos, leyendas y fechas de actualización o retiro.",
            "Explicar códigos, categorías, fechas de corte y reglas aplicadas, en lenguaje comprensible.",
            "Informar canales de reclamación y responsable de protección de datos.",
        ]),
        section("3. SOLICITUDES A LA FUENTE", bullets=[
            "Contrato, solicitud, desembolso, extractos, factura o soporte de la obligación.",
            "Autorización o base jurídica del tratamiento y del reporte.",
            "Comunicación previa, canal, contenido, dirección usada, fecha de envío, entrega o devolución.",
            "Fecha exacta de constitución en mora y primer reporte.",
            "Pagos, acuerdos, castigos, cesiones, novedades y reporte mensual al operador.",
            "Documentación de validación de identidad cuando exista alegación de suplantación.",
        ]),
        section("4. TÉRMINO Y CONTROL", table=[
            ("Actuación", "Término inicial", "Prórroga", "Condición"),
            ("Consulta", "10 días hábiles", "5 días hábiles", "Debe informarse la imposibilidad dentro del término inicial"),
            ("Traslado entre operador y fuente", "2 días hábiles", "No aplica", "Conservar trazabilidad del traslado"),
            ("Gratuidad", "Inmediata", "No aplica", "La consulta del titular por cualquier medio es gratuita"),
        ]),
        section("5. ENTREGA SEGURA Y MINIMIZACIÓN", "Solicito entrega legible y completa por canal autenticado. Los documentos de identidad, biometría, grabaciones y logs deben circular de forma restringida; no autorizo usos incompatibles, publicidad ni entrenamiento de modelos de IA."),
        signature(holder, "TITULAR O PERSONA LEGITIMADA"),
        cd001_control("CO-CD-001-CONSULTA", assumptions=["La solicitud la presenta el titular o representante acreditado", "La obligación y el operador pueden individualizarse"], sources=["Ley 1266 de 2008, artículos 10 y 16", "Ley 2157 de 2021"], red_flags=["Representación insuficiente", "Biometría o datos de terceros", "Negativa de acceso", "Consulta usada para fines laborales"]),
    ]


def cd001_claim(a: dict[str, Any]) -> list[dict[str, Any]]:
    holder=val(a,'holder_name','CAROLINA MEJÍA RÍOS')
    return [
        section("RECLAMO INTEGRAL DE ACTUALIZACIÓN, RECTIFICACIÓN O RETIRO M18", f"Titular: {holder}. Motivo informado: {val(a,'claim_reason','Pago efectuado y reporte no actualizado')}. La pretensión se condiciona a la evidencia y al régimen aplicable."),
        section("1. HECHOS DETERMINADOS", bullets=[
            f"Obligación reportada: {val(a,'obligation','Crédito de consumo No. 45821')}.",
            f"Mora informada: {val(a,'mora_date','01/03/2026')}; primer reporte: {val(a,'first_report_date','30/04/2026')}.",
            f"Pago o extinción: {val(a,'payment_date','10/07/2026')} — soporte: {val(a,'payment_support','comprobante y paz y salvo')}.",
            f"Comunicación previa: {val(a,'notice_status','no acreditada por la fuente')}.",
            f"Consulta reciente: {val(a,'credit_report_date','25/07/2026')} — estado observado: {val(a,'report_status','mora activa')}.",
        ]),
        section("2. PRETENSIONES POR RESPONSABLE", table=[
            ("Responsable", "Solicitud", "Evidencia esperada"),
            ("Fuente", "Cotejar obligación, comunicación, mora, pago y primer reporte; decidir motivadamente", "Contrato, extractos, aviso, trazabilidad y decisión"),
            ("Fuente", "Reportar de inmediato la novedad correcta al operador", "Constancia de transmisión"),
            ("Operador", "Incluir leyenda 'reclamo en trámite' dentro del término legal", "Fecha y captura del registro"),
            ("Operador", "Actualizar o retirar al recibir la novedad procedente", "Historia posterior y score actualizado"),
            ("Ambos", "Notificar respuesta y ejecución material", "Acuse, fecha, responsable y resultado"),
        ]),
        section("3. COMUNICACIÓN PREVIA", bullets=[
            "Si la obligación o cuota ya fue extinguida y no se cumplió la comunicación previa, procede solicitar retiro inmediato del reporte negativo.",
            "Si la obligación continúa vigente, debe retirarse el reporte y cumplirse la comunicación antes de reportar nuevamente.",
            "Para obligaciones iguales o inferiores al 15 % de un SMLMV se exigen al menos dos comunicaciones en días diferentes y veinte días calendario desde la última antes del reporte.",
            "La entidad debe probar el canal y la dirección utilizados; afirmar que 'se envió' no sustituye trazabilidad.",
        ]),
        section("4. PERMANENCIA, CADUCIDAD Y REPORTE TARDÍO", table=[
            ("Control", "Regla", "Dato a verificar"),
            ("Dato pagado/extinguido", "Doble del tiempo de mora, máximo cuatro años", "Mora exacta y fecha de extinción"),
            ("Dato insoluto", "Caducidad a los ocho años desde la mora", "Fecha cierta de mora y continuidad del dato"),
            ("Primer reporte", "Máximo 18 meses después de la constitución en mora", "Histórico certificado por fuente y operador"),
            ("Score", "Actualizar simultáneamente al retiro o cesación del hecho negativo", "Medición antes y después"),
        ]),
        section("5. TÉRMINO, PRÓRROGA Y SILENCIO", "El reclamo debe resolverse en quince (15) días hábiles. Solo puede prorrogarse hasta por ocho (8) días hábiles adicionales, explicando la demora antes del vencimiento inicial. El silencio produce el efecto favorable previsto en la ley, pero debe documentarse y exigirse su materialización; no extingue por sí solo una deuda válida ni reemplaza el análisis probatorio."),
        section("6. ANEXOS", bullets=["Documento de identidad minimizado", "Consulta del operador", "Contrato o extractos disponibles", "Comprobantes y paz y salvo", "Comunicación previa o prueba de su ausencia", "Cronología y radicados", "Poder, cuando aplique"]),
        signature(holder, "TITULAR O PERSONA LEGITIMADA"),
        cd001_control("CO-CD-001-RECLAMO", assumptions=["Los soportes corresponden a la obligación discutida", "La causal de corrección está individualizada"], sources=["Ley 1266 de 2008, artículos 12, 13 y 16", "Ley 2157 de 2021"], red_flags=["Obligación judicializada", "Cesión no informada", "Prescripción discutida", "Múltiples fuentes", "Daño económico relevante"]),
    ]


def cd001_identity(a: dict[str, Any]) -> list[dict[str, Any]]:
    holder=val(a,'holder_name','CAROLINA MEJÍA RÍOS')
    return [
        section("PROTOCOLO DE SUPLANTACIÓN DE IDENTIDAD M18", f"Titular afectado: {holder}. Ruta de contención, preservación, cotejo, corrección y control temporal. La alegación debe tramitarse de buena fe sin exigir cargas declaradas inconstitucionales."),
        section("1. CONTENCIÓN INMEDIATA", bullets=[
            "Bloquear productos, SIM, accesos y credenciales comprometidos por canales oficiales.",
            "Activar alertas gratuitas de nuevas obligaciones y consultas en los operadores de información.",
            "Preservar mensajes, correos, números, IP, grabaciones, comprobantes, dispositivos y metadatos sin alterarlos.",
            "No entregar códigos, instalar software remoto ni remitir documentos completos por canales inseguros.",
        ]),
        section("2. PETICIÓN A LA FUENTE", bullets=[
            "Cotejar los documentos usados para adquirir la obligación con los aportados por el titular.",
            "Entregar copia íntegra de solicitud, contrato, grabaciones, biometría, firmas, logs, IP, geolocalización y validaciones de identidad.",
            "Marcar el registro como 'Víctima de Falsedad Personal' cuando proceda, sin afectación de score.",
            "Corregir dato negativo, score y cualquier medición asociada conforme al régimen vigente.",
            "Explicar controles de conocimiento del cliente y hallazgos de la investigación interna.",
        ]),
        section("3. RÉGIMEN TEMPORAL AL 31 DE JULIO DE 2026", table=[
            ("Regla", "Estado", "Uso M18"),
            ("Ley 1266 + Ley 2157", "Vigentes", "Base principal para reclamo, cotejo, leyenda y silencio"),
            ("Ley 2573, parágrafos 1 y 2 del artículo 5", "Vigencia inmediata desde promulgación", "Aplicar únicamente su contenido exacto verificado"),
            ("Resto de Ley 2573", "Vigencia general desde 20/11/2026", "No anticipar suspensión, cobro o procedimientos futuros"),
            ("Sentencia C-413 de 2025", "Control constitucional vinculante", "No exigir denuncia como barrera para consultar o recibir documentos; observar condicionamientos"),
        ]),
        section("4. DENUNCIA Y PRUEBA", "La denuncia penal puede ser relevante para investigación y para actuaciones futuras, pero no debe exigirse como condición absoluta para que el titular consulte sus datos o reciba los documentos de contratación. Debe diferenciarse el acceso al dato, la corrección administrativa y la determinación penal de la suplantación."),
        section("5. MATRIZ DE EVIDENCIA", table=[
            ("Evidencia", "Estado", "Custodio", "Finalidad"),
            ("Consulta de historia", "Aportada", "Titular", "Identificar producto y reporte"),
            ("Contrato y solicitud", "Solicitados", "Fuente", "Cotejar firma e identidad"),
            ("Biometría/grabaciones", "Solicitadas", "Fuente", "Verificación técnica"),
            ("Logs/IP/geolocalización", "Preservación solicitada", "Fuente/proveedor", "Trazabilidad"),
            ("Denuncia/noticia criminal", "Según estrategia", "Fiscalía", "Investigación penal"),
            ("Pérdida de documento o SIM", "Por verificar", "Titular/operador", "Contexto y temporalidad"),
        ]),
        section("6. ESCALAMIENTO", bullets=["Bloqueo o embargo inminente", "Múltiples productos fraudulentos", "Movimientos de fondos", "Amenazas o extorsión", "Negativa de entrega documental", "Divergencias biométricas", "Daño grave al mínimo vital o acceso a vivienda"]),
        cd001_control("CO-CD-001-SUPLANTACIÓN", assumptions=["La persona manifiesta de buena fe no haber adquirido la obligación", "La fuente conserva evidencia de contratación"], sources=["Ley 1266 de 2008", "Ley 2157 de 2021", "Ley 2573 de 2026", "Sentencia C-413 de 2025"], red_flags=["Cobro judicial", "Pérdida patrimonial", "Fraude serial", "Riesgo personal", "Prueba digital volátil"]),
    ]


def cd001_escalation(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("REITERACIÓN Y ESCALAMIENTO ANTE AUTORIDAD M18", "Actuación para silencio, respuesta incompleta, incumplimiento material o desacuerdo persistente. Debe conservar la reclamación previa exigible y no sustituye recursos judiciales o contractuales."),
        section("1. CONTROL DE RESPUESTA", table=[
            ("Punto", "Resultado", "Defecto"),
            ("Comunicación previa", val(a,'notice_answer','No anexada'), "Falta trazabilidad"),
            ("Soporte de obligación", val(a,'contract_answer','Parcial'), "No permite cotejo"),
            ("Permanencia", val(a,'permanence_answer','No explicada'), "Sin cálculo verificable"),
            ("Leyenda de reclamo", val(a,'legend_answer','No visible'), "Incumplimiento operativo"),
            ("Actualización material", val(a,'update_answer','Pendiente'), "Respuesta formal sin ejecución"),
        ]),
        section("2. REITERACIÓN DIRIGIDA", bullets=[
            "Identificar radicado, fecha y término vencido.",
            "Enumerar exclusivamente los puntos omitidos o incongruentes.",
            "Aportar evidencia nueva y pedir decisión motivada por responsable.",
            "Exigir actualización material y constancia al operador, no solo promesa futura.",
            "Invocar el silencio favorable solo cuando la cronología y el régimen estén comprobados.",
        ]),
        section("3. AUTORIDAD COMPETENTE", table=[
            ("Actor o asunto", "Autoridad potencial", "Alcance"),
            ("Fuente u operador no sometido a SFC", "Superintendencia de Industria y Comercio", "Protección de datos y hábeas data"),
            ("Entidad vigilada financiera", "Superintendencia Financiera, según competencia", "Protección al consumidor financiero y régimen vigilado"),
            ("Delito de suplantación/fraude", "Fiscalía General de la Nación", "Investigación penal"),
            ("Amenaza urgente a derecho fundamental", "Juez constitucional", "Tutela excepcional y subsidiaria"),
            ("Cobro ejecutivo", "Juez del proceso", "Excepciones, nulidades y defensa procesal"),
        ]),
        section("4. EXPEDIENTE PARA QUEJA", bullets=["Identidad y legitimación", "Consulta y reporte", "Solicitud inicial", "Acuse y radicado", "Respuesta o silencio", "Prueba de término", "Soportes de obligación/pago", "Comunicación previa", "Captura de leyenda", "Perjuicio concreto", "Pretensión dentro de competencia"]),
        section("5. LÍMITES", "La autoridad administrativa puede investigar, ordenar medidas dentro de su competencia o sancionar, pero la plataforma no debe prometer indemnización, extinción de deuda, levantamiento judicial ni decisión favorable. La tutela exige subsidiariedad, urgencia y afectación concreta."),
        cd001_control("CO-CD-001-ESCALAMIENTO", assumptions=["Existe reclamación directa verificable cuando es requisito", "La autoridad y entidad vigilada fueron identificadas"], sources=["Ley 1266 de 2008", "Ley 2157 de 2021", "Procedimiento SIC vigente"], red_flags=["Tutela", "Proceso ejecutivo", "Embargo", "Daño reputacional o patrimonial cuantioso", "Término judicial próximo"]),
    ]


def cd001_evidence(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ DE EVIDENCIA, RESPONSABLES Y TRAZABILIDAD M18", "Control del ciclo completo del dato. Cada afirmación debe vincularse a un soporte, custodio, fecha, integridad y efecto jurídico."),
        section("1. INVENTARIO PROBATORIO", table=[
            ("Evidencia", "Custodio", "Estado", "Fecha", "Uso"),
            ("Contrato/solicitud", "Fuente", "Solicitado", "Por verificar", "Origen y autorización"),
            ("Extractos/estado de cuenta", "Fuente", "Parcial", "Por verificar", "Monto y mora"),
            ("Comunicación previa", "Fuente/proveedor", "No aportada", "Por verificar", "Procedencia del reporte"),
            ("Histórico del operador", "Operador", "Aportado", "25/07/2026", "Primer reporte y novedades"),
            ("Pago/paz y salvo", "Titular/fuente", "Aportado", "10/07/2026", "Extinción y actualización"),
            ("Radicados", "Titular/entidad", "Aportados", "20/07/2026", "Términos y silencio"),
        ]),
        section("2. MATRIZ DE CONSISTENCIA", table=[
            ("Campo", "Fuente", "Operador", "Titular", "Hallazgo"),
            ("Saldo", "COP $0", "COP $2.500.000", "Pagado", "Contradicción crítica"),
            ("Fecha mora", "01/03/2026", "01/02/2026", "No recuerda", "Obtener extractos"),
            ("Estado", "Pagada", "Mora", "Pagada", "Novedad no reflejada"),
            ("Comunicación", "Enviada", "No disponible", "No recibida", "Exigir trazabilidad"),
            ("Primer reporte", "30/04/2026", "30/04/2026", "Desconocido", "Consistente"),
        ]),
        section("3. CONTROL DE INTEGRIDAD DIGITAL", bullets=["Conservar archivo original", "Registrar URL/canal", "Fecha y hora de descarga", "Hash SHA-256", "No editar capturas", "Conservar encabezados de correo", "Restringir acceso por rol", "Eliminar copias innecesarias al cerrar"]),
        section("4. MATRIZ DE PRETENSIONES", table=[
            ("Pretensión", "Hecho", "Norma", "Prueba", "Responsable"),
            ("Actualizar pago", "Obligación extinguida", "Calidad y actualización", "Paz y salvo", "Fuente y operador"),
            ("Retirar por aviso", "No hubo comunicación previa", "Artículo 12", "Ausencia/constancias", "Fuente"),
            ("Retirar por temporalidad", "Permanencia vencida", "Artículo 13", "Mora y pago", "Operador"),
            ("Marcar reclamo", "Reclamo radicado", "Artículo 16", "Acuse", "Operador"),
            ("Corregir suplantación", "No contrató", "Régimen especial", "Cotejo y prueba sumaria", "Fuente/operador"),
        ]),
        cd001_control("CO-CD-001-EVIDENCIA", assumptions=["Los archivos son auténticos y corresponden al caso", "Las fechas no han sido alteradas"], sources=["Ley 1266 de 2008", "Ley 2157 de 2021", "Principios de veracidad, seguridad y circulación restringida"], red_flags=["Documento manipulado", "Prueba de tercero", "Biometría", "Cadena de custodia", "Contradicción material"]),
    ]


def cd001_deadline(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("CALENDARIO DE TÉRMINOS, PERMANENCIA Y CADUCIDAD M18", "Herramienta preliminar. Los días hábiles, festivos, recepción efectiva, traslado, requerimientos y prórrogas deben recalcularse antes de radicar o escalar."),
        section("1. TÉRMINOS DE ACTUACIÓN", table=[
            ("Actuación", "Término", "Inicio", "Control"),
            ("Consulta", "10 días hábiles", "Recepción completa", "Prórroga máxima de 5 días hábiles informada"),
            ("Reclamo", "15 días hábiles", "Recepción completa", "Prórroga máxima de 8 días hábiles informada"),
            ("Leyenda reclamo en trámite", "2 días hábiles", "Recepción del reclamo", "Verificar visualmente en el registro"),
            ("Traslado operador-fuente", "2 días hábiles", "Recepción por quien no resuelve", "Conservar constancia"),
            ("Comunicación previa", "20 días calendario", "Desde la última comunicación", "Antes del reporte"),
            ("Suplantación: cotejo vigente", "10 días", "Solicitud completa", "Controlar régimen temporal"),
        ]),
        section("2. PERMANENCIA DEL DATO", table=[
            ("Situación", "Regla", "Fórmula preliminar", "Resultado"),
            ("Mora pagada o extinguida", "Doble de la mora, máximo 4 años", "min(2 × duración mora, 4 años)", val(a,'paid_permanence_result','Pendiente')),
            ("Obligación insoluta", "Caducidad a 8 años desde la mora", "fecha mora + 8 años", val(a,'unpaid_caducity_result','Pendiente')),
            ("Primer reporte tardío", "Máximo 18 meses desde mora", "fecha mora + 18 meses", val(a,'late_report_result','Pendiente')),
            ("Obligación ≤15 % SMLMV", "Dos comunicaciones + 20 días", "última comunicación + 20 días", val(a,'small_debt_result','Pendiente')),
        ]),
        section("3. EJEMPLO CONTROLADO", table=[
            ("Dato", "Fecha"),
            ("Mora", val(a,'mora_date','01/03/2026')),
            ("Pago", val(a,'payment_date','10/07/2026')),
            ("Reclamo", val(a,'claim_date','20/07/2026')),
            ("Vencimiento preliminar reclamo", val(a,'claim_due','Pendiente de calendario oficial')),
            ("Prórroga máxima", val(a,'claim_extension_due','Pendiente de aviso oportuno')),
        ]),
        section("4. ALERTAS", bullets=["No sumar días calendario a términos hábiles", "No aplicar automáticamente transición de Ley 2157 ya agotada", "No confundir permanencia con prescripción de la deuda", "No calcular sin fecha cierta de mora y pago", "No anticipar la vigencia general de Ley 2573", "Registrar zona horaria y acuse efectivo"]),
        cd001_control("CO-CD-001-CALENDARIO", assumptions=["Las fechas ingresadas son ciertas", "El calendario oficial aplicable fue identificado"], sources=["Ley 1266 de 2008, artículos 12, 13 y 16", "Ley 2157 de 2021"], red_flags=["Festivos no incorporados", "Prórroga tardía", "Mora discutida", "Obligación reestructurada", "Proceso judicial"]),
    ]


# ---------------------------------------------------------------------------
# CO-CD-003 - CONSUMO
# ---------------------------------------------------------------------------

def cd003_classifier(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("CLASIFICADOR JURÍDICO DE GARANTÍA, RETRACTO, REVERSIÓN Y ENTREGA", f"Consumidor: {val(a,'consumer_name','DANIELA GÓMEZ SALAZAR')}. Proveedor: {val(a,'provider','COMERCIO DIGITAL EJEMPLO S.A.S.')}."),
        section("1. IDENTIFICACIÓN DE LA RELACIÓN DE CONSUMO", table=[
            ("Dato", "Resultado preliminar", "Control obligatorio"),
            ("Producto o servicio", val(a,'purchase','Computador portátil'), "Identificar referencia, serial, oferta y finalidad"),
            ("Canal", val(a,'channel','Comercio electrónico'), "Distinguir presencial, distancia, no tradicional o financiación directa"),
            ("Fecha de compra", val(a,'purchase_date','22 de julio de 2026'), "Separar compra, entrega y conocimiento de la causal"),
            ("Instrumento de pago", val(a,'payment_method','Tarjeta de crédito'), "Verificar si es electrónico y participantes domiciliados en Colombia"),
            ("Problema", val(a,'problem','Producto defectuoso y diferente al ofrecido'), "Clasificar defecto, incumplimiento, fraude o simple cambio de opinión"),
        ]),
        section("2. MATRIZ DE MECANISMOS", table=[
            ("Mecanismo", "Supuesto jurídico", "Término crítico", "Efecto potencial"),
            ("Garantía legal", "Falla de calidad, idoneidad, seguridad o funcionamiento", "Dentro de la garantía; reclamación directa", "Reparación gratuita; cambio o devolución cuando legalmente proceda"),
            ("Retracto", "Modalidad incluida, cinco días hábiles y ausencia de excepción", "5 días hábiles", "Resolución del contrato y devolución uniforme en máximo 15 días calendario"),
            ("Reversión del pago", "Comercio electrónico, pago electrónico y causal taxativa", "Queja y aviso dentro de 5 días hábiles", "Reversión provisional sujeta a controversia"),
            ("Terminación por no entrega", "Entrega supera plazo pactado o 30 días, o indisponibilidad", "Desde el incumplimiento", "Terminación unilateral y devolución en máximo 15 días calendario"),
            ("Reclamación directa/SIC", "Incumplimiento no solucionado", "15 días hábiles de respuesta como regla procesal", "Acción individual, denuncia o facilitación según pretensión"),
        ]),
        section("3. REGLA DE ELECCIÓN", "La aplicación debe recomendar un mecanismo principal y, cuando sea jurídicamente compatible, uno subsidiario. No debe acumular retracto, garantía y reversión como si fueran equivalentes ni permitir doble recuperación del precio."),
        section("4. ÁRBOL DE DECISIÓN", bullets=[
            "Si existe defecto dentro de garantía: priorizar garantía y documentar reparabilidad, repetición y custodia.",
            "Si el consumidor simplemente cambia de decisión: verificar modalidad, cinco días hábiles y excepciones del retracto.",
            "Si hubo fraude, operación no solicitada, no entrega, entrega diferente o defecto con pago electrónico: evaluar reversión dentro de cinco días hábiles.",
            "Si el comercio electrónico incumplió entrega: evaluar terminación unilateral y devolución, aunque no proceda retracto.",
            "Si hay daño a salud o seguridad: activar ruta de producto defectuoso, preservación y revisión profesional reforzada.",
        ]),
        section("5. CAMBIO NORMATIVO 2024-2026", "La Ley 2439 de 2024 reforzó el comercio electrónico. La Sentencia C-192 de 2026 condicionó la expresión relativa al comercio electrónico para que el término máximo de quince (15) días calendario de devolución por retracto aplique uniformemente a todas las modalidades del artículo 47 de la Ley 1480 de 2011."),
        section("6. ALERTAS DE NO AUTOMATIZACIÓN", bullets=["No concluir por el nombre comercial de la política de cambios", "No usar días calendario cuando la ley exige hábiles", "No exigir factura como única prueba de compra", "No atribuir al consumidor fallas sin diagnóstico", "No prometer reembolso duplicado", "No ignorar regímenes sectoriales especiales"]),
        control("CO-CD-003", assumptions=["Existe relación de consumo en Colombia", "Proveedor o productor identificable", "Fechas y canal verificables"], sources=["Ley 1480 de 2011", "Ley 2439 de 2024", "Sentencia C-192 de 2026", "Decreto 735 de 2013", "Decreto 587 de 2016"], red_flags=["Producto peligroso", "Fraude penal", "Proveedor extranjero", "Plazo de cinco días próximo", "Daño corporal", "Servicio financiero o telecomunicaciones"]),
    ]


def cd003_warranty(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("RECLAMACIÓN DIRECTA PARA HACER EFECTIVA LA GARANTÍA LEGAL", f"Producto/servicio: {val(a,'purchase','Computador portátil')}. Defecto informado: {val(a,'problem','Falla de encendido y especificaciones distintas')}."),
        section("1. PARTES Y TRAZABILIDAD", table=[("Campo", "Información"), ("Consumidor", val(a,'consumer_name','DANIELA GÓMEZ SALAZAR')), ("Proveedor", val(a,'provider','COMERCIO DIGITAL EJEMPLO S.A.S.')), ("Productor/importador", val(a,'producer','Por identificar')), ("Compra", val(a,'purchase_date','22 de julio de 2026')), ("Entrega", val(a,'delivery_date','23 de julio de 2026')), ("Serial/referencia", val(a,'serial','SERIAL-2026-001'))]),
        section("2. HECHOS RELEVANTES", bullets=["Oferta, publicidad y características determinantes", "Entrega y estado inicial", "Aparición y descripción precisa de la falla", "Uso normal, manuales y conservación", "Reclamaciones y reparaciones previas", "Daños adicionales o riesgos de seguridad"]),
        section("3. FUNDAMENTO Y RESPONSABLES", "La garantía legal es gratuita y obliga solidariamente al productor y al proveedor frente al consumidor. Para acreditar una falla de calidad o idoneidad debe preservarse el producto y describirse el defecto; las causales de exoneración deben ser probadas por quien las invoque."),
        section("4. PRETENSIÓN ESCALONADA", table=[
            ("Escenario", "Remedio legal preliminar", "Plazo operativo de referencia"),
            ("Bien reparable, primera falla", "Reparación totalmente gratuita, transporte y repuestos", "30 días hábiles salvo término especial; hasta 60 con bien en préstamo"),
            ("Bien no reparable", "Reposición o devolución del dinero", "Reposición 10 días hábiles; devolución 15 días hábiles desde puesta a disposición"),
            ("Falla repetida", "A elección del consumidor: nueva reparación, cambio o devolución según naturaleza", "Dejar constancia escrita de la elección"),
            ("Servicio", "Prestación en condiciones contratadas o devolución, según el caso", "Respuesta motivada y ejecución verificable"),
        ]),
        section("5. SOLICITUDES", bullets=["Radicar y entregar constancia", "Recibir el bien sin cobros ni barreras indebidas", "Emitir diagnóstico técnico sustentado", "Responder la reclamación dentro de quince días hábiles", "Indicar remedio, plazo, lugar y responsable", "Entregar constancia de reparación con piezas y fechas", "Suspender la garantía durante la privación de uso", "Reconocer nuevo término cuando exista cambio total"]),
        section("6. PRUEBAS", bullets=["Factura, extracto u otro medio de prueba de compra", "Oferta, ficha técnica y publicidad", "Fotos, videos y registros de error", "Serial, accesorios y estado de entrega", "Constancias de reparación", "Comunicaciones y radicados", "Peritaje si la causa es controvertida"]),
        section("7. CUSTODIA Y SEGURIDAD", "El recibo debe registrar estado, accesorios, serial, embalaje y motivo. Si existe riesgo para salud o seguridad, se suspenderá el uso, se preservará evidencia y se evaluará la responsabilidad por producto defectuoso sin confundirla con la sola garantía legal."),
        section("8. RESERVA JURÍDICA", "No siempre procede exigir cambio o devolución en la primera reclamación de un bien reparable. La decisión depende de la naturaleza del producto, posibilidad de reparación, repetición de la falla, régimen especial y evidencia. La negativa debe ser escrita, sustentada y acompañada de pruebas."),
        signature(val(a,'consumer_name','DANIELA GÓMEZ SALAZAR'), "CONSUMIDORA"),
        control("CO-CD-003-GARANTÍA", assumptions=["Uso normal y reclamación dentro del término", "Bien disponible para inspección"], sources=["Ley 1480 de 2011, artículos 7 a 17 y 58", "Decreto 735 de 2013"], red_flags=["Daño a salud", "Producto alterado", "Bien inmueble", "Vehículo", "Servicio regulado", "Garantía vencida discutida"]),
    ]


def cd003_retract(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("EJERCICIO FORMAL DEL DERECHO DE RETRACTO", "Documento condicionado a la modalidad contractual, oportunidad, devolución y ausencia de excepción legal."),
        section("1. OPERACIÓN", table=[("Dato", "Información"), ("Consumidor", val(a,'consumer_name','DANIELA GÓMEZ SALAZAR')), ("Proveedor", val(a,'provider','COMERCIO DIGITAL EJEMPLO S.A.S.')), ("Producto/servicio", val(a,'purchase','Computador portátil')), ("Modalidad", val(a,'channel','Comercio electrónico')), ("Compra/contrato", val(a,'purchase_date','22 de julio de 2026')), ("Entrega/inicio", val(a,'delivery_date','23 de julio de 2026')), ("Radicación", val(a,'claim_date','24 de julio de 2026'))]),
        section("2. VERIFICACIÓN DE PROCEDENCIA", table=[
            ("Requisito", "Resultado preliminar", "Evidencia"),
            ("Modalidad del artículo 47", val(a,'included_mode','Sí, venta a distancia'), "Confirmación/pedido"),
            ("Cinco días hábiles", val(a,'within_retract','Sí'), "Cronología y calendario"),
            ("Ausencia de excepción", val(a,'not_excepted','Por verificar'), "Naturaleza del bien/servicio"),
            ("Producto disponible", val(a,'return_status','Disponible para devolución'), "Fotos, serial y ubicación"),
            ("Datos de reembolso", val(a,'refund_data_status','Completos'), "Medio de pago o acuerdo"),
        ]),
        section("3. EXCEPCIONES QUE DEBEN DESCARTARSE", bullets=["Servicio iniciado con acuerdo antes de vencer el término", "Bien o precio sujeto a fluctuaciones no controladas", "Bien confeccionado o personalizado", "Bien inseparablemente mezclado", "Apuesta o lotería", "Perecedero", "Bien de uso personal", "Otra excepción sectorial aplicable"]),
        section("4. DECLARACIÓN", "El consumidor ejerce de manera inequívoca el derecho de retracto y solicita resolver el contrato, sin que deba probar defecto o incumplimiento, siempre que se satisfagan los presupuestos legales."),
        section("5. DEVOLUCIÓN DEL BIEN", "El consumidor devolverá el producto por los mismos medios y en condiciones razonables, asumiendo los costos de transporte cuando así lo dispone la ley. El proveedor debe informar instrucciones claras y no imponer exigencias que hagan imposible el derecho."),
        section("6. DEVOLUCIÓN DEL DINERO", "El proveedor debe reintegrar las sumas pagadas sin descuentos indebidos. Conforme a la Ley 2439 de 2024 y a la Sentencia C-192 de 2026, el término máximo de quince (15) días calendario aplica uniformemente a las modalidades del artículo 47, una vez el consumidor suministre la información completa y cumpla la devolución cuando corresponda."),
        section("7. MEDIO DE PAGO", "La devolución debe aplicarse al instrumento o medio de pago correspondiente o al medio acordado. El proveedor debe explicar las opciones de manera clara, detallada y específica; todos los actores, incluida la entidad financiera, están sujetos al término aplicable."),
        section("8. SOLICITUDES", bullets=["Confirmar recepción y procedencia", "Remitir guía o instrucciones de devolución", "Registrar estado y accesorios", "Reintegrar todas las sumas dentro del término", "Corregir financiación o cobros asociados", "Expedir constancia de cierre"]),
        signature(val(a,'consumer_name','DANIELA GÓMEZ SALAZAR'), "CONSUMIDORA"),
        control("CO-CD-003-RETRACTO", assumptions=["Término oportuno", "Modalidad incluida", "No existe excepción"], sources=["Ley 1480 de 2011, artículo 47", "Ley 2439 de 2024", "Sentencia C-192 de 2026"], red_flags=["Bien personalizado", "Servicio ejecutado", "Perecedero", "Uso personal", "Término vencido", "Financiación externa no coordinada"]),
    ]


def cd003_reversal(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD COORDINADA DE REVERSIÓN DEL PAGO", "La queja al proveedor y la notificación al emisor deben prepararse de forma consistente y oportuna."),
        section("1. OPERACIÓN", table=[("Transacción", val(a,'transaction','TX-2026-77881')), ("Fecha", val(a,'purchase_date','22 de julio de 2026')), ("Valor", money(a.get('amount'),4_850_000)), ("Instrumento", val(a,'payment_method','Tarjeta de crédito terminada en 4421')), ("Canal", val(a,'channel','Comercio electrónico')), ("Causal", val(a,'reversal_cause','Producto defectuoso y diferente al solicitado'))]),
        section("2. PRESUPUESTOS", table=[
            ("Control", "Resultado preliminar"),
            ("Comercio electrónico", val(a,'electronic_commerce','Sí')),
            ("Pago electrónico", val(a,'electronic_payment','Sí')),
            ("Participantes domiciliados en Colombia", val(a,'colombia_participants','Por verificar')),
            ("Causal taxativa", val(a,'reversal_cause','Producto defectuoso y diferente al solicitado')),
            ("Dentro de cinco días hábiles", val(a,'within_reversal','Sí')),
            ("Producto devuelto o disponible", val(a,'return_status','Disponible para recogida')),
        ]),
        section("3. CAUSALES", bullets=["Fraude", "Operación no solicitada", "Producto no recibido", "Producto diferente al solicitado", "Producto defectuoso"]),
        section("4. QUEJA AL PROVEEDOR", bullets=["Manifestación expresa de la causal", "Fecha de conocimiento o incumplimiento", "Valor e identificación de transacción", "Instrumento de pago", "Devolución o disponibilidad del producto cuando proceda", "Dirección o canal para recogerlo", "Solicitud de constancia de radicación"]),
        section("5. NOTIFICACIÓN AL EMISOR", bullets=["La misma causal, hechos y valor", "Identificación de la cuenta o instrumento", "Constancia de queja al proveedor", "Manifestación de devolución o disponibilidad", "Documentos adicionales razonablemente exigibles"]),
        section("6. TÉRMINO Y EFECTO", "Las actuaciones deben realizarse dentro de cinco (5) días hábiles desde el conocimiento de la operación fraudulenta o no solicitada, la fecha en que debió recibirse el producto o la recepción defectuosa/diferente. Los participantes disponen del término reglamentario para hacer efectiva la reversión."),
        section("7. PAGOS PERIÓDICOS", "En débitos automáticos debe distinguirse la revocación de la autorización para cargos futuros de la reversión de un pago ya efectuado. La solicitud de reversión de obligaciones periódicas tiene reglas particulares y no sustituye la cancelación contractual del servicio."),
        section("8. CONTROVERSIA Y RECARGA", "La reversión no decide definitivamente el conflicto de consumo. Si una decisión administrativa o jurisdiccional concluye que no procedía, la transacción puede cargarse nuevamente. El proveedor y el emisor deben informar esta posibilidad."),
        section("9. BUENA FE Y NO DUPLICIDAD", "Toda manifestación debe ser verdadera, completa y verificable. La aplicación bloqueará pretensiones que produzcan doble reembolso y advertirá que la mala fe puede generar sanciones."),
        signature(val(a,'consumer_name','DANIELA GÓMEZ SALAZAR'), "CONSUMIDORA"),
        control("CO-CD-003-REVERSIÓN", assumptions=["Comercio electrónico y pago electrónico", "Causal taxativa", "Participantes bajo régimen colombiano"], sources=["Ley 1480 de 2011, artículo 51", "Decreto 587 de 2016 compilado en Decreto 1074 de 2015"], red_flags=["Canal presencial", "Plazo vencido", "Doble reembolso", "Proveedor o emisor extranjero", "Fraude complejo", "Regulación sectorial especial"]),
    ]


def cd003_ecommerce(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("TERMINACIÓN POR NO ENTREGA O INDISPONIBILIDAD EN COMERCIO ELECTRÓNICO", "Ruta diferente del retracto y de la garantía, aplicable cuando el proveedor incumple la entrega o informa indisponibilidad."),
        section("1. PEDIDO", table=[("Proveedor", val(a,'provider','COMERCIO DIGITAL EJEMPLO S.A.S.')), ("Pedido", val(a,'order','PED-2026-44881')), ("Producto", val(a,'purchase','Computador portátil')), ("Fecha", val(a,'purchase_date','22 de julio de 2026')), ("Plazo informado", val(a,'promised_delivery','25 de julio de 2026')), ("Estado", val(a,'delivery_status','No entregado'))]),
        section("2. REGLA DE ENTREGA", "El proveedor debe informar antes de terminar la transacción el plazo aceptado por el consumidor. Si no se pactó plazo, la entrega debe realizarse a más tardar dentro de treinta (30) días calendario desde el día siguiente a la comunicación del pedido."),
        section("3. INDISPONIBILIDAD", "Si el producto no está disponible, el proveedor y, cuando corresponda, el portal de contacto deben informar de forma inmediata. Una segunda fecha solo debe operar con solicitud o aceptación real del consumidor, sin convertirla en prórroga unilateral."),
        section("4. TERMINACIÓN", "Cuando la entrega exceda el plazo pactado o los treinta días calendario, o no exista disponibilidad, el consumidor puede terminar unilateralmente el contrato y solicitar devolución total sin retenciones ni descuentos."),
        section("5. DEVOLUCIÓN", "La devolución debe hacerse efectiva en un plazo máximo de quince (15) días calendario y por el medio de pago preferido por el consumidor, conforme a la regulación vigente y sin perjuicio de coordinación con entidades financieras."),
        section("6. SOLICITUDES", bullets=["Confirmar la terminación", "Detener despacho y cobros", "Devolver precio, transporte y cargos asociados procedentes", "Corregir financiación y facturación", "Entregar soporte de reverso o devolución", "Eliminar autorizaciones de cobro no necesarias"]),
        section("7. EVIDENCIA", bullets=["Confirmación del pedido", "Plazo ofrecido", "Capturas del estado", "Comunicaciones de indisponibilidad", "Extracto o comprobante", "Radicado de terminación", "Soporte de devolución"]),
        signature(val(a,'consumer_name','DANIELA GÓMEZ SALAZAR'), "CONSUMIDORA"),
        control("CO-CD-003-ENTREGA", assumptions=["Operación de comercio electrónico", "Proveedor ubicado o sujeto al régimen colombiano"], sources=["Ley 1480 de 2011, artículo 50", "Ley 2439 de 2024"], red_flags=["Marketplace extranjero", "Entrega parcial", "Bien personalizado", "Fuerza mayor alegada", "Financiación separada"]),
    ]


def cd003_sic(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("EXPEDIENTE DE RECLAMACIÓN DIRECTA Y ESCALAMIENTO ANTE LA SIC", "Guía para diferenciar reclamación directa, SIC Facilita, denuncia administrativa y acción jurisdiccional de protección al consumidor."),
        section("1. RECLAMACIÓN DIRECTA", table=[("Radicado", val(a,'claim_number','RC-2026-115')), ("Fecha", val(a,'claim_date','24 de julio de 2026')), ("Pretensión", val(a,'claim_request','Garantía o devolución según diagnóstico')), ("Respuesta", val(a,'claim_response','Negativa genérica')), ("Vencimiento", val(a,'claim_due','Pendiente de calendario oficial'))]),
        section("2. REQUISITOS PROBATORIOS", bullets=["Identidad y datos de contacto", "Identificación del proveedor/productor", "Prueba de compra por cualquier medio idóneo", "Oferta y condiciones", "Cronología", "Reclamación directa y constancia", "Respuesta o silencio", "Cuantificación sin duplicidad"]),
        section("3. RUTAS", table=[
            ("Ruta", "Finalidad", "Resultado posible"),
            ("SIC Facilita", "Mediación voluntaria", "Acuerdo entre consumidor y proveedor"),
            ("Denuncia administrativa", "Protección del interés general y cumplimiento", "Investigación y sanción; no necesariamente indemnización individual"),
            ("Acción de protección al consumidor", "Pretensión individual", "Orden de garantía, devolución, cumplimiento u otras consecuencias legales"),
            ("Jurisdicción/autoridad especial", "Sectores con competencia propia", "Trámite conforme al régimen aplicable"),
        ]),
        section("4. RECLAMACIÓN PREVIA", "Antes de la acción jurisdiccional debe acreditarse la reclamación directa en los términos legales. Como regla procesal, el proveedor debe responder dentro de quince (15) días hábiles; la respuesta debe ser escrita, sustentada y congruente."),
        section("5. PRETENSIONES", bullets=["Declarar incumplimiento cuando proceda", "Ordenar efectividad de garantía", "Aceptar retracto o terminación", "Devolver sumas pagadas", "Corregir cobros o financiación", "Reconocer perjuicios únicamente cuando sean procedentes y probados", "Imponer costas o sanciones solo en el marco competente"]),
        section("6. COMPETENCIA Y REPRESENTACIÓN", "La plataforma no debe elegir automáticamente la autoridad. Debe revisar cuantía, territorialidad, sector, cláusula arbitral, legitimación, términos y necesidad de abogado o representación."),
        section("7. RIESGOS", bullets=["Proveedor extranjero o portal de contacto", "Producto defectuoso con daño corporal", "Peritaje técnico", "Prescripción o caducidad", "Proceso colectivo", "Cláusulas abusivas", "Publicidad engañosa", "Datos personales o fraude"]),
        control("CO-CD-003-SIC", assumptions=["Reclamación directa agotada cuando se exige", "Pretensión y autoridad diferenciadas"], sources=["Ley 1480 de 2011, artículo 58", "Decreto 735 de 2013", "Orientación oficial SIC"], red_flags=["Demanda", "Medida cautelar", "Daño a salud", "Cuantía alta", "Proveedor extranjero", "Régimen especial"]),
    ]


def cd003_evidence(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ DE EVIDENCIA, TÉRMINOS, CUSTODIA Y NO DUPLICIDAD", "Control transversal del mecanismo elegido y de las actuaciones compatibles."),
        section("1. MATRIZ DE EVIDENCIA", table=[
            ("Evidencia", "Estado", "Finalidad", "Integridad"),
            ("Factura/extracto", "Aportada", "Compra y valor", "Conservar original"),
            ("Oferta/publicidad", "Aportada", "Calidad y condiciones", "Captura con fecha/URL"),
            ("Fotos/video", "Aportada", "Defecto o diferencia", "Archivo original y metadatos"),
            ("Serial/accesorios", "Aportado", "Identidad y custodia", "Acta de entrega"),
            ("Queja/reclamación", "Aportada", "Oportunidad y pretensiones", "Radicado/acuse"),
            ("Extracto de pago", "Aportado", "Instrumento y transacción", "Ocultar datos no necesarios"),
            ("Guía de devolución", "Pendiente", "Disponibilidad y entrega", "Trazabilidad logística"),
            ("Diagnóstico técnico", "Pendiente", "Causa y reparabilidad", "Autor e independencia"),
        ]),
        section("2. CALENDARIO DE EJEMPLO", table=[
            ("Hito", "Fecha", "Regla", "Resultado preliminar"),
            ("Compra", val(a,'purchase_date','22/07/2026'), "Base documental", "Registrada"),
            ("Entrega", val(a,'delivery_date','23/07/2026'), "Inicio garantía/retracto del bien", "Registrada"),
            ("Conocimiento causal", val(a,'cause_date','23/07/2026'), "Base reversión", "Registrada"),
            ("Retracto/reversión", val(a,'claim_date','24/07/2026'), "Cinco días hábiles", "Preliminarmente oportuno"),
            ("Respuesta directa", val(a,'direct_response_due','Pendiente'), "Quince días hábiles", "Calcular con calendario oficial"),
            ("Reembolso retracto", val(a,'retract_refund_due','Pendiente'), "Quince días calendario desde cumplimiento", "Controlar hito completo"),
            ("Reparación", val(a,'repair_due','Pendiente'), "Treinta días hábiles, salvo excepción", "Depende de entrega del bien"),
        ]),
        section("3. CUSTODIA", "Registrar serial, estado, accesorios, embalaje, uso posterior, ubicación y disponibilidad. Toda entrega o recogida debe constar en acta o guía. No autorizar destrucción, reparación por terceros o manipulación que comprometa la prueba sin evaluación."),
        section("4. NO DUPLICIDAD", table=[("Situación", "Control"), ("Proveedor devolvió el precio", "Cerrar o ajustar reversión y pretensiones"), ("Emisor reversó provisionalmente", "Informar al proveedor y evitar segunda devolución"), ("Cambio del bien", "Registrar nueva garantía y cerrar pretensión incompatible"), ("Reparación aceptada", "Mantener reserva sobre repetición, no exigir simultáneamente devolución")]),
        section("5. DATOS Y SEGURIDAD", bullets=["Minimizar datos de tarjeta y documento", "Ocultar códigos de seguridad", "Separar evidencia médica o sensible", "Controlar acceso por rol", "Registrar descargas y entregas", "Cifrar soportes y eliminar copias temporales"]),
        section("6. ALERTAS", bullets=["Festivos no incorporados", "Hito de inicio incierto", "Producto perdido o alterado", "Uso intensivo posterior", "Devolución sin constancia", "Proveedor y emisor extranjeros", "Doble devolución", "Daño corporal"]),
        control("CO-CD-003-MATRIZ", assumptions=["Fechas verificadas", "Calendario oficial aplicable identificado"], sources=["Ley 1480 de 2011", "Ley 2439 de 2024", "Decretos 735 de 2013 y 587 de 2016"], red_flags=["Plazo próximo", "Evidencia incompleta", "Producto alterado", "Doble recuperación", "Datos financieros expuestos"]),
    ]


# ---------------------------------------------------------------------------
# CO-CD-004 - COBRO, ACUERDO, PAGARÉ, GARANTÍAS Y CIERRE
# ---------------------------------------------------------------------------

def cd004_diagnostic(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("DIAGNÓSTICO INTEGRAL DE CARTERA Y RUTA DE RECUPERACIÓN", f"Acreedor: {val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')}. Deudor: {val(a,'debtor','DISTRIBUCIONES DEL CENTRO S.A.S.')}. Corte de análisis: {val(a,'cutoff','31 de julio de 2026')}"),
        section("1. IDENTIFICACIÓN DE LA OBLIGACIÓN", table=[
            ("Elemento", "Dato de trabajo", "Control de liberación"),
            ("Origen", val(a,'origin','Suministro de mercancías'), "Contrato, orden, factura, entrega y aceptación deben ser coherentes"),
            ("Capital original", money(a.get('principal'),48_000_000), "Conciliar contra contabilidad, pagos y notas crédito"),
            ("Vencimiento", val(a,'due_date','30 de junio de 2026'), "Confirmar exigibilidad y ausencia de condición pendiente"),
            ("Soporte principal", val(a,'support','Contrato, facturas y actas'), "Verificar original, integridad, firma o atribución"),
            ("Garantía", val(a,'security','Pagaré sujeto a validación'), "No usar título en blanco sin instrucciones específicas"),
        ]),
        section("2. PRUEBA DE EXISTENCIA, CLARIDAD Y EXIGIBILIDAD", bullets=[
            "Individualizar acreedor, deudor, representación y cadena de cesiones o endosos.",
            "Reconstruir prestación, entrega, aceptación, incumplimiento, vencimiento, pagos, devoluciones y compensaciones.",
            "Distinguir documento probatorio, título valor y título ejecutivo; un estado de cuenta unilateral no crea por sí solo exigibilidad ejecutiva.",
            "Verificar prescripción o caducidad según la acción, el título y cualquier interrupción, suspensión o renuncia jurídicamente eficaz.",
            "Identificar procesos judiciales, medidas, conciliaciones, reorganización, insolvencia o liquidación que modifiquen la ruta de cobro.",
        ]),
        section("3. CLASIFICACIÓN DE RIESGO Y RUTA", table=[
            ("Escenario", "Indicadores", "Ruta permitida"),
            ("Preventivo", "Obligación no vencida", "Recordatorio no intimidatorio y confirmación de datos"),
            ("Prejurídico", "Mora, saldo conciliable y ausencia de disputa seria", "Requerimiento, estado de cuenta y negociación"),
            ("Disputado", "Objeción de calidad, entrega, pago, identidad o tasa", "Conciliación probatoria; no afirmar saldo definitivo"),
            ("Título valor", "Pagaré o factura con requisitos y trazabilidad", "Validación especializada antes de acción cambiaria o ejecutiva"),
            ("Insolvencia", "Solicitud admitida, negociación, reorganización o liquidación", "Suspender actuaciones incompatibles y comparecer al proceso"),
            ("Judicial", "Proceso, embargo, mandamiento o sentencia", "Abogado responsable; no automatizar estrategia ni medidas"),
        ]),
        section("4. INTERESES, GASTOS Y SANCIONES", "Toda liquidación debe identificar capital, tasa, modalidad, periodicidad, periodo, fórmula, pagos imputados y certificado vigente de la Superintendencia Financiera. No se cobrarán intereses no pactados o improcedentes, capitalización no autorizada, honorarios automáticos, gastos no causados ni conceptos que superen límites civiles, comerciales o penales."),
        section("5. COBRANZA, PRIVACIDAD Y REPORTE", bullets=[
            "Definir si el deudor es consumidor y aplicar canales autorizados, horarios, periodicidad y prohibición de contacto a terceros.",
            "No anunciar embargos, denuncias, reportes o procesos inexistentes; diferenciar alternativa de pago de presión indebida.",
            "Si se proyecta reporte negativo, verificar finalidad, exactitud, comunicación previa, espera legal, baja cuantía y régimen temporal aplicable.",
            "Minimizar datos personales, restringir accesos y conservar trazabilidad de cada contacto, descarga, modificación y entrega.",
        ]),
        section("6. DECISIÓN PRELIMINAR", "La ruta recomendada es documentar el saldo, separar lo no controvertido de lo disputado, realizar cobranza respetuosa y ofrecer una negociación verificable. La demanda, el diligenciamiento de un título, la ejecución de garantías o la actuación en insolvencia requieren revisión jurídica específica."),
        control("CO-CD-004-DIAGNOSTICO-M20", assumptions=["Obligación civil o mercantil documentada", "Datos y fechas de ejemplo sujetos a verificación"], sources=["Código Civil", "Código de Comercio", "Código General del Proceso", "Ley 2300 de 2023", "Ley 2445 de 2025"], red_flags=["Prescripción", "Insolvencia", "Interés excesivo", "Firma o título dudoso", "Cobro a tercero", "Proceso activo"]),
    ]


def cd004_statement(a: dict[str, Any]) -> list[dict[str, Any]]:
    principal = int(a.get('principal',48_000_000)); payments=int(a.get('payments',8_000_000)); balance=max(principal-payments,0)
    return [
        section("ESTADO DE CUENTA CONCILIABLE Y MEMORIA DE LIQUIDACIÓN", "Documento técnico de reconstrucción. No constituye aceptación del deudor ni crea por sí solo título ejecutivo."),
        section("1. MOVIMIENTOS Y SOPORTES", table=[
            ("Fecha", "Documento", "Concepto", "Débito", "Crédito", "Saldo"),
            ("01/04/2026", "Factura F-101", "Mercancía lote 1", money(30_000_000), money(0), money(30_000_000)),
            ("15/05/2026", "Factura F-118", "Mercancía lote 2", money(18_000_000), money(0), money(48_000_000)),
            ("20/06/2026", "Pago P-01", "Abono confirmado", money(0), money(payments), money(balance)),
        ]),
        section("2. RECONCILIACIÓN", table=[
            ("Concepto", "Valor preliminar", "Soporte obligatorio", "Estado"),
            ("Capital facturado", money(principal), "Factura y negocio causal", "Por confirmar"),
            ("Abonos", money(payments), "Extracto y recibo", "Confirmado en ejemplo"),
            ("Notas, devoluciones o compensaciones", money(a.get('credits'),0), "Nota crédito, acta o acuerdo", "Por verificar"),
            ("Saldo capital", money(balance), "Conciliación de movimientos", "Preliminar"),
            ("Intereses", "No incorporados automáticamente", "Pacto, modalidad, certificado y fórmula", "Pendiente"),
            ("Gastos no automáticos", "No incorporados automáticamente", "Causación, pacto y procedencia", "Pendiente"),
        ]),
        section("3. MEMORIA DE INTERESES", bullets=[
            "Seleccionar la modalidad crediticia correcta; no usar por defecto consumo y ordinario si la operación corresponde a otra modalidad.",
            "Convertir la tasa a efectiva anual de manera reproducible y compararla con el límite vigente para cada periodo.",
            "Liquidar por días o periodos definidos, sobre la base jurídicamente procedente y descontando pagos en la fecha real.",
            "Separar interés remuneratorio y moratorio; no duplicarlos sobre el mismo periodo sin fundamento.",
            "No capitalizar intereses salvo habilitación jurídica y factual; documentar cualquier imputación contractual o legal.",
        ]),
        section("4. OBJECIONES Y PARTIDAS EN DISCUSIÓN", table=[
            ("Partida", "Objeción", "Prueba pendiente", "Tratamiento"),
            ("Factura F-118", "Calidad del lote 2", "Informe técnico y comunicaciones", "Excluir de afirmación definitiva hasta resolver"),
            ("Intereses", "Tasa y periodo", "Contrato y resolución SFC", "Liquidar solo tras verificación"),
            ("Gastos de cobranza", "Causación", "Factura y pacto", "No sumar automáticamente"),
        ]),
        section("5. CERTIFICACIÓN Y CONTRADICCIÓN", "El responsable contable o autorizado debe identificar el sistema fuente, fecha de corte y documentos utilizados. El deudor recibirá el detalle suficiente para aceptar, objetar o proponer ajustes. Toda modificación conservará versión, autor, fecha y motivo."),
        control("CO-CD-004-ESTADO-M20", assumptions=["Movimientos de ejemplo", "No existen partidas omitidas"], sources=["Código Civil", "Código de Comercio artículo 884", "Resolución SFC 0965 de 2026"], red_flags=["Saldo sin soporte", "Doble cobro", "Tasa vencida", "Pago no imputado", "Capitalización irregular"]),
    ]


def cd004_collection(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("REQUERIMIENTO PREJURÍDICO Y PROPUESTA DE SOLUCIÓN", f"Señores {val(a,'debtor','DISTRIBUCIONES DEL CENTRO S.A.S.')}: esta comunicación busca verificar y solucionar la obligación identificada, sin anunciar medidas inexistentes ni desconocer objeciones documentadas."),
        section("1. INFORMACIÓN DE LA OBLIGACIÓN", table=[
            ("Concepto", "Dato"), ("Acreedor", val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')), ("Documento", val(a,'document_reference','Contrato y facturas F-101/F-118')), ("Capital", money(a.get('principal'),48_000_000)), ("Abonos", money(a.get('payments'),8_000_000)), ("Saldo preliminar", money(int(a.get('principal',48_000_000))-int(a.get('payments',8_000_000)))), ("Corte", val(a,'cutoff','31 de julio de 2026')),
        ]),
        section("2. DOCUMENTOS DISPONIBLES", bullets=["Contrato, orden o aceptación", "Facturas y eventos electrónicos", "Actas de entrega o prestación", "Estado de cuenta detallado", "Pagos, notas crédito y compensaciones", "Comunicaciones y objeciones", "Garantías, si existen"]),
        section("3. SOLICITUD Y ALTERNATIVAS", bullets=[
            "Pagar el saldo no controvertido mediante el canal verificado indicado por el acreedor.",
            "Presentar objeciones concretas y soportes para conciliar las partidas discutidas.",
            "Proponer un acuerdo realista con cuota inicial, calendario, fuente de pago y garantías proporcionadas.",
            "Informar inmediatamente si existe proceso de insolvencia, reorganización, liquidación, embargo o demanda relacionada.",
        ]),
        section("4. PROTOCOLO DE CONTACTO", table=[
            ("Control", "Regla operativa"),
            ("Canales autorizados", "Usar únicamente los autorizados por el consumidor cuando la Ley 2300 resulte aplicable"),
            ("Periodicidad", "Después de contacto directo, no varios canales en la misma semana ni más de una ocasión el mismo día"),
            ("Horario", "Lunes a viernes 7:00 a. m.-7:00 p. m.; sábados 8:00 a. m.-3:00 p. m.; no domingos ni festivos"),
            ("Terceros", "No contactar referencias, familiares o empleadores para revelar o cobrar la deuda"),
            ("Contenido", "Trato respetuoso, información veraz y prohibición de amenazas o medidas simuladas"),
        ]),
        section("5. PLAZO PROPUESTO", f"Se solicita respuesta antes del {val(a,'response_date','12 de agosto de 2026')}. Este plazo de negociación no modifica la prescripción, términos procesales, vencimiento ni derechos de las partes."),
        section("6. DATOS Y SEGURIDAD", "Verifique la cuenta bancaria por un segundo canal. No comparta claves, códigos de autenticación ni datos completos de tarjetas. Las respuestas y anexos serán tratados con acceso mínimo, finalidad de gestión de cartera y trazabilidad."),
        signature(val(a,'creditor_representative','LAURA RESTREPO'), "REPRESENTANTE O APODERADO DEL ACREEDOR"),
        control("CO-CD-004-COBRO-M20", assumptions=["Saldo preliminarmente conciliado", "Canal legítimo"], sources=["Ley 2300 de 2023", "Sentencia C-278 de 2024", "Ley 1266 de 2008"], red_flags=["Hostigamiento", "Contacto a tercero", "Horario prohibido", "Amenaza de embargo", "Suplantación bancaria", "Deudor insolvente"]),
    ]


def cd004_agreement(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ACUERDO INTEGRAL DE PAGO", "Modelo civil o mercantil sujeto a validación de capacidad, saldo, tasa, garantías, insolvencia y efectos sobre obligaciones o títulos anteriores."),
        section("PRIMERA: PARTES, CAPACIDAD Y ANTECEDENTES", f"Comparecen {val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')} como acreedor y {val(a,'debtor','DISTRIBUCIONES DEL CENTRO S.A.S.')} como deudor. Cada parte declara capacidad y representación suficientes, sin perjuicio de la verificación documental anexa."),
        section("SEGUNDA: OBLIGACIÓN Y RECONOCIMIENTO DELIMITADO", f"El deudor reconoce, únicamente con el alcance de la conciliación anexa, un saldo inicial de {money(a.get('agreement_balance'),40_000_000)}. No se entienden reconocidos conceptos no individualizados, intereses no liquidados, gastos no causados ni partidas expresamente reservadas."),
        section("TERCERA: NOVACIÓN Y RESERVAS", "El acuerdo no produce novación salvo declaración expresa, inequívoca y jurídicamente válida. Se identificará qué obligaciones, títulos y garantías continúan, se modifican, sustituyen o extinguen. Las reservas concretas deberán quedar escritas en anexo."),
        section("CUARTA: PLAN DE PAGOS", table=[
            ("Cuota", "Fecha", "Capital", "Interés", "Total", "Saldo capital"),
            ("1", "15/08/2026", money(10_000_000), money(0), money(10_000_000), money(30_000_000)),
            ("2", "15/09/2026", money(10_000_000), money(0), money(10_000_000), money(20_000_000)),
            ("3", "15/10/2026", money(10_000_000), money(0), money(10_000_000), money(10_000_000)),
            ("4", "15/11/2026", money(10_000_000), money(0), money(10_000_000), money(0)),
        ]),
        section("QUINTA: INTERESES, IMPUTACIÓN Y PAGOS", bullets=[
            "La tasa, periodicidad, modalidad y vigencia deberán constar expresamente y respetar el límite aplicable en cada periodo.",
            "Cada recibo indicará fecha, valor, canal, imputación a capital/interés/gasto y saldo posterior.",
            "La imputación no podrá ocultar capitalización o cobro duplicado y deberá armonizarse con la ley y el pacto válido.",
            "Los datos bancarios solo se modificarán mediante procedimiento de doble verificación." ]),
        section("SEXTA: MORA, CURA Y ACELERACIÓN", "La mora y una eventual aceleración se configurarán solo bajo hechos precisos. Antes de acelerar se otorgará el periodo de cura pactado, salvo excepción jurídicamente justificada. La cláusula no permite cobrar valores no vencidos, intereses por fuera del límite ni anunciar ejecución automática sin control judicial."),
        section("SÉPTIMA: GARANTÍAS", "Toda garantía personal, mobiliaria, real o título valor se describirá por separado, con otorgante, alcance, monto máximo, vigencia, eventos de ejecución, custodia y cancelación. Las garantías reales, mobiliarias registradas, fiducias o conflictos con garantes exigen revisión especializada."),
        section("OCTAVA: COBRANZA, DATOS Y REPORTES", "Las gestiones respetarán canales, horarios, periodicidad, intimidad y minimización. Los reportes a operadores de información solo procederán con fuente, exactitud, comunicación previa y términos aplicables. El pago o acuerdo se actualizará conforme al régimen vigente."),
        section("NOVENA: INSOLVENCIA Y PROCESOS", "La parte que conozca una solicitud o admisión a insolvencia, reorganización o liquidación lo informará. No producirán efecto las estipulaciones que obstaculicen indebidamente el régimen concursal o aceleren por la sola admisión cuando la ley lo prohíba."),
        section("DÉCIMA: MODIFICACIONES, SOLUCIÓN Y CIERRE", "Toda modificación será escrita y trazable. Las controversias podrán someterse a negociación o conciliación sin impedir medidas urgentes. Cumplido el acuerdo, el acreedor emitirá cierre, actualizará reportes y devolverá o cancelará garantías; si subsisten partidas, expedirá constancia parcial, no paz y salvo total."),
        {"heading": "FIRMA", "_type": "signature", "parties": [{"label": "ACREEDOR", "name": val(a,'creditor_representative','LAURA RESTREPO')}, {"label": "DEUDOR", "name": val(a,'debtor_representative','MIGUEL TORRES')}]},
        control("CO-CD-004-ACUERDO-M20", assumptions=["Consentimiento libre", "Saldo conciliado", "No existe prohibición concursal"], sources=["Código Civil", "Código de Comercio", "Ley 2300 de 2023", "Ley 2445 de 2025"], red_flags=["Novación ambigua", "Aceleración abusiva", "Garantía real", "Avalista no informado", "Insolvencia", "Tasa excesiva"]),
    ]


def cd004_note(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("PAGARÉ DILIGENCIADO - MODELO CONTROLADO", "Este instrumento solo debe suscribirse cuando el negocio causal, el saldo, la representación, la forma de vencimiento y la tasa estén determinados. No sustituye la carta de instrucciones cuando existan espacios por completar."),
        section("1. PROMESA", f"Yo, {val(a,'debtor','DISTRIBUCIONES DEL CENTRO S.A.S.')}, identificado y representado como consta al pie de mi firma, prometo pagar incondicionalmente a la orden de {val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')} la suma de {money(a.get('note_amount'),40_000_000)}, en el lugar y fecha de vencimiento indicados en este documento."),
        section("2. REQUISITOS Y DATOS", table=[
            ("Elemento", "Contenido controlado"),
            ("Derecho incorporado", "Pago de suma determinada de dinero"),
            ("Beneficiario", val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')),
            ("Valor", money(a.get('note_amount'),40_000_000)),
            ("Vencimiento", val(a,'note_due_date','15 de noviembre de 2026')),
            ("Lugar de pago", val(a,'payment_place','Medellín, Antioquia')),
            ("Firma", "Autógrafa o electrónica atribuible y verificable"),
        ]),
        section("3. INTERESES", "Cualquier interés deberá identificar clase, tasa, periodicidad y vigencia, y nunca superar el límite aplicable. Si no se incorpora una tasa válida, no se completará posteriormente por decisión unilateral fuera de las instrucciones."),
        section("4. PAGOS PARCIALES Y SALDO", "Todo pago se anotará o registrará de manera trazable y reducirá el saldo. El tenedor conservará estado de cuenta actualizado y no podrá presentar el pagaré por un valor superior al realmente adeudado."),
        section("5. ENDOSO, CUSTODIA Y COPIA", "Se entregará copia íntegra al suscriptor. La custodia, transferencias, endosos, pagos y cancelación quedarán registrados. El cesionario o tenedor deberá respetar defensas, instrucciones y datos aplicables conforme al régimen jurídico del caso."),
        section("6. CANCELACIÓN", "Al pago total o extinción, el tenedor devolverá el original o dejará constancia verificable de su cancelación e inutilización. Si el documento es electrónico, bloqueará su circulación y conservará evidencia de cierre."),
        signature(val(a,'debtor_representative','MIGUEL TORRES'), "SUSCRIPTOR"),
        control("CO-CD-004-PAGARE-M20", assumptions=["Suma y vencimiento determinados", "Negocio causal válido"], sources=["Código de Comercio artículos 619, 621, 622 y 709 a 711", "Ley 527 de 1999"], red_flags=["Espacios en blanco", "Firma dudosa", "Valor superior al saldo", "Endoso no trazado", "Vencimiento indefinido"]),
    ]


def cd004_instructions(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("CARTA DE INSTRUCCIONES PARA DILIGENCIAMIENTO DE PAGARÉ", "Las instrucciones son específicas, verificables y limitadas. No autorizan al tenedor a crear obligaciones, alterar firmas, exceder el saldo real ni desconocer pagos, excepciones o límites de interés."),
        section("1. DOCUMENTO VINCULADO", table=[("Campo", "Dato"), ("Suscriptor", val(a,'debtor','DISTRIBUCIONES DEL CENTRO S.A.S.')), ("Beneficiario inicial", val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')), ("Negocio causal", val(a,'origin','Contrato de suministro y acuerdo de pago')), ("Identificador", val(a,'note_reference','PAG-M20-001')), ("Fecha de entrega", val(a,'note_delivery_date','31 de julio de 2026'))]),
        section("2. EVENTO HABILITANTE", "El pagaré solo podrá diligenciarse ante incumplimiento cierto de una obligación vencida y exigible, después del periodo de cura pactado y previa conciliación de pagos, notas, compensaciones y partidas controvertidas. La sola dificultad económica, un reporte interno o la admisión a insolvencia no habilitan automáticamente el diligenciamiento cuando la ley lo impida."),
        section("3. CAMPOS Y LÍMITES", table=[
            ("Campo", "Instrucción", "Límite"),
            ("Valor", "Saldo real de capital más intereses válidos y conceptos procedentes", "Nunca superior al estado de cuenta soportado"),
            ("Vencimiento", "Fecha posterior al incumplimiento y cura", "No antedatar ni crear mora retroactiva"),
            ("Intereses", "Tasa pactada y convertida", "Límite vigente por modalidad y periodo"),
            ("Lugar", "Domicilio o lugar pactado", "No alterar competencia de forma abusiva"),
            ("Beneficiario", "Tenedor legítimo con trazabilidad", "No incorporar terceros no legitimados"),
        ]),
        section("4. PROCEDIMIENTO DE DILIGENCIAMIENTO", bullets=[
            "Generar estado de cuenta de corte y memoria de intereses.",
            "Descontar pagos, compensaciones, devoluciones y notas crédito.",
            "Identificar partidas disputadas y excluir las no definidas cuando corresponda.",
            "Registrar usuario, fecha, motivo, campos completados y soportes.",
            "Enviar copia del pagaré diligenciado, estado de cuenta e instrucciones por canal verificable, sin afirmar que el aviso sustituye requisitos procesales." ]),
        section("5. CUSTODIA, MODIFICACIÓN Y CANCELACIÓN", "No se autoriza alterar estas instrucciones unilateralmente. Se conservarán junto con el pagaré, la prueba de entrega y cada versión. Pagada o extinguida la obligación, se devolverá, cancelará o inutilizará el título y se dejará evidencia."),
        {"heading": "FIRMA", "_type": "signature", "parties": [{"label": "OTORGANTE DE LAS INSTRUCCIONES", "name": val(a,'debtor_representative','MIGUEL TORRES')}, {"label": "RECIBE Y ACEPTA LOS LÍMITES", "name": val(a,'creditor_representative','LAURA RESTREPO')}]},
        control("CO-CD-004-INSTRUCCIONES-M20", assumptions=["Existencia de espacios autorizados", "Entrega conjunta con el pagaré"], sources=["Código de Comercio artículo 622", "Código General del Proceso", "Ley 527 de 1999"], red_flags=["Instrucciones genéricas", "Firma posterior", "Monto ilimitado", "Aviso inexistente", "Custodia no trazable"]),
    ]


def cd004_followup(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ DE EVIDENCIA, SEGUIMIENTO, PAGOS Y REPORTES", "Instrumento operativo para mantener un expediente íntegro y evitar cobros, contactos o reportes incompatibles con los hechos."),
        section("1. MATRIZ PROBATORIA", table=[
            ("Evidencia", "Responsable", "Estado", "Riesgo", "Control"),
            ("Contrato y representación", "Jurídico", "Aportado", "Legitimación", "Vigencia y facultades"),
            ("Facturas y RADIAN", "Cartera", "Parcial", "Título y aceptación", "Eventos y trazabilidad"),
            ("Entrega o servicio", "Operaciones", "Pendiente", "Negocio causal", "Acta, guía o aceptación"),
            ("Pagos y notas", "Contabilidad", "Aportado", "Saldo", "Conciliación bancaria"),
            ("Contactos", "Cartera", "En curso", "Ley 2300", "Canal, fecha, hora y resultado"),
            ("Reporte negativo", "Datos", "No iniciado", "Hábeas data", "Comunicación previa y exactitud"),
            ("Pagaré e instrucciones", "Custodio", "Por verificar", "Título valor", "Original, copias y campos"),
        ]),
        section("2. CRONOGRAMA Y RECIBOS", table=[
            ("Hito", "Fecha", "Valor", "Soporte", "Saldo posterior", "Estado"),
            ("Cuota 1", "15/08/2026", money(10_000_000), "Pendiente", money(30_000_000), "Programada"),
            ("Cuota 2", "15/09/2026", money(10_000_000), "Pendiente", money(20_000_000), "Programada"),
            ("Cuota 3", "15/10/2026", money(10_000_000), "Pendiente", money(10_000_000), "Programada"),
            ("Cuota 4", "15/11/2026", money(10_000_000), "Pendiente", money(0), "Programada"),
        ]),
        section("3. REGISTRO DE COBRANZA", table=[
            ("Fecha/hora", "Canal", "Autorizado", "Contacto directo", "Resultado", "Próxima acción"),
            ("31/07/2026 10:00", "Correo", "Sí", "Sí", "Requerimiento enviado", "Esperar respuesta; no otro canal esta semana"),
        ]),
        section("4. REPORTE A OPERADORES", bullets=[
            "Confirmar que la obligación y el saldo sean ciertos, completos, actualizados, comprobables y no estén sometidos a una disputa que impida el reporte.",
            "Conservar la comunicación previa y controlar el término de espera; para baja cuantía, verificar las comunicaciones adicionales aplicables.",
            "Registrar el acuerdo, pago, incumplimiento, extinción o reclamación de acuerdo con el régimen vigente y la fecha efectiva.",
            "No usar el reporte como amenaza o condición para recibir una reclamación." ]),
        section("5. ESCALAMIENTO", table=[
            ("Evento", "Acción"), ("Objeción documentada", "Suspender afirmación definitiva y conciliar prueba"), ("Canal o identidad dudosos", "Detener contacto y validar"), ("Incumplimiento del acuerdo", "Periodo de cura y revisión de aceleración"), ("Insolvencia", "Remitir a especialista y comparecer"), ("Título exigible", "Evaluar acción judicial con abogado"), ("Pago total", "Cerrar, actualizar reportes y cancelar garantías")]),
        section("6. SEGURIDAD Y AUDITORÍA", "Aplicar acceso por rol, cifrado, minimización, retención definida, control de descargas y registro inmutable de creación, revisión, aprobación, envío, pago, actualización y cierre."),
        control("CO-CD-004-SEGUIMIENTO-M20", assumptions=["Expediente único", "Roles autorizados"], sources=["Ley 2300 de 2023", "Leyes 1266 de 2008 y 2157 de 2021", "Ley 527 de 1999"], red_flags=["Contacto repetitivo", "Reporte sin aviso", "Pago no aplicado", "Pérdida del original", "Datos expuestos"]),
    ]


def cd004_closure(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ACTA DE CIERRE, PAZ Y SALVO Y CANCELACIÓN DE GARANTÍAS", "Este documento solo puede liberarse después de verificar saldo, pagos, intereses, gastos, títulos, garantías, procesos y reportes. Si la extinción es parcial, debe denominarse constancia parcial y expresar lo pendiente."),
        section("1. VERIFICACIÓN FINAL", table=[
            ("Control", "Resultado requerido", "Evidencia"),
            ("Capital", "Cero o valor expresamente condonado", "Estado de cuenta final"),
            ("Intereses", "Cero o acuerdo documentado", "Memoria de liquidación"),
            ("Gastos", "Cero o conceptos procedentes pagados", "Soportes"),
            ("Pagos", "Aplicados y conciliados", "Extractos y recibos"),
            ("Litigios", "Terminados, desistidos o identificados", "Providencia o memorial"),
            ("Reportes", "Actualizados o retirados cuando proceda", "Constancia del operador/fuente"),
            ("Garantías", "Devueltas, canceladas o liberadas", "Original, registro o certificado"),
        ]),
        section("2. DECLARACIÓN", f"Verificados los controles anteriores, {val(a,'creditor','COMERCIALIZADORA ANDINA S.A.S.')} declara que la obligación identificada se encuentra [TOTALMENTE PAGADA / EXTINTA POR LA CAUSA INDICADA]. Esta declaración no comprende obligaciones distintas que deberán individualizarse expresamente."),
        section("3. PAGARÉS Y TÍTULOS", "El acreedor devuelve el original cancelado o certifica su inutilización y bloqueo de circulación. Si existe título electrónico, deja constancia del evento de cancelación. No conservará un título activo después del pago total."),
        section("4. GARANTÍAS", "Se liberarán avales, codeudas, garantías mobiliarias, reales o depósitos únicamente mediante el acto, registro o entrega jurídicamente requeridos. La simple expedición del paz y salvo no reemplaza cancelaciones registrales."),
        section("5. REPORTES Y DATOS", "La fuente actualizará la información financiera dentro del régimen aplicable y conservará solo los datos necesarios por el término legal o probatorio. El titular podrá solicitar evidencia de actualización, sin que el paz y salvo implique borrado inmediato cuando exista permanencia legal."),
        section("6. RESERVAS Y CONSTANCIA PARCIAL", "Si subsiste una partida, litigio, garantía, gasto o reporte pendiente, el documento identificará exactamente su naturaleza, cuantía, responsable y plazo. Queda prohibido usar la expresión paz y salvo total en ese escenario."),
        section("7. TRAZABILIDAD", "Se adjuntan estado de cuenta final, relación de pagos, devolución o cancelación de títulos, liberación de garantías y constancias de reporte. La versión aprobada queda inmutable y vinculada al expediente."),
        {"heading": "FIRMA", "_type": "signature", "parties": [{"label": "ACREEDOR / RESPONSABLE DEL CIERRE", "name": val(a,'creditor_representative','LAURA RESTREPO')}, {"label": "DEUDOR / RECIBE CONSTANCIA", "name": val(a,'debtor_representative','MIGUEL TORRES')}]},
        control("CO-CD-004-CIERRE-M20", assumptions=["Saldo final verificado", "Ausencia de obligaciones omitidas"], sources=["Código Civil", "Código de Comercio", "Leyes 1266 y 2157", "Registros de garantías aplicables"], red_flags=["Saldo positivo", "Título activo", "Garantía sin cancelar", "Reporte desactualizado", "Proceso pendiente"]),
    ]


# ---------------------------------------------------------------------------
# CO-TR-001 - SAST
# ---------------------------------------------------------------------------

def tr001_control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO M14, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo M14.1 del producto {product}. Información jurídica verificada al 31 de julio de 2026. "
            "El resultado es una clasificación preliminar y trazable, no una declaración de nulidad, revocación, devolución, "
            "inexigibilidad ni responsabilidad de una autoridad. Deben verificarse el acto administrativo completo, su estado y firmeza, "
            "el régimen temporal aplicable, la autorización ANSV, el dispositivo y punto exactos, los criterios técnicos de operación, "
            "la evidencia del comparendo y la imputación personal antes de liberar una recomendación."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def tr001_report(a: dict[str, Any]) -> list[dict[str, Any]]:
    authority = val(a, 'authority', 'SECRETARÍA DE MOVILIDAD EJEMPLO')
    date_value = val(a, 'infraction_date', '10 de marzo de 2025')
    return [
        section("INFORME JURÍDICO PRELIMINAR DE CHEQUEO SAST", f"Autoridad reportada: {authority}. Fecha de detección informada: {date_value}. El análisis se estructura por autorización, operación técnica, actuación de control y afectación individual."),
        section("1. OBJETO, ALCANCE Y RESULTADO PERMITIDO", "El chequeo busca determinar si existe una coincidencia verificable entre el comparendo y una ayuda tecnológica concreta, un periodo de autorización u operación, y una actuación oficial. El sistema solo puede emitir estados de evidencia; no puede prometer revocación, devolución o levantamiento de medidas."),
        section("2. IDENTIFICACIÓN MÍNIMA DEL CASO", table=[
            ("Dato", "Valor", "Control"),
            ("Autoridad", authority, "Normalizar denominación y competencia territorial"),
            ("Comparendo", val(a,'ticket','Pendiente'), "Obtener número completo y acto posterior"),
            ("Placa", val(a,'plate','Pendiente'), "Validar titularidad y calidad del solicitante"),
            ("Fecha y hora", date_value, "Definir régimen temporal y vigencia aplicable"),
            ("Punto/dispositivo", val(a,'device','Pendiente de individualizar'), "No basta la ciudad o autoridad"),
            ("Tipo de detección", val(a,'detection_type','Velocidad u otra conducta por confirmar'), "Define calibración y evidencia técnica"),
        ]),
        section("3. MATRIZ DE VERIFICACIÓN EN CUATRO CAPAS", table=[
            ("Capa", "Pregunta decisiva", "Evidencia requerida", "Resultado admisible"),
            ("A. Autorización", "¿La ayuda concreta tenía autorización ANSV vigente o excepción legal?", "Acto ANSV, código, punto, fechas, mapa/registro oficial", "Vigente / vencida / ausente / excepción / no verificable"),
            ("B. Operación", "¿Cumplía criterios técnicos al iniciar y durante la operación?", "Viabilidad de infraestructura, calibración vigente, señalización y fecha de operación registrada", "Cumple / brecha documentada / evidencia insuficiente"),
            ("C. Control", "¿Existe actuación de Supertransporte y qué decidió?", "Auto, resolución, recursos, ejecutoria y alcance por ayuda y periodo", "Investigación / decisión no firme / decisión firme"),
            ("D. Caso individual", "¿El comparendo está comprendido y es atribuible a la persona?", "Expediente, imagen/video, validación, notificación, identificación e imputación", "Coincide / no coincide / requiere defensa distinta"),
        ]),
        section("4. CONFLICTO INTERPRETATIVO OFICIAL 2026", "Las comunicaciones de la Superintendencia de Transporte de mayo de 2026 anunciaron investigaciones por presuntas irregularidades y, para parte del universo, aludieron al antiguo Concepto de Desempeño de la Tecnología. Posteriormente, el concepto jurídico del Ministerio de Transporte 20261340929621 del 30 de junio de 2026 sostuvo que, para nuevas solicitudes bajo la Resolución 20203040011245 de 2020, dicho concepto dejó de estar previsto y fue sustituido en la componente operativa por acreditación de calibración. Esta tensión no se resuelve por titular de prensa: debe estudiarse el auto o decisión concreta, el régimen de transición y la fecha de cada actuación."),
        section("5. RESULTADO PRELIMINAR", table=[
            ("Variable", "Resultado"),
            ("Coincidencia territorial/temporal", val(a,'match','Posible coincidencia; pendiente de individualización')),
            ("Autorización ANSV", val(a,'authorization_status','No verificada')),
            ("Criterios técnicos", val(a,'technical_status','No verificados')),
            ("Actuación Supertransporte", val(a,'investigation_status','Investigación o auto por verificar')),
            ("Decisión firme", val(a,'final_decision','No verificada')),
            ("Aplicabilidad individual", val(a,'individual_scope','No demostrada')),
            ("Nivel de confianza", val(a,'confidence','Bajo hasta completar expediente')),
        ]),
        section("6. REGLAS DE INTERPRETACIÓN", bullets=[
            "Un comunicado, auto de apertura o formulación de cargos no equivale a una decisión firme.",
            "La mención de una autoridad no demuestra que todas sus cámaras o todos sus periodos estén afectados.",
            "La autorización ANSV tiene, como regla general, duración de cinco años; deben verificarse fecha, alcance y excepciones.",
            "El artículo 158A condiciona la revocatoria oficiosa a una decisión de Supertransporte en firme y al periodo sin autorización.",
            "La responsabilidad del propietario no puede presumirse automáticamente: debe verificarse imputación personal y culpabilidad conforme a la jurisprudencia constitucional.",
            "Pago, acuerdo, cobro coactivo, prescripción o proceso judicial requieren rutas separadas y análisis profesional.",
        ]),
        section("7. SIGUIENTE PASO CONTROLADO", bullets=[
            "Obtener expediente íntegro e identificación exacta de la ayuda tecnológica.",
            "Consultar y conservar evidencia del registro oficial ANSV a la fecha del análisis.",
            "Solicitar autorización, fecha de inicio de operación, calibración, señalización y viabilidad de infraestructura.",
            "Descargar el auto o resolución de Supertransporte, verificar recursos y constancia de ejecutoria.",
            "Cruzar dispositivo, punto, conducta y periodo con el comparendo individual.",
            "Definir la actuación procedente sin abandonar términos contravencionales, coactivos o judiciales.",
        ]),
        tr001_control("CO-TR-001", assumptions=["Los datos del comparendo corresponden al expediente oficial", "La consulta se realiza sobre fuentes reproducibles"], sources=["Ley 1843 de 2017", "Resolución 20203040011245 de 2020", "Ley 2251 de 2022, artículo 18", "Sentencia C-038 de 2020", "Concepto MinTransporte 20261340929621 de 2026"], red_flags=["Cobro coactivo o embargo", "Término próximo", "Pago o acuerdo", "Proceso judicial", "Suplantación o fraude", "Fuentes oficiales contradictorias"]),
    ]


def tr001_traceability(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("FICHA DE TRAZABILIDAD, CONFLICTOS Y JERARQUÍA DE FUENTES SAST", "Registro reproducible de cada fuente consultada, su autoridad, fecha, alcance, fuerza jurídica y relación con el caso concreto."),
        section("1. IDENTIFICACIÓN DEL CRUCE", table=[
            ("Campo", "Contenido"),
            ("Autoridad normalizada", val(a,'authority','SECRETARÍA DE MOVILIDAD EJEMPLO')),
            ("Alias recibido", val(a,'authority_alias','Movilidad Ejemplo')),
            ("Fecha del hecho", val(a,'infraction_date','10/03/2025')),
            ("Punto/dispositivo", val(a,'device','Pendiente')),
            ("Comparendo", val(a,'ticket','Pendiente')),
            ("Consulta ejecutada", val(a,'query_date','31/07/2026')),
        ]),
        section("2. REGISTRO DE FUENTES", table=[
            ("Fuente", "Naturaleza", "Fuerza", "Uso permitido"),
            ("Ley 1843 de 2017 y artículo 158A", "Norma vigente", "Obligatoria", "Autorización, criterios y revocatoria condicionada"),
            ("Resolución 20203040011245 de 2020", "Reglamento técnico", "Obligatoria dentro de su ámbito", "Autorización y operación: infraestructura, calibración y señalización"),
            ("Registro/mapa ANSV", "Registro administrativo", "Evidencia oficial consultable", "Ubicación, autorización y vigencia; conservar captura y fecha"),
            ("Auto o resolución Supertransporte", "Acto particular", "Según etapa y firmeza", "Definir investigado, cargos, ayuda, periodo, decisión y recursos"),
            ("Comunicado Supertransporte", "Información institucional", "No sustituye el acto", "Alerta e identificación preliminar"),
            ("Concepto MinTransporte 20261340929621", "Concepto general no vinculante", "Criterio interpretativo oficial", "Registrar tensión sobre Concepto de Desempeño y régimen temporal"),
            ("Sentencia C-038 de 2020", "Jurisprudencia constitucional", "Obligatoria en su ratio", "Imputación personal y culpabilidad"),
        ]),
        section("3. METADATOS OBLIGATORIOS", table=[
            ("Dato", "Valor a conservar"),
            ("Título/radicado", val(a,'source_title','Acto o fuente oficial individualizada')),
            ("URL oficial", val(a,'source_url','Registrar enlace exacto')),
            ("Fecha de expedición", val(a,'source_date','Pendiente')),
            ("Fecha y hora de consulta", val(a,'query_timestamp','31/07/2026 01:45 -05:00')),
            ("Hash SHA-256", val(a,'source_hash','Calcular sobre archivo descargado')),
            ("Captura/PDF", "Guardar copia íntegra y legible"),
            ("Estado", "Vigente / derogada / en transición / impugnada / firme / no verificado"),
        ]),
        section("4. MATRIZ DE CONFLICTO", table=[
            ("Proposición", "Fuente A", "Fuente B", "Tratamiento"),
            ("Exigibilidad del Concepto de Desempeño después de 2020", "Comunicaciones y autos de mayo de 2026", "Concepto MinTransporte 30/06/2026", "No asumir; revisar acto, cargos, norma invocada y régimen temporal"),
            ("Revocatoria de comparendos", "Titulares/comunicados", "Artículo 158A", "Exigir decisión firme, periodo sin autorización y aplicabilidad individual"),
            ("Fecha final de un periodo", "Tabla oficial", "Texto narrativo", "Registrar discrepancia y solicitar certificación"),
        ]),
        section("5. CONTROL DE VERSIONES", bullets=[
            "Nunca sobrescribir una fuente: crear revisión inmutable con fecha, hash y responsable.",
            "Conservar la fuente original y la interpretación separadas.",
            "Marcar como inferencia cualquier cruce no expresamente declarado por la autoridad.",
            "Reconsultar el registro ANSV y las resoluciones antes de cada envío al usuario.",
            "No usar resultados antiguos como si describieran el estado actual del expediente.",
        ]),
        tr001_control("CO-TR-001-TRAZABILIDAD", assumptions=["La fuente fue obtenida de dominio oficial", "El hash corresponde al archivo analizado"], sources=["ANSV", "Ministerio de Transporte", "Superintendencia de Transporte", "Secretaría Jurídica del Senado", "Corte Constitucional"], red_flags=["Fuente secundaria única", "Acto incompleto", "Rango ambiguo", "Sin constancia de firmeza", "Conflicto no resuelto"]),
    ]


def tr001_enrollment(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("FICHA DE INSCRIPCIÓN VERIFICADA Y AUTORIZACIONES DEL EXPEDIENTE", "Captura mínima y proporcional de identidad, calidad, actuación, finalidades, consentimiento y evidencia. La inscripción no crea representación ni garantiza viabilidad."),
        section("1. IDENTIDAD Y LEGITIMACIÓN", table=[
            ("Campo", "Dato", "Verificación"),
            ("Titular", val(a,'holder_name','ANDRÉS FELIPE RUIZ'), "Documento y prueba de vida/canal seguro"),
            ("Documento", val(a,'holder_id','CC 71.000.000'), "Coincidencia con soporte"),
            ("Calidad", val(a,'capacity','Presunto infractor/propietario'), "Definir interés y legitimación"),
            ("Representante", val(a,'representative','No aplica'), "Poder o autorización cuando corresponda"),
            ("Correo y teléfono", val(a,'email','andres.ruiz@example.com'), "Confirmación de contacto"),
        ]),
        section("2. ACTUACIÓN OBJETO DE CHEQUEO", table=[
            ("Dato", "Contenido"),
            ("Autoridad", val(a,'authority','SECRETARÍA DE MOVILIDAD EJEMPLO')),
            ("Comparendo", val(a,'ticket','110010000000123456')),
            ("Placa", val(a,'plate','ABC123')),
            ("Fecha/hora", val(a,'infraction_date','10/03/2025 09:35')),
            ("Punto/dispositivo", val(a,'device','Pendiente de la evidencia')),
            ("Estado informado", val(a,'status','Registrado en SIMIT; por verificar')),
            ("Pago/acuerdo/coactivo", val(a,'collection_status','No informado')),
        ]),
        section("3. AUTORIZACIONES DIFERENCIADAS", table=[
            ("Finalidad", "Decisión", "Alcance"),
            ("Chequeo preliminar en fuentes públicas", val(a,'screening_consent','Sí'), "Cruce de autoridad, fecha, dispositivo y actuaciones"),
            ("Tratamiento de datos para expediente", val(a,'data_consent','Sí'), "Gestión, seguridad, trazabilidad y comunicaciones del caso"),
            ("Consulta/obtención de documentos oficiales", val(a,'records_consent','Sí'), "Solicitudes y descargas dentro de la finalidad informada"),
            ("Contacto sobre cambios materiales", val(a,'alert_consent','Sí'), "Solo novedades aplicables, no publicidad encubierta"),
            ("Representación administrativa o judicial", val(a,'representation_consent','No'), "Requiere encargo/poder separado y aceptación profesional"),
        ]),
        section("4. INVENTARIO DE EVIDENCIA", table=[
            ("Documento", "Estado", "Observación"),
            ("Comparendo y evidencia original", "Pendiente", "Imagen/video y metadatos"),
            ("Resolución sancionatoria", "Pendiente", "Si existe"),
            ("Notificación", "Pendiente", "Guía, correo, aviso o constancia"),
            ("Consulta SIMIT/RUNT", "Pendiente", "Captura fechada; no sustituye expediente"),
            ("Autorización ANSV", "Pendiente", "Ayuda, punto y vigencia"),
            ("Calibración/señalización/infraestructura", "Pendiente", "Según conducta y régimen"),
            ("Acto Supertransporte", "Pendiente", "Copia íntegra y estado"),
            ("Pago, acuerdo o coactivo", "Pendiente", "Soporte y fechas"),
        ]),
        section("5. PRIVACIDAD Y RETENCIÓN", bullets=[
            "Aplicar el principio de minimización: recopilar solo datos necesarios para el chequeo y la ruta elegida.",
            "Separar documentos de identidad de fuentes públicas y actos administrativos.",
            "Aplicar acceso por rol, cifrado, auditoría y descarga controlada.",
            "Definir plazo de conservación por estado del expediente y obligación legal; eliminar o anonimizar al cierre cuando proceda.",
            "No reutilizar imágenes, placas, datos de contacto o decisiones para entrenamiento de IA sin base y autorización separadas.",
        ]),
        section("6. DECLARACIONES DEL USUARIO", bullets=[
            "La información suministrada es completa según su conocimiento.",
            "Entiende que una coincidencia preliminar no equivale a nulidad o revocatoria.",
            "Informará de inmediato pago, acuerdo, embargo, demanda, audiencia o notificación nueva.",
            "Acepta que una alerta puede cerrarse si no existe evidencia suficiente o aplicabilidad individual.",
        ]),
        signature(val(a,'holder_name','ANDRÉS FELIPE RUIZ'), "TITULAR / SOLICITANTE"),
        tr001_control("CO-TR-001-INSCRIPCIÓN", assumptions=["Identidad y canal verificados", "Consentimientos registrados de forma demostrable"], sources=["Ley 1581 de 2012", "Decreto 1074 de 2015", "Régimen de tránsito"], red_flags=["Tercero sin poder", "Documento falso o ilegible", "Datos sensibles innecesarios", "Pago o coactivo no informado"]),
    ]


def tr001_record_request(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD DE EXPEDIENTE, AUTORIZACIÓN Y EVIDENCIA TÉCNICA SAST", "Modelo de petición para individualizar la ayuda tecnológica y obtener evidencia íntegra. Debe ajustarse a la autoridad competente, al expediente y al término vigente."),
        section("1. DESTINATARIO Y REFERENCIA", table=[
            ("Campo", "Contenido"),
            ("Autoridad", val(a,'authority','SECRETARÍA DE MOVILIDAD EJEMPLO')),
            ("Peticionario", val(a,'holder_name','ANDRÉS FELIPE RUIZ')),
            ("Comparendo", val(a,'ticket','110010000000123456')),
            ("Placa", val(a,'plate','ABC123')),
            ("Fecha", val(a,'infraction_date','10/03/2025')),
        ]),
        section("2. PETICIONES SOBRE EL EXPEDIENTE INDIVIDUAL", bullets=[
            "Remitir índice y copia íntegra, legible y descargable del expediente contravencional.",
            "Aportar orden de comparendo, evidencia original, metadatos, cadena de custodia y registro de validación por autoridad competente.",
            "Informar fecha, forma y soportes de notificación; remitir actos posteriores y constancias de ejecutoria.",
            "Identificar número interno, fabricante, modelo, serial, tipo, ubicación georreferenciada y sentido de la ayuda tecnológica.",
            "Indicar la conducta detectada y la regla técnica aplicada al evento.",
        ]),
        section("3. PETICIONES SOBRE AUTORIZACIÓN Y OPERACIÓN", bullets=[
            "Remitir el acto de autorización ANSV vigente para la ayuda, el punto y la fecha del hecho, con inicio y terminación de vigencia.",
            "Informar la fecha de inicio de operación registrada en el sistema de la ANSV.",
            "Aportar viabilidad de uso de infraestructura vial y documentos que soportaron la instalación.",
            "Aportar evidencia de señalización instalada, fecha, ubicación y mantenimiento.",
            "Para medición, aportar certificado de calibración vigente, laboratorio, trazabilidad y relación inequívoca con el equipo utilizado.",
            "Precisar si se invoca excepción de autorización y remitir su fundamento y evidencia de señalización.",
        ]),
        section("4. PETICIONES SOBRE ACTUACIONES DE CONTROL", bullets=[
            "Informar si la ayuda, autoridad o periodo está comprendido en auto o resolución de la Superintendencia de Transporte.",
            "Remitir copia íntegra del acto, cargos, pruebas, decisión, recursos y constancia de firmeza.",
            "Precisar de forma expresa cuáles ayudas y periodos fueron afectados; no responder solo con referencias generales a la entidad.",
            "Explicar el tratamiento dado a los comparendos y multas individuales comprendidos, incluido reporte a SIMIT/RUNT y pagos recibidos.",
        ]),
        section("5. PRECISIÓN SOBRE EL CONCEPTO DE DESEMPEÑO", "Si la entidad considera exigible el Concepto de Desempeño de la Tecnología para el periodo analizado, solicito identificar la norma temporal aplicable, la fecha de radicación del trámite, el régimen de transición y el acto concreto que sustenta esa exigencia. Si aplica el régimen de la Resolución 20203040011245 de 2020, solicito explicar la relación entre calibración, trazabilidad metrológica y cualquier concepto anterior."),
        section("6. INTEGRIDAD, FORMATO Y TRASLADO", "Solicito documentos en formato original o copia fiel, con foliación o índice, enlaces funcionales y explicación de cualquier reserva. Si la entidad carece de competencia o custodia, debe trasladar la petición a quien corresponda e informar. Una respuesta incompleta debe identificar expresamente el documento inexistente, su custodio y las gestiones realizadas."),
        section("7. ADVERTENCIA DE TÉRMINOS", "La petición de información no suspende por sí sola términos para audiencia, recursos, excepciones, cobro coactivo o acciones judiciales. El peticionario debe preservar en paralelo la defensa que resulte procedente."),
        signature(val(a,'holder_name','ANDRÉS FELIPE RUIZ'), "PETICIONARIO"),
        tr001_control("CO-TR-001-EXPEDIENTE", assumptions=["Autoridad y actuación individual identificadas", "Canal y legitimación verificados"], sources=["Ley 1755 de 2015", "Ley 1843 de 2017", "Resolución 20203040011245 de 2020", "Ley 2251 de 2022"], red_flags=["Audiencia o recurso próximo", "Cobro coactivo", "Reserva invocada", "Acto no aportado", "Equipo no individualizado"]),
    ]


def tr001_review(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("MATRIZ DE REVISIÓN PROFESIONAL Y DECISIÓN DE RUTA SAST", "Documento interno para valoración jurídica, probatoria y estratégica. Ninguna ruta se libera sin registrar fuentes, hechos, inferencias, confianza y riesgos."),
        section("1. CONTROL DE COMPLETITUD", table=[
            ("Elemento", "Estado", "Bloquea conclusión"),
            ("Comparendo y acto sancionatorio", val(a,'ticket_evidence','Pendiente'), "Sí"),
            ("Dispositivo/punto exacto", val(a,'device_evidence','Pendiente'), "Sí"),
            ("Autorización y vigencia ANSV", val(a,'authorization_evidence','Pendiente'), "Sí para ruta por artículo 158A"),
            ("Criterios técnicos de operación", val(a,'technical_evidence','Pendiente'), "Sí para conclusión técnica"),
            ("Acto Supertransporte", val(a,'supertransport_act','Pendiente'), "Sí"),
            ("Firmeza y alcance", val(a,'finality_evidence','Pendiente'), "Sí para revocatoria oficiosa"),
            ("Notificación e imputación personal", val(a,'due_process_evidence','Pendiente'), "Sí para defensa individual"),
        ]),
        section("2. PREGUNTAS JURÍDICAS DECISIVAS", bullets=[
            "¿La ayuda requería autorización ANSV o estaba cobijada por una excepción legal?",
            "¿La autorización comprendía el punto, sentido, tipo de detección y fecha del hecho?",
            "¿Los criterios técnicos exigibles estaban vigentes y acreditados para ese equipo?",
            "¿La actuación de Supertransporte es apertura, cargos, decisión, recurso o decisión firme?",
            "¿La decisión individualiza la ayuda y el periodo que comprende el comparendo?",
            "¿Existe conflicto entre la norma/cargo invocado y el concepto jurídico del Ministerio de junio de 2026?",
            "¿La infracción fue imputada personalmente y con culpabilidad, o solo por calidad de propietario?",
            "¿Existen pago, acuerdo, coactivo, prescripción, demanda o medidas que cambian la ruta?",
        ]),
        section("3. MATRIZ DE RESULTADOS", table=[
            ("Estado", "Conclusión permitida", "Ruta"),
            ("Sin coincidencia", "No se identificó relación con actuación oficial", "Cerrar alerta y conservar evidencia"),
            ("Coincidencia preliminar", "Autoridad/fecha coinciden, pero falta ayuda o acto", "Solicitar expediente; no prometer resultado"),
            ("Investigación abierta", "Existen cargos no decididos", "Monitorear y ejercer defensa ordinaria"),
            ("Autorización no demostrada", "Brecha probatoria, no decisión definitiva", "Requerir certificación; preservar términos"),
            ("Brecha técnica", "Falta calibración/señalización/infraestructura acreditada", "Valorar defensa según conducta y prueba"),
            ("Decisión no firme", "No activa aún revocatoria oficiosa del artículo 158A", "Monitorear recursos y ejecutoria"),
            ("Decisión firme aplicable", "Ayuda y periodo coinciden", "Solicitar ejecución oficiosa y corrección de registros"),
            ("Problema de imputación", "No se probó autoría/culpabilidad", "Defensa constitucional y contravencional"),
            ("Pago", "Puede requerir análisis restitutorio separado", "Revisar acto, firmeza, procedimiento y prueba del pago"),
            ("Coactivo/judicial", "Riesgo alto y términos propios", "Escalamiento inmediato a abogado"),
        ]),
        section("4. TRATAMIENTO DEL CONFLICTO 2026", table=[
            ("Pregunta", "Control obligatorio"),
            ("¿Se formula cargo por falta de Concepto de Desempeño después de 2020?", "Cotejar el auto con Resolución 20203040011245, Resolución INM 352/2020 y concepto 20261340929621"),
            ("¿El trámite comenzó antes del nuevo régimen?", "Revisar régimen de transición y fecha de radicación"),
            ("¿El acto está firme?", "No convertir investigación o comunicado en consecuencia individual"),
            ("¿Existe discrepancia de fechas o ayudas?", "Solicitar aclaración/certificación; registrar incertidumbre"),
        ]),
        section("5. APROBACIÓN Y TRAZABILIDAD", bullets=[
            "Registrar versión de fuentes, fecha de consulta y hash.",
            "Separar hechos acreditados, hechos informados, inferencias y recomendaciones.",
            "Asignar nivel de confianza: bajo, medio o alto, con justificación.",
            "Bloquear liberación si falta acto completo, ayuda exacta, firmeza o competencia.",
            "Conservar revisión inmutable y comparación cuando cambie una fuente o decisión.",
        ]),
        tr001_control("CO-TR-001-REVISIÓN", assumptions=["Expediente suficiente para la ruta elegida", "La decisión profesional está documentada"], sources=["Constitución, artículo 29", "Sentencia C-038 de 2020", "Ley 1843 de 2017", "Ley 2251 de 2022", "CPACA"], red_flags=["Embargo", "Demanda", "Acto firme adverso", "Término próximo", "Conflicto de fuentes sin resolver"]),
    ]


def tr001_followup(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("PROTOCOLO DE SEGUIMIENTO, ALERTAS Y CIERRE SAST", "Control de cambios oficiales y ejecución individual. Las alertas se generan solo ante eventos materiales y aplicables al expediente."),
        section("1. MATRIZ DE MONITOREO", table=[
            ("Fuente", "Frecuencia", "Evento material", "Evidencia"),
            ("Supertransporte - resoluciones", "Semanal mientras exista actuación", "Cargos, decisión, recurso o ejecutoria", "PDF íntegro, radicado, fecha y hash"),
            ("ANSV - autorización/mapa", "Al ingreso y antes de cada decisión", "Alta, vencimiento, modificación, punto o estado", "Captura/consulta fechada y acto"),
            ("Ministerio/ANSV - normativa", "Mensual", "Nueva resolución, circular o concepto relevante", "Fuente oficial y análisis de vigencia"),
            ("Autoridad de tránsito", "Según expediente", "Respuesta, revocatoria, corrección o negativa", "Radicado, acto y notificación"),
            ("SIMIT/RUNT", "Después de actuación material", "Actualización o persistencia del registro", "Consulta fechada"),
            ("Cobro coactivo/judicial", "Según término", "Mandamiento, embargo, audiencia o decisión", "Notificación y calendario procesal"),
        ]),
        section("2. REGLAS DE ALERTA", bullets=[
            "No alertar por republicación de una noticia sin acto nuevo.",
            "Distinguir investigación, decisión, recurso y firmeza.",
            "Relacionar el evento con la ayuda y periodo del usuario antes de notificar.",
            "Explicar qué cambió, qué no cambió y cuál es el siguiente paso.",
            "Nunca afirmar devolución, nulidad o eliminación hasta verificar ejecución individual.",
        ]),
        section("3. CONTROL DEL PLAZO DEL ARTÍCULO 158A", "Cuando exista decisión de Supertransporte en firme y el comparendo esté comprendido en un periodo sin autorización, registrar fecha exacta de firmeza y controlar el término máximo de treinta días hábiles para la revocatoria oficiosa. El cálculo debe considerar calendario hábil real y no sustituye verificación del acto ni de su comunicación."),
        section("4. EJECUCIÓN Y VERIFICACIÓN", table=[
            ("Hito", "Comprobación"),
            ("Revocatoria/corrección", "Acto individual o certificación de aplicación"),
            ("SIMIT/RUNT", "Registro actualizado después de plazo razonable"),
            ("Cobro coactivo", "Archivo, terminación o levantamiento de medidas"),
            ("Pago", "Ruta restitutoria decidida y soporte de desembolso si procede"),
            ("Datos personales", "Cierre, retención, anonimización o eliminación según política"),
        ]),
        section("5. CRITERIOS DE CIERRE", bullets=[
            "Sin coincidencia demostrada y sin otra defensa pendiente.",
            "Actuación investigativa cerrada sin decisión aplicable.",
            "Decisión ejecutada y registros corregidos.",
            "Ruta trasladada a abogado por coactivo, demanda o complejidad probatoria.",
            "Usuario desiste, con conservación mínima de auditoría y obligaciones legales.",
        ]),
        section("6. REAPERTURA", "Reabrir solo ante una fuente oficial nueva, cambio de firmeza, identificación posterior del dispositivo, respuesta de la autoridad o alteración material del registro. Toda reapertura crea una nueva revisión inmutable y conserva la conclusión anterior."),
        tr001_control("CO-TR-001-SEGUIMIENTO", assumptions=["Monitoreo documentado", "El usuario mantiene canales de contacto vigentes"], sources=["Registro ANSV", "Resoluciones Supertransporte", "Ley 2251 de 2022, artículo 18"], red_flags=["Firmeza no verificable", "Decisión impugnada", "Persistencia de embargo", "Información oficial contradictoria"]),
    ]


# ---------------------------------------------------------------------------
# CO-TR-002 - FOTOMULTA NO NOTIFICADA (REVALIDACIÓN M15)
# ---------------------------------------------------------------------------

def tr002_control(product: str, *, assumptions: Iterable[str], sources: Iterable[str], red_flags: Iterable[str]) -> dict[str, Any]:
    return section(
        "CONTROL JURÍDICO M15, SUPUESTOS Y LIBERACIÓN",
        (
            f"Playbook profundo M15.1 del producto {product}. Información jurídica verificada al 31 de julio de 2026. "
            "El documento separa orden de comparendo, notificación, proceso contravencional, acto sancionatorio y cobro. "
            "La falta o irregularidad de notificación no se convierte automáticamente en nulidad, archivo, prescripción, devolución o inexigibilidad. "
            "Antes de radicar debe revisarse el expediente íntegro, la dirección RUNT vigente para la fecha, la trazabilidad de validación y envío, "
            "la entrega o aviso, el conocimiento real, la conducta posterior del interesado, la imputación personal, los términos, los recursos y el estado de cobro."
        ),
        bullets=[
            *[f"Supuesto controlado: {x}" for x in assumptions],
            *[f"Fuente oficial: {x}" for x in sources],
            *[f"Escalamiento obligatorio: {x}" for x in red_flags],
        ],
        kind="control",
    )


def tr002_diagnostic(a: dict[str, Any]) -> list[dict[str, Any]]:
    authority = val(a, "authority", "SECRETARÍA DE MOVILIDAD DE MEDELLÍN")
    ticket = val(a, "ticket", "05001000000087654321")
    return [
        section("DIAGNÓSTICO JURÍDICO DE FOTODETECCIÓN, NOTIFICACIÓN Y DEFENSA", f"Autoridad informada: {authority}. Orden de comparendo: {ticket}. El diagnóstico identifica la etapa real y la consecuencia jurídicamente admisible de cada brecha de comunicación."),
        section("1. OBJETO Y RESULTADOS PERMITIDOS", "Determinar si la autoridad acreditó la secuencia legal de validación, envío y vinculación; si el interesado tuvo oportunidad real de defensa; y cuál actuación es procedente. El sistema puede clasificar evidencia, restaurar calendarios y preparar solicitudes. No puede declarar por sí solo nulidad, caducidad, revocatoria, archivo, devolución o levantamiento de medidas."),
        section("2. CRONOLOGÍA PROBATORIA OBLIGATORIA", table=[
            ("Hito", "Fecha informada", "Soporte exigible", "Pregunta decisiva"),
            ("Detección", val(a,"detection_date","10/03/2026 09:35"), "Imagen/video original y metadatos", "¿Corresponde al vehículo, conducta y punto?"),
            ("Validación", val(a,"validation_date","18/03/2026"), "Registro de validación y agente competente", "¿Cuándo nació la orden de comparendo validada?"),
            ("Envío", val(a,"sent_date","25/03/2026"), "Guía postal o log electrónico", "¿Se remitió dentro de 3 días hábiles de la validación?"),
            ("Dirección/canal", val(a,"runt_address","Dirección RUNT por certificar"), "Histórico RUNT y dato usado", "¿Era la última dirección registrada para esa fecha?"),
            ("Entrega/devolución", val(a,"delivery_date","No acreditada"), "Certificación del operador y causal", "¿Hubo entrega, rechazo, devolución o imposibilidad?"),
            ("Aviso", val(a,"notice_date","No acreditado"), "Texto, publicación, fechas y soporte", "¿Se activó la ruta subsidiaria de aviso?"),
            ("Conocimiento real", val(a,"knowledge_date","15/07/2026"), "Consulta, mensaje o actuación", "¿Cuándo pudo ejercer defensa materialmente?"),
            ("Comparecencia", val(a,"appearance_date","No registrada"), "Acta, radicado o audiencia", "¿Aceptó, negó, pidió pruebas o guardó silencio?"),
            ("Decisión", val(a,"resolution","No aportada"), "Resolución, motivación y notificación", "¿Existe sanción y está en firme?"),
        ]),
        section("3. REGLAS DE NOTIFICACIÓN INICIAL", bullets=[
            "La copia del comparendo y sus soportes debe enviarse por correo y/o correo electrónico dentro de los tres días hábiles siguientes a la validación.",
            "El envío físico debe realizarse mediante empresa de correos legalmente constituida y dirigirse a la última dirección registrada en el RUNT para la fecha relevante.",
            "Cuando no sea posible identificar o vincular al propietario mediante la última dirección RUNT, debe verificarse la notificación por aviso y su soporte íntegro.",
            "El término de once días hábiles para presentarse se cuenta desde la entrega del comparendo, no desde la detección ni desde una consulta posterior en SIMIT.",
            "La consulta en SIMIT o un mensaje informal no reemplazan automáticamente la notificación exigida, aunque pueden ser relevantes para determinar conocimiento real, conducta posterior y remedio disponible.",
        ]),
        section("4. EFECTOS JURÍDICOS DIFERENCIADOS", table=[
            ("Hallazgo", "Efecto que sí puede analizarse", "Conclusión prohibida"),
            ("Envío tardío", "Brecha procedimental y afectación concreta de defensa", "Nulidad automática"),
            ("No entrega / dirección errada", "Restablecimiento de oportunidad y revisión de vinculación", "Archivo automático"),
            ("Notificación indebida demostrada", "Los términos de reducción comienzan desde la notificación válida", "Desaparición automática de la infracción"),
            ("Conocimiento real sin expediente", "Solicitud inmediata de acceso y reserva de defensa", "Convalidación total e irrevocable"),
            ("Resolución sin oportunidad de contradicción", "Revisión de debido proceso, recursos o revocatoria según etapa", "Revocatoria garantizada"),
            ("Cobro coactivo o embargo", "Defensa especializada y control urgente de términos", "Suspensión automática por petición"),
        ]),
        section("5. IMPUTACIÓN Y NATURALEZA DEL COMPARENDO", bullets=[
            "La orden de comparendo es una citación que inicia el trámite; no equivale a la sanción ni prueba por sí sola la responsabilidad.",
            "La sanción exige procedimiento, oportunidad de defensa, valoración probatoria y decisión motivada.",
            "No puede sancionarse al propietario por el solo vínculo dominial: la autoridad debe acreditar imputación personal y culpabilidad.",
            "Las obligaciones propias del propietario previstas por la ley deben analizarse por conducta concreta y dentro del proceso, sin responsabilidad automática.",
        ]),
        section("6. CLASIFICACIÓN DE ETAPA Y RUTA", table=[
            ("Etapa verificada", "Ruta principal", "Documento M15"),
            ("Solo comparendo / sin expediente", "Acceso, preservación y cronología", "Solicitud integral de expediente"),
            ("Etapa contravencional abierta", "Comparecencia, audiencia, pruebas y contradicción", "Solicitud de audiencia y pruebas"),
            ("Sanción no firme", "Recurso y defensa según notificación", "Reclamación por notificación + revisión profesional"),
            ("Sanción firme", "Revocatoria directa condicionada y control judicial", "Solicitud condicionada de revocatoria"),
            ("Registro incorrecto tras decisión favorable", "Corrección y sincronización", "Solicitud SIMIT/RUNT"),
            ("Cobro, embargo, pago o demanda", "Escalamiento inmediato", "Guía de términos y escalamiento"),
        ]),
        section("7. RESULTADO PRELIMINAR DEL CASO DEMO", table=[
            ("Variable", "Estado"),
            ("Envío dentro de 3 días hábiles", val(a,"dispatch_compliance","No demostrado")),
            ("Dirección RUNT histórica", val(a,"runt_history","Pendiente")),
            ("Entrega o aviso", val(a,"notice_proof","No acreditado")),
            ("Conocimiento real", val(a,"knowledge_date","15/07/2026")),
            ("Etapa", val(a,"stage","Por establecer con expediente")),
            ("Acto sancionatorio", val(a,"resolution","No aportado")),
            ("Cobro", val(a,"coactive","Sin información")),
            ("Riesgo", val(a,"risk","Amarillo hasta completar cronología")),
        ]),
        section("8. SIGUIENTE PASO CONTROLADO", bullets=[
            "Descargar consulta SIMIT/RUNT y conservar fecha, pero no usarla como sustituto del expediente.",
            "Solicitar orden de comparendo, soportes, validación, guía, trazabilidad electrónica, histórico RUNT, aviso, audiencia, resolución y constancias.",
            "Reconstruir días hábiles con calendario local y registrar cada fecha cierta, informada o inferida.",
            "Definir por separado descuentos, defensa contravencional, recursos, revocatoria, registros y cobro.",
            "Someter a abogado cualquier caso con resolución firme, coactivo, embargo, pago, múltiples comparendos o término próximo.",
        ]),
        tr002_control("CO-TR-002", assumptions=["La detección proviene de un SAST y no de imposición directa en vía", "Los datos entregados deben contrastarse con el expediente"], sources=["Ley 1843 de 2017, artículos 7 a 9", "Ley 769 de 2002, artículos 135 y 136", "Sentencias C-038 de 2020 y C-321 de 2022", "Ley 1755 de 2015", "CPACA"], red_flags=["Cobro coactivo o embargo", "Sanción firme", "Pago o acuerdo", "Proceso judicial", "Término próximo", "Suplantación o fraude"]),
    ]


def tr002_record(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD INTEGRAL DE EXPEDIENTE, TRAZABILIDAD Y PRESERVACIÓN DE EVIDENCIA", "Petición de información y copias para reconstruir la notificación y ejercer defensa sin aceptar la infracción ni convalidar actuaciones."),
        section("1. IDENTIFICACIÓN", table=[
            ("Campo", "Dato"),
            ("Autoridad", val(a,"authority","SECRETARÍA DE MOVILIDAD DE MEDELLÍN")),
            ("Comparendo", val(a,"ticket","05001000000087654321")),
            ("Placa", val(a,"plate","ABC123")),
            ("Solicitante", val(a,"holder_name","ANDRÉS FELIPE RUIZ")),
            ("Documento", val(a,"holder_id","CC 71.000.000")),
            ("Fecha de conocimiento", val(a,"knowledge_date","15/07/2026")),
        ]),
        section("2. COPIA ÍNTEGRA DEL EXPEDIENTE", bullets=[
            "Orden de comparendo y todos sus soportes, incluidas imágenes, video, metadatos y certificación de integridad.",
            "Registro de detección y validación: fecha, hora, agente, identificación, competencia y constancia de validación.",
            "Actos, citaciones, audiencias, constancias de comparecencia, decisiones, recursos y ejecutoria.",
            "Actuaciones persuasivas o coactivas, mandamiento de pago, notificaciones, medidas cautelares y estado actual.",
            "Historial de novedades y sincronizaciones remitidas a SIMIT y RUNT.",
        ]),
        section("3. TRAZABILIDAD DE ENVÍO Y ENTREGA", bullets=[
            "Fecha exacta de validación y fecha/hora de generación del envío.",
            "Copia de la pieza enviada, anexos y soportes que efectivamente acompañaron el comparendo.",
            "Nombre y habilitación del operador postal, número de guía, eventos logísticos y certificación final.",
            "Dirección física y electrónica utilizadas, fuente del dato y certificación del histórico RUNT consultado.",
            "Constancia de entrega, rechazo, devolución, dirección inexistente, destinatario desconocido o cualquier causal reportada.",
            "Si hubo correo electrónico: dirección, mensaje completo, encabezados, logs de envío, rebote, entrega y acceso disponibles.",
            "Si hubo aviso: texto, fecha de fijación/publicación, fecha de desfijación, medio y evidencia de cumplimiento.",
        ]),
        section("4. INFORMACIÓN TÉCNICA Y DE IMPUTACIÓN", bullets=[
            "Identificación del dispositivo y punto exacto; autorización ANSV y vigencia para la fecha.",
            "Señalización, calibración y demás soportes técnicos según la conducta detectada.",
            "Persona a quien se atribuyó la conducta y fundamento probatorio de la imputación.",
            "Para obligaciones del propietario, norma, deber concreto, conducta omisiva y prueba de culpabilidad.",
        ]),
        section("5. PREGUNTAS DE FONDO", table=[
            ("Pregunta", "Respuesta solicitada"),
            ("¿El envío ocurrió dentro de tres días hábiles?", "Sí/no, cálculo y soporte"),
            ("¿Cuál era la última dirección RUNT?", "Certificación histórica a la fecha de validación"),
            ("¿Qué modalidad de notificación se tuvo por cumplida?", "Correo, email, aviso u otra, con fundamento"),
            ("¿Desde qué fecha se contabilizaron los once días?", "Fecha de entrega y cálculo"),
            ("¿Desde qué fecha se contabilizaron descuentos?", "Regla aplicada frente a notificación"),
            ("¿Cómo se garantizó la defensa?", "Acceso, citación, audiencia y pruebas"),
        ]),
        section("6. TÉRMINO Y FORMA DE RESPUESTA", "Las peticiones de documentos e información están sometidas al término especial de diez días. La respuesta debe ser completa, congruente, verificable y acompañar los anexos; las reservas deben identificar norma expresa y permitir el trámite de insistencia cuando proceda."),
        section("7. RESERVAS", bullets=[
            "Esta petición no acepta los hechos, la autoría, la responsabilidad, la validez de la notificación ni la firmeza del acto.",
            "La radicación no sustituye recursos ni suspende términos; se solicita informar inmediatamente cualquier término en curso.",
            "Se pide preservación de registros electrónicos, logs, metadatos y documentos originales para evitar pérdida de evidencia.",
        ]),
        signature(val(a,"holder_name","ANDRÉS FELIPE RUIZ"), "PETICIONARIO"),
        tr002_control("CO-TR-002-EXPEDIENTE", assumptions=["El solicitante acredita identidad, titularidad o interés legítimo", "La autoridad conserva los registros solicitados"], sources=["Ley 1755 de 2015, artículos 13 a 16 y 24 a 29", "Ley 1843 de 2017, artículo 8", "Ley 1581 de 2012"], red_flags=["Expediente reservado de tercero", "Proceso judicial", "Pérdida o alteración de evidencia", "Término inmediato"]),
    ]


def tr002_notice_claim(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("RECLAMACIÓN POR NOTIFICACIÓN, VINCULACIÓN Y DEBIDO PROCESO", "Solicitud de verificación de la comunicación inicial y de restablecimiento de la oportunidad de defensa cuando la irregularidad esté demostrada y sea jurídicamente relevante."),
        section("1. HECHOS ORGANIZADOS", table=[
            ("Hecho", "Fecha/dato", "Prueba"),
            ("Detección", val(a,"detection_date","10/03/2026"), "Soporte SAST"),
            ("Validación", val(a,"validation_date","18/03/2026"), "Registro por entregar"),
            ("Envío", val(a,"sent_date","25/03/2026"), "Guía por entregar"),
            ("Dirección utilizada", val(a,"used_address","No informada"), "Histórico RUNT"),
            ("Entrega o devolución", val(a,"delivery_status","No acreditada"), "Certificación postal"),
            ("Aviso", val(a,"notice_status","No acreditado"), "Constancia"),
            ("Conocimiento real", val(a,"knowledge_date","15/07/2026"), "Consulta SIMIT"),
            ("Acto sancionatorio", val(a,"resolution","No aportado"), "Expediente"),
        ]),
        section("2. ESTÁNDAR JURÍDICO APLICABLE", bullets=[
            "La remisión debe realizarse dentro de tres días hábiles siguientes a la validación y acompañar copia del comparendo y sus soportes.",
            "La dirección relevante es la última registrada en el RUNT para el momento del trámite; el propietario tiene deber de mantenerla actualizada.",
            "La comparecencia se ordena dentro de once días hábiles siguientes a la entrega.",
            "Si se demuestra que el comparendo no fue notificado o fue indebidamente notificado, los términos de reducción comienzan desde la notificación válida.",
            "Las decisiones posteriores requieren una vinculación inicial jurídicamente verificable y respeto efectivo de contradicción y defensa.",
        ]),
        section("3. DEFECTOS A VERIFICAR", table=[
            ("Defecto", "Evidencia", "Afectación concreta"),
            ("Envío fuera de término", "Validación + admisión postal", "Retraso en conocimiento y descuentos"),
            ("Dirección distinta a RUNT", "Histórico RUNT + guía", "Falla de vinculación"),
            ("Pieza sin soportes", "Contenido de envío", "Imposibilidad de controvertir evidencia"),
            ("Devolución sin aviso", "Trazabilidad + ausencia de aviso", "No agotamiento de modalidad subsidiaria"),
            ("Email sin prueba técnica", "Logs, rebotes y encabezados", "Entrega no demostrada"),
            ("Sanción anterior al conocimiento", "Resolución y cronología", "Defensa material restringida"),
        ]),
        section("4. SOLICITUDES PRINCIPALES", bullets=[
            "Certificar la cronología completa y la modalidad de notificación que la autoridad tuvo por cumplida.",
            "Entregar todos los soportes de envío, entrega, devolución, aviso y dirección RUNT histórica.",
            "Reconocer, si se prueba la falta o indebida notificación, la fecha desde la cual corren los términos de reducción.",
            "Habilitar la comparecencia, acceso, audiencia, solicitud de pruebas y contradicción cuando la etapa y el ordenamiento lo permitan.",
            "Revisar cualquier decisión adoptada sin oportunidad real de defensa y resolver de manera motivada el remedio procedente.",
            "Abstenerse de afirmar que la sola consulta en SIMIT reemplazó retroactivamente la notificación inicial.",
            "Actualizar SIMIT/RUNT únicamente cuando exista acto o decisión que lo ordene y certificar la sincronización.",
        ]),
        section("5. SOLICITUD SUBSIDIARIA Y NO AUTOMATISMO", "Subsidiariamente, si la autoridad considera que la actuación quedó convalidada o que no procede restablecimiento, se solicita explicar la norma, el hecho de convalidación, la fecha, la afectación evaluada y los recursos disponibles. La reclamación no presupone que todo defecto formal produzca nulidad; exige una respuesta individual sobre su incidencia en el derecho de defensa."),
        section("6. IMPUTACIÓN PERSONAL", "Aun cuando la comunicación sea válida, la sanción no puede imponerse al propietario por la sola titularidad. Debe identificarse el sujeto de la infracción y demostrarse la conducta y culpabilidad que legalmente le sean atribuibles, sin perjuicio de obligaciones específicas del propietario que también requieren prueba dentro del procedimiento."),
        section("7. ANEXOS", bullets=["Documento de identidad", "Consulta SIMIT/RUNT fechada", "Histórico RUNT disponible", "Pruebas de domicilio/correo para la época", "Comunicaciones recibidas", "Radicados anteriores", "Poder, cuando aplique"]),
        signature(val(a,"holder_name","ANDRÉS FELIPE RUIZ"), "PETICIONARIO"),
        tr002_control("CO-TR-002-NOTIFICACIÓN", assumptions=["La notificación inicial no está acreditada o presenta una brecha verificable", "No se renuncia a defensas ni recursos"], sources=["Ley 1843 de 2017, artículos 7 y 8", "Constitución, artículo 29", "Ley 769 de 2002", "Sentencias C-038 de 2020 y C-321 de 2022"], red_flags=["Resolución firme", "Comparecencia o pago previo", "Coactivo", "Embargo", "Término judicial"]),
    ]


def tr002_hearing(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD DE COMPARECENCIA, AUDIENCIA, PRUEBAS Y CONTRADICCIÓN", "Actuación para proceso contravencional abierto o para oportunidad de defensa restablecida. La comparecencia se realiza sin aceptación de responsabilidad."),
        section("1. MANIFESTACIÓN DE COMPARECENCIA", "El interesado informa la fecha en que conoció la actuación, niega aceptación tácita de los hechos y solicita acceso previo al expediente, canal de comparecencia presencial o virtual, funcionario competente y fecha de audiencia."),
        section("2. CUESTIONES PREVIAS", bullets=[
            "Determinar si la orden de comparendo fue validada y enviada conforme a la Ley 1843 de 2017.",
            "Resolver la fecha efectiva desde la cual se contabilizan comparecencia y descuentos.",
            "Precisar si existe resolución, firmeza, cobro o medidas que alteren la ruta procesal.",
            "Individualizar al presunto infractor y la norma que permite atribuirle la conducta.",
        ]),
        section("3. SOLICITUD DE PRUEBAS", table=[
            ("Prueba", "Finalidad"),
            ("Imagen/video original y metadatos", "Autenticidad, integridad, vehículo, conducta, lugar y hora"),
            ("Registro de validación", "Fecha, competencia y juicio humano de validación"),
            ("Trazabilidad postal/electrónica", "Envío, entrega, devolución, aviso y conocimiento"),
            ("Histórico RUNT", "Dirección y datos vigentes para la fecha"),
            ("Autorización y soporte técnico", "Legalidad y confiabilidad de la ayuda"),
            ("Identificación del conductor", "Imputación personal"),
            ("Actos y notificaciones", "Etapa, motivación, recursos y firmeza"),
        ]),
        section("4. OBJECIONES Y CONTROVERSIA", bullets=[
            "Autenticidad, integridad y cadena técnica del registro.",
            "Correspondencia entre placa, características del vehículo, punto, fecha y conducta.",
            "Término y contenido del envío; dirección RUNT y aviso subsidiario.",
            "Identificación del sujeto activo, tipicidad, imputación personal y culpabilidad.",
            "Señalización, autorización y calibración cuando sean relevantes.",
            "Valor probatorio de cada documento: el comparendo es citación, no prueba concluyente ni sanción.",
        ]),
        section("5. PETICIONES PARA LA AUDIENCIA", bullets=[
            "Decretar, practicar e incorporar las pruebas solicitadas.",
            "Permitir contradicción y entrega de copia íntegra antes de decidir.",
            "Valorar expresamente el defecto de notificación y su afectación material.",
            "Abstenerse de invertir la carga sobre autoría o culpabilidad.",
            "Emitir decisión motivada y comunicar recursos, términos y canal de interposición.",
        ]),
        section("6. RESERVA DE DEFENSAS", "La comparecencia no implica confesión, aceptación, renuncia a descuentos, convalidación de irregularidades ni desistimiento de recursos o acciones. Cualquier decisión debe basarse en prueba legalmente obtenida y controvertida."),
        tr002_control("CO-TR-002-AUDIENCIA", assumptions=["La etapa permite comparecencia o fue restablecida", "El interesado puede acreditar legitimación"], sources=["Ley 769 de 2002, artículos 135 y 136", "Ley 1843 de 2017", "Constitución, artículo 29", "Sentencias T-616 de 2006 y C-321 de 2022"], red_flags=["Audiencia o recurso vencido", "Sanción firme", "Prueba pericial", "Coactivo o embargo"]),
    ]


def tr002_revocation(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD CONDICIONADA DE REVOCATORIA DIRECTA", "Modelo reservado para acto administrativo sancionatorio identificado. No sustituye recursos, no revive términos judiciales y no suspende automáticamente la ejecución."),
        section("1. IDENTIFICACIÓN DEL ACTO", table=[
            ("Campo", "Dato", "Control"),
            ("Resolución", val(a,"resolution_number","RES-2026-4455"), "Obtener copia íntegra"),
            ("Fecha", val(a,"resolution_date","30/06/2026"), "Verificar expedición"),
            ("Notificación", val(a,"resolution_notice","No acreditada"), "Modalidad, fecha y soporte"),
            ("Firmeza", val(a,"resolution_final","Por verificar"), "Recursos y constancia"),
            ("Cobro", val(a,"coactive","No informado"), "Persuasivo/coactivo/embargo"),
            ("Demanda", val(a,"judicial","No informada"), "Caducidad y auto admisorio"),
        ]),
        section("2. FILTRO DE PROCEDENCIA", table=[
            ("Pregunta", "Consecuencia"),
            ("¿Se interpusieron recursos?", "Revisar límite del artículo 94 del CPACA para causal de oposición manifiesta"),
            ("¿Caducó el control judicial?", "Puede limitar la causal primera a solicitud de parte"),
            ("¿Hay demanda y auto admisorio notificado?", "Revisar oportunidad del artículo 95"),
            ("¿Existe pago o acuerdo?", "Analizar efectos, restitución y actos posteriores por separado"),
            ("¿Hay coactivo o embargo?", "La petición no suspende; activar defensa inmediata"),
        ]),
        section("3. CAUSALES A DESARROLLAR SOLO SI SE PRUEBAN", bullets=[
            "Oposición manifiesta a la Constitución o a la ley, considerando límites de procedencia.",
            "Inconformidad con el interés público o social.",
            "Agravio injustificado por decisión adoptada sin oportunidad real de defensa.",
            "Hechos o documentos nuevos que demuestren notificación defectuosa, error de identidad o ausencia de imputación.",
            "Decisión oficial firme sobre SAST individualmente aplicable, cuando exista y corresponda al periodo.",
        ]),
        section("4. FUNDAMENTOS DEL CASO", bullets=[
            "La cronología no acredita envío, entrega o aviso conforme al artículo 8 de la Ley 1843 de 2017.",
            "La decisión se habría adoptado antes del conocimiento real y sin acceso efectivo a pruebas.",
            "No está acreditada la imputación personal y culpable del sancionado.",
            "La autoridad debe explicar por qué la irregularidad no afectó la defensa o cuál mecanismo de restablecimiento aplicó.",
        ]),
        section("5. SOLICITUDES", bullets=[
            "Verificar competencia, procedencia y causal aplicable.",
            "Revocar, modificar o corregir el acto si se configuran los presupuestos legales.",
            "Valorar una suspensión voluntaria de actuaciones de cobro cuando exista fundamento y competencia, sin presumirla.",
            "Restablecer oportunidades de comparecencia y descuento cuando sea jurídicamente procedente.",
            "Actualizar SIMIT/RUNT después de la decisión y certificar el cambio.",
            "Resolver dentro del término legal de dos meses y comunicar que contra la decisión no procede recurso.",
        ]),
        section("6. EFECTOS Y ADVERTENCIAS", "La solicitud ni su decisión reviven términos para demandar ni producen silencio administrativo. Tampoco convierten automáticamente un defecto de notificación en pérdida de ejecutoriedad o devolución de pagos. El caso requiere control profesional de la vía contravencional, administrativa y judicial."),
        signature(val(a,"holder_name","ANDRÉS FELIPE RUIZ"), "SOLICITANTE"),
        tr002_control("CO-TR-002-REVOCATORIA", assumptions=["Existe acto sancionatorio individualizado", "Se conocen recursos, firmeza, pago y cobro"], sources=["CPACA, artículos 93 a 96", "Ley 1843 de 2017", "Constitución, artículo 29"], red_flags=["Caducidad judicial próxima", "Demanda admitida", "Mandamiento de pago", "Embargo", "Pago o acuerdo"]),
    ]


def tr002_correction(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("SOLICITUD DE CORRECCIÓN, ACTUALIZACIÓN Y SINCRONIZACIÓN SIMIT/RUNT", "Actuación posterior a una decisión, archivo, revocatoria, pago conciliado o evidencia habilitante. No debe usarse como sustituto de la defensa contra el acto fuente."),
        section("1. IDENTIFICACIÓN DEL REGISTRO", table=[
            ("Campo", "Dato"),
            ("Comparendo", val(a,"ticket","05001000000087654321")),
            ("Placa", val(a,"plate","ABC123")),
            ("Estado visible", val(a,"registry_status","Pendiente de pago")),
            ("Autoridad fuente", val(a,"authority","SECRETARÍA DE MOVILIDAD DE MEDELLÍN")),
            ("Decisión soporte", val(a,"supporting_decision","Resolución de archivo/revocatoria")),
            ("Firmeza", val(a,"decision_finality","Por acreditar")),
        ]),
        section("2. SOPORTE HABILITANTE", bullets=[
            "Acto íntegro y constancia de ejecutoria, firmeza o cumplimiento.",
            "Prueba de identidad y legitimación.",
            "Consulta SIMIT/RUNT fechada antes de la solicitud.",
            "Comprobante y conciliación de pago si la corrección depende de pago.",
            "Certificación de la autoridad de tránsito cuando el operador de registro no sea competente para alterar el acto fuente.",
        ]),
        section("3. SOLICITUDES", bullets=[
            "Corregir estado, valor, identificación, fecha o cualquier dato inexacto conforme al acto soporte.",
            "Retirar impedimentos o restricciones únicamente cuando exista fundamento legal y decisión aplicable.",
            "Sincronizar la novedad entre autoridad, SIMIT y RUNT.",
            "Informar fecha, lote, responsable y resultado de la transmisión.",
            "Certificar el estado final y explicar cualquier rechazo técnico o jurídico.",
            "Aplicar minimización y corrección de datos personales inexactos sin eliminar la trazabilidad legal obligatoria.",
        ]),
        section("4. MATRIZ DE VERIFICACIÓN POSTERIOR", table=[
            ("Control", "Evidencia", "Resultado"),
            ("Autoridad actualizó acto fuente", "Certificación o consulta", "Sí / no / pendiente"),
            ("SIMIT recibió novedad", "Radicado o lote", "Sí / no / error"),
            ("RUNT reflejó estado", "Consulta fechada", "Sí / no / no aplica"),
            ("Cobro fue cerrado", "Acto de terminación/archivo", "Sí / no / pendiente"),
            ("Medida fue levantada", "Oficio y registro", "Sí / no / no aplica"),
        ]),
        section("5. LÍMITES", "La corrección registral no declara la invalidez de una sanción ni sustituye el acto administrativo competente. Si no existe decisión habilitante, debe continuarse primero por la ruta de expediente, defensa, recurso o revocatoria."),
        signature(val(a,"holder_name","ANDRÉS FELIPE RUIZ"), "SOLICITANTE"),
        tr002_control("CO-TR-002-CORRECCIÓN", assumptions=["Existe decisión o soporte habilitante", "El registro consultado pertenece al mismo comparendo y autoridad"], sources=["Ley 1581 de 2012", "Ley 769 de 2002", "Acto administrativo aplicable"], red_flags=["Sin acto soporte", "Registro de otra autoridad", "Pago no conciliado", "Coactivo activo"]),
    ]


def tr002_followup(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("GUÍA DE TÉRMINOS, RADICACIÓN, REITERACIÓN Y ESCALAMIENTO", "Control operativo posterior al conocimiento de una fotodetección no notificada. Los calendarios deben calcularse con fechas reales y no con aproximaciones."),
        section("1. CALENDARIO MAESTRO", table=[
            ("Actuación", "Regla general", "Fecha del caso", "Alerta"),
            ("Envío del comparendo", "3 días hábiles desde validación", val(a,"sent_date","Por verificar"), "Brecha si excede; analizar afectación"),
            ("Comparecencia SAST", "11 días hábiles desde entrega", val(a,"appearance_deadline","Por calcular"), "No contar desde detección"),
            ("Documentos/información", "10 días desde petición", val(a,"record_deadline","Por calcular"), "Aceptación legal de entrega si no responden, con trámite posterior"),
            ("Petición general", "15 días", val(a,"petition_deadline","Por calcular"), "Exigir aviso de prórroga motivada"),
            ("Consulta", "30 días", val(a,"consultation_deadline","Por calcular"), "No confundir con petición de documentos"),
            ("Revocatoria directa", "2 meses", val(a,"revocation_deadline","Por calcular"), "No revive término judicial"),
            ("Recurso/demanda/coactivo", "Regla especial", val(a,"special_deadline","Revisión inmediata"), "Bloqueo y abogado"),
        ]),
        section("2. REGLAS DE RADICACIÓN", bullets=[
            "Usar el canal oficial y conservar cuerpo completo, anexos, tamaño, fecha, hora y número de radicado.",
            "Separar solicitud de documentos, reclamación de notificación, comparecencia, recurso, revocatoria y corrección registral.",
            "No enviar versiones incompatibles ni alegar simultáneamente desconocimiento total y aceptación de la infracción.",
            "No adjuntar datos de terceros innecesarios; enmascarar información sensible cuando corresponda.",
            "Registrar cada presentación como revisión inmutable y asociarla al comparendo correcto.",
        ]),
        section("3. RESPUESTA INCOMPLETA O AUSENTE", bullets=[
            "Comparar la respuesta con cada numeral solicitado y elaborar matriz de omisiones.",
            "Reiterar una sola vez con precisión, anexando el primer radicado y sin reiniciar artificialmente la estrategia.",
            "Para documentos no entregados en diez días, valorar el efecto previsto por la Ley 1755 y solicitar entrega dentro de los tres días siguientes.",
            "Si se invoca reserva, exigir norma expresa y valorar el recurso de insistencia.",
            "Escalar a personería, Procuraduría, Defensoría, tutela o control judicial solo tras verificar procedencia y urgencia.",
        ]),
        section("4. MATRIZ DE ESCALAMIENTO", table=[
            ("Escenario", "Riesgo", "Ruta"),
            ("Comparendo sin resolución", "Medio", "Expediente + reclamación + audiencia"),
            ("Resolución no firme", "Alto", "Recurso y revisión inmediata"),
            ("Resolución firme", "Alto", "Revocatoria condicionada y control judicial"),
            ("Cobro persuasivo", "Alto", "Verificar acto, firmeza y pago"),
            ("Mandamiento de pago", "Crítico", "Excepciones y abogado inmediato"),
            ("Embargo", "Crítico", "Atención prioritaria y medida competente"),
            ("Pago/acuerdo", "Alto", "Efectos de aceptación y ruta restitutoria"),
            ("Múltiples autoridades", "Alto", "Expedientes y calendarios separados"),
        ]),
        section("5. CONTROL DE DESCUENTOS", "Cuando se demuestre falta o indebida notificación, los términos de reducción comienzan desde la notificación válida. Debe verificarse la modalidad de aceptación, curso, porcentaje y regla vigente aplicable; pedir que la autoridad habilite el mecanismo correcto sin presentar el descuento como reconocimiento forzado de responsabilidad."),
        section("6. CRITERIOS DE CIERRE", bullets=[
            "Expediente íntegro y cronología consolidada.",
            "Oportunidad de defensa ejercida o renunciada de forma informada.",
            "Decisión motivada, recursos y firmeza identificados.",
            "SIMIT/RUNT sincronizados con la decisión.",
            "Cobro, medidas y pagos conciliados.",
            "Retención y cierre de datos conforme a política, conservando auditoría mínima.",
        ]),
        section("7. REAPERTURA", "Reabrir el caso únicamente ante nuevo acto, prueba de entrega, respuesta oficial, cambio registral, actuación de cobro, decisión judicial o fuente normativa material. Toda reapertura conserva la versión anterior y explica qué cambió."),
        tr002_control("CO-TR-002-SEGUIMIENTO", assumptions=["Cada fecha se soporta documentalmente", "El usuario mantiene canales vigentes"], sources=["Ley 1843 de 2017", "Ley 1755 de 2015", "Ley 769 de 2002", "CPACA"], red_flags=["Mandamiento de pago", "Embargo", "Proceso judicial", "Recurso próximo", "Respuesta contradictoria"]),
    ]


PRODUCTS: dict[str, dict[str, Any]] = {
    "CO-LA-001": {"title": "Liquidación laboral, reclamación y cierre", "documents": [
        ("diagnostic", "Informe técnico de diagnóstico y liquidación", la001_diagnostic),
        ("calculation", "Anexo de cálculo por concepto", la001_calculation),
        ("termination", "Matriz de terminación e indemnizaciones", la001_termination),
        ("claim", "Reclamación laboral directa", la001_claim),
        ("evidence", "Matriz probatoria, pagos y vacíos", la001_evidence),
        ("settlement", "Propuesta condicional de acuerdo", la001_settlement),
        ("followup", "Guía de radicación y escalamiento", la001_followup),
    ]},
    "CO-SA-001": {"title": "Acceso a salud, petición y escalamiento", "documents": [
        ("diagnostic", "Diagnóstico jurídico y ruta de salud", sa001_diagnostic),
        ("petition", "Derecho de petición prioritario", sa001_petition),
        ("record", "Solicitud de historia clínica", sa001_record),
        ("evidence", "Matriz de evidencia, términos y respuesta", sa001_evidence),
        ("reiteration", "Reiteración y medida urgente", sa001_reiteration),
        ("supersalud", "Reclamo ante Supersalud", sa001_supersalud),
        ("tutela_guide", "Guía de valoración de tutela", sa001_tutela_guide),
    ]},
    "CO-CD-001": {"title": "Hábeas data financiero y suplantación", "documents": [
        ("diagnostic", "Diagnóstico jurídico de reporte financiero", cd001_diagnostic),
        ("consultation", "Consulta integral de información y trazabilidad", cd001_consultation),
        ("claim", "Reclamo de actualización, rectificación o retiro", cd001_claim),
        ("identity", "Protocolo de suplantación de identidad", cd001_identity),
        ("escalation", "Reiteración y escalamiento ante autoridad", cd001_escalation),
        ("evidence", "Matriz de evidencia y responsables", cd001_evidence),
        ("deadline", "Calendario de términos, permanencia y caducidad", cd001_deadline),
    ]},
    "CO-CD-003": {"title": "Garantía, retracto y reversión del pago", "documents": [
        ("classifier", "Clasificador de mecanismos", cd003_classifier),
        ("warranty", "Reclamación de garantía", cd003_warranty),
        ("retract", "Ejercicio de retracto", cd003_retract),
        ("reversal", "Solicitud coordinada de reversión", cd003_reversal),
        ("ecommerce", "Terminación por no entrega o indisponibilidad", cd003_ecommerce),
        ("sic", "Reclamación directa y expediente para SIC", cd003_sic),
        ("evidence", "Matriz de evidencia y plazos", cd003_evidence),
    ]},
    "CO-CD-004": {"title": "Cobro, acuerdo de pago, pagaré, garantías y cierre", "documents": [
        ("diagnostic", "Diagnóstico integral de cartera", cd004_diagnostic),
        ("statement", "Estado de cuenta y memoria de liquidación", cd004_statement),
        ("collection", "Requerimiento prejurídico y propuesta", cd004_collection),
        ("agreement", "Acuerdo integral de pago", cd004_agreement),
        ("note", "Pagaré diligenciado y controlado", cd004_note),
        ("instructions", "Carta de instrucciones para pagaré", cd004_instructions),
        ("followup", "Matriz de evidencia y seguimiento", cd004_followup),
        ("closure", "Cierre, paz y salvo y cancelación", cd004_closure),
    ]},
    "CO-TR-001": {"title": "Chequeo SAST e inscripción verificada", "documents": [
        ("report", "Informe preliminar SAST", tr001_report),
        ("traceability", "Ficha de trazabilidad de fuentes", tr001_traceability),
        ("enrollment", "Inscripción verificada", tr001_enrollment),
        ("record_request", "Solicitud de expediente SAST", tr001_record_request),
        ("review", "Solicitud de revisión profesional", tr001_review),
        ("followup", "Seguimiento de decisiones SAST", tr001_followup),
    ]},
    "CO-TR-002": {"title": "Fotodetección, notificación y defensa", "documents": [
        ("diagnostic", "Diagnóstico de etapa y notificación", tr002_diagnostic),
        ("record", "Solicitud integral de expediente", tr002_record),
        ("notice_claim", "Reclamación por notificación", tr002_notice_claim),
        ("hearing", "Audiencia y pruebas", tr002_hearing),
        ("revocation", "Revocatoria directa condicional", tr002_revocation),
        ("correction", "Corrección SIMIT/RUNT", tr002_correction),
        ("followup", "Guía de términos y escalamiento", tr002_followup),
    ]},
}
