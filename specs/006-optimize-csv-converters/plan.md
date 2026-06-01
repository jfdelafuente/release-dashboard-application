# Implementation Plan: CSV-to-JSON Converters Review & Optimization

**Branch**: `006-optimize-csv-converters` | **Date**: 2026-05-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-optimize-csv-converters/spec.md`

## Summary

Review and optimize two CSV-to-JSON converters (`convert_incidents` for Massive Incidents Dashboard and `convert_postmortem` for Postmortem Dashboard/Dashboard Hub) to ensure correct data conversion, accurate KPI calculations, and efficient processing of large files (50,000+ records).

**Primary Requirements**:
- Validate massive incidents converter: correct encoding/delimiter detection, field normalization, data validation, KPI calculation (aggregations + trends)
- Validate postmortem converter: correct Despliegue derivation, Dashboard Hub KPI calculation, 13-field mapping
- Optimize performance: <5 seconds for 10K records, <500MB memory for 50K records
- Improve error reporting: specific, actionable messages for all validation failures

**Technical Approach**: Refactor converters using streaming to minimize memory, optimize normalization and KPI aggregation algorithms, enhance error reporting with detailed field-level diagnostics, add comprehensive test coverage for edge cases and performance scenarios.

## Technical Context

**Language/Version**: Python 3.8+ (supports 3.8, 3.9, 3.10, 3.11 per GitHub Actions matrix)

**Primary Dependencies**:
- `csv` (built-in) for parsing
- `chardet` for encoding detection (if used)
- `json` (built-in) for output serialization

**Storage**: File-based (CSV input, JSON + error report output) - no database

**Testing**: `pytest` with coverage requirement >= 80% (existing test suite: 264 tests, 86% coverage)

**Target Platform**: Linux server (VPS deployment target), compatible with Windows/macOS for development

**Project Type**: Data processing pipeline / CLI tool (Python module with converter classes)

**Performance Goals**:
- Convert 10,000 record file: < 5 seconds
- Convert 50,000 record file: < 30 seconds
- Memory usage: < 500MB for 50K records, < 800MB for 100K records
- Consistent performance per 1000 records processed

**Constraints**:
- Must maintain backward compatibility with Massive Incidents Dashboard and Postmortem Dashboard/Dashboard Hub integration
- Output JSON schema must not change (field names, KPI structure already defined)
- Error handling must be non-blocking (errors captured, processing continues)
- Date parsing must handle multiple formats: DD-MMM (Spanish), DD/MM/YYYY

**Scale/Scope**:
- Primary use: 100-50,000 records per file
- Scalability target: handle up to 100,000 records without significant degradation
- Output: Single JSON file with all records + separate error report

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Reviewing against**: Release Dashboard Application Constitution v1.0.0

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Code Quality** | ✅ PASS | SRP, clarity, no magic numbers - converters follow these rules; refactoring will improve |
| **II. Testing Standards** | ✅ PASS | 80% coverage requirement met (86% current); edge cases and date/time tests use fixed refs |
| **III. UX Consistency** | ✅ PASS | Error reporting provides consistent, actionable messages; no UI changes (backend work) |
| **IV. Performance Requirements** | ✅ PASS | <5s for 10K records, <500MB memory - explicitly targeted in success criteria |
| **V. Security & Data Integrity** | ✅ PASS | Input validation required; no eval/dynamic code; data integrity via error reporting |
| **VI. Documentation & Maintainability** | ✅ PASS | Architecture documented in CLAUDE.md; changes will maintain documented KPI structure |

**Gate Status**: ✅ **PASS** - Feature complies with all constitutional principles

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/converters/csv_to_json/
├── __init__.py                  # Module exports
├── converter.py                 # Main CsvToJsonConverter class
├── encoding.py                  # Encoding detection logic
├── delimiter.py                 # Delimiter detection logic
├── normalizers.py               # Field normalization functions
├── validators.py                # Field validation logic
├── schemas.py                   # Field definitions and allowed values
├── postmortem_converter.py       # Postmortem-specific converter (if separate)
├── postmortem_schemas.py        # Postmortem field definitions and KPI calc
└── [other supporting modules as needed]

tests/
├── test_csv_reader.py           # Encoding/delimiter detection tests
├── test_converter.py            # Main converter integration tests
├── test_normalizers.py          # Field normalization unit tests
├── test_validators.py           # Field validation unit tests
├── test_postmortem_converter.py # Postmortem converter tests
├── test_performance.py          # Performance/scaling tests
├── test_edge_cases.py           # Edge case scenarios
└── test_data/                   # Test fixtures (CSV, JSON reference files)
```

**Structure Decision**: Existing modular structure in `src/converters/csv_to_json/` is appropriate for this refactoring. No new directories required. Tests are organized by module matching source structure, with dedicated test data directory for fixtures.

## Complexity Tracking

No constitutional violations requiring justification. Feature design aligns with all constitutional principles.
