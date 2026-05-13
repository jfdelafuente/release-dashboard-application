---
description: "Implementation tasks for CSV to JSON Workflow feature"
---

# Tasks: CSV to JSON Workflow for Massive Incidents

**Feature Branch**: `001-csv-to-json-workflow`

**Input**: Design documents from `specs/001-csv-to-json-workflow/`

**Prerequisites**: plan.md (✓), spec.md (✓), data-model.md (✓), research.md (✓), contracts/ (✓), quickstart.md (✓)

**Status**: Ready for implementation

## Implementation Strategy

This feature is decomposed into 3 independent user stories (P1, P2, P3) that can be developed in parallel or sequentially. Recommended approach:

1. **MVP**: Implement User Story 1 (Basic JSON conversion) first - provides immediate value
2. **Enhancement 1**: Add User Story 2 (Auto-detection) - improves user experience
3. **Enhancement 2**: Add User Story 3 (Large files + error handling) - production readiness

Each user story is independently testable and can be deployed separately.

## Phase 1: Setup & Project Structure

### Goals
- Initialize project structure per plan.md
- Set up testing infrastructure (pytest)
- Create module skeleton with basic imports
- Establish code quality standards

### Independent Test Criteria
- Project structure exists with all directories
- pytest discovery finds test files
- All modules can be imported without errors
- Linting tools (if configured) pass on skeleton

---

- [X] T001 Create project directory structure: `csv_to_json/` module with `__init__.py`, `converter.py`, `validators.py`, `normalizers.py`, `delimiter.py`, `encoding.py`, `schemas.py`

- [X] T002 Create `tests/` directory structure: `tests/unit/`, `tests/integration/`, `tests/conftest.py`

- [X] T003 [P] Create pytest configuration: `pytest.ini` with coverage settings (minimum 80%), marker definitions for slow tests

- [X] T004 [P] Create `.gitignore` additions for Python (venv/, __pycache__/, *.pyc, .pytest_cache/, .coverage)

- [X] T005 Create test fixtures: `tests/fixtures/` with `sample-incidents.csv` (copy from incidencias/CS-Informe*.csv)

- [X] T006 Create module skeleton with docstrings: `csv_to_json/__init__.py`, add description of module purpose

- [X] T007 [P] Create requirements.txt with dependencies: pytest, pytest-cov (no other external dependencies for main code)

---

## Phase 2: Foundational Infrastructure

### Goals
- Implement encoding detection (supports UTF-8, Windows-1252, Latin-1, UTF-8-sig)
- Implement delimiter detection (supports comma, semicolon, tab)
- Implement date parsing with exact format validation
- Implement field normalization logic

### Independent Test Criteria
- Encoding detection correctly identifies 5+ encoding types from byte signatures
- Delimiter detection correctly identifies comma, semicolon, tab from sample rows
- Date parser correctly parses "dd/mm/yyyy HH:mm AM/PM" format
- Normalization correctly processes Urgencia, Estatus, casing, whitespace

### These tasks have NO story label because they support ALL user stories

---

- [X] T008 [P] Implement encoding detection: `csv_to_json/encoding.py` - BOM detection + fallback encoding detection per research.md section 1

- [X] T009 [P] Write unit tests for encoding detection: `tests/unit/test_encoding.py` with tests for UTF-8, UTF-8-sig, Windows-1252, Latin-1

- [X] T010 [P] Implement delimiter detection: `csv_to_json/delimiter.py` - csv.Sniffer + fallback logic per research.md section 2

- [X] T011 [P] Write unit tests for delimiter detection: `tests/unit/test_delimiter.py` with tests for comma, semicolon, tab delimiters

- [X] T012 [P] Implement date parsing: `csv_to_json/validators.py` add `parse_date()` function for "dd/mm/yyyy H:MM AM/PM" format per research.md section 3

- [X] T013 [P] Write unit tests for date parsing: `tests/unit/test_validators.py` with valid/invalid date examples including AM/PM variants

- [X] T014 [P] Implement Urgencia normalization: `csv_to_json/normalizers.py` add `normalize_urgencia()` function to extract text from "N-Text" format per research.md section 4

