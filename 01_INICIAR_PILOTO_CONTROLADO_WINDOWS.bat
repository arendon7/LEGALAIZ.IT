@echo off
cd /d "%~dp0"
title LegalAIZ.it 5.0.7 - M31.8 Piloto local controlado
cls
echo LegalAIZ.it 5.0.7 - M31.8 Piloto local controlado
echo Use unicamente casos ficticios o anonimizados.
where py >nul 2>nul
if errorlevel 1 goto nopy
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
set /p ADMIN_EMAIL=Correo del administrador: 
set /p ADMIN_NAME=Nombre del administrador [Administrador LegalAIZ.it]: 
if "%ADMIN_NAME%"=="" set ADMIN_NAME=Administrador LegalAIZ.it
set /p ADMIN_PASSWORD=Contrasena del administrador (minimo 12 caracteres): 
if "%ADMIN_PASSWORD%"=="" goto error
if not exist runtime\pilot\secrets mkdir runtime\pilot\secrets
if not exist runtime\pilot\secrets\conflict.key %PYTHON% -c "import secrets; print(secrets.token_urlsafe(48))" > runtime\pilot\secrets\conflict.key
set /p LEGAL_CONFLICT_HASH_KEY=<runtime\pilot\secrets\conflict.key
set LEGAL_PROFILE=local
set LEGAL_APP_ENV=pilot-local
set LEGAL_RUNTIME_DIR=%CD%\runtime\pilot
set LEGAL_ALLOW_DEMO_ACCOUNTS=false
set LEGAL_REQUIRE_MFA_ROLES=admin,specialist
set LEGAL_BOOTSTRAP_ADMIN_EMAIL=%ADMIN_EMAIL%
set LEGAL_BOOTSTRAP_ADMIN_PASSWORD=%ADMIN_PASSWORD%
set LEGAL_BOOTSTRAP_ADMIN_NAME=%ADMIN_NAME%
set LEGAL_BOOTSTRAP_ADMIN_SPECIALTY=Gobernanza juridica y producto
%PYTHON% run.py 8766
if errorlevel 1 pause
exit /b %errorlevel%
:nopy
echo Instale Python 3.9.2 o superior y active Add Python to PATH.
pause
exit /b 1
:error
echo No fue posible preparar el piloto.
pause
exit /b 1
