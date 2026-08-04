# CO-LA-002 — Changelog

## 2.36
- Capa canónica aditiva de 27 preguntas, 30 perfiles y 13 documentos.
- Autorizaciones de imagen, biometría y geolocalización separadas y no preseleccionadas.
- Compatibilidad preservada con el motor V224.


## 2.37
- Flujo visible de ocho pasos.
- Guardado local de borrador.
- Evaluación jurídica autenticada por POST.
- Resumen de bloqueos y documentos en tiempo real.
- Interfaz responsive y autorizaciones sensibles desmarcadas.


## 2.38 — Motor jurídico ampliado
- Evaluación explicable con severidades, campos faltantes y requisitos de revisión.
- Selección trazable de bloques y documentos.
- Controles ampliados sobre partes, funciones, modalidad, jornada, disponibilidad, remuneración, activos, riesgos, datos y propiedad intelectual.
- Endpoint V238 con alias de compatibilidad V237.
- Interfaz de hallazgos, faltantes, bloques y revisión profesional.


## v2.39 — Fábrica documental
- Generación DOCX real del contrato principal y documentos condicionales.
- Validación de bloqueos, completitud y variables centinela antes de generar.
- Manifiesto de generación con hashes SHA-256 y aprobaciones jurídica/QA pendientes.
- Descarga de paquete ZIP mediante RBAC para especialista y administrador.
- Interfaz con acción “Generar documentos”.

## v2.40 — Revisiones inmutables y aprobación dual

- Registro inmutable de revisiones con hash SHA-256 y vínculo a la revisión base.
- Comparación estructurada de respuestas entre revisiones.
- Invalidación automática de aprobaciones ante cualquier nueva revisión.
- Aprobación jurídica y QA separadas, secuenciales y por actores distintos.
- Liberación de paquete aprobado únicamente después de la doble aprobación.
- Cadena de auditoría enlazada por hash para generación, revisiones, decisiones y liberación.
- Endpoint de consulta, comparación, revisión, aprobación y descarga aprobada.
- Interfaz de estado y acciones de gobierno documental.


## 2.41.0 - M6
- Se ejecutó QA documental sobre cuatro escenarios y siete tipos de anexo.
- Se corrigieron etiquetas técnicas visibles (`rotating`, `ordinary`) y fecha ISO en el contrato.
- Se añadieron pruebas de localización y ausencia de variables sin resolver.
- La regresión global histórica se ejecutó parcialmente: 72 pruebas iniciales aprobadas antes del límite de ejecución; la suite focal del módulo se ejecutó completamente.


## 2.41 — Corrección de distribución
- Se declaró `python-docx` como dependencia obligatoria de la fábrica documental.
- Se reforzó el inicio local para completar entornos virtuales existentes.
- No se modificó la lógica jurídica ni documental del producto.
