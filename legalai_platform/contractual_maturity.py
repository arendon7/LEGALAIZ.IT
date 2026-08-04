from __future__ import annotations

"""Biblioteca contractual versionada para los cuatro productos contractuales P0.

M13 regenera y revalida CO-EM-004. CO-LA-002 y CO-AR-001 conservan su
revalidación M11 y CO-EM-003 conserva M12. Los demás productos mantienen el
contenido aprobado previamente. La capa no automatiza decisiones litigiosas ni
sustituye la revisión del caso concreto.
"""

from datetime import date
from typing import Any, Iterable
import re

BUILD_ID = "M13-CONFIDENTIALITY-IP-DATA-AI-REVALIDATION-2026-07-31"
MODEL_VERSION = "M4.0"

ORDINALS = [
    "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
    "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
    "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
    "DÉCIMA SÉPTIMA", "DÉCIMA OCTAVA", "DÉCIMA NOVENA", "VIGÉSIMA",
    "VIGÉSIMA PRIMERA", "VIGÉSIMA SEGUNDA", "VIGÉSIMA TERCERA",
    "VIGÉSIMA CUARTA", "VIGÉSIMA QUINTA", "VIGÉSIMA SEXTA", "VIGÉSIMA SÉPTIMA",
    "VIGÉSIMA OCTAVA", "VIGÉSIMA NOVENA", "TRIGÉSIMA", "TRIGÉSIMA PRIMERA",
    "TRIGÉSIMA SEGUNDA", "TRIGÉSIMA TERCERA", "TRIGÉSIMA CUARTA",
    "TRIGÉSIMA QUINTA", "TRIGÉSIMA SEXTA", "TRIGÉSIMA SÉPTIMA",
    "TRIGÉSIMA OCTAVA", "TRIGÉSIMA NOVENA", "CUADRAGÉSIMA",
    "CUADRAGÉSIMA PRIMERA", "CUADRAGÉSIMA SEGUNDA", "CUADRAGÉSIMA TERCERA",
    "CUADRAGÉSIMA CUARTA", "CUADRAGÉSIMA QUINTA", "CUADRAGÉSIMA SEXTA",
    "CUADRAGÉSIMA SÉPTIMA", "CUADRAGÉSIMA OCTAVA", "CUADRAGÉSIMA NOVENA",
    "QUINCUAGÉSIMA", "QUINCUAGÉSIMA PRIMERA", "QUINCUAGÉSIMA SEGUNDA",
    "QUINCUAGÉSIMA TERCERA", "QUINCUAGÉSIMA CUARTA", "QUINCUAGÉSIMA QUINTA",
    "QUINCUAGÉSIMA SEXTA", "QUINCUAGÉSIMA SÉPTIMA", "QUINCUAGÉSIMA OCTAVA",
    "QUINCUAGÉSIMA NOVENA", "SEXAGÉSIMA",
]


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


def cop(raw: Any, default: int = 0) -> str:
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
    result: dict[str, Any] = {"heading": heading, "page_break_before": page_break_before}
    if text:
        result["text"] = text
    if bullets:
        result["bullets"] = list(bullets)
    if table:
        result["table"] = table
    if kind:
        result["_type"] = kind
    return result


def clause(index: int, title: str, text: str, *, bullets: Iterable[str] | None = None,
           table: list[tuple[str, ...]] | None = None, page_break_before: bool = False) -> dict[str, Any]:
    return section(
        f"CLÁUSULA {ORDINALS[index - 1]}. {title}", text,
        bullets=bullets, table=table, page_break_before=page_break_before,
    ) | {"clause_number": index}


def intro(title: str, parties: str, considerations: Iterable[str]) -> list[dict[str, Any]]:
    return [
        section(title, parties, page_break_before=True),
        section("CONSIDERACIONES", bullets=considerations),
    ]


def signature(a_name: str, a_label: str, b_name: str, b_label: str) -> dict[str, Any]:
    return {
        "heading": "FIRMAS",
        "_type": "signature",
        "parties": [
            {"label": a_label, "name": a_name},
            {"label": b_label, "name": b_name},
        ],
    }


def control(product: str, clauses: int, sources: Iterable[str]) -> dict[str, Any]:
    if product.startswith("CO-EM-003"):
        model_version = "M12.1"
    elif product.startswith(("CO-LA-002", "CO-AR-001")):
        model_version = "M11.1"
    else:
        model_version = MODEL_VERSION
    return section(
        "CONTROL DE PUBLICACIÓN, FUENTES Y REVISIÓN",
        (
            f"Modelo contractual profundo {model_version} del producto {product}. "
            "La biblioteca fue aprobada para uso profesional controlado, pero la liberación de cada documento exige "
            "verificar identidad, capacidad, hechos, anexos, cuantías, fechas, vigencia normativa, riesgo y coherencia "
            "con la ejecución real. La aprobación multietapa fue realizada por un responsable único y no equivale a "
            "revisión externa independiente. Los asuntos litigiosos, sancionatorios, de alto impacto o con riesgo rojo "
            "deben escalarse a revisión profesional individualizada."
        ),
        bullets=[f"Fuente oficial: {source}" for source in sources],
        kind="control",
    )


# ---------------------------------------------------------------------------
# CO-EM-003 - PRESTACIÓN DE SERVICIOS
# ---------------------------------------------------------------------------

