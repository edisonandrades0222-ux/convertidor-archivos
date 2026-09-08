@echo off
setlocal enabledelayedexpansion
title Subir Cambios a GitHub (edisonandrades0222-ux/convertidor-archivos)
cd /d "%~dp0"

echo =========================================================
echo    SUBIENDO PROYECTO A GITHUB: edisonandrades0222-ux
echo =========================================================
echo.

:: 1. Agregar Git al PATH de la sesion
if exist "%LOCALAPPDATA%\Programs\MinGit\cmd\git.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%LOCALAPPDATA%\Programs\MinGit\mingw64\bin;!PATH!"
)

:: 2. Asegurar origen remoto
git remote set-url origin https://github.com/edisonandrades0222-ux/convertidor-archivos.git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    git remote add origin https://github.com/edisonandrades0222-ux/convertidor-archivos.git
)

echo [1/3] Preparando archivos...
git add .

echo [2/3] Verificando commits locales...
git commit -m "Refactor y mejoras: persistencia de descarga, Streamlit Cloud y pruebas" >nul 2>&1

echo [3/3] Subiendo a GitHub (rama main)...
echo.
echo * NOTA: Si se abre una ventana en el navegador, autoriza el acceso a GitHub.
echo.

git branch -M main
git push -u origin main --force

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================================
    echo   [EXITO] Archivos subidos exitosamente a GitHub!
    echo   Streamlit Cloud se actualizara en 1 o 2 minutos en:
    echo   https://convertidor-archivos-wcwowx7ldqebacrjnjbqb4.streamlit.app/
    echo =========================================================
) else (
    echo.
    echo [ERROR] No se pudo completar la subida. Verifica tu conexion o credenciales.
)

echo.
pause
