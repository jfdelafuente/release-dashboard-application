# Scripts de Automatización y Operación

Scripts para el despliegue, operación y conversión de datos de Release Dashboard Application.

---

## ⚡ deploy-production.ps1 (Despliegue en 1 Clic desde Windows)

Script principal de despliegue desde la máquina local Windows a producción (`infocodes@10.132.26.96`).

### Características:
- Empaquetado selectivo de runtime en `dist/release-dashboard-runtime.tar.gz` (~2.3 MB).
- Cero `git pull`, `git stash` o clonación en el servidor de producción.
- Protección total del directorio `data/` (persistencia estricta).
- Backup preventivo automático con rotación de las últimas 5 copias en `/infocodes/var/backups/release-dashboard-application/`.
- Validación de sintaxis Nginx (`nginx -t`) y recarga suave en caliente (`nginx -s reload`) con rollback automático.
- Ejecución desatendida de sondas de salud HTTP al finalizar.

### Uso:
```powershell
# Despliegue estándar completo:
.\scripts\deploy-production.ps1

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
0 2 * * * /infocodes/project/release-dashboard-application/scripts/generate-dashboards.sh >> /infocodes/project/release-dashboard-application/logs/dashboards-cron.log 2>&1
```
