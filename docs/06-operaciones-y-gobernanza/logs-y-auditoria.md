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
│   ├── dashboards-generation-YYYYMMDD.log           # Bitácora detallada diaria de conversión batch CSV -> JSON
│   └── ingestion_audit.log                          # Enlace simbólico -> /infocodes/var/storage/release-dashboard/logs/ingestion_audit.log
│
└── nginx/                                           # Logs del servidor web (puerto 8081)
    ├── infocodes.access.log                         # Registro de accesos HTTP y consultas a dashboards/APIs
    └── error.log                                    # Errores de Nginx y fallos de conexión a upstreams
`

`
/infocodes/var/storage/release-dashboard/             # Almacenamiento desacoplado persistente (Single Source of Truth)
│
├── logs/
│   └── ingestion_audit.log                          # Registro persistente y acumulativo de ingestas CSV y enriquecimiento IA
└── output/
    └── ingestion_audit_summary.json                 # Resumen estructurado JSON de la última carga (servido por Nginx en /data/)
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

## 🔍 Trazabilidad y Auditoría de Ingesta Masiva y Telemetría Semántica

Para garantizar la máxima transparencia operativa sobre qué incidencias disponen de información completa y justificar técnicamente cualquier dato faltante, el sistema incorpora un motor de auditoría continua ([`converters/cli/ingestion_logger.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/ingestion_logger.py)):

### 1. Fichero de Log de Auditoría (`data/logs/ingestion_audit.log`)
Registra de forma cronológica y persistente cada fase de la ingesta de tickets:

```text
================================================================================
PROCESO DE INGESTA DE INCIDENCIAS - 2026-11-03 15:30:12
================================================================================
[2026-11-03 15:30:12] [UPLOAD_START] Fichero recibido: CS-Informe incidencias.csv (142,058 bytes) | Tipo: massive-incidents
[2026-11-03 15:30:13] [CONVERT_OK] Conversión CSV a JSON completada en 0.420s (665 registros) -> Generado: 20261103-massive.json
[2026-11-03 15:30:13] [BACKGROUND_TASK] Disparada tarea asíncrona 'evaluate_incident_notifications.py' (PID 14280) desacoplada del ciclo HTTP.

--------------------------------------------------------------------------------
AUDITORÍA DETALLADA DE INCIDENCIAS (665 tickets) - 2026-11-03 15:30:14
Origen: CS-Informe incidencias.csv
--------------------------------------------------------------------------------
01. INC000004167733 | Estatus: En curso | Remedy: Media -> SUGERIDA P1 (DISCREPANCIA) | [PARCIAL]
    Título: CORTE TOTAL // SEVILLA // LA FINCA
    * Resumen IA: [OK] (Epsilon Telemetría IA)
    * Mensajes Ejecutivos: [PENDIENTE] Causa: Pendiente de redacción oficial por el agente incident-reporter
    * Criticidad ITIL: P1 (Proceso: O&M | Motivo: Umbral >20% desviación)
    * Dictamen: Resumen IA OK | Mensajes ejecutivos faltantes: Pendiente de redacción

02. INC000004128954 | Estatus: Cerrado | Remedy: Alta | [NO_APLICA]
    Título: Degradación de balanceador frontal
    * Resumen IA: [FALTA] Causa: Incidencia en estado terminal 'Cerrado' (Cerrado/Resuelto): omitida según ITIL/SRE
    * Mensajes Ejecutivos: [PENDIENTE] Causa: Incidencia en estado terminal 'Cerrado': no requiere comunicación oficial urgente
    * Dictamen: Incidencia en estado terminal (Cerrado)

================================================================================
BALANCE GLOBAL DE INFORMACIÓN DE INGESTA
================================================================================
  Total incidencias analizadas:      665
  * Información COMPLETA (IA+Comms): 0
  * Información PARCIAL:             18
  * Información INCOMPLETA:          0
  * Omitidas por Estado Terminal:    647
  ------------------------------------------------
  * Con Resumen IA disponible:       18 / 665
  * Con Mensajes Ejecutivos listos:  0 / 665
  * Con Discrepancias de severidad:  11 / 665
  Tiempo total de evaluación:        1.45s
================================================================================
```

### 2. Resumen Estructurado JSON (`data/output/ingestion_audit_summary.json`)
Generado en paralelo en formato JSON para consumo inmediato por parte de la API backend (`GET /api/logs/ingestion`) y la Consola de Auditoría del Cockpit (<kbd>Shift</kbd> + <kbd>I</kbd>).

---

## 🧽 Procedimiento de Purga y Reseteo Seguro del Sistema

Cuando un operador o desarrollador necesita **limpiar los datos previos de pruebas o cargas masivas antiguas para iniciar una nueva subida limpia desde cero**, debe emplear el script oficial de saneamiento ([`scripts/clean_system_data.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/clean_system_data.py)) o su acceso rápido en la raíz ([`clean_data.bat`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/clean_data.bat)).

