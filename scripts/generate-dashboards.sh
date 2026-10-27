#!/bin/bash

#####################################################################
# Script: generate-dashboards.sh
# Propósito: Ejecutar converters CSV->JSON y generar index.json
# Uso: ./generate-dashboards.sh
# Crontab: 0 2 * * * /infocodes/project/release-dashboard-application/scripts/generate-dashboards.sh
#####################################################################

# Configuración y resolución de rutas desacopladas
PROJECT_ROOT="/infocodes/project/release-dashboard-application"

# 1. Localizar converters (priorizar release activa 'current', fallback a raíz)
if [ -d "${PROJECT_ROOT}/current/converters" ]; then
    CONVERTERS_DIR="${PROJECT_ROOT}/current/converters"
elif [ -d "${PROJECT_ROOT}/converters" ]; then
    CONVERTERS_DIR="${PROJECT_ROOT}/converters"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CONVERTERS_DIR="$(cd "${SCRIPT_DIR}/../converters" && pwd)"
fi

# 2. Localizar almacenamiento persistente desacoplado (/infocodes/var/storage/release-dashboard)
if [ -n "${RELEASE_DASHBOARD_STORAGE_DIR}" ] && [ -d "${RELEASE_DASHBOARD_STORAGE_DIR}" ]; then
    STORAGE_DIR="${RELEASE_DASHBOARD_STORAGE_DIR}"
elif [ -d "/infocodes/var/storage/release-dashboard" ]; then
    STORAGE_DIR="/infocodes/var/storage/release-dashboard"
elif [ -d "${PROJECT_ROOT}/data" ]; then
    STORAGE_DIR="${PROJECT_ROOT}/data"
elif [ -d "${PROJECT_ROOT}/shared/data" ]; then
    STORAGE_DIR="${PROJECT_ROOT}/shared/data"
else
    STORAGE_DIR="${PROJECT_ROOT}/data"
fi

DATA_INPUT_DIR="${STORAGE_DIR}/input"
DATA_OUTPUT_DIR="${STORAGE_DIR}/output"
DATA_ERRORS_DIR="${STORAGE_DIR}/errors"

# 3. Localizar directorio de logs
if [ -d "/infocodes/var/log/release-dashboard" ]; then
    LOG_DIR="/infocodes/var/log/release-dashboard"
elif [ -d "${PROJECT_ROOT}/shared/logs" ]; then
    LOG_DIR="${PROJECT_ROOT}/shared/logs"
else
    LOG_DIR="${PROJECT_ROOT}/logs"
fi
LOG_FILE="${LOG_DIR}/dashboards-generation-$(date +%Y%m%d).log"

# Crear directorios necesarios si no existen
mkdir -p "${LOG_DIR}" "${DATA_INPUT_DIR}" "${DATA_OUTPUT_DIR}" "${DATA_ERRORS_DIR}"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=========================================="
log "Iniciando generación de dashboards"
log "=========================================="

# Validar que el proyecto existe
if [ ! -d "${PROJECT_ROOT}" ]; then
    log "ERROR: Directorio del proyecto no encontrado: ${PROJECT_ROOT}"
    exit 1
fi

# Validar que los converters existen
if [ ! -f "${CONVERTERS_DIR}/cli/convert_incidents.py" ]; then
    log "ERROR: convert_incidents.py no encontrado en ${CONVERTERS_DIR}/cli/"
    exit 1
fi

# 4. Localizar ejecutable de Python (priorizar venv o python3)
if [ -x "/infocodes/venv/bin/python3" ]; then
    PYTHON_CMD="/infocodes/venv/bin/python3"
elif [ -x "/infocodes/venv/bin/python" ]; then
    PYTHON_CMD="/infocodes/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python)"
else
    PYTHON_CMD="python3"
fi

if ! "${PYTHON_CMD}" --version >/dev/null 2>&1; then
    log "ERROR: No se encontró un ejecutable de Python funcional: ${PYTHON_CMD}"
    exit 1
fi

# Crear directorios necesarios si no existen
mkdir -p "${DATA_OUTPUT_DIR}"
mkdir -p "${DATA_ERRORS_DIR}"

log "Directorio de proyecto: ${PROJECT_ROOT}"
log "Directorio de entrada: ${DATA_INPUT_DIR}"
log "Directorio de salida: ${DATA_OUTPUT_DIR}"
log "Ejecutable Python: ${PYTHON_CMD} ($("${PYTHON_CMD}" --version 2>&1))"

# Cambiar al directorio del proyecto
cd "${PROJECT_ROOT}" || exit 1

# Contar archivos CSV en input
CSV_COUNT=$(find "${DATA_INPUT_DIR}" -name "*.csv" 2>/dev/null | wc -l)