def services_contract_sections(a: dict[str, Any], result: Any = None) -> list[dict[str, Any]]:
    contratante = val(a, "party_a", val(a, "employer_name", "EL CONTRATANTE"))
    contratista = val(a, "party_b", "EL CONTRATISTA")
    objeto = val(a, "object", "prestar servicios profesionales especializados conforme al alcance y entregables del Anexo No. 1")
    ciudad = val(a, "contract_city", "Medellín")
    inicio = val(a, "start_date", "la fecha de firma")
    fin = val(a, "end_date", "la fecha indicada en la ficha contractual")
    honorarios = cop(a.get("fees"), 45_000_000)
    dias_aceptacion = val(a, "acceptance_days", "cinco (5)")
    esquema_pago = val(a, "payment_scheme", "pagos contra hitos aceptados")
    exclusividad = yes(a, "exclusivity")
    datos = yes(a, "personal_data", True)
    pi = yes(a, "intellectual_property", True)
    subcontratacion = yes(a, "subcontracting", False)
    parts = (
        f"Entre {contratante}, identificado en la ficha contractual y quien para efectos del presente documento se denomina "
        f"EL CONTRATANTE, y {contratista}, identificado en la misma ficha y quien se denomina EL CONTRATISTA, se celebra "
        f"en {ciudad} el presente CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES. Las partes declaran capacidad, "
        "consentimiento informado y comprensión de que la naturaleza del vínculo depende de la realidad de su ejecución."
    )
    sections = intro(
        "CONTRATO DE PRESTACIÓN DE SERVICIOS INDEPENDIENTES",
        parts,
        [
            f"EL CONTRATANTE requiere apoyo especializado para {objeto} y no la provisión permanente de un cargo subordinado.",
            "EL CONTRATISTA declara contar con conocimiento, organización y autonomía para ejecutar el encargo por su cuenta y riesgo.",
            "Las partes desean definir resultados, gobierno, aceptación, pagos, propiedad intelectual, información, datos, seguridad, transición y cierre.",
            "La coordinación del resultado no autoriza controles propios de subordinación; cualquier desviación será registrada y corregida.",
        ],
    )
    rows: list[tuple[str, str]] = [
        ("OBJETO", f"EL CONTRATISTA se obliga a ejecutar con autonomía técnica, administrativa y operativa los servicios consistentes en {objeto}. La obligación se delimita por entregables verificables, criterios de aceptación, exclusiones y dependencias. Ninguna comunicación informal ampliará el objeto ni podrá convertirlo en disponibilidad personal indefinida."),
        ("DOCUMENTOS INTEGRANTES", "Integran el contrato la ficha de partes, el Anexo No. 1 de alcance, la propuesta aceptada, el cronograma, las matrices de aceptación y riesgos, las actas de cambio, los anexos de confidencialidad, propiedad intelectual, datos y seguridad que resulten aplicables. En caso de contradicción prevalecerá el contrato, luego la adenda más reciente y después los anexos en su ámbito específico."),
        ("ALCANCE Y EXCLUSIONES", "El alcance comprende solo las actividades indispensables para producir los resultados descritos. Se excluyen expresamente labores no estimadas, soporte indefinido, desplazamientos no aprobados, licencias de terceros, costos extraordinarios y cualquier actividad que altere materialmente esfuerzo, riesgo o perfil profesional. Las exclusiones no impiden cooperación razonable para aclarar o corregir entregables incluidos."),
        ("ENTREGABLES Y TRAZABILIDAD", "Cada entregable tendrá nombre, formato, responsable, fecha o hito, insumos, dependencias, criterio objetivo de aceptación y repositorio de entrega. El contratista conservará evidencia suficiente de versión, envío, observaciones, corrección y aceptación. Cuando un entregable sea evolutivo, la matriz distinguirá versión mínima, mejoras opcionales y deuda aceptada."),
        ("AUTONOMÍA E INDEPENDENCIA", "EL CONTRATISTA organizará métodos, secuencia, recursos y tiempos de ejecución, sin jornada laboral, potestad disciplinaria ni reglamento interno. Podrá prestar servicios a terceros, salvo conflicto específico documentado. La supervisión del resultado, la seguridad de acceso, las reuniones acordadas y los estándares de calidad no constituyen subordinación si no se utilizan para imponer disponibilidad o dirección permanente sobre la forma de trabajar."),
        ("PREVENCIÓN DEL RIESGO DE LABORALIDAD", "Las partes revisarán trimestralmente indicadores de subordinación material: horario impuesto, exclusividad general, control disciplinario, inserción orgánica, órdenes permanentes, dependencia económica no prevista, medios esenciales exclusivos y evaluación personal propia de empleados. Si aparece un indicador, deberán ajustar la ejecución o analizar la formalización laboral. La denominación contractual no prevalecerá sobre la realidad."),
        ("EQUIPO Y PERSONAL", "EL CONTRATISTA definirá el equipo idóneo y responderá por su selección, dirección, pagos, seguridad social y obligaciones. El contratante podrá objetar razonadamente a una persona por seguridad, conflicto, incumplimiento o falta de competencia, sin asumir dirección laboral. La sustitución de personal clave deberá conservar experiencia y continuidad, documentarse y no disminuir el nivel de servicio."),
        ("SUBCONTRATACIÓN", ("Se autoriza la subcontratación limitada descrita en el Anexo No. 1. EL CONTRATISTA seguirá siendo responsable y trasladará obligaciones de confidencialidad, datos, seguridad y propiedad intelectual." if subcontratacion else "No se permite subcontratar actividades sustanciales sin autorización previa y escrita. La autorización no libera al contratista y debe identificar al tercero, alcance, ubicación, acceso a información y medidas de control.")),
        ("LUGAR, DISPONIBILIDAD Y COORDINACIÓN", "Los servicios se ejecutarán principalmente con medios y desde lugares definidos por EL CONTRATISTA. Los accesos a instalaciones, reuniones o ventanas de coordinación se pactan por necesidad del proyecto y no constituyen jornada. Las partes evitarán mensajes fuera de ventanas razonables salvo incidente crítico previamente definido y con mecanismo de compensación o ajuste de carga."),
        ("PLAZO", f"El contrato inicia el {inicio} y termina el {fin}. La prórroga deberá constar por escrito, identificar entregables pendientes, plazo, honorarios y riesgos. La ejecución posterior sin adenda no implica renovación automática ni aceptación de actividades nuevas; deberá regularizarse antes de continuar, sin perjuicio de reconocer prestaciones efectivamente recibidas."),
        ("CRONOGRAMA Y DEPENDENCIAS", "El cronograma será una línea base controlada. Los retrasos causados por información incompleta, decisiones tardías, indisponibilidad de terceros, fuerza mayor o cambios aprobados desplazarán los hitos en proporción demostrable. El contratista deberá avisar el impacto tan pronto sea razonablemente identificable y proponer mitigaciones."),
        ("HONORARIOS", f"Los honorarios totales son {honorarios}, bajo el esquema {esquema_pago}. El valor remunera alcance y resultados, no disponibilidad personal ni jornada. Incluye costos ordinarios del contratista salvo rubros discriminados. Toda modificación económica requiere instrumento escrito que identifique causa, base de cálculo, impuestos, hito y responsable de autorización."),
        ("FACTURACIÓN, SOPORTES Y PAGO", "Cada cobro se acompañará de factura o cuenta de cobro, soporte del hito, aceptación o evidencia de disponibilidad para revisión y documentos tributarios o de seguridad social exigibles. El plazo de pago inicia con la recepción completa. Las observaciones deberán ser concretas y no permitirán retener sumas no controvertidas. El contratante informará retenciones y entregará certificados dentro del término legal."),
        ("GASTOS Y REEMBOLSOS", "Solo se reembolsarán gastos extraordinarios previamente autorizados, razonables, directamente asociados al encargo y soportados. La autorización deberá fijar tope, moneda, política y tratamiento tributario. Los gastos ordinarios de operación se entienden incorporados en los honorarios."),
        ("ACEPTACIÓN", f"EL CONTRATANTE contará con {dias_aceptacion} días hábiles desde la entrega completa para aceptar u observar. Las observaciones indicarán el requisito incumplido, evidencia y corrección esperada. El uso productivo sin reserva podrá constituir aceptación, salvo defectos ocultos. Una preferencia nueva o modificación del alcance no se calificará como defecto."),
        ("CORRECCIÓN Y GARANTÍA DEL SERVICIO", "El contratista corregirá, sin costo adicional, los incumplimientos demostrables frente a criterios pactados reportados dentro del periodo de garantía definido en el anexo. La garantía no cubre cambios de terceros, alteraciones del contratante, uso distinto, insumos incorrectos ni nuevos requerimientos. La corrección tendrá alcance proporcional y no supone garantía de resultados externos."),
        ("GOBIERNO DEL CONTRATO", "Cada parte designará un responsable contractual y uno operativo, con facultades delimitadas. Las decisiones relevantes quedarán en acta o registro electrónico. Solo los representantes autorizados podrán modificar honorarios, plazo, responsabilidad, propiedad intelectual, tratamiento de datos, exclusividad o terminación."),
        ("REUNIONES Y COMUNICACIONES", "Las reuniones tendrán propósito, asistentes y decisiones. Las actas se entenderán aceptadas si no se formulan observaciones razonadas dentro de tres días hábiles, pero no modificarán materias reservadas a adenda. Los canales oficiales serán los registrados en la ficha; la mensajería instantánea sirve para coordinación y no reemplaza aprobaciones formales."),
        ("CONTROL DE CAMBIOS", "Toda solicitud de cambio se registrará con descripción, motivación, prioridad, impacto en alcance, esfuerzo, cronograma, precio, seguridad, datos, propiedad intelectual y riesgos. El contratista no deberá ejecutar el cambio antes de la aprobación. En urgencias se permitirá una orden provisional con límite de tiempo y costo, seguida de formalización."),
        ("OBLIGACIONES DEL CONTRATISTA", "Además de ejecutar el objeto, deberá asignar personal competente, advertir riesgos, conservar evidencia, cumplir estándares, proteger activos, mantener continuidad razonable, informar conflictos, corregir incumplimientos y entregar resultados en formatos utilizables. No ocultará dependencias críticas ni asumirá compromisos que razonablemente no pueda cumplir."),
        ("OBLIGACIONES DEL CONTRATANTE", "Suministrará información, accesos, decisiones, responsables y retroalimentación oportunos; verificará su facultad para compartir materiales y datos; pagará; facilitará pruebas y no impondrá subordinación. Responderá por la legalidad y exactitud de instrucciones, contenidos y decisiones que sean de su exclusivo control."),
        ("SEGURIDAD SOCIAL DEL CONTRATISTA", "Cuando EL CONTRATISTA sea persona natural que ejecute servicios personales y obtenga ingresos iguales o superiores al mínimo legal aplicable, realizará sus aportes al Sistema de Seguridad Social Integral mes vencido sobre una base mínima equivalente al cuarenta por ciento (40 %) del valor mensualizado del contrato, sin incluir IVA cuando haya lugar, respetando los topes y reglas vigentes. La cláusula no altera la naturaleza real del vínculo ni exonera al contratante de las verificaciones que legalmente le correspondan."),
        ("VERIFICACIÓN DE APORTES", "EL CONTRATISTA entregará únicamente los soportes pertinentes para acreditar afiliación y pago de salud, pensión y riesgos laborales cuando sean exigibles. EL CONTRATANTE verificará correspondencia entre periodo, ingreso base y ejecución, protegerá los datos contenidos en la planilla y no condicionará pagos no controvertidos a requisitos distintos de los legales o contractualmente pactados. Las diferencias deberán aclararse antes de realizar descuentos o reportes."),
        ("RIESGOS LABORALES Y SEGURIDAD Y SALUD EN EL TRABAJO", "Cuando el contrato formal de prestación de servicios quede comprendido en el Sistema General de Riesgos Laborales, EL CONTRATANTE gestionará la afiliación como mínimo un día antes del inicio y registrará tiempo, modo, lugar, honorarios y clase de riesgo. La cotización se determinará por el mayor riesgo entre el centro de trabajo y la actividad ejecutada. El pago corresponderá al contratista para riesgos I, II o III y al contratante para riesgos IV o V, salvo modificación normativa. Ambas partes cumplirán medidas de prevención, reporte de incidentes y coordinación del SG-SST sin convertirlas en subordinación laboral."),
        ("TRIBUTOS, RETENCIONES, FACTURACIÓN Y PERMISOS", "Cada parte asumirá los impuestos, retenciones, registros y permisos que legalmente le correspondan. La factura o cuenta de cobro discriminará honorarios, IVA y gastos cuando aplique. Las retenciones se practicarán con fundamento identificable y se entregarán los certificados respectivos. La distribución tributaria no modifica honorarios ni transfiere obligaciones propias sin acuerdo escrito válido."),
        ("CONFLICTOS DE INTERÉS", "EL CONTRATISTA revelará conflictos reales o potenciales que comprometan independencia, información o competencia. Las partes definirán barreras, recusación, separación de equipos o terminación del componente afectado. No se exigirá revelar información confidencial de terceros más allá de lo necesario para evaluar el riesgo."),
        ("EXCLUSIVIDAD Y NO COMPETENCIA", ("La exclusividad se limita al proyecto, clientes o materias identificados, durante el plazo y con contraprestación incorporada. No impide actividades generales que no generen conflicto ni uso de información." if exclusividad else "No existe exclusividad general. EL CONTRATISTA puede atender a terceros, siempre que evite conflictos, incumplimientos y uso de información reservada. Cualquier restricción específica deberá ser escrita, proporcionada, temporal y materialmente delimitada.")),
        ("CONFIDENCIALIDAD", "La información confidencial se define por su naturaleza, contexto o identificación. Solo se utilizará para el contrato y se compartirá con personas que necesiten conocerla y estén obligadas. Se aplicarán medidas razonables, se registrarán revelaciones exigidas por autoridad y se devolverá o eliminará la información al cierre, salvo conservación legal o probatoria."),
        ("SECRETOS EMPRESARIALES", "Las partes identificarán activos que constituyan secretos empresariales y aplicarán medidas reforzadas de acceso, segmentación, trazabilidad y salida. La protección se mantendrá mientras subsistan los requisitos legales. No se considerará secreto lo público, legítimamente conocido, desarrollado independientemente o recibido lícitamente sin restricción."),
        ("DATOS PERSONALES", ("Cuando se traten datos personales, las partes documentarán roles, finalidades, instrucciones, categorías, titulares, medidas, incidentes, subencargados, transferencias y eliminación. El contratista no utilizará datos para fines propios incompatibles y apoyará la atención de derechos y requerimientos." if datos else "No se prevé tratamiento sistemático de datos personales. Si surge, se suspenderá el acceso hasta documentar roles, finalidades, instrucciones, medidas y base jurídica aplicable.")),
        ("SEGURIDAD DE LA INFORMACIÓN", "Se aplicarán controles proporcionales: mínimo privilegio, autenticación, gestión de credenciales, cifrado cuando corresponda, copias, registro, actualización, segregación y devolución de accesos. Cada parte notificará vulnerabilidades relevantes y no desactivará controles sin autorización documentada."),
        ("INCIDENTES", "El incidente se notificará sin dilación indebida por el canal acordado, indicando hechos conocidos, activos, datos, impacto, contención y próximos pasos. Las partes preservarán evidencia, coordinarán comunicaciones y no admitirán responsabilidad frente a terceros sin autorización. La cooperación no altera la asignación final de costos o responsabilidad."),
        ("PROPIEDAD INTELECTUAL PREEXISTENTE", "Cada parte conserva la titularidad sobre herramientas, metodologías, marcas, software, contenidos y conocimiento preexistentes. El anexo identificará activos relevantes y concederá únicamente las licencias necesarias para usar el entregable. Ninguna entrega transfiere activos preexistentes por implicación."),
        ("RESULTADOS Y DERECHOS PATRIMONIALES", ("Los resultados protegibles se regirán por el anexo de propiedad intelectual, que identificará obras, autores, modalidades de explotación, territorio, duración, contraprestación y limitaciones. Toda cesión deberá constar por escrito y no abarcará de forma indeterminada producción futura." if pi else "No se pacta cesión general. Cada parte conserva sus derechos y el contratante recibe una licencia suficiente para el uso interno del resultado descrito, en los términos del anexo.")),
        ("SOFTWARE, COMPONENTES DE TERCEROS Y CÓDIGO ABIERTO", "El contratista identificará componentes de terceros y licencias relevantes, evitará incorporar elementos incompatibles y entregará inventario cuando el resultado incluya software. Las obligaciones copyleft, atribuciones, límites de uso, dependencias de nube o modelos de IA deberán informarse antes de la aceptación."),
        ("INTELIGENCIA ARTIFICIAL Y SERVICIOS EN LA NUBE", "No se ingresará información reservada o datos personales en herramientas de IA o nube no autorizadas. El anexo definirá proveedores, ubicación, retención, entrenamiento, propiedad de entradas y salidas, revisión humana y riesgos de terceros. Las salidas deberán ser verificadas antes de integrarse a entregables jurídicos, financieros, técnicos o regulatorios."),
        ("LICENCIAS Y USO", "La licencia o cesión sobre entregables será efectiva conforme a los términos pactados y, cuando dependa del pago, después del pago de las sumas correspondientes. Se precisarán usuarios, finalidades, territorio, duración, modificación, sublicencia y entrega de fuentes. Los derechos no expresamente otorgados permanecen con su titular."),
        ("DECLARACIONES Y GARANTÍAS", "Cada parte declara capacidad y facultades. El contratista garantiza autoría o licencias suficientes y diligencia profesional, sin prometer ausencia absoluta de defectos o resultados dependientes de terceros. El contratante garantiza que los materiales e instrucciones que suministra pueden ser utilizados para el objeto."),
        ("RESPONSABILIDAD", "Cada parte responde por daños directos, ciertos y demostrados causados por incumplimiento imputable, con los límites válidamente pactados. No se excluye responsabilidad que legalmente no pueda limitarse, ni dolo o culpa grave. Las categorías especiales —confidencialidad, datos, propiedad intelectual o seguridad— se tratarán separadamente y de forma proporcionada."),
        ("INDEMNIDAD", "La parte que aporte materiales, instrucciones o actuaciones que generen reclamaciones de terceros asumirá la defensa y costos en la medida de su responsabilidad, siempre que reciba aviso, control razonable y cooperación. No se aceptará acuerdo que imponga obligaciones a la otra parte sin su consentimiento."),
        ("SEGUROS", "Cuando el riesgo lo justifique, el Anexo No. 1 indicará pólizas, coberturas, límites, vigencia y certificados. La existencia de seguro no amplía responsabilidad ni sustituye controles. La falta de póliza exigida podrá suspender actividades de riesgo hasta su subsanación."),
        ("CONTINUIDAD Y RESPALDO", "El contratista mantendrá procedimientos razonables de respaldo, sustitución de personal crítico y recuperación de entregables en curso. Los niveles de continuidad dependerán del servicio y deberán estar en el anexo; no se presumen niveles de disponibilidad propios de un servicio administrado permanente."),
        ("SUSPENSIÓN", "Podrá suspenderse por mora material, falta de insumos esenciales, riesgo de seguridad, orden de autoridad o fuerza mayor. La parte afectada avisará, limitará el impacto y conservará lo producido. La suspensión ajustará cronograma y costos demostrables, pero no autoriza retención abusiva de información o entregables pagados."),
        ("TERMINACIÓN ANTICIPADA", "El contrato terminará por acuerdo, incumplimiento no subsanado, imposibilidad prolongada, conflicto insuperable, riesgo ilegal o las causales pactadas. Salvo urgencia, se otorgará un plazo razonable de subsanación. La terminación por conveniencia requerirá preaviso y pago de entregables aceptados, trabajo verificable en curso y compromisos no cancelables autorizados."),
        ("TRANSICIÓN Y ENTREGA", "Al cierre, el contratista entregará versiones, archivos, claves transferibles, inventarios, documentación, pendientes, riesgos y conocimiento acordado. El contratante verificará recepción y revocará accesos. La asistencia adicional se cotizará salvo que corresponda a obligaciones ya incluidas."),
        ("LIQUIDACIÓN Y ACTA DE CIERRE", "Las partes conciliarán entregables, aceptaciones, pagos, activos, información, datos, propiedad intelectual, reclamos y obligaciones supervivientes. El acta no constituirá renuncia general a derechos desconocidos ni impedirá reclamar defectos ocultos dentro del periodo aplicable."),
        ("FUERZA MAYOR", "La parte afectada notificará el evento, impacto, medidas y duración estimada. Deberá mitigar y reanudar cuando sea posible. Si el impedimento supera el periodo pactado o frustra el objeto, cualquiera podrá terminar sin sanción, conservando pagos por prestaciones útiles recibidas."),
        ("CUMPLIMIENTO, ÉTICA Y ANTICORRUPCIÓN", "Las partes cumplirán normas aplicables, políticas comunicadas y prohibiciones de soborno, fraude, lavado, discriminación y acoso. Ninguna política interna podrá modificar unilateralmente el contrato. Las alertas de integridad se investigarán con confidencialidad, debido proceso y protección frente a represalias."),
        ("NOTIFICACIONES", "Las notificaciones contractuales se enviarán a los datos de la ficha por medios que permitan acreditar contenido, fecha y recepción. El cambio de dirección deberá informarse. Las comunicaciones operativas no reemplazan notificaciones de incumplimiento, terminación, reclamación o cambio contractual."),
        ("SOLUCIÓN ESCALONADA DE CONTROVERSIAS", "Las partes intentarán negociación entre responsables, luego reunión de representantes con capacidad decisoria y, si se pacta, mediación o conciliación. Las medidas urgentes, cautelares o de protección de información no requieren agotar etapas incompatibles con su finalidad. El mecanismo final y jurisdicción serán los indicados en la ficha."),
        ("LEY APLICABLE Y DOMICILIO", f"El contrato se interpreta conforme al derecho colombiano y tendrá como domicilio contractual {ciudad}, sin perjuicio de las reglas imperativas de competencia. La elección de ley no altera normas de orden público aplicables a datos, trabajo, consumidores, propiedad intelectual o tributos."),
        ("INTEGRIDAD, MODIFICACIONES Y NULIDAD PARCIAL", "El contrato y sus anexos contienen el acuerdo sobre su objeto. Toda modificación requiere forma escrita y autorización. La invalidez de una estipulación no afectará las demás; las partes la sustituirán por una válida que preserve razonablemente su finalidad sin desconocer normas imperativas."),
        ("FIRMA ELECTRÓNICA Y EJEMPLARES", "El documento podrá firmarse de forma manuscrita o electrónica mediante método que permita identificar al firmante, expresar aprobación y conservar integridad y trazabilidad. Las copias y contrapartes forman un solo instrumento. La plataforma conservará versión, evidencias y aceptación según permisos y política de retención."),
    ]
    for idx, (title, text) in enumerate(rows, 1):
        sections.append(clause(idx, title, text))
    sections += [
        signature(contratante, "EL CONTRATANTE", contratista, "EL CONTRATISTA"),
        control("CO-EM-003", len(rows), [
            "Código Sustantivo del Trabajo, artículos 22 y 23, sobre elementos del contrato laboral y primacía de la realidad.",
            "Ley 2277 de 2022, artículo 89, y Decreto 780 de 2016 sobre IBC y pago mes vencido de independientes.",
            "Ley 1562 de 2012 y Decreto 1072 de 2015 sobre afiliación, cobertura y pago en riesgos laborales.",
            "Ley 23 de 1982, Ley 1450 de 2011, Ley 1915 de 2018 y régimen andino sobre propiedad intelectual.",
            "Ley 1581 de 2012 y reglamentación compilada sobre protección de datos personales.",
            "Ley 527 de 1999 sobre mensajes de datos y firma electrónica.",
        ]),
    ]
    return sections


