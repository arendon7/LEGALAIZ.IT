#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LEGAL_PROFILE=local
export LEGAL_APP_ENV=demo_public
export LEGAL_PUBLIC_DEMO_MODE=true
export LEGAL_ALLOW_DEMO_ACCOUNTS=true
if [[ -z "${LEGAL_DEMO_PASSWORD:-}" ]]; then
  export LEGAL_DEMO_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
fi
export LEGAL_REQUIRE_MFA_ROLES=''
export LEGAL_REQUIRE_ORIGIN_CHECK=true
export LEGAL_SECURE_COOKIES=false
export LEGAL_DATABASE_BACKEND=sqlite
export LEGAL_HOST=${LEGAL_HOST:-127.0.0.1}
export LEGAL_PORT=${LEGAL_PORT:-8765}
export LEGAL_PUBLIC_BASE_URL=${LEGAL_PUBLIC_BASE_URL:-"http://127.0.0.1:${LEGAL_PORT}"}
echo "LegalAIZ.it · demo pública local"
echo "Usuario admin: ana@demo.legalaiz.it"
echo "Contraseña de esta sesión: ${LEGAL_DEMO_PASSWORD}"
python3 run.py
