# V1 Release Readiness Gate

## Propósito

Esta fase comienza después del cierre técnico de M37.3 y **no añade una nueva función jurídica al lifecycle**. Su objetivo es convertir el stack acumulado M34–M37 en un candidato de release auditable y, al mismo tiempo, impedir que una CI verde se interprete como autorización automática de producción jurídica real.

La línea canónica de `main` continúa siendo M33.1 hasta que exista una decisión explícita de integración y promoción. Este gate vive apilado sobre M37.3.

## Tres veredictos separados

### 1. Code Release Candidate

Puede quedar en verde por evidencia reproducible del repositorio. Requiere, como mínimo:

- runtime incremental activo en M37.3;
- presencia del linaje M34.1 → M37.3;
- 11 productos jurídicos;
- mínimo 473 preguntas;
- mínimo 273 reglas;
- perfil de producción con PostgreSQL, cookies seguras, control de origen, MFA privilegiado, cifrado de objetos, antimalware y cuentas demo deshabilitadas;
- modelo de aprobación dual `legal + QA` de la misma revisión;
- preservación de la frontera de datos sintéticos mientras `main` siga siendo M33.1.

Un resultado `RC_CODE_READY` significa únicamente que el código acumulado satisface el contrato técnico de candidato. **No significa producción jurídica real.**

### 2. Producción jurídica real

No puede ser autorizada sólo por CI. Además del candidato de código exige:

- `REAL_PRODUCTION_AUTHORIZED=true` mediante cambio de release gobernado;
- PostgreSQL externo certificado;
- migración certificada;
- backup/restore certificado;
- almacenamiento persistente de objetos certificado;
- gestión y rotación de secretos verificada;
- MFA privilegiado probado en el entorno real;
- antimalware operativo y fail-closed;
- monitoreo, alertamiento e incident response;
- revisión de privacidad/protección de datos para go-live;
- aprobación del modelo operativo humano de revisión jurídica + QA;
- ejercicio de disaster recovery/restore.

Cada requisito externo debe aparecer en `config/v1/production_attestations.json` como `VERIFIED_EXTERNAL_EVIDENCE` y contener un `evidence_ref` trazable. Si falta el registro o la referencia, el gate falla cerrado.

### 3. V1 comercial

Añade a producción jurídica real:

- `REAL_PAYMENTS_AUTHORIZED=true`;
- proveedor de pagos real certificado, incluyendo webhooks, conciliación, idempotencia, reembolsos y recuperación ante fallos.

Mientras esos elementos no estén acreditados, el estado correcto es `COMMERCIAL_V1_BLOCKED` aunque todas las pruebas de código pasen.

## Estado esperado al crear esta fase

El estado inicial correcto es:

- `RC_CODE_READY` si el stack M34–M37 conserva todos los invariantes;
- `REAL_PRODUCTION_BLOCKED`;
- `COMMERCIAL_V1_BLOCKED`.

Es intencional que los dos últimos permanezcan bloqueados. El gate existe precisamente para impedir una promoción prematura.

## Evidencia y trazabilidad

Archivos de control:

- `config/v1/release_readiness_contract.json`: contrato del gate;
- `config/v1/production_attestations.json`: registro de evidencias externas, sin secretos;
- `legalai_platform/release_readiness_v1.py`: evaluador fail-closed;
- `tests/test_v1_release_readiness.py`: regresiones de portfolio, linaje, metadata y gobernanza;
- `tools/v1_release_readiness_audit.py`: reporte reproducible.

El registro de attestations no debe contener contraseñas, llaves, tokens, connection strings ni datos personales. `evidence_ref` debe apuntar a una evidencia controlada fuera del repositorio o a un identificador de auditoría autorizado.

## Promoción futura

Sólo después de que el stack completo esté integrado y las evidencias externas necesarias estén verificadas debe evaluarse un cambio explícito de `VERSION`, `README.md`, `FINAL_RELEASE_NOTES.md`, `release_metadata.py` y runbooks. Esa promoción debe ser un evento separado, revisable y reversible; este gate no la ejecuta automáticamente.

## Límite jurídico

La certificación técnica de una release candidate no sustituye la revisión jurídica humana de los productos, documentos o asuntos reales, ni la aprobación QA profesional, ni acredita resultados jurídicos, radicaciones, notificaciones, términos legales o efectos externos.
