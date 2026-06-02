# Tasks: Phase 6 - CSV Upload UI & Auto-Convert Pipeline

**Feature**: CSV Upload UI & Auto-Convert Pipeline
**Phase**: 6
**Status**: Ready for Development
**Total Tasks**: 48
**Timeline**: 2-3 weeks (10-15 working days)

---

## Overview

Task breakdown organized by user story priority. Each story is independently testable and can be developed in parallel where noted. Setup and foundational tasks must complete first.

### User Stories Covered
- **US1 (P1)**: Upload Interface - Users can upload CSV files via web UI
- **US2 (P1)**: File Validation - System validates uploaded files automatically
- **US3 (P1)**: Conversion Pipeline - Files converted to JSON by cron job
- **US4 (P2)**: Error Handling - Clear error messages guide users to fix issues
- **US5 (P2)**: Dashboard Integration - Dashboard auto-refreshes with new data

### Key Constraints
- No changes to existing converters or cron job
- Validate file encoding, headers, delimiter
- Support files up to 500MB
- Handle 10+ concurrent uploads
- User-friendly error messages (Spanish)

---

## Phase 1: Setup & Infrastructure

### Goals
- Configure development environment
- Setup backend and frontend scaffolding
- Establish project structure
- Prepare testing infrastructure

### Tasks

- [X] T001 Initialize backend project structure with framework chosen (Flask, FastAPI, or Express.js), create main server file, and setup initial requirements/package files in `backend/` directory
- [X] T002 [P] Initialize frontend project structure with module loader or build tool, create HTML/JS entry points in `dashboards/` directory, setup package.json if using Node.js
- [X] T003 Create `/api/health` endpoint in backend to verify server is running and responding correctly
- [X] T004 Setup CORS configuration in backend to allow dashboard (frontend) to communicate with API if running on different port/host
- [X] T005 [P] Create logging infrastructure in backend (all API calls, file operations, errors logged with timestamp)
- [X] T006 Setup basic error middleware in backend (catch unhandled errors, return user-friendly error messages)
- [X] T007 Create `.env` configuration file template with required settings (upload directory paths, max file size, temporary directory)
- [X] T008 Create directory structure for test data: `converters/tests/test_data/` with sample CSV files (valid, invalid, various encodings)
- [X] T009 [P] Setup testing framework for backend (pytest fixtures, test config, test directory structure)
- [X] T010 [P] Setup testing framework for frontend (browser testing setup, test runners)

### Independent Test Criteria
- [ ] Backend server starts and `/health` endpoint responds with 200
- [ ] CORS headers present in responses (if applicable)
- [ ] All API requests logged with timestamp and status
- [ ] Directory structure exists for uploads and test data

---

## Phase 2: Foundational Components

### Goals
- Build shared infrastructure used by all user stories
- Implement core validation logic
- Setup file handling utilities
- Prepare for user story implementation

### Tasks

- [X] T011 Implement encoding detector in `backend/validators/encoding.py` supporting UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15 with tests
- [X] T012 [P] Implement CSV delimiter detector in `backend/validators/delimiter.py` (auto-detect comma, semicolon, tab) with fallback to comma
- [X] T013 [P] Implement required headers validator in `backend/validators/headers.py` checking for: "ID de incidencia", "Estatus", "Fecha de envío", "Grupo asignado", "Urgencia", "Impacto", "Descripción"
- [X] T014 [P] Implement CSV row counter in `backend/validators/counter.py` efficiently counting rows without loading entire file into memory
- [X] T015 Create error message generator in `backend/utils/error_messages.py` producing user-friendly error messages in Spanish for all validation failures
- [X] T016 Create file sanitizer in `backend/utils/sanitizer.py` removing/escaping dangerous characters, preventing directory traversal attacks
- [X] T017 [P] Create temporary file manager in `backend/utils/temp_files.py` handling cleanup of old temp files (>1 hour) and failed uploads
- [X] T018 Implement CSV preview generator in `backend/utils/preview.py` extracting file metadata (encoding, delimiter, row count, first 3-5 headers)
- [X] T019 [P] Create upload logger in `backend/logging/upload_log.py` tracking all uploads (timestamp, filename, file size, user, status, errors)
- [X] T020 Create validation test suite in `tests/test_validators.py` with test cases for all validators (valid/invalid inputs, edge cases)

