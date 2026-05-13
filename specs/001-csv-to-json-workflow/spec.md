# Feature Specification: CSV to JSON Workflow for Massive Incidents

**Feature Branch**: `001-csv-to-json-workflow`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Crea un flujo de trabajo que permita construir un fichero json con los datos proporcionados en un fichero de incidencias masivas en formato cvs que se adapte al dashboard de incidencias masivas que tenemos."

## Clarifications

### Session 2026-05-13

- Q1: Qué reglas de validación exactas se deben aplicar a cada campo → A: Presencia + tipo de dato + formato específico (para fechas, IDs) + valores en lista permitida (para Estatus, Urgencia, Impacto)
- Q2: Qué operaciones de normalización se deben realizar → A: Normalización estándar: trim espacios, normalizar casing para campos controlados (Estatus, Urgencia), estandarizar fechas a formato esperado
- Q3: Cómo manejar registros con errores no recuperables → B: Procesar solo registros válidos, saltar inválidos, mostrar advertencia con filas saltadas

### Session 2026-05-13 (Segunda Ronda - Validación contra Datos Reales)

- Q1: Formato de Urgencia y valores permitidos → B: Normalizar a solo texto sin números ("4-Baja" → "Baja"), actualizar lista permitida a [Bajo, Medio, Alto, Crítica]
- Q2: Valores permitidos para Impacto → B: Impacto solo tiene un valor permitido: "Masiva" (todos los registros masivos)
- Q3: Campos adicionales en CSV (Prioridad, Grupo Resolutor, Grupo Remitente) → D: Incluir TODOS los campos del CSV en JSON output

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert CSV to Dashboard-Compatible JSON (Priority: P1)

As an analyst, I need to convert a CSV file of massive incidents into a JSON format that the Massive Incidents Dashboard can load and process. This is the primary workflow that enables data analysis on the dashboard.

**Why this priority**: This is the core functionality. Without this conversion, incident data cannot be visualized or analyzed in the dashboard.

**Independent Test**: Can be fully tested by loading a sample CSV file, running the conversion workflow, and verifying the JSON output matches the dashboard's expected schema and can be successfully loaded in the dashboard UI.

**Acceptance Scenarios**:

1. **Given** a CSV file with incident data in the standard format, **When** the conversion workflow is executed, **Then** a valid JSON file is produced with all valid records converted to the dashboard schema
2. **Given** a CSV file with multiple incidents where some have invalid data, **When** the workflow completes, **Then** valid incidents are converted, invalid incidents are skipped with error report, and JSON contains only valid records
3. **Given** a CSV file with dates in "dd/mm/yyyy HH:mm a" format, **When** converted to JSON, **Then** dates are preserved exactly as-is (no format conversion)
4. **Given** a CSV file with inconsistent Estatus values (e.g., "cerrado", "CERRADO", "Cerrado"), **When** normalized and validated, **Then** all are converted to canonical form and accepted

---

### User Story 2 - Auto-Detect Encoding and Delimiters (Priority: P2)

As an analyst, I need the conversion workflow to automatically detect the encoding and delimiter of my CSV file so I don't have to specify these manually for every file.

**Why this priority**: Incident CSV files come from various sources with different encodings (UTF-8, UTF-8-sig, Latin-1, Windows-1252) and delimiters (comma, semicolon, tab). Auto-detection reduces manual work and errors.

**Independent Test**: Can be fully tested by running the workflow on CSV files with different encodings (UTF-8, UTF-8-sig, Latin-1) and delimiters (comma, semicolon, tab) without specifying these parameters, and verifying correct conversion in each case.

**Acceptance Scenarios**:

1. **Given** a CSV file with comma delimiter and UTF-8 encoding, **When** the workflow runs without parameters, **Then** the correct delimiter and encoding are detected and conversion succeeds
2. **Given** a CSV file with semicolon delimiter and UTF-8-sig encoding, **When** the workflow runs, **Then** special characters and BOM are handled correctly
3. **Given** a CSV file with Latin-1 encoding, **When** the workflow runs, **Then** accented characters (é, ñ, etc.) are preserved correctly in JSON