def service_scope_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO NO. 1 - ALCANCE, ENTREGABLES Y CRONOGRAMA", "Este anexo convierte el objeto general en resultados verificables y evita ampliaciones implícitas."),
        section("1. OBJETIVO OPERATIVO", val(a, "object", "Definir el resultado verificable que debe obtener el proyecto, su usuario, restricción y criterio de éxito.")),
        section("2. MATRIZ DE ENTREGABLES", table=[("Entregable", "Descripción / formato / responsable / fecha / criterio de aceptación"), ("E-01", val(a, "deliverable_1", "Documento o resultado principal definido en la ficha")), ("E-02", val(a, "deliverable_2", "Documentación, capacitación o transferencia asociada")), ("E-03", val(a, "deliverable_3", "Cierre, repositorio y evidencia de aceptación"))]),
        section("3. EXCLUSIONES", bullets=["Actividades no descritas ni indispensables para los entregables.", "Soporte permanente o disponibilidad fuera del plazo.", "Licencias, viajes y compras de terceros no presupuestadas.", "Correcciones derivadas de cambios o insumos incorrectos del contratante."]),
        section("4. DEPENDENCIAS DEL CONTRATANTE", bullets=["Designar responsables con capacidad de decisión.", "Entregar información y accesos lícitos y completos.", "Revisar dentro del término contractual.", "Gestionar decisiones y terceros bajo su control."]),
        section("5. CRITERIOS DE ACEPTACIÓN", "Cada criterio debe ser observable, reproducible y vinculado a un entregable. Las preferencias nuevas se procesan como cambios y no como defectos."),
        section("6. CRONOGRAMA BASE", table=[("Hito", "Fecha / dependencia / evidencia"), ("Inicio", val(a, "start_date", "Fecha de firma")), ("Entrega intermedia", val(a, "milestone_date", "Según ficha")), ("Cierre", val(a, "end_date", "Según ficha"))]),
        section("7. GOBIERNO Y RACI", table=[("Actividad", "Responsable / aprobador / consultado / informado"), ("Definición de alcance", "Ambas partes"), ("Ejecución", "Contratista"), ("Aceptación", "Contratante"), ("Control de cambios", "Responsables contractuales")]),
        section("8. RIESGOS", table=[("Riesgo", "Probabilidad / impacto / mitigación / responsable"), ("Información incompleta", "Validación inicial y registro de supuestos"), ("Cambio de terceros", "Reserva de cronograma y control de cambios"), ("Acceso a datos", "Mínimo privilegio y anexo de tratamiento")]),
        section("9. MATRIZ DE EJECUCIÓN Y RIESGOS LABORALES", table=[("Variable", "Definición verificable"), ("Tiempo", "Ventanas de coordinación, hitos y duración; no jornada laboral"), ("Modo", "Métodos autónomos, estándares de resultado y controles de seguridad"), ("Lugar", "Sitios autorizados y condiciones de acceso"), ("ARL", "Administradora, clase de riesgo, fecha de afiliación y responsable del pago")]),
        section("10. SEGURIDAD SOCIAL Y SOPORTES", table=[("Control", "Dato / responsable / periodicidad"), ("IBC", "40 % del valor mensualizado sin IVA, sujeto a topes legales"), ("PILA", "Periodo ejecutado y pago mes vencido"), ("Verificación", "Soporte pertinente, minimizado y coherente con el contrato")]),
        section("11. CONTROL DE CAMBIOS", "Toda modificación deberá identificar alcance anterior, nuevo resultado, esfuerzo, fecha, costo, riesgos, datos y propiedad intelectual. No se ejecutará sin aprobación trazable."),
        section("12. ACTA DE ACEPTACIÓN", "La aceptación registrará versión, fecha, criterio verificado, observaciones, reservas y responsable. La aceptación parcial no implica aceptación de componentes no revisados."),
        control("CO-EM-003-ANEXO-ALCANCE", 12, ["Contrato principal, Código Sustantivo del Trabajo, Decreto 780 de 2016 y Decreto 1072 de 2015."]),
    ]


def service_confidentiality_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return nda_sections(a, bilateral=True, source="CO-EM-003 - anexo de confidencialidad M12")


def service_ip_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return ip_annex_sections(a, source="CO-EM-003 - anexo PI M12")


def service_data_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return data_annex_sections(a, source="CO-EM-003 - anexo de datos M12")


def service_closure_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return closure_act_sections(a)


# ---------------------------------------------------------------------------
# CO-LA-002 - CONTRATO DE TRABAJO
# ---------------------------------------------------------------------------

def employment_contract_sections(a: dict[str, Any], result: Any = None, forced_modality: str | None = None) -> list[dict[str, Any]]:
    empleador = val(a, "employer_name", val(a, "party_a", "EL EMPLEADOR"))
    trabajador = val(a, "employee_name", val(a, "party_b", "EL TRABAJADOR"))
    cargo = val(a, "position", "cargo descrito en el Anexo de Funciones")
    ciudad = val(a, "city", "Medellín")
    salario = cop(a.get("salary"), 2_500_000)
    inicio = val(a, "start_date", "la fecha de firma")
    modalidad = forced_modality or val(a, "contract_type", "término indefinido")
    trabajo_remoto = yes(a, "remote_work") or "remot" in val(a, "work_mode", "").casefold()
    parts = (
        f"Entre {empleador}, identificado en la ficha contractual y denominado EL EMPLEADOR, y {trabajador}, identificado en la ficha y denominado "
        f"EL TRABAJADOR, se celebra en {ciudad} el presente CONTRATO DE TRABAJO A {modalidad.upper()}. Las partes reconocen que las condiciones "
        "efectivamente ejecutadas, las normas imperativas y el principio de favorabilidad prevalecen sobre estipulaciones incompatibles."
    )
    sections = intro(
        f"CONTRATO DE TRABAJO A {modalidad.upper()}",
        parts,
        [
            f"EL EMPLEADOR requiere el cargo de {cargo} y ha definido funciones, dependencia, riesgos y condiciones esenciales.",
            "EL TRABAJADOR declara haber recibido información suficiente sobre funciones, salario, jornada, lugar, seguridad y políticas aplicables.",
            "Las partes desean documentar condiciones claras sin renunciar a derechos mínimos ni trasladar al trabajador riesgos propios del empleador.",
            "Los anexos de funciones, compensación, confidencialidad, propiedad intelectual, datos, equipos y trabajo a distancia integran el contrato cuando correspondan.",
        ],
    )
    term_text = (
        "El vínculo es a término indefinido y constituye la modalidad general. Permanecerá vigente mientras subsistan las causas y no se configure una forma legal de terminación."
        if "indef" in modalidad.casefold()
        else "El término fijo deberá constar por escrito y no podrá superar, incluida su secuencia de prórrogas, cuatro (4) años. La prórroga automática, el preaviso y la conversión a término indefinido se regirán por el artículo 46 del Código Sustantivo del Trabajo vigente; la forma escrita y la ejecución real deberán permanecer coherentes."
    )
    rows = [
        ("OBJETO Y VINCULACIÓN", f"EL EMPLEADOR vincula a EL TRABAJADOR para desempeñar el cargo de {cargo} y las funciones conexas razonables descritas en el Anexo No. 1. La asignación de tareas deberá respetar dignidad, competencia, seguridad, categoría y límites legales; no autoriza cambios sustanciales arbitrarios."),
        ("NATURALEZA Y RÉGIMEN", "La relación es laboral, personal, remunerada y subordinada dentro de los límites constitucionales y legales. Se rige por el Código Sustantivo del Trabajo, las reformas vigentes, el reglamento aplicable, las políticas válidamente comunicadas y el presente contrato, aplicando favorabilidad y primacía de la realidad."),
        ("DURACIÓN", term_text),
        ("FECHA DE INICIO", f"La prestación inicia el {inicio}. La afiliación al sistema de seguridad social y la entrega de información, equipos y formación exigible deberán gestionarse antes o al comienzo efectivo. La falta de formalidad no permite desconocer el tiempo realmente trabajado."),
        ("PERÍODO DE PRUEBA", "Solo existirá si se pacta por escrito, con duración legal y antes de iniciar su ejecución. Durante este periodo se mantienen salario, seguridad social, prevención de riesgos y demás derechos. La terminación no podrá fundarse en discriminación, represalia, estabilidad reforzada desconocida o abuso del derecho."),
        ("CARGO, DEPENDENCIA Y AUTORIDAD", "El cargo, jefe funcional y nivel de autonomía constan en la ficha. Las órdenes deberán ser legítimas, relacionadas con el trabajo, proporcionales y emitidas por personas autorizadas. El trabajador podrá solicitar aclaración y reportar instrucciones inseguras, ilegales, discriminatorias o incompatibles con sus funciones."),
        ("FUNCIONES", "Las funciones principales están en el Anexo No. 1 con resultados, responsabilidades, autoridad, indicadores y riesgos. Las funciones conexas deben guardar relación con el cargo y formación. Los cambios materiales se documentarán, evaluarán salarialmente cuando corresponda y no podrán implicar desmejora injustificada."),
        ("LUGAR Y MOVILIDAD", f"El lugar principal es {val(a, 'workplace', ciudad)}. Los desplazamientos razonables asociados al cargo se coordinarán con condiciones de seguridad y gastos. El cambio permanente de ciudad, modalidad o sede exige análisis de impacto personal, familiar, económico y de riesgos, además de acuerdo cuando legalmente proceda."),
        ("MODALIDAD DE PRESTACIÓN", ("La prestación incluye trabajo remoto, teletrabajo, trabajo en casa o esquema híbrido según el anexo específico. La modalidad no altera derechos ni autoriza disponibilidad permanente; deberán definirse equipos, conectividad, seguridad, reportes, reversibilidad, prevención y desconexión." if trabajo_remoto else "La prestación es principalmente presencial. Cualquier habilitación temporal o permanente de trabajo a distancia deberá documentarse, identificar la figura jurídica aplicable y definir equipos, seguridad, gastos, conectividad y desconexión.")),
        ("JORNADA ORDINARIA", f"Desde el 15 de julio de 2026 la jornada máxima ordinaria es de cuarenta y dos (42) horas semanales, distribuibles de común acuerdo en cinco (5) o seis (6) días, garantizando el descanso. El horario será {val(a, 'schedule', 'definido por el empleador y comunicado al trabajador')}. Como regla general se respetará el límite diario legal; en jornada flexible podrán programarse entre cuatro (4) y nueve (9) horas ordinarias diarias sin exceder el promedio semanal. La reducción legal de jornada no disminuye salario, prestaciones ni valor de la hora."),
        ("TRABAJO SUPLEMENTARIO Y RECARGOS", "El trabajo entre las 7:00 p. m. y las 6:00 a. m. es nocturno. El trabajo suplementario no podrá exceder dos (2) horas diarias ni doce (12) semanales y deberá quedar autorizado o conocido, registrado y pagado. El empleador conservará relación verificable de persona, actividad, fecha, horario y liquidación. El trabajo en día de descanso obligatorio causa, como mínimo, recargo del noventa por ciento (90 %) desde el 1 de julio de 2026 y del cien por ciento (100 %) desde el 1 de julio de 2027, sin perjuicio de aplicación anticipada más favorable. No habrá renuncia válida a recargos causados."),
        ("DESCANSOS Y DESCONEXIÓN", "EL TRABAJADOR tendrá descansos diarios, semanales, vacaciones y licencias. Fuera de su jornada no estará obligado a responder comunicaciones, salvo excepciones legales, cargos excluidos válidamente o contingencias críticas definidas. Las cargas y canales deberán organizarse para hacer efectivo el derecho a la desconexión."),
        ("SALARIO", f"EL EMPLEADOR pagará un salario de {salario} con periodicidad {val(a, 'pay_frequency', 'mensual')}. El salario remunera la jornada ordinaria y no incluye conceptos no salariales salvo pacto válido y discriminado. Ninguna denominación puede excluir pagos que por su realidad retribuyan directamente el servicio."),
        ("FACTORES SALARIALES Y NO SALARIALES", "El Anexo de Compensación discrimina salario básico, variable, recargos, comisiones, auxilios, beneficios y reembolsos. Los pactos no salariales deberán ser expresos, específicos y compatibles con su finalidad. Los reembolsos exigirán soportes y no podrán reemplazar salario."),
        ("PAGO, DESPRENDIBLE Y DEDUCCIONES", "El pago se hará por canal trazable y se entregará comprobante con conceptos, periodos, cantidades, tasas y deducciones. Solo procederán descuentos autorizados por ley, orden competente o autorización válida, respetando límites. El trabajador podrá controvertir liquidaciones sin represalia."),
        ("PRESTACIONES, VACACIONES Y APORTES", "El empleador reconocerá prestaciones, vacaciones, aportes, dotación y beneficios legalmente procedentes según salario, tiempo y condiciones. Las vacaciones se programarán equilibrando descanso efectivo y operación; no se sustituirán en dinero salvo casos permitidos."),
        ("SEGURIDAD SOCIAL", "EL EMPLEADOR afiliará y cotizará oportunamente a salud, pensiones, riesgos laborales y demás subsistemas aplicables. EL TRABAJADOR suministrará información veraz, reportará novedades y seguirá procedimientos. La mora o error se corregirá sin trasladar al trabajador consecuencias imputables al empleador."),
        ("SEGURIDAD Y SALUD EN EL TRABAJO", "Las partes cumplirán el SG-SST. El empleador identificará peligros, implementará controles, entregará elementos, formará e investigará incidentes. El trabajador usará controles, reportará condiciones y participará. Puede suspender una actividad ante peligro grave e inminente, informando para evaluación, sin represalia por reporte de buena fe."),
        ("EXÁMENES Y DATOS DE SALUD", "Las evaluaciones ocupacionales se limitarán a finalidades legales y de prevención. La información clínica será reservada y el empleador recibirá solo conceptos de aptitud y recomendaciones necesarias. No se exigirán pruebas discriminatorias ni se divulgarán diagnósticos sin base jurídica."),
        ("HERRAMIENTAS, EQUIPOS Y ACTIVOS", "Los activos entregados constarán en inventario con estado, valor, accesorios, licencias y reglas. EL TRABAJADOR los usará para fines autorizados, reportará daño o pérdida y los devolverá. La responsabilidad por deterioro requiere investigación y no se presume ni autoriza descuentos automáticos."),
        ("GASTOS Y VIÁTICOS", "Los gastos ordenados o necesarios para el servicio serán asumidos o reembolsados conforme a política, autorización y soportes. Los viáticos se clasificarán según su finalidad y realidad. El trabajador no financiará permanentemente costos propios de la operación."),
        ("FORMACIÓN Y EVALUACIÓN", "EL EMPLEADOR suministrará inducción y formación necesaria. La evaluación usará criterios previos, objetivos, accesibles y relacionados con el cargo; incluirá retroalimentación y oportunidad de mejora. Los algoritmos o herramientas automatizadas no decidirán de forma opaca medidas de alto impacto y estarán sujetos a revisión humana."),
        ("REGLAMENTO Y POLÍTICAS", "EL TRABAJADOR cumplirá reglas válidas, publicadas y relacionadas con seguridad, convivencia, información, datos, uso de activos y operación. Las políticas no modifican unilateralmente salario, jornada, cargo, término o derechos mínimos. En caso de contradicción prevalecerá la norma o condición más favorable."),
        ("DEBIDO PROCESO DISCIPLINARIO", "Antes de imponer una sanción, el empleador comunicará formalmente la apertura, los hechos u omisiones y todas las pruebas; otorgará un término de defensa no inferior a cinco (5) días, permitirá contradicción y aporte probatorio, decidirá motivadamente, aplicará proporcionalidad y habilitará impugnación. Se respetarán acompañamiento sindical y ajustes razonables cuando procedan. Para trabajadores del hogar y micro o pequeñas empresas con menos de diez (10) trabajadores se aplicará la excepción legal, garantizando en todo caso audiencia previa, defensa y debido proceso."),
        ("PROHIBICIONES Y CONFLICTOS", "EL TRABAJADOR evitará fraude, violencia, acoso, discriminación, apropiación, competencia desleal, conflicto no revelado, uso indebido de información y conductas prohibidas. La enumeración no autoriza sancionar hechos ajenos al trabajo o ejercicio legítimo de derechos."),
        ("CONVIVENCIA Y PREVENCIÓN DEL ACOSO", "Las partes promoverán ambiente respetuoso y activarán canales de queja, Comité de Convivencia y medidas preventivas. Las denuncias se manejarán con confidencialidad, imparcialidad, no represalia y protección. La cláusula no reemplaza rutas legales ni obliga a confrontación con el presunto agresor."),
        ("IGUALDAD Y AJUSTES RAZONABLES", "No habrá discriminación por características protegidas. El empleador evaluará ajustes razonables por discapacidad, salud, embarazo, responsabilidades de cuidado u otras circunstancias protegidas, documentando diálogo y alternativas. La información se limitará a lo necesario."),
        ("LICENCIAS Y CALAMIDADES", "EL TRABAJADOR informará y soportará licencias, incapacidades, calamidades y permisos conforme a la ley y procedimientos razonables. La urgencia justifica aviso posterior. El empleador no exigirá información excesiva ni obstaculizará derechos legalmente reconocidos."),
        ("CONFIDENCIALIDAD", "EL TRABAJADOR protegerá información no pública conocida por razón del cargo, la usará solo para el trabajo y seguirá medidas. La obligación no cubre conocimiento general, información pública, denuncias protegidas, ejercicio de derechos o revelaciones exigidas. Al retirarse devolverá activos y no conservará copias no autorizadas."),
        ("SECRETOS EMPRESARIALES", "Los secretos serán identificados y protegidos mediante acceso restringido, clasificación, registro y formación. La obligación subsiste mientras la información conserve esa condición. El empleador no podrá designar como secreto la experiencia general, habilidades o conocimiento legítimamente adquirido por el trabajador."),
        ("PROPIEDAD INTELECTUAL", "La titularidad de creaciones se definirá por la ley, las funciones, el encargo escrito y el anexo. Se identificarán autores, obras, activos preexistentes, modalidades de explotación, territorio, duración y contraprestación cuando proceda. Los derechos morales se respetan y la cesión no abarcará de manera indeterminada toda producción futura."),
        ("SOFTWARE, IA Y CÓDIGO ABIERTO", "Cuando el cargo cree o use software, datos o IA, el anexo regulará repositorios, licencias, componentes, atribuciones, seguridad, entrenamiento, revisión humana y entrega. No se cargará información reservada en herramientas no autorizadas ni se incorporarán componentes incompatibles."),
        ("DATOS PERSONALES", "EL EMPLEADOR tratará datos para gestión laboral, seguridad social, SST, pagos, cumplimiento y finalidades informadas, aplicando necesidad, seguridad y derechos del titular. Los datos sensibles y biométricos tendrán controles reforzados. La autorización no sustituye otras bases jurídicas ni habilita finalidades incompatibles."),
        ("MONITOREO Y PRIVACIDAD", "Los controles sobre equipos, acceso, comunicaciones o ubicación deberán ser necesarios, proporcionales, transparentes y relacionados con finalidades legítimas. No se realizará vigilancia permanente de espacios privados ni acceso indiscriminado a comunicaciones personales. Las evidencias se conservarán con acceso limitado."),
        ("TRABAJO A DISTANCIA", "Si aplica, el anexo identifica figura jurídica, lugar, equipos, mantenimiento, conectividad, riesgos, reporte, visitas, reversibilidad y desconexión. El empleador mantiene obligaciones de prevención y no podrá trasladar al trabajador costos estructurales sin acuerdo o regla aplicable."),
        ("CAMBIOS EN LAS CONDICIONES", "Los cambios razonables dentro del poder de dirección respetarán dignidad, derechos y necesidades del servicio. Las modificaciones esenciales se documentarán y, cuando requieran consentimiento, no se impondrán. El trabajador podrá dejar constancia y utilizar canales de revisión sin represalia."),
        ("SUSPENSIÓN", "La suspensión solo operará por causa legal, con registro de inicio, motivo, efectos y reanudación. Durante ella se conservarán obligaciones que subsistan. No se utilizará como sanción encubierta ni para eludir pagos o estabilidad."),
        ("TERMINACIÓN", "El contrato terminará por causas y procedimientos legales. Toda decisión deberá identificar causal, hechos, fecha, soportes, pagos y entrega. El trabajador podrá comunicar su renuncia con treinta (30) días calendario de antelación para facilitar reemplazo, pero no podrá pactarse sanción por omitir ese preaviso. Cuando exista estabilidad reforzada, fuero, discapacidad, embarazo, salud, actividad sindical, denuncia o situación protegida, se realizará revisión jurídica específica y se obtendrán autorizaciones exigibles."),
        ("JUSTA CAUSA Y DESCARGOS", "La invocación de justa causa exige hechos claros, oportunidad, prueba, coherencia, proporcionalidad y respeto del debido proceso. No se utilizarán fórmulas genéricas ni causales sobrevinientes. El trabajador podrá conocer y controvertir la imputación antes de una medida cuando corresponda."),
        ("LIQUIDACIÓN Y CERTIFICACIONES", "Al cierre se liquidarán salarios, prestaciones, vacaciones, indemnizaciones y deducciones válidas; se entregarán comprobantes, certificados y soportes. El paz y salvo no implicará renuncia a derechos ciertos e indiscutibles ni validará liquidaciones incorrectas."),
        ("DEVOLUCIÓN Y ENTREGA", "Las partes suscribirán acta sobre activos, accesos, expedientes, pendientes e información. El empleador revocará credenciales oportunamente. La falta o daño se investigará y no autoriza retención total de la liquidación ni descuento sin base válida."),
        ("PETICIONES Y CANALES", "EL TRABAJADOR podrá presentar peticiones, reclamos, denuncias y solicitudes por canales trazables. El empleador responderá de fondo dentro de términos aplicables y conservará confidencialidad. El uso de canales internos no limita acudir a autoridades o mecanismos legales."),
        ("NOTIFICACIONES", "Las comunicaciones formales se enviarán a los datos registrados y deberán permitir acreditar contenido y fecha. Cada parte reportará cambios. La mensajería instantánea no reemplaza documentos que legalmente exijan forma o entrega específica."),
        ("INTEGRIDAD Y FAVORABILIDAD", "El contrato y anexos recogen las condiciones pactadas sin afectar derechos mínimos, beneficios más favorables, convención, pacto, laudo o práctica vinculante. La nulidad o ineficacia de una cláusula no afecta las demás; se aplicará la norma imperativa correspondiente."),
        ("FIRMA Y ENTREGA", "Las partes podrán firmar manuscrita o electrónicamente mediante método confiable. EL EMPLEADOR entregará copia íntegra y anexos. La plataforma conservará revisión, firma, fecha, identidad, integridad y auditoría según permisos y política de retención."),
    ]
    for idx, (title, text) in enumerate(rows, 1):
        sections.append(clause(idx, title, text))
    sections += [
        signature(empleador, "EL EMPLEADOR", trabajador, "EL TRABAJADOR"),
        control("CO-LA-002", len(rows), [
            "Código Sustantivo del Trabajo y Ley 2466 de 2025.",
            "Ley 2191 de 2022 sobre desconexión laboral.",
            "Leyes 1221 de 2008, 2088 de 2021 y 2121 de 2021, según modalidad de trabajo a distancia.",
            "Ley 1010 de 2006 sobre prevención y corrección del acoso laboral.",
            "Ley 1581 de 2012 sobre protección de datos personales.",
        ]),
    ]
    return sections


