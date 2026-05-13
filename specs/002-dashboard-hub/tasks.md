# Tasks: Unified Dashboard Hub Portal

**Feature**: Dashboard Hub Portal (002-dashboard-hub)

**Input**: Design documents from `specs/002-dashboard-hub/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/dashboard-hub-interface.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and basic HTML/CSS/JS files

- [x] T001 Create dashboard-hub.html main page in root directory with proper DOCTYPE and meta tags
- [x] T002 Create dashboard-hub.css stylesheet in root directory with base styling
- [x] T003 [P] Create dashboard-hub.js JavaScript file in root directory with core functions
- [x] T004 Create data/ directory structure with input/, output/, and errors/ subdirectories (verify .gitignore protects data/)
- [x] T005 Verify .gitignore includes data/ and datos/ directories to protect sensitive incident data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user stories can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement auto-detection logic to find latest JSON file in data/output/ by timestamp in dashboard-hub.js
- [x] T007 Implement loadLatestJSON() async function in dashboard-hub.js that fetches and parses latest JSON file
- [x] T008 Implement error handling for missing/corrupted JSON files with user-friendly messages in dashboard-hub.js
- [x] T009 Create base CSS layout with hub-container, hub-header, kpi-summary, hub-footer classes in dashboard-hub.css
- [x] T010 [P] Create CSS classes for KPI cards (.kpi-card, .kpi-value, .kpi-label, .kpi-trend) in dashboard-hub.css
- [x] T011 [P] Create CSS state classes (.loading, .error, .success, .trend-up, .trend-down, .trend-neutral) in dashboard-hub.css

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Access Dashboard Hub Portal (Priority: P1) 🎯 MVP

**Goal**: Create a unified entry point with navigation to both dashboards

**Independent Test**: Can open Dashboard Hub, see navigation links to both dashboards, and click to navigate to each one without errors

### Implementation for User Story 1

- [x] T012 [P] [US1] Create navigation HTML structure with links to postmortem-dashboard.html and massive-incidents-dashboard.html in dashboard-hub.html
- [x] T013 [P] [US1] Create hub header with title "System Status Dashboard Hub" in dashboard-hub.html
- [x] T014 [US1] Implement initHub() function in dashboard-hub.js that orchestrates page initialization
- [x] T015 [US1] Add DOMContentLoaded event listener to call initHub() in dashboard-hub.js
- [x] T016 [US1] Style navigation bar (.hub-navigation, .nav-item) with hover effects in dashboard-hub.css
- [x] T017 [US1] Test navigation links work bidirectionally (hub → dashboards → back to hub) manually

**Checkpoint**: User Story 1 is complete - users can access hub and navigate to dashboards

---

## Phase 4: User Story 2 - View KPI Summary from Both Dashboards (Priority: P1) 🎯 MVP

**Goal**: Display auto-loaded KPI metrics from both Massive Incidents and Postmortem dashboards

**Independent Test**: Dashboard Hub loads automatically on page open, detects latest JSON, extracts and displays KPI cards for both dashboards with correct values

### Implementation for User Story 2

- [x] T018 [P] [US2] Implement extractKPIs() function in dashboard-hub.js to extract Massive Incidents metrics (Total, Pending, Trends)
- [x] T019 [P] [US2] Implement extractKPIs() postmortem section in dashboard-hub.js to extract postmortem metrics
- [x] T020 [US2] Create KPI card HTML structure generator in dashboard-hub.js that returns properly formatted DOM elements
- [x] T021 [US2] Implement renderHub() function in dashboard-hub.js to render KPI cards into .kpi-summary sections
- [x] T022 [US2] Add Massive Incidents section HTML (.dashboard-kpis.massive-incidents) to dashboard-hub.html
- [x] T023 [US2] Add Postmortem section HTML (.dashboard-kpis.postmortem) to dashboard-hub.html
- [x] T024 [US2] Style KPI cards with value, label, trend indicator in dashboard-hub.css
- [x] T025 [US2] Implement trend calculation (7-day, 15-day, 30-day percentage changes) in dashboard-hub.js
- [x] T026 [US2] Implement trend color coding (green for decrease, red for increase, gray for stable) in dashboard-hub.css
- [x] T027 [US2] Add last-updated timestamp display and update logic in dashboard-hub.js
- [x] T028 [US2] Format last-updated timestamp (ISO format or human-readable) and display in footer span#last-updated

**Checkpoint**: User Stories 1 AND 2 complete - Dashboard Hub fully functional with auto-load and KPI display

---

## Phase 5: User Story 3 - Responsive Design and Mobile Support (Priority: P2)

**Goal**: Ensure Dashboard Hub works seamlessly on mobile, tablet, and desktop devices

**Independent Test**: Open Dashboard Hub on mobile device (using dev tools or actual device), verify all elements visible, readable, clickable without horizontal scrolling

### Implementation for User Story 3

- [x] T029 [P] [US3] Add viewport meta tag to dashboard-hub.html for mobile responsiveness
- [x] T030 [P] [US3] Implement mobile-first CSS media queries in dashboard-hub.css for screens < 768px
- [x] T031 [P] [US3] Implement tablet CSS media queries in dashboard-hub.css for screens 768px - 1024px
- [x] T032 [P] [US3] Implement desktop CSS media queries in dashboard-hub.css for screens > 1024px
- [ ] T033 [US3] Style navigation bar for mobile (hamburger menu or stacked layout) in dashboard-hub.css
- [ ] T034 [US3] Style KPI cards grid for mobile (single column layout) in dashboard-hub.css
- [ ] T035 [US3] Style KPI cards grid for tablet (2-column layout) in dashboard-hub.css
- [ ] T036 [US3] Style KPI cards grid for desktop (3+ column responsive layout) in dashboard-hub.css
- [ ] T037 [US3] Test KPI card text sizing on mobile (no truncation, readable font sizes) manually
- [ ] T038 [US3] Test touch target sizes on mobile (minimum 44x44px) for navigation links and card interactions
- [ ] T039 [US3] Test horizontal scroll on mobile - verify no scrolling needed

**Checkpoint**: User Story 3 complete - Dashboard Hub responsive across all device sizes

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final testing, optimization, and refinement

### Error Handling & Edge Cases

- [ ] T040 [P] Test behavior when data/output/ directory is empty - verify error message displays correctly
- [ ] T041 [P] Test behavior when data/output/ contains corrupted/invalid JSON - verify graceful error handling
- [ ] T042 [P] Test behavior when data/output/ contains only empty JSON array [] - verify appropriate message
- [ ] T043 [P] Test behavior when JSON file is extremely large (>5MB) - verify performance acceptable
- [ ] T044 [US2] Implement "No data files found" error message with helpful instructions in dashboard-hub.js
- [ ] T045 [US2] Implement "Data file is corrupted" error message with troubleshooting steps in dashboard-hub.js

### Documentation & Integration

- [x] T046 [P] Add "Back to Dashboard Hub" link to postmortem-dashboard.html navigation
- [x] T047 [P] Add "Back to Dashboard Hub" link to massive-incidents-dashboard.html navigation
- [ ] T048 Update README.md to mention Dashboard Hub as primary entry point with instructions
- [ ] T049 Update CLAUDE.md with Dashboard Hub architecture and data flow documentation
- [ ] T050 Create deployment checklist verifying all 3 files (html, css, js) are deployed together

### Browser Testing & Compatibility

- [ ] T051 [P] Test Dashboard Hub in Chrome latest version - verify all functionality
- [ ] T052 [P] Test Dashboard Hub in Firefox latest version - verify all functionality
- [ ] T053 [P] Test Dashboard Hub in Safari latest version - verify all functionality
- [ ] T054 [P] Test Dashboard Hub in Edge latest version - verify all functionality
- [ ] T055 Test page load time performance - verify < 2 seconds with realistic JSON data
- [ ] T056 Test JSON parsing performance - verify < 500ms for 5000+ incident records
- [ ] T057 Test memory usage - verify no memory leaks when navigating between hub and dashboards repeatedly

### Code Quality & Validation

- [ ] T058 [P] Validate dashboard-hub.html for HTML5 compliance
- [ ] T059 [P] Validate dashboard-hub.css for CSS syntax errors
- [ ] T060 [P] Validate dashboard-hub.js for JavaScript syntax errors
- [ ] T061 Verify no console errors in browser developer tools during normal usage
- [ ] T062 Test cross-browser session persistence - verify session maintained when navigating between hub and dashboards

### Final Integration Testing

- [ ] T063 [P] Complete end-to-end test: Open hub → auto-load latest JSON → display KPIs → click to dashboard → return to hub
- [ ] T064 [P] Complete mobile workflow test on actual mobile device or simulator
- [ ] T065 [P] Complete tablet workflow test on actual tablet device or simulator
- [ ] T066 Verify all acceptance criteria from spec.md user stories are met
- [ ] T067 Verify quickstart.md implementation checklist is complete
- [ ] T068 Run specification validation - confirm feature meets all functional requirements (FR-001 through FR-012)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately ✓
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - Can start after T005
- **User Story 2 (Phase 4)**: Depends on Foundational completion - Can start after T011, US1 not required but recommended for context
- **User Story 3 (Phase 5)**: Depends on US1 or US2 completion - Cannot start until core functionality exists
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational - No dependencies on other stories - Independent MVP component
- **US2 (P1)**: Can start after Foundational - No dependencies on US1 but recommended to complete US1 first for user flow - Independent MVP component
- **US3 (P2)**: Must start after US1 AND US2 - Cannot polish responsiveness without core features implemented

### Within Each Phase

- Models/structure before functionality
- Core functionality before enhancements
- All tests before moving to next phase
- Commit after completing each user story phase

### Parallel Opportunities

**Phase 1**: All Setup tasks can run in parallel (different files)

**Phase 2**:
- T006 (auto-detection logic)
- T007 (loadLatestJSON function)
- T008 (error handling)
These can run in parallel but depend on shared dashboard-hub.js file - coordinate changes

- T009 (base layout) can run in parallel with T006-T008
- T010 & T011 (CSS classes) can run in parallel with each other

**Phase 3 (US1)**:
- T012 & T013 (HTML structure) can run in parallel
- T014-T017 can follow HTML creation
- T016-T017 can run in parallel with T014-T015

**Phase 4 (US2)**:
- T018 & T019 (extractKPIs functions) can run in parallel
- T022 & T023 (HTML sections) can run in parallel
- After CSS styling in place (T024-T026), rendering can proceed in parallel

**Phase 5 (US3)**:
- T029-T032 (viewport + media queries) can run in parallel
- T033-T039 (mobile/tablet/desktop styling) can run in parallel per device class

**Phase 6**:
- Error handling tests (T040-T045) can run in parallel
- Documentation updates (T046-T050) can run in parallel
- Browser testing (T051-T054) can run in parallel
- Code quality validation (T058-T060) can run in parallel
- Integration tests (T063-T065) can run in parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# JavaScript logic (coordinate in same file)
Task T006: Auto-detection logic in dashboard-hub.js
Task T007: loadLatestJSON() function in dashboard-hub.js
Task T008: Error handling in dashboard-hub.js

# CSS styling (independent file)
Task T009: Base layout classes in dashboard-hub.css
Task T010: KPI card classes in dashboard-hub.css
Task T011: State classes in dashboard-hub.css
```

