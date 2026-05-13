# Postmortem CSV to JSON Converter

Convert postmortem incident CSV files to JSON format for loading into the Postmortem Dashboard and Dashboard Hub.

## Features

- **Automatic Encoding Detection**: UTF-8, Windows-1252, Latin-1, ISO-8859-15, and more
- **Automatic Delimiter Detection**: Comma, semicolon, tab-delimited CSV files
- **Field Normalization**: Title case normalization for Status, Priority, and Impact fields
- **Date Format Handling**: Multiple date format support with normalization to DD/MM/YYYY
- **KPI Calculation**: Automatic calculation of key performance indicators included in output metadata
- **Error Reporting**: Comprehensive error reports for invalid records (zero silent failures)
- **Dashboard Hub Integration**: Auto-discovery via `-postmortem` filename suffix
- **Batch Processing**: Convert multiple files in one command

## Quick Start

### Single File Conversion

Convert a single postmortem CSV file to JSON:

```bash
python convert_postmortems.py data/input/postmortem.csv
```

Output files:
- **JSON**: `data/output/postmortem-postmortem.json` (with KPIs in metadata)
- **Errors**: `data/errors/postmortem-postmortem_errors.json` (if validation errors occur)

### Batch Conversion

Convert all CSV files in a directory:

```bash
python convert_postmortems.py data/input/ -b
```

Processes each CSV file individually, creating separate JSON and error report files for each.

### Custom Output Location

Specify custom output and error directories:

```bash
python convert_postmortems.py data/input/postmortem.csv \
  -o data/output/custom-name.json \
  -e data/errors/custom-errors.json
```

## CLI Usage Guide

### Command Syntax

```bash
python convert_postmortems.py <input> [options]
```

### Arguments

- **input** (required): CSV file or directory
  - Single file: Path to a CSV file (e.g., `data/input/postmortem.csv`)
  - Directory: Path to directory with CSV files (use with `-b` flag)

### Options

- **-b, --batch**: Batch mode - process all CSV files in input directory
- **-o, --output**: Output JSON file path (default: `data/output/<filename>-postmortem.json`)
- **-e, --errors**: Error report path (default: `data/errors/<filename>_errors.json`)

### Usage Examples

#### Single File (Standard)

```bash
python convert_postmortems.py data/input/2026R4_postmortem.csv
```

Creates:
- `data/output/2026R4_postmortem-postmortem.json`
- `data/errors/2026R4_postmortem-postmortem_errors.json`

#### Single File with Custom Paths

```bash
python convert_postmortems.py data/input/postmortem.csv \
  -o custom_output.json \
  -e custom_errors.json
```

#### Batch Processing

```bash
python convert_postmortems.py data/input/ -b
```

Converts all `*.csv` files in `data/input/`:
- `monthly_report.csv` → `data/output/monthly_report-postmortem.json`
- `weekly_report.csv` → `data/output/weekly_report-postmortem.json`

#### Batch with Custom Output Directory

```bash
python convert_postmortems.py data/input/ -b \
  -o data/output/ \
  -e data/errors/
```

## Input CSV Format

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| ID de incidencia | String | Unique incident identifier |
| Descripción | String | Incident description |
| Estatus | String | Current status (any case, normalized to title) |
| Fecha de envío | Date | Incident submission date |
| Grupo asignado | String | Assigned team/group |
| Urgencia | String | Urgency level (any case, normalized to title) |
| Impacto | String | Impact level (any case, normalized to title) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| Fecha de notificación | Date | Notification date |
| Fecha de última resolución | Date | Resolution date |
| Motivo de estado | String | Status reason |
| MotivoEstado_Anterior | String | Previous status reason |
| Grupo Resolutor | String | Resolving group |
| Grupo Remitente | String | Sending group |

### Date Format Support

The converter accepts dates in multiple formats:

- **DD/MM/YYYY**: `01/05/2026` or `01/05/2026 8:00 a`
- **DD/MM/YYYY with time**: `01/05/2026 14:30 p`
- **Spanish month abbreviations**: `15-abr` (April 15th)
- **Single-digit days/months**: `5/4/2026`

