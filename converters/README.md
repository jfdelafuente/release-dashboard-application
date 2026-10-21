# Converters & Report Generators

Módulo backend en Python para el procesamiento, validación y normalización de datos (CSV a JSON) y generación automatizada de informes ejecutivos en presentaciones PowerPoint (`.pptx`).

---

## 🏛️ Arquitectura: Motor (`src/`) vs Interfaz de Consola (`cli/`)

El módulo sigue una estricta separación de responsabilidades:

```text
Usuario / Web Server (serve_app.py) / CI-CD
                   │
                   ▼
       ┌────────────────────────┐
       │     converters/cli/    │  <- Interfaces de consola, orquestación,
       │   (Ejecutables / CLIs) │     parámetros, archivado e interactividad
       └───────────┬────────────┘
                   │ invoca
                   ▼
       ┌────────────────────────┐
       │     converters/src/    │  <- Lógica de negocio pura (agnóstica a consola),
       │  (Librerías / Motores) │     parseo, normalización, validación, PPTX
       └────────────────────────┘
```

1. **`src/` (Core Libraries)**: Contiene los algoritmos, validaciones, cálculos matemáticos de KPIs, parsers y constructores de presentaciones. No gestiona argumentos de línea de comandos ni imprime directamente a consola.
2. **`cli/` (Command Line Interfaces)**: Scripts delgados ejecutables (`argparse`/`sys.argv`) que gestionan la interacción con el usuario o con el servidor web (`serve_app.py`), administran el histórico en `data/archive/`, controlan códigos de salida (`exit codes`) y formatean la salida por terminal.

---

## 📂 Estructura de Directorios

```text
converters/
├── cli/                  # Herramientas ejecutables de línea de comandos
│   ├── build_index.py               # Genera catálogo data/output/index.json
│   ├── cleanup_output.py            # Limpieza y archivado en data/archive/
│   ├── convert_incidents.py         # Conversión de incidencias masivas
│   ├── convert_postmortems.py       # Conversión de postmortems de releases
│   ├── generate_executive_report.py # Generación PPTX de informe ejecutivo puntual
│   ├── generate_postmortem_report.py# Generación PPTX de postmortem de release
│   ├── upload_csv.py                # Enrutador único para subidas desde la web
│   └── validate_kpis.py             # Auditoría y verificación de paridad de KPIs
│
├── src/                  # Motores de negocio y librerías reutilizables
│   ├── csv_to_json/      # Módulo de ingesta y normalización de datos
│   │   ├── converter.py             # Motor CsvToJsonConverter (incidencias)
│   │   ├── postmortem_converter.py  # Motor PostmortemConverter (releases)
│   │   ├── delimiter.py             # Detección automática de delimitador (, ; \t)
│   │   ├── encoding.py              # Detección de encoding (UTF-8, Latin-1, CP1252...)
│   │   ├── normalizers.py           # Normalización de fechas, estados y grupos
│   │   ├── schemas.py               # Esquemas y cálculo de KPIs para masivas
│   │   ├── postmortem_schemas.py    # Esquemas y cálculo de KPIs para postmortem
│   │   └── validators.py            # Reglas de validación de campos
│   │
│   └── report_generator/ # Módulo de generación de informes y presentaciones (.pptx)
│       ├── assets/                  # Plantillas (.pptx) y recursos corporativos
│       ├── chart_utils.py           # Utilidades gráficas y paleta Orange
│       ├── confluence_parser.py     # Parser HTML/Confluence para postmortems
│       ├── data_loader.py           # Cargador de datos de releases
│       ├── executive_models.py      # Modelos de datos para informes ejecutivos
│       ├── executive_paths.py       # Resolución de rutas de informes ejecutivos
│       ├── executive_report_builder.py # Constructor PPTX informe ejecutivo Orange
│       ├── kpi_calculator.py        # Cálculo de los 8 KPIs globales
│       ├── paths.py                 # Resolución de rutas y nombres seguros
│       ├── postmortem_charts.py     # Gráficas Plotly para postmortem
│       ├── pptx_builder.py          # Constructor base de presentaciones PPTX
│       ├── release_kpis_charts.py   # Gráficas Plotly de KPIs de release
│       └── release_kpis_data.py     # Lector de datos históricos de releases
│
├── scripts/bin/          # Lanzadores rápidos para Windows (.bat) y Linux/Mac (.sh)
│   ├── convert_incidents.bat / .sh
│   └── convert_postmortems.bat / .sh
│
├── tests/                # Suite de pruebas automatizadas (+580 tests)
│   ├── unit/             # Pruebas unitarias de parsers, normalizadores y esquemas
│   ├── integration/      # Pruebas de integración con I/O de ficheros
│   ├── e2e/              # Pruebas extremo a extremo y rendimiento
│   └── conftest.py       # Fixtures y configuración de pytest
│
├── docs/                 # Documentación técnica y guías de arquitectura
├── specs/                # Especificaciones funcionales de features
├── requirements.txt      # Dependencias de producción
├── requirements-dev.txt  # Dependencias para testing y desarrollo
└── pytest.ini            # Configuración de pruebas
```

