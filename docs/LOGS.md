# Gestión de Logs, Auditoría y Trazabilidad

Este documento describe la arquitectura, ubicación y operativa de los registros (**logs**) y la auditoría de Release Dashboard Application tanto en el servidor de producción (VPS) como en el entorno de desarrollo local.

---

## 🏛️ Principios de Logging

1. **Desacoplamiento Estricto del Código**:
   - Los logs residen fuera del árbol de releases del proyecto para evitar que una nueva versión sobrescriba el histórico o que los logs inflen los empaquetados de despliegue.
   - Los logs están totalmente excluidos de git (`.gitignore`).
2. **Persistencia Centralizada en VPS**:
   - En producción, los logs de aplicación se centralizan en el directorio de sistema **`/infocodes/var/log/release-dashboard/`**.
   - Los logs de servidor web residen en **`/infocodes/var/log/nginx/`**.
3. **Retrocompatibilidad Transparente**:
   - Dentro del directorio del proyecto (`/infocodes/project/release-dashboard-application/logs`) y dentro de la release activa (`current/logs`) existen enlaces simbólicos (**symlinks**) que apuntan hacia `/infocodes/var/log/release-dashboard/`. Cualquier script o comando que consulte `./logs/` accederá a la ubicación correcta.

---

## 📁 Ubicación de Logs en el Servidor VPS

```
/infocodes/var/log/
│
├── release-dashboard/                                # Logs de la aplicación y procesos batch
│   ├── dashboards-cron.log                          # Salida estándar y errores del cron nocturno
│   └── dashboards-generation-YYYYMMDD.log           # Bitácora detallada diaria de conversión batch CSV -> JSON
│
└── nginx/                                           # Logs del servidor web (puerto 8081)
    ├── infocodes.access.log                         # Registro de accesos HTTP y consultas a dashboards/APIs
    └── error.log                                    # Errores de Nginx y fallos de conexión a upstreams
```

---

## 📜 Detalle de Archivos de Log

### 1. Conversión Batch de Dashboards (`dashboards-generation-YYYYMMDD.log`)
* **Generado por**: [`scripts/generate-dashboards.sh`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/generate-dashboards.sh).
* **Frecuencia**: Rotación diaria por fecha (ej: `dashboards-generation-20261020.log`).
* **Contenido**:
  - Timestamp exacto de inicio y fin de la ejecución.
  - Directorios de entrada (`/infocodes/var/storage/release-dashboard/input/`) y salida (`/infocodes/var/storage/release-dashboard/output/`).
  - Lista de archivos CSV procesados de incidencias masivas y postmortems.
  - Estado de regeneración del catálogo central `output/index.json`.
  - Registros de error si algún CSV está corrupto o le faltan columnas obligatorias (redirigido a `errors/`).

### 2. Tarea Programada en Crontab (`dashboards-cron.log`)
* **Generado por**: Tarea programada en el crontab del usuario `infocodes`:
  ```bash
  0 2 * * * /infocodes/project/release-dashboard-application/scripts/generate-dashboards.sh >> /infocodes/var/log/release-dashboard/dashboards-cron.log 2>&1
  ```
* **Contenido**: Captura la salida completa de consola (`stdout` y `stderr`) generada por la ejecución desatendida de las 02:00 AM.

### 3. Registro de Accesos Nginx (`infocodes.access.log`)
* **Configurado en**: [`nginx.conf`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/nginx.conf) (`access_log /infocodes/var/log/nginx/infocodes.access.log;`).
* **Contenido**: Peticiones HTTP procesadas por el servidor web en el puerto 8081:
  - URLs de dashboards solicitadas (`/dashboards/portal/`, `/dashboards/postmortem/`, etc.).
  - Descargas de datos JSON (`/data/output/*.json`).
  - Peticiones proxificadas a Epsilon IA (`/api/epsilon/resumenIA/*`) con cabecera de estado de caché (`X-Cache-Status: HIT` o `MISS`).
  - Proxy a Gestión de Problemas (`/problemas`) y backend FastAPI (`/api`).

---

