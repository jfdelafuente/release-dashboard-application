#!/bin/bash
# Wrapper directo para lanzar el script de despliegue desde la raíz del proyecto
exec "$(dirname "$0")/scripts/deploy.sh" "$@"
