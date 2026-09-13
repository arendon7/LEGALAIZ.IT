# M34.1 — Intake UX + continuidad anónima cifrada

## Propósito

M34.1 convierte la ruta pública `/orientador` en la puerta de entrada principal para una persona que **no sabe qué producto o documento necesita**.

El usuario puede:

1. explicar su situación con sus propias palabras;
2. comenzar sin autenticarse;
3. guardar el relato de forma cifrada;
4. recibir un código de continuidad que el servidor no conserva en texto claro;
5. recuperar o corregir su relato;
6. usar, como alternativa, el orientador determinístico de tres decisiones que ya existía;
7. explorar directamente las 11 soluciones si ya sabe qué necesita.

M34.1 **no ejecuta todavía extracción de hechos ni clasificación con IA**. Esa separación es intencional: la interfaz no debe afirmar que «entendió» o inferir hechos hasta que M34.2 implemente salida estructurada, procedencia y confirmación.

## Decisión UX

Se conserva `/orientador` como ruta pública por compatibilidad con la navegación existente.

La jerarquía de la pantalla cambia a:

### Ruta principal

**Cuéntanos tu problema**

- textarea de 20–8.000 caracteres;
- lenguaje no jurídico;
- indicación de incluir, si es posible, quién interviene, qué ocurrió, cuándo y qué quiere lograr;
- sin cuenta previa;
- sin petición prematura de nombre, cédula o información de facturación.

### Ruta secundaria

**Prefiero responder preguntas**

Conserva el orientador anterior:

- audiencia;
- tema;
- objetivo;
- máximo tres productos orientativos.

No almacena hechos del caso.

### Ruta directa

**Ver las 11 soluciones**

Permite evitar triage a quien ya conoce su necesidad.

## Estado posterior a guardar

Después de guardar se muestra:

- confirmación de almacenamiento;
- el relato exacto escapado como texto;
- código de continuidad;
- advertencia de que el código permite recuperar el relato;
- opción de editar;
- opción de continuar con preguntas generales;
- explicación de que la siguiente capa convertirá el relato en hechos candidatos confirmables.

No se muestran:

- producto recomendado;
- porcentaje de confianza;
- conclusión jurídica;
- hechos «entendidos»;
- normas generadas por modelo;
- promesas de resultado.

## Persistencia

Backend: `legalai_platform/intelligent_intake_m34_1.py`.

Tabla separada: `intelligent_intake_sessions`.

Se usa una tabla separada de `anonymous_service_drafts` porque en este momento todavía **no existe un `product_code` válido**. Forzar un producto antes del diagnóstico debilitaría el modelo de dominio.

### Propiedades de seguridad

- token aleatorio de 24 caracteres útiles;
- código mostrado con separadores sólo para legibilidad;
- almacenamiento exclusivo de SHA-256 normalizado del token;
- payload cifrado con `INFRA.crypto`;
- AAD por `session_id`;
- SHA-256 del payload descifrado para control de integridad;
- expiración predeterminada de 72 horas;
- rate limit por IP para inicio, recuperación y edición;
- código de recuperación enviado por cuerpo POST, nunca por URL;
- observabilidad sin relato ni código;
- ningún hecho del relato se envía a analítica agregada.

## Payload M34.1

El payload cifrado reserva ya la estructura necesaria para M34.2:

```json
{
  "problem_statement": "...",
  "facts": [],
  "contradictions": [],
  "risk_signals": [],
  "candidate_products": [],
  "ai_processing_status": "NOT_STARTED"
}
```

M34.1 mantiene estos arrays vacíos. No simula procesamiento IA.

## API pública

Todas las rutas son `POST` y requieren origen permitido.

### `POST /api/m34/intake/start`

Entrada:

```json
{"problem_statement":"..."}
```

Salida incluye:

- `id`;
- `recovery_code` sólo en creación;
- `stage`;
- `expires_at`;
- relato normalizado.

### `POST /api/m34/intake/recover`

Entrada:

```json
{"recovery_code":"XXXXXX-..."}
```

No coloca secretos en query string o path.

### `POST /api/m34/intake/problem`

Permite corregir el relato utilizando el mismo código. Una edición futura invalidará hechos/candidatos IA derivados del relato anterior antes de reprocesar.

## Accesibilidad y móvil

- label real sobre el textarea;
- contador visible;
- mensajes mediante `role=status` / `aria-live`;
- focus visible;
- controles táctiles amplios;
- composición en una columna bajo 900 px;
- panel de confianza deja de ser sticky en móvil;
- textarea redimensionable;
- recuperación en formulario independiente, sin formularios HTML anidados;
- contenido recuperado se escapa antes de insertarse en HTML.

## Criterios de aceptación M34.1

### Funcionales

- [x] una persona anónima puede guardar una descripción válida;
- [x] puede recuperar el mismo relato con el código;
- [x] puede editarlo sin crear otra sesión;
- [x] puede elegir el orientador determinístico sin guardar relato;
- [x] puede llegar al catálogo de 11 productos;
- [x] el resto de rutas públicas mantiene compatibilidad.

### Seguridad

- [x] el relato no aparece en columnas de texto claro de la tabla M34;
- [x] el código no se almacena en texto claro;
- [x] código inválido/expirado falla cerrado;
- [x] payload alterado falla integridad;
- [x] rate limiting activo;
- [x] secretos no aparecen en URL;
- [x] relato/código no se escriben en observabilidad.

### No regresión

- [x] M34.0 sigue validando 11 productos / >=473 preguntas / >=273 reglas;
- [x] suite completa verde;
- [x] smoke HTTP verde;
- [x] smoke de producción demostrativa verde;
- [x] auditoría visual DOCX verde;
- [x] generación documental, RBAC, Studio y aprobaciones no se modifican.

## Evidencia de certificación técnica

La rama M34.1 fue certificada sobre el SHA exacto:

`31fa1e06b76b6824a0360cb37f2f4a42f6702dec`

Workflow: `Validación LegalAIZ.it` — run #683 (`32658236494`).

Resultado: **SUCCESS**.

- sintaxis: PASS;
- suite completa unittest/integration: PASS;
- interfaz y datos demo: PASS;
- smoke HTTP: PASS;
- smoke producción demostrativa M33.1: PASS;
- visual DOCX: PASS.

Esta certificación prueba integración técnica y no equivale a aprobación jurídica sustantiva ni autorización de producción jurídica real.

## Próxima subiteración: M34.2

M34.2 añadirá `FactExtractionService` con salida JSON estricta hacia el Legal Fact Model. Sólo entonces la pantalla posterior podrá evolucionar de «Tu descripción quedó guardada» a **«Esto es lo que entendimos»**, mostrando hechos candidatos editables y diferenciando expresamente:

- lo dicho por el usuario;
- lo extraído de documentos;
- lo inferido por IA;
- lo derivado por reglas;
- lo confirmado por usuario o especialista.
