# Matriz de control jurídico-documental M32.2

Esta matriz no reemplaza las reglas, fuentes ni aprobaciones de cada producto. Define la compuerta transversal mínima que debe aplicarse a los once productos canónicos antes de considerar un documento listo para demostración o liberación.

| Producto | Familia | Control sustantivo mínimo | Evidencia que debe conservarse | Compuerta documental | Revisión humana |
|---|---|---|---|---|---|
| CO-TR-001 | Tránsito / administrativo | Autoridad, territorio, fecha, identificación del dispositivo, estado oficial y etapa | Consulta, acto, comparendo, certificación y cronología | Integridad OOXML, apertura editable, hash, preflight visual y manifiesto M32.2 | Escalar cobro coactivo, fraude, litigio, urgencia o inconsistencia probatoria |
| CO-TR-002 | Tránsito / administrativo | Cronología, notificación, imputación, evidencia técnica, etapa y términos | Comparendo, constancias de notificación, expediente, SIMIT/RUNT y comunicaciones | Integridad OOXML, consistencia técnica, hash, preflight visual y manifiesto M32.2 | Escalar embargo, proceso judicial, suplantación, pago no aclarado o término crítico |
| CO-LA-001 | Laboral | Períodos, base salarial, conceptos, pagos confirmados, terminación y exclusiones | Contrato, desprendibles, pagos, novedades, liquidación y soportes | Compuerta común, conciliación económica, hash y preflight visual integrados en v2.53 | Siempre que exista riesgo laboral material o hechos no soportados |
| CO-LA-002 | Laboral | Partes, cargo, funciones, modalidad, jornada, remuneración, anexos y condiciones especiales | Identificaciones, perfil, oferta, activos, políticas y autorizaciones separadas | Generación real, OOXML, hash, preflight visual y renderizado PDF/PNG en CI | Revisión jurídica específica y QA visual antes de liberación |
| CO-AR-001 | Arrendamiento | Partes, inmueble, destinación, canon, reajuste, servicios, plazo, garantías, inventario y restitución | Identificaciones, titularidad o facultad, inventario, recibos, reglamento y comunicaciones | Compuerta común integrada en todos los documentos v2.50 | Revisión de garantías, depósitos, terminación, copropiedad y hechos disputados |
| CO-EM-003 | Empresarial / contractual | Partes, representación, objeto, resultado, independencia, alcance, entregables, honorarios, aceptación y cambios | Certificados, propuesta, alcance, cronograma, entregables, actas y facturas | Normalización semántica no destructiva y compuerta común integrada | Revisión de riesgo de laboralidad, datos, IA, PI, confidencialidad y sanciones |
| CO-EM-004 | Empresarial / contractual | Partes, información protegida, finalidad, exclusiones, acceso, divulgación, devolución y duración | Identificaciones, autoridad de firma, inventario de información y canales | Compuerta común, hash, preflight visual y renderizado PDF/PNG en CI integrados en v2.47 | Revisión cuando existan secretos empresariales, datos personales o información regulada |
| CO-SA-001 | Salud | Solicitante, prestador o asegurador, hecho clínico, solicitud concreta, urgencia y soportes | Historia, órdenes, autorizaciones, respuestas, radicados y prueba de entrega | Integridad OOXML, sujetos y fechas consistentes, hash, preflight visual y manifiesto M32.2 | Obligatoria en urgencia, riesgo vital, litigio, tutela o controversia clínica compleja |
| CO-CD-001 | Hábeas data financiero | Titular, fuente, operador, dato discutido, solicitud, cronología y soportes | Consulta, reporte, autorización, comunicaciones, identidad y radicados | Integridad OOXML, destinatarios y solicitudes trazables, hash y manifiesto M32.2 | Escalar fraude, suplantación, término crítico, sanción, litigio o autoridad dudosa |
| CO-CD-003 | Consumidor | Relación de consumo, proveedor, producto o servicio, defecto o incumplimiento, reclamación y prueba | Factura, publicidad, garantía, comunicaciones, evidencia del defecto y respuesta | Integridad OOXML, mecanismo y pretensiones coherentes, hash y manifiesto M32.2 | Revisión de cuantía, términos, competencia, excepciones y litigio activo |
| CO-CD-004 | Cobro y formalización | Acreedor, deudor, origen, saldo, título, tasa, pagos, etapa y soportes | Contrato, factura o título, estado de cuenta, abonos, comunicaciones y garantías | Integridad OOXML, conciliación económica, hash, preflight visual y manifiesto M32.2 | Revisión de prescripción, insolvencia, embargo, fraude, capacidad o proceso activo |

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
11. Todo preflight visual debe registrar `requires_human_visual_review: true` hasta la inspección humana de todas las páginas.
12. La existencia de PDF y PNG renderizados prueba la capacidad de representación, pero no equivale a aprobación estética o jurídica.
13. Cada DOCX generado por el constructor común debe producir un manifiesto lateral `.docx.quality.json` con integridad, hash, preflight, advertencias y estado de aprobación dual.
14. Un error técnico en la compuerta bloquea la devolución del archivo al flujo de generación.

## Estado de despliegue acumulado

| Estado | Productos |
|---|---|
| Compuerta transversal activa al iniciar la aplicación | Los 11 productos canónicos |
| Integración especializada previa | CO-EM-003, CO-EM-004, CO-AR-001, CO-LA-001, CO-LA-002 |
| Ola M32.2 incorporada a la compuerta común | CO-TR-001, CO-TR-002, CO-SA-001, CO-CD-001, CO-CD-003, CO-CD-004 |
| Evidencia PDF/PNG automatizada M32.1 | CO-EM-004, CO-LA-002 |
| Evidencia PDF/PNG automatizada M32.2 | Una muestra real de cada uno de los seis productos de la ola |
| Aprobación humana jurídica y QA | Permanece pendiente por documento y revisión |
