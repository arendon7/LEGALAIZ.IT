# LegalAIZ.it — V1-R0 Release Readiness Gate

## Objetivo

V1-R0 inicia la transición desde la producción demostrativa M33.1 + stack M34-M37 hacia una futura operación jurídica real. No cambia la versión canónica, no autoriza producción real, no autoriza pagos reales y no sustituye aprobaciones humanas.

El gate responde una sola pregunta: **¿existe evidencia suficiente para considerar preparado el release candidate para una autorización separada de producción?**

## Principios

1. **Fail closed.** Toda evidencia ausente o no verificable bloquea readiness.
2. **No autoautorización.** `platform_ready=true` nunca modifica `REAL_PRODUCTION_AUTHORIZED`.
3. **Pagos separados.** `payments_ready` y `commercial_ready` se evalúan aparte del núcleo jurídico-operativo.
4. **Aprobaciones humanas independientes.** Seguridad, privacidad, operación jurídica y QA requieren atestación externa/humana separada.
5. **No confiar sólo en flags.** Cuando el repositorio declara artefactos técnicos obligatorios, el gate verifica que realmente existan.
6. **Mínimo privilegio.** El endpoint es read-only y sólo accesible por `admin`.
7. **Minimización.** La respuesta no devuelve secretos, connection strings, inventarios de usuarios MFA, payloads jurídicos ni evidencias sensibles.

## Endpoint

`GET /api/release/v1/readiness`

Requisitos:

- sesión autenticada;
- rol `admin`;
- rate limit específico;
- sin operación POST asociada.

## Capas de readiness

### 1. Aplicación

- stack incremental M34.1 → M37.3 presente;
- runtime activo sobre el handler M37.3 certificado;
- piso canónico de 11 productos y 473 preguntas preservado.

### 2. Entorno y seguridad

- `LEGAL_PROFILE=production`;
- modo de demo pública deshabilitado;
- límite `SYNTHETIC_DATA_ONLY` retirado mediante una release posterior y gobernada;
- llave maestra administrada;
- cookies Secure;
- HTTPS público;
- control de origen;
- MFA para roles privilegiados;
- cifrado de volumen/base;
- antimalware operativo.

### 3. Persistencia y resiliencia

- backend PostgreSQL;
- driver disponible;
- artefactos de certificación PostgreSQL presentes en el repositorio;
- ejecución externa certificada contra PostgreSQL real;
- migración certificada;
- backup/restore PostgreSQL certificado;
- almacenamiento de objetos durable, cifrado y certificado.

### 4. Operación

- monitoreo/alertas certificados;
- respuesta a incidentes certificada;
- revisión independiente de seguridad.

### 5. Gobierno jurídico y de datos

- fuentes jurídicas canónicas verificadas;
- aprobación de privacidad y tratamiento de datos;
- aprobación del modelo operativo jurídico;
- aprobación del modelo QA humano.

### 6. Pagos reales

Se evalúan por separado:

- `REAL_PAYMENTS_AUTHORIZED`;
- proveedor real de pagos certificado.

Por diseño, una plataforma puede llegar a `platform_ready=true` y seguir con `commercial_ready=false` hasta cerrar pagos reales.

## Brechas descubiertas al iniciar V1-R0

El runtime heredado declara que la certificación PostgreSQL requiere, entre otros artefactos:

- `tools/postgres_certify.py`;
- `tools/export_postgres_schema.py`;
- `tools/migrate_sqlite_to_postgres.py`;
- `deploy/PREPRODUCTION_RUNBOOK_M31_4.md`;
- `requirements-postgres.txt`.

V1-R0 verifica físicamente esos archivos. En el punto de partida del incremento, al menos `tools/postgres_certify.py` no existe en el árbol, por lo que la certificación PostgreSQL no puede darse por acreditada.

También permanecen como bloqueos estructurales de la línea actual:

- `REAL_PRODUCTION_AUTHORIZED=false`;
- `REAL_PAYMENTS_AUTHORIZED=false`;
- `SYNTHETIC_DATA_ONLY=true`;
- perfil demo/local en CI;
- almacenamiento local cifrado, no storage durable externo certificado;
- atestaciones externas de monitoreo, incidentes, seguridad, privacidad, operación legal y QA aún no acreditadas.

## Estados

- `platform_ready`: todos los controles bloqueantes del núcleo están satisfechos.
- `payments_ready`: pagos reales autorizados + proveedor certificado.
- `commercial_ready`: `platform_ready && payments_ready`.
- `activation_authorized`: `platform_ready && REAL_PRODUCTION_AUTHORIZED`.

El gate nunca escribe ni cambia estas autorizaciones.

## Fuera de alcance de V1-R0

- implementar PostgreSQL faltante o certificarlo externamente;
- implementar storage S3/managed;
- habilitar pagos reales;
- cambiar `VERSION`;
- cambiar `REAL_PRODUCTION_AUTHORIZED`;
- usar datos reales;
- reemplazar revisión jurídica o QA humana;
- declarar cumplimiento regulatorio general.

## Siguiente secuencia recomendada

1. V1-R0 — gate ejecutable de readiness.
2. V1-R1 — persistencia PostgreSQL certificable + migración + backup/restore real.
3. V1-R2 — object storage durable + malware + data lifecycle.
4. V1-R3 — observabilidad, alertas, incident response y security hardening.
5. V1-R4 — privacy/legal/QA operational certification.
6. V1-R5 — pagos reales o decisión explícita de lanzamiento sin checkout real.
7. V1-RC — release candidate integrado, pruebas de regresión, restore drill, security review y aprobación humana final.
8. Sólo entonces: promoción de línea base, actualización de `VERSION`, README, release notes y autorización explícita.
