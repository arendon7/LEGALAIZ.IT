#!/bin/bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
clear
printf '\nLegalAIZ.it 5.0.7 — M31.8 Demo documental integral\n\n'
printf 'Preparando la aplicación. La primera apertura puede instalar dependencias.\n\n'

pause_and_exit() {
  printf '\nPresione Enter para cerrar.\n'
  read -r _
  exit "${1:-1}"
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "No se encontró Python 3. Instálelo desde python.org y vuelva a abrir este archivo."
  pause_and_exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9, 2) else 1)' >/dev/null 2>&1; then
  echo "LegalAIZ.it requiere Python 3.9.2 o superior."
  pause_and_exit 1
fi
if [ ! -x ".venv/bin/python" ]; then
  echo "Creando entorno local aislado…"
  python3 -m venv .venv || pause_and_exit 1
fi
PYTHON=".venv/bin/python"
check_dependencies() { "$PYTHON" -c "import cryptography, reportlab, docx, pypdf" >/dev/null 2>&1; }
if ! check_dependencies; then
  echo "Instalando dependencias. Mantenga conexión a Internet…"
  "$PYTHON" -m pip install --disable-pip-version-check --upgrade pip || pause_and_exit 1
  "$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt || pause_and_exit 1
fi
check_dependencies || pause_and_exit 1

export LEGAL_PROFILE=local
export LEGAL_APP_ENV=demo
export LEGAL_RUNTIME_DIR="$SCRIPT_DIR/runtime/demo"
export LEGAL_ALLOW_DEMO_ACCOUNTS=true
export LEGAL_DEMO_PASSWORD='LegalAIZDemo2026!'
export LEGAL_REQUIRE_MFA_ROLES=''

echo "Entorno: demostración local con información ficticia."
echo "Usuario recomendado: ana@demo.legalaiz.it"
echo "Clave: LegalAIZDemo2026!"
echo "Abriendo http://127.0.0.1:8765"
echo "Para cerrar la aplicación, presione Control + C."
"$PYTHON" run.py 8765
STATUS=$?
[ "$STATUS" -eq 0 ] || pause_and_exit "$STATUS"