---

## 🛠️ Herramientas CLI en Detalle (`cli/`)

| Script CLI | Motor Asociado en `src/` | Propósito Principal |
| :--- | :--- | :--- |
| **`convert_incidents.py`** | `src/csv_to_json/converter.py` | Convierte CSVs de **incidencias masivas** a JSON con KPIs. Archiva versiones anteriores en `data/archive/` y actualiza `index.json`. |
| **`convert_postmortems.py`** | `src/csv_to_json/postmortem_converter.py` | Convierte CSVs de **postmortems** agrupando por `--release-name`, calculando métricas de resolución y actualizando el índice. |
| **`upload_csv.py`** | N/A (Router de CLIs) | **Enrutador web**: llamado por el servidor backend al recibir un archivo desde la UI para despachar la ejecución a `convert_incidents.py` o `convert_postmortems.py`. |
| **`generate_executive_report.py`** | `src/report_generator/executive_report_builder.py` | Genera una presentación PPTX ejecutiva de **una incidencia concreta** a partir de Confluence o un archivo HTML/texto (Feature 010). |
| **`generate_postmortem_report.py`** | `src/report_generator/pptx_builder.py` | Genera el informe PPTX completo de **una release** con gráficas de rendimiento generadas mediante Plotly. |
| **`build_index.py`** | N/A (Catálogo) | Escanea `data/output/` y genera `index.json` que alimenta el Dashboard Hub con todos los datasets disponibles. |
| **`cleanup_output.py`** | N/A (Mantenimiento) | Traslada versiones obsoletas de `data/output/` a `data/archive/` sin pérdida de información. |
| **`validate_kpis.py`** | `src/csv_to_json/schemas.py` | Comprueba y valida la paridad matemática de los KPIs calculados en Python frente a la implementación en JS. |

---

## 🚀 Instalación y Requisitos

Requiere **Python 3.10+**.

```bash
cd converters

# Dependencias de producción (conversión y PPTX)
pip install -r requirements.txt

# Dependencias para desarrollo y testing (pytest, coverage...)
pip install -r requirements-dev.txt
```

---

## 💻 Guía de Uso

### 1. Ingesta de Incidencias Masivas
```bash
# Mediante el CLI directamente:
python cli/convert_incidents.py data/input/incidencias.csv -o data/output/

# O con el lanzador rápido:
./scripts/bin/convert_incidents.bat data/input/incidencias.csv  # Windows
./scripts/bin/convert_incidents.sh data/input/incidencias.csv   # Linux / Mac
```

### 2. Ingesta de Postmortem por Release
```bash
python cli/convert_postmortems.py data/input/postmortem.csv --release-name "2026R7"
```

