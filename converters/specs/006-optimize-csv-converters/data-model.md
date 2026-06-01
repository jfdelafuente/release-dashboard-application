# Data Model: CSV-to-JSON Converters

**Date**: 2026-05-14 | **Status**: Phase 1 Design

## Overview

The data model defines the structure of data flowing through the CSV-to-JSON converters. Input is CSV data (unstructured text with encoding/delimiter variations), and output is structured JSON with complete metadata, KPIs, and error reporting.

## Core Entities

### 1. IncidentRecord (Massive Incidents)

**Purpose**: Represents a single incident entry from CSV, normalized and validated.

**Fields**:
- `ID de incidencia` (string, required) - Unique incident identifier
- `Descripción` (string, required) - Incident description
- `Estatus` (enum, required) - Status of incident (Abierto, Pendiente, En Progreso, En Curso, Asignado, Resuelto, Cerrado, Cancelado)
- `Fecha de envío` (date, required) - Submission timestamp (format: dd/mm/yyyy HH:mm a/p)
- `Grupo asignado` (string, required) - Assigned team/group
- `Urgencia` (enum, required) - Urgency level (Baja, Medio, Alta, Crítica)
- `Impacto` (enum, required) - Impact level (Masiva)
- `Fecha de notificación` (date, optional) - Notification timestamp
- `Fecha de última resolución` (date, optional) - Resolution timestamp
- `Motivo de estado` (string, optional) - Status reason
- `MotivoEstado_Anterior` (string, optional) - Previous status reason
- `Grupo Resolutor` (string, optional) - Resolving group
- `Grupo Remitente` (string, optional) - Sending group

**Validation Rules**:
- All required fields must be present and non-empty
- Estatus must be one of 8 allowed values (case-insensitive)
- Urgencia must be one of 4 allowed values (case-insensitive)
- Impacto must be "Masiva" (case-insensitive)
- Dates must parse successfully in formats: dd/mm/yyyy or dd/mm/yyyy HH:mm or dd/mm/yyyy HH:mm a/p

**Normalization Rules**:
- Estatus: Convert to title case (e.g., "CERRADO" → "Cerrado")
- Urgencia: Extract text after numeric prefix if present (e.g., "4-Baja" → "Baja"), then title case
- Impacto: Convert to title case
- All string fields: Trim whitespace

**Output Structure** (in JSON):
```json
{
  "ID de incidencia": "INC000004002774",
  "Descripción": "[2026R4] - Descripción del problema",
  "Estatus": "Cerrado",
  "Fecha de envío": "26/04/2026 8:40 a",
  "Grupo asignado": "SOP_CRMB2B",
  "Urgencia": "Alta",
  "Impacto": "Masiva",
  "Fecha de última resolución": "26/04/2026 10:00 p"
}
```

---

### 2. PostmortemRecord (Postmortem-specific)

**Purpose**: Represents a postmortem incident entry with derived Despliegue field and KPI contribution data.

**Fields** (13 total):
- `ID de incidencia` (string, required) - Unique postmortem ID
- `Descripción` (string, required) - Postmortem description
- `Estatus` (enum, required) - Status value
- `Fecha de envío` (date, required) - Submission date
- `Grupo asignado` (string, required) - Assigned group
- `Urgencia` (enum, required) - Urgency level
- `Impacto` (enum, required) - Impact level
- `Fecha de notificación` (date, optional)
- `Fecha de última resolución` (date, optional)
- `Motivo de estado` (string, optional)
- `MotivoEstado_Anterior` (string, optional)
- `Grupo Resolutor` (string, optional)
- `Grupo Remitente` (string, optional)
- **`Despliegue`** (enum, derived) - **PAP** if this record has the earliest date across all records, **MESA** otherwise (deterministic: first occurrence wins on tie)

**Derived Field Logic** (Despliegue):
1. Scan all records to find the earliest date (checking "Fecha de envío", "Fecha de notificación", "Fecha de última resolución")
2. First record with earliest date gets `Despliegue="PAP"`
3. All other records get `Despliegue="MESA"`
4. On tie (multiple records with same earliest date): first occurrence in file order gets PAP, rest get MESA

