# Iteración M32.3 — Portafolio completo y expediente de revisión

## Objetivo

Generar, validar y renderizar un documento primario de cada uno de los once productos canónicos de LegalAIZ.it mediante sus fábricas activas, sin sustituir las rutas especializadas, sin reducir el contenido acumulado y sin confundir el preflight automatizado con aprobación jurídica o QA.

## Arquitectura

M32.3 utiliza dos rutas compatibles:

1. **Fábricas especializadas:** `CO-AR-001`, `CO-EM-003`, `CO-EM-004`, `CO-LA-001` y `CO-LA-002`.
2. **Fábricas transversales:** `CO-TR-001`, `CO-TR-002`, `CO-SA-001`, `CO-CD-001`, `CO-CD-003` y `CO-CD-004`.

Las once salidas pasan por la compuerta común de integridad OOXML, apertura con `python-docx`, control de marcadores, preflight visual estructural, hash SHA-256 y manifiesto lateral. Después se convierten a PDF, se rasterizan todas sus páginas y se incorporan a un expediente de revisión con una hoja de contacto por producto.

## Cobertura final de rama

| Producto | Documento primario | Páginas |
|---|---|---:|
| `CO-TR-001` | Informe de coincidencia y diagnóstico SAST | 2 |
| `CO-TR-002` | Solicitud integral de expediente y preservación de evidencia | 2 |
| `CO-SA-001` | Derecho de petición integral ante EPS o IPS | 3 |
| `CO-CD-001` | Reclamo integral de hábeas data financiero | 3 |
| `CO-CD-003` | Diagnóstico jurídico del mecanismo de consumo | 2 |
| `CO-CD-004` | Diagnóstico de obligación, título y ruta de cobro | 3 |
| `CO-AR-001` | Contrato de arrendamiento de vivienda urbana | 6 |
| `CO-EM-003` | Contrato de prestación de servicios independientes | 6 |
| `CO-EM-004` | Acuerdo de confidencialidad y propiedad intelectual | 7 |
| `CO-LA-001` | Informe técnico de liquidación laboral | 3 |
| `CO-LA-002` | Contrato de trabajo a término indefinido | 3 |
| **Total** | **11 documentos** | **40** |

## Hallazgos detectados y corregidos durante M32.3

La iteración se ejecutó de forma fail-closed y no se limitó a producir archivos. La inspección reveló y permitió corregir:

1. **Página vacía en `CO-EM-003`.** La fábrica introducía un salto manual inmediatamente antes de firmas. Se elimina únicamente ese salto y se vuelve a validar el archivo y su hash.
2. **Fugas de estructuras internas en servicios.** Campos compuestos de cronograma, terminación, cierre, riesgo y condiciones económicas podían imprimirse como diccionarios o etiquetas técnicas. La fábrica v2.44 los normaliza a redacción contractual antes de generar.
3. **Infinitivos duplicados.** Se corrigieron construcciones como “ejecutar prestar” o “entregar entregar” sin alterar el objeto sustantivo suministrado.
4. **Ruta ausente en tránsito.** Los expedientes sintéticos incorporan una ruta controlada por producto; no se permite `Ruta: None`.
5. **Contradicciones en hábeas data y cobro.** Los casos sintéticos fueron alineados para que estado de obligación, pago, saldo, soporte y pretensión pertenezcan a un mismo supuesto demostrativo.
6. **Tasas cero aparentes en `CO-CD-004`.** Cuando el propio documento declara que los intereses no fueron calculados, los ceros técnicos se reemplazan por “Pendiente de verificación”. La normalización queda registrada en el manifiesto.
7. **Claves históricas divergentes.** Salud, consumo y tránsito utilizaban nombres de campo distintos a los del cuestionario moderno. M32.3 incorpora una capa de casos controlados con las claves exactas de cada fábrica.
8. **Datos demo jurídicamente engañosos.** No se presentan como definitivos términos que exigen calendario de festivos, recepción efectiva, norma especial o cotejo documental. Se muestran como pendientes de validación.

## Compuerta de páginas vacías

El workflow analiza la densidad de contenido sustantivo de cada PNG, excluyendo márgenes, encabezado y pie. Una página por debajo del umbral de contenido bloquea la ejecución. Las páginas dispersas no se aprueban automáticamente: quedan advertidas para inspección humana.

Resultado del SHA `fabd92a3c03336820ec9a1aa34c3418c05173969`:

- productos: `11`;
- DOCX: `11`;
- manifiestos: `11`;
- páginas PDF/PNG: `40`;
- páginas vacías: `0`;
- páginas dispersas advertidas: `4`;
- revisión visual humana: `pending`;
- revisión jurídica sustantiva: `pending`;
- aprobación jurídica: `pending`;
- aprobación QA: `pending`;
- candidato de liberación: `false`.

## Evidencia reproducible

Ejecución M32.3 de rama: `31059461569`.

Artefacto:

- nombre: `m32-3-portafolio-11-productos`;
- ID: `8951527332`;
- tamaño: `15.224.261` bytes;
- digest: `sha256:93fb1cf3786a97ecfdf63bf23c3b345795e6dce7b64d6e1188ea5cedea10ffa9`;
- commit: `fabd92a3c03336820ec9a1aa34c3418c05173969`;
- expiración: `2026-09-05`.

La ejecución general `31059461582` aprobó `smoke` y `visual-docx`, incluyendo sintaxis, integridad documental, interfaz, datos demo y arranque HTTP.

## Inspección realizada

Se inspeccionaron las hojas de contacto y páginas individuales del portafolio durante la iteración. Después de cada corrección se reinspeccionaron específicamente los documentos modificados. También se ejecutó un escaneo textual de los once DOCX para detectar:

- `None`, `NULL` y `undefined`;
- variables con llaves sin resolver;
- marcadores centinela entre corchetes;
- infinitivos duplicados;
- etiquetas técnicas filtradas al texto final.

El escaneo final no encontró coincidencias de esas categorías. Esta inspección asistida no equivale a la aprobación formal del especialista jurídico ni del responsable de QA.

## Criterio de cierre

M32.3 solo puede integrarse a `main` cuando concurran:

1. CI general en verde;
2. workflow M32.3 en verde;
3. once productos y once manifiestos;
4. conversión y rasterización de todas las páginas;
5. cero páginas vacías;
6. expediente de revisión y once hojas de contacto;
7. matriz jurídica sustantiva documentada;
8. PR fusionado sobre el mismo SHA revisado;
9. validación completa posterior a la fusión;
10. publicación de GitHub Pages sin regresiones.

La integración técnica no autoriza firma, radicación, publicación ni uso en un caso real. Esas acciones requieren expediente completo, verificación normativa, revisión jurídica y aprobación QA sobre el hash exacto del documento.