@echo off
setlocal enabledelayedexpansion
title Configuracion de Entorno - Convertidor Universal
cd /d "%~dp0"

echo =========================================================
echo    CONFIGURACION DEL ENTORNO - CONVERTIDOR UNIVERSAL
echo =========================================================
echo.

:: 1. Verificar si Python esta instalado
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] No se encontro Python en el sistema.
    echo Por favor instala Python 3.10 o superior desde https://www.python.org/
    echo y asegurate de marcar "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [INFO] Python detectado: %PYTHON_VER%

:: 2. Crear entorno virtual si no existe
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creando entorno virtual en .venv...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Fallo al crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado exitosamente.
) else (
    echo [INFO] Entorno virtual existente detectado en .venv.
)

:: 3. Activar entorno virtual
echo [INFO] Activando entorno virtual...
call .venv\Scripts\activate.bat

:: 4. Actualizar pip
echo [INFO] Verificando pip...
python -m pip install --upgrade pip --quiet

:: 5. Instalar dependencias principales
if exist "requirements.txt" (
    echo [INFO] Instalando dependencias de requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ADVERTENCIA] Algunas dependencias tuvieron problemas durante la instalacion.
    ) else (
        echo [OK] Dependencias principales instaladas correctamente.
    )
)

:: 6. Instalar dependencias de desarrollo/pruebas si existen
if exist "dev-requirements.txt" (
    echo [INFO] Instalando dependencias de pruebas (dev-requirements.txt)...
    pip install -r dev-requirements.txt --quiet
)

echo.
echo =========================================================
echo    [EXITO] Entorno configurado correctamente.
echo    Puedes iniciar la aplicacion de escritorio con: iniciar.bat
echo    O la aplicacion web con: iniciar_web.bat
echo =========================================================
echo.
if "%1" neq "--no-pause" pause