**Date Parsing Formats**:
- DD-MMM (e.g., "26-abr") - Spanish month abbreviations, assume current year
- DD/MM/YYYY (e.g., "26/04/2026")
- DD/MM/YYYY HH:MM (e.g., "26/04/2026 10:30")
- DD/MM/YYYY HH:MM a/p (e.g., "26/04/2026 10:30 AM")

**Output Structure** (in JSON):
```json
{
  "ID de incidencia": "PM-2026-0001",
  "Descripción": "Postmortem analysis of 2026R4 release",
  "Estatus": "Cerrado",
  "Fecha de envío": "26/04/2026",
  "Grupo asignado": "Release Team",
  "Urgencia": "Alta",
  "Impacto": "Masiva",
  "Despliegue": "PAP",
  "Fecha de notificación": "26/04/2026"
}
```

---

### 3. ConversionMetadata (File-level)

**Purpose**: Aggregated statistics and information about the entire conversion process, included in output JSON root level.

**Structure**:
```json
{
  "_metadata": {
    // Essential Information
    "type": "massive | postmortem",
    "version": "1.0",
    "created": "2026-05-14T10:30:00Z",
    "record_count": 100,
    "source_filename": "CS_Masiva_20260514.csv",

    // Encoding & Format Detection
    "encoding_detected": "UTF-8",
    "delimiter_detected": ";",

    // Validation Metrics
    "success_rate": 95.0,
    "valid_records": 95,
    "invalid_records": 5,

    // KPIs Object (structure differs by type)
    "kpis": { /* see below */ }
  }
}
```

**KPIs for Massive Incidents** (inside `kpis` object):
```json
{
  "total_incidencias": 100,
  "total_pendientes": 25,
  "trend_7d": 5.3,
  "trend_15d": -2.1,
  "trend_30d": 12.4,
  "by_estatus": {
    "Abierto": 10,
    "Pendiente": 8,
    "En Progreso": 7,
    "Cerrado": 75
  },
  "by_urgencia": {
    "Baja": 40,
    "Medio": 35,
    "Alta": 20,
    "Crítica": 5
  },
  "by_impacto": {
    "Masiva": 100
  }
}
```

**KPIs for Postmortem** (inside `kpis` object):
```json
{
  "dashboard_hub": {
    "total_incidencias": 50,
    "cerradas_percent": 80,
    "pap_resueltas_percent": 90,
    "mesa_resueltas_percent": 75,
    "pap_total": 10,
    "mesa_total": 40
  },
  "by_estatus": {
    "Cerrado": 40,
    "Resuelto": 8,
    "En Progreso": 2
  },
  "by_urgencia": {
    "Baja": 20,
    "Medio": 15,
    "Alta": 10,
    "Crítica": 5
  },
  "by_impacto": {
    "Masiva": 50
  }
}
```

**Fields**:
- `type` (string) - "massive" or "postmortem" (auto-detected from output filename)
- `version` (string) - Format version (currently "1.0")
- `created` (ISO 8601 string) - Conversion timestamp (UTC)
- `record_count` (integer) - Total records in input CSV
- `source_filename` (string) - Original CSV filename
- `encoding_detected` (string) - Detected encoding (UTF-8, Windows-1252, etc.)
- `delimiter_detected` (string) - Detected delimiter (,;tab)
- `success_rate` (number) - Percentage of valid records (0-100)
- `valid_records` (integer) - Count of successfully converted records
- `invalid_records` (integer) - Count of failed records
- `kpis` (object) - Aggregated metrics (structure depends on type)

---

### 4. ValidationError (Record-level)

**Purpose**: Captures validation failures at record and field level for error reporting.

**Structure**:
```json
{
  "row": 23,
  "record_id": "INC000004002774",
  "error_type": "validation",
  "issues": [
    {
      "field": "Urgencia",
      "error": "Invalid value: must be one of [Baja, Medio, Alta, Crítica]",
      "value": "5-Desconocida"
    },
    {
      "field": "Estatus",
      "error": "Missing or empty required field"
    }
  ]
}
```

