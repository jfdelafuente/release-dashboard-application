# Task Breakdown: CSV-to-JSON Converters Review & Optimization

**Feature**: 006-optimize-csv-converters | **Branch**: `006-optimize-csv-converters`

**Date**: 2026-05-14 | **Total Tasks**: 48 | **Estimated Duration**: 10-12 days

---

## Phase 1: Setup & Project Initialization

**Goal**: Prepare project structure, test infrastructure, and development environment

- [x] T001 Create test data structure with sample CSV files in `tests/test_data/`
- [x] T002 [P] Set up pytest configuration for CSV converter tests in `tests/conftest.py`
- [x] T003 [P] Create test utilities module `tests/utils.py` with helpers for CSV/JSON comparison
- [x] T004 Initialize performance profiling module `tests/test_performance.py` with timing fixtures
- [x] T005 Create mock data generator for large-scale testing (50K+ records) in `tests/utils/data_generator.py`
- [x] T006 Set up pre-commit hooks to run linting and tests on `src/converters/csv_to_json/`

---

## Phase 2: Foundational Infrastructure

**Goal**: Build common test framework and validation utilities required by all converters

- [x] T007 [P] Create base validator class `src/converters/csv_to_json/validators.py` with field validation framework
- [x] T008 [P] Implement encoding detection module `src/converters/csv_to_json/encoding.py` with BOM and charset detection
- [x] T009 [P] Implement delimiter detection module `src/converters/csv_to_json/delimiter.py` using csv.Sniffer + statistical analysis
- [x] T010 Create normalization utilities `src/converters/csv_to_json/normalizers.py` with title case, urgencia extraction, trim functions
- [x] T011 Create schemas module `src/converters/csv_to_json/schemas.py` defining allowed field values and validation rules
- [x] T012 [P] Write unit tests for validators in `tests/test_validators.py` (required fields, enum values, date parsing)
- [x] T013 [P] Write unit tests for normalizers in `tests/test_normalizers.py` (title case, urgencia extraction, edge cases)
- [x] T014 Write unit tests for encoding detection in `tests/test_encoding.py` (BOM, common encodings, fallbacks)
- [x] T015 Write unit tests for delimiter detection in `tests/test_delimiter.py` (comma, semicolon, tab, mixed)
- [x] T016 Create error reporting class `src/converters/csv_to_json/validation_error.py` with structured error tracking

---

## Phase 3: User Story 1 - Validate Massive Incidents Converter (Priority: P1)

**Goal**: Ensure massive incidents CSV converter correctly parses, normalizes, validates, and generates JSON compatible with Massive Incidents Dashboard

**Independent Test**: Converter correctly transforms CSV → JSON with proper field normalization, validation, and KPI aggregation for all 10K+ record files

### Core Implementation

- [x] T017 [US1] Implement base CsvToJsonConverter class in `src/converters/csv_to_json/converter.py` with main convert_file() method
- [x] T018 [US1] [P] Implement IncidentRecord class in `src/converters/csv_to_json/schemas.py` representing single incident entry
- [x] T019 [US1] [P] Implement field normalization pipeline in converter: Urgencia extraction, status title case, trim whitespace
- [x] T020 [US1] [P] Implement per-record validation in converter: required fields check, enum values check, date format validation
- [x] T021 [US1] Create metadata generation `src/converters/csv_to_json/converter.py` with encoding, delimiter, record counts, success rate
- [x] T022 [US1] Implement KPI calculation for Massive Incidents: total_incidencias, total_pendientes in `src/converters/csv_to_json/converter.py`
- [x] T023 [US1] [P] Implement aggregation by_estatus, by_urgencia, by_impacto in KPI calculator
- [x] T024 [US1] Implement trend calculation (7d, 15d, 30d) based on date filtering in `src/converters/csv_to_json/converter.py`
- [x] T025 [US1] Implement JSON output writer with metadata and KPIs in `src/converters/csv_to_json/converter.py`
- [x] T026 [US1] Implement error report generator `src/converters/csv_to_json/converter.py` with row numbers, record IDs, field-level issues

### Testing

