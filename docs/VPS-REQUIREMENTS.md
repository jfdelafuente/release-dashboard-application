# Requisitos de VPS para Release Dashboard Application

Documento que especifica los requisitos de infraestructura, software y configuración del VPS donde se despliega la aplicación.

**Importante sobre el alcance real** (ver [`DEPLOYMENT.md`](DEPLOYMENT.md) y [`PROJECT-STRUCTURE.md`](PROJECT-STRUCTURE.md)):

- Solo existe **producción**. No hay un entorno de staging con URL propia.
- Este repositorio aporta **contenido estático** (dashboards HTML/CSS/JS) y **datos JSON**; Nginx los sirve directamente desde el checkout git (`/infocodes/project/release-dashboard-application/`), sin backend propio, sin build y sin Gunicorn/Flask/FastAPI de este repo.
- El VPS es **compartido** con aplicaciones hermanas (backend FastAPI de `cso-incident-masivas-report`, app estática `reportes-incidencias`, backend Next.js/pm2 de "Gestión de Problemas", y otra aplicación distinta que ocupa la raíz del dominio vía socket Unix — ver `nginx.conf`). Este documento solo cubre lo necesario para servir `/dashboards` y `/data` de este repo; el resto de servicios del mismo VPS tiene sus propios requisitos, no documentados aquí.

---

## 1. Requisitos de Hardware y Sistema Operativo

### Hardware Mínimo

| Componente | Producción (VPS compartido) |
|-----------|-----------|
| CPU | 4+ cores |
| RAM | 8+ GB |
| Almacenamiento | 50+ GB SSD |
| Ancho de banda | 1 Gbps |

**No confirmado**: estas cifras son una referencia orientativa, no las specs reales del VPS. El servidor real (`10.132.68.85` / `infocodes.si.orange.es`) es **compartido con varias aplicaciones hermanas** (ver `nginx.conf`), por lo que el dimensionamiento real depende de la carga conjunta de todas ellas, no solo de este repositorio. No se ha verificado el hardware real asignado a esta máquina.

### Sistema Operativo Soportado

- **Ubuntu 20.04 LTS** (recomendado)
- **Ubuntu 22.04 LTS** (más reciente)
- **Debian 11** (compatible)
- **Rocky Linux 8** (compatible)

**NO soportado**: Windows Server, CentOS < 7

---

## 2. Software Requerido

### 2.1 Python y Dependencias Base

```bash
# Actualizar sistema
sudo apt update
sudo apt upgrade -y

# Instalar Python 3.10 (recomendado)
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y python3-pip

# Verificar instalación
python3 --version
pip3 --version

# Instalar herramientas de sistema necesarias
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    net-tools \
    htop \
    unzip
```

### 2.2 Dependencias del Proyecto

Python en el VPS se usa **únicamente** para ejecutar los conversores CSV→JSON (`converters/`), invocados por el cron `scripts/generate-dashboards.sh` — no hay una app Python corriendo de forma continua para este repo. Las dependencias están repartidas en `requirements.txt` (raíz) y `converters/requirements.txt`:

```bash
# En el servidor, sobre el checkout real del repo
cd /infocodes/project/release-dashboard-application
pip3 install -r requirements.txt
pip3 install -r converters/requirements.txt
```

**Dependencias principales**: `pandas` (u otra librería de procesamiento de CSV usada por los conversores) y las de `converters/requirements.txt`. **No hay `Flask` ni `Gunicorn` en este repositorio**: no es una aplicación web Python con proceso propio.

**No confirmado**: si el VPS usa el intérprete de sistema o un virtualenv dedicado para estas dependencias (ver también `docs/DEPLOYMENT.md`, sección "Requisitos previos").

### 2.3 Servidor Web

Los dashboards son archivos estáticos servidos por Nginx, que **ya está instalado y corriendo en el VPS** (sirve, en el mismo dominio/puerto, tanto este repo como sus aplicaciones hermanas — ver `nginx.conf`). Este repositorio no requiere Gunicorn, uWSGI ni ningún servidor de aplicaciones propio:

