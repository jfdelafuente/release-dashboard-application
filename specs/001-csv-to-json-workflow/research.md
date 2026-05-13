# Research: CSV to JSON Workflow - Technology & Design Decisions

**Date**: 2026-05-13
**Phase**: Phase 0 - Research

## 1. Encoding Detection Strategy

### Decision: Use Python `chardet` library OR manual BOM/signature detection

**Investigation**:
- Python stdlib `locale.getpreferredencoding()` - unreliable, depends on system settings
- `chardet` library - 3rd party, high accuracy (>99%), small footprint
- Manual BOM detection - built-in, reliable for UTF-8-sig and UTF-16
- Required encodings: UTF-8, UTF-8-sig, Latin-1, Windows-1252, ISO-8859-15

**Recommendation**: Hybrid approach
1. First, detect BOM signatures (UTF-8-sig, UTF-16)
2. If no BOM, use Python stdlib `csv.Sniffer` + fallback detection
3. For production robustness, integrate `chardet` as optional dependency

**Rationale**: BOM detection is fast and reliable; chardet is slower but catches edge cases

**Implementation Path**:
```python
def detect_encoding(file_bytes):
    # Check BOM signatures first
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if file_bytes.startswith(b'\xff\xfe'):
        return 'utf-16'

    # Fallback: Try common encodings in order
    for encoding in ['utf-8', 'latin-1', 'windows-1252']:
        try:
            file_bytes.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue

    # Last resort: chardet (if available)
    try:
        import chardet
        detected = chardet.detect(file_bytes)
        return detected['encoding']
    except ImportError:
        return 'utf-8'  # Default fallback
```

---

## 2. CSV Delimiter Detection Strategy

### Decision: Use Python `csv.Sniffer` with fallback manual detection

**Investigation**:
- `csv.Sniffer.sniff()` - built-in, works well for clean CSV files
- Manual detection - count delimiters in first few rows
- Real data shows comma (,) as primary delimiter
- Edge case: quoted fields containing commas

**Recommendation**: Use `csv.Sniffer` with sample of first 5 rows

**Rationale**:
- Handles quoted fields correctly
- No external dependencies
- Works well for typical incident data

**Implementation Path**:
```python
def detect_delimiter(file_text, sample_lines=5):
    try:
        sample = '\n'.join(file_text.split('\n')[:sample_lines])
        delimiter = csv.Sniffer().sniff(sample).delimiter
        return delimiter
    except csv.Error:
        # Fallback: try common delimiters
        for delim in [',', ';', '\t']:
            if file_text.count(delim) > 5:  # Arbitrary threshold
                return delim
        return ','  # Default to comma
```

---

## 3. Date Parsing Strategy

### Decision: Use `datetime.strptime()` with exact format string

**Investigation**:
- Required format: "dd/mm/yyyy HH:mm a" (with AM/PM)
- Python `strptime` format: "%d/%m/%Y %I:%M %p"
- dateutil library - more flexible but adds dependency
- Real data examples: "02/01/2026 8:14 AM", "12/01/2026 10:24 PM"

**Recommendation**: `datetime.strptime()` with format string, custom error handling

**Rationale**:
- No external dependencies
- Exact format match = clear error messages
- Consistent with Python ecosystem

**Implementation Path**:
```python
from datetime import datetime

def parse_date(date_str):
    try:
        # Format: "02/01/2026 8:14 AM"
        # Python format: "%d/%m/%Y %I:%M %p"
        return datetime.strptime(date_str.strip(), "%d/%m/%Y %I:%M %p")
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected dd/mm/yyyy HH:mm AM/PM")
```

---

## 4. Urgencia Normalization Strategy

### Decision: Regex extraction of text portion from "N-Text" format

**Investigation**:
- Real data format: "4-Baja", "3-Medio", "2-Alta", "1-Crítica"
- Need to normalize "4-Baja" → "Baja"
- The number portion (1-4) appears to be a severity ranking, but we only preserve text
- Case-insensitive matching after normalization

**Recommendation**: Regex pattern with fallback to original if no match

**Rationale**:
- Handles variant spacing: "4-Baja" or "4 - Baja"
- Preserves case after extraction: "Baja" stays "Baja"
- Clear error message if format unexpected

