# Phase 6 Implementation Plan: CSV Upload UI & Auto-Convert Pipeline

**Phase**: 6
**Feature**: CSV Upload UI & Auto-Convert Pipeline
**Created**: 2026-06-02
**Estimated Duration**: 2-3 weeks (10-15 working days)
**Priority**: High (impacts user workflow)

---

## 1. Executive Summary

This plan outlines the implementation strategy for CSV Upload UI integration with Dashboard Portal. The feature adds a web-based upload interface that replaces manual file placement in `data/input/` directory.

### Key Milestones
1. **Week 1**: Backend API development + UI mockup
2. **Week 2**: Frontend integration + Testing
3. **Week 3**: Final testing, documentation, deployment preparation

### Success Definition
- Users can upload CSV files via web UI without SSH access
- Validation happens automatically and clearly
- Dashboard updates within 2 minutes of upload
- Error messages guide users to fix issues

---

## 2. Architecture Overview

### Component Interaction

```
Dashboard Portal (HTML/JavaScript)
    ↓ (POST /api/upload)
Backend API Server
    ├─ Validate file (encoding, headers, delimiter)
    ├─ Check for errors
    └─ Move to data/input/
         ↓
    Cron Job (existing - no changes)
         ↓
    Converters (existing - no changes)
         ↓
    data/output/index.json (updated)
         ↓
    Dashboard auto-refresh (existing)
         ↓
    User sees new data
```

### Technology Stack (Recommendations, not Prescriptions)

| Layer | Options | Notes |
|-------|---------|-------|
| **Frontend** | HTML5 + Vanilla JS, Vue, React | Must work in all modern browsers |
| **Backend** | Flask, FastAPI, Express.js | Must run on same/connected host |
| **File Handling** | Multer (Node), Flask-Upload | Must validate before moving to data/input/ |
| **Validation** | CSV parser library (any language) | Reuse existing CSV parsing logic from converters |
| **Deployment** | systemd, docker, or standalone | Must auto-start and survive restarts |

**Constraint**: Architecture must NOT require changes to existing converters or cron job.

---

## 3. Detailed Task Breakdown

### Phase 6.1: Backend API Development (5-7 days)

#### 6.1.1 Setup Backend Server
**Duration**: 1 day
**Dependencies**: None

**Tasks**:
- [ ] Choose backend framework (Flask, FastAPI, Express.js, etc.)
- [ ] Create basic server scaffold with one test endpoint
- [ ] Setup CORS if backend runs on different port than dashboards
- [ ] Create /api/upload endpoint (POST) - skeleton
- [ ] Add basic error handling middleware
- [ ] Setup logging for all API calls
- [ ] Create health check endpoint

**Acceptance**:
- [ ] `curl http://localhost:XXXX/health` returns 200
- [ ] Logs created for all requests
- [ ] CORS allows dashboard to reach API

**Estimated**: 1 day

---

#### 6.1.2 Implement File Validation Logic
**Duration**: 2 days
**Dependencies**: 6.1.1

**Tasks**:
- [ ] Create encoding detector (UTF-8, Windows-1252, Latin-1, ISO-8859-15)
  - Test with files in different encodings
  - Handle BOM (Byte Order Mark) correctly
- [ ] Create CSV header validator
  - Check required headers: "ID de incidencia", "Estatus", "Fecha de envío", "Grupo asignado", "Urgencia", "Impacto", "Descripción"
  - Return clear error message if missing (e.g., "Missing column: Estatus")
- [ ] Create delimiter detector (auto-detect comma, semicolon, tab)
- [ ] Create row counter (efficient for large files)
- [ ] Create error message generator (user-friendly, specific)

**Test Cases**:
- [ ] Valid UTF-8 CSV → passes
- [ ] Valid Windows-1252 CSV → detects encoding, passes
- [ ] CSV with missing header → specific error message
- [ ] CSV with unusual delimiter → detects, passes
- [ ] Empty CSV → error "No data rows found"
- [ ] Large CSV (100MB) → detects encoding/headers quickly

**Acceptance**:
- [ ] All validation tests pass
- [ ] Error messages are user-friendly (in Spanish)
- [ ] Validation completes in < 2 seconds for typical files

**Estimated**: 2 days

---

#### 6.1.3 Implement File Upload Handler
**Duration**: 1.5 days
**Dependencies**: 6.1.2

**Tasks**:
- [ ] Create POST /api/upload endpoint
  - Receive file from form-data
  - Store in temporary location initially
  - Return validation results JSON
