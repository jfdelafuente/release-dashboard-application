# Implementation Plan: CSV to JSON Workflow for Massive Incidents

**Branch**: `001-csv-to-json-workflow` | **Date**: 2026-05-13 | **Spec**: [Link to spec.md](spec.md)

**Input**: Feature specification from `specs/001-csv-to-json-workflow/spec.md`

## Summary

The CSV to JSON Workflow enables analysts to convert massive incident CSV files (with 100-1000+ records) into dashboard-compatible JSON format. The workflow automatically detects encoding and delimiters, validates and normalizes field values according to business rules (e.g., "4-Baja" → "Baja" for Urgencia), skips records with unrecoverable errors while reporting them, and outputs a clean JSON array plus an error report. All CSV fields are preserved in JSON to maximize data availability for the dashboard.

**Core Requirements**:
- Auto-detect CSV delimiter (comma, semicolon, tab)
- Auto-detect encoding (UTF-8, UTF-8-sig, Latin-1, Windows-1252, ISO-8859-15)
- Normalize field values: Urgencia (extract text from "N-Value" format), casing standardization
- Validate required fields and allowed values
- Skip invalid records, continue processing, report errors
- Output JSON with all fields + summary statistics

## Technical Context

**Language/Version**: Python 3.6+ (existing csv_to_json.py) OR JavaScript (HTML embedding in dashboard)

**Primary Dependencies**:
- Python option: `csv` (stdlib), `json` (stdlib), `pathlib` (stdlib)
- JavaScript option: Built-in File API, JSON (stdlib)

**Storage**: File system (temporary JSON and error report outputs)

**Testing**:
- Unit tests: Field validation, normalization logic, delimiter/encoding detection
- Integration tests: End-to-end CSV conversion with sample data files
- Tools: pytest (Python) or Jest/Mocha (JavaScript)

**Target Platform**: Browser-based (HTML/JavaScript embedding in Massive Incidents Dashboard) OR standalone Python script

**Project Type**: Web application component (data import/transformation pipeline) with optional standalone utility

**Performance Goals**:
- Convert 100-500 incidents in under 2 seconds
- Handle 1000+ incidents within 5 seconds
- Memory usage <100MB even with large files

**Constraints**:
- <200ms response time for typical dataset (100-500 records)
- JSON output must be valid and parseable in 100% of cases
- Error messages must be human-readable and actionable
- All special characters (é, ñ, ü, emojis) must be preserved

**Scale/Scope**:
- File size: up to 1000+ incident records per file
- Fields: 11 fields per record (ID, Priority, Description, Status, Submit Date, Assigned Group, Last Resolution Date, Resolution Group, Urgency, Impact, Sending Group)
- Success rate: Minimum 85% of well-formed records

## Constitution Check

**GATE 1: Code Quality (Principle I)**
- ✅ PASS: Single Responsibility - workflow module will separate concerns (parsing, validation, normalization, output)
- ✅ PASS: Complexity - conversion logic is straightforward (field mapping, simple validation)
- ✅ PASS: Maintainability - code will use named constants (not magic numbers), clear function names

**GATE 2: Testing Standards (Principle II)**
- ✅ PASS: Minimum 80% code coverage required - test all validation rules, normalization, delimiter detection
- ✅ PASS: Unit tests BEFORE implementation - test data validation first, then implement
- ✅ PASS: Integration tests - test with actual CSV file from incidencias/CS-Informe*.csv

**GATE 3: User Experience Consistency (Principle III)**
- ✅ PASS: Color/layout - error messages will use orange theme consistent with dashboard
- ✅ PASS: Terminology - will use exact field names from CLAUDE.md (Estatus, Urgencia, Impacto, etc.)
- ✅ PASS: Error messages - user-friendly, actionable, not raw error codes

**GATE 4: Performance Requirements (Principle IV)**
- ✅ PASS: <2 seconds for typical files - Python/JS can easily handle CSV parsing
- ✅ PASS: <5 seconds for 1000+ records - efficient algorithms, no unnecessary operations
- ✅ PASS: <100MB memory - streaming not needed for incident volumes (<1000 records)

