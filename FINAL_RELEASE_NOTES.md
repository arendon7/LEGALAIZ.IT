# LegalAIZ.it M33.0 — Producción demostrativa pública integrada

## Línea base canónica de demostración

M33.0 integra la activación pública demostrativa aprobada en M31.9 v5.1.0 sobre la línea M32.9. Conserva las iteraciones M32.0 a M32.9 y no retira capacidades jurídicas, documentales, operativas, de comunicaciones, gobierno ni seguridad.

## Capacidades vigentes

- Portafolio de 11 productos jurídicos.
- Formularios demo, análisis, reglas y generación documental.
- Cohorte automática de 11 expedientes sintéticos y 76 documentos demo.
- Validación DOCX/OOXML, preflight y evidencia visual automatizada.
- Revisiones inmutables, comparación y liberación del hash exacto.
- Aprobación jurídica y QA independientes.
- Mesa Jurídica, asignaciones, alertas y SLA operativos.
- Notificaciones, calendario y comunicaciones sandbox auditables.
- Relaciones de contacto, preferencias, negativas, revocatorias y supresiones.
- Decisiones por titular, finalidad, canal, horario y frecuencia.
- Integridad cruzada de las cadenas M32.7, M32.8 y M32.9.
- RBAC, CSRF, control de origen y minimización de datos.
- GitHub Pages para la presencia pública estática.
- Docker, Codespaces y blueprint Render para la aplicación Python completa.

## Producción demostrativa

Cuando `LEGAL_PUBLIC_DEMO_MODE=true`, la aplicación habilita el flujo integral de demostración y declara `PRODUCTION_AUTHORIZED=true` exclusivamente para ese entorno. Se mantienen como invariantes `REAL_PRODUCTION_AUTHORIZED=false`, `REAL_PAYMENTS_AUTHORIZED=false`, datos sintéticos y pagos sandbox.

## Gobierno del repositorio

- `main` es la única fuente de verdad.
- `VERSION` contiene el identificador canónico M33.0.
- Solo `ci.yml` y `pages.yml` permanecen activos en GitHub Actions.
- M33 añade un smoke específico de producción demostrativa a la CI existente.
- Los workflows especializados anteriores permanecen únicamente como historial recuperable en Git.

## Límites expresos

Esta línea base no acredita:

- aprobación jurídica de casos o documentos reales;
- aprobación QA profesional de asuntos reales;
- entrega externa, recepción, firma o notificación efectiva;
- radicación ante autoridades;
- representación judicial;
- cómputo automático de términos legales;
- pagos reales;
- producción jurídica real con persistencia, secretos, proveedores, monitoreo y recuperación operativa certificados.

Los estados de entrega, aprobación y evidencia usados en la demostración son sintéticos. Cualquier despliegue real exige revisión profesional, configuración segura y validación independiente.
