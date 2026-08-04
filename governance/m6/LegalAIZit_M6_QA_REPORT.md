# LegalAIZ.it M6 — Informe de QA de Release Candidate

**Fecha:** 29 de julio de 2026  
**Build:** `M6-RELEASE-CANDIDATE-2026-07-29`  
**Versión jurídica:** 2.59  
**Estado:** preparada para piloto profesional controlado; no certificada para producción pública.

## 1. Alcance validado

- Frontend activo único: `app/index.html`, `app/main.js` y `app/app.css`.
- Navegación por rol, catálogo de 11 soluciones y expediente jurídico único.
- Bibliotecas profundas M4 y M5: 4 productos contractuales y 7 playbooks.
- 78 documentos DOCX y 78 PDF profundos con hashes verificados.
- 387 documentos canónicos M3 preservados como evidencia histórica con rutas rebasadas y hashes íntegros.
- CSP estricta, errores internos genéricos, cuentas demo restringidas al perfil local y administrador institucional configurable.
- Separación entre preparación de contenido, piloto controlado y producción pública.

## 2. Regresión activa

La suite activa se ejecutó con `tools/run_m6_regression.py`, aislando cada módulo en un proceso independiente para impedir contaminación por servidores HTTP y estados temporales heredados.

- **15 módulos de prueba.**
- **107 pruebas aprobadas.**
- **630 subpruebas aprobadas.**
- **0 fallas.**
- **0 errores.**
- Duración: 218,2 segundos.

Cobertura: motor de reglas, seguridad, fábrica documental, trazabilidad, ingesta de fuentes, revisión asistida, lotes, actualización normativa, infraestructura, workflows, portal, autoservicio, continuidad, aceptación PDF y gate M6.

Las suites históricas v1.1–M5 se conservaron bajo `governance/archive/tests_legacy`. Varias comprobaban archivos `app-v*.js`, `styles-v*.css` y rutas retiradas deliberadamente en M6. No se contabilizan como regresión vigente. Se intentó ejecutar la colección histórica conjunta, pero su ciclo de vida de servidores locales y sus aserciones sobre frontend retirado impiden usarla como gate fiable de M6; por ello fue sustituida por una suite actual aislada y trazable.

## 3. Smoke test HTTP

`tools/m6_smoke_test.py` ejecutó **10 de 10 comprobaciones aprobadas**:

- salud;
- autenticación;
- configuración;
- catálogo de productos;
- estado de aprobación;
- preparación RC;
- gobierno;
- shell HTML;
- JavaScript principal;
- CSS principal.

## 4. Validación estática

- Python 3.9 mediante AST: **355 archivos, 0 errores**.
- `compileall`: aprobado.
- JavaScript: `node --check app/main.js`, aprobado.
- CSS: **387 reglas, 0 errores de parseo**.
- JSON: **488 archivos, 0 errores**.
- Frontend activo: **0 manejadores `onclick` inline** y **0 atributos `style` inline**.
- Directorio activo `app/`: un HTML, un JavaScript y un CSS principales.
- Raíz Python activa: **26 módulos**.
- Implementaciones versionadas aisladas: **88 módulos** en `legacy_runtime/`.
- Herramientas históricas archivadas: **52** en `governance/archive/tools_legacy/`.

## 5. QA visual y responsive

Se renderizaron **15 vistas**: 12 de escritorio y 3 móviles. El CSS y JavaScript utilizados fueron los archivos reales M6, con respuestas reales capturadas del servidor HTTP local.

- 0 errores de JavaScript o consola.
- 0 recortes críticos, solapamientos o caracteres rotos observados.
- Inicio, Soluciones, Nueva solución, Casos, Documentos, Operación, Catálogo, Fuentes, Calidad, Configuración, Biblioteca contractual y Biblioteca de playbooks inspeccionados.
- Inicio, Soluciones y Calidad inspeccionados en ancho móvil.

El entorno bloqueó a Chromium el acceso directo a `localhost`. Para no confundir esa restricción con una falla del producto, se verificó por separado el servidor HTTP real y se renderizó el frontend real en un documento aislado con payloads capturados de esa API.

## 6. Accesibilidad estructural

- **15 de 15 vistas aprobadas.**
- 0 identificadores duplicados.
- 0 controles visibles sin nombre.
- 0 imágenes sin texto alternativo.
- 0 saltos en jerarquía de encabezados.
- 0 desbordamientos horizontales.
- `lang="es"`, enlace de salto, un `h1` y landmark principal presentes en cada vista.
- Foco visible global para teclado.

El acta M6 en DOCX obtuvo **0 hallazgos altos, medios o bajos** en la auditoría de accesibilidad y sus cuatro páginas fueron renderizadas e inspeccionadas.

## 7. Readiness

- Compuertas de contenido: **18/18**.
- Preparación de Release Candidate: **sí**.
- Piloto profesional controlado: **sí** en perfil local/pilot.
- Producción pública: **no**.
- Score combinado en perfil local: **91 %**.
- Infraestructura: **11/14** comprobaciones aprobadas.

Bloqueos expresos del entorno actual:

1. backup cifrado restaurado y verificado;
2. migración runtime a PostgreSQL;
3. incorporación/certificación de fuentes canónicas binarias en el doctor heredado.

Además, el go-live requiere HTTPS, cookies Secure, gestor de secretos, MFA obligatorio, antimalware, observabilidad, pentest, carga, privacidad, rollback y validación en equipos reales.

## 8. Conclusión

M6 cumple el gate de **Release Candidate para piloto profesional controlado**. No se declara lista para producción pública ni validada por revisores externos independientes. Los expedientes de alto impacto o riesgo rojo mantienen revisión específica obligatoria.
