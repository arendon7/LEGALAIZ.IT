# Iteración M32.6 — Operación real del portafolio en la Mesa Jurídica

## Objetivo

Convertir la Mesa Jurídica M32.5 en una bandeja operativa capaz de administrar los once productos jurídicos sin confundir gestión, trazabilidad técnica y aprobación profesional.

M32.6 añade:

- cobertura explícita del portafolio de once productos;
- responsables jurídico y QA separados;
- prioridad y SLA operativo configurable;
- fecha objetivo y alertas de vencimiento;
- notas de seguimiento append-only;
- historial consolidado de operación y aprobación;
- expediente descargable por documento;
- cadena SHA-256 independiente para la bitácora operativa.

## Portafolio controlado

La cobertura esperada comprende:

1. CO-EM-003;
2. CO-EM-004;
3. CO-AR-001;
4. CO-LA-001;
5. CO-LA-002;
6. CO-TR-001;
7. CO-TR-002;
8. CO-SA-001;
9. CO-CD-001;
10. CO-CD-003;
11. CO-CD-004.

La cobertura significa que existe al menos un documento concreto registrado en la Mesa Jurídica. No significa que el producto o sus documentos estén aprobados profesionalmente.

La sincronización incorpora tanto documentos nuevos como expedientes creados previamente en M32.5 que todavía no tengan bitácora operativa. Nunca reemplaza revisiones ni aprobaciones existentes.

## Arquitectura incremental

### Backend

- `legalai_platform/approval_desk_operations.py`: asignaciones, SLA, alertas, actividad, cadena operativa y expediente.
- `legalai_platform/routes/m32_6_approval_operations_routes.py`: API autenticada.
- `legalai_platform/http_handler_m32_6.py`: extensión aislada del handler M32.5.
- `run.py`: activa el handler acumulado sin modificar las rutas anteriores.

### Frontend

- `app/modules/approval_operations_m32_6.js`: cobertura, responsables, SLA, alertas, notas y descarga del expediente.
- `app/modules/approval_operations_m32_6.css`: estilos responsive alineados con la marca LegalAIZ.it.

La interfaz complementa `#/mesa-juridica`; no crea una aplicación paralela.

## Gobierno de asignaciones

Solo administración puede:

- asignar especialista jurídico;
- asignar responsable QA;
- modificar prioridad;
- definir o reemplazar el vencimiento operativo.

El especialista y QA deben ser personas diferentes. La asignación jurídica también actualiza el especialista del expediente fuente para conservar el mismo alcance RBAC en toda la aplicación.

## Prioridad y SLA

Valores iniciales de operación:

| Prioridad | SLA sugerido |
|---|---:|
| Crítica | 4 horas |
| Alta | 24 horas |
| Normal | 72 horas |
| Baja | 120 horas |

Estos valores son metas internas configurables. No sustituyen términos legales, judiciales, administrativos, regulatorios o contractuales.

Estados calculados:

- `not_scheduled`;
- `in_time`;
- `at_risk`;
- `overdue`;
- `closed`.

## Alertas

M32.6 genera alertas por:

- cadena operativa alterada;
- cadena de aprobación inválida;
- especialista sin asignar;
- QA sin asignar;
- conflicto de separación de funciones;
- vencimiento no programado;
- SLA próximo a vencer;
- SLA vencido;
- hallazgos bloqueantes abiertos;
- aprobación jurídica pendiente;
- QA pendiente;
- documento listo para liberar.

Reconocer una alerta no elimina su causa. La actuación queda registrada como un evento nuevo.

## Bitácora operativa

Cada evento contiene:

- secuencia;
- tipo de evento;
- fecha y hora de Colombia;
- actor autenticado;
- payload;
- hash anterior;
- hash del evento.

La cadena es append-only. Si falla su verificación:

- no se admiten nuevas actuaciones M32.6;
- el expediente descargable queda bloqueado;
- se presenta una alerta crítica.

La cadena operativa complementa, pero no reemplaza, la cadena de aprobación M32.4/M32.5.

## Expediente de aprobación por documento

El ZIP contiene:

- `expediente_aprobacion.json`;
- `cadena_aprobacion.json`;
- `actividad_operativa.json`;
- `revision_vigente.json`;
- `revision_vigente.docx`;
- `LEAME.txt`.

El expediente declara expresamente:

- si existe liberación;
- si la doble aprobación recae sobre el mismo SHA-256;
- si todavía se requiere revisión humana;
- que la trazabilidad técnica no presume aprobación profesional.

El nombre del paquete incorpora la revisión vigente y los últimos hashes de las cadenas de aprobación y operación. Una actuación posterior produce un expediente nuevo; una copia del mismo estado solo se reutiliza después de validar su estructura y el hash del DOCX interno.

## API

Prefijo: `/api/m32/approval-operations`

### Lectura

- `GET /api/m32/approval-operations`
- `GET /api/m32/approval-operations/professionals`
- `GET /api/m32/approval-operations/cases/{case_id}`
- `GET /api/m32/approval-operations/cases/{case_id}/dossier`
- `GET /api/m32/approval-operations/cases/{case_id}/dossier-download`

### Escritura

- `POST /api/m32/approval-operations/portfolio/sync`
- `POST /api/m32/approval-operations/cases/{case_id}/assignment`
- `POST /api/m32/approval-operations/cases/{case_id}/priority`
- `POST /api/m32/approval-operations/cases/{case_id}/deadline`
- `POST /api/m32/approval-operations/cases/{case_id}/notes`
- `POST /api/m32/approval-operations/cases/{case_id}/alerts/{code}/acknowledge`

Todas las escrituras reutilizan sesión, origen permitido y CSRF. Los roles se obtienen exclusivamente de la sesión.

## Evidencia reproducible

`scripts/run_m32_6_portfolio_operations.py` construye un portafolio sintético de once productos, asigna responsables distintos, configura SLA, genera casos vencidos y en riesgo, libera un único documento demostrativo y exporta su expediente.

La evidencia exige:

- cobertura 11/11;
- 11 asignaciones completas;
- 11 cadenas operativas válidas;
- al menos un SLA vencido;
- al menos un SLA en riesgo;
- un documento liberado;
- diez documentos pendientes de revisión profesional;
- coincidencia del hash de revisión y liberación en el expediente;
- `real_legal_approval: false`;
- `real_qa_approval: false`.

## Limitaciones deliberadas

M32.6 no incorpora todavía:

- aprobación profesional real de los once documentos;
- notificaciones por correo o mensajería;
- calendarios laborales y festivos para cómputo de términos;
- reasignación masiva;
- firma electrónica o digital;
- radicación ante autoridades;
- certificación probatoria externa de las cadenas;
- anotaciones gráficas sobre el PDF.

## Criterio de cierre

La iteración puede integrarse cuando:

1. aprueben las regresiones M32.4, M32.5 y M32.6;
2. la evidencia cubra los once productos;
3. todas las cadenas operativas sean válidas;
4. el expediente ZIP contenga la revisión vigente y sus manifiestos;
5. el arranque HTTP proteja la nueva API;
6. las compuertas acumuladas M32.2 a M32.5 sigan aprobando;
7. la fusión vuelva a aprobar en `main`;
8. GitHub Pages publique el commit definitivo.
