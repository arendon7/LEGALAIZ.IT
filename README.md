# LegalAIZ.it — Demo M31.8 (v5.0.7)

Repositorio ejecutable de la demo integral de LegalAIZ.it.

## Abrir en GitHub Codespaces

1. Abra **Code → Codespaces → Create codespace on main**.
2. Espere la instalación automática.
3. Abra el puerto reenviado **8765**.
4. Ingrese con `ana@demo.legalaiz.it` y `LegalAIZDemo2026!`.

## Ejecución local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LEGAL_PROFILE=local LEGAL_APP_ENV=demo LEGAL_ALLOW_DEMO_ACCOUNTS=true
export LEGAL_DEMO_PASSWORD='LegalAIZDemo2026!' LEGAL_REQUIRE_MFA_ROLES=''
python run.py
```

> GitHub Pages no ejecuta el backend Python. Para probar la aplicación completa use Codespaces, Docker o un despliegue conectado al repositorio.

---

# LegalAIZ.it 5.0.7 — M31.8

## Demo integral por expediente y liberación documental

M31.8 conserva todas las capacidades de M31.7 y añade once expedientes sintéticos completos, uno por producto jurídico. Cada expediente recorre captura de datos, diagnóstico, generación de documentos, revisión inmutable, aprobación jurídica, QA independiente y liberación de un paquete final verificable.

### Inicio local

- macOS: `00_ABRIR_LEGALAIZIT_MAC.command`
- Windows: `00_ABRIR_LEGALAIZIT_WINDOWS.bat`
- Linux: `00_ABRIR_LEGALAIZIT_LINUX.sh`

Ingrese con `ana@demo.legalaiz.it` y clave `LegalAIZDemo2026!`, luego abra **Demo de expedientes**. También puede usar los perfiles de especialistas indicados en la propia pantalla para mostrar la aprobación jurídica separada del QA.

La cohorte genera 76 DOCX activos, 11 certificados, 11 paquetes finales y un ZIP global. Al crear una nueva revisión, la liberación anterior deja de estar vigente y deben repetirse las dos aprobaciones sobre el nuevo hash.

Los datos y aprobaciones son sintéticos. PostgreSQL externo y producción pública continúan bloqueados hasta completar sus compuertas independientes.