def employment_functions_annex(a: dict[str, Any]) -> list[dict[str, Any]]:
    cargo = val(a, "position", "cargo definido en la ficha")
    return [
        section("ANEXO NO. 1 - PERFIL, FUNCIONES, AUTORIDAD Y RESULTADOS", f"Cargo: {cargo}. Este anexo delimita el contenido funcional y evita órdenes abiertas o incompatibles con la categoría."),
        section("1. PROPÓSITO", val(a, "role_purpose", "Definir el resultado principal que justifica el cargo y su contribución a la organización.")),
        section("2. FUNCIONES ESENCIALES", bullets=[val(a, "function_1", "Ejecutar las actividades técnicas y operativas propias del cargo."), val(a, "function_2", "Conservar soportes, reportar riesgos y cumplir controles."), val(a, "function_3", "Coordinar con las áreas necesarias sin exceder la autoridad asignada."), val(a, "function_4", "Participar en formación, mejora y seguridad asociadas al cargo.")]),
        section("3. RESULTADOS E INDICADORES", table=[("Resultado", "Indicador / fuente / periodicidad / meta"), ("R-01", val(a, "indicator_1", "Calidad y oportunidad del resultado principal")), ("R-02", val(a, "indicator_2", "Cumplimiento de controles y trazabilidad")), ("R-03", val(a, "indicator_3", "Gestión de riesgos y servicio interno"))]),
        section("4. AUTORIDAD Y LÍMITES", "Se identifican decisiones que puede adoptar, aprobaciones requeridas, manejo de recursos y prohibiciones. Ninguna función autoriza contratar, obligar, sancionar o disponer de activos fuera de las delegaciones escritas."),
        section("5. DEPENDENCIA Y COORDINACIÓN", table=[("Relación", "Alcance"), ("Jefatura", val(a, "manager", "Responsable registrado")), ("Equipo", val(a, "team", "Según estructura vigente")), ("Terceros", "Coordinación limitada a las funciones")]),
        section("6. RIESGOS Y CONTROLES", "El perfil se vincula a la matriz de peligros, controles de información, riesgos de fraude, conflicto y continuidad. La inducción y equipos se ajustarán cuando cambie el riesgo."),
        section("7. CAMBIOS", "Los cambios materiales se compararán contra esta versión, analizarán en carga, salario, competencia, lugar, jornada y riesgo, y quedarán aprobados en revisión inmutable."),
        control("CO-LA-002-ANEXO-FUNCIONES", 7, ["Contrato principal, perfil ocupacional y SG-SST."]),
    ]


def employment_compensation_annex(a: dict[str, Any]) -> list[dict[str, Any]]:
    salario = cop(a.get("salary"), 2_500_000)
    return [
        section("ANEXO NO. 2 - COMPENSACIÓN Y BENEFICIOS", "Discriminación de conceptos para evitar ambigüedad sobre naturaleza, causación, pago y soporte."),
        section("1. SALARIO BÁSICO", f"Salario básico: {salario}. Periodicidad: {val(a, 'pay_frequency', 'mensual')}."),
        section("2. VARIABLE", "Todo componente variable tendrá fórmula, fuente, periodo, condiciones, fecha de cierre, responsables y tratamiento de novedades. No podrá modificarse retroactivamente ni depender de criterios inaccesibles."),
        section("3. RECARGOS Y SUPLEMENTARIO", "Se liquidarán conforme a horario, registro y porcentajes vigentes. El comprobante identificará horas, clase, tasa y periodo."),
        section("4. BENEFICIOS", table=[("Concepto", "Naturaleza / condición / periodicidad"), ("Auxilio", val(a, "allowance", "Según procedencia legal o política")), ("Bonificación", val(a, "bonus", "Según plan escrito")), ("Otros", val(a, "benefits", "Según ficha"))]),
        section("5. REEMBOLSOS", "Los reembolsos cubren gastos autorizados y soportados; no remuneran el servicio ni sustituyen salario."),
        section("6. DEDUCCIONES", "Solo se aplicarán deducciones legalmente procedentes, discriminadas y dentro de límites. Toda autorización deberá ser libre, específica y revocable cuando corresponda."),
        section("7. REVISIÓN", "Los cambios se documentarán, respetarán derechos adquiridos y no operarán por simple actualización unilateral de una política."),
        control("CO-LA-002-ANEXO-COMPENSACIÓN", 7, ["Código Sustantivo del Trabajo y Ley 2466 de 2025."]),
    ]


def employment_confidentiality_annex(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO NO. 3 - CONFIDENCIALIDAD, PROPIEDAD INTELECTUAL Y DATOS", "Regula información, secretos, creaciones y datos dentro de la relación laboral sin restringir derechos del trabajador."),
        section("1. INFORMACIÓN PROTEGIDA", "Información no pública cuya reserva resulte de su naturaleza, contexto, clasificación o deber legal. Se excluye lo público, legítimamente conocido, desarrollado de forma independiente o revelado en ejercicio protegido de derechos."),
        section("2. USO Y SEGURIDAD", "Uso exclusivo para funciones, mínimo privilegio, cuidado de credenciales, prohibición de copias no autorizadas y reporte de incidentes."),
        section("3. SECRETOS EMPRESARIALES", "Se identificarán medidas razonables y la obligación subsistirá solo mientras la información conserve legalmente esa calidad. La experiencia general y habilidades del trabajador no son secreto."),
        section("4. CREACIONES", "Se documentarán obras, autores, relación con funciones o encargo, activos preexistentes y modalidades. Las cesiones deberán ser escritas, determinables y compatibles con derechos morales."),
        section("5. SOFTWARE E IA", "Se usarán repositorios, licencias y herramientas autorizadas; se informarán componentes de terceros y no se ingresarán datos reservados en IA no autorizada."),
        section("6. DATOS PERSONALES", "El empleador informará finalidades, bases, destinatarios, derechos y medidas. Datos sensibles, biométricos y de salud tendrán acceso restringido."),
        section("7. SALIDA", "Al terminar se devolverán activos, se eliminarán copias no autorizadas y se preservará únicamente lo exigido por ley o para defensa, con acceso limitado."),
        control("CO-LA-002-ANEXO-CONFIDENCIALIDAD", 7, ["Ley 23 de 1982; Ley 1581 de 2012; Ley 256 de 1996."]),
    ]


def employment_equipment_annex(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO NO. 4 - ENTREGA DE EQUIPOS, ACCESOS Y ACTIVOS", "Inventario, uso, soporte, seguridad y devolución sin presunción automática de responsabilidad."),
        section("1. INVENTARIO", table=[("Activo", "Marca / serial / estado / accesorios / valor de referencia"), ("Equipo principal", val(a, "equipment", "Según acta de entrega")), ("Accesos", "Cuentas, roles y fecha de habilitación"), ("Otros", "Según inventario fotográfico")]),
        section("2. USO AUTORIZADO", "Uso para funciones, con tolerancia personal solo si la política lo permite. Se prohíbe compartir credenciales, desactivar controles o instalar software no autorizado."),
        section("3. SOPORTE Y MANTENIMIENTO", "El empleador gestiona mantenimiento y licencias; el trabajador reporta fallas y permite soporte razonable con respeto por privacidad."),
        section("4. PÉRDIDA O DAÑO", "Se reportará de inmediato y se investigarán hechos, desgaste, fuerza mayor, seguridad y culpa. No habrá descuento automático."),
        section("5. DEVOLUCIÓN", "La devolución se hará mediante acta con estado, accesorios, borrado seguro, pendientes y acceso revocado."),
        control("CO-LA-002-ANEXO-EQUIPOS", 5, ["Contrato principal, políticas de seguridad y régimen laboral aplicable."]),
    ]


