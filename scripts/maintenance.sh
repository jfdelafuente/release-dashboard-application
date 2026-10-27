#!/bin/bash
# ==============================================================================
# Script: maintenance.sh
# Propósito: Mantenimiento, rotación copy-truncate y purga de logs de Release Dashboard
# Uso: ./scripts/maintenance.sh {rotate-logs|clean|status} [--force] [--retention-days N]
#
# Comandos:
#   rotate-logs  : Rota dashboards-cron.log (copy-truncate) y purga logs antiguos (>30d).
#   clean        : Purga logs antiguos (>30d) y comprime los de >7d sin rotar cron.log.
#   status       : Muestra estado del almacenamiento de logs, uso de disco y ficheros.
#
# Crontab sugerido (semanal):
#   15 2 * * 6 bash /infocodes/project/release-dashboard-application/current/scripts/maintenance.sh rotate-logs >> /infocodes/var/log/release-dashboard/maintenance.log 2>&1
# ==============================================================================

set -u

# Localización de directorios base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/releases" ] || [ -L "$SCRIPT_DIR/current" ]; then
    APP_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../nginx.conf" ]; then
    APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    APP_DIR="/infocodes/project/release-dashboard-application"
fi

# Resolución de LOG_DIR desacoplado persistente
if [ -d "/infocodes/var/log/release-dashboard" ]; then
    LOG_DIR="/infocodes/var/log/release-dashboard"
elif [ -d "$APP_DIR/shared/logs" ]; then
    LOG_DIR="$APP_DIR/shared/logs"
elif [ -d "$APP_DIR/logs" ]; then
    LOG_DIR="$APP_DIR/logs"
else
    LOG_DIR="${SCRIPT_DIR}/logs"
fi

# Parámetros y umbrales por defecto (modificables por entorno)
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPRESS_DAYS="${COMPRESS_DAYS:-7}"
CRON_LOG_RETENTION="${CRON_LOG_RETENTION:-4}"
CRON_LOG_MIN_BYTES="${CRON_LOG_MIN_BYTES:-102400}" # 100 KB mínimo para rotar salvo --force
DISK_WARN_PCT=80
DISK_FAIL_PCT=90

CRON_LOG_FILE="${LOG_DIR}/dashboards-cron.log"

# Funciones de logging en consola / stdout
log_info()    { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]    $*"; }
log_success() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $*"; }
log_warn()    { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]    $*"; }
log_error()   { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]   $*"; }

file_size() {
    stat -c%s "$1" 2>/dev/null || echo 0
}

# Procesar argumentos de línea de comandos
ACTION="${1:-status}"
shift || true

FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --force|-f)
            FORCE=1
            shift
            ;;
        --retention-days|-r)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --compress-days|-c)
            COMPRESS_DAYS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

ensure_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi
}

# ------------------------------------------------------------------------------
# 1. Rotación segura de dashboards-cron.log (Copy-Truncate)
# ------------------------------------------------------------------------------
rotate_cron_log() {
    ensure_dir

    if [ ! -f "$CRON_LOG_FILE" ]; then
        log_info "No existe ${CRON_LOG_FILE}, nada que rotar para cron"
        return 0
    fi

    local size
    size="$(file_size "$CRON_LOG_FILE")"
    if [ "$FORCE" -eq 0 ] && [ "$size" -lt "$CRON_LOG_MIN_BYTES" ]; then
        log_info "dashboards-cron.log tiene $(du -h "$CRON_LOG_FILE" 2>/dev/null | cut -f1) (por debajo del umbral de ${CRON_LOG_MIN_BYTES} bytes). No se rota."
        return 0
    fi

    log_info "Rotando ${CRON_LOG_FILE} ($(du -h "$CRON_LOG_FILE" 2>/dev/null | cut -f1)) con copy-truncate..."

    # Desplazar rotaciones existentes: .3 -> .4, .2 -> .3, .1 -> .2
    local max_rot=$((CRON_LOG_RETENTION - 1))
    local i
    for ((i = max_rot; i >= 1; i--)); do
        local next=$((i + 1))
        if [ -f "${CRON_LOG_FILE}.${i}.gz" ]; then
            mv -f "${CRON_LOG_FILE}.${i}.gz" "${CRON_LOG_FILE}.${next}.gz"
        elif [ -f "${CRON_LOG_FILE}.${i}" ]; then
            mv -f "${CRON_LOG_FILE}.${i}" "${CRON_LOG_FILE}.${next}"
        fi
    done

    # Copy-truncate del archivo activo
    cp -p "$CRON_LOG_FILE" "${CRON_LOG_FILE}.1"
    : > "$CRON_LOG_FILE"

    # Comprimir la rotación reciente si gzip está disponible
    if command -v gzip >/dev/null 2>&1; then
        gzip -f "${CRON_LOG_FILE}.1"
        log_success "dashboards-cron.log rotado y comprimido a dashboards-cron.log.1.gz"
    else
        log_success "dashboards-cron.log rotado a dashboards-cron.log.1"
    fi

    # Eliminar rotaciones que excedan la retención configurada
    local excess_files
    excess_files=$(ls -1t "${CRON_LOG_FILE}".[0-9]* 2>/dev/null | tail -n +"$((CRON_LOG_RETENTION + 1))" || true)
    if [ -n "$excess_files" ]; then
        echo "$excess_files" | xargs -r rm -f --
        log_info "Eliminadas rotaciones antiguas de cron que superaban el límite de ${CRON_LOG_RETENTION}"
    fi
}