- [ ] File size validation (≤ 500MB)
- [ ] File extension validation (.csv only)
- [ ] Temporary file storage cleanup
  - Files older than 1 hour deleted
  - Failed uploads cleaned up immediately
- [ ] Error handling for network issues
- [ ] Logging of upload events (timestamp, filename, user, status)

**Test Cases**:
- [ ] Upload valid CSV → returns validation results
- [ ] Upload 2MB file → succeeds
- [ ] Upload 600MB file → rejected with message
- [ ] Upload .txt file → rejected as non-CSV
- [ ] Network disconnect mid-upload → handled gracefully
- [ ] Concurrent uploads → queued/handled

**Acceptance**:
- [ ] File uploads complete < 30 seconds for 100MB
- [ ] Validation results returned in < 2 seconds
- [ ] Temp files cleaned up automatically

**Estimated**: 1.5 days

---

#### 6.1.4 Implement File Movement & Conversion Trigger
**Duration**: 1 day
**Dependencies**: 6.1.3

**Tasks**:
- [ ] Create endpoint to move file from temp to `data/input/`
  - Sanitize filename to prevent directory traversal
  - Add timestamp to filename if exists (avoid collision)
  - Log the movement
- [ ] Check that `data/input/` is writable before moving
- [ ] Create mechanism to notify conversion is starting
  - Poll conversion status (or webhook from cron)
  - Return status to frontend
- [ ] Create error handling if move fails
- [ ] Cleanup temp file after successful move

**Test Cases**:
- [ ] Valid file moves to data/input/ ✓
- [ ] Filename with spaces/special chars sanitized ✓
- [ ] Duplicate filename gets timestamp ✓
- [ ] File not writable → error returned ✓

**Acceptance**:
- [ ] File moved to correct location
- [ ] Filename collision handled
- [ ] Temp file cleaned up
- [ ] Frontend notified status

**Estimated**: 1 day

---

#### 6.1.5 Testing & Documentation
**Duration**: 1 day
**Dependencies**: 6.1.4

**Tasks**:
- [ ] Unit tests for each validation function
- [ ] Integration tests (upload → validate → move → check file exists)
- [ ] Error scenario tests (missing headers, bad encoding, etc.)
- [ ] Performance test (100MB file validation < 2 seconds)
- [ ] Concurrent upload test (10+ simultaneous)
- [ ] Create API documentation
  - Endpoint: POST /api/upload
  - Params: file (multipart/form-data)
  - Response: {success: bool, encoding: string, headers: [], rows: int, errors: string[]}
- [ ] Setup CI/CD check for API (if needed)

**Acceptance**:
- [ ] All tests pass
- [ ] Test coverage > 80%
- [ ] API docs complete

**Estimated**: 1 day

---

### Phase 6.2: Frontend UI Development (3-4 days)

#### 6.2.1 Design & Mockup
**Duration**: 0.5 days
**Dependencies**: None (parallel to 6.1)

**Tasks**:
- [ ] Sketch upload modal design
  - Where should "Upload CSV" button go? (header, sidebar, main area?)
  - Modal layout: file picker, submit button, progress indicator
  - Success/error message layout
- [ ] Create wireframe/mockup
- [ ] Get approval from team

**Acceptance**:
- [ ] Design approved
- [ ] Clear user flow documented

**Estimated**: 0.5 days

---

#### 6.2.2 Implement Upload Modal UI
**Duration**: 1 day
**Dependencies**: 6.2.1

**Tasks**:
- [ ] Add "Upload CSV" button to Dashboard Portal
  - Location: header or sidebar
  - Styling consistent with dashboard theme
- [ ] Create modal HTML
  - File input (accept=".csv")
  - Drag-and-drop target
  - Submit button
  - Cancel button
- [ ] Add CSS styling
  - Modal appearance
  - Button states
  - Responsive design (desktop + tablet)
- [ ] Test in multiple browsers (Chrome, Firefox, Safari, Edge)

**Test Cases**:
- [ ] Button visible on Dashboard Portal ✓
- [ ] Modal opens when clicked ✓
- [ ] Modal closes on cancel ✓
- [ ] File picker works ✓
- [ ] Drag-and-drop works ✓
- [ ] Responsive on tablet/mobile ✓

**Acceptance**:
- [ ] Modal appears and functions correctly
- [ ] UI consistent with dashboard theme
- [ ] Works on all major browsers

**Estimated**: 1 day

---

#### 6.2.3 Implement Client-Side Validation
**Duration**: 1 day
**Dependencies**: 6.2.2

