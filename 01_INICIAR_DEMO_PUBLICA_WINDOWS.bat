@echo off
cd /d "%~dp0"
set "LEGAL_PROFILE=local"
set "LEGAL_APP_ENV=demo_public"
set "LEGAL_PUBLIC_DEMO_MODE=true"
set "LEGAL_ALLOW_DEMO_ACCOUNTS=true"
if not defined LEGAL_DEMO_PASSWORD (
  for /f "delims=" %%P in ('py -3 -c "import secrets; print(secrets.token_urlsafe(18))" 2^>nul') do set "LEGAL_DEMO_PASSWORD=%%P"
)
if not defined LEGAL_DEMO_PASSWORD (
  for /f "delims=" %%P in ('python -c "import secrets; print(secrets.token_urlsafe(18))"') do set "LEGAL_DEMO_PASSWORD=%%P"
)
set "LEGAL_REQUIRE_MFA_ROLES="
set "LEGAL_REQUIRE_ORIGIN_CHECK=true"
set "LEGAL_SECURE_COOKIES=false"
set "LEGAL_DATABASE_BACKEND=sqlite"
if not defined LEGAL_HOST set "LEGAL_HOST=127.0.0.1"
if not defined LEGAL_PORT set "LEGAL_PORT=8765"
if not defined LEGAL_PUBLIC_BASE_URL set "LEGAL_PUBLIC_BASE_URL=http://127.0.0.1:%LEGAL_PORT%"
echo LegalAIZ.it - demo publica local
echo Usuario admin: ana@demo.legalaiz.it
echo Contrasena de esta sesion: %LEGAL_DEMO_PASSWORD%
py -3 run.py || python run.py