### Independent Test Criteria
- [ ] All validators return correct results for test data
- [ ] Error messages are clear and actionable
- [ ] File sanitizer prevents path traversal
- [ ] Temp file cleanup works correctly
- [ ] All 20+ validation test cases pass

---

## Phase 3: User Story 1 - Upload Interface (P1)

### Story Goal
Users can upload CSV files directly via web UI without SSH/CLI access. Simple, intuitive interface with clear feedback.

### User Story Tasks

#### US1.1 Backend File Reception

- [X] T021 [US1] Create POST `/api/upload` endpoint in `backend/routes/upload.py` receiving multipart/form-data with CSV file
- [X] T022 [US1] Implement file size validation in upload endpoint (max 500MB, return 413 if exceeded) with user-friendly message
- [X] T023 [US1] Implement file extension validation in upload endpoint (.csv only, return 400 with specific error if different)
- [X] T024 [US1] Create temporary file storage in `backend/utils/temp_upload.py` storing received file with unique temporary name
- [X] T025 [US1] Implement basic error responses (400 Bad Request, 413 Payload Too Large, 500 Server Error) with JSON error details

#### US1.2 Frontend Upload Modal

- [X] T026 [P] [US1] Create modal HTML structure in `dashboards/upload-modal.html` with file input, drag-drop zone, submit/cancel buttons
- [X] T027 [P] [US1] Add "Upload CSV" button to `dashboards/dashboard-portal.html` header/navigation to open modal
- [X] T028 [P] [US1] Implement modal CSS styling in `dashboards/css/upload-modal.css` for responsive design (desktop, tablet)
- [X] T029 [P] [US1] Implement file input handler JavaScript in `dashboards/js/upload-modal.js` capturing file selection and validating basic info
- [X] T030 [US1] Implement drag-and-drop handler in `dashboards/js/upload-modal.js` accepting CSV files via drag-drop with visual feedback
- [X] T031 [US1] Create progress indicator in modal HTML showing upload percentage during transmission

#### US1.3 Client-Side Validation

- [X] T032 [P] [US1] Implement file size check in `dashboards/js/upload-modal.js` (warn if >100MB, block if >500MB)
- [X] T033 [P] [US1] Implement file extension check in `dashboards/js/upload-modal.js` (.csv only, show specific error if not)
- [X] T034 [US1] Display selected filename in modal before upload for user confirmation
- [X] T035 [US1] Create error message display area in modal HTML for user-friendly error feedback
- [X] T036 [US1] Implement progress bar update during upload using XMLHttpRequest or fetch progress events

#### US1.4 Upload Integration

- [X] T037 [US1] Create fetch request in `dashboards/js/upload-modal.js` POST to `/api/upload` with file and progress tracking
- [X] T038 [US1] Implement error handling in upload request (network errors, server errors) with retry capability
- [X] T039 [US1] Create response parser for upload API response containing validation metadata
- [X] T040 [US1] Add success/error toast notification system in `dashboards/js/notifications.js` for user feedback

### Independent Test Criteria - US1
- [ ] Upload modal opens/closes correctly
- [ ] File picker triggers file selection
- [ ] Drag-and-drop accepts CSV files
- [ ] Client-side validation blocks oversized/non-CSV files
- [ ] Progress indicator shows upload percentage
- [ ] POST request to `/api/upload` succeeds with valid file
- [ ] Error responses trigger error notifications
- [ ] Works in Chrome, Firefox, Safari, Edge

---

## Phase 4: User Story 2 - File Validation (P1)

### Story Goal
Backend automatically validates uploaded CSV files (encoding, headers, delimiter) and returns clear validation results to user.