**Tasks**:
- [ ] Add file size check (≤ 500MB)
  - Show warning if > 100MB
  - Block if > 500MB
- [ ] Add extension validation (.csv only)
- [ ] Show selected filename before upload
- [ ] Create progress indicator (upload %)
- [ ] Create error message display area
- [ ] Create preview display area (will populate after server validation)

**JavaScript Functions Needed**:
- `validateFileSize(file)` → returns {valid, message}
- `validateExtension(file)` → returns {valid, message}
- `getFileSize(bytes)` → returns "5.2 MB" formatted
- `uploadFile(file)` → calls /api/upload

**Test Cases**:
- [ ] Select valid CSV → form ready to submit ✓
- [ ] Select 600MB file → blocked with message ✓
- [ ] Select .txt file → blocked with message ✓
- [ ] Progress shows during upload ✓

**Acceptance**:
- [ ] Client validation works correctly
- [ ] User gets clear feedback
- [ ] No upload if validation fails

**Estimated**: 1 day

---

#### 6.2.4 Implement Upload & Response Handling
**Duration**: 1 day
**Dependencies**: 6.2.3, 6.1.3 (backend ready)

**Tasks**:
- [ ] Create fetch request to POST /api/upload
- [ ] Handle validation results from server
  - Display preview: filename, encoding, delimiter, row count
  - Display any warnings (unusual encoding, etc.)
  - Display any errors with specific guidance
- [ ] Create "Confirm & Convert" button (shown after validation passes)
- [ ] Call second endpoint to move file and start conversion
- [ ] Show "Processing..." message while conversion runs
- [ ] Auto-close modal after successful upload
- [ ] Show success notification (toast) with record count

**JavaScript Functions**:
- `handleUploadResponse(response)` → validate and show results
- `handleError(error)` → show user-friendly error
- `confirmAndConvert(filename)` → start conversion
- `showNotification(message, type)` → toast notification

**Test Cases**:
- [ ] Valid CSV uploaded → preview shown ✓
- [ ] User clicks confirm → conversion starts ✓
- [ ] Conversion completes → notification shown ✓
- [ ] Error response → error message displayed ✓
- [ ] Network error → handled gracefully ✓

**Acceptance**:
- [ ] Upload → validation → confirmation flow works
- [ ] User receives clear feedback at each step
- [ ] Success notification appears

**Estimated**: 1 day

---

#### 6.2.5 Dashboard Auto-Refresh Integration
**Duration**: 0.5 days
**Dependencies**: 6.2.4

**Tasks**:
- [ ] Ensure dashboard auto-refresh mechanism works
  - Check if `index.json` fetch happens automatically every 10-30 seconds
  - If not, add polling mechanism
- [ ] Update data display when new `index.json` fetched
- [ ] Test that new CSV data appears in dashboard after conversion
- [ ] Verify no manual refresh needed

**Test Cases**:
- [ ] Upload CSV → conversion completes → data appears ✓
- [ ] No manual refresh needed ✓
- [ ] Multiple uploads show cumulative data ✓

**Acceptance**:
- [ ] Dashboard updates automatically after conversion
- [ ] No manual refresh needed
- [ ] New data visible within 5 seconds of conversion complete

**Estimated**: 0.5 days

---

### Phase 6.3: Integration & Testing (3-4 days)

#### 6.3.1 End-to-End Testing
**Duration**: 1.5 days
**Dependencies**: 6.2.5

**Full Workflow Tests**:
- [ ] **Happy Path**: Upload valid CSV → validation passes → converted → dashboard shows data
- [ ] **Error Path 1**: Upload CSV with missing header → specific error shown → user can retry
- [ ] **Error Path 2**: Upload invalid encoding → error shown → user downloads template → retries
- [ ] **Error Path 3**: Network error mid-upload → recovered gracefully
- [ ] **Large File**: Upload 200MB CSV → warning shown → processed successfully
- [ ] **Concurrent**: Upload 3 files simultaneously → all processed correctly
- [ ] **Duplicate**: Upload same file twice → handled without duplication

**Test Data**:
- [ ] Valid incidents CSV
- [ ] CSV with missing "Estatus" column
- [ ] CSV with Windows-1252 encoding
- [ ] Large CSV (100MB+)
- [ ] CSV with unusual characters/special chars

**Acceptance**:
- [ ] All workflows complete successfully
- [ ] Error handling works correctly
- [ ] Large files processed without issues

**Estimated**: 1.5 days

---

