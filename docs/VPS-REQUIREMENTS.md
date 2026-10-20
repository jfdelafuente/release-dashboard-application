# Requisitos y Arquitectura del VPS para Release Dashboard Application

Este documento especifica los requisitos de infraestructura, sistema operativo, software, seguridad y arquitectura de almacenamiento del servidor VPS de producción donde opera Release Dashboard Application.

---

## 1. Alcance y Contexto de Producción

- **Entorno Único**: Producción en el host **`10.132.26.96`** (`infocodes.si.orange.es`).
- **Servidor Compartido**: El VPS aloja de forma consolidada varios servicios del ecosistema técnico de Orange:
  1. **Release Dashboard Application** (este repositorio): Dashboards estáticos en `/dashboards`, catálogo y datasets JSON en `/data`, y proxy de Resumen IA en `/api/epsilon/`.
  2. **CSO Incident Masivas Report** (backend FastAPI en `:8000` y frontend en `/reportes-incidencias`).
  3. **Gestión de Problemas** (aplicación Next.js gestionada con `pm2` en `:3001` servida en `/problemas`).
  4. **Aplicación Raíz** (atendida vía socket Unix en `/infocodes/var/run/infocodes.sock`).
- **Modelo de Despliegue**: **Standalone Runtime sin Git en el VPS**. El servidor no realiza operaciones Git ni checkouts; recibe artefactos selectivos atómicos transferidos vía SCP/SSH y gestionados por enlaces simbólicos.
- **Identidad Corporativa**: Todos los dashboards y activos visuales se rigen estrictamente por la identidad corporativa **Orange**.

---

## 2. Requisitos de Hardware y Sistema Operativo

### Hardware Recomendado (Entorno Compartido)

| Recurso | Especificación Mínima | Justificación |
|---|---|---|
| **CPU** | 4 Cores | Concurrencia de Nginx, conversiones batch Python y backends Node/FastAPI. |
| **RAM** | 8 GB | Soporte conjunto para Nginx, buffers de caché proxy, pm2 y scripts de análisis. |
| **Almacenamiento** | 50+ GB SSD | Espacio para datasets históricos, informes PPTX, backups rotativos y logs. |
| **Red** | 1 Gbps | Conectividad fluida dentro de la intranet y VPN corporativa de Orange. |

### Sistema Operativo y Usuario de Servicio

- **Distribución**: **Ubuntu 20.04 LTS / 22.04 LTS** o distribución Linux compatible (Debian / Rocky Linux).
- **Usuario de Sistema**: **`infocodes`**.
- **Permisos**: Toda la infraestructura de la aplicación reside bajo la jerarquía `/infocodes/`. Las operaciones de despliegue, ejecución de cron jobs y recarga de Nginx operan bajo el usuario `infocodes` sin requerir elevación de privilegios `sudo`.

---

## 3. Software Requerido en el Servidor

### 3.1 Intérprete Python y Dependencias
Python en el VPS se utiliza **únicamente para la ejecución de conversores CSV→JSON en modo batch** (orquestados por cron) y scripts de soporte. No existe ningún daemon o servicio web Python continuo correspondiente a este repositorio.

```bash
# Versión de Python recomendada: 3.10+ / 3.11
python3 --version   # >= 3.10.0

# Paquetes requeridos para conversores y reportes
pip3 install -r requirements.txt
```

### 3.2 Servidor Web Nginx
Nginx opera como servidor frontal único en el VPS:
- Binario: `/infocodes/nginx/sbin/nginx`
- Archivo de configuración maestro: `/infocodes/nginx/conf/nginx.conf`
- Directorio de configuraciones modulares: `/infocodes/nginx/conf/conf.d/*.conf`
- PID: `/infocodes/var/run/nginx.pid`
- Escucha: Puerto **`8081`**

### 3.3 Utilidades del Sistema
- `curl` / `wget`: Sondas de salud HTTP locales.
- `tar`: Extracción de artefactos runtime y empaquetado de copias de seguridad.
- `cron`: Planificador de tareas batch (`cron` o `crond`).
- `OpenSSH Server`: Para recepción de artefactos vía SCP y comandos remotos SSH.

> **Importante**: Git **no** es necesario ni se utiliza en el servidor de producción.

---

## 4. Estructura de Directorios en el VPS

La arquitectura desacopla estrictamente el código inmutable, los datos de negocio persistentes, los registros y las copias de seguridad:

