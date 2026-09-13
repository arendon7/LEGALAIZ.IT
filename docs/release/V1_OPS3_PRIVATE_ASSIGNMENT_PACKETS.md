# LegalAIZ.it V1-OPS3 — Private Assignment Packets

## 1. Objetivo

OPS3 prepara la transición desde el tooling certificado hacia la **ejecución humana real** de los 22 controles externos.

Su propósito es permitir que un responsable operativo suministre, fuera de Git, quién ejecutará y quién revisará cada control, validar automáticamente la separación de funciones y generar un paquete privado por control.

OPS3 **no ejecuta** el control, **no crea evidencia**, **no aprueba**, **no ratifica** y **no autoriza** producción ni pagos.

## 2. Dependencias

OPS3 consume exclusivamente:

1. una campaña RC8.1 existente;
2. la mesa OPS2 certificada;
3. el runbook OPS1 y el plan RC6 transitivamente.

La campaña debe:

- existir;
- conservar el hash vigente del plan;
- no estar abortada;
- tener cadena RC8.1 íntegra.

Un `PLAN_DRIFT` bloquea la emisión de paquetes.

## 3. Archivo de asignación privado

Schema:

`legalaiz-v1-ops3-private-assignment-input-v1`

Ejemplo **sintético**:

```json
{
  "schema": "legalaiz-v1-ops3-private-assignment-input-v1",
  "campaign_id": "CAM-EXAMPLE",
  "people": [
    {
      "person_ref": "P-001",
      "display_name": "Persona Ejecutora",
      "actor_id": "USR-PLATFORM-01",
      "roles": ["platform"],
      "contact": "canal-interno-ejecutor"
    },
    {
      "person_ref": "P-002",
      "display_name": "Persona Revisora",
      "actor_id": "USR-QA-01",
      "roles": ["qa"],
      "contact": "canal-interno-revisor"
    }
  ],
  "assignments": [
    {
      "control_ref": "RC2:example_control",
      "executor_person_ref": "P-001",
      "reviewer_person_ref": "P-002"
    }
  ]
}
```

El ejemplo no constituye un archivo válido de ejecución porque una asignación real debe cubrir **exactamente los 22 controles**.

### Reglas del archivo

- `person_ref` debe ser un identificador **opaco y no nominativo**.
- `actor_id` debe corresponder a la identidad operacional que usará el flujo canónico.
- `display_name` y `contact` son datos privados para coordinación.
- una misma identidad real no puede esconderse detrás de dos `person_ref` distintos;
- cada persona declara sus roles;
- el rol del ejecutor y del revisor debe coincidir exactamente con OPS1/OPS2;
- ejecutor y revisor deben ser personas distintas para cada control;
- no se admiten campos adicionales como contraseñas, tokens, secretos o credenciales.

## 4. Ubicación privada

El archivo real **no debe versionarse**.

OPS3 rechaza inputs ubicados en rutas versionables del repositorio.

Si el archivo está dentro del árbol local de LegalAIZ.it, sólo puede ubicarse bajo una raíz ya ignorada:

- `runtime/`
- `secrets/`
- `output/`
- `artifacts/`
- `generated/`

También puede vivir completamente fuera del repositorio.

`.gitignore` ya excluye esas ubicaciones. OPS3 no modifica ese contrato.

## 5. Validación sin escritura

```text
python tools/v1_private_assignment_packets.py \
  --ledger-path <RUTA_LOCAL_LEDGER_RC8_1> \
  validate \
  --assignments <RUTA_PRIVADA_JSON>
```

La salida estándar contiene únicamente:

- campaign ID;
- estado de campaña;
- número de controles;
- número de personas;
- número de olas;
- resultado de separación de funciones;
- banderas de no persistencia/no mutación.

No imprime:

- nombres;
- contactos;
- `actor_id`;
- contenido del input.

## 6. Generación de paquetes

```text
python tools/v1_private_assignment_packets.py \
  --ledger-path <RUTA_LOCAL_LEDGER_RC8_1> \
  write \
  --assignments <RUTA_PRIVADA_JSON> \
  --output-dir runtime/private-assignments/<CAMPAIGN_ID>
```

