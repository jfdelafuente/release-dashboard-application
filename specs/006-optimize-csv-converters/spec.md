# Feature Specification: CSV-to-JSON Converters Review & Optimization

**Feature Branch**: `006-optimize-csv-converters`

**Created**: 2026-05-14

**Status**: Draft

**Input**: User description: "vamos a revisar los 2 conversores de csv to json (convert_incident y convert_postmortem) para que realice la conversion y los calculos de forma eficiente y correcta."

## User Scenarios & Testing

### User Story 1 - Validate Massive Incidents Converter (Priority: P1)

Data analysts need to convert CSV files containing massive incident data into JSON format compatible with the Massive Incidents Dashboard. The converter must correctly parse CSV files with various encodings (UTF-8, Windows-1252, Latin-1, etc.), auto-detect delimiters, normalize field values, validate data integrity, and generate accurate JSON output with minimal errors.

**Why this priority**: This is the primary use case. The Massive Incidents Dashboard depends on correctly converted and validated incident data. Any issues with data conversion directly impact dashboard accuracy and user analysis.

**Independent Test**: Can be tested by executing the converter on real massive incident CSV files and verifying that:
- All valid records are converted to JSON with correct field normalization
- Invalid records are captured in an error report with specific details
- JSON output validates against dashboard schema
- KPI calculations match manual spot-checks

**Acceptance Scenarios**:

1. **Given** a CSV file with mixed encodings and semicolon delimiters, **When** converter processes it, **Then** all records are correctly parsed and written to JSON with proper UTF-8 encoding
2. **Given** a CSV with required fields missing, **When** converter processes it, **Then** invalid records are logged in error report with specific field names and row numbers
3. **Given** a CSV with 10,000 records, **When** converter processes it, **Then** conversion completes in under 5 seconds and uses less than 500MB memory
4. **Given** a CSV with Urgencia values like "4-Baja", **When** converter processes it, **Then** normalized to "Baja" in JSON output

---

### User Story 2 - Validate Postmortem Converter (Priority: P2)

Quality assurance teams need to convert postmortem CSV data into JSON format compatible with both the Postmortem Dashboard and the Dashboard Hub auto-load system. The converter must handle 13 postmortem-specific fields, derive the Despliegue field (PAP for earliest date, MESA for others), pre-calculate KPI metrics, and generate accurate JSON with proper timestamp tracking.

**Why this priority**: High priority because postmortem analysis is critical for incident analysis and trending. The Despliegue derivation is a complex business rule that must be implemented correctly.

**Independent Test**: Can be tested by executing the converter on postmortem CSV files and verifying:
- All 13 fields are correctly mapped and normalized
- Despliegue field is correctly derived based on oldest date
- KPI aggregations (total, by_status, by_urgency, by_impact) are mathematically correct
- Dashboard Hub can auto-load the JSON and display KPIs

**Acceptance Scenarios**:

1. **Given** a postmortem CSV with 50 records spanning multiple days, **When** converter processes it, **Then** exactly one record has Despliegue="PAP" (the record with earliest date) and rest have Despliegue="MESA"
2. **Given** a CSV with identical timestamps for multiple records, **When** converter processes it, **Then** first occurrence gets PAP, others get MESA (stable, deterministic ordering)
3. **Given** a postmortem CSV with status values in various cases ("cerrado", "CERRADO", "Cerrado"), **When** converted, **Then** all normalized to title case ("Cerrado") for consistency
4. **Given** a CSV with 1000 postmortem records, **When** converter processes it, **Then** KPI calculations for by_status, by_urgency, by_impact are mathematically correct (spot-check 5 values)

---

### User Story 3 - Optimize Converter Performance (Priority: P3)

DevOps teams need converters to handle large CSV files efficiently without excessive memory usage or long processing times. Converters must scale to handle 50,000+ record files with predictable performance and provide progress indication for long-running operations.

**Why this priority**: Important for operational efficiency and scalability, but not blocking if small-to-medium files are the primary use case. Becomes critical as incident volumes grow.

**Independent Test**: Can be tested by processing progressively larger CSV files (100, 1K, 10K, 50K records) and measuring:
- Processing time per 1000 records remains consistent
- Peak memory usage stays below 1GB regardless of file size
- Progress feedback is provided for files >10K records

**Acceptance Scenarios**:

1. **Given** a CSV file with 50,000 records, **When** converter processes it, **Then** completes in under 30 seconds on standard hardware
2. **Given** a CSV file with 100,000 records, **When** converter processes it, **Then** memory usage never exceeds 800MB and remains stable
3. **Given** a long-running conversion, **When** conversion is in progress, **Then** user receives periodic status updates (every 10,000 records processed)

---

### User Story 4 - Validate Error Handling & Reporting (Priority: P2)

Support teams need detailed error reports that clearly identify which records failed validation, why they failed, and what values were problematic. Error reporting must be comprehensive enough to allow quick identification and correction of data quality issues in source systems.

**Why this priority**: High priority because poor error reporting makes debugging data issues very difficult for analysts and support teams. Clear error messages reduce support tickets and enable faster data corrections.

**Independent Test**: Can be tested by processing CSV files with intentional data quality issues and verifying:
- Error report correctly identifies all invalid records with row numbers
- Error messages are specific and actionable (not generic)
- Error report structure allows programmatic analysis (JSON format)
- Edge cases like empty files, files with only headers, duplicate records are handled gracefully

**Acceptance Scenarios**:

