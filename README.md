# LegalAIZ.it — Demo M31.8

**Versión:** M31.8 · v5.0.7  
**Estado técnico:** publicada y validada automáticamente.

[![Validación LegalAIZ.it](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml/badge.svg)](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml)

## Abrir directamente desde GitHub

1. Selecciona **Code**.
2. Abre **Codespaces**.
3. Pulsa **Create codespace on main**.
4. La aplicación instalará dependencias, iniciará el backend y abrirá el puerto `8765`.

Acceso directo para crear el Codespace:

https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=1322097934

## Credenciales demo

- Administradora / QA: `ana@demo.legalaiz.it`
- Especialista laboral: `maria@demo.legalaiz.it`
- Especialista contractual: `carlos@demo.legalaiz.it`
- Especialista tránsito: `laura@demo.legalaiz.it`
- Contraseña común: `LegalAIZDemo2026!`

## Ejecución local

- macOS: `00_ABRIR_LEGALAIZIT_MAC.command`
- Windows: `00_ABRIR_LEGALAIZIT_WINDOWS.bat`
- Linux: `00_ABRIR_LEGALAIZIT_LINUX.sh`

Ejecución manual:

```bash
pip install -r requirements.txt
python run.py --lan --no-browser
```

Abrir `http://127.0.0.1:8765`.

## Contenido de la versión

M31.8 conserva las capacidades acumuladas de LegalAIZ.it e incorpora once expedientes sintéticos completos, uno por producto jurídico. Cada expediente permite demostrar captura de datos, diagnóstico, generación documental, revisiones inmutables, aprobación jurídica, QA independiente y liberación de paquetes finales verificables.

La cohorte demo genera 76 DOCX activos, 11 certificados, 11 paquetes finales y un ZIP global. Al crear una nueva revisión, la liberación anterior pierde vigencia y deben repetirse las dos aprobaciones sobre el nuevo hash.

## Validación automática

Cada modificación en `main` ejecuta:

- instalación de dependencias;
- compilación de sintaxis Python;
- arranque real del backend;
- comprobación del endpoint `/api/live`.

GitHub Pages no ejecuta el backend Python. Para probar la aplicación completa debe usarse Codespaces, Docker o un servicio de despliegue conectado al repositorio.

**LegalAIZ.it — Más que respuestas, soluciones.**
