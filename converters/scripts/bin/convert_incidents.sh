#!/bin/bash
# Script para convertir CSV a JSON en Linux/Mac
# Uso: ./convert_incidents.sh archivo.csv [opciones]

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[Error] Python 3 no encontrado. Por favor instala Python 3.6+${NC}"
    exit 1
fi

# Mostrar banner
echo ""
echo -e "${BOLD}${GREEN}=====================================================================${NC}"
echo -e "${BOLD}${GREEN}    CSV to JSON Converter - Dashboard de Incidencias Masivas${NC}"
echo -e "${BOLD}${GREEN}=====================================================================${NC}"
echo ""

# Procesar argumentos
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}[Info] Uso: ./convert_incidents.sh archivo.csv [opciones]${NC}"
    echo ""
    echo "Ejemplos:"
    echo "  ./convert_incidents.sh data/input/datos.csv"
    echo "  ./convert_incidents.sh data/input/ -o data/output/"
    echo "  ./convert_incidents.sh data/input/datos.csv --help"
    echo ""
    exit 1
fi

# Ejecutar script Python desde nueva ubicación cli/convert_incidents.py con argumentos
# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONVERTERS_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

python3 "$CONVERTERS_DIR/cli/convert_incidents.py" "$@"
exit $?