**Implementation Path**:
```python
import re

VALID_URGENCIA = {"Bajo", "Medio", "Alto", "Crítica"}

def normalize_urgencia(value):
    # Remove leading/trailing whitespace
    value = value.strip()

    # Try to extract text portion from "N-Text" format
    match = re.match(r'^\d+\s*-\s*(.+)$', value)
    if match:
        urgencia = match.group(1).strip()
    else:
        urgencia = value

    # Normalize casing to title case
    urgencia = urgencia.title()

    return urgencia  # Return for validation
```

---

## 5. Field Validation Rules

### Decision: Declarative validation using lookup tables and functions

**Investigation**:
- Validation needs: presence, type, format, allowed values
- Data-driven approach: Define allowed values as constants
- Error messages need to be specific (field name, row number, value)

**Recommendation**: Class-based validator with field definitions

**Rationale**:
- Easy to extend with new fields
- Clear error messages
- Testable in isolation

**Implementation Path**:
```python
FIELD_VALIDATORS = {
    'ID de incidencia': {
        'required': True,
        'type': 'text',
        'validator': lambda x: len(x.strip()) > 0
    },
    'Estatus': {
        'required': True,
        'type': 'enum',
        'allowed': ['Abierto', 'Pendiente', 'En Progreso', 'Resuelto', 'Cerrado', 'Cancelado']
    },
    'Urgencia': {
        'required': True,
        'type': 'enum',
        'allowed': ['Bajo', 'Medio', 'Alto', 'Crítica']
    },
    'Impacto': {
        'required': True,
        'type': 'enum',
        'allowed': ['Masiva']
    }
}
```

---

## 6. Error Reporting Format

### Decision: JSON structure with line-by-line error details

**Investigation**:
- User needs: Know which rows failed and why
- Format options: JSON (structured), CSV (same as input), HTML (visual)
- Dashboard context: JSON is already expected

**Recommendation**: JSON error report alongside converted JSON

**Rationale**:
- Consistent with JSON output
- Easy for dashboard to consume
- Clear actionable details

**Error Report Format**:
```json
{
  "summary": {
    "total_records": 1500,
    "successful": 1275,
    "failed": 225,
    "success_rate": 85.0
  },
  "errors": [
    {
      "row": 42,
      "fields": {
        "Urgencia": {
          "original": "invalid-value",
          "error": "Value 'invalid-value' not in allowed list: [Bajo, Medio, Alto, Crítica]"
        }
      }
    },
    {
      "row": 87,
      "fields": {
        "Fecha de envío": {
          "original": "32/13/2026 25:99 AM",
          "error": "Invalid date format. Expected dd/mm/yyyy HH:mm AM/PM"
        }
      }
    }
  ]
}
```

---

## 7. Testing Strategy

### Decision: Unit tests + integration tests with real CSV data

**Investigation**:
- Constitution requires 80% code coverage minimum
- TDD approach: tests first, then implementation
- Real data available: incidencias/CS-Informe*.csv

**Recommendation**: pytest framework with fixtures

**Rationale**:
- pytest is industry standard for Python
- Fixtures allow reusable test data
- Can easily validate against real CSV files

**Test Structure**:
```
tests/
├── unit/
│   ├── test_validators.py        # Test each validation rule
│   ├── test_normalizers.py       # Test Urgencia, date, casing
│   ├── test_encoding.py          # Test encoding detection
│   └── test_delimiters.py        # Test delimiter detection
├── integration/
│   ├── test_end_to_end.py        # Full conversion with real CSV
│   └── fixtures/
│       └── sample-incidents.csv  # Copy of real data for testing
└── conftest.py                   # pytest configuration
```

---

## Summary of Decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Encoding detection | BOM + fallback + chardet | Covers all required encodings, no mandatory dependencies |
| Delimiter detection | csv.Sniffer + fallback | Built-in, handles quoted fields, reliable |
| Date parsing | datetime.strptime() | No dependencies, exact format match |
| Urgencia normalization | Regex extraction | Handles all variant formats |
| Field validation | Declarative lookup tables | Extensible, testable, clear error messages |
| Error reporting | Structured JSON | Consistent, consumable by dashboard |
| Testing | pytest with fixtures | Industry standard, real data validation |

---

**Status**: ✅ RESEARCH COMPLETE - Ready for Phase 1 design
