#!/bin/bash

#####################################################################
# Script: deploy.sh
# Propósito: Despliegue automatizado y seguro en el servidor VPS
# Características:
#   - Backup previo de configuración Nginx y datos locales
#   - Git stash automático si hay cambios locales no commiteados
#   - Pull seguro de la rama production
#   - Detección inteligente de cambios en nginx.conf
#   - Validación sintáctica (nginx -t) antes de recargar
#   - Rollback automático de Nginx si nginx -t falla
#   - Recarga en caliente con 'nginx -s reload' (sin sudo/systemctl)
#   - Verificación de salud (smoke tests) a los dashboards y proxy
#   - Rotación y limpieza de backups antiguos
#
# Uso:
#   ./deploy.sh
#   o desde la carpeta scripts:
#   ./scripts/deploy.sh
#####################################################################

set -e

# Colores para salida interactiva
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Determinar la raíz del proyecto dinámicamente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/../nginx.conf" ]; then
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
    PROJECT_ROOT="/infocodes/project/release-dashboard-application"
fi

BRANCH="production"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${PROJECT_ROOT}/backups/deploy-${TIMESTAMP}"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/deploy-$(date +%Y%m%d).log"

NGINX_CONF_REPO="${PROJECT_ROOT}/nginx.conf"
NGINX_CONF_ACTIVE="/infocodes/nginx/conf/nginx.conf"
NGINX_PID_FILE="/infocodes/var/run/nginx.pid"

mkdir -p "${LOG_DIR}"
mkdir -p "${PROJECT_ROOT}/backups"

# Función de log tanto a consola como a archivo
log() {
    local LEVEL="$1"
    local MSG="$2"
    local TIME
    TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${TIME} [${LEVEL}] ${MSG}" >> "${LOG_FILE}"
}

info() {
    echo -e "${CYAN}ℹ ${NC}$1"
    log "INFO" "$1"
}

success() {
    echo -e "${GREEN}✔ ${BOLD}$1${NC}"
    log "SUCCESS" "$1"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARN" "$1"
}

error() {
    echo -e "${RED}✖ ${BOLD}$1${NC}"
    log "ERROR" "$1"
}

echo -e "\n${BOLD}======================================================${NC}"
echo -e "${BOLD} 🚀 Despliegue Release Dashboard Application${NC}"
echo -e "${BOLD}======================================================${NC}"
info "Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
info "Directorio: ${PROJECT_ROOT}"
info "Rama destino: ${BRANCH}"

cd "${PROJECT_ROOT}" || {
    error "No se pudo acceder a ${PROJECT_ROOT}"
    exit 1
}

OLD_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
info "Commit actual: ${OLD_COMMIT}"

# -------------------------------------------------------------------
# 1. Backup de seguridad antes de modificar nada
# -------------------------------------------------------------------
echo -e "\n${CYAN}${BOLD}[1/5] Realizando copia de seguridad preventiva...${NC}"
mkdir -p "${BACKUP_DIR}"

# Backup de datos locales generados
if [ -d "${PROJECT_ROOT}/data/output" ]; then
    cp -r "${PROJECT_ROOT}/data/output" "${BACKUP_DIR}/data_output" 2>/dev/null || true
    info "Backup de data/output guardado en ${BACKUP_DIR}/data_output"
fi

# Backup de la configuración activa de Nginx
if [ -f "${NGINX_CONF_ACTIVE}" ]; then
    cp "${NGINX_CONF_ACTIVE}" "${BACKUP_DIR}/nginx.conf.active.bak"
    info "Backup de Nginx activo guardado en ${BACKUP_DIR}/nginx.conf.active.bak"
fi

echo "${OLD_COMMIT}" > "${BACKUP_DIR}/commit_hash.txt"
success "Backup preventivo completado en: ${BACKUP_DIR}"

# -------------------------------------------------------------------
# 2. Gestión de cambios locales en git y pull de production
# -------------------------------------------------------------------
echo -e "\n${CYAN}${BOLD}[2/5] Actualizando repositorio git desde origin/${BRANCH}...${NC}"

