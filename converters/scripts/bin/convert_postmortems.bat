@echo off
REM Script para convertir CSV de postmortems a JSON en Windows
REM Versión mejorada con mejor manejo de argumentos
REM Uso: convert_postmortems.bat archivo.csv [opciones]

setlocal enabledelayedexpansion

REM Colores ANSI (solo funcionan en Windows 10+)
set "GREEN=[92m"
set "RESET=[0m"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.6+ desde python.org
    exit /b 1
)

REM Si no hay argumentos, mostrar ayuda
if "%1"=="" (
    echo.
    echo [INFO] Uso: convert_postmortems.bat archivo.csv [opciones]
    echo.
    echo Ejemplos:
    echo   convert_postmortems.bat data/input/postmortem.csv
    echo   convert_postmortems.bat "data/input/archivo con espacios.csv"
    echo   convert_postmortems.bat data/input/ -o data/output/
    echo   convert_postmortems.bat data/input/postmortem.csv --help
    echo.
    exit /b 1
)

REM Banner
echo.
echo %GREEN%======================================================================%RESET%
echo %GREEN%    CSV to JSON Converter - Dashboard de Postmortems%RESET%
echo %GREEN%======================================================================%RESET%
echo.

REM Obtener directorio del script batch
set SCRIPT_DIR=%~dp0
REM Navegar hacia arriba dos niveles (bin -> scripts -> converters)
for %%A in ("%SCRIPT_DIR%..") do set SCRIPTS_DIR=%%~dpA
for %%A in ("%SCRIPTS_DIR%..") do set CONVERTERS_DIR=%%~dpA

REM Ejecutar script Python desde nueva ubicación cli/convert_postmortems.py
REM IMPORTANTE: Usar "" para que Python interprete los argumentos correctamente
python "%CONVERTERS_DIR%cli\convert_postmortems.py" %*

REM Guardar el código de salida
set EXITCODE=!ERRORLEVEL!

REM Salir con el mismo código que Python
exit /b !EXITCODE!
