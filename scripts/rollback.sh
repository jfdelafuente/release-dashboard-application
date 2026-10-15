#!/bin/bash
# ==============================================================================
# Script: rollback.sh
# Propósito: Reversión automática a la copia de seguridad previa de Release Dashboard
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../nginx.conf" ]; then
    APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    APP_DIR="/infocodes/project/release-dashboard-application"
fi

BACKUP_DIR="/infocodes/var/backups/release-dashboard-application"
TARGET_BACKUP="$1"

echo "================================================================="
echo "   ↺ Rollback de Release Dashboard Application"
echo "   Destino : $APP_DIR"
echo "================================================================="

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Directorio de backups no encontrado: $BACKUP_DIR"
    exit 1
fi

if [ -n "$TARGET_BACKUP" ] && [ -f "$TARGET_BACKUP" ]; then
    BACKUP_FILE="$TARGET_BACKUP"
elif [ -n "$TARGET_BACKUP" ] && [ -f "$BACKUP_DIR/$TARGET_BACKUP" ]; then
    BACKUP_FILE="$BACKUP_DIR/$TARGET_BACKUP"
else
    BACKUP_FILE=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.tar.gz" -type f | sort | tail -n 1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: No se encontró ninguna copia de seguridad disponible en $BACKUP_DIR"
    exit 1
fi

echo "--> Restaurando desde copia: $(basename "$BACKUP_FILE")..."
tar -xzf "$BACKUP_FILE" -C "$APP_DIR"

# Sincronizar y recargar Nginx si procede
if [ -f "$APP_DIR/nginx.conf" ]; then
    cp -f "$APP_DIR/nginx.conf" "/infocodes/nginx/conf/nginx.conf"
    if /infocodes/nginx/sbin/nginx -t >/dev/null 2>&1; then
        /infocodes/nginx/sbin/nginx -s reload
        echo "--> Nginx recargado correctamente."
    fi
fi

echo "--> Rollback completado con éxito."
echo ""
if [ -x "$SCRIPT_DIR/status.sh" ]; then
    "$SCRIPT_DIR/status.sh"
fi

