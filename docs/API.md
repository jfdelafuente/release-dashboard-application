# API Documentation - CSV to JSON Converter

Complete documentation for the Release Dashboard Application CSV to JSON converter CLI tools.

## Overview

The converter transforms CSV incident files into JSON format compatible with the Massive Incidents Dashboard. It provides automatic encoding detection, delimiter detection, field normalization, validation, and detailed error reporting.

## Quick Start

### Windows
```batch
convert_incidents.bat data/input/datos.csv
```

### Linux/Mac
```bash
./convert_incidents.sh data/input/datos.csv
```

**That's it!** The JSON is generated automatically in `data/output/` with validation, normalization, and error reporting.

## Command-Line Usage

### Basic Syntax

```bash
# Windows
convert_incidents.bat <input> [options]

# Linux/Mac
./convert_incidents.sh <input> [options]

# Direct Python (advanced)
python -m src.converters.convert_incidents <input> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input` | Yes | Input CSV file or directory containing CSV files |

### Options

| Option | Short | Long | Argument | Default | Description |
|--------|-------|------|----------|---------|-------------|
| Output | `-o` | `--output` | `<path>` | `data/output/` | Output JSON file or directory |
| Errors | `-e` | `--errors` | `<path>` | `data/errors/` | Error report file or directory |
| Show Errors | | `--show-errors` | None | False | Display error summary after conversion |
| Verbose | `-v` | `--verbose` | None | False | Show detailed output |
| Help | `-h` | `--help` | None | - | Display help message |

## Examples

### Convert Single File

```bash
# Basic (output to data/output/)
convert_incidents.bat data/input/datos.csv

# Specify output location
convert_incidents.bat data/input/datos.csv -o data/output/incidents.json

# Include error report
convert_incidents.bat data/input/datos.csv -e data/errors/incidents_errors.json
```

### Batch Processing

```bash
# Convert all CSV files in directory
convert_incidents.bat data/input/

# Convert with custom output directory
convert_incidents.bat data/input/ -o data/output/ -e data/errors/

# Show error summary after conversion
convert_incidents.bat data/input/datos.csv --show-errors

# Verbose mode (detailed output)
convert_incidents.bat data/input/datos.csv -v
```

### Combined Options

```bash
# All options together
convert_incidents.bat data/input/datos.csv \
  -o data/output/resultado.json \
  -e data/errors/resultado_errors.json \
  --show-errors \
  -v
```

## Input Format

### CSV Structure

The converter expects CSV files with the following columns (minimum required fields):

| Column Name | Type | Required | Description | Example |
|-------------|------|----------|-------------|---------|
| ID de incidencia | String | Yes | Unique incident ID | INC000004002774 |
| Descripción | String | Yes | Incident description | System down, unable to process |
| Estatus | String | Yes | Incident status | Abierto, Cerrado, Resuelto, Pendiente |
| Fecha de envío | DateTime | Yes | Submission date/time | 26/04/2026 8:40 AM |
| Grupo asignado | String | Yes | Assigned team/group | SOP_CRMB2B |
| Urgencia | String | Yes | Urgency level | Baja, Media, Alta, Crítica |
| Impacto | String | Yes | Impact level | Bajo, Medio, Masiva |
| Fecha de última resolución | DateTime | No | Last resolution date | 26/04/2026 10:00 PM |

### CSV Encoding Support

The converter auto-detects encoding:
- ✅ UTF-8
- ✅ UTF-8 with BOM (UTF-8-sig)
- ✅ Windows-1252
- ✅ Latin-1 (ISO-8859-1)
- ✅ ISO-8859-15

### CSV Delimiter Support

The converter auto-detects delimiter:
- ✅ Comma (`,`)
- ✅ Semicolon (`;`)
- ✅ Tab (`\t`)

## Output Format

### Successful Conversion Output

**File**: `data/output/<filename>.json`

```json
[
  {
    "ID de incidencia": "INC000004002774",
    "Descripción": "System issue requiring immediate attention",
    "Estatus": "Cerrado",
    "Fecha de envío": "26/04/2026 8:40 AM",
    "Grupo asignado": "SOP_CRMB2B",
    "Urgencia": "Alta",
    "Impacto": "Masiva",
    "Fecha de última resolución": "26/04/2026 10:00 PM"
  }
]
```

