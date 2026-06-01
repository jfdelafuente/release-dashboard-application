# Research & Design Decisions: Postmortem CSV to JSON Converter

## Encoding Detection Strategy

**Decision**: Use chardet library for auto-detection with fallback to manual BOM check + common encodings

**Rationale**:
- Project already imports chardet in csv_to_json module for Massive Incidents converter
- Proven approach for mixed international data
- Handles BOM (Byte Order Mark) for UTF-8-sig files

**Alternatives Considered**:
- Pure manual detection (BOM + try/except): Less robust for Latin-1/Windows-1252 mixed files
- ichardet (faster chardet): Not needed for file conversion speed requirements

**Implementation**: Reuse `encoding.py` module from csv_to_json, adapt for postmortem-specific testing

---

## Delimiter Detection Strategy

**Decision**: Use csv.Sniffer with fallback to manual character counting for edge cases

**Rationale**:
- Python stdlib csv.Sniffer is reliable for common delimiters (comma, semicolon, tab)
- Fallback prevents failures on small files where Sniffer may be uncertain
- Already proven in csv_to_json.delimiter module

**Alternatives Considered**:
- Fixed delimiter (comma only): Won't work for Spanish data that uses semicolons
- Pandas read_csv with sep=None: External dependency, not in project

**Implementation**: Reuse `delimiter.py` module from csv_to_json unchanged

---

## Date Format Handling

**Decision**: Support both "DD-MMM" (Spanish abbrev) and "DD/MM/YYYY" formats; normalize to "DD/MM/YYYY"

**Rationale**:
- Spec indicates input formats: "DD-MMM" or "DD/MM/YYYY"
- Postmortem Dashboard expects consistent format for sorting
- Massive Incidents converter handles similar normalization

**Implementation**: Create date_parser utility that:
1. Detects format (check for slash vs dash, presence of time component)
2. Parses using appropriate format string
3. Reformats to "DD/MM/YYYY" or ISO 8601 per dashboard requirements

---

## Despliegue Derivation Logic

**Decision**: Track all three date fields, find global minimum, assign PAP to that record, MESA to rest

**Rationale**:
- Spec requirement: "oldest date indicates PAP deployment"
- Date fields: Fecha de envío, Fecha de notificación, Fecha de última resolución
- Edge case: If all dates identical, assign PAP to first date with warning in error report

**Implementation Strategy**:
1. On first pass: collect all dates from all records into single list with (date_value, record_id) tuples
2. Find minimum date value
3. On second pass: assign Despliegue="PAP" to matching record, "MESA" to others
   OR: Single-pass approach: track running minimum, assign PAP to first seen

**Edge Cases**:
- Missing dates: Skip that field when comparing
- Unparseable dates: Already marked as error, skip in derivation
- All identical dates: Warning in error report, use first-seen rule

---

## KPI Calculation Architecture

**Decision**: Single-pass calculation during CSV read; accumulate aggregates into in-memory dicts

**Rationale**:
- Performance: <5 seconds for 1000+ records requires efficiency
- Spec SC-005: KPIs must match dashboard (pre-calculated, not computed later)
- Reuse pattern from csv_to_json._calculate_massive_kpis()

**KPI Metrics to Calculate**:
- Total count of valid records
- Distribution by Estatus (e.g., {"Cerrada": 45, "En Progreso": 12})
- Distribution by Urgencia (e.g., {"Alta": 30, "Media": 20, "Baja": 7})
- Distribution by Impacto (e.g., {"Masiva": 25, "Alta": 32})

**Implementation**:
- During conversion, maintain running counters: `kpis = {"total": 0, "by_status": {}, "by_urgency": {}, "by_impact": {}}`
- After processing each valid record, update counters
- Return kpis dict with final tallies

---

## Output JSON Structure

**Decision**: Mirror Massive Incidents structure with postmortem-specific metadata

**Rationale**:
- Dashboard Hub already expects this structure
- Consistent with established patterns in project
- Enables code reuse in dashboard auto-load system

**JSON Schema**:
```json
{
  "_metadata": {
    "type": "postmortem",
    "version": "1.0",
    "created": "2026-05-13T14:30:00Z",
    "record_count": 95,
    "source_filename": "2026R4POSTMORTEM.csv",
    "conversion_timestamp": "2026-05-13T14:30:00Z",
    "kpis": {
      "total": 95,
      "by_status": {"Cerrada": 45, "En Progreso": 12, "Pendiente": 38},
      "by_urgency": {"Alta": 30, "Media": 45, "Baja": 20},
      "by_impact": {"Masiva": 25, "Alta": 35, "Media": 35}
    }
  },
  "data": [
    {
      "ID de incidencia": "INC000001",
      "Descripción": "...",
      "Estatus": "Cerrada",
      "Fecha de envío": "01/05/2026",
      "Grupo asignado": "...",
      "Fecha de notificación": "02/05/2026",
      "Fecha de última resolución": "03/05/2026",
      "Motivo de estado": "...",
      "MotivoEstado_Anterior": "...",
      "Grupo Resolutor": "...",
      "Urgencia": "Alta",
      "Impacto": "Masiva",
      "Grupo Remitente": "...",
      "Despliegue": "PAP"
    }
  ]
}
```

---

## File Discovery & Auto-Load Integration

**Decision**: Output files use `-postmortem` suffix; Dashboard Hub discovers via index.json pattern

**Rationale**:
- Spec SC-009: "100% of valid output files appear in auto-load index"
- Dashboard Hub already has build_index.py system for auto-discovery
- Filename pattern `-postmortem` distinguishes from massive incidents `-massive`

**Implementation**:
- Converter outputs: `{base_name}-postmortem.json`
- Example: `2026R4POSTMORTEM-postmortem.json`
- Dashboard Hub's build_index.py scans `data/output/` for `*-postmortem.json` files
- Index includes: filename, conversion timestamp, metadata (type, record_count)
- Auto-load triggered on Dashboard Hub page load

---

## Error Handling & Validation

**Decision**: Lenient on data, strict on structure; all errors logged, no silent failures

**Rationale**:
- SC-002: "Invalid records documented with specific error reasons (0 silent failures)"
- Follows Massive Incidents pattern: valid records pass through, errors collected
- Separate error report JSON file for audit/debugging

**Error Report Structure**:
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
      "record_id": "INC000023",
      "error_type": "validation",
      "issues": [
        {"field": "Fecha de envío", "error": "Unparseable date format: 'XX/XX/XXXX'"},
        {"field": "Urgencia", "error": "Invalid value 'Desconocida': must be one of [Alta, Media, Baja, Crítica]"}
      ]
    }
  ]
}
```

---

## Testing Strategy

**Decision**: Unit tests for each component; integration test for end-to-end conversion

**Rationale**:
- Encoding detection: test with files in UTF-8, UTF-8-sig, Windows-1252, Latin-1
- Delimiter detection: test with comma, semicolon, tab
- Date parsing: test "DD-MMM", "DD/MM/YYYY", edge cases
- Despliegue derivation: test with multiple records, identical dates edge case
- KPI calculation: verify counts match manual tallies, validate aggregates
- File discovery: verify `-postmortem` suffix files appear in Dashboard Hub index

**Test Data**: Create small CSV files with known data + expected outputs
