# M38.8 — Contractual Fidelity + DOCX Interoperability

## Precedencia

M38.8 se apila sobre el M38.7 certificado `3c9a56a6f66001042525a65e0377cc215aee176d`, que introdujo la compuerta de cobertura contractual profunda para los cuatro contratos P0 y cerró con 1.292/1.292 pruebas en PASS.

Durante la preparación de esta iteración se identificó además una rama experimental no certificada de interoperabilidad OOXML. M38.8 reutiliza sus controles técnicamente superiores, los integra sobre la línea certificada M38.7 y añade una validación de IDs de relaciones duplicados. La rama experimental no se considera evidencia de certificación por sí misma.

## Objetivo

Cerrar dos brechas distintas sin reescribir la biblioteca contractual histórica:

1. **Fidelidad factual CO-EM-003:** hechos materiales ya confirmados por la entrevista deben aparecer en la cláusula pertinente y no quedar sustituidos por texto genérico.
2. **Interoperabilidad DOCX:** el gate existente debe rechazar ambigüedades estructurales OPC/OOXML asociadas a reparación o comportamiento divergente entre procesadores de Word.

## 1. Fidelidad factual contractual

`m38_8_services_fact_fidelity.py` se aplica después del pulido jurídico M33 y mantiene intacta la selección jurídica previa. Incorpora, cuando existen, hechos confirmados sobre:

- criterio particular de aceptación;
- duración, hitos y dependencias;
- modalidad, lugar, equipo y subcontratación;
- facturación, gastos y retenciones;
- autonomía, personal y seguridad social;
- categorías y término de confidencialidad;
- roles y controles de datos personales;
- PI preexistente, resultados y terceros;
- reglas de IA cuando el módulo está activo;
- asignación de riesgos, responsabilidad y seguros;
- transición, devolución/eliminación y cierre; y
- mecanismo de controversias en lenguaje contractual visible.

### Invariantes

- no muta las respuestas;
- no inserta vacíos o sentinelas;
- no crea una conclusión jurídica nueva a partir de un dato técnico;
- no reactiva módulos condicionales previamente eliminados;
- preserva numeración, fuentes, trazabilidad y aprobación dual;
- no convierte longitud en criterio de calidad: el hecho debe cumplir una función jurídica concreta.

## 2. Interoperabilidad OPC/OOXML

`legalai_platform.document_quality.validate_docx` conserva los controles previos y añade bloqueo por:

1. entradas ZIP exactamente duplicadas;
2. colisiones de nombres de partes al ignorar mayúsculas/minúsculas;
3. nombres de parte inseguros o ambiguos;
4. raíz o namespace inválidos en `[Content_Types].xml`;
5. `Default` duplicados o incompletos;
6. `Override` duplicados, ambiguos, incompletos o que apunten a partes inexistentes;
7. ausencia del `Override` de `/word/document.xml`;
8. `ContentType` principal incompatible con un DOCX ordinario;
9. relaciones internas que escapen de la raíz del paquete;
10. relaciones internas con separadores inversos; y
11. IDs `Relationship/@Id` duplicados dentro de una misma parte `.rels`.

También corrige la resolución de targets para no borrar accidentalmente un prefijo `../` mediante `lstrip('./')`.

## Compatibilidad Word / Mac

Estos controles reducen causas estructurales concretas de avisos de reparación y diferencias de interpretación OPC/OOXML. **No constituyen certificación nativa de Microsoft Word para macOS ni Windows.** Esa afirmación requiere abrir y revisar documentos reales en las versiones objetivo de Microsoft Word y registrar la evidencia resultante.

La CI actual valida integridad OOXML, apertura `python-docx`, generación/renderizado Linux/LibreOffice y QA visual automatizado/humano disponible en el pipeline.

## Pruebas nuevas

### Fidelidad factual — 5

- los hechos materiales del fixture rico aparecen en el contrato final;
- el overlay no muta entradas y conserva numeración/fuentes;
- vacíos y sentinelas no se filtran;
- IA inactiva no se reactiva; y
- la personalización es aditiva y conserva controles jurídicos existentes.

### Interoperabilidad — 8

- DOCX válido sigue pasando;
- miembro ZIP duplicado;
- colisión por mayúsculas/minúsculas;
- nombre de parte inseguro;
- relación que escapa la raíz;
- ID de relación duplicado;
- `Override` duplicado; y
- ContentType principal inválido.

## Criterios de certificación

M38.8 sólo podrá declararse certificado cuando, sobre el SHA exacto de la rama:

- las 1.292 pruebas de M38.7 permanezcan verdes;
- las 13 pruebas M38.8 pasen;
- el inventario siga en 11 productos / 473 preguntas / 273 reglas;
- la base demo siga en 451 respuestas;
- syntax/startup/HTTP/public demo permanezcan en PASS;
- el portafolio documental y `visual-docx` permanezcan en PASS;
- no aparezcan regresiones editoriales, páginas en blanco o colas de firma defectuosas; y
- Jurídico + QA continúen siendo las únicas vías de aprobación/liberación humana del documento.

## Fuera de alcance

- no reescribe `contractual_maturity.py`;
- no cambia la lógica sustantiva de los otros tres contratos P0 en esta iteración;
- no altera RBAC, pagos, producción, fuentes normativas ni autorizaciones de release;
- no sustituye revisión jurídica humana del caso concreto; y
- no certifica Word para Mac/Windows sin evidencia nativa.
