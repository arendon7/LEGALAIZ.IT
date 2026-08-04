#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR" || exit 1
printf '\nLegalAIZ.it 5.0.7 — M31.8 Piloto local controlado\nUse únicamente casos ficticios o anonimizados.\n\n'
pause_and_exit(){ printf '\nPresione Enter para cerrar.\n'; read -r _; exit "${1:-1}"; }
command -v python3 >/dev/null 2>&1 || pause_and_exit 1
[ -x .venv/bin/python ] || python3 -m venv .venv || pause_and_exit 1
PYTHON=.venv/bin/python
"$PYTHON" -c "import cryptography, reportlab, docx, pypdf" >/dev/null 2>&1 || { "$PYTHON" -m pip install --disable-pip-version-check --upgrade pip && "$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt; } || pause_and_exit 1
read -r -p "Correo del administrador: " ADMIN_EMAIL
read -r -p "Nombre [Administrador LegalAIZ.it]: " ADMIN_NAME; ADMIN_NAME=${ADMIN_NAME:-Administrador LegalAIZ.it}
read -r -s -p "Contraseña (mínimo 12 caracteres): " ADMIN_PASSWORD; printf '\n'
[ ${#ADMIN_PASSWORD} -ge 12 ] || pause_and_exit 1
mkdir -p runtime/pilot/secrets
CONFLICT_FILE=runtime/pilot/secrets/conflict.key
[ -s "$CONFLICT_FILE" ] || { "$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))' > "$CONFLICT_FILE"; chmod 600 "$CONFLICT_FILE"; }
export LEGAL_PROFILE=local LEGAL_APP_ENV=pilot-local LEGAL_RUNTIME_DIR="$SCRIPT_DIR/runtime/pilot" LEGAL_ALLOW_DEMO_ACCOUNTS=false LEGAL_REQUIRE_MFA_ROLES='admin,specialist'
export LEGAL_BOOTSTRAP_ADMIN_EMAIL="$ADMIN_EMAIL" LEGAL_BOOTSTRAP_ADMIN_PASSWORD="$ADMIN_PASSWORD" LEGAL_BOOTSTRAP_ADMIN_NAME="$ADMIN_NAME" LEGAL_BOOTSTRAP_ADMIN_SPECIALTY='Gobernanza jurídica y producto' LEGAL_CONFLICT_HASH_KEY="$(cat "$CONFLICT_FILE")"
unset ADMIN_PASSWORD
"$PYTHON" run.py 8766