def employment_remote_annex(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO NO. 5 - TRABAJO A DISTANCIA, HÍBRIDO O TEMPORAL", "La figura concreta deberá seleccionarse según permanencia, voluntariedad, lugar y régimen aplicable."),
        section("1. FIGURA Y LUGAR", f"Modalidad: {val(a, 'work_mode', 'híbrida')}. Lugar autorizado: {val(a, 'remote_location', 'domicilio registrado y espacios aprobados')}."),
        section("2. JORNADA Y DESCONEXIÓN", "Se conservan jornada, pausas, descansos y desconexión. Los sistemas de coordinación no autorizan disponibilidad permanente."),
        section("3. EQUIPOS Y COSTOS", "Se identifican equipos, mantenimiento, conectividad, energía, auxilios y condiciones de devolución. No se trasladarán costos estructurales sin regla o acuerdo aplicable."),
        section("4. SST", "Se realizará autoevaluación o visita permitida, formación, reporte de incidentes, pausas y controles ergonómicos. La visita respetará privacidad y coordinación previa."),
        section("5. INFORMACIÓN Y PRIVACIDAD", "Se aplicarán redes, cifrado, acceso y custodia. El monitoreo será transparente, necesario y proporcional; no se accederá a espacios o dispositivos personales sin base y autorización."),
        section("6. REVERSIBILIDAD Y CAMBIOS", "La reversión o cambio seguirá la figura legal, preaviso, condiciones personales y necesidades operativas. Se documentarán fecha, equipos y transición."),
        section("7. EMERGENCIAS", "La continuidad, indisponibilidad de servicios y reporte de fallas tendrán canales y expectativas razonables; no se sancionarán eventos no imputables sin evaluación."),
        control("CO-LA-002-ANEXO-TRABAJO-DISTANCIA", 7, ["Leyes 1221 de 2008, 2088 de 2021, 2121 de 2021 y 2191 de 2022."]),
    ]


# ---------------------------------------------------------------------------
# CO-EM-004 - NDA, SECRETOS, PI Y DATOS
# ---------------------------------------------------------------------------

def nda_sections(a: dict[str, Any], bilateral: bool | None = None, source: str = "CO-EM-004 M13") -> list[dict[str, Any]]:
    party_a = val(a, "party_a", "PARTE A")
    party_b = val(a, "party_b", "PARTE B")
    bilateral = yes(a, "bilateral", True) if bilateral is None else bilateral
    receiving = "cada parte cuando reciba información de la otra" if bilateral else party_b
    disclosing = "cada parte cuando revele información" if bilateral else party_a
    purpose = val(a, "purpose", "la evaluación, negociación o ejecución de la relación identificada en la ficha")
    sections = intro(
        "ACUERDO DE CONFIDENCIALIDAD, SECRETOS EMPRESARIALES, PROPIEDAD INTELECTUAL, DATOS E IA",
        f"Entre {party_a} y {party_b} se celebra el presente acuerdo {'bilateral' if bilateral else 'unilateral'} para regular {purpose}.",
        [
            "La confidencialidad contractual y el secreto empresarial no son equivalentes: el secreto exige información no divulgada, valor comercial y medidas razonables de protección.",
            "La protección se administra por finalidad, clasificación, necesidad de acceso, trazabilidad, seguridad, incidentes y cierre verificable.",
            "La revelación no transfiere propiedad intelectual, licencias, datos ni derechos sobre resultados salvo estipulación escrita, expresa y delimitada.",
            "El uso de nube, proveedores o inteligencia artificial requiere autorización previa, evaluación de riesgos y reglas de no entrenamiento, retención y eliminación.",
        ],
    )
    rows = [
        ("OBJETO", f"Regular el acceso, uso, custodia, copia, revelación, seguridad, devolución y eliminación de la información suministrada por {disclosing} a {receiving} exclusivamente para {purpose}. El acuerdo no obliga a revelar información ni a celebrar un negocio posterior."),
        ("DEFINICIONES OPERATIVAS", "La ficha y los anexos identificarán Parte Reveladora, Parte Receptora, Información Confidencial, Secreto Empresarial, Datos Personales, Material Preexistente, Resultado, Incidente, Proveedor Autorizado y Sistema de IA. Las denominaciones se aplicarán según el rol real asumido en cada operación."),
        ("FINALIDAD AUTORIZADA", "La información se usará únicamente para la finalidad documentada. Quedan prohibidos el uso secundario, entrenamiento o ajuste de modelos, publicidad, benchmarking identificable, prospección comercial, desarrollo competitivo, extracción de bases, perfilamiento o explotación no autorizada."),
        ("INFORMACIÓN CONFIDENCIAL", "Comprende información no pública comunicada en cualquier soporte que, por marca, contenido, contexto o circunstancias, razonablemente deba tratarse como reservada: estrategias, precios, clientes, procesos, contratos, investigaciones, código, arquitectura, diseños, credenciales, vulnerabilidades, modelos, datasets, datos personales y términos de la negociación."),
        ("SECRETOS EMPRESARIALES", "Tendrá protección reforzada la información no divulgada que sea secreta, tenga valor comercial por ser secreta y haya sido objeto de medidas razonables de protección. Su amparo subsiste mientras se mantengan esos requisitos; no nace ni se conserva por una etiqueta genérica o por el solo pacto de duración."),
        ("MEDIDAS RAZONABLES DEL TITULAR", "La Parte Reveladora clasificará los activos críticos, limitará accesos, identificará custodios, utilizará controles técnicos y contractuales, documentará entregas y revisará periódicamente la vigencia de la clasificación. La omisión de una medida aislada no decide por sí sola el carácter secreto, pero será valorada con el conjunto de controles."),
        ("EXCLUSIONES Y CARGA DE PRUEBA", "No será confidencial lo que la receptora demuestre mediante evidencia contemporánea que era público sin infracción, conocía legítimamente, recibió lícitamente de tercero sin deber, desarrolló independientemente o fue autorizado. La combinación no pública de elementos públicos puede conservar protección."),
        ("IDENTIFICACIÓN Y CONFIRMACIÓN", "La información escrita podrá marcarse; la oral, visual o demostrada podrá confirmarse dentro de un plazo razonable. La falta de marca no elimina la reserva cuando el contexto la hace evidente. Las partes evitarán clasificaciones masivas o indeterminadas que impidan administrar el riesgo."),
        ("DEBER DE CUIDADO", "La Parte Receptora aplicará el cuidado utilizado para su información equivalente y nunca menos de medidas razonables: mínimo privilegio, credenciales individuales, autenticación reforzada cuando proceda, cifrado, repositorios autorizados, actualización, registro, respaldo, formación y baja oportuna de accesos."),
        ("PERSONAS AUTORIZADAS", "Solo accederán trabajadores, contratistas, asesores, afiliadas o proveedores identificados que necesiten conocer, estén sujetos a obligaciones equivalentes y hayan recibido instrucciones. La Parte Receptora responderá por su selección, alcance, supervisión y retiro de acceso, sin excluir la responsabilidad directa del tercero."),
        ("COPIAS, SOPORTES Y EXTRACCIÓN", "Las copias se limitarán a las indispensables, conservarán clasificación y estarán sujetas a inventario. Se prohíben cuentas personales, repositorios públicos, mensajería no autorizada, dispositivos no gestionados, extracción masiva, scraping, ingeniería inversa, descompilación o reproducción para otra finalidad, salvo autorización o excepción legal aplicable."),
        ("REVELACIÓN OBLIGATORIA", "Ante orden legal, judicial o administrativa, la receptora verificará competencia y alcance, notificará previamente cuando sea lícito, solicitará tratamiento reservado cuando proceda y revelará únicamente lo exigido. Conservará evidencia de solicitud, análisis, información entregada, destinatario y fecha."),
        ("DENUNCIAS Y EJERCICIO DE DERECHOS", "El acuerdo no impide denunciar de buena fe ante autoridades, ejercer derechos laborales, participar en investigaciones, colaborar con la justicia o realizar revelaciones legalmente protegidas. La persona limitará el contenido y utilizará canales razonables cuando ello sea compatible con la protección buscada."),
        ("DATOS PERSONALES", "Cuando exista tratamiento de datos, las partes definirán por operación quién decide finalidades y medios, quién actúa por cuenta ajena, instrucciones, bases jurídicas, categorías, titulares, atención de derechos, seguridad, transmisión o transferencia, conservación y eliminación. La confidencialidad no sustituye el cumplimiento de la Ley 1581 de 2012."),
        ("DATOS SENSIBLES Y DE MENORES", "El tratamiento de datos sensibles, biométricos, de salud o de niñas, niños y adolescentes exige necesidad demostrada, información reforzada, base aplicable, acceso restringido y evaluación de impacto cuando el riesgo lo justifique. No se utilizarán para entrenamiento o decisiones incompatibles con la finalidad autorizada."),
        ("SEGURIDAD DE LA INFORMACIÓN", "Los controles serán proporcionales a naturaleza, volumen, contexto y riesgo: inventario, mínimo privilegio, MFA, cifrado, segregación, registros, respaldo, gestión de vulnerabilidades, continuidad, pruebas, eliminación segura y revisión de terceros. Las excepciones deberán aprobarse, justificarse, compensarse y tener fecha de cierre."),
        ("INCIDENTES Y NOTIFICACIÓN ENTRE PARTES", "La Parte Receptora notificará sin dilación indebida y, contractualmente, dentro de las primeras veinticuatro (24) horas desde que confirme un evento con impacto potencial, sin esperar el informe final. Informará hechos conocidos, activos, datos, titulares, contención y contacto; preservará evidencia y actualizará el reporte."),
        ("REPORTE REGULATORIO", "El Responsable o Encargado determinará las obligaciones frente a la Superintendencia de Industria y Comercio y otros destinatarios. Cuando aplique el régimen de reporte de incidentes de datos personales, se respetará el término regulatorio vigente, sin que la notificación contractual interna lo sustituya o reduzca."),
        ("NUBE, SUBPROCESADORES Y TERCEROS", "No se transferirá información a proveedores no autorizados. La autorización identificará servicio, jurisdicción, región, subprocesadores, niveles de servicio, seguridad, retención, respaldo, uso secundario, auditoría, portabilidad, eliminación y apoyo en incidentes. Un cambio material requerirá evaluación previa."),
        ("INTELIGENCIA ARTIFICIAL", "No se incorporarán secretos, datos personales, credenciales, código restringido ni obras de terceros a sistemas de IA no autorizados. La ficha definirá proveedor, modelo, entradas, memoria, retención, entrenamiento, revisión humana, pruebas, trazabilidad, sesgos, seguridad, derechos sobre salidas y prohibiciones. Ninguna salida se presumirá exacta, exclusiva o libre de derechos ajenos."),
        ("DESARROLLO INDEPENDIENTE Y CONOCIMIENTO RESIDUAL", "Podrá utilizarse conocimiento general y experiencia profesional sin reproducir información protegida, siempre que exista evidencia de desarrollo independiente. No se reconoce una excepción amplia de memoria residual para secretos empresariales, código, datasets, datos personales, estrategias, combinaciones identificables o reproducciones sustanciales."),
        ("PROPIEDAD Y NO LICENCIA", "La revelación no transfiere titularidad ni concede licencia, salvo la limitada, revocable y no transferible necesaria para la finalidad. Muestras, soportes, marcas, patentes, diseños, obras, software, bases, modelos y know-how permanecen bajo los derechos de su titular."),
        ("MATERIALES PREEXISTENTES", "Cada parte identificará metodologías, software, contenidos, datos, modelos, herramientas, marcas y otros activos preexistentes incorporados. Su uso se regirá por licencia expresa; no se entenderán cedidos por integración, acceso técnico o entrega de un resultado."),
        ("RESULTADOS Y CADENA DE TITULARIDAD", "Los resultados nuevos se inventariarán por activo, autor, fecha, contribución, soporte y relación contractual. Su titularidad, cesión o licencia se acordará por escrito, con modalidades de explotación, territorio, duración, exclusividad, remuneración, entrega de fuentes y restricciones; el NDA no constituye cesión general ni de producción futura indeterminada."),
        ("SOFTWARE Y CÓDIGO ABIERTO", "Cuando existan desarrollos se entregará inventario de componentes y licencias, avisos, código fuente pactado, documentación, dependencias, scripts, materiales auxiliares, credenciales transferibles y vulnerabilidades conocidas. No se incorporarán componentes con obligaciones incompatibles sin aceptación previa documentada."),
        ("GARANTÍAS SOBRE TERCEROS", "Cada parte declara tener facultad para revelar y utilizar sus aportes y avisará restricciones, licencias, datos o secretos de terceros. No introducirá materiales obtenidos con infracción contractual, competencia desleal, acceso no autorizado o vulneración de derechos."),
        ("DURACIÓN Y SUPERVIVENCIA", f"El acuerdo rige desde {val(a, 'start_date', 'la firma')}. La obligación contractual general se mantendrá por {val(a, 'confidentiality_term', 'cinco (5) años')} desde la última revelación; los secretos empresariales se protegerán mientras conserven sus requisitos, y los datos, propiedad intelectual, conservación probatoria e incidentes por el término que corresponda a su naturaleza y ley aplicable."),
        ("DEVOLUCIÓN, ELIMINACIÓN Y CERTIFICACIÓN", "Al concluir la finalidad o mediar solicitud legítima, la receptora devolverá soportes, revocará accesos, eliminará copias de trabajo y derivados y certificará responsables, fecha, alcance y método. Las copias legales o respaldos no accesibles quedarán aislados, sin uso operativo y sometidos a eliminación en su ciclo ordinario."),
        ("CONSERVACIÓN Y LEGAL HOLD", "Una obligación legal, investigación o controversia podrá suspender de forma delimitada la eliminación. Se documentarán base, alcance, custodio, accesos, fecha de revisión y liberación. La conservación excepcional no amplía la finalidad ni autoriza explotación."),
        ("AUDITORÍA PROPORCIONADA", "Ante riesgo, incidente o incumplimiento razonable, la Parte Reveladora podrá solicitar certificaciones, informes o auditoría acordada. Se protegerán secretos de terceros, seguridad y continuidad; no habrá acceso indiscriminado, pruebas intrusivas no autorizadas ni auditorías repetitivas sin causa."),
        ("RESPONSABILIDAD Y MITIGACIÓN", "La parte incumplida responderá conforme a la ley y al daño demostrado. Cualquier límite válido deberá ser expreso y no cubrirá dolo, culpa grave ni materias legalmente indisponibles. La parte afectada adoptará medidas razonables de mitigación y preservación de evidencia."),
        ("MEDIDAS URGENTES", "La utilización o divulgación indebida puede causar daño difícil de reparar. La parte afectada podrá solicitar cesación, preservación, entrega, medidas cautelares u otras protecciones legalmente procedentes, sin que la cláusula presuma su concesión ni elimine defensas."),
        ("RECLAMOS DE TERCEROS", "Quien conozca un reclamo relacionado con información, datos o derechos avisará oportunamente, preservará evidencia y coordinará defensa. No reconocerá hechos ni celebrará acuerdos que impongan obligaciones a la otra parte sin autorización, salvo deber legal."),
        ("RESTRICCIONES COMERCIALES", "Este acuerdo no crea no competencia, no captación, exclusividad ni asignación de mercado. Cualquier restricción adicional deberá constar separadamente, ser necesaria, proporcional, temporal y compatible con normas laborales, comerciales y de libre competencia."),
        ("CESIÓN Y CAMBIO DE CONTROL", "No se cederá el acuerdo ni se ampliará acceso a terceros sin consentimiento, salvo reorganización que mantenga controles y responsabilidad. La cesión no transfiere por sí sola secretos, datos o licencias cuya transmisión requiera autorización adicional."),
        ("NOTIFICACIONES", "Las comunicaciones ordinarias se enviarán a los contactos de la ficha por medio trazable; los incidentes utilizarán el canal urgente. El cambio de contacto deberá informarse. La plataforma conservará versión, fecha, remitente, destinatario y evidencia de entrega o intento."),
        ("SOLUCIÓN DE CONTROVERSIAS", "Las partes procurarán negociación ejecutiva y, cuando proceda, conciliación, sin impedir medidas urgentes. La ley y foro se indicarán en la ficha y no desplazarán competencias administrativas, penales, de datos, propiedad intelectual o competencia desleal."),
        ("INTEGRIDAD, PRELACIÓN Y MODIFICACIONES", "La ficha, el acuerdo y sus anexos integran el régimen aplicable. Las condiciones específicas prevalecen sobre las generales en su materia. Las modificaciones deben constar por escrito; la tolerancia no es renuncia y la invalidez parcial se sustituirá por una estipulación válida y proporcionada."),
        ("FIRMA Y EVIDENCIA ELECTRÓNICA", "Podrá firmarse electrónicamente mediante método que identifique al firmante, exprese aprobación y preserve integridad. La plataforma conservará versión inmutable, aceptación, revisiones, aprobaciones y auditoría según roles, sin sustituir formalidades especiales exigibles."),
    ]
    for idx, (title, text) in enumerate(rows, 1):
        sections.append(clause(idx, title, text))
    sections += [signature(party_a, "PARTE A", party_b, "PARTE B"), control("CO-EM-004", len(rows), [
        "Decisión 486 de la Comunidad Andina, artículos 260 a 265, y Ley 256 de 1996, artículo 16, sobre secretos empresariales.",
        "Ley 1581 de 2012, Decreto 1074 de 2015 y reglas vigentes de reporte de incidentes de datos personales.",
        "Ley 23 de 1982, Ley 1450 de 2011, Ley 1915 de 2018 y Decisión Andina 351 sobre derecho de autor y software.",
        "CONPES 4144 de 2025 y lineamientos oficiales de seguridad y privacidad para IA como referentes de gobernanza, sin atribuirles el carácter de ley general de IA.",
        source,
    ])]
    return sections


