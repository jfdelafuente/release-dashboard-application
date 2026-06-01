# Feature Specification: Unified Dashboard Hub Portal

**Feature Branch**: `002-dashboard-hub`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Ahora tenemos 2 dashboard al que se accede de forma independiente. Quiero que tengamos un acceso unificado desde donde podemos acceder a los dos y tengamos un primer vistazo de los kpis"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access Dashboard Hub Portal (Priority: P1)

As an analyst, I need a unified entry point to access both dashboards and see key metrics at a glance, so that I can quickly assess incident status without having to navigate between separate applications.

**Why this priority**: This is the core MVP feature - it creates the unified access point that the user specifically requested. Without this, the feature doesn't exist.

**Independent Test**: Can be fully tested by opening the Dashboard Hub, verifying both dashboards are accessible via navigation links, and confirming KPI metrics are displayed on the main page.

**Acceptance Scenarios**:

1. **Given** I am on the Dashboard Hub homepage, **When** I view the page, **Then** I see a header with navigation options to "Postmortem Dashboard" and "Massive Incidents Dashboard"
2. **Given** I am on the Dashboard Hub homepage, **When** I click on "Postmortem Dashboard" link, **Then** I am redirected to the Postmortem Dashboard
3. **Given** I am on the Dashboard Hub homepage, **When** I click on "Massive Incidents Dashboard" link, **Then** I am redirected to the Massive Incidents Dashboard
4. **Given** I am on a child dashboard (Postmortem or Massive Incidents), **When** I want to return to the hub, **Then** I see a "Back to Hub" or "Dashboard Hub" link in the navigation

---

### User Story 2 - View KPI Summary from Both Dashboards (Priority: P1)

As an analyst, I need to see a consolidated KPI summary on the hub that shows key metrics from both the Postmortem Dashboard and Massive Incidents Dashboard, so that I can quickly assess the overall system health without opening individual dashboards.

**Why this priority**: This is the second core feature explicitly requested ("primer vistazo de los kpis"). It delivers the summarized view that makes the hub valuable.

**Independent Test**: Can be fully tested by verifying that KPI cards are rendered on the Dashboard Hub with correct values aggregated or summarized from both dashboards.

**Acceptance Scenarios**:

1. **Given** I open the Dashboard Hub for the first time, **When** the page loads, **Then** it automatically loads the most recent JSON file from `data/output/` without prompting me to select a file
2. **Given** a recent JSON file exists in `data/output/`, **When** I view the Dashboard Hub, **Then** I see cards displaying key metrics from the Massive Incidents Dashboard (Total Incidents, Pending Incidents, Trends)
3. **Given** a recent JSON file exists in `data/output/`, **When** I view the Dashboard Hub, **Then** I see cards displaying key metrics from the Postmortem Dashboard (Total Postmortems, Unresolved Items, etc.)
4. **Given** multiple JSON files exist in `data/output/`, **When** the Dashboard Hub loads, **Then** it selects the file with the most recent modification timestamp
5. **Given** KPI data is loading, **When** I view the Dashboard Hub, **Then** I see loading indicators or placeholders until data is available
6. **Given** I am on the Dashboard Hub, **When** I click on a KPI card, **Then** I am redirected to the relevant dashboard with that KPI highlighted or filtered (optional deeper interaction)

---

### User Story 3 - Responsive Design and Mobile Support (Priority: P2)

As an analyst on the go, I need the Dashboard Hub to be responsive and work on mobile/tablet devices, so that I can quickly check dashboard status from any device.

**Why this priority**: Enhances usability but not critical for MVP. Can be implemented after core navigation works.

**Independent Test**: Can be fully tested by opening the Dashboard Hub on mobile/tablet browsers and verifying that all elements are visible, clickable, and properly formatted.

**Acceptance Scenarios**:

1. **Given** I am viewing the Dashboard Hub on a mobile device, **When** I view the navigation menu, **Then** it displays in a mobile-friendly format (e.g., hamburger menu or stacked layout)
2. **Given** I am viewing the Dashboard Hub on a tablet, **When** I view the KPI cards, **Then** they are properly sized and readable without horizontal scrolling
3. **Given** I click on a dashboard link from a mobile device, **When** the dashboard loads, **Then** it is properly formatted for the mobile screen

