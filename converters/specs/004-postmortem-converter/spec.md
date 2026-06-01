# Feature Specification: Postmortem CSV to JSON Converter

**Feature Branch**: `004-postmortem-converter`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Create validation and normalization script to generate JSON file for postmortem dashboard (same as what was done for massive incidents). Review project impact and develop specifications"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert Postmortem CSV to JSON (Priority: P1)

An analyst has a Postmortem CSV file with incident resolution data (status, deployment, dates, etc.) and needs to convert it to JSON format that the Postmortem Dashboard can load and analyze.

**Why this priority**: This is the core MVP feature. Without CSV→JSON conversion, the dashboard cannot access postmortem data. This enables the primary workflow: collect postmortem data → convert to JSON → load in dashboard.

**Independent Test**: Can be fully tested by loading a Postmortem CSV file, executing the converter, verifying the output JSON has correct structure with all incidents converted, and confirming the Postmortem Dashboard can load and display the data.

**Acceptance Scenarios**:

1. **Given** a Postmortem CSV file exists in `data/input/`, **When** the converter is executed, **Then** a JSON file is created in `data/output/` with the `-postmortem` suffix (e.g., `2026R4POSTMORTEM-postmortem.json`)
2. **Given** a CSV file with 100 valid incident records, **When** converted, **Then** all 100 records appear in the output JSON `data` array
3. **Given** a CSV file with mixed valid and invalid records, **When** converted, **Then** valid records are in output JSON and invalid records are documented in the error report
4. **Given** the output JSON file is loaded in Postmortem Dashboard, **When** the page displays data, **Then** all fields (Estatus, Grupo asignado, Fecha de envío, Urgencia, Impacto, etc.) are correctly populated and visible

---

### User Story 2 - Auto-Calculate Postmortem KPIs (Priority: P1)

An analyst wants to see quick KPI summaries on the Dashboard Hub without manually calculating metrics from the postmortem data (total records, status distribution, deployment breakdown, etc.).

**Why this priority**: This supports the unified Dashboard Hub feature. The Hub displays KPI summary cards from both dashboards. Postmortem KPIs must be calculated during conversion and stored in metadata, just like Massive Incidents.

**Independent Test**: Can be fully tested by converting a Postmortem CSV, verifying that KPIs are present in the output JSON metadata, and confirming the Dashboard Hub reads and displays these KPIs correctly.

**Acceptance Scenarios**:

1. **Given** a Postmortem CSV is converted, **When** the output JSON is examined, **Then** the `_metadata.kpis` object contains calculated metrics (total records, Estatus distribution, Urgencia distribution, Impacto distribution)
2. **Given** the Dashboard Hub loads a Postmortem JSON with KPIs in metadata, **When** the KPI cards render, **Then** values match the calculated metrics
3. **Given** 100 postmortem records with varying statuses, **When** KPIs are calculated, **Then** a breakdown by Estatus (Cerrada, En Progreso, etc.) and Urgencia is included
4. **Given** JSON file created in `data/output/` with `-postmortem` suffix, **When** Dashboard Hub starts, **Then** JSON is automatically discovered and indexed without manual file selection

---

### User Story 3 - Normalize Field Names and Data (Priority: P1)

Postmortem CSV has different field naming conventions (Status instead of Estatus, date format differences, etc.) and data format inconsistencies that need normalization for consistent dashboard display.

**Why this priority**: Data quality directly impacts dashboard functionality. Inconsistent field names prevent dashboard from loading data. Inconsistent formats cause parsing errors. This must be solved before dashboard integration works.

**Independent Test**: Can be fully tested by converting CSV with various field naming styles and date formats, then verifying the output JSON has consistent field names and properly formatted dates that the Postmortem Dashboard expects.

**Acceptance Scenarios**:

