# M38.7 — DOCX Interoperability Hardening

## Objetivo

Endurecer la compuerta documental existente de LegalAIZ.it frente a defectos estructurales del paquete OOXML que pueden pasar inadvertidos en validaciones superficiales y producir advertencias de reparación, apertura inconsistente o diferencias entre consumidores de archivos DOCX.

M38.7 no crea una compuerta paralela. Amplía `legalai_platform.document_quality.validate_docx`, que ya es consumida por la compuerta transversal de liberación documental y por las fábricas contractuales especializadas.

## Hallazgo que motivó la iteración

La auditoría previa confirmó que:

- los once productos canónicos pasan por `enforce_document_release_gate` en el portafolio documental;
- las fábricas contractuales M33 revalidan los bytes finales después del render profesional;
- los postprocesadores contractuales M33.2 usan `python-docx` y guardado normal del paquete, no reescritura ZIP manual;
- la composición jurídica M33 conserva las cláusulas resultantes de los finalizadores jurídicos y aplica auditorías de profundidad/presentación.

Por ello no era justificable añadir otro wrapper de profundidad ni otra compuerta DOCX. El hueco concreto estaba en invariantes OPC/OOXML aún no comprobadas por el validador existente.

## Controles añadidos

M38.7 bloquea la entrega cuando detecta:

1. entradas ZIP exactamente duplicadas;
2. partes con colisión de nombre al ignorar mayúsculas/minúsculas;
3. nombres de parte inseguros o ambiguos —rutas absolutas, separadores inversos y segmentos vacíos, `.` o `..`—;
4. un `[Content_Types].xml` cuyo elemento raíz o namespace no corresponda a OPC;
5. declaraciones `Default` duplicadas o incompletas;
6. declaraciones `Override` duplicadas, ambiguas, incompletas o dirigidas a partes inexistentes;
7. ausencia del `Override` de `/word/document.xml`;
8. un `ContentType` distinto del tipo principal esperado para un `.docx` ordinario;
9. relaciones internas que, una vez normalizadas, escapen de la raíz del paquete;
10. relaciones internas con separadores inversos.

También se corrigió la resolución de relaciones: se eliminó el uso de `lstrip('./')`, porque podía borrar de forma excesiva el prefijo `../` de una ruta y dificultar la detección de escapes de la raíz del paquete.

## Controles preservados

Se mantienen sin reducción:

- CRC del ZIP;
- partes OOXML mínimas obligatorias;
- parseo XML de partes y relaciones;
- detección de relaciones internas rotas;
- apertura mediante `python-docx`;
- contenido jurídico mínimo;
- detección de variables y valores centinela sin resolver;
- validación del identificador de producto;
- advertencia por párrafos extensos duplicados;
- SHA-256 del documento;
- preflight visual;
- aprobación dual Jurídico + QA pendiente hasta revisión humana.

## Pruebas de regresión

`tests/test_m38_7_docx_interoperability.py` cubre:

- un DOCX válido generado por `python-docx` sigue pasando;
- miembro ZIP duplicado;
- colisión de nombre por mayúsculas/minúsculas;
- nombre de parte inseguro;
- relación que escapa la raíz del paquete;
- `Override` de Content Types duplicado;
- Content Type inválido para el documento principal.

La suite completa del repositorio y el QA visual deben permanecer verdes antes de certificar M38.7.

## Frontera de aseguramiento

M38.7 mejora la interoperabilidad **estructural** OOXML, pero no equivale a certificación nativa de Microsoft Word para macOS o Windows. Una afirmación de compatibilidad nativa exige abrir y revisar documentos reales en las versiones objetivo de Microsoft Word y registrar esa evidencia por separado.

La generación automática y el preflight técnico tampoco constituyen aprobación jurídica sustantiva ni QA visual humano. El mismo SHA-256 que se pretenda liberar debe completar los controles de aprobación aplicables.
