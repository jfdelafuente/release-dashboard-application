# Requisitos de VPS para Release Dashboard Application

Documento que especifica todos los requisitos de infraestructura, software y configuración necesarios para desplegar y ejecutar correctamente la aplicación en un servidor VPS (staging y producción).

---

## 1. Requisitos de Hardware y Sistema Operativo

### Hardware Mínimo

| Componente | Staging | Producción |
|-----------|---------|-----------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 8+ GB |
| Almacenamiento | 20 GB SSD | 50+ GB SSD |
| Ancho de banda | 1 Gbps | 10 Gbps |

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

Las dependencias Python están en `requirements.txt`:

```bash
# En el servidor, después de descargar el proyecto
cd /var/www/release-dashboard
pip3 install -r requirements.txt
```

**Dependencias principales**:
- `Flask` o `Gunicorn` (si es aplicación web)
- `pandas` (para procesamiento de CSV)
- Cualquier otra en `requirements.txt`

### 2.3 Servidor Web/Aplicación (Opcional)

Si la aplicación es una web app Python:

```bash
# Opción 1: Gunicorn (recomendado para production)
sudo apt install -y gunicorn

# Opción 2: uWSGI
sudo apt install -y uwsgi uwsgi-plugin-python3

# Opción 3: Nginx como reverse proxy
sudo apt install -y nginx
```

**Nota**: Los dashboards HTML actuales son archivos estáticos, pero si añades backend Flask/FastAPI en el futuro, necesitarás Gunicorn/uWSGI.

### 2.4 Herramientas Opcionales (Recomendadas)

```bash
# Supervisor (para mantener proceso corriendo)
sudo apt install -y supervisor

# Redis (si necesitas caché)
sudo apt install -y redis-server

# PostgreSQL (si necesitas base de datos)
sudo apt install -y postgresql postgresql-contrib

# Docker (si quieres containerizar)
sudo apt install -y docker.io docker-compose
```

---

## 3. Estructura de Directorios

### 3.1 Directorios de Aplicación

Crea esta estructura en ambos servidores (staging y producción):

```bash
# Crear directorios raíz
sudo mkdir -p /var/www/release-dashboard
sudo mkdir -p /var/www/release-dashboard-staging

# Crear directorios de datos (protegidos de git)
sudo mkdir -p /var/www/release-dashboard/data/input
sudo mkdir -p /var/www/release-dashboard/data/output
sudo mkdir -p /var/www/release-dashboard/data/errors
sudo mkdir -p /var/www/release-dashboard/data/archive

# Crear directorios de backups
sudo mkdir -p /var/backups/release-dashboard
sudo mkdir -p /var/log/release-dashboard

# Crear directorios de configuración
sudo mkdir -p /etc/release-dashboard

# Establecer permisos
sudo chown app:app /var/www/release-dashboard*
sudo chown app:app /var/backups/release-dashboard
sudo chown app:app /var/log/release-dashboard
sudo chmod 755 /var/www/release-dashboard*
sudo chmod 755 /var/backups/release-dashboard
sudo chmod 755 /var/log/release-dashboard
```

### 3.2 Crear Usuario de Aplicación

```bash
# Crear usuario 'app' (no-login, para seguridad)
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

Para HTTPS (staging y producción):

```bash
# Opción 1: Let's Encrypt (gratuito, recomendado)
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot certonly --standalone -d staging.example.com
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

Crea archivo `.env` en cada servidor:

```bash
# /var/www/release-dashboard/.env (Producción)
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-secret-key-here-change-in-production
DATA_DIR=/var/www/release-dashboard/data
LOG_DIR=/var/log/release-dashboard
LOG_LEVEL=INFO

# /var/www/release-dashboard-staging/.env (Staging)
FLASK_ENV=staging
DEBUG=False
SECRET_KEY=your-secret-key-staging
DATA_DIR=/var/www/release-dashboard-staging/data
LOG_DIR=/var/log/release-dashboard
LOG_LEVEL=DEBUG
```

```bash
# Establecer permisos
sudo chmod 600 /var/www/release-dashboard/.env
sudo chmod 600 /var/www/release-dashboard-staging/.env
sudo chown app:app /var/www/release-dashboard/.env
sudo chown app:app /var/www/release-dashboard-staging/.env
```

### 5.2 Configuración de Nginx (Reverse Proxy)

```bash
# /etc/nginx/sites-available/release-dashboard

upstream release_dashboard {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # SSL
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logs
    access_log /var/log/nginx/release-dashboard-access.log;
    error_log /var/log/nginx/release-dashboard-error.log;

    # Root
    root /var/www/release-dashboard;

    # Static files
    location /static/ {
        alias /var/www/release-dashboard/static/;
        expires 30d;
    }

    # Data files
    location /data/ {
        alias /var/www/release-dashboard/data/;
        expires 1h;
    }

    # API/Application (si tienes backend)
    location / {
        proxy_pass http://release_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Habilitar:
```bash
sudo ln -s /etc/nginx/sites-available/release-dashboard \
           /etc/nginx/sites-enabled/

