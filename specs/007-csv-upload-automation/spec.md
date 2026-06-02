# Specification: CSV Upload UI & Auto-Convert Pipeline

**Phase**: 6
**Feature**: CSV Upload UI Integration with Auto-Conversion
**Status**: Specification
**Created**: 2026-06-02
**Last Updated**: 2026-06-02

---

## 1. Overview

Currently, CSV files must be manually placed in `data/input/` directory for conversion. This feature enables users to upload CSV files directly through the Dashboard Portal UI, with automatic validation, conversion, and dashboard refresh.

### User Problem Statement
Operations team members need a simple way to upload incident CSV files without SSH access or command-line knowledge. Current workflow requires manual file placement and manual trigger of conversion process.

### Solution Vision
Integrated upload interface in Dashboard Portal where users can:
1. Upload CSV file with visual feedback
2. See validation results instantly
3. Trigger conversion automatically
4. Watch dashboard update with new data in real-time

---

## 2. User Scenarios

### Scenario 1: Daily Incident Data Upload (Primary Flow)
**Actor**: Operations Manager
**Context**: New incident CSV export from external system (10-500 MB)
**Goal**: Get incident data into dashboard for team review within 2 minutes

**Steps**:
1. Opens Dashboard Portal in browser
2. Clicks "Upload CSV" button
3. Selects `incidents-2026-06-02.csv` file
4. System shows file size, encoding, detected headers
5. User clicks "Upload & Convert"
6. User sees progress indicator
7. System shows success message with data summary
8. Dashboard auto-refreshes and shows new incident data
9. User can filter/analyze immediately

**Expected Duration**: 2 minutes (including cron execution)

### Scenario 2: Error Handling - Invalid CSV
**Actor**: Operations Manager
**Context**: File with incorrect headers or encoding

**Steps**:
1. User uploads malformed CSV
2. System validates and shows specific error
3. Error message explains: "Missing required column 'Estatus'"
4. User downloads corrected file from help link
5. User re-uploads corrected file
6. Success

**Expected Duration**: < 1 minute recovery

### Scenario 3: Large File Upload
**Actor**: Operations Manager
**Context**: Monthly archive CSV (500+ MB)

**Steps**:
1. User selects large file
2. System shows file size warning if > 100MB
3. User confirms upload
4. Upload progresses with percentage indicator
5. After upload completes, conversion starts
6. User notified when complete

**Expected Duration**: 5-10 minutes (depending on file size and conversion)

---

## 3. Functional Requirements

### 3.1 Upload Interface
- **FR-1.1**: Dashboard Portal displays prominent "Upload CSV" button in main navigation or header
- **FR-1.2**: Clicking button opens modal dialog with upload form
- **FR-1.3**: Form accepts CSV files (extensions: .csv, .CSV)
- **FR-1.4**: Form shows file size limit (≤ 500MB)
- **FR-1.5**: User can select file via file picker or drag-and-drop
- **FR-1.6**: Form displays selected filename before upload

### 3.2 Pre-Upload Validation (Client-Side)
- **FR-2.1**: File extension validation (must be .csv)
- **FR-2.2**: File size validation (must be ≤ 500MB)
- **FR-2.3**: Error messages are user-friendly ("File too large" not "413 Payload Too Large")
- **FR-2.4**: User can cancel upload anytime

### 3.3 Upload & Server Validation
- **FR-3.1**: File uploaded to temporary location on server
- **FR-3.2**: Server validates file encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15)
- **FR-3.3**: Server validates CSV structure (can be parsed, has headers)
- **FR-3.4**: Server checks for required headers: "ID de incidencia", "Estatus", "Fecha de envío", "Grupo asignado", "Urgencia", "Impacto", "Descripción"
- **FR-3.5**: Server detects delimiter (comma, semicolon, tab) automatically
- **FR-3.6**: Validation results returned to user within 2 seconds

### 3.4 Preview & Confirmation
- **FR-4.1**: On successful validation, show preview with:
  - File name
  - Detected encoding
  - Detected delimiter
  - Number of rows detected
  - First 3-5 header names
  - Sample row count (e.g., "12,543 records found")
- **FR-4.2**: Show warnings if detected (e.g., "Unusual encoding detected")
- **FR-4.3**: User can confirm upload or cancel

