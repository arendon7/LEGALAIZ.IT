# Iteración M32.5 — Interfaz operativa de la Mesa Jurídica

## Objetivo

Convertir el motor de gobierno documental M32.4 en un flujo operativo dentro de la aplicación LegalAIZ.it, sin crear una aplicación paralela ni sustituir la aprobación de plantillas de la Fábrica Documental.

M32.5 permite que especialistas jurídicos y QA trabajen sobre un documento generado concreto, identificado simultáneamente por:

- expediente de la aplicación;
- documento;
- revisión inmutable;
- SHA-256;
- hallazgos localizados;
- decisiones jurídica y QA;
- registro de liberación.

## Arquitectura incremental

La integración conserva el `Handler` seguro y el shell existentes.

### Backend

- `legalai_platform/approval_desk_workspace.py`: adaptador entre documentos y expedientes de LegalAIZ.it y el motor M32.4.
- `legalai_platform/routes/m32_5_approval_desk_routes.py`: API autenticada de la Mesa Jurídica.
- `legalai_platform/http_handler_m32_5.py`: extensión aislada del manejador existente. Solo intercepta el prefijo M32.5 y delega todas las demás rutas al handler anterior.
- `run.py`: activa el handler extendido sin modificar los contratos históricos de importación.

### Frontend

- `app/modules/approval_desk_m32_5.js`: bandeja, detalle, visor, hallazgos, comparación, decisiones y liberación.
- `app/modules/approval_desk_m32_5.css`: diseño responsive alineado con la identidad LegalAIZ.it.
- `app/index.html`: carga los activos M32.5 dentro del mismo shell de la aplicación.

La ruta de trabajo es `#/mesa-juridica`. El enlace se inserta únicamente para perfiles profesionales.

## Separación de niveles de aprobación

M32.5 mantiene dos controles jurídicamente distintos:

1. **Plantilla canónica:** aprueba estructura, bloques, variables y contenido base.
2. **Documento generado:** aprueba hechos, datos, anexos, composición y archivo concreto.

Una plantilla aprobada no aprueba automáticamente ningún documento derivado.

## Matriz RBAC

| Acción | Cliente | Especialista | Administración / QA |
|---|---:|---:|---:|
| Consultar bandeja profesional | No | Sí, dentro de su alcance | Sí |
| Consultar detalle y revisiones | No | Sí, dentro de su alcance | Sí |
| Registrar hallazgos | No | Sí | Sí |
| Resolver hallazgos | No | Sí | Sí |
| Cargar nueva revisión | No | Sí | Sí |
| Aprobar jurídicamente | No | Sí | No |
| Aprobar QA | No | No | Sí |
| Liberar documento | No | No | Sí |
| Descargar documento liberado | Sí, si pertenece a su expediente | Sí, si pertenece a su alcance | Sí |

La aprobación jurídica y QA deben corresponder a personas diferentes. QA solo puede aprobar después de la decisión jurídica positiva del mismo SHA-256.

## Estados de bandeja

- `draft`: expediente sin revisión.
- `legal_pending`: pendiente de decisión jurídica.
- `qa_pending`: aprobación jurídica vigente y QA pendiente.
- `changes_required`: hallazgo mayor o bloqueante abierto.
- `rejected`: alguna decisión vigente es de rechazo.
- `findings_pending`: ambas aprobaciones existen, pero aún hay hallazgos menores u observaciones abiertas.
- `ready_to_release`: doble aprobación positiva y ningún hallazgo abierto.
- `released`: copia final liberada y verificada.

## Operaciones disponibles

### Preparación de bandeja

Administración puede registrar los DOCX vigentes que todavía no tengan expediente M32.5. Cada documento produce un identificador `DSK-{document_id}` y una primera revisión inmutable.

### Revisiones

Una revisión nueva puede provenir de:

- el archivo vigente asociado al documento de LegalAIZ.it;
- una carga DOCX validada por tipo, estructura, límites y análisis de seguridad.

Toda revisión nueva debe declarar como padre la revisión vigente. Las revisiones anteriores nunca se reemplazan.

### Visor

Cuando LibreOffice está disponible, M32.5 convierte la revisión DOCX a PDF y presenta el texto extraído por página. También permite abrir el PDF de revisión.

Cuando el motor no está instalado, se muestra una vista estructural. Esa vista declara expresamente que:

- no acredita paginación;
- no acredita saltos de página;
- no acredita composición visual final.

El PDF de revisión no cambia la compuerta: la aprobación y liberación continúan vinculadas al DOCX y su SHA-256.

### Hallazgos

Cada hallazgo puede registrar:

- severidad;
- página;
- cláusula o sección;
- bloque;
- descripción verificable;
- actor y fecha;
- revisión y SHA-256.