**Fields**:
- `row` (integer) - CSV row number (1-indexed, header is row 1)
- `record_id` (string or null) - Value of "ID de incidencia" field if present
- `error_type` (string) - "validation" (may be extended in future)
- `issues` (array) - List of field-specific problems:
  - `field` (string) - Field name that failed validation
  - `error` (string) - Human-readable error message
  - `value` (string, optional) - Original value that caused error (omitted for empty fields)

---

## Data Flow

```
CSV File Input (raw bytes)
    ↓
[Encoding Detection] ← detect BOM, try common encodings
    ↓
Text File (decoded with detected encoding)
    ↓
[Delimiter Detection] ← csv.Sniffer + fallback heuristics
    ↓
CSV Parser (csv.DictReader)
    ↓
Per-Record Processing:
  ├─ [Normalization] ← apply field-specific rules
  ├─ [Validation] ← check required fields, enum values, formats
  ├─ [Despliegue Derivation] ← for postmortem only
  └─ [KPI Contribution] ← accumulate aggregates
    ↓
[Aggregated KPI Calculation] ← final statistics
    ↓
Output JSON Structure:
{
  "_metadata": { /* ConversionMetadata */ },
  "data": [ /* IncidentRecord[] or PostmortemRecord[] */ ]
}
+
Error Report File:
{
  "summary": { /* validation stats */ },
  "errors": [ /* ValidationError[] */ ]
}
```

---

## Relationships & Constraints

| Entity | Relationship | Constraint |
|--------|--------------|-----------|
| IncidentRecord ↔ ConversionMetadata | 1:Many | Each file produces one metadata object for many records |
| PostmortemRecord ↔ Despliegue | 1:1 | Each postmortem has exactly one Despliegue value (PAP or MESA) |
| ValidationError ↔ IncidentRecord | 1:Many | One invalid record may have multiple field-level errors |
| ConversionMetadata → KPIs | 1:1 | Metadata contains pre-calculated KPIs for dashboard consumption |

---

## Uniqueness & Identity

- **IncidentRecord**: `ID de incidencia` field assumed to be unique within a file (not enforced; duplicates allowed per spec)
- **PostmortemRecord**: Same as IncidentRecord (13th field is derived, not input)
- **Despliegue Field**: Derived deterministically from date comparison (not provided in input)
- **ValidationError**: Uniquely identified by (row number, field name) within a file

---

## State Transitions

**IncidentRecord States** (from input CSV perspective):
1. **CSV Row** → Raw text from CSV file
2. **Decoded** → Text decoded with correct encoding
3. **Parsed** → Field values extracted by CSV parser
4. **Normalized** → Field values transformed (trim, case, format)
5. **Validated** → All fields checked against validation rules
6. **Valid** → Passed validation, included in JSON output
7. **Invalid** → Failed validation, captured in error report

**No state rollback**: Invalid records are not retried; they're logged once and processing continues.

---

## Edge Cases & Special Handling

| Scenario | Handling |
|----------|----------|
| BOM (Byte Order Mark) at file start | Encoding detection should identify and strip |
| Mixed line endings (CRLF + LF) | Python's csv module handles transparently |
| Duplicate column headers | Error reported during header parsing |
| Extremely long field values (>10KB) | Accepted (no artificial limit) |
| Empty CSV file (no header) | Treated as 0 records, success_rate = 100% |
| CSV with header only (no data rows) | Treated as 0 records, success_rate = 100% |
| Null/empty required fields | Validation fails, record added to error report |
| Despliegue tie (same earliest date) | First occurrence wins (stable deterministic ordering) |
| Invalid date format in Postmortem | Date field marked as invalid, Despliegue still assigned (might fail to derive, defaults to MESA) |

---

## Output File Naming

**Convention**: Base name from input CSV, suffixes added automatically

| Input | Output JSON | Error Report |
|-------|-------------|--------------|
| `CS_Masiva_20260514.csv` | `CS_Masiva_20260514-massive.json` | `CS_Masiva_20260514_errors.json` |
| `2026R4MESAPOST.csv` | `2026R4MESAPOST-postmortem.json` | `2026R4MESAPOST_errors.json` |

**Suffix Logic**:
- Massive Incidents: Append `-massive` to base name
- Postmortem: Append `-postmortem` to base name
- Error reports: Append `_errors` to base name (no suffix)

---

**Last Updated**: 2026-05-14