### User Story Tasks

#### US2.1 Server-Side Validation Pipeline

- [X] T041 [US2] Create validation orchestrator in `backend/services/validation_service.py` calling all validators in sequence (encoding → delimiter → headers → rows)
- [X] T042 [US2] Implement encoding validation in POST `/api/upload` using encoding detector, detecting file encoding from first 4KB bytes
- [X] T043 [US2] Implement delimiter detection in validation pipeline, auto-detecting CSV delimiter (comma, semicolon, tab)
- [X] T044 [US2] Implement header validation in validation pipeline, checking required headers present and providing specific missing column error
- [X] T045 [US2] Implement row count detection in validation pipeline for preview metadata
- [X] T046 [US2] Create validation response object in `backend/models/validation_result.py` containing: encoding, delimiter, headers, row_count, errors, warnings

#### US2.2 Validation Error Handling

- [X] T047 [US2] Generate user-friendly error messages for missing headers (e.g., "Missing required column: 'Estatus' - please check your CSV")
- [X] T048 [US2] Generate error messages for unsupported encoding (suggest UTF-8 or ask user to convert file)
- [X] T049 [US2] Generate error messages for parsing failures (line number, specific error, suggestion)
- [X] T050 [US2] Create validation error list structure returning all validation issues in single response

#### US2.3 Preview & User Confirmation

- [X] T051 [US2] Extend `/api/upload` response to include preview data: detected_encoding, detected_delimiter, header_names, row_count, file_size_formatted
- [X] T052 [US2] Return validation_passed boolean to frontend indicating file is acceptable
- [X] T053 [US2] Implement warning generation (e.g., "Unusual encoding detected: Windows-1252") returned in response

#### US2.4 Validation Testing

- [X] T054 [US2] Create integration test for valid CSV upload → validation passes and returns correct metadata
- [X] T055 [US2] Create test for CSV with missing required header → specific error returned
- [X] T056 [US2] Create test for non-UTF-8 encoding → encoding correctly detected
- [X] T057 [US2] Create test for unusual delimiter (semicolon) → correctly detected
- [X] T058 [US2] Create test for empty CSV → error "No data rows found"
- [X] T059 [US2] Create test for large CSV (50MB+) → validation completes in <2 seconds

### Independent Test Criteria - US2
- [ ] All validators return correct results for test CSVs
- [ ] Validation completes in < 2 seconds for typical files
- [ ] Error messages are specific and actionable
- [ ] Preview data accurately reflects file contents
- [ ] Concurrent validations don't interfere with each other

---

## Phase 5: User Story 3 - Conversion Pipeline (P1)

### Story Goal
After file validation and user confirmation, CSV file moved to `data/input/` and automatically converted by existing cron job to JSON data visible in dashboard.

### User Story Tasks

#### US3.1 File Confirmation & Movement

- [ ] T060 [US3] Create POST `/api/confirm-upload` endpoint in `backend/routes/upload.py` accepting validated file reference
- [ ] T061 [US3] Implement sanitized filename generation in `/api/confirm-upload` (remove special chars, add timestamp if duplicate)
- [ ] T062 [US3] Implement file movement from temporary directory to `data/input/` in `/api/confirm-upload`, with validation that target directory is writable
- [ ] T063 [US3] Handle file movement errors gracefully (permission denied, disk full, etc.) returning specific error to user
- [ ] T064 [US3] Log file movement event with original filename, sanitized filename, timestamp, file size to upload log

#### US3.2 Conversion Trigger

- [ ] T065 [US3] Create mechanism to poll conversion status after file moved (or wait for webhook if cron provides notification)
- [ ] T066 [US3] Return conversion status to frontend indicating "Processing started..."
- [ ] T067 [US3] Implement timeout mechanism (wait up to 2 minutes for conversion, then notify user if still pending)

#### US3.3 Frontend Confirmation & Feedback