### 3. Generación de Informes Ejecutivos PowerPoint (.pptx)
```bash
# A partir de una referencia de incidencia y URL de Confluence:
python cli/generate_executive_report.py --ref 2606S77393 --url "https://confluence.si.orange.es/..."

# A partir de un archivo exportado HTML local:
python cli/generate_executive_report.py --ref 2606S77393 --file postmortem.html --title "Caída IVR"
```

### 4. Generación de Informe PPT de Release
```bash
# Para una release específica:
python cli/generate_postmortem_report.py 2026R7

# Para todas las releases disponibles:
python cli/generate_postmortem_report.py --all
```

### 5. Actualización del Catálogo del Dashboard Hub
```bash
python cli/build_index.py data/output/
```

### 6. Uso como Librería en Python
Aunque el uso ordinario se realiza vía CLI o scripts lanzadores, los motores pueden integrarse directamente en código Python:

```python
from csv_to_json.converter import CsvToJsonConverter
from csv_to_json.postmortem_converter import PostmortemConverter

# Instanciar y convertir archivo de incidencias masivas
converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path="data/input/incidencias.csv",
    output_path="data/output/incidencias.json",
    error_path="data/errors/incidencias_errors.json"
)

# Convertir archivo postmortem agrupado por release
pm_converter = PostmortemConverter()
success_pm, report_pm = pm_converter.convert_file(
    input_path="data/input/postmortem.csv",
    output_path="data/output/postmortem.json",
    release_name="2026R7"
)
```

---

## 📄 Contrato de Datos (JSON Output)

Los conversores estructuran la salida JSON con el siguiente esquema estándar (formato *Envelope*):

```json
{
  "_metadata": {
    "type": "massive" | "postmortem",
    "version": "1.0",
    "created": "2026-10-14T10:00:00",
    "encoding_detected": "UTF-8",
    "delimiter_detected": ";",
    "record_count": 120,
    "release_name": "2026R7",
    "kpis": {
      "total": 120,
      "pending": 15,
      "trend_7d": -5.2,
      "trend_15d": 2.1,
      "trend_30d": 10.4
    }
  },
  "data": [
    {
      "ID de incidencia": "INC000003884945",
      "Descripción": "Corte de servicio en pasarela...",
      "Estatus": "Cerrado",
      "Fecha de envío": "02/01/2026 8:14 a",
      "Grupo asignado": "CEP CAU AGI",
      "Urgencia": "Alta",
      "Impacto": "Masiva",
      "Fecha de última resolución": "12/01/2026 8:24 a"
    }
  ]
}
```

---

## 🧪 Testing y Calidad

El módulo cuenta con una suite completa de más de 580 pruebas automatizadas con un tiempo de ejecución inferior a 15 segundos:

```bash
# Situarse siempre en converters antes de ejecutar pytest
cd converters

# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar tests unitarios solamente
pytest tests/unit/ -v

# Ejecutar tests de integración y E2E
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Ejecutar en paralelo aprovechando aislamiento por tmp_path
pytest tests/ -n auto

# Medir cobertura de código
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 📚 Documentación Adicional

- [Arquitectura Global del Sistema](../docs/ARCHITECTURE.md)
- [Flujo Canónico CSV a JSON](../docs/CSV-TO-JSON-WORKFLOW.md)
- [Guía de Rendimiento y Benchmarks](docs/PERFORMANCE.md)
- [Estructura de la Suite de Pruebas](docs/TEST_STRUCTURE.md)
- [Buenas Prácticas de Testing (Aislamiento y tmp_path)](docs/TESTING_BEST_PRACTICES.md)
- [Diagrama de la Suite de Tests](docs/TEST_STRUCTURE_DIAGRAM.txt)
- Especificaciones: [001 Workflow](specs/001-csv-to-json-workflow/) | [004 Postmortem](specs/004-postmortem-converter/) | [010 Executive Report](../specs/010-incident-executive-report/)