HAS_CHANGES=false
if ! git diff-index --quiet HEAD -- 2>/dev/null || [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    HAS_CHANGES=true
    warn "Detectados cambios locales pendientes. Creando stash automático..."
    git stash push -m "Auto-stash deploy ${TIMESTAMP}" >> "${LOG_FILE}" 2>&1
    info "Stash realizado con éxito."
fi

info "Haciendo fetch de origin..."
git fetch origin "${BRANCH}" >> "${LOG_FILE}" 2>&1

info "Haciendo pull de la rama ${BRANCH}..."
if ! git pull origin "${BRANCH}" >> "${LOG_FILE}" 2>&1; then
    error "Error al ejecutar git pull origin ${BRANCH}"
    if [ "${HAS_CHANGES}" = true ]; then
        warn "Restaurando stash..."
        git stash pop >> "${LOG_FILE}" 2>&1 || true
    fi
    exit 1
fi

if [ "${HAS_CHANGES}" = true ]; then
    info "Restaurando cambios locales guardados en stash..."
    if git stash pop >> "${LOG_FILE}" 2>&1; then
        success "Cambios locales restaurados sin conflictos."
    else
        warn "Aviso: hubo diferencias al restaurar stash; tus ficheros en data/output se mantienen."
    fi
fi

NEW_COMMIT="$(git rev-parse --short HEAD)"
success "Repositorio actualizado: ${OLD_COMMIT} ➔ ${NEW_COMMIT}"

# -------------------------------------------------------------------
# 3. Sincronización y recarga de Nginx
# -------------------------------------------------------------------
echo -e "\n${CYAN}${BOLD}[3/5] Verificando configuración de Nginx...${NC}"

NGINX_CHANGED=false
if [ -f "${NGINX_CONF_REPO}" ] && [ -f "${NGINX_CONF_ACTIVE}" ]; then
    if ! cmp -s "${NGINX_CONF_REPO}" "${NGINX_CONF_ACTIVE}"; then
        NGINX_CHANGED=true
    fi
elif [ -f "${NGINX_CONF_REPO}" ]; then
    NGINX_CHANGED=true
fi

if [ "${NGINX_CHANGED}" = true ]; then
    info "Se detectaron cambios en nginx.conf. Sincronizando con ${NGINX_CONF_ACTIVE}..."
    cp "${NGINX_CONF_REPO}" "${NGINX_CONF_ACTIVE}"
    
    info "Validando sintaxis de Nginx (nginx -t)..."
    if nginx -t >> "${LOG_FILE}" 2>&1; then
        success "Sintaxis de Nginx válida."
        info "Recargando Nginx en caliente (nginx -s reload)..."
        
        RELOAD_OK=false
        if nginx -s reload >> "${LOG_FILE}" 2>&1; then
            RELOAD_OK=true
        elif [ -f "${NGINX_PID_FILE}" ]; then
            warn "nginx -s reload no respondió directamente; intentando señal HUP al PID..."
            kill -HUP "$(cat "${NGINX_PID_FILE}")" >> "${LOG_FILE}" 2>&1 && RELOAD_OK=true
        fi
        
        if [ "${RELOAD_OK}" = true ]; then
            success "Nginx recargado correctamente con la nueva configuración."
        else
            error "No se pudo recargar Nginx. Revisa logs en ${LOG_FILE}"
        fi
    else
        error "¡ERROR DE SINTAXIS en Nginx! Ejecutando rollback automático de nginx.conf..."
        if [ -f "${BACKUP_DIR}/nginx.conf.active.bak" ]; then
            cp "${BACKUP_DIR}/nginx.conf.active.bak" "${NGINX_CONF_ACTIVE}"
            warn "Restaurada la versión previa de nginx.conf."
            nginx -t >> "${LOG_FILE}" 2>&1 || true
        fi
        exit 1
    fi
else
    success "nginx.conf no presenta cambios. No es necesario recargar Nginx."
fi

# -------------------------------------------------------------------
# 4. Verificación de salud (Smoke Tests)
# -------------------------------------------------------------------
echo -e "\n${CYAN}${BOLD}[4/5] Ejecutando pruebas de verificación (Smoke Tests)...${NC}"

# Test 1: Portal de Dashboards
PORTAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8081/dashboards/portal/" 2>/dev/null || echo "000")
if [ "${PORTAL_HTTP}" = "200" ]; then
    success "Portal (/dashboards/portal/): HTTP 200 OK"
else
    warn "Portal (/dashboards/portal/): HTTP ${PORTAL_HTTP}"
fi

# Test 2: Proxy API Epsilon
EPSILON_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8081/api/epsilon/resumenIA/INC000004141215" 2>/dev/null || echo "000")
if [ "${EPSILON_HTTP}" = "200" ]; then
    success "Proxy Epsilon IA (/api/epsilon/resumenIA/...): HTTP 200 OK"
elif [ "${EPSILON_HTTP}" = "404" ]; then
    error "Proxy Epsilon IA (/api/epsilon/...): HTTP 404 Not Found (revisa /infocodes/nginx/conf/nginx.conf)"
else
    warn "Proxy Epsilon IA (/api/epsilon/...): HTTP ${EPSILON_HTTP}"
fi

# -------------------------------------------------------------------
# 5. Rotación de backups antiguos (mantiene los últimos 5)
# -------------------------------------------------------------------
echo -e "\n${CYAN}${BOLD}[5/5] Mantenimiento y rotación de copias de seguridad...${NC}"
BACKUP_COUNT=$(find "${PROJECT_ROOT}/backups" -mindepth 1 -maxdepth 1 -type d -name "deploy-*" | wc -l)
if [ "${BACKUP_COUNT}" -gt 5 ]; then
    find "${PROJECT_ROOT}/backups" -mindepth 1 -maxdepth 1 -type d -name "deploy-*" | sort | head -n -5 | while read -r OLD_BACKUP; do
        info "Eliminando backup antiguo: $(basename "${OLD_BACKUP}")"
        rm -rf "${OLD_BACKUP}"
    done
fi
success "Copias de seguridad al día (conservadas las últimas 5)."

# -------------------------------------------------------------------
# Resumen final
# -------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD} ✨ ¡Despliegue completado con éxito!${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e " Commit desplegado: ${BOLD}${NEW_COMMIT}${NC}"
echo -e " Backup generado:   ${BACKUP_DIR}"
echo -e " Log de ejecución:  ${LOG_FILE}"
echo -e " Portal disponible: http://infocodes.si.orange.es:8081/dashboards/portal/\n"
