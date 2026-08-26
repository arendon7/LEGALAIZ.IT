# M38.7 — Contract Composition Coverage

## Objetivo

M38.7 evita que los cuatro contratos P0 regresen silenciosamente a instrumentos básicos aunque el archivo DOCX siga siendo técnicamente válido.

Productos cubiertos:

- `CO-EM-003` — prestación de servicios;
- `CO-EM-004` — confidencialidad / secretos / PI / datos;
- `CO-AR-001` — arrendamiento de vivienda urbana;
- `CO-LA-002` — contrato individual de trabajo.

## Hallazgo de auditoría previo

La investigación sobre el SHA M38.6 certificado demostró que la profundidad jurídica ya existe y está conectada al runtime M33:

1. `m33_legal_composition.compose_services_m33()` consume directamente `services_contract_sections()` y `service_scope_sections()`.
2. `m33_contractual_adapters` consume directamente `nda_sections()`, `lease_contract_sections()` y `employment_contract_sections()`.
3. Las capas M33 posteriores trabajan sobre copias de esas composiciones y refinan hechos, redacción, fuentes, comparecencia y presentación; no sustituyen el instrumento por una plantilla corta.
4. El portafolio M32.3 ya ejecuta el gate de integridad/visual sobre cada DOCX final.

El riesgo restante era de regresión futura: no existía una aserción transversal que exigiera conservar familias contractuales esenciales en la composición y en el DOCX efectivamente renderizado.

## Qué añade M38.7

`legalai_platform/contract_composition_coverage.py` define una política conservadora por producto.

Cada contrato debe conservar simultáneamente:

- un mínimo de cláusulas públicas;
- un volumen mínimo de texto contractual renderizado;
- sección de firmas;
- familias esenciales de contenido propias del instrumento.

La familia debe aparecer tanto en la composición que recibe el renderer como en el texto extraído del DOCX final. De este modo se detectan dos clases de regresión:

1. la biblioteca/compositor pierde una materia contractual esencial;
2. la composición la conserva, pero el renderer deja de materializarla.

## Familias estructurales

### CO-EM-003

Objeto, alcance/exclusiones, entregables/aceptación, autonomía/riesgo de laboralidad, economía/pago, riesgo/responsabilidad, terminación/cierre y controversias/ley aplicable.

### CO-EM-004

Confidencialidad, secreto empresarial, finalidad/uso, exclusiones, acceso/seguridad/incidentes, duración, devolución/eliminación y remedios/controversias.

### CO-AR-001

Inmueble/objeto, duración, canon/pago, entrega/inventario, obligaciones de las partes, reparaciones/mantenimiento, servicios/cargas y terminación/restitución.

### CO-LA-002

Cargo/funciones, término, salario, jornada, lugar/modalidad, deberes, seguridad social/riesgos laborales y terminación.

Los módulos condicionales no se convierten artificialmente en requisitos universales. La ausencia legítima de un módulo que depende de hechos no debe forzar información o cláusulas que el expediente no activa.

## Punto de enforcement

La cobertura se ejecuta dentro de `build_m33_presentation()` exclusivamente sobre `approval_candidate`, después de:

1. renderizar el DOCX;
2. aplicar formato contractual M33.2;
3. finalizar paginación cuando corresponda;
4. estampar identidad interna;
5. superar el preflight técnico M33.

No se integra al `document_release_gate` global porque las fábricas M33 pueden producir un DOCX legacy intermedio antes de reemplazarlo por el instrumento profesional final. Bloquear el intermedio impediría llegar a la composición madura.

Si la cobertura falla, el approval candidate se elimina y la generación falla cerrado.

## Lo que M38.7 NO afirma

El resultado `passed=true` significa únicamente que el instrumento conserva la profundidad estructural mínima certificada para evitar una regresión a documentos básicos.

No acredita por sí mismo:

- suficiencia jurídica para un caso concreto;
- vigencia normativa;
- ausencia de riesgos o contingencias;
- validez, eficacia o ejecutabilidad de todas las cláusulas;
- cumplimiento de formalidades particulares;
- corrección de hechos ingresados por el usuario;
- aprobación profesional.

La liberación continúa requiriendo la revisión jurídica y QA existentes sobre la misma revisión y hash.

## Compatibilidad DOCX / Mac

M38.7 no se presenta como certificación de Microsoft Word para macOS.

El repositorio ya dispone de validación OOXML, CRC, partes obligatorias, relaciones internas, parseo XML, apertura con `python-docx`, estructura visual y render a PDF. El ensayo real Mac/Windows permanece como evidencia externa separada del release assurance.

La auditoría detectó posibles endurecimientos OOXML incrementales —por ejemplo entradas ZIP duplicadas y consistencia avanzada de `[Content_Types].xml`— que pueden evaluarse después, pero no justifican sustituir el gate actual ni afirmar compatibilidad física no probada.

## Criterios de aceptación

1. Las políticas aplican exactamente a los cuatro contratos P0.
2. Los cuatro compositores maduros actuales superan el auditor.
3. Una composición truncada falla por volumen/familias.
4. Una familia presente en composición pero ausente del DOCX falla.
5. Las firmas deben existir en composición y render.
6. Los siete productos no contractuales no son bloqueados.
7. El enforcement ocurre sólo en el approval candidate final M33.
8. El release gate global no se modifica con esta comprobación.
9. La evidencia M33 incorpora el reporte de cobertura.
10. Un fallo elimina el candidato y falla cerrado.
11. La suite completa, inventario, demo, journeys y QA visual continúan verdes.
12. No se declara suficiencia jurídica automática ni compatibilidad Mac sin ensayo real.