### 3.5 File Management
- **FR-5.1**: Validated CSV file moved to `data/input/` directory
- **FR-5.2**: Original filename preserved (or date-stamped to avoid collisions)
- **FR-5.3**: Temporary files cleaned up (uploaded + rejected files removed after 1 hour)
- **FR-5.4**: System logs file upload with timestamp, user info, filename

### 3.6 Conversion Trigger
- **FR-6.1**: After file moved to `data/input/`, conversion starts automatically within 30 seconds
- **FR-6.2**: User informed that conversion is starting ("Your CSV is being processed...")
- **FR-6.3**: User can close modal and continue working (async process)

### 3.7 Conversion Completion & Feedback
- **FR-7.1**: System monitors conversion process
- **FR-7.2**: On success: Show message with converted record count
- **FR-7.3**: On error: Show user-friendly error message with troubleshooting link
- **FR-7.4**: Dashboard refreshes automatically to show new data
- **FR-7.5**: Conversion completion notification shown in dashboard (toast/alert)

### 3.8 Error Handling & Recovery
- **FR-8.1**: Network error during upload → Show "Connection failed, please try again"
- **FR-8.2**: Invalid header during validation → Show which headers are missing
- **FR-8.3**: Unsupported encoding → Show list of supported encodings
- **FR-8.4**: Conversion failure → Show conversion error log with line numbers (if applicable)
- **FR-8.5**: User can download error report for debugging

---

## 4. Non-Functional Requirements

### 4.1 Performance
- File upload must complete in < 30 seconds for files ≤ 100MB
- Validation must complete in < 2 seconds
- Dashboard refresh after conversion in < 5 seconds
- System must support 10+ concurrent uploads

