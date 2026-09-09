# M38.3 — Client Workspace & Controlled Delivery Experience

## Objetivo

Convertir `/caso/:id` en un centro de solución comprensible para el cliente, reutilizando la entrega controlada M36.3 ya certificada en vez de crear una segunda lógica de documentos o descarga.

## Hallazgos de auditoría

El expediente cliente ya tenía resumen, revisión dual y seguimiento, pero conservaba lenguaje de implementación visible:

- `checkout sandbox`;
- `Orden` y `Comprobante sandbox`;
- `Journey`;
- descripciones de documentos como `auditorías y paquetes generados`;
- ausencia de una tarjeta cliente que consumiera directamente el estado `DELIVERED_IN_APP` de M36.3.

Esto producía una ruptura entre el flujo jurídico seguro del backend y la experiencia percibida por el usuario.

## Implementación

La capa `client_workspace_m38_3`:

1. sólo se activa para usuarios `client` dentro de `/caso/:id`;
2. reutiliza `GET /api/m36/delivery/cases/:case_id`;
3. no añade endpoints ni modifica M36.3;
4. sólo presenta una entrega positiva si el servidor devuelve `DELIVERED_IN_APP`, `dual_human_approval_preserved=true`, al menos un documento y la URL de descarga exacta esperada;
5. no muestra hashes, ids internos de delivery, assignment/intake, actores, rutas internas ni metadata de integridad;
6. reutiliza el `download_url` certificado para que el servidor registre `DOWNLOAD_REQUESTED` únicamente cuando el usuario hace clic;
7. no interpreta una descarga como lectura, recepción externa, radicación ni resultado jurídico.

## Experiencia visible

Cuando existe una entrega válida, el cliente ve:

- `Documentos finales disponibles`;
- número de documentos liberados;
- revisión jurídica completada;
- control de calidad independiente completado;
- puesta a disposición dentro del expediente autenticado;
- acceso a `Ver documentos` y `Descargar paquete final`;
- explicación expresa de qué significa y qué no significa la puesta a disposición.

Si la API responde `DELIVERY_NOT_AVAILABLE`, M38.3 no inventa una entrega ni presenta error al cliente: mantiene la experiencia normal de revisión/seguimiento. Si ocurre un fallo distinto, muestra un estado neutral y no ofrece descarga hasta verificar nuevamente la entrega.

## Limpieza de lenguaje

Sin modificar M35.3, la capa de presentación transforma términos técnicos de la tarjeta de activación:

- `Expediente activado` → `Expediente listo para continuar`;
- `Total sandbox` → `Valor en entorno de prueba`;
- `Orden` → `Referencia de servicio`;
- `Comprobante sandbox` → `Comprobante de prueba`;
- `Pago sandbox verificado` → `Operación de prueba validada`;
- `Trazabilidad de orden y expediente verificada` → `Vinculación con tu expediente confirmada`;
- `Journey` → `Estado del proceso`.

También mejora la descripción del tab de documentos y renombra `Exportar expediente` como `Descargar copia del expediente` para el cliente.

## Límites de seguridad y gobierno

M38.3 no:

- ejecuta entrega;
- llama `POST /deliver`;
- crea aprobación jurídica ni QA;
- altera estados M24/M32/M35/M36/M37;
- crea documentos o versiones;
- descarga automáticamente archivos;
- usa `localStorage` o `sessionStorage`;
- expone hashes o rutas internas;
- afirma recepción, lectura, notificación externa, radicación o éxito jurídico.

La autorización de lectura, aislamiento por propietario, integridad del paquete y registro de descarga siguen siendo responsabilidad exclusiva de M36.3.

## Validación requerida

- suite integral sin regresiones;
- regresiones M38.3;
- inventario 11 productos / 473 preguntas / 273 reglas;
- 451 respuestas demo históricas;
- M33.3 + M34.2→M37.3 HTTP smoke;
- public demo 8/8;
- QA visual documental y conteos sin regresión.