- [X] T015 [P] Write unit tests for Urgencia normalization: `tests/unit/test_normalizers.py` with tests for "4-Baja", "3-Medio", "2-Alta", "1-Crítica" variants

- [X] T016 [P] Implement field normalization utility: `csv_to_json/normalizers.py` add functions for trim, casing normalization (title case), date format preservation

- [X] T017 [P] Write unit tests for field normalization: `tests/unit/test_normalizers.py` with edge cases (extra spaces, mixed casing, special chars)

---

## Phase 3: User Story 1 - Convert CSV to Dashboard-Compatible JSON (P1)

### Story Goal
As an analyst, I need to convert a CSV file of massive incidents into a JSON format that the Massive Incidents Dashboard can load and process.

### Independent Test Criteria
- Can load valid CSV with 10+ incident records
- Converts all fields to JSON objects with exact field names
- All valid records appear in output JSON
- Dashboard can parse output JSON without errors
- Field values are preserved exactly (except for normalized fields like Urgencia)

### Acceptance Scenarios
1. **Given** a CSV file with incident data in standard format, **When** the conversion runs, **Then** valid JSON is produced with all records
2. **Given** a CSV with dates in "dd/mm/yyyy HH:mm a" format, **When** converted, **Then** dates are preserved exactly as-is

---

- [X] T018 [US1] Implement field validator schema: `csv_to_json/schemas.py` - Define FIELD_VALIDATORS dict with rules for ID, Descripción, Estatus, etc. per data-model.md

- [X] T019 [US1] Implement validation logic: `csv_to_json/validators.py` - Add `validate_record()` function checking required fields, types, enum values

- [X] T020 [US1] Write unit tests for validation: `tests/unit/test_validators.py` - Test each validation rule (presence, type, format, values) with examples from data-model.md

- [X] T021 [US1] Implement CSV parser: `csv_to_json/converter.py` - Read CSV with detected encoding/delimiter, parse headers and rows

- [X] T022 [US1] Implement record normalization pipeline: `csv_to_json/converter.py` - Apply normalization to all fields before validation

- [X] T023 [US1] Implement JSON output writer: `csv_to_json/converter.py` - Write valid records as JSON array with all fields from CSV (per json-output-schema.md)

- [X] T024 [US1] Write integration test for basic conversion: `tests/integration/test_converter_e2e.py` - Load sample CSV, run converter, verify JSON structure and field values

- [X] T025 [US1] Test with real data: `tests/integration/test_converter_e2e.py` - Run converter on incidencias/CS-Informe*.csv, verify all records convert or errors reported

- [X] T026 [US1] Implement summary statistics: `csv_to_json/converter.py` - Calculate total_records, successful, failed, success_rate for output

---

## Phase 4: User Story 2 - Auto-Detect Encoding and Delimiters (P2)

### Story Goal
As an analyst, I need the conversion workflow to automatically detect the encoding and delimiter of my CSV file so I don't have to specify these manually.

### Independent Test Criteria
- Auto-detects comma, semicolon, and tab delimiters correctly
- Auto-detects UTF-8, UTF-8-sig, Windows-1252, Latin-1 encodings
- Handles encoded files with special characters (accents, emojis) correctly
- Falls back gracefully when encoding/delimiter ambiguous

### Acceptance Scenarios
1. **Given** CSV with comma delimiter and UTF-8 encoding, **When** converter runs, **Then** delimiter and encoding are detected automatically
2. **Given** CSV with semicolon delimiter and UTF-8-sig encoding, **When** converter runs, **Then** special characters preserved correctly
3. **Given** CSV with Latin-1 encoding, **When** converter runs, **Then** accented characters (é, ñ) preserved in output

---

- [ ] T027 [US2] Integrate encoding detection into converter: `csv_to_json/converter.py` - Read file bytes, detect encoding before parsing

- [ ] T028 [US2] Integrate delimiter detection into converter: `csv_to_json/converter.py` - Read sample lines, detect delimiter before CSV parsing

