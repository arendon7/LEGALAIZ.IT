# V1 — Controlled Pilot Readiness Gate

## 1. Objetivo

Esta fase convierte el candidato técnicamente endurecido V1-RC2 en un proceso de **preparación de piloto controlado**, sin confundir preparación con autorización de producción comercial.

No añade funcionalidades jurídicas al journey M34–M37 y no modifica la Fábrica Documental, RBAC, revisión dual, proveedores, `release_metadata` ni flags de despliegue.

La compuerta distingue cuatro conceptos:

1. **assurance RC2**: configuración productiva segura + 10/10 evidencias externas vigentes y ratificadas;
2. **gobernanza de piloto**: alcance explícito + aprobación jurídica + QA + privacidad + seguridad/operaciones + ratificación final;
3. **ventana de ejecución**: el piloto sólo puede ejecutarse entre `starts_on` y `ends_on`;
4. **autorización por modo**: datos sintéticos y clientes reales tienen fronteras diferentes.

## 2. Base certificada

La rama `release/v1-pilot-readiness` parte del V1-RC2 certificado:

`c39ab67124ff2139c58f34d583d4748e4b23e11a`

La nueva compuerta consume `V1RC2ReleaseAssuranceGate`; no reemplaza ni debilita RC1/RC2.

## 3. Plan de piloto

Cada plan registra de forma append-only:

- `pilot_id` estable;
- modo;
- fecha inicial y final;
- límite de usuarios;
- límite de tenants;
- subconjunto de productos;
- alcance de datos;
- modo de pagos;
- modo de comunicaciones externas;
- propósito interno.

La política actual limita el piloto a:

- máximo **45 días**;
- máximo **25 usuarios**;
- máximo **5 tenants**;
- uno o más productos tomados exclusivamente de los **11 contratos canónicos M34**.

Estos límites son de gobierno operativo del piloto. **No son términos legales, periodos regulatorios ni recomendaciones jurídicas.**

No puede existir más de un plan activo. Un cambio material de alcance exige revocar el plan anterior y registrar uno nuevo; no se sobreescribe el histórico.

## 4. Modos

### `SYNTHETIC_CONTROLLED`

Requiere:

- `data_scope = SYNTHETIC_ONLY`;
- pagos `DISABLED` o `SANDBOX_ONLY`;
- comunicaciones externas `DISABLED`.

Este modo está diseñado para un piloto de validación de producto, operaciones, UX y journey sin afirmar tratamiento autorizado de datos de clientes reales.

### `REAL_CLIENT_CONTROLLED`

Requiere:

- `data_scope = REAL_CLIENT_DATA`;
- pagos `DISABLED`, `SANDBOX_ONLY` o `REAL_PROVIDER`;
- comunicaciones `DISABLED` o `REAL_PROVIDER`.

La mera selección del modo no lo autoriza. Debe superar adicionalmente la frontera de `release_metadata` y, cuando aplique, proveedores reales y autorizaciones específicas.

Con la metadata actual de LegalAIZ.it:

- `REAL_PRODUCTION_AUTHORIZED=False`;
- `REAL_PAYMENTS_AUTHORIZED=False`;
- `SYNTHETIC_DATA_ONLY=True`;

por diseño, **un piloto con clientes reales continúa bloqueado**.

Variables de entorno no pueden sobreescribir esa prohibición versionada.

## 5. Aprobaciones humanas

Un plan requiere cuatro dominios independientes:

| Dominio | Rol permitido |
|---|---|
| Jurídico | `specialist` |
| QA | `qa` |
| Privacidad | `admin` o `specialist` |
| Seguridad / Operaciones | `admin` o `qa` |

Reglas adicionales:

- jurídico y QA deben usar `actor_id` distintos;
- la ratificación final sólo puede realizarla `admin` o `qa`;
- el ratificador debe ser distinto de los aprobadores jurídico y QA;
- una aprobación existente no se reemplaza silenciosamente;
- retries exactos del mismo actor son idempotentes;
- cambiar un aprobador exige revocar y volver a registrar el plan.

Estas aprobaciones no sustituyen la aprobación dual documento por documento ya existente en M32/M36.

## 6. Ledger de gobernanza

`PilotAuthorizationDossier` registra:

- `PLAN_REGISTERED`;
- `APPROVAL_RECORDED`;
- `PILOT_RATIFIED`;
- `PLAN_REVOKED`.

