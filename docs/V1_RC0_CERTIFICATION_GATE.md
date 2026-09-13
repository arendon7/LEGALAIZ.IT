# LegalAIZ.it — V1-RC0 Integrated Certification Gate

Estado: **candidato, no certificado** hasta que un SHA exacto complete todos los gates de este documento y del workflow canónico.

## 1. Objetivo

V1-RC0 es la primera línea integrada que debe demostrar simultáneamente dos capacidades que hasta ahora evolucionaron en ramas divergentes:

1. profundidad jurídica, documental, editorial y de fuentes de M33.0–M33.4;
2. journey inteligente y trazable M34–M37.3, desde orientación pública hasta seguimiento, cierre profesional o escalamiento.

Un resultado verde aislado de una de las dos líneas no basta. RC0 sólo puede certificarse si ambas sobreviven juntas en el mismo runtime y en el mismo SHA.

## 2. Invariantes de portafolio

El candidato debe preservar, como mínimo:

- 11 productos jurídicos canónicos;
- 473 preguntas fuente o más, sin reducir overlays runtime aprobados;
- 273 reglas o más;
- Studio Jurídico y Fábrica Documental;
- revisiones inmutables, comparación de versiones, vista previa y DOCX;
- aprobación dual especialista jurídico + QA;
- RBAC, auditoría, mínimo privilegio y aislamiento entre titulares;
- generación documental sin variables rotas, `NULL`, `N/A`, `undefined` o sentinelas visibles;
- compatibilidad de apertura y renderizado DOCX;
- profundidad jurídica M33 y trazabilidad de fuentes M33.4.

Ningún gate de release puede sustituir estas capacidades por una versión simplificada.

## 3. Gate jurídico-documental M33

RC0 debe conservar y ejecutar las pruebas M33 incorporadas a la línea integrada, incluyendo:

- arquitectura documental y wrappers de calidad;
- portfolio contractual y procedimental completo;
- auditoría editorial M33.2;
- overlays runtime M33.3;
- registry, manifiestos, trazabilidad y freshness M33.4;
- renderizado visual del portafolio M33 completo;
- generación de 53 muestras M33.0 según los scripts canónicos de CI;
- prohibición de presentar contenido desactualizado o sin procedencia como verificado.

La existencia de archivos M33 no basta: las pruebas deben ejecutarse sobre el runtime combinado RC0.

## 4. Gate de journey M34–M37

El mismo SHA debe preservar el recorrido completo:

- M34: intake público, extracción conservadora, confirmación de hechos, preguntas adaptativas y recomendación explicable;
- M35: handoff a cuenta, bridge de fulfillment, comercio sandbox trazable y activación de expediente;
- M36: intake profesional, asignación manual, reconciliación de aprobación dual y entrega controlada;
- M37: seguimiento post-entrega, soportes, fechas/recordatorios operativos y compuerta profesional de cierre/escalamiento.

Deben mantenerse las fronteras de autoridad:

- inferencias AI no confirmadas no se convierten silenciosamente en hechos decisorios;
- pago sandbox no se presenta como pago real;
- ninguna aprobación legal o QA se crea automáticamente;
- `DELIVERED_IN_APP` no equivale a descarga, lectura o recepción externa;
- fechas operativas no se presentan como términos legales;
- soporte recibido/revisado no equivale a autenticidad o suficiencia probatoria;
- `CERRADO` no equivale a éxito jurídico;
- cierre y escalamiento no son automáticos.

## 5. Seguridad y privacidad

RC0 debe fallar cerrado ante:

- acceso cross-tenant;
- manipulación de cadenas hash, snapshots, archivos o eventos;
- drift entre decisión, draft, orden, pago, expediente, documentos o journey;
- intento de bypass por endpoints legacy una vez activadas las compuertas M35/M36/M37;
- discrepancias de actor, rol o asignación;
- exposición pública de relato, respuestas, hashes de integridad, IDs internos, razones profesionales privadas, firmas o payloads de pago.

Los endpoints mutantes deben conservar autenticación, same-origin, CSRF y rate limiting según su contrato.

## 6. Pruebas obligatorias del candidato

Para un SHA RC0 exacto se requiere como mínimo:

1. `python -m compileall -q .` PASS;
2. suite completa `unittest` PASS;
3. `tools/v1_rc0_inventory_gate.py` PASS;
4. validación JS/assets PASS;
5. fuente demo: 11 productos, >=473 preguntas y respuestas demo consistentes;
6. `tools/v1_rc0_m33_runtime_smoke.py` PASS sobre el runtime integrado;
7. HTTP M34.2 → M37.3 PASS;
8. public demo M33.1 8/8 PASS;
9. portfolio visual M33 completo PASS;
10. auditoría editorial M33.2 PASS;
11. conversión DOCX→PDF y rasterización de todas las páginas PASS;
12. artifact visual generado y asociado al mismo SHA.

## 7. Evidencia de certificación

La evidencia final debe registrar explícitamente:

- SHA exacto certificado;
- workflow/run exactos;
- número total de pruebas;
- conteo de productos, preguntas y reglas;
- resultado del runtime M33 combinado;
- resultado del journey HTTP M34–M37.3;
- resultado M33.1;
- resultado del portfolio visual;
- artifact id, tamaño y digest;
- base y HEAD del PR después de restaurar su topología lógica;
- cualquier defecto encontrado durante RC0 y la corrección que obligó a generar un nuevo SHA.

Si el HEAD cambia después del verde, la certificación anterior deja de cubrir el candidato nuevo.

## 8. Lo que RC0 no autoriza

Incluso con todos los gates verdes, RC0 representa **certificación técnica integrada**, no:

- aprobación jurídica humana final de todo el portafolio;
- QA humano visual/semántico definitivo de cada documento;
- autorización de pagos reales;
- aprobación de precios comerciales definitivos;
- habilitación de producción jurídica real;
- representación judicial;
- declaración de vigencia normativa perpetua;
- declaración de resultado jurídico garantizado.

Esos asuntos pertenecen a la fase posterior de Release Readiness / Commercial V1 Approval.

## 9. Criterio de salida

RC0 puede pasar a Release Readiness sólo cuando el mismo SHA demuestra conjuntamente M33 + M34–M37, sin regresiones de portafolio, seguridad, trazabilidad, profundidad jurídica o calidad documental. Hasta entonces el PR debe permanecer `draft` y no debe fusionarse a `main`.