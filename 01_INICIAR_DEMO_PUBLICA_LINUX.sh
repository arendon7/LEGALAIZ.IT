#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LEGAL_PROFILE=local
export LEGAL_APP_ENV=demo_public
export LEGAL_PUBLIC_DEMO_MODE=true
export LEGAL_ALLOW_DEMO_ACCOUNTS=true
export LEGAL_DEMO_PASSWORD='LegalAIZDemo2026!'
export LEGAL_REQUIRE_MFA_ROLES=''
export LEGAL_REQUIRE_ORIGIN_CHECK=false
export LEGAL_SECURE_COOKIES=false
export LEGAL_DATABASE_BACKEND=sqlite
export LEGAL_HOST=0.0.0.0
export LEGAL_PORT=${LEGAL_PORT:-8765}
python3 run.py --lan