La resolución es un registro nuevo. El hallazgo original no se sobrescribe.

### Comparación

La interfaz permite comparar dos revisiones mediante extracción textual del DOCX. La comparación identifica líneas agregadas y retiradas, pero no sustituye la inspección visual página por página.

### Aprobaciones

La decisión jurídica y QA incluye:

- revisión;
- SHA-256 esperado;
- actor autenticado;
- rol obtenido de la sesión;
- decisión;
- comentario;
- fecha y hora;
- hash del registro.

El rol no se acepta desde el payload del usuario.

### Liberación

Administración solo puede liberar cuando:

1. la revisión es la vigente;
2. el archivo físico coincide con su manifiesto;
3. el SHA-256 solicitado coincide con el archivo;
4. existe aprobación jurídica positiva del mismo hash;
5. existe aprobación QA positiva del mismo hash;
6. los aprobadores son personas distintas;
7. no hay hallazgos abiertos;
8. la cadena de auditoría es consistente;
9. no existe una liberación previa;
10. la copia final conserva el SHA-256 aprobado.

La descarga final utiliza exclusivamente la carpeta de liberación. No expone rutas internas ni permite descargar como final una revisión todavía pendiente.

## API

Prefijo: `/api/m32/approval-desk`

### Lectura

- `GET /api/m32/approval-desk`
- `GET /api/m32/approval-desk/cases/{case_id}`
- `GET /api/m32/approval-desk/cases/{case_id}/compare?from=REV-0001&to=REV-0002`
- `GET /api/m32/approval-desk/cases/{case_id}/audit`
- `GET /api/m32/approval-desk/cases/{case_id}/revisions/{revision_id}/preview`
- `GET /api/m32/approval-desk/cases/{case_id}/revisions/{revision_id}/preview.pdf`
- `GET /api/m32/approval-desk/cases/{case_id}/released-download`

### Escritura

- `POST /api/m32/approval-desk/bootstrap`
- `POST /api/m32/approval-desk/cases/{case_id}/register-current`
- `POST /api/m32/approval-desk/cases/{case_id}/upload-revision`
- `POST /api/m32/approval-desk/cases/{case_id}/findings`
- `POST /api/m32/approval-desk/cases/{case_id}/findings/{finding_id}/resolve`
- `POST /api/m32/approval-desk/cases/{case_id}/approvals`
- `POST /api/m32/approval-desk/cases/{case_id}/release`

Todas las escrituras reutilizan origen permitido, sesión autenticada y token CSRF del manejador existente.

## Evidencia reproducible

`scripts/run_m32_5_approval_workspace.py` genera un caso sintético que contiene:

- dos revisiones DOCX;
- una comparación con cambios;
- una vista PDF de al menos dos páginas;
- un hallazgo mayor localizado en la página 2;
- un intento de aprobación bloqueado;
- una resolución;
- aprobación jurídica y QA por actores distintos;
- liberación del SHA-256 exacto;
- descarga final con el mismo hash;
- cadena de auditoría válida.

La evidencia mantiene:

- `real_legal_approval: false`;
- `real_qa_approval: false`.

## Pruebas

`tests/test_m32_5_approval_workspace.py` cubre:

1. preparación de bandeja exclusiva de administración;
2. exclusión del cliente de la mesa profesional;
3. entrega posterior del documento liberado al cliente autorizado;
4. aislamiento entre especialistas;
5. bloqueo por hallazgo mayor;
6. separación de funciones jurídica y QA;
7. liberación del hash exacto;
8. obsolescencia de decisiones al crear una revisión nueva;
9. comparación de versiones;
10. carga DOCX como revisión hija;
11. declaración explícita del fallback sin paginación;
12. bloqueo de recorrido de rutas;
13. conexión de activos, handler y controles visibles.

## Limitaciones deliberadas

M32.5 no declara todavía:

- aprobación profesional real de los once documentos del portafolio;
- firma electrónica o digital;
- radicación automática;
- valor probatorio certificado de los registros;
- edición colaborativa simultánea;
- anotaciones gráficas directamente sobre el lienzo del PDF;
- equivalencia perfecta entre LibreOffice y todas las versiones de Word para Windows o macOS.

## Criterio de cierre

La iteración puede integrarse cuando:

1. las regresiones M32.4 y M32.5 aprueben;
2. la evidencia genere al menos dos páginas renderizadas;
3. el hash liberado coincida con revisión, aprobaciones, manifiesto y archivo físico;
4. la sintaxis Python y JavaScript sea válida;
5. la validación general y los once productos no presenten regresiones;
6. el PR apruebe sobre un único SHA;
7. la fusión vuelva a aprobar en `main`;
8. GitHub Pages se publique correctamente.