- [ ] T029 [US2] Add encoding/delimiter to error messages: `csv_to_json/converter.py` - Log detected encoding and delimiter for debugging

- [ ] T030 [US2] Write integration test for encoding detection: `tests/integration/test_converter_e2e.py` - Test with UTF-8, UTF-8-sig, Windows-1252, Latin-1 encoded files

- [ ] T031 [US2] Write integration test for delimiter detection: `tests/integration/test_converter_e2e.py` - Test with comma, semicolon, tab delimited files

- [ ] T032 [US2] Test special character preservation: `tests/integration/test_converter_e2e.py` - Verify é, ñ, ü, emojis preserved in output JSON

---

## Phase 5: User Story 3 - Handle Large Files & Error Feedback (P3)

### Story Goal
As an analyst, I need the workflow to handle large CSV files and provide clear error messages when something goes wrong.

### Independent Test Criteria
- Processes 1000+ record files within 5 seconds
- Skips records with validation errors, continues processing
- Generates detailed error report with row numbers, field names, reasons
- Outputs valid records even when some records fail
- Error messages are human-readable and actionable

### Acceptance Scenarios
1. **Given** CSV with 1000+ incidents, **When** converter completes, **Then** all valid records converted, processing time <5 seconds
2. **Given** CSV with missing required fields, **When** converter runs, **Then** clear error identifies field name and row numbers
3. **Given** CSV with invalid data (bad dates, unknown Estatus), **When** converter runs, **Then** user informed of invalid data with row numbers and fix suggestions

---

- [ ] T033 [US3] Implement error collection: `csv_to_json/converter.py` - Accumulate errors for each failed record without stopping processing

- [ ] T034 [US3] Implement error report generation: `csv_to_json/converter.py` - Format errors as JSON per json-output-schema.md with summary stats

- [ ] T035 [US3] Write error messages: `csv_to_json/converter.py` - Create user-friendly error messages (no stack traces) per quickstart.md "Common Pitfalls"

- [ ] T036 [US3] Implement error report output: `csv_to_json/converter.py` - Write conversion-error-report.json alongside converted-incidents.json

- [ ] T037 [US3] [P] Write unit tests for error handling: `tests/unit/test_validators.py` - Test error message formatting for each validation rule

- [ ] T038 [US3] Write integration test for mixed valid/invalid records: `tests/integration/test_converter_e2e.py` - Convert file with 50% valid, 50% invalid records

- [ ] T039 [US3] Write integration test for large files: `tests/integration/test_converter_e2e.py` - Generate 1000+ record CSV, verify <5 second conversion, check error report accuracy

- [ ] T040 [US3] Test performance with edge cases: `tests/integration/test_converter_e2e.py` - Test with maximum field lengths, special characters, etc.

---

## Phase 6: Polish & Cross-Cutting Concerns

### Goals
- Achieve 80% code coverage minimum
- Document all public APIs
- Create user-facing documentation
- Optimize performance
- Prepare for dashboard integration

### Independent Test Criteria
- Code coverage ≥80% across all modules
- All public functions have docstrings
- README/quickstart.md covers common usage
- Performance benchmarks meet targets (<2 sec typical, <5 sec large)

---

- [X] T041 [P] Verify code coverage: Run `pytest tests/ --cov=csv_to_json --cov-report=term-missing`, ensure 80%+ coverage

- [X] T042 [P] Fill coverage gaps: Identify uncovered lines from report, add tests to reach 80%

- [X] T043 [P] Add docstrings: Add Python docstrings to all public functions in converter.py, validators.py, normalizers.py per style guide

- [X] T044 [P] Create module README: `csv_to_json/README.md` with usage examples, API reference, error handling guide

- [X] T045 [P] Update quickstart.md: Add "Testing Quick Start" section with pytest commands, coverage reporting

- [X] T046 [P] Performance benchmarking: Run converter on progressively larger test files (100, 500, 1000+ records), document times

- [X] T047 [P] Optimize hot paths: Profile bottlenecks (if any), optimize date parsing, field validation, JSON serialization

- [X] T048 Create user documentation: `csv_to_json/USAGE.md` with step-by-step guide for analysts using the tool/dashboard integration