#### 6.3.2 Cross-Browser & Responsiveness Testing
**Duration**: 1 day
**Dependencies**: 6.2.5

**Browsers**:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Devices**:
- [ ] Desktop (1920x1080)
- [ ] Tablet (iPad, 768x1024)
- [ ] Mobile (if applicable, though primary use is desktop)

**Test Cases**:
- [ ] File picker works on all browsers
- [ ] Drag-and-drop works on all browsers
- [ ] Modal displays correctly at all resolutions
- [ ] Progress indicator visible on all devices
- [ ] Error messages readable on all sizes

**Acceptance**:
- [ ] Feature works on all major browsers
- [ ] Responsive design functions correctly
- [ ] No visual glitches

**Estimated**: 1 day

---

#### 6.3.3 Performance & Load Testing
**Duration**: 0.5 days
**Dependencies**: 6.1.5

**Tests**:
- [ ] Upload 10MB file → completes < 30 seconds
- [ ] Upload 100MB file → completes < 3 minutes
- [ ] Server validation of 100MB file → < 2 seconds
- [ ] 5 concurrent uploads → all succeed
- [ ] Dashboard refresh after upload → < 5 seconds
- [ ] Server under load → no crashes/timeouts

**Tools** (if applicable):
- Artillery, JMeter, or similar for load testing

**Acceptance**:
- [ ] All performance targets met
- [ ] No degradation under load
- [ ] Memory usage reasonable

**Estimated**: 0.5 days

---

#### 6.3.4 Security Testing
**Duration**: 0.5 days
**Dependencies**: 6.1.5

**Tests**:
- [ ] File path traversal attack blocked (filename like "../../../etc/passwd")
- [ ] Malicious file content not executed (no script injection)
- [ ] Large file bombs rejected (500MB+)
- [ ] Null byte handling correct
- [ ] Special characters in filename handled safely
- [ ] Authentication check (if enabled)

**Acceptance**:
- [ ] No security vulnerabilities found
- [ ] File upload cannot escape `data/input/` directory
- [ ] No code injection possible

**Estimated**: 0.5 days

---

#### 6.3.5 Documentation & Knowledge Transfer
**Duration**: 1 day
**Dependencies**: All previous tasks

**Documentation**:
- [ ] User Guide: "How to Upload CSV Files"
  - Screenshots of upload flow
  - Common errors and solutions
  - Supported CSV format
- [ ] API Documentation
  - Endpoint specifications
  - Request/response examples
  - Error codes
- [ ] Admin Guide: "Setting up CSV Upload Service"
  - Installation instructions
  - Configuration options
  - Troubleshooting
- [ ] Developer Guide
  - Code overview
  - Key functions
  - How to extend/modify

**Knowledge Transfer**:
- [ ] Code walkthrough with team
- [ ] Testing process documented
- [ ] Deployment procedure documented

**Acceptance**:
- [ ] All documentation complete
- [ ] Team can deploy without asking questions
- [ ] Users have clear guides

**Estimated**: 1 day

---

### Phase 6.4: Deployment Preparation (1 day)

#### 6.4.1 Production Readiness
**Duration**: 1 day
**Dependencies**: 6.3.5

**Tasks**:
- [ ] Create deployment script/playbook
  - Install backend dependencies
  - Start API server
  - Configure auto-restart
  - Verify connectivity to `data/input/` and `data/output/`
- [ ] Create rollback procedure (if needed)
- [ ] Setup error monitoring/logging
- [ ] Create runbook for common issues
- [ ] Final smoke test on staging server

**Acceptance**:
- [ ] Deployment automated and documented
- [ ] Feature works identically to dev environment
- [ ] Ready for production deployment

**Estimated**: 1 day

---

## 4. Task Dependencies & Timeline

### Dependency Graph

```
6.1.1 Backend Setup
    ↓
6.1.2 File Validation
    ↓
6.1.3 Upload Handler
    ↓
6.1.4 File Movement
    ↓
6.1.5 Backend Testing ────┐
                          ├──→ 6.3.1 E2E Testing
6.2.1 UI Design           │
    ↓                      │
6.2.2 Modal UI ──────┐    │
    ↓                 │    │
6.2.3 Client Validation
    ↓                 │
6.2.4 Upload Handler ├────→ 6.3.2 Browser Testing
    ↓                 │    │
6.2.5 Dashboard Refresh    │
    ↓                 └────┤
                           │
                    ↓
            6.3.3 Performance
            6.3.4 Security
                    ↓
            6.3.5 Documentation
                    ↓
            6.4.1 Deployment
```

