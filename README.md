# Release Dashboard Application

Aplicación web para análisis y visualización de incidencias masivas y postmortems de release, con conversión automática de CSV a JSON.

**Portal** (`dashboards/dashboard-portal.html`) es el **punto de acceso principal**: enlaza a los dashboards de este repo (Incidencias Masivas, Postmortem/Release) y a los paneles de los repos hermanos (Reportes de Incidencias, Gestión de Problemas).

---

## 📦 Estructura: 2 Componentes Independientes

El proyecto está dividido en **2 partes claramente diferenciadas**:

| Componente | Ubicación | Descripción | Tecnología |
|-----------|-----------|-------------|-----------|
| **Converters** | [`converters/`](converters/) | Scripts de conversión CSV→JSON | Python 3.8+ |
| **Dashboards** | [`dashboards/`](dashboards/) | Visualización web de datos | HTML5/CSS3/JavaScript |

Cada componente puede funcionar **independientemente**.

---

## 🚀 Inicio Rápido (5 minutos)

### 1️⃣ Arranca el servidor local

```bash
python serve_app.py
# Abre: http://localhost:8000/dashboards/dashboard-portal.html
```

> ⚠️ **No uses `python -m http.server` ni Live Server.** Solo sirven
> archivos estáticos: no implementan `POST`, así que la subida de CSV
> desde el navegador falla con "Failed to fetch". `serve_app.py` añade el
> endpoint `/api/upload`, imprescindible para poder subir un CSV desde la
> interfaz.

### 2️⃣ Carga un CSV

**Opción A: Desde el navegador (recomendado)**

Cada dashboard (Incidencias Masivas, Postmortem) muestra una pantalla de
subida si no hay datos cargados: arrastra el CSV o haz clic para
seleccionarlo. El propio servidor lo guarda en `data/input/` y ejecuta el
conversor correspondiente automáticamente.

**Opción B: Manualmente, con los scripts de conversión**

```
data/input/
├── incidencias.csv         (para Incidencias Masivas)
└── postmortem.csv          (para Postmortem/Release)
```

```bash
# Windows
converters/scripts/bin/convert_incidents.bat data/input/incidencias.csv
converters/scripts/bin/convert_postmortems.bat data/input/postmortem.csv

# Linux/Mac
./converters/scripts/bin/convert_incidents.sh data/input/incidencias.csv
./converters/scripts/bin/convert_postmortems.sh data/input/postmortem.csv
```

Los JSONs se generan en `data/output/` e `index.json` se actualiza automáticamente.

### 3️⃣ Abre el Portal

Con `serve_app.py` corriendo, ve a `http://localhost:8000/dashboards/dashboard-portal.html` (o simplemente `/dashboards/`, que redirige ahí vía `dashboards/index.html`).

### 4️⃣ Los dashboards cargan automáticamente los datos más recientes

- **Incidencias Masivas** (`massive-incidents-dashboard.html`): evolución temporal, backlog, tendencias, filtros por estado/sistema/urgencia.
- **Postmortem / Release** (`postmortem-dashboard.html`): análisis por despliegue (PAP/MESA), KPIs de resolución.

Desde el Portal también se enlaza a **Reportes de Incidencias** y **Gestión de Problemas**, que son aplicaciones de los repos hermanos (`cso-incident-masivas-report` y el backend de gestión de problemas), no parte de este repositorio.

---

## 📦 Scripts de Conversión

Los scripts de conversión están en [`converters/scripts/bin/`](converters/scripts/bin/) y son la vía manual/batch para generar los JSONs (la vía normal desde el navegador ya los invoca automáticamente vía `serve_app.py` o el endpoint `/api/upload`):

| Script | Propósito | Entrada |
|--------|-----------|---------|
| `convert_incidents.bat/sh` | Convierte incidencias masivas a JSON | `data/input/*.csv` |
| `convert_postmortems.bat/sh` | Convierte postmortems a JSON | `data/input/*.csv` |

