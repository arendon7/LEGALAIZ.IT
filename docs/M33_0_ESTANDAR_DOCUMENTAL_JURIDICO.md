# M33.0 — Estándar documental jurídico transversal

## Objetivo

M33.0 eleva la salida de la Fábrica Documental de LegalAIZ.it desde documentos técnicamente válidos pero de densidad y formato heterogéneos hacia documentos jurídicos profesionales, modulares, trazables y compatibles con Word/LibreOffice/macOS.

La iteración se construye encima de M32.9. No revierte ni sustituye RBAC, seguridad, consentimientos, comunicaciones, Mesa Jurídica, revisiones inmutables, comparación, aprobación dual, publicación por hash ni las capacidades acumuladas del portafolio de once productos.

## Estándar formal obligatorio

Las salidas finales sujetas a M33.0 deben cumplir simultáneamente:

- Times New Roman 12 pt como estilo corporal.
- Interlineado 1,15.
- Espacio posterior de 6 pt.
- Texto corporal justificado.
- Márgenes de 2,5 cm.
- Títulos principales centrados, en negrilla y mayúscula sostenida.
- Cláusulas con ordinal y título en negrilla; cuerpo sin negrilla generalizada.
- Control de viudas y encabezados sin quedar huérfanos.
- Tablas con filas no divisibles y encabezados repetidos cuando corresponda.
- Anexos iniciados en página nueva.
- Pie con Página X de Y.
- Firmas mediante tablas invisibles; se prohíben líneas manuales de guiones bajos.
- Se prohíben separadores decorativos entre cláusulas, secciones, anexos y firmas.

## Arquitectura de la migración

### Capa A — Renderizado DOCX

`docx_builder.py` aplica el formato común a las salidas que utilizan el constructor transversal. Studio conserva previews editables y la generación canónica aplica la modalidad estricta.

### Capa B — QA semántico y OOXML

`document_standard_v33.py` incorpora controles fail-closed para:

- variables o marcadores sin resolver;
- NULL, undefined, N/A y otros valores centinela;
- líneas manuales o separadores decorativos;
- firmas sin partes estructuradas;
- estilo base distinto de Times New Roman 12;
- márgenes distintos de 2,5 cm;
- ausencia de interlineado 1,15;
- ausencia de paginación;
- estructura DOCX incompleta.

Las cláusulas excesivamente breves producen advertencia, no bloqueo automático, porque la suficiencia jurídica depende también de su función.

### Capa C — Modelo de bloques enriquecido

`factory_backend.py` conserva los tipos históricos y añade soporte compatible para:

- `clause`: cláusula contractual diferenciada;
- `annex`: anexo con salto de página y estructura propia;
- `signature`: firmas con datos estructurados;
- `paragraphs`: múltiples párrafos dentro de un mismo bloque;
- `numbered`: enumeraciones jurídicas;
- tablas sin bordes cuando la naturaleza del documento lo requiera.

La condición, las fuentes, las variables, los hashes y el historial de revisiones continúan funcionando en el mismo bloque. Por tanto, aumentar la profundidad jurídica no obliga a abandonar la modularidad ni la trazabilidad.

### Capa D — Puerta canónica

`canonical_generation_backend.py` valida la estructura renderizada antes de escribir la salida y vuelve a auditar el OOXML después de generarlo. Una salida que no cumple M33.0 se elimina y no ingresa como documento canónico.

La puerta sigue exigiendo fuente verificada, cotejo, paquete canónico, plantilla publicada, decisión de publicación, ausencia de brechas críticas y ausencia de alertas normativas bloqueantes.

## Principio de composición jurídica

M33.0 no busca maximizar el número de cláusulas. Busca aumentar la densidad jurídica y la coherencia.

Una cláusula sustantiva madura debe desarrollar, cuando resulte pertinente:

1. finalidad jurídica o contractual;
2. regla principal;
3. obligaciones de las partes;
4. procedimiento o evidencia;
5. consecuencias del incumplimiento;
6. excepciones, supervivencia o referencias cruzadas.

Los detalles operativos repetitivos deben desplazarse a anexos, matrices, cronogramas o actas.

## Migración de contenido por oleadas

### Oleada 1 — Contratos de referencia

1. CO-EM-003 — prestación de servicios.
2. CO-LA-002 — contrato individual de trabajo.
3. CO-AR-001 — arrendamiento de vivienda urbana.
4. CO-EM-004 — confidencialidad, datos, PI e IA.

Los cuatro contratos fijan el patrón de cláusulas, anexos y firmas.

### Oleada 2 — Documentos de cálculo, reclamación y cartera

5. CO-LA-001 — liquidación laboral y reclamación.
6. CO-CD-004 — cartera, acuerdo de pago y pagaré.
7. CO-CD-001 — hábeas data financiero.
8. CO-CD-003 — consumidor, garantía, retracto y reversión.

### Oleada 3 — Salud y tránsito

9. CO-SA-001 — petición/reclamo en salud.
10. CO-TR-001 — verificación SAST.
11. CO-TR-002 — fotodetección no notificada.

## Invariantes que no se modifican

La migración no puede reducir ni eliminar:

- once productos;
- entrevistas y reglas vigentes;
- fuentes y trazabilidad;
- RBAC y principio de mínimo privilegio;
- revisiones inmutables;
- comparación entre revisiones;
- aprobación jurídica y QA por personas distintas;
- publicación/liberación sobre el hash exacto;
- registros de auditoría;
- documentos anexos o módulos condicionales;
- compuertas de riesgo y escalamiento profesional.

## Aceptación de una plantilla M33

Una plantilla solo puede considerarse migrada cuando:

1. el esquema de variables está completo;
2. no quedan marcadores centinela en una salida final;
3. las condiciones activan y desactivan los módulos correctos;
4. el documento supera auditoría OOXML;
5. abre con `python-docx`;
6. abre y convierte con LibreOffice en CI;
7. todas sus páginas se rasterizan sin páginas vacías;
8. se revisa visualmente el resultado;
9. se valida jurídicamente el contenido;
10. QA valida variables, referencias, fechas, valores, anexos y firmas;
11. ambas aprobaciones recaen sobre la misma revisión/hash;
12. solo entonces puede entrar a liberación controlada.

## Estado de M33.0

La infraestructura transversal se incorpora primero y permanece compatible con las plantillas M32.9. La migración de contenido se realiza por revisiones nuevas; no se sobrescriben las revisiones aprobadas históricas. Hasta completar la revisión humana, los documentos permanecen como borradores controlados y no son candidatos de liberación.
