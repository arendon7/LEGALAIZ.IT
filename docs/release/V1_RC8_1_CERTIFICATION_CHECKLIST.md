# V1-RC8.1 — Certification checklist

SHA objetivo: se fija al cerrar el árbol antes de CI.

## Invariantes funcionales

- [ ] `campaign_state=CREATED` en campaña nueva aunque existan controles esperando prerrequisitos.
- [ ] `campaign_state=IN_PROGRESS` después de actividad válida aunque queden dependencias pendientes.
- [ ] `start_control()` rechaza controles con prerrequisitos RC6 no verificados.
- [ ] `CONTROL_BLOCKED` explícito produce bloqueo global.
- [ ] drift del plan produce bloqueo global.
- [ ] `CAMPAIGN_ABORTED` conserva estado terminal.
- [ ] `EVIDENCE_COMPLETE` no autoriza producción ni pagos.
- [ ] CLI canónico usa overlay RC8.1.
- [ ] no existen comandos approve/ratify/authorize/go-live.
- [ ] no se expone endpoint runtime de campañas o release activation.

## Regresión obligatoria

- [ ] sintaxis/imports PASS.
- [ ] suite completa PASS.
- [ ] inventario 11 productos / >=473 preguntas / >=273 reglas PASS.
- [ ] datos demo PASS.
- [ ] smoke HTTP acumulado M33.3 + M34-M37 PASS.
- [ ] public demo M33.1 PASS.
- [ ] QA visual DOCX PASS.

## Gobierno

RC8.1 no autoriza producción real, pagos reales ni go-live. No sustituye evidencia RC2/RC7, aprobación profesional, ratificación ni decisión humana versionada.
