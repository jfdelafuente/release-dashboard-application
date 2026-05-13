# Quick Start: CSV to JSON Workflow

**Date**: 2026-05-13
**For**: Developers implementing the CSV to JSON conversion feature

## 5-Minute Overview

The CSV to JSON Workflow converts massive incident CSV files into JSON format compatible with the Massive Incidents Dashboard. Key features:

- ✅ Auto-detects encoding (UTF-8, Windows-1252, Latin-1, etc.)
- ✅ Auto-detects delimiter (comma, semicolon, tab)
- ✅ Normalizes field values (e.g., "4-Baja" → "Baja")
- ✅ Validates required fields and allowed values
- ✅ Skips invalid records, continues processing
- ✅ Reports errors with row numbers and reasons
- ✅ Outputs valid records as JSON + error report

## Project Layout

```
specs/001-csv-to-json-workflow/
├── spec.md                          # Feature specification (read this first)
├── plan.md                          # Implementation plan (this file's parent)
├── research.md                      # Technology decisions & research findings
├── data-model.md                    # Entity schema & validation rules
├── quickstart.md                    # This file (quick reference)
└── contracts/
    ├── csv-input-schema.md          # Input CSV field definitions
    └── json-output-schema.md        # Output JSON structure
```

## Data Files

**Example CSV**: `data/input/CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv`
- 50+ real incident records
- Already contains the exact format you'll handle
- Use this for testing/validation

## Key Concepts

### Field Normalization

The converter **normalizes fields BEFORE validation**:

| Input | Output | Why |
|-------|--------|-----|
| `"4-Baja"` | `"Baja"` | Extract text from "N-Text" format for Urgencia |
| `"cerrado"` | `"Cerrado"` | Normalize to title case for Estatus |
| `"  text  "` | `"text"` | Trim whitespace from all fields |
| `"masiva"` | `"Masiva"` | Normalize to title case for Impacto |

### Field Validation

Required fields:
- `ID de incidencia` - must be non-empty
- `Descripción` - must be non-empty
- `Estatus` - must be in allowed list: [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado]
- `Fecha de envío` - must parse to valid datetime
- `Grupo asignado` - must be non-empty
- `Urgencia` - must normalize to: [Bajo, Medio, Alto, Crítica]
- `Impacto` - must be exactly "Masiva"

Optional fields (can be empty):
- `Prioridad`, `Fecha de última resolución`, `Grupo Resolutor`, `Grupo Remitente`

### Error Handling

When a record fails validation:
1. Record is SKIPPED (not included in output JSON)
2. Error details are recorded (row number, field name, original value, reason)
3. Processing CONTINUES (rest of file is processed)
4. Error report is generated

**Example**:
```
Input CSV: 1000 incidents
Processing: 850 valid ✓, 150 invalid ✗
Output JSON: Array of 850 valid records
Output Report: Details of 150 errors
Success Rate: 85%
```

## Architecture at a Glance

```
CSV File (raw bytes)
    ↓
Encoding Detection (UTF-8? Windows-1252? Latin-1?)
    ↓
Delimiter Detection (comma? semicolon? tab?)
    ↓
CSV Parser (extract headers & rows)
    ↓
Normalize Field Values (trim, casing, parse Urgencia)
    ↓
Validate Each Record (presence, type, format, values)
    ↓
┌─────────────────────────────────────┐
│ Valid? ─ YES → Add to output JSON  │
│        └─ NO  → Record error       │
└─────────────────────────────────────┘
    ↓
Generate Summary Statistics
    ↓
Output Files
├── converted-incidents.json (valid records)
└── conversion-error-report.json (error details)
```

## Implementation Checklist

### Phase 1: Setup & Testing (Week 1)

- [ ] Create `csv_to_json/` module structure
- [ ] Write unit tests for encoders/delimiter detection (in `tests/unit/`)
- [ ] Write unit tests for validation rules (in `tests/unit/`)
- [ ] Write unit tests for normalization logic (in `tests/unit/`)
- [ ] Set up pytest with fixtures and real CSV sample
- [ ] Verify 80% code coverage target