- [x] T027 [US1] Write integration test for valid 100-record CSV in `tests/test_converter.py::test_valid_massive_incidents_100`
- [x] T028 [US1] [P] Write integration test for encoding detection (UTF-8, Windows-1252, Latin-1) in `tests/test_converter.py::test_encoding_detection_massive`
- [x] T029 [US1] [P] Write integration test for delimiter detection (comma, semicolon, tab) in `tests/test_converter.py::test_delimiter_detection_massive`
- [x] T030 [US1] Write integration test for field normalization (Urgencia extraction, status case) in `tests/test_converter.py::test_normalization_massive`
- [x] T031 [US1] Write test for KPI accuracy: verify by_estatus, by_urgencia, by_impacto counts match records in `tests/test_converter.py::test_kpi_calculations_massive`
- [x] T032 [US1] Write test for trend calculation accuracy: verify 7d/15d/30d trends vs manual calc in `tests/test_converter.py::test_trend_calculations`
- [x] T033 [US1] [P] Write test for JSON schema validation: verify output matches dashboard expectations in `tests/test_converter.py::test_json_schema_massive`
- [x] T034 [US1] Verify 80% test coverage for massive incidents converter: `pytest tests/ --cov=src.converters.csv_to_json.converter --cov-fail-under=80`

---

## Phase 4: User Story 2 - Validate Postmortem Converter (Priority: P2)

**Goal**: Ensure postmortem CSV converter correctly handles 13 fields, derives Despliegue field, calculates Dashboard Hub KPIs

**Independent Test**: Postmortem converter correctly derives Despliegue (PAP for earliest date, MESA for others), calculates Dashboard Hub KPIs, and generates JSON compatible with Dashboard Hub

### Core Implementation

- [x] T035 [US2] Create PostmortemRecord class `src/converters/csv_to_json/postmortem_schemas.py` with 13-field specification
- [x] T036 [US2] Implement date parsing for postmortem: DD-MMM format, DD/MM/YYYY, with/without time in `src/converters/csv_to_json/postmortem_schemas.py`
- [x] T037 [US2] Implement Despliegue derivation algorithm `src/converters/csv_to_json/postmortem_schemas.py`: scan all dates, PAP=earliest, MESA=others, deterministic tie-breaking
- [x] T038 [US2] [P] Create PostmortemKPIMetrics class `src/converters/csv_to_json/postmortem_schemas.py` with by_estatus, by_urgencia, by_impacto aggregation
- [x] T039 [US2] [P] Implement Dashboard Hub KPI calculation in PostmortemKPIMetrics: cerradas_percent, pap_resueltas_percent, mesa_resueltas_percent
- [x] T040 [US2] Create postmortem-specific converter class (extends CsvToJsonConverter) or add postmortem logic to base converter
- [x] T041 [US2] Implement postmortem metadata generation with Dashboard Hub KPIs in metadata.kpis object

### Testing

- [x] T042 [US2] Write integration test for postmortem CSV with multiple dates in `tests/test_postmortem_converter.py::test_despliegue_derivation_basic`
- [x] T043 [US2] Write test for Despliegue tie-breaking: verify first occurrence gets PAP in `tests/test_postmortem_converter.py::test_despliegue_tie_breaking`
- [x] T044 [US2] [P] Write test for date parsing: DD-MMM, DD/MM/YYYY, with/without time in `tests/test_postmortem_converter.py::test_date_parsing_formats`
- [x] T045 [US2] [P] Write test for Dashboard Hub KPI accuracy: cerradas_percent, pap/mesa_resueltas_percent in `tests/test_postmortem_converter.py::test_dashboard_hub_kpis`
- [x] T046 [US2] Write test for aggregation accuracy: by_estatus, by_urgencia, by_impacto in `tests/test_postmortem_converter.py::test_postmortem_aggregations`
- [x] T047 [US2] Verify 80% test coverage for postmortem converter: `pytest tests/ --cov=src.converters.csv_to_json.postmortem_schemas --cov-fail-under=80`

---

## Phase 5: User Story 4 - Validate Error Handling & Reporting (Priority: P2)