### Matriz de Acciones de Purga

| Directorio / Fichero | Acción Ejecutada | Justificación Operativa |
| :--- | :---: | :--- |
| `data/input/*.csv` | **Eliminado** | Elimina ficheros CSV temporales de cargas previas. |
| `data/output/*-massive.json` | **Eliminado** | Elimina datasets masivos antiguos. |
| `data/output/*-postmortem.json` | **Eliminado** | Elimina datasets de postmortem antiguos. |
| `data/archive/*` | **Eliminado** | Limpia el historial archivado. |
| `data/errors/*` | **Eliminado** | Limpia reportes de error de CSVs previos. |
| `data/reports/*.pptx` | **Eliminado** | Purga informes ejecutivos generados. |
| `data/.epsilon_cache/*` | **Eliminado** *(salvo `--keep-cache`)* | Invalida respuestas semánticas en caché para forzar consultas frescas. |
| `data/output/index.json` | **Reseteado** | Se restaura a plantilla válida: `{"massive": [], "postmortem": [], "last_updated": "<UTC>"}`. |
| `data/output/active_incidents.json` | **Reseteado** | Se restaura a `{"_metadata": {"total": 0}, "data": []}`. |
| `data/output/high_priority_notifications.json` | **Reseteado** | Se restaura a catálogo estructurado sin tickets. |
| `data/output/ingestion_audit_summary.json` | **Reseteado** | Se restaura a métricas iniciales en cero. |
| `data/agent_executive_messages.json` | **Reseteado** | Se restaura a plantilla vacía estructurada. |
| `data/logs/ingestion_audit.log` | **Reseteado** | Se trunca a cero bytes con cabecera de inicialización limpia. |
| **`data/input/scheduled_changes_pap.json`** | 🔒 **ESTRICTAMENTE PROTEGIDO** | **NUNCA se elimina ni modifica**: Calendario maestro de trabajos programados (PaP). |
| **`data/output/agents_catalog.json`** | 🔒 **ESTRICTAMENTE PROTEGIDO** | **NUNCA se elimina ni modifica**: Catálogo oficial de agentes de IA y skills. |

### Comandos de Ejecución:

```powershell
# 1. Simulación segura (Dry Run) sin modificar ningún fichero en disco (Recomendado antes de ejecutar):
.\clean_data.bat --dry-run
# o directamente con Python:
python scripts/clean_system_data.py --dry-run

# 2. Ejecución con solicitud de confirmación interactiva por teclado:
.\clean_data.bat

# 3. Ejecución directa desatendida (para pipelines o tests):
.\clean_data.bat --yes

# 4. Limpieza conservando la caché local de Epsilon Resumen IA:
.\clean_data.bat --yes --keep-cache
```

> [!CAUTION]
> El borrado de ficheros es irreversible. Se recomienda ejecutar siempre primero con `--dry-run` para previsualizar los ficheros que se eliminarán y los que se resetearán.

---

## 🧹 Política de Retención y Mantenimiento

| Tipo de Registro | Ubicación | Política de Retención | Mecanismo de Limpieza |
|---|---|---|---|
| **Logs de Generación Batch** | `/infocodes/var/log/release-dashboard/` | 90 días | Script de mantenimiento / Logrotate |
| **Logs de Acceso Nginx** | `/infocodes/var/log/nginx/` | 30 días con compresión rotativa | Configuración estándar de `logrotate` en VPS |
| **Copias Preventivas (Backups)** | `/infocodes/var/backups/release-dashboard-application/` | 5 últimas versiones | Rotación automática en `deploy-production.ps1` |
| **Informes Ejecutivos PPTX** | `/infocodes/var/storage/executive_pptx/` | 14 días (mínimo 5 retenidos) | Función `cleanup_old_executive_reports()` |