sudo systemctl restart nginx
```

### 5.3 Supervisor (Mantener Proceso Activo)

Si tienes backend Flask/FastAPI:

```bash
# /etc/supervisor/conf.d/release-dashboard.conf

[program:release-dashboard]
command=/usr/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 app:app
directory=/var/www/release-dashboard
user=app
autostart=true
autorestart=true
stdout_logfile=/var/log/release-dashboard/supervisor.log
stderr_logfile=/var/log/release-dashboard/supervisor-error.log
environment=PATH="/var/www/release-dashboard/venv/bin"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start release-dashboard
```

---

## 6. Health Checks y Monitoreo

### 6.1 Script de Health Check

Crea `/var/www/release-dashboard/scripts/health-check.sh`:

```bash
#!/bin/bash

# Health check para la aplicación

LOG_FILE="/var/log/release-dashboard/health-check.log"

check_disk_space() {
    USAGE=$(df /var/www/release-dashboard | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 85 ]; then
        echo "[$(date)] ERROR: Disk usage ${USAGE}% > 85%" >> $LOG_FILE
        return 1
    fi
    echo "[$(date)] OK: Disk usage ${USAGE}%" >> $LOG_FILE
    return 0
}

check_http_status() {
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
    if [ "$STATUS" != "200" ]; then
        echo "[$(date)] ERROR: HTTP status $STATUS" >> $LOG_FILE
        return 1
    fi
    echo "[$(date)] OK: HTTP status 200" >> $LOG_FILE
    return 0
}

check_python_process() {
    if pgrep -f "gunicorn" > /dev/null; then
        echo "[$(date)] OK: Gunicorn process running" >> $LOG_FILE
        return 0
    else
        echo "[$(date)] ERROR: Gunicorn process not running" >> $LOG_FILE
        return 1
    fi
}

# Ejecutar checks
check_disk_space
check_http_status
check_python_process

exit 0
```

### 6.2 Cron Job para Health Check

```bash
# Editar crontab
sudo -u app crontab -e

# Añadir (ejecutar cada 5 minutos)
*/5 * * * * /var/www/release-dashboard/scripts/health-check.sh
```

### 6.3 Monitoreo de Logs

```bash
# Ver logs de aplicación
tail -f /var/log/release-dashboard/app.log

# Ver logs de Nginx
tail -f /var/log/nginx/release-dashboard-access.log

# Ver logs de Supervisor
tail -f /var/log/release-dashboard/supervisor.log

