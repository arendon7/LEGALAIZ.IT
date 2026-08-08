# Despliegue M33.1

`main` es la fuente de verdad. `ci.yml` valida la aplicación y `pages.yml` publica el frontend estático únicamente después de una validación satisfactoria.

## GitHub Pages

La vista estática se publica en `https://arendon7.github.io/LEGALAIZ.IT/`. No ejecuta Python, sesiones, generación DOCX ni persistencia de expedientes.

## Render — aplicación completa de demostración

El repositorio incluye `render.yaml` para crear un Web Service Docker sobre `main`.

### Creación

1. En Render selecciona **New → Blueprint**.
2. Conecta `arendon7/LEGALAIZ.IT`.
3. Selecciona la rama `main`.
4. Render leerá `render.yaml`.
5. Cuando solicite `LEGAL_DEMO_PASSWORD`, define una contraseña robusta para las cinco cuentas sintéticas.
6. Crea el Blueprint y espera a que el healthcheck `/api/live` quede saludable.

No es necesario definir manualmente `LEGAL_MASTER_KEY`: Render genera `LEGAL_MASTER_KEY_SEED` y LegalAIZ.it deriva en memoria una llave AES de 32 bytes. Tampoco es necesario fijar `LEGAL_PUBLIC_BASE_URL` para la URL estándar de Render: el runtime adopta `RENDER_EXTERNAL_URL` automáticamente.

### Controles activos

- plan de demostración explícito en `render.yaml`;
- despliegue automático solo después de checks satisfactorios;
- contraseña demo fuera de Git;
- secreto de cifrado administrado por el proveedor;
- control de origen activado;
- cookies seguras bajo HTTPS;
- healthcheck `/api/live`;
- apagado controlado mediante `SIGTERM`;
- ejecución Docker como usuario no root;
- SQLite y archivos de runtime en `/tmp/legalaiz-runtime` exclusivamente para la demo sintética.

### Persistencia

La configuración gratuita es deliberadamente efímera. Si la instancia reinicia, la cohorte de 11 expedientes y 76 documentos sintéticos puede reconstruirse automáticamente. No cargar información personal, expedientes reales ni documentos confidenciales en esta instancia.

Una futura demo persistente puede migrarse a un plan con almacenamiento persistente o PostgreSQL, pero ese cambio debe tratarse como una iteración independiente de infraestructura y costo.

## Ejecución local

Los iniciadores M33 generan una contraseña aleatoria por sesión cuando `LEGAL_DEMO_PASSWORD` no está definida:

- macOS: `01_INICIAR_DEMO_PUBLICA_MAC.command`
- Linux: `01_INICIAR_DEMO_PUBLICA_LINUX.sh`
- Windows: `01_INICIAR_DEMO_PUBLICA_WINDOWS.bat`

Por defecto escuchan en `127.0.0.1`, activan control de origen y usan HTTP local sin cookies `Secure`. Para exposición en red deben configurarse explícitamente host, URL pública y proxy TLS.

## Producción jurídica real

La demo pública utiliza cuentas y datos sintéticos y pagos sandbox. `REAL_PRODUCTION_AUTHORIZED=false` y `REAL_PAYMENTS_AUTHORIZED=false` son invariantes.

Producción jurídica real exige, como mínimo, PostgreSQL y persistencia certificados, secretos administrados, MFA, HTTPS, control de origen, almacenamiento adecuado, backup/restore, monitoreo, escaneo antimalware, pentest, privacidad, continuidad operativa y aprobación profesional independiente.
