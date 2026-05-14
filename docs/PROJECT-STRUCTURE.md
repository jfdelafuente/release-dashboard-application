# Estructura del Proyecto: Estático vs Python

Documento que especifica la separación clara entre:
- **Contenido Estático**: HTML, CSS, JS (sirve Nginx)
- **Código Python**: Conversores, scripts (ejecuta Python)
- **Datos**: CSVs, JSONs (directorio compartido)

---

## 📁 Estructura en Local (Desarrollo)

```
release-dashboard-application/
│
├── 📄 README.md
├── 📄 CLAUDE.md
├── 📄 VERSION
├── 📄 requirements.txt
│
├── 📁 src/                          # CÓDIGO FUENTE
│   ├── 📁 converters/               # ⚙️ PYTHON (ejecuta)
│   │   ├── convert_incidents.py
│   │   ├── convert_postmortems.py
│   │   ├── csv_to_json/
│   │   ├── build_index.py
│   │   └── __init__.py
│   │
│   ├── 📁 dashboards/               # 🌐 ESTÁTICO (sirve Nginx)
│   │   ├── dashboard-hub.html
│   │   ├── massive-incidents-dashboard.html
│   │   ├── postmortem-dashboard.html
│   │   └── 📁 assets/
│   │       ├── 📁 css/
│   │       │   ├── dashboard-hub.css
│   │       │   ├── massive-incidents.css
│   │       │   └── postmortem.css
│   │       └── 📁 js/
│   │           └── dashboard-hub.js
│   │
│   └── 📁 scripts/                  # ⚙️ PYTHON (utilidades)
│       ├── health-check.sh
│       ├── backup.sh
│       └── watch-and-convert.sh
│
├── 📁 data/                         # 📊 DATOS (compartido)
│   ├── 📁 input/                    # CSVs originales
│   │   ├── incidencias.csv
│   │   └── postmortem.csv
│   ├── 📁 output/                   # JSONs generados
│   │   ├── index.json
│   │   ├── incidencias.json
│   │   └── postmortem.json
│   ├── 📁 errors/                   # Reportes de errores
│   │   └── incidencias_errors.json
│   └── 📁 archive/                  # Histórico
│       └── YYYY/MM/...
│
├── 📁 docs/                         # 📚 DOCUMENTACIÓN
│   ├── README.md
│   ├── CI-CD.md
│   ├── VPS-REQUIREMENTS.md
│   ├── CSV-TO-JSON-WORKFLOW.md
│   └── PROJECT-STRUCTURE.md
│
├── 📁 specs/                        # 📋 ESPECIFICACIONES
│   ├── 001-csv-to-json-workflow/
│   └── ...
│
├── 📁 tests/                        # 🧪 TESTS
│   ├── test_converter.py
│   └── ...
│
└── 📁 .github/                      # 🔄 CI/CD
    └── workflows/
        ├── tests.yml
        ├── lint.yml
        └── deploy.yml
```

---

## 🖥️ Estructura en VPS (Producción/Staging)

```
/var/www/release-dashboard/         # Raíz de la aplicación
│
├── 📁 static/                       # 🌐 ESTÁTICO (sirve Nginx)
│   ├── 📁 dashboards/
│   │   ├── dashboard-hub.html
│   │   ├── massive-incidents-dashboard.html
│   │   ├── postmortem-dashboard.html
│   │   └── 📁 assets/
│   │       ├── 📁 css/
│   │       └── 📁 js/
│   │
│   └── 📁 images/                   # (si hay imágenes)
│       └── ...
│
├── 📁 app/                          # ⚙️ PYTHON (ejecuta)
│   ├── converters/
│   │   ├── convert_incidents.py
│   │   ├── convert_postmortems.py
│   │   ├── csv_to_json/
│   │   ├── build_index.py
│   │   └── __init__.py
│   │
│   ├── scripts/
│   │   ├── health-check.sh
│   │   └── backup.sh
│   │
│   └── __init__.py
│
├── 📁 data/                         # 📊 DATOS
│   ├── 📁 input/                    # CSVs colocados aquí
│   │   └── incidencias.csv
│   ├── 📁 output/                   # JSONs generados
│   │   ├── index.json
│   │   └── incidencias.json
│   ├── 📁 errors/
│   └── 📁 archive/
│
├── 📁 logs/                         # 📝 LOGS
│   ├── app.log
│   ├── supervisor.log
│   └── health-check.log
│
├── 📄 requirements.txt
├── 📄 VERSION
└── 📄 .env                          # Variables de entorno (NO en git)
```

---

## 🔄 Flujo de Deploy: Local → VPS