### Normalization Examples

The converter applies automatic normalization:

| Original | Normalized | Rule |
|----------|------------|------|
| `4-Baja` | `Baja` | Urgencia: Extract text after prefix |
| `CERRADO` | `Cerrado` | Estatus: Convert to Title Case |
| `masiva` | `Masiva` | Impacto: Convert to Title Case |
| `26/04/2026 8:40 a` | `26/04/2026 8:40 AM` | Fecha: Normalize AM/PM format |

### Error Report Output

**File**: `data/errors/<filename>_errors.json`

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
          "error": "Invalid value: must be one of [Baja, Media, Alta, Crítica]"
        }
      }
    }
  ]
}
```

## Validation Rules

### Required Fields

The following fields are required and must be present:
- ID de incidencia
- Descripción
- Estatus
- Fecha de envío
- Grupo asignado
- Urgencia
- Impacto

### Allowed Values

| Field | Allowed Values |
|-------|----------------|
| Estatus | Abierto, Cerrado, Resuelto, Pendiente, Cancelado |
| Urgencia | Baja, Media, Alta, Crítica |
| Impacto | Bajo, Medio, Masiva |

### Date Format

- **Required Format**: `dd/mm/yyyy HH:mm AM/PM`
- **Examples**:
  - ✅ 26/04/2026 8:40 AM
  - ✅ 26/04/2026 20:40 PM
  - ❌ 04/26/2026 8:40 AM (month/day order wrong)
  - ❌ 2026-04-26 08:40 (ISO format not supported)

## Return Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Conversion completed successfully |
| 1 | Error | Conversion failed (check error report) |
| 2 | Usage Error | Invalid command-line arguments |

## Performance Characteristics

- **Processing Speed**: ~1000+ records/second
- **Memory Usage**: ~100MB for 10,000 incidents
- **Maximum Size**: No hard limit (tested up to 100,000 incidents)

## Troubleshooting

### "Python not found"

**Cause**: Python 3.6+ not installed or not in PATH

**Solution**:
```bash
# Check Python version
python --version

# Should output: Python 3.6+ (e.g., Python 3.10.5)

# If not found, install from: https://www.python.org/
```

### "ModuleNotFoundError: No module named 'csv_to_json'"

**Cause**: Running from wrong directory or PATH issue

**Solution**:
```bash
# Run from project root directory
cd /path/to/release-dashboard-application

# Then execute
./scripts/bin/convert_incidents.sh data/input/datos.csv

# OR use Python module execution
python -m src.converters.convert_incidents data/input/datos.csv
```

### "Encoding error: 'utf-8' codec can't decode byte"

**Cause**: File uses unsupported encoding

**Solution**:
1. The converter auto-detects encoding (UTF-8, Windows-1252, Latin-1, etc.)
2. If still failing, save file with UTF-8 encoding in your editor
3. Try converting with verbose mode for details:
   ```bash
   convert_incidents.bat data/input/datos.csv -v
   ```

### "Invalid delimiter"

**Cause**: CSV uses unusual delimiter

**Solution**:
1. The converter auto-detects comma, semicolon, and tab
2. If using different delimiter, convert file to use one of these delimiters
3. For manual delimiter specification (future feature), see DEVELOPMENT.md

### "Validation errors: X records failed"

**Cause**: CSV contains invalid data

**Solution**:
1. Check `data/errors/<filename>_errors.json` for specific errors
2. Use `--show-errors` flag to see summary:
   ```bash
   convert_incidents.bat data/input/datos.csv --show-errors
   ```
3. Fix CSV values according to validation rules (see Validation Rules section)
4. Re-run conversion

## Related Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup and advanced usage
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and data flow
- [SECURITY.md](../SECURITY.md) - Security practices

## Examples Repository

For complete examples with sample CSV files, see:
- `tests/fixtures/` - Sample CSV and JSON files
- `tests/integration/` - Integration test examples

## Support

For issues or questions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review error report in `data/errors/`
3. Create issue with example CSV (sanitized)

---

**Last Updated**: 2026-05-14