---

## Parallel Example: Phase 4 (US2)

```bash
# Extract KPI metrics (can write functions in parallel)
Task T018: Massive Incidents KPI extraction in dashboard-hub.js
Task T019: Postmortem KPI extraction in dashboard-hub.js

# HTML structure (independent sections)
Task T022: Massive Incidents section in dashboard-hub.html
Task T023: Postmortem section in dashboard-hub.html

# Styling (independent classes)
Task T024: KPI card styling in dashboard-hub.css
Task T025: Trend calculation logic in dashboard-hub.js
Task T026: Trend color coding in dashboard-hub.css
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (all files created)
2. Complete Phase 2: Foundational (JSON loading infrastructure)
3. Complete Phase 3: US1 (Dashboard Hub with navigation)
4. Complete Phase 4: US2 (KPI Summary with auto-load)
5. **STOP and VALIDATE**: Manual testing of complete hub functionality
6. Deploy MVP (dashboard-hub.html, css, js + back links in existing dashboards)

**Estimated time**: 3-5 days for MVP

### Incremental Delivery

1. **Deliver MVP** (Phase 1-4): Core hub with auto-load and KPI display
2. **Enhance with mobile** (Phase 5): Add responsive design for tablets/phones
3. **Polish & optimize** (Phase 6): Performance tuning, browser testing, documentation

### Parallel Team Strategy

With multiple developers:

1. One developer: Complete Phase 1 + Phase 2 foundational setup
2. Once Phase 2 complete:
   - Developer A: Phase 3 (US1 - Navigation)
   - Developer B: Phase 4 (US2 - KPI Summary)
3. Once US1 & US2 complete:
   - Developer C: Phase 5 (US3 - Responsive Design)
4. All developers: Phase 6 (Polish & Testing)

---

## Success Criteria Validation

After completing all tasks, validate against spec.md success criteria:

- **SC-001**: Users can navigate from Dashboard Hub to either dashboard in under 2 seconds ✓
- **SC-002**: KPI metrics load and display within 3 seconds of page load ✓
- **SC-003**: 100% of navigation links function correctly ✓
- **SC-004**: Dashboard Hub displays correctly on 100% of tested screen sizes ✓
- **SC-005**: Users report improved workflow efficiency (manual validation) ✓
- **SC-006**: Page load time for Dashboard Hub is under 2 seconds ✓
- **SC-007**: No JavaScript errors during normal usage ✓

---

## Notes

- [P] tasks = different files, no dependencies (use "coordinate" label for same-file tasks)
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after completing each task or logical group (T001-T005, T006-T011, T012-T017, etc.)
- Stop at each checkpoint to validate story functionality independently
- Test on actual browsers, not just dev tools emulation where possible
- Handle timezone and date format consistently (use ISO 8601 for timestamps)
- Ensure cross-browser session context is maintained (no re-authentication when navigating between pages)
