# LegalAIZ.it V1-OPS4 — Private Execution Preflight & Dispatch Guard

## 1. Objetivo

OPS4 introduce una barrera inmediatamente anterior a la distribución manual de los paquetes humanos OPS3.

El problema que resuelve es temporal: un paquete OPS3 puede haber sido correcto al generarse y quedar obsoleto después por un cambio legítimo en la campaña RC8.1. Por ejemplo, inicio de otro control, bloqueo, aborto o cualquier evento que cambie el board OPS2.

OPS4 evita que un operador distribuya paquetes contra un estado antiguo.

OPS4 **no envía** archivos, **no ejecuta** controles, **no registra** coordinación, **no registra evidencia**, **no aprueba**, **no ratifica** y **no autoriza** producción o pagos.

## 2. Regla de vigencia

Todo paquete OPS3 contiene `source_board_sha256`.

OPS4 reconstruye el board actual de la misma campaña y compara:

```text
OPS3 source_board_sha256 == OPS2 current board_sha256
```

Si no son idénticos:

```text
STALE_SOURCE_BOARD
```

y el despacho queda bloqueado completamente.

No se intenta inferir qué packet podría seguir siendo útil. La estrategia es deliberadamente fail-closed: regenerar OPS3 desde el board actual y volver a ejecutar OPS4.

## 3. Estado despachable

OPS4 sólo considera despachable:

```text
READY_TO_EXECUTE
```

No despacha automáticamente controles en:

- `WAITING_FOR_DEPENDENCY`;
- `EXECUTION_COORDINATION_STARTED`;
- `EVIDENCE_LINKED`;
- `REVIEW_REQUIRED`;
- `REVIEW_COORDINATION_READY`;
- `RATIFICATION_REQUIRED`;
- `CONTROL_BLOCKED`;
- `PLAN_DRIFT`;
- `EVIDENCE_EXPIRED`;
- `INTEGRITY_FAILURE`;
- `CAMPAIGN_ABORTED`;
- `VERIFIED`.

Cada uno requiere su flujo canónico específico. OPS4 no amplía semánticas para ganar conveniencia.

## 4. Preflight

```text
python tools/v1_private_execution_dispatch.py \
  --ledger-path <RUTA_LOCAL_LEDGER_RC8_1> \
  preflight \
  --pack-dir <RUTA_PRIVADA_PACK_OPS3>
```

El resultado es redactado y puede mostrar:

- campaign ID;
- estado de campaña;
- board de origen y board actual;
- número de controles listos;
- `control_ref`, secuencia, ola y estado;
- controles no despachables por estado;
- blockers globales.

Nunca muestra:

- nombres;
- contactos;
- `person_ref`;
- `actor_id`;
- contenido de los packets privados;
- evidencia;
- secretos.

## 5. Validación estructural del pack OPS3

Antes del board check, OPS4 exige:

1. `assignment-manifest.json` regular, no symlink.
2. Schema exacto OPS3.
3. Exactamente 22 controles.
4. 22 `control_ref` únicos.
5. 22 `packet_file` únicos.
6. Rutas relativas `controls/*.md` sin traversal.
7. Cada packet existe y no es symlink.
8. Ningún packet escapa del directorio privado.
9. El manifest conserva las garantías OPS3 de no PII y no mutación.
10. No aparecen claves `display_name`, `contact`, `actor_id` o `person_ref` en el manifest.
11. Cada packet conserva bindings textuales mínimos con campaña, control, estado y roles del manifest.
12. Secuencia, ola y roles coinciden con el board canónico actual.

Esta validación no pretende convertir el packet privado en evidencia criptográfica. Su objetivo es evitar errores operativos evidentes, sustitución accidental de archivos y desalineación estructural.

## 6. Despacho privado

```text
python tools/v1_private_execution_dispatch.py \
  --ledger-path <RUTA_LOCAL_LEDGER_RC8_1> \
  write \
  --pack-dir <RUTA_PRIVADA_PACK_OPS3> \
  --output-dir <RUTA_PRIVADA_DISPATCH>
```

El comando sólo materializa localmente una carpeta con los packets que en ese board exacto estaban `READY_TO_EXECUTE`.

No los transmite.

Contenido:

- `dispatch-manifest.json` — redactado;
- `README_PRIVATE.md` — advertencias de uso/custodia;
- `controls/*.md` — únicamente packets privados despachables.

## 7. No persistencia de PII derivada

`dispatch-manifest.json` no incluye nombres, contactos, person refs ni actor IDs.

Tampoco persiste hashes de archivos privados que contienen PII. El vínculo de frescura se hace contra el `board_sha256`, no contra identidades humanas.

