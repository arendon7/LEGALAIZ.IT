#!/bin/bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
clear
printf '\nLegalAIZ.it 5.0.7 — M31.8 Piloto local controlado\n\n'
printf 'Este modo separa sus datos de la demostración y deshabilita las cuentas demo.\nUse únicamente casos ficticios o anonimizados.\n\n'

pause_and_exit(){ printf '\nPresione Enter para cerrar.\n'; read -r _; exit "${1:-1}"; }
command -v python3 >/dev/null 2>&1 || { echo "Instale Python 3.9.2 o superior."; pause_and_exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9,2) else 1)' >/dev/null 2>&1 || pause_and_exit 1
[ -x .venv/bin/python ] || python3 -m venv .venv || pause_and_exit 1
PYTHON=.venv/bin/python
check(){ "$PYTHON" -c "import cryptography, reportlab, docx, pypdf" >/dev/null 2>&1; }
check || { "$PYTHON" -m pip install --disable-pip-version-check --upgrade pip && "$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt; } || pause_and_exit 1

read -r -p "Correo del administrador del piloto: " ADMIN_EMAIL
[ -n "$ADMIN_EMAIL" ] || { echo "El correo es obligatorio."; pause_and_exit 1; }
read -r -p "Nombre del administrador [Administrador LegalAIZ.it]: " ADMIN_NAME
ADMIN_NAME=${ADMIN_NAME:-Administrador LegalAIZ.it}
read -r -s -p "Contraseña del administrador: " ADMIN_PASSWORD
printf '\n'
[ ${#ADMIN_PASSWORD} -ge 12 ] || { echo "La contraseña debe tener al menos 12 caracteres."; pause_and_exit 1; }

mkdir -p runtime/pilot/secrets
CONFLICT_FILE="runtime/pilot/secrets/conflict.key"
if [ ! -s "$CONFLICT_FILE" ]; then
  "$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))' > "$CONFLICT_FILE"
  chmod 600 "$CONFLICT_FILE" 2>/dev/null || true
fi
export LEGAL_PROFILE=local
export LEGAL_APP_ENV=pilot-local
export LEGAL_RUNTIME_DIR="$SCRIPT_DIR/runtime/pilot"
export LEGAL_ALLOW_DEMO_ACCOUNTS=false
export LEGAL_REQUIRE_MFA_ROLES='admin,specialist'
export LEGAL_BOOTSTRAP_ADMIN_EMAIL="$ADMIN_EMAIL"
export LEGAL_BOOTSTRAP_ADMIN_PASSWORD="$ADMIN_PASSWORD"
export LEGAL_BOOTSTRAP_ADMIN_NAME="$ADMIN_NAME"
export LEGAL_BOOTSTRAP_ADMIN_SPECIALTY='Gobernanza jurídica y producto'
export LEGAL_CONFLICT_HASH_KEY="$(cat "$CONFLICT_FILE")"
unset ADMIN_PASSWORD

echo "Abriendo piloto controlado en http://127.0.0.1:8766"
echo "MFA será requerido para administración y especialistas."
echo "Para cerrar la aplicación, presione Control + C."
"$PYTHON" run.py 8766
STATUS=$?
[ "$STATUS" -eq 0 ] || pause_and_exit "$STATUS"