1. **Given** a CSV with mixed-case field names (Status, status, STATUS), **When** converted, **Then** all are normalized to expected field names (Status → Status, Estatus → Status where applicable)
2. **Given** dates in CSV format "26-abr" or "26/04/2026", **When** converted, **Then** dates are normalized to consistent format (DD/MM/YYYY or ISO 8601)
3. **Given** a CSV with multiple date fields, **When** converted, **Then** a derived Despliegue field is created with PAP assigned to oldest date and MESA to all others

---

### Edge Cases

- What happens when a Postmortem CSV is empty (0 records)? System should produce valid JSON with empty data array and report in error file.
- What happens when required fields (e.g., ID de incidencia, Estatus) are missing from CSV? System should skip those records and document in error report.
- What happens when date fields have unparseable formats (e.g., "invalid-date")? System should mark as error and skip that field/record.
- What happens when a CSV uses different encoding (UTF-8, Windows-1252, Latin-1)? System should auto-detect encoding and process correctly.
- What happens when all date fields are identical (no oldest date to determine)? System should assign PAP to first date and MESA to others, with a warning in error report.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Converter MUST detect encoding of Postmortem CSV files (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- **FR-002**: Converter MUST auto-detect CSV delimiter (comma, semicolon, tab)
- **FR-003**: Converter MUST normalize field names to match Postmortem Dashboard expectations (Estatus, Grupo asignado, Fecha de envío, Fecha de última resolución, etc.)
- **FR-004**: Converter MUST normalize date formats from CSV format (e.g., "26-abr") to consistent format (DD/MM/YYYY)
- **FR-005**: Converter MUST validate required fields are present and non-empty
- **FR-006**: Converter MUST calculate postmortem KPIs during conversion (total records, status distribution, deployment breakdown)
- **FR-007**: Converter MUST store KPIs in `_metadata.kpis` section of output JSON
- **FR-008**: Converter MUST include metadata in output JSON with type="postmortem", version, created timestamp, record_count, and calculated KPIs
- **FR-009**: Converter MUST output valid JSON that Postmortem Dashboard can load and parse without errors
- **FR-010**: Converter MUST generate detailed error report (separate JSON file) documenting all validation failures with row number and reason
- **FR-011**: Converter MUST handle single and batch file conversion (directory of CSVs)
- **FR-012**: Converter MUST derive and add a "Despliegue" field to each record (not present in input CSV): assign PAP to the record with oldest date across all date fields, assign MESA to all other records
- **FR-013**: Converter MUST normalize "Estatus" values to title case (Cerrada → Cerrada, PENDIENTE → Pendiente)
- **FR-014**: Converter MUST include file metadata in output JSON for discovery: timestamp of conversion (ISO 8601), filename with `-postmortem` suffix, source CSV filename for audit trail
- **FR-015**: Converter output MUST be discoverable by Dashboard Hub auto-load system: JSON files in `data/output/` directory with `-postmortem` suffix are automatically indexed and available for loading without manual intervention

### Key Entities

- **Postmortem Record**: Represents a single incident postmortem with fields:
  - ID de incidencia (unique identifier)
  - Descripción (incident description)
  - Estatus (status: Cerrada, En Progreso, Pendiente, etc.)
  - Fecha de envío (submission/opening date)
  - Grupo asignado (assigned team)
  - Fecha de notificación (notification date)
  - Fecha de última resolución (resolution date)
  - Motivo de estado (current state reason)
  - MotivoEstado_Anterior (previous state reason)
  - Grupo Resolutor (resolving team)
  - Urgencia (urgency level)
  - Impacto (impact level)
  - Grupo Remitente (submitting team)

- **Postmortem KPI Metrics**: Aggregated statistics including:
  - Total: Count of all postmortem records
  - By Estatus: Distribution of records by status (Cerrada, En Progreso, Pendiente, etc.)
  - By Urgencia: Distribution of records by urgency level
  - By Impacto: Distribution of records by impact level

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid postmortem records from CSV are converted to JSON without data loss
- **SC-002**: Invalid records are documented with specific error reasons in error report (0 silent failures)
- **SC-003**: Converter processes 1000+ record CSV files in under 5 seconds
- **SC-004**: Output JSON is valid and loadable by Postmortem Dashboard without parsing errors
- **SC-005**: KPI values calculated during conversion match values that would be calculated by dashboard (within 0.1% tolerance for percentages)
- **SC-006**: Postmortem Dashboard successfully loads and displays data from converted JSON with correct field mapping
- **SC-007**: Date fields in all records are properly formatted and sortable
- **SC-008**: CSV encoding auto-detection succeeds for 100% of test files with various encodings
- **SC-009**: Output JSON files are automatically discoverable by Dashboard Hub: 100% of valid output files in `data/output/` with `-postmortem` suffix appear in auto-load index without manual intervention
- **SC-010**: KPIs in output metadata are sufficient for Dashboard Hub to calculate and display KPI summary cards without additional computation (pre-calculated aggregates match dashboard display requirements)

## Clarifications

### Session 2026-05-13

- Q: What fields will be in the postmortem CSV input data? → A: ID de incidencia; Descripción; Estatus; Fecha de envío; Grupo asignado; Fecha de notificación; Fecha de última resolución; Motivo de estado; MotivoEstado_Anterior; Grupo Resolutor; Urgencia; Impacto; Grupo Remitente
- Q: How should deployment type (Despliegue) be determined? → A: Derived from date analysis - the oldest date in the file indicates PAP (Production) deployment; all others are MESA (Maintenance Escalated Service Area)
- Q: What additional output requirements beyond basic conversion? → A: (1) KPIs MUST be calculated and included in `_metadata.kpis` section; (2) File management/discovery system required to enable automatic JSON loading into Dashboard Hub (index generation with timestamp metadata)

## Assumptions

- Postmortem CSV files contain exactly these 13 input fields: ID de incidencia, Descripción, Estatus, Fecha de envío, Grupo asignado, Fecha de notificación, Fecha de última resolución, Motivo de estado, MotivoEstado_Anterior, Grupo Resolutor, Urgencia, Impacto, Grupo Remitente
- Field "ID de incidencia" is the unique identifier for each incident record
- "Estatus" field (Spanish) contains status values like "Cerrada", "En Progreso", "Pendiente", etc.
- Date fields (Fecha de envío, Fecha de notificación, Fecha de última resolución) may use format "DD-MMM" or "DD/MM/YYYY"
- "Despliegue" is NOT in the input CSV; it is DERIVED during conversion based on date analysis:
  - The record with the oldest date across all three date fields receives Despliegue = "PAP"
  - All other records receive Despliegue = "MESA"
- Field names in CSV are consistent within files (same column headers throughout)
- "Grupo asignado", "Grupo Resolutor", "Grupo Remitente" contain team/group identifiers
- "MotivoEstado_Anterior" tracks the previous state reason for audit/history purposes
- Postmortem Dashboard expects all 14 fields in output JSON (13 original + 1 derived Despliegue)
- Converter will reuse CSV→JSON infrastructure from Massive Incidents Converter (same modules, patterns)
- Output JSON will follow same structure as Massive Incidents: `{_metadata: {..., kpis: {...}}, data: [...]}`
- Error handling and validation logic can be adapted from Massive Incidents Converter with postmortem-specific adjustments
- The converter will be integrated into `convert_incidents.py` script or run as separate command `convert_postmortems.py`
- Auto-load file discovery: Dashboard Hub uses index.json system (like build_index.py) to discover postmortem JSON files by filename pattern (`*-postmortem.json`) in `data/output/` directory
- KPIs in metadata are pre-calculated during conversion (not deferred to dashboard): ensures Dashboard Hub can display KPI cards immediately without additional computation
- File metadata includes `conversion_timestamp` (ISO 8601) and `source_filename` for audit trail and data lineage tracking