# ------------------------------------------------------------------------------
# 2. Compresión de logs intermedios (> COMPRESS_DAYS)
# ------------------------------------------------------------------------------
compress_old_logs() {
    ensure_dir
    if ! command -v gzip >/dev/null 2>&1; then
        return 0
    fi

    local count=0
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        [ ! -f "$file" ] && continue
        gzip "$file"
        count=$((count + 1))
    done < <(find "$LOG_DIR" -maxdepth 1 -type f \( -name "dashboards-generation-*.log" -o -name "deploy-*.log" \) -mtime "+${COMPRESS_DAYS}" ! -name "*.gz" 2>/dev/null)

    if [ "$count" -gt 0 ]; then
        log_success "Comprimidos con gzip ${count} archivo(s) de log con más de ${COMPRESS_DAYS} días"
    fi
}

# ------------------------------------------------------------------------------
# 3. Purga de logs antiguos por retención (> RETENTION_DAYS)
# ------------------------------------------------------------------------------
purge_expired_logs() {
    ensure_dir

    log_info "Buscando logs diarios anteriores a ${RETENTION_DAYS} días en ${LOG_DIR}..."

    local purged_count=0
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        [ ! -f "$file" ] && continue
        rm -f "$file"
        purged_count=$((purged_count + 1))
    done < <(find "$LOG_DIR" -maxdepth 1 -type f \( -name "dashboards-generation-*.log*" -o -name "deploy-*.log*" \) -mtime "+${RETENTION_DAYS}" 2>/dev/null)

    if [ "$purged_count" -gt 0 ]; then
        log_success "Purgados ${purged_count} archivo(s) de log con antigüedad superior a ${RETENTION_DAYS} días"
    else
        log_info "No hay archivos de logs diarios que excedan la retención de ${RETENTION_DAYS} días"
    fi
}

