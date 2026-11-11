#!/bin/bash
#####################################################################
# Script: sync-remedy-cron.sh
# Propósito: Sincronización periódica incremental de Remedy vía API MonTMC
# Uso: ./sync-remedy-cron.sh [dias]
# Crontab: */15 * * * * bash /infocodes/project/release-dashboard-application/current/scripts/sync-remedy-cron.sh >> /infocodes/var/log/release-dashboard/remedy-sync-cron.log 2>&1
#####################################################################

set -e

PROJECT_ROOT="/infocodes/project/release-dashboard-application"
CURRENT_DIR="${PROJECT_ROOT}/current"

# 1. Localizar converters y CLI de sincronización
if [ -f "${CURRENT_DIR}/converters/cli/sync_montmc_incidents.py" ]; then
    SYNC_CLI="${CURRENT_DIR}/converters/cli/sync_montmc_incidents.py"
elif [ -f "${PROJECT_ROOT}/converters/cli/sync_montmc_incidents.py" ]; then
    SYNC_CLI="${PROJECT_ROOT}/converters/cli/sync_montmc_incidents.py"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SYNC_CLI="$(cd "${SCRIPT_DIR}/../converters/cli" && pwd)/sync_montmc_incidents.py"
fi

if [ ! -f "${SYNC_CLI}" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] No se encontró sync_montmc_incidents.py en ${SYNC_CLI}" >&2
    exit 1
fi

# 2. Localizar ejecutable de Python
if [ -x "/infocodes/venv/bin/python3" ]; then
    PYTHON_CMD="/infocodes/venv/bin/python3"
elif [ -x "/infocodes/project/cso-incident-masivas-report/current/backend/venv/bin/python3" ]; then
    PYTHON_CMD="/infocodes/project/cso-incident-masivas-report/current/backend/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
else
    PYTHON_CMD="python3"
fi

# 3. Directorio de logs
LOG_DIR="/infocodes/var/log/release-dashboard"
mkdir -p "${LOG_DIR}"

DIAS="${1:-3}"

echo "======================================================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CRON] Iniciando sincronización Remedy API (ventana: ${DIAS} días)..."
echo "  CLI    : ${SYNC_CLI}"
echo "  Python : ${PYTHON_CMD}"

"${PYTHON_CMD}" "${SYNC_CLI}" --dias "${DIAS}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CRON] Sincronización completada con éxito."
echo "======================================================================"
