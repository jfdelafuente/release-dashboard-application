# Implementation Plan: Postmortem CSV to JSON Converter

**Branch**: `004-postmortem-converter` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-postmortem-converter/spec.md`

## Summary

Create a CSV-to-JSON converter for postmortem incident data that auto-detects encoding and delimiters, normalizes fields, derives deployment type from date analysis, pre-calculates KPIs, and integrates with Dashboard Hub auto-load discovery system. Follows Massive Incidents Converter pattern (chardet + csv.Sniffer) for encoding/delimiter detection, single-pass KPI calculation, and file-based output to `data/output/` with `-postmortem` suffix for automatic Dashboard Hub indexing.

## Technical Context

**Language/Version**: Python 3.7+ (matches project baseline)

**Primary Dependencies**: chardet (encoding detection), csv (stdlib), json (stdlib), pathlib (stdlib)

**Storage**: File-based - CSV input from `data/input/`, JSON output to `data/output/`

**Testing**: pytest (Python testing framework)

**Target Platform**: Windows/Linux CLI (cross-platform via pathlib)

**Project Type**: CLI data converter / ETL script

**Performance Goals**: Process 1000+ record CSV in under 5 seconds (SC-003)

**Constraints**: Zero encoding failures (100% auto-detection success per SC-008), zero silent failures (all errors logged per SC-002)

**Scale/Scope**: Variable CSV sizes (typical: 100-500 records; tested: 1000+), 13 input fields + 1 derived field

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **PASS** - No constitution violations detected:
- Follows established CSV-JSON conversion pattern (Massive Incidents Converter)
- Uses only stdlib + chardet (minimal dependencies)
- File-based storage (no new infrastructure required)
- Contributes to unified Dashboard Hub feature (002-dashboard-hub already merged)

## Project Structure

### Documentation (this feature)

```text
specs/004-postmortem-converter/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Design decisions and strategy
├── data-model.md        # Entity definitions and relationships
├── quickstart.md        # Testing scenarios and integration guide
├── spec.md              # Feature specification (completed)
└── tasks.md             # Task breakdown (/speckit-tasks command - NOT YET created)
```

### Source Code (repository root)

```text
csv_to_json/                    # Existing converter module (REUSE)
├── __init__.py
├── encoding.py                 # Reuse: encoding detection
├── delimiter.py                # Reuse: delimiter detection
├── normalizers.py              # Adapt: postmortem-specific normalization
├── validators.py               # Adapt: postmortem-specific validation
├── schemas.py                  # Adapt: 13-field postmortem schema
└── converter.py                # Adapt: add _calculate_postmortem_kpis()

convert_postmortems.py          # NEW: CLI entry point for postmortem conversion
                                 # (or adapt convert_incidents.py)

data/                            # Data directories
├── input/                       # CSV input files (users place files here)
├── output/                      # JSON output files (converter creates here)
└── errors/                      # Error reports (converter creates here)

tests/                           # Test suite
├── test_postmortem_encoding.py  # Unit: encoding detection
├── test_postmortem_delimiter.py # Unit: delimiter detection
├── test_postmortem_parser.py    # Unit: date parsing and Despliegue logic
├── test_postmortem_kpis.py      # Unit: KPI calculation
├── test_postmortem_converter.py # Integration: end-to-end conversion
└── test_data/                   # Test CSV files
    ├── valid-100.csv
    ├── invalid-mixed.csv
    ├── encoding-utf8.csv
    └── large-1000.csv
```

**Structure Decision**: Extend existing `csv_to_json` module (proven pattern for Massive Incidents) with postmortem-specific adaptations. Create new CLI entry point `convert_postmortems.py` or extend `convert_incidents.py`. Data directories already exist; converter creates output files with `-postmortem` suffix for Dashboard Hub discovery.

## Phase 0: Research (COMPLETE)

**Deliverables**: `research.md`

Completed design decisions for:
- Encoding detection strategy (chardet + BOM fallback)
- Delimiter detection strategy (csv.Sniffer + manual fallback)
- Date format handling (DD-MMM and DD/MM/YYYY normalization)
- Despliegue derivation logic (PAP = oldest date, MESA = rest)
- KPI calculation architecture (single-pass aggregation)
- Output JSON structure (metadata + data with postmortem KPIs)
- File discovery integration (`-postmortem` suffix pattern)
- Error handling approach (lenient data, strict structure)
- Testing strategy (unit + integration)

## Phase 1: Design (COMPLETE)

**Deliverables**: `data-model.md`, `quickstart.md`

Completed design for:
- **PostmortemRecord** entity (13 input fields + 1 derived Despliegue)
- **PostmortemKPIMetrics** (total, by_status, by_urgency, by_impact)
- **ConversionMetadata** (type, version, timestamps, audit trail)
- **ValidationError** (row-level error tracking)
- Data relationships and state transitions
- Performance targets and constraints
- Integration points with Dashboard Hub
- End-to-end testing scenarios (8 test cases)

## Next Phase: Implementation Planning

Run `/speckit-tasks` to generate:
- Detailed task breakdown by user story
- Dependency tracking
- Parallel execution opportunities
- Acceptance criteria for each task
- Estimated effort allocation

---

## Key Design Decisions Summary

| Decision | Rationale | Implementation |
|----------|-----------|-----------------|
| Reuse csv_to_json module | Proven pattern for Massive Incidents | Adapt encoding.py, delimiter.py, schemas.py, validators.py |
| Single-pass KPI calculation | Performance: <5 sec for 1000 records | In-memory dicts accumulate during CSV read |
| Despliegue from date analysis | Business requirement: oldest date = PAP | Two-pass or tracking-minimum approach |
| `-postmortem` suffix for auto-load | Dashboard Hub auto-discovery pattern | Index.json scans for filename pattern |
| Pre-calculated KPIs in metadata | Spec SC-010: Dashboard needs ready values | No deferred computation in dashboard |
| Lenient data validation | SC-002: 0 silent failures | Collect all errors, output valid records |