**Goal**: Generate detailed, actionable error reports that enable quick identification and correction of data quality issues

**Independent Test**: Error report correctly identifies all invalid records with specific field-level error messages, allowing analysts to fix source data efficiently

### Core Implementation

- [x] T048 [P] [US4] Enhance error reporting: include row number, record ID, specific field errors in error report JSON
- [x] T049 [P] [US4] Implement field-level error messages in validators with specific guidance (e.g., "Invalid Estatus: must be one of [...]")
- [x] T050 [US4] [P] Create error report generator that aggregates all ValidationError objects into structured JSON file
- [x] T051 [US4] Implement edge case handling: empty CSV, header-only CSV, malformed records (continue processing, log all)
- [x] T052 [US4] Add original value capture to error reporting for debugging purposes

### Testing

- [x] T053 [US4] Write test for missing required fields error reporting in `tests/test_error_handling.py::test_missing_required_fields`
- [x] T054 [US4] [P] Write test for invalid enum values in error report in `tests/test_error_handling.py::test_invalid_enum_values`
- [x] T055 [US4] [P] Write test for invalid date formats error reporting in `tests/test_error_handling.py::test_invalid_date_formats`
- [x] T056 [US4] Write test for empty CSV handling (0 records, 100% success rate) in `tests/test_error_handling.py::test_empty_csv`
- [x] T057 [US4] Write test for partial record handling: missing optional fields should not fail, only required fields in `tests/test_error_handling.py::test_optional_fields`
- [x] T058 [US4] Verify error report JSON structure: summary (total, successful, failed, success_rate) + errors array

---

## Phase 6: User Story 3 - Optimize Converter Performance (Priority: P3)

**Goal**: Ensure converters handle large files (50K+ records) efficiently without excessive memory or processing time

**Independent Test**: Converter processes 50K record file in <30 seconds, uses <500MB memory, maintains consistent throughput

### Core Implementation

- [x] T059 [US3] Optimize CSV parsing: use streaming with csv.DictReader to avoid loading entire file in memory
- [x] T060 [US3] [P] Optimize normalization: pre-compile regex patterns, cache title case results, avoid redundant operations
- [x] T061 [US3] [P] Optimize KPI aggregation: use efficient data structures (dict/Counter) instead of nested loops, calculate trends in single pass
- [x] T062 [US3] [P] Implement progress tracking for large files: log progress every 10K records to stderr without blocking
- [x] T063 [US3] Profile converter with large test files (10K, 50K, 100K) and identify bottlenecks in `tests/test_performance.py`

### Testing

- [x] T064 [US3] Write performance test for 10K records: must complete <5 seconds in `tests/test_performance.py::test_10k_records_timing`
- [x] T065 [US3] [P] Write performance test for 50K records: must complete <30 seconds, memory <500MB in `tests/test_performance.py::test_50k_records_timing`
- [x] T066 [US3] [P] Write performance test for 100K records: memory must stay <800MB in `tests/test_performance.py::test_100k_records_memory`
- [x] T067 [US3] Write performance test for consistent throughput: verify processing rate per 1K records is consistent
- [x] T068 [US3] Benchmark before/after optimization: document performance improvements in `docs/PERFORMANCE.md`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Final validation, documentation, and integration testing for complete feature

- [x] T069 [P] Conduct end-to-end integration test with actual Massive Incidents Dashboard: load JSON, verify KPIs display correctly
- [x] T070 [P] Conduct end-to-end integration test with Postmortem Dashboard + Dashboard Hub: verify Despliegue display, KPI cards show correct values
- [x] T071 Write edge case test: BOM handling, mixed line endings, duplicate headers in `tests/test_edge_cases.py`
- [x] T072 [P] Write edge case test: extremely long field values (>10KB) in `tests/test_edge_cases.py`
- [x] T073 Verify all 264 existing tests still pass after changes: `pytest tests/ --cov=src.converters --cov-fail-under=80`
- [ ] T074 Update CLAUDE.md with any changes to converter usage or API in `CLAUDE.md`
- [ ] T075 Create migration guide if output JSON format changed in `docs/MIGRATION.md`
- [ ] T076 [P] Document performance optimization decisions in `docs/PERFORMANCE.md`
- [ ] T077 [P] Update project README with converter usage examples in `README.md`
- [ ] T078 Verify linting passes: `flake8 src/converters/ --max-line-length=120`
- [ ] T079 Verify code formatting: `black --check src/converters/`
- [ ] T080 Verify imports are sorted: `isort --check-only src/converters/`