```text
/infocodes/
├── nginx/
│   ├── sbin/nginx                      # Binario ejecutable de Nginx
│   └── conf/
│       ├── nginx.conf                  # Configuración activa de Nginx
│       └── conf.d/                     # Módulos de configuración (cso-incident.conf)
│
├── project/
│   └── release-dashboard-application/  # Raíz del proyecto en el servidor
│       ├── current ───────────────────► Enlace simbólico atómico a la release activa
│       ├── releases/
│       │   ├── 20261015_120000/        # Releases históricas inmutables
│       │   └── 20261020_164500/        # Release activa desplegada
│       │       ├── dashboards/         # HTML/CSS/JS estático
│       │       ├── converters/         # Motor CLI de conversión
│       │       ├── scripts/            # Scripts operacionales
│       │       ├── data ──────────────► Enlace a /infocodes/var/storage/release-dashboard
│       │       ├── logs ──────────────► Enlace a /infocodes/var/log/release-dashboard
│       │       └── VERSION             # Versión semántica del release
│       ├── status.sh                   # Sonda de salud y diagnóstico
│       └── rollback.sh                 # Reversión rápida por symlink
│
└── var/
    ├── storage/                        # Almacenamiento persistente desacoplado (Single Source of Truth)
    │   ├── release-dashboard/
    │   │   ├── input/                  # Archivos CSV origen depositados
    │   │   ├── output/                 # JSONs convertidos (*-massive.json, index.json)
    │   │   ├── reports/                # Informes generados
    │   │   │   └── executive ─────────► Enlace sinérgico a ../executive_pptx
    │   │   ├── errors/                 # Logs de discrepancias y errores de validación
    │   │   └── archive/                # Histórico de datasets
    │   └── executive_pptx/             # Informes PowerPoint ejecutivos (.pptx)
    │
    ├── log/
    │   ├── release-dashboard/          # Logs de cron batch y conversiones
    │   └── nginx/                      # infocodes.access.log y infocodes.error.log
    │
    ├── backups/
    │   └── release-dashboard-application/ # Copias de seguridad preventivas (backup_*.tar.gz)
    │
    └── cache/
        └── nginx/                      # Caché compartida para Epsilon IA y proxies
```

---

## 5. Configuración de Red, Puertos y Firewall

### Puertos de Red

| Puerto | Protocolo | Servicio | Acceso |
|---|---|---|---|
| **22** | TCP | SSH (acceso remoto y despliegue SCP) | Restringido a red corporativa Orange / VPN. |
| **8081** | TCP | Nginx (Release Dashboard y servicios web) | Acceso institucional / intranet Orange. |
| **8000** | TCP | Backend FastAPI (`cso-incident-masivas-report`) | Interno (`localhost` únicamente). |
| **3001** | TCP | Backend Next.js (`Gestión de Problemas`) | Interno (`localhost` únicamente). |

### DNS y Resolución

```text
infocodes.si.orange.es ──► 10.132.26.96
```

---

## 6. Configuración de Nginx (`nginx.conf`)

Extracto de la configuración activa en `/infocodes/nginx/conf/nginx.conf`:

```nginx
worker_processes 1;
error_log /infocodes/var/log/nginx/error.log info;
pid /infocodes/var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    gzip on;

    proxy_cache_path /infocodes/var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m use_temp_path=off;

    upstream fastapi_backend {
        server localhost:8000;
    }

    upstream gestion_problemas_backend {
        server localhost:3001;
    }

    server {
        listen 8081 default_server;
        server_name 10.132.26.96 infocodes.si.orange.es;
        access_log /infocodes/var/log/nginx/infocodes.access.log;

        # Cabeceras de seguridad
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Dashboards estáticos del release activo
        location /dashboards {
            alias /infocodes/project/release-dashboard-application/current/dashboards;
            index index.html index.htm;
            try_files $uri $uri/ /index.html;
        }

        # Datasets JSON desde almacenamiento desacoplado persistente
        location /data {
            alias /infocodes/var/storage/release-dashboard;
            autoindex off;
        }

        # Proxy hacia servicio Epsilon IA (con caché compartida resiliente)
        location /api/epsilon/ {
            proxy_pass https://soptmc.si.orange.es/MonTMC/api/epsilon/;
            proxy_ssl_verify off;
            proxy_ssl_server_name on;
            proxy_set_header Host soptmc.si.orange.es;
            proxy_connect_timeout 15s;
            proxy_read_timeout 30s;
            proxy_cache my_cache;
            proxy_cache_valid 200 15m;
            proxy_cache_valid 404 1m;
            proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
            proxy_cache_lock on;
            proxy_cache_lock_timeout 5s;
            proxy_ignore_headers Cache-Control Expires Set-Cookie;
            add_header X-Cache-Status $upstream_cache_status always;
        }

        # Aplicación Gestión de Problemas (Next.js con pm2)
        location /problemas {
            proxy_pass http://gestion_problemas_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Módulos hermanos (conf.d/cso-incident.conf -> /reportes-incidencias y /api)
        include /infocodes/nginx/conf/conf.d/*.conf;

        # Aplicación raíz delegada a socket Unix
        location / {
            proxy_pass http://unix:/infocodes/var/run/infocodes.sock;
            proxy_cache my_cache;
        }
    }
}
```

