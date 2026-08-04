@echo off
cd /d "%~dp0"
title LegalAIZ.it 5.0.7 - M31.8 Demo documental integral
cls
echo LegalAIZ.it 5.0.7 - M31.8 Demo documental integral
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.9.2 o superior y active Add Python to PATH.
  pause
  exit /b 1
)
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,9,2) else 1)" >nul 2>nul
if errorlevel 1 (
  echo LegalAIZ.it requiere Python 3.9.2 o superior.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto error
set PYTHON=.venv\Scripts\python.exe
%PYTHON% -c "import cryptography, reportlab, docx, pypdf" >nul 2>nul
if errorlevel 1 (
  %PYTHON% -m pip install --disable-pip-version-check --upgrade pip
  if errorlevel 1 goto error
  %PYTHON% -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto error
)
set LEGAL_PROFILE=local
set LEGAL_APP_ENV=demo
set LEGAL_RUNTIME_DIR=%CD%\runtime\demo
set LEGAL_ALLOW_DEMO_ACCOUNTS=true
set LEGAL_DEMO_PASSWORD=LegalAIZDemo2026!
set LEGAL_REQUIRE_MFA_ROLES=
echo Usuario: ana@demo.legalaiz.it
echo Clave: LegalAIZDemo2026!
echo Abriendo http://127.0.0.1:8765
%PYTHON% run.py 8765
if errorlevel 1 pause
exit /b %errorlevel%
:error
echo No fue posible preparar la aplicacion.
pause
exit /b 1
