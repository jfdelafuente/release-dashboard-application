# CSV-to-JSON Converters

Conversores Python independientes para transformar archivos CSV de incidencias masivas y postmortems al formato JSON compatible con dashboards.

## 🚀 Características

- ✅ Auto-detección de encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- ✅ Auto-detección de delimitadores (coma, punto y coma, tabulación)
- ✅ Normalización automática de campos (Urgencia, Estatus, fechas)
- ✅ Validación de datos con reportes detallados
- ✅ KPI pre-calculadas en metadata
- ✅ 477 tests con cobertura de código

## 📦 Instalación

```bash
cd converters
pip install -r requirements.txt
```

Para desarrollo (incluye pytest, coverage, linting):
```bash
pip install -r requirements-dev.txt
```

## 🔧 Uso

### Convertir Incidencias Masivas

```bash
# Windows
./scripts/bin/convert_incidents.bat ../data/input/incidencias.csv

# Linux/Mac
./scripts/bin/convert_incidents.sh ../data/input/incidencias.csv
```

**Opciones disponibles:**
```bash
# Especificar output
./scripts/bin/convert_incidents.bat ../data/input/datos.csv -o ../data/output/custom.json

# Especificar error report
./scripts/bin/convert_incidents.bat ../data/input/datos.csv -e ../data/errors/errors.json

# Ver help
./scripts/bin/convert_incidents.bat --help
```

### Convertir Postmortems

```bash
# Windows
./scripts/bin/convert_postmortems.bat ../data/input/postmortem.csv

# Linux/Mac
./scripts/bin/convert_postmortems.sh ../data/input/postmortem.csv
```

### Generar Index para Dashboard Hub

```bash
python cli/build_index.py ../data/output/
```

## 📊 Salida

Los converters generan:

1. **JSON validado**: `../data/output/{nombre}-massive.json` o `{nombre}-postmortem.json`
   - Contiene registros validados y normalizados
   - Incluye `_metadata` con KPIs pre-calculadas

2. **Reporte de errores**: `../data/errors/{nombre}_errors.json`
   - Solo si hay registros inválidos
   - Incluye número de línea y detalles del error

3. **Index.json**: `../data/output/index.json`
   - Auto-generado por converters
   - Catalog de datasets disponibles para Dashboard Hub

## 🧪 Testing

### Ejecutar todos los tests

```bash
pytest tests/ -v
```

### Ejecutar por categoría

```bash
# Solo tests unitarios (lógica pura)
pytest tests/unit/ -v

# Solo tests de integración (con I/O)
pytest tests/integration/ -v

# Solo tests E2E y performance
pytest tests/e2e/ -v
```

### Con coverage

```bash
pytest tests/ --cov=src --cov-report=html
# Abre htmlcov/index.html para ver reporte visual
```

### En paralelo (más rápido)

```bash
pytest tests/ -n auto  # Auto-detecta número de CPUs
```

## 📚 Documentación

- [API Reference](docs/API.md) - Referencia técnica de los conversores
- [Architecture](docs/ARCHITECTURE.md) - Arquitectura interna
- [Performance Guide](docs/PERFORMANCE.md) - Optimizaciones y benchmarks
- [Test Structure](docs/TEST_STRUCTURE.md) - Organización de tests
- [Testing Best Practices](docs/TESTING_BEST_PRACTICES.md) - Guía de testing
- [Code Quality](docs/CODE_QUALITY.md) - Linting y formatting

## 📋 Especificaciones

- [001: CSV-to-JSON Workflow](specs/001-csv-to-json-workflow/) - Especificación completa
- [004: Postmortem Converter](specs/004-postmortem-converter/) - Conversor postmortem
- [006: Optimize CSV Converters](specs/006-optimize-csv-converters/) - Optimizaciones

## 🔌 Uso Programático

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='../data/input/datos.csv',
    output_path='../data/output/datos-massive.json',
    error_report_path='../data/errors/datos_errors.json'
)

