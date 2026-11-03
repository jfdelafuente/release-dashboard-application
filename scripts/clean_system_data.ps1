<#
.SYNOPSIS
    Script de limpieza y reseteo de datos en Release Dashboard Application.
.DESCRIPTION
    Ejecuta el script python scripts/clean_system_data.py pasando todos los argumentos.
.EXAMPLE
    .\scripts\clean_system_data.ps1 -dry-run
    .\scripts\clean_system_data.ps1 -yes
#>
param(
    [switch]$Yes,
    [switch]$DryRun,
    [switch]$KeepCache,
    [string]$StorageDir
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir "clean_system_data.py"

$argsList = @()
if ($Yes) { $argsList += "--yes" }
if ($DryRun) { $argsList += "--dry-run" }
if ($KeepCache) { $argsList += "--keep-cache" }
if ($StorageDir) { $argsList += "--storage-dir"; $argsList += $StorageDir }

python $pythonScript @argsList