### Timeline (Gantt-style)

```
Week 1:
  [6.1.1    ] Backend Setup
  [6.1.2       ] File Validation
  [6.1.3         ] Upload Handler
  [6.1.4           ] File Movement
  [6.2.1 ] Design
  [6.2.2    ] Modal UI

Week 2:
  [6.1.5           ] Backend Testing
  [6.2.3      ] Client Validation
  [6.2.4        ] Upload Handler (Frontend)
  [6.2.5          ] Dashboard Refresh
  [6.3.1            ] E2E Testing

Week 3:
  [6.3.2      ] Browser Testing
  [6.3.3        ] Performance
  [6.3.4        ] Security
  [6.3.5          ] Documentation
  [6.4.1            ] Deployment
```

---

## 5. Resource Requirements

### Team
- **1 Backend Developer** (5-7 days)
  - API development
  - File validation logic
  - Server setup

- **1 Frontend Developer** (3-4 days)
  - UI implementation
  - JavaScript upload handling
  - Modal/form logic

- **1 QA/Tester** (2-3 days)
  - Test case creation
  - Cross-browser testing
  - Performance testing
  - Security testing

- **0.5 DevOps/Admin** (1 day)
  - Deployment preparation
  - Server setup
  - Monitoring

### Infrastructure
- Backend server (existing or new) with:
  - Python 3.8+ or Node.js
  - Access to `data/input/` and `data/output/` directories
  - 2GB+ disk space for temporary uploads
  - Accessible from dashboard (same host or via network)

### Tools/Libraries (Recommendations)
- **Backend**:
  - Flask-Upload or Multer (file handling)
  - chardet or similar (encoding detection)
  - csv-parser library
  - pytest or similar for testing

- **Frontend**:
  - Vanilla JS or lightweight framework
  - Fetch API for HTTP
  - HTML5 File API

---

## 6. Risk Analysis & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| **Large file upload timeout** | Users cannot upload large files | Medium | Set appropriate timeouts, implement resumable uploads if needed |
| **Encoding detection failure** | File conversion fails for user | Low | Test with diverse encodings, fallback to UTF-8 |
| **Cron job timing issues** | File not converted immediately | Low | Monitor cron, add fallback polling |
| **File system permission issues** | Cannot move file to data/input/ | Medium | Test permissions before production, clear error messages |
| **Network interruption** | Incomplete upload | Low | Cleanup mechanism for partial uploads |
| **Concurrent upload collision** | Files overwrite each other | Low | Timestamp filenames, validate no duplicates |
| **Security vulnerability in upload** | Malicious file execution | Medium | Strict validation, file type checks, sandboxing |
| **UI not intuitive** | Users make mistakes | Medium | User testing, clear error messages, help text |

---

## 7. Success Metrics

### Technical
- [x] API responds to upload requests (< 2 sec for validation)
- [x] Files successfully moved to `data/input/`
- [x] Cron job detects and converts within 30 seconds
- [x] Dashboard refreshes within 5 seconds of conversion
- [x] 10+ concurrent uploads handled without failure
- [x] Error recovery automatic (temp files cleaned up)

### User Experience
- [x] Users complete upload in < 2 minutes
- [x] Error messages guide users to solutions
- [x] No SSH/CLI knowledge required
- [x] UI works on desktop and tablet
- [x] Feedback provided at each step

### Operations
- [x] Feature reduces manual file placement requests
- [x] Less downtime from manual errors
- [x] Clear audit trail of uploads (logging)
- [x] Easy to troubleshoot issues

---

## 8. Post-Implementation

### Support & Maintenance
- [ ] Monitor upload errors/failures
- [ ] Collect user feedback
- [ ] Plan Phase 7 (future enhancements):
  - Bulk upload (multiple files)
  - Schedule uploads
  - Email notifications
  - Upload history/audit trail

### Future Enhancements
- Excel file support
- Automatic field mapping
- Duplicate detection
- Data preview before conversion
- Upload scheduling
- Email notifications on completion

---

## 9. Approval & Sign-Off

**Plan Owner**: [DevOps/Project Lead]
**Reviewed By**: [Technical Lead]
**Approved By**: [Manager]

**Sign-Off**:
- [ ] Plan reviewed and approved
- [ ] Resources allocated
- [ ] Timeline confirmed
- [ ] Ready to proceed

---

**Plan Status**: ✅ READY FOR DEVELOPMENT

**Next Step**: Create sprint tasks from this plan and assign to team members.
