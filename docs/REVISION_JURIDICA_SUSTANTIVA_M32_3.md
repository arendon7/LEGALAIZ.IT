# Revisión jurídica sustantiva M32.3 — Matriz de los 11 productos

## Alcance y estado

Esta matriz documenta la revisión jurídica asistida del portafolio M32.3 y los controles que debe aplicar el especialista responsable. No equivale a dictamen, aprobación final, representación judicial ni autorización para firma o radicación.

Estado común:

- preflight técnico: `passed`;
- inspección asistida de estructura y coherencia: realizada;
- revisión visual humana formal: `pending`;
- aprobación del especialista jurídico: `pending`;
- aprobación QA: `pending`;
- candidato de liberación: `false`.

La validez de cada documento depende de los hechos, soportes, capacidad de las partes, competencia de la autoridad, vigencia normativa y estrategia del expediente concreto.

## Matriz de control

| Producto | Control sustantivo principal | Riesgo que debe impedir la liberación | Estado M32.3 |
|---|---|---|---|
| `CO-TR-001` | Separar coincidencia documental, irregularidad técnica y consecuencia jurídica; exigir expediente e imputación individual. | Presentar una coincidencia SAST o una deficiencia técnica como anulación automática. | Preparado para revisión especialista. |
| `CO-TR-002` | Reconstruir detección, validación, envío, entrega, conocimiento, audiencia y decisión; preservar evidencia y solicitar expediente íntegro. | Inventar notificación, conductor, culpabilidad, término vencido o consecuencia sancionatoria. | Preparado para revisión especialista. |
| `CO-SA-001` | Identificar paciente, legitimación, orden médica, continuidad, priorización, entidad competente y canal seguro. | Fijar términos definitivos sin norma especial y recepción efectiva; divulgar historia clínica innecesaria; confundir petición con atención de urgencias. | Preparado para revisión especialista. |
| `CO-CD-001` | Diferenciar consulta, reclamo y controversia; identificar fuente, operador, usuario, obligación, comunicación previa, pago y estado del dato. | Declarar eliminación automática o desconocer soportes, temporalidad, legitimación y procedimiento especial. | Preparado para revisión especialista. |
| `CO-CD-003` | Identificar relación de consumo, calidad del consumidor, proveedor, garantía, reclamación directa, prueba del defecto y remedio pretendido. | Acumular garantía, retracto y reversión sin supuesto; calcular términos sin canal, recepción, festivos o norma sectorial. | Preparado para revisión especialista. |
| `CO-CD-004` | Cotejar título, obligación clara/expresa/exigible, autenticidad, vencimiento, pagos, saldo, intereses, prescripción y procesos concurrentes. | Tratar cero técnico como tasa validada; afirmar mérito ejecutivo, saldo o exigibilidad sin original y anexos. | Preparado para revisión especialista. |
| `CO-AR-001` | Verificar inmueble, destino, partes, canon, servicios, duración, inventario, reajuste, terminación y restricciones legales. | Exigir depósito en efectivo o caución real prohibida; superar límites del canon o reajuste; usar cláusulas incompatibles con vivienda urbana. | Preparado para revisión especialista. |
| `CO-EM-003` | Mantener sujetos, objeto, entregables, aceptación, honorarios, plazo, autonomía, datos, PI, riesgos y cierre claramente diferenciados. | Creer que una cláusula elimina la primacía de la realidad; mezclar nombres con objeto; imprimir estructuras técnicas; ampliar cesiones o exoneraciones sin límite. | Preparado para revisión especialista. |
| `CO-EM-004` | Delimitar finalidad, información, exclusiones, destinatarios, medidas, incidentes, duración, devolución, datos e IP preexistente. | Confundir confidencialidad con cesión total de PI; imponer obligaciones perpetuas indiscriminadas; autorizar usos de IA o datos no definidos. | Preparado para revisión especialista. |
| `CO-LA-001` | Validar fechas, salario, jornada, novedades, base, prestaciones, indemnización, pagos y prescripción contra soportes. | Convertir una simulación en liquidación definitiva; omitir conceptos, retenciones, seguridad social, pagos previos o reforma vigente. | Preparado para revisión especialista. |
| `CO-LA-002` | Confirmar empleador, trabajador, cargo, funciones, inicio, lugar, modalidad, jornada, salario y obligaciones laborales vigentes. | Renunciar a derechos mínimos; absorber prestaciones en salario ordinario; exclusividad o sanciones desproporcionadas; desconocer horas extra y realidad de ejecución. | Preparado para revisión especialista. |

