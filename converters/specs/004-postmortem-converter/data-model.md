# Data Model: Postmortem CSV to JSON Converter

## Entities

### PostmortemRecord

Represents a single incident postmortem entry from CSV input.

**Input Fields** (13 from CSV):
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| ID de incidencia | String | Required, unique | Identifier for incident; maps to Remedy system |
| Descripción | String | Required | Incident description text |
| Estatus | String | Required | Status: Cerrada, En Progreso, Pendiente, Escalada, etc. |
| Fecha de envío | Date | Required | Submission date; format DD-MMM or DD/MM/YYYY |
| Grupo asignado | String | Required | Team assigned to incident |
| Fecha de notificación | Date | Optional | Notification date |
| Fecha de última resolución | Date | Optional | Resolution completion date |
| Motivo de estado | String | Optional | Reason for current status |
| MotivoEstado_Anterior | String | Optional | Previous status reason (audit trail) |
| Grupo Resolutor | String | Optional | Team that resolved incident |
| Urgencia | String | Required | Urgency level: Alta, Media, Baja, Crítica |
| Impacto | String | Required | Impact level: Masiva, Alta, Media, Baja |
| Grupo Remitente | String | Optional | Submitting team identifier |

**Derived Fields** (created during conversion):
| Field | Type | Derivation | Output |
|-------|------|-----------|--------|
| Despliegue | String | Calculated from date fields | PAP or MESA |

**Despliegue Derivation Logic**:
1. Compare all three date fields across entire dataset
2. Find global minimum date value
3. Record with minimum date receives Despliegue = "PAP"
4. All other records receive Despliegue = "MESA"
5. If dates missing/unparseable, exclude from comparison

**Output Format** (14 fields = 13 input + 1 derived):
- All input fields preserved in output
- Despliegue added as 14th field
- Field names unchanged (Spanish names preserved)
- Estatus values: title case normalized (e.g., "CERRADA" → "Cerrada")
- Dates: normalized to consistent format (DD/MM/YYYY)

**Validation Rules**:
- ID de incidencia: Required, non-empty
- Estatus: Required; must be recognized status value
- Fecha de envío: Required; must be parseable date
- Urgencia: Required; must be one of [Alta, Media, Baja, Crítica]
- Impacto: Required; must be one of [Masiva, Alta, Media, Baja]
- Other fields: Tolerate missing values, trim whitespace

---

### PostmortemKPIMetrics

Aggregated statistics calculated during conversion.

**Attributes**:
- Total: Integer - count of all valid records processed
- ByStatus: Dict[String, Integer] - distribution by Estatus value (e.g., {"Cerrada": 45, "En Progreso": 12})
- ByUrgency: Dict[String, Integer] - distribution by Urgencia value
- ByImpact: Dict[String, Integer] - distribution by Impacto value

**Calculation Timing**: Pre-calculated during CSV parsing (single pass)

**Storage**: In output JSON `_metadata.kpis` section for immediate Dashboard Hub access

---

### ConversionMetadata

File-level metadata attached to output JSON.

**Attributes**:
- Type: String = "postmortem" (constant)
- Version: String = "1.0" (converter version)
- Created: ISO 8601 timestamp - when conversion was performed
- RecordCount: Integer - total valid records in data array
- SourceFilename: String - original CSV filename (for audit trail)
- ConversionTimestamp: ISO 8601 timestamp - same as created

**Purpose**: Enable Dashboard Hub auto-load system to:
1. Discover files by type ("postmortem")
2. Track conversion time for ordering
3. Validate file integrity (record count)
4. Audit data lineage (source filename)

---

### ValidationError

Represents a single validation failure.

**Attributes**:
- Row: Integer - line number in CSV (1-indexed)
- RecordId: String - ID de incidencia value (if parseable)
- ErrorType: String - "validation", "parsing", "missing_field"
- Issues: List[Dict] - array of field-level issues:
  - field: String - column name
  - error: String - human-readable error description
  - value: String (optional) - problematic value found

**Purpose**: Non-blocking error collection for audit and debugging

---

## Relationships

```
ConversionRequest
  ├── input: CSV file path
  └── → [parse CSV with encoding/delimiter detection]
       ├── generates: PostmortemRecord (valid)
       ├── collects: ValidationError (invalid)
       └── accumulates: PostmortemKPIMetrics (running totals)
            └── → [output JSON]
                 ├── _metadata: ConversionMetadata + PostmortemKPIMetrics
                 └── data: [PostmortemRecord]
            └── → [error report JSON]
                 ├── summary: counts and success_rate
                 └── errors: [ValidationError]
            └── → [auto-discovery]
                 └── Dashboard Hub discovers *-postmortem.json files via index.json
```

---

## State Transitions

The converter is stateless (single-pass). Per-record flow:

```
CSV Row
  ↓
Parse fields
  ↓ (success) ↓ (failure)
Validate      → ValidationError
  ↓ (pass)
Normalize values
  ↓
Calculate Despliegue
  ↓
Accumulate KPIs
  ↓
PostmortemRecord (output)
```

---

## Data Volumes & Constraints

**Performance Targets** (from spec SC-003):
- Converter processes 1000+ record CSV in <5 seconds
- Estimated throughput: 200-1000 records/sec depending on validation complexity

**File Size Assumptions**:
- Typical postmortem file: 100-500 records
- Maximum tested: 1000+ records
- Encoding overhead: UTF-8 ≤ 4 bytes/char, minimal impact on throughput

**Memory Constraints**:
- KPI aggregates: O(1) memory (fixed-size dicts for status/urgency/impact values)
- Error collection: O(n) where n = number of invalid records (typically <5-10% of records)
- No full file load required: streaming parse via csv.DictReader

---

## Integration Points

**Input**: CSV files in `data/input/` directory (via CLI argument or batch scan)

**Output**:
- JSON file → `data/output/{basename}-postmortem.json`
- Error report → `data/output/{basename}_errors.json`
- Auto-discovered by → Dashboard Hub index.json system

**Dashboard Integration**:
- Postmortem Dashboard loads JSON from `data/output/`
- Dashboard Hub auto-loads via `-postmortem` suffix discovery
- KPIs in metadata enable zero-latency KPI card display