### Paso 1: Local (Desarrollo)

```
En tu máquina:

src/dashboards/*.html          (HTML estático)
src/converters/                (Python)
data/input/                    (CSVs para testing)
```

### Paso 2: Git Push → GitHub

```
Incluye en git:
  ✅ src/converters/
  ✅ src/dashboards/
  ✅ src/scripts/
  ✅ docs/
  ✅ requirements.txt

Excluye de git (.gitignore):
  ❌ data/input/
  ❌ data/output/
  ❌ data/errors/
  ❌ data/archive/
  ❌ logs/
  ❌ .env
```

### Paso 3: GitHub Actions Deploy

```yaml
# .github/workflows/deploy.yml

- name: Download artifact
  # Descarga source code (converters + dashboards)

- name: Deploy to VPS via SSH
  run: |
    scp -r src/dashboards/* app@vps:/var/www/release-dashboard/static/
    scp -r src/converters/* app@vps:/var/www/release-dashboard/app/
    scp -r src/scripts/* app@vps:/var/www/release-dashboard/app/scripts/

- name: Convert CSVs (en VPS)
  run: |
    ssh app@vps 'cd /var/www/release-dashboard && \
      python3 app/converters/convert_incidents.py data/input/*.csv && \
      python3 app/converters/convert_postmortems.py data/input/*.csv'
```

### Paso 4: VPS (Servidor)

```
/var/www/release-dashboard/
├── static/              ← Nginx sirve esto
├── app/                 ← Python ejecuta esto
├── data/
│   ├── input/          ← Usuario coloca CSVs aquí
│   ├── output/         ← Conversores generan JSONs aquí
│   └── errors/
└── logs/
```

---

## 🌐 Configuración Nginx (VPS)

```nginx
# /etc/nginx/sites-available/release-dashboard

server {
    listen 443 ssl http2;
    server_name example.com;

    # SSL
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # ============================================================
    # ESTÁTICO: Nginx sirve directamente (rápido)
    # ============================================================

    # Raíz de archivos estáticos
    root /var/www/release-dashboard/static;

    # Dashboards HTML
    location / {
        try_files $uri $uri/ =404;
        expires 1h;
    }

    # CSS
    location /assets/css/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # JavaScript
    location /assets/js/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Imágenes
    location /images/ {
        expires 365d;
        add_header Cache-Control "public, immutable";
    }

    # ============================================================
    # DATOS: Nginx sirve JSONs (generados por Python)
    # ============================================================

    location /data/ {
        alias /var/www/release-dashboard/data/;
        expires 1h;  # Cache de 1 hora (se actualiza frecuentemente)
        add_header Cache-Control "public";
    }

    # ============================================================
    # API: Si en futuro añades backend Python
    # ============================================================

    # location /api/ {
    #     proxy_pass http://127.0.0.1:8000;
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    #     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #     proxy_set_header X-Forwarded-Proto $scheme;
    # }

    # ============================================================
    # LOGS
    # ============================================================

    access_log /var/log/nginx/release-dashboard-access.log;
    error_log /var/log/nginx/release-dashboard-error.log;
}
```

---

## ⚙️ Cron Job para Conversión (VPS)

```bash
# /etc/cron.d/release-dashboard-converter

# Ejecutar conversores cada hora
0 * * * * app cd /var/www/release-dashboard && \
  python3 app/converters/convert_incidents.py data/input/*.csv && \
  python3 app/converters/convert_postmortems.py data/input/*.csv >> logs/converter.log 2>&1
```

---

## 📋 Tabla: Quién Sirve Qué

| Archivo/Directorio | Ubicación Local | Ubicación VPS | Quién Sirve | Cómo |
|-------------------|-----------------|---------------|-----------|------|
| `dashboard-hub.html` | `src/dashboards/` | `/var/www/release-dashboard/static/` | Nginx | `localhost:8000/dashboard-hub.html` |
| `dashboard-hub.js` | `src/dashboards/assets/js/` | `/var/www/release-dashboard/static/assets/js/` | Nginx | HTTP GET |
| `dashboard-hub.css` | `src/dashboards/assets/css/` | `/var/www/release-dashboard/static/assets/css/` | Nginx | HTTP GET |
| `convert_incidents.py` | `src/converters/` | `/var/www/release-dashboard/app/converters/` | Python | `python3 app/converters/convert_incidents.py` |
| `build_index.py` | `src/converters/` | `/var/www/release-dashboard/app/converters/` | Python | Llamado por conversor |
| `index.json` | `data/output/` | `/var/www/release-dashboard/data/output/` | Nginx | HTTP GET (generado por Python) |
| `incidencias.json` | `data/output/` | `/var/www/release-dashboard/data/output/` | Nginx | HTTP GET (generado por Python) |
| `incidencias.csv` | `data/input/` | `/var/www/release-dashboard/data/input/` | - | Colocado por usuario |

