#!/bin/bash
# ==============================================================================
# Script: status.sh
# Propósito: Consulta rápida de estado y sondas de salud de Release Dashboard
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/releases" ] || [ -L "$SCRIPT_DIR/current" ]; then
    APP_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../nginx.conf" ]; then
    APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    APP_DIR="/infocodes/project/release-dashboard-application"
fi

ACTIVE_REL="desconocida"
if [ -L "$APP_DIR/current" ]; then
    ACTIVE_REL="$(readlink "$APP_DIR/current" 2>/dev/null || true)"
fi

VERSION="desconocida"
if [ -f "$APP_DIR/current/VERSION" ]; then
    VERSION="$(cat "$APP_DIR/current/VERSION" 2>/dev/null)"
elif [ -f "$APP_DIR/VERSION" ]; then
    VERSION="$(cat "$APP_DIR/VERSION" 2>/dev/null)"
fi

echo "================================================================="
echo "   Release Dashboard Application - Estado del Servicio"
echo "   Ruta           : $APP_DIR"
echo "   Release Activa : $ACTIVE_REL"
echo "   Versión        : $VERSION"
echo "================================================================="

# Estado de Nginx
echo -n "Proceso Nginx (puerto 8081): "
if /infocodes/nginx/sbin/nginx -t >/dev/null 2>&1; then
    echo "CONFIG OK"
else
    echo "ERROR EN CONFIGURACIÓN"
fi

# Estadísticas de datos persistentes
DATA_DIR=""
if [ -d "$APP_DIR/shared/data" ]; then
    DATA_DIR="$APP_DIR/shared/data"
elif [ -d "$APP_DIR/data" ]; then
    DATA_DIR="$APP_DIR/data"
fi

if [ -n "$DATA_DIR" ]; then
    CSV_COUNT=$(find "$DATA_DIR/input" -name "*.csv" 2>/dev/null | wc -l)
    JSON_COUNT=$(find "$DATA_DIR/output" -name "*.json" 2>/dev/null | wc -l)
    PPTX_COUNT=$(find "$DATA_DIR/reports" -name "*.pptx" 2>/dev/null | wc -l)
    echo "Datos persistentes: $CSV_COUNT CSVs en input | $JSON_COUNT JSONs en output | $PPTX_COUNT informes PPTX"
fi

echo ""
echo "=== Sondas de Salud HTTP (localhost:8081) ==="
check_endpoint() {
    local label="$1"
    local url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --noproxy '*' "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        printf "  %-35s : \033[0;32m%s OK\033[0m\n" "$label" "$code"
    elif [ "$code" = "404" ]; then
        printf "  %-35s : \033[0;31m%s Not Found\033[0m\n" "$label" "$code"
    else
        printf "  %-35s : \033[0;33m%s\033[0m\n" "$label" "$code"
    fi
}

check_endpoint "Portal (/dashboards/portal/)" "http://localhost:8081/dashboards/portal/"
check_endpoint "Incidencias Masivas" "http://localhost:8081/dashboards/massive-incidents/"
check_endpoint "Postmortem" "http://localhost:8081/dashboards/postmortem/"
check_endpoint "Release KPIs" "http://localhost:8081/dashboards/release-kpis/"
check_endpoint "Reportes Incidencias" "http://localhost:8081/dashboards/reportes-incidencias/"
check_endpoint "Proxy API Epsilon" "http://localhost:8081/api/epsilon/resumenIA/INC000004141215"
check_endpoint "Backend CSO Health" "http://localhost:8081/api/health"

echo "================================================================="
