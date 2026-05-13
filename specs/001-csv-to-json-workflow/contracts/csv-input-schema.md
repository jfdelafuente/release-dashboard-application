# CSV Input Schema Contract

**Version**: 1.0
**Date**: 2026-05-13
**Scope**: Massive Incidents CSV Input

## File Format

- **Format**: Comma-separated values (CSV)
- **Encoding**: UTF-8, UTF-8-sig, Windows-1252, or Latin-1 (auto-detected)
- **Delimiter**: Comma (,), semicolon (;), or tab (\t) (auto-detected)
- **Line endings**: CRLF (Windows) or LF (Unix) (both supported)
- **Headers**: Required in first row
- **Quoting**: Standard CSV quoting (double quotes) for fields containing delimiters or newlines

## Column Specification

The CSV MUST contain the following columns in any order (order does not matter):

| Column # | Field Name | Type | Required | Description | Example |
|----------|------------|------|----------|-------------|---------|
| 1 | ID de incidencia | String | Yes | Unique incident identifier | "INC000003884945" |
| 2 | Prioridad | String | No | Priority level (passed through as-is) | "Media", "Alta", "Crítica" |
| 3 | Descripción | String | Yes | Incident description, may contain special chars | "LIVEPERSON // DERIO // ERROR FUNCIONAL" |
| 4 | Estatus | String | Yes | Current status of incident | "Cerrado", "Abierto", "Pendiente" |
| 5 | Fecha de envío | String | Yes | Submission date/time | "02/01/2026 8:14 AM" |
| 6 | Grupo asignado | String | Yes | Assigned team/group | "CEP CAU AGI", "RTV-TECSE RED DATOS" |
| 7 | Fecha de última resolución | String | No | Last resolution date/time | "12/01/2026 8:24 AM" |
| 8 | Grupo Resolutor | String | No | Resolution team (passed through as-is) | "CEP CAU AGI", "Soporte Siebel" |
| 9 | Urgencia | String | Yes | Urgency level with numeric prefix | "4-Baja", "3-Medio", "2-Alta", "1-Crítica" |
| 10 | Impacto | String | Yes | Impact level | "Masiva" |
| 11 | Grupo Remitente | String | No | Source/sending group | "SLN Arvato Salamanca" |

## Field Details

### ID de incidencia
- **Type**: String
- **Required**: Yes
- **Format**: Alphanumeric starting with "INC"
- **Max length**: 50 characters
- **Validation**: Must not be empty or whitespace-only
- **Example**: "INC000003884945"

### Prioridad
- **Type**: String
- **Required**: No
- **Format**: Free text (no validation on values)
- **Max length**: 100 characters
- **Validation**: Passed through as-is; not validated
- **Examples**: "Media", "Alta", "Crítica", "Baja"

