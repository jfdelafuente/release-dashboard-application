#!/bin/bash

#####################################################################
# Script: generate-dashboards.sh
# Propósito: Ejecutar converters CSV->JSON y generar index.json
# Uso: ./generate-dashboards.sh
# Crontab: 0 2 * * * /infocodes/release-dashboard-application/scripts/generate-dashboards.sh
#####################################################################

# Configuración - Detectar PROJECT_ROOT dinámicamente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
CONVERTERS_DIR="${PROJECT_ROOT}/converters"
DATA_INPUT_DIR="${PROJECT_ROOT}/data/input"
DATA_OUTPUT_DIR="${PROJECT_ROOT}/data/output"
DATA_ERRORS_DIR="${PROJECT_ROOT}/data/errors"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/dashboards-generation-$(date +%Y%m%d).log"

# Crear directorio de logs si no existe
mkdir -p "${LOG_DIR}"

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

# Crear directorios necesarios si no existen
mkdir -p "${DATA_OUTPUT_DIR}"
mkdir -p "${DATA_ERRORS_DIR}"

log "Directorio de proyecto: ${PROJECT_ROOT}"
log "Directorio de entrada: ${DATA_INPUT_DIR}"
log "Directorio de salida: ${DATA_OUTPUT_DIR}"

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

# Procesar cada CSV encontrado
for csv_file in "${DATA_INPUT_DIR}"/*.csv; do
    if [ -f "${csv_file}" ]; then
        filename=$(basename "${csv_file}")
        log "Procesando: ${filename}"

        # Ejecutar converter de incidencias masivas
        if python "${CONVERTERS_DIR}/cli/convert_incidents.py" "${csv_file}" -o "${DATA_OUTPUT_DIR}" 2>>"${LOG_FILE}"; then
            log "✓ Conversión exitosa: ${filename}"
        else
            log "✗ Error en conversión de: ${filename}"
        fi
    fi
done

# Procesar postmortems si existen
for csv_file in "${DATA_INPUT_DIR}"/*postmortem*.csv; do
    if [ -f "${csv_file}" ]; then
        filename=$(basename "${csv_file}")
        log "Procesando postmortem: ${filename}"

        if python "${CONVERTERS_DIR}/cli/convert_postmortems.py" "${csv_file}" -o "${DATA_OUTPUT_DIR}" 2>>"${LOG_FILE}"; then
            log "✓ Conversión exitosa: ${filename}"
        else
            log "✗ Error en conversión de: ${filename}"
        fi
    fi
done

# Generar index.json
log "Generando index.json..."
if python "${CONVERTERS_DIR}/cli/build_index.py" "${DATA_OUTPUT_DIR}" 2>>"${LOG_FILE}"; then
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

# Resumen final
TOTAL_JSON=$(find "${DATA_OUTPUT_DIR}" -name "*.json" | wc -l)
log "=========================================="
log "✓ Proceso completado exitosamente"
log "Total de archivos JSON generados: ${TOTAL_JSON}"
log "Log disponible en: ${LOG_FILE}"
log "=========================================="

exit 0
