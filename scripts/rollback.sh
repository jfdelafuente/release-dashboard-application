#!/bin/bash
# ==============================================================================
# Script: rollback.sh
# Propósito: Reversión atómica por symlink a la release previa de Release Dashboard
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

RELEASES_DIR="$APP_DIR/releases"
CURRENT_LINK="$APP_DIR/current"
BACKUP_DIR="/infocodes/var/backups/release-dashboard-application"
TARGET_RELEASE="$1"

echo "================================================================="
echo "   ↺ Rollback de Release Dashboard Application"
echo "   Destino : $APP_DIR"
echo "================================================================="

cd "$APP_DIR"

# 1. Intentar rollback atómico por symlink en releases/
if [ -d "$RELEASES_DIR" ]; then
    ACTIVE_RELEASE=""
    if [ -L "$CURRENT_LINK" ]; then
        ACTIVE_TARGET="$(readlink "$CURRENT_LINK" 2>/dev/null || true)"
        ACTIVE_RELEASE="$(basename "$ACTIVE_TARGET")"
    fi

    if [ -n "$TARGET_RELEASE" ] && [ -d "$RELEASES_DIR/$TARGET_RELEASE" ]; then
        PREV_RELEASE="$TARGET_RELEASE"
    else
        PREV_RELEASE=""
        for rel in $(ls -1 "$RELEASES_DIR" 2>/dev/null | sort); do
            if [ -d "$RELEASES_DIR/$rel/dashboards" ]; then
                if [ "$rel" != "$ACTIVE_RELEASE" ]; then
                    PREV_RELEASE="$rel"
                fi
            fi
        done
    fi

    if [ -n "$PREV_RELEASE" ] && [ -d "$RELEASES_DIR/$PREV_RELEASE" ]; then
        echo "--> Conmutando symlink atómico hacia releases/$PREV_RELEASE..."
        ln -sfn "releases/$PREV_RELEASE" "$CURRENT_LINK"

        # Compatibilidad en raíz y persistencia desacoplada
        STORAGE_BASE="/infocodes/var/storage/release-dashboard"
        LOGS_BASE="/infocodes/var/log/release-dashboard"
        ln -sfn "$CURRENT_LINK/dashboards" "$APP_DIR/dashboards" 2>/dev/null || true
        ln -sfn "$CURRENT_LINK/converters" "$APP_DIR/converters" 2>/dev/null || true
        ln -sfn "$CURRENT_LINK/scripts" "$APP_DIR/scripts" 2>/dev/null || true
        if [ -d "$STORAGE_BASE" ]; then
            ln -sfn "$STORAGE_BASE" "$APP_DIR/data" 2>/dev/null || true
            ln -sfn "$STORAGE_BASE" "$CURRENT_LINK/data" 2>/dev/null || true
        fi
        if [ -d "$LOGS_BASE" ]; then
            ln -sfn "$LOGS_BASE" "$APP_DIR/logs" 2>/dev/null || true
            ln -sfn "$LOGS_BASE" "$CURRENT_LINK/logs" 2>/dev/null || true
        fi

        # Sincronizar y recargar Nginx si procede
        if [ -f "$CURRENT_LINK/nginx.conf" ]; then
            cp -f "$CURRENT_LINK/nginx.conf" "/infocodes/nginx/conf/nginx.conf"
            if /infocodes/nginx/sbin/nginx -t >/dev/null 2>&1; then
                /infocodes/nginx/sbin/nginx -s reload
                echo "--> Nginx recargado con éxito."
            fi
        fi

        echo "--> Rollback atómico completado con éxito."
        if [ -x "$APP_DIR/status.sh" ]; then
            "$APP_DIR/status.sh"
        fi
        exit 0
    fi
fi

# 2. Fallback: Restauración desde archivo de backup comprimido
if [ -d "$BACKUP_DIR" ]; then
    if [ -n "$TARGET_RELEASE" ] && [ -f "$BACKUP_DIR/$TARGET_RELEASE" ]; then
        BACKUP_FILE="$BACKUP_DIR/$TARGET_RELEASE"
    else
        BACKUP_FILE=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.tar.gz" -type f | sort | tail -n 1)
    fi

    if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
        echo "--> Restaurando desde archivo de backup: $(basename "$BACKUP_FILE")..."
        tar -xzf "$BACKUP_FILE" -C "$APP_DIR"
        if [ -f "$APP_DIR/nginx.conf" ]; then
            cp -f "$APP_DIR/nginx.conf" "/infocodes/nginx/conf/nginx.conf"
            /infocodes/nginx/sbin/nginx -t >/dev/null 2>&1 && /infocodes/nginx/sbin/nginx -s reload 2>/dev/null || true
        fi
        echo "--> Rollback desde backup completado."
        if [ -x "$APP_DIR/status.sh" ]; then
            "$APP_DIR/status.sh"
        fi
        exit 0
    fi
fi

echo "ERROR: No se encontró ninguna release o copia previa para revertir."
exit 1
