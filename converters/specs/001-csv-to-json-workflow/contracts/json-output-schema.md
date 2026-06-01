# JSON Output Schema Contract

**Version**: 1.0
**Date**: 2026-05-13
**Scope**: Massive Incidents Dashboard Compatible JSON

## Output File Structure

The workflow produces two files:

1. **converted-incidents.json** - Array of successfully converted incident records
2. **conversion-error-report.json** - Details of records that failed validation

## File 1: Converted Incidents JSON

### Format
- **Type**: JSON (RFC 7158)
- **Structure**: Array of objects (one object per valid incident)
- **Encoding**: UTF-8
- **Pretty-print**: Yes (indented for readability)

### JSON Schema (Detailed)

```json
[
  {
    "ID de incidencia": "string (required)",
    "Prioridad": "string (optional)",
    "Descripción": "string (required)",
    "Estatus": "enum string (required)",
    "Fecha de envío": "string datetime (required)",
    "Grupo asignado": "string (required)",
    "Fecha de última resolución": "string datetime (optional)",
    "Grupo Resolutor": "string (optional)",
    "Urgencia": "enum string (required)",
    "Impacto": "enum string (required, always 'Masiva')",
    "Grupo Remitente": "string (optional)"
  }
]
```

### Field Specifications (Output)

| Field | Type | Required | Format | Values | Notes |
|-------|------|----------|--------|--------|-------|
| ID de incidencia | string | Yes | Alphanumeric | "INC000003884945" | From CSV, preserved exactly |
| Prioridad | string | No | Free text | "Media", "Alta", "Crítica" | From CSV, passed through as-is |
| Descripción | string | Yes | Free text (UTF-8) | Any non-empty string | Special chars/emojis preserved |
| Estatus | string | Yes | Enum | "Abierto", "Pendiente", "En Progreso", "Resuelto", "Cerrado", "Cancelado" | Normalized to title case |
| Fecha de envío | string | Yes | DateTime "dd/mm/yyyy HH:mm AM/PM" | "02/01/2026 8:14 AM" | Format preserved from CSV |
| Grupo asignado | string | Yes | Free text | "CEP CAU AGI", "RTV-TECSE RED DATOS" | From CSV, preserved exactly |
| Fecha de última resolución | string | No | DateTime "dd/mm/yyyy HH:mm AM/PM" | "12/01/2026 8:24 AM" | Optional; format preserved |
| Grupo Resolutor | string | No | Free text | "CEP CAU AGI", "Soporte Siebel" | From CSV, passed through as-is |
| Urgencia | string | Yes | Enum | "Bajo", "Medio", "Alto", "Crítica" | Normalized from "N-Text" format |
| Impacto | string | Yes | Enum | "Masiva" | Always this value |
| Grupo Remitente | string | No | Free text | "SLN Arvato Salamanca" | From CSV, passed through as-is |

### Example Output

```json
[
  {
    "ID de incidencia": "INC000003884945",
    "Prioridad": "Media",
    "Descripción": "LIVEPERSON // DERIO // ERROR FUNCIONAL",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 8:14 AM",
    "Grupo asignado": "CEP CAU AGI",
    "Fecha de última resolución": "12/01/2026 8:24 AM",
    "Grupo Resolutor": "CEP CAU AGI",
    "Urgencia": "Baja",
    "Impacto": "Masiva",
    "Grupo Remitente": "SLN Arvato Salamanca"
  },
  {
    "ID de incidencia": "INC000003884989",
    "Prioridad": "Media",
    "Descripción": "PRDIAS-25896 LIVEPERSON // CORUÑA // ERROR FUNCIONAL",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 3:18 PM",
    "Grupo asignado": "CEP CAU AGI",
    "Fecha de última resolución": "23/02/2026 8:32 AM",
    "Grupo Resolutor": "CEP CAU AGI",
    "Urgencia": "Medio",
    "Impacto": "Masiva",
    "Grupo Remitente": "SLN Arvato Salamanca"
  },
  {
    "ID de incidencia": "INC000003885040",
    "Prioridad": "Alta",
    "Descripción": "INDISPONIBILIDAD/ aotlxprvin10211/SL2",
    "Estatus": "Cerrado",
    "Fecha de envío": "02/01/2026 1:02 AM",
    "Grupo asignado": "RTV-TECSE RED DATOS",
    "Fecha de última resolución": "02/01/2026 5:17 AM",
    "Grupo Resolutor": "GNOC",
    "Urgencia": "Alta",
    "Impacto": "Masiva",
    "Grupo Remitente": "Operador (A.G.I.)"
  }
]
```

