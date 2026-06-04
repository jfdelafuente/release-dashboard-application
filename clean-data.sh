#!/bin/bash

##############################################################################
# Script para limpiar archivos CSV y JSON de directorios de datos
# Uso: ./clean-data.sh
##############################################################################

set -e  # Exit on error

echo "🧹 Iniciando limpieza de datos..."
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories to clean
declare -a DIRS=(
    "data/input"
    "data/output"
    "data/errors"
    "backend/temp_uploads"
)

# Function to clean directory
clean_directory() {
    local dir=$1
    local count=0

    if [ -d "$dir" ]; then
        echo -n "Limpiando $dir... "

        # Count files before deletion
        if [ "$(ls -A "$dir" 2>/dev/null)" ]; then
            # Remove CSV files
            find "$dir" -maxdepth 1 -type f \( -name "*.csv" -o -name "*.json" \) -delete 2>/dev/null
            count=$(find "$dir" -maxdepth 1 -type f | wc -l)

            if [ $count -eq 0 ]; then
                echo -e "${GREEN}✓ Limpiado${NC}"
            else
                echo -e "${YELLOW}⚠ Quedan $count archivo(s)${NC}"
            fi
        else
            echo -e "${GREEN}✓ Ya está vacío${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No existe el directorio: $dir${NC}"
    fi
}

# Clean each directory
for dir in "${DIRS[@]}"; do
    clean_directory "$dir"
done

echo ""
echo "✅ Limpieza completada"
echo ""
echo "Resumen de directorios:"
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        file_count=$(find "$dir" -type f | wc -l)
        csv_count=$(find "$dir" -maxdepth 1 -type f -name "*.csv" | wc -l)
        json_count=$(find "$dir" -maxdepth 1 -type f -name "*.json" | wc -l)
        echo "  $dir: $file_count archivo(s) total (CSV: $csv_count, JSON: $json_count)"
    fi
done

echo ""
echo "🚀 Ambiente limpio y listo para pruebas"