### Phase 2: Core Implementation (Week 1-2)

- [ ] Implement encoding detection (`encoding.py`)
- [ ] Implement delimiter detection (`delimiter.py`)
- [ ] Implement field normalizers (`normalizers.py`)
- [ ] Implement field validators (`validators.py`)
- [ ] Implement main converter orchestration (`converter.py`)
- [ ] Pass all unit tests

### Phase 3: Integration & Polish (Week 2-3)

- [ ] Write integration tests against real CSV file (in `tests/integration/`)
- [ ] Test with data/input/CS-Informe*.csv (ensure 100% pass rate for well-formed records)
- [ ] Generate error report for test file with intentional errors
- [ ] Test encoding variants (UTF-8-sig, Windows-1252, Latin-1)
- [ ] Test delimiter variants (comma, semicolon, tab)
- [ ] Verify error messages are user-friendly
- [ ] Performance test with 1000+ record file (<5 seconds)
- [ ] Document any edge cases found

### Phase 4: Dashboard Integration (Week 3+)

- [ ] Integrate into Massive Incidents Dashboard HTML
- [ ] Test with drag-and-drop file upload
- [ ] Validate JSON loads successfully in dashboard
- [ ] Display summary statistics to user
- [ ] Display error report to user
- [ ] Add success/error notifications

## Common Pitfalls to Avoid

1. **Date Format**: Input is "dd/mm/yyyy HH:mm AM/PM", NOT ISO 8601
   - ❌ Don't convert to "2026-01-02T08:14:00Z"
   - ✅ Do preserve "02/01/2026 8:14 AM" exactly

2. **Urgencia Format**: Input has numeric prefix, output should not
   - ❌ Don't output "4-Baja"
   - ✅ Do output "Baja" after normalization

3. **Empty Optional Fields**: Don't include null values
   - ❌ Don't output `"Prioridad": null`
   - ✅ Do omit the field entirely if empty in CSV

4. **Impacto Validation**: Only "Masiva" is allowed (no other values)
   - ❌ Don't accept "Alto", "Medio", "Bajo"
   - ✅ Do only accept "Masiva"

5. **Field Order**: Include ALL fields from CSV (not just documented ones)
   - ❌ Don't drop "Prioridad", "Grupo Resolutor", etc.
   - ✅ Do include every field present in input CSV

## Helpful Resources

- **Specification**: [spec.md](spec.md) - Full feature requirements
- **Data Model**: [data-model.md](data-model.md) - Entity schema & validation rules
- **Input Schema**: [contracts/csv-input-schema.md](contracts/csv-input-schema.md) - CSV field definitions
- **Output Schema**: [contracts/json-output-schema.md](contracts/json-output-schema.md) - JSON structure
- **Research Findings**: [research.md](research.md) - Technology decisions
- **Example Data**: `data/input/CS-Informe incidencias P1,  P2 y P3 - 2026 - 13 May 2026.csv`

## Testing Quick Start

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Integration Tests (with real CSV)
```bash
pytest tests/integration/ -v
```

### Check Code Coverage
```bash
pytest tests/ --cov=csv_to_json --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Against Real Data
```bash
python -m csv_to_json.converter \
  input=data/input/CS-Informe*.csv \
  output=converted.json \
  errors=errors.json
```

## Questions?

- **How do I handle encoding edge cases?** → See [research.md](research.md) section 1
- **What if date parsing fails?** → See [data-model.md](data-model.md) "Invalid Records" examples
- **Where do I find allowed Estatus values?** → See [contracts/csv-input-schema.md](contracts/csv-input-schema.md) Estatus field
- **What's the exact JSON output format?** → See [contracts/json-output-schema.md](contracts/json-output-schema.md)

---

**Next**: Read [spec.md](spec.md) for complete feature requirements, then [data-model.md](data-model.md) for entity details.

**Ready to code?** Start with unit tests in `tests/unit/test_validators.py` - TDD approach! 🚀