### 4.2 Reliability
- Failed uploads must not corrupt `data/input/` directory
- Partial uploads must be cleaned up automatically
- Conversion must be idempotent (re-uploading same file shouldn't create duplicates)

### 4.3 Security
- File upload restricted to authenticated users [NEEDS CLARIFICATION: Authentication method?]
- Files scanned for malicious content before processing
- File names sanitized to prevent directory traversal attacks
- Uploaded files must be in `data/input/` only (no arbitrary file system access)

### 4.4 Usability
- UI must work on desktop and tablet browsers
- Error messages must be in Spanish
- Upload progress must be visible (percentage indicator)
- Mobile: File picker must trigger native file browser

### 4.5 Maintainability
- Upload handling logic separate from conversion logic
- Clear logging of upload events (success, failure, reason)
- Temporary file cleanup automated

---

## 5. Technical Context

### 5.1 Existing Components
- **Converters**: `converters/cli/convert_incidents.py` and `convert_postmortems.py` (existing, no changes needed)
- **Cron Script**: `scripts/generate-dashboards.sh` (existing, monitoring `data/input/`)
- **Dashboard**: `dashboards/dashboard-portal.html` and individual dashboards (will auto-refresh via existing index.json fetch)
- **Data Structure**: `data/input/` → `data/output/` → dashboards

### 5.2 Integration Points
- Dashboard Portal serves as upload interface
- Backend API handles validation and file movement
- Cron automation (existing `generate-dashboards.sh`) handles conversion
- Dashboard existing auto-refresh mechanism shows new data

### 5.3 No Changes Required
- Converter logic (no changes to CSV parsing, validation, normalization)
- Cron automation (no changes to scheduling)
- Dashboard structure (no changes to layout, only refresh trigger)
- Data formats (CSV input and JSON output unchanged)

---

## 6. Success Criteria

### 6.1 Functional Success
- Users can upload CSV files via web interface
- All uploaded files go through validation
- Invalid files rejected with clear error messages
- Valid files converted to JSON within 2 minutes
- Dashboard displays new data automatically after conversion

### 6.2 Performance Success
- Upload and validation complete in < 60 seconds for typical files (100MB)
- Dashboard updates within 5 seconds of conversion completion
- System handles 10+ concurrent uploads without degradation

### 6.3 User Experience Success
- Operations team can upload files without SSH/CLI knowledge
- User receives clear feedback at each step (upload, validation, conversion, completion)
- Error recovery is intuitive (user understands what went wrong and how to fix)
- Process requires no manual intervention after upload

### 6.4 Reliability Success
- Zero data loss from failed uploads
- Failed uploads don't block subsequent uploads
- System recovers gracefully from network interruptions
- Conversion accuracy unchanged from manual CSV placement method

---

## 7. Acceptance Scenarios

### Happy Path
```
GIVEN user is on Dashboard Portal
WHEN user clicks "Upload CSV"
THEN modal opens with file picker

WHEN user selects valid CSV file
AND user clicks "Upload"
THEN system validates file
AND shows preview with detected encoding, delimiter, row count
AND user confirms

WHEN user clicks "Convert"
THEN file moved to data/input/
AND system shows "Processing..." message

WHEN conversion completes
THEN dashboard shows new data
AND user sees success notification with record count
```

### Validation Failure
```
GIVEN user selects CSV with missing headers
WHEN system validates
THEN specific error shown: "Column 'Estatus' not found"
AND user offered option to download template
```

### Large File
```
GIVEN user selects 200MB CSV file
WHEN system shows size warning
AND user confirms
THEN upload progresses with percentage indicator
AND conversion queued after upload completes
```

---

## 8. Data Entities

### File Metadata
- **upload_filename**: Original filename from user
- **stored_filename**: Sanitized name in data/input/
- **file_size**: Bytes
- **detected_encoding**: UTF-8, UTF-8-sig, Windows-1252, etc.
- **detected_delimiter**: Comma, semicolon, tab
- **row_count**: Number of CSV rows
- **upload_timestamp**: When file uploaded
- **upload_user**: User ID (if auth enabled)
- **conversion_status**: pending, processing, success, failed
- **error_message**: If conversion failed

### Upload Event Log
- **timestamp**: When event occurred
- **event_type**: upload_started, validation_passed, validation_failed, conversion_started, conversion_completed, conversion_failed
- **filename**: File involved
- **details**: Any relevant info (error messages, row counts, etc.)

---

## 9. Edge Cases & Constraints

### Edge Cases Handled
1. **Duplicate filenames**: System auto-appends timestamp to prevent collision
2. **Very large files** (>100MB): Warning shown but allowed up to 500MB
3. **Special characters in filename**: Sanitized automatically
4. **Empty CSV files**: Validation error ("No data rows found")
5. **Files with BOM**: Handled by existing converter (UTF-8-sig support)
6. **Mixed line endings**: CSV parser handles CRLF/LF gracefully
7. **Concurrent uploads**: System queues and processes sequentially
8. **Network interruption**: File upload can retry; user informed
9. **Slow network**: Progress indicator shows upload status
10. **Browser tab closed during upload**: Upload continues; user can check status later

### Constraints
- Maximum file size: 500MB
- Supported file format: CSV only (not Excel, JSON, etc.)
- Supported encodings: UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15
- Required headers: Fixed set (cannot be customized)
- Upload location: `data/input/` only (cannot change)

---

## 10. Assumptions

### Technical Assumptions
1. Backend API server runs on same host as dashboards (or accessible via network)
2. `data/input/` and `data/output/` directories writable by API process
3. Cron job continues to monitor `data/input/` (no changes needed)
4. Browsers support modern HTML5 File API and fetch
5. CORS allows dashboard to communicate with API (if on different port)
6. Authentication mechanism exists (or feature works unauthenticated for now)

### User Assumptions
1. Users have valid CSV files in expected format (headers match required list)
2. Users have appropriate permissions to upload (no per-user quotas initially)
3. Users understand what the data represents (no validation of data semantics)
4. Cron job runs automatically (users not responsible for triggering conversion)

### Business Assumptions
1. Operations team uses Dashboard Portal regularly
2. CSV uploads happen during business hours (no night batch processing)
3. No audit trail required beyond basic logging
4. No data retention policies (files kept until manually deleted)
5. No per-user upload quotas or limits

---

## 11. Dependencies

### External Dependencies
- None (uses existing converters, cron, dashboards)

### Internal Dependencies
- Existing converter modules work correctly
- Cron script running and monitoring `data/input/`
- Dashboard auto-refresh mechanism functional
- `data/` directory structure intact

### Timeline Dependencies
- Can start immediately after Phase 5 completion
- No blockers from other features

---

## 12. Open Questions

None - specification is complete pending user confirmation of authentication approach.

---

## 13. Success Definition for Next Phase

This specification is ready for `/speckit-plan` when:
- [ ] All functional requirements are clear
- [ ] Acceptance scenarios cover main flows
- [ ] Edge cases documented
- [ ] No unresolved questions

**Recommended Next Step**: `/speckit-plan` to create implementation tasks and timeline