# Buscar errores
grep ERROR /var/log/release-dashboard/*.log
```

---

## 7. Backups y Restauración

### 7.1 Script de Backup Automático

Crea `/var/www/release-dashboard/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/release-dashboard"
DATA_DIR="/var/www/release-dashboard/data"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

echo "[$(date)] Starting backup..."

# Crear directorio
mkdir -p "$BACKUP_PATH"

# Backup de datos
tar -czf "$BACKUP_PATH/data.tar.gz" -C "$DATA_DIR" . 2>/dev/null

# Backup de configuración
tar -czf "$BACKUP_PATH/config.tar.gz" /var/www/release-dashboard/.env 2>/dev/null

# Backup de código (opcional)
tar -czf "$BACKUP_PATH/code.tar.gz" --exclude=data --exclude=venv \
    -C /var/www release-dashboard/ 2>/dev/null

# Mantener solo últimos 30 días
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null

echo "[$(date)] Backup completed: $BACKUP_PATH"

# Enviar a almacenamiento remoto (opcional)
# aws s3 sync "$BACKUP_DIR" s3://my-bucket/backups/release-dashboard/
```

### 7.2 Cron Job de Backup

```bash
# Crontab de root (para tener acceso a directorios restringidos)
sudo crontab -e

# Backup diario a las 2am
0 2 * * * /var/www/release-dashboard/scripts/backup.sh
```

### 7.3 Restauración desde Backup

```bash
#!/bin/bash
# /var/www/release-dashboard/scripts/restore.sh

BACKUP_DATE=$1  # Ej: 20260514-020000

if [ -z "$BACKUP_DATE" ]; then
    echo "Uso: restore.sh 20260514-020000"
    exit 1
fi

BACKUP_PATH="/var/backups/release-dashboard/$BACKUP_DATE"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup no encontrado: $BACKUP_PATH"
    exit 1
fi

echo "Restaurando desde: $BACKUP_PATH"

# Detener aplicación
sudo systemctl stop release-dashboard

# Restaurar datos
tar -xzf "$BACKUP_PATH/data.tar.gz" -C /var/www/release-dashboard/data

# Restaurar configuración (si es necesario)
# tar -xzf "$BACKUP_PATH/config.tar.gz" -C /

# Reiniciar
sudo systemctl start release-dashboard

echo "Restauración completada"
```

---

## 8. Requisitos de Conectividad

### 8.1 Puertos Requeridos

```
22/TCP   - SSH (acceso remoto, esencial)
80/TCP   - HTTP (tráfico web)
443/TCP  - HTTPS (tráfico web seguro)
```

**Puertos opcionales internos**:
```
8000/TCP - Gunicorn (si usas socket TCP)
5432/TCP - PostgreSQL (si usas DB)
6379/TCP - Redis (si usas caché)
```

### 8.2 DNS

Configura registros DNS:

```
A record:
  staging.example.com  → IP_SERVIDOR_STAGING
  example.com          → IP_SERVIDOR_PRODUCCION

CNAME (opcional):
  www.example.com      → example.com
```

### 8.3 Bandwidth Requerido

- **Staging**: 100 Mbps mínimo
- **Producción**: 1 Gbps recomendado (según tráfico esperado)

---

## 9. Verificación Post-Deploy

Después de desplegar, verifica:

```bash
# 1. Acceso SSH
ssh -p 22 app@staging.example.com "echo OK"

# 2. Directorios creados
ls -la /var/www/release-dashboard/

# 3. Permisos correctos
ls -la /var/www/ | grep release-dashboard

# 4. Python instalado
python3 --version

# 5. Dependencias instaladas
pip3 list | grep -i flask

# 6. Firewall activo
sudo ufw status

# 7. SSL certificate
sudo certbot certificates

# 8. Nginx activo
sudo systemctl status nginx

# 9. Acceso HTTP
curl -I https://staging.example.com

# 10. Datos accesibles
ls -la /var/www/release-dashboard/data/
```

---

## 10. Requisitos de Aplicación en Ejecución

### Si tienes Dashboards HTML (actuales)

✅ **Suficiente con**:
- Nginx o Apache para servir archivos estáticos
- No necesitas Python ejecutándose constantemente
- Archivos JSON en `/data/output/`

```bash
# Servir archivos estáticos
sudo systemctl start nginx
sudo systemctl enable nginx  # Autostart on boot
```

### Si añades Backend (Flask/FastAPI en futuro)

✅ **Necesitarás**:
- Python 3.10+ ejecutándose
- Gunicorn o uWSGI
- Supervisor o systemd para mantener proceso activo
- Nginx como reverse proxy

```bash
# Ejemplo con systemd
sudo nano /etc/systemd/system/release-dashboard.service

[Unit]
Description=Release Dashboard Application
After=network.target

[Service]
Type=notify
User=app
WorkingDirectory=/var/www/release-dashboard
ExecStart=/usr/bin/gunicorn --workers 4 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Habilitar
sudo systemctl enable release-dashboard
sudo systemctl start release-dashboard
```

---

## 11. Checklist de Deploymnet

Antes de desplegar en producción:

- [ ] VPS creado y accesible por SSH
- [ ] SO actualizado (`apt update && apt upgrade`)
- [ ] Python 3.10 instalado
- [ ] Directorios creados con permisos correctos
- [ ] SSH key configurada en GitHub Secrets
- [ ] Firewall habilitado y puertos abiertos
- [ ] SSL certificate instalado
- [ ] Nginx configurado y corriendo
- [ ] Health checks configurados
- [ ] Backups configurados
- [ ] Logs configurados
- [ ] Monitoreo configurado
- [ ] Prueba: SSH desde GitHub Actions
- [ ] Prueba: Acceso HTTP/HTTPS funcionando
- [ ] Prueba: Deploy automático funciona

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
# Verificar requirements.txt
cat /var/www/release-dashboard/requirements.txt

# Reinstalar dependencias
pip3 install -r /var/www/release-dashboard/requirements.txt

# Verificar en venv (si usas)
source /var/www/release-dashboard/venv/bin/activate
pip list
```

### "Nginx: 404 Not Found"

```bash
# Verificar configuración Nginx
sudo nginx -t

# Verificar directorios
ls -la /var/www/release-dashboard/

# Revisar logs
tail -f /var/log/nginx/error.log
```

### "Disk space full"

```bash
# Ver uso de disco
df -h

# Limpiar logs antiguos
sudo find /var/log -name "*.log" -mtime +30 -delete

# Limpiar backups antiguos
sudo find /var/backups/release-dashboard -type d -mtime +30 -exec rm -rf {} \;
```

---

**Fecha de Actualización**: 2026-05-14
**Versión**: 1.0
**Mantenedor**: DevOps Team
