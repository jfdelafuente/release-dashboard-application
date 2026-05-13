# Data Model: CSV to JSON Workflow

**Date**: 2026-05-13
**Phase**: Phase 1 - Design

## Entity: IncidentRecord

Represents a single incident record from the CSV input that passes validation and normalization.

### Fields

| Field | Type | Required | Default | Validation Rules | Notes |
|-------|------|----------|---------|------------------|-------|
| `ID de incidencia` | String | Yes | N/A | Non-empty, unique within batch | Example: "INC000003884945" |
| `Prioridad` | String | No | N/A | No specific validation; passed through as-is | Example: "Media", "Alta", "Crítica" |
| `Descripción` | String | Yes | N/A | Non-empty, max 5000 chars, special chars allowed | May contain //, //, -, emojis |
| `Estatus` | Enum | Yes | N/A | Must be one of: [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado] (case-insensitive) | Normalized to title case |
| `Fecha de envío` | DateTime | Yes | N/A | Must parse to valid date/time in dd/mm/yyyy HH:mm a format | Example: "02/01/2026 8:14 AM" |
| `Grupo asignado` | String | Yes | N/A | Non-empty, max 200 chars | Example: "CEP CAU AGI", "RTV-TECSE RED DATOS" |
| `Fecha de última resolución` | DateTime | No | N/A | If present, must parse to valid date/time in dd/mm/yyyy HH:mm a format | Optional field |
| `Grupo Resolutor` | String | No | N/A | No specific validation; passed through as-is | Linked to resolution group |
| `Urgencia` | Enum | Yes | N/A | After normalization, must be one of: [Bajo, Medio, Alto, Crítica] | Normalized from "N-Text" format (e.g., "4-Baja" → "Baja") |
| `Impacto` | Enum | Yes | N/A | Must be exactly "Masiva" (no other values allowed) | All incident records are massive |
| `Grupo Remitente` | String | No | N/A | No specific validation; passed through as-is | Source organization/group |

### Validation Rules (Detailed)

#### Presence Validation
- Required fields: ID de incidencia, Descripción, Estatus, Fecha de envío, Grupo asignado, Urgencia, Impacto
- Optional fields: Prioridad, Fecha de última resolución, Grupo Resolutor, Grupo Remitente
- Empty string = missing (after trim)

#### Type Validation
- Text fields (ID, Descripción, Grupo asignado, etc.): Must be string, non-empty after trim
- DateTime fields (Fecha de envío, Fecha de última resolución): Must parse successfully
- Enum fields (Estatus, Urgencia, Impacto): Must match exactly one value in allowed list

#### Format Validation
- Fecha de envío: Parse with format `"%d/%m/%Y %I:%M %p"` (Python strptime)
  - Example valid: "02/01/2026 8:14 AM", "31/12/2026 11:59 PM"
  - Example invalid: "2/1/2026 8:14 AM" (no zero padding), "02-01-2026 8:14" (wrong separator), "02/01/2026 8:14" (missing AM/PM)

#### Value Validation (Enums)
- Estatus allowed values: `[Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]` (case-insensitive)
- Urgencia allowed values: `[Bajo, Medio, Alto, Crítica]` (case-insensitive) **after normalization**
- Impacto allowed values: `[Masiva]` only (case-insensitive)

#### Character Validation
- Special characters, accents (é, ñ, ü), and emojis: ALLOWED in all text fields
- HTML/XML tags: NOT filtered (preserved as-is)
- No null bytes or control characters

### Normalization Rules (Applied BEFORE Validation)

1. **All fields**: Trim leading/trailing whitespace
   - `"  Cerrado  "` → `"Cerrado"`

2. **Estatus**: Normalize to title case
   - `"cerrado"` → `"Cerrado"`
   - `"CERRADO"` → `"Cerrado"`

3. **Urgencia**: Extract text portion from "N-Text" format, then title case
   - `"4-Baja"` → `"Baja"`
   - `"3-Medio"` → `"Medio"`
   - `"2-Alta"` → `"Alta"`
   - `"1-Crítica"` → `"Crítica"`
   - Handles variants: `"4 - Baja"` → `"Baja"`, `"4-baja"` → `"Baja"`

4. **Impacto**: Normalize to title case
   - `"masiva"` → `"Masiva"`
   - `"MASIVA"` → `"Masiva"`

5. **DateTime fields**: Preserve exact format from CSV (no conversion)
   - `"02/01/2026 8:14 AM"` → STORED as `"02/01/2026 8:14 AM"` (not converted to ISO 8601)

### Example Valid Record (After Normalization)

```json
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
}
```

### Example Invalid Records (Rejection Reasons)

**Record 1: Missing required field**
```csv
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,,4-Baja,Masiva,SLN Arvato Salamanca
```
- Rejection: `Grupo Asignado` field is empty (required)
- Row: 42
- Error message: "Required field 'Grupo asignado' is empty"

**Record 2: Invalid Estatus value**
```csv
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Invalid,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,,4-Baja,Masiva,SLN Arvato Salamanca
```
- Rejection: `Estatus` is not in allowed list
- Row: 87
- Error message: "Invalid Estatus value: 'Invalid'. Allowed values: [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]"

**Record 3: Invalid date format**
```csv
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,32/13/2026 25:99 AM,CEP CAU AGI,12/01/2026 8:24 AM,,4-Baja,Masiva,SLN Arvato Salamanca
```
- Rejection: `Fecha de envío` cannot be parsed
- Row: 120
- Error message: "Invalid Fecha de envío format: '32/13/2026 25:99 AM'. Expected dd/mm/yyyy HH:mm AM/PM"

**Record 4: Invalid Urgencia after normalization**
```csv
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,,5-ExtraAlta,Masiva,SLN Arvato Salamanca
```
- Rejection: After normalization ("5-ExtraAlta" → "ExtraAlta"), not in allowed list
- Row: 156
- Error message: "Invalid Urgencia value: 'ExtraAlta'. Allowed values: [Bajo, Medio, Alto, Crítica]"

**Record 5: Invalid Impacto**
```csv
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,,4-Baja,Alto,SLN Arvato Salamanca
```
- Rejection: `Impacto` is not "Masiva"
- Row: 200
- Error message: "Invalid Impacto value: 'Alto'. Only 'Masiva' is allowed for this dashboard"

## Conversion Process

### Input
- CSV file (bytes or text)
- Encoding: Auto-detected or specified
- Delimiter: Auto-detected or specified

### Processing Steps
1. **Load CSV file** with auto-detected encoding and delimiter
2. **Extract headers** from first row
3. **Normalize all fields** according to normalization rules
4. **Validate each record** against validation rules
5. **Collect errors** for records that fail validation
6. **Output** valid records as JSON array + error report

### Output
- **JSON file**: Array of IncidentRecord objects (only valid records)
- **Error report**: JSON structure with errors summary and details
- **Statistics**: Total records, successful, failed, success percentage

---

**Status**: ✅ DATA MODEL COMPLETE
