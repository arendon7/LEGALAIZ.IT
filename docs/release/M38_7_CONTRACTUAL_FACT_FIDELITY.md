# M38.7 — Contractual Fact Fidelity

## Objetivo

Cerrar una brecha concreta entre la entrevista inteligente de CO-EM-003 y el instrumento contractual visible: la biblioteca jurídica M33 ya es profunda, pero varios hechos materiales confirmados por el usuario podían quedar representados únicamente mediante redacción genérica.

M38.7 no aumenta texto por una meta de páginas. Conforme al estándar contractual canónico, cada incorporación debe cumplir una función jurídica, estar vinculada a un hecho confirmado y permanecer dentro de una cláusula materialmente pertinente.

## Hallazgo de partida

Sobre el caso sintético rico utilizado por el portafolio documental, el contrato final ya incorporaba correctamente, entre otros, objeto, resultado esperado, alcance incluido/excluido, honorarios, plazo, terminación, aceptación general, exclusividad y controles sustantivos. Sin embargo, podían no quedar expresados de forma específica hechos ya disponibles en la entrevista sobre:

- criterio particular de aceptación;
- modalidad, lugar, equipo, subcontratación, hitos y dependencias de ejecución;
- factura, gastos y retenciones;
- dirección del contratista, manejo de su personal y seguridad social;
- categorías y término de confidencialidad;
- roles y controles de seguridad para datos personales;
- activos preexistentes, resultados y componentes de terceros en propiedad intelectual;
- reglas particulares de uso de IA;
- asignación de riesgos, responsabilidad y seguros;
- transición, devolución o eliminación al cierre; y
- mecanismo de controversias seleccionado por la entrevista.

## Implementación

### 1. Overlay de fidelidad factual

`m38_7_services_fact_fidelity.py` se ejecuta después de `m33_services_release_polish` y:

- trabaja sobre una copia de la composición;
- no modifica el diccionario de respuestas;
- no crea nuevas cláusulas sustantivas cuando ya existe una cláusula materialmente adecuada;
- añade hechos confirmados mediante párrafos/parágrafos dentro de la cláusula pertinente;
- no inserta valores vacíos, `NULL`, `N/A`, `undefined`, `NaN` ni otros sentinelas definidos;
- no reactiva módulos condicionales eliminados por una decisión jurídica previa, por ejemplo IA cuando `ai.used` es falso;
- traduce valores internos de selección, como `negotiation_conciliation_courts`, a lenguaje contractual visible;
- no modifica aprobación jurídica, QA, liberación ni trazabilidad de fuentes.

### 2. Endurecimiento OOXML

`legalai_platform/document_quality.py` amplía la validación técnica existente para rechazar además:

- nombres de entradas ZIP duplicados dentro del DOCX;
- IDs `Relationship/@Id` duplicados dentro de una parte `.rels`;
- extensiones `Default` duplicadas en `[Content_Types].xml`; y
- `PartName` `Override` duplicados en `[Content_Types].xml`.

Estos controles complementan CRC, partes obligatorias, parseo XML, relaciones internas, apertura con `python-docx`, sentinelas y controles visuales ya existentes.

## Compatibilidad Word / Mac

M38.7 reduce causas estructurales concretas que pueden provocar avisos de reparación en procesadores OOXML. Esto **no constituye certificación de Microsoft Word para macOS**: la CI disponible valida OOXML, `python-docx` y renderizado mediante LibreOffice en Linux. Una validación nativa de Word para Mac requiere ejecución real en ese entorno y debe registrarse como evidencia separada.

## Criterios de aceptación

1. El fixture rico CO-EM-003 conserva en el instrumento final los hechos materiales definidos arriba.
2. Los enums internos no aparecen literalmente en el contrato cuando existe una traducción contractual definida.
3. Los hechos opcionales vacíos o sentinelas no generan texto residual.
4. Un módulo de IA inactivo no reaparece por la capa de fidelidad.
5. Las respuestas de entrada no se mutan.
6. La numeración de cláusulas y el control de fuentes se conservan.
7. Los DOCX válidos existentes siguen superando el gate.
8. Paquetes con entrada ZIP duplicada, relación duplicada o declaración Content Types duplicada quedan bloqueados.
9. La suite completa, inventario, HTTP/public demo y QA visual deben permanecer en PASS antes de certificar la iteración.
10. La aprobación dual jurídica + QA permanece pendiente por documento; M38.7 no autoriza liberación automática.

## Alcance deliberadamente excluido

- No reescribe la biblioteca histórica `contractual_maturity.py`.
- No modifica los otros tres contratos P0 en esta primera subiteración.
- No crea nuevas fuentes normativas ni altera el registro jurídico M33.4.
- No representa una revisión jurídica humana del caso concreto.
- No certifica Word para Mac sin evidencia nativa.
