#!/bin/bash
# ==============================================================================
# Script: deploy.sh (DEPRECADO en VPS)
# ==============================================================================
# El despliegue se realiza ahora mediante empaquetado selectivo desde la máquina
# de desarrollo (sin git pull en el VPS):
#
#   powershell: .\scripts\deploy-production.ps1
#
# ==============================================================================

echo "================================================================="
echo " ℹ Despliegue de Release Dashboard Application"
echo "================================================================="
echo "El despliegue en producción se realiza ahora de forma automatizada"
echo "y segura desde tu máquina local mediante:"
echo ""
echo "   .\\scripts\\deploy-production.ps1"
echo ""
echo "Herramientas disponibles en este servidor:"
echo "   ./status.sh    - Comprobar estado de Nginx y sondas HTTP"
echo "   ./rollback.sh  - Revertir a la copia de seguridad anterior"
echo "================================================================="

# Si se invoca interactivamente, mostrar el estado actual
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SCRIPT_DIR/status.sh" ]; then
    echo ""
    "$SCRIPT_DIR/status.sh"
elif [ -x "$SCRIPT_DIR/../status.sh" ]; then
    echo ""
    "$SCRIPT_DIR/../status.sh"
fi