if success:
    stats = report['stats']
    print(f"Procesados: {stats['total_records']}")
    print(f"Exitosos: {stats['successful']}")
    print(f"Fallidos: {stats['failed']}")
    print(f"Tasa éxito: {stats['success_rate']:.1f}%")
```

### Postmortem Converter

```python
from csv_to_json.postmortem_converter import PostmortemConverter

converter = PostmortemConverter()
success, report = converter.convert_file(
    input_path='../data/input/postmortem.csv',
    output_path='../data/output/postmortem.json',
    error_report_path='../data/errors/postmortem_errors.json'
)
```

## 📄 Contrato JSON

Ambos converters generan JSON en este formato:

```json
{
  "_metadata": {
    "type": "massive" | "postmortem",
    "version": "1.0",
    "created": "ISO timestamp",
    "encoding_detected": "UTF-8",
    "delimiter_detected": ",",
    "record_count": 100,
    "kpis": {
      "total": 100,
      "pending": 23,
      "trend_7d": 5.2,
      "trend_15d": -3.1,
      "trend_30d": 12.8
    }
  },
  "data": [
    {
      "ID de incidencia": "INC000003884945",
      "Descripción": "...",
      "Estatus": "Cerrado",
      "Fecha de envío": "02/01/2026 8:14 a",
      "Grupo asignado": "CEP CAU AGI",
      "Urgencia": "Baja",
      "Impacto": "Masiva",
      "Fecha de última resolución": "12/01/2026 8:24 a"
    }
  ]
}
```

## 🤝 Desarrollo

### Estructura del código

```
src/csv_to_json/
├── __init__.py           # Exporta CsvToJsonConverter
├── converter.py          # Orquestador principal (masivas)
├── postmortem_converter.py # Conversor postmortem
├── encoding.py           # Detección de encoding
├── delimiter.py          # Detección de delimitador
├── normalizers.py        # Normalización de campos
├── validators.py         # Validación de datos
├── schemas.py            # Esquemas (masivas)
└── postmortem_schemas.py # Esquemas (postmortem)
```

### Flujo de conversión

```
CSV Input
  ↓
Detección de Encoding
  ↓
Detección de Delimitador
  ↓
Parsing CSV
  ↓
Normalización de Campos
  ↓
Validación de Datos
  ↓
Cálculo de KPIs
  ↓
Generación de JSON
  ↓
Reporte de Errores (si hay)
```

### Ejecutar en desarrollo

```bash
# Instalar en modo editable
pip install -e .

# Ejecutar converter desde CLI
python cli/convert_incidents.py ../data/input/datos.csv

# O importar en scripts
python -c "from csv_to_json import CsvToJsonConverter; ..."
```

## 📊 Estadísticas

- **Módulos**: 9 archivos Python
- **Tests**: 477 tests (unit + integration + e2e)
- **Ejecución**: ~2.5 segundos
- **Cobertura**: 86%
- **Sin dependencias externas**: Solo stdlib Python

## 🔐 Seguridad

- Datos de entrada/salida en `../data/` (git-ignored)
- Manejo seguro de encoding y caracteres especiales
- Validación exhaustiva de entrada
- Reportes detallados de errores

## 📞 Soporte

Para problemas o preguntas:
1. Consultar [documentación](docs/)
2. Revisar [especificaciones](specs/)
3. Ejecutar tests para diagnóstico: `pytest tests/ -v`

## 🤖 Uso con CI/CD

El conversor está diseñado para usarse en pipelines automatizados:

```bash
# En GitHub Actions o similar
cd converters
pip install -r requirements.txt
python cli/convert_incidents.py ./input/*.csv -o ./output/
python cli/build_index.py ./output/
```

## 📝 Licencia

Parte del proyecto Release Dashboard Application.

---

**Última actualización**: 2026-06-01

<!-- CI/CD Test: Phase 5 Implementation Verified -->