---

### Edge Cases

- What happens when one of the child dashboards is unavailable or fails to load? (System should display a graceful error message)
- How does the system handle when no JSON data files exist in `data/output/`? (Should show placeholder/empty state with message explaining where to put JSON files)
- What happens when the latest JSON file in `data/output/` is corrupted or invalid? (System should display error and suggest checking file format)
- What happens when the user navigates directly to a child dashboard and then tries to return to hub? (Back navigation should work correctly)
- How does the hub handle if a user's browser blocks third-party iframes or data loading? (Should display clear error with troubleshooting steps)
- What happens when the `data/output/` directory is inaccessible or permissions are denied? (System should display error explaining the issue)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard Hub MUST display a navigation header with links to both the Postmortem Dashboard and Massive Incidents Dashboard
- **FR-002**: Dashboard Hub MUST automatically load the most recent JSON file from the `data/output/` directory on page load without requiring user file selection
- **FR-003**: Dashboard Hub MUST detect and use the latest JSON file by comparing file modification timestamps in the default directory
- **FR-004**: Dashboard Hub MUST load and display KPI summary metrics from the Massive Incidents Dashboard (at minimum: Total Incidents, Pending Incidents, 7-day/15-day/30-day trends)
- **FR-005**: Dashboard Hub MUST load and display KPI summary metrics from the Postmortem Dashboard (at minimum: Total Postmortems, Unresolved Items, Status distribution)
- **FR-006**: Dashboard Hub MUST allow users to navigate to the Postmortem Dashboard when clicking its link
- **FR-007**: Dashboard Hub MUST allow users to navigate to the Massive Incidents Dashboard when clicking its link
- **FR-008**: Dashboard Hub MUST display loading states while data is being fetched
- **FR-009**: Dashboard Hub MUST handle errors gracefully and display meaningful error messages if KPI data cannot be loaded or no JSON files exist in the default directory
- **FR-010**: Dashboard Hub MUST be responsive and render correctly on desktop, tablet, and mobile screens
- **FR-011**: Child dashboards (Postmortem, Massive Incidents) MUST include a navigation option to return to the Dashboard Hub
- **FR-012**: Dashboard Hub MUST use the same authentication/session context as the existing dashboards (no login required if already authenticated)

### Key Entities

- **Dashboard Hub**: The main portal page that aggregates navigation and KPI summaries from both dashboards
- **KPI Summary Card**: Display component showing a single metric with value, label, and optional trend indicator
- **Navigation Menu**: Header/menu component providing access to both child dashboards and hub

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from the Dashboard Hub to either dashboard in under 2 seconds
- **SC-002**: KPI metrics load and display within 3 seconds of page load
- **SC-003**: 100% of navigation links function correctly and direct to the intended dashboard
- **SC-004**: Dashboard Hub displays correctly on 100% of tested screen sizes (desktop, tablet, mobile)
- **SC-005**: Users report improved workflow efficiency: able to assess system status from single entry point
- **SC-006**: Page load time for Dashboard Hub is under 2 seconds (measured with average network conditions)
- **SC-007**: No JavaScript errors occur during normal usage on modern browsers (Chrome, Firefox, Safari, Edge)

## Assumptions

- Dashboard Hub will be a new HTML file (similar to existing Postmortem and Massive Incidents dashboards) deployed in the same directory
- Both existing dashboards already export their KPI data in a format accessible to the hub (JSON from their data loading functions)
- Users already have access to both dashboards (no additional permissions management needed)
- Authentication/session management from the existing dashboards will be reused (no new auth system needed)
- Dashboard Hub will use vanilla JavaScript (no new frontend framework dependencies) to match the existing dashboard implementation
- The hub will load KPI data from existing JavaScript functions or APIs used by the current dashboards
- Mobile responsiveness will be achieved using CSS media queries and responsive design patterns
- The feature does not require backend modifications - it's purely a new frontend entry point
- The default directory for loading JSON files is `data/output/` (where converted incident data is stored)
- The Dashboard Hub automatically loads the most recent JSON file from the default directory without user intervention

## Clarifications

### Session 2026-05-13

- Q: Should the Dashboard Hub auto-load the latest JSON file from the default directory? → A: Yes, by default it must load the most recent JSON file from `data/output/` automatically without user selection
