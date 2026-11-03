@echo off
setlocal
cd /d "%~dp0"
python scripts\clean_system_data.py %*
endlocal