---

## 🔐 Permisos en VPS

```bash
# Nginx puede leer estático
sudo chown -R www-data:www-data /var/www/release-dashboard/static/
sudo chmod -R 755 /var/www/release-dashboard/static/

# Python puede leer/escribir datos
sudo chown -R app:app /var/www/release-dashboard/app/
sudo chown -R app:app /var/www/release-dashboard/data/
sudo chmod -R 755 /var/www/release-dashboard/app/
sudo chmod -R 755 /var/www/release-dashboard/data/
sudo chmod -R 755 /var/www/release-dashboard/data/input
sudo chmod -R 755 /var/www/release-dashboard/data/output

# Logs pueden escribir app
sudo chown -R app:app /var/www/release-dashboard/logs/
sudo chmod -R 755 /var/www/release-dashboard/logs/
```

---

## 📦 El Archivo `.env` (NO en Git)

Solo en VPS, no en git:

```bash
# /var/www/release-dashboard/.env

FLASK_ENV=production
DEBUG=False
DATA_DIR=/var/www/release-dashboard/data
STATIC_DIR=/var/www/release-dashboard/static
LOG_DIR=/var/www/release-dashboard/logs
APP_DIR=/var/www/release-dashboard/app
```

---

## 🚀 Diferencia: Local vs VPS

### Local (Desarrollo)

```
python -m http.server 8000
    ↓
Sirve TODO desde raíz del proyecto:
  - src/dashboards/*.html       (estático)
  - src/converters/*.py         (no sirve, solo ejecutas)
  - data/output/*.json          (estático, servido por http.server)
```

### VPS (Producción)

```
Nginx en puerto 80/443
    ↓
    ├─ Estático: /var/www/release-dashboard/static/
    │   ├─ dashboards/*.html
    │   └─ assets/css/, /js/
    │
    └─ Datos: /var/www/release-dashboard/data/output/
        └─ index.json, *.json

Python ejecutándose por cron/supervisor
    ↓
    ├─ Lee: /var/www/release-dashboard/data/input/*.csv
    └─ Escribe: /var/www/release-dashboard/data/output/*.json
```

---

## 📝 Archivos a Actualizar en VPS

Cuando haces deploy (push → GitHub Actions → VPS):

```bash
# Estos se copian al VPS
DEPLOY:
  src/dashboards/          → /var/www/release-dashboard/static/
  src/converters/          → /var/www/release-dashboard/app/
  src/scripts/             → /var/www/release-dashboard/app/scripts/
  requirements.txt         → /var/www/release-dashboard/
  VERSION                  → /var/www/release-dashboard/

# Estos NO se tocan (data del usuario)
NO DEPLOY:
  data/input/*             (usuario coloca)
  data/output/*            (Python genera)
  data/errors/*            (Python genera)
  logs/*                   (Python escribe)
  .env                     (secrets del server)
```

---

## ✅ Checklist: Verificar Separación Correcta

### En Local

- [ ] `src/dashboards/` contiene solo HTML, CSS, JS
- [ ] `src/converters/` contiene solo código Python
- [ ] `data/` está en `.gitignore`
- [ ] `requirements.txt` está en raíz

### En VPS

- [ ] `/var/www/release-dashboard/static/` = HTML, CSS, JS (lee Nginx)
- [ ] `/var/www/release-dashboard/app/` = código Python (ejecuta app user)
- [ ] `/var/www/release-dashboard/data/` = datos (lee/escribe app user)
- [ ] Nginx apunta a `/var/www/release-dashboard/static/` como root
- [ ] Cron job ejecuta Python contra `/var/www/release-dashboard/data/`

---

## 🎯 Resumen

| Aspecto | Responsable |
|--------|-----------|
| Servir HTML, CSS, JS | **Nginx** (rápido, estático) |
| Ejecutar conversores | **Python** (cron job o CI/CD) |
| Leer/escribir datos | **Python** |
| Servir JSONs generados | **Nginx** (desde `/data/output/`) |
| Servir index.json | **Nginx** (generado por Python) |

**Beneficio**:
- Nginx es rápido para estático
- Python ejecuta solo cuando necesita
- Separación clara de responsabilidades
- Fácil de debuggear y mantener

---

**Fecha de Actualización**: 2026-05-14
**Versión**: 1.0
