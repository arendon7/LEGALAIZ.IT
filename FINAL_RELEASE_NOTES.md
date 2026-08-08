# LegalAIZ.it M33.1 — Despliegue público demostrativo endurecido

## Línea base canónica

M33.1 evoluciona M33.0 v5.1.1 sin retirar capacidades. Conserva la producción demostrativa pública integrada sobre M32.9 y añade controles específicos para desplegar la aplicación completa en un proveedor administrado sin versionar credenciales ni relajar las protecciones de navegador.

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
- Docker, Codespaces y Blueprint Render para la aplicación Python completa.

## Endurecimiento M33.1

- `render.yaml` fija explícitamente el plan de demostración y usa `autoDeployTrigger: checksPass`.
- `LEGAL_DEMO_PASSWORD` se solicita como secreto al crear el Blueprint; no existe una contraseña fija en Git.
- `LEGAL_MASTER_KEY_SEED` se genera en el proveedor y se deriva a una llave AES-256 válida antes de cargar el runtime.
- `RENDER_EXTERNAL_URL` se convierte automáticamente en `LEGAL_PUBLIC_BASE_URL` cuando no existe una URL explícita.
- El control de origen queda activo en la demo desplegada.
- Las cookies permanecen `Secure` bajo el acceso HTTPS público.
- `run.py` no imprime contraseñas en logs.
- Los iniciadores locales generan una contraseña aleatoria por sesión cuando el usuario no define una.
- La configuración gratuita se declara deliberadamente efímera y limitada a datos sintéticos.
- La suite incorpora regresiones específicas de Blueprint, secretos, derivación de llave y rechazo de orígenes no autorizados.

## Producción demostrativa

Cuando `LEGAL_PUBLIC_DEMO_MODE=true`, la aplicación habilita el flujo integral de demostración y declara `PRODUCTION_AUTHORIZED=true` exclusivamente para ese entorno. Se mantienen como invariantes `REAL_PRODUCTION_AUTHORIZED=false`, `REAL_PAYMENTS_AUTHORIZED=false`, datos sintéticos y pagos sandbox.

## Gobierno del repositorio

- `main` es la única fuente de verdad.
- `VERSION` contiene el identificador canónico M33.1.
- Solo `ci.yml` y `pages.yml` permanecen activos en GitHub Actions.
- El smoke M33 valida arranque, estado público, autenticación, control de origen, cohorte, integridad y compuerta demostrativa.
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
