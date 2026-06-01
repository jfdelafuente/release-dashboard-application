# Release Dashboard Application

Aplicación web interactiva para análisis y visualización de incidencias masivas y postmortems.

**Dashboard Hub** (`dashboards/src/dashboard-hub.html`) es el **punto de acceso principal**. Carga automáticamente todos los datos desde `data/output/` y proporciona KPIs en tiempo real.

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

### 1️⃣ Coloca tus CSVs en `data/input/`

```
data/input/
├── incidencias.csv         (para Massive Incidents Dashboard)
└── postmortem.csv          (para Postmortem Dashboard)
```

### 2️⃣ Ejecuta los Conversores (necesario para generar JSONs)

**Convertir Incidencias Masivas**
```batch
# Windows
converters/scripts/bin/convert_incidents.bat ../data/input/incidencias.csv

# Linux/Mac
./converters/scripts/bin/convert_incidents.sh ../data/input/incidencias.csv
```

**Convertir Postmortems** (necesario para datos postmortem)
```batch
# Windows
converters/scripts/bin/convert_postmortems.bat ../data/input/postmortem.csv

# Linux/Mac
./converters/scripts/bin/convert_postmortems.sh ../data/input/postmortem.csv
```

Los JSONs se generan en `data/output/` e `index.json` se actualiza automáticamente.

### 3️⃣ Abre el Dashboard Hub

**Opción A: Con Live Server** (recomendado)
- En VSCode: Click derecho en `dashboards/index.html` → "Open with Live Server"

**Opción B: Con Python**
```bash
python -m http.server 8000
# Luego abre: http://localhost:8000/dashboards/
```

### 4️⃣ Dashboard Hub carga automáticamente los datos

- 📊 **KPIs en tiempo real** de incidencias masivas y postmortems
- 🔗 Navega a **dashboards especializados**:
  - Massive Incidents Dashboard (gráficas temporales, filtros)
  - Postmortem Dashboard (análisis por despliegues PAP/MESA)

---

## 📦 Scripts de Conversión

Los scripts de conversión están en [`converters/scripts/bin/`](converters/scripts/bin/) y son **necesarios** para generar los JSONs que el Dashboard Hub consume:

| Script | Propósito | Entrada |
|--------|-----------|---------|
| `convert_incidents.bat/sh` | Convierte incidencias masivas a JSON | `data/input/*.csv` |
| `convert_postmortems.bat/sh` | Convierte postmortems a JSON | `data/input/*.csv` |

**Características:**
- ✅ Auto-detección de encoding (UTF-8, Windows-1252, Latin-1, ISO-8859-15)
- ✅ Auto-detección de delimitadores (coma, punto y coma, tabulación)
- ✅ Normalización de campos automática
- ✅ Reporte de errores detallado
- ✅ Estadísticas de conversión
- ✅ KPIs pre-calculadas en metadata
- ✅ 264 tests (86% code coverage)

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
// En el Dashboard Hub
const result = JSON.parse(massiveIncidentsJSON);
const metadata = result._metadata;

console.log(`Total incidencias: ${metadata.kpis.total}`);
console.log(`Incidencias pendientes: ${metadata.kpis.pending}`);
console.log(`Tendencia 7 días: ${metadata.kpis.trend_7d}%`);
```

---

## 📋 Requisitos

- **Python 3.6+**
- **Sin dependencias externas** (usa librerías estándar)

---

## 📚 Documentación

Para más información, consulta:

### Guías Principales
| Documento | Contenido |
|-----------|-----------|
| **[docs/QUICKSTART.md](docs/QUICKSTART.md)** | Setup completo en 5 minutos |
| **[docs/README.md](docs/README.md)** | Índice de toda la documentación |
| **[docs/API.md](docs/API.md)** | Referencia técnica de los conversores |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Solución de problemas comunes |

### Optimización & Conversores
| Documento | Contenido |
|-----------|-----------|
| **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** | Decisiones de optimización, benchmarks, análisis de cuello de botella |
| **[docs/TEST_STRUCTURE.md](docs/TEST_STRUCTURE.md)** | Organización de tests por funcionalidad, cómo ejecutar tests específicos |
| **[docs/TEST_STRUCTURE_DIAGRAM.txt](docs/TEST_STRUCTURE_DIAGRAM.txt)** | Diagrama visual de la jerarquía de tests |
| **[docs/TESTING_BEST_PRACTICES.md](docs/TESTING_BEST_PRACTICES.md)** | Guía completa de pytest fixtures, refactorización, y aislamiento |

### Especificaciones del Feature
| Documento | Contenido |
|-----------|-----------|
| **[specs/006-optimize-csv-converters/](specs/006-optimize-csv-converters/)** | Plan completo, especificación, desglose de tareas (80 tareas, 7 fases) |

---

## ✅ Estado del Proyecto

- **Tests**: ✅ 264 passing (86.13% coverage)
- **Dashboards**: ✅ Todos funcionales
- **Conversores**: ✅ Incidents + Postmortems
- **MVP**: ✅ Completamente validado

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

Los tests están organizados en una estructura híbrida por funcionalidad y tipo de conversor:

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
│   ├── converters/         # Conversor CSV→JSON general
│   └── postmortem/         # Conversor postmortem
└── e2e/                    # Tests end-to-end
    └── performance/        # Benchmarks y límites
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
├── src/dashboards/              # Dashboards (HTML/CSS/JS)
│   ├── dashboard-hub.html       # Principal dashboard
│   ├── massive-incidents-dashboard.html
│   ├── postmortem-dashboard.html
│   └── assets/                  # CSS y JavaScript
├── src/converters/              # Scripts Python de conversión
│   ├── convert_incidents.py
│   └── convert_postmortems.py
├── scripts/bin/                 # Scripts wrapper (batch + shell)
│   ├── convert_incidents.bat/sh
│   └── convert_postmortems.bat/sh
├── data/                        # Almacenamiento de datos (git-ignored)
│   ├── input/                   # CSVs de entrada
│   ├── output/                  # JSONs generados
│   └── errors/                  # Reportes de error
├── tests/                       # Suite de tests
├── docs/                        # Documentación
└── config/                      # Configuración
```

---

## 💡 Flujo de Datos

```
CSV Files (data/input/)
    ↓
convert_incidents.bat/sh  +  convert_postmortems.bat/sh
    ↓
JSON Files (data/output/)
    ↓
build_index.py (genera index.json)
    ↓
Dashboard Hub (auto-carga)
    ↓
KPIs + Dashboards Especializados
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

**Última actualización**: 2026-05-14
