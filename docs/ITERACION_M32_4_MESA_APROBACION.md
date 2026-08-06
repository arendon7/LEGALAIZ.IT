# Iteración M32.4 — Mesa de aprobación documental por hash

## Objetivo

Incorporar una mesa de revisión y aprobación para documentos concretos generados por LegalAIZ.it, con trazabilidad por expediente, revisión inmutable, página, cláusula, bloque y SHA-256.

M32.4 no reemplaza la aprobación de las plantillas canónicas. Añade un segundo control obligatorio:

1. **Nivel de plantilla:** estructura y contenido canónico aprobados en la Fábrica Documental.
2. **Nivel de documento generado:** hechos, variables, anexos, formato y archivo concreto aprobados sobre un hash exacto.

Una plantilla aprobada nunca convierte automáticamente sus documentos derivados en documentos aprobados.

## Componente principal

`legalai_platform/document_approval_desk.py`

El componente implementa:

- expedientes documentales independientes;
- revisiones DOCX inmutables y numeradas;
- relación padre-hijo obligatoria entre revisiones;
- hallazgos por página, cláusula y bloque;
- severidades `blocking`, `major`, `minor` y `observation`;
- cierre inmutable de hallazgos;
- comparación textual entre revisiones DOCX;
- aprobación jurídica independiente;
- aprobación QA posterior e independiente;
- comprobación del archivo contra el SHA-256 esperado;
- invalidación funcional de aprobaciones anteriores cuando existe una nueva revisión;
- copia liberada con el mismo hash aprobado;
- registro de liberación inmutable;
- cadena de auditoría enlazada mediante hashes.

## Reglas de gobierno

### Revisión vigente

Solo la revisión vigente puede recibir nuevos hallazgos, aprobaciones o liberación. Una nueva revisión debe declarar expresamente como padre la revisión vigente. Esto bloquea bifurcaciones silenciosas y evita aprobar por error una versión histórica.

### Hallazgos

Los hallazgos no se sobrescriben. Su creación y resolución son registros diferentes. Un hallazgo `blocking` o `major` abierto impide aprobar. Cualquier hallazgo abierto, incluso `minor` u `observation`, impide la liberación final.

### Aprobación jurídica

Requiere un actor con rol jurídico autorizado. La decisión queda vinculada a:

- expediente;
- revisión;
- SHA-256;
- actor;
- rol;
- decisión;
- comentario;
- fecha y hora;
- hash del registro de aprobación.

La decisión no puede modificarse. Un cambio de criterio requiere una nueva revisión.

### Aprobación QA

Requiere aprobación jurídica previa del mismo hash. El actor QA debe ser diferente al aprobador jurídico. La aprobación QA también es inmutable y queda enlazada a la misma revisión y SHA-256.

### Liberación

La liberación falla de forma cerrada salvo que concurran simultáneamente:

1. la revisión es la vigente;
2. el archivo existe y abre como DOCX;
3. el hash físico coincide con el manifiesto de revisión;
4. el hash físico coincide con el hash solicitado;
5. existe aprobación jurídica positiva del mismo hash;
6. existe aprobación QA positiva del mismo hash;
7. las aprobaciones pertenecen a personas distintas;
8. no existe ningún hallazgo abierto;
9. el expediente no tiene una liberación previa;
10. la copia liberada conserva exactamente el SHA-256 aprobado.

## Inmutabilidad y auditoría

Cada expediente conserva un archivo `events.jsonl`. Cada evento contiene:

- secuencia;
- tipo;
- actor;
- carga útil;
- hash del evento anterior;
- hash propio.

La función `verify_audit_chain` recalcula toda la cadena y detecta alteraciones de contenido, orden o relación entre eventos.

La persistencia usa escrituras atómicas para manifiestos JSON. Los DOCX de revisión se copian a carpetas numeradas y no se reemplazan.

## Pruebas adversariales

`tests/test_document_approval_desk_m32_4.py` cubre:

1. liberación del mismo hash aprobado;
2. rechazo de un hash solicitado incorrecto;
3. detección de manipulación física del DOCX;
4. bloqueo por hallazgo mayor o bloqueante;
5. imposibilidad de aprobación QA antes de la jurídica;
6. separación de personas entre aprobación jurídica y QA;
7. inmutabilidad de decisiones;
8. obsolescencia de aprobaciones anteriores tras nueva revisión;
9. rechazo de ramas de revisión no autorizadas;
10. comparación entre revisiones;
11. control de roles;
12. detección de manipulación del registro de auditoría;
13. bloqueo de liberación por hallazgos menores abiertos.

## Evidencia sintética

`scripts/run_m32_4_approval_lifecycle.py` produce un expediente demostrativo con:

- dos revisiones DOCX;
- un hallazgo mayor localizado en la cláusula primera;
- un intento de aprobación correctamente bloqueado;
- cierre del hallazgo;
- revisión corregida;
- comparación con una línea agregada y una retirada;
- aprobación jurídica y QA de actores distintos;
- liberación del SHA-256 de la segunda revisión;
- ocho eventos auditables encadenados.

Las aprobaciones incluidas en la evidencia son sintéticas. Los campos `real_legal_approval` y `real_qa_approval` permanecen en `false`.

## Estructura de almacenamiento

```text
approval-desk/
  CASE-ID/
    case.json
    events.jsonl
    findings/
      FND-....json
    finding-resolutions/
      FND-....json
    revisions/
      REV-0001/
        document.docx
        revision.json
        approvals/
          legal.json
          qa.json
      REV-0002/
        ...
    releases/
      REL-.../
        release.json
        documento-aprobado.docx
```

## Limitaciones deliberadas

M32.4 introduce el motor de gobierno y su evidencia reproducible. No declara todavía:

- aprobación profesional de los once documentos M32.3;
- integración visual final de la mesa dentro de todas las pantallas de Studio Jurídico;
- firma electrónica o digital;
- representación judicial;
- radicación automática;
- certificación de valor probatorio;
- reemplazo de expedientes reales por datos sintéticos.

## Criterio de cierre

La iteración puede integrarse cuando:

1. las 13 regresiones M32.4 estén en verde;
2. el ciclo integral sintético sea reproducible;
3. el hash liberado coincida con ambas aprobaciones y con el archivo físico;
4. la cadena de auditoría sea válida;
5. la validación general de LegalAIZ.it apruebe;
6. el PR apruebe sobre el mismo SHA revisado;
7. la fusión se valide nuevamente en `main`;
8. GitHub Pages se publique sin regresiones.