### Compatibility

This JSON structure is designed to be immediately consumable by the Massive Incidents Dashboard:
- Field names match exactly (case-sensitive) with dashboard expectations
- Enum values match allowed values defined in dashboard
- Date/time format preserved (no conversion to ISO 8601)
- All fields included, allowing dashboard to selectively use what it needs

## File 2: Error Report JSON

### Format
- **Type**: JSON (RFC 7158)
- **Structure**: Object containing summary + error details array

### JSON Schema

```json
{
  "summary": {
    "total_records": "number",
    "successful": "number",
    "failed": "number",
    "success_rate": "number (0-100)"
  },
  "errors": [
    {
      "row": "number (1-indexed, starts at row 2 after header)",
      "fields": {
        "[field_name]": {
          "original": "string (original value from CSV)",
          "error": "string (human-readable error message)"
        }
      }
    }
  ]
}
```

### Example Error Report

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
        "Grupo asignado": {
          "original": "",
          "error": "Required field 'Grupo asignado' is empty"
        }
      }
    },
    {
      "row": 87,
      "fields": {
        "Estatus": {
          "original": "Invalid",
          "error": "Invalid Estatus value: 'Invalid'. Allowed values: [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]"
        }
      }
    },
    {
      "row": 120,
      "fields": {
        "Fecha de envío": {
          "original": "32/13/2026 25:99 AM",
          "error": "Invalid date format: '32/13/2026 25:99 AM'. Expected dd/mm/yyyy HH:mm AM/PM"
        }
      }
    },
    {
      "row": 156,
      "fields": {
        "Urgencia": {
          "original": "5-ExtraAlta",
          "error": "Invalid Urgencia value after normalization: 'ExtraAlta'. Allowed values: [Bajo, Medio, Alto, Crítica]"
        }
      }
    },
    {
      "row": 200,
      "fields": {
        "Impacto": {
          "original": "Alto",
          "error": "Invalid Impacto value: 'Alto'. Only 'Masiva' is allowed for this dashboard"
        }
      }
    }
  ]
}
```

### Error Message Format

Error messages MUST be:
- **Clear**: Specify what the issue is
- **Actionable**: Tell the user how to fix it
- **Specific**: Include field name, original value, and allowed values
- **Friendly**: No technical jargon or stack traces

**Examples**:
- ❌ BAD: "ValueError: time data does not match format"
- ✅ GOOD: "Invalid date format: '32/13/2026 25:99 AM'. Expected dd/mm/yyyy HH:mm AM/PM"

- ❌ BAD: "KeyError: Urgencia"
- ✅ GOOD: "Required field 'Urgencia' is missing"

- ❌ BAD: "Invalid enum value"
- ✅ GOOD: "Invalid Estatus value: 'Invalid'. Allowed values: [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]"

## Consistency Rules

1. **Field ordering**: All objects have same field order (matches CSV column order)
2. **Null vs empty**: No null values in JSON; optional fields omitted if empty in CSV
3. **Case sensitivity**: Field names are case-sensitive (must match exactly)
4. **Encoding**: All output is UTF-8 encoded
5. **Date format**: Dates always in "dd/mm/yyyy HH:mm AM/PM" format (never converted)
6. **Enum values**: Always exact case as specified (e.g., "Baja", not "baja")

## Size & Performance Constraints

- **Maximum file size**: ~100MB for 1000+ incidents (reasonable for modern browsers)
- **Maximum object count**: No hard limit (tested up to 5000 records)
- **Parsing time**: Workflow must produce output JSON within 5 seconds
- **Memory usage**: <100MB during conversion of 1000+ records

## Validation Checklist (Before Output)

Before writing JSON files, validate:
- ✅ All objects have same set of fields (consistent schema)
- ✅ All enum fields contain only allowed values
- ✅ All required fields are present in every object
- ✅ All datetime fields follow "dd/mm/yyyy HH:mm AM/PM" format
- ✅ JSON is valid and parseable
- ✅ Error report has summary with correct counts
- ✅ Error details match rows in CSV (row numbers are 1-indexed, starting at 2)

---

**Status**: ✅ SCHEMA APPROVED