def information_inventory_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO - INVENTARIO, CLASIFICACIÓN Y MEDIDAS DE PROTECCIÓN", "Registro operativo para demostrar titularidad, finalidad, valor, secreto, acceso y controles."),
        section("1. MATRIZ DE ACTIVOS", table=[("Activo / categoría", "Titular", "Clasificación", "Repositorio", "Custodio", "Plazo"), ("Comercial", "Según ficha", "Restringida", "Aprobado", "Área responsable", "Según finalidad"), ("Técnica / código", "Según ficha", "Secreto o restringida", "Repositorio gestionado", "Líder técnico", "Mientras conserve requisitos"), ("Datos personales", "Responsable definido", "Según sensibilidad", "Sistema autorizado", "Privacidad", "Según tabla de retención"), ("Seguridad", "Organización", "Crítica", "Bóveda / sistema seguro", "Seguridad", "Rotación y cierre")]),
        section("2. PRUEBA DEL SECRETO EMPRESARIAL", table=[("Requisito", "Evidencia mínima"), ("No divulgada", "Mapa de divulgaciones y destinatarios"), ("Valor comercial", "Uso productivo, ventaja, costo o impacto"), ("Medidas razonables", "Clasificación, accesos, contratos, registros y seguridad")]),
        section("3. PERSONAS AUTORIZADAS", "Registrar identidad, rol, necesidad, activo, nivel, aprobador, fecha de alta, formación, revisión y baja. Los grupos genéricos o accesos heredados requieren depuración."),
        section("4. SISTEMAS Y TERCEROS", "Registrar repositorio, proveedor, región, subprocesadores, cifrado, respaldo, autenticación, logs, exportación y eliminación. Todo cambio material actualiza el inventario."),
        section("5. DIVULGACIONES", "Registrar fecha, parte reveladora, receptor, propósito, activo, medio, clasificación, restricciones y evidencia. Las revelaciones orales relevantes se confirmarán."),
        section("6. RETENCIÓN Y ELIMINACIÓN", "Definir evento de cierre, plazo, método verificable, copias legales, respaldos, custodio y certificación. La conservación excepcional se revisará periódicamente."),
        section("7. REVISIÓN DE CLASIFICACIÓN", "Revisar al menos ante cambio de finalidad, riesgo, proveedor, relación, divulgación pública, pérdida de valor comercial o modificación normativa. Documentar reclasificación y efecto sobre accesos."),
        control("CO-EM-004-INVENTARIO", 7, ["NDA M13, Decisión 486 artículos 260 a 265 y políticas de seguridad aplicables."]),
    ]


def relationship_annex_sections(a: dict[str, Any], source: str = "CO-EM-004 - relación M13", model_version: str | None = None) -> list[dict[str, Any]]:
    return [
        section("ANEXO - CONTEXTO, FINALIDAD Y GOBIERNO DE ACCESOS", "Delimita por qué, quién, a qué y durante cuánto tiempo accede."),
        section("1. RELACIÓN", val(a, "relationship", "Evaluación comercial, prestación de servicios, empleo, alianza, inversión o investigación según ficha.")),
        section("2. FINALIDAD Y RESULTADO ESPERADO", val(a, "purpose", "Finalidad específica y resultado esperado registrados en la ficha.")),
        section("3. ACTIVOS REQUERIDOS", "Relacionar únicamente los activos indispensables y excluir repositorios completos cuando sea suficiente una vista, extracto, ambiente segregado o dato anonimizado."),
        section("4. MATRIZ DE ACCESO", table=[("Rol / persona", "Activo", "Permiso", "Aprobador", "Inicio", "Revisión / baja"), ("Según ficha", "Según inventario", "Mínimo necesario", "Propietario", val(a, "start_date", "Firma"), val(a, "end_date", "Fin"))]),
        section("5. CONDICIONES TÉCNICAS", "Definir dispositivo, red, repositorio, MFA, exportación, impresión, monitoreo, horario, ambiente de prueba y prohibiciones. El acceso técnico posible no equivale a autorización jurídica."),
        section("6. HITOS", table=[("Hito", "Responsable / evidencia / efecto"), ("Alta", "Aprobación y formación"), ("Revisión", "Continuidad de necesidad y privilegios"), ("Cambio", "Nueva finalidad, activo o tercero"), ("Cierre", "Revocación, devolución, eliminación y certificación")]),
        section("7. SALIDA Y OFFBOARDING", "Revocar cuentas, tokens, llaves, VPN, grupos, repositorios y dispositivos; recuperar activos; transferir conocimiento; eliminar copias; preservar excepciones legales y verificar accesos residuales."),
        control("CO-EM-004-ANEXO-RELACIÓN", 7, [source]),
    ]


def ip_annex_sections(a: dict[str, Any], source: str = "CO-EM-004 - anexo PI M13") -> list[dict[str, Any]]:
    return [
        section("ANEXO - PROPIEDAD INTELECTUAL, SOFTWARE, DATOS, MODELOS E IA", "La titularidad, cesión o licencia se define por activo, autor, modalidad y evidencia; la confidencialidad no la reemplaza."),
        section("1. INVENTARIO PREEXISTENTE", table=[("Activo", "Titular", "Versión", "Licencia / restricción", "Evidencia"), ("Metodologías", "Según declaración", "Actual", "Uso delimitado", "Inventario"), ("Software y librerías", "Según SBOM", "Bloqueada", "Licencia aplicable", "Repositorio"), ("Datos / modelos / contenidos", "Según fuente", "Según ficha", "Base y autorización", "Registro")]),
        section("2. RESULTADOS Y AUTORÍA", "Identificar cada obra, programa, diseño, base, documentación, modelo, contenido o invención; autor o inventor, contribuciones, fecha, soporte, versión, relación con el encargo y materiales preexistentes incorporados."),
        section("3. TITULARIDAD, CESIÓN O LICENCIA", "Precisar si existe titularidad originaria, presunción por encargo, cesión o licencia. Toda transferencia o limitación patrimonial constará por escrito y definirá modalidades de explotación, territorio, duración, exclusividad, sublicencia, remuneración y momento de efectividad. No se incluye producción futura indeterminada."),
        section("4. DERECHOS MORALES", "Los derechos morales permanecen en cabeza de los autores. Créditos, modificaciones, integridad, divulgación y retiro se gestionarán dentro de los límites legales; ninguna cláusula se interpretará como renuncia general."),
        section("5. SOFTWARE Y ENTREGABLES TÉCNICOS", "Entregar el código fuente pactado, ejecutables, scripts, infraestructura como código, modelos de datos, documentación, pruebas, manuales, material auxiliar, repositorios, historial necesario, credenciales transferibles y procedimiento de compilación o despliegue."),
        section("6. CÓDIGO ABIERTO Y TERCEROS", "Mantener SBOM o inventario de dependencias con versión, licencia, autor, aviso y vulnerabilidades conocidas. No incorporar componentes copyleft, source-available, datos o modelos con obligaciones incompatibles sin aprobación previa y plan de cumplimiento."),
        section("7. DATOS, BASES Y MODELOS", "Diferenciar titularidad o derechos sobre la estructura original de una base, derechos sobre contenidos, licencias de datos, datos personales y secretos. El acceso a datos no concede derecho para crear datasets derivados, modelos, embeddings o productos secundarios."),
        section("8. INTELIGENCIA ARTIFICIAL", "Registrar sistemas, proveedor, modelo y versión, entradas, prompts sustanciales, fuentes, memoria, entrenamiento, configuración, revisión humana y pruebas. La asignación contractual de una salida no garantiza que sea protegible, exclusiva o libre de derechos de terceros."),
        section("9. PROCEDENCIA Y TRAZABILIDAD", "Conservar evidencia suficiente de fuentes, licencias, autores, contribuciones humanas, transformaciones, herramientas y revisiones. Los resultados de IA de riesgo alto no se aceptarán sin validación técnica, jurídica y de seguridad."),
        section("10. REGISTRO Y OPONIBILIDAD", "El derecho nace con la creación cuando corresponda; el registro de obras o software es declarativo y sirve como medio de prueba. Los actos y contratos se registrarán cuando sea útil o necesario para publicidad y oponibilidad frente a terceros."),
        section("11. GARANTÍAS Y RECLAMOS", "Cada aportante declara facultades, revelará restricciones y cooperará en reclamos. La defensa e indemnidad se sujetarán a aviso, control razonable, mitigación, no admisión inconsulta y exclusiones expresas."),
        section("12. ENTREGA Y CIERRE", "El acta relacionará activos, archivos, versiones, autores, repositorios, componentes, licencias, datos, modelos, documentación, pruebas, derechos otorgados, registros pendientes y obligaciones supervivientes."),
        control("CO-EM-004-ANEXO-PI", 12, ["Ley 23 de 1982; Ley 1450 de 2011; Ley 1915 de 2018; Decisión Andina 351; orientaciones DNDA sobre software, cesión y registro.", source]),
    ]


def data_annex_sections(a: dict[str, Any], source: str = "CO-EM-004 - anexo datos M13") -> list[dict[str, Any]]:
    return [
        section("ANEXO - TRATAMIENTO, SEGURIDAD Y GOBIERNO DE DATOS PERSONALES", "Se diligencia por operación; los roles se determinan por quién decide finalidades y medios, no por el nombre del contrato."),
        section("1. ROLES Y OPERACIONES", table=[("Elemento", "Definición"), ("Responsable", val(a, "data_controller", "Según ficha y operación")), ("Encargado", val(a, "data_processor", "Según ficha y operación")), ("Finalidades", val(a, "data_purpose", "Únicamente las autorizadas y documentadas")), ("Operaciones", "Recolección, acceso, uso, almacenamiento, circulación, transmisión, transferencia o supresión aplicables")]),
        section("2. TITULARES Y CATEGORÍAS", "Identificar titulares, datos, sensibles, menores, volumen, frecuencia, origen y destinatarios. Aplicar necesidad, minimización, calidad y acceso restringido."),
        section("3. BASE JURÍDICA E INFORMACIÓN", "Documentar autorización o excepción, aviso, finalidades y prueba. El encargado no presume que el responsable cumplió; deberá alertar instrucciones manifiestamente incompatibles."),
        section("4. INSTRUCCIONES", "El encargado tratará únicamente conforme a instrucciones lícitas, documentadas y trazables; no decidirá finalidades propias, combinará bases ni utilizará datos para analítica, publicidad o entrenamiento sin nuevo fundamento."),
        section("5. SEGURIDAD Y PRIVACIDAD DESDE EL DISEÑO", "Aplicar controles técnicos, humanos y administrativos proporcionales: acceso, MFA, cifrado, logs, segregación, pruebas, respaldo, continuidad, vulnerabilidades, gestión de cambios, anonimización o seudonimización y eliminación segura."),
        section("6. PERSONAS Y CONFIDENCIALIDAD", "Acceso por necesidad, autorización individual, formación, deber de reserva y revocación inmediata. Mantener evidencia de altas, cambios, revisiones y bajas."),
        section("7. SUBENCARGADOS", "Requieren autorización previa general o específica, información suficiente y obligaciones equivalentes. El encargado principal conserva responsabilidad por instrucciones, selección, supervisión, incidentes y salida."),
        section("8. DERECHOS DE TITULARES", "Apoyar consultas, reclamos, prueba de autorización, actualización, rectificación, supresión y revocatoria dentro de términos. Definir canal, responsable, escalamiento y conservación de evidencia."),
        section("9. TRANSFERENCIAS Y TRANSMISIONES", "Documentar país, proveedor, rol, mecanismo, contrato, instrucciones, medidas, subencargados y autorización cuando corresponda. Cambios de región o acceso remoto internacional requieren evaluación."),
        section("10. INCIDENTES", "Notificar internamente sin dilación indebida, contener, preservar evidencia y entregar información progresiva. Las partes determinarán el reporte a la SIC y demás comunicaciones; cuando aplique, el reporte regulatorio se realizará dentro de quince (15) días hábiles desde la detección y conocimiento del área encargada."),
        section("11. EVALUACIONES Y AUDITORÍA", "Mantener evidencia de riesgos, políticas, registros, pruebas, medidas y acciones correctivas. La auditoría será proporcionada, protegerá terceros y podrá satisfacerse mediante certificaciones o informes cuando sean suficientes."),
        section("12. RETENCIÓN, DEVOLUCIÓN Y SUPRESIÓN", "Definir plazo por finalidad y obligación. Al cierre, devolver o eliminar y certificar; las excepciones legales quedarán delimitadas, aisladas y sin tratamiento activo."),
        section("13. IA Y DECISIONES", "No utilizar datos para entrenamiento, ajuste, embeddings, memoria o decisiones automatizadas no autorizadas. Los usos aprobados identificarán proveedor, finalidad, explicación, revisión humana, pruebas, riesgos, sesgos, seguridad y mecanismo para atender derechos."),
        control("CO-EM-004-ANEXO-DATOS", 13, ["Ley 1581 de 2012; Decreto 1074 de 2015; Circular Única SIC y reglas vigentes de reporte de incidentes.", source]),
    ]