All dates are normalized to **DD/MM/YYYY** format in output.

### Encoding Support

Automatic detection for:
- UTF-8 (with or without BOM)
- Windows-1252 (CP1252)
- Latin-1 (ISO-8859-1)
- ISO-8859-15

### Delimiter Support

Automatic detection for:
- Comma (`,`) - Standard CSV
- Semicolon (`;`) - European CSV
- Tab (`\t`) - TSV (Tab-Separated Values)

## Output JSON Structure

### Root Structure

```json
{
  "_metadata": { ... },
  "data": [ ... ]
}
```

### Metadata Section

```json
{
  "_metadata": {
    "type": "postmortem",
    "version": "1.0",
    "created": "2026-05-13T16:38:44.870807Z",
    "source_filename": "postmortem.csv",
    "record_count": 100,
    "conversion_timestamp": "2026-05-13T16:38:44.870807Z",
    "kpis": {
      "total": 100,
      "by_estatus": {
        "Cerrada": 76,
        "En Progreso": 24
      },
      "by_urgencia": {
        "Alta": 20,
        "Media": 60,
        "Baja": 20
      },
      "by_impacto": {
        "Masiva": 30,
        "Parcial": 50,
        "Mínimo": 20
      }
    }
  }
}
```

### Record Structure

```json
{
  "ID de incidencia": "INC000004002774",
  "Descripción": "System unavailability affecting production",
  "Estatus": "Cerrada",
  "Fecha de envío": "26/04/2026",
  "Grupo asignado": "SOP_CRMB2B",
  "Urgencia": "Alta",
  "Impacto": "Masiva",
  "Despliegue": "PAP",
  "Fecha de notificación": "26/04/2026",
  "Fecha de última resolución": "26/04/2026"
}
```

### Key Points

- **Despliegue**: Automatically derived (PAP for oldest date, MESA for others)
- **Field Normalization**: Title case applied to Estatus, Urgencia, Impacto
- **Date Normalization**: All dates in DD/MM/YYYY format
- **KPIs**: Aggregated counts by status, urgency, and impact
- **Dashboard Hub Discovery**: Files with `-postmortem` suffix auto-discovered

## Error Handling

### Error Report Format

When validation errors occur, a detailed error report is generated:

```json
{
  "summary": {
    "total_records": 60,
    "successful": 45,
    "failed": 15,
    "success_rate": 75.0
  },
  "errors": [
    {
      "row": 12,
      "record_id": "INC000000001234",
      "issues": [
        {
          "field": "Fecha de envío",
          "error": "Unparseable date format",
          "value": "INVALID_DATE"
        }
      ]
    }
  ]
}
```

### Exit Codes

- **0**: All records successfully converted (no errors)
- **1**: Some records failed validation (see error report)

### Zero Silent Failures Guarantee

The converter ensures: **Total Records = Successful + Failed**

Every invalid record is captured with detailed information about what failed and why.

## Validation Rules

### Required Fields

All 7 required fields must be present and non-empty:
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
| Estatus | Any value (normalized to title case) |
| Urgencia | Any value (normalized to title case) |
| Impacto | Any value (normalized to title case) |

### Date Validation

- Must be parseable in supported formats
- Day must be 1-31 (valid for month)
- Month must be 1-12
- Year must be valid

### Field Trimming

Whitespace is automatically trimmed from all fields:
- Input: `"  Cerrada  "` → Output: `"Cerrada"`

## Data Model

### PostmortemRecord

Represents a single postmortem incident record with:
- 13 input fields (7 required, 6 optional)
- Validation method for field checking
- Despliegue derivation (PAP/MESA)
- Data dictionary output

### PostmortemKPIMetrics

Aggregates statistics:
- Total incident count
- Count by Estatus (status)
- Count by Urgencia (urgency)
- Count by Impacto (impact)

### ConversionMetadata

File-level metadata:
- Type: "postmortem"
- Version: "1.0"
- ISO 8601 timestamps
- Source filename tracking
- Record count
- KPI embedding

## Performance

### Speed Metrics

