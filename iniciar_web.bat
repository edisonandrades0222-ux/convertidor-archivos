@echo off
title Servidor Web - Convertidor Universal
cd /d "%~dp0"

:: Verificar si existe el entorno virtual
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Primera ejecucion detectada: configurando entorno virtual...
    call setup_env.bat --no-pause
    echo.
)

:: Activar entorno virtual
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo Iniciando aplicacion web en tu navegador...
python -m streamlit run web_app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrio un error al iniciar Streamlit.
    pause
)
