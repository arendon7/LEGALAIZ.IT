# LegalAIZ.it M32.9

## Línea base canónica de demostración

M32.9 consolida las iteraciones M32.0 a M32.8 y añade una compuerta de gobierno de contacto antes del procesamiento de comunicaciones transaccionales.

## Capacidades vigentes

- Portafolio de 11 productos jurídicos.
- Formularios demo, análisis, reglas y generación documental.
- Validación DOCX/OOXML, preflight y evidencia visual automatizada.
- Revisiones inmutables, comparación y liberación del hash exacto.
- Aprobación jurídica y QA independientes.
- Mesa Jurídica, asignaciones, alertas y SLA operativos.
- Notificaciones, calendario y comunicaciones sandbox auditables.
- Relaciones de contacto, preferencias, negativas, revocatorias y supresiones.
- Decisiones por titular, finalidad, canal, horario y frecuencia.
- Integridad cruzada de las cadenas M32.7, M32.8 y M32.9.
- RBAC, CSRF, control de origen y minimización de datos.

## Gobierno del repositorio

- `main` es la única fuente de verdad.
- `VERSION` contiene el identificador canónico.
- Solo `ci.yml` y `pages.yml` permanecen activos en GitHub Actions.
- Los workflows especializados anteriores se retiraron del árbol actual; sus definiciones permanecen recuperables en Git y en los PR fusionados.
- La documentación de iteraciones se considera histórica salvo la descripción de M32.9 y los documentos expresamente señalados como vigentes en `docs/README.md`.

## Límites expresos

Esta línea base no acredita:

- aprobación jurídica de casos o documentos reales;
- aprobación QA profesional de asuntos reales;
- entrega externa, recepción, firma o notificación efectiva;
- radicación ante autoridades;
- representación judicial;
- cómputo automático de términos legales;
- producción pública con secretos, proveedores, monitoreo y recuperación operativa validados.

Los estados de entrega, aprobación y evidencia usados en pruebas son sintéticos. Cualquier despliegue real exige revisión profesional, configuración segura y validación independiente.