- **Processing**: < 5 milliseconds per record
- **Encoding Detection**: < 50ms for file analysis
- **Delimiter Detection**: < 50ms for format detection
- **File Size**: Handles 1000+ records in under 5 seconds
- **Memory**: Efficient single-pass processing

### Optimization

The converter uses single-pass processing:
1. Read CSV with encoding/delimiter detection
2. Normalize each record during read
3. Aggregate KPIs during processing
4. Write output in one pass

## Integration with Dashboard

### Postmortem Dashboard

The converter output is compatible with the Postmortem Dashboard:

1. Place JSON file in `data/output/`
2. Open Postmortem Dashboard HTML
3. Use drag-and-drop to load JSON
4. Dashboard automatically parses metadata and KPIs

### Dashboard Hub Auto-Discovery

Files with `-postmortem` suffix are auto-discovered by Dashboard Hub:

- **Pattern**: `<name>-postmortem.json`
- **Default Output**: `data/output/<filename>-postmortem.json`
- **Discovery**: Dashboard Hub scans `data/output/` for these files

## Troubleshooting

### Common Issues

#### "Encoding Error" or "UnicodeDecodeError"

**Cause**: File encoding not supported by Python

**Solution**: Ensure CSV is saved in UTF-8, Windows-1252, or Latin-1

#### "File not found"

**Cause**: Input file path incorrect

**Solution**: Use full path or relative path from project root:
```bash
# Full path
python convert_postmortems.py /full/path/to/postmortem.csv

# Relative path (from project root)
python convert_postmortems.py data/input/postmortem.csv
```

#### "Delimiter not detected"

**Cause**: CSV uses unusual delimiter

**Solution**: Verify delimiter is comma, semicolon, or tab. Check for mixed delimiters in file.

#### "Many validation errors"

**Cause**: Required fields missing or invalid date formats

**Solution**: Check error report for specific issues. Fix CSV and retry.

#### "Output file not created"

**Cause**: Output directory doesn't exist

**Solution**: Directory is created automatically. If error persists, check file permissions.

### Debug Information

Enable detailed error reporting:
```bash
python convert_postmortems.py data/input/postmortem.csv \
  -e debug_errors.json
```

Check error file for:
- Row numbers of failed records
- Specific field validation errors
- Original values causing issues

## Advanced Usage

### Scripting

Use the converter in Python scripts:

```python
from csv_to_json.postmortem_converter import PostmortemConverter

converter = PostmortemConverter()
success, report = converter.convert_file(
    input_path='data/input/postmortem.csv',
    output_path='data/output/postmortem-postmortem.json',
    error_report_path='data/errors/postmortem-postmortem_errors.json'
)

print(f"Converted: {report['stats']['successful']} records")
print(f"Failed: {report['stats']['failed']} records")
print(f"Success Rate: {report['stats']['success_rate']:.1f}%")
```

### Batch Processing with Python

```python
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter

input_dir = Path('data/input')
output_dir = Path('data/output')
error_dir = Path('data/errors')

for csv_file in input_dir.glob('*.csv'):
    converter = PostmortemConverter()
    success, report = converter.convert_file(
        str(csv_file),
        str(output_dir / f'{csv_file.stem}-postmortem.json'),
        str(error_dir / f'{csv_file.stem}-postmortem_errors.json')
    )

    if not success:
        print(f"Conversion of {csv_file.name} had {report['stats']['failed']} errors")
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run only postmortem converter tests
python -m pytest tests/ -k postmortem -v

# Run with coverage
python -m pytest tests/ --cov=csv_to_json --cov-report=html
```

## Support

For issues or questions:
1. Check error report (if errors occurred)
2. Review troubleshooting section above
3. Verify CSV format against Input CSV Format section
4. Check test data examples in `tests/test_data/`

## Version History

### 1.0 (2026-05-13)

Initial release with:
- CSV to JSON conversion with field normalization
- Automatic encoding and delimiter detection
- KPI calculation and metadata generation
- Comprehensive error reporting
- CLI with single and batch processing
- Dashboard Hub integration support

---

Generated for Release Dashboard Application - Postmortem Converter
