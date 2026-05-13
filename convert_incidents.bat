@echo off
REM Script para convertir CSV a JSON en Windows
REM Uso: convert_incidents.bat archivo.csv [opciones]

setlocal enabledelayedexpansion

REM Colores
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo !RED![Error] Python no encontrado. Instala Python 3.6+ desde python.org!RESET!
    exit /b 1
)

REM Mostrar banner
echo.
echo !GREEN!======================================================================!RESET!
echo !GREEN!    CSV to JSON Converter - Dashboard de Incidencias Masivas!RESET!
echo !GREEN!======================================================================!RESET!
echo.

REM Procesar argumentos
if "%1"=="" (
    echo !YELLOW![Info] Uso: convert_incidents.bat archivo.csv [opciones]!RESET!
    echo.
    echo Ejemplos:
    echo   convert_incidents.bat incidencias/datos.csv
    echo   convert_incidents.bat incidencias/ -o output/
    echo   convert_incidents.bat datos.csv --help
    echo.
    exit /b 1
)

REM Ejecutar script Python con argumentos
python convert_incidents.py %*
set EXITCODE=!ERRORLEVEL!

exit /b !EXITCODE!