```bash
# Nginx (si no estuviera ya instalado en el VPS)
sudo apt install -y nginx
```

**Backends reales del dominio (fuera de este repo)**: un backend **FastAPI** (repo hermano `cso-incident-masivas-report`, escuchando en `localhost:8000`, al que Nginx hace `proxy_pass` en `/api`) y un backend **Next.js** gestionado con **pm2** (escuchando en `localhost:3001`, `proxy_pass` en `/problemas`). Ambos se instalan, ejecutan y mantienen desde sus propios repos/procesos; no forman parte del alcance de este documento ni de este repositorio.

### 2.4 Herramientas Opcionales

No confirmado que este repositorio necesite alguna de estas herramientas — no usa caché Redis, base de datos relacional ni contenedores. Se listan solo por si el VPS las requiere para otras aplicaciones hermanas que conviven en el mismo servidor:

```bash
# Redis (usado, si acaso, por otra aplicación del VPS — no por este repo)
sudo apt install -y redis-server

# PostgreSQL (usado, si acaso, por otra aplicación del VPS — no por este repo)
sudo apt install -y postgresql postgresql-contrib

# Docker (si se decide containerizar en el futuro; no es el estado actual)
sudo apt install -y docker.io docker-compose
```

---

## 3. Estructura de Directorios

### 3.1 Directorio de la Aplicación

No hay una carpeta `/var/www/...` separada: en el VPS real, la aplicación **es** el checkout git del repo, y Nginx sirve `dashboards/` y `data/` directamente desde ahí vía `alias` (ver `nginx.conf` y `docs/PROJECT-STRUCTURE.md`). El único directorio a preparar es el checkout en sí:

```bash
# Clonar/ubicar el checkout del repo (rama `production`)
sudo mkdir -p /infocodes/project
cd /infocodes/project
git clone <url-del-repo> release-dashboard-application
cd release-dashboard-application
git checkout production

# Los subdirectorios de datos los crean los propios conversores al ejecutarse
# (data/ está en .gitignore, no se versiona):
#   data/input/    - CSV de origen
#   data/output/   - JSON generados (servidos por Nginx en /data)
#   data/errors/   - reportes de error de conversión
# Los logs de la conversión batch se escriben dentro del propio repo en:
#   logs/dashboards-generation-YYYYMMDD.log

# Establecer permisos (ajustar el usuario/grupo real de despliegue)
sudo chown -R <usuario-deploy>:<grupo-deploy> /infocodes/project/release-dashboard-application
sudo chmod -R 755 /infocodes/project/release-dashboard-application
```

**No confirmado**: el usuario/grupo real bajo el que corre Nginx y con el que se hace el `git pull` en el VPS; qué grupo de sistema es propietario de `/infocodes/`. No existen (ni están documentados en este repo) directorios separados de tipo `/var/backups/release-dashboard`, `/var/log/release-dashboard` o `/etc/release-dashboard` — si el VPS los usa para otros fines, es ajeno a este proyecto.

### 3.2 Usuario de Aplicación

**No confirmado**: qué usuario real se usa en el VPS para el checkout, el `git pull` manual y la ejecución del cron `generate-dashboards.sh`. Los comandos siguientes usan `app` como nombre de ejemplo; sustitúyelo por el usuario real de despliegue.

```bash
# Crear usuario 'app' (no-login, para seguridad) — ejemplo, ajustar al usuario real
sudo useradd -m -s /bin/bash app

# O si quieres que sea login:
sudo useradd -m -s /bin/bash app
sudo passwd app  # Establecer contraseña

# Añadir a sudoers si necesita permisos especiales
sudo usermod -aG sudo app
```

---

## 4. Configuración de Seguridad

### 4.1 SSH (Acceso Remoto)