### Comandos de Operación de Nginx (Usuario `infocodes`)

```bash
# Validar sintaxis de configuración
/infocodes/nginx/sbin/nginx -t

# Recargar configuración en caliente sin caída de conexiones
/infocodes/nginx/sbin/nginx -s reload
```

---

## 7. Automatización Batch y Cron Jobs

El procesamiento batch de los archivos CSV depositados en `input/` se ejecuta de forma desatendida mediante el crontab del usuario `infocodes`:

```bash
# Editar crontab del usuario
crontab -e
```

**Entrada configurada**:
```cron
# Procesamiento periódico de incidencias cada 15 minutos
*/15 * * * * /infocodes/project/release-dashboard-application/current/scripts/generate-dashboards.sh >> /infocodes/var/log/release-dashboard/cron-generate.log 2>&1
```

---

## 8. Sondas de Salud, Backups y Contingencia

### 8.1 Sondas de Salud (`status.sh`)
El servidor dispone de una herramienta de diagnóstico rápido ejecutable local o remotamente:

```bash
/infocodes/project/release-dashboard-application/scripts/status.sh
```

El script comprueba:
- Estado del proceso y sintaxis de Nginx (`nginx -t`).
- Versión activa en `current/VERSION`.
- Conteo de archivos en `/infocodes/var/storage/release-dashboard/` (`input`, `output`, `reports`).
- Códigos de respuesta HTTP (200) de `/dashboards/portal/`, `/data/index.json` y proxies.

### 8.2 Backups Preventivos
En cada despliegue ejecutado por `deploy-production.ps1`:
- Se genera un paquete comprimido en `/infocodes/var/backups/release-dashboard-application/backup_<TIMESTAMP>.tar.gz` respaldando el catálogo actual de `output/` y la configuración de `nginx.conf`.
- Se aplica rotación automática reteniendo las últimas **5 copias**.

### 8.3 Protocolo de Rollback Inmediato
Si una release presenta problemas:
1. **Reversión por Symlink (`rollback.sh`)**:
   ```bash
   /infocodes/project/release-dashboard-application/scripts/rollback.sh
   ```
   Conmuta de inmediato el enlace `current` a la release previa y recarga Nginx.
2. **Reversión por Copia de Seguridad**:
   ```powershell
   .\scripts\deploy-production.ps1 -Rollback
   ```

---

## 9. Checklist de Preparación y Auditoría del VPS

Antes de poner en marcha o auditar el servidor, verificar:

- [ ] Conectividad SSH a `infocodes@10.132.26.96` operativa con autenticación por clave pública.
- [ ] Directorios persistentes `/infocodes/var/storage/release-dashboard/` y `/infocodes/var/storage/executive_pptx/` creados con permisos para el usuario `infocodes`.
- [ ] Directorio de logs `/infocodes/var/log/release-dashboard/` disponible.
- [ ] Intérprete Python 3.10+ y paquetes de `requirements.txt` instalados.
- [ ] Binario Nginx operativo en `/infocodes/nginx/sbin/nginx` escuchando en el puerto 8081.
- [ ] Tarea programada en `crontab` apuntando a `current/scripts/generate-dashboards.sh`.
- [ ] Sonda `scripts/status.sh` respondiendo con código 200 en todos los endpoints.

---

## Documentación Relacionada

- [DEPLOYMENT.md](DEPLOYMENT.md) — Manual integral de despliegue Standalone Runtime.
- [PROJECT-STRUCTURE.md](PROJECT-STRUCTURE.md) — Arquitectura y mapa exhaustivo de directorios.
- [VERSION-MANAGEMENT.md](VERSION-MANAGEMENT.md) — Política de versionado semántico y trazabilidad.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Diagnóstico y resolución de incidencias en VPS y local.
- [LOGS.md](LOGS.md) — Estándar unificado de bitácora técnica e intervenciones.

---

**Última actualización**: 2026-10-20  
**Versión del documento**: 2.0  
**Entorno**: Producción (`10.132.26.96`)