**GATE 5: Security & Data Integrity (Principle V)**
- ✅ PASS: Input validation - all CSV data sanitized before processing
- ✅ PASS: No eval() - field mapping done via safe lookup tables
- ✅ PASS: Data protection - incident details treated as sensitive

**GATE 6: Documentation & Maintainability (Principle VI)**
- ✅ PASS: Architecture documented in this plan
- ✅ PASS: Complex functions have JSDoc/docstrings
- ✅ PASS: Data validation rules documented in assumptions

**Constitution Status**: ✅ ALL GATES PASS - Plan is aligned with project constitution

## Project Structure

### Documentation

```
specs/001-csv-to-json-workflow/
├── spec.md               # Feature specification (✓ complete)
├── plan.md               # This file (implementation plan)
├── research.md           # Phase 0 output (technology decisions, alternatives)
├── data-model.md         # Phase 1 output (entity schemas, validation rules)
├── quickstart.md         # Phase 1 output (quick start guide for developers)
└── contracts/
    ├── csv-input-schema.md       # Input CSV field definitions
    └── json-output-schema.md     # Output JSON structure
```

### Source Code Structure

**Option 1 (Recommended): Standalone Python Module**

```
csv_to_json/
├── __init__.py
├── converter.py          # Main CSV to JSON conversion logic
├── validators.py         # Field validation (required, type, format, values)
├── normalizers.py        # Field normalization (trim, casing, date parsing)
├── delimiter.py          # CSV delimiter detection
├── encoding.py           # File encoding detection
└── schemas.py            # Field definitions and allowed values

tests/
├── unit/
│   ├── test_validators.py
│   ├── test_normalizers.py
│   ├── test_delimiter.py
│   └── test_encoding.py
├── integration/
│   ├── test_converter_e2e.py
│   └── fixtures/
│       └── sample-incidents.csv
└── conftest.py
```

**Option 2 (Alternative): JavaScript/HTML Integration**

```
massive-incidents-dashboard.html   # Extend with CSV upload form
├── <script>
│   ├── CsvParser.js               # Delimiter and encoding detection
│   ├── CsvValidator.js            # Field validation
│   ├── CsvNormalizer.js           # Field normalization
│   └── CsvConverter.js            # Main conversion orchestration
└── </script>
```

**Selected**: Option 1 (Python standalone) with Option 2 as future migration target

## Phase 0: Research

### Research Tasks (to be resolved)

1. **Encoding Detection Algorithms**
   - Task: Evaluate chardet vs manual BOM/signature detection
   - Decision needed: Best approach for handling UTF-8-sig, Windows-1252, Latin-1
   - Rationale: Different methods have different accuracy/performance tradeoffs

2. **Date Parsing for "dd/mm/yyyy HH:mm a" Format**
   - Task: Find or implement parser for this exact format
   - Decision needed: Use datetime.strptime or custom regex parser
   - Rationale: Python datetime may need custom format string

3. **CSV Dialect Detection**
   - Task: Evaluate csv.Sniffer vs manual delimiter detection
   - Decision needed: How to handle edge cases (comma in quoted fields, etc.)
   - Rationale: Sniffer is built-in but may be unreliable for ambiguous files

4. **Error Reporting Format**
   - Task: Best practices for error reports (JSON, CSV, HTML)
   - Decision needed: How to structure error details for user consumption
   - Rationale: Must be actionable, not overwhelming with technical jargon

**Phase 0 Deliverable**: `research.md` with findings and technology decisions

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**Entity: IncidentRecord**
```
Fields:
- ID de incidencia: text, required, non-empty
- Prioridad: text, optional (passed through)
- Descripción: text, required, non-empty, max 5000 chars
- Estatus: enum [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado], required
- Fecha de envío: datetime (dd/mm/yyyy HH:mm a format), required
- Grupo asignado: text, required, non-empty
- Fecha de última resolución: datetime (dd/mm/yyyy HH:mm a format), optional
- Grupo Resolutor: text, optional (passed through)
- Urgencia: enum [Bajo, Medio, Alto, Crítica] (after normalizing from "4-Baja" → "Baja"), required
- Impacto: enum [Masiva] (only one value allowed), required
- Grupo Remitente: text, optional (passed through)

Validation Rules:
- All required fields must be present and non-empty
- Estatus must be one of exact list (case-insensitive after normalization)
- Urgencia must be parsed from "N-Text" format and normalized to text-only
- Impacto must be "Masiva" exactly
- Fecha de envío must parse successfully to datetime
- If Fecha de última resolución present, must parse successfully to datetime
```