```bash
# Editar configuración de SSH
sudo nano /etc/ssh/sshd_config

# Cambios recomendados:
Port 22                          # o puerto personalizado
PermitRootLogin no              # ¡IMPORTANTE!
PasswordAuthentication no       # Solo key-based auth
PubkeyAuthentication yes        # Autenticación por clave
MaxAuthTries 3
MaxSessions 10
ClientAliveInterval 300
ClientAliveCountMax 2
```

**Configurar clave SSH para despliegue**:

```bash
# Como usuario 'app', crear directorio SSH
sudo -u app mkdir -p /home/app/.ssh
sudo -u app chmod 700 /home/app/.ssh

# Añadir clave pública de GitHub Actions
# (la que generaste con ssh-keygen)
echo "ssh-rsa AAAA..." | sudo tee -a /home/app/.ssh/authorized_keys
sudo -u app chmod 600 /home/app/.ssh/authorized_keys

# Reiniciar SSH
sudo systemctl restart sshd
```

### 4.2 Firewall

```bash
# Habilitar UFW (Uncomplicated Firewall)
sudo ufw enable

# Permitir SSH
sudo ufw allow 22/tcp

# Permitir HTTP y HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Bloquear todo lo demás por defecto
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Ver estado
sudo ufw status verbose
```

### 4.3 Fail2Ban (Protección contra ataques SSH)