Los packets copiados siguen siendo confidenciales y conservan únicamente los datos de coordinación que ya fueron validados por OPS3.

## 8. Filesystem

Pack fuente y output deben vivir:

- fuera del repositorio; o
- bajo raíces ya ignoradas por Git: `runtime/`, `secrets/`, `output/`, `artifacts/`, `generated/`.

Una ruta versionable falla cerrado.

La salida:

- no puede existir previamente;
- se construye en temporal privado y se mueve al final;
- usa `0700` para directorios;
- usa `0600` para archivos.

## 9. Ausencia de transporte

OPS4 no importa ni utiliza:

- clientes HTTP;
- sockets;
- email;
- Slack;
- subprocess para envío;
- APIs externas.

No existe comando `send` o `deliver`.

La distribución a la persona asignada sigue siendo una actuación humana sobre un almacenamiento/canal autorizado.

## 10. Ausencia de ejecución

OPS4 no llama `start_control`.

El packet puede contener un comando de coordinación generado por OPS3, pero OPS4 sólo copia el archivo. Un humano decide posteriormente si corresponde utilizarlo.

Por esta razón:

```text
network_delivery_performed = false
control_execution_performed = false
campaign_mutated = false
evidence_mutated = false
release_authorization_changed = false
```

## 11. Relación con dependencias RC6

OPS4 no recalcula dependencias por cuenta propia.

Consume `work_status` del board OPS2, que a su vez deriva dependencias del plan RC6 y evidencia canónica RC2/RC7.

Así se mantiene una única semántica de dependencia.

## 12. Por qué no se despacha un pack parcialmente obsoleto

Podría parecer suficiente comparar sólo cada control. Se descartó esa opción porque un evento de campaña puede cambiar:

- el estado de coordinación;
- blockers explícitos;
- secuencia operativa esperada;
- decisiones humanas sobre si continuar;
- la lectura agregada del board.

El costo de regenerar OPS3 es bajo y la seguridad/trazabilidad de exigir un snapshot exacto es mayor.

## 13. Flujo operativo resultante

```text
RC6 plan
  ↓
RC8.1 campaign
  ↓
OPS1 runbook
  ↓
OPS2 current board
  ↓
OPS3 private human assignments
  ↓
OPS4 exact-board preflight
  ↓
private READY_TO_EXECUTE subset
  ↓
manual authorized distribution
  ↓
manual/material external execution
  ↓
RC2/RC7 authentic evidence
  ↓
RC8.1 evidence coordination
  ↓
RC9 release-readiness
  ↓
RC10 custody
  ↓
separate human production/payment authorization
```

## 14. Regeneración obligatoria

Después de cualquier evento RC8.1, el board cambia.

Por tanto, un pack OPS3 ya generado debe tratarse como snapshot histórico y no como instrucción vigente. Antes de un nuevo despacho:

1. reconstruir OPS2;
2. regenerar OPS3 con la asignación privada vigente;
3. ejecutar OPS4 otra vez.

Esto evita instrucciones zombis.

## 15. Seguridad y protección de datos

OPS4 mantiene mínimo privilegio y minimización:

- no introduce PII nueva;
- no replica el archivo original de asignación;
- no crea un directorio nominativo;
- no versiona PII;
- no publica PII en stdout;
- no sube packets a CI;
- no convierte PII en evidencia de release.

La organización sigue siendo responsable por cifrado, controles de acceso, retención y eliminación del almacenamiento privado.

## 16. Criterios de aceptación

1. Pack OPS3 completo de 22 controles.
2. Manifest exacto y sin PII.
3. Traversal y symlinks rechazados.
4. Packet faltante rechazado.
5. Binding alterado rechazado.
6. Roles/secuencia/ola alineados con board actual.
7. `source_board_sha256` idéntico al board vivo para permitir despacho.
8. Cualquier evento posterior de campaña produce `STALE_SOURCE_BOARD`.
9. Campaña abortada bloquea despacho.
10. Sólo `READY_TO_EXECUTE` es despachable.
11. Output contiene únicamente subset listo.
12. Manifest de despacho sin PII.
13. Sin hashes de packet privado.
14. Sin transporte de red.
15. Sin ejecución de control.
16. Sin mutación de campaign ledger.
17. Sin mutación de evidence dossiers.
18. Sin cambio de autorización.
19. Output existente no se sobrescribe.
20. Rutas versionables rechazadas.
21. Permisos 0700/0600.
22. CLI únicamente `preflight`/`write`.
23. Sin endpoint runtime.
24. RC9 permanece release gate.
