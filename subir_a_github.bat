@echo off
setlocal enabledelayedexpansion
title Subir Cambios a GitHub
cd /d "%~dp0"

echo =========================================================
echo       SUBIR PROYECTO A GITHUB (STREAMLIT CLOUD)
echo =========================================================
echo.

:: 1. Comprobar si Git esta en el PATH o en la carpeta portable MinGit
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Programs\MinGit\cmd\git.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;!PATH!"
    ) else (
        echo [ERROR] No se encontro Git instalado.
        pause
        exit /b 1
    )
)

:: 2. Verificar estado del repositorio
git status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Inicializando repositorio Git...
    git init -b main
)

:: 3. Verificar si ya existe remote origin
git remote get-url origin >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo No hay un repositorio remoto de GitHub configurado.
    echo Por favor introduce la URL de tu repositorio en GitHub
    echo (Ejemplo: https://github.com/TuUsuario/convertidor-archivos.git):
    echo.
    set /p REPO_URL="URL del repositorio: "
    if "!REPO_URL!"=="" (
        echo [ERROR] No introdujiste una URL valida.
        pause
        exit /b 1
    )
    git remote add origin !REPO_URL!
    echo [OK] Repositorio remoto agregado.
) else (
    for /f "tokens=*" %%i in ('git remote get-url origin') do set CURRENT_REMOTE=%%i
    echo [INFO] Repositorio remoto actual: !CURRENT_REMOTE!
)

echo.
echo [1/3] Agregando archivos modificados...
git add .

echo [2/3] Creando commit...
set /p COMMIT_MSG="Mensaje para el commit (presiona ENTER para 'Actualizacion'): "
if "!COMMIT_MSG!"=="" set COMMIT_MSG=Actualizacion
git commit -m "!COMMIT_MSG!"

echo.
echo [3/3] Subiendo a la rama principal (main)...
git branch -M main
git push -u origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ADVERTENCIA] Si el repositorio remoto ya tenia commits previos, es posible que requiera forzar o sincronizar:
    echo Deseas forzar la subida (git push -u origin main --force)? [S/N]
    set /p FORCE_PUSH="Opcion: "
    if /i "!FORCE_PUSH!"=="S" (
        git push -u origin main --force
    )
)

echo.
echo =========================================================
echo [EXITO] Proceso terminado.
echo Tu aplicacion en Streamlit Cloud se actualizara automaticamente en 1-2 minutos.
echo =========================================================
echo.
pause
