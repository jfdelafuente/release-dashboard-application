# Guía de Administrador - Sistema de Carga CSV para Release Dashboard

**Versión**: 1.0
**Fecha**: 2 de junio de 2026
**Idioma**: Español

## Tabla de Contenidos

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación](#instalación)
3. [Configuración](#configuración)
4. [Estructura de Directorios](#estructura-de-directorios)
5. [Cron Job de Conversión](#cron-job-de-conversión)
6. [Monitoreo y Logs](#monitoreo-y-logs)
7. [Mantenimiento](#mantenimiento)
8. [Solución de Problemas](#solución-de-problemas)
9. [Recuperación ante Fallos](#recuperación-ante-fallos)
10. [Seguridad](#seguridad)

---

## Requisitos del Sistema

### Hardware Mínimo

- **CPU**: 2 cores @ 2.0 GHz
- **RAM**: 4 GB mínimo, 8 GB recomendado
- **Disco**: 100 GB disponible (ajusta según volumen de datos)
- **Conexión**: 100 Mbps

### Software Requerido

```
✅ Python 3.8+
✅ FastAPI 0.95+
✅ Node.js 14+ (para frontend)
✅ Cron (Linux/Mac) o Task Scheduler (Windows)
✅ Git 2.25+
```

### Navegadores Compatibles (Users)

- Google Chrome 90+
- Mozilla Firefox 88+
- Apple Safari 14+
- Microsoft Edge 90+

---

## Instalación

### Paso 1: Preparar el Servidor

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv git -y

# Install Node.js (for frontend build)
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install nodejs -y
```

### Paso 2: Clonar el Repositorio

```bash
cd /opt
sudo git clone https://github.com/yourorg/release-dashboard.git
cd release-dashboard
sudo chown -R ubuntu:ubuntu .
```

### Paso 3: Configurar Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Paso 4: Configurar Frontend

```bash
cd ../dashboards

# Install frontend dependencies (if using npm build)
npm install

# Build frontend (if applicable)
npm run build
```

### Paso 5: Crear Directorios de Datos

```bash
cd ../data

# Create required directories
mkdir -p input
mkdir -p output
mkdir -p errors
mkdir -p archive

# Set proper permissions
chmod 755 input output errors archive
chmod 644 *.json  # If there are any existing JSON files
```

### Paso 6: Configurar Variables de Entorno

```bash
cd /opt/release-dashboard/backend

# Create .env file
cat > .env << EOF
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# File Paths
TEMP_UPLOAD_DIR=../data/temp_uploads
DATA_INPUT_DIR=../data/input
DATA_OUTPUT_DIR=../data/output
ERROR_LOG_DIR=../logs

# Upload Settings
MAX_FILE_SIZE=524288000  # 500MB
ALLOWED_EXTENSIONS=.csv

# CORS
CORS_ORIGINS=["http://localhost:5000", "https://yourdomain.com"]

# Cron Job
CRON_ENABLED=true
CRON_SCHEDULE=*/5 * * * *  # Every 5 minutes
EOF

# Restrict permissions
chmod 600 .env
```

### Paso 7: Iniciar el Servicio Backend

```bash
# Run manually first to verify
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Should see:
# Uvicorn running on http://0.0.0.0:8000
# Application startup complete
```

### Paso 8: Servir el Frontend

Option A - Using Python SimpleHTTPServer:
```bash
cd ../dashboards
python3 -m http.server 5000

# Access at http://localhost:5000
```

Option B - Using Nginx (Production):
```bash
# Install Nginx
sudo apt install nginx -y

# Create config (see Nginx configuration below)
sudo nano /etc/nginx/sites-available/dashboard

# Enable site
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## Configuración

### Nginx Configuration (Production)

```nginx
# /etc/nginx/sites-available/dashboard

server {
    listen 80;
    server_name dashboard.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.example.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/dashboard.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Frontend - Static files
    location / {
        root /opt/release-dashboard/dashboards;
        try_files $uri $uri/ =404;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # API - Backend proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Upload size limit
        client_max_body_size 500M;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Data files - Static
    location /data/output/ {
        root /opt/release-dashboard;
        autoindex off;
        expires 30m;
    }
}
```

### Systemd Service (Auto-start)

```bash
# Create service file
sudo tee /etc/systemd/system/release-dashboard.service << EOF
[Unit]
Description=Release Dashboard Backend Service
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/opt/release-dashboard/backend
Environment="PATH=/opt/release-dashboard/backend/venv/bin"
ExecStart=/opt/release-dashboard/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable release-dashboard.service
sudo systemctl start release-dashboard.service

# Check status
sudo systemctl status release-dashboard.service
```

---

## Estructura de Directorios

```
release-dashboard/
├── backend/
│   ├── venv/                    # Virtual environment
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   └── upload.py         # Upload endpoints
│   │   ├── services/             # Business logic
│   │   ├── validators/           # Validation rules
│   │   ├── utils/                # Utilities
│   │   └── upload_logging/       # Logging
│   ├── tests/                    # Test files
│   ├── requirements.txt
│   └── .env                      # Configuration
├── dashboards/
│   ├── massive-incidents-dashboard.html
│   ├── postmortem-dashboard.html
│   ├── dashboard-portal.html
│   ├── js/
│   │   ├── auto-refresh-manager.js
│   │   ├── config.js
│   │   ├── notifications.js
│   │   └── upload-modal.js
│   └── css/
│       ├── auto-refresh.css
│       └── upload-modal.css
├── data/
│   ├── input/                   # CSV files waiting for conversion
│   ├── output/                  # Converted JSON files
│   ├── errors/                  # Error reports
│   ├── temp_uploads/            # Temporary upload files
│   └── archive/                 # Old files (optional)
├── docs/                        # Documentation
├── logs/                        # Log files
└── scripts/                     # Helper scripts
    ├── convert_csv.py           # CSV conversion script
    └── deploy.sh                # Deployment script
```

---

## Cron Job de Conversión

### Configurar Cron para Conversión Automática

```bash
# Edit crontab
crontab -e

# Add this line to run conversion every 5 minutes
*/5 * * * * /opt/release-dashboard/scripts/run_converter.sh

# Or run every minute (more responsive)
* * * * * /opt/release-dashboard/scripts/run_converter.sh

# Check cron logs
sudo journalctl -u cron --no-pager | tail -20
```

### Script de Conversión (run_converter.sh)

```bash
#!/bin/bash
# /opt/release-dashboard/scripts/run_converter.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"
INPUT_DIR="$BACKEND_DIR/../data/input"
OUTPUT_DIR="$BACKEND_DIR/../data/output"
ERRORS_DIR="$BACKEND_DIR/../data/errors"
LOGS_DIR="$BACKEND_DIR/../logs"

# Create directories if needed
mkdir -p "$OUTPUT_DIR" "$ERRORS_DIR" "$LOGS_DIR"

# Activate virtual environment
source "$BACKEND_DIR/venv/bin/activate"

# Run converter
cd "$BACKEND_DIR"
python -m src.converters.csv_to_json.converter \
    --input-dir "$INPUT_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --error-dir "$ERRORS_DIR" \
    --log-file "$LOGS_DIR/converter_$(date +%Y%m%d_%H%M%S).log" \
    >> "$LOGS_DIR/cron.log" 2>&1

echo "[$(date)] Conversion cycle completed" >> "$LOGS_DIR/cron.log"
```

### Monitorear Cron Executions

```bash
# View cron logs
sudo tail -f /var/log/syslog | grep CRON

# Check conversion history
tail -50 /opt/release-dashboard/logs/cron.log

# Test cron manually
cd /opt/release-dashboard/scripts
bash run_converter.sh
```

---

## Monitoreo y Logs

### Ubicación de Logs

```
logs/
├── cron.log                 # Cron execution logs
├── errors_detailed.log      # Detailed error logs
├── converter.log            # CSV conversion logs
└── app.log                  # FastAPI application logs
```

### Ver Logs en Tiempo Real

```bash
# Backend logs
tail -f /opt/release-dashboard/backend/logs/app.log

# Conversion logs
tail -f /opt/release-dashboard/logs/cron.log

# Error logs
tail -f /opt/release-dashboard/logs/errors_detailed.log

# All logs together
tail -f /opt/release-dashboard/logs/*.log
```

### Monitoreo Básico con Scripts

```bash
# Check if backend is running
ps aux | grep "[p]ython.*main:app"

# Check disk usage
df -h /opt/release-dashboard/data/

# Check recent conversions
ls -lht /opt/release-dashboard/data/output/ | head -10

# Count pending uploads
ls /opt/release-dashboard/data/input/ | wc -l

# Check error reports
ls -lht /opt/release-dashboard/data/errors/ | head -10
```

---

## Mantenimiento

### Limpiar Archivos Temporales

```bash
# Remove temp files older than 24 hours
find /opt/release-dashboard/data/temp_uploads/ -type f -mtime +1 -delete

# Archive old input files (after successful conversion)
mv /opt/release-dashboard/data/input/processed_* /opt/release-dashboard/data/archive/
```

### Hacer Backup de Datos

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/release-dashboard"
DATA_DIR="/opt/release-dashboard/data"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup converted data
tar -czf "$BACKUP_DIR/output_$DATE.tar.gz" "$DATA_DIR/output/"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/output_$DATE.tar.gz"
```

### Limpiar Logs Antiguos

```bash
# Remove logs older than 30 days
find /opt/release-dashboard/logs/ -type f -mtime +30 -delete

# Or use logrotate (better approach)
```

### Logrotate Configuration

```bash
# /etc/logrotate.d/release-dashboard

/opt/release-dashboard/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload release-dashboard > /dev/null 2>&1 || true
    endscript
}
```

---

## Solución de Problemas

### ❌ Backend no inicia

**Síntomas**: `Connection refused` cuando intentas acceder al API

**Solución**:
```bash
# Check if port 8000 is in use
lsof -i :8000

# Check backend logs
tail -50 /opt/release-dashboard/backend/app.log

# Restart backend
sudo systemctl restart release-dashboard.service

# Run manually to see errors
cd /opt/release-dashboard/backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### ❌ Conversion not happening

**Síntomas**: Archivos quedan en `data/input/` sin convertirse

**Solución**:
```bash
# Check if cron is running
systemctl status cron

# Test conversion script manually
bash /opt/release-dashboard/scripts/run_converter.sh

# Check converter logs
tail -100 /opt/release-dashboard/logs/cron.log

# Check permissions on data directories
ls -la /opt/release-dashboard/data/

# Should show ubuntu:ubuntu ownership and 755 permissions
```

### ❌ Upload fails with permission error

**Síntomas**: 403 error when confirming upload

**Solución**:
```bash
# Check directory permissions
ls -la /opt/release-dashboard/data/input/
ls -la /opt/release-dashboard/data/temp_uploads/

# Fix permissions (if needed)
sudo chown -R ubuntu:ubuntu /opt/release-dashboard/data/
sudo chmod -R 755 /opt/release-dashboard/data/

# Check disk space
df -h /opt/release-dashboard/data/
```

### ❌ Disk full error

**Síntomas**: 507 error, no space left on device

**Solución**:
```bash
# Check disk usage
du -sh /opt/release-dashboard/data/*

# Archive old converted files
mkdir -p /archive/$(date +%Y/%m)
mv /opt/release-dashboard/data/output/old_* /archive/$(date +%Y/%m)/

# Delete old error reports (after reviewing)
find /opt/release-dashboard/data/errors/ -type f -mtime +90 -delete

# Cleanup temp files
rm -f /opt/release-dashboard/data/temp_uploads/*

# If still full, check what's taking space
ls -lhS /opt/release-dashboard/data/
```

---

## Recuperación ante Fallos

### Backup y Restore

```bash
# Full backup
tar -czf release-dashboard_backup_$(date +%Y%m%d).tar.gz \
    /opt/release-dashboard/data/ \
    /opt/release-dashboard/backend/logs/

# Restore from backup
tar -xzf release-dashboard_backup_20260602.tar.gz -C /opt/
```

### Rollback de Versión

```bash
# If deployment goes wrong, rollback
cd /opt/release-dashboard
git log --oneline | head -10
git revert <commit-hash>  # Or use git reset

# Restart services
sudo systemctl restart release-dashboard.service
```

### Database Recovery (if applicable)

```bash
# If using database for metadata
mysqldump -u root -p release_dashboard > backup.sql

# Restore if needed
mysql -u root -p release_dashboard < backup.sql
```

---

## Seguridad

### Checklist de Seguridad

- [ ] ✅ Cambiar contraseñas default
- [ ] ✅ Desactivar SSH root login
- [ ] ✅ Instalar firewall (ufw, iptables)
- [ ] ✅ Habilitar HTTPS/SSL (Let's Encrypt)
- [ ] ✅ Configurar CORS restrictivo
- [ ] ✅ Implementar rate limiting
- [ ] ✅ Validar todos los uploads
- [ ] ✅ Sanitizar nombres de archivo
- [ ] ✅ Usar HTTPS para todas las comunicaciones
- [ ] ✅ Monitorear accesos a logs

### Firewall Configuration

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny everything else
sudo ufw default deny incoming
```

### File Permissions

```bash
# Secure permissions
chmod 644 /opt/release-dashboard/dashboards/html/*.html
chmod 644 /opt/release-dashboard/dashboards/js/*.js
chmod 755 /opt/release-dashboard/data/input/
chmod 755 /opt/release-dashboard/data/output/
chmod 600 /opt/release-dashboard/backend/.env
```

---

## Contacto y Soporte

**Problemas de Administración**: admin-support@example.com
**Reportar Security Issues**: security@example.com
**Documentación Técnica**: https://docs.example.com

---

**Última Actualización**: 2 de junio de 2026
**Versión**: 1.0