# ------------------------------------------------------------------------------
# 4. Chequeo de estado y diagnóstico
# ------------------------------------------------------------------------------
show_status() {
    ensure_dir
    echo "================================================================="
    echo "   📋 Estado de Mantenimiento de Logs - Release Dashboard"
    echo "   Ruta de Logs      : ${LOG_DIR}"
    echo "   Retención diaria  : ${RETENTION_DAYS} días"
    echo "   Rotaciones cron   : ${CRON_LOG_RETENTION} copias"
    echo "================================================================="

    # Uso de disco
    local pct
    pct="$(df -P "$LOG_DIR" 2>/dev/null | awk 'NR==2 { gsub("%","",$(NF-1)); print $(NF-1) }')"
    local avail
    avail="$(df -h "$LOG_DIR" 2>/dev/null | awk 'NR==2 { print $(NF-2) }')"
    if [ -n "$pct" ]; then
        if [ "$pct" -ge "$DISK_FAIL_PCT" ]; then
            log_error "Uso de disco en ${LOG_DIR}: ${pct}% (Espacio libre: ${avail})"
        elif [ "$pct" -ge "$DISK_WARN_PCT" ]; then
            log_warn "Uso de disco en ${LOG_DIR}: ${pct}% (Espacio libre: ${avail})"
        else
            log_success "Uso de disco en ${LOG_DIR}: ${pct}% (Espacio libre: ${avail})"
        fi
    fi

    # Volumen total del directorio de logs
    local total_size
    total_size="$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)"
    echo "Tamaño total ocupado: ${total_size}"
    echo ""

    # Estado de dashboards-cron.log
    if [ -f "$CRON_LOG_FILE" ]; then
        local csize
        csize="$(du -h "$CRON_LOG_FILE" 2>/dev/null | cut -f1)"
        echo "Log cron activo:"
        echo "  - $(basename "$CRON_LOG_FILE") (${csize})"
    else
        echo "Log cron activo: No existe aún"
    fi

    local rotated_cron
    rotated_cron=$(ls -1 "${CRON_LOG_FILE}".[0-9]* 2>/dev/null | wc -l)
    echo "  - Rotaciones conservadas: ${rotated_cron} / ${CRON_LOG_RETENTION}"
    echo ""

    # Conteo de logs de generación y despliegue
    local gen_logs
    gen_logs=$(find "$LOG_DIR" -maxdepth 1 -name "dashboards-generation-*.log*" 2>/dev/null | wc -l)
    local deploy_logs
    deploy_logs=$(find "$LOG_DIR" -maxdepth 1 -name "deploy-*.log*" 2>/dev/null | wc -l)
    local gz_logs
    gz_logs=$(find "$LOG_DIR" -maxdepth 1 -name "*.gz" 2>/dev/null | wc -l)

    echo "Logs diarios y de despliegue:"
    echo "  - Logs de generación (dashboards-generation-*): ${gen_logs}"
    echo "  - Logs de despliegue (deploy-*)              : ${deploy_logs}"
    echo "  - Archivos comprimidos (.gz)                 : ${gz_logs}"

    # Log más antiguo y más reciente
    local oldest
    oldest=$(find "$LOG_DIR" -maxdepth 1 -type f \( -name "dashboards-generation-*.log*" -o -name "deploy-*.log*" \) 2>/dev/null | sort | head -n 1)
    local newest
    newest=$(find "$LOG_DIR" -maxdepth 1 -type f \( -name "dashboards-generation-*.log*" -o -name "deploy-*.log*" \) 2>/dev/null | sort | tail -n 1)
    if [ -n "$oldest" ]; then
        echo "  - Archivo más antiguo: $(basename "$oldest") ($(stat -c%y "$oldest" 2>/dev/null | cut -d' ' -f1))"
    fi
    if [ -n "$newest" ]; then
        echo "  - Archivo más reciente: $(basename "$newest") ($(stat -c%y "$newest" 2>/dev/null | cut -d' ' -f1))"
    fi

    # Aviso sobre log de Nginx si está accesible
    if [ -f "/infocodes/nginx/logs/error.log" ]; then
        local ngx_size
        ngx_size="$(du -h "/infocodes/nginx/logs/error.log" 2>/dev/null | cut -f1)"
        echo ""
        echo "Nota operativa de Nginx:"
        echo "  - /infocodes/nginx/logs/error.log: ${ngx_size}"
    fi

    echo "================================================================="
}

show_help() {
    echo "Uso: $0 {rotate-logs|clean|status|help} [opciones]"
    echo ""
    echo "Comandos:"
    echo "  rotate-logs       Ejecuta rotación copy-truncate de cron.log, comprime y purga logs >${RETENTION_DAYS}d."
    echo "  clean             Comprime logs >${COMPRESS_DAYS}d y purga logs >${RETENTION_DAYS}d sin rotar cron.log."
    echo "  status            Muestra el estado de ocupación, métricas y archivos de log."
    echo "  help              Muestra esta ayuda."
    echo ""
    echo "Opciones:"
    echo "  --force, -f             Fuerza la rotación de cron.log aunque no alcance el tamaño mínimo."
    echo "  --retention-days, -r N  Sobrescribe el periodo de retención en días (por defecto: ${RETENTION_DAYS})."
    echo "  --compress-days, -c N   Sobrescribe el umbral de compresión en días (por defecto: ${COMPRESS_DAYS})."
}

# ------------------------------------------------------------------------------
# Despachador principal
# ------------------------------------------------------------------------------
case "$ACTION" in
    rotate-logs)
        log_info "=== Iniciando mantenimiento de logs: rotación y purga ==="
        rotate_cron_log
        compress_old_logs
        purge_expired_logs
        log_success "=== Mantenimiento completado ==="
        ;;
    clean|purge)
        log_info "=== Iniciando limpieza y purga de logs ==="
        compress_old_logs
        purge_expired_logs
        log_success "=== Limpieza completada ==="
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Acción no reconocida: '$ACTION'"
        show_help
        exit 1
        ;;
esac

exit 0