---

### User Story 3 - Handle Large Files and Provide Error Feedback (Priority: P3)

As an analyst, I need the workflow to handle large CSV files with many incidents and provide clear error messages when something goes wrong, so I can debug issues quickly.

**Why this priority**: Production incident files may contain 1000+ records. Clear error messages help analysts identify and resolve data quality issues in their source files.

**Independent Test**: Can be fully tested by running the workflow on a large CSV file (1000+ incidents) and a malformed CSV file, verifying successful conversion for the large file and clear error messages for the malformed file.

**Acceptance Scenarios**:

1. **Given** a CSV file with 1000+ incidents, **When** the workflow completes, **Then** all records are converted and processing time is reasonable (<5 seconds)
2. **Given** a CSV file with missing required fields, **When** the workflow runs, **Then** a clear error message identifies which fields are missing and which rows are affected
3. **Given** a CSV file with invalid data (e.g., malformed dates), **When** the workflow runs, **Then** the user is informed of the invalid data with row numbers and field names

---

### Edge Cases

- What happens when the CSV file is empty (no records, only headers)? → Workflow completes successfully with JSON array containing 0 records and appropriate message to user
- What happens when CSV has extra columns not expected by the dashboard? → Extra columns are ignored; only expected fields are included in JSON output
- What happens when the CSV has duplicate incident IDs? → Both records are processed if valid (duplicates preserved in JSON; dashboard handles deduplication if needed)
- How does the workflow handle very long description fields (1000+ characters)? → Fields are preserved as-is without truncation; dashboard is responsible for display handling
- What happens when dates are in an unexpected format? → Record is marked invalid; row is skipped with error message specifying "Invalid date format: expected dd/mm/yyyy HH:mm a"
- How does the workflow handle special characters and emojis in description fields? → Special characters and emojis are preserved in output after normalization (trim only, no character filtering)
- What happens when a Estatus value is not in the allowed list after normalization? → Record is rejected with error "Invalid Estatus value: [value] not in allowed list: [list]"
- What happens when a required field is present but empty (blank cell)? → Record is rejected with error "Required field [field name] is empty in row [N]"
- What happens when ID de incidencia is not unique across records? → Both records are processed if valid (deduplication is dashboard responsibility)
- What happens when 90% of records have validation errors? → Workflow completes, outputs JSON with 10% valid records, and displays warning that "Only 10% of records were successfully converted"

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept CSV files as input via drag-and-drop interface or file selection
- **FR-002**: System MUST auto-detect CSV delimiter (comma, semicolon, tab) without user input
- **FR-003**: System MUST auto-detect file encoding (UTF-8, UTF-8-sig, Latin-1, Windows-1252, ISO-8859-15)
- **FR-004**: System MUST convert CSV records to JSON format including ALL fields from source CSV; core expected fields are: ID de incidencia, Descripción, Estatus, Fecha de envío, Grupo asignado, Urgencia, Impacto, Fecha de última resolución, plus any additional fields present in source (e.g., Prioridad, Grupo Resolutor, Grupo Remitente)
- **FR-005**: System MUST preserve exact date format from CSV ("dd/mm/yyyy HH:mm a") without conversion
- **FR-006**: System MUST handle BOM (Byte Order Mark) characters in filenames and field names automatically
- **FR-007**: System MUST normalize all data before validation: (a) trim leading/trailing whitespace, (b) normalize casing for controlled fields (Estatus, Urgencia, Impacto to title case), (c) for Urgencia field, extract text portion only (e.g., "4-Baja" → "Baja"), (d) standardize dates to expected format
- **FR-008**: System MUST validate each record against strict rules: (a) all required fields present (ID de incidencia, Estatus, Fecha de envío), (b) field types correct (ID/Grupos = text, dates = valid format, urgency/impact = from allowed list), (c) Estatus values limited to: Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado
- **FR-009**: System MUST skip records that fail validation after normalization; continue processing remaining records and report skipped records with details
- **FR-010**: System MUST provide detailed error report listing: row number, field name, original value, reason for rejection (missing, invalid format, value not in allowed list)
- **FR-011**: System MUST output JSON as an array of objects containing only successfully validated records
- **FR-012**: System MUST allow users to download the converted JSON file and error report (if any records were skipped)
- **FR-013**: System MUST preserve special characters, accents (é, ñ, ü), and emojis in text fields after normalization
- **FR-014**: System MUST display summary statistics: total records in CSV, records successfully converted, records skipped, percentage success rate

