# Release Dashboard Application - CSV to JSON Workflow

Herramienta completa para convertir archivos CSV de incidencias masivas a formato JSON compatible con el **Massive Incidents Dashboard**.

## ⚡ Manera Más Rápida (30 segundos)

```bash
# Windows
convert_incidents.bat "incidencias/datos.csv"

# Linux/Mac
./convert_incidents.sh "incidencias/datos.csv"
```

**¡Eso es todo!** El JSON se genera automáticamente con validación, normalización y reporte de errores.

→ **[Más detalles y opciones](CONVERTER_USAGE.md)**

## 🎯 Características Principales

✅ **Auto-detección inteligente**
- Encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- Delimitadores (coma, punto y coma, tabulación)

✅ **Normalización de campos**
- Urgencia: extrae texto de formato "N-Text" ("4-Baja" → "Baja")
- Estatus: normaliza a Title Case
- Impacto: normaliza a Title Case
- Fechas: valida formato dd/mm/yyyy HH:mm a/p

✅ **Validación robusta**
- Verifica campos requeridos
- Valida valores permitidos (enums)
- Detecta formatos de fecha inválidos
- Continúa procesando saltando registros inválidos

✅ **Reporte de errores**
- Genera reporte JSON detallado con errores
- Incluye número de fila, campo y motivo del error
- Estadísticas de conversión (total, exitosos, fallidos, tasa de éxito)

✅ **Compatible con Dashboard**
- JSON output compatible 100% con Massive Incidents Dashboard
- Preserva todos los campos del CSV
- Mantiene caracteres especiales (é, ñ, ü)

## 📋 Requisitos

- Python 3.6+
- Sin dependencias externas (usa librerías estándar)

## 📦 Archivos de Script

Scripts listos para ejecutar (recomendado para la mayoría de usuarios):

| Archivo | Descripción | Uso |
|---------|-------------|-----|
| `convert_incidents.py` | Script principal en Python | `python convert_incidents.py archivo.csv` |
| `convert_incidents.bat` | Wrapper para Windows | `convert_incidents.bat archivo.csv` |
| `convert_incidents.sh` | Wrapper para Linux/Mac | `./convert_incidents.sh archivo.csv` |

**Características de los scripts:**
- ✅ Interfaz amigable con colores
- ✅ Procesamiento individual o por lotes
- ✅ Estadísticas detalladas
- ✅ Reporte de errores JSON
- ✅ Detección automática de encoding/delimitadores

**→ [Guía completa de scripts](CONVERTER_USAGE.md)**

## 🚀 Inicio Rápido

### ⭐ Opción 1: Scripts Listos para Usar (RECOMENDADO)

**Los scripts hacen todo automáticamente - mejor opción para usuarios finales**

#### Windows
```batch
convert_incidents.bat incidencias/datos.csv
```

#### Linux/Mac
```bash
./convert_incidents.sh incidencias/datos.csv
```

#### Con opciones personalizadas
```bash
# Especificar directorio de salida
convert_incidents.bat incidencias/ -o output/ -e output/

# Ver resumen de errores
convert_incidents.bat datos.csv --show-errors
```

**¿Qué hacen los scripts?**
- ✅ Detectan encoding automáticamente
- ✅ Procesan archivos individuales o directorios completos
- ✅ Generan JSON y reporte de errores
- ✅ Muestran estadísticas (total, exitosos, fallidos, tasa de éxito)
- ✅ Colores y progreso en consola

**Documentación completa**: [CONVERTER_USAGE.md](CONVERTER_USAGE.md)

---

### Opción 2: Uso Programático (Python)

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='incidencias/data.csv',
    output_path='output/incidents.json',
    error_report_path='output/errors.json'
)

print(f"Exitoso: {report['stats']['successful']}")
print(f"Errores: {report['stats']['failed']}")
print(f"Encoding detectado: {report['encoding_detected']}")
```

### Opción 3: Uso desde Python (CLI avanzada)

## 💻 Ejemplos de Uso

### Ejemplo 1: Convertir archivo de incidencias masivas

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file(
    input_path='incidencias/CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv',
    output_path='dashboard_data.json',
    error_report_path='conversion_errors.json'
)

stats = report['stats']
print(f"Total: {stats['total_records']}")
print(f"Exitosos: {stats['successful']}")
print(f"Fallidos: {stats['failed']}")
print(f"Tasa: {stats['success_rate']:.1f}%")
```

### Ejemplo 2: Procesar múltiples archivos

```python
from csv_to_json import CsvToJsonConverter
from pathlib import Path

converter = CsvToJsonConverter()
csv_files = Path('csv').glob('*.csv')

for csv_file in csv_files:
    output = f'json/{csv_file.stem}.json'
    errors = f'json/{csv_file.stem}_errors.json'

    success, report = converter.convert_file(
        str(csv_file),
        output,
        errors
    )

    print(f"{csv_file.name}: {report['stats']['successful']}/{report['stats']['total_records']}")
```

### Ejemplo 3: Obtener estadísticas de conversión

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
converter.convert_file('data.csv', 'output.json')