## 🚀 Trazabilidad y Auditoría de Despliegues

El despliegue a producción se gestiona desde la estación de desarrollo con el script [`scripts/deploy-production.ps1`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/deploy-production.ps1). La trazabilidad y seguridad se garantiza a través de:

### 1. Copias Preventivas Automáticas (Backups)
* Antes de aplicar cualquier cambio, el script empaqueta el estado previo en:
  `/infocodes/var/backups/release-dashboard-application/backup_YYYYMMDD_HHMMSS.tar.gz`
* **Política de Rotación**: Conserva automáticamente las **5 copias más recientes**, purgando las anteriores para evitar saturación de espacio en disco.
* **Rollback en 1 Clic**: Si se detecta un problema post-despliegue:
  ```powershell
  # Desde Windows:
  .\scripts\deploy-production.ps1 -Rollback

  # O directamente en el servidor VPS:
  ./rollback.sh
  ```

### 2. Sondas de Salud Post-Despliegue (`Smoke Tests`)
* Tras la recarga en caliente de Nginx (`nginx -s reload`), el despliegue ejecuta automáticamente [`scripts/status.sh`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/status.sh) tanto en local como en remoto:
  - Comprobación de versión desplegada (`VERSION`).
  - Validación sintáctica de Nginx (`nginx -t`).
  - Validación de respuesta HTTP 200 OK para todos los dashboards y proxies.

---

## 💻 Logs en Entorno de Desarrollo Local (`serve_app.py`)

Al ejecutar [`serve_app.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/serve_app.py) en local (puerto `8080`), los logs se imprimen de forma interactiva en la consola de PowerShell:

```
[127.0.0.1] "GET /dashboards/portal/ HTTP/1.1" 200 -
  Proxy Epsilon IA (cache HIT): INC000012345678
  [FastAPI Proxy] Delegando GET /api/reports a http://127.0.0.1:8000...
  Guardado: data/input/incidencias.csv (142058 bytes)
  Conversión OK: incidencias.csv
```

* **Proxy Epsilon IA**: Muestra si la consulta fue resuelta desde la memoria local (`cache HIT`) o requirió petición exterior (`cache MISS/LIVE`).
* **Subida de CSV**: Muestra la ruta del archivo recibido y el resultado de la invocación a `upload_csv.py`.

---

## 🛠️ Comandos de Diagnóstico en el Servidor VPS

```bash
# 1. Ver en tiempo real la ejecución del cron de dashboards:
tail -f /infocodes/var/log/release-dashboard/dashboards-cron.log

# 2. Consultar el informe de la última conversión batch diaria:
ls -lt /infocodes/var/log/release-dashboard/dashboards-generation-*.log | head -n 1 | awk '{print $9}' | xargs tail -n 50

# 3. Monitorear accesos HTTP y tráfico web:
tail -f /infocodes/var/log/nginx/infocodes.access.log

# 4. Filtrar errores HTTP (códigos 4xx y 5xx) en Nginx:
awk '$9 ~ /^[45]/' /infocodes/var/log/nginx/infocodes.access.log | tail -n 20

# 5. Listar las copias preventivas de despliegue disponibles para rollback:
ls -lh /infocodes/var/backups/release-dashboard-application/
```

---

## 🧹 Política de Retención y Mantenimiento

| Tipo de Registro | Ubicación | Política de Retención | Mecanismo de Limpieza |
|---|---|---|---|
| **Logs de Generación Batch** | `/infocodes/var/log/release-dashboard/` | 90 días | Script de mantenimiento / Logrotate |
| **Logs de Acceso Nginx** | `/infocodes/var/log/nginx/` | 30 días con compresión rotativa | Configuración estándar de `logrotate` en VPS |
| **Copias Preventivas (Backups)** | `/infocodes/var/backups/release-dashboard-application/` | 5 últimas versiones | Rotación automática en `deploy-production.ps1` |
| **Informes Ejecutivos PPTX** | `/infocodes/var/storage/executive_pptx/` | 14 días (mínimo 5 retenidos) | Función `cleanup_old_executive_reports()` |
