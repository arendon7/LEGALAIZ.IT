# LegalAIZ.it — M33.1 · v5.1.2

**Versión canónica del repositorio:** M33.1  
**Estado:** producción demostrativa pública endurecida, revisión y desarrollo incremental.  
**Jurisdicción principal:** Colombia.

[![Validación LegalAIZ.it](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml/badge.svg)](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/pages.yml/badge.svg)](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/pages.yml)

> M33.1 conserva íntegramente M33.0 y M32.9 y endurece el despliegue de la producción demostrativa pública: elimina credenciales fijas del repositorio, activa control de origen, mantiene cookies seguras bajo HTTPS, deriva la llave de cifrado desde un secreto administrado por el proveedor y condiciona el autodespliegue a CI satisfactoria. No acredita aprobación profesional de asuntos reales, representación judicial, radicación, firma, notificación externa ni entrega efectiva.

## Fuente de verdad

- Rama vigente: `main`.
- Marcador de versión: [`VERSION`](VERSION).
- Notas de versión: [`FINAL_RELEASE_NOTES.md`](FINAL_RELEASE_NOTES.md).
- Estado documental y técnico: [`docs/README.md`](docs/README.md).
- Guía de despliegue M33: [`docs/DESPLIEGUE_M33.md`](docs/DESPLIEGUE_M33.md).
- Historial de cambios: pull requests fusionados y commits de Git.

Las ramas de trabajo y los documentos de iteraciones anteriores son históricos. No deben utilizarse como versión vigente ni como base de nuevas modificaciones.

## Capacidades consolidadas

M33.1 conserva las capacidades acumuladas hasta M33.0 y añade controles de despliegue:

- 11 productos jurídicos y formularios demo completos;
- 11 expedientes sintéticos precargados y 76 documentos demo;
- generación DOCX con compuertas de integridad, OOXML y preflight visual;
- expedientes, revisiones inmutables, comparación y liberación por SHA-256;
- aprobación jurídica y QA separadas;
- Mesa Jurídica, asignaciones, SLA operativos y alertas;
- centro de notificaciones, calendario operativo y cola externa sandbox;
- comunicaciones transaccionales auditables sin entrega real;
- relaciones, preferencias, negativas, revocatorias, supresiones y decisiones de contacto trazables;
- RBAC, CSRF, control de origen, minimización de datos y cadenas append-only;
- landing, catálogo público, diagnóstico guiado y checkout sandbox;
- bootstrap automático de la cohorte cuando `LEGAL_PUBLIC_DEMO_MODE=true`;
- Blueprint Render con plan explícito, despliegue tras checks verdes y secretos fuera de Git.

## Vista pública — GitHub Pages

La landing y la interfaz estática se publican automáticamente en:

https://arendon7.github.io/LEGALAIZ.IT/

GitHub Pages no ejecuta el backend Python. Sirve como presencia pública sincronizada con `main`.

## Aplicación completa desde GitHub

### Codespaces

1. Selecciona **Code**.
2. Abre **Codespaces**.
3. Crea un codespace sobre `main`.
4. Ejecuta `01_INICIAR_DEMO_PUBLICA_LINUX.sh` o inicia `run.py` con el perfil demo.
5. Abre el puerto publicado por el entorno.

Acceso directo:

https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=1322097934

### Ejecución local de la producción demostrativa

- macOS: `01_INICIAR_DEMO_PUBLICA_MAC.command`
- Windows: `01_INICIAR_DEMO_PUBLICA_WINDOWS.bat`
- Linux: `01_INICIAR_DEMO_PUBLICA_LINUX.sh`

Si `LEGAL_DEMO_PASSWORD` no está definida, los iniciadores locales generan una contraseña aleatoria para esa sesión y la muestran únicamente en la terminal local. No existe una contraseña fija versionada.

### Docker / Render

- `deploy/docker-compose.public-demo.yml` levanta la demo con Docker Compose.
- `render.yaml` define el servicio web conectado a `main`.
- `Dockerfile` acepta el puerto dinámico del proveedor y conserva el healthcheck `/api/live`.
- Render solicita `LEGAL_DEMO_PASSWORD` al crear el Blueprint; el valor no se almacena en Git.
- `LEGAL_MASTER_KEY_SEED` es generado por el proveedor y se deriva en runtime a una llave AES de 32 bytes.
- `RENDER_EXTERNAL_URL` se adopta automáticamente como `LEGAL_PUBLIC_BASE_URL`, permitiendo control de origen real.
- El autodespliegue está configurado para ejecutarse después de checks satisfactorios.

La instancia gratuita de demostración usa almacenamiento efímero y reconstruye la cohorte sintética al iniciar. No debe recibir información real. Para producción jurídica real se exige persistencia certificada y la infraestructura adicional descrita abajo.

## Credenciales demo

Cuentas sintéticas disponibles:

- Administración / QA: `ana@demo.legalaiz.it`
- Cliente: `juan@demo.legalaiz.it`
- Especialista laboral: `maria@demo.legalaiz.it`
- Especialista contractual: `carlos@demo.legalaiz.it`
- Especialista tránsito: `laura@demo.legalaiz.it`

**Contraseña:** valor configurado en `LEGAL_DEMO_PASSWORD`. No se publica ni se fija en el repositorio.

Estas cuentas son exclusivamente demostrativas y deben permanecer deshabilitadas fuera del perfil demo autorizado.

## Separación de entornos

`LEGAL_PUBLIC_DEMO_MODE=true` permite presentar toda la plataforma como producción demostrativa. En ese perfil:

- `PRODUCTION_AUTHORIZED=true` significa únicamente autorización de la demostración;
- `REAL_PRODUCTION_AUTHORIZED=false` permanece invariable;
- `REAL_PAYMENTS_AUTHORIZED=false` permanece invariable;
- todos los datos deben ser sintéticos y los pagos permanecen sandbox.

Producción jurídica real requiere, entre otros controles, PostgreSQL certificado, secretos administrados, MFA, HTTPS/control de origen, persistencia, backup/restore, monitoreo, pruebas de seguridad y aprobación profesional independiente.

## Validación automática

Solo existen dos workflows activos:

- `ci.yml`: sintaxis, suite completa, 11 productos, cobertura de formularios, arranque HTTP, smoke M33 con rechazo de origen no autorizado y renderizado DOCX;
- `pages.yml`: publicación posterior a una validación satisfactoria de `main`.

La CI usa concurrencia con cancelación de ejecuciones equivalentes. Las definiciones históricas de workflows no forman parte del árbol operativo.

**LegalAIZ.it — Más que respuestas, soluciones.**