1. **Given** a CSV with missing required fields in multiple records, **When** converter processes it, **Then** error report lists each record with specific field names that are missing or empty
2. **Given** a CSV with invalid date formats, **When** converter processes it, **Then** error report shows the problematic date value and expected format
3. **Given** a CSV with invalid Estatus values (e.g., "Unknown Status"), **When** converter processes it, **Then** error report lists the invalid value and valid options
4. **Given** a CSV file with 0 records (only header), **When** converter processes it, **Then** result shows 0 valid records, 0 failed, success_rate=100% (not an error)

---

### Edge Cases

- What happens when a CSV file has a BOM (Byte Order Mark) at the start?
- How does converter handle mixed line endings (CRLF vs LF) in same file?
- What happens when a CSV has duplicate column headers?
- How does converter handle extremely long field values (>10KB)?
- What happens when Despliegue derivation has ties (multiple records with same earliest date)?
- How does converter handle null/empty Urgencia fields in normalization?
- What happens when CSV has column order different from expected?

## Requirements

### Functional Requirements

- **FR-001**: Massive Incidents Converter MUST auto-detect file encoding from BOM and file content
- **FR-002**: Massive Incidents Converter MUST auto-detect CSV delimiter (comma, semicolon, tab) using statistical analysis
- **FR-003**: Converter MUST normalize Urgencia field by extracting text after numeric prefix (e.g., "4-Baja" → "Baja")
- **FR-004**: Converter MUST normalize Estatus and Impacto fields to title case while preserving case-insensitivity
- **FR-005**: Converter MUST validate all required fields are present and non-empty for each record
- **FR-006**: Converter MUST validate Estatus values against allowed list (Abierto, Pendiente, En Progreso, En Curso, Asignado, Resuelto, Cerrado, Cancelado)
- **FR-007**: Converter MUST validate Urgencia values against allowed list (Baja, Medio, Alta, Crítica)
- **FR-008**: Converter MUST validate Impacto field contains only "Masiva"
- **FR-009**: Postmortem Converter MUST derive Despliegue field: PAP for record with earliest date, MESA for all others
- **FR-010**: Postmortem Converter MUST parse dates in format DD-MMM (e.g., "26-abr") and DD/MM/YYYY (e.g., "26/04/2026")
- **FR-011**: Postmortem Converter MUST calculate KPI metrics aggregated by Estatus, Urgencia, and Impacto
- **FR-012**: Postmortem Converter MUST calculate Dashboard Hub KPIs: cerradas_percent, pap_resueltas_percent, mesa_resueltas_percent
- **FR-013**: Converter MUST include metadata in output JSON: type, version, created timestamp, record_count, source_filename
- **FR-014**: Converter MUST generate separate error report file containing: summary (total, successful, failed, success_rate) and detailed error list
- **FR-015**: Error report MUST include row number, record ID, error type, and specific field-level issues for each failed record
- **FR-016**: Converter MUST handle edge case: files with empty content, only headers, or malformed CSV structure gracefully
- **FR-017**: Converter MUST preserve all input fields in output JSON, including optional fields
- **FR-018**: Converter MUST process files in streaming fashion to minimize memory usage for large files

### Key Entities

- **IncidentRecord**: Represents a single incident entry with fields: ID, Description, Status, Submission Date, Assigned Group, Urgency, Impact, and optional resolution fields
- **PostmortemRecord**: Represents a postmortem entry with 13 fields including derived Despliegue field and calculated KPI contributions
- **ConversionMetadata**: File-level metadata including encoding detected, delimiter detected, record counts, KPI aggregates
- **ValidationError**: Record-level error with row number, record ID, specific field errors, and original values

## Success Criteria

### Measurable Outcomes

- **SC-001**: Converter correctly processes 100% of valid records (records with all required fields present and valid values)
- **SC-002**: Converter achieves >= 95% success rate on real-world incident CSV files (95% of records valid)
- **SC-003**: Error report identifies 100% of invalid records with specific, actionable error messages
- **SC-004**: Processing time for 10,000 record file is under 5 seconds on standard hardware
- **SC-005**: Peak memory usage for processing 50,000 record file is under 500MB
- **SC-006**: Postmortem Despliegue derivation is correct in 100% of test cases (deterministic, stable)
- **SC-007**: KPI calculations in postmortem output match manual calculations (spot-check on 20+ records)
- **SC-008**: Converted JSON validates against dashboard schema with zero structural errors
- **SC-009**: Auto-detected encoding matches actual file encoding in 99%+ of test cases
- **SC-010**: Auto-detected delimiter matches actual CSV delimiter in 100% of test cases

## Assumptions

- **Scope**: Review and optimization applies to both convert_incidents (massive) and convert_postmortem converters
- **Input Format**: CSV files are well-formed (even if with encoding issues) and don't contain embedded newlines in field values
- **Data Volume**: Primary use cases involve 100-50,000 records; optimization targets this range
- **User Interface**: Converters are used via Python API (CsvToJsonConverter class) or as CLI scripts, not as web service
- **Error Tolerance**: Up to 5% of records can fail validation due to data quality issues; errors must be captured, not silently ignored
- **Performance Baseline**: Current implementation is functional but may have inefficiencies in normalization, KPI calculation, or memory usage
- **Output Format**: JSON output schema is already defined and validated against dashboard requirements
- **Backward Compatibility**: Changes should maintain compatibility with existing dashboard integration (field names, formats, KPI structure)
- **Testing**: Existing test suite covers functionality; optimization should maintain or improve test coverage
