@echo off
title Convertidor Universal de Archivos (Escritorio)
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

:: Iniciar la aplicacion de escritorio
echo Iniciando interfaz de escritorio...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrio un error al ejecutar la aplicacion.
    pause
)