El directorio de salida **debe no existir**. OPS3 nunca sobrescribe un paquete previo.

Se generan:

- `assignment-manifest.json` — sin PII;
- `README_PRIVATE.md` — reglas de custodia;
- `controls/<CONTROL>.md` — un archivo privado por cada uno de los 22 controles.

Total normal: **24 archivos**.

## 7. Contenido de cada paquete privado

Cada paquete incluye únicamente lo necesario para coordinar ese control:

- campaign ID;
- control y ola;
- estado OPS2 y siguiente acción;
- dependencias;
- entorno y alcance;
- ejecutor: nombre, `person_ref`, `actor_id`, rol y contacto;
- revisor independiente: mismos campos;
- confirmación de separación de funciones;
- artefactos obligatorios RC6;
- vigencia máxima;
- política de redacción;
- comando de `start-control` con el actor asignado.

El comando de `start-control` sigue teniendo exactamente la semántica RC8.1: **registra coordinación; no ejecuta la prueba externa**.

## 8. Minimización de PII

OPS3 deliberadamente no crea un índice nominativo global.

`assignment-manifest.json` contiene:

- control;
- secuencia/ola;
- estado;
- roles;
- nombre del archivo privado.

No contiene:

- `display_name`;
- `contact`;
- `actor_id`;
- `person_ref`;
- evidencia;
- hashes de archivos que contienen PII.

El input no se copia al output.

## 9. Permisos de filesystem

En la salida generada:

- directorios: `0700`;
- archivos: `0600`.

La creación usa archivos exclusivos y un directorio temporal privado antes del movimiento final. Un output existente causa error en vez de sobrescritura.

Estos permisos son una medida de defensa en profundidad. La organización debe mantener además almacenamiento cifrado, mínimo privilegio, retención y eliminación conforme a su política de protección de datos.

## 10. Separación de funciones

OPS3 valida la separación **ejecutor vs. revisor** que ya exige RC6/OPS1 para cada control.

No inventa reglas globales adicionales: una persona que legítimamente posee más de un rol puede participar en controles distintos si la política canónica lo permite.

Las separaciones posteriores de registro, revisión y ratificación continúan gobernadas por RC2/RC7; OPS3 no intenta reemplazarlas.

## 11. Relación con evidencia y autorización

Los paquetes OPS3 son instrumentos de coordinación interna.

No son:

- evidencia de que el control ocurrió;
- certificación de resultado;
- aprobación del revisor;
- ratificación del dossier;
- autorización de despliegue;
- autorización de pagos.

La evidencia auténtica debe ingresar únicamente a RC2/RC7 y vincularse a RC8.1 mediante los mecanismos ya certificados.

RC9 continúa siendo el release-readiness gate. RC10 continúa siendo la capa de custodia del audit pack redactado.

## 12. Protección frente a Git/CI

OPS3 no añade endpoint HTTP y no se incorpora a `run.py`.

Los paquetes privados:

- no deben adjuntarse a issues o PRs;
- no deben subirse como artifact de GitHub Actions;
- no deben entrar a RC9/RC10;
- no deben copiarse a documentación versionada.

La suite sólo usa identidades y contactos **sintéticos** `.invalid`.

## 13. Criterios de aceptación

1. La asignación cubre exactamente 22 controles.
2. Cada control aparece una sola vez.
3. Cada referencia de persona existe.
4. Cada rol coincide con el rol canónico requerido.
5. Ejecutores y revisores son distintos por control.
6. Un mismo `actor_id` no puede representarse con dos referencias.
7. Campos extra/secret-bearing fallan cerrado.
8. Inputs en rutas versionables fallan cerrado.
9. Outputs en rutas versionables fallan cerrado.
10. Campaña abortada o con plan drift no genera paquetes.
11. Validar/generar no modifica campaign ledger.
12. El manifest no contiene PII.
13. Los paquetes privados sí contienen los datos mínimos de coordinación.
14. El input no se copia.
15. No se persisten hashes de archivos con PII.
16. Output existente no se sobrescribe.
17. Permisos `0700/0600`.
18. CLI limitada a `validate`/`write`.
19. Sin endpoint runtime.
20. RC9 permanece release gate y no hay autorización automática.