stats = converter.get_stats()
errors = converter.get_errors()

print(f"Tasa de éxito: {stats['success_rate']:.1f}%")
print(f"Registros con error: {len(errors)}")

for error in errors[:5]:  # Mostrar primeros 5 errores
    print(f"  Fila {error['row']}: {error['fields']}")
```

## 📊 Formato de Salida

### JSON válido (output.json)

```json
[
  {
    "ID de incidencia": "INC000003884945",
    "Descripción": "LIVEPERSON // DERIO // ERROR FUNCIONAL",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 8:14 AM",
    "Grupo asignado": "CEP CAU AGI",
    "Urgencia": "Baja",
    "Impacto": "Masiva",
    "Fecha de última resolución": "12/01/2026 8:24 AM"
  }
]
```

### Reporte de errores (errors.json)

```json
{
  "summary": {
    "total_records": 100,
    "successful": 95,
    "failed": 5,
    "success_rate": 95.0
  },
  "errors": [
    {
      "row": 23,
      "fields": {
        "Urgencia": {
          "original": "5-Desconocida",
          "error": "Invalid value: must be one of [Baja, Medio, Alta, Crítica]"
        }
      }
    }
  ]
}
```

## 🔧 Configuración de Validación

### Campos requeridos
- ID de incidencia
- Descripción
- Estatus
- Fecha de envío
- Grupo asignado
- Urgencia
- Impacto

### Valores permitidos

| Campo | Valores Permitidos |
|-------|------------------|
| **Estatus** | Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado |
| **Urgencia** | Baja, Medio, Alta, Crítica |
| **Impacto** | Masiva |

### Normalización automática

| Campo | Entrada | Salida |
|-------|---------|--------|
| **Urgencia** | 4-Baja | Baja |
| **Urgencia** | 3-Medio | Medio |
| **Urgencia** | 2-Alta | Alta |
| **Urgencia** | 1-Crítica | Crítica |
| **Estatus** | cerrado | Cerrado |
| **Impacto** | masiva | Masiva |

## 🧪 Ejecución de Tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ver cobertura de código
pytest tests/ --cov=csv_to_json --cov-report=html

# Ejecutar solo tests de integración
pytest tests/integration/ -v

# Ejecutar tests unitarios
pytest tests/unit/ -v
```

**Estado Actual**: ✅ 34/34 tests pasando | 81.95% coverage

## 📚 Documentación Adicional

- [Especificación Feature](specs/001-csv-to-json-workflow/spec.md)
- [Plan Técnico](specs/001-csv-to-json-workflow/plan.md)
- [Modelo de Datos](specs/001-csv-to-json-workflow/data-model.md)
- [Guía de Inicio Rápido](specs/001-csv-to-json-workflow/quickstart.md)
- [Investigación Técnica](specs/001-csv-to-json-workflow/research.md)

## 🐛 Solución de Problemas

### Error: "Required field 'Urgencia' is empty"

```
Error: Validación falló - campo obligatorio vacío
```

**Solución**: Verifica que el CSV tenga datos en el campo Urgencia. Si viene como "N-Texto", la normalización lo extraerá automáticamente.

### Error: "Invalid Estatus value"

```
Error: Valor no permitido en Estatus
```

**Solución**: Verifica que Estatus esté en la lista permitida. Se normaliza a Title Case automáticamente.

### Encoding incorrecto

```
Error: UnicodeDecodeError o caracteres raros
```

**Solución**: El módulo auto-detecta encoding. Si falla, verifica manualmente el encoding del archivo.

### Delimitador incorrecto

```
Error: Las columnas no se parsean correctamente
```

**Solución**: El módulo auto-detecta delimitadores. Si falla, revisa el archivo manualmente.

## 📈 Monitoreo y Logs

```python
from csv_to_json import CsvToJsonConverter

converter = CsvToJsonConverter()
success, report = converter.convert_file('data.csv', 'out.json', 'err.json')

# Ver estadísticas
print(f"Total: {report['stats']['total_records']}")
print(f"Tasa éxito: {report['stats']['success_rate']:.1f}%")
print(f"Encoding: {report['encoding_detected']}")

# Ver errores específicos
for error in report['errors']:
    row = error['row']
    fields = error['fields']
    print(f"Fila {row}: {fields}")
```

## 🚀 Integración con Dashboard

El JSON generado es compatible 100% con **Massive Incidents Dashboard**:

1. Carga el CSV en el conversor
2. Genera `output.json`
3. Carga `output.json` en el dashboard
4. Dashboard parsea automáticamente los datos

**Campos normalizados automáticamente para compatibilidad:**
- Urgencia: Sin prefijo numérico
- Estatus: Title case
- Impacto: Title case

## 📞 Soporte

Para preguntas o problemas:
- Revisa [quickstart.md](specs/001-csv-to-json-workflow/quickstart.md)
- Consulta [spec.md](specs/001-csv-to-json-workflow/spec.md) para detalles técnicos
- Ejecuta tests con `pytest` para verificar funcionamiento

## 📄 Licencia

Uso interno del proyecto Release Dashboard Application.
