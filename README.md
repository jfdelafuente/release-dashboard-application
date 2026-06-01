# Release Dashboard Application

Aplicación web interactiva para análisis y visualización de incidencias masivas y postmortems.

**Dashboard Hub** (`src/dashboards/dashboard-hub.html`) es el **punto de acceso principal**. Carga automáticamente todos los datos desde `data/output/` y proporciona KPIs en tiempo real.

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
convert_incidents.bat data/input/incidencias.csv

# Linux/Mac
./convert_incidents.sh data/input/incidencias.csv
```

**Convertir Postmortems** (necesario para datos postmortem)
```batch
# Windows
convert_postmortems.bat data/input/postmortem.csv

# Linux/Mac
./convert_postmortems.sh data/input/postmortem.csv
```

Los JSONs se generan en `data/output/` e `index.json` se actualiza automáticamente.

### 3️⃣ Abre el Dashboard Hub

**Opción A: Con Live Server** (recomendado)
- En VSCode: Click derecho en `src/dashboards/dashboard-hub.html` → "Open with Live Server"

**Opción B: Con Python**
```bash
python -m http.server 8000
# Luego abre: http://localhost:8000/src/dashboards/dashboard-hub.html
```

### 4️⃣ Dashboard Hub carga automáticamente los datos

- 📊 **KPIs en tiempo real** de incidencias masivas y postmortems
- 🔗 Navega a **dashboards especializados**:
  - Massive Incidents Dashboard (gráficas temporales, filtros)
  - Postmortem Dashboard (análisis por despliegues PAP/MESA)

---

## 📦 Scripts de Conversión

Ambos conversores son **necesarios** para que el Dashboard Hub muestre toda la información:

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
from src.converters.csv_to_json import CsvToJsonConverter

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
from src.converters.csv_to_json.postmortem_converter import convertPostmortemCSV

success, records, kpis, metadata, errors = convertPostmortemCSV(
    input_path='data/input/postmortem.csv',
    output_path='data/output/postmortem.json',
    error_report_path='data/errors/postmortem_errors.json'
)

print(f"Postmortems procesados: {len(records)}")
print(f"KPIs Despliegue PAP - Resueltas: {kpis.dashboard_hub_kpis.pap_resueltas_percent}%")
print(f"KPIs Despliegue MESA - Resueltas: {kpis.dashboard_hub_kpis.mesa_resueltas_percent}%")
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

| Documento | Contenido |
|-----------|-----------|
| **[docs/QUICKSTART.md](docs/QUICKSTART.md)** | Setup completo en 5 minutos |
| **[docs/README.md](docs/README.md)** | Índice de toda la documentación |
| **[docs/API.md](docs/API.md)** | Referencia técnica de los conversores |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Solución de problemas comunes |

---

## ✅ Estado del Proyecto

- **Tests**: ✅ 264 passing (86.13% coverage)
- **Dashboards**: ✅ Todos funcionales
- **Conversores**: ✅ Incidents + Postmortems
- **MVP**: ✅ Completamente validado

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