**Características:**
- ✅ Auto-detección de encoding (UTF-8, Windows-1252, Latin-1, ISO-8859-15)
- ✅ Auto-detección de delimitadores (coma, punto y coma, tabulación)
- ✅ Normalización de campos automática
- ✅ Reporte de errores detallado (en `data/errors/`)
- ✅ Estadísticas de conversión
- ✅ KPIs pre-calculadas en metadata
- ✅ Suite de tests con >80% de cobertura (ver [Testing](#-testing--calidad-de-código))

### Uso Programático en Python

**Convertir Incidencias Masivas:**
```python
import sys
from pathlib import Path

# Agregar converters/src al path
sys.path.insert(0, str(Path('converters/src')))

from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='data/input/incidencias.csv',
    output_path='data/output/incidencias-massive.json',
    error_report_path='data/errors/incidencias_errors.json'
)

print(f"Conversión exitosa: {success}")
print(f"Registros procesados: {report['stats']['successful']}/{report['stats']['total_records']}")
print(f"Encoding detectado: {report['encoding_detected']}")
```

**Convertir Postmortems:**
```python
import sys
from pathlib import Path

# Agregar converters/src al path
sys.path.insert(0, str(Path('converters/src')))

from csv_to_json.postmortem_converter import PostmortemConverter

converter = PostmortemConverter()
success, report = converter.convert_file(
    input_path='data/input/postmortem.csv',
    output_path='data/output/postmortem.json',
    error_report_path='data/errors/postmortem_errors.json'
)

print(f"Conversión exitosa: {success}")
print(f"Registros procesados: {report['stats']['successful']}/{report['stats']['total_records']}")
```

### Acceder a los KPIs en JavaScript

Una vez generados los JSONs, los dashboards acceden a los KPIs automáticamente:

```javascript
const result = JSON.parse(massiveIncidentsJSON);
const metadata = result._metadata;

console.log(`Total incidencias: ${metadata.kpis.total}`);
console.log(`Incidencias pendientes: ${metadata.kpis.pending}`);
console.log(`Tendencia 7 días: ${metadata.kpis.trend_7d}%`);
```

---

## 📋 Requisitos

- **Python 3.8+**
- **Sin dependencias externas** para los dashboards (usan librerías estándar del navegador + Plotly.js vía CDN)
- Ver [`converters/requirements.txt`](converters/requirements.txt) y [`converters/requirements-dev.txt`](converters/requirements-dev.txt) para dependencias de desarrollo/test de los converters

---

## 📚 Documentación

### Guías Principales
| Documento | Contenido |
|-----------|-----------|
| **[docs/QUICKSTART.md](docs/QUICKSTART.md)** | Setup completo |
| **[docs/README.md](docs/README.md)** | Índice de documentación |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Solución de problemas comunes |
| **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** | Entorno de desarrollo |
| **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | Procedimientos de despliegue |

### Converters (API, arquitectura, testing)
| Documento | Contenido |
|-----------|-----------|
| **[converters/docs/API.md](converters/docs/API.md)** | Referencia técnica de los conversores |
| **[converters/docs/ARCHITECTURE.md](converters/docs/ARCHITECTURE.md)** | Arquitectura del módulo de conversión |
| **[converters/docs/PERFORMANCE.md](converters/docs/PERFORMANCE.md)** | Decisiones de optimización, benchmarks |
| **[converters/docs/TEST_STRUCTURE.md](converters/docs/TEST_STRUCTURE.md)** | Organización de tests por funcionalidad |
| **[converters/docs/TESTING_BEST_PRACTICES.md](converters/docs/TESTING_BEST_PRACTICES.md)** | Guía de pytest fixtures y aislamiento |

### Especificaciones
| Documento | Contenido |
|-----------|-----------|
| **[converters/specs/006-optimize-csv-converters/](converters/specs/006-optimize-csv-converters/)** | Optimización de los conversores |
| **[converters/specs/004-postmortem-converter/](converters/specs/004-postmortem-converter/)** | Conversor de postmortem |
| **[converters/specs/001-csv-to-json-workflow/](converters/specs/001-csv-to-json-workflow/)** | Flujo CSV→JSON original |

---

## ✅ Estado del Proyecto

- **Tests**: ✅ passing (>80% coverage) — ver `converters/tests/`
- **Dashboards**: ✅ Portal, Incidencias Masivas y Postmortem/Release funcionales
- **Subida de CSV desde el navegador**: ✅ vía `serve_app.py` (`/api/upload`)
- **Conversores**: ✅ Incidencias masivas + Postmortems

---

## 🧪 Testing & Calidad de Código

### Ejecutar Tests

```bash
cd converters

# Todos los tests
pytest tests/

# Por categoría
pytest tests/unit/                    # Tests unitarios (pura lógica)
pytest tests/integration/             # Tests de integración (con I/O)
pytest tests/e2e/                     # Tests end-to-end (flujos completos)

# Por funcionalidad específica
pytest tests/unit/encoding/           # Solo tests de encoding
pytest tests/unit/normalizers/        # Solo tests de normalización
pytest tests/unit/validators/         # Solo tests de validación

# Con opciones útiles
pytest tests/ -v                      # Verbose (muestra cada test)
pytest tests/ -k "normalization"      # Filtra por patrón
pytest tests/ --cov=src --cov-report=html  # Genera reporte de coverage

# En paralelo (requiere pytest-xdist)
pip install pytest-xdist
pytest tests/ -n auto                 # Auto-detecta número de CPUs
```

### Estructura de Tests

```
converters/tests/
├── unit/                    # Tests de lógica pura (sin I/O)
│   ├── encoding/           # Detección de encoding
│   ├── delimiter/          # Detección de delimitadores
│   ├── normalizers/        # Normalización de datos
│   ├── validators/         # Validación de campos
│   ├── schemas/            # Estructuras de datos
│   └── derivation/         # Lógica derivada (Despliegue)
├── integration/             # Tests con I/O (archivos, CSV)
└── e2e/                     # Tests end-to-end (incluye benchmarks de performance)
```

Ver [converters/docs/TEST_STRUCTURE.md](converters/docs/TEST_STRUCTURE.md) para detalle completo.

### Calidad de Código

```bash
cd converters

# Linting (PEP 8)
pip install flake8
flake8 src/ cli/ --max-line-length=120

# Formatting
pip install black
black --check src/ cli/

# Import sorting
pip install isort
isort --check-only src/ cli/
```

---

## 🔧 Estructura del Proyecto

```
release-dashboard-application/
├── serve_app.py                  # Servidor local (dashboards + /api/upload)
├── dashboards/                   # Dashboards (HTML/CSS/JS)
│   ├── index.html                # Redirige a dashboard-portal.html
│   ├── dashboard-portal.html     # Portal principal
│   ├── massive-incidents-dashboard.html
│   ├── postmortem-dashboard.html
│   └── assets/                   # Logos e imágenes
├── converters/                   # Módulo Python de conversión CSV→JSON
│   ├── cli/                      # convert_incidents.py, convert_postmortems.py, build_index.py
│   ├── src/csv_to_json/          # Lógica de conversión (encoding, normalización, validación)
│   ├── scripts/bin/               # Wrappers .bat/.sh para los CLI
│   ├── tests/                    # Suite de tests (unit/integration/e2e)
│   ├── docs/                     # Documentación técnica de los converters
│   └── specs/                    # Especificaciones de features de los converters
├── data/                         # Almacenamiento de datos (git-ignored)
│   ├── input/                    # CSVs de entrada
│   ├── output/                   # JSONs generados + index.json
│   └── errors/                   # Reportes de error de conversión
├── scripts/                      # Scripts de operación (cron, generación batch)
├── docs/                         # Documentación general del proyecto
└── config/                       # Configuración
```

---

## 💡 Flujo de Datos

```
CSV (subido desde el navegador, o en data/input/)
    ↓
serve_app.py [/api/upload]  o  convert_incidents.py / convert_postmortems.py
    ↓
JSON (data/output/) + build_index.py → index.json
    ↓
Portal (dashboard-portal.html)
    ↓
Incidencias Masivas · Postmortem/Release
```

---

## 🔐 Seguridad

- ✅ Datos sensibles protegidos por `.gitignore`
- ✅ Configuración mediante variables de entorno
- ✅ Pre-commit hooks para evitar secrets en git
- ✅ Tests de validación automatizados

---

## 📞 Soporte

- **¿Cómo empiezo?** → [docs/QUICKSTART.md](docs/QUICKSTART.md)
- **¿Problemas?** → [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **¿Desarrollo?** → [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

**Última actualización**: 2026-07-09