def incident_protocol_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("PROTOCOLO DE INCIDENTES DE INFORMACIÓN, DATOS, SOFTWARE E IA", "Ruta contractual mínima; debe coordinarse con el plan técnico y regulatorio de cada organización."),
        section("1. DETECCIÓN Y CANAL", "Reportar eventos reales o sospechados por el canal urgente. No borrar evidencia, apagar indiscriminadamente, negociar con atacantes, atribuir responsabilidades ni comunicar externamente sin coordinación autorizada."),
        section("2. NOTIFICACIÓN INICIAL", "La contraparte recibirá aviso sin dilación indebida y máximo dentro de veinticuatro (24) horas desde la confirmación de impacto potencial. El aviso inicial puede ser incompleto y se actualizará; no constituye admisión de responsabilidad."),
        section("3. TRIAGE", table=[("Nivel", "Criterio / respuesta"), ("Crítico", "Secretos críticos, datos sensibles, credenciales privilegiadas, exfiltración, ransomware o indisponibilidad esencial"), ("Alto", "Acceso no autorizado, propagación probable o afectación relevante"), ("Medio/Bajo", "Evento contenido sin impacto material conocido; seguimiento documentado")]),
        section("4. CONTENCIÓN Y CONTINUIDAD", "Aislar activos, bloquear indicadores, revocar accesos, rotar secretos, proteger respaldos y mantener servicios esenciales de forma segura. Toda acción se registrará para evitar pérdida de evidencia."),
        section("5. PRESERVACIÓN Y ANÁLISIS", "Conservar logs, imágenes, archivos, mensajes y cadena de custodia; determinar cronología, vector, causa, activos, datos, titulares, terceros, jurisdicciones, alcance, impacto y persistencia."),
        section("6. DECISIONES REGULATORIAS", "Identificar responsable decisor, autoridades, asegurador, titulares, clientes y terceros. Cuando se afecten datos personales, evaluar y ejecutar el reporte a la SIC dentro del término vigente, incluidos quince (15) días hábiles cuando resulte aplicable."),
        section("7. COMUNICACIONES", "Aprobar mensajes veraces, claros y coordinados; distinguir hechos confirmados, hipótesis y medidas. Evitar ocultamiento, especulación, revelación adicional de secretos o afectación de investigaciones."),
        section("8. ERRADICACIÓN Y RECUPERACIÓN", "Eliminar persistencia, corregir causa, restaurar desde fuentes confiables, validar integridad, monitorear recaída y obtener aceptación del retorno por el responsable autorizado."),
        section("9. LECCIONES Y REMEDIACIÓN", "Emitir informe de causa raíz, impacto, decisiones, eficacia, incumplimientos y plan con responsables, fechas y verificación. Actualizar riesgos, contratos, inventarios, controles y formación."),
        section("10. CIERRE Y EVIDENCIA", "Cerrar únicamente cuando contención, recuperación, obligaciones, comunicaciones y acciones inmediatas estén documentadas. Conservar expediente conforme a retención y legal hold."),
        control("CO-EM-004-PROTOCOLO-INCIDENTES", 10, ["NDA M13, anexo de datos, políticas de seguridad y reglas SIC sobre incidentes."]),
    ]


def closure_act_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ACTA DE TERMINACIÓN, DEVOLUCIÓN Y CIERRE M13", "Registra hechos, evidencias y pendientes; no constituye paz y salvo o renuncia sobre asuntos no verificados."),
        section("1. IDENTIFICACIÓN", table=[("Campo", "Dato"), ("Relación", val(a, "relationship", "Según contrato")), ("Fecha de cierre", val(a, "end_date", str(date.today()))), ("Responsables", val(a, "closure_contacts", "Según ficha"))]),
        section("2. INFORMACIÓN Y SECRETOS", "Relacionar activos devueltos o eliminados, excepciones, custodios, medios, certificaciones, clasificación superviviente y medidas que continúan vigentes."),
        section("3. ACCESOS Y ACTIVOS", "Revocar usuarios, grupos, tokens, llaves, VPN, repositorios, cuentas de proveedor y dispositivos; transferir activos autorizados y verificar accesos residuales."),
        section("4. DATOS PERSONALES", "Documentar devolución o supresión, copias legales, responsables, plazo, incidentes abiertos, solicitudes de titulares y subencargados pendientes."),
        section("5. PROPIEDAD INTELECTUAL", "Inventariar resultados, autores, archivos fuente, versiones, materiales preexistentes, componentes, licencias, modelos, datasets, cesiones o licencias y registros pendientes."),
        section("6. IA, NUBE Y TERCEROS", "Cerrar proyectos, memorias, workspaces, datasets, claves y cuentas; solicitar eliminación o exportación; registrar retención del proveedor y evidencia disponible."),
        section("7. INCIDENTES Y RECLAMOS", "Identificar incidentes, investigaciones, reclamaciones, legal holds, acciones correctivas y comunicaciones pendientes. El cierre contractual no extingue estas obligaciones."),
        section("8. PLAN DE CIERRE", table=[("Acción", "Responsable", "Fecha", "Evidencia / estado"), ("Revocar accesos", "Según inventario", "Según ficha", "Registro"), ("Devolver / eliminar", "Custodio", "Según ficha", "Certificación"), ("Transferir PI", "Responsable", "Según contrato", "Acta / repositorio"), ("Cerrar terceros", "Administrador", "Según ficha", "Confirmación")]),
        section("9. RESERVAS", "Registrar saldos, defectos, derechos no transferidos, obligaciones supervivientes y asuntos que requieren revisión profesional. Ningún silencio se interpreta como aceptación de hechos desconocidos."),
        control("CO-EM-004-ACTA-CIERRE", 9, ["Contrato M13 y anexos aplicables."]),
    ]


# ---------------------------------------------------------------------------
# CO-AR-001 - ARRENDAMIENTO DE VIVIENDA URBANA
# ---------------------------------------------------------------------------

def lease_contract_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    arrendador = val(a, "landlord_name", val(a, "party_a", "EL ARRENDADOR"))
    arrendatario = val(a, "tenant_name", val(a, "party_b", "EL ARRENDATARIO"))
    inmueble = val(a, "property_address", "el inmueble identificado en la ficha y el inventario")
    ciudad = val(a, "city", "Medellín")
    canon = cop(a.get("rent"), 2_000_000)
    inicio = val(a, "start_date", "la fecha de entrega")
    meses = val(a, "term_months", "doce (12)")
    copropiedad = yes(a, "horizontal_property", True)
    mascotas = yes(a, "pets", False)
    sections = intro(
        "CONTRATO DE ARRENDAMIENTO DE VIVIENDA URBANA",
        f"Entre {arrendador}, denominado EL ARRENDADOR, y {arrendatario}, denominado EL ARRENDATARIO, se celebra en {ciudad} el presente contrato respecto de {inmueble}.",
        [
            "El inmueble será destinado exclusivamente a vivienda urbana en la modalidad identificada en la ficha.",
            "Las partes documentarán estado, servicios, inventario, pagos, reparaciones, comunicaciones y restitución.",
            "Las estipulaciones se interpretan conforme a la Ley 820 de 2003 y normas imperativas; no se exigirán depósitos o garantías prohibidos.",
            "La aprobación del modelo no sustituye estudio de tradición, facultades, reglamento, seguros, garantías personales o situación particular.",
        ],
    )
    rows = [
        ("OBJETO", f"EL ARRENDADOR concede a EL ARRENDATARIO el goce de {inmueble}, con zonas, servicios, cosas o usos conexos y adicionales descritos en la ficha e inventario. El arrendatario paga el canon y cumple las obligaciones de uso, conservación y restitución."),
        ("IDENTIFICACIÓN DEL INMUEBLE", "La dirección, matrícula cuando se suministre, unidad, parqueadero, cuarto útil, áreas privadas, zonas compartidas, medidores, linderos funcionales y elementos entregados constan en la ficha e inventario. La omisión deberá corregirse antes de la entrega si impide identificar lo arrendado."),
        ("MODALIDAD", f"El contrato se clasifica como {val(a, 'lease_type', 'individual')} conforme a la realidad del uso. Los ocupantes autorizados se relacionan en anexo. La denominación no permite destinarlo a hospedaje, actividad comercial o modalidad distinta sin autorización y cumplimiento normativo."),
        ("DESTINACIÓN", "El inmueble se destinará a habitación del arrendatario y ocupantes autorizados. Se prohíben actividades ilícitas, peligrosas, molestas, hoteleras o que cambien el uso; el trabajo remoto de baja incidencia no será actividad comercial prohibida si respeta propiedad horizontal, seguridad y normas urbanísticas."),
        ("ENTREGA", f"La entrega se realizará el {inicio} mediante acta, inventario y evidencia fotográfica. Se registrarán llaves, medidores, estado, defectos, pendientes y documentos. La recepción no implica renuncia a reclamar defectos ocultos o incumplimientos no verificables en la entrega."),
        ("TÉRMINO", f"El término inicial será de {meses} meses. La prórroga operará conforme a la ley si las partes cumplen y no se comunica terminación válida. Los preavisos se contarán y acreditarán por medios idóneos; el silencio no subsana una causal o forma legal incumplida."),
        ("CANON", f"El canon mensual es {canon}, sin incluir conceptos diferentes salvo discriminación expresa. No podrá exceder el uno por ciento (1 %) del valor comercial soportado del inmueble o de la parte arrendada; para este control, la estimación comercial no podrá superar dos (2) veces el avalúo catastral vigente. Se pagará por periodos anticipados dentro del plazo de la ficha, en la cuenta o canal informado y contra comprobante."),
        ("REAJUSTE", "Cada doce (12) meses de ejecución bajo un mismo precio, el arrendador podrá incrementar el canon hasta el cien por ciento (100 %) de la variación del IPC del año calendario inmediatamente anterior, sin superar el límite legal del canon. Para reajustes realizados en 2026, el IPC anual de 2025 verificado por el DANE es 5,10 %. El monto y la fecha efectiva deberán notificarse mediante servicio postal autorizado o el mecanismo de notificación personal expresamente pactado; sin esa comunicación el reajuste será inoponible. No habrá reajustes retroactivos ni antes de completar doce meses."),
        ("FORMA Y PRUEBA DEL PAGO", "El arrendatario usará el canal autorizado e identificará periodo. El arrendador expedirá recibo o permitirá comprobante bancario. Si cambia la cuenta deberá informar por medio verificable; el arrendatario no asumirá consecuencias de pagos realizados de buena fe al canal vigente."),
        ("MORA", "La mora se configura conforme al plazo y ley, sin necesidad de requerimientos que puedan renunciarse válidamente. Los intereses o cobros solo procederán si están autorizados, son proporcionales y discriminados. La cobranza respetará dignidad, privacidad y prohibiciones legales."),
        ("SERVICIOS PÚBLICOS", "La ficha identifica la parte responsable y los medidores. El arrendatario pagará consumos y cargos a su cargo y entregará soportes al cierre. Las partes podrán aplicar el procedimiento legal para excluir solidaridad del inmueble cuando proceda, documentando garantías permitidas frente a empresas de servicios."),
        ("ADMINISTRACIÓN Y CUOTAS", "Se discriminará quién paga administración ordinaria, extraordinaria, multas y conceptos. Las cuotas extraordinarias y obligaciones de propietario corresponden al arrendador salvo regla válida. Las multas atribuibles a conducta del arrendatario exigirán comunicación y soporte del debido proceso de copropiedad."),
        ("SERVICIOS, COSAS Y USOS ADICIONALES", "Todo servicio adicional tendrá descripción, valor, duración, responsable y mecanismo de terminación. El precio conjunto de servicios, cosas o usos adicionales no podrá exceder el cincuenta por ciento (50 %) del canon del inmueble y no se confundirá con este para eludir topes o reajustes."),
        ("DEPÓSITOS Y GARANTÍAS", "No se exigirán depósitos en dinero efectivo u otras cauciones reales prohibidas para garantizar obligaciones del arrendatario. Las garantías personales, seguros o mecanismos permitidos deberán ser proporcionales, transparentes y no podrán convertirse en retención automática sin liquidación y soporte."),
        ("OBLIGACIONES DEL ARRENDADOR", "Entregar el inmueble, servicios y elementos en buen estado de seguridad, sanidad y funcionamiento; mantener condiciones necesarias; suministrar al arrendatario y al codeudor, cuando exista, copia del contrato escrito con firmas originales dentro de los diez (10) días siguientes a su celebración; entregar la parte normativa del reglamento de propiedad horizontal; respetar goce pacífico y privacidad; gestionar reparaciones a su cargo; y responder comunicaciones."),
        ("OBLIGACIONES DEL ARRENDATARIO", "Pagar, cuidar, usar según destino, cumplir convivencia, informar daños, permitir reparaciones coordinadas, asumir consumos y daños imputables, no realizar modificaciones no autorizadas y restituir. No responde por desgaste normal, vicios, fuerza mayor o reparaciones del arrendador."),
        ("REPARACIONES NECESARIAS", "El arrendatario informará por canal trazable. El arrendador evaluará y ejecutará reparaciones necesarias a su cargo en plazo según urgencia. Ante riesgo grave, el arrendatario podrá adoptar medidas razonables de protección y conservar soportes, sin perjuicio de reglas legales sobre reembolso o terminación."),
        ("REPARACIONES LOCATIVAS", "El arrendatario asumirá reparaciones derivadas del uso ordinario que legalmente le correspondan y daños imputables, previa valoración. No se le cargarán defectos estructurales, antigüedad, vicios, redes generales o desgaste normal."),
        ("MEJORAS Y MODIFICACIONES", "No se harán obras, perforaciones relevantes, instalaciones o cambios sin autorización escrita y, si aplica, permisos de copropiedad o autoridad. La autorización indicará propiedad, retiro, restitución, costos y tratamiento al cierre. Las mejoras no autorizadas no generan reembolso automático."),
        ("INVENTARIO Y EVIDENCIA", "El inventario describe estado funcional y estético, muebles, medidores, fotografías y defectos. Las partes podrán actualizarlo durante un periodo inicial para defectos no visibles. Al cierre se comparará con desgaste normal y reparaciones pendientes."),
        ("PROPIEDAD HORIZONTAL", ("EL ARRENDATARIO recibirá reglas relevantes de la copropiedad y las cumplirá. El arrendador conserva obligaciones de propietario y facilitará trámites de acceso. Las sanciones exigirán soporte y no se trasladarán si provienen de omisión del propietario." if copropiedad else "No se ha informado sometimiento a propiedad horizontal. Si existe, el arrendador entregará reglamento y reglas antes de exigir su cumplimiento.")),
        ("CONVIVENCIA", "Los ocupantes respetarán tranquilidad, seguridad, residuos, ruido, zonas y derechos de vecinos. Las quejas se documentarán y permitirán contradicción. No se aceptarán restricciones discriminatorias o incompatibles con derechos fundamentales."),
        ("MASCOTAS", ("Se permiten las mascotas identificadas, sujetas a normas sanitarias, cuidado, daños y convivencia. No se impondrán prohibiciones absolutas incompatibles con la normativa de propiedad horizontal y derechos aplicables." if mascotas else "No se autoriza mantener mascotas sin acuerdo previo, salvo situaciones protegidas como animales de asistencia. Toda decisión respetará ley, reglamento válido y convivencia, evitando prohibiciones arbitrarias.")),
        ("OCUPANTES E INVITADOS", "Los ocupantes permanentes se registran por seguridad y administración, sin crear obligaciones directas salvo firma o garantía. Las visitas razonables no pueden prohibirse, pero deberán respetar capacidad, seguridad, convivencia y normas."),
        ("SUBARRIENDO Y CESIÓN", "El arrendatario no subarrendará ni cederá sin autorización expresa cuando sea exigible. La autorización identificará persona, alcance, plazo y responsabilidad. El alquiler por plataformas o hospedaje se considera uso distinto y requiere autorización y cumplimiento."),
        ("ACCESO DEL ARRENDADOR", "El arrendador no ingresará sin consentimiento, urgencia real u orden competente. Las inspecciones y reparaciones se coordinarán con aviso razonable, horario y finalidad, respetando privacidad. La venta o nueva renta no autoriza visitas indiscriminadas."),
        ("SEGURIDAD Y EMERGENCIAS", "Las partes informarán riesgos, fugas, incendios, fallas y eventos. El arrendatario adoptará medidas razonables y permitirá atención urgente. El arrendador conservará contactos y no diferirá reparaciones que comprometan habitabilidad o seguridad."),
        ("SEGUROS", "La ficha indicará seguros del inmueble, hogar, responsabilidad o arrendamiento. El seguro no reemplaza obligaciones ni autoriza cobros duplicados. La parte que formule reclamación cooperará y preservará evidencia."),
        ("DATOS PERSONALES", "Los datos se tratarán para selección, contrato, pagos, seguridad, servicios, administración, reclamaciones y cumplimiento. Se informarán responsable, finalidades, derechos, destinatarios y conservación. No se divulgará información a vecinos o terceros sin base."),
        ("COMUNICACIONES", "Arrendador, arrendatario, codeudores y fiadores indicarán la dirección para notificaciones judiciales y extrajudiciales. El cambio de dirección se informará mediante servicio postal autorizado. Reparaciones, quejas, pagos, reajustes, preavisos y terminación se comunicarán por medios que acrediten contenido, envío, entrega y fecha. La mensajería instantánea servirá para coordinación, salvo que el contrato y la ley la admitan expresamente para la actuación concreta."),
        ("INCUMPLIMIENTO Y SUBSANACIÓN", "La parte afectada describirá hechos, obligación, soporte y plazo razonable de subsanación cuando proceda. Las medidas serán proporcionales y no autorizan vías de hecho, corte de servicios, ingreso, retención o desalojo sin procedimiento."),
        ("TERMINACIÓN POR EL ARRENDADOR", "Solo procederá por las causales y procedimientos de la Ley 820 de 2003. La terminación durante prórrogas por plena voluntad exige aviso escrito mediante servicio postal autorizado con mínimo tres (3) meses y, en el supuesto legal, indemnización equivalente a tres (3) cánones. Las causales especiales al vencimiento exigen el mismo preaviso y, según el caso, caución por seis (6) cánones o indemnización de uno punto cinco (1,5) cánones. Antes de actuar se verificará causal, oportunidad, prueba, consignación y autoridad competente."),
        ("TERMINACIÓN POR EL ARRENDATARIO", "El arrendatario podrá terminar por causales legales. Por plena voluntad, durante el término o sus prórrogas deberá avisar por escrito mediante servicio postal autorizado con mínimo tres (3) meses y pagar la indemnización legal de tres (3) cánones; al vencimiento podrá terminar sin indemnización con preaviso de tres (3) meses. La comunicación identificará la fecha de restitución. Si el arrendador se niega a recibir, se utilizará el procedimiento de entrega provisional ante la autoridad competente."),
        ("RESTITUCIÓN", "La restitución se realizará mediante acta, llaves, lectura de medidores, inventario comparado y soportes de servicios. El arrendador no podrá negarse injustificadamente a recibir; las partes utilizarán mecanismos legales si existe controversia."),
        ("LIQUIDACIÓN DE SALDOS", "Se conciliarán canon, servicios, administración, daños demostrados, pagos y créditos. Se distinguirá desgaste normal. Las cotizaciones no son prueba definitiva de pago o daño; se conservarán facturas, fotografías, dictámenes y contradicción."),
        ("ABANDONO Y BIENES", "La ausencia no autoriza ingreso o disposición de bienes sin verificar abandono y seguir procedimiento aplicable. Los bienes dejados se inventariarán y custodiarán razonablemente; cualquier disposición exigirá base legal y trazabilidad."),
        ("SOLUCIÓN DE CONTROVERSIAS", "Las partes intentarán comunicación documentada y conciliación cuando sea útil. No se exige agotar etapas que afecten urgencia, habitabilidad, servicios o medidas. La competencia será la legalmente aplicable."),
        ("LEY APLICABLE", "Se aplica la Ley 820 de 2003, el Código Civil en lo pertinente, normas de servicios, propiedad horizontal, datos y demás disposiciones imperativas. Las cláusulas incompatibles se tendrán por no escritas en la medida legal."),
        ("INTEGRIDAD", "La ficha, inventario, actas y anexos integran el contrato. Las modificaciones deben ser escritas y no podrán desconocer normas imperativas. La tolerancia no constituye renuncia permanente."),
        ("FIRMA Y COPIA", "El contrato podrá firmarse manuscrita o electrónicamente. Cada parte recibirá copia y anexos. La plataforma conservará revisión, integridad y evidencia de aceptación según permisos."),
    ]
    for idx, (title, text) in enumerate(rows, 1):
        sections.append(clause(idx, title, text))
    sections += [signature(arrendador, "EL ARRENDADOR", arrendatario, "EL ARRENDATARIO"), control("CO-AR-001", len(rows), [
        "Ley 820 de 2003 sobre arrendamiento de vivienda urbana.",
        "Decreto 3130 de 2003 sobre servicios públicos en vivienda arrendada.",
        "Ley 675 de 2001 cuando exista propiedad horizontal.",
        "Ley 1581 de 2012 sobre datos personales.",
    ])]
    return sections


