# M32.9 — Gobierno de consentimientos, preferencias y supresiones

## Objetivo

Incorporar una compuerta trazable antes del procesamiento de comunicaciones M32.8, diferenciando finalidad, canal, relación, preferencia, supresión, horario y frecuencia.

## Criterios jurídicos incorporados

La implementación toma como referencia normativa principal:

- Ley 1581 de 2012: legalidad, finalidad, libertad, transparencia, acceso restringido, seguridad, confidencialidad, autorización y deber de informar.
- Decreto 1074 de 2015: reglamentación del régimen general de protección de datos personales.
- Ley 2300 de 2023: canales autorizados, horarios y reglas de contacto en cobranza, además de su extensión a comunicaciones comerciales o publicitarias.

La plataforma no presume que toda comunicación se rige de forma idéntica. Se clasifican cuatro finalidades:

1. `professional_operational`: alertas internas a profesionales activos.
2. `service_transactional`: comunicaciones necesarias para un servicio solicitado o relación acreditada.
3. `commercial_marketing`: comunicaciones comerciales, sujetas a consentimiento expreso en la compuerta.
4. `collections`: comunicaciones de cobranza, sujetas a canal autorizado, horario y frecuencia.

## Capacidades

- Relaciones activas o inactivas con base declarada y hash de evidencia.
- Preferencias concedidas o negadas por finalidad y canal.
- Avisos versionados y verificados mediante SHA-256.
- Activación de avisos por una persona distinta de quien creó la versión.
- Supresión global, por canal, por finalidad o por combinación finalidad-canal.
- Levantamiento trazable de supresiones sin borrar el historial.
- Evaluación `allowed` o `blocked` con razones estructuradas.
- Ventanas horarias configurables y cierres explícitos.
- Límites operativos diarios y semanales.
- Registro sintético de contactos permitidos.
- Cadena M32.9 append-only independiente.
- Integración efectiva con el procesamiento M32.8.

## Privacidad y minimización

- No se guarda el texto de la evidencia original; se conserva su SHA-256.
- No se guarda la referencia contextual del contacto; se conserva su SHA-256.
- No se incorporan direcciones completas, documentos, cláusulas ni anexos.
- Una autorización concedida debe quedar vinculada al aviso activo y a su SHA-256.
- Una negativa o supresión prevalece sobre la autorización anterior dentro del alcance aplicable.

## Política conservadora

Para marketing y cobranza, la configuración inicial usa:

- Lunes a viernes: 7:00 a. m. a 7:00 p. m.
- Sábados: 8:00 a. m. a 3:00 p. m.
- Domingos: bloqueados.
- Festivos: bloqueados únicamente cuando hayan sido cargados expresamente.
- Máximo operativo: un contacto por día.
- Máximo operativo: un canal distinto dentro de siete días.

Estas reglas se registran como política operativa conservadora. `official_holiday_calendar` permanece en `false`; no se afirma que el sistema calcule automáticamente calendarios oficiales ni que resuelva por sí solo la aplicación jurídica de una excepción.

## Integración con M32.8

`GovernedTransactionalCommunications` evalúa cada despacho elegible antes de llamar al proveedor sandbox:

- Si la decisión es permitida, M32.8 procesa el despacho y M32.9 registra un contacto sintético.
- Si la decisión es bloqueada, el despacho pasa a `dead_letter` con `governance_blocked` y referencia a la decisión.
- La dirección completa continúa resolviéndose únicamente durante el intento y no se persiste.
- La entrega real continúa deshabilitada.

## Límites expresos

M32.9 no sustituye:

- La política de tratamiento de datos personales del responsable.
- La autorización real del titular.
- La validación de identidad de quien solicita una revocatoria o supresión.
- El análisis jurídico de excepciones legales o contractuales.
- La gestión formal de consultas y reclamos de hábeas data.
- Un calendario oficial de festivos.
- La evidencia de entrega de un proveedor real.

## Validación prevista

- Regresiones acumuladas M32.4 a M32.9.
- Cobertura de los 11 productos jurídicos.
- Autorización comercial por finalidad y canal.
- Bloqueo por horario, frecuencia, negativa y supresión.
- Separación de funciones para avisos.
- Integración efectiva con M32.8.
- Integridad de las cadenas M32.7, M32.8 y M32.9.
- Arranque HTTP y protección anónima de `/api/m32/contact-governance`.