---

## Dependency Graph & Parallelization

### Critical Path (Sequential)
```
T001 → T002-T005 → T007-T015 → T017-T026 → T027-T033 → T035-T046 → T048-T058 → T059-T068 → T069-T080
```

### Parallelizable Groups

**After T001-T006 (Setup)**:
- T007-T015 (Foundational validators, normalizers, schemas) - All independent, can run in parallel [P]
- T012-T015 (Tests for foundational) - All independent, can run in parallel [P]

**During Phase 3 (Massive Incidents)**:
- T018-T020 (Record class, normalization, validation) - Independent, can run in parallel [P]
- T027-T033 (Integration tests) - Independent, can run in parallel [P]

**During Phase 4 (Postmortem)**:
- T035-T039 (PostmortemRecord, KPI metrics) - Independent, can run in parallel [P]
- T042-T047 (Postmortem tests) - Independent, can run in parallel [P]

**During Phase 5 (Error Handling)**:
- T048-T052 (Error implementation) - Partially parallelizable [P]
- T053-T058 (Error tests) - Independent, can run in parallel [P]

**During Phase 6 (Performance)**:
- T060-T062 (Optimization tasks) - Independent, can run in parallel [P]
- T064-T067 (Performance tests) - Independent, can run in parallel [P]

**Phase 7 (Polish)**:
- T069-T070 (Dashboard integration tests) - Can run in parallel [P]
- T076-T080 (Documentation and linting) - Independent, can run in parallel [P]

### Estimated Parallelization Savings
- Sequential execution: ~12 days
- With parallelization: ~8 days (40% reduction)

---

## Test Coverage Strategy

**Total Test Tasks**: 20 (T012-T015, T027-T034, T042-T047, T053-T058, T064-T068)

**Coverage Target**: 80% (Constitution requirement)

**By Category**:
- Unit tests (validators, normalizers, encoding, delimiter): 4 tasks
- Integration tests (converter pipeline): 8 tasks
- Performance tests (throughput, memory, scaling): 5 tasks
- Error handling tests: 3 tasks

**TDD Approach**: Tests written BEFORE implementation for each user story

---

## Implementation Strategy

### MVP Scope (Phase 3 Only)
**Minimal Viable Product**: US1 (Massive Incidents Converter)
- Task range: T001-T034
- Delivers: Working converter for massive incidents with proper validation and error reporting
- Enables: Dashboard to load and display incident data
- Duration: ~4 days

### Incremental Delivery
1. **Week 1**: Setup (T001-T006) + Foundational (T007-T016)
2. **Week 1-2**: US1 (T017-T034) + US2 (T035-T047)
3. **Week 2**: US4 (T048-T058) + US3 Performance (T059-T068)
4. **Week 2-3**: Polish (T069-T080)

### Risk Mitigation
- T012-T015 (Foundation tests) validate before main implementation
- T027-T033 (Converter tests) catch issues early in Phase 3
- T064-T068 (Performance tests) identify bottlenecks before Phase 7

---

## Success Criteria (Checklist)

- [ ] All 48 tasks completed
- [ ] All tests passing (264 existing + ~20 new = 284 total)
- [ ] Code coverage >= 80%
- [ ] Performance targets met:
  - [ ] 10K records: < 5 seconds
  - [ ] 50K records: < 30 seconds, < 500MB memory
- [ ] Massive Incidents Dashboard loads JSON successfully
- [ ] Postmortem Dashboard + Dashboard Hub display KPIs correctly
- [ ] Error reports are specific and actionable
- [ ] Linting, formatting, imports all pass
- [ ] Documentation updated with usage examples

---

**Last Updated**: 2026-05-14 | **Next Phase**: Implementation (run `/speckit-implement` with user story selection)
