@echo off
cd /d "%~dp0"
set "LEGAL_PROFILE=local"
set "LEGAL_APP_ENV=demo_public"
set "LEGAL_PUBLIC_DEMO_MODE=true"
set "LEGAL_ALLOW_DEMO_ACCOUNTS=true"
set "LEGAL_DEMO_PASSWORD=LegalAIZDemo2026!"
set "LEGAL_REQUIRE_MFA_ROLES="
set "LEGAL_REQUIRE_ORIGIN_CHECK=false"
set "LEGAL_SECURE_COOKIES=false"
set "LEGAL_DATABASE_BACKEND=sqlite"
set "LEGAL_HOST=0.0.0.0"
if not defined LEGAL_PORT set "LEGAL_PORT=8765"
py -3 run.py --lan || python run.py --lan