- [ ] T068 [US3] Extend modal to show preview after validation (filename, encoding, rows, etc.) with confirmation button
- [ ] T069 [US3] Implement "Confirm & Convert" button click handler calling `/api/confirm-upload`
- [ ] T070 [US3] Show "Processing..." message in modal after confirmation
- [ ] T071 [US3] Auto-close modal after successful upload/confirmation
- [ ] T072 [US3] Display success notification with converted record count after conversion complete

#### US3.4 Integration Testing

- [ ] T073 [US3] Create E2E test: upload valid CSV → validation passes → file moved to data/input/ → verify file exists
- [ ] T074 [US3] Create test for large file (200MB) → moved successfully without corruption
- [ ] T075 [US3] Create test for concurrent uploads → all files moved without collision/overwrite
- [ ] T076 [US3] Create test for filename with special characters → properly sanitized and moved

### Independent Test Criteria - US3
- [ ] File successfully moved from temp to `data/input/`
- [ ] Filenames sanitized correctly (no path traversal)
- [ ] Duplicate filenames handled (timestamp added)
- [ ] Cron job detects and converts file within 30 seconds
- [ ] JSON output exists in `data/output/`
- [ ] No data corruption in conversion

---

## Phase 6: User Story 4 - Error Handling (P2)

### Story Goal
Clear, actionable error messages guide users to fix issues. System recovers gracefully from failures (network, file system, validation).

### User Story Tasks

#### US4.1 Validation Error Messages

- [ ] T077 [US4] Create missing header error template: "Missing required column: {column_name} - Check that your CSV file includes this column"
- [ ] T078 [US4] Create unsupported encoding error with suggestion: "This encoding is not supported. Please convert file to UTF-8"
- [ ] T079 [US4] Create delimiter detection error: "Could not detect CSV delimiter. Please use comma, semicolon, or tab"
- [ ] T080 [US4] Create row count error: "No data rows found in CSV file. Ensure data starts below headers"

#### US4.2 Network & File System Errors

- [ ] T081 [US4] Implement network error handler in frontend: "Connection failed. Please check your internet and retry"
- [ ] T082 [US4] Implement file system error handling: "Permission denied. Cannot write to data directory"
- [ ] T083 [US4] Implement disk space error: "Not enough disk space. Please free up space and retry"
- [ ] T084 [US4] Create retry mechanism with exponential backoff (retry 1s, 3s, 5s, then fail)

#### US4.3 Error Recovery

- [ ] T085 [US4] Temporary file cleanup on upload failure (temp file deleted, not orphaned)
- [ ] T086 [US4] Partial upload handling (incomplete file rejected, not left in data/input/)
- [ ] T087 [US4] Error logging with full stack trace (for admin debugging) while showing simple message to user
- [ ] T088 [US4] Error report download option (user can download validation error details for analysis)

#### US4.4 Error Message Localization

- [ ] T089 [US4] All error messages in Spanish (no English error codes shown to users)
- [ ] T090 [US4] Help/documentation links pointing to troubleshooting guide (in Spanish)

#### US4.5 Error Handling Testing

- [ ] T091 [US4] Test missing header error message → specific, actionable guidance provided
- [ ] T092 [US4] Test network error handling → retry works, eventual success or timeout message
- [ ] T093 [US4] Test file system error → clear message what went wrong and how to fix
- [ ] T094 [US4] Test concurrent upload with one failure → failed upload doesn't affect others
- [ ] T095 [US4] Test temp file cleanup → no orphaned files after failed upload

### Independent Test Criteria - US4
- [ ] All error messages are user-friendly (Spanish)
- [ ] Specific error guidance helps users fix issues
- [ ] Failed uploads don't corrupt system state
- [ ] Retry mechanisms work correctly
- [ ] Logs contain detailed error information for debugging

---

## Phase 7: User Story 5 - Dashboard Integration (P2)

### Story Goal
Dashboard automatically refreshes and displays new data after conversion, no manual action needed.

### User Story Tasks

#### US5.1 Dashboard Auto-Refresh

