# Script para limpiar archivos CSV y JSON de directorios de datos
# Uso: .\clean-data.ps1

Write-Host "🧹 Iniciando limpieza de datos..." -ForegroundColor Cyan
Write-Host ""

# Directories to clean
$dirs = @(
    "data/input",
    "data/output",
    "data/errors",
    "backend/temp_uploads"
)

# Function to clean directory
function Clean-Directory {
    param([string]$dir)

    if (Test-Path $dir) {
        Write-Host -NoNewline "Limpiando $dir... "

        # Get files before cleanup
        $csvFiles = Get-ChildItem -Path $dir -Filter "*.csv" -File -ErrorAction SilentlyContinue
        $jsonFiles = Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue

        $totalRemoved = 0

        # Remove CSV files
        foreach ($file in $csvFiles) {
            Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
            $totalRemoved++
        }

        # Remove JSON files
        foreach ($file in $jsonFiles) {
            Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
            $totalRemoved++
        }

        if ($totalRemoved -gt 0) {
            Write-Host "✓ Eliminados $totalRemoved archivo(s)" -ForegroundColor Green
        } else {
            Write-Host "✓ Ya está vacío" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠ No existe el directorio: $dir" -ForegroundColor Yellow
    }
}

# Clean each directory
foreach ($dir in $dirs) {
    Clean-Directory $dir
}

Write-Host ""
Write-Host "✅ Limpieza completada" -ForegroundColor Green
Write-Host ""
Write-Host "Resumen de directorios:" -ForegroundColor Cyan

foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        $csvCount = (Get-ChildItem -Path $dir -Filter "*.csv" -File -ErrorAction SilentlyContinue | Measure-Object).Count
        $jsonCount = (Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue | Measure-Object).Count
        $totalCount = (Get-ChildItem -Path $dir -File -ErrorAction SilentlyContinue | Measure-Object).Count

        Write-Host "  $dir`: $totalCount archivo(s) total (CSV: $csvCount, JSON: $jsonCount)"
    }
}

Write-Host ""
Write-Host "🚀 Ambiente limpio y listo para pruebas" -ForegroundColor Green