### Input/Output Contracts (`contracts/`)

**CSV Input Schema** (`csv-input-schema.md`)
```
Column Order (from example file):
1. ID de incidencia (string, INC000003884945)
2. Prioridad (string, Media/Alta/Crítica)
3. Descripción (string, may contain // / - and special chars)
4. Estatus (string, Cerrado/Abierto/etc.)
5. Fecha de envío (string, dd/mm/yyyy H:MM AM/PM format)
6. Grupo asignado (string, CEP CAU AGI/RTV-TECSE RED DATOS/etc.)
7. Fecha de última resolución (string, dd/mm/yyyy H:MM AM/PM format)
8. Grupo Resolutor (string, may be same as Grupo asignado)
9. Urgencia (string, format "N-Text" like "4-Baja", "3-Medio", "2-Alta", "1-Crítica")
10. Impacto (string, always "Masiva")
11. Grupo Remitente (string, organization name)

Encoding: UTF-8, UTF-8-sig, Windows-1252, or Latin-1
Delimiter: comma (,), semicolon (;), or tab (\t)
Headers: Always present in first row
```

**JSON Output Schema** (`json-output-schema.md`)
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
  }
]
```

### Quickstart (`quickstart.md`)

Quick reference for developers:
- How to run the converter (CLI usage)
- How to use as a library (import, API)
- Common issues and solutions
- Example workflow

### Phase 1 Deliverables

1. ✅ `data-model.md` - Complete entity definition with validation rules
2. ✅ `contracts/csv-input-schema.md` - Input CSV specification
3. ✅ `contracts/json-output-schema.md` - Output JSON specification
4. ✅ `quickstart.md` - Developer quick start guide

## Phase 2: Task Decomposition

*Note: Phase 2 is executed by `/speckit-tasks` command (NOT this command)*

Phase 2 will decompose the design into actionable implementation tasks:
- Unit test implementations (validators, normalizers, detection)
- Integration test implementations
- Main converter orchestration
- Error handling and reporting
- Documentation and examples

**Next Command**: `/speckit-tasks` to generate `tasks.md` with detailed implementation tasks

## Architecture Decisions

1. **Single-file processing**: Process one CSV file at a time (not batch directory processing)
   - Rationale: Simpler error reporting, more predictable performance, user can control workflow

2. **Fail-safe approach**: Skip invalid records, continue processing
   - Rationale: Maximize data recovery; dashboard prefers partial data over no data

3. **All fields included in output**: Don't filter fields, preserve everything from CSV
   - Rationale: Dashboard or downstream systems may need data not immediately obvious

4. **Normalization before validation**: Normalize first, then validate
   - Rationale: Reduces false rejections due to formatting variations (casing, spacing)

5. **Detailed error reporting**: Include row number, field name, original value, reason
   - Rationale: Helps analysts fix source data for next attempt

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Encoding detection fails on exotic files | Medium | High | Provide manual encoding override option; test with all known encodings |
| Date parsing fails for variant formats | Low | Medium | Document exact expected format; provide clear error messages |
| Performance degrades with 1000+ records | Low | Medium | Profile with test data; optimize hot paths if needed |
| Validation too strict, rejects valid data | Medium | High | Iterative refinement during testing with real data files |

## Next Steps

1. **Before Phase 0**: Approve this plan and technical context
2. **During Phase 0**: Research encoding/delimiter detection, date parsing approaches
3. **During Phase 1**: Design data model, validate against real CSV file (incidencias/CS-Informe*.csv)
4. **Before Phase 2**: Finalize all contracts and schemas
5. **Phase 2+**: Execute `/speckit-tasks` to generate detailed implementation tasks

---

**Status**: ✅ PLAN COMPLETE - Ready for Phase 0 research
**Generated**: 2026-05-13
