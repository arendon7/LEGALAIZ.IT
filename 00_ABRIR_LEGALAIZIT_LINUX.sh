#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
printf '\nLegalAIZ.it 5.0.7 — M31.8 Demo documental integral\n\n'
pause_and_exit(){ printf '\nPresione Enter para cerrar.\n'; read -r _; exit "${1:-1}"; }
command -v python3 >/dev/null 2>&1 || { echo "Instale Python 3.9.2 o superior."; pause_and_exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9,2) else 1)' >/dev/null 2>&1 || pause_and_exit 1
[ -x .venv/bin/python ] || python3 -m venv .venv || pause_and_exit 1
PYTHON=.venv/bin/python
check(){ "$PYTHON" -c "import cryptography, reportlab, docx, pypdf" >/dev/null 2>&1; }
check || { "$PYTHON" -m pip install --disable-pip-version-check --upgrade pip && "$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt; } || pause_and_exit 1
export LEGAL_PROFILE=local LEGAL_APP_ENV=demo LEGAL_RUNTIME_DIR="$SCRIPT_DIR/runtime/demo" LEGAL_ALLOW_DEMO_ACCOUNTS=true LEGAL_DEMO_PASSWORD='LegalAIZDemo2026!' LEGAL_REQUIRE_MFA_ROLES=''
echo "Usuario: ana@demo.legalaiz.it · Clave: LegalAIZDemo2026!"
"$PYTHON" run.py 8765
