@echo off
title Pruebas Automatizadas - Convertidor Universal
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo =========================================================
echo    EJECUTANDO PRUEBAS DE CONVERSION
echo =========================================================
echo.

python -m pytest test_converters.py -v -s
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ADVERTENCIA] Algunas pruebas fallaron o arrojaron advertencias.
) else (
    echo.
    echo [OK] Todas las pruebas pasaron satisfactoriamente.
)

echo.
pause