- [X] T049 Create error reference: `csv_to_json/ERROR_REFERENCE.md` with all possible error messages and how to fix them

- [X] T050 Integration with dashboard: Update `massive-incidents-dashboard.html` to use converter module (if JavaScript) or add import instructions for Python version

---

## Task Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational - blocking all stories)
├→ T008-T017 (Encoding, Delimiter, Parsing, Normalization)
    ↓
Phase 3 (US1 - Core Conversion) [CAN START AFTER Phase 2]
├→ T018-T026 (Schema, Validation, Parser, Writer, Integration tests)
    ↓
Phase 4 (US2 - Auto-Detection) [CAN START AFTER Phase 2 OR IN PARALLEL with US1]
├→ T027-T032 (Integrate detection, Test with encodings/delimiters)
    ↓
Phase 5 (US3 - Error Handling) [CAN START AFTER Phase 3 OR IN PARALLEL with US1+US2]
├→ T033-T040 (Error collection, Report, Messages, Large file testing)
    ↓
Phase 6 (Polish) [FINAL PHASE - after all user stories complete]
└→ T041-T050 (Coverage, Documentation, Performance, Dashboard integration)
```

## Parallel Execution Examples

### Fastest Path (Sequential MVP)
```
Phase 1 → Phase 2 → Phase 3 → Phase 6
Total: ~2 weeks for MVP (US1 + basic testing + documentation)
```

### Balanced Path (Parallel user stories)
```
Phase 1
    ↓
Phase 2 (4 days)
    ↓
Phase 3 + Phase 4 + Phase 5 in parallel (6-8 days each)
    ↓
Phase 6 (3-4 days)
Total: ~2-3 weeks for complete feature
```

### Aggressive Path (Maximum parallelization after Phase 2)
```
Phase 1 (1 day)
Phase 2 (3-4 days)
Phase 3, 4, 5 in parallel (pick 2-3 devs, work simultaneously)
Phase 6 (2-3 days, coordinator integrates)
Total: ~1-2 weeks with 3 developers
```

## Task Checklist Summary

| Phase | Task Count | Stories | Notes |
|-------|-----------|---------|-------|
| Phase 1: Setup | 7 | None | Foundation; blocks everything |
| Phase 2: Foundational | 10 | None | Core infrastructure; blocks all stories |
| Phase 3: US1 | 9 | P1 | Basic conversion; provides MVP value |
| Phase 4: US2 | 6 | P2 | Auto-detection; can parallel with US1 after Phase 2 |
| Phase 5: US3 | 8 | P3 | Error handling; can parallel with US1+US2 after Phase 2 |
| Phase 6: Polish | 10 | None | Finishing touches; blocks deployment |
| **TOTAL** | **50** | 3 | ~2-3 weeks depending on team size |

## User Story Priorities & Dependencies

| Story | Priority | Dependencies | Can Start | Est. Duration |
|-------|----------|--------------|-----------|--------------|
| US1 | P1 | Phase 2 | Day 5 | 4-5 days |
| US2 | P2 | Phase 2 (US1 helpful but optional) | Day 5 (parallel with US1 OK) | 3-4 days |
| US3 | P3 | Phase 3 (US1) | Day 9 (or parallel after Phase 2) | 4-5 days |

## MVP Scope (Recommended First Release)

For fastest MVP (1.5-2 weeks):
- ✅ Phase 1: Setup
- ✅ Phase 2: Foundational infrastructure
- ✅ Phase 3: User Story 1 (basic CSV → JSON conversion)
- ✅ Phase 6: Polish (documentation, testing)
- ❌ Phase 4: US2 (defer to v1.1)
- ❌ Phase 5: US3 (defer to v1.1, but test error cases)

MVP delivers: Analysts can convert well-formed CSV files to JSON, load in dashboard, with basic error reporting.

---

**Status**: ✅ TASKS COMPLETE - 50 tasks across 3 user stories, ready for implementation

**Generated**: 2026-05-13
**Next Command**: Select one user story or MVP scope, begin with Phase 1 setup tasks, then Phase 2 foundational tasks