```bash
# Instalar
sudo apt install -y fail2ban

# Crear configuración local
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# Cambios recomendados en [DEFAULT] section:
bantime = 3600          # Ban por 1 hora
findtime = 600          # Ventana de tiempo (10 min)
maxretry = 5            # Intentos máximos

# En [sshd] section:
enabled = true

# Reiniciar
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### 4.4 Certificado SSL/TLS

**No confirmado**: el `nginx.conf` real de este proyecto escucha en el puerto `8081` (no en 80/443) y su bloque `server { listen 443 ssl; ... }` está comentado/deshabilitado (ver `nginx.conf`, líneas finales). No está confirmado si el VPS termina TLS en otra capa (otro Nginx/balanceador delante de este, o directamente no hay HTTPS para `infocodes.si.orange.es:8081`). Lo siguiente es la referencia genérica de cómo se configuraría Let's Encrypt si este Nginx fuera el punto de terminación TLS; no asumas que ya está así configurado sin verificarlo en el VPS real.

```bash
# Opción 1: Let's Encrypt (gratuito, recomendado)
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado (ejemplo genérico; el dominio real es infocodes.si.orange.es,
# pero no está confirmado que este Nginx sea el punto de terminación TLS — ver nota arriba)
sudo certbot certonly --standalone -d example.com

# Auto-renovación (automática con apt)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Opción 2: Certificado autofirmado (solo testing)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/server.key \
  -out /etc/ssl/certs/server.crt
```

---

## 5. Configuración de la Aplicación

### 5.1 Variables de Entorno

**No confirmado**: si en el VPS de producción se usa realmente un archivo `.env` para este repo. El repo incluye una plantilla (`config/.env.example`) pensada para configuración local/desarrollo de los conversores, pero `docs/DEPLOYMENT.md` no menciona ningún `.env` como parte del procedimiento de despliegue en el VPS. Las variables reales que aparecen en `config/.env.example` son estas (no `FLASK_ENV`/`SECRET_KEY`, que no existen en este repo):

```bash
# config/.env.example (plantilla real del repo)
APP_ENV=development
DEBUG=True
LOG_LEVEL=debug
LOG_FORMAT=standard
CACHE_TTL=60
FEATURE_FLAGS={"advanced_filters": true, "experimental_features": false}
DATABASE_URL=sqlite:///incidents.db
VERSION=0.1.0
DEPLOYMENT_ENVIRONMENT=development
```

Si se decide usar un `.env` equivalente en el VPS, debería vivir en el checkout real y no en `/var/www/...`:

```bash
sudo chmod 600 /infocodes/project/release-dashboard-application/.env
sudo chown <usuario-deploy>:<grupo-deploy> /infocodes/project/release-dashboard-application/.env
```

### 5.2 Configuración de Nginx

Este es un extracto fiel de la configuración real (`nginx.conf` en la raíz del repo, no versionado — copia idéntica en el VPS). Nginx escucha en el puerto **8081** (no 80/443) y sirve, en el mismo `server{}`, este repo **y** sus aplicaciones hermanas:

```nginx
upstream fastapi_backend {
    server localhost:8000;
}

upstream gestion_problemas_backend {
    server localhost:3001;
}

server {
    listen 8081 default_server;
    server_name 10.132.68.85 infocodes.si.orange.es;
    access_log /infocodes/var/log/nginx/infocodes.access.log;

    # Dashboards de este repo (contenido estático, servido directo desde el checkout)
    location /dashboards {
        alias /infocodes/project/release-dashboard-application/dashboards;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # JSON generados por los conversores de este repo
    location /data {
        alias /infocodes/project/release-dashboard-application/data;
        autoindex off;
    }

    # Lo siguiente pertenece a repos/servicios hermanos, fuera de este proyecto:
    location /reportes-incidencias {
        alias /infocodes/project/cso-incident-masivas-report/app;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    location /problemas {
        proxy_pass http://gestion_problemas_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

No hay `location /static/` ni `root /var/www/...` para este proyecto: `alias` apunta directamente al checkout git, sin copia intermedia. Ver el `nginx.conf` completo en la raíz del repo para el resto de bloques (caché, la ruta `/` que delega a otra aplicación vía socket Unix, etc.) — todos ajenos a este repositorio.

Tras cambiar `nginx.conf` en el VPS:
```bash
sudo nginx -t
sudo systemctl reload nginx   # o el mecanismo equivalente — no confirmado si nginx corre como servicio systemd estándar en este VPS
```

### 5.3 Supervisor / pm2 (procesos de los backends hermanos)

Este repositorio **no tiene backend propio que mantener vivo** con Supervisor, systemd ni Gunicorn: los dashboards son estáticos y los conversores solo se ejecutan puntualmente vía cron (`scripts/generate-dashboards.sh`), no como proceso persistente.

Los dos backends que sí necesitan un supervisor de procesos son de repos hermanos y quedan **fuera del alcance de este documento**:
- El backend **FastAPI** (`cso-incident-masivas-report`, puerto 8000) — su gestión de proceso (Supervisor, systemd o similar) se documenta en ese repo, no en este.
- El backend **Next.js** de "Gestión de Problemas" (puerto 3001) — gestionado con **pm2** según el propio `nginx.conf`; su configuración de pm2 vive en ese otro repo/proceso.

Si se necesita reiniciar o inspeccionar esos procesos, hay que hacerlo en el contexto de esos repos hermanos (`pm2 status`, `pm2 restart ...` para el de Next.js; el mecanismo del backend FastAPI **no confirmado** desde este repositorio).

---

## 6. Health Checks y Monitoreo

**No confirmado / no implementado actualmente**: `scripts/` en este repo solo contiene `generate-dashboards.sh` (ver `docs/PROJECT-STRUCTURE.md`) — no existe ningún `health-check.sh` real. Lo que sigue es una propuesta de referencia, no algo ya desplegado.

### 6.1 Script de Health Check (propuesta, no existente hoy)

Si se decide crear uno, debería vivir en `scripts/health-check.sh` dentro del propio checkout (no en `/var/www/...`), y no depende de ningún proceso Python persistente porque este repo no tiene uno:

```bash
#!/bin/bash

# Health check para la aplicación (propuesta — no implementado en el repo actualmente)

REPO_DIR="/infocodes/project/release-dashboard-application"
LOG_FILE="$REPO_DIR/logs/health-check.log"

check_disk_space() {
    USAGE=$(df "$REPO_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 85 ]; then
        echo "[$(date)] ERROR: Disk usage ${USAGE}% > 85%" >> "$LOG_FILE"
        return 1
    fi
    echo "[$(date)] OK: Disk usage ${USAGE}%" >> "$LOG_FILE"
    return 0
}

check_http_status() {
    # Puerto real del Nginx que sirve este repo (ver nginx.conf): 8081, no 80
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8081/dashboards/dashboard-portal.html")
    if [ "$STATUS" != "200" ]; then
        echo "[$(date)] ERROR: HTTP status $STATUS" >> "$LOG_FILE"
        return 1
    fi
    echo "[$(date)] OK: HTTP status 200" >> "$LOG_FILE"
    return 0
}

# Este repo no tiene proceso Python persistente que comprobar (los conversores
# solo corren puntualmente vía cron); no incluir un check de tipo "gunicorn running".

check_disk_space
check_http_status

exit 0
```

### 6.2 Cron Job para Health Check (si se implementa)

```bash
sudo -u <usuario-deploy> crontab -e

# Ejecutar cada 5 minutos
*/5 * * * * /infocodes/project/release-dashboard-application/scripts/health-check.sh
```

### 6.3 Monitoreo de Logs

```bash
# Logs de la conversión batch (generados por scripts/generate-dashboards.sh)
tail -f /infocodes/project/release-dashboard-application/logs/dashboards-generation-$(date +%Y%m%d).log

# Logs de Nginx (ruta real, ver nginx.conf: worker_processes/error_log relativos a /infocodes)
tail -f /infocodes/var/log/nginx/infocodes.access.log

# Buscar errores en los logs de conversión
grep ERROR /infocodes/project/release-dashboard-application/logs/*.log
```

**No confirmado**: no hay logs de "Supervisor" ni de "app.log" para este repo, porque no hay proceso de aplicación propio corriendo de forma continua.

---

## 7. Backups y Restauración

**No confirmado / no implementado actualmente**: no existe hoy ningún script de backup en este repo (`scripts/` solo tiene `generate-dashboards.sh`), ni un mecanismo de backup automático documentado en `docs/DEPLOYMENT.md`. Según esa guía, el rollback real es solo `git checkout <commit-anterior>` / `git revert` sobre el código; **no hay backup ni restauración de `data/`** (no se versiona, está en `.gitignore`) — si hace falta recuperar datos, se regeneran desde los CSV de `data/input/` con `scripts/generate-dashboards.sh`. Lo que sigue es una propuesta de referencia, no algo ya desplegado.

### 7.1 Script de Backup (propuesta, no existente hoy)

```bash
#!/bin/bash
# Propuesta de scripts/backup.sh — no implementado en el repo actualmente

REPO_DIR="/infocodes/project/release-dashboard-application"
BACKUP_DIR="/infocodes/backups/release-dashboard"   # ruta de ejemplo, no confirmada
DATA_DIR="$REPO_DIR/data"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

echo "[$(date)] Starting backup..."

mkdir -p "$BACKUP_PATH"

# Backup de datos (data/output, data/input, data/errors — no versionados en git)
tar -czf "$BACKUP_PATH/data.tar.gz" -C "$DATA_DIR" . 2>/dev/null

# Mantener solo últimos 30 días
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null

echo "[$(date)] Backup completed: $BACKUP_PATH"
```

El código no necesita backup propio más allá de git (es un checkout de la rama `production`); no hay `.env` de producción confirmado que respaldar (ver sección 5.1).

### 7.2 Cron Job de Backup (si se implementa)

```bash
sudo crontab -e

# Backup diario a las 2am
0 2 * * * /infocodes/project/release-dashboard-application/scripts/backup.sh
```

### 7.3 Restauración de datos

No hay `systemctl stop/start release-dashboard` que ejecutar (no hay servicio propio de este repo). Restaurar datos es simplemente extraer el `tar.gz` sobre `data/`, o —la vía real usada hoy— regenerar desde los CSV originales:

```bash
# Opción A: desde un backup (si existiera)
tar -xzf "$BACKUP_PATH/data.tar.gz" -C /infocodes/project/release-dashboard-application/data

# Opción B: regenerar desde los CSV de origen (vía real documentada en DEPLOYMENT.md)
cd /infocodes/project/release-dashboard-application
./scripts/generate-dashboards.sh
```

---

## 8. Requisitos de Conectividad

### 8.1 Puertos Requeridos

```
22/TCP    - SSH (acceso remoto, esencial)
8081/TCP  - Nginx (puerto real donde escucha este VPS, ver nginx.conf;
            no 80/443 directamente para este dominio/servidor)
```

**No confirmado**: si 80/443 están expuestos por delante de este Nginx (p. ej. otro balanceador que redirige a 8081) para servir HTTPS al público; el `nginx.conf` de este proyecto no lo gestiona (ver sección 4.4).

**Puertos internos usados por servicios hermanos** (no de este repo, no deberían exponerse fuera del VPS):
```
8000/TCP - Backend FastAPI (cso-incident-masivas-report)
3001/TCP - Backend Next.js / pm2 (Gestión de Problemas)
```

### 8.2 DNS

```
A record:
  infocodes.si.orange.es → 10.132.68.85   (según server_name en nginx.conf)
```

No hay entorno de staging, por lo que no aplica ningún registro DNS adicional para este proyecto.

### 8.3 Bandwidth Requerido

**No confirmado**: no se ha medido el tráfico real. Al ser un VPS compartido con varias aplicaciones (ver introducción de este documento), el ancho de banda necesario depende del conjunto, no solo de este repo.

---

## 9. Verificación Post-Deploy

Después de desplegar (ver también el checklist real de `docs/DEPLOYMENT.md`), verifica:

```bash
# 1. Acceso SSH
ssh app@infocodes.si.orange.es "echo OK"

# 2. Checkout en la rama correcta
cd /infocodes/project/release-dashboard-application && git log -1 && git branch --show-current

# 3. Directorios de datos presentes
ls -la /infocodes/project/release-dashboard-application/data/

# 4. Firewall activo
sudo ufw status

# 5. Nginx activo y config válida
sudo nginx -t
sudo systemctl status nginx

# 6. Acceso HTTP al portal (puerto real: 8081)
curl -I http://infocodes.si.orange.es:8081/dashboards/dashboard-portal.html

# 7. Datos accesibles vía Nginx
curl -I http://infocodes.si.orange.es:8081/data/index.json

# 8. Servicios hermanos no afectados (comparten el mismo Nginx)
curl -I http://infocodes.si.orange.es:8081/reportes-incidencias
curl -I http://infocodes.si.orange.es:8081/problemas
```

No hay `pip3 list | grep -i flask` que comprobar (no hay Flask en este repo) ni URL de staging que verificar.

---

## 10. Requisitos de Aplicación en Ejecución

### Este repositorio: solo Dashboards HTML + datos JSON (estado real, no hipotético)

✅ **Suficiente con**:
- Nginx (ya instalado y corriendo en el VPS, compartido con las apps hermanas) sirviendo `dashboards/` y `data/` directamente desde el checkout git vía `alias` (ver `nginx.conf`, sección 5.2 de este documento).
- Python **solo para la ejecución puntual** de los conversores CSV→JSON, disparada por el cron `scripts/generate-dashboards.sh` — no hay ningún proceso Python de este repo que deba mantenerse corriendo de forma continua.
- Los JSON consumidos por los dashboards viven en `data/output/` del propio checkout.

```bash
# Nginx ya debería estar activo para el resto de apps del VPS; si no lo estuviera:
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Los backends reales (FastAPI + Next.js) — fuera del alcance de este repo

El dominio sí tiene backends con proceso persistente, pero **viven en repos/procesos hermanos, no en este**:

- **FastAPI** (repo `cso-incident-masivas-report`, puerto 8000, `proxy_pass` en `/api`). Su gestión de proceso (Gunicorn/Uvicorn + Supervisor o systemd) se documenta y despliega desde ese repo.
- **Next.js con pm2** (puerto 3001, `proxy_pass` en `/problemas`), de la aplicación de Gestión de Problemas. Se gestiona con comandos `pm2` desde ese otro proyecto.

No hay que montar Gunicorn, uWSGI, Supervisor ni una unidad `systemd` para *este* repositorio: no tiene ni tendrá (salvo cambio de arquitectura futuro, no planificado a fecha de este documento) un backend propio. Si en algún momento se añadiera uno, habría que actualizar tanto este documento como `nginx.conf`, `docs/DEPLOYMENT.md` y `docs/PROJECT-STRUCTURE.md` para reflejarlo — hoy no es el caso.

---

## 11. Checklist de Deploymnet

Antes de desplegar en producción (ver también el checklist de `docs/DEPLOYMENT.md`, que es la referencia real del procedimiento):

- [ ] VPS accesible por SSH, checkout del repo presente en `/infocodes/project/release-dashboard-application`
- [ ] SO actualizado (`apt update && apt upgrade`)
- [ ] Python instalado (para los conversores; versión exacta no confirmada)
- [ ] Directorios de datos (`data/input`, `data/output`, `data/errors`) presentes con permisos correctos
- [ ] Firewall habilitado y puerto 8081 (y 22) accesibles
- [ ] Nginx configurado (`nginx -t` sin errores) y corriendo
- [ ] Cron de `scripts/generate-dashboards.sh` configurado (ver `scripts/README.md`)
- [ ] Prueba: `git pull origin production` funciona sin conflictos
- [ ] Prueba: acceso HTTP a `/dashboards/dashboard-portal.html` y `/data/index.json` en el puerto 8081

**No aplica** (no existe ese mecanismo en este proyecto): despliegue automático desde GitHub Actions (no hay `deploy.yml`, ver `docs/PROJECT-STRUCTURE.md`), SSH key en GitHub Secrets para deploy, certificado SSL gestionado por este Nginx (ver sección 4.4), health checks/backups automáticos (no implementados hoy, ver secciones 6 y 7).

---

## 12. Troubleshooting Común

### "Permission denied (publickey)"

```bash
# Verificar permisos SSH
sudo -u app ssh -i /home/app/.ssh/id_rsa app@localhost "echo OK"

# Revisar authorized_keys
cat ~/.ssh/authorized_keys

# Revisar logs
sudo journalctl -u ssh -f
```

### "Python package not found"

```bash
# Verificar requirements.txt (raíz y converters/)
cat /infocodes/project/release-dashboard-application/requirements.txt
cat /infocodes/project/release-dashboard-application/converters/requirements.txt

# Reinstalar dependencias
cd /infocodes/project/release-dashboard-application
pip3 install -r requirements.txt
pip3 install -r converters/requirements.txt
```

**No confirmado**: si el VPS usa un virtualenv dedicado o el intérprete de sistema (ver sección 2.2).

### "Nginx: 404 Not Found"

```bash
# Verificar configuración Nginx
sudo nginx -t

# Verificar que el checkout y el alias apuntan al mismo sitio
ls -la /infocodes/project/release-dashboard-application/dashboards/

# Revisar logs (ruta real, ver nginx.conf)
tail -f /infocodes/var/log/nginx/infocodes.access.log
```

### "Disk space full"

```bash
# Ver uso de disco
df -h

# Limpiar logs de conversión antiguos (dentro del propio repo)
find /infocodes/project/release-dashboard-application/logs -name "*.log" -mtime +30 -delete
```

**No confirmado**: no existe hoy un directorio de backups (`/var/backups/release-dashboard`) para este proyecto que limpiar — ver sección 7.

---

**Fecha de Actualización**: 2026-07-10 — corregido para reflejar la arquitectura real (sin backend Flask/FastAPI propio de este repo, sin entorno de staging, rutas reales `/infocodes/project/release-dashboard-application/`). Ver [`DEPLOYMENT.md`](DEPLOYMENT.md) y [`PROJECT-STRUCTURE.md`](PROJECT-STRUCTURE.md) para el detalle verificado del despliegue y la estructura real.
**Versión**: 1.1
**Mantenedor**: DevOps Team