- [ ] T096 [US5] Verify existing dashboard auto-refresh mechanism in `dashboards/js/` that polls `index.json` (check interval: every 10-30 seconds)
- [ ] T097 [US5] If auto-refresh doesn't exist, implement polling mechanism that fetches `data/output/index.json` periodically
- [ ] T098 [US5] Implement event listener for successful conversion notification (from API)
- [ ] T099 [US5] Trigger immediate dashboard refresh when conversion completes (don't wait for next poll cycle)

#### US5.2 Data Display Update

- [ ] T100 [US5] Verify dashboard data display updates when new `index.json` loaded
- [ ] T101 [US5] Test that incident data appears in dashboard filters/tables after upload
- [ ] T102 [US5] Test that multiple uploads show cumulative data (not duplicates or overwrites)
- [ ] T103 [US5] Ensure KPI cards (Total, Pending, Trends) update correctly with new data

#### US5.3 User Feedback During Refresh

- [ ] T104 [US5] Show loading indicator during dashboard refresh (if lengthy operation)
- [ ] T105 [US5] Display notification "Dashboard updated with new data" after refresh completes
- [ ] T106 [US5] Provide visual indication of last refresh time in dashboard

#### US5.4 Integration Testing

- [ ] T107 [US5] E2E test: upload CSV → conversion complete → dashboard shows new data within 5 seconds
- [ ] T108 [US5] Test dashboard refresh after multiple uploads → all data visible, no duplication
- [ ] T109 [US5] Test dashboard doesn't break if index.json missing/corrupted (graceful error)
- [ ] T110 [US5] Test concurrent uploads → dashboard updates for each correctly

### Independent Test Criteria - US5
- [ ] Dashboard polls `index.json` automatically
- [ ] New data appears within 5 seconds of conversion
- [ ] No manual refresh needed
- [ ] Multiple uploads show cumulative data
- [ ] Dashboard handles missing/corrupted `index.json` gracefully

---

## Phase 8: Polish & Cross-Cutting Concerns

### Goals
- Complete documentation
- Finalize testing
- Performance optimization
- Prepare for production

### Tasks

- [ ] T111 Cross-browser testing: Chrome, Firefox, Safari, Edge on desktop and tablet
- [ ] T112 [P] Performance testing: upload 10MB file completes <30s, 100MB completes <3min
- [ ] T113 [P] Load testing: 5+ concurrent uploads handled without failure
- [ ] T114 Security testing: path traversal attacks blocked, no code injection possible
- [ ] T115 [P] Create User Guide in Spanish: "How to Upload CSV Files" with screenshots
- [ ] T116 [P] Create Admin Guide: "Setting up CSV Upload Service" with installation steps
- [ ] T117 Create API Documentation: endpoint specs, request/response examples, error codes
- [ ] T118 Create Developer Guide: code overview, key functions, extending the feature
- [ ] T119 [P] Setup production deployment script in `scripts/deploy-upload-service.sh`
- [ ] T120 [P] Create health check endpoint test suite in `tests/health_checks.py`
- [ ] T121 Create smoke test for production deployment (verify feature works end-to-end)
- [ ] T122 Setup error monitoring/logging in production
- [ ] T123 Create rollback procedure documentation
- [ ] T124 [P] Setup runbook for common issues in `docs/CSV_UPLOAD_RUNBOOK.md`
- [ ] T125 Final integration test: entire workflow verified (upload → validate → convert → display)

---

## Task Dependencies & Execution Strategy

### Phase Dependency Order
```
Phase 1 (Setup) [REQUIRED FIRST]
    ↓
Phase 2 (Foundational) [REQUIRED BEFORE USER STORIES]
    ↓
Phase 3 (US1 Upload)  ────┐
Phase 4 (US2 Validation) ├─→ Can execute in parallel
Phase 5 (US3 Conversion) ─┘
    ↓
Phase 6 (US4 Error Handling) ────┐
Phase 7 (US5 Dashboard)          ├─→ Can execute in parallel
    ↓
Phase 8 (Polish & Deployment)
```

### Within-Phase Parallelization

**Phase 1 - Can parallelize**:
- T001 (backend setup) + T002 (frontend setup)
- T005 (backend logging) + T010 (frontend testing setup)
- T008 (test data) + T007 (config template)

**Phase 2 - Can parallelize**:
- T011 (encoding), T012 (delimiter), T013 (headers), T014 (counter) all independent
- T017 (temp files) + T019 (upload logger) independent
- T020 (test suite) can run after validators are implemented

**Phase 3 - Partial parallelization**:
- T026-T030 (modal HTML/CSS/JS) can run in parallel
- T021-T025 (backend) + T032-T036 (client validation) can run in parallel (different files)
- T037-T040 (integration) waits for backend done

**Phase 4 - Can parallelize**:
- T041 (orchestrator) must be first
- T042-T045 (individual validators) can parallelize
- T047-T050 (error messages) can parallelize
- T054-T059 (tests) can parallelize

**Phase 5 - Partial parallelization**:
- T060-T064 (backend file movement) sequential
- T068-T072 (frontend confirmation) can parallelize with T065-T066
- T073-T076 (tests) after implementation done

**Phase 6 & 7 - Can parallelize**:
- US4 (error handling) and US5 (dashboard) are mostly independent
- Can develop both teams in parallel

**Phase 8 - Mostly sequential**:
- All components must exist before testing
- Documentation can parallelize (different docs)

---

## MVP Scope (Minimal Viable Product)

**Phase 1**: Setup (T001-T010)
**Phase 2**: Foundational (T011-T020)
**Phase 3**: US1 - Upload Interface (T021-T040)
**Phase 4**: US2 - File Validation (T041-T059)
**Phase 5**: US3 - Conversion Pipeline (T060-T076)

**MVP Features**:
- Users can upload CSV files via web UI
- Automatic validation (encoding, headers, rows)
- File moved to data/input/ for cron conversion
- Dashboard shows converted data

**MVP Timeline**: 1 week (Phase 1-5)

**Later additions** (Phases 6-8):
- Enhanced error handling (US4)
- Dashboard refinements (US5)
- Complete documentation & polish

---

## Success Criteria Checklist

### Technical Success
- [ ] All 125 tasks completed and verified
- [ ] Test coverage > 80% for backend code
- [ ] Cross-browser testing passed (Chrome, Firefox, Safari, Edge)
- [ ] Performance targets met (< 60s upload, < 5s refresh)
- [ ] Security testing passed (no vulnerabilities found)

### Functional Success
- [ ] Users upload CSV files via modal
- [ ] Validation catches all bad files with clear errors
- [ ] Valid files converted to JSON within 2 minutes
- [ ] Dashboard auto-updates without manual refresh

### User Experience Success
- [ ] Operations team can upload files without SSH knowledge
- [ ] Error messages guide users to solutions
- [ ] Modal works on desktop and tablet
- [ ] Process takes < 2 minutes end-to-end

### Operations Success
- [ ] Deployment fully automated
- [ ] Error monitoring setup
- [ ] Rollback procedure documented
- [ ] Runbook for common issues

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Tasks** | 125 |
| **Setup Tasks** | 10 |
| **Foundational Tasks** | 10 |
| **User Story 1 Tasks** | 20 |
| **User Story 2 Tasks** | 19 |
| **User Story 3 Tasks** | 17 |
| **User Story 4 Tasks** | 19 |
| **User Story 5 Tasks** | 15 |
| **Polish & Deployment** | 15 |
| **Parallelizable Tasks** | 45 |
| **Estimated Effort** | 10-15 days |
| **Team Size** | 2-3 developers |
| **MVP Tasks** | 59 (Phase 1-5) |
| **MVP Timeline** | ~1 week |

---

**Status**: ✅ Ready for development sprint planning
**Next Step**: Assign tasks to team members, estimate story points, create sprints