def lease_inventory_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ANEXO NO. 1 - INVENTARIO Y ESTADO DEL INMUEBLE", f"Inmueble: {val(a, 'property_address', 'Según ficha')}. Debe acompañarse con fotografías fechadas y relación de archivos."),
        section("1. IDENTIFICACIÓN Y MEDIDORES", table=[("Elemento", "Número / lectura / estado / evidencia"), ("Energía", "Según inspección"), ("Agua", "Según inspección"), ("Gas", "Según inspección"), ("Administración", "Estado de cuenta / paz y salvo")]),
        section("2. ESPACIOS", table=[("Espacio", "Pisos / muros / techos / puertas / ventanas / iluminación / observaciones"), ("Sala-comedor", "Según registro"), ("Cocina", "Según registro"), ("Habitaciones", "Según registro"), ("Baños", "Según registro"), ("Zonas adicionales", "Según registro")]),
        section("3. REDES Y APARATOS", "Probar grifería, desagües, calentador, tomas, interruptores, cerraduras, electrodomésticos y detectores; registrar fallas y pendientes."),
        section("4. MUEBLES Y ACCESORIOS", table=[("Bien", "Marca / serial / cantidad / estado / fotografía"), ("Llaves y controles", "Según entrega"), ("Muebles", "Según inventario"), ("Electrodomésticos", "Según inventario")]),
        section("5. DEFECTOS Y PENDIENTES", "Cada pendiente tendrá responsable, solución, fecha y reserva. El arrendatario podrá reportar defectos no visibles durante el periodo inicial acordado."),
        section("6. CLASIFICACIÓN DEL ESTADO", "Usar categorías objetivas: nuevo, bueno funcional, desgaste previo, reparación pendiente, no probado. Evitar descripciones genéricas como ‘perfecto’."),
        section("7. ARCHIVOS", "Relacionar fotografías y videos con nombre, fecha, espacio y hash cuando la plataforma lo permita."),
        section("8. ACEPTACIÓN", "La firma confirma recepción y observaciones registradas, no renuncia a defectos ocultos ni reparaciones del arrendador."),
        control("CO-AR-001-INVENTARIO", 8, ["Contrato principal y Ley 820 de 2003."]),
    ]


def delivery_act_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ACTA DE ENTREGA DEL INMUEBLE", "Formaliza la posesión material, documentos y pendientes."),
        section("1. FECHA Y PARTES", table=[("Campo", "Dato"), ("Fecha y hora", val(a, "start_date", "Según entrega")), ("Arrendador", val(a, "landlord_name", "Según ficha")), ("Arrendatario", val(a, "tenant_name", "Según ficha"))]),
        section("2. LLAVES Y ACCESOS", "Relacionar llaves, controles, tarjetas, códigos y accesos de copropiedad."),
        section("3. MEDIDORES Y SERVICIOS", "Registrar lecturas, cuentas, estado y trámite de cambio o garantías de servicios."),
        section("4. DOCUMENTOS", "Copia del contrato, inventario, reglamento, manuales, contactos, pólizas y soportes."),
        section("5. PENDIENTES", table=[("Pendiente", "Responsable / fecha / medida temporal"), ("P-01", "Según inspección")]),
        section("6. RESERVAS", "Identificar defectos, pruebas no realizadas y asuntos que no se entienden aceptados."),
        section("7. INICIO DE OBLIGACIONES", "Precisar inicio de canon, servicios y administración de acuerdo con entrega real."),
        control("CO-AR-001-ACTA-ENTREGA", 7, ["Contrato e inventario."]),
    ]


def restitution_act_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("ACTA DE RESTITUCIÓN Y CIERRE", "Compara estado inicial y final sin convertir el acta en renuncia general."),
        section("1. FECHA Y RECEPCIÓN", "Registrar fecha, personas, entrega de llaves y reserva frente a aceptación del estado."),
        section("2. COMPARACIÓN", table=[("Espacio/bien", "Estado inicial / final / desgaste / daño / evidencia"), ("General", "Según inventarios")]),
        section("3. MEDIDORES", "Lecturas finales, facturas pendientes y mecanismo de conciliación."),
        section("4. REPARACIONES", "Distinguir desgaste normal, obligación del arrendador, daño imputable y asunto controvertido. Incluir evidencia y derecho a observación."),
        section("5. SALDOS", "Conciliar canon, servicios, administración, pagos y créditos, sin cobros estimados como definitivos."),
        section("6. BIENES", "Registrar bienes retirados o dejados y el procedimiento de custodia."),
        section("7. RESERVAS", "La recepción de llaves no extingue automáticamente obligaciones probadas ni habilita reclamaciones sin soporte."),
        section("8. CIERRE", "Definir acciones, responsables, fechas y emisión de constancia final."),
        control("CO-AR-001-ACTA-RESTITUCIÓN", 8, ["Contrato, inventarios y soportes de cierre."]),
    ]


def lease_guide_sections(a: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section("GUÍA OPERATIVA DEL ARRENDAMIENTO", "Lista de verificación para firma, ejecución, incidentes, terminación y cierre."),
        section("1. ANTES DE FIRMAR", bullets=["Verificar identidad y facultad del arrendador.", "Identificar inmueble, modalidad, ocupantes y copropiedad.", "Revisar canon, límites, reajuste, servicios y garantías permitidas.", "Completar inventario y estado de cuentas."]),
        section("2. ENTREGA", bullets=["Firmar acta e inventario.", "Registrar medidores, llaves y defectos.", "Recibir reglamento, contactos y documentos."]),
        section("3. EJECUCIÓN", bullets=["Conservar pagos y comunicaciones.", "Reportar reparaciones por canal trazable.", "Documentar quejas y permitir contradicción.", "Actualizar contactos y ocupantes."]),
        section("4. TERMINACIÓN", bullets=["Verificar causal, preaviso, indemnización o consignación.", "Evitar mensajes genéricos o fechas ambiguas.", "Coordinar restitución y lecturas.", "Escalar si hay negativa de recepción o riesgo de vía de hecho."]),
        section("5. CIERRE", bullets=["Comparar inventarios.", "Separar desgaste y daños.", "Conciliar facturas y saldos.", "Cerrar accesos y conservar evidencia."]),
        section("6. ALERTAS ROJAS", bullets=["Intento de desalojo sin proceso.", "Corte o manipulación de servicios.", "Habitabilidad o riesgo estructural.", "Violencia, discriminación o ingreso no autorizado.", "Embargo, proceso judicial o reclamación de tercero."]),
        control("CO-AR-001-GUÍA", 6, ["Ley 820 de 2003 y contrato principal."]),
    ]


PRODUCTS = {
    "CO-EM-003": {
        "title": "Contrato de prestación de servicios independientes",
        "main": services_contract_sections,
        "annexes": [
            ("Anexo de alcance, entregables y cronograma", service_scope_sections),
            ("Acuerdo de confidencialidad", service_confidentiality_sections),
            ("Anexo de propiedad intelectual, software e IA", service_ip_sections),
            ("Anexo de tratamiento y seguridad de datos", service_data_sections),
            ("Acta de terminación, entrega y cierre", service_closure_sections),
        ],
    },
    "CO-LA-002": {
        "title": "Contrato de trabajo personalizado",
        "main": employment_contract_sections,
        "annexes": [
            ("Anexo de funciones y resultados", employment_functions_annex),
            ("Anexo de compensación y beneficios", employment_compensation_annex),
            ("Anexo de confidencialidad, PI y datos", employment_confidentiality_annex),
            ("Anexo de equipos y accesos", employment_equipment_annex),
            ("Anexo de trabajo a distancia", employment_remote_annex),
        ],
    },
    "CO-EM-004": {
        "title": "Confidencialidad, secretos empresariales y propiedad intelectual",
        "main": nda_sections,
        "annexes": [
            ("Inventario y clasificación de información", information_inventory_sections),
            ("Anexo de contexto y accesos", relationship_annex_sections),
            ("Anexo de propiedad intelectual, software e IA", ip_annex_sections),
            ("Anexo de tratamiento y seguridad de datos", data_annex_sections),
            ("Protocolo de incidentes", incident_protocol_sections),
            ("Acta de cierre", closure_act_sections),
        ],
    },
    "CO-AR-001": {
        "title": "Arrendamiento de vivienda urbana",
        "main": lease_contract_sections,
        "annexes": [
            ("Inventario y estado del inmueble", lease_inventory_sections),
            ("Acta de entrega", delivery_act_sections),
            ("Acta de restitución y cierre", restitution_act_sections),
            ("Guía operativa", lease_guide_sections),
        ],
    },
}


def product_summary() -> dict[str, Any]:
    return {
        "build_id": BUILD_ID,
        "model_version": MODEL_VERSION,
        "products": [
            {"code": code, "title": cfg["title"], "documents": 2 + len(cfg["annexes"])}
            for code, cfg in PRODUCTS.items()
        ],
    }