## Criterios jurídicos por familia

### Tránsito

La defensa no puede descansar en una promesa de anulación automática. La autoridad debe acreditar actuación, notificación, evidencia, imputación y responsabilidad personal conforme al tipo de infracción y al debido proceso. La Sentencia C-038 de 2020 declaró inexequible la solidaridad sancionatoria objetiva del propietario prevista en la norma examinada y destacó los principios de imputabilidad personal y culpabilidad; no declaró inconstitucional el sistema de detección automática en sí mismo.

Control de liberación:

- identificar si la conducta se atribuye al conductor o deriva de una obligación jurídicamente imputable al propietario;
- no afirmar identidad del infractor por la sola placa;
- cotejar expediente, acto, notificación, recursos, ejecutoria y registros SIMIT/RUNT;
- recalcular términos con calendario, recepción efectiva y actuaciones del expediente.

Fuente oficial: [Corte Constitucional, Sentencia C-038 de 2020](https://www.corteconstitucional.gov.co/relatoria/2020/C-038-20.htm).

### Salud y derecho de petición

La Ley Estatutaria 1751 de 2015 reconoce la salud como derecho fundamental autónomo e irrenunciable y desarrolla continuidad y oportunidad. La Ley 1755 de 2015 regula las modalidades y respuesta de fondo del derecho de petición y extiende reglas pertinentes a instituciones del Sistema de Seguridad Social Integral.

Control de liberación:

- usar únicamente datos clínicos necesarios y canal seguro;
- diferenciar petición, PQRD, tutela y urgencia médica;
- no establecer un vencimiento definitivo sin fecha efectiva de recepción, categoría, norma especial, traslado, prórroga y festivos;
- acreditar legitimación cuando actúa un tercero.

Fuentes oficiales:

- [Ley Estatutaria 1751 de 2015](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=60733).
- [Ley 1755 de 2015](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=65334).

### Hábeas data y protección de datos

La Ley 1266 de 2008 regula especialmente información financiera, crediticia, comercial y de servicios y fue modificada por la Ley 2157 de 2021. La Ley 1581 de 2012 establece el régimen general de protección de datos personales y los deberes de responsables y encargados.

Control de liberación:

- clasificar si procede consulta, reclamo, actualización, rectificación o supresión;
- identificar fuente, operador, usuario y titular;
- distinguir pago, extinción, mora, comunicación previa, permanencia y actualización;
- no prometer supresión cuando el remedio jurídicamente procedente puede ser actualización, rectificación, bloqueo o anotación;
- preservar autenticación y reserva en la entrega.

Fuentes oficiales:

- [Ley 1266 de 2008](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=34488).
- [Ley 1581 de 2012](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981).

### Protección al consumidor

La Ley 1480 de 2011 protege, entre otros aspectos, la seguridad, información e intereses económicos de los consumidores. La selección del mecanismo depende del canal, bien o servicio, defecto, entrega, pago, relación de consumo, reclamación directa y régimen especial aplicable.

Control de liberación:

- no tratar garantía, retracto, reversión y falta de entrega como mecanismos equivalentes;
- documentar compra, entrega, defecto, reclamación y respuesta;
- validar términos con hechos, recepción, festivos y normas sectoriales;
- identificar el remedio principal y las pretensiones subsidiarias compatibles.

Fuente oficial: [Ley 1480 de 2011](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=44306).

### Arrendamiento de vivienda urbana

La Ley 820 de 2003 exige acuerdo mínimo sobre partes, inmueble, precio, servicios, duración y responsable de servicios públicos. Prohíbe depósitos en dinero efectivo y cauciones reales para garantizar obligaciones del arrendatario; limita el canon mensual y regula su reajuste.

Control de liberación:

- confirmar que el destino sea vivienda urbana;
- validar canon frente al valor comercial y avalúo aplicable;
- no incluir depósito o garantía real prohibida directa o indirectamente;
- revisar inventario, servicios, administración, reajuste, prórroga, causales y notificaciones;
- aplicar el procedimiento de servicios públicos cuando corresponda.

Fuentes oficiales:

- [Ley 820 de 2003](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=8738).
- [Decreto 3130 de 2003](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=10482).

### Servicios independientes

La denominación contractual no prevalece sobre la ejecución. Los elementos de prestación personal, subordinación continuada y salario son determinantes para la existencia de un contrato de trabajo. El contrato de servicios debe describir autonomía real, resultados, coordinación compatible, personal, medios, facturación, seguridad social, datos, PI y riesgos sin intentar neutralizar la primacía de la realidad.

Control de liberación:

- mantener contratante, contratista y objeto en campos independientes;
- evitar horario, disciplina y control operativo propios de subordinación cuando se pretende independencia;
- delimitar aceptación, cambios, pagos y cierre;
- asignar PI de forma expresa y limitada, respetando materiales preexistentes y terceros;
- definir responsable/encargado e instrucciones de tratamiento cuando existan datos personales.

Fuentes oficiales:

- [Código Sustantivo del Trabajo, elementos esenciales — referencia oficial incorporada por Ley 50 de 1990](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=281).
- [Ley 1581 de 2012](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981).
- [Ley 23 de 1982](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=3431).

### Confidencialidad, propiedad intelectual y firma electrónica

La confidencialidad debe proteger información delimitable y una finalidad concreta, con exclusiones, destinatarios, medidas, incidentes, devolución y duración. No reemplaza una cesión o licencia de derechos de propiedad intelectual. Los mensajes de datos y firmas deben conservar identificación, aprobación, integridad, accesibilidad y trazabilidad suficientes para el propósito.

Control de liberación:

- no presumir cesión por la entrega de archivos;
- diferenciar derechos preexistentes, resultados, licencias de terceros y derechos morales;
- definir si las obligaciones son unilaterales o recíprocas;
- limitar el acceso por necesidad de conocer;
- exigir método de firma adecuado, evidencia de identidad, integridad y conservación.

Fuentes oficiales:

- [Ley 23 de 1982](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=3431).
- [Ley 527 de 1999](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4276).
- [Decreto 2364 de 2012](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=50583).

### Laboral

La Ley 2101 de 2021 estableció la reducción gradual de la jornada hasta 42 horas semanales sin disminución salarial ni afectación de derechos. La Ley 2466 de 2025 modificó parcialmente normas laborales, por lo que los contratos y liquidaciones deben cotejarse contra el texto vigente y la fecha de causación.

Control de liberación:

- aplicar la jornada vigente para el período concreto;
- no renunciar a salario, prestaciones, seguridad social, descansos, recargos u horas extra;
- diferenciar salario ordinario, pagos no salariales jurídicamente admisibles y salario integral cuando proceda;
- validar indemnización, terminación, justa causa y prescripción con hechos y soportes;
- no imponer arbitraje, exclusividad, cesión de PI o autorización de datos de manera desproporcionada;
- revisar modalidad presencial, teletrabajo, trabajo remoto o trabajo en casa conforme a los hechos.

Fuentes oficiales:

- [Ley 2101 de 2021](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=166506).
- [Ley 2466 de 2025](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=260676).

## Conclusión de M32.3

Los once documentos superan la compuerta técnica y cuentan con una salida coherente para revisión. La iteración corrigió defectos objetivos de generación y de datos sintéticos. Aun así, la plataforma debe conservar el estado `pending` hasta que:

1. un especialista jurídico revise el texto y el expediente concreto;
2. QA inspeccione todas las páginas sobre el hash exacto;
3. se documenten observaciones, correcciones y nueva revisión inmutable;
4. ambas aprobaciones queden registradas de forma independiente;
5. solo entonces se habilite la versión final para el uso autorizado.

La matriz debe actualizarse cuando cambien la normativa, la jurisprudencia, las plantillas, las reglas o las fábricas documentales.