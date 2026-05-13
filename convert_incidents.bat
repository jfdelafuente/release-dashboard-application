@echo off
REM Script para convertir CSV a JSON en Windows
REM Versión mejorada con mejor manejo de argumentos
REM Uso: convert_incidents.bat archivo.csv [opciones]

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
    echo [INFO] Uso: convert_incidents.bat archivo.csv [opciones]
    echo.
    echo Ejemplos:
    echo   convert_incidents.bat incidencias/datos.csv
    echo   convert_incidents.bat "incidencias/archivo con espacios.csv"
    echo   convert_incidents.bat incidencias/ -o output/
    echo   convert_incidents.bat datos.csv --help
    echo.
    exit /b 1
)

REM Banner
echo.
echo %GREEN%======================================================================%RESET%
echo %GREEN%    CSV to JSON Converter - Dashboard de Incidencias Masivas%RESET%
echo %GREEN%======================================================================%RESET%
echo.

REM Ejecutar script Python
REM IMPORTANTE: Usar "" para que Python interprete los argumentos correctamente
python convert_incidents.py %*

REM Guardar el código de salida
set EXITCODE=!ERRORLEVEL!

REM Salir con el mismo código que Python
exit /b !EXITCODE!