Cada evento contiene secuencia, `previous_hash` y `event_hash` SHA-256. La aplicación verifica la cadena antes de nuevas actuaciones.

El ledger es append-only bajo el modelo de control de la aplicación y permite detectar manipulación. **No equivale por sí solo a WORM, blockchain o firma digital externa independiente.**

## 7. Minimización pública

`summary()` no expone:

- `actor_id`;
- `plan_hash`;
- `event_id`;
- `previous_hash`;
- `event_hash`;
- propósito libre del piloto.

El modelo público expone sólo alcance operativo mínimo, estado de ventana, dominios aprobados y ratificación.

## 8. Ventana temporal

La fecha del plan produce tres estados:

- `UPCOMING`: gobernanza puede estar completa, pero la ejecución todavía no está permitida;
- `ACTIVE`: la ventana temporal permite evaluar readiness de ejecución;
- `EXPIRED`: el plan conserva su historia, pero deja de poder ejecutarse.

Un request explícito de ejecución fuera de una ventana activa produce `BLOCKED_UNSAFE_PILOT_EXECUTION_CLAIM`.

## 9. Estados del gate

Entre los estados previstos:

- `BLOCKED_RC2_ASSURANCE`;
- `BLOCKED_PILOT_GOVERNANCE`;
- `READY_AWAITING_PILOT_WINDOW`;
- `BLOCKED_PILOT_WINDOW_EXPIRED`;
- `READY_FOR_SYNTHETIC_CONTROLLED_PILOT`;
- `BLOCKED_REAL_CLIENT_AUTHORIZATION`;
- `REAL_CLIENT_PILOT_READY`;
- `BLOCKED_UNSAFE_PILOT_EXECUTION_CLAIM`.

`REAL_CLIENT_PILOT_READY` es un estado modelado para una futura release expresamente autorizada. No describe el estado actual del proyecto.

## 10. Pagos y comunicaciones

Si un plan `REAL_CLIENT_CONTROLLED` declara `REAL_PROVIDER` para pagos, se exige simultáneamente:

- `release_metadata.REAL_PAYMENTS_AUTHORIZED=True`;
- `LEGAL_REAL_PAYMENTS_AUTHORIZED=true`;
- proveedor distinto de `sandbox`, `disabled`, `none` o vacío.

Si declara comunicaciones externas reales, se exige:

- `LEGAL_EXTERNAL_COMMUNICATIONS_AUTHORIZED=true`;
- proveedor distinto de `sandbox`, `disabled`, `none` o vacío.

El gate nunca activa esos proveedores; sólo comprueba condiciones.

## 11. Qué falta para un piloto real

Aunque esta implementación quede técnicamente certificada, un piloto real todavía exige evidencia fuera de CI, entre otras:

- las 10 evidencias RC2 reales, no fixtures;
- infraestructura PostgreSQL/TLS/monitoring efectiva;
- restore y rollback drills;
- load test y pentest;
- incident-response drill;
- validación Mac/Windows;
- aprobación de privacidad aplicable al tratamiento real;
- aprobación jurídica y QA del alcance del piloto;
- definición de responsables y ventana;
- controles de soporte, monitoreo y rollback durante el piloto;
- decisión explícita sobre si el piloto usa sólo datos sintéticos o datos personales reales;
- si hay clientes reales, revisión de términos, privacidad, autorizaciones y mecanismos de atención aplicables;
- modificación consciente y revisada de `release_metadata` únicamente cuando corresponda.

## 12. Criterio de certificación técnica

Antes de llamar “certificada” a esta fase deben pasar sobre un SHA exacto:

1. `compileall`;
2. suite completa del repositorio;
3. pruebas de alcance, RBAC, separación de funciones, idempotencia, revocación, manipulación y ventanas;
4. tests RC2;
5. inventario 11 productos / >=473 preguntas / >=273 reglas;
6. runtime M33 integrado;
7. smoke HTTP M34.2 → M37.3;
8. M33.1 public demo 8/8;
9. visual-docx del portafolio completo.

Un CI verde acredita la implementación y ausencia de regresiones del SHA exacto. No constituye por sí mismo autorización jurídica, de privacidad, seguridad externa, piloto con usuarios reales ni lanzamiento comercial.