### Descripción
- **Type**: String
- **Required**: Yes
- **Format**: Free text with special characters allowed
- **Max length**: 5000 characters
- **Validation**: Must not be empty
- **Special chars**: Allowed (/, //, -, emojis, etc.)
- **Example**: "[2026R4] - [PRJ-10523] No deja modificar el producto"

### Estatus
- **Type**: String (Enum after normalization)
- **Required**: Yes
- **Format**: One of [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]
- **Validation**: Case-insensitive; normalized to title case
- **Examples**: "Cerrado", "cerrado", "CERRADO", "En Progreso"

### Fecha de envío
- **Type**: String (DateTime)
- **Required**: Yes
- **Format**: `dd/mm/yyyy H:MM AM/PM` or `dd/mm/yyyy HH:MM AM/PM`
- **Validation**: Must parse successfully
- **Examples**: "02/01/2026 8:14 AM", "31/12/2026 11:59 PM", "15/06/2026 3:45 PM"

### Grupo asignado
- **Type**: String
- **Required**: Yes
- **Format**: Free text (team/group name)
- **Max length**: 200 characters
- **Validation**: Must not be empty
- **Examples**: "CEP CAU AGI", "RTV-TECSE RED DATOS", "TS GSS MONITORIZACION"

### Fecha de última resolución
- **Type**: String (DateTime, Optional)
- **Required**: No
- **Format**: `dd/mm/yyyy H:MM AM/PM` or `dd/mm/yyyy HH:MM AM/PM` (if present)
- **Validation**: If present, must parse successfully
- **Examples**: "12/01/2026 8:24 AM", "05/01/2026 7:05 AM"

### Grupo Resolutor
- **Type**: String
- **Required**: No
- **Format**: Free text (resolution team name)
- **Max length**: 200 characters
- **Validation**: Passed through as-is; not validated
- **Examples**: "CEP CAU AGI", "Soporte Siebel", "SOP_DJINGO"

### Urgencia
- **Type**: String (Enum after normalization)
- **Required**: Yes
- **Format**: `N-Text` where N is digit and Text is urgency level
- **Validation**: Must normalize to one of [Bajo, Medio, Alto, Crítica]
- **Examples**: "4-Baja", "3-Medio", "2-Alta", "1-Crítica"
- **Variants accepted**: "4 - Baja", "4-baja", "4 -Baja", etc.

### Impacto
- **Type**: String (Enum)
- **Required**: Yes
- **Format**: Must be exactly "Masiva"
- **Validation**: Case-insensitive; only "Masiva" allowed
- **Examples**: "Masiva", "masiva", "MASIVA"

### Grupo Remitente
- **Type**: String
- **Required**: No
- **Format**: Free text (organization/group name)
- **Max length**: 200 characters
- **Validation**: Passed through as-is; not validated
- **Examples**: "SLN Arvato Salamanca", "Operador (A.G.I.)", "MESA DE AYUDA COLOMBIA"

## Example Valid CSV

```csv
ID de incidencia,Prioridad,Descripción,Estatus,Fecha de envío,Grupo asignado,Fecha de última resolución,Grupo Resolutor,Urgencia,Impacto,Grupo Remitente
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,CEP CAU AGI,4-Baja,Masiva,SLN Arvato Salamanca
INC000003884989,Media,PRDIAS-25896 LIVEPERSON // CORUÑA // ERROR FUNCIONAL,Cerrado,02/01/2026 3:18 PM,CEP CAU AGI,23/02/2026 8:32 AM,CEP CAU AGI,3-Medio,Masiva,SLN Arvato Salamanca
INC000003885040,Alta,INDISPONIBILIDAD/ aotlxprvin10211/SL2,Cerrado,02/01/2026 1:02 AM,RTV-TECSE RED DATOS,02/01/2026 5:17 AM,GNOC,2-Alta,Masiva,Operador (A.G.I.)
```

## Encoding Support

The CSV file may use any of these encodings; the workflow will auto-detect:
- **UTF-8**: Standard Unicode encoding
- **UTF-8-sig**: UTF-8 with BOM (common from Windows systems)
- **Windows-1252**: Microsoft Windows encoding
- **Latin-1** (ISO-8859-1): Western European encoding
- **ISO-8859-15**: Latin-9 (rare but supported)

## Delimiter Support

The CSV file may use any of these delimiters; the workflow will auto-detect:
- **Comma** (,): Standard CSV delimiter (RECOMMENDED)
- **Semicolon** (;): Common in European locales
- **Tab** (\t): Tab-separated values

## Edge Cases

### Empty file
- File with only headers (no data rows): Valid, produces empty JSON array

### Very large files
- Files with 1000+ incidents: Supported, processed within 5 seconds

### Special characters in fields
- Special chars (/, //, -, emojis) in Descripción: Supported, preserved as-is

### Quoted fields
- Fields containing delimiters must be quoted: `"Description with, comma"` - Standard CSV quoting

### Duplicate ID de incidencia
- Same incident ID in multiple rows: Allowed, both records processed if valid

### Missing optional fields
- Prioridad, Fecha de última resolución, Grupo Resolutor, Grupo Remitente: Optional, can be empty
- Empty cell for optional field: Valid, preserved as empty string in output

---

**Status**: ✅ SCHEMA APPROVED
