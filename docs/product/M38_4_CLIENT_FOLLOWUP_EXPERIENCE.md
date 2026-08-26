# M38.4 — Seguimiento guiado posterior a la entrega

## Objetivo

Convertir las capacidades certificadas M37.0–M37.3 en una experiencia comprensible para el cliente dentro del expediente autenticado, sin crear un segundo motor de seguimiento ni alterar las reglas jurídicas, RBAC, trazabilidad o compuertas de cierre existentes.

M38.4 se apila sobre M38.3 y utiliza como fuentes de verdad exclusivamente:

- M37.0 para enrolamiento, actividades y `close_readiness`.
- M37.1 para soportes cifrados y el estado público de revisión de ingreso.
- M37.2 para fechas registradas y recordatorios operativos.
- M37.3 para la evaluación y el resumen profesional visible al cliente.

## Alcance de experiencia

En `/caso/:id`, exclusivamente para el cliente autenticado, la interfaz puede:

1. mostrar la disponibilidad de seguimiento después de una entrega M36.3 válida;
2. activar M37.0 mediante una acción explícita del usuario y la confirmación canónica `INICIAR SEGUIMIENTO`;
3. mostrar las actividades M24 reutilizadas por M37.0 y su avance reportado;
4. registrar una actividad como realizada con nota obligatoria;
5. adjuntar un soporte individual mediante el intake M37.1, respetando tipos y límite cliente de 10 MB;
6. mostrar la revisión pública del soporte y cualquier mensaje de aclaración dirigido al cliente;
7. descargar el soporte únicamente mediante la URL exacta publicada por M37.1;
8. registrar fechas de hechos ya contemplados por M37.2;
9. crear, reconocer o cancelar recordatorios in-app ya contemplados por M37.2;
10. mostrar `close_readiness` como preparación para una decisión profesional, nunca como cierre automático;
11. mostrar el `client_summary` M37.3 cuando exista una disposición profesional completada.

## Límites jurídicos y de gobernanza

M38.4 no:

- calcula términos legales o calendarios normativos;
- presenta `due_at` como vencimiento jurídico;
- verifica recepción por autoridades o terceros;
- convierte una actividad reportada por el cliente en hecho externamente verificado;
- convierte la carga o revisión de un soporte en autenticidad, suficiencia jurídica o valor probatorio;
- completa una actividad por adjuntar un soporte, registrar una fecha o atender un recordatorio;
- permite al cliente revisar soportes profesionalmente;
- permite al cliente cerrar o escalar el expediente;
- envía correo, SMS ni notificaciones externas;
- crea estado M38 paralelo, almacenamiento en navegador ni polling de fondo;
- expone `object_ref`, hashes de integridad, actores internos, razones internas, datos de pago o detalles del escáner.

El cierre o escalamiento sigue perteneciendo exclusivamente a M37.3 y a los roles allí autorizados. Un cierre de alcance de seguimiento no equivale a éxito jurídico ni acredita efectos externos.

## Seguridad

- El frontend sólo se monta para `state.user.role === client` y para el caso presente en `/caso/:id`.
- El servidor conserva la autorización real y el aislamiento de propietario de M37; la validación del navegador es únicamente UX defensiva.
- Las mutaciones usan `api()` y por tanto conservan sesión same-origin y CSRF existentes.
- Los soportes usan `FormData`; el servidor sigue validando extensión, firma, contenido activo, cuotas, escaneo e integridad del object store cifrado.
- La descarga de soportes sólo se ofrece cuando la URL pública coincide exactamente con `/api/m37/evidence/cases/:case/items/:item/download`.
- Las APIs profesionales de revisión, cierre y escalamiento no son invocadas por M38.4.

## UX

La nueva tarjeta organiza el post-entrega en una sola narrativa:

- siguiente etapa y activación explícita;
- resumen de actividades, soportes y recordatorios;
- avance reportado, expresamente separado de cualquier probabilidad de éxito;
- checklist por actividad;
- soportes y referencias operativas desplegables por tarea;
- estado profesional final o condiciones pendientes para revisión de cierre.

Incluye estados de error fail-closed, foco visible, `progressbar` accesible, layouts adaptativos a 900 px y 640 px, y respeto por `prefers-reduced-motion`.

## Criterios de aceptación

1. Los assets M38.4 cargan después de M38.3.
2. No existe `/api/m38/*` ni backend M38 nuevo.
3. Las cuatro fuentes M37 existentes son reutilizadas, no duplicadas.
4. El seguimiento no aparece como disponible cuando M37 responde 404.
5. Una lectura parcial con error no inventa avance ni cierre; muestra estado de reintento.
6. Activar seguimiento exige acción explícita y confirmación canónica del servidor.
7. Completar una tarea se presenta como reporte, no verificación.
8. La carga de soportes no completa tareas y no habilita revisión profesional al cliente.
9. Fechas y recordatorios permanecen operativos y sin cálculo normativo.
10. El cliente no puede invocar cierre ni escalamiento M37.3.
11. El resumen profesional sólo usa el modelo público M37.3.
12. No se renderizan secretos ni plumbing interno M37.
13. No hay `localStorage`, `sessionStorage`, IndexedDB ni polling.
14. El `MutationObserver` no genera un ciclo de remount desde caché.
15. La interfaz conserva accesibilidad, responsive y marca LegalAIZ.it.
16. La suite completa, inventario, demo, smoke M33.3→M37.3, demo pública y QA visual documental deben permanecer verdes antes de certificar el SHA.
