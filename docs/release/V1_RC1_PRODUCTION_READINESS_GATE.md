# V1-RC1 — Production Readiness Gate

## 1. Objetivo

V1-RC1 endurece la transición desde el candidato integrado V1-RC0 hacia un entorno de validación productiva controlada. No activa pagos reales, comunicaciones externas ni publicación comercial por defecto.

La compuerta separa tres conceptos que no deben confundirse:

1. **arranque técnico seguro**: el proceso puede cargar el perfil `production` sin una configuración evidentemente insegura;
2. **validación productiva controlada**: además del arranque seguro, existen las evidencias externas canónicas requeridas;
3. **lanzamiento comercial**: además de lo anterior, existen autorizaciones humanas, proveedores reales validados y la metadata de release autoriza expresamente producción y pagos reales.

## 2. Arranque fail-closed

`legalai_platform.deployment_environment.prepare_deployment_environment()` se ejecuta antes de importar el runtime principal. Cuando `LEGAL_PROFILE=production`, V1-RC1 exige como mínimo:

- `LEGAL_APP_ENV=production`;
- URL pública HTTPS no local y sin placeholders;
- cookies `Secure`;
- control de origen;
- proxy confiable activado y lista explícita de proxies sin comodines globales;
- cuentas demo desactivadas;
- modo public-demo desactivado;
- PostgreSQL como backend;
- `DATABASE_URL` administrada y no-placeholder;
- certificación externa PostgreSQL declarada;
- cifrado de objetos;
- cifrado del volumen confirmado;
- ClamAV como scanner antimalware;
- MFA obligatorio, como mínimo, para `admin` y `specialist`;
- llave maestra desde `LEGAL_MASTER_KEY`, `LEGAL_MASTER_KEY_FILE` o `LEGAL_MASTER_KEY_SEED`;
- bootstrap admin opcional, pero si existe debe ser un par email/contraseña no-demo y no-placeholder.

Si cualquiera falla, se lanza `ProductionConfigurationError` antes de cargar `core_v11`. El error enumera únicamente claves de control; no imprime `DATABASE_URL`, llaves, seeds ni contraseñas.

Los perfiles `local` y `pilot` no cambian por esta compuerta. La producción demostrativa M33.1 en Render continúa siendo `LEGAL_PROFILE=local` y, por tanto, no se presenta como producción comercial real.

## 3. Evidencia externa

La validación productiva controlada consume el registro canónico `ExternalAttestationRegistry` y exige exactamente estas diez evidencias:

- `postgres_runtime`;
- `tls_certificate`;
- `monitoring_alerts`;
- `restore_drill_production`;
- `load_test`;
- `pentest`;
- `privacy_approval`;
- `incident_drill`;
- `mac_windows_validation`;
- `rollback_drill`.

La política RC1 falla si esta lista diverge del registro canónico. No se reemplaza una evidencia externa por una variable de entorno o por un test unitario.

## 4. Frontera comercial

`V1RC1ProductionReadinessGate` no modifica estado ni activa proveedores. Para poder representar un estado hipotético `COMMERCIAL_LAUNCH_READY`, deben coincidir todas las capas:

- arranque productivo seguro;
- diez atestaciones externas aprobadas y con evidencia;
- `LEGAL_PRODUCTION_LAUNCH_AUTHORIZED=true`;
- `LEGAL_REAL_PAYMENTS_AUTHORIZED=true`;
- proveedor de pagos distinto de `sandbox`, `disabled` o `none`;
- `LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED=true`;
- proveedor transaccional distinto de `sandbox`, `disabled` o `none`;
- aprobación final jurídica del portafolio;
- aprobación final QA del portafolio;
- aprobación final de privacidad;
- `release_metadata.REAL_PRODUCTION_AUTHORIZED=True`;
- `release_metadata.REAL_PAYMENTS_AUTHORIZED=True`;
- `release_metadata.SYNTHETIC_DATA_ONLY=False`.

Una variable de entorno no puede sobreescribir una prohibición de `release_metadata`. En la línea RC0/RC1 actual, la metadata mantiene `REAL_PRODUCTION_AUTHORIZED=False`, `REAL_PAYMENTS_AUTHORIZED=False` y `SYNTHETIC_DATA_ONLY=True`; por diseño, el lanzamiento comercial continúa bloqueado.

## 5. Estados públicos del gate

- `NOT_PRODUCTION_PROFILE`: el gate comercial se consulta fuera de production.
- `BLOCKED_CONFIGURATION`: falla uno o más controles de arranque.
- `BLOCKED_EXTERNAL_EVIDENCE`: la configuración es segura, pero faltan atestaciones externas.
- `READY_FOR_CONTROLLED_PRODUCTION_VALIDATION`: infraestructura/evidencia podrían permitir una validación controlada, pero el lanzamiento comercial sigue bloqueado.
- `BLOCKED_UNSAFE_LAUNCH_CLAIM`: alguien solicita autorización comercial sin cumplir todas las capas.
- `COMMERCIAL_LAUNCH_READY`: estado posible sólo cuando todas las compuertas futuras estén expresamente satisfechas.

## 6. Plantilla de entorno

`.env.production.example` es intencionalmente no ejecutable. Contiene placeholders y mantiene las autorizaciones comerciales en `false`. No debe convertirse en `.env` sin sustituir valores desde infraestructura administrada y completar evidencia.

Nunca deben versionarse:

- `DATABASE_URL` real;
- llaves AES;
- seeds de llave;
- contraseñas bootstrap;
- tokens de proveedores;
- credenciales de scanner, correo o pago.

## 7. Certificación automatizada

La suite incorpora:

- pruebas de cada frontera técnica de startup;
- compatibilidad del public-demo M33.1;
- bloqueo de cuentas demo/HTTP/SQLite/MFA incompleto/scanner ausente;
- prueba de no filtración de secretos;
- equivalencia exacta de las diez atestaciones;
- imposibilidad de autorizar lanzamiento sólo con env vars;
- rechazo de proveedores sandbox/disabled;
- prueba hipotética del estado final sólo cuando todas las capas, incluida release metadata, se vuelven verdaderas;
- ejecución de `tools/v1_rc1_readiness_gate.py` dentro de `unittest`.

## 8. Límite de alcance

V1-RC1 es una compuerta técnica y de gobernanza. No sustituye revisión jurídica humana, QA humano de documentos, evaluación de protección de datos, pentest, pruebas de carga, simulacro de incidentes, restore productivo, rollback, validación Mac/Windows ni aprobación de proveedores de pago/comunicación.