### Key Entities *(include if feature involves data)*

- **Incident Record (CSV)**: Source data row containing incident details; attributes: ID, Description, Status, Submit Date, Assigned Group, Urgency, Impact, Resolution Date; no special encoding beyond standard CSV
- **Incident Object (JSON)**: Converted representation of incident for dashboard consumption; attributes match CSV but structured as JSON object with exact field names as expected by dashboard
- **Conversion Output**: JSON array of incident objects; schema must match Massive Incidents Dashboard expectations exactly

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can convert a typical CSV file (100-500 incidents) to JSON in under 2 seconds
- **SC-002**: At least 85% of well-formed incident records from CSV are successfully converted without data loss (normalized values match original intent)
- **SC-003**: Auto-detection correctly identifies delimiter and encoding for 99% of incident CSV files without manual specification
- **SC-004**: Error messages clearly identify issues in 100% of skipped records (specific field name, row number, original value, reason for rejection)
- **SC-005**: Large CSV files (1000+ incidents) are processed successfully within 5 seconds even if 50% of records are invalid
- **SC-006**: Special characters and accents are preserved correctly in 100% of converted records after normalization
- **SC-007**: JSON output is valid (parseable by JSON parsers) in 100% of workflow executions (even if some records were skipped)
- **SC-008**: Normalization rules are applied correctly: casing normalization for controlled fields reduces validation failures by at least 20% compared to strict case-sensitive matching
- **SC-009**: Error report is generated and made available whenever any records are skipped, with summary statistics (total, converted, skipped, success percentage)

## Assumptions

- CSV files follow the standard incident format with headers in the first row
- Required fields (ID de incidencia, Estatus, Fecha de envío) are present in source CSV files (workflow will skip records where they are missing/empty)
- Users have Python 3.6+ installed (or workflow is embedded in dashboard application)
- Dates in source CSV are expected in "dd/mm/yyyy HH:mm a" format (12-hour clock with AM/PM indicator); other formats will cause record rejection
- The dashboard application already exists and expects JSON in the schema currently documented in CLAUDE.md
- BOM and encoding issues are primarily caused by CSV exports from Windows systems (UTF-8-sig, Windows-1252) and European systems (Latin-1)
- Users may upload CSV files from various sources (Remedy exports, custom scripts, manual reports) with varying data quality
- Performance target of 5 seconds for 1000+ incidents assumes standard developer laptop specifications
- Normalization includes: (a) whitespace trimming, (b) casing normalization (title case for Estatus/Urgencia/Impacto), (c) Urgencia numeric prefix extraction (e.g., "4-Baja" becomes "Baja"), (d) date format standardization
- Validation rules: (a) ID de incidencia and Grupo asignado = non-empty text, (b) Estatus = one of [Abierto, Pendiente, En Progreso, Resuelto, Cerrado, Cancelado], (c) Urgencia = one of [Bajo, Medio, Alto, Crítica] (after normalizing numeric prefixes like "4-Baja" → "Baja"), (d) Impacto = "Masiva" (only value allowed), (e) Fecha de envío = valid date in dd/mm/yyyy HH:mm a format
- Source data quality may be variable; workflow is designed to maximize valid data recovery rather than reject entire files for minor issues
