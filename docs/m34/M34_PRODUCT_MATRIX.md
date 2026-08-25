# M34 — Matriz maestra de productos para el Intelligent Journey

Esta matriz no sustituye preguntas, reglas, fuentes ni plantillas. Resume la interfaz semántica que M34 debe usar para decidir qué información falta antes de recomendar un producto.

| Producto | Problema humano principal | Hechos mínimos para recomendación | Dominios críticos | Política inicial |
|---|---|---|---|---|
| `CO-TR-001` · Chequeo SAST + inscripción verificada | Verificar una actuación asociada a detección automática/semi-automática y definir ruta documental | identidad; referencia; autoridad; etapa; objetivo | términos; cobro/actuación; evidencia; autoridad | riesgo |
| `CO-TR-002` · Fotomulta no notificada | Revisar notificación, expediente y ruta administrativa de una fotodetección/comparendo | identidad; referencia; estado de notificación; fecha de conocimiento; etapa; objetivo | notificación; términos; cobro; evidencia | riesgo |
| `CO-LA-001` · Liquidación laboral + reclamación | Revisar acreencias al terminar una relación laboral privada y preparar reclamación | alcance de relación; inicio; fin; base salarial; conceptos pendientes; objetivo | naturaleza de relación; terminación; remuneración; protección especial; disputa activa | revisión específica esperada |
| `CO-LA-002` · Contrato de trabajo personalizado | Formalizar una relación laboral coherente con la necesidad y realidad del cargo | empleador; trabajador; necesidad; inicio; cargo; remuneración | modalidad; régimen/edad; lugar; jornada; protecciones | riesgo |
| `CO-EM-003` · Prestación de servicios | Contratar o prestar servicios independientes con alcance y autonomía verificables | cliente; contratista; objeto; autonomía; honorarios; término | subordinación; servicio regulado; aceptación; datos/PI | riesgo |
| `CO-EM-004` · Confidencialidad y PI | Proteger información, secretos, PI y datos en una relación empresarial/profesional | revelador; receptor; relación; categorías de información; PI; datos personales | alcance; materiales preexistentes; licencia/cesión; datos sensibles; IA | riesgo |
| `CO-AR-001` · Arrendamiento vivienda urbana | Formalizar arrendamiento residencial urbano y su entrega | arrendador; arrendatario; inmueble; uso; canon; término | uso; facultad para arrendar; habitabilidad; canon; garantías; disputa | revisión específica esperada |
| `CO-CD-001` · Centrales de riesgo / hábeas data | Revisar, corregir o reclamar un reporte o información crediticia | fuente/reportante; obligación; estado del reporte; reclamo previo; objetivo | suplantación; comunicación previa; términos; pago/extinción; reclamo previo | revisión específica esperada |
| `CO-CD-003` · Garantía, retracto y reversión | Identificar la ruta de protección al consumidor adecuada | proveedor; transacción; tipo de problema; fecha; remedio; pago | términos; canal; bien/servicio; reclamo previo; trazabilidad del pago | riesgo |
| `CO-CD-004` · Cobro, acuerdo y pagaré | Gestionar/documentar deuda o acuerdo con soporte suficiente | acreedor; deudor; origen; monto; vencimiento; soporte | existencia; cuantía; exigibilidad; garantías; disputa; términos | revisión específica esperada |
| `CO-SA-001` · Petición EPS/IPS | Solicitar información, documentos o actuación a una entidad de salud | solicitante; entidad; necesidad; urgencia; petición previa; objetivo | urgencia; vulnerabilidad; actuación previa; términos; proceso activo | revisión específica esperada |

## Regla transversal de suficiencia

M34 distinguirá tres niveles:

1. `ORIENTATION_READY`: hay información para orientar el área o ruta general, pero no para recomendar producto con suficiente trazabilidad.
2. `RECOMMENDATION_READY`: están presentes los hechos mínimos decisivos y no quedan contradicciones/bloqueos materiales sin resolver.
3. `GENERATION_READY`: están presentes todos los datos que el producto exige para construir el paquete documental. Este nivel pertenece principalmente al flujo posterior a la selección/compra y no debe confundirse con el triage.

El objetivo UX de M34 es llegar a `RECOMMENDATION_READY` con la menor fricción compatible con seguridad jurídica. No debe ejecutar el cuestionario completo sólo para descubrir qué producto conviene.

## Regla de confirmación

- `USER_ASSERTED`: puede alimentar el diagnóstico como afirmación del usuario, conservando procedencia.
- `DOCUMENT_EXTRACTED`: debe confirmarse antes de convertirse en hecho decisivo.
- `AI_INFERRED`: nunca es un hecho confirmado por sí mismo.
- `RULE_DERIVED`: debe conservar la regla y los hechos de entrada que originaron la derivación.
- hechos `DISPUTED` o `SUPERSEDED`: no pueden sostener una recomendación.

## Próximo trabajo de mapeo

M34.3 añadirá un mapa declarativo para cada pregunta actual:

```text
question_id
→ fact_target
→ products
→ ask_when
→ skip_when
→ priority
→ critical
→ why_copy
→ dependencies
```

Ese mapa se construirá sobre las preguntas existentes, no reemplazándolas. El objetivo es transformar el banco actual en un grafo de adquisición de hechos sin perder IDs ni compatibilidad documental.