if [ "${CSV_COUNT}" -eq 0 ]; then
    log "ADVERTENCIA: No hay archivos CSV en ${DATA_INPUT_DIR}"
    log "Saltando procesamiento"
    exit 0
fi

log "Encontrados ${CSV_COUNT} archivo(s) CSV para procesar"

# Seleccionar los CSVs activos más recientes (último masivo global y último postmortem por release)
# Evita redundancia de conversiones y bucles de archivado
selector_script="${CONVERTERS_DIR}/cli/select_active_csvs.py"
if [ -f "${selector_script}" ]; then
    log "Seleccionando archivos CSV activos más recientes..."
    active_files_raw=$("${PYTHON_CMD}" "${selector_script}" "${DATA_INPUT_DIR}" 2>>"${LOG_FILE}")
else
    # Fallback si el selector no estuviese disponible
    active_files_raw=$(find "${DATA_INPUT_DIR}" -name "*.csv" | awk '{print $0 "\tfallback\t"}')
fi

if [ -z "${active_files_raw}" ]; then
    log "ADVERTENCIA: No se seleccionaron archivos CSV para procesar"
    exit 0
fi

# Procesar cada CSV seleccionado
while IFS=$'\t' read -r csv_file csv_type release_name; do
    [ -z "${csv_file}" ] && continue
    [ ! -f "${csv_file}" ] && continue

    filename=$(basename "${csv_file}")
    filename_lower=$(echo "${filename}" | tr '[:upper:]' '[:lower:]')

    if [ "${csv_type}" = "postmortem" ] || [[ "${filename_lower}" == *postmortem* ]] || [[ "${filename_lower}" == *"mesa post"* ]]; then
        converter_script="${CONVERTERS_DIR}/cli/convert_postmortems.py"
        release_arg=()
        if [ -n "${release_name}" ] && [ "${release_name}" != "None" ]; then
            release_arg=("--release-name" "${release_name}")
        fi
        log "Procesando postmortem: ${filename} (release: ${release_name:-'no detectada'})"
        if "${PYTHON_CMD}" "${converter_script}" "${csv_file}" -o "${DATA_OUTPUT_DIR}" "${release_arg[@]}" 2>>"${LOG_FILE}"; then
            log "✓ Conversión exitosa: ${filename}"
        else
            log "✗ Error en conversión de: ${filename}"
        fi
    else
        converter_script="${CONVERTERS_DIR}/cli/convert_incidents.py"
        log "Procesando incidencias: ${filename}"
        if "${PYTHON_CMD}" "${converter_script}" "${csv_file}" -o "${DATA_OUTPUT_DIR}" 2>>"${LOG_FILE}"; then
            log "✓ Conversión exitosa: ${filename}"
        else
            log "✗ Error en conversión de: ${filename}"
        fi
    fi
done <<< "${active_files_raw}"

# Generar index.json
log "Generando index.json..."
if "${PYTHON_CMD}" "${CONVERTERS_DIR}/cli/build_index.py" "${DATA_OUTPUT_DIR}" 2>>"${LOG_FILE}"; then
    log "✓ index.json generado correctamente"

    # Validar que index.json existe y tiene contenido
    if [ -f "${DATA_OUTPUT_DIR}/index.json" ] && [ -s "${DATA_OUTPUT_DIR}/index.json" ]; then
        JSON_SIZE=$(du -h "${DATA_OUTPUT_DIR}/index.json" | cut -f1)
        log "✓ index.json validado (tamaño: ${JSON_SIZE})"
    else
        log "✗ ERROR: index.json no tiene contenido"
        exit 1
    fi
else
    log "✗ ERROR: Fallo al generar index.json"
    exit 1
fi

# Generar notificaciones de alta prioridad (P1/P2)
log "Evaluando notificaciones de alta prioridad..."
eval_script="${CONVERTERS_DIR}/cli/evaluate_incident_notifications.py"
if [ -f "${eval_script}" ]; then
    if "${PYTHON_CMD}" "${eval_script}" --index "${DATA_OUTPUT_DIR}/index.json" --output "${DATA_OUTPUT_DIR}/high_priority_notifications.json" 2>>"${LOG_FILE}"; then
        log "✓ Notificaciones de alta prioridad generadas correctamente"
    else
        log "⚠ Advertencia: Error en la evaluación de notificaciones de alta prioridad"
    fi
else
    log "⚠ Advertencia: evaluate_incident_notifications.py no encontrado en ${CONVERTERS_DIR}/cli/"
fi

# Resumen final
TOTAL_JSON=$(find "${DATA_OUTPUT_DIR}" -name "*.json" | wc -l)
log "=========================================="
log "✓ Proceso completado exitosamente"
log "Total de archivos JSON generados: ${TOTAL_JSON}"
log "Log disponible en: ${LOG_FILE}"
log "=========================================="

exit 0
