# Matriz de control jurídico-documental M32.0

Esta matriz no reemplaza las reglas, fuentes ni aprobaciones de cada producto. Define la compuerta transversal mínima que debe aplicarse a los once productos canónicos antes de considerar un documento listo para demostración o liberación.

| Producto | Familia | Control sustantivo mínimo | Evidencia que debe conservarse | Compuerta documental | Revisión humana |
|---|---|---|---|---|---|
| CO-TR-001 | Tránsito / administrativo | Autoridad, territorio, fecha, identificación del dispositivo, estado oficial y etapa | Consulta, acto, comparendo, certificación y cronología | Integridad DOCX, variables resueltas, anexos y código de producto | Escalar cobro coactivo, fraude, litigio, urgencia o inconsistencia probatoria |
| CO-TR-002 | Tránsito / administrativo | Cronología, notificación, imputación, evidencia técnica, etapa y términos | Comparendo, constancias de notificación, expediente, SIMIT/RUNT y comunicaciones | Integridad DOCX, consistencia de fechas, documentos condicionados y código de producto | Escalar embargo, proceso judicial, suplantación, pago no aclarado o término crítico |
| CO-LA-001 | Laboral | Períodos, base salarial, conceptos, pagos confirmados, terminación y exclusiones | Contrato, desprendibles, pagos, novedades, liquidación y soportes | Integridad DOCX, cálculos reproducibles, valores en COP y variables resueltas | Siempre que exista riesgo laboral material o hechos no soportados |
| CO-LA-002 | Laboral | Partes, cargo, funciones, modalidad, jornada, remuneración, anexos y condiciones especiales | Identificaciones, perfil, oferta, activos, políticas y autorizaciones separadas | Generación real en CI, apertura `python-docx`, OOXML, código, hash y aprobación dual pendiente | Revisión jurídica específica y QA antes de liberación |
| CO-AR-001 | Arrendamiento | Partes, inmueble, destinación, canon, reajuste, servicios, plazo, garantías, inventario y restitución | Identificaciones, titularidad o facultad, inventario, recibos, reglamento y comunicaciones | Compuerta común integrada en todos los documentos v2.50 | Revisión de garantías, depósitos, terminación, copropiedad y hechos disputados |
| CO-EM-003 | Empresarial / contractual | Partes, representación, objeto, resultado, independencia, alcance, entregables, honorarios, aceptación y cambios | Certificados, propuesta, alcance, cronograma, entregables, actas y facturas | Normalización semántica no destructiva y compuerta común integrada | Revisión de riesgo de laboralidad, datos, IA, PI, confidencialidad y sanciones |
| CO-EM-004 | Empresarial / contractual | Partes, información protegida, finalidad, exclusiones, acceso, divulgación, devolución y duración | Identificaciones, autoridad de firma, inventario de información y canales | Integridad OOXML, variables resueltas, anexos seleccionados y trazabilidad | Revisión cuando existan secretos empresariales, datos personales o información regulada |
| CO-SA-001 | Salud | Solicitante, prestador o asegurador, hecho clínico, solicitud concreta, urgencia y soportes | Historia, órdenes, autorizaciones, respuestas, radicados y prueba de entrega | Integridad DOCX, consistencia de sujetos, fechas, anexos y advertencias | Obligatoria en urgencia, riesgo vital, litigio, tutela o controversia clínica compleja |
| CO-CD-001 | Constitucional / administrativo | Peticionario, destinatario competente, hechos, petición clara, anexos y notificación | Identificación, prueba del hecho, radicado, anexos y respuesta | Integridad DOCX, destinatario coherente, solicitudes numeradas y variables resueltas | Escalar términos vencidos, reserva, sanción, litigio o autoridad dudosa |
| CO-CD-003 | Consumidor | Relación de consumo, proveedor, producto o servicio, defecto o incumplimiento, reclamación y prueba | Factura, publicidad, garantía, comunicaciones, evidencia del defecto y respuesta | Integridad DOCX, pretensiones coherentes, anexos y código de producto | Revisión de cuantía, caducidad o prescripción, competencia y litigio activo |
| CO-CD-004 | Datos / consumidor | Titular, responsable o fuente, dato discutido, autorización, consulta o reclamo y respuesta | Consulta, reporte, autorización, comunicaciones, identidad y radicados | Integridad DOCX, identificación del dato, solicitudes trazables y variables resueltas | Revisión de datos sensibles, fraude, suplantación, sanción o proceso judicial |

## Reglas transversales de liberación

1. El archivo debe abrirse como paquete OOXML y mediante `python-docx`.
2. No puede contener variables dinámicas, `NULL`, `undefined` o `NaN` sin resolver.
3. Debe conservar el código del producto y un hash SHA-256 verificable.
4. Los nombres, identificaciones, fechas, valores, obligaciones, anexos y firmas deben ser coherentes entre sí.
5. Los anexos solo se generan cuando la regla o respuesta correspondiente los activa.
6. Una advertencia no equivale a aprobación: debe quedar visible para el especialista jurídico y QA.
7. Los documentos de riesgo alto, litigiosos, sancionatorios, laborales, de salud o regulatorios requieren revisión específica del caso.
8. La aprobación jurídica y la aprobación QA permanecen separadas y trazables.
9. Una nueva revisión no puede alterar el contenido ni el hash de una revisión ya cerrada.
10. La liberación final exige que la CI, el smoke HTTP y las verificaciones documentales estén aprobados.

## Despliegue incremental de la compuerta común

| Estado | Productos |
|---|---|
| Integración activa en fábrica | CO-EM-003, CO-AR-001 |
| Regresión real de generación en CI | CO-LA-002 |
| Siguiente ola de integración | CO-EM-004, CO-LA-001 |
| Ola administrativa y tránsito | CO-TR-001, CO-TR-002, CO-CD-001 |
| Ola regulada y consumidor | CO-SA-001, CO-CD-003, CO-CD-004 |
