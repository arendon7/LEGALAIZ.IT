# M32.8 — Comunicaciones transaccionales auditables

## Objetivo

Convertir la cola externa creada en M32.7 en un subsistema transaccional trazable, sin habilitar todavía un proveedor de correo real ni almacenar direcciones completas en la bitácora.

## Alcance

- Sincronización idempotente de mensajes M32.7.
- Plantillas versionadas por SHA-256.
- Activación independiente de la persona creadora.
- Variables permitidas y bloqueo de marcadores desconocidos.
- Prohibición de adjuntos y contenido documental.
- Resolución del correo únicamente al momento del intento.
- Cola con estados, intentos, backoff exponencial, cancelación y cola muerta.
- Proveedor `sandbox` desacoplado.
- Recibos sintéticos de entrega, rebote, rechazo, queja o aplazamiento.
- Cadena M32.8 append-only, independiente de M32.7.
- Interfaz integrada en la Mesa Jurídica.

## Estados

`queued`, `processing`, `retry_scheduled`, `accepted_sandbox`, `delivered_sandbox`, `bounced_sandbox`, `rejected_sandbox`, `complained_sandbox`, `cancelled` y `dead_letter`.

Los estados con sufijo `sandbox` son evidencia técnica sintética. No prueban envío, recepción, apertura ni notificación jurídica.

## Seguridad y privacidad

- La dirección completa se consulta en la base de usuarios durante el intento y no se incorpora al evento ni al despacho persistido.
- La cola conserva identificador interno y pista enmascarada.
- No se permiten documentos, cláusulas, anexos o datos reservados del cliente.
- Todas las escrituras pasan por sesión, control de origen y CSRF.
- Administración sincroniza, procesa, configura y cancela.
- QA o administración pueden registrar recibos sintéticos.
- La activación de una plantilla exige una persona diferente de quien creó la versión.
- Una alteración de la cadena M32.7 o M32.8 bloquea el procesamiento.

## Límites expresos

M32.8 no incorpora proveedor real, credenciales, webhook firmado, DNS transaccional, rebotes reales, apertura, clics, firma electrónica, radicación, notificación judicial ni constancia legal de entrega.

## Validación prevista

- Sintaxis Python y JavaScript.
- Regresiones M32.4 a M32.8.
- Cobertura de los 11 productos.
- Evidencia de plantillas, importación, procesamiento sandbox y recibos sintéticos.
- Verificación de minimización de datos.
- Arranque HTTP y protección anónima de `/api/m32/communications`.
