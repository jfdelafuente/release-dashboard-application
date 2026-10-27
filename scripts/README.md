# Scripts de Automatización y Operación

Scripts para el despliegue, operación y conversión de datos de Release Dashboard Application.

---

## ⚡ deploy-production.ps1 (Despliegue en 1 Clic desde Windows)

Script principal de despliegue desde la máquina local Windows a producción (`infocodes@10.132.26.96`).

### Características:
- Regeneración automática del catálogo de agentes IA (`data/output/agents_catalog.json`) desde `biblioteca-agentes`.
- Empaquetado selectivo de runtime en `dist/release-dashboard-runtime.tar.gz` (~2.3 MB).
- Cero `git pull`, `git stash` o clonación en el servidor de producción.
- Protección total del directorio `data/` (persistencia estricta) y sincronización del catálogo.
- Backup preventivo automático con rotación de las últimas 5 copias en `/infocodes/var/backups/release-dashboard-application/`.
- Validación de sintaxis Nginx (`nginx -t`) y recarga suave en caliente (`nginx -s reload`) con rollback automático.
- Ejecución desatendida de sondas de salud HTTP al finalizar.

### Uso:
```powershell
# Despliegue estándar completo (regenera catálogo, valida git, empaqueta y despliega):
.\scripts\deploy-production.ps1

# Despliegue omitiendo la regeneración del catálogo:
.\scripts\deploy-production.ps1 -SkipCatalogBuild

# Solo verificar salud y estado del servidor sin modificar nada:
.\scripts\deploy-production.ps1 -VerifyOnly

# Rollback instantáneo a la copia preventiva anterior:
.\scripts\deploy-production.ps1 -Rollback

# Desplegar sin hacer git push previo:
.\scripts\deploy-production.ps1 -SkipPush

# Simulación sin aplicar cambios (DryRun):
.\scripts\deploy-production.ps1 -DryRun
```

---

## 📊 status.sh (Sondas de Salud en el Servidor)

Script de consulta rápida de estado en el VPS (`/infocodes/project/release-dashboard-application/status.sh`):

### Uso:
```bash
./status.sh
```

### Qué comprueba:
- Versión actual (`VERSION`).
- Sintaxis y estado de configuración de Nginx.
- Conteo de archivos de datos (`data/input/*.csv`, `data/output/*.json`, `data/reports/*.pptx`).
- Códigos HTTP (200 OK) de todos los dashboards y proxies locales.

---

## ↺ rollback.sh (Reversión Inmediata en el Servidor)

Script para restaurar una versión previa desde los backups preventivos (`/infocodes/project/release-dashboard-application/rollback.sh`):

### Uso:
```bash
# Restaurar la copia más reciente:
./rollback.sh

# Restaurar una copia específica:
./rollback.sh backup_20261015_145000.tar.gz
```

---

## 📜 generate-dashboards.sh (Conversión Batch)

Script para procesar CSVs y generar los archivos JSON para los dashboards estáticos.

### Características:
- Procesa todos los CSV en `data/input/`
- Ejecuta converters de incidencias masivas y postmortems
- Genera `index.json`
- Logging detallado en `logs/dashboards-generation-YYYYMMDD.log`

### Uso Manual:
```bash
./scripts/generate-dashboards.sh
```

### Configuración en Crontab (VPS):
```bash
0 * * * * bash /infocodes/project/release-dashboard-application/current/scripts/generate-dashboards.sh >> /infocodes/var/log/release-dashboard/dashboards-cron.log 2>&1
```

---

## 🧹 maintenance.sh (Rotación y Purga de Logs)

Script para el mantenimiento preventivo y depuración de ficheros de registro (`/infocodes/project/release-dashboard-application/maintenance.sh` o `scripts/maintenance.sh`).

### Características:
- **Rotación *Copy-Truncate* de `dashboards-cron.log`**: Desplaza las rotaciones históricas (.1 a .4) y vacía el fichero activo sin interrumpir la ejecución del cron.
- **Compresión automática con gzip**: Comprime logs diarios con más de 7 días de antigüedad (`.gz`).
- **Purga por retención**: Elimina de forma segura los ficheros de log diarios (`dashboards-generation-*.log` y `deploy-*.log`) que superen el periodo de retención (por defecto 30 días).
- **Diagnóstico y estado (`status`)**: Informa del tamaño ocupado por logs, uso porcentual de disco, número de archivos y advertencias de Nginx.

### Uso Manual:
```bash
# Ver estado y ocupación de logs
./maintenance.sh status

# Ejecutar rotación de cron.log y purga de logs antiguos (>30d)
./maintenance.sh rotate-logs

# Limpiar logs antiguos (>30d) sin rotar cron.log
./maintenance.sh clean

# Forzar rotación de cron.log aunque no alcance el tamaño mínimo
./maintenance.sh rotate-logs --force

# Sobrescribir periodo de retención a 15 días
./maintenance.sh rotate-logs --retention-days 15
```

### Configuración recomendada en Crontab (Semanal):
```bash
15 2 * * 6 bash /infocodes/project/release-dashboard-application/current/scripts/maintenance.sh rotate-logs >> /infocodes/var/log/release-dashboard/maintenance.log 2>&1
```
