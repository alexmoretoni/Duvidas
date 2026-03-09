@echo off
REM ============================================================
REM start.bat — Inicia o servidor no Windows
REM ============================================================

set VENV_DIR=.venv
set PORT=8000
set HOST=0.0.0.0

echo.
echo === Trending Article Recommender ===
echo.

REM Verifica se o venv existe
if not exist "%VENV_DIR%" (
    echo Ambiente virtual nao encontrado. Criando...
    python -m venv %VENV_DIR%
    %VENV_DIR%\Scripts\pip install --upgrade pip -q
    %VENV_DIR%\Scripts\pip install -r requirements.txt -q
    copy .env.example .env >nul 2>&1
    echo [OK] Instalacao concluida
)

if not exist ".env" (
    copy .env.example .env >nul 2>&1
)

echo Iniciando servidor em http://%HOST%:%PORT%
echo Documentacao: http://localhost:%PORT%/docs
echo.

%VENV_DIR%\Scripts\python cli.py serve --host %HOST% --port %PORT%
pause
